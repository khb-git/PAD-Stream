#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R3"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R3_FIRST_REFRESH_PRESSURE_CAPACITY_INCOMPATIBILITY_"
    "READ_ONLY_AUDIT_AND_PROSPECTIVE_RECONCILIATION_DESIGN_FREEZE_PASS_"
    "NO_FLOW_REFRESH_NO_REPROJECTION_NO_TIME_ADVANCE"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3O3R3_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_O3R2_COMMIT = "ebc57d6a4f6e50d38042703cac59ed0d205519f0"
O3R2_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_O2_Manifest_Cardinality_"
    "Authority_Repair_Same_Time_Flow_Refresh_and_Bounded_Reprojection_Execution.py"
)
O3R2_RUNNER_BLOB = "02e77ac9cf890c8e61f6787045e0f40a90b2ecc9"
O3R2_FAIL_STATUS = (
    "AV4F4R3R3R3R3R3O3R2_SAME_TIME_FLOW_REFRESH_OR_BOUNDED_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_SUPPORT_EXPANSION_NO_SECOND_REFRESH_NO_AUTOMATIC_RERUN"
)
EXPECTED_FAIL_GATE = "O3R2_event_refresh_same_time_local_cell_mass_capacity"
EXPECTED_FAIL_STAGE = "single_same_time_event_flow_refresh"
EXPECTED_MAX_EXCESS_KG = 41.00208069124892

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
O3R2_FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_SCIENTIFIC_FAIL"
O3R2_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R2_Scientific_Fail_Report.json"
OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Pressure_Capacity_Incompatibility_Audit"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_BLOCKED"

GRID = (15, 50, 50)
NCELL = int(np.prod(GRID))
BACKGROUND = 0.20
INJECTED = 0.80
NCVTOTAL = 1078 * 200

class GateError(RuntimeError):
    pass

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def git_text(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, text=True, capture_output=True).stdout.strip()

def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def self_test() -> None:
    assert GRID == (15, 50, 50)
    assert NCELL == 37500
    assert MILESTONE.endswith("O3-R3")
    assert len(PARENT_O3R2_COMMIT) == 40
    print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R3 pressure-capacity audit structural self-test: PASS")

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

    print("=" * 180)
    print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R3 -- READ-ONLY FIRST-REFRESH PRESSURE/CAPACITY INCOMPATIBILITY AUDIT")
    print("=" * 180)
    print("NO FLOW REFRESH COMPLETION. NO DARCY/POLLOCK/TOF REGENERATION. NO REPROJECTION.")
    print("NO ASSIGNMENT OPTIMIZATION. NO SUPPORT EXPANSION. NO SECOND EVENT REFRESH. NO PHYSICAL-TIME ADVANCE.")
    print("THIS MILESTONE ONLY REPRODUCES THE FIRST PRESSURE SOLVE THAT TRIGGERED O3-R2'S CAPACITY FAILURE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_O3R2_commit", parent == PARENT_O3R2_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))
        o3r2_path = root / O3R2_RUNNER
        gate("O3R2_runner_present", o3r2_path.is_file(), str(o3r2_path))
        gate("O3R2_runner_git_blob_exact", git_blob(o3r2_path, root) == O3R2_RUNNER_BLOB, git_blob(o3r2_path, root))

        base = load_module(o3r2_path, "postv16_o3r3_base_o3r2")
        for fn, expected in base.SOURCE_BLOBS.items():
            p = root / fn
            actual = base.git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "O3R2_scientific_fail_binding"
        fail_path = drive / O3R2_FAIL_REL / O3R2_FAIL_REPORT
        gate("O3R2_scientific_fail_report_present", fail_path.is_file(), str(fail_path))
        fail = load_json(fail_path)
        detail = fail.get("detail", {})
        gate(
            "O3R2_scientific_fail_exact",
            fail.get("milestone") == base.MILESTONE
            and fail.get("status") == O3R2_FAIL_STATUS
            and fail.get("failed_stage") == EXPECTED_FAIL_STAGE
            and fail.get("failed_gate") == EXPECTED_FAIL_GATE
            and abs(float(detail.get("maximum_excess_kg", float("nan"))) - EXPECTED_MAX_EXCESS_KG) <= 1e-10
            and fail.get("O2_optimized_H2_assignment_preserved") is True
            and fail.get("O2_assignment_reexecuted") is False
            and fail.get("event_mass_inversion_executed") is True
            and fail.get("event_refresh_executed") is False
            and fail.get("event_reprojection_executed") is False
            and fail.get("physical_time_advanced") is False
            and fail.get("automatic_fallback_authorized") is False
            and fail.get("automatic_rerun_authorized") is False
            and fail.get("R3R3R4_authorized") is False,
            {
                "failed_stage": fail.get("failed_stage"),
                "failed_gate": fail.get("failed_gate"),
                "maximum_excess_kg": detail.get("maximum_excess_kg"),
                "pre_refresh_completion": fail.get("event_refresh_executed") is False,
            },
        )

        stage = "immutable_input_binding"
        o2d = drive / base.O2_REL
        a2d = drive / base.A2E_REL
        gate("O2_output_present", o2d.is_dir(), str(o2d))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        o2manifest = base.verify_manifest(o2d, base.O2_MANIFEST)
        gate("O2_manifest_exact_8", len(o2manifest) == 8, len(o2manifest))
        gate("O2_manifest_payload_file_set_exact", set(o2manifest) == set(base.EXPECTED_O2_MANIFEST_FILES), sorted(o2manifest))
        base.verify_manifest(a2d, base.A2E_MANIFEST)

        with np.load(o2d / base.O2_STATE, allow_pickle=False) as z:
            event_grid_mass = np.asarray(z["event_grid_component_mass_kg"], dtype=np.float64)
            event_mapped_grid = np.asarray(z["event_mapped_grid_mass_kg"], dtype=np.float64)
            frozen_residual_grid = np.asarray(z["frozen_residual_grid_component_mass_kg"], dtype=np.float64)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            e2_mass = np.asarray(z["E2_pair_event_mass_kg"], dtype=np.float64)
            event_day = float(np.asarray(z["event_day"]).reshape(()))
        with np.load(a2d / base.A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}

        parent_pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        grid_pv = np.asarray(epoch["pore_volume_m3"], dtype=np.float64)
        p_ref = float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)
        gate("immutable_grid_shapes_exact", event_grid_mass.shape == GRID and parent_pressure.shape == GRID and grid_pv.shape == GRID)
        gate("event_day_exact", abs(event_day - base.EVENT_DAY) <= 1e-12, event_day)
        gate("O2_grid_split_exact", float(np.max(np.abs(event_mapped_grid + frozen_residual_grid - event_grid_mass))) <= 1e-8)

        stage = "source_helper_binding"
        a2e = load_module(root / base.A2E, "postv16_o3r3_a2e")
        r2 = load_module(root / base.R2, "postv16_o3r3_r2")
        sg2 = load_module(root / base.SG2, "postv16_o3r3_sg2")
        sg3 = load_module(root / base.SG3, "postv16_o3r3_sg3")
        r3r2r1 = load_module(root / base.R3R2R1, "postv16_o3r3_r3r2r1")
        gate(
            "required_read_only_helpers_present",
            all([
                hasattr(a2e, "invert_local_mass"), hasattr(a2e, "local_mass"), hasattr(a2e, "spatial_mobility"),
                hasattr(sg2, "build_directional_permeability"), hasattr(sg2, "build_face_permeabilities"),
                hasattr(sg3, "construct_si_transmissibilities"),
                hasattr(r3r2r1, "build_updated_transmissibilities"),
                hasattr(r3r2r1, "assemble_updated_pressure_system"), hasattr(r3r2r1, "solve_updated_pressure"),
            ]),
        )

        stage = "parent_pressure_mass_inversion_reproduction"
        event_sg = a2e.invert_local_mass(r2, event_grid_mass, parent_pressure, p_ref, grid_pv)
        event_sat = BACKGROUND + np.asarray(event_sg, dtype=np.float64)
        gate("parent_pressure_mass_inversion_reproduced", np.isfinite(event_sat).all() and float(np.min(event_sat)) >= BACKGROUND - 1e-10 and float(np.max(event_sat)) <= INJECTED + 1e-10, [float(np.min(event_sat)), float(np.max(event_sat))])

        stage = "first_refresh_pressure_solve_reproduction"
        permeability_md = np.loadtxt(root / base.PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        mobility = a2e.spatial_mobility(event_sat, grid_nw, grid_no, grid_krw, grid_kro)
        tx, ty, tz, _face_mobility = r3r2r1.build_updated_transmissibilities(sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"])
        A, b, producer_wi = r3r2r1.assemble_updated_pressure_system(sg3, permeability_md, tx, ty, tz, mobility["lambda_total"])
        _pressure_pa, p1, linear_residual = r3r2r1.solve_updated_pressure(sg3, A, b)
        p1 = np.asarray(p1, dtype=np.float64)
        gate("first_refresh_pressure_shape_exact", p1.shape == GRID)
        gate("first_refresh_pressure_linear_residual", float(linear_residual) < float(a2e.PRESSURE_LINEAR_REL_RESIDUAL_MAX), float(linear_residual))

        stage = "pressure_capacity_incompatibility_quantification"
        parent_capacity = np.asarray(a2e.local_mass(r2, np.full(GRID, INJECTED), parent_pressure, p_ref, grid_pv), dtype=np.float64)
        refreshed_capacity = np.asarray(a2e.local_mass(r2, np.full(GRID, INJECTED), p1, p_ref, grid_pv), dtype=np.float64)
        cap_tol = max(1e-8, 1e-12 * max(float(np.max(refreshed_capacity)), 1.0))
        deficit = event_grid_mass - refreshed_capacity
        viol_mask = deficit > cap_tol
        viol_flat = np.flatnonzero(viol_mask.ravel())
        max_excess = float(np.max(deficit))
        gate("O3R2_capacity_failure_reproduced", len(viol_flat) > 0 and abs(max_excess - EXPECTED_MAX_EXCESS_KG) <= 1e-8, {"violating_cells": int(len(viol_flat)), "maximum_excess_kg": max_excess, "tolerance_kg": cap_tol})

        flat_mass = event_grid_mass.ravel()
        flat_mapped = event_mapped_grid.ravel()
        flat_residual = frozen_residual_grid.ravel()
        flat_parent_cap = parent_capacity.ravel()
        flat_cap = refreshed_capacity.ravel()
        flat_p0 = parent_pressure.ravel()
        flat_p1 = p1.ravel()
        flat_sat = event_sat.ravel()
        flat_deficit = deficit.ravel()

        residual_excess = flat_residual - flat_cap
        residual_bad = residual_excess > cap_tol
        mapped_slack = np.maximum(flat_cap - flat_residual - flat_mapped, 0.0)
        e2_support_cells = np.unique(e2_cell)
        violating_in_e2 = np.isin(viol_flat, e2_support_cells)
        deficit_total = float(np.sum(np.maximum(flat_deficit, 0.0)))
        residual_infeasible_count = int(np.count_nonzero(residual_bad))
        residual_infeasible_max = float(np.max(residual_excess)) if residual_infeasible_count else 0.0
        e2_support_slack_total = float(np.sum(mapped_slack[e2_support_cells]))

        # Affected CVs are CVs with positive assigned mass in a violating cell.
        edge_in_viol = np.isin(e2_cell, viol_flat) & (e2_mass > 1e-12)
        affected_cvs = np.unique(e2_cv[edge_in_viol])
        edge_has_slack = mapped_slack[e2_cell] > cap_tol
        cv_positive_slack_edge_count = np.bincount(e2_cv, weights=edge_has_slack.astype(np.int64), minlength=NCVTOTAL)
        affected_cvs_without_any_slack_edge = affected_cvs[cv_positive_slack_edge_count[affected_cvs] == 0]
        candidate_edge_mask = np.isin(e2_cv, affected_cvs)
        candidate_cells = np.unique(e2_cell[candidate_edge_mask]) if affected_cvs.size else np.array([], dtype=np.int64)
        affected_candidate_slack_total = float(np.sum(mapped_slack[candidate_cells])) if candidate_cells.size else 0.0

        cell_rows = []
        for c in viol_flat:
            k, j, i = np.unravel_index(int(c), GRID)
            cell_rows.append({
                "flat_cell": int(c), "k0": int(k), "j0": int(j), "i0": int(i),
                "layer1": int(k+1), "row1": int(j+1), "col1": int(i+1),
                "event_mass_kg": float(flat_mass[c]),
                "mapped_mass_kg": float(flat_mapped[c]),
                "frozen_residual_mass_kg": float(flat_residual[c]),
                "parent_capacity_kg": float(flat_parent_cap[c]),
                "refreshed_capacity_kg": float(flat_cap[c]),
                "capacity_loss_kg": float(flat_parent_cap[c] - flat_cap[c]),
                "capacity_excess_kg": float(flat_deficit[c]),
                "parent_pressure_psi": float(flat_p0[c]),
                "first_refresh_pressure_psi": float(flat_p1[c]),
                "pressure_change_psi": float(flat_p1[c] - flat_p0[c]),
                "event_saturation_parent_pressure": float(flat_sat[c]),
                "residual_only_capacity_excess_kg": float(max(residual_excess[c], 0.0)),
                "mapped_mass_movable_enough_for_local_relief": bool(flat_mapped[c] + cap_tol >= max(flat_deficit[c], 0.0)),
                "cell_in_E2_support": bool(c in set(e2_support_cells.tolist())),
            })

        # Classification is deliberately necessary-condition only; no LP / assignment solve is executed here.
        same_h2_necessary_conditions = (
            residual_infeasible_count == 0
            and bool(np.all(violating_in_e2))
            and e2_support_slack_total + cap_tol >= deficit_total
            and affected_candidate_slack_total + cap_tol >= deficit_total
            and int(affected_cvs_without_any_slack_edge.size) == 0
            and all(bool(r["mapped_mass_movable_enough_for_local_relief"]) for r in cell_rows)
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": event_day,
            "O3R2_scientific_failure_bound": True,
            "failed_gate_reproduced": EXPECTED_FAIL_GATE,
            "first_refresh_pressure_solve_only": True,
            "flow_refresh_completed": False,
            "Darcy_Pollock_TOF_regenerated": False,
            "reprojection_executed": False,
            "assignment_optimization_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "violating_cell_count": int(len(viol_flat)),
            "maximum_capacity_excess_kg": max_excess,
            "total_positive_capacity_deficit_kg": deficit_total,
            "capacity_tolerance_kg": cap_tol,
            "residual_only_infeasible_cell_count": residual_infeasible_count,
            "residual_only_max_capacity_excess_kg": residual_infeasible_max,
            "all_violating_cells_in_E2_support": bool(np.all(violating_in_e2)),
            "E2_support_available_mapped_slack_kg": e2_support_slack_total,
            "affected_CV_count": int(affected_cvs.size),
            "affected_CVs_without_any_positive_slack_candidate": int(affected_cvs_without_any_slack_edge.size),
            "affected_candidate_cell_count": int(candidate_cells.size),
            "affected_candidate_available_mapped_slack_kg": affected_candidate_slack_total,
            "same_H2_reassignment_necessary_conditions_satisfied": bool(same_h2_necessary_conditions),
        }

        design = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "scientific_interpretation": (
                "The immutable O2 event mass is feasible at the parent pressure but becomes locally nonrepresentable "
                "after the first same-time refreshed pressure solve because pressure-dependent gas density lowers one "
                "or more cell mass capacities below the frozen event mass."
            ),
            "prohibited_repairs": [
                "capacity relaxation", "mass clipping/discarding", "global rescaling", "physical-time advance",
                "second event refresh", "support radius >2", "vertical support", "H2+V1 fallback", "automatic rerun",
            ],
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R4 — exact same-H2 pressure-consistent reassignment feasibility audit/design"
                if same_h2_necessary_conditions
                else "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R4 — same-time refresh formulation incompatibility design review"
            ),
            "O3R4_execution_authorized": False,
            "O3R4_design_or_exact_feasibility_audit_authorized": True,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        audit = {
            **summary,
            "pressure_parent_minmax_psi": [float(np.min(parent_pressure)), float(np.max(parent_pressure))],
            "pressure_first_refresh_minmax_psi": [float(np.min(p1)), float(np.max(p1))],
            "pressure_change_minmax_psi": [float(np.min(p1-parent_pressure)), float(np.max(p1-parent_pressure))],
            "capacity_parent_minmax_kg": [float(np.min(parent_capacity)), float(np.max(parent_capacity))],
            "capacity_first_refresh_minmax_kg": [float(np.min(refreshed_capacity)), float(np.max(refreshed_capacity))],
            "gates": gates,
        }

        arrays = {
            "event_grid_mass_kg": event_grid_mass,
            "event_mapped_grid_mass_kg": event_mapped_grid,
            "frozen_residual_grid_mass_kg": frozen_residual_grid,
            "event_saturation_parent_pressure": event_sat,
            "parent_pressure_psi": parent_pressure,
            "first_refresh_pressure_psi": p1,
            "parent_capacity_kg": parent_capacity,
            "first_refresh_capacity_kg": refreshed_capacity,
            "capacity_deficit_kg": deficit,
            "violating_flat_cells": viol_flat.astype(np.int64),
            "affected_cv_ids": affected_cvs.astype(np.int64),
            "affected_candidate_flat_cells": candidate_cells.astype(np.int64),
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Summary.json": base.json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Pressure_Capacity_Audit.json": base.json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Violating_Cell_Diagnostics.csv": base.csv_bytes(cell_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Diagnostic_State.npz": base.deterministic_npz_bytes(arrays),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Prospective_Reconciliation_Design.json": base.json_bytes(design),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Final_Gate_Matrix.csv": base.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        base.immutable_publish(out, files)
        manifest_name = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Artifact_Manifest.csv"
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != manifest_name:
                rows.append({"file": p.name, "sha256": base.sha256_file(p), "bytes": p.stat().st_size})
        base.immutable_publish(out, {manifest_name: base.csv_bytes(rows)})

        print()
        print("=" * 180)
        print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R3: AUDIT PASS")
        print("=" * 180)
        print("Event day                                  :", event_day)
        print("Violating cells                            :", int(len(viol_flat)))
        print("Maximum refreshed-pressure excess kg       :", max_excess)
        print("Total positive refreshed-pressure deficit kg:", deficit_total)
        print("Residual-only infeasible cells             :", residual_infeasible_count)
        print("All violating cells in E2 support          :", bool(np.all(violating_in_e2)))
        print("E2 support mapped slack kg                 :", e2_support_slack_total)
        print("Affected CVs                               :", int(affected_cvs.size))
        print("Affected CVs with no positive-slack edge   :", int(affected_cvs_without_any_slack_edge.size))
        print("Affected-candidate mapped slack kg         :", affected_candidate_slack_total)
        print("Same-H2 necessary conditions               :", bool(same_h2_necessary_conditions))
        print("Flow refresh completed                     : False")
        print("Reprojection executed                      : False")
        print("Physical-time advance                      : False")
        print("R3-R3-R4                                   : NOT AUTHORIZED")
        print("O3-R4                                      : DESIGN / EXACT-FEASIBILITY AUDIT ONLY")
        print("=" * 180)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "flow_refresh_completed": False,
            "reprojection_executed": False,
            "assignment_optimization_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = base.json_bytes(report) if 'base' in locals() else (json.dumps(report, indent=2, sort_keys=True)+"\n").encode()
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R3_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(data)
        print()
        print("=" * 180)
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO EXECUTION FALLBACK OR RERUN AUTHORIZED.")
        print("=" * 180)
        return 2

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()

if __name__ == "__main__":
    args=parse_args()
    if args.self_test:
        self_test(); raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
