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
import tarfile
import zipfile
from typing import Any, Iterable

MILESTONE = "POSTV16-AV1-B1R2"
STATUS_FOUND_LOOSE = "AV1B1R2_EXACT_C18R_C19_LOCAL_AUTHORITIES_FOUND_AS_LOOSE_FILES"
STATUS_FOUND_ARCHIVE = "AV1B1R2_EXACT_C18R_C19_LOCAL_AUTHORITIES_FOUND_ARCHIVE_ONLY"
STATUS_PARTIAL = "AV1B1R2_PARTIAL_EXACT_LOCAL_AUTHORITY_RECOVERY"
STATUS_NOT_FOUND = "AV1B1R2_EXACT_LOCAL_AUTHORITY_RECOVERY_EXHAUSTED_NOT_FOUND"
STATUS_BLOCKED = "AV1B1R2_WINDOWS_LOCAL_AUDIT_BLOCKED"

B1R_COMMIT = "8f2faf0c50b5fcc6098826740ca505d4c0cee57d"

B1R_RUNNER = "PAD_Stream_POSTV16_AV1_B1R_Exact_Heavy_Artifact_Location_Audit.py"
B1R_RUNNER_BLOB = "8769941b55c4591176ac8d143228e127d1ef1fc7"

B1_RUNNER = (
    "PAD_Stream_POSTV16_AV1_B1_C26_to_E37A_Component_Mass_"
    "Representation_Equivalence_Audit.py"
)
B1_RUNNER_BLOB = "75574d5d76ef12c23751bac3716d1a36470c6920"

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

ZIP_SUFFIXES = (".zip", ".whl", ".keras")
TAR_SUFFIXES = (
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".tbz2",
    ".tar.xz",
    ".txz",
)
SEVENZIP_SUFFIXES = (".7z", ".rar")

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".ipynb_checkpoints",
    "$Recycle.Bin",
    "System Volume Information",
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "Recovery",
}

# Within the user's profile, AppData is intentionally skipped. The frozen PAD
# artifacts were generated as project/output files, not application cache files.
PROFILE_SKIP_DIR_NAMES = {
    "AppData",
    ".cache",
    ".conda",
    ".continuum",
    ".npm",
    ".vscode",
    ".idea",
    "node_modules",
}


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
    if s.endswith(ZIP_SUFFIXES):
        return "zip"
    if s.endswith(TAR_SUFFIXES):
        return "tar"
    if s.endswith(SEVENZIP_SUFFIXES):
        return "7z"
    return None


def should_hash_loose(path: Path) -> bool:
    return path.suffix.lower() == ".npz"


def should_hash_member(name: str) -> bool:
    return name.lower().endswith(".npz")


def fixed_drives() -> list[Path]:
    if os.name != "nt":
        return []
    drives: list[Path] = []
    try:
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        get_type = ctypes.windll.kernel32.GetDriveTypeW
        for i in range(26):
            if not (mask & (1 << i)):
                continue
            root = f"{chr(ord('A') + i)}:\\"
            # DRIVE_FIXED = 3
            if get_type(root) == 3:
                drives.append(Path(root))
    except Exception:
        pass
    return drives


def locate_7z() -> str | None:
    candidates = [
        shutil.which("7z"),
        shutil.which("7za"),
        shutil.which("7zz"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return str(c)
    return None


def prioritized_roots(
    project_root: Path,
    full_fixed_drives: bool,
) -> list[tuple[str, Path, bool]]:
    home = Path.home()
    roots: list[tuple[str, Path, bool]] = [
        ("project_root", project_root, False),
        ("pycharm_projects", project_root.parent, False),
        ("downloads", home / "Downloads", False),
        ("documents", home / "Documents", False),
        ("desktop", home / "Desktop", False),
        ("onedrive", home / "OneDrive", False),
        ("user_profile", home, True),
    ]

    if full_fixed_drives:
        for drive in fixed_drives():
            # C: user profile is already covered; scanning all of C: adds mostly
            # operating-system files. Other fixed drives are searched broadly.
            if drive.drive.upper() == home.drive.upper():
                continue
            roots.append((f"fixed_drive_{drive.drive.rstrip(':')}", drive, False))

    out: list[tuple[str, Path, bool]] = []
    seen: set[str] = set()
    for label, p, is_profile in roots:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if not rp.exists():
            continue
        key = os.path.normcase(str(rp))
        if key in seen:
            continue
        seen.add(key)
        out.append((label, rp, is_profile))
    return out


def iter_unique_files(
    roots: list[tuple[str, Path, bool]],
) -> Iterable[tuple[str, Path]]:
    seen: set[str] = set()
    for label, root, profile_mode in roots:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            skip = set(SKIP_DIR_NAMES)
            if profile_mode:
                skip |= PROFILE_SKIP_DIR_NAMES
            dirnames[:] = [d for d in dirnames if d not in skip]

            base = Path(dirpath)
            for filename in filenames:
                p = base / filename
                try:
                    key = os.path.normcase(str(p.resolve()))
                except Exception:
                    key = os.path.normcase(str(p))
                if key in seen:
                    continue
                seen.add(key)
                yield label, p


def add_match(
    rows: list[dict[str, Any]],
    target: str,
    storage: str,
    path: Path,
    sha256: str,
    size: int,
    archive_member: str = "",
) -> None:
    rows.append(
        {
            "target": target,
            "storage": storage,
            "path": str(path),
            "archive_member": archive_member,
            "sha256": sha256,
            "bytes": int(size),
            "exact": True,
        }
    )


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
                    add_match(
                        rows,
                        target,
                        "archive_member",
                        archive,
                        digest,
                        info.file_size,
                        info.filename,
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
                    add_match(
                        rows,
                        target,
                        "archive_member",
                        archive,
                        digest,
                        member.size,
                        member.name,
                    )
    except (tarfile.TarError, OSError, RuntimeError):
        counters["archives_unreadable"] += 1


def list_7z_members(exe: str, archive: Path) -> list[tuple[str, int | None]]:
    p = subprocess.run(
        [exe, "l", "-slt", str(archive)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    if p.returncode != 0:
        raise OSError(f"7z_list_failed:{archive}")

    members: list[tuple[str, int | None]] = []
    current_path: str | None = None
    current_size: int | None = None
    for line in p.stdout.splitlines():
        if line.startswith("Path = "):
            if current_path and should_hash_member(current_path):
                members.append((current_path, current_size))
            current_path = line[7:]
            current_size = None
        elif line.startswith("Size = "):
            try:
                current_size = int(line[7:])
            except ValueError:
                current_size = None
    if current_path and should_hash_member(current_path):
        members.append((current_path, current_size))
    return members


def scan_7z(
    exe: str | None,
    archive: Path,
    target_by_sha: dict[str, str],
    rows: list[dict[str, Any]],
    counters: dict[str, int],
) -> None:
    if exe is None:
        counters["opaque_7z_or_rar_archives"] += 1
        return

    try:
        members = list_7z_members(exe, archive)
        counters["archives_opened"] += 1
        for member, declared_size in members:
            counters["archive_npz_members_hashed"] += 1
            p = subprocess.Popen(
                [exe, "x", "-so", str(archive), member],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            assert p.stdout is not None
            digest = sha256_stream(p.stdout)
            _, stderr = p.communicate()
            if p.returncode != 0:
                counters["archives_unreadable"] += 1
                continue
            target = target_by_sha.get(digest)
            if target is not None:
                add_match(
                    rows,
                    target,
                    "archive_member",
                    archive,
                    digest,
                    declared_size or 0,
                    member,
                )
    except (OSError, RuntimeError):
        counters["archives_unreadable"] += 1


def self_test() -> None:
    import tempfile

    payload_a = b"C18R" + b"A" * 1000
    payload_b = b"C19" + b"B" * 2000
    sha_a = hashlib.sha256(payload_a).hexdigest()
    sha_b = hashlib.sha256(payload_b).hexdigest()
    target_by_sha = {sha_a: "C18R", sha_b: "C19"}

    with tempfile.TemporaryDirectory(prefix="AV1B1R2_SELFTEST_") as td:
        td = Path(td)
        loose = td / "renamed.npz"
        loose.write_bytes(payload_a)

        archive = td / "backup.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("nested/random_name.npz", payload_b)

        rows: list[dict[str, Any]] = []
        counters = {
            "archives_opened": 0,
            "archives_unreadable": 0,
            "archive_npz_members_hashed": 0,
        }

        digest = sha256_file(loose)
        add_match(
            rows,
            target_by_sha[digest],
            "loose_file",
            loose,
            digest,
            loose.stat().st_size,
        )
        scan_zip(archive, target_by_sha, rows, counters)

        found = {(r["target"], r["storage"]) for r in rows}
        if ("C18R", "loose_file") not in found:
            raise RuntimeError("self_test_loose_recovery_failed")
        if ("C19", "archive_member") not in found:
            raise RuntimeError("self_test_archive_recovery_failed")

    print("POSTV16-AV1-B1R2 self-test: PASS")


def main(
    project_root: Path,
    output_root: Path,
    full_fixed_drives: bool,
) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
        fatal: bool = True,
    ) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if fatal and not ok:
            raise GateError(name)

    print("=" * 168)
    print("POSTV16-AV1-B1R2 — WINDOWS LOCAL EXACT HEAVY-ARTIFACT RECOVERY AUDIT")
    print("=" * 168)
    print("TARGETS: exact frozen C18R and C19 NPZ authorities.")
    print("SEARCH AUTHORITY: SHA-256, not filename, timestamp, numerical similarity, or version order.")
    print("NO DATASET RECONSTRUCTION. NO TRAINING. NO INFERENCE. NO ARCHIVE EXTRACTION.")
    print("NO FROZEN ARTIFACT MUTATION.\n")

    try:
        if os.name != "nt":
            raise GateError("B1R2_requires_Windows_local_execution")

        project_root = project_root.resolve()
        output_root = output_root.resolve()

        head = git_text(project_root, "rev-parse", "HEAD")
        parent = git_text(project_root, "rev-parse", "HEAD^")
        status = git_text(project_root, "status", "--porcelain")

        gate(
            "repository_parent_is_B1R_commit",
            parent == B1R_COMMIT,
            parent,
        )
        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        b1r = project_root / B1R_RUNNER
        b1 = project_root / B1_RUNNER
        b1r_blob = git_blob_sha(b1r, project_root) if b1r.is_file() else "missing"
        b1_blob = git_blob_sha(b1, project_root) if b1.is_file() else "missing"

        gate(
            "B1R_runner_blob_exact",
            b1r_blob == B1R_RUNNER_BLOB,
            b1r_blob,
        )
        gate(
            "B1_runner_blob_exact",
            b1_blob == B1_RUNNER_BLOB,
            b1_blob,
        )

        stage = "windows_local_scan"

        roots = prioritized_roots(project_root, full_fixed_drives)
        gate(
            "local_scan_roots_present",
            len(roots) > 0,
            [(label, str(p)) for label, p, _ in roots],
        )

        sevenzip = locate_7z()
        print("\n7-ZIP SUPPORT")
        print("  executable:", sevenzip if sevenzip else "not found; .7z/.rar will be logged as opaque")

        print("\nSCAN ROOTS")
        for label, p, profile in roots:
            print(f"  {label:24s}: {p}" + ("  [profile exclusions active]" if profile else ""))

        target_by_sha = {
            info["sha256"]: label
            for label, info in TARGETS.items()
        }

        rows: list[dict[str, Any]] = []
        opaque_rows: list[dict[str, Any]] = []
        counters = {
            "files_seen": 0,
            "loose_npz_hashed": 0,
            "archives_seen": 0,
            "archives_opened": 0,
            "archives_unreadable": 0,
            "archive_npz_members_hashed": 0,
            "opaque_7z_or_rar_archives": 0,
        }

        for label, path in iter_unique_files(roots):
            counters["files_seen"] += 1
            if counters["files_seen"] % 10000 == 0:
                print(
                    f"  scanned files={counters['files_seen']}, "
                    f"loose_npz={counters['loose_npz_hashed']}, "
                    f"archives={counters['archives_seen']}, "
                    f"archive_npz_members={counters['archive_npz_members_hashed']}"
                )

            try:
                if should_hash_loose(path):
                    counters["loose_npz_hashed"] += 1
                    digest = sha256_file(path)
                    target = target_by_sha.get(digest)
                    if target is not None:
                        add_match(
                            rows,
                            target,
                            "loose_file",
                            path,
                            digest,
                            path.stat().st_size,
                        )

                kind = archive_kind(path)
                if kind is None:
                    continue

                counters["archives_seen"] += 1
                if kind == "zip":
                    scan_zip(path, target_by_sha, rows, counters)
                elif kind == "tar":
                    scan_tar(path, target_by_sha, rows, counters)
                elif kind == "7z":
                    before = counters["opaque_7z_or_rar_archives"]
                    scan_7z(sevenzip, path, target_by_sha, rows, counters)
                    if counters["opaque_7z_or_rar_archives"] > before:
                        opaque_rows.append(
                            {
                                "path": str(path),
                                "reason": "7z_executable_not_available",
                            }
                        )
            except (OSError, PermissionError):
                continue

        matches_by_target = {
            key: [r for r in rows if r["target"] == key]
            for key in TARGETS
        }
        c18r_found = bool(matches_by_target["C18R"])
        c19_found = bool(matches_by_target["C19"])
        c18r_loose = any(
            r["storage"] == "loose_file"
            for r in matches_by_target["C18R"]
        )
        c19_loose = any(
            r["storage"] == "loose_file"
            for r in matches_by_target["C19"]
        )

        print("\nEXACT MATCHES")
        if not rows:
            print("  none")
        else:
            for row in rows:
                member = (
                    f" :: {row['archive_member']}"
                    if row["archive_member"]
                    else ""
                )
                print(
                    f"  {row['target']:5s} {row['storage']:14s} "
                    f"{row['path']}{member}"
                )

        gate(
            "exact_C18R_SHA_found_locally",
            c18r_found,
            len(matches_by_target["C18R"]),
            fatal=False,
        )
        gate(
            "exact_C19_SHA_found_locally",
            c19_found,
            len(matches_by_target["C19"]),
            fatal=False,
        )
        gate(
            "exact_C18R_loose_file_found_locally",
            c18r_loose,
            sum(r["storage"] == "loose_file" for r in matches_by_target["C18R"]),
            fatal=False,
        )
        gate(
            "exact_C19_loose_file_found_locally",
            c19_loose,
            sum(r["storage"] == "loose_file" for r in matches_by_target["C19"]),
            fatal=False,
        )

        both_found = c18r_found and c19_found
        both_loose = c18r_loose and c19_loose
        partial = c18r_found ^ c19_found

        if both_loose:
            final_status = STATUS_FOUND_LOOSE
            next_action = (
                "Exact C18R and C19 authorities exist as loose local files. "
                "Next copy only SHA-certified bytes into a dedicated recovery location "
                "under PAD_Stream_Compute, verify SHA again there, then rerun unchanged B1."
            )
        elif both_found:
            final_status = STATUS_FOUND_ARCHIVE
            next_action = (
                "Exact C18R and C19 authorities exist locally, with at least one archive-only. "
                "Next materialize only the SHA-certified archive member bytes into a dedicated "
                "recovery location, verify SHA again, then rerun unchanged B1."
            )
        elif partial:
            final_status = STATUS_PARTIAL
            missing = [k for k in TARGETS if not matches_by_target[k]]
            next_action = (
                "Preserve recovered exact authority, but do not rerun B1. "
                f"Missing exact authority remains: {missing}. "
                "Do not reconstruct or substitute it."
            )
        else:
            final_status = STATUS_NOT_FOUND
            if opaque_rows:
                next_action = (
                    "No exact C18R/C19 SHA was found in all readable local files/archives. "
                    "One or more .7z/.rar archives were opaque because 7-Zip was unavailable; "
                    "install/use 7-Zip only to hash those archive members in place before declaring "
                    "local recovery exhausted. Do not reconstruct or substitute."
                )
            else:
                next_action = (
                    "Windows-local recovery is exhausted for the searched roots: neither exact "
                    "C18R nor C19 SHA was found. Do not reconstruct, substitute, or relabel a "
                    "regenerated dataset as the missing frozen authority."
                )

        summary = {
            "milestone": MILESTONE,
            "status": final_status,
            "repository_head": head,
            "repository_parent": parent,
            "targets": TARGETS,
            "scan_roots": [
                {"label": label, "path": str(p), "profile_exclusions": profile}
                for label, p, profile in roots
            ],
            "full_fixed_drives_enabled": bool(full_fixed_drives),
            "sevenzip_executable": sevenzip,
            "counters": counters,
            "matches": rows,
            "opaque_archives": opaque_rows,
            "exact_C18R_found": c18r_found,
            "exact_C19_found": c19_found,
            "exact_C18R_loose": c18r_loose,
            "exact_C19_loose": c19_loose,
            "dataset_reconstruction_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "archive_extraction_performed": False,
            "frozen_artifact_mutation": False,
            "next_action": next_action,
        }

        files = {
            "PAD_Stream_POSTV16_AV1_B1R2_Summary.json": json_bytes(summary),
            "POSTV16_AV1_B1R2_Exact_Matches.csv": csv_bytes(rows),
            "POSTV16_AV1_B1R2_Opaque_Archives.csv": csv_bytes(opaque_rows),
            "POSTV16_AV1_B1R2_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }
        immutable_publish(output_root, files)

        manifest = []
        for p in sorted(output_root.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV1_B1R2_Artifact_Manifest.csv":
                manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            output_root,
            {"POSTV16_AV1_B1R2_Artifact_Manifest.csv": csv_bytes(manifest)},
        )

        print("\n" + "=" * 168)
        print("POSTV16-AV1-B1R2: COMPLETE")
        print("=" * 168)
        print(f"{'Status':84}: {final_status}")
        print(f"{'Files seen':84}: {counters['files_seen']}")
        print(f"{'Loose NPZ files hashed':84}: {counters['loose_npz_hashed']}")
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
            f"{'Opaque .7z/.rar archives':84}: "
            f"{counters['opaque_7z_or_rar_archives']}"
        )
        print(
            f"{'Exact C18R matches / loose':84}: "
            f"{len(matches_by_target['C18R'])} / {c18r_loose}"
        )
        print(
            f"{'Exact C19 matches / loose':84}: "
            f"{len(matches_by_target['C19'])} / {c19_loose}"
        )
        print(f"{'Dataset reconstruction performed':84}: False")
        print(f"{'Training / inference performed':84}: False / False")
        print(f"{'Archive extraction performed':84}: False")
        print(f"{'Frozen artifact mutation':84}: False")
        print(f"{'Output':84}: {output_root}")
        print(f"{'NEXT':84}: {next_action}")
        print("=" * 168)
        return 0

    except Exception as exc:
        output_root.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "dataset_reconstruction_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "archive_extraction_performed": False,
            "frozen_artifact_mutation": False,
            "next_action": "Audit only the failed B1R2 preflight/execution gate.",
        }
        data = json_bytes(report)
        p = output_root / "POSTV16_AV1_B1R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = output_root / (
                "POSTV16_AV1_B1R2_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-B1R2: BLOCKED")
        print("=" * 168)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", p)
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, required=False)
    p.add_argument("--output-root", type=Path, required=False)
    p.add_argument("--full-fixed-drives", action="store_true")
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    project_root = args.project_root
    if project_root is None:
        project_root = Path.cwd()

    output_root = args.output_root
    if output_root is None:
        output_root = (
            Path.home()
            / "Downloads"
            / "POSTV16_AV1_B1R2_Windows_Local_Exact_Heavy_Artifact_Recovery_Audit"
        )

    raise SystemExit(
        main(
            project_root,
            output_root,
            bool(args.full_fixed_drives),
        )
    )
