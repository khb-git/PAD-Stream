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
from scipy.sparse import coo_matrix, csr_matrix, eye, hstack


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R1"

STATUS_PASS = (
    "AV4F4R3R3R3R1_R3R3R3_STAGE1_S0_ASSIGNMENT_SCIENTIFIC_FAIL_PRESERVED_"
    "EXACT_CONTINUOUS_MINIMUM_UNSERVED_MASS_AND_RESIDUAL_MINCUT_HALL_WITNESS_"
    "LOCALIZED_NO_REPAIR_SELECTED"
)
STATUS_BLOCKED = "AV4F4R3R3R3R1_S0_CAPACITY_FEASIBILITY_LOCALIZATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R3_COMMIT = "fb6a678307615e4eafca55ae84b29e77aa443a84"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NN = 201
NCV = 200
NCVTOTAL = NSL * NCV
BACKGROUND = 0.20
INJECTED = 0.80
EVENT_DAY = 413.78677770818403

R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_"
    "Ownership_Reconciled_Event_MapBack_and_Flow_Refresh_Execution.py"
)
R3R3_BLOB = "b2c129bd067ef75163c3f06de5c15adc53ae5633"

R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R2_"
    "Bounded_Parent_Ownership_Event_MapBack_Reconciliation_Freeze.py"
)
R3R2_BLOB = "247e1e5b6d3fc83bd81d3dd84f0bbeb88c5280c0"

R3R1R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R1_R2_"
    "Corrected_Interior_Bound_Failure_Localization.py"
)
R3R1R2_BLOB = "b7613d8eda48b6e3528115c40faebe46d7b61604"

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

SOURCE_BLOBS = {
    R3R3: R3R3_BLOB,
    R3R2: R3R2_BLOB,
    R3R1R2: R3R1R2_BLOB,
    F2R3: F2R3_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R3_FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_SCIENTIFIC_FAIL"
R3R3_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_Scientific_Fail_Report.json"
R3R3_FAIL_STATUS = (
    "AV4F4R3R3R3_FROZEN_EVENT_MAPBACK_OR_SINGLE_FLOW_REFRESH_OR_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_SUPPORT_EXPANSION_NO_ALTERNATE_REPAIR_NO_AUTOMATIC_RERUN"
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
    / "POSTV16_AV4_F4_R3_R3_R3_R1_S0_CV_Cell_Capacity_Hall_Deficit_Localization"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R1_BLOCKED"


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


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=np.float64))))


def incidence(rows_idx: np.ndarray, nrows: int, ncols: int) -> csr_matrix:
    cols = np.arange(ncols, dtype=np.int64)
    return coo_matrix(
        (
            np.ones(ncols, dtype=np.float64),
            (np.asarray(rows_idx, dtype=np.int64), cols),
        ),
        shape=(nrows, ncols),
    ).tocsr()


def minimum_unserved_lp(
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    ncv: int,
    ncell: int,
) -> dict[str, Any]:
    pair_cv = np.asarray(pair_cv, dtype=np.int64)
    pair_cell = np.asarray(pair_cell, dtype=np.int64)
    demand = np.asarray(demand, dtype=np.float64).reshape(ncv)
    available = np.asarray(available, dtype=np.float64).reshape(ncell)

    n = len(pair_cv)
    A_cv = incidence(pair_cv, ncv, n)
    A_cell = incidence(pair_cell, ncell, n)

    A_eq = hstack([A_cv, eye(ncv, format="csr")], format="csr")
    b_eq = demand

    A_ub = hstack(
        [A_cell, csr_matrix((ncell, ncv))],
        format="csr",
    )
    b_ub = available

    c = np.concatenate(
        [
            np.zeros(n, dtype=np.float64),
            np.ones(ncv, dtype=np.float64),
        ]
    )
    bounds = [(0.0, None)] * (n + ncv)

    res = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
        options={"presolve": True},
    )
    if not res.success:
        raise GateError(
            "minimum_unserved_LP_should_be_feasible_but_failed:"
            + str(res.status)
            + ":"
            + str(res.message)
        )

    x = np.asarray(res.x[:n], dtype=np.float64)
    y = np.asarray(res.x[n:], dtype=np.float64)
    used = np.bincount(pair_cell, weights=x, minlength=ncell).astype(np.float64)
    served = np.bincount(pair_cv, weights=x, minlength=ncv).astype(np.float64)

    return {
        "pair_flow": x,
        "unserved_cv": y,
        "cell_used": used,
        "cv_served": served,
        "minimum_unserved_mass": float(np.sum(y)),
        "status": int(res.status),
        "message": str(res.message),
        "iterations": getattr(res, "nit", None),
    }


def residual_mincut_witness(
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    pair_flow: np.ndarray,
    unserved_cv: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
    ncv: int,
    ncell: int,
    flow_tol: float,
) -> dict[str, Any]:
    pair_cv = np.asarray(pair_cv, dtype=np.int64)
    pair_cell = np.asarray(pair_cell, dtype=np.int64)
    x = np.asarray(pair_flow, dtype=np.float64)
    y = np.asarray(unserved_cv, dtype=np.float64).reshape(ncv)
    demand = np.asarray(demand, dtype=np.float64).reshape(ncv)
    available = np.asarray(available, dtype=np.float64).reshape(ncell)

    support = coo_matrix(
        (
            np.ones(len(pair_cv), dtype=np.int8),
            (pair_cv, pair_cell),
        ),
        shape=(ncv, ncell),
    ).tocsr()

    pos = x > flow_tol
    reverse_flow = coo_matrix(
        (
            np.ones(int(np.sum(pos)), dtype=np.int8),
            (pair_cv[pos], pair_cell[pos]),
        ),
        shape=(ncv, ncell),
    ).tocsr()

    cv_reach = y > flow_tol
    cell_reach = np.zeros(ncell, dtype=bool)

    iterations = 0
    while True:
        iterations += 1
        prev_cv = int(np.sum(cv_reach))
        prev_cell = int(np.sum(cell_reach))

        if np.any(cv_reach):
            reached_cells_now = (
                support.T.dot(cv_reach.astype(np.int32)) > 0
            )
            cell_reach |= np.asarray(reached_cells_now).reshape(-1)

        if np.any(cell_reach) and reverse_flow.nnz:
            reached_cvs_now = (
                reverse_flow.dot(cell_reach.astype(np.int32)) > 0
            )
            cv_reach |= np.asarray(reached_cvs_now).reshape(-1)

        if (
            int(np.sum(cv_reach)) == prev_cv
            and int(np.sum(cell_reach)) == prev_cell
        ):
            break
        if iterations > ncv + ncell + 5:
            raise GateError("residual_cut_closure_did_not_converge")

    used = np.bincount(pair_cell, weights=x, minlength=ncell).astype(np.float64)
    residual_capacity = available - used

    demand_u = fsum_array(demand[cv_reach])
    capacity_n = fsum_array(available[cell_reach])
    hall_deficit = demand_u - capacity_n

    return {
        "cv_reachable": cv_reach,
        "cell_reachable": cell_reach,
        "iterations": iterations,
        "demand_U": demand_u,
        "capacity_N": capacity_n,
        "hall_deficit": hall_deficit,
        "max_reachable_cell_residual_capacity":
            float(np.max(residual_capacity[cell_reach]))
            if np.any(cell_reach)
            else 0.0,
        "cell_used": used,
        "residual_capacity": residual_capacity,
    }


def self_test() -> None:
    # Hall-deficit toy problem:
    # CV0 and CV1 each demand 5 kg; both can use only cell0 with capacity 7 kg.
    pair_cv = np.array([0, 1], dtype=np.int64)
    pair_cell = np.array([0, 0], dtype=np.int64)
    demand = np.array([5.0, 5.0])
    available = np.array([7.0])

    sol = minimum_unserved_lp(
        pair_cv,
        pair_cell,
        demand,
        available,
        ncv=2,
        ncell=1,
    )
    assert abs(sol["minimum_unserved_mass"] - 3.0) < 1e-9

    witness = residual_mincut_witness(
        pair_cv,
        pair_cell,
        sol["pair_flow"],
        sol["unserved_cv"],
        demand,
        available,
        ncv=2,
        ncell=1,
        flow_tol=1e-10,
    )
    assert np.all(witness["cv_reachable"])
    assert np.all(witness["cell_reachable"])
    assert abs(witness["hall_deficit"] - 3.0) < 1e-9

    print(
        "POSTV16-AV4-F4-R3-R3-R3-R1 S0 CV-cell Hall-deficit "
        "localization self-test: PASS"
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
        "POSTV16-AV4-F4-R3-R3-R3-R1 — S0 CV-TO-CELL CAPACITY "
        "FEASIBILITY / HALL-DEFICIT LOCALIZATION"
    )
    print("=" * 214)
    print("DIAGNOSTIC ONLY. FORMAL R3-R3-R3 SCIENTIFIC FAIL REMAINS IMMUTABLE.")
    print("NO MAPBACK REPAIR. NO SUPPORT EXPANSION. NO HALO. NO CAPACITY RELAXATION.")
    print("NO FLOW REFRESH. NO PHYSICAL-TIME ADVANCE. NO F5. NO TRAINING. NO CMG.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_R3R3_commit",
            parent == PARENT_R3R3_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "R3R3_scientific_fail_binding"
        fail_path = drive / R3R3_FAIL_REL / R3R3_FAIL_REPORT
        gate("R3R3_scientific_fail_report_present", fail_path.is_file(), str(fail_path))
        fail = load_json(fail_path)
        gate("R3R3_fail_status_exact", fail["status"] == R3R3_FAIL_STATUS, fail["status"])
        gate(
            "R3R3_fail_stage_exact",
            fail["failed_stage"] == "frozen_parent_ownership_event_mapback_LP",
            fail["failed_stage"],
        )
        gate(
            "R3R3_fail_gate_exact",
            fail["failed_gate"] == "stage1_parent_ownership_L1_LP_infeasible",
            fail["failed_gate"],
        )
        gate(
            "R3R3_fail_HiGHS_infeasible_exact",
            int(fail["detail"]["status"]) == 2
            and "infeasible" in str(fail["detail"]["message"]).lower(),
            fail["detail"],
        )
        gate(
            "R3R3_fail_no_fallback_or_time_advance",
            fail["support_domain_changed"] is False
            and fail["physical_time_advanced"] is False
            and fail["second_event_refresh_authorized"] is False
            and fail["automatic_fallback_authorized"] is False
            and fail["R3R3R4_authorized"] is False
            and fail["F5_dataset_generation_authorized"] is False,
        )

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
            parent_residual = np.asarray(z["residual_grid_component_mass_kg"], dtype=np.float64)
            parent_cell_pv = np.asarray(z["physical_cell_pore_volume_m3"], dtype=np.float64)
            sub_flat = np.asarray(z["subsegment_flat_cell"], dtype=np.int64)
            sub_stream = np.asarray(z["subsegment_streamline"], dtype=np.int64)
            sub_cv = np.asarray(z["subsegment_control_volume"], dtype=np.int64)

        with np.load(evd / R3R1R2_STATE, allow_pickle=False) as z:
            event_cv_mass = np.asarray(z["partial_CV_component_mass_kg"], dtype=np.float64)

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            parent_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            grid_pv = np.asarray(z["pore_volume_m3"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate(
            "authority_shapes_exact",
            parent_residual.shape == GRID
            and parent_cell_pv.shape == GRID
            and event_cv_mass.shape == (NSL, NCV)
            and parent_pressure.shape == GRID
            and grid_pv.shape == GRID
            and len(sub_flat) == len(sub_stream) == len(sub_cv),
        )
        gate(
            "F2R3_physical_cell_pv_matches_A2E",
            max_abs(parent_cell_pv - grid_pv) <= 1e-12,
            max_abs(parent_cell_pv - grid_pv),
        )

        stage = "exact_S0_graph_and_capacity_reconstruction"
        r3r3 = load_module(root / R3R3, "postv16_r3r3r1_r3r3")
        a2e = load_module(root / A2E, "postv16_r3r3r1_a2e")
        r2 = load_module(root / R2, "postv16_r3r3r1_r2")

        cv_id = sub_stream * NCV + sub_cv
        key = cv_id * NCELL + sub_flat
        unique_key = np.unique(key)
        pair_cv = (unique_key // NCELL).astype(np.int64)
        pair_cell = (unique_key % NCELL).astype(np.int64)
        order = np.lexsort((pair_cell, pair_cv))
        pair_cv = pair_cv[order]
        pair_cell = pair_cell[order]

        gate("S0_pair_count_exact_269721", len(pair_cv) == 269721, len(pair_cv))

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
        available = cell_capacity.reshape(-1) - parent_residual.reshape(-1)
        cap_tol = max(
            1e-7,
            1e-12 * max(float(np.max(np.abs(cell_capacity))), 1.0),
        )
        gate(
            "residual_sidecar_within_physical_capacity",
            float(np.min(available)) >= -cap_tol,
            {
                "minimum_available_capacity_kg": float(np.min(available)),
                "tolerance_kg": cap_tol,
            },
        )
        available = np.maximum(available, 0.0)

        demand = event_cv_mass.reshape(-1)
        supported_cells = np.unique(pair_cell)
        total_demand = fsum_array(demand)
        global_capacity = fsum_array(available[supported_cells])
        global_tol = max(1e-6, 1e-10 * max(total_demand, 1.0))

        gate(
            "S0_global_capacity_is_sufficient",
            total_demand <= global_capacity + global_tol,
            {
                "event_CV_demand_kg": total_demand,
                "supported_cell_available_capacity_kg": global_capacity,
                "global_surplus_kg": global_capacity - total_demand,
                "tolerance_kg": global_tol,
            },
        )

        stage = "minimum_unserved_mass_LP"
        sol = minimum_unserved_lp(
            pair_cv,
            pair_cell,
            demand,
            available,
            NCVTOTAL,
            NCELL,
        )
        min_deficit = float(sol["minimum_unserved_mass"])
        deficit_tol = max(1e-6, 1e-10 * max(total_demand, 1.0))

        cv_eq_resid = sol["cv_served"] + sol["unserved_cv"] - demand
        cell_excess = sol["cell_used"] - available
        gate(
            "minimum_unserved_LP_primal_CV_equalities",
            max_abs(cv_eq_resid) <= deficit_tol,
            max_abs(cv_eq_resid),
        )
        gate(
            "minimum_unserved_LP_cell_capacities",
            float(np.max(cell_excess)) <= deficit_tol,
            float(np.max(cell_excess)),
        )

        stage = "continuous_residual_mincut_localization"
        if min_deficit > deficit_tol:
            classification = "S0_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT"
            witness = residual_mincut_witness(
                pair_cv,
                pair_cell,
                sol["pair_flow"],
                sol["unserved_cv"],
                demand,
                available,
                NCVTOTAL,
                NCELL,
                flow_tol=max(1e-8, 1e-12 * max(total_demand, 1.0)),
            )
            cut_tol = max(1e-5, 1e-9 * max(total_demand, 1.0))
            gate(
                "Hall_witness_deficit_positive",
                witness["hall_deficit"] > deficit_tol,
                witness["hall_deficit"],
            )
            gate(
                "Hall_witness_matches_minimum_unserved_mass",
                abs(witness["hall_deficit"] - min_deficit) <= cut_tol,
                {
                    "minimum_unserved_mass_kg": min_deficit,
                    "Hall_deficit_kg": witness["hall_deficit"],
                    "residual_kg": witness["hall_deficit"] - min_deficit,
                    "tolerance_kg": cut_tol,
                },
            )
            gate(
                "Hall_witness_cells_are_capacity_saturated",
                witness["max_reachable_cell_residual_capacity"] <= cut_tol,
                witness["max_reachable_cell_residual_capacity"],
            )
        else:
            classification = "STAGE1_FORMULATION_OR_SOLVER_NUMERICAL_INCONSISTENCY"
            witness = {
                "cv_reachable": np.zeros(NCVTOTAL, dtype=bool),
                "cell_reachable": np.zeros(NCELL, dtype=bool),
                "iterations": 0,
                "demand_U": 0.0,
                "capacity_N": 0.0,
                "hall_deficit": 0.0,
                "max_reachable_cell_residual_capacity": 0.0,
                "cell_used": sol["cell_used"],
                "residual_capacity": available - sol["cell_used"],
            }
            gate(
                "feasible_slack_diagnostic_contradicts_stage1_fail",
                min_deficit <= deficit_tol,
                {
                    "minimum_unserved_mass_kg": min_deficit,
                    "tolerance_kg": deficit_tol,
                },
            )

        cv_mask = np.asarray(witness["cv_reachable"], dtype=bool)
        cell_mask = np.asarray(witness["cell_reachable"], dtype=bool)

        witness_cv_ids = np.flatnonzero(cv_mask)
        witness_cell_ids = np.flatnonzero(cell_mask)

        cv_rows = []
        if witness_cv_ids.size:
            slack = np.asarray(sol["unserved_cv"], dtype=np.float64)
            support_count = np.bincount(pair_cv, minlength=NCVTOTAL)
            sort_cv = witness_cv_ids[
                np.argsort(
                    -np.maximum(slack[witness_cv_ids], demand[witness_cv_ids])
                )
            ]
            for j in sort_cv[:1000]:
                cv_rows.append(
                    {
                        "cv_flat": int(j),
                        "streamline": int(j // NCV),
                        "control_volume": int(j % NCV),
                        "event_demand_kg": float(demand[j]),
                        "unserved_mass_in_minimum_deficit_LP_kg": float(slack[j]),
                        "S0_supported_cell_count": int(support_count[j]),
                    }
                )

        cell_rows = []
        if witness_cell_ids.size:
            residual_cap = np.asarray(witness["residual_capacity"], dtype=np.float64)
            used = np.asarray(witness["cell_used"], dtype=np.float64)
            sort_cells = witness_cell_ids[
                np.argsort(residual_cap[witness_cell_ids])
            ]
            for c in sort_cells[:1000]:
                k = int(c // (NY * NX))
                rem = int(c % (NY * NX))
                j = int(rem // NX)
                i = int(rem % NX)
                cell_rows.append(
                    {
                        "flat_cell": int(c),
                        "k": k,
                        "j": j,
                        "i": i,
                        "available_capacity_kg": float(available[c]),
                        "used_capacity_kg": float(used[c]),
                        "residual_capacity_kg": float(residual_cap[c]),
                    }
                )

        positive_slack = np.flatnonzero(sol["unserved_cv"] > deficit_tol)
        positive_slack_streamlines = (
            np.unique(positive_slack // NCV)
            if positive_slack.size
            else np.array([], dtype=np.int64)
        )
        witness_streamlines = (
            np.unique(witness_cv_ids // NCV)
            if witness_cv_ids.size
            else np.array([], dtype=np.int64)
        )
        witness_cv_positions = (
            witness_cv_ids % NCV
            if witness_cv_ids.size
            else np.array([], dtype=np.int64)
        )

        diagnosis = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "R3R3_scientific_FAIL_preserved": True,
            "R3R3_failed_gate": "stage1_parent_ownership_L1_LP_infeasible",
            "global_S0": {
                "event_CV_demand_kg": total_demand,
                "supported_cell_available_capacity_kg": global_capacity,
                "global_surplus_kg": global_capacity - total_demand,
            },
            "minimum_unserved_mass_LP": {
                "minimum_unserved_mass_kg": min_deficit,
                "positive_unserved_CV_count": int(positive_slack.size),
                "positive_unserved_streamline_count":
                    int(positive_slack_streamlines.size),
                "solver_status": sol["status"],
                "solver_message": sol["message"],
                "solver_iterations": sol["iterations"],
            },
            "residual_mincut_Hall_witness": {
                "CV_count": int(witness_cv_ids.size),
                "Cartesian_cell_count": int(witness_cell_ids.size),
                "streamline_count": int(witness_streamlines.size),
                "demand_U_kg": float(witness["demand_U"]),
                "capacity_N_of_U_kg": float(witness["capacity_N"]),
                "Hall_deficit_kg": float(witness["hall_deficit"]),
                "closure_iterations": int(witness["iterations"]),
                "max_reachable_cell_residual_capacity_kg":
                    float(witness["max_reachable_cell_residual_capacity"]),
                "CV_position_min":
                    int(np.min(witness_cv_positions))
                    if witness_cv_positions.size
                    else None,
                "CV_position_median":
                    float(np.median(witness_cv_positions))
                    if witness_cv_positions.size
                    else None,
                "CV_position_max":
                    int(np.max(witness_cv_positions))
                    if witness_cv_positions.size
                    else None,
                "terminal_CV_190_199_count":
                    int(np.sum(witness_cv_positions >= 190))
                    if witness_cv_positions.size
                    else 0,
            },
            "interpretation": (
                "Global S0 capacity is sufficient, but a positive Hall deficit means "
                "at least one CV subset has insufficient capacity in its own fixed S0 "
                "neighbor cells. Stage-1 infeasibility is therefore structural to the "
                "frozen incidence/capacity constraints, not to the L1 ownership objective."
                if classification == "S0_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT"
                else
                "The minimum-unserved diagnostic finds an S0-feasible assignment despite "
                "the prior Stage-1 failure; the next design must audit Stage-1 formulation "
                "or solver numerics rather than alter support."
            ),
        }

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R3-R2",
            "name": "S0 Assignment Infeasibility Repair Design Freeze",
            "authorized": True,
            "execution": False,
            "required_R3R3R3R1_status": STATUS_PASS,
            "required_classification": classification,
            "repair_selected": False,
            "repair_execution_authorized": False,
            "support_expansion_authorized": False,
            "capacity_relaxation_authorized": False,
            "per_CV_mass_relaxation_authorized": False,
            "residual_sidecar_change_authorized": False,
            "automatic_rerun_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "R3R3_scientific_FAIL_preserved": True,
            "repair_selected": False,
            "mapback_repair_executed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "R3R3R3R2_design_freeze_authorized": True,
            "R3R3R3R2_repair_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "event_day": EVENT_DAY,
            "global_S0_capacity_surplus_kg": global_capacity - total_demand,
            "minimum_unserved_mass_kg": min_deficit,
            "Hall_witness_CV_count": int(witness_cv_ids.size),
            "Hall_witness_cell_count": int(witness_cell_ids.size),
            "Hall_witness_streamline_count": int(witness_streamlines.size),
            "Hall_deficit_kg": float(witness["hall_deficit"]),
            "repair_selected": False,
            "R3R3R3R2_design_freeze_authorized": True,
            "repair_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_authorized": False,
        }

        witness_npz = deterministic_npz_bytes(
            {
                "pair_cv_id": pair_cv,
                "pair_flat_cell": pair_cell,
                "event_CV_demand_kg": demand,
                "S0_available_cell_capacity_kg": available,
                "minimum_unserved_LP_pair_flow_kg": sol["pair_flow"],
                "minimum_unserved_LP_unserved_CV_kg": sol["unserved_cv"],
                "minimum_unserved_LP_cell_used_kg": sol["cell_used"],
                "Hall_witness_CV_mask": cv_mask,
                "Hall_witness_cell_mask": cell_mask,
            }
        )

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R1_S0_Feasibility_Diagnosis.json":
                json_bytes(diagnosis),
            "POSTV16_AV4_F4_R3_R3_R3_R1_Hall_Witness_State.npz":
                witness_npz,
            "POSTV16_AV4_F4_R3_R3_R3_R1_Hall_Witness_CVs_Top1000.csv":
                csv_bytes(cv_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R1_Hall_Witness_Cells_Top1000.csv":
                csv_bytes(cell_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R1_R3R3R3R2_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R1_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R1_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R1_Artifact_Manifest.csv":
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
                "POSTV16_AV4_F4_R3_R3_R3_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R1: S0 CV-CELL CAPACITY "
            "FEASIBILITY / HALL-DEFICIT LOCALIZATION PASS"
        )
        print("=" * 214)
        print("R3-R3-R3 scientific FAIL                : PRESERVED")
        print("Global S0 capacity surplus kg            :", global_capacity - total_demand)
        print("Minimum unassignable event mass kg       :", min_deficit)
        print("Classification                           :", classification)
        print("Hall witness CV / cell / streamline count:",
              int(witness_cv_ids.size), "/",
              int(witness_cell_ids.size), "/",
              int(witness_streamlines.size))
        print("Hall witness demand kg                   :", float(witness["demand_U"]))
        print("Hall witness neighbor capacity kg        :", float(witness["capacity_N"]))
        print("Hall deficit kg                          :", float(witness["hall_deficit"]))
        print("Repair selected                          : False")
        print("POSTV16-AV4-F4-R3-R3-R3-R2 design freeze: AUTHORIZED")
        print("Repair execution / R3-R3-R4 / F5        : NOT AUTHORIZED")
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
            "repair_execution_authorized": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R3R2_design_freeze_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R1_Blocked_Report_"
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
        print("R3-R3-R3 scientific FAIL remains immutable.")
        print("NO REPAIR, SUPPORT CHANGE, FLOW REFRESH, OR AUTOMATIC RERUN AUTHORIZED.")
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
