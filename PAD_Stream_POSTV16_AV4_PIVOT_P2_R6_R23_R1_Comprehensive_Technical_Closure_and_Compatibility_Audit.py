#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV4-PIVOT-P2-R6-R23-R1"
NAME = "R23 Technical Closure + Day375 Regenerated Geometry / Accepted Transport Compatibility Audit"

PASS = (
    "AV4PIVOTP2R6R23R1_TECHNICAL_CLOSURE_DAY375_REGENERATED_GEOMETRY_ACCEPTED_TRANSPORT_"
    "COMPATIBILITY_AUDIT_PASS_NO_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R23R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "08088a899a77ea607591bd94306a7f0cf478146d"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

GRID = (15, 50, 50)
NCELL = 37500
NSL = 1078
NN = 201
NCV = 200
NCVT = NSL * NCV
DAY = 375.0
DAY_TO_S = 86400.0

MASS_TOL = 1.0e-7
LEDGER_TOL = 1.0e-6
CAPACITY_TOL = 1.0e-7

# --------------------------------------------------------------------------------------------------
# R22 regenerated flow geometry.
# --------------------------------------------------------------------------------------------------

R22_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R22_"
    "Controlled_Day375_AcceptedState_Darcy_Pollock_TOF_Regeneration"
)
R22_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R22_Summary.json"
R22_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R22_Decision_Contract.json"
R22_EPOCH = "POSTV16_AV4_PIVOT_P2_R6_R22_Day375_Regenerated_Darcy_Pollock_TOF_Epoch.npz"
R22_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R22_Artifact_Manifest.csv"
R22_STATUS = (
    "AV4PIVOTP2R6R22_DAY375_ACCEPTED_STATE_DARCY_POLLOCK_TOF_"
    "REGENERATION_PASS_NO_TRANSPORT_MUTATION_NO_TIME_ADVANCE"
)
R22_EPOCH_SHA256 = "7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"

# --------------------------------------------------------------------------------------------------
# Accepted transport / pressure authority.
# --------------------------------------------------------------------------------------------------

R19_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Day375_Remaining_NonExecuted_R7_"
    "Group_Coupled_Global_CVConservative_Reconciliation_Execution"
)
R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"

R20_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"
R20_STATUS = "AV4PIVOTP2R6R20_DAY375_GLOBAL_CLOSURE_AND_ACCEPTANCE_AUDIT_PASS_ACCEPTED_STATE"
R20_ACCEPTED_SHA256 = "e209adb5a169008698db9acb24e5cade82df3f6991b5174515d5957901bceb67"

CLOSURE_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
CLOSURE_REL = BASE / (
    CLOSURE_TOKEN
    + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
PRESSURE_EPOCH = f"{CLOSURE_TOKEN}_Accepted_Day375_Pressure_Epoch.npz"
CLOSURE_MANIFEST = f"{CLOSURE_TOKEN}_Artifact_Manifest.csv"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

# --------------------------------------------------------------------------------------------------
# Old Day365 refreshed geometry and split-state semantics.
# --------------------------------------------------------------------------------------------------

A2E_REL = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

F1R2_REL = BASE / "POSTV16_AV4_F1_R2_Restart_State_and_Conservative_Parent_Projection_Freeze"
F1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F1_R2_Summary.json"
F1R2_RESTART_STATE = "POSTV16_AV4_F1_R2_Restart_State_Authority_Contract.json"
F1R2_PROJECTION = "POSTV16_AV4_F1_R2_Conservative_Grid_to_Streamline_Projection_Protocol.json"
F1R2_RESIDUAL = "POSTV16_AV4_F1_R2_Residual_Grid_State_Sidecar_Contract.json"
F1R2_DECISION = "POSTV16_AV4_F1_R2_Decision_Contract.json"
F1R2_MANIFEST = "POSTV16_AV4_F1_R2_Artifact_Manifest.csv"
F1R2_STATUS = (
    "AV4F1R2_F1R1_TECHNICAL_CLOSURE_BOUND_E1R2_STRUCTURAL_RESTART_"
    "INCOMPATIBILITY_BOUND_RESTART_STATE_REPRESENTATION_CONSERVATIVE_"
    "SPLIT_PARENT_PROJECTION_AND_TEMPORAL_SEMANTICS_PROSPECTIVELY_"
    "FROZEN_NO_PROJECTION_EXECUTION"
)


R23_ORIGINAL_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R23_"
    "Day375_RegeneratedGeometry_AcceptedTransport_Compatibility_Audit.py"
)
R23_ORIGINAL_BLOB = "e915ca6c6b2005506c485223d6f460166965cc09"

R23_BLOCK_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R23_BLOCKED"
R23_BLOCK = "POSTV16_AV4_PIVOT_P2_R6_R23_Blocked_Report.json"
R23_BLOCK_STATUS = "AV4PIVOTP2R6R23_TECHNICAL_OR_AUTHORITY_BLOCK"
R23_BLOCK_STAGE = "F1R2_split_state_semantics"
R23_BLOCK_EXCEPTION = "GateError('F1R2_cartesian_mass_is_primary_recurrent_state')"

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

R22_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R22_"
    "Controlled_Day375_AcceptedState_Darcy_Pollock_TOF_Regeneration.py"
)
R22_RUNNER_BLOB = "fe6b5cff2e658fb1ab6414335c407de4286c278b"

R19_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_"
    "Controlled_Remaining_Group_Coupled_Global_Reconciliation_Execution.py"
)
R19_BLOB = "2626e4a08660a907752be5aca70d29f69dd2a71e"

R20_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Global_Closure_and_Acceptance_Audit.py"
R20_BLOB = "3f872ed6a5cf2e8b4cb15f0c6f2fdeea99565d53"

F1R2_RUNNER = "PAD_Stream_POSTV16_AV4_F1_R2_Corrected_Restart_State_and_Conservative_Parent_Projection_Freeze.py"
F1R2_BLOB = "51f86f3591bf66148ef468b304c18fb4fc668e77"

A2E_RUNNER = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R23_ORIGINAL_RUNNER: R23_ORIGINAL_BLOB,
    R22_RUNNER: R22_RUNNER_BLOB,
    R19_RUNNER: R19_BLOB,
    R20_RUNNER: R20_BLOB,
    F1R2_RUNNER: F1R2_BLOB,
    A2E_RUNNER: A2E_BLOB,
    SG7D: SG7D_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Output.
# --------------------------------------------------------------------------------------------------

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R23_R1"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Technical_Closure_and_Day375_RegeneratedGeometry_AcceptedTransport_Compatibility_Audit"
)
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
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


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    rows = csvr(directory / filename)
    out: dict[str, str] = {}
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def edge_keys(cv: np.ndarray, cell: np.ndarray) -> np.ndarray:
    cv = np.asarray(cv, dtype=np.int64).reshape(-1)
    cell = np.asarray(cell, dtype=np.int64).reshape(-1)
    return np.unique(cv * NCELL + cell)


def operator_edge_keys(op: dict[str, np.ndarray]) -> np.ndarray:
    stream = np.asarray(op["streamline"], dtype=np.int64).reshape(-1)
    node = np.asarray(op["node"], dtype=np.int64).reshape(-1)
    cell = np.asarray(op["flat_cell"], dtype=np.int64).reshape(-1)
    cv = stream * NCV + node
    return edge_keys(cv, cell)


def normalized_transpose_projection(
    grid_mass: np.ndarray,
    op: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    gm = np.asarray(grid_mass, dtype=np.float64).reshape(-1)
    stream = np.asarray(op["streamline"], dtype=np.int64).reshape(-1)
    node = np.asarray(op["node"], dtype=np.int64).reshape(-1)
    cell = np.asarray(op["flat_cell"], dtype=np.int64).reshape(-1)
    pv = np.asarray(op["pv_m3"], dtype=np.float64).reshape(-1)

    if not (len(stream) == len(node) == len(cell) == len(pv)):
        raise GateError("operator_parallel_array_length_mismatch")
    if np.any(node < 0) or np.any(node >= NCV):
        raise GateError("operator_node_outside_CV_interval")
    if np.any(cell < 0) or np.any(cell >= NCELL):
        raise GateError("operator_cell_out_of_bounds")
    if np.any(pv <= 0.0) or not np.isfinite(pv).all():
        raise GateError("operator_nonpositive_or_nonfinite_pv")

    den = np.bincount(cell, weights=pv, minlength=NCELL)
    if np.any(den[cell] <= 0.0):
        raise GateError("operator_zero_cell_denominator")

    sub_mass = gm[cell] * pv / den[cell]
    cv = stream * NCV + node
    cv_mass = np.bincount(cv, weights=sub_mass, minlength=NCVT).reshape(NSL, NCV)

    s0 = np.unique(cell)
    residual = gm.copy()
    residual[s0] = 0.0
    residual = residual.reshape(GRID)

    s0_mass = float(np.sum(gm[s0]))
    cv_total = float(np.sum(cv_mass))
    residual_total = float(np.sum(residual))
    total = float(np.sum(gm))
    ledger = cv_total + residual_total - total

    return cv_mass, residual, {
        "S0_cell_count": int(len(s0)),
        "S0_mass_kg": s0_mass,
        "S0_mass_fraction": s0_mass / max(total, 1.0e-30),
        "projected_CV_mass_kg": cv_total,
        "residual_grid_mass_kg": residual_total,
        "residual_grid_mass_fraction": residual_total / max(total, 1.0e-30),
        "global_split_state_ledger_residual_kg": ledger,
    }


def weighted_edge_membership_fraction(
    cv: np.ndarray,
    cell: np.ndarray,
    mass: np.ndarray,
    support_keys: np.ndarray,
) -> tuple[float, float, int, int]:
    cv = np.asarray(cv, dtype=np.int64).reshape(-1)
    cell = np.asarray(cell, dtype=np.int64).reshape(-1)
    mass = np.asarray(mass, dtype=np.float64).reshape(-1)
    keys = cv * NCELL + cell
    on = np.isin(keys, support_keys)
    abs_mass = np.abs(mass)
    total = float(np.sum(abs_mass))
    on_mass = float(np.sum(abs_mass[on]))
    frac = on_mass / total if total > 0.0 else 1.0
    return frac, on_mass, int(np.count_nonzero(on)), int(len(on))


def selftest() -> None:
    assert NCVT == 1078 * 200
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert BLOCK_REL.name == OUT_TOKEN + "_BLOCKED"

    gm = np.asarray([2.0, 3.0], dtype=float)
    op = {
        "streamline": np.asarray([0, 0, 0], dtype=np.int64),
        "node": np.asarray([0, 0, 1], dtype=np.int64),
        "flat_cell": np.asarray([0, 0, 1], dtype=np.int64),
        "pv_m3": np.asarray([1.0, 3.0, 2.0], dtype=float),
    }
    # Adapt toy globals by checking the partition algebra directly.
    den = np.bincount(op["flat_cell"], weights=op["pv_m3"], minlength=2)
    sub = gm[op["flat_cell"]] * op["pv_m3"] / den[op["flat_cell"]]
    assert abs(float(np.sum(sub)) - float(np.sum(gm))) < 1e-12

    print("POSTV16 AV4 PIVOT P2-R6-R23 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL

    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        # ------------------------------------------------------------------------------------------
        # Immutable one-shot firewall.
        # ------------------------------------------------------------------------------------------
        stage = "preexisting_state_firewall"

        pass_summary = out / f"PAD_Stream_{OUT_TOKEN}_Summary.json"
        block_report = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"

        gate("no_preexisting_R23R1_PASS", not pass_summary.exists(), str(pass_summary))
        gate("no_preexisting_R23R1_BLOCK", not block_report.exists(), str(block_report))

        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R23_BLOCK_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Immutable R23 BLOCK authority.
        # ------------------------------------------------------------------------------------------
        stage = "R23_BLOCK_authority"

        r23_block_path = drive / R23_BLOCK_REL / R23_BLOCK
        gate("R23_BLOCK_present", r23_block_path.is_file(), str(r23_block_path))
        r23_block_sha = sha(r23_block_path)
        b23 = js(r23_block_path)
        gate("R23_BLOCK_status_exact", b23.get("status") == R23_BLOCK_STATUS, b23.get("status"))
        gate("R23_BLOCK_stage_exact", b23.get("failed_stage") == R23_BLOCK_STAGE, b23.get("failed_stage"))
        gate("R23_BLOCK_exception_exact", b23.get("exception") == R23_BLOCK_EXCEPTION, b23.get("exception"))
        gate("R23_BLOCK_transport_preserved", b23.get("accepted_transport_state_preserved") is True)
        gate("R23_BLOCK_pressure_preserved", b23.get("accepted_pressure_epoch_preserved") is True)
        gate("R23_BLOCK_R22_preserved", b23.get("R22_flow_epoch_preserved") is True)
        gate("R23_BLOCK_no_state_mutation", b23.get("state_mutation_executed") is False)
        gate("R23_BLOCK_no_mapback", b23.get("mapback_executed") is False)
        gate("R23_BLOCK_no_time_advance", b23.get("physical_time_advance_executed") is False)
        gate("R23_BLOCK_no_automatic_rerun", b23.get("automatic_rerun_authorized") is False)

        # ------------------------------------------------------------------------------------------
        # R22 authority.
        # ------------------------------------------------------------------------------------------
        stage = "R22_authority"

        r22 = drive / R22_REL
        m22 = manifest(r22, R22_MANIFEST)
        s22 = js(r22 / R22_SUMMARY)
        d22 = js(r22 / R22_DECISION)
        r22_epoch_path = r22 / R22_EPOCH

        gate("R22_status_exact", s22.get("status") == R22_STATUS, s22.get("status"))
        gate("R22_epoch_SHA_summary_exact", s22.get("regenerated_flow_epoch_sha256") == R22_EPOCH_SHA256)
        gate("R22_epoch_manifest_SHA_exact", m22.get(R22_EPOCH) == R22_EPOCH_SHA256)
        gate("R22_epoch_file_SHA_exact", sha(r22_epoch_path) == R22_EPOCH_SHA256, sha(r22_epoch_path))
        gate("R23_authorized", d22.get("P2_R6_R23_authorized") is True)
        gate("R23_diagnostic_only", d22.get("P2_R6_R23_design_or_diagnostic_only") is True)
        gate("R23_must_bind_R22_epoch", d22.get("P2_R6_R23_must_bind_R22_flow_epoch_SHA") is True)
        gate("R23_bound_R22_epoch_SHA_exact", d22.get("P2_R6_R23_R22_flow_epoch_sha256") == R22_EPOCH_SHA256)
        gate("R22_transport_mutation_forbidden", d22.get("transport_state_mutation_authorized") is False)
        gate("R22_mapback_forbidden", d22.get("mapback_execution_authorized") is False)
        gate("R22_time_advance_forbidden", d22.get("physical_time_advance_authorized") is False)

        # ------------------------------------------------------------------------------------------
        # R20 accepted transport + R19 state authority.
        # ------------------------------------------------------------------------------------------
        stage = "accepted_transport_authority"

        r20 = drive / R20_REL
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)

        gate("R20_status_exact", s20.get("status") == R20_STATUS, s20.get("status"))
        gate("R20_state_accepted", a20.get("accepted_Day375_state") is True)
        gate("R20_accepted_SHA_exact", a20.get("accepted_Day375_state_sha256") == R20_ACCEPTED_SHA256)

        r19 = drive / R19_REL
        m19 = manifest(r19, R19_MANIFEST)
        r19_state_path = r19 / R19_STATE
        gate("R19_state_manifest_present", R19_STATE in m19)
        gate("R19_state_SHA_exact", sha(r19_state_path) == R20_ACCEPTED_SHA256, sha(r19_state_path))

        with np.load(r19_state_path, allow_pickle=False) as z:
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            accepted_cv_mass = np.asarray(z["preserved_CV_mass_kg"], dtype=float).reshape(NSL, NCV)
            r19_grid_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(GRID)
            state_day = float(np.asarray(z["state_day"]).reshape(()))

        gate("R19_state_day_375", state_day == DAY, state_day)
        gate("accepted_CV_shape_exact", accepted_cv_mass.shape == (NSL, NCV))
        gate("R19_grid_shape_exact", r19_grid_mass.shape == GRID)

        # ------------------------------------------------------------------------------------------
        # Pressure-compatible accepted Day375 grid mass and pressure sidecar.
        # ------------------------------------------------------------------------------------------
        stage = "accepted_pressure_compatible_state_authority"

        closure = drive / CLOSURE_REL
        mc = manifest(closure, CLOSURE_MANIFEST)
        p_epoch_path = closure / PRESSURE_EPOCH
        gate("pressure_epoch_manifest_SHA_exact", mc.get(PRESSURE_EPOCH) == PRESSURE_EPOCH_SHA256)
        gate("pressure_epoch_file_SHA_exact", sha(p_epoch_path) == PRESSURE_EPOCH_SHA256)

        with np.load(p_epoch_path, allow_pickle=False) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            pressure_grid_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            pressure_sidecar_cv = np.asarray(z["pressure_reconciliation_sidecar_cv"], dtype=np.int64).reshape(-1)
            pressure_sidecar_cell = np.asarray(z["pressure_reconciliation_sidecar_cell"], dtype=np.int64).reshape(-1)
            pressure_sidecar_mass = np.asarray(z["pressure_reconciliation_sidecar_mass_kg"], dtype=np.float64).reshape(-1)

        gate("pressure_shape_exact", pressure.shape == GRID)
        gate("pressure_compatible_grid_mass_shape_exact", pressure_grid_mass.shape == GRID)
        gate(
            "pressure_reconciliation_sidecar_lengths_exact",
            len(pressure_sidecar_cv) == len(pressure_sidecar_cell) == len(pressure_sidecar_mass),
        )

        per_cv_sidecar = np.bincount(
            pressure_sidecar_cv,
            weights=pressure_sidecar_mass,
            minlength=NCVT,
        )
        gate("pressure_sidecar_per_CV_zero_sum", float(np.max(np.abs(per_cv_sidecar))) <= 1e-10, float(np.max(np.abs(per_cv_sidecar))))
        gate("pressure_sidecar_global_zero_sum", abs(float(np.sum(pressure_sidecar_mass))) <= 1e-10, float(np.sum(pressure_sidecar_mass)))
        gate(
            "pressure_compatible_grid_global_mass_matches_R19",
            abs(float(np.sum(pressure_grid_mass) - np.sum(r19_grid_mass))) <= MASS_TOL,
            float(np.sum(pressure_grid_mass) - np.sum(r19_grid_mass)),
        )

        # ------------------------------------------------------------------------------------------
        # F1-R2 split-state semantics.
        # ------------------------------------------------------------------------------------------
        stage = "F1R2_split_state_semantics"

        f1 = drive / F1R2_REL
        manifest(f1, F1R2_MANIFEST)
        sf1 = js(f1 / F1R2_SUMMARY)
        rsf1 = js(f1 / F1R2_RESTART_STATE)
        pf1 = js(f1 / F1R2_PROJECTION)
        rf1 = js(f1 / F1R2_RESIDUAL)
        df1 = js(f1 / F1R2_DECISION)

        gate("F1R2_status_exact", sf1.get("status") == F1R2_STATUS, sf1.get("status"))
        gate(
            "F1R2_cartesian_mass_is_primary_recurrent_state",
            rsf1.get("recurrent_state_principle")
            == (
                "Cartesian component mass is the authoritative global recurrent physical state. "
                "Streamline control-volume mass is a conservative transport-coordinate representation "
                "derived from that state at each refreshed-flow epoch."
            ),
            rsf1.get("recurrent_state_principle"),
        )
        gate(
            "F1R2_parent_mass_role_exact",
            rsf1.get("authoritative_parent_component_mass", {}).get("role")
            == (
                "primary conserved recurrent state; never reconstructed from saturation "
                "when exact A2-E cellwise component mass is available"
            ),
        )
        gate(
            "F1R2_geometry_shape_contract_exact",
            rsf1.get("refreshed_flow_geometry", {}).get("streamlines") == NSL
            and rsf1.get("refreshed_flow_geometry", {}).get("nodes") == NN
            and rsf1.get("refreshed_flow_geometry", {}).get("transport_control_volumes") == NCV,
            rsf1.get("refreshed_flow_geometry"),
        )
        gate(
            "F1R2_normalized_transpose_frozen",
            pf1.get("name") == "Exact-support normalized-transpose mass projection with residual grid sidecar"
            and pf1.get("normalized_transpose", {}).get("cell_denominator") == "W_c = sum_{q: c(q)=c} PV_q"
            and pf1.get("normalized_transpose", {}).get("subsegment_mass_assignment")
                == "m_q = M_parent[c(q)] * PV_q / W_c"
            and pf1.get("normalized_transpose", {}).get("control_volume_mass")
                == "M_cv[r] = sum_{q: r(q)=r} m_q",
        )
        gate(
            "F1R2_exact_support_definition_bound",
            pf1.get("exact_support_S0", {}).get("definition")
            == "unique Cartesian flat_cell indices present in the refreshed SG7D subsegment operator",
        )
        gate(
            "F1R2_residual_grid_ledger_bound",
            pf1.get("residual_grid_sidecar", {}).get("global_ledger")
            == "sum(M_cv) + sum(R_grid) = sum(M_parent_grid)",
        )
        gate(
            "F1R2_reverse_H1_S0_forbidden",
            "no reverse H1->S0 physical transport" in pf1.get("prohibitions", [])
            and pf1.get("residual_grid_sidecar", {}).get("H1_policy")
                == (
                    "H1/off-streamline mass remains exact grid-residual mass; it is not "
                    "reverse-moved through forbidden H1->S0 arcs"
                ),
        )
        gate("F1R2_projection_was_not_execution", pf1.get("execution_in_F1") is False)
        gate(
            "F1R2_CV_capacity_check_required",
            pf1.get("CV_saturation_recovery_for_F2", {}).get("capacity_check_required") is True
            and pf1.get("CV_saturation_recovery_for_F2", {}).get("authority")
                == "E37A invert_cv_mass_to_saturation",
        )
        gate("F1R2_split_state_contract_frozen", df1.get("split_restart_state_contract_frozen") is True)
        gate("F1R2_normalized_transpose_decision_frozen", df1.get("normalized_transpose_projection_frozen") is True)
        gate("F1R2_residual_grid_sidecar_decision_frozen", df1.get("residual_grid_sidecar_frozen") is True)
        gate(
            "F1R2_residual_grid_state_block_present",
            any(
                x.get("name") == "grid_residual_component_mass"
                and x.get("shape") == list(GRID)
                for x in rf1.get("state_blocks", [])
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Load old Day365 and new Day375 geometry.
        # ------------------------------------------------------------------------------------------
        stage = "old_new_geometry_binding"

        a2e = drive / A2E_REL
        m2e = manifest(a2e, A2E_MANIFEST)
        old_epoch_path = a2e / A2E_EPOCH
        gate("A2E_epoch_manifest_present", A2E_EPOCH in m2e)

        with np.load(old_epoch_path, allow_pickle=False) as z:
            old_xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            old_tof = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            old_weight = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            old_xi = np.asarray(z["xi"], dtype=np.float64)
            old_producer = np.asarray(z["producer_labels"]).astype("U32")

        with np.load(r22_epoch_path, allow_pickle=False) as z:
            new_xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            new_tof = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            new_weight = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            new_xi = np.asarray(z["xi"], dtype=np.float64)
            new_producer = np.asarray(z["producer_labels"]).astype("U32")
            new_streamline_id = np.asarray(z["streamline_id"], dtype=np.int64)

        gate("old_geometry_shape_exact", old_xyz.shape == (NSL, NN, 3) and old_tof.shape == (NSL, NN))
        gate("new_geometry_shape_exact", new_xyz.shape == (NSL, NN, 3) and new_tof.shape == (NSL, NN))
        gate("old_new_xi_exact", np.array_equal(old_xi, new_xi) and new_xi.shape == (NN,))
        gate("new_streamline_ids_exact_seed_order", np.array_equal(new_streamline_id, np.arange(NSL, dtype=np.int64)))

        seed_position_max_abs_m = float(np.max(np.abs(old_xyz[:, 0, :] - new_xyz[:, 0, :])))
        producer_identity_count = int(np.count_nonzero(old_producer == new_producer))
        producer_changed_count = int(NSL - producer_identity_count)
        producer_identity_fraction = float(producer_identity_count / NSL)

        seed_position_identity_exact = bool(seed_position_max_abs_m <= 1e-12)

        node_displacement = np.linalg.norm(new_xyz - old_xyz, axis=2)
        geometry_changed = bool(float(np.max(node_displacement)) > 1e-10)
        tof_endpoint_rel = np.abs(new_tof[:, -1] - old_tof[:, -1]) / np.maximum(np.abs(old_tof[:, -1]), 1e-30)

        # ------------------------------------------------------------------------------------------
        # Rebuild exact old/new SG7D geometry support read-only.
        # ------------------------------------------------------------------------------------------
        stage = "read_only_SG7D_support_rebuild"

        sg7d = mod(root / SG7D, "r23_sg7d")

        old_op = sg7d.build_subsegment_operator(
            old_xyz,
            old_tof / DAY_TO_S,
            old_weight * DAY_TO_S,
        )
        new_op = sg7d.build_subsegment_operator(
            new_xyz,
            new_tof / DAY_TO_S,
            new_weight * DAY_TO_S,
        )

        gate(
            "old_operator_finite_positive",
            len(old_op["pv_m3"]) > 0
            and np.isfinite(old_op["pv_m3"]).all()
            and np.all(np.asarray(old_op["pv_m3"]) > 0.0),
        )
        gate(
            "new_operator_finite_positive",
            len(new_op["pv_m3"]) > 0
            and np.isfinite(new_op["pv_m3"]).all()
            and np.all(np.asarray(new_op["pv_m3"]) > 0.0),
        )

        old_support = operator_edge_keys(old_op)
        new_support = operator_edge_keys(new_op)
        common_support = np.intersect1d(old_support, new_support, assume_unique=True)

        old_support_retained_fraction = float(len(common_support) / max(len(old_support), 1))
        new_support_inherited_fraction = float(len(common_support) / max(len(new_support), 1))
        support_jaccard = float(
            len(common_support)
            / max(len(old_support) + len(new_support) - len(common_support), 1)
        )

        # Exact per-CV support-change count from the support symmetric difference.
        # A CV changed iff at least one (CV,cell) edge was added or removed.
        support_symmetric_difference = np.setxor1d(
            old_support,
            new_support,
            assume_unique=True,
        )
        changed_cv_ids = np.unique(
            (support_symmetric_difference // NCELL).astype(np.int64)
        )
        changed_cv_count = int(len(changed_cv_ids))

        # ------------------------------------------------------------------------------------------
        # Accepted explicit CV-cell bookkeeping vs R22 exact support.
        # ------------------------------------------------------------------------------------------
        stage = "accepted_CV_cell_support_compatibility"

        explicit_cv = np.concatenate([pair_cv, halo_cv, pressure_sidecar_cv])
        explicit_cell = np.concatenate([pair_cell, halo_cell, pressure_sidecar_cell])
        explicit_mass = np.concatenate([pair_mass, halo_mass, pressure_sidecar_mass])

        pair_frac, pair_on_mass, pair_on_count, pair_total_count = weighted_edge_membership_fraction(
            pair_cv, pair_cell, pair_mass, new_support
        )
        halo_frac, halo_on_mass, halo_on_count, halo_total_count = weighted_edge_membership_fraction(
            halo_cv, halo_cell, halo_mass, new_support
        )
        sidecar_frac, sidecar_on_mass, sidecar_on_count, sidecar_total_count = weighted_edge_membership_fraction(
            pressure_sidecar_cv,
            pressure_sidecar_cell,
            pressure_sidecar_mass,
            new_support,
        )
        explicit_frac, explicit_on_mass, explicit_on_count, explicit_total_count = weighted_edge_membership_fraction(
            explicit_cv, explicit_cell, explicit_mass, new_support
        )

        direct_reuse_compatible = bool(
            seed_position_identity_exact
            and not geometry_changed
            and producer_changed_count == 0
            and pair_frac >= 1.0 - 1e-15
            and halo_frac >= 1.0 - 1e-15
            and sidecar_frac >= 1.0 - 1e-15
            and abs(float(np.sum(pressure_sidecar_mass))) <= 1e-10
        )

        # ------------------------------------------------------------------------------------------
        # Prospective F1-R2 normalized-transpose projection from the current
        # pressure-compatible Day375 Cartesian mass to the R22 exact support.
        # Diagnostic only: do not publish projected state arrays.
        # ------------------------------------------------------------------------------------------
        stage = "prospective_normalized_transpose_projection"

        projected_cv_mass, residual_grid, projection_audit = normalized_transpose_projection(
            pressure_grid_mass,
            new_op,
        )

        gate(
            "prospective_projection_global_split_state_ledger_closed",
            abs(projection_audit["global_split_state_ledger_residual_kg"]) <= LEDGER_TOL,
            projection_audit["global_split_state_ledger_residual_kg"],
        )
        gate(
            "prospective_projected_CV_mass_nonnegative",
            float(np.min(projected_cv_mass)) >= -MASS_TOL,
            float(np.min(projected_cv_mass)),
        )
        gate(
            "prospective_residual_grid_mass_nonnegative",
            float(np.min(residual_grid)) >= -MASS_TOL,
            float(np.min(residual_grid)),
        )

        # ------------------------------------------------------------------------------------------
        # Prospective CV capacity at the accepted Day375 pressure.
        # ------------------------------------------------------------------------------------------
        stage = "prospective_CV_capacity_audit"

        r2 = mod(root / R2, "r23_r2")
        e37a = mod(root / E37A, "r23_e37a")

        geometry = e37a.build_control_volume_geometry(
            r2,
            new_op,
            pressure,
            p_ref,
            NSL,
            NCV,
        )

        cv_capacity = e37a.cv_mass_from_saturation(
            r2,
            np.full((NSL, NCV), 0.80, dtype=np.float64),
            geometry["cv_pressure_mass_coeff"],
        )

        capacity_excess = projected_cv_mass - cv_capacity
        max_capacity_excess = float(np.max(capacity_excess))
        violating_cv_count = int(np.count_nonzero(capacity_excess > CAPACITY_TOL))
        projection_capacity_feasible = bool(violating_cv_count == 0)

        inversion_pass = False
        inversion_max_residual = None
        projected_sat_min = None
        projected_sat_max = None
        inversion_exception = None

        if projection_capacity_feasible:
            try:
                projected_sat = e37a.invert_cv_mass_to_saturation(
                    r2,
                    projected_cv_mass,
                    geometry["cv_pressure_mass_coeff"],
                )
                reconstructed = e37a.cv_mass_from_saturation(
                    r2,
                    projected_sat,
                    geometry["cv_pressure_mass_coeff"],
                )
                inversion_max_residual = float(np.max(np.abs(reconstructed - projected_cv_mass)))
                projected_sat_min = float(np.min(projected_sat))
                projected_sat_max = float(np.max(projected_sat))
                inversion_pass = bool(
                    inversion_max_residual <= max(
                        1e-6,
                        1e-10 * max(float(np.max(projected_cv_mass)), 1.0),
                    )
                )
            except Exception as exc:
                inversion_exception = repr(exc)
                inversion_pass = False

        reprojection_execution_ready = bool(
            projection_capacity_feasible
            and inversion_pass
            and abs(projection_audit["global_split_state_ledger_residual_kg"]) <= LEDGER_TOL
        )

        # ------------------------------------------------------------------------------------------
        # Classification / next authority.
        # ------------------------------------------------------------------------------------------
        stage = "classification"

        if direct_reuse_compatible:
            classification = (
                "R6R23_DIRECT_CV_CELL_REUSE_COMPATIBLE_BUT_CONTROLLED_"
                "REPROJECTION_STILL_REQUIRED_BY_F1R2_REFRESH_SEMANTICS"
            )
        elif reprojection_execution_ready:
            classification = (
                "R6R23_DIRECT_CV_CELL_REUSE_NOT_COMPATIBLE_R22_GEOMETRY_CHANGED_"
                "F1R2_CONSERVATIVE_REPROJECTION_EXACT_FEASIBLE_R24_EXECUTION_NEXT"
            )
        else:
            classification = (
                "R6R23_DIRECT_CV_CELL_REUSE_NOT_COMPATIBLE_R22_GEOMETRY_CHANGED_"
                "PROSPECTIVE_REPROJECTION_REQUIRES_CAPACITY_OR_REPRESENTATION_DESIGN_R24"
            )

        # Diagnostic PASS: incompatibility is an expected possible outcome.
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "source_R23_BLOCK_sha256": r23_block_sha,
            "R23_technical_block_closed": True,
            "F1R2_semantic_bindings_comprehensively_revalidated": True,
            "direct_old_CV_cell_reuse_compatible": direct_reuse_compatible,
            "F1R2_conservative_reprojection_execution_ready": reprojection_execution_ready,
            "P2_R6_R24_authorized": True,
            "P2_R6_R24_name": (
                "Controlled Day375 Accepted Cartesian Mass to R22 Geometry Conservative Reprojection Execution"
                if reprojection_execution_ready
                else "Day375 R22 Geometry Conservative Reprojection Capacity / Representation Design Freeze"
            ),
            "P2_R6_R24_execution_authorized": reprojection_execution_ready,
            "P2_R6_R24_design_only": not reprojection_execution_ready,
            "P2_R6_R24_must_bind_R22_flow_epoch_SHA": True,
            "P2_R6_R24_R22_flow_epoch_sha256": R22_EPOCH_SHA256,
            "P2_R6_R24_must_bind_pressure_epoch_SHA": True,
            "P2_R6_R24_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "accepted_Day375_pressure_refresh_remains_authoritative": True,
            "R22_regenerated_flow_geometry_remains_authoritative": True,
            "old_CV_cell_ownership_direct_reuse_authorized": False,
            "normalized_transpose_projection_protocol": "F1R2 exact-support normalized transpose + residual grid sidecar",
            "reverse_H1_to_S0_pullback_authorized": False,
            "mapback_execution_authorized": False,
            "transport_time_advance_authorized": False,
            "physical_time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        geometry_audit = {
            "old_day365_streamline_count": NSL,
            "new_day375_streamline_count": NSL,
            "nodes_per_streamline": NN,
            "seed_position_max_abs_change_m": seed_position_max_abs_m,
            "seed_position_identity_exact": seed_position_identity_exact,
            "producer_identity_count": producer_identity_count,
            "producer_changed_count": producer_changed_count,
            "producer_identity_fraction": producer_identity_fraction,
            "geometry_changed": geometry_changed,
            "node_displacement_min_m": float(np.min(node_displacement)),
            "node_displacement_median_m": float(np.median(node_displacement)),
            "node_displacement_mean_m": float(np.mean(node_displacement)),
            "node_displacement_max_m": float(np.max(node_displacement)),
            "terminal_TOF_relative_change_min": float(np.min(tof_endpoint_rel)),
            "terminal_TOF_relative_change_median": float(np.median(tof_endpoint_rel)),
            "terminal_TOF_relative_change_mean": float(np.mean(tof_endpoint_rel)),
            "terminal_TOF_relative_change_max": float(np.max(tof_endpoint_rel)),
            "old_exact_CV_cell_support_edge_count": int(len(old_support)),
            "new_exact_CV_cell_support_edge_count": int(len(new_support)),
            "common_exact_CV_cell_support_edge_count": int(len(common_support)),
            "old_support_retained_fraction": old_support_retained_fraction,
            "new_support_inherited_fraction": new_support_inherited_fraction,
            "support_jaccard": support_jaccard,
            "CVs_with_exact_support_change_count": changed_cv_count,
            "CVs_with_exact_support_change_fraction": float(changed_cv_count / NCVT),
        }

        ownership_audit = {
            "accepted_pair_entry_count": pair_total_count,
            "accepted_pair_abs_mass_kg": float(np.sum(np.abs(pair_mass))),
            "accepted_pair_entries_on_R22_exact_support": pair_on_count,
            "accepted_pair_abs_mass_on_R22_exact_support_kg": pair_on_mass,
            "accepted_pair_abs_mass_on_R22_exact_support_fraction": pair_frac,
            "accepted_halo_entry_count": halo_total_count,
            "accepted_halo_abs_mass_kg": float(np.sum(np.abs(halo_mass))),
            "accepted_halo_entries_on_R22_exact_support": halo_on_count,
            "accepted_halo_abs_mass_on_R22_exact_support_kg": halo_on_mass,
            "accepted_halo_abs_mass_on_R22_exact_support_fraction": halo_frac,
            "pressure_sidecar_entry_count": sidecar_total_count,
            "pressure_sidecar_abs_mass_kg": float(np.sum(np.abs(pressure_sidecar_mass))),
            "pressure_sidecar_entries_on_R22_exact_support": sidecar_on_count,
            "pressure_sidecar_abs_mass_on_R22_exact_support_kg": sidecar_on_mass,
            "pressure_sidecar_abs_mass_on_R22_exact_support_fraction": sidecar_frac,
            "explicit_combined_entry_count": explicit_total_count,
            "explicit_combined_abs_mass_kg": float(np.sum(np.abs(explicit_mass))),
            "explicit_combined_entries_on_R22_exact_support": explicit_on_count,
            "explicit_combined_abs_mass_on_R22_exact_support_kg": explicit_on_mass,
            "explicit_combined_abs_mass_on_R22_exact_support_fraction": explicit_frac,
            "direct_old_CV_cell_reuse_compatible": direct_reuse_compatible,
        }

        projection_report = {
            **projection_audit,
            "projected_CV_shape": [NSL, NCV],
            "projected_CV_min_mass_kg": float(np.min(projected_cv_mass)),
            "projected_CV_max_mass_kg": float(np.max(projected_cv_mass)),
            "residual_grid_min_cell_mass_kg": float(np.min(residual_grid)),
            "residual_grid_max_cell_mass_kg": float(np.max(residual_grid)),
            "accepted_pressure_compatible_grid_total_mass_kg": float(np.sum(pressure_grid_mass)),
            "prospective_CV_capacity_max_excess_kg": max_capacity_excess,
            "prospective_CV_capacity_violating_count": violating_cv_count,
            "prospective_CV_capacity_feasible": projection_capacity_feasible,
            "prospective_CV_mass_inversion_PASS": inversion_pass,
            "prospective_CV_mass_inversion_max_residual_kg": inversion_max_residual,
            "prospective_CV_saturation_min": projected_sat_min,
            "prospective_CV_saturation_max": projected_sat_max,
            "prospective_CV_mass_inversion_exception": inversion_exception,
            "F1R2_conservative_reprojection_execution_ready": reprojection_execution_ready,
            "projection_arrays_published_as_state": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R23_BLOCK_sha256": r23_block_sha,
            "source_R22_flow_epoch_sha256": R22_EPOCH_SHA256,
            "source_R20_accepted_transport_state_sha256": R20_ACCEPTED_SHA256,
            "source_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "canonical_day": DAY,
            "streamline_count": NSL,
            "nodes_per_streamline": NN,
            "transport_CV_count_per_streamline": NCV,
            "seed_position_max_abs_change_m": seed_position_max_abs_m,
            "producer_changed_count": producer_changed_count,
            "geometry_changed": geometry_changed,
            "node_displacement_max_m": geometry_audit["node_displacement_max_m"],
            "support_jaccard": support_jaccard,
            "CVs_with_exact_support_change_count": changed_cv_count,
            "accepted_pair_abs_mass_on_R22_exact_support_fraction": pair_frac,
            "accepted_halo_abs_mass_on_R22_exact_support_fraction": halo_frac,
            "direct_old_CV_cell_reuse_compatible": direct_reuse_compatible,
            "prospective_S0_mass_fraction": projection_audit["S0_mass_fraction"],
            "prospective_residual_grid_mass_fraction": projection_audit["residual_grid_mass_fraction"],
            "prospective_split_state_ledger_residual_kg": projection_audit["global_split_state_ledger_residual_kg"],
            "prospective_CV_capacity_max_excess_kg": max_capacity_excess,
            "prospective_CV_capacity_violating_count": violating_cv_count,
            "prospective_CV_capacity_feasible": projection_capacity_feasible,
            "prospective_CV_mass_inversion_PASS": inversion_pass,
            "F1R2_conservative_reprojection_execution_ready": reprojection_execution_ready,
            "state_mutation_executed": False,
            "mapback_executed": False,
            "transport_time_advance_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        # ------------------------------------------------------------------------------------------
        # PASS-only diagnostic publication. No projected arrays are persisted.
        # ------------------------------------------------------------------------------------------
        stage = "diagnostic_publication"

        out.mkdir(parents=True, exist_ok=False)

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Geometry_Compatibility_Audit.json").write_bytes(jb(geometry_audit))
        (out / f"{OUT_TOKEN}_Accepted_CVCell_Ownership_Audit.json").write_bytes(jb(ownership_audit))
        (out / f"{OUT_TOKEN}_Prospective_F1R2_Reprojection_Feasibility_Audit.json").write_bytes(jb(projection_report))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("R23 BLOCK SHA256                          :", r23_block_sha)
        print("R22 flow epoch SHA256                     :", R22_EPOCH_SHA256)
        print("Accepted transport state SHA256           :", R20_ACCEPTED_SHA256)
        print("Pressure epoch SHA256                     :", PRESSURE_EPOCH_SHA256)
        print("Seed position max abs change m            :", seed_position_max_abs_m)
        print("Seed positions byte-equivalent geometrically:", seed_position_identity_exact)
        print("Producer labels changed                   :", producer_changed_count, "/", NSL)
        print("Geometry changed                          :", geometry_changed)
        print("Node displacement max m                   :", geometry_audit["node_displacement_max_m"])
        print("Old/new exact-support Jaccard             :", support_jaccard)
        print("CVs with exact-support change             :", changed_cv_count, "/", NCVT)
        print("Accepted pair abs mass on new S0 fraction :", pair_frac)
        print("Accepted halo abs mass on new S0 fraction :", halo_frac)
        print("Direct old CV-cell reuse compatible       :", direct_reuse_compatible)
        print("Prospective S0 mass fraction              :", projection_audit["S0_mass_fraction"])
        print("Prospective residual grid mass fraction   :", projection_audit["residual_grid_mass_fraction"])
        print("Prospective split-state ledger residual kg:", projection_audit["global_split_state_ledger_residual_kg"])
        print("Prospective CV capacity max excess kg     :", max_capacity_excess)
        print("Prospective CV capacity violating count   :", violating_cv_count)
        print("Prospective CV mass inversion PASS        :", inversion_pass)
        print("R24 reprojection execution ready          :", reprojection_execution_ready)
        print("State / mapback / time mutation           : False / False / False")
        print("P3 authorized                             : False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "source_R23_BLOCK_preserved": True,
                "accepted_transport_state_preserved": True,
                "accepted_pressure_epoch_preserved": True,
                "R22_flow_epoch_preserved": True,
                "state_mutation_executed": False,
                "mapback_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
                "automatic_rerun_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO STATE MUTATION / MAPBACK / TIME ADVANCE / AUTOMATIC RERUN.")
        print("=" * 190)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        selftest()
        raise SystemExit(0)

    raise SystemExit(main(args.project_root, args.drive_root))
