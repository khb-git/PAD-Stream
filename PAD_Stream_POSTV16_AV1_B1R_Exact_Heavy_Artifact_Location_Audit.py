#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile
from typing import Any, Iterable

MILESTONE = "POSTV16-AV1-B1R"
STATUS_LOOSE = "AV1B1R_EXACT_C18R_C19_AUTHORITIES_LOCATED_AS_LOOSE_FILES"
STATUS_ARCHIVE = "AV1B1R_EXACT_C18R_C19_AUTHORITIES_LOCATED_ARCHIVE_ONLY"
STATUS_BLOCKED = "AV1B1R_EXACT_HEAVY_ARTIFACT_LOCATION_AUDIT_BLOCKED"

B1_COMMIT = "551bd8a4b0984567173522753583f0343d70f755"

B1_RUNNER = (
    "PAD_Stream_POSTV16_AV1_B1_C26_to_E37A_Component_Mass_"
    "Representation_Equivalence_Audit.py"
)
B1_RUNNER_BLOB = "75574d5d76ef12c23751bac3716d1a36470c6920"

BR_RUNNER = (
    "PAD_Stream_POSTV16_AV1_BR_Exact_Half_Half_Geometry_"
    "Floating_Point_Failure_Audit.py"
)
BR_RUNNER_BLOB = "80a9fb93cb147f9b97c367af8ab3a2caaaf78da1"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

TARGETS = {
    "C18R": {
        "filename": "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz",
        "sha256": "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3",
    },
    "C19": {
        "filename": "V16C19_Leakage_Safe_Split_Assignment.npz",
        "sha256": "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a",
    },
}

B1_BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1_BLOCKED"
)
B1_BLOCKED_REPORT = "POSTV16_AV1_B1_Blocked_Report.json"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1R_Exact_Heavy_Artifact_Location_Audit"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1R_BLOCKED"
)

EXPECTED_B1_EXCEPTION_PREFIX = (
    "GateError('artifact_not_found_with_exact_sha:"
    "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz:"
    "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
)

LOOSE_SUFFIXES_TO_HASH = (".npz",)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_stream(stream) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1 << 20), b""):
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
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def archive_kind(path: Path) -> str | None:
    s = path.name.lower()
    if s.endswith((".zip", ".whl", ".keras")):
        return "zip"
    if s.endswith(
        (
            ".tar",
            ".tar.gz",
            ".tgz",
            ".tar.bz2",
            ".tbz2",
            ".tar.xz",
            ".txz",
        )
    ):
        return "tar"
    return None


def should_hash_loose(path: Path) -> bool:
    return path.name.lower().endswith(LOOSE_SUFFIXES_TO_HASH)


def should_hash_member(name: str) -> bool:
    return name.lower().endswith(".npz")


def normalize_roots(
    project_root: Path,
    drive_root: Path,
) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = [
        ("project_root", project_root),
        ("configured_drive_root", drive_root),
        ("mydrive_root", drive_root.parent),
        ("content_root", Path("/content")),
    ]
    out: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for label, p in candidates:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        key = str(rp)
        if key in seen or not rp.exists():
            continue
        seen.add(key)
        out.append((label, rp))
    return out


def iter_unique_files(
    roots: list[tuple[str, Path]],
) -> Iterable[tuple[str, Path]]:
    seen: set[str] = set()
    for label, root in roots:
        for dirpath, dirnames, filenames in os.walk(
            root,
            followlinks=False,
        ):
            dirnames[:] = [
                d
                for d in dirnames
                if d
                not in {
                    ".git",
                    "__pycache__",
                    ".ipynb_checkpoints",
                }
            ]
            base = Path(dirpath)
            for filename in filenames:
                p = base / filename
                try:
                    key = str(p.resolve())
                except Exception:
                    key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                yield label, p


def scan_zip(
    archive: Path,
    target_by_sha: dict[str, str],
    rows: list[dict[str, Any]],
    counters: dict[str, int],
) -> None:
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            counters["archives_opened"] += 1
            for info in zf.infolist():
                if info.is_dir() or not should_hash_member(info.filename):
                    continue
                counters["archive_npz_members_hashed"] += 1
                with zf.open(info, "r") as f:
                    digest = sha256_stream(f)
                target = target_by_sha.get(digest)
                if target is not None:
                    rows.append(
                        {
                            "target": target,
                            "storage": "archive_member",
                            "path": str(archive),
                            "archive_member": info.filename,
                            "sha256": digest,
                            "bytes": int(info.file_size),
                            "exact": True,
                        }
                    )
    except (zipfile.BadZipFile, OSError, RuntimeError):
        counters["archives_unreadable"] += 1


def scan_tar(
    archive: Path,
    target_by_sha: dict[str, str],
    rows: list[dict[str, Any]],
    counters: dict[str, int],
) -> None:
    try:
        with tarfile.open(archive, "r:*") as tf:
            counters["archives_opened"] += 1
            for member in tf:
                if not member.isfile() or not should_hash_member(member.name):
                    continue
                f = tf.extractfile(member)
                if f is None:
                    continue
                counters["archive_npz_members_hashed"] += 1
                with f:
                    digest = sha256_stream(f)
                target = target_by_sha.get(digest)
                if target is not None:
                    rows.append(
                        {
                            "target": target,
                            "storage": "archive_member",
                            "path": str(archive),
                            "archive_member": member.name,
                            "sha256": digest,
                            "bytes": int(member.size),
                            "exact": True,
                        }
                    )
    except (tarfile.TarError, OSError, RuntimeError):
        counters["archives_unreadable"] += 1


def self_test() -> None:
    import tempfile

    payload_a = b"A" * 1024 + b"C18R"
    payload_b = b"B" * 2048 + b"C19"
    sha_a = hashlib.sha256(payload_a).hexdigest()
    sha_b = hashlib.sha256(payload_b).hexdigest()
    target_by_sha = {
        sha_a: "C18R",
        sha_b: "C19",
    }

    with tempfile.TemporaryDirectory(
        prefix="AV1B1R_SELFTEST_"
    ) as td:
        td = Path(td)

        loose = td / "renamed.npz"
        loose.write_bytes(payload_a)

        zp = td / "bundle.zip"
        with zipfile.ZipFile(
            zp,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as zf:
            zf.writestr(
                "nested/not_expected_name.npz",
                payload_b,
            )

        rows: list[dict[str, Any]] = []
        counters = {
            "archives_opened": 0,
            "archives_unreadable": 0,
            "archive_npz_members_hashed": 0,
        }

        digest = sha256_file(loose)
        if digest in target_by_sha:
            rows.append(
                {
                    "target": target_by_sha[digest],
                    "storage": "loose_file",
                    "path": str(loose),
                    "archive_member": "",
                    "sha256": digest,
                    "bytes": loose.stat().st_size,
                    "exact": True,
                }
            )

        scan_zip(
            zp,
            target_by_sha,
            rows,
            counters,
        )

        found = {
            (
                row["target"],
                row["storage"],
            )
            for row in rows
        }
        if (
            "C18R",
            "loose_file",
        ) not in found:
            raise RuntimeError(
                "self_test_loose_sha_search_failed"
            )
        if (
            "C19",
            "archive_member",
        ) not in found:
            raise RuntimeError(
                "self_test_archive_sha_search_failed"
            )

    print(
        "POSTV16-AV1-B1R self-test: PASS"
    )


def main(
    project_root: Path,
    drive_root: Path,
) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    out = drive_root / OUT_REL
    blocked = drive_root / BLOCKED_REL

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
        fatal: bool = True,
    ) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
        }
        suffix = (
            f" — {value}"
            if value is not None
            else ""
        )
        print(
            f"[{'PASS' if ok else 'FAIL'}] "
            f"{name}{suffix}"
        )
        if fatal and not ok:
            raise GateError(name)

    print("=" * 168)
    print(
        "POSTV16-AV1-B1R — EXACT HEAVY-ARTIFACT LOCATION AUDIT"
    )
    print("=" * 168)
    print(
        "SCOPE: locate exact frozen C18R and C19 bytes by SHA-256."
    )
    print(
        "NO DATASET RECONSTRUCTION. NO TRAINING. NO INFERENCE. "
        "NO EXTRACTION."
    )
    print(
        "NO FROZEN ARTIFACT MUTATION. "
        "ARCHIVE MEMBERS ARE HASHED IN PLACE ONLY.\n"
    )

    try:
        project_root = project_root.resolve()
        drive_root = drive_root.resolve()

        head = git_text(
            project_root,
            "rev-parse",
            "HEAD",
        )
        parent = git_text(
            project_root,
            "rev-parse",
            "HEAD^",
        )
        status = git_text(
            project_root,
            "status",
            "--porcelain",
        )

        gate(
            "repository_parent_is_blocked_B1_commit",
            parent == B1_COMMIT,
            parent,
        )
        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        b1 = project_root / B1_RUNNER
        br = project_root / BR_RUNNER

        b1_blob = (
            git_blob_sha(
                b1,
                project_root,
            )
            if b1.is_file()
            else "missing"
        )
        br_blob = (
            git_blob_sha(
                br,
                project_root,
            )
            if br.is_file()
            else "missing"
        )

        gate(
            "B1_runner_blob_exact",
            b1_blob == B1_RUNNER_BLOB,
            b1_blob,
        )
        gate(
            "BR_runner_blob_exact",
            br_blob == BR_RUNNER_BLOB,
            br_blob,
        )

        b1_blocked_report = (
            drive_root
            / B1_BLOCKED_REL
            / B1_BLOCKED_REPORT
        )
        gate(
            "blocked_B1_report_present",
            b1_blocked_report.is_file(),
            str(b1_blocked_report),
        )

        b1_blocked = json.loads(
            b1_blocked_report.read_text(
                encoding="utf-8"
            )
        )

        gate(
            "blocked_B1_status_exact",
            b1_blocked.get("status")
            == (
                "AV1B1_BLOCKED_COMPONENT_MASS_RUNTIME_"
                "REPRESENTATION_EQUIVALENCE_INCOMPLETE"
            ),
            b1_blocked.get("status"),
        )
        gate(
            "blocked_B1_failed_stage_artifact_binding",
            b1_blocked.get("failed_stage")
            == "artifact_binding",
            b1_blocked.get("failed_stage"),
        )

        exc = str(
            b1_blocked.get(
                "exception",
                "",
            )
        )
        gate(
            "blocked_B1_exception_exact_C18R_missing_authority",
            exc.startswith(
                EXPECTED_B1_EXCEPTION_PREFIX
            ),
            exc,
        )

        stage = "exact_location_scan"

        roots = normalize_roots(
            project_root,
            drive_root,
        )

        print("\nSCAN ROOTS")
        for label, p in roots:
            print(
                f"  {label:24s}: {p}"
            )

        target_by_sha = {
            info["sha256"]: label
            for label, info in TARGETS.items()
        }

        rows: list[dict[str, Any]] = []
        counters = {
            "files_seen": 0,
            "loose_npz_hashed": 0,
            "archives_seen": 0,
            "archives_opened": 0,
            "archives_unreadable": 0,
            "archive_npz_members_hashed": 0,
        }

        for label, path in iter_unique_files(
            roots
        ):
            counters["files_seen"] += 1

            if (
                counters["files_seen"]
                % 5000
                == 0
            ):
                print(
                    "  scanned "
                    f"files={counters['files_seen']}, "
                    f"loose_npz={counters['loose_npz_hashed']}, "
                    f"archives={counters['archives_seen']}, "
                    "archive_npz_members="
                    f"{counters['archive_npz_members_hashed']}"
                )

            try:
                if should_hash_loose(path):
                    counters[
                        "loose_npz_hashed"
                    ] += 1
                    digest = sha256_file(path)
                    target = (
                        target_by_sha.get(
                            digest
                        )
                    )
                    if target is not None:
                        rows.append(
                            {
                                "target": target,
                                "storage": "loose_file",
                                "path": str(
                                    path
                                ),
                                "archive_member": "",
                                "sha256": digest,
                                "bytes": (
                                    path.stat().st_size
                                ),
                                "exact": True,
                            }
                        )

                kind = archive_kind(path)
                if kind is not None:
                    counters[
                        "archives_seen"
                    ] += 1
                    if kind == "zip":
                        scan_zip(
                            path,
                            target_by_sha,
                            rows,
                            counters,
                        )
                    else:
                        scan_tar(
                            path,
                            target_by_sha,
                            rows,
                            counters,
                        )
            except (
                OSError,
                PermissionError,
            ):
                continue

        print(
            "\nEXACT MATCHES"
        )
        if not rows:
            print("  none")
        else:
            for row in rows:
                member = (
                    " :: "
                    + row[
                        "archive_member"
                    ]
                    if row[
                        "archive_member"
                    ]
                    else ""
                )
                print(
                    f"  {row['target']:5s} "
                    f"{row['storage']:14s} "
                    f"{row['path']}"
                    f"{member}"
                )

        matches_by_target = {
            key: [
                row
                for row in rows
                if row["target"] == key
            ]
            for key in TARGETS
        }

        c18r_found = (
            len(
                matches_by_target[
                    "C18R"
                ]
            )
            > 0
        )
        c19_found = (
            len(
                matches_by_target[
                    "C19"
                ]
            )
            > 0
        )

        c18r_loose = any(
            row["storage"]
            == "loose_file"
            for row in matches_by_target[
                "C18R"
            ]
        )
        c19_loose = any(
            row["storage"]
            == "loose_file"
            for row in matches_by_target[
                "C19"
            ]
        )

        gate(
            "exact_C18R_SHA_found_somewhere",
            c18r_found,
            len(
                matches_by_target[
                    "C18R"
                ]
            ),
            fatal=False,
        )
        gate(
            "exact_C19_SHA_found_somewhere",
            c19_found,
            len(
                matches_by_target[
                    "C19"
                ]
            ),
            fatal=False,
        )
        gate(
            "exact_C18R_loose_file_found",
            c18r_loose,
            sum(
                row["storage"]
                == "loose_file"
                for row in matches_by_target[
                    "C18R"
                ]
            ),
            fatal=False,
        )
        gate(
            "exact_C19_loose_file_found",
            c19_loose,
            sum(
                row["storage"]
                == "loose_file"
                for row in matches_by_target[
                    "C19"
                ]
            ),
            fatal=False,
        )

        both_found = (
            c18r_found
            and c19_found
        )
        both_loose = (
            c18r_loose
            and c19_loose
        )

        if both_loose:
            status_final = STATUS_LOOSE
            b1_rerun_authorized = True
            next_action = (
                "Rerun the unchanged POSTV16-AV1-B1 runner. "
                "Its exact-hash search can bind the loose exact "
                "C18R/C19 authorities."
            )
        elif both_found:
            status_final = STATUS_ARCHIVE
            b1_rerun_authorized = False
            next_action = (
                "Do not rerun B1 yet. Exact authorities exist only "
                "inside archive member(s). Next perform a separate "
                "exact-byte materialization step that copies only "
                "SHA-certified bytes without reconstruction."
            )
        else:
            status_final = STATUS_BLOCKED
            b1_rerun_authorized = False
            missing = [
                label
                for label in TARGETS
                if not matches_by_target[
                    label
                ]
            ]
            next_action = (
                "Do not reconstruct or substitute missing authority. "
                "Exact SHA search did not recover: "
                f"{missing}."
            )

        summary = {
            "milestone": MILESTONE,
            "status": status_final,
            "repository_head": head,
            "repository_parent": parent,
            "scope": (
                "exact SHA location audit only"
            ),
            "targets": TARGETS,
            "scan_roots": [
                {
                    "label": label,
                    "path": str(path),
                }
                for label, path in roots
            ],
            "counters": counters,
            "matches": rows,
            "exact_C18R_found": c18r_found,
            "exact_C19_found": c19_found,
            "exact_C18R_loose": c18r_loose,
            "exact_C19_loose": c19_loose,
            "B1_rerun_authorized": (
                b1_rerun_authorized
            ),
            "dataset_reconstruction_performed": False,
            "archive_extraction_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "frozen_artifact_mutation": False,
            "next_action": next_action,
        }

        files = {
            "PAD_Stream_POSTV16_AV1_B1R_Summary.json": (
                json_bytes(
                    summary
                )
            ),
            "POSTV16_AV1_B1R_Exact_Matches.csv": (
                csv_bytes(
                    rows
                )
            ),
            "POSTV16_AV1_B1R_Final_Gate_Matrix.csv": (
                csv_bytes(
                    [
                        {
                            "gate": k,
                            **v,
                        }
                        for k, v
                        in gates.items()
                    ]
                )
            ),
        }

        immutable_publish(
            out,
            files,
        )

        manifest_rows = []
        for p in sorted(
            out.iterdir()
        ):
            if (
                p.is_file()
                and p.name
                != (
                    "POSTV16_AV1_B1R_"
                    "Artifact_Manifest.csv"
                )
            ):
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": (
                            sha256_file(p)
                        ),
                        "bytes": (
                            p.stat().st_size
                        ),
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV1_B1R_Artifact_Manifest.csv": (
                    csv_bytes(
                        manifest_rows
                    )
                )
            },
        )

        print(
            "\n"
            + "=" * 168
        )
        print(
            "POSTV16-AV1-B1R: "
            + (
                "PASS"
                if both_found
                else "BLOCKED"
            )
        )
        print(
            "=" * 168
        )
        print(
            f"{'Status':84}: "
            f"{status_final}"
        )
        print(
            f"{'Files seen':84}: "
            f"{counters['files_seen']}"
        )
        print(
            f"{'Loose NPZ files hashed':84}: "
            f"{counters['loose_npz_hashed']}"
        )
        print(
            f"{'Archives seen / opened / unreadable':84}: "
            f"{counters['archives_seen']} / "
            f"{counters['archives_opened']} / "
            f"{counters['archives_unreadable']}"
        )
        print(
            f"{'Archive NPZ members hashed':84}: "
            f"{counters['archive_npz_members_hashed']}"
        )
        print(
            f"{'Exact C18R matches / loose':84}: "
            f"{len(matches_by_target['C18R'])} / "
            f"{c18r_loose}"
        )
        print(
            f"{'Exact C19 matches / loose':84}: "
            f"{len(matches_by_target['C19'])} / "
            f"{c19_loose}"
        )
        print(
            f"{'B1 rerun authorized':84}: "
            f"{b1_rerun_authorized}"
        )
        print(
            f"{'Dataset reconstruction performed':84}: False"
        )
        print(
            f"{'Archive extraction performed':84}: False"
        )
        print(
            f"{'Training / inference performed':84}: "
            f"False / False"
        )
        print(
            f"{'Frozen artifact mutation':84}: False"
        )
        print(
            f"{'NEXT':84}: "
            f"{next_action}"
        )
        print(
            "=" * 168
        )

        return (
            0
            if both_found
            else 2
        )

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
            "dataset_reconstruction_performed": False,
            "archive_extraction_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "frozen_artifact_mutation": False,
            "next_action": (
                "Audit only the failed B1R gate(s)."
            ),
        }
        data = json_bytes(
            report
        )
        p = (
            blocked
            / "POSTV16_AV1_B1R_Blocked_Report.json"
        )
        if (
            p.exists()
            and p.read_bytes()
            != data
        ):
            p = (
                blocked
                / (
                    "POSTV16_AV1_B1R_Blocked_Report_"
                    + hashlib.sha256(
                        data
                    ).hexdigest()[
                        :12
                    ]
                    + ".json"
                )
            )
        if not p.exists():
            p.write_bytes(data)

        print(
            "\n"
            + "=" * 168
        )
        print(
            "POSTV16-AV1-B1R: BLOCKED"
        )
        print(
            "=" * 168
        )
        print(
            "Failed stage:",
            stage,
        )
        print(
            "Exception   :",
            repr(exc),
        )
        print(
            "Report      :",
            p,
        )
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
