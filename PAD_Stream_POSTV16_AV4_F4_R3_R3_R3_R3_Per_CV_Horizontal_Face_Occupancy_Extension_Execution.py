#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3"

STATUS_PASS = (
    "AV4F4R3R3R3R3_FROZEN_SINGLE_RING_PER_CV_HORIZONTAL_FACE_OCCUPANCY_"
    "EXTENSION_FEASIBLE_MINIMUM_EXTENSION_MASS_ASSIGNMENT_PASS_SINGLE_SAME_TIME_"
    "FLOW_REFRESH_AND_REFRESHED_GEOMETRY_REPROJECTION_PASS_NO_PHYSICAL_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3_FROZEN_E1_ASSIGNMENT_OR_SINGLE_FLOW_REFRESH_OR_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_H2_NO_VERTICAL_OR_DIAGONAL_EXTENSION_NO_ALTERNATE_REPAIR"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R3R3R2_COMMIT = "6f2e7b423d75eb1089370d2ec6529a222ded44d4"

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

R3R3R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R2_"
    "Per_CV_Horizontal_Face_Occupancy_Extension_Freeze.py"
)
R3R3R3R2_BLOB = "3768e7b2793b959be83629bc3299e81353ca4af2"

R3R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_"
    "Ownership_Reconciled_Event_MapBack_and_Flow_Refresh_Execution.py"
)
R3R3R3_BLOB = "b2c129bd067ef75163c3f06de5c15adc53ae5633"

R3R3R3R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R1_"
    "S0_CV_Cell_Capacity_Hall_Deficit_Localization.py"
)
R3R3R3R1_BLOB = "304f68abf78a55cf00917667cff33e20b415db46"

R3_EVENT = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_"
    "First_Event_Flow_Epoch_Renewal_Execution.py"
)
R3_EVENT_BLOB = "4aaf46d18253ac0fc4a8e50ffb3d30e841c93709"

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
    R3R3R3R2: R3R3R3R2_BLOB,
    R3R3R3: R3R3R3_BLOB,
    R3R3R3R1: R3R3R3R1_BLOB,
    R3_EVENT: R3_EVENT_BLOB,
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

R2FREEZE_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R2_Per_CV_Horizontal_Face_Occupancy_Extension_Freeze"
)
R2FREEZE_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R2_Summary.json"
R2FREEZE_PROTOCOL = "POSTV16_AV4_F4_R3_R3_R3_R2_Frozen_Occupancy_Extension_Protocol.json"
R2FREEZE_HANDOFF = "POSTV16_AV4_F4_R3_R3_R3_R2_R3R3R3R3_Execution_Handoff_Contract.json"
R2FREEZE_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R2_Artifact_Manifest.csv"
R2FREEZE_STATUS = (
    "AV4F4R3R3R3R2_R3R3R3R1_EXACT_S0_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT_"
    "BOUND_SINGLE_NONRECURSIVE_PER_CV_SAME_LAYER_XY_FACE_NEIGHBOR_OCCUPANCY_"
    "EXTENSION_PROSPECTIVELY_FROZEN_NO_EXECUTION"
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
    / "POSTV16_AV4_F4_R3_R3_R3_R3_Per_CV_Horizontal_Face_Extension_Execution"
)
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_BLOCKED"


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


def incidence(rows_idx: np.ndarray, nrows: int, ncols: int) -> csr_matrix:
    cols = np.arange(ncols, dtype=np.int64)
    return coo_matrix(
        (
            np.ones(ncols, dtype=np.float64),
            (np.asarray(rows_idx, dtype=np.int64), cols),
        ),
        shape=(nrows, ncols),
    ).tocsr()


def build_e1_support(
    e0_cv: np.ndarray,
    e0_cell: np.ndarray,
) -> dict[str, np.ndarray]:
    cv = np.asarray(e0_cv, dtype=np.int64).reshape(-1)
    cell = np.asarray(e0_cell, dtype=np.int64).reshape(-1)
    if cv.shape != cell.shape:
        raise GateError("E0_pair_shape_mismatch")

    k = cell // (NY * NX)
    rem = cell % (NY * NX)
    j = rem // NX
    i = rem % NX

    keys = [cv * NCELL + cell]

    # Exactly one non-recursive same-layer ±x/±y face ring from E0 only.
    masks_and_cells = [
        (i > 0, cell - 1),
        (i < NX - 1, cell + 1),
        (j > 0, cell - NX),
        (j < NY - 1, cell + NX),
    ]
    for mask, neighbor_cell in masks_and_cells:
        keys.append(cv[mask] * NCELL + neighbor_cell[mask])

    e1_key = np.unique(np.concatenate(keys))
    e1_cv = (e1_key // NCELL).astype(np.int64)
    e1_cell = (e1_key % NCELL).astype(np.int64)

    e0_key = np.unique(cv * NCELL + cell)
    pos = np.searchsorted(e1_key, e0_key)
    if np.any(pos >= len(e1_key)) or not np.array_equal(e1_key[pos], e0_key):
        raise GateError("E0_not_subset_of_E1")

    is_e0 = np.zeros(len(e1_key), dtype=bool)
    is_e0[pos] = True

    e0_global_cells = np.unique(cell)
    e1_global_cells = np.unique(e1_cell)
    globally_new_h1 = np.setdiff1d(
        e1_global_cells,
        e0_global_cells,
        assume_unique=True,
    )

    added_per_cv = (
        np.bincount(e1_cv, minlength=NCVTOTAL)
        - np.bincount(cv, minlength=NCVTOTAL)
    )

    return {
        "e0_key": e0_key,
        "e1_key": e1_key,
        "e1_cv": e1_cv,
        "e1_cell": e1_cell,
        "is_e0": is_e0,
        "e0_indices_in_e1": pos.astype(np.int64),
        "e0_global_cells": e0_global_cells,
        "e1_global_cells": e1_global_cells,
        "globally_new_h1_cells": globally_new_h1,
        "added_pairs_per_cv": added_per_cv.astype(np.int64),
    }


def solve_stage1_min_extension(
    e1_cv: np.ndarray,
    e1_cell: np.ndarray,
    is_e0: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    n = len(e1_cv)
    Aeq = incidence(e1_cv, NCVTOTAL, n)
    Acap = incidence(e1_cell, NCELL, n)
    c = (~np.asarray(is_e0, dtype=bool)).astype(np.float64)
    res = linprog(
        c,
        A_ub=Acap,
        b_ub=available,
        A_eq=Aeq,
        b_eq=demand,
        bounds=[(0.0, None)] * n,
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E1_stage1_minimum_extension_mass_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x, dtype=np.float64)
    return x, float(np.dot(c, x)), {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def solve_stage2_parent_L1(
    e1_cv: np.ndarray,
    e1_cell: np.ndarray,
    e0_idx: np.ndarray,
    halo_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    target0: np.ndarray,
    halo_opt: float,
    halo_tol: float,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    n = len(e1_cv)
    m = len(e0_idx)
    Aeq_x = incidence(e1_cv, NCVTOTAL, n)
    Acap_x = incidence(e1_cell, NCELL, n)

    # Selector S: x[E0] in the exact E0 lexicographic order.
    S = coo_matrix(
        (
            np.ones(m),
            (np.arange(m, dtype=np.int64), e0_idx),
        ),
        shape=(m, n),
    ).tocsr()
    Iu = eye(m, format="csr")

    Aub = vstack(
        [
            hstack([S, -Iu], format="csr"),
            hstack([-S, -Iu], format="csr"),
            hstack([Acap_x, csr_matrix((NCELL, m))], format="csr"),
        ],
        format="csr",
    )
    bub = np.concatenate([target0, -target0, available])

    halo_row = csr_matrix(
        (
            halo_mask.astype(np.float64),
            (
                np.zeros(n, dtype=np.int64),
                np.arange(n, dtype=np.int64),
            ),
        ),
        shape=(1, n + m),
    )
    Aub = vstack([Aub, halo_row], format="csr")
    bub = np.concatenate([bub, [halo_opt + halo_tol]])

    Aeq = hstack([Aeq_x, csr_matrix((NCVTOTAL, m))], format="csr")
    c = np.concatenate([np.zeros(n), np.ones(m)])

    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=demand,
        bounds=[(0.0, None)] * (n + m),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E1_stage2_parent_ownership_L1_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x[:n], dtype=np.float64)
    obj = float(np.sum(np.asarray(res.x[n:], dtype=np.float64)))
    return x, obj, {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def solve_stage3_raw_L1(
    e1_cv: np.ndarray,
    e1_cell: np.ndarray,
    e0_idx: np.ndarray,
    halo_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    target0: np.ndarray,
    qtarget0: np.ndarray,
    halo_opt: float,
    halo_tol: float,
    parent_opt: float,
    parent_tol: float,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    n = len(e1_cv)
    m = len(e0_idx)
    Aeq_x = incidence(e1_cv, NCVTOTAL, n)
    Acap_x = incidence(e1_cell, NCELL, n)
    S = coo_matrix(
        (np.ones(m), (np.arange(m), e0_idx)),
        shape=(m, n),
    ).tocsr()
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
    bub = np.concatenate(
        [target0, -target0, qtarget0, -qtarget0, available]
    )

    halo_row = csr_matrix(
        (
            halo_mask.astype(np.float64),
            (np.zeros(n, dtype=np.int64), np.arange(n, dtype=np.int64)),
        ),
        shape=(1, n + 2 * m),
    )
    parent_row = csr_matrix(
        (
            np.ones(m),
            (
                np.zeros(m, dtype=np.int64),
                n + np.arange(m, dtype=np.int64),
            ),
        ),
        shape=(1, n + 2 * m),
    )
    Aub = vstack([Aub, halo_row, parent_row], format="csr")
    bub = np.concatenate(
        [bub, [halo_opt + halo_tol, parent_opt + parent_tol]]
    )

    Aeq = hstack([Aeq_x, csr_matrix((NCVTOTAL, 2 * m))], format="csr")
    c = np.concatenate([np.zeros(n + m), np.ones(m)])

    res = linprog(
        c,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=demand,
        bounds=[(0.0, None)] * (n + 2 * m),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E1_stage3_raw_event_EOS_L1_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x[:n], dtype=np.float64)
    obj = float(np.sum(np.asarray(res.x[n + m :], dtype=np.float64)))
    return x, obj, {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def solve_stage4_tiebreak(
    e1_cv: np.ndarray,
    e1_cell: np.ndarray,
    e0_idx: np.ndarray,
    halo_mask: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    target0: np.ndarray,
    qtarget0: np.ndarray,
    halo_opt: float,
    halo_tol: float,
    parent_opt: float,
    parent_tol: float,
    raw_opt: float,
    raw_tol: float,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    n = len(e1_cv)
    m = len(e0_idx)
    Aeq_x = incidence(e1_cv, NCVTOTAL, n)
    Acap_x = incidence(e1_cell, NCELL, n)
    S = coo_matrix(
        (np.ones(m), (np.arange(m), e0_idx)),
        shape=(m, n),
    ).tocsr()
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
    bub = np.concatenate(
        [target0, -target0, qtarget0, -qtarget0, available]
    )

    halo_row = csr_matrix(
        (
            halo_mask.astype(np.float64),
            (np.zeros(n, dtype=np.int64), np.arange(n, dtype=np.int64)),
        ),
        shape=(1, n + 2 * m),
    )
    parent_row = csr_matrix(
        (
            np.ones(m),
            (
                np.zeros(m, dtype=np.int64),
                n + np.arange(m, dtype=np.int64),
            ),
        ),
        shape=(1, n + 2 * m),
    )
    raw_row = csr_matrix(
        (
            np.ones(m),
            (
                np.zeros(m, dtype=np.int64),
                n + m + np.arange(m, dtype=np.int64),
            ),
        ),
        shape=(1, n + 2 * m),
    )
    Aub = vstack([Aub, halo_row, parent_row, raw_row], format="csr")
    bub = np.concatenate(
        [
            bub,
            [
                halo_opt + halo_tol,
                parent_opt + parent_tol,
                raw_opt + raw_tol,
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
        bounds=[(0.0, None)] * (n + 2 * m),
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise ScientificFail(
            "E1_stage4_deterministic_tiebreak_LP_infeasible",
            {"status": int(res.status), "message": str(res.message)},
        )
    x = np.asarray(res.x[:n], dtype=np.float64)
    return x, float(np.dot(rank, x)), {
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def build_e0_targets(
    e0_cv: np.ndarray,
    parent_pair_mass: np.ndarray,
    raw_event_pair_mass: np.ndarray,
    parent_cv_mass: np.ndarray,
    event_cv_mass: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    m0 = np.asarray(parent_cv_mass, dtype=np.float64).reshape(-1)
    m1 = np.asarray(event_cv_mass, dtype=np.float64).reshape(-1)
    p = np.asarray(parent_pair_mass, dtype=np.float64)
    q = np.asarray(raw_event_pair_mass, dtype=np.float64)
    cv = np.asarray(e0_cv, dtype=np.int64)

    eps = max(1e-12, 1e-15 * max(float(np.max(m0)), 1.0))
    p_cv = np.bincount(cv, weights=p, minlength=NCVTOTAL)
    q_cv = np.bincount(cv, weights=q, minlength=NCVTOTAL)

    if np.max(np.abs(p_cv - m0)) > max(1e-7, 1e-12 * max(float(np.max(m0)), 1.0)):
        raise GateError("E0_parent_pair_mass_does_not_reconstruct_parent_CV")

    target = np.zeros_like(p)
    qtarget = np.zeros_like(q)

    positive_m0 = m0 > eps
    scale = np.zeros_like(m0)
    scale[positive_m0] = m1[positive_m0] / m0[positive_m0]
    target = p * scale[cv]

    zero_parent_positive = (~positive_m0) & (m1 > eps)
    for cv_id in np.flatnonzero(zero_parent_positive):
        mask = cv == cv_id
        qsum = float(q_cv[cv_id])
        if not np.any(mask) or qsum <= eps:
            raise ScientificFail(
                "zero_parent_positive_event_CV_lacks_raw_event_EOS_E0_support",
                int(cv_id),
            )
        target[mask] = q[mask] * (m1[cv_id] / qsum)

    for cv_id in np.flatnonzero(m1 > eps):
        mask = cv == cv_id
        qsum = float(q_cv[cv_id])
        if qsum <= eps:
            qtarget[mask] = target[mask]
        else:
            qtarget[mask] = q[mask] * (m1[cv_id] / qsum)

    return target, qtarget, int(np.sum(zero_parent_positive))


def execute_e1_assignment(
    *,
    e0_cv: np.ndarray,
    e0_cell: np.ndarray,
    parent_pair_mass: np.ndarray,
    raw_event_pair_mass: np.ndarray,
    parent_cv_mass: np.ndarray,
    event_cv_mass: np.ndarray,
    residual_grid_mass: np.ndarray,
    cell_capacity: np.ndarray,
    r1mod: Any,
) -> dict[str, Any]:
    support = build_e1_support(e0_cv, e0_cell)
    e1_cv = support["e1_cv"]
    e1_cell = support["e1_cell"]
    e0_idx = support["e0_indices_in_e1"]
    is_e0 = support["is_e0"]
    halo_mask = ~is_e0

    demand = np.asarray(event_cv_mass, dtype=np.float64).reshape(-1)
    residual = np.asarray(residual_grid_mass, dtype=np.float64).reshape(-1)
    cap = np.asarray(cell_capacity, dtype=np.float64).reshape(-1)
    available = cap - residual
    cap_tol = max(1e-7, 1e-12 * max(float(np.max(np.abs(cap))), 1.0))
    if float(np.min(available)) < -cap_tol:
        raise ScientificFail(
            "E1_residual_sidecar_exceeds_physical_capacity",
            {"minimum_available_capacity_kg": float(np.min(available))},
        )
    available = np.maximum(available, 0.0)

    target0, qtarget0, zero_parent_count = build_e0_targets(
        e0_cv,
        parent_pair_mass,
        raw_event_pair_mass,
        parent_cv_mass,
        event_cv_mass,
    )

    # Stage 0 feasibility: exact E1 only. If infeasible, preserve a new Hall witness.
    feas = r1mod.minimum_unserved_lp(
        e1_cv,
        e1_cell,
        demand,
        available,
        NCVTOTAL,
        NCELL,
    )
    total_demand = float(math.fsum(float(v) for v in demand))
    feas_tol = max(1e-6, 1e-10 * max(total_demand, 1.0))
    if float(feas["minimum_unserved_mass"]) > feas_tol:
        witness = r1mod.residual_mincut_witness(
            e1_cv,
            e1_cell,
            feas["pair_flow"],
            feas["unserved_cv"],
            demand,
            available,
            NCVTOTAL,
            NCELL,
            flow_tol=max(1e-8, 1e-12 * max(total_demand, 1.0)),
        )
        raise ScientificFail(
            "E1_SINGLE_RING_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT",
            {
                "minimum_unserved_mass_kg": float(feas["minimum_unserved_mass"]),
                "Hall_CV_count": int(np.sum(witness["cv_reachable"])),
                "Hall_cell_count": int(np.sum(witness["cell_reachable"])),
                "Hall_demand_kg": float(witness["demand_U"]),
                "Hall_capacity_kg": float(witness["capacity_N"]),
                "Hall_deficit_kg": float(witness["hall_deficit"]),
            },
        )

    # Stage 1: minimum extension mass.
    x1, halo_opt, meta1 = solve_stage1_min_extension(
        e1_cv,
        e1_cell,
        is_e0,
        demand,
        available,
    )
    halo_tol = max(1e-7, 1e-12 * max(abs(halo_opt), 1.0))

    # Stage 2: preserve parent-continuity target on original E0.
    x2, parent_opt, meta2 = solve_stage2_parent_L1(
        e1_cv,
        e1_cell,
        e0_idx,
        halo_mask,
        demand,
        available,
        target0,
        halo_opt,
        halo_tol,
    )
    parent_tol = max(1e-7, 1e-12 * max(abs(parent_opt), 1.0))

    # Stage 3: preserve raw event EOS target on E0.
    x3, raw_opt, meta3 = solve_stage3_raw_L1(
        e1_cv,
        e1_cell,
        e0_idx,
        halo_mask,
        demand,
        available,
        target0,
        qtarget0,
        halo_opt,
        halo_tol,
        parent_opt,
        parent_tol,
    )
    raw_tol = max(1e-7, 1e-12 * max(abs(raw_opt), 1.0))

    # Stage 4: deterministic tie break.
    x4, tie_obj, meta4 = solve_stage4_tiebreak(
        e1_cv,
        e1_cell,
        e0_idx,
        halo_mask,
        demand,
        available,
        target0,
        qtarget0,
        halo_opt,
        halo_tol,
        parent_opt,
        parent_tol,
        raw_opt,
        raw_tol,
    )

    x = np.asarray(x4, dtype=np.float64)
    mapped = np.bincount(e1_cell, weights=x, minlength=NCELL).astype(np.float64)
    cv_mass = np.bincount(e1_cv, weights=x, minlength=NCVTOTAL).astype(np.float64)
    grid = residual + mapped

    extension_mass = float(np.sum(x[halo_mask]))
    extension_positive = halo_mask & (x > max(1e-10, 1e-14 * max(extension_mass, 1.0)))
    extension_cvs = np.unique(e1_cv[extension_positive])
    extension_streamlines = np.unique(extension_cvs // NCV)
    extension_cells = np.unique(e1_cell[extension_positive])

    return {
        **support,
        "x_pair_mass": x,
        "target0": target0,
        "qtarget0": qtarget0,
        "event_mapped_grid_mass": mapped,
        "event_grid_mass": grid,
        "event_CV_mass_reconstructed": cv_mass,
        "available_capacity": available,
        "stage0_minimum_unserved_mass": float(feas["minimum_unserved_mass"]),
        "stage1_minimum_extension_mass": halo_opt,
        "stage2_parent_L1": parent_opt,
        "stage3_raw_L1": raw_opt,
        "stage4_tiebreak": tie_obj,
        "stage1_meta": meta1,
        "stage2_meta": meta2,
        "stage3_meta": meta3,
        "stage4_meta": meta4,
        "extension_mass_actual": extension_mass,
        "extension_CV_count": int(extension_cvs.size),
        "extension_streamline_count": int(extension_streamlines.size),
        "extension_cell_count": int(extension_cells.size),
        "zero_parent_positive_event_CV_count": zero_parent_count,
    }


def self_test() -> None:
    # Geometry test: exact one-ring, no recursion/vertical.
    old_ncv = globals()["NCVTOTAL"]
    old_ncell = globals()["NCELL"]
    old_grid = (globals()["NZ"], globals()["NY"], globals()["NX"])
    try:
        globals()["NCVTOTAL"] = 2
        globals()["NZ"] = 1
        globals()["NY"] = 1
        globals()["NX"] = 2
        globals()["NCELL"] = 2

        # Both CVs initially reach cell 0 only. E0 is infeasible for 10 kg demand
        # with 7 kg capacity in cell 0; one horizontal neighbor adds cell 1 (3 kg).
        e0_cv = np.array([0, 1], dtype=np.int64)
        e0_cell = np.array([0, 0], dtype=np.int64)
        support = build_e1_support(e0_cv, e0_cell)
        assert len(support["e1_key"]) == 4
        assert int(np.sum(~support["is_e0"])) == 2
        assert support["globally_new_h1_cells"].tolist() == [1]

        # Lightweight fake R1 diagnostic helper.
        class FakeR1:
            @staticmethod
            def minimum_unserved_lp(pair_cv, pair_cell, demand, available, ncv, ncell):
                n = len(pair_cv)
                Aeq = incidence(pair_cv, ncv, n)
                Acap = incidence(pair_cell, ncell, n)
                c = np.zeros(n)
                res = linprog(
                    c,
                    A_ub=Acap,
                    b_ub=available,
                    A_eq=Aeq,
                    b_eq=demand,
                    bounds=[(0.0, None)] * n,
                    method="highs",
                )
                if res.success:
                    x = np.asarray(res.x)
                    return {
                        "minimum_unserved_mass": 0.0,
                        "pair_flow": x,
                        "unserved_cv": np.zeros(ncv),
                    }
                raise AssertionError("toy E1 should be feasible")

        out = execute_e1_assignment(
            e0_cv=e0_cv,
            e0_cell=e0_cell,
            parent_pair_mass=np.array([5.0, 5.0]),
            raw_event_pair_mass=np.array([5.0, 5.0]),
            parent_cv_mass=np.array([5.0, 5.0]),
            event_cv_mass=np.array([5.0, 5.0]),
            residual_grid_mass=np.zeros(2),
            cell_capacity=np.array([7.0, 3.0]),
            r1mod=FakeR1,
        )
        assert abs(out["stage1_minimum_extension_mass"] - 3.0) < 1e-7
        assert np.max(np.abs(out["event_CV_mass_reconstructed"] - 5.0)) < 1e-7
        assert np.max(out["event_grid_mass"] - np.array([7.0, 3.0])) < 1e-7
    finally:
        globals()["NCVTOTAL"] = old_ncv
        globals()["NCELL"] = old_ncell
        globals()["NZ"], globals()["NY"], globals()["NX"] = old_grid

    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3 per-CV single-ring horizontal "
        "occupancy-extension execution self-test: PASS"
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

    # Load exact failed R3 implementation as helper authority only after its blob is checked.
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
        "POSTV16-AV4-F4-R3-R3-R3-R3 — CONTROLLED PER-CV SINGLE-RING "
        "HORIZONTAL FACE OCCUPANCY-EXTENSION EXECUTION"
    )
    print("=" * 214)
    print("ONE FROZEN E1 CANDIDATE ONLY. NON-RECURSIVE SAME-LAYER ±X/±Y.")
    print("NO H2. NO VERTICAL OR DIAGONAL EXTENSION. NO CAPACITY OR MASS RELAXATION.")
    print("NO CLIPPING. NO GLOBAL RESCALING. NO TIMESTEP CHANGE.")
    print("NO PHYSICAL-TIME ADVANCE. NO DAY500 CONTINUATION. NO F5. NO TRAINING.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository and freeze authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"
        parent = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD^"],
            check=True, text=True, stdout=subprocess.PIPE
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=True, text=True, stdout=subprocess.PIPE
        ).stdout.strip()
        gate("repository_parent_is_R3R3R3R2_commit", parent == PARENT_R3R3R3R2_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = (
                subprocess.run(
                    ["git", "-C", str(root), "hash-object", str(p)],
                    check=True, text=True, stdout=subprocess.PIPE
                ).stdout.strip()
                if p.is_file()
                else "missing"
            )
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        base = load_module(root / R3R3R3, "postv16_av4_r3r3r3_base")

        freeze_dir = drive / R2FREEZE_REL
        gate("R3R3R3R2_output_present", freeze_dir.is_dir(), str(freeze_dir))
        freeze_manifest = base.verify_manifest(freeze_dir, R2FREEZE_MANIFEST)
        gate("R3R3R3R2_manifest_exact_5", len(freeze_manifest) == 5, len(freeze_manifest))
        freeze_summary = base.load_json(freeze_dir / R2FREEZE_SUMMARY)
        freeze_protocol = base.load_json(freeze_dir / R2FREEZE_PROTOCOL)
        freeze_handoff = base.load_json(freeze_dir / R2FREEZE_HANDOFF)

        gate("R3R3R3R2_status_exact", freeze_summary["status"] == R2FREEZE_STATUS, freeze_summary["status"])
        gate(
            "R3R3R3R2_candidate_exact",
            freeze_summary["candidate_count"] == 1
            and freeze_summary["single_ring"] is True
            and freeze_summary["same_layer_xy_face_neighbors_only"] is True
            and freeze_summary["nonrecursive"] is True
            and freeze_summary["vertical_halo"] is False
            and freeze_summary["diagonal_halo"] is False,
        )
        gate(
            "R3R3R3R2_protocol_exact",
            freeze_protocol["per_CV_extension"]["single_ring"] is True
            and freeze_protocol["per_CV_extension"]["nonrecursive"] is True
            and freeze_protocol["per_CV_extension"]["vertical_neighbors"] is False
            and freeze_protocol["per_CV_extension"]["diagonal_neighbors"] is False
            and freeze_protocol["per_CV_extension"]["second_ring"] is False,
        )
        gate(
            "R3R3R3R2_handoff_exact",
            freeze_handoff["milestone"] == MILESTONE
            and freeze_handoff["authorized"] is True
            and freeze_handoff["execution"] is True,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact accepted event and Day365 parent split state.
        # ------------------------------------------------------------------------------------------
        stage = "state_authority_binding"
        f2d = drive / F2R3_REL
        evd = drive / R3R1R2_REL
        a2d = drive / A2E_REL
        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        gate("R3R1R2_output_present", evd.is_dir(), str(evd))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        base.verify_manifest(f2d, F2R3_MANIFEST)
        base.verify_manifest(evd, R3R1R2_MANIFEST)
        base.verify_manifest(a2d, A2E_MANIFEST)

        with np.load(f2d / F2R3_STATE, allow_pickle=False) as z:
            parent_cv_mass = np.asarray(z["parent_CV_component_mass_kg"], dtype=np.float64)
            parent_residual_grid = np.asarray(z["residual_grid_component_mass_kg"], dtype=np.float64)
            parent_mapped_grid = np.asarray(z["mapped_grid_component_mass_kg"], dtype=np.float64)
            parent_cell_pv = np.asarray(z["physical_cell_pore_volume_m3"], dtype=np.float64)
            sub_parent_mass = np.asarray(z["subsegment_parent_mass_kg"], dtype=np.float64)
            sub_flat = np.asarray(z["subsegment_flat_cell"], dtype=np.int64)
            sub_stream = np.asarray(z["subsegment_streamline"], dtype=np.int64)
            sub_cv = np.asarray(z["subsegment_control_volume"], dtype=np.int64)
            sub_pv = np.asarray(z["subsegment_pore_volume_m3"], dtype=np.float64)

        with np.load(evd / R3R1R2_STATE, allow_pickle=False) as z:
            event_cv_mass = np.asarray(z["partial_CV_component_mass_kg"], dtype=np.float64)
            event_cv_sat = np.asarray(z["partial_CV_saturation"], dtype=np.float64)
            elapsed = float(np.asarray(z["elapsed_days"]).reshape(()))
            remaining = float(np.asarray(z["remaining_days"]).reshape(()))
            substeps = int(np.asarray(z["accepted_substeps"]).reshape(()))

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
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
        gate(
            "Day365_split_grid_exact",
            base.max_abs(parent_mapped_grid + parent_residual_grid - parent_grid_mass) <= 1e-9,
            base.max_abs(parent_mapped_grid + parent_residual_grid - parent_grid_mass),
        )

        # ------------------------------------------------------------------------------------------
        # Reconstruct exact E0 pair ownership and raw event EOS secondary target.
        # ------------------------------------------------------------------------------------------
        stage = "E0_authority_reconstruction"
        r3event = load_module(root / R3_EVENT, "postv16_av4_r3r3r3r3_event")
        f4r3 = load_module(root / F4R3, "postv16_av4_r3r3r3r3_f4r3")
        a2e = load_module(root / A2E, "postv16_av4_r3r3r3r3_a2e")
        r2 = load_module(root / R2, "postv16_av4_r3r3r3r3_r2")
        e37 = load_module(root / E37A, "postv16_av4_r3r3r3r3_e37")
        sg2 = load_module(root / SG2, "postv16_av4_r3r3r3r3_sg2")
        sg3 = load_module(root / SG3, "postv16_av4_r3r3r3r3_sg3")
        sg4 = load_module(root / SG4, "postv16_av4_r3r3r3r3_sg4")
        sg5 = load_module(root / SG5, "postv16_av4_r3r3r3r3_sg5")
        sg6 = load_module(root / SG6, "postv16_av4_r3r3r3r3_sg6")
        sg7d = load_module(root / SG7D, "postv16_av4_r3r3r3r3_sg7d")
        r3r2r1 = load_module(root / R3R2R1, "postv16_av4_r3r3r3r3_r3r2r1")
        r1mod = load_module(root / R3R3R3R1, "postv16_av4_r3r3r3r3_r1")

        parent_operator = sg7d.build_subsegment_operator(
            parent_xyz,
            parent_tof / 86400.0,
            np.asarray(epoch["streamline_weight_m3_s"], dtype=np.float64) * 86400.0,
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
            and base.max_abs(sub_pv - geom_pv) <= 1e-12,
            {"subsegments": int(len(sub_flat)), "pv_Linf": base.max_abs(sub_pv - geom_pv)},
        )

        event_sub_sat = event_cv_sat.reshape(-1)[geom_cv_id]
        event_sub_sg = np.clip(event_sub_sat - BACKGROUND, 0.0, MAX_SG)
        event_sub_rho = np.asarray(
            r2.gas_density_from_state(event_sub_sat, geom_pseg, p_ref),
            dtype=np.float64,
        )
        raw_event_sub_mass = geom_pv * event_sub_rho * event_sub_sg

        e0_cv, e0_cell, parent_pair_mass, e0_key = base.aggregate_pairs(
            cv_id_f2, sub_flat, sub_parent_mass
        )
        q_cv, q_cell, raw_event_pair_mass, q_key = base.aggregate_pairs(
            geom_cv_id, geom_flat, raw_event_sub_mass
        )
        gate(
            "E0_parent_and_raw_event_pair_support_identical",
            np.array_equal(e0_key, q_key)
            and np.array_equal(e0_cv, q_cv)
            and np.array_equal(e0_cell, q_cell),
            len(e0_key),
        )
        gate("E0_pair_count_exact_269721", len(e0_key) == 269721, len(e0_key))

        # Physical capacity is unchanged from failed R3-R3-R3.
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
            np.isfinite(cell_capacity).all() and float(np.min(cell_capacity)) > 0.0,
            [float(np.min(cell_capacity)), float(np.max(cell_capacity))],
        )

        # ------------------------------------------------------------------------------------------
        # Execute the one frozen E1 candidate.
        # ------------------------------------------------------------------------------------------
        stage = "frozen_E1_assignment"
        assignment = execute_e1_assignment(
            e0_cv=e0_cv,
            e0_cell=e0_cell,
            parent_pair_mass=parent_pair_mass,
            raw_event_pair_mass=raw_event_pair_mass,
            parent_cv_mass=parent_cv_mass,
            event_cv_mass=event_cv_mass,
            residual_grid_mass=parent_residual_grid,
            cell_capacity=cell_capacity,
            r1mod=r1mod,
        )
        lp_executed = True
        mapback_executed = True

        event_grid_mass = np.asarray(assignment["event_grid_mass"], dtype=np.float64).reshape(GRID)
        event_mapped_grid = np.asarray(assignment["event_mapped_grid_mass"], dtype=np.float64).reshape(GRID)
        event_cv_reconstructed = np.asarray(
            assignment["event_CV_mass_reconstructed"], dtype=np.float64
        ).reshape(NSL, NCV)

        cv_tol = max(1e-6, 1e-10 * max(float(np.max(np.abs(event_cv_mass))), 1.0))
        grid_tol = max(1e-6, 1e-10 * max(float(np.max(np.abs(cell_capacity))), 1.0))

        sci_gate(
            "E1_event_CV_mass_equalities_exact",
            base.max_abs(event_cv_reconstructed - event_cv_mass) <= cv_tol,
            {"Linf_kg": base.max_abs(event_cv_reconstructed - event_cv_mass), "tol": cv_tol},
        )
        sci_gate(
            "E1_event_grid_nonnegative",
            float(np.min(event_grid_mass)) >= -grid_tol,
            float(np.min(event_grid_mass)),
        )
        sci_gate(
            "E1_event_grid_within_source_authentic_capacity",
            float(np.max(event_grid_mass - cell_capacity)) <= grid_tol,
            float(np.max(event_grid_mass - cell_capacity)),
        )
        sci_gate(
            "E1_residual_sidecar_unchanged",
            base.max_abs(event_grid_mass - event_mapped_grid - parent_residual_grid) <= 1e-8,
            base.max_abs(event_grid_mass - event_mapped_grid - parent_residual_grid),
        )
        global_resid = (
            base.fsum_array(event_grid_mass)
            - base.fsum_array(parent_residual_grid)
            - base.fsum_array(event_cv_mass)
        )
        sci_gate(
            "E1_global_component_mass_exact",
            abs(global_resid) <= max(1e-5, 1e-10 * max(base.fsum_array(event_grid_mass), 1.0)),
            global_resid,
        )
        gate(
            "E1_four_stages_success",
            assignment["stage1_meta"]["status"] == 0
            and assignment["stage2_meta"]["status"] == 0
            and assignment["stage3_meta"]["status"] == 0
            and assignment["stage4_meta"]["status"] == 0,
            {
                "stage1": assignment["stage1_meta"],
                "stage2": assignment["stage2_meta"],
                "stage3": assignment["stage3_meta"],
                "stage4": assignment["stage4_meta"],
            },
        )
        sci_gate(
            "E1_minimum_extension_mass_positive",
            assignment["stage1_minimum_extension_mass"] > 0.0,
            assignment["stage1_minimum_extension_mass"],
        )
        gate(
            "E1_actual_extension_mass_matches_stage1_optimum",
            abs(
                assignment["extension_mass_actual"]
                - assignment["stage1_minimum_extension_mass"]
            )
            <= max(
                1e-5,
                assignment["stage1_minimum_extension_mass"] * 1e-10,
            ),
            {
                "actual_kg": assignment["extension_mass_actual"],
                "optimum_kg": assignment["stage1_minimum_extension_mass"],
            },
        )

        # ------------------------------------------------------------------------------------------
        # Same-time mass inversion and exactly one flow refresh.
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

        event_sat_start = BACKGROUND + np.asarray(event_sg_start, dtype=np.float64)
        sci_gate(
            "event_parent_pressure_saturation_bounds",
            float(np.min(event_sat_start)) >= BACKGROUND - 1e-10
            and float(np.max(event_sat_start)) <= INJECTED + 1e-10,
            [float(np.min(event_sat_start)), float(np.max(event_sat_start))],
        )

        stage = "single_same_time_event_flow_refresh"
        permeability_md = np.loadtxt(
            root / PERM,
            skiprows=1,
            dtype=np.float64,
        ).reshape(GRID, order="C")

        try:
            event_flow = r3event.refresh_flow_epoch(
                label="event_refresh_E1",
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
        flow_refresh_executed = True

        # ------------------------------------------------------------------------------------------
        # Refreshed-geometry bounded reprojection.
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
            <= max(1e-5, 1e-10 * max(base.fsum_array(event_grid_mass), 1.0)),
            float(event_split["ledger_residual_kg"]),
        )
        reconstructed_refresh_grid = (
            np.asarray(event_split["mapped_grid_mass"], dtype=np.float64)
            + np.asarray(event_split["residual_grid_mass"], dtype=np.float64)
        )
        sci_gate(
            "event_reprojection_exact_full_grid_reconstruction",
            base.max_abs(reconstructed_refresh_grid - event_grid_mass) <= 1e-8,
            base.max_abs(reconstructed_refresh_grid - event_grid_mass),
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

        tof_change = base.relative_l2(event_flow["tof_s"], parent_tof)
        pressure_change = base.relative_l2(event_flow["pressure_psi"], parent_pressure)
        sci_gate(
            "single_refresh_changes_flow_epoch",
            tof_change > 1e-12 or pressure_change > 1e-12,
            {
                "TOF_relative_L2_change": tof_change,
                "pressure_relative_L2_change": pressure_change,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Publish refreshed event state. Stop before any physical-time continuation.
        # ------------------------------------------------------------------------------------------
        stage = "artifact_publication"
        e1_pair_mass = np.asarray(assignment["x_pair_mass"], dtype=np.float64)

        state_npz = base.deterministic_npz_bytes(
            {
                "event_day": np.asarray(EVENT_DAY),
                "physical_time_advanced_in_R3R3R3R3": np.asarray(False),
                "event_grid_component_mass_kg": event_grid_mass,
                "event_parent_pressure_saturation": event_sat_start,
                "E0_pair_cv_id": e0_cv,
                "E0_pair_flat_cell": e0_cell,
                "E0_parent_ownership_mass_kg": parent_pair_mass,
                "E1_pair_cv_id": assignment["e1_cv"],
                "E1_pair_flat_cell": assignment["e1_cell"],
                "E1_pair_is_E0": assignment["is_e0"],
                "E1_pair_event_mass_kg": e1_pair_mass,
                "E0_parent_continuity_target_kg": assignment["target0"],
                "E0_raw_event_EOS_target_kg": assignment["qtarget0"],
                "ownership_extended_event_mapped_grid_mass_kg": event_mapped_grid,
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

        e0_pairs = int(len(e0_cv))
        e1_pairs = int(len(assignment["e1_cv"]))
        global_new_h1 = int(len(assignment["globally_new_h1_cells"]))
        extension_fraction = (
            assignment["extension_mass_actual"] / base.fsum_array(event_cv_mass)
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "physical_time_advanced": False,
            "E0_pair_count": e0_pairs,
            "E1_pair_count": e1_pairs,
            "added_pair_count": e1_pairs - e0_pairs,
            "globally_new_H1_cell_count": global_new_h1,
            "E1_stage0_minimum_unserved_mass_kg":
                assignment["stage0_minimum_unserved_mass"],
            "minimum_extension_mass_kg":
                assignment["stage1_minimum_extension_mass"],
            "minimum_extension_mass_fraction":
                extension_fraction,
            "parent_ownership_L1_kg": assignment["stage2_parent_L1"],
            "raw_event_EOS_L1_kg": assignment["stage3_raw_L1"],
            "extension_CV_count": assignment["extension_CV_count"],
            "extension_streamline_count": assignment["extension_streamline_count"],
            "extension_cell_count": assignment["extension_cell_count"],
            "event_grid_mass_kg": base.fsum_array(event_grid_mass),
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
            "E0_pair_count": e0_pairs,
            "E1_pair_count": e1_pairs,
            "globally_new_H1_cell_count": global_new_h1,
            "added_pairs_per_CV": {
                "minimum": int(np.min(assignment["added_pairs_per_cv"])),
                "median": float(np.median(assignment["added_pairs_per_cv"])),
                "maximum": int(np.max(assignment["added_pairs_per_cv"])),
                "positive_CV_count": int(np.sum(assignment["added_pairs_per_cv"] > 0)),
            },
            "stage0_minimum_unserved_mass_kg":
                assignment["stage0_minimum_unserved_mass"],
            "stage1_minimum_extension_mass_kg":
                assignment["stage1_minimum_extension_mass"],
            "stage2_parent_ownership_L1_kg":
                assignment["stage2_parent_L1"],
            "stage3_raw_event_EOS_L1_kg":
                assignment["stage3_raw_L1"],
            "stage4_tiebreak_objective":
                assignment["stage4_tiebreak"],
            "extension_CV_count": assignment["extension_CV_count"],
            "extension_streamline_count": assignment["extension_streamline_count"],
            "extension_cell_count": assignment["extension_cell_count"],
            "event_CV_mass_Linf_error_kg":
                base.max_abs(event_cv_reconstructed - event_cv_mass),
            "global_event_mass_residual_kg": global_resid,
            "support_expansion_type":
                "single_nonrecursive_per_CV_same_layer_xy_face_neighbors",
            "H2_or_vertical_or_diagonal_expansion": False,
            "capacity_relaxed": False,
            "CV_mass_relaxed": False,
            "mass_clipped": False,
            "global_rescaling": False,
        }

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R4",
            "name":
                "Refreshed Event-Epoch Day413.78677770818403 to Day500 Controlled Continuation Execution",
            "authorized": True,
            "execution": True,
            "required_R3R3R3R3_status": STATUS_PASS,
            "parent_event_day": EVENT_DAY,
            "remaining_days": EVENT_REMAINING,
            "required_parent_state":
                "POSTV16_AV4_F4_R3_R3_R3_R3_Refreshed_Event_Recurrent_State.npz",
            "single_event_refresh_already_consumed": True,
            "second_event_refresh_authorized": False,
            "scope": [
                "resume exactly 86.21322229181597 days on refreshed event epoch",
                "use unchanged raw F4 internal operator",
                "use unchanged F4-R2 terminal producer pass-through",
                "a second interior invariant-domain conflict is SCIENTIFIC FAIL",
                "on Day500 success execute Day500 same-time refresh/reprojection certification",
            ],
            "not_authorized": [
                "second event refresh",
                "further occupancy-domain expansion",
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
            "R3R3_scientific_FAIL_preserved": True,
            "R3R3R3R2_freeze_bound": True,
            "E1_execution_performed": True,
            "LP_executed": True,
            "support_domain_changed_exactly_as_frozen": True,
            "H2_or_vertical_or_diagonal_expansion": False,
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
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_Summary.json":
                base.json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_E1_Assignment_Audit.json":
                base.json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_Refreshed_Event_Recurrent_State.npz":
                state_npz,
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3R3R4_Handoff_Contract.json":
                base.json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R3_Decision_Contract.json":
                base.json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_Final_Gate_Matrix.csv":
                base.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        base.immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R3_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": base.sha256_file(p), "bytes": p.stat().st_size}
                )
        base.immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_Artifact_Manifest.csv":
                    base.csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R3: PER-CV SINGLE-RING HORIZONTAL FACE "
            "OCCUPANCY EXTENSION + FLOW REFRESH / REPROJECTION PASS"
        )
        print("=" * 214)
        print("Event day                                :", EVENT_DAY)
        print("E0 / E1 pair counts                     :", e0_pairs, "/", e1_pairs)
        print("Globally new H1 cells                   :", global_new_h1)
        print("E1 minimum unserved mass kg             :", assignment["stage0_minimum_unserved_mass"])
        print("Minimum extension mass kg               :", assignment["stage1_minimum_extension_mass"])
        print("Minimum extension mass fraction         :", extension_fraction)
        print("CVs / streamlines / cells using extension:",
              assignment["extension_CV_count"], "/",
              assignment["extension_streamline_count"], "/",
              assignment["extension_cell_count"])
        print("Event CV mass Linf error kg             :", base.max_abs(event_cv_reconstructed - event_cv_mass))
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
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "R3R3_scientific_FAIL_preserved": True,
            "R3R3R3R2_freeze_preserved": True,
            "LP_executed": lp_executed,
            "E1_mapback_executed": mapback_executed,
            "flow_refresh_executed": flow_refresh_executed,
            "event_reprojection_executed": reprojection_executed,
            "H2_or_vertical_or_diagonal_expansion": False,
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
        data = base.json_bytes(report) if base is not None else (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
        p = failed / "POSTV16_AV4_F4_R3_R3_R3_R3_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = failed / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_Scientific_Fail_Report_"
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
        print("NO H2, VERTICAL/DIAGONAL EXTENSION, ALTERNATE REPAIR, SECOND REFRESH, OR AUTO-RERUN.")
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
            "R3R3R3R2_freeze_preserved": True,
            "LP_executed": lp_executed,
            "E1_mapback_executed": mapback_executed,
            "flow_refresh_executed": flow_refresh_executed,
            "event_reprojection_executed": reprojection_executed,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = base.json_bytes(report) if base is not None else (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_Blocked_Report_"
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
        print("R3-R3-R3 scientific FAIL and R3-R3-R3-R2 freeze remain immutable.")
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
