#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R1"
NAME = "First-Atomic-Step Runtime / Representation-Path Localization"
PASS = "AV4PIVOTP3R1R1_FIRST_ATOMIC_STEP_RUNTIME_REPRESENTATION_LOCALIZATION_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "b91f66f096113685d0f166421ab63cebe31fdf1e"
P3R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py"
P3R1_BLOB = "84076001f40ebcf0825bb8d9bcabe060ed0840d2"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
P3R1_STAGE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_STAGING"
P3R1_DAY365_STATE = "POSTV16_AV4_PIVOT_P3_R1_Day0365_Accepted_Dense_State.npz"
P3R1_DAY365_DIAG = "POSTV16_AV4_PIVOT_P3_R1_Day0365_Exact_Flow_Diagnostic.npz"
P3R1_DAY370_STATE = "POSTV16_AV4_PIVOT_P3_R1_Day0370_Accepted_Dense_State.npz"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_First_Atomic_Step_Runtime_Representation_Localization")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
METRICS = f"{OUT_TOKEN}_First_Atomic_Step_Metrics.csv"
LP_PROBE = f"{OUT_TOKEN}_Bounded_XY1_LP_Probe.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HIGHS_FEAS_TOL = 1.0e-10
HALO_OPT_TOL = 1.0e-6


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


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
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def classify(direct_pass: bool, lp: dict[str, Any]) -> tuple[str, str]:
    if direct_pass:
        return (
            "P3R1_FIRST_ATOMIC_STEP_DIRECT_EDGE_EXACT_ADMISSIBLE_RUNTIME_BOTTLENECK_NOT_TRIGGERED_AT_STEP1_MULTI_STEP_PROFILE_REQUIRED",
            "Profile a short multi-step prefix before changing representation or physics.",
        )
    s1 = lp.get("stage1", {}).get("outcome")
    s2 = lp.get("stage2", {}).get("outcome")
    if s1 == "TIME_LIMIT" or s2 == "TIME_LIMIT":
        return (
            "P3R1_FIRST_ATOMIC_STEP_DIRECT_EDGE_EXACT_REJECTED_XY1_FALLBACK_TRIGGERED_BOUNDED_LP_PROBE_RUNTIME_BOTTLENECK_LOCALIZED",
            "Design a representation/runtime repair that preserves R32/P3-R0 physics and avoids repeated global XY1 solves.",
        )
    if s1 == "SUCCESS" and s2 == "SUCCESS":
        return (
            "P3R1_FIRST_ATOMIC_STEP_DIRECT_EDGE_EXACT_REJECTED_XY1_FALLBACK_REQUIRED_BOUNDED_LP_SOLVES_COMPLETE_REPEATED_GLOBAL_REPAIR_COST_REQUIRES_EXECUTION_REDESIGN",
            "Design a repeated-mapback execution repair; do not change CFL, transport law, support topology, or cadence science.",
        )
    return (
        "P3R1_FIRST_ATOMIC_STEP_DIRECT_EDGE_EXACT_REJECTED_XY1_FALLBACK_PATH_CONFIRMED_ADDITIONAL_REPRESENTATION_DIAGNOSIS_REQUIRED",
        "Use the recorded direct-gate and bounded-LP evidence to design the next diagnostic/repair stage.",
    )


def selftest() -> None:
    c, _ = classify(True, {})
    assert "DIRECT_EDGE_EXACT_ADMISSIBLE" in c
    c, _ = classify(False, {"stage1": {"outcome": "TIME_LIMIT"}})
    assert "RUNTIME_BOTTLENECK_LOCALIZED" in c
    assert PARENT == "b91f66f096113685d0f166421ab63cebe31fdf1e"
    print("POSTV16 AV4 PIVOT P3-R1-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path, lp_time_limit_seconds: float) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    staging = drive / STAGE_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 190, flush=True)
        print("POSTV16-AV4-PIVOT-P3-R1-R1 — FIRST-ATOMIC-STEP RUNTIME / REPRESENTATION-PATH LOCALIZATION", flush=True)
        print("READ-ONLY DIAGNOSTIC. NO TIME ADVANCE. NO STATE COMMIT. NO CADENCE SELECTION. NO PHYSICS CHANGE.", flush=True)
        print("P3-R1 PARTIAL DAY365 STAGING IS DIAGNOSTIC EVIDENCE ONLY, NOT NEW SCIENTIFIC AUTHORITY.", flush=True)
        print("=" * 190, flush=True)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_R1R1_STAGING", not staging.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_P3R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        p3path = root / P3R1
        gate("P3R1_runner_present", p3path.is_file(), str(p3path))
        gate("P3R1_runner_blob_exact", gt(root, "hash-object", str(p3path)) == P3R1_BLOB, gt(root, "hash-object", str(p3path)))

        p3 = load_module(p3path, "p3r1_authority")
        gate("P3R1_parent_exact", p3.PARENT == "c6c7f62911605e78cd466b9700d7c26ef12fb578", p3.PARENT)
        gate("P3R1_nominal_policy_global_CFL", hasattr(p3, "NCV") and p3.NCV == 200)

        # Bind only source modules used to reproduce the exact first P3-R1 candidate.
        for fn, expected in [
            (p3.A2E, p3.A2E_BLOB),
            (p3.R2SRC, p3.R2SRC_BLOB),
            (p3.E37A, p3.E37A_BLOB),
            (p3.SG7A, p3.SG7A_BLOB),
            (p3.SG7D, p3.SG7D_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == expected, gt(root, "hash-object", str(fp)))

        stage = "partial_P3R1_evidence_binding"
        p3stage = drive / P3R1_STAGE_REL
        state_path = p3stage / P3R1_DAY365_STATE
        diag_path = p3stage / P3R1_DAY365_DIAG
        day370_path = p3stage / P3R1_DAY370_STATE
        gate("P3R1_partial_staging_exists", p3stage.is_dir(), str(p3stage))
        gate("P3R1_Day365_state_exists", state_path.is_file(), str(state_path))
        gate("P3R1_Day365_diagnostic_exists", diag_path.is_file(), str(diag_path))
        print("[INFO] Day370 state present:", day370_path.is_file(), flush=True)
        print("[INFO] Day365 state SHA256:", sha(state_path), flush=True)
        print("[INFO] Day365 diagnostic SHA256:", sha(diag_path), flush=True)

        stage = "authoritative_input_binding"
        a2ed = drive / p3.A2E_REL
        a2ep = a2ed / p3.A2E_EPOCH
        a6ed = drive / p3.A6E_REL
        a6ep = a6ed / p3.A6E_STATE
        gate("A2E_epoch_exists", a2ep.is_file(), str(a2ep))
        gate("A2E_epoch_SHA_exact", sha(a2ep) == p3.A2E_EPOCH_SHA, sha(a2ep))
        gate("A6E_state_exists", a6ep.is_file(), str(a6ep))
        gate("A6E_state_SHA_exact", sha(a6ep) == p3.A6E_SHA, sha(a6ep))

        a2e = load_module(root / p3.A2E, "p3r1r1_a2e")
        r2 = load_module(root / p3.R2SRC, "p3r1r1_r2")
        e37a = load_module(root / p3.E37A, "p3r1r1_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1r1_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1r1_sg7d")

        with np.load(a2ep, allow_pickle=False) as z:
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)

        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        with np.load(state_path, allow_pickle=False) as z:
            physical_day = float(np.asarray(z["physical_day"]).reshape(()))
            current_grid_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            current_edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)

        gate("partial_state_day365_exact", abs(physical_day - 365.0) <= 1.0e-12, physical_day)
        gate("partial_state_cartesian_shape", current_grid_mass.shape == p3.GRID, current_grid_mass.shape)
        gate("partial_state_CV_shape", current_cv_mass.shape == (p3.NSL, p3.NCV), current_cv_mass.shape)
        gate("partial_state_edge_shapes", edge_cv.shape == edge_cell.shape == shell.shape == current_edge_mass.shape, edge_cv.shape)
        split_err = float(np.max(np.abs(current_grid_mass - current_rep - current_residual)))
        cv_edge = np.bincount(edge_cv, weights=current_edge_mass, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
        cv_edge_err = float(np.max(np.abs(cv_edge - current_cv_mass)))
        gate("partial_state_split_identity", split_err <= MASS_TOL, split_err)
        gate("partial_state_CV_edge_equality", cv_edge_err <= MASS_TOL, cv_edge_err)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2, op, frozen_pressure, p_ref, p3.NSL, p3.NCV)
        xi_faces = np.linspace(0.0, 1.0, p3.NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S
        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        dtD_cfl = float(sg7a.CFL * (1.0 / p3.NCV) / (float(np.max(u_face)) * max_df + float(sg7a.EPS)))
        dt = float(dtD_cfl * np.min(tau_end_s / DAY_TO_S))
        gate("nominal_dt_reproduced", np.isfinite(dt) and dt > 0.0, dt)

        stage = "first_atomic_candidate_transport"
        t_candidate0 = time.perf_counter()
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)
        theory_flux = np.zeros((p3.NSL, p3.NCV + 1), dtype=np.float64)
        theory_flux[:, 0] = weights_m3_day * rho_ref
        ff_internal = np.asarray(sg7a.fractional_flow(current_cv_sat[:, :-1]), dtype=np.float64)
        theory_flux[:, 1:-1] = weights_m3_day[:, None] * u_face[None, 1:-1] * ff_internal * rho_ref
        ff_out = np.asarray(sg7a.fractional_flow(current_cv_sat[:, -1]), dtype=np.float64)
        theory_flux[:, -1] = weights_m3_day * float(u_face[-1]) * ff_out * rho_ref
        new_cv_mass = current_cv_mass + dt * (theory_flux[:, :-1] - theory_flux[:, 1:])
        new_cv_sat = np.asarray(
            e37a.invert_cv_mass_to_saturation(r2, new_cv_mass, geometry["cv_pressure_mass_coeff"]), dtype=np.float64
        )
        injected = float(np.sum(theory_flux[:, 0]) * dt)
        produced = float(np.sum(theory_flux[:, -1]) * dt)
        cv_delta = float(np.sum(new_cv_mass) - np.sum(current_cv_mass))
        cv_source_sink = cv_delta - injected + produced
        candidate_transport_s = time.perf_counter() - t_candidate0

        gate("candidate_CV_nonnegative", float(np.min(new_cv_mass)) >= -MASS_TOL, float(np.min(new_cv_mass)))
        gate("candidate_CV_saturation_bounds",
             float(np.min(new_cv_sat)) >= p3.BACKGROUND - SAT_TOL and float(np.max(new_cv_sat)) <= p3.MAX_SAT + SAT_TOL,
             [float(np.min(new_cv_sat)), float(np.max(new_cv_sat))])
        gate("candidate_CV_source_sink", abs(cv_source_sink) <= max(MASS_TOL, REL_TOL * max(abs(injected), 1.0)), cv_source_sink)

        stage = "first_atomic_candidate_mapback"
        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)

        old_sub_sat = current_cv_sat.reshape(-1)[geom_cv_id]
        new_sub_sat = new_cv_sat.reshape(-1)[geom_cv_id]
        old_sub_sg = np.clip(old_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        new_sub_sg = np.clip(new_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        rho_old = np.asarray(r2.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
        rho_new = np.asarray(r2.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
        sub_delta = sub_pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)
        sub_to_cv_error = float(np.sum(sub_delta) - cv_delta)
        gate("candidate_subsegment_delta_closure", abs(sub_to_cv_error) <= MASS_TOL, sub_to_cv_error)
        delta_grid = np.bincount(flat_cell, weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
        direct_target_rep = current_rep + delta_grid

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        rep_capacity = cart_capacity - current_residual
        cart_cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cart_capacity)), 1.0))
        rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)
        gate("represented_capacity_nonnegative", float(np.min(rep_capacity)) >= -cart_cap_tol, float(np.min(rep_capacity)))

        # Map every physical subsegment delta directly onto its saved exact-support edge.
        edge_keys = edge_cv * p3.NCELL + edge_cell
        key_to_edge = {int(k): i for i, k in enumerate(edge_keys.tolist())}
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * p3.NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_keys = sub_cv * p3.NCELL + sub_cell
        missing = [int(k) for k in np.unique(sub_keys) if int(k) not in key_to_edge]
        gate("every_subsegment_has_saved_exact_support_edge", len(missing) == 0, len(missing))
        sub_edge_pos = np.asarray([key_to_edge[int(k)] for k in sub_keys.tolist()], dtype=np.int64)
        gate("subsegments_map_only_to_shell0", bool(np.all(shell[sub_edge_pos] == 0)))

        edge_delta = np.bincount(sub_edge_pos, weights=sub_delta, minlength=len(edge_cv))
        candidate_edge = current_edge_mass + edge_delta
        cv_from_edge = np.bincount(edge_cv, weights=candidate_edge, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
        cell_from_edge = np.bincount(edge_cell, weights=candidate_edge, minlength=p3.NCELL).reshape(p3.GRID)

        min_candidate_edge = float(np.min(candidate_edge))
        negative_edge_mask = candidate_edge < -MASS_TOL
        negative_edge_count = int(np.count_nonzero(negative_edge_mask))
        negative_edge_total_deficit = float(np.sum(-candidate_edge[negative_edge_mask])) if negative_edge_count else 0.0
        cv_err = float(np.max(np.abs(cv_from_edge - new_cv_mass)))
        cap_excess_rep = float(np.max(cell_from_edge.reshape(-1) - rep_capacity_flat))
        cell_diff = cell_from_edge - direct_target_rep
        direct_l1 = float(np.sum(np.abs(cell_diff)))
        direct_l1_tol = max(1.0e-5, 1.0e-10 * max(float(np.sum(np.abs(direct_target_rep))), 1.0))
        direct_max_cell_abs = float(np.max(np.abs(cell_diff)))

        direct_checks = {
            "edge_nonnegative": min_candidate_edge >= -MASS_TOL,
            "CV_equality": cv_err <= MASS_TOL,
            "represented_capacity": cap_excess_rep <= cart_cap_tol,
            "direct_target_L1": direct_l1 <= direct_l1_tol,
        }
        direct_pass = bool(all(direct_checks.values()))

        neg_cvs = int(np.unique(edge_cv[negative_edge_mask]).size) if negative_edge_count else 0
        neg_cells = int(np.unique(edge_cell[negative_edge_mask]).size) if negative_edge_count else 0
        cap_mask = cell_from_edge.reshape(-1) - rep_capacity_flat > cart_cap_tol
        cap_cell_count = int(np.count_nonzero(cap_mask))
        shell_count = int(np.count_nonzero(shell > 0))
        exact_count = int(np.count_nonzero(shell == 0))

        print("--- FIRST ATOMIC DIRECT-PATH DIAGNOSIS ---", flush=True)
        print("nominal dt days                    :", dt, flush=True)
        print("min candidate edge mass kg         :", min_candidate_edge, flush=True)
        print("negative edge count (< -MASS_TOL)  :", negative_edge_count, flush=True)
        print("negative edge total deficit kg     :", negative_edge_total_deficit, flush=True)
        print("affected CVs from negative edges   :", neg_cvs, flush=True)
        print("affected cells from negative edges :", neg_cells, flush=True)
        print("CV equality max abs error kg       :", cv_err, flush=True)
        print("represented capacity excess kg     :", cap_excess_rep, flush=True)
        print("capacity-violating cell count      :", cap_cell_count, flush=True)
        print("direct target L1 error kg          :", direct_l1, flush=True)
        print("direct target L1 tolerance kg      :", direct_l1_tol, flush=True)
        print("direct target max cell error kg    :", direct_max_cell_abs, flush=True)
        print("DIRECT_EDGE_EXACT admissible       :", direct_pass, flush=True)
        print("direct checks                      :", direct_checks, flush=True)

        stage = "bounded_XY1_probe"
        lp: dict[str, Any] = {
            "executed": not direct_pass,
            "time_limit_seconds_per_stage": float(lp_time_limit_seconds),
            "support_edge_count": int(len(edge_cv)),
            "exact_edge_count": exact_count,
            "terminal_shell_edge_count": shell_count,
            "CV_equality_count": int(p3.NCVT),
            "Cartesian_cell_count": int(p3.NCELL),
        }

        if not direct_pass:
            nedge = len(edge_cv)
            t_build1 = time.perf_counter()
            Aeq = coo_matrix((np.ones(nedge), (edge_cv, np.arange(nedge))), shape=(p3.NCVT, nedge)).tocsr()
            Acell = coo_matrix((np.ones(nedge), (edge_cell, np.arange(nedge))), shape=(p3.NCELL, nedge)).tocsr()
            beq = new_cv_mass.reshape(-1).copy()
            c1 = (shell > 0).astype(np.float64)
            build1_s = time.perf_counter() - t_build1
            print(f"[LP] Stage1 matrix build: {build1_s:.3f}s | variables={nedge} eq={p3.NCVT} ub={p3.NCELL}", flush=True)
            t1 = time.perf_counter()
            lp1 = linprog(
                c1, A_ub=Acell, b_ub=rep_capacity_flat, A_eq=Aeq, b_eq=beq,
                bounds=(0.0, None), method="highs-ds",
                options={
                    "presolve": True,
                    "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "time_limit": float(lp_time_limit_seconds),
                },
            )
            wall1 = time.perf_counter() - t1
            outcome1 = "SUCCESS" if lp1.success else ("TIME_LIMIT" if int(lp1.status) == 1 and "time" in str(lp1.message).lower() else "NOT_SUCCESS")
            lp["stage1"] = {
                "outcome": outcome1,
                "success": bool(lp1.success),
                "status": int(lp1.status),
                "message": str(lp1.message),
                "wall_seconds": wall1,
                "matrix_build_seconds": build1_s,
                "variables": int(nedge),
                "equalities": int(p3.NCVT),
                "inequalities": int(p3.NCELL),
                "Aeq_nnz": int(Aeq.nnz),
                "Acell_nnz": int(Acell.nnz),
                "objective_terminal_mass_kg": float(lp1.fun) if lp1.success else None,
            }
            print("[LP] Stage1 outcome:", outcome1, "status=", lp1.status, "wall_s=", wall1, flush=True)

            if lp1.success:
                halo_opt = float(lp1.fun)
                t_build2 = time.perf_counter()
                nd = p3.NCELL
                zero_d = csr_matrix((p3.NCELL, nd), dtype=np.float64)
                I = eye(nd, format="csr", dtype=np.float64)
                A_cap = hstack([Acell, zero_d], format="csr")
                A_abs_pos = hstack([Acell, -I], format="csr")
                A_abs_neg = hstack([-Acell, -I], format="csr")
                target = direct_target_rep.reshape(-1)
                halo_row = csr_matrix(c1.reshape(1, -1))
                zero1 = csr_matrix((1, nd), dtype=np.float64)
                A_halo_pos = hstack([halo_row, zero1], format="csr")
                A_halo_neg = hstack([-halo_row, zero1], format="csr")
                b_halo = np.asarray([halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL], dtype=np.float64)
                A_ub = vstack([A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg], format="csr")
                b_ub = np.concatenate([rep_capacity_flat, target, -target, b_halo])
                Aeq2 = hstack([Aeq, csr_matrix((p3.NCVT, nd), dtype=np.float64)], format="csr")
                c2 = np.concatenate([np.zeros(nedge), np.ones(nd)])
                bounds = [(0.0, None)] * (nedge + nd)
                build2_s = time.perf_counter() - t_build2
                print(f"[LP] Stage2 matrix build: {build2_s:.3f}s | variables={nedge+nd} eq={p3.NCVT} ub={3*p3.NCELL+2}", flush=True)
                t2 = time.perf_counter()
                lp2 = linprog(
                    c2, A_ub=A_ub, b_ub=b_ub, A_eq=Aeq2, b_eq=beq,
                    bounds=bounds, method="highs-ds",
                    options={
                        "presolve": True,
                        "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                        "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                        "time_limit": float(lp_time_limit_seconds),
                    },
                )
                wall2 = time.perf_counter() - t2
                outcome2 = "SUCCESS" if lp2.success else ("TIME_LIMIT" if int(lp2.status) == 1 and "time" in str(lp2.message).lower() else "NOT_SUCCESS")
                lp["stage2"] = {
                    "outcome": outcome2,
                    "success": bool(lp2.success),
                    "status": int(lp2.status),
                    "message": str(lp2.message),
                    "wall_seconds": wall2,
                    "matrix_build_seconds": build2_s,
                    "variables": int(nedge + nd),
                    "equalities": int(p3.NCVT),
                    "inequalities": int(3 * p3.NCELL + 2),
                    "Aeq_nnz": int(Aeq2.nnz),
                    "Aub_nnz": int(A_ub.nnz),
                    "objective_cell_L1_kg": float(lp2.fun) if lp2.success else None,
                    "stage1_terminal_mass_kg": halo_opt,
                }
                print("[LP] Stage2 outcome:", outcome2, "status=", lp2.status, "wall_s=", wall2, flush=True)
            else:
                lp["stage2"] = {"outcome": "NOT_EXECUTED_STAGE1_NOT_SUCCESS"}
        else:
            lp["stage1"] = {"outcome": "NOT_EXECUTED_DIRECT_PATH_ADMISSIBLE"}
            lp["stage2"] = {"outcome": "NOT_EXECUTED_DIRECT_PATH_ADMISSIBLE"}

        classification, recommendation = classify(direct_pass, lp)

        stage = "diagnostic_publication"
        staging.mkdir(parents=True, exist_ok=False)
        metrics_row = {
            "physical_day_parent": physical_day,
            "nominal_dt_days": dt,
            "candidate_day_if_committed": physical_day + dt,
            "candidate_transport_wall_seconds": candidate_transport_s,
            "support_edge_count": int(len(edge_cv)),
            "exact_edge_count": exact_count,
            "terminal_shell_edge_count": shell_count,
            "min_candidate_edge_mass_kg": min_candidate_edge,
            "negative_edge_count_below_minus_mass_tol": negative_edge_count,
            "negative_edge_total_deficit_kg": negative_edge_total_deficit,
            "negative_edge_affected_CV_count": neg_cvs,
            "negative_edge_affected_cell_count": neg_cells,
            "CV_equality_max_abs_error_kg": cv_err,
            "represented_capacity_excess_kg": cap_excess_rep,
            "capacity_violating_cell_count": cap_cell_count,
            "direct_target_L1_error_kg": direct_l1,
            "direct_target_L1_tolerance_kg": direct_l1_tol,
            "direct_target_max_cell_abs_error_kg": direct_max_cell_abs,
            "direct_edge_nonnegative_pass": direct_checks["edge_nonnegative"],
            "direct_CV_equality_pass": direct_checks["CV_equality"],
            "direct_represented_capacity_pass": direct_checks["represented_capacity"],
            "direct_target_L1_pass": direct_checks["direct_target_L1"],
            "DIRECT_EDGE_EXACT_admissible": direct_pass,
            "bounded_stage1_outcome": lp.get("stage1", {}).get("outcome"),
            "bounded_stage1_wall_seconds": lp.get("stage1", {}).get("wall_seconds"),
            "bounded_stage2_outcome": lp.get("stage2", {}).get("outcome"),
            "bounded_stage2_wall_seconds": lp.get("stage2", {}).get("wall_seconds"),
        }
        (staging / METRICS).write_bytes(csvb([metrics_row]))
        (staging / LP_PROBE).write_bytes(jb(lp))
        (staging / GATES).write_bytes(csvb(gates))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_P3R1_commit": PARENT,
            "P3R1_runner_git_blob": P3R1_BLOB,
            "P3R1_partial_Day365_state_sha256": sha(state_path),
            "P3R1_partial_Day365_diagnostic_sha256": sha(diag_path),
            "P3R1_partial_Day370_state_present": day370_path.is_file(),
            "partial_P3R1_staging_is_scientific_authority": False,
            "physics_state_mutated": False,
            "physical_time_advanced": False,
            "candidate_committed": False,
            "cadence_selected": False,
            "P4_authorized": False,
            "nominal_CFL_dt_days": dt,
            "steps_per_5_days_ceiling": int(np.ceil(5.0 / dt)),
            "steps_per_135_days_ceiling": int(np.ceil(135.0 / dt)),
            "DIRECT_EDGE_EXACT_admissible_first_step": direct_pass,
            "direct_path_checks": direct_checks,
            "negative_edge_count": negative_edge_count,
            "negative_edge_total_deficit_kg": negative_edge_total_deficit,
            "CV_equality_max_abs_error_kg": cv_err,
            "represented_capacity_excess_kg": cap_excess_rep,
            "direct_target_L1_error_kg": direct_l1,
            "direct_target_L1_tolerance_kg": direct_l1_tol,
            "bounded_XY1_probe": lp,
            "recommended_next_action": recommendation,
            "CFL_change_authorized": False,
            "transport_law_change_authorized": False,
            "XY1_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P3_R1_R2_diagnostic_or_runtime_repair_design_authorized": True,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "diagnosis_complete_for_first_atomic_step": True,
            "scientific_failure_declared": False,
            "P3_R1_prior_manual_termination_is_scientific_failure": False,
            "P3_R1_prior_manual_termination_is_PASS": False,
            "P3_R0_remains_authoritative": True,
            "R32_recurrent_semantics_remain_authoritative": True,
            "P4_authorized": False,
            "cadence_selection_authorized": False,
            "CFL_change_authorized": False,
            "physics_change_authorized": False,
            "support_topology_change_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P3_R1_R2_diagnostic_or_runtime_repair_design_authorized": True,
            "recommended_next_action": recommendation,
        }
        (staging / SUMMARY).write_bytes(jb(summary))
        (staging / DECISION).write_bytes(jb(decision))

        rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (staging / MANIFEST).write_bytes(csvb(rows))
        if out.exists():
            raise GateError("final_output_directory_preexists")
        staging.rename(out)

        print("=" * 190, flush=True)
        print(M, "PASS", flush=True)
        print("Classification                         :", classification, flush=True)
        print("Nominal CFL dt days                    :", dt, flush=True)
        print("Steps / 5 days                         :", int(np.ceil(5.0 / dt)), flush=True)
        print("DIRECT_EDGE_EXACT admissible first step:", direct_pass, flush=True)
        print("Negative edge count                    :", negative_edge_count, flush=True)
        print("Stage1 bounded LP outcome              :", lp.get("stage1", {}).get("outcome"), flush=True)
        print("Stage2 bounded LP outcome              :", lp.get("stage2", {}).get("outcome"), flush=True)
        print("Physics/state mutation                 : False", flush=True)
        print("P4 authorized                          : False", flush=True)
        print("Next                                   : P3-R1-R2 diagnostic/runtime-repair design authorized", flush=True)
        print("=" * 190, flush=True)
        return 0

    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging)
        blocked.mkdir(parents=True, exist_ok=True)
        report = blocked / f"{OUT_TOKEN}_Blocked_Report.json"
        if not report.exists():
            report.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "physics_state_mutated": False,
                "physical_time_advanced": False,
                "cadence_selected": False,
                "P4_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK", flush=True)
        print("Stage:", stage, flush=True)
        print("Exception:", repr(exc), flush=True)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--lp-time-limit-seconds", type=float, default=60.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.lp_time_limit_seconds))
