#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

MILESTONE = "POSTV16-AV1-B1R3-R1"
STATUS_BUNDLE = "AV1B1R3_WINDOWS_EXACT_AUTHORITY_TRANSFER_BUNDLE_CERTIFIED"
STATUS_MATERIALIZED = "AV1B1R3_DRIVE_EXACT_AUTHORITIES_MATERIALIZED_AND_CERTIFIED"

B1R2_COMMIT = "41f1e224b05e521f13f691e77eb90eb2b8b31828"
B1R2_RUNNER = "PAD_Stream_POSTV16_AV1_B1R2_Windows_Local_Exact_Heavy_Artifact_Recovery_Audit.py"
B1R2_BLOB = "1e0b5c2b6ece1317188f2889e8b514279c2140ad"
B1_RUNNER = "PAD_Stream_POSTV16_AV1_B1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "75574d5d76ef12c23751bac3716d1a36470c6920"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BUNDLE_NAME = "POSTV16_AV1_B1R3_Exact_Authority_Transfer_Bundle.zip"

TARGETS = {
    "C18R": {
        "filename": "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz",
        "sha256": "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3",
        "source_rel": Path("output/V16_C18R_ALIGNMENT_RESIDUAL_AUDIT/V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"),
    },
    "C19": {
        "filename": "V16C19_Leakage_Safe_Split_Assignment.npz",
        "sha256": "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a",
        "source_rel": Path("output/V16_C19_LEAKAGE_SAFE_TRAIN_VALIDATION_TEST_OOD_SPLIT_AUTHORITY_CONTRACT/V16C19_Leakage_Safe_Split_Assignment.npz"),
    },
}

RECOVERY_REL = (
    Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1R3_Recovered_Exact_Authorities"
)
AUDIT_REL = (
    Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1R3_Exact_Authority_Transfer_Audit"
)

MANIFEST_JSON = "POSTV16_AV1_B1R3_Transfer_Manifest.json"
MANIFEST_CSV = "POSTV16_AV1_B1R3_Transfer_Manifest.csv"


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return p.stdout.strip()


def git_blob(root: Path, path: Path) -> str:
    return git_text(root, "hash-object", str(path))


def jbytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def cbytes(rows: list[dict[str, Any]]) -> bytes:
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


def immutable_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise GateError(f"existing_output_differs:{path}")
        return
    path.write_bytes(data)


def validate_repo(root: Path, gate) -> tuple[str, str]:
    head = git_text(root, "rev-parse", "HEAD")
    parent = git_text(root, "rev-parse", "HEAD^")
    status = git_text(root, "status", "--porcelain")
    gate("repository_parent_is_B1R2_commit", parent == B1R2_COMMIT, parent)
    gate("repository_clean", status == "", repr(status))

    p = root / B1R2_RUNNER
    actual = git_blob(root, p) if p.is_file() else "missing"
    gate("B1R2_runner_blob_exact", actual == B1R2_BLOB, actual)

    p = root / B1_RUNNER
    actual = git_blob(root, p) if p.is_file() else "missing"
    gate("B1_runner_blob_exact", actual == B1_BLOB, actual)
    return head, parent


def make_bundle_bytes(payloads: dict[str, bytes], manifest_json: bytes, manifest_csv: bytes) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        members: dict[str, bytes] = {
            MANIFEST_JSON: manifest_json,
            MANIFEST_CSV: manifest_csv,
        }
        for key, info in TARGETS.items():
            members[f"authorities/{key}/{info['filename']}"] = payloads[key]
        for name in sorted(members):
            zi = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            zf.writestr(zi, members[name])
    return outer.getvalue()


def build_local_bundle(root: Path, bundle_out: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    def gate(name, passed, value=None):
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*160)
    print("POSTV16-AV1-B1R3 — WINDOWS EXACT AUTHORITY TRANSFER-BUNDLE CONSTRUCTION")
    print("="*160)
    print("NO RECONSTRUCTION. NO TRAINING. NO INFERENCE. SOURCE FILES REMAIN UNMODIFIED.\n")

    try:
        if os.name != "nt":
            raise GateError("Windows_execution_required")

        root = root.resolve()
        bundle_out = bundle_out.resolve()
        head, parent = validate_repo(root, gate)

        payloads = {}
        rows = []
        for key, info in TARGETS.items():
            src = root / info["source_rel"]
            gate(f"{key}_source_present", src.is_file(), str(src))
            actual = sha256_file(src)
            gate(f"{key}_source_SHA_exact", actual == info["sha256"], actual)
            data = src.read_bytes()
            gate(f"{key}_readback_SHA_exact", sha256_bytes(data) == info["sha256"], sha256_bytes(data))
            payloads[key] = data
            rows.append({
                "authority": key,
                "source_path": str(src),
                "bundle_member": f"authorities/{key}/{info['filename']}",
                "filename": info["filename"],
                "sha256": info["sha256"],
                "bytes": len(data),
            })

        manifest = {
            "milestone": MILESTONE,
            "status": STATUS_BUNDLE,
            "repository_head": head,
            "repository_parent": parent,
            "authorities": rows,
            "dataset_reconstruction_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "source_mutation_performed": False,
        }
        bundle_bytes = make_bundle_bytes(payloads, jbytes(manifest), cbytes(rows))
        immutable_write(bundle_out, bundle_bytes)

        with zipfile.ZipFile(bundle_out, "r") as zf:
            for key, info in TARGETS.items():
                member = f"authorities/{key}/{info['filename']}"
                gate(f"{key}_bundle_member_present", member in zf.namelist(), member)
                digest = sha256_bytes(zf.read(member))
                gate(f"{key}_bundle_member_SHA_exact", digest == info["sha256"], digest)

        sidecar = {
            "milestone": MILESTONE,
            "status": STATUS_BUNDLE,
            "bundle": str(bundle_out),
            "bundle_sha256": sha256_file(bundle_out),
            "C18R_sha256": TARGETS["C18R"]["sha256"],
            "C19_sha256": TARGETS["C19"]["sha256"],
            "all_gates_passed": all(v["passed"] for v in gates.values()),
            "next": "Upload bundle unchanged under MyDrive/PAD_Stream_Compute, then materialize with this same runner in Colab.",
        }
        immutable_write(bundle_out.with_suffix(".json"), jbytes(sidecar))

        print("\n" + "="*160)
        print("POSTV16-AV1-B1R3 WINDOWS BUNDLE: PASS")
        print("="*160)
        print("Status       :", STATUS_BUNDLE)
        print("Bundle       :", bundle_out)
        print("Bundle SHA256:", sha256_file(bundle_out))
        print("C18R SHA256  :", TARGETS["C18R"]["sha256"])
        print("C19 SHA256   :", TARGETS["C19"]["sha256"])
        print("Reconstruction / training / inference: False / False / False")
        print("="*160)
        return 0
    except Exception as exc:
        print("\nPOSTV16-AV1-B1R3 WINDOWS BUNDLE: BLOCKED")
        print("Exception:", repr(exc))
        return 2


def materialize_drive(root: Path, drive: Path, bundle: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    def gate(name, passed, value=None):
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*160)
    print("POSTV16-AV1-B1R3 — COLAB DRIVE EXACT AUTHORITY MATERIALIZATION")
    print("="*160)
    print("NO RECONSTRUCTION. NO TRAINING. NO INFERENCE. ONLY SHA-CERTIFIED BYTES MAY BE WRITTEN.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()
        bundle = bundle.resolve()
        head, parent = validate_repo(root, gate)

        gate("transfer_bundle_present", bundle.is_file(), str(bundle))
        gate("transfer_bundle_is_zip", zipfile.is_zipfile(bundle), sha256_file(bundle) if bundle.is_file() else "missing")

        recovery = drive / RECOVERY_REL
        audit = drive / AUDIT_REL
        recovery.mkdir(parents=True, exist_ok=True)
        audit.mkdir(parents=True, exist_ok=True)

        rows = []
        with zipfile.ZipFile(bundle, "r") as zf:
            names = set(zf.namelist())
            gate("bundle_manifest_present", MANIFEST_JSON in names, MANIFEST_JSON)
            manifest = json.loads(zf.read(MANIFEST_JSON).decode("utf-8"))
            gate("bundle_manifest_status_exact", manifest.get("status") == STATUS_BUNDLE, manifest.get("status"))
            gate("bundle_manifest_no_reconstruction", manifest.get("dataset_reconstruction_performed") is False)

            for key, info in TARGETS.items():
                member = f"authorities/{key}/{info['filename']}"
                gate(f"{key}_bundle_member_present", member in names, member)
                data = zf.read(member)
                digest = sha256_bytes(data)
                gate(f"{key}_bundle_member_SHA_exact", digest == info["sha256"], digest)

                dst = recovery / info["filename"]
                immutable_write(dst, data)
                post = sha256_file(dst)
                gate(f"{key}_Drive_SHA_exact", post == info["sha256"], post)
                rows.append({
                    "authority": key,
                    "materialized_path": str(dst),
                    "sha256": post,
                    "bytes": dst.stat().st_size,
                })

        for key, info in TARGETS.items():
            matches = []
            for p in drive.rglob(info["filename"]):
                try:
                    if p.is_file() and sha256_file(p) == info["sha256"]:
                        matches.append(str(p))
                except OSError:
                    pass
            gate(f"{key}_discoverable_by_unchanged_B1_drive_search", len(matches) >= 1, matches)

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_MATERIALIZED,
            "repository_head": head,
            "repository_parent": parent,
            "bundle": str(bundle),
            "bundle_sha256": sha256_file(bundle),
            "recovery_directory": str(recovery),
            "materialized_authorities": rows,
            "dataset_reconstruction_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "frozen_source_mutation": False,
            "B1_unchanged_rerun_authorized": True,
        }
        immutable_write(audit / "PAD_Stream_POSTV16_AV1_B1R3_Summary.json", jbytes(summary))
        immutable_write(audit / "POSTV16_AV1_B1R3_Materialized_Authorities.csv", cbytes(rows))
        immutable_write(audit / "POSTV16_AV1_B1R3_Final_Gate_Matrix.csv", cbytes([{"gate":k, **v} for k,v in gates.items()]))

        print("\n" + "="*160)
        print("POSTV16-AV1-B1R3 DRIVE MATERIALIZATION: PASS")
        print("="*160)
        print("Status                  :", STATUS_MATERIALIZED)
        print("Bundle SHA256           :", sha256_file(bundle))
        print("Recovery directory      :", recovery)
        print("C18R Drive SHA256       :", TARGETS["C18R"]["sha256"])
        print("C19 Drive SHA256        :", TARGETS["C19"]["sha256"])
        print("Unchanged B1 authorized : True")
        print("Reconstruction / training / inference: False / False / False")
        print("="*160)
        return 0
    except Exception as exc:
        print("\nPOSTV16-AV1-B1R3 DRIVE MATERIALIZATION: BLOCKED")
        print("Exception:", repr(exc))
        return 2


def self_test() -> None:
    a = b"A" * 1024
    b = b"B" * 2048
    original = {k: dict(v) for k,v in TARGETS.items()}
    try:
        TARGETS["C18R"]["filename"] = "a.npz"
        TARGETS["C19"]["filename"] = "b.npz"
        payloads = {"C18R": a, "C19": b}
        rows = [{"authority":"C18R","sha256":sha256_bytes(a)}, {"authority":"C19","sha256":sha256_bytes(b)}]
        data = make_bundle_bytes(
            payloads,
            jbytes({"status":STATUS_BUNDLE,"dataset_reconstruction_performed":False}),
            cbytes(rows),
        )
        with tempfile.TemporaryDirectory(prefix="AV1B1R3_SELFTEST_") as td:
            zp = Path(td) / "bundle.zip"
            zp.write_bytes(data)
            with zipfile.ZipFile(zp, "r") as zf:
                assert zf.read("authorities/C18R/a.npz") == a
                assert zf.read("authorities/C19/b.npz") == b
    finally:
        TARGETS.clear()
        TARGETS.update(original)
    print("POSTV16-AV1-B1R3 self-test: PASS")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--build-local-bundle", action="store_true")
    p.add_argument("--materialize-drive", action="store_true")
    p.add_argument("--project-root", type=Path)
    p.add_argument("--bundle-out", type=Path)
    p.add_argument("--drive-root", type=Path)
    p.add_argument("--bundle", type=Path)
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)

    if a.build_local_bundle:
        root = a.project_root or Path.cwd()
        bundle_out = a.bundle_out or (Path.home() / "Downloads" / BUNDLE_NAME)
        raise SystemExit(build_local_bundle(root, bundle_out))

    if a.materialize_drive:
        root = a.project_root or Path("/content/PAD-Stream")
        drive = a.drive_root or Path("/content/drive/MyDrive/PAD_Stream_Compute")
        if a.bundle is None:
            raise SystemExit("--bundle is required for --materialize-drive")
        raise SystemExit(materialize_drive(root, drive, a.bundle))

    raise SystemExit("Choose --build-local-bundle, --materialize-drive, or --self-test.")
