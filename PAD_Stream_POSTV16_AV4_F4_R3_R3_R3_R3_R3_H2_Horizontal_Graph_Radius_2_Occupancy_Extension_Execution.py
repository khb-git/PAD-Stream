#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3"

STATUS_PASS = (
    "AV4F4R3R3R3R3R3_FROZEN_H2_HORIZONTAL_GRAPH_RADIUS_2_ASSIGNMENT_PASS_"
    "MINIMUM_SECOND_SHELL_AND_TOTAL_EXTENSION_PASS_SINGLE_SAME_TIME_FLOW_REFRESH_"
    "AND_REFRESHED_GEOMETRY_REPROJECTION_PASS_NO_PHYSICAL_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3_FROZEN_H2_ASSIGNMENT_OR_SINGLE_FLOW_REFRESH_OR_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_RADIUS3_NO_VERTICAL_OR_H2V1_FALLBACK_NO_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R2_COMMIT = "48f24139717630a842fb2e02caf902b25df67a86"

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
EXPECTED_E1_PAIRS = 1245666
EXPECTED_E2_PAIRS = 3091073
EXPECTED_E2_GLOBAL_CELLS = 34497

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

R2FREEZE = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R2_"
    "H2_Horizontal_Graph_Radius_2_Support_Selection_Freeze.py"
)
R2FREEZE_BLOB = "0ae1e22f25ffd807b98cca9ead74b4b8cf61f672"

H1EXEC = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_"
    "Per_CV_Horizontal_Face_Occupancy_Extension_Execution.py"
)
H1EXEC_BLOB = "a20a31bd48d4331b50dc71488ceaa5dc611acf25"

R1AUDIT = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R1_"
    "Prospective_Support_Class_Feasibility_Audit.py"
)
R1AUDIT_BLOB = "a342684ee48567ad11ee65cce2afe8c85eb9b432"

SOURCE_BLOBS = {
    R2FREEZE: R2FREEZE_BLOB,
    H1EXEC: H1EXEC_BLOB,
    R1AUDIT: R1AUDIT_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Exact Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R2_H2_Horizontal_Graph_Radius_2_Freeze"
)
R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R2_Summary.json"
R2_PROTOCOL = "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Frozen_H2_Protocol.json"
R2_HANDOFF = "POSTV16_AV4_F4_R3_R3_R3_R3_R2_R3R3R3R3R3_Execution_Handoff_Contract.json"
R2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Artifact_Manifest.csv"
R2_STATUS = (
    "AV4F4R3R3R3R3R2_R3R3R3R3R1_PROSPECTIVE_SUPPORT_AUDIT_BOUND_"
    "H2_HORIZONTAL_GRAPH_RADIUS_2_SELECTED_AS_SMALLEST_TESTED_FEASIBLE_CLASS_"
    "PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

# H1 immutable scientific fail is preserved and bound directly.
H1_FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_SCIENTIFIC_FAIL"
H1_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_Scientific_Fail_Report.json"
H1_FAIL_STATUS = (
    "AV4F4R3R3R3R3_FROZEN_E1_ASSIGNMENT_OR_SINGLE_FLOW_REFRESH_OR_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_H2_NO_VERTICAL_OR_DIAGONAL_EXTENSION_NO_ALTERNATE_REPAIR"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_H2_Horizontal_Graph_Radius_2_Execution"
)
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_BLOCKED"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def incidence(rows_idx: np.ndarray, nrows: int, ncols: int) -> csr_matrix:
    cols = np.arange(ncols, dtype=np.int64)
    return coo_matrix(
        (
            np.ones(ncols, dtype=np.float64),
            (np.asarray(rows_idx, dtype=np.int64), cols),
        ),
        shape=(nrows, ncols),
    ).tocsr()


def support_keys_from_offsets(
    e0_cv: np.ndarray,
    e0_cell: np.ndarray,
    offsets: list[tuple[int, int, int]],
) -> np.ndarray:
    cv = np.asarray(e0_cv, dtype=np.int64).reshape(-1)
    cell = np.asarray(e0_cell, dtype=np.int64).reshape(-1)

    k = cell // (NY * NX)
    rem = cell % (NY * NX)
    j = rem // NX
    i = rem % NX

    keys = []
    for dk, dj, di in offsets:
        kk = k + dk
        jj = j + dj
        ii = i + di
        mask = (
            (kk >= 0) & (kk < NZ)
            & (jj >= 0) & (jj < NY)
            & (ii >= 0) & (ii < NX)
        )
        cc = kk[mask] * (NY * NX) + jj[mask] * NX + ii[mask]
        keys.append(cv[mask] * NCELL + cc)

    return np.unique(np.concatenate(keys))


def h1_offsets() -> list[tuple[int, int, int]]:
    return [
        (0, 0, 0),
        (0, 0, -1),
        (0, 0, 1),
        (0, -1, 0),
        (0, 1, 0),
    ]


def h2_offsets() -> list[tuple[int, int, int]]:
    return [
        (0, dj, di)
        for dj in range(-2, 3)
        for di in range(-2, 3)
        if abs(dj) + abs(di) <= 2
    ]


def build_e2_support(
    e0_cv: np.ndarray,
    e0_cell: np.ndarray,
) -> dict[str, np.ndarray]:
    e0_cv = np.asarray(e0_cv, dtype=np.int64).reshape(-1)
    e0_cell = np.asarray(e0_cell, dtype=np.int64).reshape(-1)
    e0_key = np.unique(e0_cv * NCELL + e0_cell)
    e1_key = support_keys_from_offsets(e0_cv, e0_cell, h1_offsets())
    e2_key = support_keys_from_offsets(e0_cv, e0_cell, h2_offsets())

    def positions(sub: np.ndarray, sup: np.ndarray, label: str) -> np.ndarray:
        pos = np.searchsorted(sup, sub)
        if np.any(pos >= len(sup)) or not np.array_equal(sup[pos], sub):
            raise GateError(label + "_not_subset")
        return pos.astype(np.int64)

    e0_idx = positions(e0_key, e2_key, "E0_E2")
    e1_idx = positions(e1_key, e2_key, "E1_E2")

    is_e0 = np.zeros(len(e2_key), dtype=bool)
    is_e0[e0_idx] = True
    is_e1 = np.zeros(len(e2_key), dtype=bool)
    is_e1[e1_idx] = True

    e2_cv = (e2_key // NCELL).astype(np.int64)
    e2_cell = (e2_key % NCELL).astype(np.int64)
    e1_cv = (e1_key // NCELL).astype(np.int64)
    e1_cell = (e1_key % NCELL).astype(np.int64)

    e0_global = np.unique(e0_cell)
    e1_global = np.unique(e1_cell)
    e2_global = np.unique(e2_cell)

    return {
        "e0_key": e0_key,
        "e1_key": e1_key,
        "e2_key": e2_key,
        "e2_cv": e2_cv,
        "e2_cell": e2_cell,
        "e0_indices_in_e2": e0_idx,
        "e1_indices_in_e2": e1_idx,
        "is_e0": is_e0,
        "is_e1": is_e1,
        "is_h2_shell": ~is_e1,
        "is_any_extension": ~is_e0,
        "e0_global_cells": e0_global,
        "e1_global_cells": e1_global,
        "e2_global_cells": e2_global,
        "globally_new_h1_cells": np.setdiff1d(e1_global, e0_global, assume_unique=True),
        "globally_new_h2_cells": np.setdiff1d(e2_global, e1_global, assume_unique=True),
    }


def _tol(v: float) -> float:
    return max(1e-7, 1e-12 * max(abs(float(v)), 1.0))


def solve_stage1_h2_shell(
    e2_cv: np.ndarray,
    e2_cell: np.ndarray,
    shell_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
) -> tuple[float, dict[str, Any]]:
    n = len(e2_cv)
    Aeq = incidence(e2_cv, NCVTOTAL, n)
    Acap = incidence(e2_cell, NCELL, n)
    c = shell_mask.astype(np.float64)
    res = linprog(
        c,
        A_ub=Acap,
        b_ub=available,
        A_eq=Aeq,
        b_eq=demand,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E2_stage1_minimum_H2_shell_mass_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    obj = float(res.fun)
    meta = {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }
    del res, Aeq, Acap, c
    gc.collect()
    return obj, meta


def solve_stage2_total_extension(
    e2_cv: np.ndarray,
    e2_cell: np.ndarray,
    shell_mask: np.ndarray,
    extension_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    shell_opt: float,
) -> tuple[float, dict[str, Any]]:
    n = len(e2_cv)
    Aeq = incidence(e2_cv, NCVTOTAL, n)
    Acap = incidence(e2_cell, NCELL, n)
    shell_row = csr_matrix(
        (
            shell_mask.astype(np.float64),
            (np.zeros(n, dtype=np.int64), np.arange(n, dtype=np.int64)),
        ),
        shape=(1, n),
    )
    Aub = vstack([Acap, shell_row], format="csr")
    bub = np.concatenate([available, [shell_opt + _tol(shell_opt)]])
    c = extension_mask.astype(np.float64)
    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=demand,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E2_stage2_minimum_total_extension_mass_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    obj = float(res.fun)
    meta = {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }
    del res, Aeq, Acap, shell_row, Aub, bub, c
    gc.collect()
    return obj, meta


def _selector(e0_idx: np.ndarray, n: int) -> csr_matrix:
    m = len(e0_idx)
    return coo_matrix(
        (
            np.ones(m, dtype=np.float64),
            (np.arange(m, dtype=np.int64), e0_idx),
        ),
        shape=(m, n),
    ).tocsr()


def solve_stage3_parent_L1(
    e2_cv: np.ndarray,
    e2_cell: np.ndarray,
    e0_idx: np.ndarray,
    shell_mask: np.ndarray,
    extension_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    target0: np.ndarray,
    shell_opt: float,
    extension_opt: float,
) -> tuple[float, dict[str, Any]]:
    n = len(e2_cv)
    m = len(e0_idx)
    Aeq_x = incidence(e2_cv, NCVTOTAL, n)
    Acap_x = incidence(e2_cell, NCELL, n)
    S = _selector(e0_idx, n)
    I = eye(m, format="csr")

    Aub = vstack(
        [
            hstack([S, -I], format="csr"),
            hstack([-S, -I], format="csr"),
            hstack([Acap_x, csr_matrix((NCELL, m))], format="csr"),
        ],
        format="csr",
    )
    bub = np.concatenate([target0, -target0, available])

    shell_row = csr_matrix(
        (
            shell_mask.astype(np.float64),
            (np.zeros(n), np.arange(n)),
        ),
        shape=(1, n + m),
    )
    extension_row = csr_matrix(
        (
            extension_mask.astype(np.float64),
            (np.zeros(n), np.arange(n)),
        ),
        shape=(1, n + m),
    )
    Aub = vstack([Aub, shell_row, extension_row], format="csr")
    bub = np.concatenate(
        [bub, [shell_opt + _tol(shell_opt), extension_opt + _tol(extension_opt)]]
    )

    Aeq = hstack([Aeq_x, csr_matrix((NCVTOTAL, m))], format="csr")
    c = np.concatenate([np.zeros(n), np.ones(m)])
    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=demand,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E2_stage3_parent_ownership_L1_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    obj = float(res.fun)
    meta = {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }
    del res, Aeq_x, Acap_x, S, I, Aub, bub, Aeq, c, shell_row, extension_row
    gc.collect()
    return obj, meta


def solve_stage4_raw_L1(
    e2_cv: np.ndarray,
    e2_cell: np.ndarray,
    e0_idx: np.ndarray,
    shell_mask: np.ndarray,
    extension_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    target0: np.ndarray,
    qtarget0: np.ndarray,
    shell_opt: float,
    extension_opt: float,
    parent_opt: float,
) -> tuple[float, dict[str, Any]]:
    n = len(e2_cv)
    m = len(e0_idx)
    Aeq_x = incidence(e2_cv, NCVTOTAL, n)
    Acap_x = incidence(e2_cell, NCELL, n)
    S = _selector(e0_idx, n)
    I = eye(m, format="csr")
    Z = csr_matrix((m, m))

    Aub = vstack(
        [
            hstack([S, -I, Z], format="csr"),
            hstack([-S, -I, Z], format="csr"),
            hstack([S, Z, -I], format="csr"),
            hstack([-S, Z, -I], format="csr"),
            hstack([Acap_x, csr_matrix((NCELL, 2 * m))], format="csr"),
        ],
        format="csr",
    )
    bub = np.concatenate([target0, -target0, qtarget0, -qtarget0, available])

    shell_row = csr_matrix(
        (
            shell_mask.astype(np.float64),
            (np.zeros(n), np.arange(n)),
        ),
        shape=(1, n + 2 * m),
    )
    extension_row = csr_matrix(
        (
            extension_mask.astype(np.float64),
            (np.zeros(n), np.arange(n)),
        ),
        shape=(1, n + 2 * m),
    )
    parent_row = csr_matrix(
        (
            np.ones(m),
            (np.zeros(m), n + np.arange(m)),
        ),
        shape=(1, n + 2 * m),
    )
    Aub = vstack([Aub, shell_row, extension_row, parent_row], format="csr")
    bub = np.concatenate(
        [
            bub,
            [
                shell_opt + _tol(shell_opt),
                extension_opt + _tol(extension_opt),
                parent_opt + _tol(parent_opt),
            ],
        ]
    )
    Aeq = hstack([Aeq_x, csr_matrix((NCVTOTAL, 2 * m))], format="csr")
    c = np.concatenate([np.zeros(n + m), np.ones(m)])
    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=demand,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E2_stage4_raw_event_EOS_L1_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    obj = float(res.fun)
    meta = {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }
    del res, Aeq_x, Acap_x, S, I, Z, Aub, bub, Aeq, c
    del shell_row, extension_row, parent_row
    gc.collect()
    return obj, meta


def solve_stage5_tiebreak(
    e2_cv: np.ndarray,
    e2_cell: np.ndarray,
    e0_idx: np.ndarray,
    shell_mask: np.ndarray,
    extension_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    target0: np.ndarray,
    qtarget0: np.ndarray,
    shell_opt: float,
    extension_opt: float,
    parent_opt: float,
    raw_opt: float,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    n = len(e2_cv)
    m = len(e0_idx)
    Aeq_x = incidence(e2_cv, NCVTOTAL, n)
    Acap_x = incidence(e2_cell, NCELL, n)
    S = _selector(e0_idx, n)
    I = eye(m, format="csr")
    Z = csr_matrix((m, m))

    Aub = vstack(
        [
            hstack([S, -I, Z], format="csr"),
            hstack([-S, -I, Z], format="csr"),
            hstack([S, Z, -I], format="csr"),
            hstack([-S, Z, -I], format="csr"),
            hstack([Acap_x, csr_matrix((NCELL, 2 * m))], format="csr"),
        ],
        format="csr",
    )
    bub = np.concatenate([target0, -target0, qtarget0, -qtarget0, available])

    shell_row = csr_matrix(
        (
            shell_mask.astype(np.float64),
            (np.zeros(n), np.arange(n)),
        ),
        shape=(1, n + 2 * m),
    )
    extension_row = csr_matrix(
        (
            extension_mask.astype(np.float64),
            (np.zeros(n), np.arange(n)),
        ),
        shape=(1, n + 2 * m),
    )
    parent_row = csr_matrix(
        (
            np.ones(m),
            (np.zeros(m), n + np.arange(m)),
        ),
        shape=(1, n + 2 * m),
    )
    raw_row = csr_matrix(
        (
            np.ones(m),
            (np.zeros(m), n + m + np.arange(m)),
        ),
        shape=(1, n + 2 * m),
    )
    Aub = vstack(
        [Aub, shell_row, extension_row, parent_row, raw_row],
        format="csr",
    )
    bub = np.concatenate(
        [
            bub,
            [
                shell_opt + _tol(shell_opt),
                extension_opt + _tol(extension_opt),
                parent_opt + _tol(parent_opt),
                raw_opt + _tol(raw_opt),
            ],
        ]
    )
    Aeq = hstack([Aeq_x, csr_matrix((NCVTOTAL, 2 * m))], format="csr")
    rank = (np.arange(n, dtype=np.float64) + 1.0) / max(float(n), 1.0)
    c = np.concatenate([rank, np.zeros(2 * m)])
    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=demand,
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E2_stage5_deterministic_tiebreak_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x[:n], dtype=np.float64).copy()
    obj = float(np.dot(rank, x))
    meta = {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }
    del res, Aeq_x, Acap_x, S, I, Z, Aub, bub, Aeq, c
    del shell_row, extension_row, parent_row, raw_row, rank
    gc.collect()
    return x, obj, meta


def execute_e2_assignment(
    *,
    e0_cv: np.ndarray,
    e0_cell: np.ndarray,
    parent_pair_mass: np.ndarray,
    raw_event_pair_mass: np.ndarray,
    parent_cv_mass: np.ndarray,
    event_cv_mass: np.ndarray,
    residual_grid_mass: np.ndarray,
    cell_capacity: np.ndarray,
    h1base: Any,
    r1mod: Any,
) -> dict[str, Any]:
    support = build_e2_support(e0_cv, e0_cell)

    e2_cv = support["e2_cv"]
    e2_cell = support["e2_cell"]
    e0_idx = support["e0_indices_in_e2"]
    shell_mask = support["is_h2_shell"]
    extension_mask = support["is_any_extension"]

    if len(support["e0_key"]) != EXPECTED_E0_PAIRS:
        raise GateError("E0_pair_count_mismatch")
    if len(support["e1_key"]) != EXPECTED_E1_PAIRS:
        raise GateError("E1_pair_count_mismatch")
    if len(support["e2_key"]) != EXPECTED_E2_PAIRS:
        raise GateError("E2_pair_count_mismatch")
    if len(support["e2_global_cells"]) != EXPECTED_E2_GLOBAL_CELLS:
        raise GateError("E2_global_cell_count_mismatch")

    demand = np.asarray(event_cv_mass, dtype=np.float64).reshape(-1)
    residual = np.asarray(residual_grid_mass, dtype=np.float64).reshape(-1)
    cap = np.asarray(cell_capacity, dtype=np.float64).reshape(-1)
    available = cap - residual
    cap_tol = max(1e-7, 1e-12 * max(float(np.max(np.abs(cap))), 1.0))
    if float(np.min(available)) < -cap_tol:
        raise ScientificFail(
            "E2_residual_sidecar_exceeds_physical_capacity",
            {"minimum_available_capacity_kg": float(np.min(available))},
        )
    available = np.maximum(available, 0.0)

    target0, qtarget0, zero_parent_count = h1base.build_e0_targets(
        e0_cv,
        parent_pair_mass,
        raw_event_pair_mass,
        parent_cv_mass,
        event_cv_mass,
    )

    # Stage 0: reproduce formal E2 zero-minimum-unserved result.
    feasibility = r1mod.minimum_unserved_lp(
        e2_cv,
        e2_cell,
        demand,
        available,
        NCVTOTAL,
        NCELL,
    )
    minimum_unserved = float(feasibility["minimum_unserved_mass"])
    total_demand = float(math.fsum(float(v) for v in demand))
    feas_tol = max(1e-6, 1e-10 * max(total_demand, 1.0))
    if minimum_unserved > feas_tol:
        witness = r1mod.residual_mincut_witness(
            e2_cv,
            e2_cell,
            feasibility["pair_flow"],
            feasibility["unserved_cv"],
            demand,
            available,
            NCVTOTAL,
            NCELL,
            flow_tol=max(1e-8, 1e-12 * max(total_demand, 1.0)),
        )
        raise ScientificFail(
            "E2_FORMAL_FEASIBILITY_REPRODUCTION_FAIL",
            {
                "minimum_unserved_mass_kg": minimum_unserved,
                "Hall_CV_count": int(np.sum(witness["cv_reachable"])),
                "Hall_cell_count": int(np.sum(witness["cell_reachable"])),
                "Hall_demand_kg": float(witness["demand_U"]),
                "Hall_capacity_kg": float(witness["capacity_N"]),
                "Hall_deficit_kg": float(witness["hall_deficit"]),
            },
        )
    del feasibility
    gc.collect()

    # Stages 1-5 exactly follow the frozen R2 lexicographic contract.
    shell_opt, meta1 = solve_stage1_h2_shell(
        e2_cv, e2_cell, shell_mask, demand, available
    )
    extension_opt, meta2 = solve_stage2_total_extension(
        e2_cv, e2_cell, shell_mask, extension_mask,
        demand, available, shell_opt
    )
    parent_opt, meta3 = solve_stage3_parent_L1(
        e2_cv, e2_cell, e0_idx, shell_mask, extension_mask,
        demand, available, target0, shell_opt, extension_opt
    )
    raw_opt, meta4 = solve_stage4_raw_L1(
        e2_cv, e2_cell, e0_idx, shell_mask, extension_mask,
        demand, available, target0, qtarget0,
        shell_opt, extension_opt, parent_opt
    )
    x, tie_obj, meta5 = solve_stage5_tiebreak(
        e2_cv, e2_cell, e0_idx, shell_mask, extension_mask,
        demand, available, target0, qtarget0,
        shell_opt, extension_opt, parent_opt, raw_opt
    )

    mapped = np.bincount(e2_cell, weights=x, minlength=NCELL).astype(np.float64)
    cv_mass = np.bincount(e2_cv, weights=x, minlength=NCVTOTAL).astype(np.float64)
    grid = residual + mapped

    pos_tol = max(1e-10, 1e-14 * max(float(np.sum(x)), 1.0))
    shell_positive = shell_mask & (x > pos_tol)
    extension_positive = extension_mask & (x > pos_tol)

    shell_cvs = np.unique(e2_cv[shell_positive])
    shell_streamlines = np.unique(shell_cvs // NCV)
    shell_cells = np.unique(e2_cell[shell_positive])

    ext_cvs = np.unique(e2_cv[extension_positive])
    ext_streamlines = np.unique(ext_cvs // NCV)
    ext_cells = np.unique(e2_cell[extension_positive])

    shell_actual = float(np.sum(x[shell_mask]))
    extension_actual = float(np.sum(x[extension_mask]))

    return {
        **support,
        "x_pair_mass": x,
        "target0": target0,
        "qtarget0": qtarget0,
        "event_mapped_grid_mass": mapped,
        "event_grid_mass": grid,
        "event_CV_mass_reconstructed": cv_mass,
        "available_capacity": available,
        "stage0_minimum_unserved_mass_kg": minimum_unserved,
        "stage1_minimum_H2_shell_mass_kg": shell_opt,
        "stage2_minimum_total_extension_mass_kg": extension_opt,
        "stage3_parent_L1_kg": parent_opt,
        "stage4_raw_L1_kg": raw_opt,
        "stage5_tiebreak": tie_obj,
        "stage1_meta": meta1,
        "stage2_meta": meta2,
        "stage3_meta": meta3,
        "stage4_meta": meta4,
        "stage5_meta": meta5,
        "H2_shell_mass_actual_kg": shell_actual,
        "total_extension_mass_actual_kg": extension_actual,
        "H2_shell_CV_count": int(shell_cvs.size),
        "H2_shell_streamline_count": int(shell_streamlines.size),
        "H2_shell_cell_count": int(shell_cells.size),
        "any_extension_CV_count": int(ext_cvs.size),
        "any_extension_streamline_count": int(ext_streamlines.size),
        "any_extension_cell_count": int(ext_cells.size),
        "zero_parent_positive_event_CV_count": zero_parent_count,
    }


def self_test() -> None:
    global NZ, NY, NX, NCELL, NCVTOTAL

    old = (NZ, NY, NX, NCELL, NCVTOTAL)
    try:
        # Two CVs begin at cell 0. H1 can reach cells 0-1 with total
        # capacity 8 kg; E2 adds cell 2 and reaches exactly 10 kg.
        NZ, NY, NX = 1, 1, 3
        NCELL = 3
        NCVTOTAL = 2

        e0_cv = np.array([0, 1], dtype=np.int64)
        e0_cell = np.array([0, 0], dtype=np.int64)
        support = build_e2_support(e0_cv, e0_cell)
        assert len(support["e0_key"]) == 2
        assert len(support["e1_key"]) == 4
        assert len(support["e2_key"]) == 6
        assert int(np.sum(support["is_h2_shell"])) == 2

        demand = np.array([5.0, 5.0])
        available = np.array([4.0, 4.0, 2.0])
        shell_opt, _ = solve_stage1_h2_shell(
            support["e2_cv"],
            support["e2_cell"],
            support["is_h2_shell"],
            demand,
            available,
        )
        assert abs(shell_opt - 2.0) < 1e-7

        extension_opt, _ = solve_stage2_total_extension(
            support["e2_cv"],
            support["e2_cell"],
            support["is_h2_shell"],
            support["is_any_extension"],
            demand,
            available,
            shell_opt,
        )
        assert abs(extension_opt - 6.0) < 1e-7

    finally:
        NZ, NY, NX, NCELL, NCVTOTAL = old

    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3 H2 horizontal graph-radius-2 "
        "execution self-test: PASS"
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
    mapback_executed = False
    flow_refresh_executed = False
    reprojection_executed = False
    h1base = None
    base = None

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
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3 — CONTROLLED H2 HORIZONTAL "
        "GRAPH-RADIUS-2 OCCUPANCY-EXTENSION EXECUTION"
    )
    print("=" * 214)
    print("ONE FROZEN E2 CANDIDATE ONLY: dk=0 AND |dj|+|di|<=2 FROM EXACT E0.")
    print("NO RADIUS 3. NO VERTICAL SUPPORT. NO H2+V1 FALLBACK.")
    print("NO CAPACITY OR CV-MASS RELAXATION. NO CLIPPING. NO GLOBAL RESCALING.")
    print("NO PHYSICAL-TIME ADVANCE. NO DAY500 CONTINUATION. NO F5. NO TRAINING.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority, then import exact H1 helper implementation.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R2_commit", parent == PARENT_R2_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        h1base = load_module(root / H1EXEC, "postv16_av4_h2_h1base")

        # The H1 source itself carries the exact lower-level source authority map.
        for fn, expected in h1base.SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # R3-R3-R3 is the exact utility/physics base used by the H1 execution runner.
        base = load_module(root / h1base.R3R3R3, "postv16_av4_h2_base")

        # ------------------------------------------------------------------------------------------
        # Formal R2 freeze binding.
        # ------------------------------------------------------------------------------------------
        stage = "R2_freeze_binding"
        r2dir = drive / R2_REL
        gate("R2_output_present", r2dir.is_dir(), str(r2dir))
        r2manifest = base.verify_manifest(r2dir, R2_MANIFEST)
        gate("R2_manifest_exact_5", len(r2manifest) == 5, len(r2manifest))

        load_json = base.load_json
        summary = load_json(r2dir / R2_SUMMARY)
        protocol = load_json(r2dir / R2_PROTOCOL)
        handoff = load_json(r2dir / R2_HANDOFF)

        gate("R2_status_exact", summary["status"] == R2_STATUS, summary["status"])
        gate(
            "R2_selected_H2_exact",
            summary["selected_candidate"] == "H2_HORIZONTAL_GRAPH_RADIUS_2"
            and int(summary["H2_pair_count"]) == EXPECTED_E2_PAIRS
            and int(summary["H2_global_cell_count"]) == EXPECTED_E2_GLOBAL_CELLS
            and float(summary["H2_minimum_unserved_mass_kg"]) == 0.0
            and summary["vertical_support"] is False,
        )
        gate(
            "R2_protocol_geometry_exact",
            protocol["E2"]["offset_rule"] == "dk=0 and |dj|+|di|<=2"
            and int(protocol["E2"]["offset_count_including_origin"]) == 13
            and int(protocol["E2"]["second_shell_offset_count"]) == 8
            and protocol["E2"]["vertical_neighbors"] is False
            and protocol["E2"]["radius_greater_than_2"] is False,
        )
        gate(
            "R2_handoff_exact",
            handoff["milestone"] == MILESTONE
            and handoff["authorized"] is True
            and handoff["execution"] is True
            and handoff["selected_candidate"] == "H2_HORIZONTAL_GRAPH_RADIUS_2",
        )

        # Preserve and bind the H1 scientific fail.
        h1fail_path = drive / H1_FAIL_REL / H1_FAIL_REPORT
        gate("H1_scientific_fail_report_present", h1fail_path.is_file(), str(h1fail_path))
        h1fail = load_json(h1fail_path)
        gate("H1_fail_status_exact", h1fail["status"] == H1_FAIL_STATUS, h1fail["status"])
        gate("H1_fail_stage_exact", h1fail["failed_stage"] == "frozen_E1_assignment", h1fail["failed_stage"])
        gate(
            "H1_fail_gate_exact",
            h1fail["failed_gate"] == "E1_SINGLE_RING_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT",
            h1fail["failed_gate"],
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact accepted event state and parent split state using H1 constants.
        # ------------------------------------------------------------------------------------------
        stage = "state_authority_binding"
        f2d = drive / h1base.F2R3_REL
        evd = drive / h1base.R3R1R2_REL
        a2d = drive / h1base.A2E_REL
        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        gate("R3R1R2_output_present", evd.is_dir(), str(evd))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        base.verify_manifest(f2d, h1base.F2R3_MANIFEST)
        base.verify_manifest(evd, h1base.R3R1R2_MANIFEST)
        base.verify_manifest(a2d, h1base.A2E_MANIFEST)

        with np.load(f2d / h1base.F2R3_STATE, allow_pickle=False) as z:
            parent_cv_mass = np.asarray(z["parent_CV_component_mass_kg"], dtype=np.float64)
            parent_residual_grid = np.asarray(z["residual_grid_component_mass_kg"], dtype=np.float64)
            parent_mapped_grid = np.asarray(z["mapped_grid_component_mass_kg"], dtype=np.float64)
            sub_parent_mass = np.asarray(z["subsegment_parent_mass_kg"], dtype=np.float64)
            sub_flat = np.asarray(z["subsegment_flat_cell"], dtype=np.int64)
            sub_stream = np.asarray(z["subsegment_streamline"], dtype=np.int64)
            sub_cv = np.asarray(z["subsegment_control_volume"], dtype=np.int64)
            sub_pv = np.asarray(z["subsegment_pore_volume_m3"], dtype=np.float64)

        with np.load(evd / h1base.R3R1R2_STATE, allow_pickle=False) as z:
            event_cv_mass = np.asarray(z["partial_CV_component_mass_kg"], dtype=np.float64)
            event_cv_sat = np.asarray(z["partial_CV_saturation"], dtype=np.float64)
            elapsed = float(np.asarray(z["elapsed_days"]).reshape(()))
            remaining = float(np.asarray(z["remaining_days"]).reshape(()))
            substeps = int(np.asarray(z["accepted_substeps"]).reshape(()))

        with np.load(a2d / h1base.A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}

        parent_grid_mass = np.asarray(epoch["parent_component_mass_kg"], dtype=np.float64)
        parent_pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        grid_pv = np.asarray(epoch["pore_volume_m3"], dtype=np.float64)
        p_ref = float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        parent_xyz = np.asarray(epoch["streamline_xyz_m"], dtype=np.float64)
        parent_tof = np.asarray(epoch["streamline_tof_s"], dtype=np.float64)
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)
        grid_phi = np.asarray(epoch["paired_porosity"], dtype=np.float64)

        gate(
            "state_shapes_exact",
            parent_cv_mass.shape == (NSL, NCV)
            and event_cv_mass.shape == (NSL, NCV)
            and event_cv_sat.shape == (NSL, NCV)
            and parent_residual_grid.shape == GRID
            and parent_mapped_grid.shape == GRID
            and parent_grid_mass.shape == GRID
            and parent_pressure.shape == GRID
            and grid_pv.shape == GRID
            and parent_xyz.shape == (NSL, NN, 3)
            and parent_tof.shape == (NSL, NN),
        )
        gate(
            "event_identity_exact",
            substeps == EVENT_SUBSTEPS
            and abs(elapsed - EVENT_ELAPSED) <= 1e-12
            and abs(remaining - EVENT_REMAINING) <= 1e-12,
            {"substeps": substeps, "elapsed": elapsed, "remaining": remaining},
        )

        max_abs = base.max_abs
        gate(
            "Day365_split_grid_exact",
            max_abs(parent_mapped_grid + parent_residual_grid - parent_grid_mass) <= 1e-9,
            max_abs(parent_mapped_grid + parent_residual_grid - parent_grid_mass),
        )

        # ------------------------------------------------------------------------------------------
        # Reconstruct exact E0 ownership and raw-event EOS targets.
        # ------------------------------------------------------------------------------------------
        stage = "E0_authority_reconstruction"
        r3event = load_module(root / h1base.R3_EVENT, "postv16_av4_h2_r3event")
        f4r3 = load_module(root / h1base.F4R3, "postv16_av4_h2_f4r3")
        a2e = load_module(root / h1base.A2E, "postv16_av4_h2_a2e")
        r2phys = load_module(root / h1base.R2, "postv16_av4_h2_r2")
        e37 = load_module(root / h1base.E37A, "postv16_av4_h2_e37")
        sg2 = load_module(root / h1base.SG2, "postv16_av4_h2_sg2")
        sg3 = load_module(root / h1base.SG3, "postv16_av4_h2_sg3")
        sg4 = load_module(root / h1base.SG4, "postv16_av4_h2_sg4")
        sg5 = load_module(root / h1base.SG5, "postv16_av4_h2_sg5")
        sg6 = load_module(root / h1base.SG6, "postv16_av4_h2_sg6")
        sg7d = load_module(root / h1base.SG7D, "postv16_av4_h2_sg7d")
        r3r2r1 = load_module(root / h1base.R3R2R1, "postv16_av4_h2_r3r2r1")
        r1mod = load_module(root / h1base.R3R3R3R1, "postv16_av4_h2_r1")

        parent_operator = sg7d.build_subsegment_operator(
            parent_xyz,
            parent_tof / 86400.0,
            np.asarray(epoch["streamline_weight_m3_s"], dtype=np.float64) * 86400.0,
        )
        geometry = e37.build_control_volume_geometry(
            r2phys,
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
            {"subsegments": int(len(sub_flat)), "pv_Linf": max_abs(sub_pv - geom_pv)},
        )

        event_sub_sat = event_cv_sat.reshape(-1)[geom_cv_id]
        event_sub_sg = np.clip(event_sub_sat - BACKGROUND, 0.0, MAX_SG)
        event_sub_rho = np.asarray(
            r2phys.gas_density_from_state(event_sub_sat, geom_pseg, p_ref),
            dtype=np.float64,
        )
        raw_event_sub_mass = geom_pv * event_sub_rho * event_sub_sg

        aggregate_pairs = base.aggregate_pairs
        e0_cv, e0_cell, parent_pair_mass, e0_key = aggregate_pairs(
            cv_id_f2, sub_flat, sub_parent_mass
        )
        q_cv, q_cell, raw_event_pair_mass, q_key = aggregate_pairs(
            geom_cv_id, geom_flat, raw_event_sub_mass
        )
        gate(
            "E0_parent_and_raw_event_pair_support_identical",
            np.array_equal(e0_key, q_key)
            and np.array_equal(e0_cv, q_cv)
            and np.array_equal(e0_cell, q_cell),
            len(e0_key),
        )
        gate("E0_pair_count_exact_269721", len(e0_key) == EXPECTED_E0_PAIRS, len(e0_key))

        cell_capacity = np.asarray(
            a2e.local_mass(
                r2phys,
                np.full(GRID, INJECTED, dtype=np.float64),
                parent_pressure,
                p_ref,
                grid_pv,
            ),
            dtype=np.float64,
        )
        sci_gate(
            "source_authentic_cell_capacity_finite_positive",
            np.isfinite(cell_capacity).all() and float(np.min(cell_capacity)) > 0.0,
            [float(np.min(cell_capacity)), float(np.max(cell_capacity))],
        )

        # ------------------------------------------------------------------------------------------
        # Execute the one frozen E2/H2 candidate.
        # ------------------------------------------------------------------------------------------
        stage = "frozen_E2_assignment"
        lp_executed = True
        assignment = execute_e2_assignment(
            e0_cv=e0_cv,
            e0_cell=e0_cell,
            parent_pair_mass=parent_pair_mass,
            raw_event_pair_mass=raw_event_pair_mass,
            parent_cv_mass=parent_cv_mass,
            event_cv_mass=event_cv_mass,
            residual_grid_mass=parent_residual_grid,
            cell_capacity=cell_capacity,
            h1base=h1base,
            r1mod=r1mod,
        )
        mapback_executed = True

        event_grid_mass = np.asarray(assignment["event_grid_mass"], dtype=np.float64).reshape(GRID)
        event_mapped_grid = np.asarray(assignment["event_mapped_grid_mass"], dtype=np.float64).reshape(GRID)
        event_cv_reconstructed = np.asarray(
            assignment["event_CV_mass_reconstructed"], dtype=np.float64
        ).reshape(NSL, NCV)

        cv_tol = max(1e-6, 1e-10 * max(float(np.max(np.abs(event_cv_mass))), 1.0))
        grid_tol = max(1e-6, 1e-10 * max(float(np.max(np.abs(cell_capacity))), 1.0))

        sci_gate(
            "E2_event_CV_mass_equalities_exact",
            max_abs(event_cv_reconstructed - event_cv_mass) <= cv_tol,
            {"Linf_kg": max_abs(event_cv_reconstructed - event_cv_mass), "tol": cv_tol},
        )
        sci_gate(
            "E2_event_grid_nonnegative",
            float(np.min(event_grid_mass)) >= -grid_tol,
            float(np.min(event_grid_mass)),
        )
        sci_gate(
            "E2_event_grid_within_source_authentic_capacity",
            float(np.max(event_grid_mass - cell_capacity)) <= grid_tol,
            float(np.max(event_grid_mass - cell_capacity)),
        )
        sci_gate(
            "E2_residual_sidecar_unchanged",
            max_abs(event_grid_mass - event_mapped_grid - parent_residual_grid) <= 1e-8,
            max_abs(event_grid_mass - event_mapped_grid - parent_residual_grid),
        )

        fsum_array = base.fsum_array
        global_resid = (
            fsum_array(event_grid_mass)
            - fsum_array(parent_residual_grid)
            - fsum_array(event_cv_mass)
        )
        sci_gate(
            "E2_global_component_mass_exact",
            abs(global_resid) <= max(1e-5, 1e-10 * max(fsum_array(event_grid_mass), 1.0)),
            global_resid,
        )
        gate(
            "E2_six_stage_assignment_success",
            assignment["stage0_minimum_unserved_mass_kg"]
            <= max(1e-6, 1e-10 * max(fsum_array(event_cv_mass), 1.0))
            and all(
                assignment[k]["status"] == 0
                for k in ["stage1_meta", "stage2_meta", "stage3_meta", "stage4_meta", "stage5_meta"]
            ),
            {
                "stage0_minimum_unserved_mass_kg": assignment["stage0_minimum_unserved_mass_kg"],
                "stage1": assignment["stage1_meta"],
                "stage2": assignment["stage2_meta"],
                "stage3": assignment["stage3_meta"],
                "stage4": assignment["stage4_meta"],
                "stage5": assignment["stage5_meta"],
            },
        )
        gate(
            "E2_actual_H2_shell_mass_matches_stage1_optimum",
            abs(
                assignment["H2_shell_mass_actual_kg"]
                - assignment["stage1_minimum_H2_shell_mass_kg"]
            )
            <= max(1e-5, 1e-10 * max(assignment["stage1_minimum_H2_shell_mass_kg"], 1.0)),
            {
                "actual_kg": assignment["H2_shell_mass_actual_kg"],
                "optimum_kg": assignment["stage1_minimum_H2_shell_mass_kg"],
            },
        )
        gate(
            "E2_actual_total_extension_mass_matches_stage2_optimum",
            abs(
                assignment["total_extension_mass_actual_kg"]
                - assignment["stage2_minimum_total_extension_mass_kg"]
            )
            <= max(1e-5, 1e-10 * max(assignment["stage2_minimum_total_extension_mass_kg"], 1.0)),
            {
                "actual_kg": assignment["total_extension_mass_actual_kg"],
                "optimum_kg": assignment["stage2_minimum_total_extension_mass_kg"],
            },
        )

        # ------------------------------------------------------------------------------------------
        # Same-time inversion and the one already-authorized event flow refresh.
        # ------------------------------------------------------------------------------------------
        stage = "event_parent_pressure_mass_inversion"
        try:
            event_sg_start = a2e.invert_local_mass(
                r2phys,
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

        event_sat_start = BACKGROUND + np.asarray(event_sg_start, dtype=np.float64)
        sci_gate(
            "event_parent_pressure_saturation_bounds",
            float(np.min(event_sat_start)) >= BACKGROUND - 1e-10
            and float(np.max(event_sat_start)) <= INJECTED + 1e-10,
            [float(np.min(event_sat_start)), float(np.max(event_sat_start))],
        )

        stage = "single_same_time_event_flow_refresh"
        permeability_md = np.loadtxt(
            root / h1base.PERM,
            skiprows=1,
            dtype=np.float64,
        ).reshape(GRID, order="C")

        try:
            event_flow = r3event.refresh_flow_epoch(
                label="event_refresh_E2_H2",
                r3=f4r3,
                a2e=a2e,
                r2=r2phys,
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
        flow_refresh_executed = True

        # ------------------------------------------------------------------------------------------
        # Bounded reprojection on refreshed flow geometry.
        # ------------------------------------------------------------------------------------------
        stage = "refreshed_geometry_bounded_reprojection"
        try:
            event_split = f4r3.bounded_reproject(
                r2=r2phys,
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
        reprojection_executed = True

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
            <= max(1e-5, 1e-10 * max(fsum_array(event_grid_mass), 1.0)),
            float(event_split["ledger_residual_kg"]),
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

        stage = "refreshed_event_recurrent_state_rebuild"
        event_fields = r3event.rebuild_transport_epoch_fields(
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
                    "permeability_cv_md",
                    "porosity_cv",
                    "nw_cv",
                    "no_cv",
                    "krw_max_cv",
                    "kro_max_cv",
                ]
            ),
        )

        relative_l2 = base.relative_l2
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
        # Publish refreshed Day413.786... state and stop before physical-time continuation.
        # ------------------------------------------------------------------------------------------
        stage = "artifact_publication"
        deterministic_npz_bytes = base.deterministic_npz_bytes
        json_bytes = base.json_bytes
        csv_bytes = base.csv_bytes
        immutable_publish = base.immutable_publish
        sha256_file = base.sha256_file

        state_npz = deterministic_npz_bytes(
            {
                "event_day": np.asarray(EVENT_DAY),
                "physical_time_advanced_in_R3R3R3R3R3": np.asarray(False),
                "event_grid_component_mass_kg": event_grid_mass,
                "event_parent_pressure_saturation": event_sat_start,
                "E0_pair_cv_id": e0_cv,
                "E0_pair_flat_cell": e0_cell,
                "E0_parent_ownership_mass_kg": parent_pair_mass,
                "E1_pair_key": assignment["e1_key"],
                "E2_pair_cv_id": assignment["e2_cv"],
                "E2_pair_flat_cell": assignment["e2_cell"],
                "E2_pair_is_E0": assignment["is_e0"],
                "E2_pair_is_E1": assignment["is_e1"],
                "E2_pair_event_mass_kg": assignment["x_pair_mass"],
                "E0_parent_continuity_target_kg": assignment["target0"],
                "E0_raw_event_EOS_target_kg": assignment["qtarget0"],
                "H2_event_mapped_grid_mass_kg": event_mapped_grid,
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
                "permeability_cv_md": np.asarray(event_fields["permeability_cv_md"]),
                "porosity_cv": np.asarray(event_fields["porosity_cv"]),
                "nw_cv": np.asarray(event_fields["nw_cv"]),
                "no_cv": np.asarray(event_fields["no_cv"]),
                "krw_max_cv": np.asarray(event_fields["krw_max_cv"]),
                "kro_max_cv": np.asarray(event_fields["kro_max_cv"]),
            }
        )

        shell_fraction = (
            assignment["H2_shell_mass_actual_kg"] / fsum_array(event_cv_mass)
        )
        extension_fraction = (
            assignment["total_extension_mass_actual_kg"] / fsum_array(event_cv_mass)
        )

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "physical_time_advanced": False,
            "E0_pair_count": int(len(assignment["e0_key"])),
            "E1_pair_count": int(len(assignment["e1_key"])),
            "E2_pair_count": int(len(assignment["e2_key"])),
            "E2_global_cell_count": int(len(assignment["e2_global_cells"])),
            "globally_new_H1_cell_count": int(len(assignment["globally_new_h1_cells"])),
            "globally_new_H2_cell_count": int(len(assignment["globally_new_h2_cells"])),
            "stage0_minimum_unserved_mass_kg":
                assignment["stage0_minimum_unserved_mass_kg"],
            "minimum_H2_shell_mass_kg":
                assignment["stage1_minimum_H2_shell_mass_kg"],
            "minimum_H2_shell_mass_fraction": shell_fraction,
            "minimum_total_extension_mass_kg":
                assignment["stage2_minimum_total_extension_mass_kg"],
            "minimum_total_extension_mass_fraction": extension_fraction,
            "parent_ownership_L1_kg": assignment["stage3_parent_L1_kg"],
            "raw_event_EOS_L1_kg": assignment["stage4_raw_L1_kg"],
            "H2_shell_CV_count": assignment["H2_shell_CV_count"],
            "H2_shell_streamline_count": assignment["H2_shell_streamline_count"],
            "H2_shell_cell_count": assignment["H2_shell_cell_count"],
            "any_extension_CV_count": assignment["any_extension_CV_count"],
            "event_grid_mass_kg": fsum_array(event_grid_mass),
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

        audit = {
            "milestone": MILESTONE,
            "support_expansion_type":
                "fixed_per_CV_same_layer_horizontal_manhattan_graph_radius_2",
            "vertical_support": False,
            "radius_greater_than_2": False,
            "H2_plus_V1_fallback": False,
            "stage0_minimum_unserved_mass_kg":
                assignment["stage0_minimum_unserved_mass_kg"],
            "stage1_minimum_H2_shell_mass_kg":
                assignment["stage1_minimum_H2_shell_mass_kg"],
            "stage2_minimum_total_extension_mass_kg":
                assignment["stage2_minimum_total_extension_mass_kg"],
            "stage3_parent_ownership_L1_kg":
                assignment["stage3_parent_L1_kg"],
            "stage4_raw_event_EOS_L1_kg":
                assignment["stage4_raw_L1_kg"],
            "stage5_tiebreak_objective":
                assignment["stage5_tiebreak"],
            "H2_shell_CV_count": assignment["H2_shell_CV_count"],
            "H2_shell_streamline_count": assignment["H2_shell_streamline_count"],
            "H2_shell_cell_count": assignment["H2_shell_cell_count"],
            "any_extension_CV_count": assignment["any_extension_CV_count"],
            "any_extension_streamline_count": assignment["any_extension_streamline_count"],
            "any_extension_cell_count": assignment["any_extension_cell_count"],
            "event_CV_mass_Linf_error_kg":
                max_abs(event_cv_reconstructed - event_cv_mass),
            "global_event_mass_residual_kg": global_resid,
            "capacity_relaxed": False,
            "CV_mass_relaxed": False,
            "mass_clipped": False,
            "global_rescaling": False,
        }

        handoff_out = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R4",
            "name":
                "Refreshed Event-Epoch Day413.78677770818403 to Day500 Controlled Continuation Execution",
            "authorized": True,
            "execution": True,
            "required_R3R3R3R3R3_status": STATUS_PASS,
            "parent_event_day": EVENT_DAY,
            "remaining_days": EVENT_REMAINING,
            "required_parent_state":
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Refreshed_Event_Recurrent_State.npz",
            "single_event_refresh_already_consumed": True,
            "second_event_refresh_authorized": False,
            "further_support_expansion_authorized": False,
            "scope": [
                "resume exactly 86.21322229181597 days on refreshed event epoch",
                "use unchanged raw F4 internal operator",
                "use unchanged F4-R2 terminal producer pass-through",
                "a second interior invariant-domain conflict is SCIENTIFIC FAIL",
                "on Day500 success execute Day500 same-time refresh/reprojection certification",
            ],
            "not_authorized": [
                "second event refresh",
                "radius >2 support expansion",
                "vertical support",
                "H2+V1 fallback",
                "F5",
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
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "R2_H2_freeze_bound": True,
            "E2_execution_performed": True,
            "LP_executed": True,
            "support_domain_changed_exactly_as_frozen": True,
            "vertical_support_used": False,
            "radius_greater_than_2_used": False,
            "H2_plus_V1_fallback_used": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "residual_sidecar_changed_during_event_mapback": False,
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
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_Summary.json":
                json_bytes(summary_out),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_H2_Assignment_Audit.json":
                json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Refreshed_Event_Recurrent_State.npz":
                state_npz,
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_R3R3R4_Handoff_Contract.json":
                json_bytes(handoff_out),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R3-R3: H2 HORIZONTAL GRAPH-RADIUS-2 "
            "ASSIGNMENT + FLOW REFRESH / REPROJECTION PASS"
        )
        print("=" * 214)
        print("Event day                                :", EVENT_DAY)
        print("E0 / E1 / E2 pair counts                :",
              len(assignment["e0_key"]), "/",
              len(assignment["e1_key"]), "/",
              len(assignment["e2_key"]))
        print("E2 global cell count                    :", len(assignment["e2_global_cells"]))
        print("Stage-0 minimum unserved mass kg        :", assignment["stage0_minimum_unserved_mass_kg"])
        print("Minimum H2 shell mass kg                :", assignment["stage1_minimum_H2_shell_mass_kg"])
        print("Minimum total extension mass kg         :", assignment["stage2_minimum_total_extension_mass_kg"])
        print("H2 shell CV / streamline / cell count   :",
              assignment["H2_shell_CV_count"], "/",
              assignment["H2_shell_streamline_count"], "/",
              assignment["H2_shell_cell_count"])
        print("Event CV mass Linf error kg             :", max_abs(event_cv_reconstructed - event_cv_mass))
        print("Event grid min mass kg                  :", float(np.min(event_grid_mass)))
        print("Event grid max capacity excess kg       :", float(np.max(event_grid_mass - cell_capacity)))
        print("Same-time event flow refresh            : EXECUTED ONCE")
        print("Refreshed-geometry reprojection         : PASS")
        print("Physical-time advance                   : False")
        print("POSTV16-AV4-F4-R3-R3-R4                : AUTHORIZED")
        print("F5 / training / A3-E2 / general AV4     : NOT AUTHORIZED")
        print("=" * 214)
        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True, exist_ok=True)
        json_bytes = (
            base.json_bytes if base is not None
            else lambda x: (json.dumps(x, indent=2, sort_keys=True) + "\n").encode()
        )
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "R2_H2_freeze_preserved": True,
            "LP_executed": lp_executed,
            "E2_mapback_executed": mapback_executed,
            "flow_refresh_executed": flow_refresh_executed,
            "event_reprojection_executed": reprojection_executed,
            "radius_greater_than_2_used": False,
            "vertical_support_used": False,
            "H2_plus_V1_fallback_used": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
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
        p = failed / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = failed / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Scientific_Fail_Report_"
                + hashlib.sha256(data).hexdigest()[:12] + ".json"
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
        print("NO RADIUS-3, VERTICAL, H2+V1, ALTERNATE REPAIR, SECOND REFRESH, OR AUTO-RERUN.")
        print("R3-R3-R4 / F5 / training: NOT AUTHORIZED")
        print("=" * 214)
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        json_bytes = (
            base.json_bytes if base is not None
            else lambda x: (json.dumps(x, indent=2, sort_keys=True) + "\n").encode()
        )
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "R2_H2_freeze_preserved": True,
            "LP_executed": lp_executed,
            "E2_mapback_executed": mapback_executed,
            "flow_refresh_executed": flow_refresh_executed,
            "event_reprojection_executed": reprojection_executed,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12] + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("R3-R3-R3-R3 scientific FAIL and R2 H2 freeze remain immutable.")
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
