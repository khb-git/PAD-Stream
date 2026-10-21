#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F4-R3-R1-R2"

STATUS_PASS = (
    "AV4F4R3R1R2_R3R1R1_BLOCK_REPORT_FILENAME_AUTHORITY_TYPO_CLOSED_"
    "R3_INTERIOR_MASS_BOUND_SCIENTIFIC_FAIL_PRESERVED_EXACT_INTERIOR_"
    "CV_BOUND_AND_FLUX_MECHANISM_LOCALIZED_NO_REPAIR_SELECTED"
)
STATUS_BLOCKED = "AV4F4R3R1R2_CORRECTED_INTERIOR_FAILURE_LOCALIZATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F4R3R1R1_COMMIT = "6f346060baa2f68b33f1abd8b312401d48760c6a"

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200
BACKGROUND = 0.20
MAX_SG = 0.60
SPD = 86400.0
PARENT_DAY = 365.0
TARGET_DAY = 500.0
DELTA_DAY = 135.0

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

F4R3R1R1_BLOCKED_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R1_R1_Corrected_Interior_Bound_Failure_Localization.py"
)
F4R3R1R1_BLOCKED_RUNNER_BLOB = "9af3dca5e7c450f9e9a512e3e39107d637807676"

F4R3R1_BLOCKED_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R1_Interior_Bound_Failure_Localization.py"
)
F4R3R1_BLOCKED_RUNNER_BLOB = "9e22881ffe733c2cccc1d82b023483e4ac17b1a1"

F4R3 = "PAD_Stream_POSTV16_AV4_F4_R3_Terminal_Producer_PassThrough_Repair_Execution.py"
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"

F4R2 = "PAD_Stream_POSTV16_AV4_F4_R2_Terminal_Producer_PassThrough_Repair_Freeze.py"
F4R2_BLOB = "d2ce7625d74a27ead60e6669fd11d2c5ffa2dae6"

F4R1 = "PAD_Stream_POSTV16_AV4_F4_R1_Teacher_Stiffness_Failure_Localization.py"
F4R1_BLOB = "b3fc5722740992aeadfcbe7911cb9bf8d08027e5"

F4 = "PAD_Stream_POSTV16_AV4_F4_Day365_to_Day500_Restart_Teacher_Certification.py"
F4_BLOB = "a893ab32a1b3a396c3b2242f603c47bc94187a54"

F2R3 = "PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

E1R2 = (
    "PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
    "Refreshed_X13_Structural_InputDomain_Audit.py"
)
E1R2_BLOB = "058f00fd12bd491dc7d7d7e471af3d4ff865af70"

A4R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SOURCE_BLOBS = {
    F4R3R1R1_BLOCKED_RUNNER: F4R3R1R1_BLOCKED_RUNNER_BLOB,
    F4R3R1_BLOCKED_RUNNER: F4R3R1_BLOCKED_RUNNER_BLOB,
    F4R3: F4R3_BLOB,
    F4R2: F4R2_BLOB,
    F4R1: F4R1_BLOB,
    F4: F4_BLOB,
    F2R3: F2R3_BLOB,
    E1R2: E1R2_BLOB,
    A4R2: A4R2_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F4R3R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R1_BLOCKED"
F4R3R1_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R1_Blocked_Report.json"
F4R3R1_BLOCK_STATUS = "AV4F4R3R1_INTERIOR_FAILURE_LOCALIZATION_BLOCKED"

F4R3R1R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R1_R1_BLOCKED"
F4R3R1R1_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R1_R1_Blocked_Report.json"
F4R3R1R1_BLOCK_STATUS = (
    "AV4F4R3R1R1_CORRECTED_INTERIOR_FAILURE_LOCALIZATION_BLOCKED"
)

F4R3_FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_SCIENTIFIC_FAIL"
F4R3_FAIL_REPORT = "POSTV16_AV4_F4_R3_Scientific_Fail_Report.json"
F4R3_FAIL_STATUS = (
    "AV4F4R3_TERMINAL_PRODUCER_PASSTHROUGH_REPAIR_OR_RECURRENT_LOOP_"
    "SCIENTIFIC_FAIL_NO_ADAPTATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)

F4R2_REL = BASE_AV4 / "POSTV16_AV4_F4_R2_Terminal_Producer_PassThrough_Repair_Freeze"
F4R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R2_Summary.json"
F4R2_MANIFEST = "POSTV16_AV4_F4_R2_Artifact_Manifest.csv"
F4R2_STATUS = (
    "AV4F4R2_F4R1_ADVECTION_DOMINATED_TERMINAL_UPPER_CAPACITY_CONFLICT_BOUND_"
    "MINIMAL_PRODUCER_FACE_PASSTHROUGH_REPAIR_PROSPECTIVELY_FROZEN_"
    "NO_REPAIR_EXECUTION"
)

F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"
F2R3_MANIFEST = "POSTV16_AV4_F2_R3_Artifact_Manifest.csv"

E1R2_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_Refreshed_X13_Structural_InputDomain_Audit"
E1R2_X13 = "POSTV16_AV4_A3_E1_R2_Refreshed_Day365_13Channel_Representation.npz"
E1R2_MANIFEST = "POSTV16_AV4_A3_E1_R2_Artifact_Manifest.csv"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R1_R2_Corrected_Interior_Bound_Failure_Localization"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R1_R2_BLOCKED"


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def fsum_array(a: np.ndarray) -> float:
    return float(
        math.fsum(
            float(x)
            for x in np.asarray(a, dtype=np.float64).ravel()
        )
    )


def interior_limiter_candidate(
    mass: np.ndarray,
    capacity: np.ndarray,
    rhs: np.ndarray,
    factor: float,
) -> dict[str, Any]:
    m = np.asarray(mass, dtype=np.float64)[:, :-1]
    cap = np.asarray(capacity, dtype=np.float64)[:, :-1]
    r = np.asarray(rhs, dtype=np.float64)[:, :-1]

    best_dt = float("inf")
    best = None

    pos = r > 1.0e-18
    if np.any(pos):
        coords = np.argwhere(pos)
        room = cap[pos] - m[pos]
        raw = room / r[pos]
        valid = np.isfinite(raw) & (raw > 0.0)
        if np.any(valid):
            vals = factor * raw[valid]
            q = int(np.argmin(vals))
            coords_valid = coords[valid]
            sl, cv = [int(x) for x in coords_valid[q]]
            best_dt = float(vals[q])
            best = {
                "bound": "UPPER_CAPACITY",
                "streamline": sl,
                "control_volume": cv,
                "dt_days": best_dt,
                "mass_kg": float(m[sl, cv]),
                "capacity_kg": float(cap[sl, cv]),
                "distance_to_bound_kg": float(
                    cap[sl, cv] - m[sl, cv]
                ),
                "rhs_kg_day": float(r[sl, cv]),
                "mass_fraction": float(m[sl, cv] / cap[sl, cv]),
            }

    neg = r < -1.0e-18
    if np.any(neg):
        coords = np.argwhere(neg)
        raw = m[neg] / (-r[neg])
        valid = np.isfinite(raw) & (raw > 0.0)
        if np.any(valid):
            vals = factor * raw[valid]
            q = int(np.argmin(vals))
            coords_valid = coords[valid]
            sl, cv = [int(x) for x in coords_valid[q]]
            dt = float(vals[q])
            if dt < best_dt:
                best_dt = dt
                best = {
                    "bound": "LOWER_ZERO",
                    "streamline": sl,
                    "control_volume": cv,
                    "dt_days": dt,
                    "mass_kg": float(m[sl, cv]),
                    "capacity_kg": float(cap[sl, cv]),
                    "distance_to_bound_kg": float(m[sl, cv]),
                    "rhs_kg_day": float(r[sl, cv]),
                    "mass_fraction": float(m[sl, cv] / cap[sl, cv]),
                }

    if best is None:
        return {
            "bound": "NONE",
            "streamline": -1,
            "control_volume": -1,
            "dt_days": float("inf"),
            "mass_kg": None,
            "capacity_kg": None,
            "distance_to_bound_kg": None,
            "rhs_kg_day": None,
            "mass_fraction": None,
        }
    return best


def self_test() -> None:
    mass = np.asarray([[9.0, 9.999, 0.5]], dtype=np.float64)
    cap = np.asarray([[10.0, 10.0, 1.0]], dtype=np.float64)
    rhs = np.asarray([[0.0, 2.0, 100.0]], dtype=np.float64)
    x = interior_limiter_candidate(mass, cap, rhs, 0.5)
    assert x["bound"] == "UPPER_CAPACITY"
    assert x["control_volume"] == 1
    assert abs(float(x["dt_days"]) - 0.00025) < 1.0e-14
    # Terminal CV is excluded regardless of its stronger RHS.
    assert x["control_volume"] != 2
    print(
        "POSTV16-AV4-F4-R3-R1-R2 corrected interior failure localization self-test: PASS"
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
        "POSTV16-AV4-F4-R3-R1-R2 — CORRECTED R3 INTERIOR MASS-BOUND "
        "SCIENTIFIC-FAIL LOCALIZATION AUDIT"
    )
    print("=" * 214)
    print("DIAGNOSTIC ONLY. THE FORMAL F4 AND F4-R3 SCIENTIFIC FAILS REMAIN IMMUTABLE.")
    print("THE F4-R2 TERMINAL PASS-THROUGH REMAINS FROZEN AND IS REPRODUCED EXACTLY.")
    print("NO INTERIOR REPAIR. NO FLUX LIMITER. NO TIMESTEP-FLOOR CHANGE. NO CLIPPING.")
    print("NO MAPBACK. NO DAY500 REFRESH. NO REPROJECTION. NO TRAINING. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository/source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_blocked_F4R3R1R1_commit",
            parent == PARENT_F4R3R1R1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind and preserve the immutable R3-R1 technical BLOCK caused only by the
        # truncated 38-character E1-R2 blob constant.
        # ------------------------------------------------------------------------------------------
        stage = "F4R3R1_block_closure_binding"

        prior_block_path = drive / F4R3R1_BLOCK_REL / F4R3R1_BLOCK_REPORT
        gate(
            "blocked_F4R3R1_report_present",
            prior_block_path.is_file(),
            str(prior_block_path),
        )
        prior_block = load_json(prior_block_path)

        gate(
            "blocked_F4R3R1_status_exact",
            prior_block["status"] == F4R3R1_BLOCK_STATUS,
            prior_block["status"],
        )
        gate(
            "blocked_F4R3R1_stage_exact",
            prior_block["failed_stage"] == "repository_authority",
            prior_block["failed_stage"],
        )
        gate(
            "blocked_F4R3R1_exception_exact_class",
            "PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
            "Refreshed_X13_Structural_InputDomain_Audit_git_blob_exact"
            in prior_block["exception"],
            prior_block["exception"],
        )
        gate(
            "blocked_F4R3R1_no_scientific_or_repair_execution",
            prior_block["repair_selected"] is False
            and prior_block["interior_repair_executed"] is False
            and prior_block["mapback_executed"] is False
            and prior_block["Day500_refresh_executed"] is False
            and prior_block["Day500_reprojection_executed"] is False
            and prior_block["F4R3R2_authorized"] is False
            and prior_block["F5_authorized"] is False
            and prior_block["automatic_rerun_authorized"] is False,
        )
        gate(
            "E1R2_corrected_blob_is_full_40_char_SHA",
            len(E1R2_BLOB) == 40
            and E1R2_BLOB
            == "058f00fd12bd491dc7d7d7e471af3d4ff865af70",
            {"length": len(E1R2_BLOB), "sha": E1R2_BLOB},
        )

        # Bind the second immutable R1-R1 technical BLOCK caused only by
        # the incorrect prior R3-R1 blocked-report filename.
        prior_r1r1_block_path = (
            drive / F4R3R1R1_BLOCK_REL / F4R3R1R1_BLOCK_REPORT
        )
        gate(
            "blocked_F4R3R1R1_report_present",
            prior_r1r1_block_path.is_file(),
            str(prior_r1r1_block_path),
        )
        prior_r1r1_block = load_json(prior_r1r1_block_path)

        gate(
            "blocked_F4R3R1R1_status_exact",
            prior_r1r1_block["status"] == F4R3R1R1_BLOCK_STATUS,
            prior_r1r1_block["status"],
        )
        gate(
            "blocked_F4R3R1R1_stage_exact",
            prior_r1r1_block["failed_stage"]
            == "F4R3R1_block_closure_binding",
            prior_r1r1_block["failed_stage"],
        )
        gate(
            "blocked_F4R3R1R1_exception_exact_class",
            "blocked_F4R3R1_report_present"
            in prior_r1r1_block["exception"],
            prior_r1r1_block["exception"],
        )
        gate(
            "blocked_F4R3R1R1_no_scientific_or_repair_execution",
            prior_r1r1_block["repair_selected"] is False
            and prior_r1r1_block["interior_repair_executed"] is False
            and prior_r1r1_block["mapback_executed"] is False
            and prior_r1r1_block["Day500_refresh_executed"] is False
            and prior_r1r1_block["Day500_reprojection_executed"] is False
            and prior_r1r1_block["F4R3R2_authorized"] is False
            and prior_r1r1_block["F5_authorized"] is False
            and prior_r1r1_block["automatic_rerun_authorized"] is False,
        )
        gate(
            "original_R3R1_block_report_filename_corrected",
            F4R3R1_BLOCK_REPORT
            == "POSTV16_AV4_F4_R3_R1_Blocked_Report.json",
            F4R3R1_BLOCK_REPORT,
        )

        # ------------------------------------------------------------------------------------------
        # Bind formal R3 scientific FAIL.
        # ------------------------------------------------------------------------------------------
        stage = "F4R3_fail_binding"

        fail_path = drive / F4R3_FAIL_REL / F4R3_FAIL_REPORT
        gate(
            "F4R3_scientific_fail_report_present",
            fail_path.is_file(),
            str(fail_path),
        )
        r3fail = load_json(fail_path)

        gate(
            "F4R3_fail_status_exact",
            r3fail["status"] == F4R3_FAIL_STATUS,
            r3fail["status"],
        )
        gate(
            "F4R3_fail_stage_exact",
            r3fail["failed_stage"] == "controlled_200CV_restart_teacher",
            r3fail["failed_stage"],
        )
        gate(
            "F4R3_fail_gate_exact",
            r3fail["failed_gate"]
            == "teacher_interior_substep_nonpositive_or_stiff",
            r3fail["failed_gate"],
        )

        detail = r3fail["detail"]
        gate(
            "F4R3_fail_detail_exact_class",
            float(detail["dt_days"]) > 0.0
            and float(detail["dt_days"]) <= 1.0e-10
            and float(detail["dt_days"])
            == float(detail["interior_mass_dt_days"])
            and float(detail["adv_dt_days"]) > 1.0e-3
            and float(detail["cap_dt_days"]) > 1.0e-3
            and float(detail["remaining_days"]) > 80.0,
            detail,
        )
        gate(
            "F4R3_fail_no_downstream_execution",
            r3fail["mapback_executed"] is False
            and r3fail["target_refresh_executed"] is False
            and r3fail["target_reprojection_executed"] is False
            and r3fail["training_performed"] is False
            and r3fail["checkpoint_created"] is False
            and r3fail["locked_OOD_opened"] is False
            and r3fail["automatic_rerun_authorized"] is False,
        )

        # Bind R2 formal output as the repair authority being reproduced.
        r2d = drive / F4R2_REL
        gate("F4R2_output_present", r2d.is_dir(), str(r2d))
        mr2 = verify_manifest(r2d, F4R2_MANIFEST)
        gate("F4R2_manifest_exact_8", len(mr2) == 8, len(mr2))
        sr2 = load_json(r2d / F4R2_SUMMARY)
        gate(
            "F4R2_status_exact",
            sr2["status"] == F4R2_STATUS,
            sr2["status"],
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact Day365 parent state and predictor conditioning.
        # ------------------------------------------------------------------------------------------
        stage = "parent_authority_binding"

        f2d = drive / F2R3_REL
        e1d = drive / E1R2_REL
        a2d = drive / A2E_REL

        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        gate("E1R2_output_present", e1d.is_dir(), str(e1d))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))

        verify_manifest(f2d, F2R3_MANIFEST)
        verify_manifest(e1d, E1R2_MANIFEST)
        verify_manifest(a2d, A2E_MANIFEST)

        with np.load(f2d / F2R3_STATE, allow_pickle=False) as z:
            parent_cv_mass = np.asarray(
                z["parent_CV_component_mass_kg"],
                dtype=np.float64,
            )
            parent_cv_sat = np.asarray(
                z["parent_CV_saturation"],
                dtype=np.float64,
            )
            parent_cv_capacity = np.asarray(
                z["parent_CV_capacity_kg"],
                dtype=np.float64,
            )
            parent_cv_pv = np.asarray(
                z["parent_CV_pore_volume_m3"],
                dtype=np.float64,
            )

        with np.load(e1d / E1R2_X13, allow_pickle=False) as z:
            X13 = np.asarray(
                z["X_refreshed_13"],
                dtype=np.float64,
            )

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            parent_tof = np.asarray(
                z["streamline_tof_s"],
                dtype=np.float64,
            )
            parent_weights_s = np.asarray(
                z["streamline_weight_m3_s"],
                dtype=np.float64,
            )
            parent_face_pressure = np.asarray(
                z["streamline_face_pressure_psi"],
                dtype=np.float64,
            )
            xi_1d = np.asarray(
                z["xi"],
                dtype=np.float64,
            ).reshape(-1)
            p_ref = float(
                np.asarray(
                    z["reference_gas_pressure_pa"]
                ).reshape(())
            )

        gate(
            "diagnostic_parent_shapes_exact",
            parent_cv_mass.shape == (NSL, NCV)
            and parent_cv_sat.shape == (NSL, NCV)
            and parent_cv_capacity.shape == (NSL, NCV)
            and parent_cv_pv.shape == (NSL, NCV)
            and X13.shape == (NSL, NN, 13)
            and parent_tof.shape == (NSL, NN)
            and parent_weights_s.shape == (NSL,)
            and parent_face_pressure.shape == (NSL, NN)
            and xi_1d.shape == (NN,),
        )

        # ------------------------------------------------------------------------------------------
        # Load the exact R3/F4 frozen helpers.
        # ------------------------------------------------------------------------------------------
        stage = "diagnostic_module_binding"

        r3 = load_module(
            root / F4R3,
            "postv16_av4_f4r3r1_r3",
        )
        a4 = load_module(
            root / A4R2,
            "postv16_av4_f4r3r1_a4",
        )
        r2 = load_module(
            root / R2,
            "postv16_av4_f4r3r1_r2",
        )

        gate(
            "R3_frozen_teacher_helpers_present",
            hasattr(r3, "build_mass_fraction_lookup")
            and hasattr(r3, "saturation_from_mass_fraction")
            and hasattr(r3, "build_cv_geometry_from_faces")
            and hasattr(r3, "teacher_face_fluxes"),
        )

        cvavg = 0.5 * (
            X13[:, :-1, :] + X13[:, 1:, :]
        )
        phi_cv = cvavg[:, :, 5]
        nw_cv = 3.0 + cvavg[:, :, 9]
        no_cv = 3.0 + cvavg[:, :, 10]
        krw_cv = 0.80 + 0.20 * cvavg[:, :, 11]
        kro_cv = 0.80 + 0.20 * cvavg[:, :, 12]

        cvgeom = r3.build_cv_geometry_from_faces(
            parent_tof,
            xi_1d,
        )
        y_lookup, s_lookup = r3.build_mass_fraction_lookup(r2)

        dfmax = float(
            a4.max_dfw_realization(
                nw_cv,
                no_cv,
                krw_cv,
                kro_cv,
            )
        )
        dt_eta_adv = float(
            r3.CFL
            * np.min(cvgeom["dtheta_cv"])
            / (dfmax + 1.0e-12)
        )
        adv_dt_days = float(
            dt_eta_adv
            * np.min(cvgeom["tau_end_s"])
            / SPD
        )

        # ------------------------------------------------------------------------------------------
        # Reproduce R3 exactly through its new interior stopping condition.
        # ------------------------------------------------------------------------------------------
        stage = "R3_failure_reproduction_and_localization"

        mass = parent_cv_mass.copy()
        cap = parent_cv_capacity
        q_m3_day = parent_weights_s * SPD

        remaining = DELTA_DAY
        elapsed = 0.0
        step = 0
        injected = 0.0
        produced = 0.0

        pass_steps = 0
        pass_events = 0
        pass_upper = 0
        pass_lower = 0
        pass_unique: set[int] = set()
        pass_correction_mass = 0.0

        history: list[dict[str, Any]] = []
        failure_snapshot = None

        while remaining > 1.0e-12 * DELTA_DAY:
            sat = r3.saturation_from_mass_fraction(
                mass,
                cap,
                y_lookup,
                s_lookup,
                1.0e-9,
            )

            flux = r3.teacher_face_fluxes(
                a4=a4,
                r2=r2,
                saturation=sat,
                q_m3_day=q_m3_day,
                face_pressure_psi=parent_face_pressure,
                p_ref_pa=p_ref,
                nw=nw_cv,
                no=no_cv,
                krw_max=krw_cv,
                kro_max=kro_cv,
                phi_cv=phi_cv,
                cvgeom=cvgeom,
            )

            raw_adv = np.asarray(
                flux["advective_mass_flux_kg_day"],
                dtype=np.float64,
            )
            raw_cap = np.asarray(
                flux["capillary_mass_flux_kg_day"],
                dtype=np.float64,
            )
            raw_rhs = np.asarray(
                flux["rhs_mass_kg_day"],
                dtype=np.float64,
            )
            conductance = np.asarray(
                flux["capillary_phase_conductance_m3_day_per_sat"],
                dtype=np.float64,
            )

            adv_rhs = (
                raw_adv[:, :-1]
                - raw_adv[:, 1:]
            )
            cap_rhs = (
                raw_cap[:, :-1]
                - raw_cap[:, 1:]
            )

            con_sum = np.zeros(
                (NSL, NCV),
                dtype=np.float64,
            )
            con_sum[:, :-1] += conductance
            con_sum[:, 1:] += conductance
            active = con_sum > 1.0e-30
            cap_dt_days = (
                float(
                    r3.CFL
                    * np.min(
                        parent_cv_pv[active]
                        / con_sum[active]
                    )
                )
                if np.any(active)
                else float("inf")
            )

            total_lim = interior_limiter_candidate(
                mass,
                cap,
                raw_rhs,
                float(r3.MASS_CAPACITY_CFL),
            )
            adv_lim = interior_limiter_candidate(
                mass,
                cap,
                adv_rhs,
                float(r3.MASS_CAPACITY_CFL),
            )
            cap_lim = interior_limiter_candidate(
                mass,
                cap,
                cap_rhs,
                float(r3.MASS_CAPACITY_CFL),
            )
            dt_mass_interior = float(
                total_lim["dt_days"]
            )

            h = min(
                remaining,
                adv_dt_days,
                cap_dt_days,
                dt_mass_interior,
            )

            history.append(
                {
                    "step": step,
                    "elapsed_days": elapsed,
                    "remaining_days": remaining,
                    "adv_CFL_dt_days": adv_dt_days,
                    "capillary_CFL_dt_days": cap_dt_days,
                    "interior_mass_bound_dt_days":
                        dt_mass_interior,
                    "limiter_bound": total_lim["bound"],
                    "limiter_streamline":
                        total_lim["streamline"],
                    "limiter_CV":
                        total_lim["control_volume"],
                    "limiter_mass_fraction":
                        total_lim["mass_fraction"],
                    "limiter_distance_to_bound_kg":
                        total_lim["distance_to_bound_kg"],
                    "limiter_rhs_kg_day":
                        total_lim["rhs_kg_day"],
                    "adv_only_interior_mass_dt_days":
                        adv_lim["dt_days"],
                    "cap_only_interior_mass_dt_days":
                        cap_lim["dt_days"],
                    "pass_through_events_so_far":
                        pass_events,
                    "pass_through_unique_streamlines_so_far":
                        len(pass_unique),
                    "max_interior_mass_fraction":
                        float(
                            np.max(
                                mass[:, :-1]
                                / cap[:, :-1]
                            )
                        ),
                    "min_interior_mass_fraction":
                        float(
                            np.min(
                                mass[:, :-1]
                                / cap[:, :-1]
                            )
                        ),
                }
            )

            if (
                not np.isfinite(h)
                or h
                <= float(r3.MIN_TEACHER_DT_DAYS)
            ):
                sl = int(total_lim["streamline"])
                cv = int(
                    total_lim["control_volume"]
                )
                if (
                    sl < 0
                    or cv < 0
                    or cv >= NCV - 1
                ):
                    raise GateError(
                        "R3_failure_reached_without_valid_interior_limiter"
                    )

                left = cv - 1 if cv > 0 else None
                right = cv + 1

                local = {
                    "step": step,
                    "elapsed_days": elapsed,
                    "remaining_days": remaining,
                    "limiter": total_lim,
                    "advective_only_limiter": adv_lim,
                    "capillary_only_limiter": cap_lim,
                    "advective_CFL_dt_days":
                        adv_dt_days,
                    "capillary_CFL_dt_days":
                        cap_dt_days,
                    "minimum_teacher_dt_days":
                        float(
                            r3.MIN_TEACHER_DT_DAYS
                        ),
                    "saturation":
                        float(sat[sl, cv]),
                    "mass_kg":
                        float(mass[sl, cv]),
                    "capacity_kg":
                        float(cap[sl, cv]),
                    "mass_fraction":
                        float(
                            mass[sl, cv]
                            / cap[sl, cv]
                        ),
                    "rhs_total_kg_day":
                        float(raw_rhs[sl, cv]),
                    "rhs_advective_kg_day":
                        float(adv_rhs[sl, cv]),
                    "rhs_capillary_kg_day":
                        float(cap_rhs[sl, cv]),
                    "advective_west_face_kg_day":
                        float(raw_adv[sl, cv]),
                    "advective_east_face_kg_day":
                        float(raw_adv[sl, cv + 1]),
                    "capillary_west_face_kg_day":
                        float(raw_cap[sl, cv]),
                    "capillary_east_face_kg_day":
                        float(raw_cap[sl, cv + 1]),
                    "streamline_rate_m3_day":
                        float(q_m3_day[sl]),
                    "CV_pore_volume_m3":
                        float(parent_cv_pv[sl, cv]),
                    "phi":
                        float(phi_cv[sl, cv]),
                    "nw":
                        float(nw_cv[sl, cv]),
                    "no":
                        float(no_cv[sl, cv]),
                    "krw_max":
                        float(krw_cv[sl, cv]),
                    "kro_max":
                        float(kro_cv[sl, cv]),
                    "theta_face_west":
                        float(
                            cvgeom["theta_face"][
                                sl, cv
                            ]
                        ),
                    "theta_face_east":
                        float(
                            cvgeom["theta_face"][
                                sl, cv + 1
                            ]
                        ),
                    "dtheta_CV":
                        float(
                            cvgeom["dtheta_cv"][
                                sl, cv
                            ]
                        ),
                    "metric_CV":
                        float(
                            cvgeom["metric_cv"][
                                sl, cv
                            ]
                        ),
                    "left_neighbor":
                        None
                        if left is None
                        else {
                            "CV": left,
                            "saturation":
                                float(
                                    sat[sl, left]
                                ),
                            "mass_fraction":
                                float(
                                    mass[sl, left]
                                    / cap[sl, left]
                                ),
                            "mass_kg":
                                float(
                                    mass[sl, left]
                                ),
                            "capacity_kg":
                                float(
                                    cap[sl, left]
                                ),
                        },
                    "right_neighbor": {
                        "CV": right,
                        "saturation":
                            float(
                                sat[sl, right]
                            ),
                        "mass_fraction":
                            float(
                                mass[sl, right]
                                / cap[sl, right]
                            ),
                        "mass_kg":
                            float(
                                mass[sl, right]
                            ),
                        "capacity_kg":
                            float(
                                cap[sl, right]
                            ),
                    },
                    "pass_through_history": {
                        "activation_steps":
                            pass_steps,
                        "activation_events":
                            pass_events,
                        "upper_events":
                            pass_upper,
                        "lower_events":
                            pass_lower,
                        "unique_streamline_count":
                            len(pass_unique),
                        "integrated_production_correction_kg":
                            pass_correction_mass,
                    },
                    "global_state": {
                        "total_CV_mass_kg":
                            fsum_array(mass),
                        "injected_mass_so_far_kg":
                            injected,
                        "produced_mass_so_far_kg":
                            produced,
                        "max_interior_mass_fraction":
                            float(
                                np.max(
                                    mass[:, :-1]
                                    / cap[:, :-1]
                                )
                            ),
                        "min_interior_mass_fraction":
                            float(
                                np.min(
                                    mass[:, :-1]
                                    / cap[:, :-1]
                                )
                            ),
                        "near_upper_interior_count_1e8":
                            int(
                                np.sum(
                                    (
                                        1.0
                                        - mass[:, :-1]
                                        / cap[:, :-1]
                                    )
                                    <= 1.0e-8
                                )
                            ),
                        "near_lower_interior_count_1e8":
                            int(
                                np.sum(
                                    (
                                        mass[:, :-1]
                                        / cap[:, :-1]
                                    )
                                    <= 1.0e-8
                                )
                            ),
                        "positive_rhs_near_upper_interior_count_1e8":
                            int(
                                np.sum(
                                    (
                                        (
                                            1.0
                                            - mass[:, :-1]
                                            / cap[:, :-1]
                                        )
                                        <= 1.0e-8
                                    )
                                    & (
                                        raw_rhs[:, :-1]
                                        > 1.0e-18
                                    )
                                )
                            ),
                        "negative_rhs_near_lower_interior_count_1e8":
                            int(
                                np.sum(
                                    (
                                        (
                                            mass[:, :-1]
                                            / cap[:, :-1]
                                        )
                                        <= 1.0e-8
                                    )
                                    & (
                                        raw_rhs[:, :-1]
                                        < -1.0e-18
                                    )
                                )
                            ),
                    },
                }

                local[
                    "rhs_decomposition_residual_kg_day"
                ] = (
                    local["rhs_total_kg_day"]
                    - local["rhs_advective_kg_day"]
                    - local["rhs_capillary_kg_day"]
                )

                failure_snapshot = {
                    "mass": mass.copy(),
                    "saturation": sat.copy(),
                    "rhs_total":
                        raw_rhs.copy(),
                    "rhs_advective":
                        adv_rhs.copy(),
                    "rhs_capillary":
                        cap_rhs.copy(),
                    "advective_faces":
                        raw_adv.copy(),
                    "capillary_faces":
                        raw_cap.copy(),
                    "local": local,
                }
                break

            # --------------------------------------------------------------
            # Exact frozen R2 terminal producer pass-through.
            # --------------------------------------------------------------
            corrected_adv = raw_adv.copy()
            terminal_cap_net = (
                raw_cap[:, -2]
                - raw_cap[:, -1]
            )
            raw_terminal_rhs = (
                raw_adv[:, -2]
                - raw_adv[:, -1]
                + terminal_cap_net
            )
            raw_terminal_trial = (
                mass[:, -1]
                + h * raw_terminal_rhs
            )

            upper = (
                raw_terminal_trial
                > cap[:, -1]
            )
            lower = (
                raw_terminal_trial
                < 0.0
            )
            active_terminal = upper | lower

            if np.any(upper):
                corrected_adv[
                    upper, -1
                ] = (
                    raw_adv[upper, -2]
                    + terminal_cap_net[upper]
                    - (
                        cap[upper, -1]
                        - mass[upper, -1]
                    )
                    / h
                )

            if np.any(lower):
                corrected_adv[
                    lower, -1
                ] = (
                    raw_adv[lower, -2]
                    + terminal_cap_net[lower]
                    + mass[lower, -1] / h
                )
                bad_lower = (
                    lower
                    & (
                        corrected_adv[:, -1]
                        < 0.0
                    )
                )
                if np.any(bad_lower):
                    raise GateError(
                        "diagnostic_R2_lower_pass_through_became_infeasible_before_formal_R3_failure"
                    )

            corrected_rhs = raw_rhs.copy()
            corrected_rhs[:, -1] = (
                corrected_adv[:, -2]
                - corrected_adv[:, -1]
                + terminal_cap_net
            )

            if np.any(active_terminal):
                pass_steps += 1
                idx = np.where(
                    active_terminal
                )[0]
                pass_events += int(idx.size)
                pass_upper += int(
                    np.sum(upper)
                )
                pass_lower += int(
                    np.sum(lower)
                )
                pass_unique.update(
                    int(x)
                    for x in idx.tolist()
                )
                pass_correction_mass += (
                    h
                    * fsum_array(
                        corrected_adv[:, -1]
                        - raw_adv[:, -1]
                    )
                )

            before = fsum_array(mass)
            trial = (
                mass
                + h * corrected_rhs
            )

            tol = max(
                1.0e-7,
                1.0e-12
                * max(before, 1.0),
            )
            if (
                float(np.min(trial))
                < -tol
            ):
                raise GateError(
                    "diagnostic_diverged_before_formal_R3_failure_negative_mass"
                )
            if (
                float(
                    np.max(
                        trial - cap
                    )
                )
                > tol
            ):
                raise GateError(
                    "diagnostic_diverged_before_formal_R3_failure_capacity"
                )

            mass = trial

            injected += (
                h
                * fsum_array(
                    corrected_adv[:, 0]
                )
            )
            produced += (
                h
                * fsum_array(
                    corrected_adv[:, -1]
                )
            )

            elapsed += h
            remaining = max(
                0.0,
                DELTA_DAY - elapsed,
            )
            step += 1

            if (
                step
                > int(
                    r3.MAX_TEACHER_SUBSTEPS
                )
            ):
                raise GateError(
                    "diagnostic_exceeded_R3_substep_limit"
                )

        gate(
            "F4R3_failure_reproduced",
            failure_snapshot is not None,
        )

        local = failure_snapshot["local"]

        gate(
            "F4R3_failure_remaining_days_reproduced",
            abs(
                float(local["remaining_days"])
                - float(
                    detail["remaining_days"]
                )
            )
            <= 1.0e-9,
            {
                "diagnostic":
                    local["remaining_days"],
                "formal_R3":
                    detail["remaining_days"],
            },
        )
        gate(
            "F4R3_failure_interior_mass_dt_reproduced",
            abs(
                float(
                    local["limiter"][
                        "dt_days"
                    ]
                )
                - float(
                    detail[
                        "interior_mass_dt_days"
                    ]
                )
            )
            <= 1.0e-15,
            {
                "diagnostic":
                    local["limiter"][
                        "dt_days"
                    ],
                "formal_R3":
                    detail[
                        "interior_mass_dt_days"
                    ],
            },
        )
        gate(
            "F4R3_failure_adv_dt_reproduced",
            abs(
                float(
                    local[
                        "advective_CFL_dt_days"
                    ]
                )
                - float(
                    detail["adv_dt_days"]
                )
            )
            <= 1.0e-12,
            {
                "diagnostic":
                    local[
                        "advective_CFL_dt_days"
                    ],
                "formal_R3":
                    detail["adv_dt_days"],
            },
        )
        gate(
            "F4R3_failure_cap_dt_reproduced",
            abs(
                float(
                    local[
                        "capillary_CFL_dt_days"
                    ]
                )
                - float(
                    detail["cap_dt_days"]
                )
            )
            <= 1.0e-12,
            {
                "diagnostic":
                    local[
                        "capillary_CFL_dt_days"
                    ],
                "formal_R3":
                    detail["cap_dt_days"],
            },
        )
        gate(
            "interior_limiter_location_valid",
            0
            <= int(
                local["limiter"][
                    "control_volume"
                ]
            )
            <= NCV - 2,
            local["limiter"],
        )
        gate(
            "interior_RHS_decomposition_exact",
            abs(
                float(
                    local[
                        "rhs_decomposition_residual_kg_day"
                    ]
                )
            )
            <= 1.0e-10,
            local[
                "rhs_decomposition_residual_kg_day"
            ],
        )

        # ------------------------------------------------------------------------------------------
        # Mechanism classification only.
        # ------------------------------------------------------------------------------------------
        stage = "mechanism_classification"

        total_rhs = float(
            local["rhs_total_kg_day"]
        )
        adv_rhs_local = float(
            local["rhs_advective_kg_day"]
        )
        cap_rhs_local = float(
            local["rhs_capillary_kg_day"]
        )
        bound = str(
            local["limiter"]["bound"]
        )

        actual_dt = float(
            local["limiter"]["dt_days"]
        )
        adv_dt = float(
            local[
                "advective_only_limiter"
            ]["dt_days"]
        )
        cap_only_dt = float(
            local[
                "capillary_only_limiter"
            ]["dt_days"]
        )

        if (
            cap_only_dt
            <= actual_dt * (1.0 + 1.0e-8)
            and (
                not np.isfinite(adv_dt)
                or adv_dt
                > 100.0 * actual_dt
            )
        ):
            driver = (
                "CAPILLARY_DOMINATED_"
                "INTERIOR_BOUND_CONFLICT"
            )
        elif (
            adv_dt
            <= actual_dt * (1.0 + 1.0e-8)
            and (
                not np.isfinite(
                    cap_only_dt
                )
                or cap_only_dt
                > 100.0 * actual_dt
            )
        ):
            driver = (
                "ADVECTION_DOMINATED_"
                "INTERIOR_BOUND_CONFLICT"
            )
        else:
            driver = (
                "COUPLED_ADVECTION_CAPILLARY_"
                "INTERIOR_BOUND_CONFLICT"
            )

        diagnosis = {
            "milestone": MILESTONE,
            "historical_F4_scientific_FAIL_preserved":
                True,
            "F4R3_scientific_FAIL_preserved":
                True,
            "blocked_F4R3R1_technical_authority_failure_preserved":
                True,
            "blocked_F4R3R1R1_report_filename_authority_failure_preserved":
                True,
            "E1R2_blob_authority_typo_corrected_only":
                True,
            "R3R1_block_report_filename_corrected_only":
                True,
            "F4R2_terminal_pass_through_preserved":
                True,
            "formal_R3_failure_gate":
                r3fail["failed_gate"],
            "formal_R3_failure_detail":
                detail,
            "reproduced_failure":
                True,
            "elapsed_days_at_failure":
                float(local["elapsed_days"]),
            "remaining_days_at_failure":
                float(local["remaining_days"]),
            "accepted_substeps_before_failure":
                int(local["step"]),
            "limiting_interior_CV": {
                "streamline":
                    int(
                        local["limiter"][
                            "streamline"
                        ]
                    ),
                "control_volume":
                    int(
                        local["limiter"][
                            "control_volume"
                        ]
                    ),
                "bound": bound,
                "mass_kg":
                    float(
                        local["mass_kg"]
                    ),
                "capacity_kg":
                    float(
                        local["capacity_kg"]
                    ),
                "distance_to_bound_kg":
                    float(
                        local["limiter"][
                            "distance_to_bound_kg"
                        ]
                    ),
                "mass_fraction":
                    float(
                        local["mass_fraction"]
                    ),
                "saturation":
                    float(
                        local["saturation"]
                    ),
            },
            "local_flux_budget": {
                "rhs_total_kg_day":
                    total_rhs,
                "rhs_advective_kg_day":
                    adv_rhs_local,
                "rhs_capillary_kg_day":
                    cap_rhs_local,
                "advective_west_face_kg_day":
                    local[
                        "advective_west_face_kg_day"
                    ],
                "advective_east_face_kg_day":
                    local[
                        "advective_east_face_kg_day"
                    ],
                "capillary_west_face_kg_day":
                    local[
                        "capillary_west_face_kg_day"
                    ],
                "capillary_east_face_kg_day":
                    local[
                        "capillary_east_face_kg_day"
                    ],
            },
            "limiter_comparison": {
                "actual_total_RHS_mass_dt_days":
                    actual_dt,
                "advective_only_mass_dt_days":
                    adv_dt,
                "capillary_only_mass_dt_days":
                    cap_only_dt,
                "advective_CFL_dt_days":
                    float(
                        local[
                            "advective_CFL_dt_days"
                        ]
                    ),
                "capillary_CFL_dt_days":
                    float(
                        local[
                            "capillary_CFL_dt_days"
                        ]
                    ),
            },
            "classification":
                driver,
            "terminal_pass_through_history":
                local[
                    "pass_through_history"
                ],
            "global_near_bound_population":
                local["global_state"],
            "scientific_interpretation": (
                "The frozen F4-R2 terminal producer pass-through "
                "successfully moves the first singularity away from "
                "terminal CV199, but the teacher later reaches a "
                "separate interior invariant-domain bound conflict. "
                "R3-R1 localizes that interior mechanism without "
                "generalizing the repair. The result does not by itself "
                "authorize an interior flux limiter, state clipping, "
                "capacity relaxation, or timestep-floor change."
            ),
            "repair_selected": False,
        }

        handoff = {
            "milestone":
                "POSTV16-AV4-F4-R3-R2",
            "name": (
                "Prospective Conservative Interior "
                "Invariant-Domain Repair Design Freeze"
            ),
            "authorized": True,
            "execution": False,
            "must_preserve": [
                "formal F4 scientific FAIL as immutable",
                "formal F4-R3 scientific FAIL as immutable",
                "F4-R2 terminal producer pass-through exactly",
                "F3 200-CV/17-channel restart signature",
                "F2-R3 split-state authority",
                "fixed injector mass source",
                "pairwise conservative internal flux accounting",
                "E37A CV capacities and saturation bounds",
                "exact global component-mass ledger",
                "no clipping, rescaling, capacity relaxation, or support expansion",
            ],
            "R2_must_decide_from_R1_evidence": [
                "whether the interior active bound is upper capacity or lower zero",
                "whether the interior driver is advection-, capillary-, or coupled-dominated",
                "whether a pairwise conservative interior face correction is mathematically required",
                "whether any correction can be restricted to faces adjacent to threatened CVs while preserving shared-face conservation",
                "whether the repaired operator remains identical to the frozen raw F4 operator whenever the invariant-domain constraint is inactive",
                "whether the correction preserves the source-authentic local-density EOS flux lineage rather than replacing it",
            ],
            "interior_repair_execution_authorized":
                False,
            "F5_dataset_generation_authorized":
                False,
            "training_authorized":
                False,
            "A3_E2_authorized":
                False,
            "AV4_dynamic_transport_execution_authorized":
                False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "historical_F4_scientific_FAIL_preserved":
                True,
            "F4R3_scientific_FAIL_preserved":
                True,
            "blocked_F4R3R1_technical_authority_failure_preserved":
                True,
            "blocked_F4R3R1R1_report_filename_authority_failure_preserved":
                True,
            "E1R2_blob_authority_typo_corrected_only":
                True,
            "R3R1_block_report_filename_corrected_only":
                True,
            "F4R2_terminal_pass_through_preserved":
                True,
            "R3_failure_reproduced":
                True,
            "interior_failure_localized":
                True,
            "mechanism_classified":
                True,
            "repair_selected":
                False,
            "interior_repair_executed":
                False,
            "terminal_pass_through_changed":
                False,
            "timestep_floor_changed":
                False,
            "mass_clipped_or_rescaled":
                False,
            "capacity_changed":
                False,
            "support_changed":
                False,
            "mapback_executed":
                False,
            "Day500_refresh_executed":
                False,
            "Day500_reprojection_executed":
                False,
            "training_performed":
                False,
            "F4R3R2_design_freeze_authorized":
                True,
            "F4R3R2_execution_authorized":
                False,
            "F5_dataset_generation_authorized":
                False,
            "A3_E2_authorized":
                False,
            "AV4_dynamic_transport_execution_authorized":
                False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "historical_F4_scientific_FAIL_preserved":
                True,
            "F4R3_scientific_FAIL_preserved":
                True,
            "blocked_F4R3R1_technical_authority_failure_preserved":
                True,
            "blocked_F4R3R1R1_report_filename_authority_failure_preserved":
                True,
            "E1R2_blob_authority_typo_corrected_only":
                True,
            "R3R1_block_report_filename_corrected_only":
                True,
            "failure_elapsed_days":
                float(local["elapsed_days"]),
            "failure_remaining_days":
                float(local["remaining_days"]),
            "accepted_substeps_before_failure":
                int(local["step"]),
            "limiter_bound":
                bound,
            "limiter_streamline":
                int(
                    local["limiter"][
                        "streamline"
                    ]
                ),
            "limiter_control_volume":
                int(
                    local["limiter"][
                        "control_volume"
                    ]
                ),
            "limiter_mass_fraction":
                float(
                    local["mass_fraction"]
                ),
            "limiter_saturation":
                float(
                    local["saturation"]
                ),
            "limiter_distance_to_bound_kg":
                float(
                    local["limiter"][
                        "distance_to_bound_kg"
                    ]
                ),
            "total_rhs_kg_day":
                total_rhs,
            "advective_rhs_kg_day":
                adv_rhs_local,
            "capillary_rhs_kg_day":
                cap_rhs_local,
            "actual_mass_dt_days":
                actual_dt,
            "advective_only_mass_dt_days":
                adv_dt,
            "capillary_only_mass_dt_days":
                cap_only_dt,
            "classification":
                driver,
            "terminal_pass_through_activation_events_before_failure":
                int(pass_events),
            "terminal_pass_through_unique_streamlines_before_failure":
                int(len(pass_unique)),
            "terminal_pass_through_integrated_production_correction_kg_before_failure":
                float(pass_correction_mass),
            "repair_selected":
                False,
            "F4R3R2_design_freeze_authorized":
                True,
            "F5_authorized":
                False,
        }

        state_npz = deterministic_npz_bytes(
            {
                "partial_CV_component_mass_kg":
                    failure_snapshot["mass"],
                "partial_CV_saturation":
                    failure_snapshot[
                        "saturation"
                    ],
                "partial_CV_mass_fraction":
                    (
                        failure_snapshot["mass"]
                        / parent_cv_capacity
                    ),
                "rhs_total_kg_day":
                    failure_snapshot[
                        "rhs_total"
                    ],
                "rhs_advective_kg_day":
                    failure_snapshot[
                        "rhs_advective"
                    ],
                "rhs_capillary_kg_day":
                    failure_snapshot[
                        "rhs_capillary"
                    ],
                "advective_face_mass_flux_kg_day":
                    failure_snapshot[
                        "advective_faces"
                    ],
                "capillary_face_mass_flux_kg_day":
                    failure_snapshot[
                        "capillary_faces"
                    ],
                "CV_capacity_kg":
                    parent_cv_capacity,
                "CV_pore_volume_m3":
                    parent_cv_pv,
                "elapsed_days":
                    np.asarray(
                        local[
                            "elapsed_days"
                        ]
                    ),
                "remaining_days":
                    np.asarray(
                        local[
                            "remaining_days"
                        ]
                    ),
                "accepted_substeps":
                    np.asarray(
                        local["step"],
                        dtype=np.int64,
                    ),
                "terminal_pass_through_events":
                    np.asarray(
                        pass_events,
                        dtype=np.int64,
                    ),
                "terminal_pass_through_integrated_production_correction_kg":
                    np.asarray(
                        pass_correction_mass,
                        dtype=np.float64,
                    ),
            }
        )

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R1_R2_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_R3_R1_R2_R3_Failure_Preservation.json":
                json_bytes(
                    {
                        "R3_fail_report":
                            str(fail_path),
                        "R3_fail_report_sha256":
                            sha256_file(
                                fail_path
                            ),
                        "status":
                            r3fail[
                                "status"
                            ],
                        "failed_stage":
                            r3fail[
                                "failed_stage"
                            ],
                        "failed_gate":
                            r3fail[
                                "failed_gate"
                            ],
                        "detail":
                            detail,
                    }
                ),
            "POSTV16_AV4_F4_R3_R1_R2_Interior_Limiter_and_Flux_Diagnosis.json":
                json_bytes(
                    diagnosis
                ),
            "POSTV16_AV4_F4_R3_R1_R2_Interior_Limiter_Trajectory.csv":
                csv_bytes(
                    history
                ),
            "POSTV16_AV4_F4_R3_R1_R2_Partial_Teacher_State_at_Failure.npz":
                state_npz,
            "POSTV16_AV4_F4_R3_R1_R2_R3R2_Design_Handoff_Contract.json":
                json_bytes(
                    handoff
                ),
            "POSTV16_AV4_F4_R3_R1_R2_Decision_Contract.json":
                json_bytes(
                    decision
                ),
            "POSTV16_AV4_F4_R3_R1_R2_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate": name,
                            **value,
                        }
                        for name, value
                        in gates.items()
                    ]
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
                != "POSTV16_AV4_F4_R3_R1_R2_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256":
                            sha256_file(p),
                        "bytes":
                            p.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R1_R2_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 214)
        print(
            f"{MILESTONE}: E1-R2 AUTHORITY TYPO CLOSED + "
            "INTERIOR BOUND-FAILURE LOCALIZATION PASS"
        )
        print("=" * 214)
        print("Historical F4 scientific FAIL            : PRESERVED")
        print("F4-R3 scientific FAIL                    : PRESERVED")
        print("Accepted substeps before failure         :", local["step"])
        print(
            "Elapsed / remaining days                 :",
            local["elapsed_days"],
            "/",
            local["remaining_days"],
        )
        print("Interior limiter bound                   :", bound)
        print(
            "Interior limiter streamline / CV         :",
            local["limiter"]["streamline"],
            "/",
            local["limiter"]["control_volume"],
        )
        print(
            "Limiter mass fraction                    :",
            local["mass_fraction"],
        )
        print(
            "Limiter saturation                       :",
            local["saturation"],
        )
        print(
            "Distance to active bound kg              :",
            local["limiter"]["distance_to_bound_kg"],
        )
        print(
            "Total / advective / capillary RHS kg/day :",
            total_rhs,
            "/",
            adv_rhs_local,
            "/",
            cap_rhs_local,
        )
        print(
            "Actual interior mass-limiter dt days     :",
            actual_dt,
        )
        print(
            "Adv-only / cap-only interior dt days     :",
            adv_dt,
            "/",
            cap_only_dt,
        )
        print(
            "Terminal pass-through events before fail :",
            pass_events,
        )
        print(
            "Terminal pass-through unique streamlines :",
            len(pass_unique),
        )
        print(
            "Mechanism classification                 :",
            driver,
        )
        print("Repair selected                          : False")
        print(
            "POSTV16-AV4-F4-R3-R2 design freeze       : AUTHORIZED"
        )
        print(
            "R3-R2 repair execution                   : NOT AUTHORIZED"
        )
        print(
            "F5 / training / A3-E2 / dynamic AV4      : NOT AUTHORIZED"
        )
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
            "historical_F4_scientific_FAIL_preserved":
                True,
            "F4R3_scientific_FAIL_preserved":
                True,
            "blocked_F4R3R1_technical_authority_failure_preserved":
                True,
            "F4R2_terminal_pass_through_preserved":
                True,
            "repair_selected":
                False,
            "interior_repair_executed":
                False,
            "mapback_executed":
                False,
            "Day500_refresh_executed":
                False,
            "Day500_reprojection_executed":
                False,
            "F4R3R2_authorized":
                False,
            "F5_authorized":
                False,
            "A3_E2_authorized":
                False,
            "AV4_dynamic_transport_execution_authorized":
                False,
            "automatic_rerun_authorized":
                False,
        }

        data = json_bytes(
            report
        )
        p = (
            blocked
            / "POSTV16_AV4_F4_R3_R1_R2_Blocked_Report.json"
        )
        if (
            p.exists()
            and p.read_bytes()
            != data
        ):
            p = blocked / (
                "POSTV16_AV4_F4_R3_R1_R2_Blocked_Report_"
                + hashlib.sha256(
                    data
                ).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(
            f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK"
        )
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print(
            "F4 and F4-R3 scientific FAILs remain immutable."
        )
        print(
            "NO INTERIOR REPAIR OR AUTOMATIC RERUN AUTHORIZED."
        )
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
