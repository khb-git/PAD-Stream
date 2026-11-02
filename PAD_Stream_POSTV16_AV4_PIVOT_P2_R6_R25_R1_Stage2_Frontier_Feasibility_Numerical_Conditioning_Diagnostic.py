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


M = "POSTV16-AV4-PIVOT-P2-R6-R25-R1"
NAME = "R25 Stage-2 Frontier Feasibility / Numerical Conditioning Diagnostic Freeze"

PASS = (
    "AV4PIVOTP2R6R25R1_STAGE2_FRONTIER_FEASIBILITY_NUMERICAL_CONDITIONING_"
    "DIAGNOSTIC_PASS_NO_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R25R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "5238a386639d208ee9227a308382af80d1238c85"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

GRID = (15, 50, 50)
NCELL = 37500
NSL = 1078
NN = 201
NCV = 200
NCVT = NSL * NCV
DAY_TO_S = 86400.0

MASS_TOL = 1.0e-6
CAPACITY_TOL = 1.0e-7
OPT_REL_TOL = 1.0e-10

R24_MAX_REPRESENTABLE_S0_MASS_KG = 52457458.82473308
R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG = 6646660.64504873
R24_EXACT_SUPPORT_EDGE_COUNT = 269532

# --------------------------------------------------------------------------------------
# Immutable R25 scientific-fail authority.
# --------------------------------------------------------------------------------------

R25_FAIL_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R25_SCIENTIFIC_FAIL"
R25_FAIL = "POSTV16_AV4_PIVOT_P2_R6_R25_Scientific_Fail_Report.json"
R25_FAIL_STATUS = (
    "AV4PIVOTP2R6R25_DAY375_CAPACITY_LIMITED_EXACT_SUPPORT_SPLIT_STATE_"
    "REPROJECTION_EXECUTION_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN"
)
R25_FAIL_STAGE = "stage2_minimum_L1_deviation"
R25_FAIL_GATE = "stage2_min_L1_HiGHS"

# --------------------------------------------------------------------------------------
# R24 / R22 / accepted pressure state.
# --------------------------------------------------------------------------------------

R24_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R24_"
    "Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze"
)
R24_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_Summary.json"
R24_PROTOCOL = "POSTV16_AV4_PIVOT_P2_R6_R24_Capacity_Aware_Reprojection_Protocol.json"
R24_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R24_Decision_Contract.json"
R24_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R24_Artifact_Manifest.csv"

R22_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R22_"
    "Controlled_Day375_AcceptedState_Darcy_Pollock_TOF_Regeneration"
)
R22_EPOCH = "POSTV16_AV4_PIVOT_P2_R6_R22_Day375_Regenerated_Darcy_Pollock_TOF_Epoch.npz"
R22_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R22_Artifact_Manifest.csv"
R22_EPOCH_SHA256 = "7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"

CLOSURE_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
CLOSURE_REL = BASE / (
    CLOSURE_TOKEN
    + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
PRESSURE_EPOCH = f"{CLOSURE_TOKEN}_Accepted_Day375_Pressure_Epoch.npz"
CLOSURE_MANIFEST = f"{CLOSURE_TOKEN}_Artifact_Manifest.csv"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

# --------------------------------------------------------------------------------------
# Repository authorities.
# --------------------------------------------------------------------------------------

R25_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution.py"
)
R25_BLOB = "55f0ebcc5dacdaf3b039cda434748d1e86d4d8ad"

R24_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_"
    "Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze.py"
)
R24_BLOB = "9168baf3155e712b9c342239bed9ab4b1d787691"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R25_RUNNER: R25_BLOB,
    R24_RUNNER: R24_BLOB,
    SG7D: SG7D_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R25_R1"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Stage2_Frontier_Feasibility_Numerical_Conditioning_Diagnostic_Freeze"
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


def build_edge_target_and_support(
    grid_mass: np.ndarray,
    op: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gm = np.asarray(grid_mass, dtype=np.float64).reshape(-1)
    stream = np.asarray(op["streamline"], dtype=np.int64).reshape(-1)
    node = np.asarray(op["node"], dtype=np.int64).reshape(-1)
    cell = np.asarray(op["flat_cell"], dtype=np.int64).reshape(-1)
    pv = np.asarray(op["pv_m3"], dtype=np.float64).reshape(-1)

    cv = stream * NCV + node
    den = np.bincount(cell, weights=pv, minlength=NCELL)
    if np.any(den[cell] <= 0.0):
        raise GateError("zero_cell_denominator")

    sub_target = gm[cell] * pv / den[cell]
    key = cv * NCELL + cell

    uniq, inv = np.unique(key, return_inverse=True)
    target = np.bincount(inv, weights=sub_target, minlength=len(uniq))

    return (
        (uniq // NCELL).astype(np.int64),
        (uniq % NCELL).astype(np.int64),
        np.asarray(target, dtype=np.float64),
    )


def common_supply_capacity(
    grid_mass: np.ndarray,
    cv_capacity: np.ndarray,
    edge_cv: np.ndarray,
    edge_cell: np.ndarray,
):
    from scipy import sparse

    gm = np.asarray(grid_mass, dtype=np.float64).reshape(-1)
    cap = np.asarray(cv_capacity, dtype=np.float64).reshape(-1)
    edge_cv = np.asarray(edge_cv, dtype=np.int64).reshape(-1)
    edge_cell = np.asarray(edge_cell, dtype=np.int64).reshape(-1)

    active_cells = np.unique(edge_cell)
    active_cvs = np.unique(edge_cv)
    cell_row = np.searchsorted(active_cells, edge_cell)
    cv_row = np.searchsorted(active_cvs, edge_cv)
    ncell = len(active_cells)
    ncv = len(active_cvs)
    nedge = len(edge_cv)

    rows = np.concatenate([cell_row, ncell + cv_row])
    cols = np.concatenate([
        np.arange(nedge, dtype=np.int64),
        np.arange(nedge, dtype=np.int64),
    ])
    data = np.ones(2 * nedge, dtype=np.float64)

    A = sparse.coo_matrix(
        (data, (rows, cols)),
        shape=(ncell + ncv, nedge),
    ).tocsr()
    b = np.concatenate([gm[active_cells], cap[active_cvs]])
    return A, b, active_cells, active_cvs


def stage1_solve(grid_mass, cv_capacity, edge_cv, edge_cell):
    from scipy.optimize import linprog

    A, b, active_cells, active_cvs = common_supply_capacity(
        grid_mass,
        cv_capacity,
        edge_cv,
        edge_cell,
    )
    nedge = len(edge_cv)
    lp = linprog(
        -np.ones(nedge, dtype=np.float64),
        A_ub=A,
        b_ub=b,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )
    if not lp.success:
        raise GateError(f"stage1_reproduction_failed:{lp.status}:{lp.message}")
    x = np.asarray(lp.x, dtype=np.float64)
    return x, float(np.sum(x)), A, b, active_cells, active_cvs


def evaluate_stage2_witness(
    x: np.ndarray,
    target: np.ndarray,
    A_supply,
    b_supply: np.ndarray,
    represented_mass_kg: float,
) -> dict[str, float]:
    x = np.asarray(x, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    d = np.abs(x - target)

    supply_residual = np.asarray(A_supply @ x - b_supply, dtype=np.float64)
    max_supply_violation = max(0.0, float(np.max(supply_residual)))
    min_x = float(np.min(x))
    min_d = float(np.min(d))

    upper_abs = x - d - target
    lower_abs = -x - d + target
    max_abs_constraint_violation = max(
        0.0,
        float(np.max(upper_abs)),
        float(np.max(lower_abs)),
    )

    equality_residual = float(np.sum(x) - represented_mass_kg)

    return {
        "maximum_supply_or_capacity_violation_kg": max_supply_violation,
        "minimum_x_kg": min_x,
        "minimum_d_kg": min_d,
        "maximum_L1_epigraph_violation_kg": max_abs_constraint_violation,
        "exact_frontier_equality_residual_kg": equality_residual,
        "witness_L1_objective_kg": float(np.sum(d)),
    }


def solve_stage2(
    grid_mass: np.ndarray,
    cv_capacity: np.ndarray,
    edge_cv: np.ndarray,
    edge_cell: np.ndarray,
    target: np.ndarray,
    represented_mass_kg: float,
    *,
    mass_floor_delta_kg: float | None,
    presolve: bool,
    method: str = "highs",
) -> dict[str, Any]:
    from scipy import sparse
    from scipy.optimize import linprog

    A_supply_x, b_supply, _active_cells, _active_cvs = common_supply_capacity(
        grid_mass,
        cv_capacity,
        edge_cv,
        edge_cell,
    )

    target = np.asarray(target, dtype=np.float64).reshape(-1)
    nedge = len(target)
    nvar = 2 * nedge

    # Lift supply/capacity matrix from x-space into [x,d]-space.
    A_supply = sparse.hstack(
        [A_supply_x, sparse.csr_matrix((A_supply_x.shape[0], nedge))],
        format="csr",
    )

    r = np.arange(nedge, dtype=np.int64)
    rows_abs = np.concatenate([r, r, nedge + r, nedge + r])
    cols_abs = np.concatenate([r, nedge + r, r, nedge + r])
    data_abs = np.concatenate([
        np.ones(nedge),
        -np.ones(nedge),
        -np.ones(nedge),
        -np.ones(nedge),
    ])
    A_abs = sparse.coo_matrix(
        (data_abs, (rows_abs, cols_abs)),
        shape=(2 * nedge, nvar),
    ).tocsr()
    b_abs = np.concatenate([target, -target])

    A_ub_parts = [A_supply, A_abs]
    b_ub_parts = [b_supply, b_abs]

    A_eq = None
    b_eq = None

    if mass_floor_delta_kg is None:
        # Original R25 exact-frontier equality.
        A_eq = sparse.csr_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (
                    np.zeros(nedge, dtype=np.int64),
                    np.arange(nedge, dtype=np.int64),
                ),
            ),
            shape=(1, nvar),
        )
        b_eq = np.asarray([represented_mass_kg], dtype=np.float64)
    else:
        # Diagnostic lexicographic floor:
        # sum(x) >= M1 - delta.
        A_floor = sparse.csr_matrix(
            (
                -np.ones(nedge, dtype=np.float64),
                (
                    np.zeros(nedge, dtype=np.int64),
                    np.arange(nedge, dtype=np.int64),
                ),
            ),
            shape=(1, nvar),
        )
        A_ub_parts.append(A_floor)
        b_ub_parts.append(
            np.asarray([-(represented_mass_kg - mass_floor_delta_kg)], dtype=np.float64)
        )

    A_ub = sparse.vstack(A_ub_parts, format="csr")
    b_ub = np.concatenate(b_ub_parts)

    c = np.concatenate([
        np.zeros(nedge, dtype=np.float64),
        np.ones(nedge, dtype=np.float64),
    ])

    lp = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=(0.0, None),
        method=method,
        options={"presolve": presolve},
    )

    result = {
        "success": bool(lp.success),
        "status": int(lp.status),
        "message": str(lp.message),
        "presolve": bool(presolve),
        "method": method,
        "mass_floor_delta_kg": mass_floor_delta_kg,
    }
    if lp.success:
        z = np.asarray(lp.x, dtype=np.float64)
        x = z[:nedge]
        d = z[nedge:]
        result.update({
            "represented_mass_kg": float(np.sum(x)),
            "mass_loss_vs_stage1_kg": float(represented_mass_kg - np.sum(x)),
            "L1_objective_kg": float(np.sum(d)),
            "minimum_x_kg": float(np.min(x)),
            "minimum_d_kg": float(np.min(d)),
        })
    return result


def selftest() -> None:
    assert NCVT == NSL * NCV
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert BLOCK_REL.name == OUT_TOKEN + "_BLOCKED"

    # Direct witness algebra.
    x = np.asarray([1.0, 2.0])
    target = np.asarray([1.0, 4.0])
    from scipy import sparse
    A = sparse.eye(2, format="csr")
    b = np.asarray([2.0, 2.0])
    w = evaluate_stage2_witness(x, target, A, b, 3.0)
    assert w["maximum_supply_or_capacity_violation_kg"] == 0.0
    assert w["maximum_L1_epigraph_violation_kg"] == 0.0
    assert w["exact_frontier_equality_residual_kg"] == 0.0
    assert abs(w["witness_L1_objective_kg"] - 2.0) < 1e-12

    print("POSTV16 AV4 PIVOT P2-R6-R25-R1 structural self-test: PASS")


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
        stage = "preexisting_state_firewall"
        pass_summary = out / f"PAD_Stream_{OUT_TOKEN}_Summary.json"
        block_report = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"

        gate("no_preexisting_R25R1_PASS", not pass_summary.exists(), str(pass_summary))
        gate("no_preexisting_R25R1_BLOCK", not block_report.exists(), str(block_report))

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R25_FAIL_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # ----------------------------------------------------------------------------------
        # Immutable R25 SCIENTIFIC FAIL authority.
        # ----------------------------------------------------------------------------------
        stage = "R25_scientific_fail_authority"

        fail_path = drive / R25_FAIL_REL / R25_FAIL
        gate("R25_FAIL_present", fail_path.is_file(), str(fail_path))
        fail_sha = sha(fail_path)
        f25 = js(fail_path)

        gate("R25_FAIL_status_exact", f25.get("status") == R25_FAIL_STATUS, f25.get("status"))
        gate("R25_FAIL_stage_exact", f25.get("failed_stage") == R25_FAIL_STAGE, f25.get("failed_stage"))
        gate("R25_FAIL_gate_exact", f25.get("failed_gate") == R25_FAIL_GATE, f25.get("failed_gate"))
        detail = f25.get("detail")
        gate(
            "R25_FAIL_HiGHS_infeasible_bound",
            isinstance(detail, list)
            and len(detail) >= 2
            and int(detail[0]) == 2
            and "infeasible" in str(detail[1]).lower(),
            detail,
        )
        gate("R25_FAIL_R24_preserved", f25.get("R24_design_preserved") is True)
        gate("R25_FAIL_R22_preserved", f25.get("R22_flow_epoch_preserved") is True)
        gate("R25_FAIL_pressure_preserved", f25.get("accepted_pressure_epoch_preserved") is True)
        gate("R25_FAIL_cartesian_state_preserved", f25.get("accepted_cartesian_state_preserved") is True)
        gate("R25_FAIL_no_automatic_rerun", f25.get("automatic_rerun_authorized") is False)

        # ----------------------------------------------------------------------------------
        # R24 design contract and source state.
        # ----------------------------------------------------------------------------------
        stage = "R24_R22_pressure_authority"

        r24 = drive / R24_REL
        manifest(r24, R24_MANIFEST)
        s24 = js(r24 / R24_SUMMARY)
        d24 = js(r24 / R24_DECISION)

        gate(
            "R24_max_mass_exact",
            abs(float(s24["maximum_representable_S0_mass_kg"]) - R24_MAX_REPRESENTABLE_S0_MASS_KG)
            <= 1e-6,
        )
        gate("R24_R25_execution_authorized_historically", d24.get("P2_R6_R25_execution_authorized") is True)

        r22 = drive / R22_REL
        m22 = manifest(r22, R22_MANIFEST)
        r22_epoch_path = r22 / R22_EPOCH
        gate("R22_epoch_SHA_exact", m22.get(R22_EPOCH) == R22_EPOCH_SHA256 and sha(r22_epoch_path) == R22_EPOCH_SHA256)

        closure = drive / CLOSURE_REL
        mc = manifest(closure, CLOSURE_MANIFEST)
        pressure_epoch_path = closure / PRESSURE_EPOCH
        gate(
            "pressure_epoch_SHA_exact",
            mc.get(PRESSURE_EPOCH) == PRESSURE_EPOCH_SHA256
            and sha(pressure_epoch_path) == PRESSURE_EPOCH_SHA256,
        )

        with np.load(r22_epoch_path, allow_pickle=False) as z:
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weight_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)

        with np.load(pressure_epoch_path, allow_pickle=False) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            grid_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate("geometry_shapes_exact", xyz.shape == (NSL, NN, 3) and tof_s.shape == (NSL, NN))
        gate("grid_mass_shape_exact", grid_mass.shape == GRID)

        # ----------------------------------------------------------------------------------
        # Reconstruct Stage 1 and the exact Stage-2 witness.
        # ----------------------------------------------------------------------------------
        stage = "stage1_witness_reconstruction"

        sg7d = mod(root / SG7D, "r25r1_sg7d")
        e37a = mod(root / E37A, "r25r1_e37a")
        r2 = mod(root / R2, "r25r1_r2")

        op = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weight_m3_s * DAY_TO_S,
        )
        edge_cv, edge_cell, target = build_edge_target_and_support(grid_mass, op)
        gate("edge_count_exact", len(edge_cv) == R24_EXACT_SUPPORT_EDGE_COUNT, len(edge_cv))

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

        x1, m1, A_supply, b_supply, _active_cells, _active_cvs = stage1_solve(
            grid_mass,
            cv_capacity,
            edge_cv,
            edge_cell,
        )

        stage1_acceptance_tol = max(
            MASS_TOL,
            OPT_REL_TOL * max(abs(R24_MAX_REPRESENTABLE_S0_MASS_KG), 1.0),
        )
        gate(
            "stage1_mass_matches_R24_with_frozen_acceptance_tolerance",
            abs(m1 - R24_MAX_REPRESENTABLE_S0_MASS_KG) <= stage1_acceptance_tol,
            {
                "R25R1_stage1_mass_kg": m1,
                "R24_mass_kg": R24_MAX_REPRESENTABLE_S0_MASS_KG,
                "acceptance_tolerance_kg": stage1_acceptance_tol,
            },
        )

        witness = evaluate_stage2_witness(
            x1,
            target,
            A_supply,
            b_supply,
            m1,
        )

        # Do not hard-fail on the witness residuals: they are precisely the diagnostic.
        # The only hard requirement is finite diagnostic output.
        gate(
            "stage1_witness_diagnostics_finite",
            all(np.isfinite(float(v)) for v in witness.values()),
            witness,
        )

        # ----------------------------------------------------------------------------------
        # Numerical-conditioning probes.
        # ----------------------------------------------------------------------------------
        stage = "frontier_conditioning_probes"

        # We already have the immutable exact-equality/presolve=True failure from R25.
        # Probe exact equality without presolve, then bounded mass floors.
        exact_no_presolve = solve_stage2(
            grid_mass,
            cv_capacity,
            edge_cv,
            edge_cell,
            target,
            m1,
            mass_floor_delta_kg=None,
            presolve=False,
            method="highs",
        )

        floor_deltas = [
            stage1_acceptance_tol,
            100.0 * stage1_acceptance_tol,
            10000.0 * stage1_acceptance_tol,
        ]
        floor_results = []
        first_feasible = None

        for delta in floor_deltas:
            result = solve_stage2(
                grid_mass,
                cv_capacity,
                edge_cv,
                edge_cell,
                target,
                m1,
                mass_floor_delta_kg=float(delta),
                presolve=True,
                method="highs",
            )
            floor_results.append(result)
            if result["success"] and first_feasible is None:
                first_feasible = result
                break

        # ----------------------------------------------------------------------------------
        # Classification.
        # ----------------------------------------------------------------------------------
        stage = "classification"

        witness_feasible_at_scientific_tol = bool(
            witness["maximum_supply_or_capacity_violation_kg"] <= stage1_acceptance_tol
            and witness["minimum_x_kg"] >= -stage1_acceptance_tol
            and witness["minimum_d_kg"] >= -stage1_acceptance_tol
            and witness["maximum_L1_epigraph_violation_kg"] <= stage1_acceptance_tol
            and abs(witness["exact_frontier_equality_residual_kg"]) <= stage1_acceptance_tol
        )

        exact_alternate_solver_path_feasible = bool(exact_no_presolve["success"])
        bounded_frontier_feasible = bool(first_feasible is not None)

        if exact_alternate_solver_path_feasible:
            classification = (
                "R6R25R1_STAGE1_WITNESS_VALID_EXACT_STAGE2_FEASIBLE_WITHOUT_PRESOLVE_"
                "HIGHS_PRESOLVE_CONDITIONING_FAILURE_DESIGN_REPAIR_NEXT"
            )
            next_name = (
                "R25 Lexicographic Solver-Conditioning Repair Design Freeze — Exact Frontier Preserved"
            )
        elif witness_feasible_at_scientific_tol and bounded_frontier_feasible:
            classification = (
                "R6R25R1_STAGE1_WITNESS_VALID_WITHIN_FROZEN_OPTIMUM_TOLERANCE_"
                "EXACT_EQUALITY_FRONTIER_NUMERICALLY_ILL_CONDITIONED_"
                "BOUNDED_LEXICOGRAPHIC_FRONTIER_DESIGN_REPAIR_NEXT"
            )
            next_name = (
                "R25 Bounded Lexicographic Frontier Semantics Design Freeze"
            )
        elif bounded_frontier_feasible:
            classification = (
                "R6R25R1_STAGE1_FRONTIER_REQUIRES_NONZERO_MASS_RELAXATION_"
                "BOUNDED_LEXICOGRAPHIC_FRONTIER_DESIGN_REPAIR_NEXT"
            )
            next_name = (
                "R25 Quantified Frontier-Relaxation Lexicographic Design Freeze"
            )
        else:
            classification = (
                "R6R25R1_STAGE2_REMAINS_INFEASIBLE_UNDER_DIAGNOSTIC_FRONTIER_BANDS_"
                "SECONDARY_OBJECTIVE_FORMULATION_REDESIGN_REQUIRED"
            )
            next_name = (
                "R25 Secondary Objective Formulation Redesign Freeze"
            )

        minimum_tested_feasible_delta = (
            None if first_feasible is None
            else float(first_feasible["mass_floor_delta_kg"])
        )
        realized_mass_loss = (
            None if first_feasible is None
            else float(first_feasible["mass_loss_vs_stage1_kg"])
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R25_SCIENTIFIC_FAIL_sha256": fail_sha,
            "R25_failed_stage": R25_FAIL_STAGE,
            "R25_failed_gate": R25_FAIL_GATE,
            "stage1_reproduced_mass_kg": m1,
            "R24_maximum_representable_mass_kg": R24_MAX_REPRESENTABLE_S0_MASS_KG,
            "stage1_frozen_acceptance_tolerance_kg": stage1_acceptance_tol,
            "stage1_witness_maximum_supply_or_capacity_violation_kg": witness["maximum_supply_or_capacity_violation_kg"],
            "stage1_witness_minimum_x_kg": witness["minimum_x_kg"],
            "stage1_witness_maximum_L1_epigraph_violation_kg": witness["maximum_L1_epigraph_violation_kg"],
            "stage1_witness_exact_frontier_equality_residual_kg": witness["exact_frontier_equality_residual_kg"],
            "stage1_witness_L1_objective_kg": witness["witness_L1_objective_kg"],
            "stage1_witness_feasible_within_frozen_optimum_tolerance": witness_feasible_at_scientific_tol,
            "exact_stage2_without_presolve_success": exact_no_presolve["success"],
            "exact_stage2_without_presolve_status": exact_no_presolve["status"],
            "exact_stage2_without_presolve_message": exact_no_presolve["message"],
            "bounded_frontier_any_tested_success": bounded_frontier_feasible,
            "minimum_tested_feasible_frontier_delta_kg": minimum_tested_feasible_delta,
            "realized_mass_loss_at_first_feasible_frontier_kg": realized_mass_loss,
            "diagnostic_only": True,
            "state_mutation_executed": False,
            "support_growth_executed": False,
            "mapback_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        diagnostic = {
            "source_R25_fail_sha256": fail_sha,
            "stage1_witness": witness,
            "exact_equality_without_presolve": exact_no_presolve,
            "bounded_frontier_probes": floor_results,
            "classification": classification,
            "interpretation": (
                "R25 Stage-1 remains the frozen primary optimum authority. "
                "R25-R1 does not authorize execution; it diagnoses whether Stage-2 infeasibility "
                "is caused by exact-frontier numerical conditioning or a deeper secondary-objective issue."
            ),
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R25_R2_authorized": True,
            "P2_R6_R25_R2_name": next_name,
            "P2_R6_R25_R2_design_only": True,
            "P2_R6_R25_R2_execution_authorized": False,
            "P2_R6_R25_R2_must_bind_R25_FAIL_SHA": True,
            "P2_R6_R25_R2_R25_FAIL_sha256": fail_sha,
            "P2_R6_R25_R2_must_bind_R25R1_diagnostic": True,
            "stage1_maximum_representable_mass_remains_authoritative": True,
            "capacity_limited_split_state_execution_authorized_now": False,
            "automatic_rerun_authorized": False,
            "support_growth_authorized": False,
            "reverse_H1_to_S0_pullback_authorized": False,
            "mapback_execution_authorized": False,
            "physical_time_advance_authorized": False,
            "P3_authorized": False,
        }

        stage = "diagnostic_publication"
        out.mkdir(parents=True, exist_ok=False)

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Frontier_Feasibility_Diagnostic.json").write_bytes(jb(diagnostic))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({
                    "file": p.name,
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                })
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Classification                              :", classification)
        print("R25 SCIENTIFIC FAIL SHA256                  :", fail_sha)
        print("Stage1 reproduced mass kg                   :", m1)
        print("Frozen Stage1 acceptance tolerance kg       :", stage1_acceptance_tol)
        print("Witness max supply/capacity violation kg    :", witness["maximum_supply_or_capacity_violation_kg"])
        print("Witness max L1 epigraph violation kg        :", witness["maximum_L1_epigraph_violation_kg"])
        print("Witness exact-frontier equality residual kg :", witness["exact_frontier_equality_residual_kg"])
        print("Witness feasible within frozen tolerance    :", witness_feasible_at_scientific_tol)
        print("Exact Stage2 without presolve success       :", exact_no_presolve["success"])
        print("Bounded frontier feasible                   :", bounded_frontier_feasible)
        print("Minimum tested feasible delta kg            :", minimum_tested_feasible_delta)
        print("Realized mass loss at first feasible kg     :", realized_mass_loss)
        print("R25-R2 design-only authorized               : True")
        print("State/support/mapback/time mutation         : False / False / False / False")
        print("P3 authorized                               : False")
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
                "R25_SCIENTIFIC_FAIL_preserved": True,
                "R24_design_preserved": True,
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
