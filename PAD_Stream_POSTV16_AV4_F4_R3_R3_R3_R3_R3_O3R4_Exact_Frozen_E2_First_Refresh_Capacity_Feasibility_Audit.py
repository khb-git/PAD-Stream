#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gc
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R4"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R4_EXACT_FROZEN_E2_FIRST_REFRESH_CAPACITY_"
    "FEASIBILITY_AUDIT_PASS_NO_STATE_MUTATION_NO_FLOW_REFRESH_NO_TIME_ADVANCE"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3O3R4_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_O3R3_COMMIT = "13a88ecaa0860bd14ff0a374a06a8757b6974684"
O3R3_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_"
    "Pressure_Capacity_Incompatibility_Audit_and_Prospective_Reconciliation_Design_Freeze.py"
)
O3R3_RUNNER_BLOB = "696b88ca5a95730de9ea7b95fef0b8388d95c8ac"
O3R3_STATUS = (
    "AV4F4R3R3R3R3R3O3R3_FIRST_REFRESH_PRESSURE_CAPACITY_INCOMPATIBILITY_"
    "READ_ONLY_AUDIT_AND_PROSPECTIVE_RECONCILIATION_DESIGN_FREEZE_PASS_"
    "NO_FLOW_REFRESH_NO_REPROJECTION_NO_TIME_ADVANCE"
)
O3R2_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_O2_Manifest_Cardinality_"
    "Authority_Repair_Same_Time_Flow_Refresh_and_Bounded_Reprojection_Execution.py"
)
O3R2_RUNNER_BLOB = "02e77ac9cf890c8e61f6787045e0f40a90b2ecc9"
O2_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution.py"
)
O2_RUNNER_BLOB = "2e04f77750add23f9cfe5143119668450201354f"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
O3R3_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Pressure_Capacity_Incompatibility_Audit"
O3R3_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Summary.json"
O3R3_AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Pressure_Capacity_Audit.json"
O3R3_DIAG = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Diagnostic_State.npz"
O3R3_DESIGN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Prospective_Reconciliation_Design.json"
O3R3_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Final_Gate_Matrix.csv"
O3R3_CELLS = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Violating_Cell_Diagnostics.csv"
O3R3_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Artifact_Manifest.csv"
EXPECTED_O3R3_FILES = {O3R3_SUMMARY, O3R3_AUDIT, O3R3_DIAG, O3R3_DESIGN, O3R3_GATES, O3R3_CELLS}

OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Exact_Frozen_E2_First_Refresh_Capacity_Feasibility_Audit"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_BLOCKED"

GRID = (15, 50, 50)
NCELL = 37500
NSL = 1078
NCV = 200
NCVTOTAL = NSL * NCV
EVENT_DAY = 413.78677770818403
EXPECTED_VIOLATING_CELLS = 10915
EXPECTED_MAX_EXCESS_KG = 41.00208069124892
EXPECTED_TOTAL_DEFICIT_KG = 254225.0106034257
EXPECTED_DIRECT_NO_SLACK_CVS = 13794
NUMERICAL_ZERO_KG = 1.0e-6

class GateError(RuntimeError):
    pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, text=True, capture_output=True).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fsum(a: np.ndarray) -> float:
    return math.fsum(np.asarray(a, dtype=np.float64).ravel().tolist())


def build_feasibility_lp(highspy, coo_matrix, e2_cv, e2_cell, demand, available):
    # Exact-zero graph pruning only. No tolerance-based support pruning.
    active = (demand[e2_cv] > 0.0) & (available[e2_cell] > 0.0)
    cv_e = np.asarray(e2_cv[active], dtype=np.int64)
    cell_e = np.asarray(e2_cell[active], dtype=np.int64)
    nedge = int(cv_e.size)

    # Variables: x_e >= 0 on frozen E2 edges, plus u_cv >= 0 unserved mass.
    # CV rows: sum_e x_e + u_cv == demand_cv.
    # Cell rows: sum_e x_e <= available_cell.
    ncol = nedge + NCVTOTAL
    nrow = NCVTOTAL + NCELL
    xcols = np.arange(nedge, dtype=np.int64)
    ucols = nedge + np.arange(NCVTOTAL, dtype=np.int64)

    rows = np.concatenate([
        cv_e,
        NCVTOTAL + cell_e,
        np.arange(NCVTOTAL, dtype=np.int64),
    ])
    cols = np.concatenate([xcols, xcols, ucols])
    vals = np.ones(rows.size, dtype=np.float64)
    A = coo_matrix((vals, (rows, cols)), shape=(nrow, ncol)).tocsc()

    inf = highspy.kHighsInf
    cost = np.zeros(ncol, dtype=np.float64)
    cost[nedge:] = 1.0
    col_lower = np.zeros(ncol, dtype=np.float64)
    col_upper = np.full(ncol, inf, dtype=np.float64)
    col_upper[nedge:] = np.asarray(demand, dtype=np.float64)

    row_lower = np.full(nrow, -inf, dtype=np.float64)
    row_upper = np.full(nrow, inf, dtype=np.float64)
    row_lower[:NCVTOTAL] = demand
    row_upper[:NCVTOTAL] = demand
    row_upper[NCVTOTAL:] = available

    lp = highspy.HighsLp()
    lp.num_col_ = int(ncol)
    lp.num_row_ = int(nrow)
    lp.sense_ = highspy.ObjSense.kMinimize
    lp.col_cost_ = cost
    lp.col_lower_ = col_lower
    lp.col_upper_ = col_upper
    lp.row_lower_ = row_lower
    lp.row_upper_ = row_upper
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.asarray(A.indptr, dtype=np.int64)
    lp.a_matrix_.index_ = np.asarray(A.indices, dtype=np.int64)
    lp.a_matrix_.value_ = np.asarray(A.data, dtype=np.float64)
    return lp, active, cv_e, cell_e, nedge, int(A.nnz)


def run_highs_feasibility(highspy, lp, nedge: int):
    h = highspy.Highs()
    h.setOptionValue("solver", "simplex")
    h.setOptionValue("presolve", "on")
    h.setOptionValue("output_flag", True)
    h.setOptionValue("primal_feasibility_tolerance", 1.0e-8)
    h.setOptionValue("dual_feasibility_tolerance", 1.0e-8)
    if h.passModel(lp) == highspy.HighsStatus.kError:
        raise GateError("highspy_passModel_error")
    t0 = time.perf_counter()
    run_status = h.run()
    wall = time.perf_counter() - t0
    if run_status == highspy.HighsStatus.kError:
        raise GateError("highspy_run_error")
    model_status = h.getModelStatus()
    model_text = h.modelStatusToString(model_status)
    if model_status != highspy.HighsModelStatus.kOptimal:
        raise GateError("highspy_min_unserved_not_optimal:" + model_text)
    sol = np.asarray(list(h.getSolution().col_value), dtype=np.float64)
    info = h.getInfo()
    x = sol[:nedge].copy()
    u = sol[nedge:].copy()
    obj = float(h.getObjectiveValue())
    telemetry = {
        "model_status": model_text,
        "wall_time_s": float(wall),
        "objective_minimum_unserved_mass_kg": obj,
        "simplex_iterations": int(getattr(info, "simplex_iteration_count", -1)),
        "ipm_iterations": int(getattr(info, "ipm_iteration_count", -1)),
    }
    try:
        h.releaseMemory()
    except Exception:
        pass
    return x, u, telemetry


def self_test() -> None:
    assert GRID == (15, 50, 50)
    assert NCVTOTAL == 215600
    assert NCELL == 37500
    assert MILESTONE.endswith("O3-R4")
    assert len(PARENT_O3R3_COMMIT) == 40
    # Important semantic assertion: O3-R3's direct-slack screen is not treated as an infeasibility proof.
    assert EXPECTED_DIRECT_NO_SLACK_CVS > 0
    print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R4 exact frozen-E2 feasibility audit structural self-test: PASS")


def solver_self_test() -> None:
    import highspy
    from scipy.sparse import coo_matrix
    # Tiny 2-CV/2-cell flow with coordinated reassignment. Both CVs can be served exactly.
    demand = np.zeros(NCVTOTAL, dtype=np.float64)
    available = np.zeros(NCELL, dtype=np.float64)
    demand[0] = 1.0; demand[1] = 1.0
    available[0] = 1.0; available[1] = 1.0
    e2_cv = np.array([0,0,1,1], dtype=np.int64)
    e2_cell = np.array([0,1,0,1], dtype=np.int64)
    lp, active, cv_e, cell_e, nedge, nnz = build_feasibility_lp(highspy, coo_matrix, e2_cv, e2_cell, demand, available)
    x,u,t = run_highs_feasibility(highspy, lp, nedge)
    assert abs(float(np.sum(u))) <= 1e-8
    assert t["model_status"].lower().startswith("optimal")
    print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R4 native HiGHS feasibility self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, cond: bool, detail: Any = None) -> None:
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    print("=" * 190)
    print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R4 -- EXACT FROZEN-E2 / FIRST-REFRESH-CAPACITY FEASIBILITY AUDIT")
    print("=" * 190)
    print("AUDIT ONLY. THE O3-R3 DIRECT-SLACK SCREEN IS NOT TREATED AS AN INFEASIBILITY PROOF.")
    print("MINIMIZE TOTAL UNSERVED CV MASS ON THE FROZEN E2 GRAPH UNDER FIRST-REFRESH CELL CAPACITIES.")
    print("NO DEPLOYED REASSIGNMENT. NO FLOW REFRESH. NO REPROJECTION. NO SUPPORT EXPANSION. NO PHYSICAL-TIME ADVANCE.")
    print("NO CAPACITY RELAXATION. NO PER-CV MASS RELAXATION. NO CLIPPING. NO GLOBAL RESCALING.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_O3R3_commit", parent == PARENT_O3R3_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))
        o3r3_path = root / O3R3_RUNNER
        o3r2_path = root / O3R2_RUNNER
        o2_path = root / O2_RUNNER
        gate("O3R3_runner_git_blob_exact", o3r3_path.is_file() and git_blob(o3r3_path, root) == O3R3_RUNNER_BLOB, git_blob(o3r3_path, root) if o3r3_path.is_file() else "missing")
        gate("O3R2_runner_git_blob_exact", o3r2_path.is_file() and git_blob(o3r2_path, root) == O3R2_RUNNER_BLOB, git_blob(o3r2_path, root) if o3r2_path.is_file() else "missing")
        gate("O2_runner_git_blob_exact", o2_path.is_file() and git_blob(o2_path, root) == O2_RUNNER_BLOB, git_blob(o2_path, root) if o2_path.is_file() else "missing")

        base = load_module(o3r2_path, "postv16_o3r4_base_o3r2")
        for fn, expected in base.SOURCE_BLOBS.items():
            p = root / fn
            actual = base.git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "O3R3_audit_binding"
        o3r3d = drive / O3R3_REL
        gate("O3R3_output_present", o3r3d.is_dir(), str(o3r3d))
        o3r3manifest = base.verify_manifest(o3r3d, O3R3_MANIFEST)
        gate("O3R3_manifest_exact_6", len(o3r3manifest) == 6, len(o3r3manifest))
        gate("O3R3_manifest_payload_file_set_exact", set(o3r3manifest) == EXPECTED_O3R3_FILES, sorted(o3r3manifest))
        s3 = load_json(o3r3d / O3R3_SUMMARY)
        d3 = load_json(o3r3d / O3R3_DESIGN)
        gate(
            "O3R3_result_exact",
            s3.get("status") == O3R3_STATUS
            and abs(float(s3.get("event_day", float("nan"))) - EVENT_DAY) <= 1e-12
            and int(s3.get("violating_cell_count", -1)) == EXPECTED_VIOLATING_CELLS
            and abs(float(s3.get("maximum_capacity_excess_kg", float("nan"))) - EXPECTED_MAX_EXCESS_KG) <= 1e-8
            and abs(float(s3.get("total_positive_capacity_deficit_kg", float("nan"))) - EXPECTED_TOTAL_DEFICIT_KG) <= 1e-6
            and int(s3.get("residual_only_infeasible_cell_count", -1)) == 0
            and s3.get("all_violating_cells_in_E2_support") is True
            and int(s3.get("affected_CVs_without_any_positive_slack_candidate", -1)) == EXPECTED_DIRECT_NO_SLACK_CVS
            and s3.get("same_H2_reassignment_necessary_conditions_satisfied") is False
            and s3.get("assignment_optimization_executed") is False
            and s3.get("flow_refresh_completed") is False
            and s3.get("physical_time_advanced") is False,
            {
                "violating_cells": s3.get("violating_cell_count"),
                "total_deficit_kg": s3.get("total_positive_capacity_deficit_kg"),
                "direct_no_slack_CVs": s3.get("affected_CVs_without_any_positive_slack_candidate"),
            },
        )
        gate(
            "O3R3_authorizes_exact_feasibility_audit_only",
            d3.get("O3R4_design_or_exact_feasibility_audit_authorized") is True
            and d3.get("O3R4_execution_authorized") is False
            and d3.get("R3R3R4_authorized") is False
            and d3.get("F5_dataset_generation_authorized") is False
            and d3.get("training_authorized") is False,
        )

        stage = "immutable_O2_and_O3R3_state_binding"
        o2d = drive / base.O2_REL
        gate("O2_output_present", o2d.is_dir(), str(o2d))
        o2manifest = base.verify_manifest(o2d, base.O2_MANIFEST)
        gate("O2_manifest_exact_8", len(o2manifest) == 8, len(o2manifest))
        gate("O2_manifest_payload_file_set_exact", set(o2manifest) == set(base.EXPECTED_O2_MANIFEST_FILES), sorted(o2manifest))
        with np.load(o2d / base.O2_STATE, allow_pickle=False) as z:
            event_cv_mass = np.asarray(z["event_CV_component_mass_kg"], dtype=np.float64)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            event_grid_mass_o2 = np.asarray(z["event_grid_component_mass_kg"], dtype=np.float64)
            frozen_residual_o2 = np.asarray(z["frozen_residual_grid_component_mass_kg"], dtype=np.float64)
        with np.load(o3r3d / O3R3_DIAG, allow_pickle=False) as z:
            event_grid_mass = np.asarray(z["event_grid_mass_kg"], dtype=np.float64)
            frozen_residual = np.asarray(z["frozen_residual_grid_mass_kg"], dtype=np.float64)
            first_refresh_capacity = np.asarray(z["first_refresh_capacity_kg"], dtype=np.float64)
            first_refresh_pressure = np.asarray(z["first_refresh_pressure_psi"], dtype=np.float64)

        gate(
            "input_shapes_exact",
            event_cv_mass.shape == (NSL, NCV)
            and e2_cv.shape == (base.EXPECTED_E2_PAIRS,)
            and e2_cell.shape == (base.EXPECTED_E2_PAIRS,)
            and event_grid_mass.shape == GRID
            and frozen_residual.shape == GRID
            and first_refresh_capacity.shape == GRID
            and first_refresh_pressure.shape == GRID,
        )
        gate("O3R3_event_grid_matches_O2", float(np.max(np.abs(event_grid_mass - event_grid_mass_o2))) <= 1e-8, float(np.max(np.abs(event_grid_mass - event_grid_mass_o2))))
        gate("O3R3_residual_matches_O2", float(np.max(np.abs(frozen_residual - frozen_residual_o2))) <= 1e-8, float(np.max(np.abs(frozen_residual - frozen_residual_o2))))

        demand = event_cv_mass.reshape(-1).astype(np.float64)
        residual = frozen_residual.reshape(-1).astype(np.float64)
        cap = first_refresh_capacity.reshape(-1).astype(np.float64)
        available_raw = cap - residual
        cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(np.abs(cap))), 1.0))
        gate("first_refresh_residual_sidecar_feasible", float(np.min(available_raw)) >= -cap_tol, {"minimum_available_kg": float(np.min(available_raw)), "tolerance_kg": cap_tol})
        available = np.maximum(available_raw, 0.0)
        gate("global_capacity_not_limiting", fsum(available) + NUMERICAL_ZERO_KG >= fsum(demand), {"available_mapped_capacity_kg": fsum(available), "CV_demand_kg": fsum(demand)})

        stage = "exact_frozen_E2_minimum_unserved_solve"
        try:
            import highspy
            from scipy.sparse import coo_matrix
        except Exception as exc:
            raise GateError("required_solver_import_failure:" + repr(exc)) from exc

        lp, active_mask, active_cv, active_cell, nedge, nnz = build_feasibility_lp(
            highspy, coo_matrix, e2_cv, e2_cell, demand, available
        )
        gate("frozen_E2_cardinality_preserved", e2_cv.shape[0] == base.EXPECTED_E2_PAIRS, int(e2_cv.shape[0]))
        gate("no_support_expansion_in_feasibility_model", True, {"raw_E2_edges": int(e2_cv.size), "active_exact_zero_pruned_edges": nedge})
        print("[START] Native HiGHS minimum-unserved feasibility solve")
        print("Raw / active E2 edges:", int(e2_cv.size), "/", nedge)
        print("CV rows             :", NCVTOTAL)
        print("Cell rows           :", NCELL)
        print("Matrix nnz          :", nnz)
        print("Total CV demand kg  :", fsum(demand))
        print("Total avail cap kg  :", fsum(available))
        sys.stdout.flush()

        x, u, telemetry = run_highs_feasibility(highspy, lp, nedge)
        del lp
        gc.collect()

        assigned_by_cv = np.bincount(active_cv, weights=x, minlength=NCVTOTAL).astype(np.float64)
        mapped_by_cell = np.bincount(active_cell, weights=x, minlength=NCELL).astype(np.float64)
        cv_eq_linf = float(np.max(np.abs(assigned_by_cv + u - demand)))
        max_cell_excess = float(np.max(mapped_by_cell - available))
        min_x = float(np.min(x)) if x.size else 0.0
        min_u = float(np.min(u)) if u.size else 0.0
        objective_unserved = float(np.sum(u))
        objective_reported = float(telemetry["objective_minimum_unserved_mass_kg"])
        unserved_mask = u > NUMERICAL_ZERO_KG
        unserved_ids = np.flatnonzero(unserved_mask)
        exact_feasible = objective_unserved <= NUMERICAL_ZERO_KG

        gate("solver_objective_matches_unserved_sum", abs(objective_reported - objective_unserved) <= max(1e-6, 1e-10 * max(abs(objective_unserved), 1.0)), {"solver_objective": objective_reported, "sum_u": objective_unserved})
        gate("feasibility_model_CV_equalities", cv_eq_linf <= 1.0e-6, cv_eq_linf)
        gate("feasibility_model_cell_capacities", max_cell_excess <= 1.0e-6, max_cell_excess)
        gate("feasibility_model_nonnegative", min_x >= -1.0e-8 and min_u >= -1.0e-8, {"minimum_x_kg": min_x, "minimum_u_kg": min_u})

        # Audit PASS regardless of feasible/infeasible classification; the LP optimum is the scientific finding.
        unserved_rows = []
        edge_count = np.bincount(e2_cv, minlength=NCVTOTAL)
        for cv in unserved_ids:
            s = int(cv // NCV); n = int(cv % NCV)
            unserved_rows.append({
                "cv_id": int(cv),
                "streamline": s,
                "control_volume": n,
                "demand_kg": float(demand[cv]),
                "minimum_unserved_kg": float(u[cv]),
                "frozen_E2_candidate_edge_count": int(edge_count[cv]),
            })

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "audit_semantics": "exact minimum-unserved LP on frozen E2 graph under O3-R3 first-refresh capacities",
            "O3R3_direct_slack_screen_bound_but_not_used_as_infeasibility_proof": True,
            "raw_E2_edge_count": int(e2_cv.size),
            "active_exact_zero_pruned_E2_edge_count": nedge,
            "CV_count": NCVTOTAL,
            "cell_count": NCELL,
            "total_CV_demand_kg": fsum(demand),
            "total_available_mapped_capacity_kg": fsum(available),
            "minimum_unserved_mass_kg": objective_unserved,
            "unserved_CV_count_above_1e-6_kg": int(unserved_ids.size),
            "exact_frozen_E2_first_refresh_capacity_feasible": bool(exact_feasible),
            "CV_equality_Linf_kg": cv_eq_linf,
            "maximum_cell_capacity_excess_kg": max_cell_excess,
            "solver": "HiGHS native highspy",
            "solver_version": highspy.Highs().version(),
            "solver_telemetry": telemetry,
            "deployment_assignment_executed": False,
            "flow_refresh_executed": False,
            "reprojection_executed": False,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "physical_time_advanced": False,
        }

        if exact_feasible:
            interpretation = (
                "The O3-R3 direct-slack screen was conservative: coordinated redistribution over the existing frozen E2/H2 graph can satisfy every per-CV event mass exactly under the first-refresh pressure capacities. This is only a first-refresh feasibility certificate; it does not establish a self-consistent pressure-assignment fixed point."
            )
            next_milestone = (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R5 — prospective coupled pressure/same-H2 reassignment fixed-point semantics design freeze"
            )
        else:
            interpretation = (
                "Even a fully coordinated redistribution over all frozen E2/H2 edges cannot satisfy the exact per-CV event masses under the first-refresh pressure capacities. The minimum-unserved optimum is therefore an exact graph/ownership infeasibility certificate for the current same-H2 formulation at this pressure state."
            )
            next_milestone = (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R5 — same-time pressure/mapback ownership-coupling incompatibility design review"
            )

        design = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "exact_frozen_E2_first_refresh_capacity_feasible": bool(exact_feasible),
            "minimum_unserved_mass_kg": objective_unserved,
            "scientific_interpretation": interpretation,
            "next_milestone": next_milestone,
            "O3R5_design_only_authorized": True,
            "O3R5_execution_authorized": False,
            "R3R3R4_authorized": False,
            "support_expansion_authorized": False,
            "second_event_refresh_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "prohibited_automatic_repairs": [
                "capacity relaxation", "per-CV mass relaxation", "mass clipping/discarding", "global rescaling",
                "support radius >2", "vertical support", "H2+V1 fallback", "physical-time advance",
                "automatic second refresh", "automatic execution rerun",
            ],
        }

        audit = {
            **summary,
            "O3R3_violating_cell_count": int(s3["violating_cell_count"]),
            "O3R3_total_positive_capacity_deficit_kg": float(s3["total_positive_capacity_deficit_kg"]),
            "O3R3_E2_support_available_mapped_slack_kg": float(s3["E2_support_available_mapped_slack_kg"]),
            "O3R3_affected_CVs_without_current_positive_slack_candidate": int(s3["affected_CVs_without_any_positive_slack_candidate"]),
            "first_refresh_pressure_minmax_psi": [float(np.min(first_refresh_pressure)), float(np.max(first_refresh_pressure))],
            "first_refresh_cell_capacity_minmax_kg": [float(np.min(cap)), float(np.max(cap))],
            "residual_sidecar_minmax_kg": [float(np.min(residual)), float(np.max(residual))],
            "available_mapped_capacity_minmax_kg": [float(np.min(available)), float(np.max(available))],
            "gates": gates,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Summary.json": base.json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Exact_Feasibility_Audit.json": base.json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Unserved_CV_Diagnostics.csv": base.csv_bytes(unserved_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Prospective_Coupling_Design.json": base.json_bytes(design),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Final_Gate_Matrix.csv": base.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        base.immutable_publish(out, files)
        manifest_name = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Artifact_Manifest.csv"
        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != manifest_name:
                rows.append({"file": p.name, "sha256": base.sha256_file(p), "bytes": p.stat().st_size})
        base.immutable_publish(out, {manifest_name: base.csv_bytes(rows)})

        print()
        print("=" * 190)
        print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R4: EXACT FEASIBILITY AUDIT PASS")
        print("=" * 190)
        print("Event day                                  :", EVENT_DAY)
        print("Raw / active frozen E2 edges               :", int(e2_cv.size), "/", nedge)
        print("Total CV demand kg                         :", fsum(demand))
        print("Total available mapped capacity kg         :", fsum(available))
        print("Minimum unserved mass kg                   :", objective_unserved)
        print("Unserved CVs > 1e-6 kg                     :", int(unserved_ids.size))
        print("Exact frozen-E2 first-refresh feasible     :", bool(exact_feasible))
        print("CV equality Linf kg                        :", cv_eq_linf)
        print("Maximum cell capacity excess kg            :", max_cell_excess)
        print("Deployment assignment executed             : False")
        print("Flow refresh / reprojection                : False / False")
        print("Physical-time advance                      : False")
        print("R3-R3-R4                                   : NOT AUTHORIZED")
        print("O3-R5                                      : DESIGN ONLY")
        print("=" * 190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "deployment_assignment_executed": False,
            "flow_refresh_executed": False,
            "reprojection_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = base.json_bytes(report) if "base" in locals() else (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(data)
        print()
        print("=" * 190)
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO SCIENTIFIC FEASIBILITY CLAIM. NO EXECUTION FALLBACK OR RERUN AUTHORIZED.")
        print("=" * 190)
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--solver-self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test(); raise SystemExit(0)
    if args.solver_self_test:
        solver_self_test(); raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
