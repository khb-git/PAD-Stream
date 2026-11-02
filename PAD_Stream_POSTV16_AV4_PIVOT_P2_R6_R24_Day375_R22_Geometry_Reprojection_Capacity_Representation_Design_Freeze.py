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


M = "POSTV16-AV4-PIVOT-P2-R6-R24"
NAME = "Day375 R22 Geometry Conservative Reprojection Capacity / Representation Design Freeze"

PASS = (
    "AV4PIVOTP2R6R24_DAY375_R22_GEOMETRY_REPROJECTION_CAPACITY_"
    "REPRESENTATION_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R24_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "f16dd3547efd2b60eb8563b0f5d16571fb1c1067"

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

LEDGER_TOL = 1.0e-6
CAPACITY_TOL = 1.0e-7
MASS_TOL = 1.0e-7

# --------------------------------------------------------------------------------------------------
# R23-R1 authority.
# --------------------------------------------------------------------------------------------------

R23R1_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R23_R1_"
    "Technical_Closure_and_Day375_RegeneratedGeometry_AcceptedTransport_Compatibility_Audit"
)
R23R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R23_R1_Summary.json"
R23R1_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R23_R1_Decision_Contract.json"
R23R1_PROJECTION = "POSTV16_AV4_PIVOT_P2_R6_R23_R1_Prospective_F1R2_Reprojection_Feasibility_Audit.json"
R23R1_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R23_R1_Artifact_Manifest.csv"
R23R1_STATUS = (
    "AV4PIVOTP2R6R23R1_TECHNICAL_CLOSURE_DAY375_REGENERATED_GEOMETRY_ACCEPTED_TRANSPORT_"
    "COMPATIBILITY_AUDIT_PASS_NO_STATE_MUTATION"
)
R23R1_CLASSIFICATION = (
    "R6R23_DIRECT_CV_CELL_REUSE_NOT_COMPATIBLE_R22_GEOMETRY_CHANGED_"
    "PROSPECTIVE_REPROJECTION_REQUIRES_CAPACITY_OR_REPRESENTATION_DESIGN_R24"
)

R23_BLOCK_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R23_BLOCKED"
R23_BLOCK = "POSTV16_AV4_PIVOT_P2_R6_R23_Blocked_Report.json"
R23_BLOCK_SHA256 = "3af990890807f42396022aa882ea4601b389b1ee5beec0dbdc278c214d9b0467"

# --------------------------------------------------------------------------------------------------
# R22 regenerated geometry.
# --------------------------------------------------------------------------------------------------

R22_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R22_"
    "Controlled_Day375_AcceptedState_Darcy_Pollock_TOF_Regeneration"
)
R22_EPOCH = "POSTV16_AV4_PIVOT_P2_R6_R22_Day375_Regenerated_Darcy_Pollock_TOF_Epoch.npz"
R22_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R22_Artifact_Manifest.csv"
R22_EPOCH_SHA256 = "7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"

# --------------------------------------------------------------------------------------------------
# Accepted pressure-compatible Cartesian mass.
# --------------------------------------------------------------------------------------------------

CLOSURE_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
CLOSURE_REL = BASE / (
    CLOSURE_TOKEN
    + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
PRESSURE_EPOCH = f"{CLOSURE_TOKEN}_Accepted_Day375_Pressure_Epoch.npz"
CLOSURE_MANIFEST = f"{CLOSURE_TOKEN}_Artifact_Manifest.csv"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

# --------------------------------------------------------------------------------------------------
# F1-R2 frozen semantics.
# --------------------------------------------------------------------------------------------------

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

# --------------------------------------------------------------------------------------------------
# Repository source authorities.
# --------------------------------------------------------------------------------------------------

R23R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R23_R1_"
    "Comprehensive_Technical_Closure_and_Compatibility_Audit.py"
)
R23R1_BLOB = "3fb381eccb131f1d69a240cdee602122fdacda97"

R22_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R22_"
    "Controlled_Day375_AcceptedState_Darcy_Pollock_TOF_Regeneration.py"
)
R22_BLOB = "fe6b5cff2e658fb1ab6414335c407de4286c278b"

F1R2_RUNNER = "PAD_Stream_POSTV16_AV4_F1_R2_Corrected_Restart_State_and_Conservative_Parent_Projection_Freeze.py"
F1R2_BLOB = "51f86f3591bf66148ef468b304c18fb4fc668e77"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R23R1_RUNNER: R23R1_BLOB,
    R22_RUNNER: R22_BLOB,
    F1R2_RUNNER: F1R2_BLOB,
    SG7D: SG7D_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Output.
# --------------------------------------------------------------------------------------------------

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R24"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze"
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
    sub_mass = gm[cell] * pv / den[cell]
    cv = stream * NCV + node
    cv_mass = np.bincount(cv, weights=sub_mass, minlength=NCVT).reshape(NSL, NCV)

    s0 = np.unique(cell)
    residual = gm.copy()
    residual[s0] = 0.0
    residual = residual.reshape(GRID)

    return cv_mass, residual, {
        "S0_cell_count": int(len(s0)),
        "S0_mass_kg": float(np.sum(gm[s0])),
        "S0_mass_fraction": float(np.sum(gm[s0]) / max(float(np.sum(gm)), 1.0e-30)),
        "residual_grid_mass_kg": float(np.sum(residual)),
        "residual_grid_mass_fraction": float(np.sum(residual) / max(float(np.sum(gm)), 1.0e-30)),
        "global_split_state_ledger_residual_kg": float(np.sum(cv_mass) + np.sum(residual) - np.sum(gm)),
    }


def unique_support_edges(op: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    stream = np.asarray(op["streamline"], dtype=np.int64).reshape(-1)
    node = np.asarray(op["node"], dtype=np.int64).reshape(-1)
    cell = np.asarray(op["flat_cell"], dtype=np.int64).reshape(-1)
    cv = stream * NCV + node
    keys = np.unique(cv * NCELL + cell)
    return (keys // NCELL).astype(np.int64), (keys % NCELL).astype(np.int64)


def max_representable_exact_support_lp(
    grid_mass: np.ndarray,
    cv_capacity: np.ndarray,
    edge_cv: np.ndarray,
    edge_cell: np.ndarray,
) -> dict[str, Any]:
    from scipy import sparse
    from scipy.optimize import linprog

    gm = np.asarray(grid_mass, dtype=np.float64).reshape(-1)
    cap = np.asarray(cv_capacity, dtype=np.float64).reshape(-1)
    edge_cv = np.asarray(edge_cv, dtype=np.int64).reshape(-1)
    edge_cell = np.asarray(edge_cell, dtype=np.int64).reshape(-1)

    if len(edge_cv) != len(edge_cell):
        raise GateError("edge_parallel_length_mismatch")
    if np.any(edge_cv < 0) or np.any(edge_cv >= NCVT):
        raise GateError("edge_CV_out_of_bounds")
    if np.any(edge_cell < 0) or np.any(edge_cell >= NCELL):
        raise GateError("edge_cell_out_of_bounds")

    active_cells = np.unique(edge_cell)
    active_cvs = np.unique(edge_cv)
    cell_row = np.searchsorted(active_cells, edge_cell)
    cv_row_local = np.searchsorted(active_cvs, edge_cv)

    ncell = len(active_cells)
    ncv = len(active_cvs)
    nedge = len(edge_cv)

    rows = np.concatenate([
        cell_row,
        ncell + cv_row_local,
    ])
    cols = np.concatenate([
        np.arange(nedge, dtype=np.int64),
        np.arange(nedge, dtype=np.int64),
    ])
    data = np.ones(2 * nedge, dtype=np.float64)

    A_ub = sparse.coo_matrix(
        (data, (rows, cols)),
        shape=(ncell + ncv, nedge),
    ).tocsr()

    b_ub = np.concatenate([
        gm[active_cells],
        cap[active_cvs],
    ])

    lp = linprog(
        -np.ones(nedge, dtype=np.float64),
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )

    if not lp.success:
        raise GateError(f"HiGHS_max_representable_failed:{lp.status}:{lp.message}")

    x = np.asarray(lp.x, dtype=np.float64)

    assigned_cell = np.bincount(
        edge_cell,
        weights=x,
        minlength=NCELL,
    )
    assigned_cv = np.bincount(
        edge_cv,
        weights=x,
        minlength=NCVT,
    )

    s0_mass = float(np.sum(gm[active_cells]))
    represented = float(np.sum(x))
    minimum_s0_residual = max(0.0, s0_mass - represented)

    cell_over = float(np.max(assigned_cell - gm))
    cv_over = float(np.max(assigned_cv - cap))

    residual_grid = gm - assigned_cell
    residual_grid[np.abs(residual_grid) < 1e-12] = 0.0

    ledger = float(np.sum(assigned_cv) + np.sum(residual_grid) - np.sum(gm))

    tol = max(1.0e-6, 1.0e-10 * max(s0_mass, 1.0))
    full_S0_feasible = bool(minimum_s0_residual <= tol)

    return {
        "solver_status": int(lp.status),
        "solver_message": str(lp.message),
        "edge_variable_count": int(nedge),
        "active_S0_cell_count": int(ncell),
        "active_CV_count": int(ncv),
        "S0_mass_kg": s0_mass,
        "maximum_representable_S0_mass_kg": represented,
        "minimum_unavoidable_S0_residual_kg": minimum_s0_residual,
        "minimum_unavoidable_S0_residual_fraction_of_S0": (
            minimum_s0_residual / max(s0_mass, 1e-30)
        ),
        "full_S0_exact_support_capacity_feasible": full_S0_feasible,
        "maximum_cell_supply_excess_kg": max(0.0, cell_over),
        "maximum_CV_capacity_excess_kg": max(0.0, cv_over),
        "global_split_state_ledger_residual_kg": ledger,
        "assigned_cv_mass": assigned_cv,
        "residual_grid_mass": residual_grid,
    }


def selftest() -> None:
    assert NCVT == 1078 * 200
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert BLOCK_REL.name == OUT_TOKEN + "_BLOCKED"

    # Tiny transportation feasibility problem:
    # cells [2,3], CV caps [4,2], complete 2x2 support -> all 5 representable.
    gm = np.asarray([2.0, 3.0], dtype=float)
    cap = np.zeros(2, dtype=float)
    cap[:] = [4.0, 2.0]
    edge_cv = np.asarray([0, 1, 0, 1], dtype=np.int64)
    edge_cell = np.asarray([0, 0, 1, 1], dtype=np.int64)

    from scipy import sparse
    from scipy.optimize import linprog

    rows = np.asarray([0, 0, 1, 1, 2, 3, 2, 3], dtype=np.int64)
    cols = np.asarray([0, 1, 2, 3, 0, 1, 2, 3], dtype=np.int64)
    A = sparse.coo_matrix((np.ones(8), (rows, cols)), shape=(4, 4)).tocsr()
    b = np.asarray([2.0, 3.0, 4.0, 2.0])
    lp = linprog(-np.ones(4), A_ub=A, b_ub=b, bounds=(0.0, None), method="highs")
    assert lp.success
    assert abs(-float(lp.fun) - 5.0) < 1e-10

    print("POSTV16 AV4 PIVOT P2-R6-R24 structural self-test: PASS")


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
        # Immutable firewall.
        # ------------------------------------------------------------------------------------------
        stage = "preexisting_state_firewall"
        pass_summary = out / f"PAD_Stream_{OUT_TOKEN}_Summary.json"
        block_report = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"

        gate("no_preexisting_R24_PASS", not pass_summary.exists(), str(pass_summary))
        gate("no_preexisting_R24_BLOCK", not block_report.exists(), str(block_report))

        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R23R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # R23 immutable BLOCK + R23-R1 PASS authority.
        # ------------------------------------------------------------------------------------------
        stage = "R23R1_authority"

        r23_block_path = drive / R23_BLOCK_REL / R23_BLOCK
        gate("R23_BLOCK_present", r23_block_path.is_file(), str(r23_block_path))
        gate("R23_BLOCK_SHA_exact", sha(r23_block_path) == R23_BLOCK_SHA256, sha(r23_block_path))

        r23 = drive / R23R1_REL
        m23 = manifest(r23, R23R1_MANIFEST)
        s23 = js(r23 / R23R1_SUMMARY)
        d23 = js(r23 / R23R1_DECISION)
        p23 = js(r23 / R23R1_PROJECTION)

        gate("R23R1_status_exact", s23.get("status") == R23R1_STATUS, s23.get("status"))
        gate("R23R1_classification_exact", s23.get("classification") == R23R1_CLASSIFICATION, s23.get("classification"))
        gate("R23R1_source_BLOCK_SHA_exact", s23.get("source_R23_BLOCK_sha256") == R23_BLOCK_SHA256)
        gate("R23R1_direct_reuse_false", s23.get("direct_old_CV_cell_reuse_compatible") is False)
        gate("R23R1_normalized_projection_capacity_infeasible", s23.get("prospective_CV_capacity_feasible") is False)
        gate("R23R1_reprojection_execution_not_ready", s23.get("F1R2_conservative_reprojection_execution_ready") is False)

        gate("R24_authorized", d23.get("P2_R6_R24_authorized") is True)
        gate("R24_design_only", d23.get("P2_R6_R24_design_only") is True)
        gate("R24_execution_not_authorized", d23.get("P2_R6_R24_execution_authorized") is False)
        gate("old_CV_reuse_forbidden", d23.get("old_CV_cell_ownership_direct_reuse_authorized") is False)
        gate("reverse_H1_pullback_forbidden", d23.get("reverse_H1_to_S0_pullback_authorized") is False)
        gate("mapback_forbidden", d23.get("mapback_execution_authorized") is False)
        gate("time_advance_forbidden", d23.get("physical_time_advance_authorized") is False)

        # ------------------------------------------------------------------------------------------
        # F1-R2 semantic authority.
        # ------------------------------------------------------------------------------------------
        stage = "F1R2_semantics"

        f1 = drive / F1R2_REL
        manifest(f1, F1R2_MANIFEST)
        sf1 = js(f1 / F1R2_SUMMARY)
        rsf1 = js(f1 / F1R2_RESTART_STATE)
        pf1 = js(f1 / F1R2_PROJECTION)
        rf1 = js(f1 / F1R2_RESIDUAL)
        df1 = js(f1 / F1R2_DECISION)

        gate("F1R2_status_exact", sf1.get("status") == F1R2_STATUS, sf1.get("status"))
        gate(
            "F1R2_cartesian_mass_primary",
            rsf1.get("recurrent_state_principle")
            == (
                "Cartesian component mass is the authoritative global recurrent physical state. "
                "Streamline control-volume mass is a conservative transport-coordinate representation "
                "derived from that state at each refreshed-flow epoch."
            ),
        )
        gate(
            "F1R2_normalized_transpose_exact",
            pf1.get("name") == "Exact-support normalized-transpose mass projection with residual grid sidecar",
        )
        gate(
            "F1R2_original_residual_zero_on_S0",
            pf1.get("residual_grid_sidecar", {}).get("definition")
            == "R_grid[c] = 0 for c in S0; R_grid[c] = M_parent[c] for c not in S0",
        )
        gate(
            "F1R2_reverse_H1_forbidden",
            "no reverse H1->S0 physical transport" in pf1.get("prohibitions", []),
        )
        gate(
            "F1R2_capacity_check_required",
            pf1.get("CV_saturation_recovery_for_F2", {}).get("capacity_check_required") is True,
        )
        gate("F1R2_split_contract_frozen", df1.get("split_restart_state_contract_frozen") is True)
        gate(
            "F1R2_residual_grid_state_exists",
            any(x.get("name") == "grid_residual_component_mass" for x in rf1.get("state_blocks", [])),
        )

        # ------------------------------------------------------------------------------------------
        # Load R22 geometry and accepted pressure-compatible Cartesian mass.
        # ------------------------------------------------------------------------------------------
        stage = "R22_pressure_epoch_binding"

        r22 = drive / R22_REL
        m22 = manifest(r22, R22_MANIFEST)
        r22_epoch_path = r22 / R22_EPOCH
        gate("R22_epoch_manifest_SHA_exact", m22.get(R22_EPOCH) == R22_EPOCH_SHA256)
        gate("R22_epoch_file_SHA_exact", sha(r22_epoch_path) == R22_EPOCH_SHA256)

        closure = drive / CLOSURE_REL
        mc = manifest(closure, CLOSURE_MANIFEST)
        pressure_epoch_path = closure / PRESSURE_EPOCH
        gate("pressure_epoch_manifest_SHA_exact", mc.get(PRESSURE_EPOCH) == PRESSURE_EPOCH_SHA256)
        gate("pressure_epoch_file_SHA_exact", sha(pressure_epoch_path) == PRESSURE_EPOCH_SHA256)

        with np.load(r22_epoch_path, allow_pickle=False) as z:
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weight_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)

        with np.load(pressure_epoch_path, allow_pickle=False) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            grid_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate("R22_geometry_shapes_exact", xyz.shape == (NSL, NN, 3) and tof_s.shape == (NSL, NN))
        gate("R22_weights_shape_positive", weight_m3_s.shape == (NSL,) and np.all(weight_m3_s > 0.0))
        gate("pressure_shape_exact", pressure.shape == GRID)
        gate("grid_mass_shape_nonnegative", grid_mass.shape == GRID and float(np.min(grid_mass)) >= -MASS_TOL)

        # ------------------------------------------------------------------------------------------
        # Reconstruct exact R22 support and physical CV capacities.
        # ------------------------------------------------------------------------------------------
        stage = "R22_support_capacity_reconstruction"

        sg7d = mod(root / SG7D, "r24_sg7d")
        e37a = mod(root / E37A, "r24_e37a")
        r2 = mod(root / R2, "r24_r2")

        op = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weight_m3_s * DAY_TO_S,
        )

        geometry = e37a.build_control_volume_geometry(
            r2,
            op,
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
        gate("CV_capacity_shape_positive", cv_capacity.shape == (NSL, NCV) and np.all(cv_capacity > 0.0))

        # Reproduce the R23 normalized-transpose failure exactly.
        norm_cv, norm_residual, norm_audit = normalized_transpose_projection(grid_mass, op)
        norm_excess = norm_cv - cv_capacity
        norm_max_excess = float(np.max(norm_excess))
        norm_violating = int(np.count_nonzero(norm_excess > CAPACITY_TOL))

        gate(
            "R23_normalized_max_excess_reproduced",
            abs(norm_max_excess - float(s23["prospective_CV_capacity_max_excess_kg"]))
            <= max(1e-6, 1e-10 * max(abs(norm_max_excess), 1.0)),
            [norm_max_excess, s23["prospective_CV_capacity_max_excess_kg"]],
        )
        gate(
            "R23_normalized_violating_count_reproduced",
            norm_violating == int(s23["prospective_CV_capacity_violating_count"]),
            [norm_violating, s23["prospective_CV_capacity_violating_count"]],
        )
        gate("normalized_projection_still_infeasible", norm_violating > 0)

        # ------------------------------------------------------------------------------------------
        # Exact-support max-representable transportation diagnostic.
        # This distinguishes allocation failure from support-capacity failure.
        # ------------------------------------------------------------------------------------------
        stage = "exact_support_transportation_capacity_diagnostic"

        edge_cv, edge_cell = unique_support_edges(op)
        transport = max_representable_exact_support_lp(
            grid_mass,
            cv_capacity,
            edge_cv,
            edge_cell,
        )

        gate("transport_LP_cell_supply_respected", transport["maximum_cell_supply_excess_kg"] <= MASS_TOL, transport["maximum_cell_supply_excess_kg"])
        gate("transport_LP_CV_capacity_respected", transport["maximum_CV_capacity_excess_kg"] <= CAPACITY_TOL, transport["maximum_CV_capacity_excess_kg"])
        gate(
            "transport_LP_split_state_ledger_closed",
            abs(transport["global_split_state_ledger_residual_kg"]) <= LEDGER_TOL,
            transport["global_split_state_ledger_residual_kg"],
        )

        assigned_cv = np.asarray(transport.pop("assigned_cv_mass"), dtype=np.float64).reshape(NSL, NCV)
        residual_grid = np.asarray(transport.pop("residual_grid_mass"), dtype=np.float64).reshape(GRID)

        # Prospective inversion of the max-representable CV state.
        inversion_pass = False
        inversion_error = None
        sat_min = None
        sat_max = None
        inversion_exception = None

        try:
            projected_sat = e37a.invert_cv_mass_to_saturation(
                r2,
                assigned_cv,
                geometry["cv_pressure_mass_coeff"],
            )
            reconstructed = e37a.cv_mass_from_saturation(
                r2,
                projected_sat,
                geometry["cv_pressure_mass_coeff"],
            )
            inversion_error = float(np.max(np.abs(reconstructed - assigned_cv)))
            sat_min = float(np.min(projected_sat))
            sat_max = float(np.max(projected_sat))
            inv_tol = max(1e-6, 1e-10 * max(float(np.max(assigned_cv)), 1.0))
            inversion_pass = bool(inversion_error <= inv_tol)
        except Exception as exc:
            inversion_exception = repr(exc)

        gate("max_representable_CV_inversion_PASS", inversion_pass, inversion_exception or inversion_error)

        full_S0_feasible = bool(transport["full_S0_exact_support_capacity_feasible"])
        min_s0_residual = float(transport["minimum_unavoidable_S0_residual_kg"])
        min_s0_residual_fraction = float(transport["minimum_unavoidable_S0_residual_fraction_of_S0"])

        if full_S0_feasible:
            classification = (
                "R6R24_NORMALIZED_TRANSPOSE_ALLOCATION_FAILURE_ONLY_"
                "EXACT_R22_SUPPORT_FULL_S0_CAPACITY_FEASIBLE_"
                "CAPACITY_AWARE_REPROJECTION_EXECUTION_NEXT"
            )
            successor_name = (
                "Controlled Day375 Capacity-Aware Exact-Support Conservative Reprojection Execution"
            )
            residual_semantics = (
                "retain original F1-R2 residual semantics: residual grid mass only outside R22 exact S0"
            )
            representation_amendment_required = False
        else:
            classification = (
                "R6R24_EXACT_R22_SUPPORT_CANNOT_REPRESENT_ALL_S0_MASS_WITHIN_CV_CAPACITY_"
                "CAPACITY_LIMITED_SPLIT_STATE_WITH_MINIMUM_S0_RESIDUAL_REQUIRED_"
                "CONTROLLED_EXECUTION_NEXT"
            )
            successor_name = (
                "Controlled Day375 Capacity-Limited Exact-Support Split-State Reprojection Execution"
            )
            residual_semantics = (
                "amend F1-R2 residual sidecar: retain exact Cartesian residual for all mass not "
                "representable on R22 exact support within frozen CV capacity, including minimum "
                "unavoidable residual in S0; no reverse H1->S0 pullback and no support growth"
            )
            representation_amendment_required = True

        execution_ready = bool(inversion_pass)

        # ------------------------------------------------------------------------------------------
        # Freeze the R25 execution semantics.
        # ------------------------------------------------------------------------------------------
        stage = "R25_protocol_freeze"

        protocol = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "diagnostic_only_in_R24": True,
            "source_authorities": {
                "R23_R1_summary": R23R1_SUMMARY,
                "R22_flow_epoch_sha256": R22_EPOCH_SHA256,
                "pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
                "F1R2_projection_protocol": F1R2_PROJECTION,
            },
            "capacity_diagnosis": {
                "normalized_transpose_max_CV_excess_kg": norm_max_excess,
                "normalized_transpose_violating_CV_count": norm_violating,
                **transport,
            },
            "representation_design": {
                "Cartesian_component_mass_remains_primary_recurrent_state": True,
                "R22_exact_support_only": True,
                "support_growth_authorized": False,
                "reverse_H1_to_S0_pullback_authorized": False,
                "old_CV_cell_ownership_reuse_authorized": False,
                "representation_amendment_required": representation_amendment_required,
                "residual_grid_semantics": residual_semantics,
                "CV_capacity_must_be_enforced": True,
                "global_split_state_mass_ledger_must_close": True,
                "prospective_max_representable_CV_inversion_PASS": inversion_pass,
            },
            "R25_lexicographic_execution_objective": {
                "stage1": (
                    "maximize total accepted Day375 Cartesian component mass represented on "
                    "R22 exact (cell,CV) support subject to per-cell supply and frozen CV capacity"
                ),
                "stage2": (
                    "subject to the stage1 optimum, minimize L1 deviation from the original "
                    "F1-R2 PV-normalized-transpose edge-mass target"
                ),
                "stage3": (
                    "publish exact residual Cartesian sidecar as parent grid mass minus the "
                    "cellwise mass represented on R22 support"
                ),
                "if_full_S0_feasible": (
                    "require numerical-zero S0 residual and retain original F1-R2 residual outside S0 only"
                ),
                "if_full_S0_infeasible": (
                    "require the stage1 minimum-unavoidable S0 residual and forbid discarding, clipping, "
                    "global rescaling, reverse halo pullback, or automatic support growth"
                ),
            },
            "R25_firewalls": {
                "mapback_execution": False,
                "transport_time_advance": False,
                "physical_time_advance": False,
                "PI_RNN_inference": False,
                "training": False,
                "P3_authorized": False,
            },
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R23_BLOCK_sha256": R23_BLOCK_SHA256,
            "source_R22_flow_epoch_sha256": R22_EPOCH_SHA256,
            "source_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "normalized_transpose_max_CV_excess_kg": norm_max_excess,
            "normalized_transpose_violating_CV_count": norm_violating,
            "R22_exact_support_edge_count": int(transport["edge_variable_count"]),
            "R22_exact_support_S0_cell_count": int(transport["active_S0_cell_count"]),
            "R22_exact_support_active_CV_count": int(transport["active_CV_count"]),
            "S0_mass_kg": float(transport["S0_mass_kg"]),
            "maximum_representable_S0_mass_kg": float(transport["maximum_representable_S0_mass_kg"]),
            "minimum_unavoidable_S0_residual_kg": min_s0_residual,
            "minimum_unavoidable_S0_residual_fraction_of_S0": min_s0_residual_fraction,
            "full_S0_exact_support_capacity_feasible": full_S0_feasible,
            "max_representable_split_state_ledger_residual_kg": float(transport["global_split_state_ledger_residual_kg"]),
            "max_representable_CV_inversion_PASS": inversion_pass,
            "max_representable_CV_inversion_max_error_kg": inversion_error,
            "max_representable_CV_saturation_min": sat_min,
            "max_representable_CV_saturation_max": sat_max,
            "representation_amendment_required": representation_amendment_required,
            "state_mutation_executed": False,
            "support_growth_executed": False,
            "mapback_executed": False,
            "transport_time_advance_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R25_authorized": execution_ready,
            "P2_R6_R25_name": successor_name,
            "P2_R6_R25_execution_authorized": execution_ready,
            "P2_R6_R25_must_bind_R24_design_contract": True,
            "P2_R6_R25_must_bind_R22_flow_epoch_SHA": True,
            "P2_R6_R25_R22_flow_epoch_sha256": R22_EPOCH_SHA256,
            "P2_R6_R25_must_bind_pressure_epoch_SHA": True,
            "P2_R6_R25_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "full_S0_exact_support_capacity_feasible": full_S0_feasible,
            "representation_amendment_required": representation_amendment_required,
            "minimum_unavoidable_S0_residual_kg": min_s0_residual,
            "old_CV_cell_ownership_direct_reuse_authorized": False,
            "automatic_support_growth_authorized": False,
            "reverse_H1_to_S0_pullback_authorized": False,
            "mapback_execution_authorized": False,
            "transport_time_advance_authorized": False,
            "physical_time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        # ------------------------------------------------------------------------------------------
        # PASS-only design publication. No LP assignment arrays are persisted.
        # ------------------------------------------------------------------------------------------
        stage = "design_freeze_publication"

        out.mkdir(parents=True, exist_ok=False)

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_ExactSupport_Capacity_Diagnostic.json").write_bytes(jb({
            "normalized_transpose": {
                **norm_audit,
                "maximum_CV_capacity_excess_kg": norm_max_excess,
                "violating_CV_count": norm_violating,
            },
            "max_representable_exact_support_transportation": transport,
            "max_representable_CV_mass_inversion": {
                "PASS": inversion_pass,
                "maximum_reconstruction_error_kg": inversion_error,
                "saturation_min": sat_min,
                "saturation_max": sat_max,
                "exception": inversion_exception,
            },
        }))
        (out / f"{OUT_TOKEN}_Capacity_Aware_Reprojection_Protocol.json").write_bytes(jb(protocol))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Classification                              :", classification)
        print("Normalized-transpose max CV excess kg       :", norm_max_excess)
        print("Normalized-transpose violating CVs          :", norm_violating)
        print("R22 exact support edges                     :", transport["edge_variable_count"])
        print("R22 exact S0 cells / active CVs             :", transport["active_S0_cell_count"], "/", transport["active_CV_count"])
        print("S0 mass kg                                  :", transport["S0_mass_kg"])
        print("Maximum representable S0 mass kg            :", transport["maximum_representable_S0_mass_kg"])
        print("Minimum unavoidable S0 residual kg          :", min_s0_residual)
        print("Minimum unavoidable S0 residual fraction    :", min_s0_residual_fraction)
        print("Full S0 exact-support capacity feasible      :", full_S0_feasible)
        print("Prospective CV inversion PASS                :", inversion_pass)
        print("Representation amendment required            :", representation_amendment_required)
        print("R25 controlled execution authorized          :", execution_ready)
        print("State/support/mapback/time mutation in R24   : False / False / False / False")
        print("P3 authorized                                : False")
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
                "R23_R1_PASS_preserved": True,
                "R22_flow_epoch_preserved": True,
                "accepted_pressure_epoch_preserved": True,
                "state_mutation_executed": False,
                "support_growth_executed": False,
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
        print("NO STATE MUTATION / SUPPORT GROWTH / MAPBACK / TIME ADVANCE.")
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
