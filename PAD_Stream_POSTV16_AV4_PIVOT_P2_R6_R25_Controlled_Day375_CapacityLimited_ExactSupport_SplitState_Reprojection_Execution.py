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
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV4-PIVOT-P2-R6-R25"
NAME = "Controlled Day375 Capacity-Limited Exact-Support Split-State Reprojection Execution"

PASS = (
    "AV4PIVOTP2R6R25_DAY375_CAPACITY_LIMITED_EXACT_SUPPORT_SPLIT_STATE_"
    "REPROJECTION_EXECUTION_PASS_NO_MAPBACK_NO_TIME_ADVANCE"
)
FAIL = (
    "AV4PIVOTP2R6R25_DAY375_CAPACITY_LIMITED_EXACT_SUPPORT_SPLIT_STATE_"
    "REPROJECTION_EXECUTION_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN"
)
BLOCK = "AV4PIVOTP2R6R25_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "47fa72580abc51ef029fdb15ecb9f5c45f27cf0c"

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

MASS_TOL = 1.0e-6
LEDGER_TOL = 1.0e-6
CAPACITY_TOL = 1.0e-7
OPT_REL_TOL = 1.0e-10
SAT_TOL = 1.0e-10

R24_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R24_"
    "Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze"
)
R24_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_Summary.json"
R24_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P2_R6_R24_ExactSupport_Capacity_Diagnostic.json"
R24_PROTOCOL = "POSTV16_AV4_PIVOT_P2_R6_R24_Capacity_Aware_Reprojection_Protocol.json"
R24_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R24_Decision_Contract.json"
R24_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R24_Artifact_Manifest.csv"

R24_STATUS = (
    "AV4PIVOTP2R6R24_DAY375_R22_GEOMETRY_REPROJECTION_CAPACITY_"
    "REPRESENTATION_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
R24_CLASSIFICATION = (
    "R6R24_EXACT_R22_SUPPORT_CANNOT_REPRESENT_ALL_S0_MASS_WITHIN_CV_CAPACITY_"
    "CAPACITY_LIMITED_SPLIT_STATE_WITH_MINIMUM_S0_RESIDUAL_REQUIRED_"
    "CONTROLLED_EXECUTION_NEXT"
)

R24_MAX_REPRESENTABLE_S0_MASS_KG = 52457458.82473308
R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG = 6646660.64504873
R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_FRACTION = 0.1124568085046419
R24_S0_MASS_KG = 59104119.46978181
R24_EXACT_SUPPORT_EDGE_COUNT = 269532
R24_S0_CELL_COUNT = 20702
R24_ACTIVE_CV_COUNT = 215600

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
ACCEPTED_TRANSPORT_R20_SHA256 = "e209adb5a169008698db9acb24e5cade82df3f6991b5174515d5957901bceb67"

F1R2_REL = BASE / "POSTV16_AV4_F1_R2_Restart_State_and_Conservative_Parent_Projection_Freeze"
F1R2_RESTART_STATE = "POSTV16_AV4_F1_R2_Restart_State_Authority_Contract.json"
F1R2_PROJECTION = "POSTV16_AV4_F1_R2_Conservative_Grid_to_Streamline_Projection_Protocol.json"
F1R2_RESIDUAL = "POSTV16_AV4_F1_R2_Residual_Grid_State_Sidecar_Contract.json"
F1R2_DECISION = "POSTV16_AV4_F1_R2_Decision_Contract.json"
F1R2_MANIFEST = "POSTV16_AV4_F1_R2_Artifact_Manifest.csv"

R24_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_"
    "Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze.py"
)
R24_BLOB = "9168baf3155e712b9c342239bed9ab4b1d787691"

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
    R24_RUNNER: R24_BLOB,
    R22_RUNNER: R22_BLOB,
    F1R2_RUNNER: F1R2_BLOB,
    SG7D: SG7D_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R25"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution"
)
FAIL_REL = BASE / (OUT_TOKEN + "_SCIENTIFIC_FAIL")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_array_forbidden:{key}")
            buf = io.BytesIO()
            np.save(buf, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, buf.getvalue())
    return outer.getvalue()


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

    edge_cv = (uniq // NCELL).astype(np.int64)
    edge_cell = (uniq % NCELL).astype(np.int64)

    return edge_cv, edge_cell, np.asarray(target, dtype=np.float64)


def stage1_max_representable(
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

    A_ub = sparse.coo_matrix(
        (data, (rows, cols)),
        shape=(ncell + ncv, nedge),
    ).tocsr()
    b_ub = np.concatenate([gm[active_cells], cap[active_cvs]])

    lp = linprog(
        -np.ones(nedge, dtype=np.float64),
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )

    if not lp.success:
        raise ScientificFail("stage1_max_representable_HiGHS", [lp.status, lp.message])

    x = np.asarray(lp.x, dtype=np.float64)
    represented = float(np.sum(x))

    return {
        "x": x,
        "represented_mass_kg": represented,
        "solver_status": int(lp.status),
        "solver_message": str(lp.message),
    }


def stage2_min_l1_to_target(
    grid_mass: np.ndarray,
    cv_capacity: np.ndarray,
    edge_cv: np.ndarray,
    edge_cell: np.ndarray,
    target: np.ndarray,
    represented_mass_kg: float,
) -> dict[str, Any]:
    from scipy import sparse
    from scipy.optimize import linprog

    gm = np.asarray(grid_mass, dtype=np.float64).reshape(-1)
    cap = np.asarray(cv_capacity, dtype=np.float64).reshape(-1)
    edge_cv = np.asarray(edge_cv, dtype=np.int64).reshape(-1)
    edge_cell = np.asarray(edge_cell, dtype=np.int64).reshape(-1)
    target = np.asarray(target, dtype=np.float64).reshape(-1)

    nedge = len(edge_cv)
    if len(edge_cell) != nedge or len(target) != nedge:
        raise GateError("stage2_parallel_length_mismatch")

    active_cells = np.unique(edge_cell)
    active_cvs = np.unique(edge_cv)
    cell_row = np.searchsorted(active_cells, edge_cell)
    cv_row = np.searchsorted(active_cvs, edge_cv)
    ncell = len(active_cells)
    ncv = len(active_cvs)

    nvar = 2 * nedge

    rows_supply = np.concatenate([cell_row, ncell + cv_row])
    cols_supply = np.concatenate([
        np.arange(nedge, dtype=np.int64),
        np.arange(nedge, dtype=np.int64),
    ])
    data_supply = np.ones(2 * nedge, dtype=np.float64)
    A_supply = sparse.coo_matrix(
        (data_supply, (rows_supply, cols_supply)),
        shape=(ncell + ncv, nvar),
    ).tocsr()
    b_supply = np.concatenate([gm[active_cells], cap[active_cvs]])

    r = np.arange(nedge, dtype=np.int64)
    rows_abs = np.concatenate([r, r, nedge + r, nedge + r])
    cols_abs = np.concatenate([
        r,
        nedge + r,
        r,
        nedge + r,
    ])
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

    A_ub = sparse.vstack([A_supply, A_abs], format="csr")
    b_ub = np.concatenate([b_supply, b_abs])

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
        method="highs",
        options={"presolve": True},
    )

    if not lp.success:
        raise ScientificFail("stage2_min_L1_HiGHS", [lp.status, lp.message])

    z = np.asarray(lp.x, dtype=np.float64)
    x = z[:nedge]
    d = z[nedge:]

    return {
        "x": x,
        "d": d,
        "L1_objective_kg": float(np.sum(d)),
        "solver_status": int(lp.status),
        "solver_message": str(lp.message),
    }


def selftest() -> None:
    assert NCVT == NSL * NCV
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert FAIL_REL.name == OUT_TOKEN + "_SCIENTIFIC_FAIL"
    assert BLOCK_REL.name == OUT_TOKEN + "_BLOCKED"

    from scipy import sparse
    from scipy.optimize import linprog

    # x0+x1=3; target=(1,4); caps x0,x1<=2.
    # Unique L1 optimum is x=(1,2), d=(0,2), objective=2.
    c = np.asarray([0.0, 0.0, 1.0, 1.0])

    rows = []
    cols = []
    data = []
    b = []

    def add(row, entries, rhs):
        for col, val in entries:
            rows.append(row)
            cols.append(col)
            data.append(val)
        b.append(rhs)

    add(0, [(0,1.0),(2,-1.0)], 1.0)
    add(1, [(0,-1.0),(2,-1.0)], -1.0)
    add(2, [(1,1.0),(3,-1.0)], 4.0)
    add(3, [(1,-1.0),(3,-1.0)], -4.0)

    A_abs = sparse.coo_matrix(
        (np.asarray(data), (np.asarray(rows), np.asarray(cols))),
        shape=(4,4),
    ).tocsr()

    A_cap = sparse.csr_matrix(
        (
            np.asarray([1.0,1.0]),
            (np.asarray([0,1]), np.asarray([0,1])),
        ),
        shape=(2,4),
    )

    A_eq = sparse.csr_matrix(
        (
            np.asarray([1.0,1.0]),
            (np.asarray([0,0]), np.asarray([0,1])),
        ),
        shape=(1,4),
    )

    lp = linprog(
        c,
        A_ub=sparse.vstack([A_cap,A_abs]),
        b_ub=np.asarray([2.0,2.0] + b, dtype=float),
        A_eq=A_eq,
        b_eq=np.asarray([3.0]),
        bounds=[(0,None)]*4,
        method="highs",
    )

    assert lp.success
    assert abs(float(lp.fun) - 2.0) < 1e-10
    assert np.allclose(lp.x[:2], [1.0,2.0], atol=1e-10)

    print("POSTV16 AV4 PIVOT P2-R6-R25 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()

    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL

    stage = "preflight"
    gates: list[dict[str, Any]] = []
    execution_started = False

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

    def sci_gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "scientific_execution_gate": True,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise ScientificFail(name, detail)

    try:
        stage = "preexisting_state_firewall"

        pass_summary = out / f"PAD_Stream_{OUT_TOKEN}_Summary.json"
        fail_report = fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json"
        block_report = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"

        gate("no_preexisting_R25_PASS", not pass_summary.exists(), str(pass_summary))
        gate("no_preexisting_R25_FAIL", not fail_report.exists(), str(fail_report))
        gate("no_preexisting_R25_BLOCK", not block_report.exists(), str(block_report))

        stage = "repository_authority"

        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R24_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        stage = "R24_design_authority"

        r24 = drive / R24_REL
        manifest(r24, R24_MANIFEST)
        s24 = js(r24 / R24_SUMMARY)
        p24 = js(r24 / R24_PROTOCOL)
        d24 = js(r24 / R24_DECISION)

        gate("R24_status_exact", s24.get("status") == R24_STATUS, s24.get("status"))
        gate("R24_classification_exact", s24.get("classification") == R24_CLASSIFICATION, s24.get("classification"))
        gate("R24_full_S0_infeasible", s24.get("full_S0_exact_support_capacity_feasible") is False)
        gate("R24_representation_amendment_required", s24.get("representation_amendment_required") is True)
        gate("R24_CV_inversion_PASS", s24.get("max_representable_CV_inversion_PASS") is True)
        gate("R25_authorized", d24.get("P2_R6_R25_authorized") is True)
        gate("R25_execution_authorized", d24.get("P2_R6_R25_execution_authorized") is True)
        gate("old_CV_reuse_forbidden", d24.get("old_CV_cell_ownership_direct_reuse_authorized") is False)
        gate("support_growth_forbidden", d24.get("automatic_support_growth_authorized") is False)
        gate("reverse_H1_pullback_forbidden", d24.get("reverse_H1_to_S0_pullback_authorized") is False)
        gate("mapback_forbidden", d24.get("mapback_execution_authorized") is False)
        gate("time_advance_forbidden", d24.get("physical_time_advance_authorized") is False)

        gate(
            "R24_max_representable_mass_exact",
            abs(float(s24["maximum_representable_S0_mass_kg"]) - R24_MAX_REPRESENTABLE_S0_MASS_KG)
            <= 1e-6,
            s24["maximum_representable_S0_mass_kg"],
        )
        gate(
            "R24_minimum_residual_exact",
            abs(float(s24["minimum_unavoidable_S0_residual_kg"]) - R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG)
            <= 1e-6,
            s24["minimum_unavoidable_S0_residual_kg"],
        )
        gate(
            "R24_protocol_stage1_exact",
            p24.get("R25_lexicographic_execution_objective", {}).get("stage1")
            == (
                "maximize total accepted Day375 Cartesian component mass represented on "
                "R22 exact (cell,CV) support subject to per-cell supply and frozen CV capacity"
            ),
        )
        gate(
            "R24_protocol_stage2_exact",
            p24.get("R25_lexicographic_execution_objective", {}).get("stage2")
            == (
                "subject to the stage1 optimum, minimize L1 deviation from the original "
                "F1-R2 PV-normalized-transpose edge-mass target"
            ),
        )
        gate(
            "R24_protocol_stage3_exact",
            p24.get("R25_lexicographic_execution_objective", {}).get("stage3")
            == (
                "publish exact residual Cartesian sidecar as parent grid mass minus the "
                "cellwise mass represented on R22 support"
            ),
        )

        stage = "R22_pressure_state_authority"

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
            producer_labels = np.asarray(z["producer_labels"]).astype("U32")
            streamline_id = np.asarray(z["streamline_id"], dtype=np.int64)

        with np.load(pressure_epoch_path, allow_pickle=False) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            grid_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            source_r20_sha = str(np.asarray(z["accepted_transport_base_R20_sha256"]).reshape(()))

        gate("R22_geometry_shapes_exact", xyz.shape == (NSL, NN, 3) and tof_s.shape == (NSL, NN))
        gate("R22_weight_shape_positive", weight_m3_s.shape == (NSL,) and np.all(weight_m3_s > 0.0))
        gate("R22_streamline_ID_exact", np.array_equal(streamline_id, np.arange(NSL, dtype=np.int64)))
        gate("pressure_shape_exact", pressure.shape == GRID)
        gate("grid_mass_shape_nonnegative", grid_mass.shape == GRID and float(np.min(grid_mass)) >= -MASS_TOL)
        gate("accepted_transport_R20_SHA_exact", source_r20_sha == ACCEPTED_TRANSPORT_R20_SHA256)

        stage = "F1R2_semantics"

        f1 = drive / F1R2_REL
        manifest(f1, F1R2_MANIFEST)
        restart = js(f1 / F1R2_RESTART_STATE)
        projection = js(f1 / F1R2_PROJECTION)
        decision_f1 = js(f1 / F1R2_DECISION)

        gate(
            "Cartesian_mass_primary",
            restart.get("recurrent_state_principle")
            == (
                "Cartesian component mass is the authoritative global recurrent physical state. "
                "Streamline control-volume mass is a conservative transport-coordinate representation "
                "derived from that state at each refreshed-flow epoch."
            ),
        )
        gate(
            "normalized_transpose_target_authority_bound",
            projection.get("name") == "Exact-support normalized-transpose mass projection with residual grid sidecar",
        )
        gate(
            "reverse_H1_forbidden",
            "no reverse H1->S0 physical transport" in projection.get("prohibitions", []),
        )
        gate("split_state_contract_frozen", decision_f1.get("split_restart_state_contract_frozen") is True)

        stage = "exact_support_capacity_reconstruction"

        sg7d = mod(root / SG7D, "r25_sg7d")
        e37a = mod(root / E37A, "r25_e37a")
        r2 = mod(root / R2, "r25_r2")

        op = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weight_m3_s * DAY_TO_S,
        )

        edge_cv, edge_cell, target = build_edge_target_and_support(grid_mass, op)

        sci_gate("exact_support_edge_count_R24", len(edge_cv) == R24_EXACT_SUPPORT_EDGE_COUNT, len(edge_cv))
        sci_gate("exact_support_S0_cell_count_R24", len(np.unique(edge_cell)) == R24_S0_CELL_COUNT, len(np.unique(edge_cell)))
        sci_gate("exact_support_active_CV_count_R24", len(np.unique(edge_cv)) == R24_ACTIVE_CV_COUNT, len(np.unique(edge_cv)))

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
        sci_gate("CV_capacity_shape_positive", cv_capacity.shape == (NSL, NCV) and np.all(cv_capacity > 0.0))

        execution_started = True

        stage = "stage1_maximum_representable_mass"

        st1 = stage1_max_representable(
            grid_mass,
            cv_capacity,
            edge_cv,
            edge_cell,
        )

        stage1_mass = float(st1["represented_mass_kg"])
        stage1_tol = max(MASS_TOL, OPT_REL_TOL * max(abs(R24_MAX_REPRESENTABLE_S0_MASS_KG), 1.0))

        sci_gate(
            "stage1_mass_matches_R24",
            abs(stage1_mass - R24_MAX_REPRESENTABLE_S0_MASS_KG) <= stage1_tol,
            {
                "R25": stage1_mass,
                "R24": R24_MAX_REPRESENTABLE_S0_MASS_KG,
                "tol": stage1_tol,
            },
        )

        stage = "stage2_minimum_L1_deviation"

        st2 = stage2_min_l1_to_target(
            grid_mass,
            cv_capacity,
            edge_cv,
            edge_cell,
            target,
            stage1_mass,
        )

        x = np.asarray(st2["x"], dtype=np.float64)
        d = np.asarray(st2["d"], dtype=np.float64)

        sci_gate("stage2_nonnegative_assignment", float(np.min(x)) >= -MASS_TOL, float(np.min(x)))
        sci_gate("stage2_abs_deviation_nonnegative", float(np.min(d)) >= -MASS_TOL, float(np.min(d)))

        stage2_total = float(np.sum(x))
        sci_gate(
            "stage2_preserves_stage1_optimum",
            abs(stage2_total - stage1_mass) <= stage1_tol,
            [stage2_total, stage1_mass, stage1_tol],
        )

        assigned_cell = np.bincount(edge_cell, weights=x, minlength=NCELL)
        assigned_cv = np.bincount(edge_cv, weights=x, minlength=NCVT).reshape(NSL, NCV)

        grid_flat = grid_mass.reshape(-1)
        residual_flat = grid_flat - assigned_cell
        residual_flat[np.abs(residual_flat) < 1.0e-12] = 0.0
        residual_grid = residual_flat.reshape(GRID)

        cell_supply_excess = float(np.max(assigned_cell - grid_flat))
        cv_capacity_excess = float(np.max(assigned_cv - cv_capacity))
        residual_min = float(np.min(residual_grid))

        sci_gate("cell_supply_not_exceeded", cell_supply_excess <= MASS_TOL, cell_supply_excess)
        sci_gate("CV_capacity_not_exceeded", cv_capacity_excess <= CAPACITY_TOL, cv_capacity_excess)
        sci_gate("residual_grid_nonnegative", residual_min >= -MASS_TOL, residual_min)

        total_grid = float(np.sum(grid_mass))
        total_cv = float(np.sum(assigned_cv))
        total_residual = float(np.sum(residual_grid))
        global_ledger = total_cv + total_residual - total_grid

        sci_gate("global_split_state_ledger_closed", abs(global_ledger) <= LEDGER_TOL, global_ledger)

        s0 = np.unique(edge_cell)
        outside_mask = np.ones(NCELL, dtype=bool)
        outside_mask[s0] = False
        s0_residual = float(np.sum(residual_flat[s0]))
        outside_residual = float(np.sum(residual_flat[outside_mask]))
        s0_mass = float(np.sum(grid_flat[s0]))

        residual_tol = max(MASS_TOL, OPT_REL_TOL * max(abs(R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG), 1.0))

        sci_gate(
            "S0_mass_matches_R24",
            abs(s0_mass - R24_S0_MASS_KG) <= max(MASS_TOL, OPT_REL_TOL * R24_S0_MASS_KG),
            [s0_mass, R24_S0_MASS_KG],
        )
        sci_gate(
            "minimum_unavoidable_S0_residual_matches_R24",
            abs(s0_residual - R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG) <= residual_tol,
            [s0_residual, R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG, residual_tol],
        )

        min_fraction = s0_residual / max(s0_mass, 1.0e-30)
        sci_gate(
            "minimum_unavoidable_S0_residual_fraction_matches_R24",
            abs(min_fraction - R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_FRACTION) <= 1.0e-10,
            [min_fraction, R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_FRACTION],
        )

        stage = "CV_mass_to_saturation_inversion"

        try:
            cv_sat = e37a.invert_cv_mass_to_saturation(
                r2,
                assigned_cv,
                geometry["cv_pressure_mass_coeff"],
            )
        except Exception as exc:
            raise ScientificFail("CV_mass_inversion", repr(exc)) from exc

        reconstructed_cv = e37a.cv_mass_from_saturation(
            r2,
            cv_sat,
            geometry["cv_pressure_mass_coeff"],
        )
        cv_reconstruction_error = float(np.max(np.abs(reconstructed_cv - assigned_cv)))
        cv_reconstruction_tol = max(
            1.0e-6,
            1.0e-10 * max(float(np.max(assigned_cv)), 1.0),
        )

        sci_gate(
            "CV_mass_inversion_reconstruction",
            cv_reconstruction_error <= cv_reconstruction_tol,
            [cv_reconstruction_error, cv_reconstruction_tol],
        )
        sci_gate(
            "CV_saturation_bounds",
            float(np.min(cv_sat)) >= 0.20 - SAT_TOL
            and float(np.max(cv_sat)) <= 0.80 + SAT_TOL,
            [float(np.min(cv_sat)), float(np.max(cv_sat))],
        )

        stage = "lexicographic_objective_closure"

        exact_abs = np.abs(x - target)
        L1_exact = float(np.sum(exact_abs))
        d_slack = float(np.max(np.abs(d - exact_abs)))

        sci_gate(
            "stage2_reported_L1_matches_exact",
            abs(float(st2["L1_objective_kg"]) - L1_exact)
            <= max(1e-6, 1e-10 * max(L1_exact, 1.0)),
            [st2["L1_objective_kg"], L1_exact],
        )
        sci_gate(
            "stage2_abs_auxiliary_exact",
            d_slack <= max(1e-6, 1e-10 * max(float(np.max(exact_abs)), 1.0)),
            d_slack,
        )

        stage = "PASS_publication"

        state_arrays = {
            "canonical_day": np.asarray(DAY, dtype=np.float64),
            "source_R22_flow_epoch_sha256": np.asarray(R22_EPOCH_SHA256, dtype="U64"),
            "source_pressure_epoch_sha256": np.asarray(PRESSURE_EPOCH_SHA256, dtype="U64"),
            "source_R20_accepted_transport_state_sha256": np.asarray(ACCEPTED_TRANSPORT_R20_SHA256, dtype="U64"),
            "source_R24_maximum_representable_S0_mass_kg": np.asarray(
                R24_MAX_REPRESENTABLE_S0_MASS_KG,
                dtype=np.float64,
            ),
            "cartesian_component_mass_kg": np.asarray(grid_mass, dtype=np.float64),
            "transport_CV_component_mass_kg": np.asarray(assigned_cv, dtype=np.float64),
            "transport_CV_saturation": np.asarray(cv_sat, dtype=np.float64),
            "grid_residual_component_mass_kg": np.asarray(residual_grid, dtype=np.float64),
            "represented_cartesian_cell_mass_kg": np.asarray(
                assigned_cell.reshape(GRID),
                dtype=np.float64,
            ),
            "exact_support_edge_cv": np.asarray(edge_cv, dtype=np.int64),
            "exact_support_edge_cell": np.asarray(edge_cell, dtype=np.int64),
            "exact_support_edge_assigned_mass_kg": np.asarray(x, dtype=np.float64),
            "F1R2_normalized_transpose_edge_target_mass_kg": np.asarray(target, dtype=np.float64),
            "streamline_xyz_m": np.asarray(xyz, dtype=np.float64),
            "streamline_tof_s": np.asarray(tof_s, dtype=np.float64),
            "streamline_weight_m3_s": np.asarray(weight_m3_s, dtype=np.float64),
            "producer_labels": np.asarray(producer_labels, dtype="U32"),
            "streamline_id": np.asarray(streamline_id, dtype=np.int64),
            "refreshed_pressure_psi": np.asarray(pressure, dtype=np.float64),
            "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
            "stage1_maximum_representable_mass_kg": np.asarray(stage1_mass, dtype=np.float64),
            "stage2_L1_deviation_kg": np.asarray(L1_exact, dtype=np.float64),
            "minimum_unavoidable_S0_residual_kg": np.asarray(s0_residual, dtype=np.float64),
            "outside_S0_residual_kg": np.asarray(outside_residual, dtype=np.float64),
            "global_split_state_ledger_residual_kg": np.asarray(global_ledger, dtype=np.float64),
            "representation_amendment_required": np.asarray(True, dtype=np.bool_),
            "old_CV_cell_ownership_reused": np.asarray(False, dtype=np.bool_),
            "support_growth_executed": np.asarray(False, dtype=np.bool_),
            "reverse_H1_to_S0_pullback_executed": np.asarray(False, dtype=np.bool_),
            "mapback_executed": np.asarray(False, dtype=np.bool_),
            "transport_time_advanced": np.asarray(False, dtype=np.bool_),
            "physical_time_advanced": np.asarray(False, dtype=np.bool_),
        }

        object_keys = [
            k for k, v in state_arrays.items()
            if np.asarray(v).dtype == object
        ]
        sci_gate("state_contains_no_object_arrays", not object_keys, object_keys)

        state_bytes = deterministic_npz_bytes(state_arrays)

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": (
                "R6R25_CAPACITY_LIMITED_EXACT_SUPPORT_SPLIT_STATE_REPROJECTION_EXECUTION_PASS_"
                "DAY375_RESTART_REPRESENTATION_ACCEPTANCE_AUDIT_NEXT"
            ),
            "source_R22_flow_epoch_sha256": R22_EPOCH_SHA256,
            "source_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "source_R20_accepted_transport_state_sha256": ACCEPTED_TRANSPORT_R20_SHA256,
            "R24_maximum_representable_S0_mass_kg": R24_MAX_REPRESENTABLE_S0_MASS_KG,
            "stage1_reproduced_maximum_representable_mass_kg": stage1_mass,
            "stage2_L1_deviation_from_F1R2_target_kg": L1_exact,
            "exact_support_edge_count": int(len(edge_cv)),
            "exact_support_S0_cell_count": int(len(s0)),
            "active_CV_count": int(len(np.unique(edge_cv))),
            "transport_CV_total_mass_kg": total_cv,
            "grid_residual_total_mass_kg": total_residual,
            "S0_residual_mass_kg": s0_residual,
            "S0_residual_fraction_of_S0": min_fraction,
            "outside_S0_residual_mass_kg": outside_residual,
            "global_split_state_ledger_residual_kg": global_ledger,
            "maximum_cell_supply_excess_kg": max(0.0, cell_supply_excess),
            "maximum_CV_capacity_excess_kg": max(0.0, cv_capacity_excess),
            "CV_mass_inversion_max_error_kg": cv_reconstruction_error,
            "CV_saturation_min": float(np.min(cv_sat)),
            "CV_saturation_max": float(np.max(cv_sat)),
            "representation_amendment_executed": True,
            "old_CV_cell_ownership_reused": False,
            "support_growth_executed": False,
            "reverse_H1_to_S0_pullback_executed": False,
            "mapback_executed": False,
            "transport_time_advance_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        execution_contract = {
            "milestone": M,
            "status": PASS,
            "representation": (
                "capacity-limited exact-support split state: capacity-feasible R22 CV mass "
                "+ exact Cartesian residual sidecar"
            ),
            "primary_recurrent_authority": "cartesian_component_mass_kg",
            "transport_coordinate_state": {
                "component_mass": "transport_CV_component_mass_kg",
                "saturation": "transport_CV_saturation",
                "shape": [NSL, NCV],
                "exact_R22_support_only": True,
            },
            "residual_grid_state": {
                "component_mass": "grid_residual_component_mass_kg",
                "shape": list(GRID),
                "includes_outside_S0_mass": True,
                "includes_minimum_unavoidable_S0_residual": True,
                "minimum_unavoidable_S0_residual_kg": s0_residual,
            },
            "lexicographic_execution": {
                "stage1_maximum_representable_mass_kg": stage1_mass,
                "stage2_L1_deviation_from_F1R2_target_kg": L1_exact,
                "stage1_optimum_preserved_in_stage2": True,
            },
            "firewalls": {
                "old_CV_cell_ownership_reused": False,
                "support_growth": False,
                "reverse_H1_to_S0_pullback": False,
                "mass_discard_or_clipping": False,
                "global_mass_rescaling": False,
                "mapback": False,
                "transport_time_advance": False,
                "physical_time_advance": False,
                "P3_authorized": False,
            },
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "P2_R6_R26_authorized": True,
            "P2_R6_R26_name": (
                "Day375 Capacity-Limited Split-State Restart Representation Closure and Acceptance Audit"
            ),
            "P2_R6_R26_design_or_diagnostic_only": True,
            "P2_R6_R26_must_bind_R25_state_SHA": True,
            "accepted_Day375_cartesian_component_mass_remains_primary_authority": True,
            "R22_flow_geometry_remains_authoritative": True,
            "accepted_Day375_pressure_epoch_remains_authoritative": True,
            "capacity_limited_split_state_is_provisional_until_R26_acceptance": True,
            "transport_execution_authorized": False,
            "mapback_execution_authorized": False,
            "transport_time_advance_authorized": False,
            "physical_time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        out.mkdir(parents=True, exist_ok=False)

        state_name = f"{OUT_TOKEN}_CapacityLimited_SplitState_Day375.npz"
        state_path = out / state_name
        state_path.write_bytes(state_bytes)
        state_sha = sha(state_path)

        summary["capacity_limited_split_state_sha256"] = state_sha
        execution_contract["capacity_limited_split_state_sha256"] = state_sha
        decision["P2_R6_R26_R25_state_sha256"] = state_sha

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Execution_Contract.json").write_bytes(jb(execution_contract))
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
        print("Capacity-limited split-state SHA256        :", state_sha)
        print("Stage1 maximum representable mass kg       :", stage1_mass)
        print("Stage2 L1 deviation kg                     :", L1_exact)
        print("Transport CV total mass kg                 :", total_cv)
        print("Grid residual total mass kg                :", total_residual)
        print("S0 residual mass kg                        :", s0_residual)
        print("S0 residual fraction                       :", min_fraction)
        print("Outside-S0 residual mass kg                :", outside_residual)
        print("Global split-state ledger residual kg      :", global_ledger)
        print("Maximum CV capacity excess kg              :", max(0.0, cv_capacity_excess))
        print("CV saturation min / max                    :", float(np.min(cv_sat)), "/", float(np.max(cv_sat)))
        print("Old CV ownership / support growth          : False / False")
        print("Reverse H1 pullback / mapback / time       : False / False / False")
        print("R26 closure/acceptance audit authorized    : True")
        print("P3 authorized                              : False")
        print("=" * 190)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True, exist_ok=True)
        p = fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": FAIL,
                "failed_stage": stage,
                "failed_gate": exc.gate,
                "detail": exc.detail,
                "execution_started": execution_started,
                "R24_design_preserved": True,
                "R22_flow_epoch_preserved": True,
                "accepted_pressure_epoch_preserved": True,
                "accepted_cartesian_state_preserved": True,
                "automatic_rerun_authorized": False,
                "support_growth_authorized": False,
                "mapback_authorized": False,
                "physical_time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "SCIENTIFIC FAIL")
        print("Stage :", stage)
        print("Gate  :", exc.gate)
        print("Detail:", exc.detail)
        print("NO AUTOMATIC RERUN / SUPPORT GROWTH / MAPBACK / TIME ADVANCE.")
        print("=" * 190)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "execution_started": execution_started,
                "R24_design_preserved": True,
                "R22_flow_epoch_preserved": True,
                "accepted_pressure_epoch_preserved": True,
                "accepted_cartesian_state_preserved": True,
                "automatic_rerun_authorized": False,
                "support_growth_authorized": False,
                "mapback_authorized": False,
                "physical_time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO AUTOMATIC RERUN / SUPPORT GROWTH / MAPBACK / TIME ADVANCE.")
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
