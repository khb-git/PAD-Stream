#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import io
import json
import math
import os
try:
    import resource
except ImportError:  # Windows: resource is Unix-only.
    resource = None
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O2"

STATUS_PASS = (
    "AV4F4R3R3R3R3R3O2_PERSISTENT_NATIVE_HIGHS_EXACT_ZERO_GRAPH_"
    "PREPROCESSING_COMPONENT_DECOMPOSITION_BASIS_REUSE_H2_ASSIGNMENT_PASS_"
    "EXACT_CARTESIAN_EVENT_MAPBACK_CERTIFIED_NO_FLOW_REFRESH_NO_TIME_ADVANCE"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3O2_OPTIMIZED_H2_ASSIGNMENT_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_O1_COMMIT = "948ec24cded27690369ae39ae524ca18a5ef7695"

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
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

O1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_"
    "H2_Assignment_Computational_Optimization_Protocol_Freeze.py"
)
O1_BLOB = "558790608560a8ab0c809d09085158aa894dd189"

R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_"
    "H2_Horizontal_Graph_Radius_2_Occupancy_Extension_Execution.py"
)
R3_BLOB = "14035aa5ec2e5338b8ba6d8b099e1423bd426beb"

R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R2_"
    "H2_Horizontal_Graph_Radius_2_Support_Selection_Freeze.py"
)
R2_BLOB = "0ae1e22f25ffd807b98cca9ead74b4b8cf61f672"

R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R1_"
    "Prospective_Support_Class_Feasibility_Audit.py"
)
R1_BLOB = "a342684ee48567ad11ee65cce2afe8c85eb9b432"

SOURCE_BLOBS = {
    O1: O1_BLOB,
    R3: R3_BLOB,
    R2: R2_BLOB,
    R1: R1_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Exact Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

O1_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_H2_Assignment_Computational_Optimization_Freeze"
)
O1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Summary.json"
O1_PROTOCOL = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Frozen_Optimization_Protocol.json"
O1_HANDOFF = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_O2_Handoff_Contract.json"
O1_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Decision_Contract.json"
O1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Artifact_Manifest.csv"
O1_STATUS = (
    "AV4F4R3R3R3R3R3O1_FROZEN_H2_PHYSICS_AND_LEXICOGRAPHIC_SEMANTICS_"
    "PERSISTENT_NATIVE_HIGHS_EXACT_GRAPH_REDUCTION_COMPONENT_DECOMPOSITION_"
    "WARM_START_TELEMETRY_OPTIMIZATION_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

R1_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Prospective_Support_Class_Feasibility_Audit"
)
R1_MATRIX = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Candidate_Matrix.csv"
R1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Artifact_Manifest.csv"

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Persistent_Native_HiGHS_H2_Assignment_Execution"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_BLOCKED"


class GateError(RuntimeError):
    pass


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


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def current_rss_mb() -> float | None:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return None


def peak_rss_mb() -> float | None:
    if resource is None:
        return None
    try:
        x = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # Linux reports KiB; macOS reports bytes. Colab/Linux is canonical.
        return x / 1024.0 if sys.platform != "darwin" else x / (1024.0 * 1024.0)
    except Exception:
        return None


def parse_version_tuple(s: str) -> tuple[int, ...]:
    out = []
    for piece in str(s).split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if not digits:
            break
        out.append(int(digits))
    return tuple(out)


def import_highspy():
    try:
        import highspy
    except Exception as exc:
        raise GateError(
            "highspy_import_failed: install highspy>=1.13 before formal execution: "
            + repr(exc)
        ) from exc

    h = highspy.Highs()
    version = h.version()
    if parse_version_tuple(version) < (1, 13, 0):
        raise GateError(f"highspy_version_too_old:{version}:require>=1.13.0")

    required = [
        "passModel",
        "run",
        "getSolution",
        "getInfo",
        "getBasis",
        "setBasis",
        "clearSolver",
        "changeColsCost",
        "changeColsBounds",
        "changeRowsBounds",
        "changeRowBounds",
        "getModelStatus",
        "modelStatusToString",
        "setOptionValue",
    ]
    missing = [name for name in required if not hasattr(h, name)]
    if missing:
        raise GateError("highspy_required_API_missing:" + ",".join(missing))
    return highspy, version


def highspy_api_test() -> None:
    highspy, version = import_highspy()
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("solver", "simplex")

    inf = highspy.kHighsInf
    lp = highspy.HighsLp()
    lp.num_col_ = 2
    lp.num_row_ = 1
    lp.sense_ = highspy.ObjSense.kMinimize
    lp.col_cost_ = np.array([1.0, 0.0], dtype=np.float64)
    lp.col_lower_ = np.zeros(2, dtype=np.float64)
    lp.col_upper_ = np.full(2, inf, dtype=np.float64)
    lp.row_lower_ = np.array([1.0], dtype=np.float64)
    lp.row_upper_ = np.array([1.0], dtype=np.float64)
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.array([0, 1, 2], dtype=np.int64)
    lp.a_matrix_.index_ = np.array([0, 0], dtype=np.int64)
    lp.a_matrix_.value_ = np.array([1.0, 1.0], dtype=np.float64)

    if h.passModel(lp) == highspy.HighsStatus.kError:
        raise GateError("highspy_api_test_passModel_error")
    if h.run() == highspy.HighsStatus.kError:
        raise GateError("highspy_api_test_run1_error")
    if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise GateError("highspy_api_test_run1_not_optimal")

    basis = h.getBasis()
    idx = np.array([0, 1], dtype=np.int32)
    costs = np.array([0.0, 1.0], dtype=np.float64)
    if h.changeColsCost(2, idx, costs) == highspy.HighsStatus.kError:
        raise GateError("highspy_api_test_changeColsCost_error")

    ridx = np.array([0], dtype=np.int32)
    one = np.array([1.0], dtype=np.float64)
    if h.changeRowsBounds(1, ridx, one, one) == highspy.HighsStatus.kError:
        raise GateError("highspy_api_test_changeRowsBounds_error")

    if h.setBasis(basis) == highspy.HighsStatus.kError:
        raise GateError("highspy_api_test_setBasis_error")
    if h.run() == highspy.HighsStatus.kError:
        raise GateError("highspy_api_test_run2_error")
    if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise GateError("highspy_api_test_run2_not_optimal")

    sol = np.asarray(list(h.getSolution().col_value), dtype=np.float64)
    if not (abs(float(np.sum(sol)) - 1.0) < 1e-9 and sol[0] > 0.999999):
        raise GateError("highspy_api_test_solution_wrong:" + repr(sol.tolist()))

    print(
        f"POSTV16-AV4-F4-R3-R3-R3-R3-R3-O2 native HiGHS API self-test: "
        f"PASS (HiGHS {version})"
    )


def self_test() -> None:
    # Exact component decomposition toy graph.
    cv = np.array([0, 0, 1, 1], dtype=np.int64)
    cell = np.array([0, 1, 2, 3], dtype=np.int64)
    demand = np.array([1.0, 1.0], dtype=np.float64)
    available = np.ones(4, dtype=np.float64)

    prep = preprocess_active_graph(
        e2_cv=cv,
        e2_cell=cell,
        demand=demand,
        available_raw=available,
    )
    assert prep["component_count"] == 2
    assert prep["active_edge_count"] == 4
    assert prep["exact_zero_demand_CV_count_removed"] == 0

    # Exact-zero demand pruning.
    demand2 = np.array([1.0, 0.0], dtype=np.float64)
    prep2 = preprocess_active_graph(
        e2_cv=cv,
        e2_cell=cell,
        demand=demand2,
        available_raw=available,
    )
    assert prep2["exact_zero_demand_CV_count_removed"] == 1
    assert prep2["active_edge_count"] == 2

    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O2 persistent-native-HiGHS "
        "assignment self-test: PASS"
    )


def preprocess_active_graph(
    *,
    e2_cv: np.ndarray,
    e2_cell: np.ndarray,
    demand: np.ndarray,
    available_raw: np.ndarray,
) -> dict[str, Any]:
    t0 = time.perf_counter()

    e2_cv = np.asarray(e2_cv, dtype=np.int64).reshape(-1)
    e2_cell = np.asarray(e2_cell, dtype=np.int64).reshape(-1)
    demand = np.asarray(demand, dtype=np.float64).reshape(-1)
    available_raw = np.asarray(available_raw, dtype=np.float64).reshape(-1)

    zero_demand = demand == 0.0
    zero_capacity = available_raw == 0.0

    active_edge_mask = (~zero_demand[e2_cv]) & (~zero_capacity[e2_cell])
    active_edge_idx = np.flatnonzero(active_edge_mask).astype(np.int64)
    active_cv_global = np.unique(e2_cv[active_edge_idx])
    active_cell_global = np.unique(e2_cell[active_edge_idx])

    positive_demand_cv = np.flatnonzero(demand != 0.0)
    missing_positive = np.setdiff1d(
        positive_demand_cv, active_cv_global, assume_unique=True
    )
    if missing_positive.size:
        raise GateError(
            "positive_demand_CV_has_no_active_E2_edge:"
            + repr(missing_positive[:20].tolist())
        )

    cv_local = np.searchsorted(active_cv_global, e2_cv[active_edge_idx]).astype(np.int64)
    cell_local = np.searchsorted(active_cell_global, e2_cell[active_edge_idx]).astype(np.int64)

    ncv = len(active_cv_global)
    ncell = len(active_cell_global)
    nnode = ncv + ncell

    rows = np.concatenate([cv_local, ncv + cell_local])
    cols = np.concatenate([ncv + cell_local, cv_local])
    data = np.ones(len(rows), dtype=np.int8)
    graph = coo_matrix((data, (rows, cols)), shape=(nnode, nnode)).tocsr()
    ncomp, labels = connected_components(
        graph, directed=False, return_labels=True
    )

    edge_comp = labels[cv_local]
    if not np.array_equal(edge_comp, labels[ncv + cell_local]):
        raise GateError("component_label_inconsistency")

    # Deterministic component ordering follows scipy's scan of sorted active nodes.
    comp_edge_counts = np.bincount(edge_comp, minlength=ncomp).astype(np.int64)
    comp_cv_counts = np.bincount(labels[:ncv], minlength=ncomp).astype(np.int64)
    comp_cell_counts = np.bincount(labels[ncv:], minlength=ncomp).astype(np.int64)

    order = np.argsort(edge_comp, kind="stable")
    sorted_edge_idx = active_edge_idx[order]
    sorted_comp = edge_comp[order]
    comp_starts = np.searchsorted(
        sorted_comp, np.arange(ncomp + 1), side="left"
    ).astype(np.int64)

    elapsed = time.perf_counter() - t0
    largest = int(np.argmax(comp_edge_counts)) if ncomp else -1

    return {
        "active_edge_mask": active_edge_mask,
        "active_edge_idx": active_edge_idx,
        "active_cv_global": active_cv_global,
        "active_cell_global": active_cell_global,
        "component_labels": labels,
        "edge_component": edge_comp,
        "component_count": int(ncomp),
        "component_edge_counts": comp_edge_counts,
        "component_cv_counts": comp_cv_counts,
        "component_cell_counts": comp_cell_counts,
        "sorted_edge_idx": sorted_edge_idx,
        "component_starts": comp_starts,
        "active_edge_count": int(active_edge_idx.size),
        "active_CV_count": int(active_cv_global.size),
        "active_cell_count": int(active_cell_global.size),
        "exact_zero_demand_CV_count_removed": int(np.sum(zero_demand)),
        "exact_zero_capacity_cell_count_removed": int(np.sum(zero_capacity)),
        "largest_component_id": largest,
        "largest_component_edge_count":
            int(comp_edge_counts[largest]) if largest >= 0 else 0,
        "largest_component_CV_count":
            int(comp_cv_counts[largest]) if largest >= 0 else 0,
        "largest_component_cell_count":
            int(comp_cell_counts[largest]) if largest >= 0 else 0,
        "preprocessing_wall_time_s": float(elapsed),
        "rss_mb_after_preprocessing": current_rss_mb(),
    }


def make_component(
    *,
    component_id: int,
    edge_idx: np.ndarray,
    support: dict[str, np.ndarray],
    demand: np.ndarray,
    available_safe: np.ndarray,
    target_by_edge: np.ndarray,
    qtarget_by_edge: np.ndarray,
) -> dict[str, Any]:
    edge_idx = np.asarray(edge_idx, dtype=np.int64)
    cv_global = support["e2_cv"][edge_idx]
    cell_global = support["e2_cell"][edge_idx]

    cv_ids, cv_inv = np.unique(cv_global, return_inverse=True)
    cell_ids, cell_inv = np.unique(cell_global, return_inverse=True)
    is_e0 = support["is_e0"][edge_idx]
    e0_x_local = np.flatnonzero(is_e0).astype(np.int64)
    is_shell = support["is_h2_shell"][edge_idx]
    is_extension = support["is_any_extension"][edge_idx]

    target = target_by_edge[edge_idx[e0_x_local]]
    qtarget = qtarget_by_edge[edge_idx[e0_x_local]]
    rank = (edge_idx.astype(np.float64) + 1.0) / float(EXPECTED_E2_PAIRS)

    return {
        "component_id": int(component_id),
        "edge_idx": edge_idx,
        "cv_global": cv_global,
        "cell_global": cell_global,
        "cv_ids": cv_ids,
        "cell_ids": cell_ids,
        "cv_inv": cv_inv.astype(np.int64),
        "cell_inv": cell_inv.astype(np.int64),
        "demand": demand[cv_ids].astype(np.float64),
        "available": available_safe[cell_ids].astype(np.float64),
        "is_e0": is_e0,
        "e0_x_local": e0_x_local,
        "is_shell": is_shell,
        "is_extension": is_extension,
        "target": target.astype(np.float64),
        "qtarget": qtarget.astype(np.float64),
        "global_rank": rank.astype(np.float64),
    }


def build_component_model(comp: dict[str, Any], highspy) -> dict[str, Any]:
    n = len(comp["edge_idx"])
    m = len(comp["e0_x_local"])
    ncv = len(comp["cv_ids"])
    ncell = len(comp["cell_ids"])

    x0 = 0
    up0 = n
    uq0 = n + m
    ncol = n + 2 * m

    r_cv0 = 0
    r_cell0 = r_cv0 + ncv
    r_pp0 = r_cell0 + ncell
    r_pm0 = r_pp0 + m
    r_qp0 = r_pm0 + m
    r_qm0 = r_qp0 + m
    r_shell = r_qm0 + m
    r_extension = r_shell + 1
    r_parent = r_extension + 1
    r_raw = r_parent + 1
    nrow = r_raw + 1

    xcols = np.arange(n, dtype=np.int64)
    e0_local = comp["e0_x_local"]
    e0_ord = np.arange(m, dtype=np.int64)
    upcols = up0 + e0_ord
    uqcols = uq0 + e0_ord

    rows_list = [
        r_cv0 + comp["cv_inv"],
        r_cell0 + comp["cell_inv"],
        r_pp0 + e0_ord,
        r_pm0 + e0_ord,
        r_qp0 + e0_ord,
        r_qm0 + e0_ord,
        r_pp0 + e0_ord,
        r_pm0 + e0_ord,
        r_qp0 + e0_ord,
        r_qm0 + e0_ord,
        np.full(int(np.sum(comp["is_shell"])), r_shell, dtype=np.int64),
        np.full(int(np.sum(comp["is_extension"])), r_extension, dtype=np.int64),
        np.full(m, r_parent, dtype=np.int64),
        np.full(m, r_raw, dtype=np.int64),
    ]
    cols_list = [
        xcols,
        xcols,
        e0_local,
        e0_local,
        e0_local,
        e0_local,
        upcols,
        upcols,
        uqcols,
        uqcols,
        xcols[comp["is_shell"]],
        xcols[comp["is_extension"]],
        upcols,
        uqcols,
    ]
    vals_list = [
        np.ones(n),
        np.ones(n),
        np.ones(m),
        -np.ones(m),
        np.ones(m),
        -np.ones(m),
        -np.ones(m),
        -np.ones(m),
        -np.ones(m),
        -np.ones(m),
        np.ones(int(np.sum(comp["is_shell"]))),
        np.ones(int(np.sum(comp["is_extension"]))),
        np.ones(m),
        np.ones(m),
    ]

    A = coo_matrix(
        (
            np.concatenate(vals_list).astype(np.float64),
            (
                np.concatenate(rows_list).astype(np.int64),
                np.concatenate(cols_list).astype(np.int64),
            ),
        ),
        shape=(nrow, ncol),
    ).tocsc()

    inf = highspy.kHighsInf
    col_cost = np.zeros(ncol, dtype=np.float64)
    col_cost[:n] = comp["is_shell"].astype(np.float64)
    col_lower = np.zeros(ncol, dtype=np.float64)
    col_upper = np.full(ncol, inf, dtype=np.float64)
    # Auxiliary variables are prebuilt but fixed at zero until their stage.
    if m:
        col_upper[up0 : up0 + m] = 0.0
        col_upper[uq0 : uq0 + m] = 0.0

    row_lower = np.full(nrow, -inf, dtype=np.float64)
    row_upper = np.full(nrow, inf, dtype=np.float64)

    row_lower[r_cv0 : r_cv0 + ncv] = comp["demand"]
    row_upper[r_cv0 : r_cv0 + ncv] = comp["demand"]
    row_upper[r_cell0 : r_cell0 + ncell] = comp["available"]

    lp = highspy.HighsLp()
    lp.num_col_ = int(ncol)
    lp.num_row_ = int(nrow)
    lp.sense_ = highspy.ObjSense.kMinimize
    lp.col_cost_ = col_cost
    lp.col_lower_ = col_lower
    lp.col_upper_ = col_upper
    lp.row_lower_ = row_lower
    lp.row_upper_ = row_upper
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.asarray(A.indptr, dtype=np.int64)
    lp.a_matrix_.index_ = np.asarray(A.indices, dtype=np.int64)
    lp.a_matrix_.value_ = np.asarray(A.data, dtype=np.float64)

    return {
        "lp": lp,
        "n": n,
        "m": m,
        "ncv": ncv,
        "ncell": ncell,
        "ncol": ncol,
        "nrow": nrow,
        "nnz": int(A.nnz),
        "up0": up0,
        "uq0": uq0,
        "r_pp0": r_pp0,
        "r_pm0": r_pm0,
        "r_qp0": r_qp0,
        "r_qm0": r_qm0,
        "r_shell": r_shell,
        "r_extension": r_extension,
        "r_parent": r_parent,
        "r_raw": r_raw,
    }


def set_full_costs(h, highspy, costs: np.ndarray) -> None:
    costs = np.asarray(costs, dtype=np.float64)
    idx = np.arange(len(costs), dtype=np.int32)
    status = h.changeColsCost(len(costs), idx, costs)
    if status == highspy.HighsStatus.kError:
        raise GateError("highspy_changeColsCost_error")


def set_col_bounds(h, highspy, idx: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> None:
    idx = np.asarray(idx, dtype=np.int32)
    lower = np.asarray(lower, dtype=np.float64)
    upper = np.asarray(upper, dtype=np.float64)
    if len(idx) == 0:
        return
    status = h.changeColsBounds(len(idx), idx, lower, upper)
    if status == highspy.HighsStatus.kError:
        raise GateError("highspy_changeColsBounds_error")


def set_row_bounds(h, highspy, idx: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> None:
    idx = np.asarray(idx, dtype=np.int32)
    lower = np.asarray(lower, dtype=np.float64)
    upper = np.asarray(upper, dtype=np.float64)
    if len(idx) == 0:
        return
    status = h.changeRowsBounds(len(idx), idx, lower, upper)
    if status == highspy.HighsStatus.kError:
        raise GateError("highspy_changeRowsBounds_error")


def stage_validation(comp: dict[str, Any], x: np.ndarray) -> dict[str, float]:
    cv_sum = np.bincount(
        comp["cv_inv"], weights=x, minlength=len(comp["cv_ids"])
    ).astype(np.float64)
    cell_sum = np.bincount(
        comp["cell_inv"], weights=x, minlength=len(comp["cell_ids"])
    ).astype(np.float64)
    return {
        "CV_equality_Linf_kg":
            float(np.max(np.abs(cv_sum - comp["demand"]))) if len(cv_sum) else 0.0,
        "max_capacity_excess_kg":
            float(np.max(cell_sum - comp["available"])) if len(cell_sum) else 0.0,
        "minimum_x_kg": float(np.min(x)) if len(x) else 0.0,
    }


def solve_component(
    *,
    comp: dict[str, Any],
    highspy,
    model_data: dict[str, Any],
    verbose_solver: bool,
) -> dict[str, Any]:
    cid = comp["component_id"]
    n = model_data["n"]
    m = model_data["m"]
    ncol = model_data["ncol"]
    inf = highspy.kHighsInf

    h = highspy.Highs()
    h.setOptionValue("solver", "simplex")
    h.setOptionValue("presolve", "on")
    h.setOptionValue("output_flag", bool(verbose_solver))
    if h.passModel(model_data["lp"]) == highspy.HighsStatus.kError:
        raise GateError(f"component_{cid}_passModel_error")

    all_col_idx = np.arange(ncol, dtype=np.int32)
    up_idx = np.arange(model_data["up0"], model_data["up0"] + m, dtype=np.int32)
    uq_idx = np.arange(model_data["uq0"], model_data["uq0"] + m, dtype=np.int32)

    telemetry = []
    solutions = {}
    objectives = {}
    previous_basis = None

    def solve_stage(stage_no: int, name: str, cost: np.ndarray, warm: bool) -> tuple[np.ndarray, Any]:
        nonlocal previous_basis
        set_full_costs(h, highspy, cost)

        warm_requested = bool(warm and previous_basis is not None)
        warm_applied = False
        warm_status = "not_requested"
        if warm_requested:
            status = h.setBasis(previous_basis)
            if status == highspy.HighsStatus.kError:
                h.clearSolver()
                warm_status = "basis_rejected_cold_resolve"
            else:
                warm_applied = True
                warm_status = str(status)

        print()
        print("-" * 160)
        print(f"[START] COMPONENT {cid} — STAGE {stage_no}: {name}")
        print("-" * 160)
        print("edges / E0 edges :", n, "/", m)
        print("variables / rows :", model_data["ncol"], "/", model_data["nrow"])
        print("matrix nonzeros  :", model_data["nnz"])
        print("warm start       :", warm_applied, f"({warm_status})")
        print("RSS MB           :", current_rss_mb())
        sys.stdout.flush()

        t0 = time.perf_counter()
        run_status = h.run()
        wall = time.perf_counter() - t0
        model_status = h.getModelStatus()
        model_status_text = h.modelStatusToString(model_status)

        if run_status == highspy.HighsStatus.kError:
            raise GateError(f"component_{cid}_stage_{stage_no}_highs_run_error")
        if model_status != highspy.HighsModelStatus.kOptimal:
            # R1 formally proved E2 feasible. Any infeasible/non-optimal status in O2
            # is therefore a computational/authority contradiction, not a new science result.
            raise GateError(
                f"component_{cid}_stage_{stage_no}_not_optimal:"
                f"{model_status_text}"
            )

        sol = np.asarray(list(h.getSolution().col_value), dtype=np.float64)
        x = sol[:n]
        info = h.getInfo()
        val = stage_validation(comp, x)
        obj = float(h.getObjectiveValue())
        previous_basis = h.getBasis()

        rec = {
            "component_id": int(cid),
            "stage": int(stage_no),
            "stage_name": name,
            "warm_start_requested": warm_requested,
            "warm_start_applied": warm_applied,
            "warm_start_status": warm_status,
            "model_status": model_status_text,
            "wall_time_s": float(wall),
            "objective": obj,
            "simplex_iterations": int(getattr(info, "simplex_iteration_count", -1)),
            "ipm_iterations": int(getattr(info, "ipm_iteration_count", -1)),
            "variables": int(model_data["ncol"]),
            "rows": int(model_data["nrow"]),
            "matrix_nonzeros": int(model_data["nnz"]),
            "CV_equality_Linf_kg": val["CV_equality_Linf_kg"],
            "max_capacity_excess_kg": val["max_capacity_excess_kg"],
            "minimum_x_kg": val["minimum_x_kg"],
            "rss_mb": current_rss_mb(),
            "peak_rss_mb": peak_rss_mb(),
        }
        telemetry.append(rec)

        print(
            f"[PASS] COMPONENT {cid} — STAGE {stage_no}: {name} | "
            f"wall={wall:.6f}s | objective={obj:.12g} | "
            f"simplex_iter={rec['simplex_iterations']} | "
            f"CV_Linf={val['CV_equality_Linf_kg']:.6e} | "
            f"cap_excess={val['max_capacity_excess_kg']:.6e}"
        )
        sys.stdout.flush()
        return sol, previous_basis

    # Stage 1: minimum H2 shell mass. Its feasible optimum is the fresh O2 E2
    # feasibility certificate, replacing the redundant standalone Stage-0 LP.
    cost = np.zeros(ncol, dtype=np.float64)
    cost[:n] = comp["is_shell"].astype(np.float64)
    sol1, _ = solve_stage(1, "MINIMUM_H2_SECOND_SHELL_MASS", cost, warm=False)
    x1 = sol1[:n]
    obj1 = float(np.sum(x1[comp["is_shell"]]))
    objectives["stage1_shell_kg"] = obj1
    solutions["stage1_x"] = x1

    # Freeze Stage 1 in this exact disconnected component.
    tol1 = max(1e-7, 1e-12 * max(abs(obj1), 1.0))
    h.changeRowBounds(model_data["r_shell"], -inf, obj1 + tol1)

    # Stage 2: minimum total extension E2\E0.
    cost = np.zeros(ncol, dtype=np.float64)
    cost[:n] = comp["is_extension"].astype(np.float64)
    sol2, _ = solve_stage(2, "MINIMUM_TOTAL_EXTENSION_MASS", cost, warm=True)
    x2 = sol2[:n]
    obj2 = float(np.sum(x2[comp["is_extension"]]))
    objectives["stage2_extension_kg"] = obj2
    solutions["stage2_x"] = x2

    tol2 = max(1e-7, 1e-12 * max(abs(obj2), 1.0))
    h.changeRowBounds(model_data["r_extension"], -inf, obj2 + tol2)

    # Stage 3: activate parent absolute-value rows and u_parent.
    if m:
        set_col_bounds(
            h, highspy, up_idx,
            np.zeros(m, dtype=np.float64),
            np.full(m, inf, dtype=np.float64),
        )
        p_rows = np.concatenate([
            np.arange(model_data["r_pp0"], model_data["r_pp0"] + m, dtype=np.int32),
            np.arange(model_data["r_pm0"], model_data["r_pm0"] + m, dtype=np.int32),
        ])
        p_lo = np.full(2 * m, -inf, dtype=np.float64)
        p_up = np.concatenate([comp["target"], -comp["target"]])
        set_row_bounds(h, highspy, p_rows, p_lo, p_up)

    cost = np.zeros(ncol, dtype=np.float64)
    if m:
        cost[model_data["up0"] : model_data["up0"] + m] = 1.0
    sol3, _ = solve_stage(3, "MINIMUM_PARENT_OWNERSHIP_L1", cost, warm=True)
    x3 = sol3[:n]
    up3 = sol3[model_data["up0"] : model_data["up0"] + m]
    obj3 = float(np.sum(up3))
    objectives["stage3_parent_L1_kg"] = obj3
    solutions["stage3_x"] = x3

    tol3 = max(1e-7, 1e-12 * max(abs(obj3), 1.0))
    h.changeRowBounds(model_data["r_parent"], -inf, obj3 + tol3)

    # Stage 4: activate raw-EOS absolute-value rows and u_raw.
    if m:
        set_col_bounds(
            h, highspy, uq_idx,
            np.zeros(m, dtype=np.float64),
            np.full(m, inf, dtype=np.float64),
        )
        q_rows = np.concatenate([
            np.arange(model_data["r_qp0"], model_data["r_qp0"] + m, dtype=np.int32),
            np.arange(model_data["r_qm0"], model_data["r_qm0"] + m, dtype=np.int32),
        ])
        q_lo = np.full(2 * m, -inf, dtype=np.float64)
        q_up = np.concatenate([comp["qtarget"], -comp["qtarget"]])
        set_row_bounds(h, highspy, q_rows, q_lo, q_up)

    cost = np.zeros(ncol, dtype=np.float64)
    if m:
        cost[model_data["uq0"] : model_data["uq0"] + m] = 1.0
    sol4, _ = solve_stage(4, "MINIMUM_RAW_EVENT_EOS_L1", cost, warm=True)
    x4 = sol4[:n]
    uq4 = sol4[model_data["uq0"] : model_data["uq0"] + m]
    obj4 = float(np.sum(uq4))
    objectives["stage4_raw_L1_kg"] = obj4
    solutions["stage4_x"] = x4

    tol4 = max(1e-7, 1e-12 * max(abs(obj4), 1.0))
    h.changeRowBounds(model_data["r_raw"], -inf, obj4 + tol4)

    # Stage 5: identical global E2 pair-rank coefficients, evaluated within
    # each exact disconnected component.
    cost = np.zeros(ncol, dtype=np.float64)
    cost[:n] = comp["global_rank"]
    sol5, _ = solve_stage(5, "DETERMINISTIC_GLOBAL_PAIR_RANK_TIEBREAK", cost, warm=True)
    x5 = sol5[:n].copy()
    obj5 = float(np.dot(comp["global_rank"], x5))
    objectives["stage5_tiebreak"] = obj5

    # Release HiGHS memory after final component solution is copied.
    try:
        h.releaseMemory()
    except Exception:
        pass

    return {
        "component_id": int(cid),
        "edge_idx": comp["edge_idx"],
        "final_x": x5,
        "objectives": objectives,
        "telemetry": telemetry,
        "model": {
            "edges": int(n),
            "E0_edges": int(m),
            "CVs": int(model_data["ncv"]),
            "cells": int(model_data["ncell"]),
            "variables": int(model_data["ncol"]),
            "rows": int(model_data["nrow"]),
            "nonzeros": int(model_data["nnz"]),
        },
    }


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    # Reuse exact deterministic helper semantics from historical base when available
    # in formal execution. This local fallback is only for defensive use.
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return buf.getvalue()


def main(project_root: Path, drive_root: Path, verbose_solver: bool = True) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
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

    print("=" * 214)
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O2 — PERSISTENT NATIVE-HiGHS "
        "H2 ASSIGNMENT EXECUTION"
    )
    print("=" * 214)
    print("OPTIMIZED ASSIGNMENT ONLY. EXACT O1 SEMANTICS.")
    print("NO STANDALONE STAGE-0 LP. NO FLOW REFRESH. NO POLLOCK/TOF REFRESH.")
    print("NO PHYSICAL-TIME ADVANCE. NO RADIUS-3. NO VERTICAL OR H2+V1 FALLBACK.")
    print("NO CAPACITY/CV-MASS RELAXATION. NO TOLERANCE-BASED GRAPH PRUNING.")
    print()

    try:
        highspy, highspy_version = import_highspy()

        # ------------------------------------------------------------------------------------------
        # Repository + O1 authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_O1_commit", parent == PARENT_O1_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        o1d = drive / O1_REL
        gate("O1_output_present", o1d.is_dir(), str(o1d))
        o1manifest = verify_manifest(o1d, O1_MANIFEST)
        gate("O1_manifest_exact_5", len(o1manifest) == 5, len(o1manifest))
        o1summary = load_json(o1d / O1_SUMMARY)
        o1protocol = load_json(o1d / O1_PROTOCOL)
        o1handoff = load_json(o1d / O1_HANDOFF)
        o1decision = load_json(o1d / O1_DECISION)

        gate("O1_status_exact", o1summary["status"] == O1_STATUS, o1summary["status"])
        gate(
            "O1_solver_semantics_exact",
            o1summary["native_highspy_persistent_model"] is True
            and o1summary["standalone_stage0_LP_in_O2"] is False
            and o1summary["exact_zero_pruning_only"] is True
            and o1summary["exact_component_decomposition_allowed"] is True
            and o1summary["basis_reuse_authorized"] is True
            and o1summary["stage_level_telemetry_required"] is True,
        )
        gate(
            "O1_O2_handoff_exact",
            o1handoff["milestone"] == MILESTONE
            and o1handoff["authorized"] is True
            and o1handoff["execution"] is True
            and o1decision["O2_authorized"] is True
            and o1decision["O3_authorized"] is False,
        )
        gate(
            "O1_scientific_problem_unchanged",
            o1decision["scientific_problem_changed"] is False
            and o1decision["lexicographic_objectives_changed"] is False,
        )
        gate(
            "highspy_API_and_version_supported",
            parse_version_tuple(highspy_version) >= (1, 13, 0),
            highspy_version,
        )

        # ------------------------------------------------------------------------------------------
        # Load exact historical helper stack from immutable R3/H1/base.
        # ------------------------------------------------------------------------------------------
        stage = "historical_helper_binding"
        r3 = load_module(root / R3, "postv16_av4_o2_r3")
        h1base = load_module(root / r3.H1EXEC, "postv16_av4_o2_h1base")
        base = load_module(root / h1base.R3R3R3, "postv16_av4_o2_base")

        # R3 source itself carries exact lower-level source authorities.
        for fn, expected in h1base.SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind exact accepted event state and parent split state.
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
        # Exact E0 reconstruction, targets and source-authentic capacity.
        # ------------------------------------------------------------------------------------------
        stage = "E0_authority_reconstruction"
        a2e = load_module(root / h1base.A2E, "postv16_av4_o2_a2e")
        r2phys = load_module(root / h1base.R2, "postv16_av4_o2_r2")
        e37 = load_module(root / h1base.E37A, "postv16_av4_o2_e37")
        sg7d = load_module(root / h1base.SG7D, "postv16_av4_o2_sg7d")

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
            and base.max_abs(sub_pv - geom_pv) <= 1e-12,
            {"subsegments": int(len(sub_flat)), "pv_Linf": base.max_abs(sub_pv - geom_pv)},
        )

        event_sub_sat = event_cv_sat.reshape(-1)[geom_cv_id]
        event_sub_sg = np.clip(event_sub_sat - BACKGROUND, 0.0, MAX_SG)
        event_sub_rho = np.asarray(
            r2phys.gas_density_from_state(event_sub_sat, geom_pseg, p_ref),
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
        gate(
            "source_authentic_cell_capacity_finite_positive",
            np.isfinite(cell_capacity).all() and float(np.min(cell_capacity)) > 0.0,
            [float(np.min(cell_capacity)), float(np.max(cell_capacity))],
        )

        # ------------------------------------------------------------------------------------------
        # Exact E2 construction and formal R1 certificate.
        # ------------------------------------------------------------------------------------------
        stage = "E2_support_and_R1_certificate_binding"
        support = r3.build_e2_support(e0_cv, e0_cell)
        gate("E1_pair_count_exact_1245666", len(support["e1_key"]) == EXPECTED_E1_PAIRS, len(support["e1_key"]))
        gate("E2_pair_count_exact_3091073", len(support["e2_key"]) == EXPECTED_E2_PAIRS, len(support["e2_key"]))
        gate(
            "E2_global_cell_count_exact_34497",
            len(support["e2_global_cells"]) == EXPECTED_E2_GLOBAL_CELLS,
            len(support["e2_global_cells"]),
        )

        r1d = drive / R1_REL
        verify_manifest(r1d, R1_MANIFEST)
        h2row = [
            row for row in read_csv(r1d / R1_MATRIX)
            if row["candidate"] == "H2_HORIZONTAL_GRAPH_RADIUS_2"
        ]
        gate(
            "formal_R1_H2_zero_unserved_certificate_bound",
            len(h2row) == 1
            and h2row[0]["feasible"].strip().lower() == "true"
            and float(h2row[0]["minimum_unserved_mass_kg"]) == 0.0
            and int(h2row[0]["pair_count"]) == EXPECTED_E2_PAIRS,
            h2row[0] if h2row else None,
        )

        demand = event_cv_mass.reshape(-1).astype(np.float64)
        residual = parent_residual_grid.reshape(-1).astype(np.float64)
        cap = cell_capacity.reshape(-1).astype(np.float64)
        available_raw = cap - residual
        cap_tol = max(1e-7, 1e-12 * max(float(np.max(np.abs(cap))), 1.0))
        gate(
            "residual_sidecar_within_capacity",
            float(np.min(available_raw)) >= -cap_tol,
            {"minimum_available_kg": float(np.min(available_raw)), "tolerance_kg": cap_tol},
        )
        available_safe = np.maximum(available_raw, 0.0)

        target0, qtarget0, zero_parent_count = h1base.build_e0_targets(
            e0_cv,
            parent_pair_mass,
            raw_event_pair_mass,
            parent_cv_mass,
            event_cv_mass,
        )
        target_by_edge = np.zeros(EXPECTED_E2_PAIRS, dtype=np.float64)
        qtarget_by_edge = np.zeros(EXPECTED_E2_PAIRS, dtype=np.float64)
        target_by_edge[support["e0_indices_in_e2"]] = target0
        qtarget_by_edge[support["e0_indices_in_e2"]] = qtarget0

        # ------------------------------------------------------------------------------------------
        # Exact-zero preprocessing and exact component audit.
        # ------------------------------------------------------------------------------------------
        stage = "exact_graph_preprocessing"
        prep = preprocess_active_graph(
            e2_cv=support["e2_cv"],
            e2_cell=support["e2_cell"],
            demand=demand,
            available_raw=available_raw,
        )

        print()
        print("=" * 160)
        print("[PASS] EXACT H2 GRAPH PREPROCESSING")
        print("=" * 160)
        print("Raw E0 / E1 / E2 pairs          :", EXPECTED_E0_PAIRS, "/", EXPECTED_E1_PAIRS, "/", EXPECTED_E2_PAIRS)
        print("Active CVs                       :", prep["active_CV_count"])
        print("Exact-zero demand CVs removed    :", prep["exact_zero_demand_CV_count_removed"])
        print("Active cells                     :", prep["active_cell_count"])
        print("Exact-zero capacity cells removed:", prep["exact_zero_capacity_cell_count_removed"])
        print("Active E2 edges                  :", prep["active_edge_count"])
        print("Connected components             :", prep["component_count"])
        print(
            "Largest component CV/cell/edges  :",
            prep["largest_component_CV_count"], "/",
            prep["largest_component_cell_count"], "/",
            prep["largest_component_edge_count"],
        )
        print("Preprocessing wall time s         :", prep["preprocessing_wall_time_s"])
        print("RSS MB                            :", prep["rss_mb_after_preprocessing"])
        sys.stdout.flush()

        # Constants from exact-fixed-zero E0 variables removed by preprocessing.
        removed_edge_mask = ~prep["active_edge_mask"]
        removed_e0 = removed_edge_mask & support["is_e0"]
        parent_fixed_zero_constant = float(np.sum(np.abs(target_by_edge[removed_e0])))
        raw_fixed_zero_constant = float(np.sum(np.abs(qtarget_by_edge[removed_e0])))

        # ------------------------------------------------------------------------------------------
        # Persistent native-HiGHS component solves.
        # ------------------------------------------------------------------------------------------
        stage = "persistent_native_HiGHS_assignment"
        t_opt0 = time.perf_counter()
        full_x = np.zeros(EXPECTED_E2_PAIRS, dtype=np.float64)
        component_results = []
        all_telemetry = []

        for cid in range(prep["component_count"]):
            a = int(prep["component_starts"][cid])
            b = int(prep["component_starts"][cid + 1])
            edge_idx = prep["sorted_edge_idx"][a:b]
            comp = make_component(
                component_id=cid,
                edge_idx=edge_idx,
                support=support,
                demand=demand,
                available_safe=available_safe,
                target_by_edge=target_by_edge,
                qtarget_by_edge=qtarget_by_edge,
            )

            print()
            print("=" * 160)
            print(f"[START] COMPONENT {cid+1}/{prep['component_count']}")
            print("=" * 160)
            print("CVs / cells / edges :", len(comp["cv_ids"]), "/", len(comp["cell_ids"]), "/", len(comp["edge_idx"]))
            print("E0 edges            :", len(comp["e0_x_local"]))
            print("RSS MB              :", current_rss_mb())
            sys.stdout.flush()

            build_t0 = time.perf_counter()
            model_data = build_component_model(comp, highspy)
            build_wall = time.perf_counter() - build_t0
            print(
                f"[PASS] COMPONENT {cid} MODEL BUILD | wall={build_wall:.6f}s | "
                f"vars={model_data['ncol']} | rows={model_data['nrow']} | nnz={model_data['nnz']}"
            )
            sys.stdout.flush()

            result = solve_component(
                comp=comp,
                highspy=highspy,
                model_data=model_data,
                verbose_solver=verbose_solver,
            )
            full_x[result["edge_idx"]] = result["final_x"]
            result["model_build_wall_time_s"] = float(build_wall)
            component_results.append(result)
            all_telemetry.extend(result["telemetry"])

            del comp, model_data, result
            gc.collect()

        total_optimization_wall = time.perf_counter() - t_opt0

        # ------------------------------------------------------------------------------------------
        # Full E2 reconstruction and exact scientific certification.
        # ------------------------------------------------------------------------------------------
        stage = "full_E2_assignment_certification"
        mapped = np.bincount(
            support["e2_cell"], weights=full_x, minlength=NCELL
        ).astype(np.float64)
        cv_reconstructed = np.bincount(
            support["e2_cv"], weights=full_x, minlength=NCVTOTAL
        ).astype(np.float64)
        event_grid_mass = residual + mapped

        cv_tol = max(1e-6, 1e-10 * max(float(np.max(np.abs(demand))), 1.0))
        grid_tol = max(1e-6, 1e-10 * max(float(np.max(np.abs(cap))), 1.0))

        gate(
            "O2_stage1_primal_recertifies_E2_feasibility",
            base.max_abs(cv_reconstructed - demand) <= cv_tol
            and float(np.max(mapped - available_safe)) <= grid_tol,
            {
                "CV_Linf_kg": base.max_abs(cv_reconstructed - demand),
                "max_capacity_excess_kg": float(np.max(mapped - available_safe)),
            },
        )
        gate(
            "O2_event_grid_nonnegative",
            float(np.min(event_grid_mass)) >= -grid_tol,
            float(np.min(event_grid_mass)),
        )
        gate(
            "O2_event_grid_within_source_authentic_capacity",
            float(np.max(event_grid_mass - cap)) <= grid_tol,
            float(np.max(event_grid_mass - cap)),
        )
        gate(
            "O2_residual_sidecar_unchanged",
            base.max_abs(event_grid_mass - mapped - residual) <= 1e-8,
            base.max_abs(event_grid_mass - mapped - residual),
        )

        global_resid = (
            base.fsum_array(event_grid_mass)
            - base.fsum_array(residual)
            - base.fsum_array(demand)
        )
        gate(
            "O2_global_component_mass_exact",
            abs(global_resid)
            <= max(1e-5, 1e-10 * max(base.fsum_array(event_grid_mass), 1.0)),
            global_resid,
        )
        gate(
            "O2_no_mass_outside_E2",
            True,
            "full decision vector has exactly E2 cardinality; pruned entries reconstructed as exact zero",
        )

        shell_mass = float(np.sum(full_x[support["is_h2_shell"]]))
        extension_mass = float(np.sum(full_x[support["is_any_extension"]]))
        parent_l1 = float(
            np.sum(np.abs(full_x[support["e0_indices_in_e2"]] - target0))
        )
        raw_l1 = float(
            np.sum(np.abs(full_x[support["e0_indices_in_e2"]] - qtarget0))
        )
        rank = (
            np.arange(EXPECTED_E2_PAIRS, dtype=np.float64) + 1.0
        ) / float(EXPECTED_E2_PAIRS)
        tie_obj = float(np.dot(rank, full_x))

        component_stage1 = float(sum(r["objectives"]["stage1_shell_kg"] for r in component_results))
        component_stage2 = float(sum(r["objectives"]["stage2_extension_kg"] for r in component_results))
        component_stage3 = parent_fixed_zero_constant + float(
            sum(r["objectives"]["stage3_parent_L1_kg"] for r in component_results)
        )
        component_stage4 = raw_fixed_zero_constant + float(
            sum(r["objectives"]["stage4_raw_L1_kg"] for r in component_results)
        )
        component_stage5 = float(sum(r["objectives"]["stage5_tiebreak"] for r in component_results))

        objective_tol = lambda v: max(1e-5, 1e-10 * max(abs(float(v)), 1.0))
        gate(
            "O2_component_stage1_sum_matches_full_shell_mass",
            abs(component_stage1 - shell_mass) <= objective_tol(shell_mass),
            {"component_sum": component_stage1, "full": shell_mass},
        )
        gate(
            "O2_component_stage2_sum_matches_full_extension_mass",
            abs(component_stage2 - extension_mass) <= objective_tol(extension_mass),
            {"component_sum": component_stage2, "full": extension_mass},
        )
        gate(
            "O2_component_stage3_sum_matches_full_parent_L1",
            abs(component_stage3 - parent_l1) <= objective_tol(parent_l1),
            {"component_plus_fixed": component_stage3, "full": parent_l1},
        )
        gate(
            "O2_component_stage4_sum_matches_full_raw_L1",
            abs(component_stage4 - raw_l1) <= objective_tol(raw_l1),
            {"component_plus_fixed": component_stage4, "full": raw_l1},
        )
        gate(
            "O2_component_stage5_sum_matches_full_tiebreak",
            abs(component_stage5 - tie_obj) <= objective_tol(tie_obj),
            {"component_sum": component_stage5, "full": tie_obj},
        )

        positive_tol = max(
            1e-10, 1e-14 * max(base.fsum_array(full_x), 1.0)
        )
        shell_positive = support["is_h2_shell"] & (full_x > positive_tol)
        extension_positive = support["is_any_extension"] & (full_x > positive_tol)
        shell_cvs = np.unique(support["e2_cv"][shell_positive])
        shell_streamlines = np.unique(shell_cvs // NCV)
        shell_cells = np.unique(support["e2_cell"][shell_positive])
        ext_cvs = np.unique(support["e2_cv"][extension_positive])

        # ------------------------------------------------------------------------------------------
        # Artifacts. O2 stops here: no pressure/flow/Pollock/TOF work.
        # ------------------------------------------------------------------------------------------
        stage = "artifact_publication"
        npz_bytes = base.deterministic_npz_bytes(
            {
                "event_day": np.asarray(EVENT_DAY),
                "physical_time_advanced_in_O2": np.asarray(False),
                "event_grid_component_mass_kg": event_grid_mass.reshape(GRID),
                "event_mapped_grid_mass_kg": mapped.reshape(GRID),
                "frozen_residual_grid_component_mass_kg": residual.reshape(GRID),
                "event_CV_component_mass_kg": demand.reshape(NSL, NCV),
                "E0_pair_cv_id": e0_cv,
                "E0_pair_flat_cell": e0_cell,
                "E0_parent_ownership_mass_kg": parent_pair_mass,
                "E1_pair_key": support["e1_key"],
                "E2_pair_cv_id": support["e2_cv"],
                "E2_pair_flat_cell": support["e2_cell"],
                "E2_pair_is_E0": support["is_e0"],
                "E2_pair_is_E1": support["is_e1"],
                "E2_pair_event_mass_kg": full_x,
                "E0_parent_continuity_target_kg": target0,
                "E0_raw_event_EOS_target_kg": qtarget0,
                "parent_pressure_psi": parent_pressure,
                "grid_pore_volume_m3": grid_pv,
                "reference_gas_pressure_pa": np.asarray(p_ref),
            }
        )

        stage_wall = {}
        for stage_no in range(1, 6):
            stage_wall[f"stage_{stage_no}_wall_time_s"] = float(
                sum(
                    row["wall_time_s"]
                    for row in all_telemetry
                    if row["stage"] == stage_no
                )
            )

        preprocess_summary = {
            k: v for k, v in prep.items()
            if k not in {
                "active_edge_mask", "active_edge_idx", "active_cv_global",
                "active_cell_global", "component_labels", "edge_component",
                "component_edge_counts", "component_cv_counts",
                "component_cell_counts", "sorted_edge_idx", "component_starts",
            }
        }
        preprocess_summary["top_component_edge_counts"] = sorted(
            [int(x) for x in prep["component_edge_counts"]], reverse=True
        )[:20]
        preprocess_summary["top_component_CV_counts"] = sorted(
            [int(x) for x in prep["component_cv_counts"]], reverse=True
        )[:20]
        preprocess_summary["top_component_cell_counts"] = sorted(
            [int(x) for x in prep["component_cell_counts"]], reverse=True
        )[:20]

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "highspy_version": highspy_version,
            "formal_R1_H2_feasibility_certificate_bound": True,
            "standalone_stage0_LP_executed": False,
            "stage1_fresh_feasibility_recertification_pass": True,
            "E0_pair_count": EXPECTED_E0_PAIRS,
            "E1_pair_count": EXPECTED_E1_PAIRS,
            "E2_pair_count": EXPECTED_E2_PAIRS,
            "E2_global_cell_count": EXPECTED_E2_GLOBAL_CELLS,
            "component_count": prep["component_count"],
            "active_edge_count": prep["active_edge_count"],
            "minimum_H2_shell_mass_kg": shell_mass,
            "minimum_total_extension_mass_kg": extension_mass,
            "parent_ownership_L1_kg": parent_l1,
            "raw_event_EOS_L1_kg": raw_l1,
            "deterministic_tiebreak_objective": tie_obj,
            "H2_shell_CV_count": int(shell_cvs.size),
            "H2_shell_streamline_count": int(shell_streamlines.size),
            "H2_shell_cell_count": int(shell_cells.size),
            "any_extension_CV_count": int(ext_cvs.size),
            "CV_mass_Linf_error_kg": base.max_abs(cv_reconstructed - demand),
            "event_grid_min_mass_kg": float(np.min(event_grid_mass)),
            "event_grid_max_capacity_excess_kg": float(np.max(event_grid_mass - cap)),
            "global_mass_residual_kg": global_resid,
            "preprocessing_wall_time_s": prep["preprocessing_wall_time_s"],
            "total_optimization_wall_time_s": float(total_optimization_wall),
            **stage_wall,
            "flow_refresh_executed": False,
            "Pollock_or_TOF_refresh_executed": False,
            "physical_time_advanced": False,
            "O3_authorized": True,
            "R3R3R4_authorized": False,
            "F5_authorized": False,
            "training_authorized": False,
        }

        audit = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "optimization_engine": "highspy.Highs",
            "highspy_version": highspy_version,
            "solver": "simplex",
            "persistent_model_per_component": True,
            "basis_reuse_attempted_between_stages": True,
            "exact_zero_pruning_only": True,
            "tolerance_based_graph_pruning": False,
            "exact_component_decomposition": True,
            "preprocessing": preprocess_summary,
            "fixed_zero_parent_L1_constant_kg": parent_fixed_zero_constant,
            "fixed_zero_raw_L1_constant_kg": raw_fixed_zero_constant,
            "zero_parent_positive_event_CV_count": int(zero_parent_count),
            "objectives": {
                "stage1_H2_shell_kg": shell_mass,
                "stage2_total_extension_kg": extension_mass,
                "stage3_parent_L1_kg": parent_l1,
                "stage4_raw_L1_kg": raw_l1,
                "stage5_tiebreak": tie_obj,
            },
            "final_validation": {
                "CV_mass_Linf_error_kg": base.max_abs(cv_reconstructed - demand),
                "max_capacity_excess_kg": float(np.max(mapped - available_safe)),
                "event_grid_max_capacity_excess_kg": float(np.max(event_grid_mass - cap)),
                "global_mass_residual_kg": global_resid,
                "minimum_pair_mass_kg": float(np.min(full_x)),
            },
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
        }

        component_rows = []
        for r in component_results:
            row = {
                "component_id": r["component_id"],
                **r["model"],
                "model_build_wall_time_s": r["model_build_wall_time_s"],
                **r["objectives"],
            }
            component_rows.append(row)

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3",
            "name": "Same-Time Flow Refresh and Bounded Reprojection from Optimized H2 Event Mapback",
            "authorized": True,
            "execution": True,
            "required_O2_status": STATUS_PASS,
            "required_parent_state":
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz",
            "parent_event_day": EVENT_DAY,
            "physical_time_advance_before_O3": False,
            "scope": [
                "invert optimized event Cartesian mass under parent pressure",
                "execute exactly one same-time event flow refresh",
                "regenerate pressure/Darcy/Pollock/TOF/weights",
                "execute bounded refreshed-geometry reprojection",
                "publish refreshed event recurrent state and stop",
            ],
            "not_authorized": [
                "physical-time advance",
                "Day500 continuation",
                "second event refresh",
                "support radius >2",
                "vertical support",
                "H2+V1 fallback",
                "F5",
                "training",
                "A3-E2",
                "CMG",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "O1_optimization_freeze_bound": True,
            "scientific_problem_changed": False,
            "lexicographic_objectives_changed": False,
            "optimized_H2_assignment_executed": True,
            "standalone_stage0_LP_executed": False,
            "exact_zero_pruning_only": True,
            "exact_component_decomposition_used": True,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "O3_authorized": True,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Summary.json":
                base.json_bytes(summary_out),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimization_Audit.json":
                base.json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Stage_Telemetry.csv":
                base.csv_bytes(all_telemetry),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Component_Summary.csv":
                base.csv_bytes(component_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz":
                npz_bytes,
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_O3_Handoff_Contract.json":
                base.json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Decision_Contract.json":
                base.json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Final_Gate_Matrix.csv":
                base.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        base.immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": base.sha256_file(p), "bytes": p.stat().st_size}
                )
        base.immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Artifact_Manifest.csv":
                    base.csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O2: PERSISTENT NATIVE-HiGHS "
            "H2 ASSIGNMENT PASS"
        )
        print("=" * 214)
        print("HiGHS version                         :", highspy_version)
        print("Standalone Stage-0 LP                : NOT EXECUTED")
        print("Connected components                 :", prep["component_count"])
        print("Active / raw E2 edges                :", prep["active_edge_count"], "/", EXPECTED_E2_PAIRS)
        print("Minimum H2 shell mass kg             :", shell_mass)
        print("Minimum total extension mass kg      :", extension_mass)
        print("Parent ownership L1 kg               :", parent_l1)
        print("Raw event EOS L1 kg                  :", raw_l1)
        print("H2 shell CV / streamline / cell      :", int(shell_cvs.size), "/", int(shell_streamlines.size), "/", int(shell_cells.size))
        print("CV mass Linf error kg                :", base.max_abs(cv_reconstructed - demand))
        print("Event-grid max capacity excess kg    :", float(np.max(event_grid_mass - cap)))
        print("Preprocessing wall time s            :", prep["preprocessing_wall_time_s"])
        print("Total optimization wall time s       :", total_optimization_wall)
        for k, v in stage_wall.items():
            print(f"{k:<39}:", v)
        print("Flow refresh / physical-time advance : False / False")
        print("POSTV16-...-O3                      : AUTHORIZED")
        print("R3-R3-R4 / F5 / training             : NOT AUTHORIZED")
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
            "original_R3_source_preserved": True,
            "O1_optimization_freeze_preserved": True,
            "scientific_problem_changed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = (
            base.json_bytes(report)
            if base is not None
            else json_bytes(report)
        )
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Blocked_Report_"
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
        print("NO SCIENTIFIC FAIL CLAIM. R1 H2 FEASIBILITY PASS REMAINS AUTHORITATIVE.")
        print("NO O3 / R3-R3-R4 / F5 / TRAINING AUTHORIZED.")
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
    p.add_argument("--highspy-api-test", action="store_true")
    p.add_argument(
        "--quiet-solver",
        action="store_true",
        help="Disable HiGHS native console log; stage telemetry remains enabled.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    if args.highspy_api_test:
        highspy_api_test()
        raise SystemExit(0)
    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
            verbose_solver=not args.quiet_solver,
        )
    )
