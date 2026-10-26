#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R1"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R1_CV60424_FROZEN_E2_ACTIVE_CUT_LOCAL_"
    "FEASIBILITY_GEOMETRY_READ_ONLY_AUDIT_PASS_NO_COUPLED_EXECUTION_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R4_COMMIT = "70f19e8678f7dcf0474e0ee0ba1321da6d925f0e"
EVENT_DAY = 413.78677770818403

GRID = (15, 50, 50)
NCELL = 37500
NCV = 200
NCVTOTAL = 215600
EXPECTED_E2 = 3091073
CONTROLLING_CV = 60424
CONTROLLING_STREAMLINE_ZERO_BASED = CONTROLLING_CV // NCV
CONTROLLING_CONTROL_VOLUME_ZERO_BASED = CONTROLLING_CV % NCV
LINE_DEN = 1024
OMEGA_INDICES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
EXPECTED_MIN_UNSERVED = {
    1: 0.05175696318383416,
    2: 0.1038389245968574,
    4: 0.20799761993202992,
    8: 0.41629405650928675,
    16: 0.8328028920959696,
    32: 1.6654824969641595,
    64: 3.3294743306787495,
    128: 6.651868712079249,
    256: 13.273361396728887,
    512: 26.41596704301037,
    1024: 52.24751699612352,
}
MIN_STEP_INDEX = 1
CUT_MATCH_TOL_KG = 2.0e-5
FLOW_POSITIVE_TOL_KG = 1.0e-9
ACTIVE_CELL_SLACK_TOL_KG = 2.0e-5

R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
    "Controlled_Adaptive_Feasibility_Preserving_Stabilized_Coupled_Execution.py"
)
R4_BLOB = "c41cd5c78e7cc2d91e1920e538f1793037961a31"
R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze.py"
)
R3_BLOB = "c118972a991e4ae0ce7200a9f880a73407450b8b"
O3R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_"
    "Exact_Frozen_E2_First_Refresh_Capacity_Feasibility_Audit.py"
)
O3R4_BLOB = "4446ca612d1f6a00472327818aff674d568f9ede"
O2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution.py"
)
O2_BLOB = "2e04f77750add23f9cfe5143119668450201354f"

SOURCE_BLOBS = {
    R4: R4_BLOB,
    R3: R3_BLOB,
    O3R4: O3R4_BLOB,
    O2: O2_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R4_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Recovery_Checkpoints"
R4_FAIL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_SCIENTIFIC_FAIL"
R4_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Scientific_Fail_Report.json"

R2R2_POINTS = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_"
    "Boundary_Audit_Point_Checkpoints"
)

O2_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution"
)
O2_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz"
O2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Artifact_Manifest.csv"

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_"
    "CV60424_FrozenE2_Active_Cut_Local_Feasibility_Geometry_Audit"
)
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Summary.json"
AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Active_Cut_Audit.json"
OMEGA_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Active_Cut_Omega_Sweep.csv"
CUT_CV_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Active_Cut_CVs.csv"
CUT_CELL_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Active_Cut_Cells.csv"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Artifact_Manifest.csv"


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
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def r4_point_names(index: int) -> tuple[str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
        f"Iteration_001_Omega_{index:04d}_of_{LINE_DEN}"
    )
    return stem + "_State.npz", stem + "_Result.json", stem + "_Manifest.csv"


def r2r2_point_names(index: int) -> tuple[str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_"
        f"Omega_{index:04d}_of_{LINE_DEN}"
    )
    return stem + "_State.npz", stem + "_Result.json", stem + "_Manifest.csv"


def flat_to_kji(cell: int) -> tuple[int, int, int]:
    k = int(cell) // (GRID[1] * GRID[2])
    rem = int(cell) % (GRID[1] * GRID[2])
    j = rem // GRID[2]
    i = rem % GRID[2]
    return k, j, i


def residual_min_cut(
    *,
    active_cv: np.ndarray,
    active_cell: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    # Source -> CV residual is positive exactly where unserved mass remains.
    cut_cv = np.asarray(u > 1.0e-6, dtype=bool)
    cut_cell = np.zeros(NCELL, dtype=bool)

    if not cut_cv[CONTROLLING_CV]:
        raise GateError("controlling_CV_not_source_reachable_in_min_cut_reconstruction")

    positive_flow = np.asarray(x > FLOW_POSITIVE_TOL_KG, dtype=bool)
    iterations = 0
    while True:
        iterations += 1
        if iterations > NCVTOTAL + NCELL:
            raise GateError("residual_cut_closure_nontermination")

        # Infinite-forward residual on every active CV->cell edge.
        edge_from_cut_cv = cut_cv[active_cv]
        new_cells = np.zeros(NCELL, dtype=bool)
        if np.any(edge_from_cut_cv):
            new_cells[np.unique(active_cell[edge_from_cut_cv])] = True

        updated_cells = cut_cell | new_cells

        # Positive-flow reverse residual cell->CV.
        edge_from_cut_cell_reverse = updated_cells[active_cell] & positive_flow
        new_cvs = np.zeros(NCVTOTAL, dtype=bool)
        if np.any(edge_from_cut_cell_reverse):
            new_cvs[np.unique(active_cv[edge_from_cut_cell_reverse])] = True

        updated_cvs = cut_cv | new_cvs
        if np.array_equal(updated_cells, cut_cell) and np.array_equal(updated_cvs, cut_cv):
            break
        cut_cell = updated_cells
        cut_cv = updated_cvs

    cut_demand = float(np.sum(demand[cut_cv]))
    cut_capacity = float(np.sum(available[cut_cell]))
    cut_deficit = cut_demand - cut_capacity

    # Any source-reachable cell with positive residual capacity would provide an
    # augmenting path to the sink, contradicting maximum flow.
    mapped = np.bincount(
        active_cell, weights=x, minlength=NCELL
    ).astype(np.float64)
    reachable_cell_slack = available[cut_cell] - mapped[cut_cell]
    max_reachable_slack = (
        float(np.max(reachable_cell_slack)) if reachable_cell_slack.size else 0.0
    )

    return cut_cv, cut_cell, {
        "closure_iterations": int(iterations),
        "cut_CV_count": int(np.count_nonzero(cut_cv)),
        "cut_cell_count": int(np.count_nonzero(cut_cell)),
        "cut_demand_kg": cut_demand,
        "cut_capacity_kg": cut_capacity,
        "cut_deficit_kg": cut_deficit,
        "maximum_source_reachable_cell_residual_capacity_kg": max_reachable_slack,
    }


def self_test() -> None:
    assert CONTROLLING_CV == 60424
    assert CONTROLLING_STREAMLINE_ZERO_BASED == 302
    assert CONTROLLING_CONTROL_VOLUME_ZERO_BASED == 24
    assert OMEGA_INDICES == [1,2,4,8,16,32,64,128,256,512,1024]
    assert len(PARENT_R4_COMMIT) == 40
    print(
        "POSTV16 O3-R6-R4-R1 CV60424 active-cut geometry audit structural self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT
    blocked = drive / BLOCK

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, cond: bool, detail: Any = None):
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    print("=" * 210)
    print(
        MILESTONE
        + " -- CV60424 FROZEN-E2 ACTIVE-CUT / LOCAL FEASIBILITY-GEOMETRY AUDIT"
    )
    print("=" * 210)
    print("READ-ONLY DIAGNOSTIC AUDIT.")
    print("ONE DIAGNOSTIC MINIMUM-UNSERVED LP AT OMEGA=1/1024 TO RECOVER THE OPTIMAL FLOW.")
    print("NO FIVE-STAGE ASSIGNMENT. NO COUPLED CONTINUATION. NO DAMPING EXECUTION.")
    print("NO SUPPORT EXPANSION. NO CAPACITY/CV-MASS RELAXATION. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R4_commit", parent == PARENT_R4_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        r4 = load_module(root / R4, "postv16_o3r6r4r1_r4")
        r3 = load_module(root / R3, "postv16_o3r6r4r1_r3")
        o3r4 = load_module(root / O3R4, "postv16_o3r6r4r1_o3r4")

        import highspy
        from scipy.sparse import coo_matrix

        gate(
            "highspy_version_exact_1_15_1",
            highspy.Highs().version() == "1.15.1",
            highspy.Highs().version(),
        )

        stage = "R4_scientific_fail_binding"
        fail_dir = drive / R4_FAIL
        fail_path = fail_dir / R4_FAIL_REPORT
        gate("R4_fail_report_present", fail_path.is_file(), str(fail_path))
        fail = r3.load_json(fail_path)
        gate(
            "R4_fail_exact",
            fail.get("status") == r4.STATUS_FAIL
            and fail.get("failed_gate") == "no_positive_feasible_omega_at_or_above_1_over_1024"
            and fail.get("failed_stage") == "iteration_001_line_search"
            and int(fail.get("current_iteration", -1)) == 1
            and abs(float(fail.get("detail", {}).get("minimum_omega", -1.0)) - 1.0/1024.0) <= 1.0e-15
            and fail.get("support_domain_changed") is False
            and fail.get("capacity_relaxed") is False
            and fail.get("per_CV_mass_relaxed") is False
            and fail.get("physical_time_advanced") is False
            and fail.get("automatic_rerun_authorized") is False
            and fail.get("O3R7_authorized") is False,
        )

        stage = "immutable_O2_state_binding"
        o2d = drive / O2_REL
        gate("O2_output_present", o2d.is_dir(), str(o2d))
        r3.verify_manifest(o2d, O2_MANIFEST)
        with np.load(o2d / O2_STATE, allow_pickle=False) as z:
            demand = np.asarray(z["event_CV_component_mass_kg"], dtype=np.float64).reshape(-1)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            residual = np.asarray(
                z["frozen_residual_grid_component_mass_kg"], dtype=np.float64
            ).reshape(-1)
        gate(
            "O2_shapes_exact",
            demand.shape == (NCVTOTAL,)
            and e2_cv.shape == (EXPECTED_E2,)
            and e2_cell.shape == (EXPECTED_E2,)
            and residual.shape == (NCELL,),
        )
        gate(
            "controlling_CV_has_positive_demand",
            float(demand[CONTROLLING_CV]) > 0.0,
            float(demand[CONTROLLING_CV]),
        )

        stage = "R4_recovery_checkpoint_binding"
        recovery = drive / R4_RECOVERY
        gate("R4_recovery_root_present", recovery.is_dir(), str(recovery))

        stage_manifests = sorted(
            recovery.glob("lex_stages/iteration_001/stage_*/*_Manifest.csv")
        )
        map_manifests = sorted(
            recovery.glob("physical_maps/iteration_001/*_Manifest.csv")
        )
        line_manifests = sorted(
            recovery.glob("line_search/iteration_001/omega_*/*_Manifest.csv")
        )
        accepted_manifests = sorted(
            recovery.glob("accepted_iterates/iteration_000/*_Manifest.csv")
        )
        gate("R4_five_lex_stage_checkpoints_present", len(stage_manifests) == 5, len(stage_manifests))
        gate("R4_one_physical_map_checkpoint_present", len(map_manifests) == 1, len(map_manifests))
        gate("R4_eleven_line_search_checkpoints_present", len(line_manifests) == 11, len(line_manifests))
        gate("R4_bootstrap_accepted_iterate_present", len(accepted_manifests) == 1, len(accepted_manifests))

        # Load and bind all 11 line-search results and capacities.
        line_results: dict[int, dict[str, Any]] = {}
        capacities: dict[int, np.ndarray] = {}
        availabilities: dict[int, np.ndarray] = {}
        for idx in OMEGA_INDICES:
            d = recovery / "line_search" / "iteration_001" / f"omega_{idx:04d}_of_{LINE_DEN}"
            sn, rn, man = r4.point_names(
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4", 1, idx
            )
            gate(
                f"R4_omega_{idx:04d}_manifest_valid",
                r4.manifest_valid(r3, d, man, {sn, rn}),
            )
            rr = r3.load_json(d / rn)
            with np.load(d / sn, allow_pickle=False) as z:
                cap = np.asarray(z["cell_capacity_kg"], dtype=np.float64).reshape(-1)
                avail = np.asarray(
                    z["available_mapped_capacity_kg"], dtype=np.float64
                ).reshape(-1)
            gate(
                f"R4_omega_{idx:04d}_result_exact",
                int(rr.get("omega_index", -1)) == idx
                and abs(float(rr.get("omega", -1.0)) - idx/LINE_DEN) <= 1.0e-15
                and rr.get("exact_frozen_E2_feasible") is False
                and int(rr.get("unserved_CV_count_above_1e-6_kg", -1)) == 1
                and rr.get("unserved_CV_ids") == [CONTROLLING_CV]
                and abs(
                    float(rr.get("minimum_unserved_mass_kg", -1.0))
                    - EXPECTED_MIN_UNSERVED[idx]
                ) <= 1.0e-9,
            )
            gate(
                f"R4_omega_{idx:04d}_capacity_identity",
                cap.shape == (NCELL,)
                and avail.shape == (NCELL,)
                and float(np.max(np.abs((cap - residual) - avail))) <= 1.0e-8,
                float(np.max(np.abs((cap - residual) - avail))),
            )
            line_results[idx] = rr
            capacities[idx] = cap
            availabilities[idx] = avail

        # Omega=0 is exactly the R2-R2 omega=147/1024 accepted bootstrap point.
        stage = "omega_zero_bootstrap_binding"
        r2dir = (
            drive / R2R2_POINTS
            / f"omega_{r3.FIRST_FEASIBLE_INDEX:04d}_of_{LINE_DEN}"
        )
        r2sn, r2rn, r2man = r2r2_point_names(r3.FIRST_FEASIBLE_INDEX)
        gate(
            "R2R2_bootstrap_manifest_valid",
            r4.manifest_valid(r3, r2dir, r2man, {r2sn, r2rn}),
        )
        r2res = r3.load_json(r2dir / r2rn)
        with np.load(r2dir / r2sn, allow_pickle=False) as z:
            cap0 = np.asarray(z["cell_capacity_kg"], dtype=np.float64).reshape(-1)
        avail0_raw = cap0 - residual
        cap0_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(np.abs(cap0))), 1.0))
        gate(
            "omega_zero_residual_sidecar_feasible",
            float(np.min(avail0_raw)) >= -cap0_tol,
            float(np.min(avail0_raw)),
        )
        avail0 = np.maximum(avail0_raw, 0.0)
        gate(
            "omega_zero_exact_feasible",
            r2res.get("exact_frozen_E2_feasible") is True,
            r2res.get("minimum_unserved_mass_kg"),
        )

        # --------------------------------------------------------------------------------------
        # One diagnostic min-unserved LP at omega=1/1024.
        # --------------------------------------------------------------------------------------
        stage = "minimum_step_exact_flow_reconstruction"
        available_min = availabilities[MIN_STEP_INDEX]
        lp, active_mask, active_cv, active_cell, nedge, nnz = o3r4.build_feasibility_lp(
            highspy, coo_matrix, e2_cv, e2_cell, demand, available_min
        )
        print("[START] diagnostic exact minimum-unserved LP at omega=1/1024")
        print("Raw / active E2 edges:", int(e2_cv.size), "/", int(nedge))
        print("Matrix nnz:", int(nnz))
        sys.stdout.flush()
        x, u, telemetry = o3r4.run_highs_feasibility(highspy, lp, nedge)
        del lp
        gc.collect()

        objective = float(np.sum(u))
        gate(
            "minimum_step_objective_reproduced",
            abs(objective - EXPECTED_MIN_UNSERVED[MIN_STEP_INDEX]) <= 1.0e-6,
            {
                "reconstructed": objective,
                "checkpoint": EXPECTED_MIN_UNSERVED[MIN_STEP_INDEX],
            },
        )
        unserved = np.flatnonzero(u > 1.0e-6)
        gate(
            "minimum_step_unserved_CV_exactly_60424",
            unserved.tolist() == [CONTROLLING_CV],
            unserved.tolist(),
        )

        # --------------------------------------------------------------------------------------
        # Residual-network exact min-cut reconstruction.
        # --------------------------------------------------------------------------------------
        stage = "residual_network_min_cut_reconstruction"
        cut_cv_mask, cut_cell_mask, cut_meta = residual_min_cut(
            active_cv=active_cv,
            active_cell=active_cell,
            x=x,
            u=u,
            demand=demand,
            available=available_min,
        )
        cut_cv_ids = np.flatnonzero(cut_cv_mask).astype(np.int64)
        cut_cell_ids = np.flatnonzero(cut_cell_mask).astype(np.int64)

        gate(
            "CV60424_inside_reconstructed_cut",
            bool(cut_cv_mask[CONTROLLING_CV]),
        )
        gate(
            "minimum_step_cut_deficit_matches_LP",
            abs(float(cut_meta["cut_deficit_kg"]) - objective) <= CUT_MATCH_TOL_KG,
            {
                "cut_deficit_kg": cut_meta["cut_deficit_kg"],
                "LP_objective_kg": objective,
            },
        )
        gate(
            "source_reachable_cut_cells_are_capacity_active",
            float(cut_meta["maximum_source_reachable_cell_residual_capacity_kg"])
                <= ACTIVE_CELL_SLACK_TOL_KG,
            cut_meta["maximum_source_reachable_cell_residual_capacity_kg"],
        )

        cut_demand = float(np.sum(demand[cut_cv_mask]))

        # Evaluate the exact same cut at omega=0 and all 11 stored line points.
        omega_rows: list[dict[str, Any]] = []
        same_cut_controls_all = True

        def append_cut_row(idx: int, omega: float, available: np.ndarray,
                           minimum_unserved: float, feasible: bool):
            nonlocal same_cut_controls_all
            cut_capacity = float(np.sum(available[cut_cell_mask]))
            deficit = cut_demand - cut_capacity
            positive_deficit = max(deficit, 0.0)
            error = positive_deficit - minimum_unserved
            if abs(error) > CUT_MATCH_TOL_KG:
                same_cut_controls_all = False
            omega_rows.append({
                "omega_index": idx,
                "omega": omega,
                "cut_CV_count": int(cut_cv_ids.size),
                "cut_cell_count": int(cut_cell_ids.size),
                "cut_demand_kg": cut_demand,
                "cut_available_capacity_kg": cut_capacity,
                "cut_signed_deficit_kg": deficit,
                "cut_positive_deficit_kg": positive_deficit,
                "checkpoint_minimum_unserved_kg": minimum_unserved,
                "cut_minus_checkpoint_unserved_kg": error,
                "checkpoint_feasible": feasible,
                "same_cut_matches_optimum_within_tolerance":
                    abs(error) <= CUT_MATCH_TOL_KG,
            })

        append_cut_row(
            0, 0.0, avail0,
            float(r2res.get("minimum_unserved_mass_kg", 0.0) or 0.0),
            True,
        )
        for idx in OMEGA_INDICES:
            append_cut_row(
                idx,
                idx / LINE_DEN,
                availabilities[idx],
                float(line_results[idx]["minimum_unserved_mass_kg"]),
                False,
            )

        gate(
            "same_reconstructed_cut_controls_all_11_failed_omega_points",
            same_cut_controls_all,
            max(abs(float(r["cut_minus_checkpoint_unserved_kg"])) for r in omega_rows[1:]),
        )

        base_signed_deficit = float(omega_rows[0]["cut_signed_deficit_kg"])
        gate(
            "same_cut_is_active_at_omega_zero_within_tolerance",
            abs(base_signed_deficit) <= CUT_MATCH_TOL_KG,
            base_signed_deficit,
        )

        # Small-omega first-order slope using omega=1/1024.
        min_row = next(r for r in omega_rows if r["omega_index"] == 1)
        local_slope = (
            float(min_row["cut_positive_deficit_kg"]) / float(min_row["omega"])
        )
        extrapolated_omega_for_1e6 = 1.0e-6 / max(local_slope, 1.0e-300)

        # --------------------------------------------------------------------------------------
        # Cut membership diagnostics.
        # --------------------------------------------------------------------------------------
        stage = "cut_membership_diagnostics"
        # Active support at the minimum failed point.
        direct_edge_mask = (active_cv == CONTROLLING_CV)
        direct_cells = np.unique(active_cell[direct_edge_mask])
        cut_cell_lookup = cut_cell_mask[active_cell]
        cut_cv_lookup = cut_cv_mask[active_cv]

        edges_per_cv = np.bincount(
            active_cv[cut_cell_lookup], minlength=NCVTOTAL
        ).astype(np.int64)
        cut_edges_per_cv = np.bincount(
            active_cv[cut_cell_lookup & cut_cv_lookup], minlength=NCVTOTAL
        ).astype(np.int64)

        cv_rows = []
        for cv in cut_cv_ids:
            cv_rows.append({
                "cv_id": int(cv),
                "streamline_zero_based": int(cv // NCV),
                "control_volume_zero_based": int(cv % NCV),
                "streamline_one_based": int(cv // NCV) + 1,
                "control_volume_one_based": int(cv % NCV) + 1,
                "demand_kg": float(demand[cv]),
                "is_controlling_CV60424": bool(cv == CONTROLLING_CV),
                "active_edges_into_cut_cells": int(edges_per_cv[cv]),
                "active_cut_internal_edges": int(cut_edges_per_cv[cv]),
            })

        # Global CV competition count for each cut cell.
        global_cell_degree = np.bincount(active_cell, minlength=NCELL).astype(np.int64)
        internal_cell_degree = np.bincount(
            active_cell[cut_cv_lookup], minlength=NCELL
        ).astype(np.int64)
        cell_rows = []
        for cell in cut_cell_ids:
            k, j, i = flat_to_kji(int(cell))
            cell_rows.append({
                "flat_cell": int(cell),
                "k_zero_based": k,
                "j_zero_based": j,
                "i_zero_based": i,
                "layer_one_based": k + 1,
                "row_one_based": j + 1,
                "column_one_based": i + 1,
                "immutable_residual_mass_kg": float(residual[cell]),
                "available_capacity_omega0_kg": float(avail0[cell]),
                "available_capacity_omega1over1024_kg":
                    float(available_min[cell]),
                "available_capacity_change_kg":
                    float(available_min[cell] - avail0[cell]),
                "directly_reachable_from_CV60424":
                    bool(np.any(direct_cells == cell)),
                "global_active_CV_edge_degree": int(global_cell_degree[cell]),
                "cut_internal_CV_edge_degree": int(internal_cell_degree[cell]),
            })

        cut_contains_only_60424 = cut_cv_ids.tolist() == [CONTROLLING_CV]
        direct_reachable_cell_count = int(direct_cells.size)

        # Classification.
        if same_cut_controls_all and abs(base_signed_deficit) <= CUT_MATCH_TOL_KG:
            classification = (
                "INVARIANT_ACTIVE_MINIMUM_CUT_AT_OMEGA_ZERO_WITH_IMMEDIATE_"
                "OUTWARD_CAPACITY_LOSS_ALONG_R4_RAW_MAP_DIRECTION"
            )
            implication = (
                "Scalar under-relaxation cannot create a meaningful positive feasible "
                "step along this raw fixed-point direction. The next algorithmic design "
                "must change the update direction while preserving frozen-E2/H2 support "
                "and the original mass/capacity physics."
            )
            next_milestone = (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R2 — "
                "projected / tangent-constrained feasibility-preserving update "
                "semantics design freeze"
            )
            r2_design_authorized = True
        else:
            classification = (
                "LOCALIZED_CV60424_FAILURE_CONFIRMED_BUT_SINGLE_INVARIANT_ACTIVE_CUT_"
                "NOT_CERTIFIED"
            )
            implication = (
                "CV60424 is confirmed as the local bottleneck, but the audit does not "
                "certify one invariant active cut across the stored line-search path. "
                "Further read-only geometry analysis is required before changing the "
                "stabilization operator."
            )
            next_milestone = (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R2 — "
                "additional read-only local feasibility geometry review"
            )
            r2_design_authorized = False

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "classification": classification,
            "controlling_CV_id": CONTROLLING_CV,
            "controlling_streamline_zero_based": CONTROLLING_STREAMLINE_ZERO_BASED,
            "controlling_control_volume_zero_based":
                CONTROLLING_CONTROL_VOLUME_ZERO_BASED,
            "cut_CV_count": int(cut_cv_ids.size),
            "cut_cell_count": int(cut_cell_ids.size),
            "cut_contains_only_CV60424": bool(cut_contains_only_60424),
            "CV60424_direct_reachable_cell_count": direct_reachable_cell_count,
            "omega_zero_cut_signed_deficit_kg": base_signed_deficit,
            "omega_1_over_1024_cut_deficit_kg":
                float(min_row["cut_positive_deficit_kg"]),
            "omega_1_over_1024_checkpoint_minimum_unserved_kg":
                EXPECTED_MIN_UNSERVED[1],
            "local_cut_deficit_slope_kg_per_unit_omega": local_slope,
            "extrapolated_omega_for_1e_minus_6_kg_cut_deficit":
                extrapolated_omega_for_1e6,
            "same_cut_controls_all_11_failed_omega_points":
                bool(same_cut_controls_all),
            "diagnostic_min_unserved_LP_executed": True,
            "five_stage_assignment_executed": False,
            "coupled_continuation_executed": False,
            "damping_execution_executed": False,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "physical_time_advanced": False,
        }

        audit = {
            **summary,
            "minimum_step_solver_telemetry": telemetry,
            "minimum_step_residual_cut": cut_meta,
            "cut_demand_kg": cut_demand,
            "cut_CV_ids": [int(v) for v in cut_cv_ids],
            "cut_cell_ids": [int(v) for v in cut_cell_ids],
            "scientific_implication": implication,
            "gates": gates,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "scientific_implication": implication,
            "next_milestone": next_milestone,
            "O3R6R4R2_design_freeze_authorized": bool(r2_design_authorized),
            "O3R6R4R2_execution_authorized": False,
            "scalar_damping_rerun_authorized": False,
            "sub_1_over_1024_scalar_damping_search_authorized": False,
            "support_expansion_authorized": False,
            "capacity_relaxation_authorized": False,
            "per_CV_mass_relaxation_authorized": False,
            "automatic_R4_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        files = {
            SUMMARY: r3.json_bytes(summary),
            AUDIT: r3.json_bytes(audit),
            OMEGA_CSV: r3.csv_bytes(omega_rows),
            CUT_CV_CSV: r3.csv_bytes(cv_rows),
            CUT_CELL_CSV: r3.csv_bytes(cell_rows),
            DECISION: r3.json_bytes(decision),
            GATES: r3.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        r3.immutable_publish(out, files)
        manifest_rows = [
            {
                "file": p.name,
                "sha256": r3.sha256_file(p),
                "bytes": p.stat().st_size,
            }
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != MANIFEST
        ]
        r3.immutable_publish(out, {MANIFEST: r3.csv_bytes(manifest_rows)})

        print()
        print("=" * 210)
        print(MILESTONE + ": READ-ONLY AUDIT PASS")
        print("=" * 210)
        print("Classification                         :", classification)
        print("Controlling CV                         :", CONTROLLING_CV)
        print("Cut CV count                           :", int(cut_cv_ids.size))
        print("Cut cell count                         :", int(cut_cell_ids.size))
        print("Cut contains only CV60424              :", bool(cut_contains_only_60424))
        print("Omega=0 cut signed deficit kg          :", base_signed_deficit)
        print("Omega=1/1024 cut deficit kg            :", float(min_row["cut_positive_deficit_kg"]))
        print("Local cut-deficit slope kg / omega     :", local_slope)
        print("Same cut controls all 11 failed points :", bool(same_cut_controls_all))
        print("Five-stage assignment executed         : False")
        print("Coupled continuation executed          : False")
        print("Support expansion                      : False")
        print("Physical-time advance                  : False")
        print("R4-R2 design freeze authorized         :", bool(r2_design_authorized))
        print("R4-R2 execution authorized             : False")
        print("O3-R7                                  : NOT AUTHORIZED")
        print("=" * 210)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "read_only_audit": True,
            "diagnostic_min_unserved_LP_may_have_executed":
                stage in {
                    "minimum_step_exact_flow_reconstruction",
                    "residual_network_min_cut_reconstruction",
                    "cut_membership_diagnostics",
                },
            "five_stage_assignment_executed": False,
            "coupled_continuation_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_R4_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
        }
        p = blocked / (
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Blocked_Report.json"
        )
        if not p.exists():
            p.write_bytes(
                (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
            )
        print()
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        print("NO SCIENTIFIC ACTIVE-CUT CLAIM.")
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
