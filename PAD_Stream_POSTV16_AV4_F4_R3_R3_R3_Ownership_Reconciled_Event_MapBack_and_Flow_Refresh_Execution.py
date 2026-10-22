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
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3"

STATUS_PASS = (
    "AV4F4R3R3R3_FROZEN_BOUNDED_PARENT_OWNERSHIP_EVENT_MAPBACK_EXECUTED_"
    "EXACT_EVENT_CV_MASS_AND_CARTESIAN_CAPACITY_PASS_SINGLE_SAME_TIME_FLOW_"
    "REFRESH_AND_REFRESHED_GEOMETRY_REPROJECTION_PASS_NO_PHYSICAL_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3_FROZEN_EVENT_MAPBACK_OR_SINGLE_FLOW_REFRESH_OR_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_SUPPORT_EXPANSION_NO_ALTERNATE_REPAIR_NO_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4F4R3R3R3_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R2_COMMIT = "5439d532072a0a5fc7717343ef39cc23789d6891"

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

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R2_"
    "Bounded_Parent_Ownership_Event_MapBack_Reconciliation_Freeze.py"
)
R3R2_BLOB = "247e1e5b6d3fc83bd81d3dd84f0bbeb88c5280c0"

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
    R3R2: R3R2_BLOB,
    R3R3: R3R3_BLOB,
    R3R1R2: R3R1R2_BLOB,
    F4R3: F4R3_BLOB,
    F2R3: F2R3_BLOB,
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

R3R2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R2_Bounded_Parent_Ownership_Event_MapBack_Freeze"
)
R3R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R2_Summary.json"
R3R2_PROTOCOL = "POSTV16_AV4_F4_R3_R3_R2_Frozen_MapBack_Reconciliation_Protocol.json"
R3R2_HANDOFF = "POSTV16_AV4_F4_R3_R3_R2_R3R3R3_Execution_Handoff_Contract.json"
R3R2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R2_Artifact_Manifest.csv"
R3R2_STATUS = (
    "AV4F4R3R3R2_R3R3R1R1R1_MIXED_COVERAGE_PARENT_OWNERSHIP_VS_RAW_EOS_"
    "DISAGGREGATION_FAILURE_BOUND_SINGLE_CONSERVATIVE_BOUNDED_PARENT_OWNERSHIP_"
    "CV_TO_CARTESIAN_EVENT_MAPBACK_RECONCILIATION_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

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

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_Ownership_Reconciled_Event_MapBack_and_Flow_Refresh"
)
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_BLOCKED"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


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
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


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
    return s.getvalue().encode()


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


def aggregate_pairs(
    cv_id: np.ndarray,
    flat_cell: np.ndarray,
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cv = np.asarray(cv_id, dtype=np.int64).reshape(-1)
    cell = np.asarray(flat_cell, dtype=np.int64).reshape(-1)
    val = np.asarray(values, dtype=np.float64).reshape(-1)
    if not (len(cv) == len(cell) == len(val)):
        raise GateError("pair_aggregation_length_mismatch")
    key = cv * NCELL + cell
    uniq, inverse = np.unique(key, return_inverse=True)
    sums = np.bincount(inverse, weights=val, minlength=len(uniq)).astype(np.float64)
    pair_cv = (uniq // NCELL).astype(np.int64)
    pair_cell = (uniq % NCELL).astype(np.int64)
    order = np.lexsort((pair_cell, pair_cv))
    return pair_cv[order], pair_cell[order], sums[order], uniq[order]


def incidence_matrix(rows_idx: np.ndarray, nrows: int, ncols: int) -> csr_matrix:
    cols = np.arange(ncols, dtype=np.int64)
    data = np.ones(ncols, dtype=np.float64)
    return coo_matrix(
        (data, (np.asarray(rows_idx, dtype=np.int64), cols)),
        shape=(nrows, ncols),
    ).tocsr()


def solve_stage1(
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    target: np.ndarray,
    event_cv_mass: np.ndarray,
    available_capacity: np.ndarray,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    n = len(target)
    Aeq_x = incidence_matrix(pair_cv, NCVTOTAL, n)
    Acap_x = incidence_matrix(pair_cell, NCELL, n)
    # |x-T| <= u -> x-u<=T and -x-u<=-T
    from scipy.sparse import eye
    I = eye(n, format="csr")
    A_abs = vstack(
        [
            hstack([I, -I], format="csr"),
            hstack([-I, -I], format="csr"),
        ],
        format="csr",
    )
    b_abs = np.concatenate([target, -target])

    A_cap = hstack([Acap_x, csr_matrix((NCELL, n))], format="csr")

    Aub = vstack([A_abs, A_cap], format="csr")
    bub = np.concatenate([b_abs, available_capacity])

    Aeq = hstack([Aeq_x, csr_matrix((NCVTOTAL, n))], format="csr")
    beq = np.asarray(event_cv_mass, dtype=np.float64).reshape(-1)

    c = np.concatenate([np.zeros(n), np.ones(n)])
    bounds = [(0.0, None)] * (2 * n)

    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=beq,
        bounds=bounds,
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "stage1_parent_ownership_L1_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x[:n], dtype=np.float64)
    obj = float(np.sum(np.asarray(res.x[n:], dtype=np.float64)))
    return x, obj, {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def solve_stage2(
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    target: np.ndarray,
    qtarget: np.ndarray,
    event_cv_mass: np.ndarray,
    available_capacity: np.ndarray,
    primary_opt: float,
    primary_tol: float,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    from scipy.sparse import eye

    n = len(target)
    I = eye(n, format="csr")
    Z = csr_matrix((n, n))
    Aeq_x = incidence_matrix(pair_cv, NCVTOTAL, n)
    Acap_x = incidence_matrix(pair_cell, NCELL, n)

    # Variables [x,u,v].
    rows = [
        hstack([I, -I, Z], format="csr"),
        hstack([-I, -I, Z], format="csr"),
        hstack([I, Z, -I], format="csr"),
        hstack([-I, Z, -I], format="csr"),
        hstack([Acap_x, csr_matrix((NCELL, 2 * n))], format="csr"),
    ]
    Aub = vstack(rows, format="csr")
    bub = np.concatenate(
        [target, -target, qtarget, -qtarget, available_capacity]
    )

    # Freeze stage-1 objective: sum u <= opt+tol.
    primary_row = csr_matrix(
        (
            np.ones(n),
            (
                np.zeros(n, dtype=np.int64),
                n + np.arange(n, dtype=np.int64),
            ),
        ),
        shape=(1, 3 * n),
    )
    Aub = vstack([Aub, primary_row], format="csr")
    bub = np.concatenate([bub, [primary_opt + primary_tol]])

    Aeq = hstack(
        [Aeq_x, csr_matrix((NCVTOTAL, 2 * n))],
        format="csr",
    )
    beq = np.asarray(event_cv_mass, dtype=np.float64).reshape(-1)

    c = np.concatenate([np.zeros(2 * n), np.ones(n)])
    bounds = [(0.0, None)] * (3 * n)

    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=beq,
        bounds=bounds,
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "stage2_raw_event_EOS_secondary_L1_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x[:n], dtype=np.float64)
    obj = float(np.sum(np.asarray(res.x[2 * n :], dtype=np.float64)))
    return x, obj, {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def solve_stage3(
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    target: np.ndarray,
    qtarget: np.ndarray,
    event_cv_mass: np.ndarray,
    available_capacity: np.ndarray,
    primary_opt: float,
    primary_tol: float,
    secondary_opt: float,
    secondary_tol: float,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    from scipy.sparse import eye

    n = len(target)
    I = eye(n, format="csr")
    Z = csr_matrix((n, n))
    Aeq_x = incidence_matrix(pair_cv, NCVTOTAL, n)
    Acap_x = incidence_matrix(pair_cell, NCELL, n)

    Aub = vstack(
        [
            hstack([I, -I, Z], format="csr"),
            hstack([-I, -I, Z], format="csr"),
            hstack([I, Z, -I], format="csr"),
            hstack([-I, Z, -I], format="csr"),
            hstack([Acap_x, csr_matrix((NCELL, 2 * n))], format="csr"),
        ],
        format="csr",
    )
    bub = np.concatenate(
        [target, -target, qtarget, -qtarget, available_capacity]
    )

    primary_row = csr_matrix(
        (
            np.ones(n),
            (
                np.zeros(n, dtype=np.int64),
                n + np.arange(n, dtype=np.int64),
            ),
        ),
        shape=(1, 3 * n),
    )
    secondary_row = csr_matrix(
        (
            np.ones(n),
            (
                np.zeros(n, dtype=np.int64),
                2 * n + np.arange(n, dtype=np.int64),
            ),
        ),
        shape=(1, 3 * n),
    )
    Aub = vstack([Aub, primary_row, secondary_row], format="csr")
    bub = np.concatenate(
        [
            bub,
            [primary_opt + primary_tol, secondary_opt + secondary_tol],
        ]
    )

    Aeq = hstack(
        [Aeq_x, csr_matrix((NCVTOTAL, 2 * n))],
        format="csr",
    )
    beq = np.asarray(event_cv_mass, dtype=np.float64).reshape(-1)

    # Deterministic tiny normalized lexicographic mass preference.
    rank = (np.arange(n, dtype=np.float64) + 1.0) / max(float(n), 1.0)
    c = np.concatenate([rank, np.zeros(2 * n)])
    bounds = [(0.0, None)] * (3 * n)

    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=beq,
        bounds=bounds,
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "stage3_deterministic_tiebreak_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x[:n], dtype=np.float64)
    obj = float(np.dot(rank, x))
    return x, obj, {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def execute_frozen_assignment(
    *,
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    parent_pair_mass: np.ndarray,
    raw_event_pair_mass: np.ndarray,
    parent_cv_mass: np.ndarray,
    event_cv_mass: np.ndarray,
    residual_grid_mass: np.ndarray,
    cell_capacity: np.ndarray,
) -> dict[str, Any]:
    m0 = np.asarray(parent_cv_mass, dtype=np.float64).reshape(-1)
    m1 = np.asarray(event_cv_mass, dtype=np.float64).reshape(-1)
    p = np.asarray(parent_pair_mass, dtype=np.float64)
    qraw = np.asarray(raw_event_pair_mass, dtype=np.float64)
    residual = np.asarray(residual_grid_mass, dtype=np.float64).reshape(-1)
    cap = np.asarray(cell_capacity, dtype=np.float64).reshape(-1)

    if len(pair_cv) != len(pair_cell) or len(pair_cv) != len(p):
        raise GateError("frozen_assignment_pair_shapes")
    if m0.shape != (NCVTOTAL,) or m1.shape != (NCVTOTAL,):
        raise GateError("frozen_assignment_CV_shapes")
    if residual.shape != (NCELL,) or cap.shape != (NCELL,):
        raise GateError("frozen_assignment_grid_shapes")
    if np.min(p) < -1e-10 or np.min(qraw) < -1e-10:
        raise GateError("frozen_assignment_negative_pair_authority")

    # Aggregate checks.
    p_cv = np.bincount(pair_cv, weights=p, minlength=NCVTOTAL)
    p_tol = max(1e-7, 1e-12 * max(float(np.max(np.abs(m0))), 1.0))
    if max_abs(p_cv - m0) > p_tol:
        raise GateError(
            "parent_pair_ownership_does_not_reconstruct_parent_CV_mass"
        )

    # Raw event EOS secondary target normalized per CV to exact event mass.
    q_cv = np.bincount(pair_cv, weights=qraw, minlength=NCVTOTAL)
    qtarget = np.zeros_like(qraw)

    eps = max(1e-12, 1e-15 * max(float(np.max(m0)), 1.0))
    positive_m0 = m0 > eps
    target = np.zeros_like(p)
    scale = np.zeros_like(m0)
    scale[positive_m0] = m1[positive_m0] / m0[positive_m0]
    target = p * scale[pair_cv]

    zero_parent_positive_event = (~positive_m0) & (m1 > eps)
    for j in np.flatnonzero(zero_parent_positive_event):
        mask = pair_cv == j
        qsum = float(q_cv[j])
        if not np.any(mask) or qsum <= eps:
            raise ScientificFail(
                "zero_parent_positive_event_CV_lacks_raw_event_EOS_support",
                int(j),
            )
        target[mask] = qraw[mask] * (m1[j] / qsum)

    # qtarget always normalizes raw event EOS where event mass is positive.
    for j in np.flatnonzero(m1 > eps):
        mask = pair_cv == j
        qsum = float(q_cv[j])
        if qsum <= eps:
            # For nonzero-parent CV this is secondary only; fall back to primary target.
            qtarget[mask] = target[mask]
        else:
            qtarget[mask] = qraw[mask] * (m1[j] / qsum)

    # Exact per-CV target sums.
    target_cv = np.bincount(pair_cv, weights=target, minlength=NCVTOTAL)
    target_tol = max(1e-7, 1e-12 * max(float(np.max(np.abs(m1))), 1.0))
    if max_abs(target_cv - m1) > target_tol:
        raise GateError("parent_continuity_target_CV_sum_failure")

    available = cap - residual
    cap_tol = max(1e-7, 1e-12 * max(float(np.max(np.abs(cap))), 1.0))
    if float(np.min(available)) < -cap_tol:
        raise ScientificFail(
            "residual_sidecar_already_exceeds_physical_cell_capacity",
            {
                "minimum_available_capacity_kg": float(np.min(available)),
                "tolerance_kg": cap_tol,
            },
        )
    available = np.maximum(available, 0.0)

    support_count = np.bincount(pair_cv, minlength=NCVTOTAL)
    missing = np.flatnonzero((m1 > target_tol) & (support_count == 0))
    if missing.size:
        raise ScientificFail(
            "positive_event_CV_without_S0_support",
            missing[:20].tolist(),
        )

    supported_cells = np.unique(pair_cell)
    global_capacity = fsum_array(available[supported_cells])
    event_mapped_total = fsum_array(m1)
    global_tol = max(1e-6, 1e-10 * max(event_mapped_total, 1.0))
    if event_mapped_total > global_capacity + global_tol:
        raise ScientificFail(
            "S0_global_available_capacity_insufficient",
            {
                "event_mapped_mass_kg": event_mapped_total,
                "available_capacity_kg": global_capacity,
                "deficit_kg": event_mapped_total - global_capacity,
                "tolerance_kg": global_tol,
            },
        )

    # Parent zero-delta identity probe.
    identity_grid = residual + np.bincount(
        pair_cell,
        weights=p,
        minlength=NCELL,
    )
    identity_pair_cv = np.bincount(
        pair_cv,
        weights=p,
        minlength=NCVTOTAL,
    )

    # Run all three frozen stages.
    x1, obj1, meta1 = solve_stage1(
        pair_cv,
        pair_cell,
        target,
        m1,
        available,
    )
    tol1 = max(1e-8, 1e-12 * max(abs(obj1), 1.0))

    x2, obj2, meta2 = solve_stage2(
        pair_cv,
        pair_cell,
        target,
        qtarget,
        m1,
        available,
        obj1,
        tol1,
    )
    tol2 = max(1e-8, 1e-12 * max(abs(obj2), 1.0))

    x3, obj3, meta3 = solve_stage3(
        pair_cv,
        pair_cell,
        target,
        qtarget,
        m1,
        available,
        obj1,
        tol1,
        obj2,
        tol2,
    )

    x = x3
    mapped = np.bincount(pair_cell, weights=x, minlength=NCELL)
    grid = residual + mapped
    cv = np.bincount(pair_cv, weights=x, minlength=NCVTOTAL)

    primary_actual = fsum_array(np.abs(x - target))
    secondary_actual = fsum_array(np.abs(x - qtarget))

    return {
        "x_pair_mass": x,
        "target_pair_mass": target,
        "qtarget_pair_mass": qtarget,
        "event_mapped_grid_mass": mapped,
        "event_grid_mass": grid,
        "event_CV_mass_reconstructed": cv,
        "available_capacity": available,
        "identity_grid_mass": identity_grid,
        "identity_CV_mass": identity_pair_cv,
        "stage1_objective": obj1,
        "stage2_objective": obj2,
        "stage3_objective": obj3,
        "stage1_tolerance": tol1,
        "stage2_tolerance": tol2,
        "primary_actual": primary_actual,
        "secondary_actual": secondary_actual,
        "stage1_meta": meta1,
        "stage2_meta": meta2,
        "stage3_meta": meta3,
        "supported_cell_count": int(supported_cells.size),
        "pair_count": int(len(pair_cv)),
        "zero_parent_positive_event_CV_count": int(
            np.sum(zero_parent_positive_event)
        ),
    }


def self_test() -> None:
    # Tiny synthetic frozen-support problem with one shared capacity cell.
    global NCVTOTAL, NCELL
    old_ncv, old_ncell = NCVTOTAL, NCELL
    try:
        NCVTOTAL = 2
        NCELL = 3
        pair_cv = np.array([0, 0, 1, 1], dtype=np.int64)
        pair_cell = np.array([0, 1, 1, 2], dtype=np.int64)
        p = np.array([3.0, 2.0, 2.0, 3.0])
        m0 = np.array([5.0, 5.0])
        m1 = np.array([6.0, 4.0])
        q = np.array([4.0, 2.0, 1.0, 3.0])
        residual = np.zeros(3)
        capacity = np.array([4.0, 4.0, 4.0])
        out = execute_frozen_assignment(
            pair_cv=pair_cv,
            pair_cell=pair_cell,
            parent_pair_mass=p,
            raw_event_pair_mass=q,
            parent_cv_mass=m0,
            event_cv_mass=m1,
            residual_grid_mass=residual,
            cell_capacity=capacity,
        )
        assert np.max(
            np.abs(out["event_CV_mass_reconstructed"] - m1)
        ) < 1e-8
        assert np.min(out["event_grid_mass"]) >= -1e-10
        assert np.max(out["event_grid_mass"] - capacity) <= 1e-8
        assert out["pair_count"] == 4
    finally:
        NCVTOTAL = old_ncv
        NCELL = old_ncell

    print(
        "POSTV16-AV4-F4-R3-R3-R3 ownership-reconciled event mapback "
        "+ flow-refresh execution self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    lp_executed = False
    event_mapback_executed = False
    event_refresh_executed = False
    event_reprojection_executed = False

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value, "scientific": True}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise ScientificFail(name, value)

    print("=" * 214)
    print(
        "POSTV16-AV4-F4-R3-R3-R3 — CONTROLLED OWNERSHIP-RECONCILED EVENT "
        "MAPBACK + SINGLE SAME-TIME FLOW REFRESH / REPROJECTION EXECUTION"
    )
    print("=" * 214)
    print("ONE FROZEN MAPBACK REPAIR ONLY. EXISTING S0 SUPPORT ONLY.")
    print("NO HALO. NO CLIPPING. NO GLOBAL RESCALING. NO TIMESTEP CHANGE.")
    print("NO PHYSICAL-TIME ADVANCE. NO DAY500 CONTINUATION.")
    print("NO TRAINING. NO CHECKPOINT INFERENCE. NO F5. NO A3-E2. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_R3R2_commit",
            parent == PARENT_R3R2_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind formal R3-R2 freeze.
        # ------------------------------------------------------------------------------------------
        stage = "R3R2_freeze_binding"
        r2d = drive / R3R2_REL
        gate("R3R2_output_present", r2d.is_dir(), str(r2d))
        r2manifest = verify_manifest(r2d, R3R2_MANIFEST)
        gate("R3R2_manifest_exact_5", len(r2manifest) == 5, len(r2manifest))
        r2summary = load_json(r2d / R3R2_SUMMARY)
        protocol = load_json(r2d / R3R2_PROTOCOL)
        handoff = load_json(r2d / R3R2_HANDOFF)

        gate("R3R2_status_exact", r2summary["status"] == R3R2_STATUS, r2summary["status"])
        gate(
            "R3R2_single_candidate_exact",
            int(r2summary["candidate_count"]) == 1
            and protocol["candidate_count"] == 1,
        )
        gate(
            "R3R2_S0_support_only",
            protocol["support"]["domain"] == "exact existing S0 CV-cell incidence only"
            and protocol["support"]["H1_or_other_halo_eligible"] is False
            and protocol["support"]["automatic_support_expansion"] is False,
        )
        gate(
            "R3R2_residual_sidecar_frozen",
            protocol["authoritative_parent_state"][
                "residual_sidecar_during_event_mapback"
            ] == "unchanged exactly",
        )
        gate(
            "R3R2_per_CV_mass_exact",
            protocol["optimization"]["hard_constraints"][0]
            == "sum_c x_jc = M1_j for every CV j",
        )
        gate(
            "R3R2_R3R3_handoff_exact",
            handoff["milestone"] == MILESTONE
            and handoff["authorized"] is True
            and handoff["execution"] is True,
        )

        # ------------------------------------------------------------------------------------------
        # Load frozen Drive states.
        # ------------------------------------------------------------------------------------------
        stage = "state_authority_binding"
        f2d = drive / F2R3_REL
        evd = drive / R3R1R2_REL
        a2d = drive / A2E_REL

        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        gate("R3R1R2_output_present", evd.is_dir(), str(evd))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        verify_manifest(f2d, F2R3_MANIFEST)
        verify_manifest(evd, R3R1R2_MANIFEST)
        verify_manifest(a2d, A2E_MANIFEST)

        with np.load(f2d / F2R3_STATE, allow_pickle=False) as z:
            parent_cv_mass = np.asarray(z["parent_CV_component_mass_kg"], dtype=np.float64)
            parent_cv_sat = np.asarray(z["parent_CV_saturation"], dtype=np.float64)
            parent_residual_grid = np.asarray(z["residual_grid_component_mass_kg"], dtype=np.float64)
            parent_mapped_grid = np.asarray(z["mapped_grid_component_mass_kg"], dtype=np.float64)
            parent_cell_pv = np.asarray(z["physical_cell_pore_volume_m3"], dtype=np.float64)
            s0_mask = np.asarray(z["S0_mask"], dtype=bool)
            sub_parent_mass = np.asarray(z["subsegment_parent_mass_kg"], dtype=np.float64)
            sub_flat = np.asarray(z["subsegment_flat_cell"], dtype=np.int64)
            sub_stream = np.asarray(z["subsegment_streamline"], dtype=np.int64)
            sub_cv = np.asarray(z["subsegment_control_volume"], dtype=np.int64)
            sub_pv = np.asarray(z["subsegment_pore_volume_m3"], dtype=np.float64)

        with np.load(evd / R3R1R2_STATE, allow_pickle=False) as z:
            event_cv_mass = np.asarray(z["partial_CV_component_mass_kg"], dtype=np.float64)
            event_cv_sat_frozen = np.asarray(z["partial_CV_saturation"], dtype=np.float64)
            elapsed = float(np.asarray(z["elapsed_days"]).reshape(()))
            remaining = float(np.asarray(z["remaining_days"]).reshape(()))
            substeps = int(np.asarray(z["accepted_substeps"]).reshape(()))

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}

        required_epoch = {
            "parent_component_mass_kg",
            "reconciled_saturation",
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

        parent_grid_mass = np.asarray(epoch["parent_component_mass_kg"], dtype=np.float64)
        parent_grid_sat = np.asarray(epoch["reconciled_saturation"], dtype=np.float64)
        parent_pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        grid_pv = np.asarray(epoch["pore_volume_m3"], dtype=np.float64)
        p_ref = float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        parent_xyz = np.asarray(epoch["streamline_xyz_m"], dtype=np.float64)
        parent_tof = np.asarray(epoch["streamline_tof_s"], dtype=np.float64)
        parent_weights = np.asarray(epoch["streamline_weight_m3_s"], dtype=np.float64)
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)
        grid_phi = np.asarray(epoch["paired_porosity"], dtype=np.float64)

        gate(
            "state_shapes_exact",
            parent_cv_mass.shape == (NSL, NCV)
            and parent_cv_sat.shape == (NSL, NCV)
            and event_cv_mass.shape == (NSL, NCV)
            and event_cv_sat_frozen.shape == (NSL, NCV)
            and parent_residual_grid.shape == GRID
            and parent_mapped_grid.shape == GRID
            and parent_cell_pv.shape == GRID
            and parent_grid_mass.shape == GRID
            and parent_pressure.shape == GRID
            and grid_pv.shape == GRID
            and parent_xyz.shape == (NSL, NN, 3)
            and parent_tof.shape == (NSL, NN)
            and parent_weights.shape == (NSL,),
        )
        gate(
            "event_identity_exact",
            substeps == EVENT_SUBSTEPS
            and abs(elapsed - EVENT_ELAPSED) <= 1e-12
            and abs(remaining - EVENT_REMAINING) <= 1e-12,
            {"substeps": substeps, "elapsed": elapsed, "remaining": remaining},
        )
        gate(
            "Day365_split_grid_exact",
            max_abs(parent_mapped_grid + parent_residual_grid - parent_grid_mass) <= 1e-9,
            max_abs(parent_mapped_grid + parent_residual_grid - parent_grid_mass),
        )
        gate(
            "physical_cell_pv_matches_A2E",
            relative_l2(parent_cell_pv, grid_pv) <= 1e-14,
            relative_l2(parent_cell_pv, grid_pv),
        )

        # ------------------------------------------------------------------------------------------
        # Load source-authentic helper modules and reconstruct raw event EOS secondary target.
        # ------------------------------------------------------------------------------------------
        stage = "source_module_binding"
        r3exec = load_module(root / R3R3, "postv16_av4_r3r3r3_exec")
        f4r3 = load_module(root / F4R3, "postv16_av4_r3r3r3_f4r3")
        a2e = load_module(root / A2E, "postv16_av4_r3r3r3_a2e")
        r2 = load_module(root / R2, "postv16_av4_r3r3r3_r2")
        e37 = load_module(root / E37A, "postv16_av4_r3r3r3_e37")
        sg2 = load_module(root / SG2, "postv16_av4_r3r3r3_sg2")
        sg3 = load_module(root / SG3, "postv16_av4_r3r3r3_sg3")
        sg4 = load_module(root / SG4, "postv16_av4_r3r3r3_sg4")
        sg5 = load_module(root / SG5, "postv16_av4_r3r3r3_sg5")
        sg6 = load_module(root / SG6, "postv16_av4_r3r3r3_sg6")
        sg7d = load_module(root / SG7D, "postv16_av4_r3r3r3_sg7d")
        r3r2r1 = load_module(root / R3R2R1, "postv16_av4_r3r3r3_r3r2r1")

        gate(
            "execution_helpers_present",
            hasattr(r3exec, "refresh_flow_epoch")
            and hasattr(r3exec, "rebuild_transport_epoch_fields")
            and hasattr(f4r3, "bounded_reproject")
            and hasattr(a2e, "invert_local_mass")
            and hasattr(r2, "gas_density_from_state"),
        )

        parent_operator = sg7d.build_subsegment_operator(
            parent_xyz,
            parent_tof / 86400.0,
            parent_weights * 86400.0,
        )
        geometry = e37.build_control_volume_geometry(
            r2,
            parent_operator,
            parent_pressure,
            p_ref,
            NSL,
            NCV,
        )

        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        geom_flat = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        geom_pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

        cv_id_f2 = sub_stream * NCV + sub_cv
        gate(
            "F2_subsegment_geometry_matches_rebuilt_E37A",
            np.array_equal(cv_id_f2, geom_cv_id)
            and np.array_equal(sub_flat, geom_flat)
            and max_abs(sub_pv - geom_pv) <= 1e-12,
            {
                "subsegments": int(len(sub_flat)),
                "pv_Linf": max_abs(sub_pv - geom_pv),
            },
        )

        event_flat_sat = event_cv_sat_frozen.reshape(-1)
        event_sub_sat = event_flat_sat[geom_cv_id]
        event_sub_sg = np.clip(event_sub_sat - BACKGROUND, 0.0, MAX_SG)
        event_sub_rho = np.asarray(
            r2.gas_density_from_state(event_sub_sat, geom_pseg, p_ref),
            dtype=np.float64,
        )
        raw_event_sub_mass = geom_pv * event_sub_rho * event_sub_sg

        pair_cv, pair_cell, parent_pair_mass, pair_key = aggregate_pairs(
            cv_id_f2,
            sub_flat,
            sub_parent_mass,
        )
        q_cv2, q_cell2, raw_event_pair_mass, pair_key2 = aggregate_pairs(
            geom_cv_id,
            geom_flat,
            raw_event_sub_mass,
        )
        gate(
            "parent_and_raw_event_pair_support_identical",
            np.array_equal(pair_key, pair_key2)
            and np.array_equal(pair_cv, q_cv2)
            and np.array_equal(pair_cell, q_cell2),
            len(pair_key),
        )

        parent_cv_flat = parent_cv_mass.reshape(-1)
        event_cv_flat = event_cv_mass.reshape(-1)
        reconstructed_parent_cv = np.bincount(
            pair_cv,
            weights=parent_pair_mass,
            minlength=NCVTOTAL,
        )
        gate(
            "parent_pair_ownership_exact_CV_reconstruction",
            max_abs(reconstructed_parent_cv - parent_cv_flat) <= 1e-8,
            max_abs(reconstructed_parent_cv - parent_cv_flat),
        )
        reconstructed_parent_mapped = np.bincount(
            pair_cell,
            weights=parent_pair_mass,
            minlength=NCELL,
        ).reshape(GRID)
        gate(
            "parent_pair_ownership_exact_grid_reconstruction",
            max_abs(reconstructed_parent_mapped - parent_mapped_grid) <= 1e-8,
            max_abs(reconstructed_parent_mapped - parent_mapped_grid),
        )

        # Source-authentic physical Cartesian capacity under old pressure.
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
        sci_gate(
            "source_authentic_cell_capacity_finite_positive",
            np.isfinite(cell_capacity).all()
            and float(np.min(cell_capacity)) > 0.0,
            [float(np.min(cell_capacity)), float(np.max(cell_capacity))],
        )

        # ------------------------------------------------------------------------------------------
        # Execute exactly the frozen S0 ownership reconciliation.
        # ------------------------------------------------------------------------------------------
        stage = "frozen_parent_ownership_event_mapback_LP"
        assignment = execute_frozen_assignment(
            pair_cv=pair_cv,
            pair_cell=pair_cell,
            parent_pair_mass=parent_pair_mass,
            raw_event_pair_mass=raw_event_pair_mass,
            parent_cv_mass=parent_cv_flat,
            event_cv_mass=event_cv_flat,
            residual_grid_mass=parent_residual_grid,
            cell_capacity=cell_capacity,
        )
        lp_executed = True
        event_mapback_executed = True

        event_grid_mass = np.asarray(
            assignment["event_grid_mass"],
            dtype=np.float64,
        ).reshape(GRID)
        event_mapped_grid = np.asarray(
            assignment["event_mapped_grid_mass"],
            dtype=np.float64,
        ).reshape(GRID)
        event_cv_reconstructed = np.asarray(
            assignment["event_CV_mass_reconstructed"],
            dtype=np.float64,
        ).reshape(NSL, NCV)

        cv_tol = max(1e-7, 1e-10 * max(float(np.max(np.abs(event_cv_mass))), 1.0))
        grid_tol = max(1e-7, 1e-10 * max(float(np.max(np.abs(cell_capacity))), 1.0))

        sci_gate(
            "LP_event_CV_mass_equalities_exact",
            max_abs(event_cv_reconstructed - event_cv_mass) <= cv_tol,
            {
                "Linf_kg": max_abs(event_cv_reconstructed - event_cv_mass),
                "tolerance_kg": cv_tol,
            },
        )
        sci_gate(
            "LP_event_grid_nonnegative",
            float(np.min(event_grid_mass)) >= -grid_tol,
            float(np.min(event_grid_mass)),
        )
        sci_gate(
            "LP_event_grid_within_source_authentic_capacity",
            float(np.max(event_grid_mass - cell_capacity)) <= grid_tol,
            {
                "max_excess_kg": float(np.max(event_grid_mass - cell_capacity)),
                "tolerance_kg": grid_tol,
            },
        )
        sci_gate(
            "LP_global_component_mass_exact",
            abs(
                fsum_array(event_grid_mass)
                - (
                    fsum_array(parent_residual_grid)
                    + fsum_array(event_cv_mass)
                )
            )
            <= max(1e-6, 1e-10 * max(fsum_array(event_grid_mass), 1.0)),
            {
                "event_grid_kg": fsum_array(event_grid_mass),
                "expected_kg": fsum_array(parent_residual_grid) + fsum_array(event_cv_mass),
            },
        )
        sci_gate(
            "LP_residual_sidecar_unchanged",
            max_abs(event_grid_mass - event_mapped_grid - parent_residual_grid) <= 1e-8,
            max_abs(event_grid_mass - event_mapped_grid - parent_residual_grid),
        )
        sci_gate(
            "LP_outside_S0_added_mapped_mass_zero",
            float(np.max(np.abs(event_mapped_grid[~s0_mask]))) <= 1e-12,
            float(np.max(np.abs(event_mapped_grid[~s0_mask]))),
        )
        gate(
            "LP_three_stages_success",
            assignment["stage1_meta"]["status"] == 0
            and assignment["stage2_meta"]["status"] == 0
            and assignment["stage3_meta"]["status"] == 0,
            {
                "stage1": assignment["stage1_meta"],
                "stage2": assignment["stage2_meta"],
                "stage3": assignment["stage3_meta"],
            },
        )

        parent_identity_grid = np.asarray(
            assignment["identity_grid_mass"],
            dtype=np.float64,
        ).reshape(GRID)
        gate(
            "parent_zero_delta_identity_exact",
            max_abs(parent_identity_grid - parent_grid_mass) <= 1e-8,
            max_abs(parent_identity_grid - parent_grid_mass),
        )

        # Preliminary saturation under old pressure; same event mass, zero physical time.
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
            raise ScientificFail(
                "event_parent_pressure_mass_inversion_failure",
                repr(exc),
            ) from exc
        event_sat_start = BACKGROUND + np.asarray(event_sg_start, dtype=np.float64)
        sci_gate(
            "event_parent_pressure_saturation_bounds",
            float(np.min(event_sat_start)) >= BACKGROUND - 1e-10
            and float(np.max(event_sat_start)) <= INJECTED + 1e-10,
            [float(np.min(event_sat_start)), float(np.max(event_sat_start))],
        )

        # ------------------------------------------------------------------------------------------
        # Execute exactly one same-time flow refresh.
        # ------------------------------------------------------------------------------------------
        stage = "single_same_time_event_flow_refresh"
        permeability_md = np.loadtxt(
            root / PERM,
            skiprows=1,
            dtype=np.float64,
        ).reshape(GRID, order="C")

        try:
            event_flow = r3exec.refresh_flow_epoch(
                label="event_refresh",
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
                raise ScientificFail(
                    str(exc.gate),
                    getattr(exc, "detail", None),
                ) from exc
            raise ScientificFail(
                "single_event_flow_refresh_failure",
                repr(exc),
            ) from exc
        event_refresh_executed = True

        # ------------------------------------------------------------------------------------------
        # Bounded refreshed-geometry reprojection.
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
            raise ScientificFail(
                "event_reprojection_failure",
                repr(exc),
            ) from exc
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
        # Rebuild refreshed transport fields, but do not advance physical time.
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

        sci_gate(
            "refreshed_event_fields_finite",
            all(
                np.isfinite(np.asarray(event_fields[k])).all()
                for k in [
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
            ),
        )
        sci_gate(
            "refreshed_event_state_shapes",
            np.asarray(event_split["cv_mass"]).shape == (NSL, NCV)
            and np.asarray(event_split["cv_saturation"]).shape == (NSL, NCV)
            and np.asarray(event_split["cv_capacity"]).shape == (NSL, NCV)
            and np.asarray(event_flow["xyz_m"]).shape == (NSL, NN, 3)
            and np.asarray(event_flow["tof_s"]).shape == (NSL, NN)
            and np.asarray(event_flow["weights_m3_s"]).shape == (NSL,),
        )

        tof_change = relative_l2(event_flow["tof_s"], parent_tof)
        pressure_change = relative_l2(event_flow["pressure_psi"], parent_pressure)
        sci_gate(
            "single_refresh_changes_flow_epoch",
            tof_change > 1e-12 or pressure_change > 1e-12,
            {
                "TOF_relative_L2_change": tof_change,
                "pressure_relative_L2_change": pressure_change,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Publish exact event-time recurrent state.
        # ------------------------------------------------------------------------------------------
        stage = "artifact_publication"

        state_npz = deterministic_npz_bytes(
            {
                "event_day": np.asarray(EVENT_DAY),
                "physical_time_advanced_in_R3R3R3": np.asarray(False),
                "event_grid_component_mass_kg": event_grid_mass,
                "event_parent_pressure_saturation": event_sat_start,
                "ownership_reconciled_event_mapped_grid_mass_kg": event_mapped_grid,
                "frozen_parent_residual_grid_mass_kg": parent_residual_grid,
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
                "pair_cv_id": pair_cv,
                "pair_flat_cell": pair_cell,
                "pair_parent_ownership_mass_kg": parent_pair_mass,
                "pair_event_mass_kg": np.asarray(assignment["x_pair_mass"]),
                "pair_parent_continuity_target_kg": np.asarray(assignment["target_pair_mass"]),
                "pair_raw_event_EOS_target_kg": np.asarray(assignment["qtarget_pair_mass"]),
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
            "event_day": EVENT_DAY,
            "physical_time_advanced": False,
            "LP_pair_count": assignment["pair_count"],
            "LP_supported_cell_count": assignment["supported_cell_count"],
            "LP_stage1_primary_L1_kg": assignment["stage1_objective"],
            "LP_stage2_secondary_L1_kg": assignment["stage2_objective"],
            "LP_stage3_tiebreak_objective": assignment["stage3_objective"],
            "LP_primary_actual_L1_kg": assignment["primary_actual"],
            "LP_secondary_actual_L1_kg": assignment["secondary_actual"],
            "zero_parent_positive_event_CV_count":
                assignment["zero_parent_positive_event_CV_count"],
            "event_grid_mass_kg": fsum_array(event_grid_mass),
            "event_CV_mapped_mass_kg": fsum_array(event_cv_mass),
            "frozen_parent_residual_mass_kg": fsum_array(parent_residual_grid),
            "event_grid_min_mass_kg": float(np.min(event_grid_mass)),
            "event_grid_max_capacity_excess_kg":
                float(np.max(event_grid_mass - cell_capacity)),
            "flow_refresh_executed": True,
            "reprojection_executed": True,
            "TOF_relative_L2_change": tof_change,
            "pressure_relative_L2_change": pressure_change,
            "second_epoch_transport_started": False,
            "R3R3R4_event_to_Day500_continuation_authorized": True,
            "F5_authorized": False,
            "training_authorized": False,
        }

        lp_audit = {
            "milestone": MILESTONE,
            "pair_count": assignment["pair_count"],
            "supported_cell_count": assignment["supported_cell_count"],
            "stage1": {
                "objective_L1_kg": assignment["stage1_objective"],
                "tolerance": assignment["stage1_tolerance"],
                **assignment["stage1_meta"],
            },
            "stage2": {
                "objective_L1_kg": assignment["stage2_objective"],
                "tolerance": assignment["stage2_tolerance"],
                **assignment["stage2_meta"],
            },
            "stage3": {
                "tiebreak_objective": assignment["stage3_objective"],
                **assignment["stage3_meta"],
            },
            "primary_actual_L1_kg": assignment["primary_actual"],
            "secondary_actual_L1_kg": assignment["secondary_actual"],
            "event_CV_mass_Linf_error_kg":
                max_abs(event_cv_reconstructed - event_cv_mass),
            "event_grid_min_mass_kg": float(np.min(event_grid_mass)),
            "event_grid_max_capacity_excess_kg":
                float(np.max(event_grid_mass - cell_capacity)),
            "global_event_mass_residual_kg":
                fsum_array(event_grid_mass)
                - fsum_array(parent_residual_grid)
                - fsum_array(event_cv_mass),
            "support_expanded": False,
            "mass_clipped": False,
            "global_rescaling": False,
        }

        handoff_out = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R4",
            "name":
                "Refreshed Event-Epoch Day413.78677770818403 to Day500 Controlled Continuation Execution",
            "authorized": True,
            "execution": True,
            "required_R3R3R3_status": STATUS_PASS,
            "parent_event_day": EVENT_DAY,
            "remaining_days": EVENT_REMAINING,
            "required_parent_state":
                "POSTV16_AV4_F4_R3_R3_R3_Refreshed_Event_Recurrent_State.npz",
            "single_event_refresh_already_consumed": True,
            "second_event_refresh_authorized": False,
            "scope": [
                "resume remaining 86.21322229181597 days using refreshed event epoch",
                "unchanged raw F4 internal operator",
                "unchanged F4-R2 terminal producer pass-through",
                "if another interior conflict occurs, preserve SCIENTIFIC FAIL with no second refresh",
                "on Day500 success perform original Day500 same-time refresh/reprojection certification",
            ],
            "not_authorized": [
                "F5 dataset generation",
                "training",
                "checkpoint inference",
                "locked OOD",
                "A3-E2",
                "CMG",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "R3R3_scientific_FAIL_preserved": True,
            "R3R2_freeze_bound": True,
            "mapback_repair_executed": True,
            "LP_executed": True,
            "support_domain_changed": False,
            "residual_sidecar_changed_during_event_mapback": False,
            "event_CV_mass_changed_by_mapback": False,
            "single_same_time_flow_refresh_executed": True,
            "event_reprojection_executed": True,
            "physical_time_advanced": False,
            "second_epoch_transport_started": False,
            "second_event_refresh_executed": False,
            "R3R3R4_authorized": True,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_Summary.json": json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_LP_Reconciliation_Audit.json": json_bytes(lp_audit),
            "POSTV16_AV4_F4_R3_R3_R3_Refreshed_Event_Recurrent_State.npz": state_npz,
            "POSTV16_AV4_F4_R3_R3_R3_R3R3R4_Handoff_Contract.json": json_bytes(handoff_out),
            "POSTV16_AV4_F4_R3_R3_R3_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3: OWNERSHIP-RECONCILED EVENT MAPBACK "
            "+ SINGLE SAME-TIME FLOW REFRESH / REPROJECTION PASS"
        )
        print("=" * 214)
        print("Event day                                :", EVENT_DAY)
        print("LP pair / supported-cell counts          :", assignment["pair_count"], "/", assignment["supported_cell_count"])
        print("Primary parent-ownership L1 kg           :", assignment["stage1_objective"])
        print("Secondary raw-event-EOS L1 kg            :", assignment["stage2_objective"])
        print("Event grid min mass kg                   :", float(np.min(event_grid_mass)))
        print("Event grid max capacity excess kg        :", float(np.max(event_grid_mass - cell_capacity)))
        print("Event CV mass Linf reconstruction kg     :", max_abs(event_cv_reconstructed - event_cv_mass))
        print("Residual sidecar changed in event mapback: False")
        print("Same-time event flow refresh             : EXECUTED ONCE")
        print("Refreshed-geometry reprojection          : PASS")
        print("Physical-time advance                    : False")
        print("Second-epoch transport                   : NOT STARTED")
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
            "R3R3_scientific_FAIL_preserved": True,
            "R3R2_freeze_preserved": True,
            "LP_executed": lp_executed,
            "mapback_repair_executed": event_mapback_executed,
            "event_refresh_executed": event_refresh_executed,
            "event_reprojection_executed": event_reprojection_executed,
            "support_domain_changed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "physical_time_advanced": False,
            "second_event_refresh_authorized": False,
            "automatic_fallback_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = failed / "POSTV16_AV4_F4_R3_R3_R3_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = failed / (
                "POSTV16_AV4_F4_R3_R3_R3_Scientific_Fail_Report_"
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
        print("NO SUPPORT EXPANSION, ALTERNATE REPAIR, SECOND REFRESH, OR AUTOMATIC RERUN AUTHORIZED.")
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
            "R3R3_scientific_FAIL_preserved": True,
            "R3R2_freeze_preserved": True,
            "LP_executed": lp_executed,
            "mapback_repair_executed": event_mapback_executed,
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
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_Blocked_Report_"
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
        print("R3-R3 scientific FAIL and R3-R2 freeze remain immutable.")
        print("NO AUTOMATIC RERUN AUTHORIZED.")
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
