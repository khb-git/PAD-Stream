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


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R2"

STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R2_OPTIMIZED_H2_EVENT_MAPBACK_BOUND_SINGLE_SAME_TIME_"
    "PRESSURE_DARCY_POLLOCK_TOF_REFRESH_BOUNDED_REFRESHED_GEOMETRY_"
    "REPROJECTION_PASS_NO_PHYSICAL_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R2_SAME_TIME_FLOW_REFRESH_OR_BOUNDED_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_SUPPORT_EXPANSION_NO_SECOND_REFRESH_NO_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3O3R2_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_O3R1_BLOCK_COMMIT = "c4b1b67f9835d79f23e50b5340318a45dd6d6274"
PRIOR_O3_BLOCK_COMMIT = "c6d38db2f3f0ae284ecd9f62013bc2fc421b36f5"
PRIOR_O3R1_MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R1"
PRIOR_O3R1_STATUS_BLOCKED = "AV4F4R3R3R3R3R3O3R1_TECHNICAL_OR_AUTHORITY_BLOCK"
PRIOR_O3R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R1_SG3_Blob_Authority_Repair_"
    "Same_Time_Flow_Refresh_and_Bounded_Reprojection_Execution.py"
)
PRIOR_O3R1_RUNNER_BLOB = "c5e7f809fce3d66b9ad2a28d56e7f43d58327097"
PRIOR_O3_MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3"
PRIOR_O3_STATUS_BLOCKED = "AV4F4R3R3R3R3R3O3_TECHNICAL_OR_AUTHORITY_BLOCK"
PRIOR_O3_RUNNER = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3_Same_Time_Flow_Refresh_and_Bounded_Reprojection_Execution.py"
PRIOR_O3_RUNNER_BLOB = "d332d40c388e3f125ce08022827026548e1656ab"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NN = 201
NCV = 200
NCVTOTAL = NSL * NCV
BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
EVENT_DAY = 413.78677770818403
EVENT_ELAPSED = 48.78677770818403
EVENT_REMAINING = 86.21322229181597
EVENT_SUBSTEPS = 3604
EXPECTED_E0_PAIRS = 269721
EXPECTED_E2_PAIRS = 3091073
EXPECTED_E2_GLOBAL_CELLS = 34497
EXPECTED_O2_MANIFEST_FILES = {
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Summary.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimization_Audit.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Stage_Telemetry.csv",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Component_Summary.csv",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_O3_Handoff_Contract.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Decision_Contract.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Final_Gate_Matrix.csv",
}

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# O3-R2 repairs one incorrect O2 manifest-cardinality authority assertion only. O2 is immutable input; the remaining machinery is the exact
# already-audited same-time flow refresh / bounded reprojection stack used by the earlier event path.
# --------------------------------------------------------------------------------------------------

O2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution.py"
)
O2_BLOB = "2e04f77750add23f9cfe5143119668450201354f"

R3R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_"
    "Ownership_Reconciled_Event_MapBack_and_Flow_Refresh_Execution.py"
)
R3R3R3_BLOB = "b2c129bd067ef75163c3f06de5c15adc53ae5633"

R3EXEC = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_"
    "First_Event_Flow_Epoch_Renewal_Execution.py"
)
R3EXEC_BLOB = "4aaf46d18253ac0fc4a8e50ffb3d30e841c93709"

F4R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_"
    "Terminal_Producer_PassThrough_Repair_Execution.py"
)
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"

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

SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"

SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"

SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"

SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"

SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    PRIOR_O3R1_RUNNER: PRIOR_O3R1_RUNNER_BLOB,
    PRIOR_O3_RUNNER: PRIOR_O3_RUNNER_BLOB,
    O2: O2_BLOB,
    R3R3R3: R3R3R3_BLOB,
    R3EXEC: R3EXEC_BLOB,
    F4R3: F4R3_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    SG7D: SG7D_BLOB,
    R3R2R1: R3R2R1_BLOB,
    PERM: PERM_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Exact Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

PRIOR_O3_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3_BLOCKED"
PRIOR_O3_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3_Blocked_Report.json"

PRIOR_O3R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R1_BLOCKED"
PRIOR_O3R1_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R1_Blocked_Report.json"

O2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Persistent_Native_HiGHS_H2_Assignment_Execution"
)
O2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Summary.json"
O2_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz"
O2_HANDOFF = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_O3_Handoff_Contract.json"
O2_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Decision_Contract.json"
O2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Artifact_Manifest.csv"
O2_STATUS = (
    "AV4F4R3R3R3R3R3O2_PERSISTENT_NATIVE_HIGHS_EXACT_ZERO_GRAPH_"
    "PREPROCESSING_COMPONENT_DECOMPOSITION_BASIS_REUSE_H2_ASSIGNMENT_PASS_"
    "EXACT_CARTESIAN_EVENT_MAPBACK_CERTIFIED_NO_FLOW_REFRESH_NO_TIME_ADVANCE"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Same_Time_Flow_Refresh_and_Bounded_Reprojection"
)
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_BLOCKED"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


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
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
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
    return float(math.fsum(float(x) for x in np.asarray(a, dtype=np.float64).ravel()))


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(float(np.linalg.norm(bb.ravel())), 1.0e-30)
    )


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=np.float64))))


def self_test() -> None:
    a = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    assert fsum_array(a) == 6.0
    assert relative_l2(a, a) == 0.0
    assert max_abs(np.array([-2.0, 1.0])) == 2.0
    payload = {"b": np.array([2, 3]), "a": np.array([1.0])}
    assert deterministic_npz_bytes(payload) == deterministic_npz_bytes(payload)
    assert MILESTONE.endswith("O3-R2")
    assert PRIOR_O3_MILESTONE.endswith("O3")
    assert PRIOR_O3R1_MILESTONE.endswith("O3-R1")
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R2 same-time flow-refresh / "
        "bounded-reprojection structural self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    event_mass_inverted = False
    event_refresh_executed = False
    event_reprojection_executed = False

    def gate(name: str, cond: bool, detail: Any = None) -> None:
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" — {detail}" if detail is not None else ""))

    def sci_gate(name: str, cond: bool, detail: Any = None) -> None:
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise ScientificFail(name, detail)
        print(f"[PASS] {name}" + (f" — {detail}" if detail is not None else ""))

    print("=" * 214)
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R2 — SAME-TIME FLOW REFRESH AND "
        "BOUNDED REPROJECTION FROM OPTIMIZED H2 EVENT MAPBACK"
    )
    print("=" * 214)
    print("O3-R2 IS A TECHNICAL-AUTHORITY REPAIR ONLY: O2 MANIFEST CARDINALITY 9 -> 8.")
    print("O2 OPTIMIZED H2 EVENT MAPBACK IS IMMUTABLE INPUT. NO ASSIGNMENT LP IN O3-R2.")
    print("EXACTLY ONE SAME-TIME PRESSURE/DARCY/POLLOCK/TOF REFRESH.")
    print("EXACTLY ONE BOUNDED REFRESHED-GEOMETRY REPROJECTION.")
    print("NO PHYSICAL-TIME ADVANCE. NO DAY500 CONTINUATION. NO SECOND EVENT REFRESH.")
    print("NO SUPPORT RADIUS >2. NO VERTICAL/H2+V1 FALLBACK. NO F5. NO TRAINING. NO A3-E2. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_blocked_O3R1_commit", parent == PARENT_O3R1_BLOCK_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind the immutable prior O3 technical block. This proves no scientific operation ran and
        # that O3-R2 preserves that SG3 repair while correcting only the O2 manifest-cardinality assertion.
        # ------------------------------------------------------------------------------------------
        stage = "prior_O3_technical_block_binding"
        prior_block_path = drive / PRIOR_O3_BLOCK_REL / PRIOR_O3_BLOCK_REPORT
        gate("prior_O3_block_report_present", prior_block_path.is_file(), str(prior_block_path))
        prior_block = load_json(prior_block_path)
        prior_sg3_gate = (
            prior_block.get("gates", {})
            .get("PAD_Stream_V15SG3_FiveSpot_Pressure_Solve_git_blob_exact", {})
        )
        gate(
            "prior_O3_block_exact_and_prephysics",
            prior_block.get("milestone") == PRIOR_O3_MILESTONE
            and prior_block.get("status") == PRIOR_O3_STATUS_BLOCKED
            and prior_block.get("failed_stage") == "repository_authority"
            and prior_block.get("O2_optimized_H2_assignment_preserved") is True
            and prior_block.get("O2_assignment_reexecuted") is False
            and prior_block.get("event_mass_inversion_executed") is False
            and prior_block.get("event_refresh_executed") is False
            and prior_block.get("event_reprojection_executed") is False
            and prior_block.get("physical_time_advanced") is False
            and prior_block.get("R3R3R4_authorized") is False
            and prior_sg3_gate.get("status") == "FAIL"
            and prior_sg3_gate.get("detail") == SG3_BLOB
            and "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve_git_blob_exact"
                in str(prior_block.get("exception", "")),
            {
                "failed_stage": prior_block.get("failed_stage"),
                "SG3_actual_blob": prior_sg3_gate.get("detail"),
                "prephysics": not any([
                    prior_block.get("event_mass_inversion_executed"),
                    prior_block.get("event_refresh_executed"),
                    prior_block.get("event_reprojection_executed"),
                ]),
            },
        )

        # ------------------------------------------------------------------------------------------
        # Bind the immutable O3-R1 technical block. It must have failed only because the O2 manifest
        # was correctly verified but then incorrectly asserted to contain 9 rows rather than 8.
        # No scientific operation may have run in O3-R1.
        # ------------------------------------------------------------------------------------------
        stage = "prior_O3R1_technical_block_binding"
        prior_r1_block_path = drive / PRIOR_O3R1_BLOCK_REL / PRIOR_O3R1_BLOCK_REPORT
        gate("prior_O3R1_block_report_present", prior_r1_block_path.is_file(), str(prior_r1_block_path))
        prior_r1_block = load_json(prior_r1_block_path)
        prior_manifest_gate = (
            prior_r1_block.get("gates", {}).get("O2_manifest_exact_9", {})
        )
        gate(
            "prior_O3R1_block_exact_and_prephysics",
            prior_r1_block.get("milestone") == PRIOR_O3R1_MILESTONE
            and prior_r1_block.get("status") == PRIOR_O3R1_STATUS_BLOCKED
            and prior_r1_block.get("failed_stage") == "O2_authority_binding"
            and prior_r1_block.get("O2_optimized_H2_assignment_preserved") is True
            and prior_r1_block.get("O2_assignment_reexecuted") is False
            and prior_r1_block.get("event_mass_inversion_executed") is False
            and prior_r1_block.get("event_refresh_executed") is False
            and prior_r1_block.get("event_reprojection_executed") is False
            and prior_r1_block.get("physical_time_advanced") is False
            and prior_r1_block.get("R3R3R4_authorized") is False
            and prior_manifest_gate.get("status") == "FAIL"
            and int(prior_manifest_gate.get("detail", -1)) == 8
            and "O2_manifest_exact_9" in str(prior_r1_block.get("exception", "")),
            {
                "failed_stage": prior_r1_block.get("failed_stage"),
                "manifest_rows_verified": prior_manifest_gate.get("detail"),
                "prephysics": not any([
                    prior_r1_block.get("event_mass_inversion_executed"),
                    prior_r1_block.get("event_refresh_executed"),
                    prior_r1_block.get("event_reprojection_executed"),
                ]),
            },
        )

        # ------------------------------------------------------------------------------------------
        # Bind immutable O2 PASS and its original O3 handoff.
        # ------------------------------------------------------------------------------------------
        stage = "O2_authority_binding"
        o2d = drive / O2_REL
        gate("O2_output_present", o2d.is_dir(), str(o2d))
        o2manifest = verify_manifest(o2d, O2_MANIFEST)
        gate("O2_manifest_exact_8", len(o2manifest) == 8, len(o2manifest))
        gate(
            "O2_manifest_payload_file_set_exact",
            set(o2manifest) == EXPECTED_O2_MANIFEST_FILES,
            sorted(o2manifest),
        )

        o2summary = load_json(o2d / O2_SUMMARY)
        o2handoff = load_json(o2d / O2_HANDOFF)
        o2decision = load_json(o2d / O2_DECISION)

        gate("O2_status_exact", o2summary.get("status") == O2_STATUS, o2summary.get("status"))
        gate(
            "O2_assignment_pass_exact",
            o2summary.get("formal_R1_H2_feasibility_certificate_bound") is True
            and o2summary.get("stage1_fresh_feasibility_recertification_pass") is True
            and int(o2summary.get("E0_pair_count", -1)) == EXPECTED_E0_PAIRS
            and int(o2summary.get("E2_pair_count", -1)) == EXPECTED_E2_PAIRS
            and int(o2summary.get("E2_global_cell_count", -1)) == EXPECTED_E2_GLOBAL_CELLS,
        )
        gate(
            "O2_no_refresh_or_time_advance",
            o2summary.get("flow_refresh_executed") is False
            and o2summary.get("Pollock_or_TOF_refresh_executed") is False
            and o2summary.get("physical_time_advanced") is False,
        )
        gate(
            "O2_O3_handoff_exact",
            o2handoff.get("milestone") == PRIOR_O3_MILESTONE
            and o2handoff.get("authorized") is True
            and o2handoff.get("execution") is True
            and o2handoff.get("required_O2_status") == O2_STATUS
            and o2handoff.get("required_parent_state") == O2_STATE
            and o2handoff.get("physical_time_advance_before_O3") is False,
        )
        gate(
            "O2_decision_authority_exact",
            o2decision.get("status") == O2_STATUS
            and o2decision.get("optimized_H2_assignment_executed") is True
            and o2decision.get("capacity_relaxed") is False
            and o2decision.get("per_CV_mass_relaxed") is False
            and o2decision.get("mass_clipped_or_discarded") is False
            and o2decision.get("global_rescaling_performed") is False
            and o2decision.get("O3_authorized") is True
            and o2decision.get("R3R3R4_authorized") is False
            and o2decision.get("F5_dataset_generation_authorized") is False
            and o2decision.get("training_authorized") is False,
        )

        # ------------------------------------------------------------------------------------------
        # Load O2 optimized event state and recertify immutable assignment output.
        # ------------------------------------------------------------------------------------------
        stage = "O2_state_recertification"
        o2_state_sha256 = sha256_file(o2d / O2_STATE)
        with np.load(o2d / O2_STATE, allow_pickle=False) as z:
            required_o2_arrays = {
                "event_day",
                "physical_time_advanced_in_O2",
                "event_grid_component_mass_kg",
                "event_mapped_grid_mass_kg",
                "frozen_residual_grid_component_mass_kg",
                "event_CV_component_mass_kg",
                "E0_pair_cv_id",
                "E0_pair_flat_cell",
                "E0_parent_ownership_mass_kg",
                "E2_pair_cv_id",
                "E2_pair_flat_cell",
                "E2_pair_is_E0",
                "E2_pair_is_E1",
                "E2_pair_event_mass_kg",
                "E0_parent_continuity_target_kg",
                "E0_raw_event_EOS_target_kg",
                "parent_pressure_psi",
                "grid_pore_volume_m3",
                "reference_gas_pressure_pa",
            }
            gate("O2_state_required_arrays_present", required_o2_arrays.issubset(set(z.files)), sorted(required_o2_arrays))

            event_day = float(np.asarray(z["event_day"]).reshape(()))
            physical_time_advanced_in_o2 = bool(np.asarray(z["physical_time_advanced_in_O2"]).reshape(()))
            event_grid_mass = np.asarray(z["event_grid_component_mass_kg"], dtype=np.float64)
            event_mapped_grid = np.asarray(z["event_mapped_grid_mass_kg"], dtype=np.float64)
            frozen_residual_grid = np.asarray(z["frozen_residual_grid_component_mass_kg"], dtype=np.float64)
            event_cv_mass = np.asarray(z["event_CV_component_mass_kg"], dtype=np.float64)
            e0_cv = np.asarray(z["E0_pair_cv_id"], dtype=np.int64)
            e0_cell = np.asarray(z["E0_pair_flat_cell"], dtype=np.int64)
            e0_parent_mass = np.asarray(z["E0_parent_ownership_mass_kg"], dtype=np.float64)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            e2_is_e0 = np.asarray(z["E2_pair_is_E0"], dtype=bool)
            e2_is_e1 = np.asarray(z["E2_pair_is_E1"], dtype=bool)
            e2_mass = np.asarray(z["E2_pair_event_mass_kg"], dtype=np.float64)
            e0_parent_target = np.asarray(z["E0_parent_continuity_target_kg"], dtype=np.float64)
            e0_raw_target = np.asarray(z["E0_raw_event_EOS_target_kg"], dtype=np.float64)
            o2_parent_pressure = np.asarray(z["parent_pressure_psi"], dtype=np.float64)
            o2_grid_pv = np.asarray(z["grid_pore_volume_m3"], dtype=np.float64)
            o2_p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate(
            "O2_state_shapes_exact",
            event_grid_mass.shape == GRID
            and event_mapped_grid.shape == GRID
            and frozen_residual_grid.shape == GRID
            and event_cv_mass.shape == (NSL, NCV)
            and o2_parent_pressure.shape == GRID
            and o2_grid_pv.shape == GRID
            and e0_cv.shape == (EXPECTED_E0_PAIRS,)
            and e0_cell.shape == (EXPECTED_E0_PAIRS,)
            and e0_parent_mass.shape == (EXPECTED_E0_PAIRS,)
            and e0_parent_target.shape == (EXPECTED_E0_PAIRS,)
            and e0_raw_target.shape == (EXPECTED_E0_PAIRS,)
            and e2_cv.shape == (EXPECTED_E2_PAIRS,)
            and e2_cell.shape == (EXPECTED_E2_PAIRS,)
            and e2_is_e0.shape == (EXPECTED_E2_PAIRS,)
            and e2_is_e1.shape == (EXPECTED_E2_PAIRS,)
            and e2_mass.shape == (EXPECTED_E2_PAIRS,),
        )
        gate(
            "O2_event_identity_exact",
            abs(event_day - EVENT_DAY) <= 1e-12 and physical_time_advanced_in_o2 is False,
            {"event_day": event_day, "physical_time_advanced_in_O2": physical_time_advanced_in_o2},
        )
        gate(
            "O2_split_grid_exact",
            max_abs(event_mapped_grid + frozen_residual_grid - event_grid_mass) <= 1e-8,
            max_abs(event_mapped_grid + frozen_residual_grid - event_grid_mass),
        )

        e2_cv_reconstructed = np.bincount(e2_cv, weights=e2_mass, minlength=NCVTOTAL).reshape(NSL, NCV)
        e2_grid_reconstructed = np.bincount(e2_cell, weights=e2_mass, minlength=NCELL).reshape(GRID)
        cv_tol = max(1e-7, 1e-10 * max(float(np.max(np.abs(event_cv_mass))), 1.0))
        gate(
            "O2_E2_CV_mass_reconstructs_event_mass",
            max_abs(e2_cv_reconstructed - event_cv_mass) <= cv_tol,
            {"Linf_kg": max_abs(e2_cv_reconstructed - event_cv_mass), "tolerance_kg": cv_tol},
        )
        gate(
            "O2_E2_grid_mass_reconstructs_mapped_mass",
            max_abs(e2_grid_reconstructed - event_mapped_grid) <= 1e-8,
            max_abs(e2_grid_reconstructed - event_mapped_grid),
        )
        gate(
            "O2_global_mass_ledger_exact",
            abs(
                fsum_array(event_grid_mass)
                - fsum_array(frozen_residual_grid)
                - fsum_array(event_cv_mass)
            ) <= max(1e-5, 1e-10 * max(fsum_array(event_grid_mass), 1.0)),
            fsum_array(event_grid_mass) - fsum_array(frozen_residual_grid) - fsum_array(event_cv_mass),
        )
        gate("O2_E2_pair_mass_nonnegative", float(np.min(e2_mass)) >= -1e-10, float(np.min(e2_mass)))

        # ------------------------------------------------------------------------------------------
        # Bind the original Day365 flow epoch. O2 carries the parent pressure/PV/p_ref identities;
        # A2-E supplies the frozen spatial Corey/porosity fields and parent flow epoch for change audit.
        # ------------------------------------------------------------------------------------------
        stage = "A2E_epoch_binding"
        a2d = drive / A2E_REL
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        verify_manifest(a2d, A2E_MANIFEST)
        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}

        required_epoch = {
            "refreshed_pressure_psi",
            "pore_volume_m3",
            "reference_gas_pressure_pa",
            "streamline_xyz_m",
            "streamline_tof_s",
            "streamline_weight_m3_s",
            "streamline_face_pressure_psi",
            "xi",
            "nw",
            "no",
            "krw_max",
            "kro_max",
            "paired_porosity",
        }
        gate("A2E_required_epoch_arrays", required_epoch.issubset(set(epoch)), sorted(required_epoch))

        parent_pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        grid_pv = np.asarray(epoch["pore_volume_m3"], dtype=np.float64)
        p_ref = float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        parent_xyz = np.asarray(epoch["streamline_xyz_m"], dtype=np.float64)
        parent_tof = np.asarray(epoch["streamline_tof_s"], dtype=np.float64)
        parent_weights = np.asarray(epoch["streamline_weight_m3_s"], dtype=np.float64)
        parent_face_pressure = np.asarray(epoch["streamline_face_pressure_psi"], dtype=np.float64)
        parent_xi = np.asarray(epoch["xi"], dtype=np.float64)
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)
        grid_phi = np.asarray(epoch["paired_porosity"], dtype=np.float64)

        gate(
            "A2E_epoch_shapes_exact",
            parent_pressure.shape == GRID
            and grid_pv.shape == GRID
            and parent_xyz.shape == (NSL, NN, 3)
            and parent_tof.shape == (NSL, NN)
            and parent_weights.shape == (NSL,)
            and parent_face_pressure.shape == (NSL, NN)
            and parent_xi.shape == (NN,),
        )
        gate(
            "O2_parent_pressure_matches_A2E",
            max_abs(o2_parent_pressure - parent_pressure) <= 1e-12,
            max_abs(o2_parent_pressure - parent_pressure),
        )
        gate(
            "O2_grid_PV_matches_A2E",
            max_abs(o2_grid_pv - grid_pv) <= 1e-12,
            max_abs(o2_grid_pv - grid_pv),
        )
        gate("O2_reference_pressure_matches_A2E", abs(o2_p_ref - p_ref) <= 1e-9, abs(o2_p_ref - p_ref))

        # ------------------------------------------------------------------------------------------
        # Load exact source-authentic helpers. No O2 optimization routine is called in O3-R2.
        # ------------------------------------------------------------------------------------------
        stage = "source_module_binding"
        r3exec = load_module(root / R3EXEC, "postv16_av4_o3_r3exec")
        f4r3 = load_module(root / F4R3, "postv16_av4_o3_f4r3")
        a2e = load_module(root / A2E, "postv16_av4_o3_a2e")
        r2 = load_module(root / R2, "postv16_av4_o3_r2")
        e37 = load_module(root / E37A, "postv16_av4_o3_e37")
        sg2 = load_module(root / SG2, "postv16_av4_o3_sg2")
        sg3 = load_module(root / SG3, "postv16_av4_o3_sg3")
        sg4 = load_module(root / SG4, "postv16_av4_o3_sg4")
        sg5 = load_module(root / SG5, "postv16_av4_o3_sg5")
        sg6 = load_module(root / SG6, "postv16_av4_o3_sg6")
        sg7d = load_module(root / SG7D, "postv16_av4_o3_sg7d")
        r3r2r1 = load_module(root / R3R2R1, "postv16_av4_o3_r3r2r1")

        gate(
            "execution_helpers_present",
            hasattr(r3exec, "refresh_flow_epoch")
            and hasattr(r3exec, "rebuild_transport_epoch_fields")
            and hasattr(f4r3, "bounded_reproject")
            and hasattr(a2e, "invert_local_mass")
            and hasattr(a2e, "local_mass")
            and hasattr(r2, "gas_density_from_state"),
        )

        # Source-authentic capacity under the frozen parent pressure; recertifies O2 before refresh.
        cell_capacity = np.asarray(
            a2e.local_mass(
                r2,
                np.full(GRID, INJECTED, dtype=np.float64),
                parent_pressure,
                p_ref,
                grid_pv,
            ),
            dtype=np.float64,
        )
        grid_tol = max(1e-7, 1e-10 * max(float(np.max(np.abs(cell_capacity))), 1.0))
        sci_gate(
            "O2_event_grid_within_source_authentic_parent_capacity",
            np.isfinite(cell_capacity).all()
            and float(np.min(cell_capacity)) > 0.0
            and float(np.min(event_grid_mass)) >= -grid_tol
            and float(np.max(event_grid_mass - cell_capacity)) <= grid_tol,
            {
                "capacity_min_kg": float(np.min(cell_capacity)),
                "capacity_max_kg": float(np.max(cell_capacity)),
                "event_grid_min_kg": float(np.min(event_grid_mass)),
                "event_grid_max_capacity_excess_kg": float(np.max(event_grid_mass - cell_capacity)),
                "tolerance_kg": grid_tol,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Invert immutable O2 event Cartesian mass under the parent pressure. Zero physical time.
        # ------------------------------------------------------------------------------------------
        stage = "event_parent_pressure_mass_inversion"
        try:
            event_sg_start = a2e.invert_local_mass(
                r2,
                event_grid_mass,
                parent_pressure,
                p_ref,
                grid_pv,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(
                    "event_parent_pressure_" + str(exc.gate),
                    getattr(exc, "detail", None),
                ) from exc
            raise ScientificFail("event_parent_pressure_mass_inversion_failure", repr(exc)) from exc
        event_mass_inverted = True
        event_sat_start = BACKGROUND + np.asarray(event_sg_start, dtype=np.float64)
        sci_gate(
            "event_parent_pressure_saturation_bounds",
            np.isfinite(event_sat_start).all()
            and float(np.min(event_sat_start)) >= BACKGROUND - 1e-10
            and float(np.max(event_sat_start)) <= INJECTED + 1e-10,
            [float(np.min(event_sat_start)), float(np.max(event_sat_start))],
        )

        # ------------------------------------------------------------------------------------------
        # Exactly one same-time flow refresh.
        # ------------------------------------------------------------------------------------------
        stage = "single_same_time_event_flow_refresh"
        permeability_md = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")

        try:
            event_flow = r3exec.refresh_flow_epoch(
                label="O3R2_event_refresh",
                r3=f4r3,
                a2e=a2e,
                r2=r2,
                sg2=sg2,
                sg3=sg3,
                sg4=sg4,
                sg5=sg5,
                sg6=sg6,
                sg7d=sg7d,
                r3r2r1=r3r2r1,
                permeability_md=permeability_md,
                grid_mass=event_grid_mass,
                start_saturation=event_sat_start,
                start_pressure_psi=parent_pressure,
                p_ref_pa=p_ref,
                grid_pv=grid_pv,
                grid_nw=grid_nw,
                grid_no=grid_no,
                grid_krw=grid_krw,
                grid_kro=grid_kro,
                sci_gate=sci_gate,
            )
        except ScientificFail:
            raise
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(str(exc.gate), getattr(exc, "detail", None)) from exc
            raise ScientificFail("single_event_flow_refresh_failure", repr(exc)) from exc
        event_refresh_executed = True

        gate(
            "refreshed_flow_shapes_exact",
            np.asarray(event_flow["pressure_psi"]).shape == GRID
            and np.asarray(event_flow["saturation"]).shape == GRID
            and np.asarray(event_flow["xyz_m"]).shape == (NSL, NN, 3)
            and np.asarray(event_flow["tof_s"]).shape == (NSL, NN)
            and np.asarray(event_flow["weights_m3_s"]).shape == (NSL,)
            and np.asarray(event_flow["face_pressure_psi"]).shape == (NSL, NN)
            and np.asarray(event_flow["xi"]).shape == (NN,),
        )

        # ------------------------------------------------------------------------------------------
        # Exactly one bounded refreshed-geometry reprojection of the same immutable Cartesian mass.
        # ------------------------------------------------------------------------------------------
        stage = "refreshed_geometry_bounded_reprojection"
        try:
            event_split = f4r3.bounded_reproject(
                r2=r2,
                e37=e37,
                sg7d=sg7d,
                xyz_m=event_flow["xyz_m"],
                tof_s=event_flow["tof_s"],
                weights_m3_s=event_flow["weights_m3_s"],
                grid_mass=event_grid_mass,
                grid_pore_volume_m3=grid_pv,
                pressure_psi=event_flow["pressure_psi"],
                p_ref_pa=p_ref,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(
                    "event_reprojection_" + str(exc.gate),
                    getattr(exc, "detail", None),
                ) from exc
            raise ScientificFail("event_reprojection_failure", repr(exc)) from exc
        event_reprojection_executed = True

        sci_gate(
            "event_reprojection_zero_overloaded_CVs",
            int(event_split["overloaded_CV_count"]) == 0,
            {
                "overloaded": int(event_split["overloaded_CV_count"]),
                "max_excess_kg": float(event_split["maximum_capacity_excess_kg"]),
            },
        )
        sci_gate(
            "event_reprojection_global_mass_ledger",
            abs(float(event_split["ledger_residual_kg"]))
            <= max(1e-6, 1e-10 * max(fsum_array(event_grid_mass), 1.0)),
            float(event_split["ledger_residual_kg"]),
        )
        sci_gate(
            "event_reprojection_residual_nonnegative",
            float(np.min(event_split["residual_grid_mass"])) >= -1e-8,
            float(np.min(event_split["residual_grid_mass"])),
        )
        reconstructed_refresh_grid = (
            np.asarray(event_split["mapped_grid_mass"], dtype=np.float64)
            + np.asarray(event_split["residual_grid_mass"], dtype=np.float64)
        )
        sci_gate(
            "event_reprojection_exact_full_grid_reconstruction",
            max_abs(reconstructed_refresh_grid - event_grid_mass) <= 1e-8,
            max_abs(reconstructed_refresh_grid - event_grid_mass),
        )

        # ------------------------------------------------------------------------------------------
        # Rebuild refreshed recurrent fields. Still no physical-time advance.
        # ------------------------------------------------------------------------------------------
        stage = "refreshed_event_recurrent_state_rebuild"
        event_fields = r3exec.rebuild_transport_epoch_fields(
            r3=f4r3,
            sg7d=sg7d,
            xyz_m=event_flow["xyz_m"],
            tof_s=event_flow["tof_s"],
            xi=event_flow["xi"],
            permeability_md=permeability_md,
            grid_phi=grid_phi,
            grid_nw=grid_nw,
            grid_no=grid_no,
            grid_krw=grid_krw,
            grid_kro=grid_kro,
            pressure_nodes_psi=event_flow["face_pressure_psi"],
        )

        field_keys = [
            "permeability_nodes_md",
            "porosity_nodes",
            "nw_nodes",
            "no_nodes",
            "krw_max_nodes",
            "kro_max_nodes",
            "pressure_nodes_psi",
            "permeability_cv_md",
            "porosity_cv",
            "nw_cv",
            "no_cv",
            "krw_max_cv",
            "kro_max_cv",
        ]
        sci_gate(
            "refreshed_event_fields_finite",
            all(np.isfinite(np.asarray(event_fields[k])).all() for k in field_keys),
        )
        sci_gate(
            "refreshed_event_state_shapes",
            np.asarray(event_split["cv_mass"]).shape == (NSL, NCV)
            and np.asarray(event_split["cv_saturation"]).shape == (NSL, NCV)
            and np.asarray(event_split["cv_capacity"]).shape == (NSL, NCV)
            and np.asarray(event_split["cv_pore_volume_m3"]).shape == (NSL, NCV)
            and np.asarray(event_split["cv_pressure_mass_coeff"]).shape == (NSL, NCV),
        )

        tof_change = relative_l2(event_flow["tof_s"], parent_tof)
        pressure_change = relative_l2(event_flow["pressure_psi"], parent_pressure)
        weights_change = relative_l2(event_flow["weights_m3_s"], parent_weights)
        sci_gate(
            "single_refresh_changes_flow_epoch",
            tof_change > 1e-12 or pressure_change > 1e-12 or weights_change > 1e-12,
            {
                "TOF_relative_L2_change": tof_change,
                "pressure_relative_L2_change": pressure_change,
                "weight_relative_L2_change": weights_change,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Publish refreshed event recurrent state and STOP. No Day500 transport in O3-R2.
        # ------------------------------------------------------------------------------------------
        stage = "artifact_publication"
        refreshed_state = deterministic_npz_bytes(
            {
                "event_day": np.asarray(EVENT_DAY),
                "event_elapsed_days_from_Day365": np.asarray(EVENT_ELAPSED),
                "event_remaining_days_to_Day500": np.asarray(EVENT_REMAINING),
                "event_accepted_substeps_before_refresh": np.asarray(EVENT_SUBSTEPS),
                "physical_time_advanced_in_O3R2": np.asarray(False),
                "second_event_refresh_executed_in_O3R2": np.asarray(False),
                "O2_event_grid_component_mass_kg": event_grid_mass,
                "O2_event_mapped_grid_mass_kg": event_mapped_grid,
                "O2_frozen_residual_grid_component_mass_kg": frozen_residual_grid,
                "O2_event_CV_component_mass_kg": event_cv_mass,
                "event_parent_pressure_saturation": event_sat_start,
                "refreshed_pressure_psi": np.asarray(event_flow["pressure_psi"]),
                "refreshed_saturation": np.asarray(event_flow["saturation"]),
                "refreshed_streamline_xyz_m": np.asarray(event_flow["xyz_m"]),
                "refreshed_streamline_tof_s": np.asarray(event_flow["tof_s"]),
                "refreshed_streamline_weight_m3_s": np.asarray(event_flow["weights_m3_s"]),
                "refreshed_streamline_face_pressure_psi": np.asarray(event_flow["face_pressure_psi"]),
                "refreshed_xi": np.asarray(event_flow["xi"]),
                "refreshed_CV_component_mass_kg": np.asarray(event_split["cv_mass"]),
                "refreshed_CV_saturation": np.asarray(event_split["cv_saturation"]),
                "refreshed_CV_capacity_kg": np.asarray(event_split["cv_capacity"]),
                "refreshed_CV_pore_volume_m3": np.asarray(event_split["cv_pore_volume_m3"]),
                "refreshed_CV_pressure_mass_coeff": np.asarray(event_split["cv_pressure_mass_coeff"]),
                "refreshed_mapped_grid_mass_kg": np.asarray(event_split["mapped_grid_mass"]),
                "refreshed_residual_grid_mass_kg": np.asarray(event_split["residual_grid_mass"]),
                "permeability_cv_md": np.asarray(event_fields["permeability_cv_md"]),
                "porosity_cv": np.asarray(event_fields["porosity_cv"]),
                "nw_cv": np.asarray(event_fields["nw_cv"]),
                "no_cv": np.asarray(event_fields["no_cv"]),
                "krw_max_cv": np.asarray(event_fields["krw_max_cv"]),
                "kro_max_cv": np.asarray(event_fields["kro_max_cv"]),
            }
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "technical_authority_repair_only": True,
            "repaired_authority": "O2_manifest_payload_cardinality",
            "inherited_O3R1_SG3_blob_repair_bound": True,
            "repaired_SG3_blob": SG3_BLOB,
            "repaired_O2_manifest_cardinality": 8,
            "prior_O3R1_block_commit": PARENT_O3R1_BLOCK_COMMIT,
            "prior_O3_block_commit": PRIOR_O3_BLOCK_COMMIT,
            "event_day": EVENT_DAY,
            "event_elapsed_days_from_Day365": EVENT_ELAPSED,
            "event_remaining_days_to_Day500": EVENT_REMAINING,
            "O2_status_bound": O2_STATUS,
            "O2_parent_state_sha256": o2_state_sha256,
            "O2_optimized_H2_assignment_reexecuted_in_O3R2": False,
            "O2_event_grid_mass_kg": fsum_array(event_grid_mass),
            "O2_event_CV_mass_kg": fsum_array(event_cv_mass),
            "O2_frozen_residual_mass_kg": fsum_array(frozen_residual_grid),
            "event_parent_pressure_mass_inversion_executed": True,
            "same_time_flow_refresh_executed": True,
            "bounded_refreshed_geometry_reprojection_executed": True,
            "TOF_relative_L2_change": tof_change,
            "pressure_relative_L2_change": pressure_change,
            "weight_relative_L2_change": weights_change,
            "reprojection_overloaded_CV_count": int(event_split["overloaded_CV_count"]),
            "reprojection_maximum_capacity_excess_kg": float(event_split["maximum_capacity_excess_kg"]),
            "reprojection_ledger_residual_kg": float(event_split["ledger_residual_kg"]),
            "physical_time_advanced": False,
            "Day500_continuation_executed": False,
            "second_event_refresh_executed": False,
            "R3R3R4_authorized": True,
            "F5_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
        }

        refresh_audit = {
            "milestone": MILESTONE,
            "O2_input_state": O2_STATE,
            "O2_input_state_sha256": o2_state_sha256,
            "O2_assignment_semantics_changed": False,
            "assignment_solver_called_in_O3R2": False,
            "support_domain_changed_in_O3R2": False,
            "mass_clipped_or_discarded": False,
            "global_mass_rescaling_performed": False,
            "event_mass_inversion": {
                "executed": True,
                "pressure_authority": "A2-E parent pressure bound exactly to O2 parent_pressure_psi",
                "saturation_min": float(np.min(event_sat_start)),
                "saturation_max": float(np.max(event_sat_start)),
            },
            "same_time_refresh": {
                "executed_exactly_once": True,
                "TOF_relative_L2_change": tof_change,
                "pressure_relative_L2_change": pressure_change,
                "weight_relative_L2_change": weights_change,
            },
            "bounded_reprojection": {
                "executed_exactly_once": True,
                "overloaded_CV_count": int(event_split["overloaded_CV_count"]),
                "maximum_capacity_excess_kg": float(event_split["maximum_capacity_excess_kg"]),
                "ledger_residual_kg": float(event_split["ledger_residual_kg"]),
                "grid_reconstruction_Linf_kg": max_abs(reconstructed_refresh_grid - event_grid_mass),
            },
            "physical_time_advanced": False,
            "Day500_transport_started": False,
            "second_event_refresh_executed": False,
        }

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R4",
            "name": "Refreshed H2 Event-Epoch Day413.78677770818403 to Day500 Controlled Continuation Execution",
            "authorized": True,
            "execution": True,
            "required_O3R2_status": STATUS_PASS,
            "required_parent_state": "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Refreshed_Event_Recurrent_State.npz",
            "O2_parent_state_sha256": o2_state_sha256,
            "parent_event_day": EVENT_DAY,
            "remaining_days": EVENT_REMAINING,
            "single_event_refresh_already_consumed": True,
            "second_event_refresh_authorized": False,
            "scope": [
                "resume remaining 86.21322229181597 days from the O3-R2 refreshed event epoch",
                "use unchanged raw F4 internal transport operator",
                "use unchanged F4-R2 terminal producer pass-through",
                "if another interior conflict occurs preserve SCIENTIFIC FAIL with no second refresh",
                "if Day500 is reached execute the original same-time Day500 flow refresh and bounded split-state reprojection certification",
            ],
            "not_authorized": [
                "second event refresh before Day500",
                "support radius >2",
                "vertical support",
                "H2+V1 fallback",
                "F5 dataset generation",
                "training",
                "checkpoint inference",
                "locked OOD",
                "A3-E2",
                "general dynamic AV4 deployment",
                "CMG",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "O2_optimized_H2_assignment_bound_immutably": True,
            "O2_assignment_reexecuted": False,
            "support_domain_changed": False,
            "event_CV_mass_changed_before_refresh": False,
            "event_Cartesian_mass_changed_before_refresh": False,
            "capacity_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "single_same_time_flow_refresh_executed": True,
            "bounded_refreshed_geometry_reprojection_executed": True,
            "physical_time_advanced": False,
            "Day500_continuation_started": False,
            "second_event_refresh_executed": False,
            "R3R3R4_authorized": True,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Summary.json": json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Flow_Refresh_and_Reprojection_Audit.json": json_bytes(refresh_audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Refreshed_Event_Recurrent_State.npz": refreshed_state,
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_R3R3R4_Handoff_Contract.json": json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }
        immutable_publish(out, files)

        manifest_rows = []
        manifest_name = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Artifact_Manifest.csv"
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != manifest_name:
                manifest_rows.append(
                    {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
                )
        immutable_publish(out, {manifest_name: csv_bytes(manifest_rows)})

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R2: OPTIMIZED H2 EVENT MAPBACK "
            "+ SINGLE SAME-TIME FLOW REFRESH / BOUNDED REPROJECTION PASS"
        )
        print("=" * 214)
        print("Event day                                :", EVENT_DAY)
        print("O2 assignment reexecuted                 : False")
        print("O2 event grid mass kg                    :", fsum_array(event_grid_mass))
        print("O2 event CV mass kg                      :", fsum_array(event_cv_mass))
        print("Same-time event flow refresh             : EXECUTED ONCE")
        print("Refreshed-geometry reprojection          : PASS")
        print("Reprojection overloaded CVs              :", int(event_split["overloaded_CV_count"]))
        print("Reprojection max capacity excess kg      :", float(event_split["maximum_capacity_excess_kg"]))
        print("Reprojection ledger residual kg          :", float(event_split["ledger_residual_kg"]))
        print("TOF relative L2 change                   :", tof_change)
        print("Pressure relative L2 change              :", pressure_change)
        print("Weight relative L2 change                :", weights_change)
        print("Physical-time advance                    : False")
        print("Day500 continuation                      : NOT STARTED")
        print("Second event refresh                     : NOT EXECUTED / NOT AUTHORIZED")
        print("POSTV16-AV4-F4-R3-R3-R4                 : AUTHORIZED")
        print("F5 / training / A3-E2 / general AV4      : NOT AUTHORIZED")
        print("=" * 214)
        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "O2_optimized_H2_assignment_preserved": True,
            "O2_assignment_reexecuted": False,
            "event_mass_inversion_executed": event_mass_inverted,
            "event_refresh_executed": event_refresh_executed,
            "event_reprojection_executed": event_reprojection_executed,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "physical_time_advanced": False,
            "second_event_refresh_authorized": False,
            "automatic_fallback_authorized": False,
            "automatic_rerun_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = failed / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = failed / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Scientific_Fail_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: SCIENTIFIC FAIL")
        print("=" * 214)
        print("Stage    :", stage)
        print("Gate     :", exc.gate)
        print("Detail   :", exc.detail)
        print("O2 OPTIMIZED H2 ASSIGNMENT REMAINS IMMUTABLE AND VALID.")
        print("NO SUPPORT EXPANSION, SECOND REFRESH, ALTERNATE REPAIR, OR AUTOMATIC RERUN AUTHORIZED.")
        print("R3-R3-R4 / F5 / training: NOT AUTHORIZED")
        print("=" * 214)
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "O2_optimized_H2_assignment_preserved": True,
            "O2_assignment_reexecuted": False,
            "event_mass_inversion_executed": event_mass_inverted,
            "event_refresh_executed": event_refresh_executed,
            "event_reprojection_executed": event_reprojection_executed,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Blocked_Report_"
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
        print("O2 OPTIMIZED H2 ASSIGNMENT REMAINS IMMUTABLE AND VALID.")
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        print("NO R3-R3-R4 / F5 / TRAINING AUTHORIZED.")
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
