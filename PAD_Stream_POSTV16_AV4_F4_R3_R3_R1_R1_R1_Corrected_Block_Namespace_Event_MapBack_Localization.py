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
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F4-R3-R3-R1-R1-R1"

STATUS_PASS = (
    "AV4F4R3R3R1R1R1_BLOCK_NAMESPACE_CROSSING_CORRECTED_"
    "F2R3_WC_ARCHIVE_KEY_SCHEMA_CORRECTED_"
    "R3R3_EVENT_MAPBACK_NEGATIVE_CARTESIAN_CELL_FAILURE_LOCALIZED_"
    "BOUNDED_PARENT_OWNERSHIP_AND_RAW_EOS_DELTA_DISAGGREGATION_AUDITED_NO_REPAIR_SELECTED"
)
STATUS_BLOCKED = "AV4F4R3R3R1R1R1_MAPBACK_NEGATIVE_CELL_LOCALIZATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R3R1R1_COMMIT = "f41544d20fbd6d7bc00edd4a965c19cc525db482"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NN = 201
NCV = 200

BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
EVENT_DAY = 413.78677770818403

EXPECTED_FAIL_MIN_KG = -996.2885121085193
EXPECTED_FAIL_TOL_KG = 0.008722532240143905

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

R3R3R1R1_BLOCKED_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R1_R1_"
    "Corrected_Event_MapBack_Negative_Cell_Localization.py"
)
R3R3R1R1_BLOCKED_RUNNER_BLOB = "9299411d6b91f9854a7296249e1ebc4414dc7ead"

R3R3R1_BLOCKED_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R1_"
    "Event_MapBack_Negative_Cell_Localization.py"
)
R3R3R1_BLOCKED_RUNNER_BLOB = "347ba736f4a0f7e56de37365bbc9dcbf623cc860"

R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_"
    "First_Event_Flow_Epoch_Renewal_Execution.py"
)
R3R3_BLOB = "4aaf46d18253ac0fc4a8e50ffb3d30e841c93709"

R3R1R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R1_R2_"
    "Corrected_Interior_Bound_Failure_Localization.py"
)
R3R1R2_BLOB = "b7613d8eda48b6e3528115c40faebe46d7b61604"

F4R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_"
    "Terminal_Producer_PassThrough_Repair_Execution.py"
)
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"

F2R3 = (
    "PAD_Stream_POSTV16_AV4_F2_R3_"
    "Bounded_Physical_Occupancy_Projection_Execution.py"
)
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

A2E = (
    "PAD_Stream_POSTV16_AV4_A2_E_"
    "Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
)
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_"
    "Capillary_Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = (
    "PAD_Stream_V16E37A_"
    "Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
)
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

# Prior scientific precedents are bound as evidence only, never executed here.
R7R1 = "PAD_Stream_POSTV16_AV1_D_R7_R1_E37A_Mapback_Capacity_Failure_Localization.py"
R7R1_BLOB = "734fe31b3ff3cc6d40c33ebb9b0162b02e99a368"

R7R2 = (
    "PAD_Stream_POSTV16_AV1_D_R7_R2_"
    "Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
)
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"

E41R2 = "PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_Timestep_Repair.py"
E41R2_BLOB = "f6961c48dc47c5fb55f2af658ef4ce429eb66533"

SOURCE_BLOBS = {
    R3R3R1R1_BLOCKED_RUNNER: R3R3R1R1_BLOCKED_RUNNER_BLOB,
    R3R3R1_BLOCKED_RUNNER: R3R3R1_BLOCKED_RUNNER_BLOB,
    R3R3: R3R3_BLOB,
    R3R1R2: R3R1R2_BLOB,
    F4R3: F4R3_BLOB,
    F2R3: F2R3_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    R7R1: R7R1_BLOB,
    R7R2: R7R2_BLOB,
    E41R2: E41R2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R3_FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_SCIENTIFIC_FAIL"
R3R3_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_Scientific_Fail_Report.json"
R3R3_FAIL_STATUS = (
    "AV4F4R3R3_EVENT_REFRESH_OR_POST_REFRESH_TRANSPORT_OR_DAY500_RECURRENCE_"
    "SCIENTIFIC_FAIL_NO_SECOND_EVENT_REFRESH_OR_AUTOMATIC_RERUN_AUTHORIZED"
)

R3R3R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R1_BLOCKED"
R3R3R1_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R1_Blocked_Report.json"
R3R3R1_BLOCK_STATUS = "AV4F4R3R3R1_MAPBACK_NEGATIVE_CELL_LOCALIZATION_BLOCKED"

# R3-R3-R1-R1 was itself blocked before science. Because its own BLOCK_REL was
# crossed, that report was written into the historical R1 directory under a
# unique R1-R1 filename. Bind it exactly where it actually exists.
R3R3R1R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R1_BLOCKED"
R3R3R1R1_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R1_R1_Blocked_Report.json"
R3R3R1R1_BLOCK_STATUS = "AV4F4R3R3R1R1_MAPBACK_NEGATIVE_CELL_LOCALIZATION_BLOCKED"

R3R1R2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R1_R2_Corrected_Interior_Bound_Failure_Localization"
)
R3R1R2_STATE = "POSTV16_AV4_F4_R3_R1_R2_Partial_Teacher_State_at_Failure.npz"
R3R1R2_MANIFEST = "POSTV16_AV4_F4_R3_R1_R2_Artifact_Manifest.csv"

F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"
F2R3_MANIFEST = "POSTV16_AV4_F2_R3_Artifact_Manifest.csv"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Event_MapBack_Negative_Cell_Localization"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R1_R1_R1_BLOCKED"


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
        math.fsum(float(x) for x in np.asarray(a, dtype=np.float64).ravel())
    )


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(float(np.linalg.norm(bb.ravel())), 1.0e-30)
    )


def flat_to_kji(flat_idx: int) -> tuple[int, int, int]:
    k = int(flat_idx // (NY * NX))
    rem = int(flat_idx % (NY * NX))
    j = int(rem // NX)
    i = int(rem % NX)
    return k, j, i


def self_test() -> None:
    # Bounded-occupancy ownership and raw subsegment geometry can be globally
    # conservative yet cellwise different.
    parent = np.array([10.0, 10.0])
    cell_pv = np.array([2.0, 2.0])
    flat = np.array([0, 0, 1])
    pv = np.array([1.5, 1.5, 1.0])
    W = np.bincount(flat, weights=pv, minlength=2)
    denom = np.maximum(cell_pv, W)
    owned = parent[flat] * pv / denom[flat]
    mapped = np.bincount(flat, weights=owned, minlength=2)
    assert np.all(mapped <= parent + 1.0e-14)
    assert W[0] > cell_pv[0]

    # Occupancy scaling alone changes a signed delta's global mass and therefore
    # cannot silently be promoted to a conservative repair.
    raw_delta = np.array([-4.0, -4.0, 2.0])
    alpha = np.minimum(1.0, W / cell_pv)
    scaled = raw_delta * alpha[flat]
    assert abs(float(np.sum(raw_delta) - np.sum(scaled))) > 1.0e-12

    print(
        "POSTV16-AV4-F4-R3-R3-R1-R1-R1 corrected block-namespace + event mapback "
        "negative-cell localization self-test: PASS"
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
        "POSTV16-AV4-F4-R3-R3-R1-R1-R1 — CORRECTED BLOCK-NAMESPACE + EVENT MAPBACK NEGATIVE-CELL / "
        "OWNERSHIP-DISAGGREGATION LOCALIZATION"
    )
    print("=" * 214)
    print("DIAGNOSTIC ONLY.")
    print("FORMAL R3-R3 SCIENTIFIC FAIL REMAINS IMMUTABLE.")
    print("NO EVENT REFRESH RETRY. NO MAPBACK REPAIR. NO LP. NO SUPPORT EXPANSION.")
    print("NO CLIPPING. NO GLOBAL RESCALING. NO TIMESTEP CHANGE.")
    print("NO TRAINING. NO CHECKPOINT/INFERENCE. NO F5. NO A3-E2. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_blocked_R3R3R1R1_commit",
            parent == PARENT_R3R3R1R1_COMMIT,
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
        # Bind immutable blocked R3-R3-R1-R1 correction.
        # ------------------------------------------------------------------------------------------
        stage = "R3R3R1R1_block_closure_binding"

        prior_r1r1_block_path = drive / R3R3R1R1_BLOCK_REL / R3R3R1R1_BLOCK_REPORT
        gate(
            "blocked_R3R3R1R1_report_present",
            prior_r1r1_block_path.is_file(),
            str(prior_r1r1_block_path),
        )
        prior_r1r1_block = load_json(prior_r1r1_block_path)
        gate(
            "blocked_R3R3R1R1_status_exact",
            prior_r1r1_block["status"] == R3R3R1R1_BLOCK_STATUS,
            prior_r1r1_block["status"],
        )
        gate(
            "blocked_R3R3R1R1_stage_exact",
            prior_r1r1_block["failed_stage"] == "R3R3R1_block_closure_binding",
            prior_r1r1_block["failed_stage"],
        )
        gate(
            "blocked_R3R3R1R1_exception_exact",
            prior_r1r1_block["exception"] == "GateError('blocked_R3R3R1_report_present')",
            prior_r1r1_block["exception"],
        )
        gate(
            "blocked_R3R3R1R1_no_scientific_or_repair_execution",
            prior_r1r1_block["R3R3_scientific_FAIL_preserved"] is True
            and prior_r1r1_block["repair_selected"] is False
            and prior_r1r1_block["mapback_repair_executed"] is False
            and prior_r1r1_block["event_refresh_retried"] is False
            and prior_r1r1_block["F5_dataset_generation_authorized"] is False
            and prior_r1r1_block["automatic_rerun_authorized"] is False,
        )
        gate(
            "R3R3R1R1_crossed_namespace_closed",
            True,
            {
                "prior_R1_directory": str(R3R3R1_BLOCK_REL),
                "prior_R1_report": R3R3R1_BLOCK_REPORT,
                "prior_R1R1_actual_directory": str(R3R3R1R1_BLOCK_REL),
                "prior_R1R1_report": R3R3R1R1_BLOCK_REPORT,
                "current_block_directory": str(BLOCK_REL),
            },
        )

        # ------------------------------------------------------------------------------------------
        # Bind immutable blocked R3-R3-R1 diagnostic.
        # ------------------------------------------------------------------------------------------
        stage = "R3R3R1_block_closure_binding"

        prior_block_path = drive / R3R3R1_BLOCK_REL / R3R3R1_BLOCK_REPORT
        gate(
            "blocked_R3R3R1_report_present",
            prior_block_path.is_file(),
            str(prior_block_path),
        )
        prior_block = load_json(prior_block_path)
        gate(
            "blocked_R3R3R1_status_exact",
            prior_block["status"] == R3R3R1_BLOCK_STATUS,
            prior_block["status"],
        )
        gate(
            "blocked_R3R3R1_stage_exact",
            prior_block["failed_stage"] == "state_authority_binding",
            prior_block["failed_stage"],
        )
        gate(
            "blocked_R3R3R1_exception_exact",
            "W_m3 is not a file in the archive" in prior_block["exception"],
            prior_block["exception"],
        )
        gate(
            "blocked_R3R3R1_no_scientific_or_repair_execution",
            prior_block["R3R3_scientific_FAIL_preserved"] is True
            and prior_block["repair_selected"] is False
            and prior_block["mapback_repair_executed"] is False
            and prior_block["event_refresh_retried"] is False
            and prior_block["F5_dataset_generation_authorized"] is False
            and prior_block["automatic_rerun_authorized"] is False,
        )
        gate(
            "F2R3_Wc_archive_key_schema_corrected",
            True,
            "SG7D_occupancy_pore_volume_Wc_m3",
        )

        # ------------------------------------------------------------------------------------------
        # Bind immutable formal R3-R3 scientific FAIL.
        # ------------------------------------------------------------------------------------------
        stage = "R3R3_fail_binding"

        fail_path = drive / R3R3_FAIL_REL / R3R3_FAIL_REPORT
        gate("R3R3_scientific_fail_report_present", fail_path.is_file(), str(fail_path))
        fail = load_json(fail_path)

        gate(
            "R3R3_fail_status_exact",
            fail["status"] == R3R3_FAIL_STATUS,
            fail["status"],
        )
        gate(
            "R3R3_fail_stage_exact",
            fail["failed_stage"] == "event_exact_cartesian_mapback",
            fail["failed_stage"],
        )
        gate(
            "R3R3_fail_gate_exact",
            fail["failed_gate"] == "event_mapback_F4_mapback_negative_grid_cell_mass",
            fail["failed_gate"],
        )
        gate(
            "R3R3_fail_detail_exact",
            abs(float(fail["detail"]["minimum_kg"]) - EXPECTED_FAIL_MIN_KG) <= 1.0e-10
            and abs(float(fail["detail"]["tolerance_kg"]) - EXPECTED_FAIL_TOL_KG) <= 1.0e-12,
            fail["detail"],
        )
        gate(
            "R3R3_fail_pre_mapback_science_exact",
            fail["event_refresh_executed"] is False
            and fail["event_reprojection_executed"] is False
            and fail["second_epoch_teacher_started"] is False
            and fail["second_event_refresh_executed"] is False
            and fail["F5_dataset_generation_authorized"] is False
            and fail["automatic_rerun_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind frozen event and Day365 split-state authorities.
        # ------------------------------------------------------------------------------------------
        stage = "state_authority_binding"

        r1d = drive / R3R1R2_REL
        f2d = drive / F2R3_REL
        a2d = drive / A2E_REL

        gate("R3R1R2_output_present", r1d.is_dir(), str(r1d))
        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))

        verify_manifest(r1d, R3R1R2_MANIFEST)
        verify_manifest(f2d, F2R3_MANIFEST)
        verify_manifest(a2d, A2E_MANIFEST)

        with np.load(r1d / R3R1R2_STATE, allow_pickle=False) as z:
            event_cv_mass = np.asarray(
                z["partial_CV_component_mass_kg"],
                dtype=np.float64,
            )
            event_elapsed = float(np.asarray(z["elapsed_days"]).reshape(()))
            event_remaining = float(np.asarray(z["remaining_days"]).reshape(()))
            event_substeps = int(np.asarray(z["accepted_substeps"]).reshape(()))

        with np.load(f2d / F2R3_STATE, allow_pickle=False) as z:
            parent_cv_mass = np.asarray(
                z["parent_CV_component_mass_kg"],
                dtype=np.float64,
            )
            parent_cv_sat = np.asarray(
                z["parent_CV_saturation"],
                dtype=np.float64,
            )
            parent_cv_coeff = np.asarray(
                z["parent_CV_pressure_mass_coeff"],
                dtype=np.float64,
            )
            parent_mapped_grid = np.asarray(
                z["mapped_grid_component_mass_kg"],
                dtype=np.float64,
            )
            parent_residual_grid = np.asarray(
                z["residual_grid_component_mass_kg"],
                dtype=np.float64,
            )
            parent_W = np.asarray(
                z["SG7D_occupancy_pore_volume_Wc_m3"],
                dtype=np.float64,
            )
            parent_alpha = np.asarray(
                z["occupancy_fraction_alpha"],
                dtype=np.float64,
            )

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            parent_grid_mass = np.asarray(
                z["parent_component_mass_kg"],
                dtype=np.float64,
            )
            pressure = np.asarray(
                z["refreshed_pressure_psi"],
                dtype=np.float64,
            )
            grid_pv = np.asarray(
                z["pore_volume_m3"],
                dtype=np.float64,
            )
            p_ref = float(
                np.asarray(z["reference_gas_pressure_pa"]).reshape(())
            )
            xyz = np.asarray(
                z["streamline_xyz_m"],
                dtype=np.float64,
            )
            tof_s = np.asarray(
                z["streamline_tof_s"],
                dtype=np.float64,
            )
            weights_s = np.asarray(
                z["streamline_weight_m3_s"],
                dtype=np.float64,
            )

        gate(
            "authority_shapes_exact",
            event_cv_mass.shape == (NSL, NCV)
            and parent_cv_mass.shape == (NSL, NCV)
            and parent_cv_sat.shape == (NSL, NCV)
            and parent_cv_coeff.shape == (NSL, NCV)
            and parent_grid_mass.shape == GRID
            and parent_mapped_grid.shape == GRID
            and parent_residual_grid.shape == GRID
            and parent_W.shape == GRID
            and parent_alpha.shape == GRID
            and grid_pv.shape == GRID
            and pressure.shape == GRID
            and xyz.shape == (NSL, NN, 3)
            and tof_s.shape == (NSL, NN)
            and weights_s.shape == (NSL,),
        )
        gate(
            "event_identity_exact",
            event_substeps == 3604
            and abs(event_elapsed - 48.78677770818403) <= 1.0e-12
            and abs(event_remaining - 86.21322229181597) <= 1.0e-12,
            {
                "substeps": event_substeps,
                "elapsed": event_elapsed,
                "remaining": event_remaining,
            },
        )
        gate(
            "Day365_split_state_cellwise_ledger",
            float(
                np.max(
                    np.abs(
                        parent_mapped_grid
                        + parent_residual_grid
                        - parent_grid_mass
                    )
                )
            ) <= 1.0e-10,
            float(
                np.max(
                    np.abs(
                        parent_mapped_grid
                        + parent_residual_grid
                        - parent_grid_mass
                    )
                )
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Rebuild exact Day365 operator / geometry.
        # ------------------------------------------------------------------------------------------
        stage = "operator_geometry_reconstruction"

        r2 = load_module(root / R2, "postv16_av4_r3r3r1_r2")
        e37 = load_module(root / E37A, "postv16_av4_r3r3r1_e37")
        sg7d = load_module(root / SG7D, "postv16_av4_r3r3r1_sg7d")

        operator = sg7d.build_subsegment_operator(
            xyz,
            tof_s / 86400.0,
            weights_s * 86400.0,
        )
        geometry = e37.build_control_volume_geometry(
            r2,
            operator,
            pressure,
            p_ref,
            NSL,
            NCV,
        )

        cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        flat = np.asarray(geometry["flat_cell"], dtype=np.int64)
        pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

        gate(
            "operator_geometry_exact_shapes",
            len(flat) == len(cv_id) == len(pv) == len(pseg)
            and int(np.min(cv_id)) >= 0
            and int(np.max(cv_id)) < NSL * NCV
            and int(np.min(flat)) >= 0
            and int(np.max(flat)) < NCELL
            and np.all(pv > 0.0),
            len(flat),
        )
        gate(
            "operator_W_matches_F2R3",
            relative_l2(
                np.bincount(flat, weights=pv, minlength=NCELL).reshape(GRID),
                parent_W,
            ) <= 1.0e-14,
        )

        event_cv_sat = np.asarray(
            e37.invert_cv_mass_to_saturation(
                r2,
                event_cv_mass,
                parent_cv_coeff,
            ),
            dtype=np.float64,
        )

        # ------------------------------------------------------------------------------------------
        # Reconstruct the exact raw F4 signed mapback without applying its FAIL.
        # ------------------------------------------------------------------------------------------
        stage = "raw_F4_mapback_localization"

        old_flat_sat = parent_cv_sat.reshape(-1)
        new_flat_sat = event_cv_sat.reshape(-1)

        old_sub_sat = old_flat_sat[cv_id]
        new_sub_sat = new_flat_sat[cv_id]
        old_sg = np.clip(old_sub_sat - BACKGROUND, 0.0, MAX_SG)
        new_sg = np.clip(new_sub_sat - BACKGROUND, 0.0, MAX_SG)

        rho_old = np.asarray(
            r2.gas_density_from_state(old_sub_sat, pseg, p_ref),
            dtype=np.float64,
        )
        rho_new = np.asarray(
            r2.gas_density_from_state(new_sub_sat, pseg, p_ref),
            dtype=np.float64,
        )

        raw_old_sub_mass = pv * rho_old * old_sg
        raw_new_sub_mass = pv * rho_new * new_sg
        raw_sub_delta = raw_new_sub_mass - raw_old_sub_mass

        raw_old_cell = np.bincount(
            flat,
            weights=raw_old_sub_mass,
            minlength=NCELL,
        )
        raw_new_cell = np.bincount(
            flat,
            weights=raw_new_sub_mass,
            minlength=NCELL,
        )
        raw_delta_cell = np.bincount(
            flat,
            weights=raw_sub_delta,
            minlength=NCELL,
        )

        parent_flat = parent_grid_mass.reshape(-1)
        mapped_flat = parent_mapped_grid.reshape(-1)
        residual_flat = parent_residual_grid.reshape(-1)
        pvcell_flat = grid_pv.reshape(-1)
        W_flat = parent_W.reshape(-1)
        alpha_flat = parent_alpha.reshape(-1)

        future_flat = parent_flat + raw_delta_cell

        cv_delta = fsum_array(event_cv_mass) - fsum_array(parent_cv_mass)
        raw_delta_total = fsum_array(raw_sub_delta)
        transfer_residual = raw_delta_total - cv_delta
        transfer_tol = max(1.0e-6, 1.0e-10 * max(abs(cv_delta), 1.0))

        gate(
            "raw_F4_CV_to_subsegment_transfer_closure",
            abs(transfer_residual) <= transfer_tol,
            {
                "cv_delta_kg": cv_delta,
                "subsegment_delta_kg": raw_delta_total,
                "residual_kg": transfer_residual,
                "tolerance_kg": transfer_tol,
            },
        )

        raw_min = float(np.min(future_flat))
        negative_mask = future_flat < -EXPECTED_FAIL_TOL_KG
        negative_idx = np.flatnonzero(negative_mask)
        negative_count = int(negative_idx.size)
        worst_flat = int(np.argmin(future_flat))
        worst_kji = flat_to_kji(worst_flat)

        gate(
            "R3R3_negative_cell_failure_reproduced",
            negative_count > 0
            and abs(raw_min - EXPECTED_FAIL_MIN_KG) <= 1.0e-8,
            {
                "negative_cell_count": negative_count,
                "minimum_kg": raw_min,
                "worst_cell_kji": list(worst_kji),
            },
        )

        # ------------------------------------------------------------------------------------------
        # Reconstruct exact F2-R3 bounded parent ownership at subsegment level.
        # ------------------------------------------------------------------------------------------
        stage = "bounded_parent_ownership_audit"

        denom = np.maximum(pvcell_flat, W_flat)
        owned_parent_sub_mass = parent_flat[flat] * pv / denom[flat]
        owned_parent_cell = np.bincount(
            flat,
            weights=owned_parent_sub_mass,
            minlength=NCELL,
        )

        gate(
            "bounded_parent_subsegment_ownership_reconstructs_F2R3_mapped_grid",
            float(np.max(np.abs(owned_parent_cell - mapped_flat))) <= 1.0e-8,
            float(np.max(np.abs(owned_parent_cell - mapped_flat))),
        )

        owned_cv = np.bincount(
            cv_id,
            weights=owned_parent_sub_mass,
            minlength=NSL * NCV,
        ).reshape(NSL, NCV)
        gate(
            "bounded_parent_subsegment_ownership_reconstructs_F2R3_CV_mass",
            relative_l2(owned_cv, parent_cv_mass) <= 1.0e-14,
            relative_l2(owned_cv, parent_cv_mass),
        )

        old_distribution_delta_cell = raw_old_cell - owned_parent_cell
        old_distribution_total = fsum_array(old_distribution_delta_cell)
        old_distribution_TV = 0.5 * fsum_array(np.abs(old_distribution_delta_cell))

        gate(
            "old_raw_EOS_inventory_global_mass_equals_bounded_CV_mass",
            abs(
                fsum_array(raw_old_sub_mass)
                - fsum_array(parent_cv_mass)
            ) <= max(
                1.0e-6,
                1.0e-10 * max(fsum_array(parent_cv_mass), 1.0),
            ),
            {
                "raw_old_subsegment_mass_kg": fsum_array(raw_old_sub_mass),
                "bounded_parent_CV_mass_kg": fsum_array(parent_cv_mass),
            },
        )
        gate(
            "old_cellwise_disaggregation_is_not_identical_to_bounded_ownership",
            old_distribution_TV > 1.0e-6,
            old_distribution_TV,
        )

        # ------------------------------------------------------------------------------------------
        # Cellwise localization.
        # ------------------------------------------------------------------------------------------
        stage = "negative_cell_mechanism_classification"

        subcount = np.bincount(flat, minlength=NCELL)
        pair_stream = flat.astype(np.int64) * NSL + (
            cv_id // NCV
        )
        unique_stream_pair = np.unique(pair_stream)
        unique_stream_cell = unique_stream_pair // NSL
        streamcount = np.bincount(
            unique_stream_cell,
            minlength=NCELL,
        )

        pair_cv = flat.astype(np.int64) * (NSL * NCV) + cv_id
        unique_cv_pair = np.unique(pair_cv)
        unique_cv_cell = unique_cv_pair // (NSL * NCV)
        cvcount = np.bincount(
            unique_cv_cell,
            minlength=NCELL,
        )

        rows: list[dict[str, Any]] = []
        order = sorted(
            negative_idx.tolist(),
            key=lambda idx: float(future_flat[idx]),
        )

        for idx in order:
            k, j, i = flat_to_kji(int(idx))
            rows.append(
                {
                    "flat_cell": int(idx),
                    "k": k,
                    "j": j,
                    "i": i,
                    "parent_total_mass_kg": float(parent_flat[idx]),
                    "parent_mapped_mass_kg": float(mapped_flat[idx]),
                    "parent_residual_mass_kg": float(residual_flat[idx]),
                    "physical_cell_pore_volume_m3": float(pvcell_flat[idx]),
                    "SG7D_coverage_W_m3": float(W_flat[idx]),
                    "coverage_ratio_W_over_cellPV": float(
                        W_flat[idx] / pvcell_flat[idx]
                    ),
                    "occupancy_fraction_alpha": float(alpha_flat[idx]),
                    "raw_old_EOS_subsegment_mass_cell_kg": float(raw_old_cell[idx]),
                    "raw_new_EOS_subsegment_mass_cell_kg": float(raw_new_cell[idx]),
                    "raw_signed_delta_kg": float(raw_delta_cell[idx]),
                    "raw_future_cell_mass_kg": float(future_flat[idx]),
                    "negative_deficit_kg": float(-future_flat[idx]),
                    "raw_old_minus_bounded_mapped_kg": float(
                        old_distribution_delta_cell[idx]
                    ),
                    "raw_old_minus_parent_total_kg": float(
                        raw_old_cell[idx] - parent_flat[idx]
                    ),
                    "withdrawal_demand_kg": float(
                        max(-raw_delta_cell[idx], 0.0)
                    ),
                    "subsegment_count": int(subcount[idx]),
                    "unique_streamline_count": int(streamcount[idx]),
                    "unique_CV_count": int(cvcount[idx]),
                    "overcovered_W_gt_cellPV": bool(
                        W_flat[idx] > pvcell_flat[idx]
                    ),
                }
            )

        worst = rows[0]
        overcovered_negative = int(
            np.sum(
                negative_mask
                & (W_flat > pvcell_flat)
            )
        )
        raw_old_exceeds_parent_negative = int(
            np.sum(
                negative_mask
                & (raw_old_cell > parent_flat)
            )
        )
        raw_old_exceeds_mapped_negative = int(
            np.sum(
                negative_mask
                & (raw_old_cell > mapped_flat)
            )
        )
        total_negative_deficit = fsum_array(
            -future_flat[negative_mask]
        )

        # ------------------------------------------------------------------------------------------
        # NON-AUTHORITATIVE diagnostic probe A:
        # occupancy-scale the signed raw delta. This may improve local bounds
        # but is not conservative with respect to the CV transport delta.
        # ------------------------------------------------------------------------------------------
        scaled_sub_delta = raw_sub_delta * alpha_flat[flat]
        scaled_delta_cell = np.bincount(
            flat,
            weights=scaled_sub_delta,
            minlength=NCELL,
        )
        scaled_future = parent_flat + scaled_delta_cell
        scaled_global_defect = (
            fsum_array(scaled_sub_delta) - cv_delta
        )

        # ------------------------------------------------------------------------------------------
        # NON-AUTHORITATIVE diagnostic probe B:
        # distribute negative CV deltas proportionally to the actual bounded
        # parent ownership inside each CV. Positive deltas are intentionally
        # omitted; therefore this is NOT a full mapback candidate.
        # ------------------------------------------------------------------------------------------
        delta_cv_flat = (
            event_cv_mass - parent_cv_mass
        ).reshape(-1)
        old_cv_flat = parent_cv_mass.reshape(-1)

        negative_cv = delta_cv_flat < 0.0
        safe_denom = np.maximum(
            old_cv_flat[cv_id],
            1.0e-300,
        )
        ownership_negative_sub_delta = np.zeros_like(
            owned_parent_sub_mass
        )
        qneg = negative_cv[cv_id]
        ownership_negative_sub_delta[qneg] = (
            delta_cv_flat[cv_id[qneg]]
            * owned_parent_sub_mass[qneg]
            / safe_denom[qneg]
        )
        ownership_negative_cell = np.bincount(
            flat,
            weights=ownership_negative_sub_delta,
            minlength=NCELL,
        )
        withdrawal_only_future = parent_flat + ownership_negative_cell

        gate(
            "ownership_proportional_negative_withdrawal_probe_nonnegative",
            float(np.min(withdrawal_only_future)) >= -1.0e-8,
            float(np.min(withdrawal_only_future)),
        )

        # Mechanism classification is evidence-driven and does not select repair.
        all_negative_overcovered = (
            negative_count > 0
            and overcovered_negative == negative_count
        )
        if (
            all_negative_overcovered
            and raw_old_exceeds_mapped_negative == negative_count
        ):
            cause_class = (
                "OVERLAP_AMPLIFIED_BOUNDED_PARENT_OWNERSHIP_"
                "VS_RAW_EOS_DELTA_DISAGGREGATION_INCOMPATIBILITY"
            )
        elif raw_old_exceeds_mapped_negative > 0:
            cause_class = (
                "BOUNDED_PARENT_OWNERSHIP_VS_RAW_EOS_DELTA_"
                "DISAGGREGATION_INCOMPATIBILITY_WITH_MIXED_COVERAGE"
            )
        else:
            cause_class = (
                "SIGNED_MAPBACK_LOCAL_CELL_WITHDRAWAL_INCOMPATIBILITY_"
                "NOT_EXPLAINED_BY_PARENT_OWNERSHIP_MISMATCH"
            )

        diagnosis = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "R3R3_scientific_FAIL_preserved": True,
            "formal_failure": {
                "stage": "event_exact_cartesian_mapback",
                "gate": "event_mapback_F4_mapback_negative_grid_cell_mass",
                "minimum_kg": EXPECTED_FAIL_MIN_KG,
                "tolerance_kg": EXPECTED_FAIL_TOL_KG,
            },
            "raw_mapback": {
                "CV_delta_mass_kg": cv_delta,
                "raw_subsegment_delta_mass_kg": raw_delta_total,
                "transfer_residual_kg": transfer_residual,
                "negative_cartesian_cell_count": negative_count,
                "total_negative_deficit_kg": total_negative_deficit,
                "worst_cell_kji": list(worst_kji),
                "worst_future_mass_kg": raw_min,
            },
            "parent_split_state": {
                "bounded_ownership_operator":
                    "m_q = M_parent[c(q)] * PV_q / max(PV_cell_c, W_c)",
                "mapped_mass_kg": fsum_array(mapped_flat),
                "residual_mass_kg": fsum_array(residual_flat),
                "cellwise_split_state_closure": True,
            },
            "cellwise_old_inventory_reconciliation": {
                "raw_EOS_old_subsegment_mass_kg": fsum_array(raw_old_sub_mass),
                "bounded_parent_CV_mass_kg": fsum_array(parent_cv_mass),
                "global_mass_equal": True,
                "cellwise_total_variation_kg": old_distribution_TV,
                "cellwise_signed_sum_kg": old_distribution_total,
                "interpretation": (
                    "The same globally conserved parent CV mass is distributed "
                    "differently across Cartesian cells by bounded F2-R3 ownership "
                    "and by the raw E37A EOS/subsegment reconstruction."
                ),
            },
            "negative_cell_statistics": {
                "count": negative_count,
                "overcovered_count": overcovered_negative,
                "raw_old_exceeds_parent_total_count":
                    raw_old_exceeds_parent_negative,
                "raw_old_exceeds_bounded_mapped_count":
                    raw_old_exceeds_mapped_negative,
                "all_negative_cells_overcovered":
                    all_negative_overcovered,
            },
            "worst_cell": worst,
            "non_authoritative_probes": {
                "occupancy_scaled_raw_delta": {
                    "minimum_future_cell_mass_kg":
                        float(np.min(scaled_future)),
                    "negative_cell_count":
                        int(np.sum(scaled_future < -EXPECTED_FAIL_TOL_KG)),
                    "global_CV_delta_conservation_defect_kg":
                        scaled_global_defect,
                    "repair_candidate": False,
                    "reason_not_authoritative": (
                        "Scaling signed delta by occupancy changes the global "
                        "CV transport mass increment."
                    ),
                },
                "ownership_proportional_negative_withdrawal_only": {
                    "minimum_future_cell_mass_kg":
                        float(np.min(withdrawal_only_future)),
                    "negative_cell_count":
                        int(
                            np.sum(
                                withdrawal_only_future
                                < -EXPECTED_FAIL_TOL_KG
                            )
                        ),
                    "positive_CV_delta_placement_included": False,
                    "repair_candidate": False,
                    "reason_not_authoritative": (
                        "This probe certifies only the withdrawal branch and "
                        "does not define placement/capacity handling for positive deltas."
                    ),
                },
            },
            "cause_class": cause_class,
            "repair_selected": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "R3R3_scientific_FAIL_preserved": True,
            "blocked_R3R3R1_schema_failure_preserved": True,
            "blocked_R3R3R1R1_namespace_failure_preserved": True,
            "block_namespace_crossing_corrected_only": True,
            "F2R3_Wc_archive_key_schema_corrected_only": True,
            "negative_mapback_cells_localized": True,
            "cause_class": cause_class,
            "repair_selected": False,
            "mapback_repair_executed": False,
            "LP_executed": False,
            "support_domain_changed": False,
            "mass_clipped_or_rescaled": False,
            "timestep_changed": False,
            "event_refresh_retried": False,
            "F4R3R3R2_design_freeze_authorized": True,
            "F4R3R3R2_repair_execution_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R2",
            "name": (
                "Prospective Event-Time Conservative Cartesian MapBack "
                "Ownership-Reconciliation Repair Design Freeze"
            ),
            "authorized": True,
            "execution": False,
            "required_R3R3R1_status": STATUS_PASS,
            "required_evidence": [
                "exact negative-cell set and worst cell",
                "coverage / physical-PV ratios",
                "bounded parent ownership versus raw EOS old inventory",
                "signed raw mapback withdrawals/additions",
                "global transfer closure",
                "diagnostic-only occupancy scaling conservation defect",
                "diagnostic-only ownership-proportional withdrawal feasibility",
            ],
            "must_decide_before_execution": [
                "whether repair acts on subsegment ownership, Cartesian reconciliation, or both",
                "how positive CV mass increments are placed without violating cell capacity",
                "whether support remains S0 or requires already-frozen occupancy-domain machinery",
                "how exact CV transport delta and Cartesian mass conservation remain identical",
                "how residual-grid sidecar participates",
            ],
            "forbidden": [
                "silent occupancy scaling of signed delta",
                "cellwise clipping",
                "mass discard",
                "global mass rescaling",
                "saturation-bound relaxation",
                "unfrozen LP execution",
                "unfrozen support expansion",
                "event refresh retry",
                "training",
                "checkpoint inference",
                "locked OOD access",
                "CMG",
            ],
            "F5_dataset_generation_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "blocked_R3R3R1_schema_failure_preserved": True,
            "blocked_R3R3R1R1_namespace_failure_preserved": True,
            "block_namespace_crossing_corrected": True,
            "F2R3_Wc_archive_key": "SG7D_occupancy_pore_volume_Wc_m3",
            "negative_cartesian_cell_count": negative_count,
            "worst_cell_kji": list(worst_kji),
            "worst_future_mass_kg": raw_min,
            "total_negative_deficit_kg": total_negative_deficit,
            "all_negative_cells_overcovered": all_negative_overcovered,
            "old_inventory_cellwise_total_variation_kg": old_distribution_TV,
            "cause_class": cause_class,
            "repair_selected": False,
            "R3R3R2_design_freeze_authorized": True,
            "F5_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R1_R1_R1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R1_R1_R1_MapBack_Failure_Diagnosis.json":
                json_bytes(diagnosis),
            "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Negative_Cell_Audit.csv":
                csv_bytes(rows),
            "POSTV16_AV4_F4_R3_R3_R1_R1_R1_R3R3R2_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name
                != "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Artifact_Manifest.csv"
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
                "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            f"{MILESTONE}: EVENT MAPBACK NEGATIVE-CELL LOCALIZATION PASS"
        )
        print("=" * 214)
        print("R3-R3 scientific FAIL                    : PRESERVED")
        print("Negative Cartesian cells                 :", negative_count)
        print("Worst cell k/j/i                         :", *worst_kji, sep=" / ")
        print("Worst future cell mass kg                :", raw_min)
        print("Total negative deficit kg                :", total_negative_deficit)
        print("Worst coverage W / physical cell PV      :", worst["coverage_ratio_W_over_cellPV"])
        print("Worst parent / mapped / residual mass kg :", worst["parent_total_mass_kg"], "/", worst["parent_mapped_mass_kg"], "/", worst["parent_residual_mass_kg"])
        print("Worst raw old / new EOS cell mass kg     :", worst["raw_old_EOS_subsegment_mass_cell_kg"], "/", worst["raw_new_EOS_subsegment_mass_cell_kg"])
        print("Worst raw signed delta kg                :", worst["raw_signed_delta_kg"])
        print("Old inventory cellwise TV mismatch kg    :", old_distribution_TV)
        print("All negative cells overcovered           :", all_negative_overcovered)
        print("Cause class                              :", cause_class)
        print("Repair selected                          : False")
        print("POSTV16-AV4-F4-R3-R3-R2 design freeze   : AUTHORIZED")
        print("Repair execution / F5 / training         : NOT AUTHORIZED")
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
            "R3R3_scientific_FAIL_preserved": True,
            "repair_selected": False,
            "mapback_repair_executed": False,
            "event_refresh_retried": False,
            "F4R3R3R2_design_freeze_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("R3-R3 scientific FAIL remains immutable.")
        print("NO MAPBACK REPAIR OR AUTOMATIC RERUN AUTHORIZED.")
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
