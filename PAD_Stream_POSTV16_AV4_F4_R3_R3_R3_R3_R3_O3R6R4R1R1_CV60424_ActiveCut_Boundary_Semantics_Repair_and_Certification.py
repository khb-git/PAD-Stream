#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R1-R1"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R1R1_CV60424_INVARIANT_ACTIVE_CUT_BOUNDARY_"
    "SEMANTICS_REPAIR_AND_CERTIFICATION_PASS_READ_ONLY_NO_COUPLED_EXECUTION_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R1_COMMIT = "6e6c3a02ce41cc3ec043be947e04fd8e083aba11"

R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_"
    "CV60424_FrozenE2_Active_Cut_Local_Feasibility_Geometry_Audit.py"
)
R1_BLOB = "c7f7b33885c36808e9ea5cda929c3fc60dfea31e"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R1_BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_BLOCKED"
R1_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_Blocked_Report.json"

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_"
    "CV60424_ActiveCut_Boundary_Semantics_Repair_and_Certification"
)
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Summary.json"
AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_Audit.json"
OMEGA_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_Omega_Sweep.csv"
CUT_CV_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_CVs.csv"
CUT_CELL_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_Cells.csv"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Artifact_Manifest.csv"

EXPECTED_R1_ZERO_DEFICIT = -0.00032674171234248206
CUT_MATCH_TOL_KG = 2.0e-5


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


def self_test() -> None:
    assert len(PARENT_R1_COMMIT) == 40
    assert len(R1_BLOB) == 40
    assert EXPECTED_R1_ZERO_DEFICIT < 0.0
    print(
        "POSTV16 O3-R6-R4-R1-R1 active-cut boundary-semantics repair structural self-test: PASS"
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

    print("=" * 214)
    print(
        MILESTONE
        + " -- CV60424 ACTIVE-CUT BOUNDARY-SEMANTICS REPAIR AND CERTIFICATION"
    )
    print("=" * 214)
    print("READ-ONLY SUCCESSOR TO IMMUTABLE R4-R1 TECHNICAL BLOCK.")
    print("CORRECTED SEMANTICS: OMEGA=0 MAY HAVE SMALL POSITIVE CUT SLACK; IT NEED NOT BE EXACTLY ACTIVE.")
    print("ONE DIAGNOSTIC MINIMUM-UNSERVED LP AT OMEGA=1/1024 TO RECONSTRUCT THE CUT.")
    print("NO FIVE-STAGE ASSIGNMENT. NO COUPLED CONTINUATION. NO DAMPING EXECUTION.")
    print("NO SUPPORT EXPANSION. NO CAPACITY/CV-MASS RELAXATION. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R1_commit", parent == PARENT_R1_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))

        r1_path = root / R1
        actual_r1_blob = git_blob(r1_path, root) if r1_path.is_file() else "missing"
        gate("R1_runner_blob_exact", actual_r1_blob == R1_BLOB, actual_r1_blob)

        r1 = load_module(r1_path, "postv16_o3r6r4r1r1_r1")
        r3 = load_module(root / r1.R3, "postv16_o3r6r4r1r1_r3")
        o3r4 = load_module(root / r1.O3R4, "postv16_o3r6r4r1r1_o3r4")

        # Bind all source identities used by the blocked R1 audit.
        for fn, expected in r1.SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        import highspy
        from scipy.sparse import coo_matrix

        gate(
            "highspy_version_exact_1_15_1",
            highspy.Highs().version() == "1.15.1",
            highspy.Highs().version(),
        )

        # ----------------------------------------------------------------------------------
        # Bind immutable R1 technical block and prove the only failed gate was the
        # overly strict omega=0 "exactly active" assumption.
        # ----------------------------------------------------------------------------------
        stage = "R1_block_binding"
        r1_block_path = drive / R1_BLOCK / R1_BLOCK_REPORT
        gate("R1_block_report_present", r1_block_path.is_file(), str(r1_block_path))
        b1 = r3.load_json(r1_block_path)
        gate(
            "R1_is_technical_block_only",
            b1.get("status") == r1.STATUS_BLOCK
            and b1.get("failed_stage") == "residual_network_min_cut_reconstruction"
            and b1.get("five_stage_assignment_executed") is False
            and b1.get("coupled_continuation_executed") is False
            and b1.get("support_domain_changed") is False
            and b1.get("physical_time_advanced") is False,
        )
        failed_gate = b1.get("gates", {}).get(
            "same_cut_is_active_at_omega_zero_within_tolerance", {}
        )
        gate(
            "R1_only_semantic_failure_bound",
            failed_gate.get("status") == "FAIL"
            and abs(float(failed_gate.get("detail")) - EXPECTED_R1_ZERO_DEFICIT) <= 1.0e-12
            and b1.get("gates", {}).get(
                "same_reconstructed_cut_controls_all_11_failed_omega_points", {}
            ).get("status") == "PASS"
            and b1.get("gates", {}).get(
                "minimum_step_cut_deficit_matches_LP", {}
            ).get("status") == "PASS"
            and b1.get("gates", {}).get(
                "source_reachable_cut_cells_are_capacity_active", {}
            ).get("status") == "PASS",
            {
                "omega0_cut_signed_deficit_kg": failed_gate.get("detail"),
                "same_cut_max_error_kg": b1.get("gates", {}).get(
                    "same_reconstructed_cut_controls_all_11_failed_omega_points", {}
                ).get("detail"),
            },
        )

        # ----------------------------------------------------------------------------------
        # Rebind immutable R4 fail, O2 graph/masses, R4 checkpoints, and R2-R2 omega=0.
        # ----------------------------------------------------------------------------------
        stage = "immutable_state_binding"
        fail_path = drive / r1.R4_FAIL / r1.R4_FAIL_REPORT
        gate("R4_fail_report_present", fail_path.is_file(), str(fail_path))
        fail = r3.load_json(fail_path)
        gate(
            "R4_fail_exact",
            fail.get("failed_gate") == "no_positive_feasible_omega_at_or_above_1_over_1024"
            and fail.get("failed_stage") == "iteration_001_line_search"
            and fail.get("support_domain_changed") is False
            and fail.get("physical_time_advanced") is False
            and fail.get("automatic_rerun_authorized") is False,
        )

        o2d = drive / r1.O2_REL
        gate("O2_output_present", o2d.is_dir(), str(o2d))
        r3.verify_manifest(o2d, r1.O2_MANIFEST)
        with np.load(o2d / r1.O2_STATE, allow_pickle=False) as z:
            demand = np.asarray(z["event_CV_component_mass_kg"], dtype=np.float64).reshape(-1)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            residual = np.asarray(
                z["frozen_residual_grid_component_mass_kg"], dtype=np.float64
            ).reshape(-1)

        gate(
            "O2_shapes_exact",
            demand.shape == (r1.NCVTOTAL,)
            and e2_cv.shape == (r1.EXPECTED_E2,)
            and e2_cell.shape == (r1.EXPECTED_E2,)
            and residual.shape == (r1.NCELL,),
        )

        recovery = drive / r1.R4_RECOVERY
        gate("R4_recovery_root_present", recovery.is_dir(), str(recovery))

        line_results: dict[int, dict[str, Any]] = {}
        availabilities: dict[int, np.ndarray] = {}

        for idx in r1.OMEGA_INDICES:
            d = (
                recovery / "line_search" / "iteration_001"
                / f"omega_{idx:04d}_of_{r1.LINE_DEN}"
            )
            stem = (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
                f"Iteration_001_Omega_{idx:04d}_of_{r1.LINE_DEN}"
            )
            sn, rn, man = stem + "_State.npz", stem + "_Result.json", stem + "_Manifest.csv"
            gate(
                f"R4_omega_{idx:04d}_manifest_present",
                d.is_dir() and (d / man).is_file(),
                str(d / man),
            )
            # Use generic manifest verification from R3 regardless of helper namespace.
            gate(
                f"R4_omega_{idx:04d}_manifest_exact",
                set(r3.verify_manifest(d, man)) == {sn, rn},
            )
            rr = r3.load_json(d / rn)
            with np.load(d / sn, allow_pickle=False) as z:
                avail = np.asarray(
                    z["available_mapped_capacity_kg"], dtype=np.float64
                ).reshape(-1)

            gate(
                f"R4_omega_{idx:04d}_result_exact",
                int(rr.get("omega_index", -1)) == idx
                and abs(float(rr.get("omega", -1.0)) - idx/r1.LINE_DEN) <= 1.0e-15
                and rr.get("exact_frozen_E2_feasible") is False
                and rr.get("unserved_CV_ids") == [r1.CONTROLLING_CV]
                and abs(
                    float(rr.get("minimum_unserved_mass_kg", -1.0))
                    - r1.EXPECTED_MIN_UNSERVED[idx]
                ) <= 1.0e-9,
            )
            line_results[idx] = rr
            availabilities[idx] = avail

        r2dir = (
            drive / r1.R2R2_POINTS
            / f"omega_{r3.FIRST_FEASIBLE_INDEX:04d}_of_{r1.LINE_DEN}"
        )
        r2sn, r2rn, r2man = r1.r2r2_point_names(r3.FIRST_FEASIBLE_INDEX)
        gate(
            "R2R2_bootstrap_manifest_exact",
            set(r3.verify_manifest(r2dir, r2man)) == {r2sn, r2rn},
        )
        r2res = r3.load_json(r2dir / r2rn)
        with np.load(r2dir / r2sn, allow_pickle=False) as z:
            cap0 = np.asarray(z["cell_capacity_kg"], dtype=np.float64).reshape(-1)
        avail0 = np.maximum(cap0 - residual, 0.0)
        gate(
            "omega_zero_exact_feasible",
            r2res.get("exact_frozen_E2_feasible") is True,
            r2res.get("minimum_unserved_mass_kg"),
        )

        # ----------------------------------------------------------------------------------
        # Reconstruct the exact minimum-step optimal flow and residual min cut.
        # ----------------------------------------------------------------------------------
        stage = "minimum_step_exact_flow_reconstruction"
        available_min = availabilities[1]
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
            abs(objective - r1.EXPECTED_MIN_UNSERVED[1]) <= 1.0e-6,
            {
                "reconstructed": objective,
                "checkpoint": r1.EXPECTED_MIN_UNSERVED[1],
            },
        )
        unserved = np.flatnonzero(u > 1.0e-6)
        gate(
            "minimum_step_unserved_CV_exactly_60424",
            unserved.tolist() == [r1.CONTROLLING_CV],
            unserved.tolist(),
        )

        stage = "residual_network_min_cut_reconstruction"
        cut_cv_mask, cut_cell_mask, cut_meta = r1.residual_min_cut(
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
            bool(cut_cv_mask[r1.CONTROLLING_CV]),
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
                <= r1.ACTIVE_CELL_SLACK_TOL_KG,
            cut_meta["maximum_source_reachable_cell_residual_capacity_kg"],
        )

        cut_demand = float(np.sum(demand[cut_cv_mask]))
        omega_rows: list[dict[str, Any]] = []
        same_cut_controls_all = True

        def append_row(idx: int, omega: float, available: np.ndarray,
                       checkpoint_unserved: float, checkpoint_feasible: bool):
            nonlocal same_cut_controls_all
            cap = float(np.sum(available[cut_cell_mask]))
            signed = cut_demand - cap
            positive = max(signed, 0.0)
            error = positive - checkpoint_unserved
            if idx > 0 and abs(error) > CUT_MATCH_TOL_KG:
                same_cut_controls_all = False
            omega_rows.append({
                "omega_index": idx,
                "omega": omega,
                "cut_CV_count": int(cut_cv_ids.size),
                "cut_cell_count": int(cut_cell_ids.size),
                "cut_demand_kg": cut_demand,
                "cut_available_capacity_kg": cap,
                "cut_signed_deficit_kg": signed,
                "cut_positive_deficit_kg": positive,
                "checkpoint_minimum_unserved_kg": checkpoint_unserved,
                "cut_minus_checkpoint_unserved_kg": error,
                "checkpoint_feasible": checkpoint_feasible,
                "same_cut_matches_failed_optimum_within_tolerance":
                    True if idx == 0 else abs(error) <= CUT_MATCH_TOL_KG,
            })

        append_row(
            0, 0.0, avail0,
            float(r2res.get("minimum_unserved_mass_kg", 0.0) or 0.0),
            True,
        )
        for idx in r1.OMEGA_INDICES:
            append_row(
                idx,
                idx / r1.LINE_DEN,
                availabilities[idx],
                float(line_results[idx]["minimum_unserved_mass_kg"]),
                False,
            )

        gate(
            "same_reconstructed_cut_controls_all_11_failed_omega_points",
            same_cut_controls_all,
            max(
                abs(float(r["cut_minus_checkpoint_unserved_kg"]))
                for r in omega_rows if r["omega_index"] > 0
            ),
        )

        row0 = next(r for r in omega_rows if r["omega_index"] == 0)
        row1 = next(r for r in omega_rows if r["omega_index"] == 1)
        d0 = float(row0["cut_signed_deficit_kg"])
        d1 = float(row1["cut_signed_deficit_kg"])
        omega1 = 1.0 / r1.LINE_DEN

        # Corrected semantics: the cut is feasible with small positive slack at omega=0,
        # and deficient at the first tested positive step. Exact activity at omega=0 is
        # neither required nor claimed.
        gate("same_cut_feasible_at_omega_zero", d0 < 0.0, d0)
        gate("same_cut_infeasible_at_omega_1_over_1024", d1 > 0.0, d1)
        gate(
            "sampled_boundary_bracket_inside_first_1_over_1024_step",
            d0 < 0.0 and d1 > 0.0,
            {
                "lower_omega": 0.0,
                "lower_signed_cut_deficit_kg": d0,
                "upper_omega": omega1,
                "upper_signed_cut_deficit_kg": d1,
            },
        )

        secant_slope = (d1 - d0) / omega1
        secant_root = -d0 / secant_slope
        gate(
            "diagnostic_secant_root_inside_sampled_bracket",
            0.0 < secant_root < omega1,
            secant_root,
        )

        # Membership diagnostics.
        direct_cells = np.unique(active_cell[active_cv == r1.CONTROLLING_CV])
        cut_cell_lookup = cut_cell_mask[active_cell]
        cut_cv_lookup = cut_cv_mask[active_cv]
        edges_per_cv = np.bincount(
            active_cv[cut_cell_lookup], minlength=r1.NCVTOTAL
        ).astype(np.int64)
        cut_edges_per_cv = np.bincount(
            active_cv[cut_cell_lookup & cut_cv_lookup], minlength=r1.NCVTOTAL
        ).astype(np.int64)

        cv_rows = []
        for cv in cut_cv_ids:
            cv_rows.append({
                "cv_id": int(cv),
                "streamline_zero_based": int(cv // r1.NCV),
                "control_volume_zero_based": int(cv % r1.NCV),
                "streamline_one_based": int(cv // r1.NCV) + 1,
                "control_volume_one_based": int(cv % r1.NCV) + 1,
                "demand_kg": float(demand[cv]),
                "is_controlling_CV60424": bool(cv == r1.CONTROLLING_CV),
                "active_edges_into_cut_cells": int(edges_per_cv[cv]),
                "active_cut_internal_edges": int(cut_edges_per_cv[cv]),
            })

        global_cell_degree = np.bincount(
            active_cell, minlength=r1.NCELL
        ).astype(np.int64)
        internal_cell_degree = np.bincount(
            active_cell[cut_cv_lookup], minlength=r1.NCELL
        ).astype(np.int64)

        cell_rows = []
        for cell in cut_cell_ids:
            k, j, i = r1.flat_to_kji(int(cell))
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
                "global_active_CV_edge_degree":
                    int(global_cell_degree[cell]),
                "cut_internal_CV_edge_degree":
                    int(internal_cell_degree[cell]),
            })

        cut_contains_only_60424 = cut_cv_ids.tolist() == [r1.CONTROLLING_CV]

        classification = (
            "INVARIANT_CV60424_MINIMUM_CUT_CONTROLS_ALL_11_FAILED_R4_LINE_SEARCH_"
            "POINTS_WITH_FEASIBLE_TO_INFEASIBLE_BOUNDARY_BRACKETED_INSIDE_FIRST_"
            "1_OVER_1024_STEP"
        )
        implication = (
            "The immutable R4 scalar under-relaxation direction is blocked by one "
            "persistent frozen-E2 capacity cut rooted at CV60424. The same cut has "
            "positive spare capacity at omega=0 and is already deficient at omega=1/1024. "
            "The next stabilization design must change the update direction rather than "
            "search for a smaller scalar damping factor, while preserving frozen-E2/H2 "
            "support and the original mass/capacity physics."
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "controlling_CV_id": r1.CONTROLLING_CV,
            "cut_CV_count": int(cut_cv_ids.size),
            "cut_cell_count": int(cut_cell_ids.size),
            "cut_contains_only_CV60424": bool(cut_contains_only_60424),
            "CV60424_direct_reachable_cell_count": int(direct_cells.size),
            "omega_zero_cut_signed_deficit_kg": d0,
            "omega_zero_cut_spare_capacity_kg": -d0,
            "omega_1_over_1024_cut_signed_deficit_kg": d1,
            "sampled_boundary_lower_omega": 0.0,
            "sampled_boundary_upper_omega": omega1,
            "sampled_boundary_width": omega1,
            "diagnostic_secant_slope_kg_per_unit_omega": secant_slope,
            "diagnostic_secant_root_omega": secant_root,
            "diagnostic_secant_root_percent_full_update": 100.0 * secant_root,
            "secant_root_is_certified_boundary": False,
            "same_cut_controls_all_11_failed_omega_points": True,
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
            "R1_technical_block_preserved": True,
            "R1_failed_semantic_assumption":
                "required exact active cut at omega=0 within 2e-5 kg",
            "R1_observed_omega0_cut_signed_deficit_kg":
                EXPECTED_R1_ZERO_DEFICIT,
            "corrected_semantics":
                "omega=0 is feasible with positive cut slack; omega=1/1024 is infeasible; "
                "the same cut controls all 11 failed positive line-search points",
            "gates": gates,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "scientific_implication": implication,
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R2 — "
                "projected / tangent-constrained feasibility-preserving update "
                "semantics design freeze"
            ),
            "O3R6R4R2_design_freeze_authorized": True,
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

        rows = [
            {
                "file": p.name,
                "sha256": r3.sha256_file(p),
                "bytes": p.stat().st_size,
            }
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != MANIFEST
        ]
        r3.immutable_publish(out, {MANIFEST: r3.csv_bytes(rows)})

        print()
        print("=" * 214)
        print(MILESTONE + ": READ-ONLY CERTIFICATION PASS")
        print("=" * 214)
        print("Classification                       :", classification)
        print("Controlling CV                       :", r1.CONTROLLING_CV)
        print("Cut CV / cell count                  :", int(cut_cv_ids.size), "/", int(cut_cell_ids.size))
        print("Omega=0 cut spare capacity kg        :", -d0)
        print("Omega=1/1024 cut deficit kg          :", d1)
        print("Sampled boundary bracket             :", "(0, 1/1024)")
        print("Diagnostic secant root omega         :", secant_root)
        print("Diagnostic secant root percent       :", 100.0 * secant_root)
        print("Secant root certified boundary       : False")
        print("Same cut controls all 11 failures    :", True)
        print("R4-R2 design freeze authorized       : True")
        print("R4-R2 execution authorized           : False")
        print("O3-R7                                : NOT AUTHORIZED")
        print("=" * 214)
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
            "five_stage_assignment_executed": False,
            "coupled_continuation_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_R4_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
        }
        p = blocked / (
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Blocked_Report.json"
        )
        if not p.exists():
            p.write_bytes(
                (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
            )
        print()
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        print("NO SCIENTIFIC ACTIVE-CUT CERTIFICATION CLAIM.")
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
