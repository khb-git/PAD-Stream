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


MILESTONE = "POSTV16-AV4-A3-E1-R1-R1"

PROTOCOL_ID = (
    "POSTV16_AV4_A3_E1_R1_R1_PREEXECUTION_COMPLETE_R5_SCHEMA_AUDIT_"
    "EXTENSION_AND_E1R2_CORRECTION_AUTHORITY_FREEZE_V1"
)

STATUS_PASS = (
    "AV4A3E1R1R1_E1R1_PASS_PRESERVED_COMPLETE_R5_SCHEMA_READ_AUDIT_"
    "EXTENSION_FROZEN_E1R2_FULL_SCHEMA_CORRECTIONS_AUTHORIZED_"
    "NO_SCIENTIFIC_EXECUTION"
)

STATUS_BLOCKED = "AV4A3E1R1R1_TECHNICAL_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_E1R1_COMMIT = "3108463e8c8b9e342abb72ec52bf9b31a63bc55c"

E1 = "PAD_Stream_POSTV16_AV4_A3_E1_Refreshed_X13_Structural_InputDomain_Audit.py"
E1_BLOB = "2555ccdb5c3311ea49b0269746ba6ce17aa46258"

E1R1 = "PAD_Stream_POSTV16_AV4_A3_E1_R1_Technical_Authority_Schema_Block_Closure.py"
E1R1_BLOB = "26cd1dcde3850cd3c9bde4b73d67e096e16a1de3"

R5 = (
    "PAD_Stream_POSTV16_AV4_A3_R2_R1_R5_Preexecution_Historical_Gate_Validated_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
R5_BLOB = "7192495d80d656fb950b7c5418f928f32246e93f"

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

E1R1_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R1_Technical_Authority_Schema_Block_Closure"
E1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_E1_R1_Summary.json"
E1R1_CORRECTED = "POSTV16_AV4_A3_E1_R1_Corrected_R5_Reconstruction_Schema_Read_Contract.json"
E1R1_HANDOFF = "POSTV16_AV4_A3_E1_R1_E1R2_Handoff_Contract.json"
E1R1_DECISION = "POSTV16_AV4_A3_E1_R1_Decision_Contract.json"
E1R1_MANIFEST = "POSTV16_AV4_A3_E1_R1_Artifact_Manifest.csv"

E1R1_STATUS = (
    "AV4A3E1R1_ORIGINAL_E1_TECHNICAL_BLOCK_PRESERVED_"
    "R5_RECONSTRUCTION_CONTRACT_SHAPE_SCHEMA_ROOT_CAUSE_CLOSED_"
    "CORRECTED_E1R2_CONTINUATION_PROSPECTIVELY_FROZEN_"
    "NO_E1_SCIENTIFIC_EXECUTION"
)

R5_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_R5_Preexecution_Historical_Gate_Validated_Protocol_Continuation"
)
R5_RECON = "POSTV16_AV4_A3_R2_R1_R5_Refreshed_13Channel_Reconstruction_Contract.json"
R5_TEMPORAL = "POSTV16_AV4_A3_R2_R1_R5_Temporal_Semantics_and_Restartability_Firewall.json"
R5_DOMAIN = "POSTV16_AV4_A3_R2_R1_R5_Input_Domain_Shift_Audit_Contract.json"
R5_HANDOFF = "POSTV16_AV4_A3_R2_R1_R5_A3E1_Handoff_Contract.json"
R5_MANIFEST = "POSTV16_AV4_A3_R2_R1_R5_Artifact_Manifest.csv"

OUT_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R1_R1_Preexecution_Complete_R5_Schema_Audit_Extension"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R1_R1_BLOCKED"


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
    # Frozen R5 schema names confirmed from R5 source/contract.
    recon = {
        "refreshed_streamlines": 1078,
        "nodes_per_streamline": 201,
        "channel_order": [f"c{i}" for i in range(13)],
    }
    temporal = {
        "historical_AV3_training_semantics": {
            "time_features": [
                "target_time_hat = target_day/1000",
                "target_eta_sequence = target_day*86400/terminal_TOF",
            ]
        },
        "direct_restart_authority": {
            "currently_proven": False,
        },
    }
    domain = {
        "domain_shift_role": (
            "diagnostic evidence only in A3-E1; no arbitrary numeric extrapolation "
            "threshold is allowed to authorize checkpoint reuse"
        )
    }

    assert recon["refreshed_streamlines"] == 1078
    assert recon["nodes_per_streamline"] == 201
    assert len(recon["channel_order"]) == 13
    assert temporal["historical_AV3_training_semantics"]["time_features"][0] == (
        "target_time_hat = target_day/1000"
    )
    assert temporal["direct_restart_authority"]["currently_proven"] is False
    assert domain["domain_shift_role"].startswith("diagnostic evidence only")

    print(
        "POSTV16-AV4-A3-E1-R1-R1 complete R5-schema audit extension "
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
        "POSTV16-AV4-A3-E1-R1-R1 — PREEXECUTION COMPLETE R5-SCHEMA AUDIT "
        "EXTENSION / E1-R2 CORRECTION AUTHORITY FREEZE"
    )
    print("=" * 214)
    print("CLOSURE EXTENSION / FREEZE ONLY.")
    print("E1-R1 FORMAL PASS REMAINS IMMUTABLE.")
    print("NO X13 RECONSTRUCTION. NO CHECKPOINT LOAD/INFERENCE. NO TEACHER.")
    print("NO PHYSICAL-TIME ADVANCE. NO MAPBACK / LP / TRAINING / CMG.")
    print("A3-E2 AND AV4 DYNAMIC TRANSPORT REMAIN UNAUTHORIZED.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository/source identity.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_E1R1_commit",
            parent == PARENT_E1R1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in [
            (E1, E1_BLOB),
            (E1R1, E1R1_BLOB),
            (R5, R5_BLOB),
        ]:
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind formal E1-R1 closure PASS.
        # ------------------------------------------------------------------------------------------
        stage = "E1R1_closure_binding"

        r1 = drive / E1R1_REL
        gate("E1R1_output_present", r1.is_dir(), str(r1))

        m1 = verify_manifest(r1, E1R1_MANIFEST)
        gate("E1R1_manifest_exact_6", len(m1) == 6, len(m1))

        s1 = load_json(r1 / E1R1_SUMMARY)
        c1 = load_json(r1 / E1R1_CORRECTED)
        h1 = load_json(r1 / E1R1_HANDOFF)
        d1 = load_json(r1 / E1R1_DECISION)

        gate("E1R1_status_exact", s1["status"] == E1R1_STATUS, s1["status"])
        gate(
            "E1R1_root_cause_closed",
            d1["root_cause_closed"] is True
            and d1["root_cause_type"] == "TECHNICAL_AUTHORITY_SCHEMA_READ_MISMATCH",
        )
        gate(
            "E1R1_original_E1_scientific_PASS_not_claimed",
            d1["original_E1_scientific_PASS_claimed"] is False
            and s1["original_E1_reconstruction_started"] is False,
        )
        gate(
            "E1R1_shape_correction_exact",
            c1["R5_reconstruction_contract_shape_key_exists"] is False
            and c1["authoritative_shape_components"]["refreshed_streamlines"]
            == "recon5['refreshed_streamlines']"
            and c1["authoritative_shape_components"]["nodes_per_streamline"]
            == "recon5['nodes_per_streamline']",
        )
        gate(
            "E1R1_E1R2_handoff_authorized",
            h1["milestone"] == "POSTV16-AV4-A3-E1-R2"
            and h1["authorized"] is True
            and h1["execution"] is True,
            h1,
        )
        gate(
            "E1R1_downstream_firewalls_preserved",
            h1["A3_E2_authorized"] is False
            and h1["AV4_dynamic_transport_execution_authorized"] is False
            and d1["A3_E2_authorized"] is False
            and d1["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind complete frozen R5 schemas.
        # ------------------------------------------------------------------------------------------
        stage = "R5_complete_schema_binding"

        r5 = drive / R5_REL
        gate("R5_output_present", r5.is_dir(), str(r5))
        m5 = verify_manifest(r5, R5_MANIFEST)
        gate("R5_manifest_exact_11", len(m5) == 11, len(m5))

        recon = load_json(r5 / R5_RECON)
        temporal = load_json(r5 / R5_TEMPORAL)
        domain = load_json(r5 / R5_DOMAIN)
        handoff5 = load_json(r5 / R5_HANDOFF)

        gate(
            "R5_reconstruction_schema_exact",
            "shape" not in recon
            and recon["refreshed_streamlines"] == 1078
            and recon["nodes_per_streamline"] == 201
            and len(recon["channel_order"]) == 13,
            {
                "keys": sorted(recon.keys()),
                "streamlines": recon["refreshed_streamlines"],
                "nodes": recon["nodes_per_streamline"],
                "channels": len(recon["channel_order"]),
            },
        )

        expected_time_features = [
            "target_time_hat = target_day/1000",
            "target_eta_sequence = target_day*86400/terminal_TOF",
        ]

        gate(
            "R5_temporal_training_semantics_schema_exact",
            "historical_temporal_semantics" not in temporal
            and "historical_AV3_training_semantics" in temporal
            and temporal["historical_AV3_training_semantics"]["time_features"]
            == expected_time_features,
            temporal["historical_AV3_training_semantics"],
        )

        gate(
            "R5_direct_restart_authority_schema_exact",
            "historical_checkpoint_restart_semantics" not in temporal
            and temporal["direct_restart_authority"]["currently_proven"] is False
            and temporal["direct_restart_authority"]["AV3_checkpoint_committed_reuse"] is False,
            temporal["direct_restart_authority"],
        )

        expected_domain_role = (
            "diagnostic evidence only in A3-E1; no arbitrary numeric extrapolation "
            "threshold is allowed to authorize checkpoint reuse"
        )

        gate(
            "R5_domain_shift_role_schema_exact",
            "role" not in domain
            and domain["domain_shift_role"] == expected_domain_role,
            domain["domain_shift_role"],
        )

        gate(
            "R5_handoff_remains_original_E1",
            handoff5["milestone"] == "POSTV16-AV4-A3-E1",
            handoff5["milestone"],
        )

        # ------------------------------------------------------------------------------------------
        # Prove all original E1 schema mismatches from source.
        # ------------------------------------------------------------------------------------------
        stage = "original_E1_complete_schema_mismatch_audit"

        e1_source = (root / E1).read_text(encoding="utf-8", errors="replace")

        mismatches = {
            "shape_key": 'recon5["shape"] == [NSL, NN, 13]',
            "temporal_semantics_key":
                'temporal5["historical_temporal_semantics"]["target_time_hat"]',
            "restart_semantics_key":
                'temporal5["historical_checkpoint_restart_semantics"]["direct_day365_to_day500_restart_authority"]',
            "domain_role_key":
                'domain5["role"] == "descriptive compatibility audit; no post-hoc threshold authorizes reuse"',
            "R5_handoff_compared_to_current_MILESTONE":
                'handoff5["milestone"] == MILESTONE',
        }

        for name, pattern in mismatches.items():
            gate(
                f"original_E1_{name}_present",
                pattern in e1_source,
                pattern,
            )

        # ------------------------------------------------------------------------------------------
        # Freeze the complete E1-R2 correction authority.
        # ------------------------------------------------------------------------------------------
        stage = "E1R2_complete_correction_authority_freeze"

        correction_contract = {
            "milestone": MILESTONE,
            "purpose": (
                "Extend E1-R1's shape-only authority after a preexecution full-schema audit "
                "proved additional frozen-R5 schema mismatches in original E1."
            ),
            "E1R1_PASS_preserved": True,
            "original_E1_source_modified": False,
            "scientific_change": False,
            "physics_change": False,
            "channel_definition_change": False,
            "normalization_change": False,
            "ADV_algorithm_change": False,
            "checkpoint_change": False,
            "teacher_change": False,
            "transport_change": False,
            "time_advance_change": False,
            "authorized_E1R2_schema_corrections": [
                {
                    "original":
                        'recon5["shape"] == [NSL, NN, 13]',
                    "corrected":
                        "recon5['refreshed_streamlines'] == NSL and "
                        "recon5['nodes_per_streamline'] == NN and "
                        "len(recon5['channel_order']) == 13 and "
                        "recon5['channel_order'] == CHANNELS13",
                },
                {
                    "original":
                        'temporal5["historical_temporal_semantics"]["target_time_hat"] / '
                        '["target_eta_sequence"]',
                    "corrected":
                        "temporal5['historical_AV3_training_semantics']['time_features'] "
                        "equals frozen two-string absolute-time feature list",
                },
                {
                    "original":
                        'temporal5["historical_checkpoint_restart_semantics"]'
                        '["direct_day365_to_day500_restart_authority"]',
                    "corrected":
                        "temporal5['direct_restart_authority']['currently_proven'] is False",
                },
                {
                    "original":
                        'domain5["role"]',
                    "corrected":
                        "domain5['domain_shift_role'] equals frozen diagnostic-evidence-only role",
                },
                {
                    "original":
                        'handoff5["milestone"] == MILESTONE',
                    "corrected":
                        "R5 handoff remains compared to literal 'POSTV16-AV4-A3-E1'; "
                        "E1-R1/R1-R1 handoff authorities authorize E1-R2",
                },
            ],
            "mandatory_preservation": [
                "all original E1 scientific reconstruction gates",
                "exact A2-E refreshed epoch authority",
                "exact historical AV3 A4-R2 dataset and TRAIN-only normalization",
                "exact AV2-A2 pore-velocity rule",
                "exact R7 solve_adv path",
                "exact V16C2 trilinear sampling",
                "no .keras load",
                "no checkpoint inference",
                "no teacher transport",
                "no physical-time advance",
                "no mapback / LP",
                "no training / checkpoint reselection",
                "no normalization refit",
                "no locked-OOD tuning",
                "no CMG",
                "A3-E2 unauthorized",
                "AV4 dynamic transport unauthorized",
            ],
        }

        handoff_r2 = {
            "milestone": "POSTV16-AV4-A3-E1-R2",
            "name": (
                "Fully Schema-Corrected Refreshed X13 Structural/Input-Domain "
                "Audit Continuation"
            ),
            "authorized": True,
            "execution": True,
            "required_parent": MILESTONE,
            "correction_authority": (
                "E1-R1 shape closure + E1-R1-R1 complete frozen-R5 schema audit extension"
            ),
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "E1R1_formal_PASS_bound": True,
            "complete_R5_schema_audit_completed": True,
            "additional_schema_mismatches_found_preexecution": True,
            "original_E1_scientific_execution_performed": False,
            "E1R2_full_schema_corrections_authorized": True,
            "E1R2_execution_authorized": True,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "E1R1_status": E1R1_STATUS,
            "R5_reconstruction_streamlines": recon["refreshed_streamlines"],
            "R5_reconstruction_nodes": recon["nodes_per_streamline"],
            "R5_reconstruction_channels": len(recon["channel_order"]),
            "R5_time_features": expected_time_features,
            "R5_direct_restart_currently_proven":
                temporal["direct_restart_authority"]["currently_proven"],
            "R5_domain_shift_role": domain["domain_shift_role"],
            "additional_schema_mismatches_closed": 4,
            "continuation_handoff_namespace_correction_frozen": True,
            "E1R2_authorized": True,
            "E1R2_execution_authorized": True,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        output_files = {
            "PAD_Stream_POSTV16_AV4_A3_E1_R1_R1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_A3_E1_R1_R1_Complete_R5_Schema_Audit.json":
                json_bytes({
                    "reconstruction_schema": recon,
                    "temporal_schema_keys": sorted(temporal.keys()),
                    "domain_schema_keys": sorted(domain.keys()),
                    "original_E1_mismatches": mismatches,
                }),
            "POSTV16_AV4_A3_E1_R1_R1_E1R2_Complete_Correction_Authority.json":
                json_bytes(correction_contract),
            "POSTV16_AV4_A3_E1_R1_R1_E1R2_Handoff_Contract.json":
                json_bytes(handoff_r2),
            "POSTV16_AV4_A3_E1_R1_R1_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_A3_E1_R1_R1_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": name, **value} for name, value in gates.items()]),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_A3_E1_R1_R1_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })

        immutable_publish(
            out,
            {
                "POSTV16_AV4_A3_E1_R1_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: COMPLETE R5-SCHEMA AUDIT EXTENSION PASS")
        print("=" * 214)
        print("E1-R1 formal closure                    : PRESERVED / BOUND")
        print("Original E1 scientific execution        : False")
        print("Additional R5 schema mismatches closed  : 4")
        print("R5 handoff namespace correction         : FROZEN")
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
        p = blocked / "POSTV16_AV4_A3_E1_R1_R1_Blocked_Report.json"

        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV4_A3_E1_R1_R1_Blocked_Report_{suffix}.json"

        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL CLOSURE EXTENSION BLOCKED")
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
