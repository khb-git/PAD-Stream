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

M = "POSTV16-AV4-PIVOT-P3-R1-R4-R1"
NAME = "Positive-Halo Stage-2 Restricted-Master / Column-Generation Diagnostic"
PASS = "AV4PIVOTP3R1R4R1_POSITIVE_HALO_STAGE2_COLUMN_GENERATION_DIAGNOSTIC_PASS_NO_AUTHORITATIVE_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R4R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "23385fe23892b93ab936b7f8ebaa721dbff2a097"

P3R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py"
P3R1_BLOB = "84076001f40ebcf0825bb8d9bcabe060ed0840d2"
R31 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"
R31_BLOB = "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a"
R32 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"
R32_BLOB = "435f5d6dcba38de7166e41ba9e081b6ef573edcf"
R4 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R4_Reduced_Stage2_TenStep_Recurrent_Prefix_Certification.py"
R4_BLOB = "b4ef3e9824fae934a7adf799a2666c0ebd5945b6"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R4_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R4_Reduced_Stage2_TenStep_Recurrent_Prefix_Certification"
R4_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R4_Summary.json"
R4_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R4_Decision_Contract.json"
R4_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R4_Step_Audit.csv"
R4_FINAL = "POSTV16_AV4_PIVOT_P3_R1_R4_Shadow_Final_State.npz"
R4_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R4_Artifact_Manifest.csv"
R4_STATUS = "AV4PIVOTP3R1R4_REDUCED_STAGE2_TEN_STEP_RECURRENT_PREFIX_CERTIFICATION_PASS_SHADOW_EXECUTION"
R4_CLASS = "P3R1_TEN_STEP_RECURRENT_PREFIX_NOT_CERTIFIED_REPAIR_PATH_REQUIRES_ADDITIONAL_DIAGNOSIS"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R4_R1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_PositiveHalo_Stage2_ColumnGeneration_Diagnostic")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
STAGE1 = f"{OUT_TOKEN}_Step3_Stage1_Localization.json"
CG = f"{OUT_TOKEN}_Column_Generation_Audit.csv"
RESULT = f"{OUT_TOKEN}_Restricted_Stage2_Result.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HIGHS_FEAS_TOL = 1.0e-10
HALO_OPT_TOL = 1.0e-6
PRICING_TOL = 1.0e-8
POSITIVE_EDGE_TOL = 1.0e-10


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


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    result = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    if not result:
        raise GateError(f"manifest_empty:{filename}")
    return result


def classify(global_certified: bool, cg_rows: list[dict[str, Any]], result: dict[str, Any]) -> tuple[str, str, bool]:
    if global_certified:
        return (
            "P3R1_STEP3_POSITIVE_HALO_STAGE2_GLOBAL_OPTIMUM_CERTIFIED_BY_RESTRICTED_MASTER_AND_DUAL_PRICING_COLUMN_GENERATION_TEN_STEP_REPAIR_IMPLEMENTATION_AUTHORIZED",
            "Implement the positive-halo column-generation Stage-2 path alongside the zero-halo reduced path and rerun the ten-step shadow prefix before any Day370 pilot.",
            True,
        )
    if result.get("restricted_master_success") is True:
        return (
            "P3R1_STEP3_RESTRICTED_MASTER_SOLVED_BUT_GLOBAL_PRICING_NOT_CLOSED_ADDITIONAL_COLUMN_GENERATION_REQUIRED",
            "Continue the bounded column-generation diagnostic from the recorded negative reduced-cost shell columns; do not run the Day370 pilot.",
            False,
        )
    return (
        "P3R1_STEP3_POSITIVE_HALO_STAGE2_RESTRICTED_MASTER_NOT_SOLVED_RUNTIME_SOLVER_DESIGN_REQUIRES_ADDITIONAL_DIAGNOSIS",
        "Use the Stage-1 sparsity and restricted-master diagnostics to refine the positive-halo solver path; keep the full trajectory locked.",
        False,
    )


def selftest() -> None:
    c, _, ok = classify(True, [], {})
    assert "GLOBAL_OPTIMUM_CERTIFIED" in c and ok
    c, _, ok = classify(False, [], {"restricted_master_success": True})
    assert "GLOBAL_PRICING_NOT_CLOSED" in c and not ok
    assert PARENT == "23385fe23892b93ab936b7f8ebaa721dbff2a097"
    print("POSTV16 AV4 PIVOT P3-R1-R4-R1 structural self-test: PASS")


def main(
    project_root: Path,
    drive_root: Path,
    solve_time_limit_seconds: float,
    max_cg_iterations: int,
    column_batch_size: int,
) -> int:
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
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 220, flush=True)
        print("POSTV16-AV4-PIVOT-P3-R1-R4-R1 — POSITIVE-HALO STAGE-2 RESTRICTED-MASTER / COLUMN-GENERATION DIAGNOSTIC", flush=True)
        print("READ-ONLY DIAGNOSTIC. REPRODUCES R4 STEP 3 ONLY. NO AUTHORITATIVE STATE MUTATION OR TIME ADVANCE.", flush=True)
        print("GOAL: PRESERVE THE FULL R31 STAGE-2 LP WHILE ACTIVATING ONLY SHELL COLUMNS NEEDED BY DUAL PRICING.", flush=True)
        print("=" * 220, flush=True)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_STAGING", not staging.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R4_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [(P3R1, P3R1_BLOB), (R31, R31_BLOB), (R32, R32_BLOB), (R4, R4_BLOB)]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        p3 = load_module(root / P3R1, "p3r1_r4r1_authority")

        stage = "R4_authority"
        r4dir = drive / R4_REL
        gate("R4_dir_exists", r4dir.is_dir(), str(r4dir))
        for fn in [R4_SUMMARY, R4_DECISION, R4_AUDIT, R4_FINAL, R4_MANIFEST]:
            gate(f"R4_artifact_present:{fn}", (r4dir / fn).is_file())
        verify_manifest(r4dir, R4_MANIFEST)
        r4sum = js(r4dir / R4_SUMMARY)
        r4dec = js(r4dir / R4_DECISION)
        r4audit = csvr(r4dir / R4_AUDIT)

        gate("R4_status_exact", r4sum.get("status") == R4_STATUS, r4sum.get("status"))
        gate("R4_classification_exact", r4sum.get("classification") == R4_CLASS, r4sum.get("classification"))
        gate("R4_two_steps_certified", int(r4sum.get("certified_prefix_steps")) == 2, r4sum.get("certified_prefix_steps"))
        gate("R4_day370_pilot_locked", r4dec.get("Day365_to_Day370_repaired_pilot_authorized") is False)
        gate("R4_full_rerun_locked", r4dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R4_P4_locked", r4dec.get("P4_authorized") is False)

        step3 = next((row for row in r4audit if row.get("step") == "3"), None)
        gate("R4_step3_audit_present", step3 is not None)
        gate("R4_step3_generic_stage2_timeout",
             step3.get("outcome") == "GENERIC_STAGE2_FALLBACK_NOT_SUCCESS",
             step3.get("outcome"))
        expected_halo = float(step3["stage1_halo_optimum_kg"])
        gate("R4_step3_positive_halo", expected_halo > HALO_OPT_TOL, expected_halo)

        stage = "R4_shadow_state_binding"
        shadow_path = r4dir / R4_FINAL
        with np.load(shadow_path, allow_pickle=False) as z:
            shadow_only = bool(np.asarray(z["shadow_only"]).reshape(()))
            authoritative_state = bool(np.asarray(z["authoritative_state"]).reshape(()))
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

        gate("R4_shadow_state_marked_shadow", shadow_only is True)
        gate("R4_shadow_state_not_authoritative", authoritative_state is False)
        gate("R4_shadow_state_day_exact",
             abs(physical_day - float(r4sum["shadow_prefix_final_day"])) <= 1.0e-12,
             [physical_day, r4sum["shadow_prefix_final_day"]])

        stage = "authoritative_inputs"
        a2ep = drive / p3.A2E_REL / p3.A2E_EPOCH
        a6ep = drive / p3.A6E_REL / p3.A6E_STATE
        gate("A2E_epoch_exists", a2ep.is_file(), str(a2ep))
        gate("A2E_epoch_SHA_exact", sha(a2ep) == p3.A2E_EPOCH_SHA, sha(a2ep))
        gate("A6E_state_exists", a6ep.is_file(), str(a6ep))
        gate("A6E_state_SHA_exact", sha(a6ep) == p3.A6E_SHA, sha(a6ep))
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

        a2e = load_module(root / p3.A2E, "p3r1r4r1_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1r4r1_r2src")
        e37a = load_module(root / p3.E37A, "p3r1r4r1_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1r4r1_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1r4r1_sg7d")

        with np.load(a2ep, allow_pickle=False) as z:
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)
        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2src, op, frozen_pressure, p_ref, p3.NSL, p3.NCV)
        xi_faces = np.linspace(0.0, 1.0, p3.NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S
        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        dtD = float(sg7a.CFL * (1.0 / p3.NCV) / (float(np.max(u_face)) * max_df + float(sg7a.EPS)))
        dt = float(dtD * np.min(tau_end_s / DAY_TO_S))
        gate("nominal_dt_matches_R4",
             abs(dt - float(r4sum["nominal_CFL_dt_days"])) <= 1.0e-14,
             [dt, r4sum["nominal_CFL_dt_days"]])

        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2src, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        rep_capacity = cart_capacity - current_residual
        cart_cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cart_capacity)), 1.0))
        rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)
        gate("represented_capacity_nonnegative", float(np.min(rep_capacity)) >= -cart_cap_tol, float(np.min(rep_capacity)))

        stage = "step3_candidate_reproduction"
        theory_flux = np.zeros((p3.NSL, p3.NCV + 1), dtype=np.float64)
        theory_flux[:, 0] = weights_m3_day * rho_ref
        ff_internal = np.asarray(sg7a.fractional_flow(current_cv_sat[:, :-1]), dtype=np.float64)
        theory_flux[:, 1:-1] = weights_m3_day[:, None] * u_face[None, 1:-1] * ff_internal * rho_ref
        ff_out = np.asarray(sg7a.fractional_flow(current_cv_sat[:, -1]), dtype=np.float64)
        theory_flux[:, -1] = weights_m3_day * float(u_face[-1]) * ff_out * rho_ref
        new_cv_mass = current_cv_mass + dt * (theory_flux[:, :-1] - theory_flux[:, 1:])
        new_cv_sat = np.asarray(
            e37a.invert_cv_mass_to_saturation(r2src, new_cv_mass, geometry["cv_pressure_mass_coeff"]),
            dtype=np.float64,
        )

        old_sub_sat = current_cv_sat.reshape(-1)[geom_cv_id]
        new_sub_sat = new_cv_sat.reshape(-1)[geom_cv_id]
        old_sub_sg = np.clip(old_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        new_sub_sg = np.clip(new_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        rho_old = np.asarray(r2src.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
        rho_new = np.asarray(r2src.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
        sub_delta = sub_pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)
        delta_grid = np.bincount(flat_cell, weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
        direct_target_rep = current_rep + delta_grid

        nedge = len(edge_cv)
        all_idx = np.arange(nedge, dtype=np.int64)
        Aeq_full = coo_matrix(
            (np.ones(nedge, dtype=np.float64), (edge_cv, all_idx)),
            shape=(p3.NCVT, nedge),
        ).tocsr()
        Acell_full = coo_matrix(
            (np.ones(nedge, dtype=np.float64), (edge_cell, all_idx)),
            shape=(p3.NCELL, nedge),
        ).tocsr()
        c1 = (shell > 0).astype(np.float64)

        stage = "step3_full_stage1_localization"
        t1 = time.perf_counter()
        lp1 = linprog(
            c1,
            A_ub=Acell_full,
            b_ub=rep_capacity_flat,
            A_eq=Aeq_full,
            b_eq=new_cv_mass.reshape(-1),
            bounds=(0.0, None),
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                "time_limit": float(solve_time_limit_seconds),
            },
        )
        stage1_wall = time.perf_counter() - t1
        gate("step3_stage1_success", lp1.success, [lp1.status, lp1.message])
        halo_opt = float(lp1.fun)
        gate("step3_halo_optimum_reproduces_R4",
             abs(halo_opt - expected_halo) <= 2.0e-6,
             [halo_opt, expected_halo])

        x1 = np.asarray(lp1.x, dtype=np.float64)
        shell_mask = shell > 0
        exact_mask = shell == 0
        positive_shell = shell_mask & (x1 > POSITIVE_EDGE_TOL)
        positive_shell_positions = np.where(positive_shell)[0]
        exact_positions = np.where(exact_mask)[0]
        shell_positions = np.where(shell_mask)[0]
        positive_shell_mass = float(np.sum(x1[positive_shell_positions]))
        stage1_info = {
            "stage1_success": bool(lp1.success),
            "stage1_status": int(lp1.status),
            "stage1_message": str(lp1.message),
            "stage1_wall_seconds": stage1_wall,
            "halo_optimum_kg": halo_opt,
            "expected_R4_halo_optimum_kg": expected_halo,
            "full_support_edge_count": int(nedge),
            "exact_edge_count": int(exact_positions.size),
            "terminal_shell_edge_count": int(shell_positions.size),
            "positive_terminal_shell_edge_count_above_tol": int(positive_shell_positions.size),
            "positive_terminal_shell_mass_kg": positive_shell_mass,
            "positive_terminal_shell_unique_CV_count": int(np.unique(edge_cv[positive_shell_positions]).size),
            "positive_terminal_shell_unique_cell_count": int(np.unique(edge_cell[positive_shell_positions]).size),
        }
        print("--- STEP3 STAGE1 LOCALIZATION ---", flush=True)
        for k, v in stage1_info.items():
            print(f"{k:58s}: {v}", flush=True)

        stage = "column_generation"
        selected_shell = set(int(x) for x in positive_shell_positions.tolist())
        cg_rows: list[dict[str, Any]] = []
        global_certified = False
        final_lp = None
        final_positions = None
        pricing_validation_error = None
        final_min_omitted_rc = None

        for iteration in range(1, max_cg_iterations + 1):
            selected_positions = np.concatenate([
                exact_positions,
                np.asarray(sorted(selected_shell), dtype=np.int64),
            ])
            selected_positions = np.unique(selected_positions)
            nsel = int(selected_positions.size)

            sel_cv = edge_cv[selected_positions]
            sel_cell = edge_cell[selected_positions]
            sel_shell = shell[selected_positions]
            sel_idx = np.arange(nsel, dtype=np.int64)

            Aeq_x = coo_matrix(
                (np.ones(nsel, dtype=np.float64), (sel_cv, sel_idx)),
                shape=(p3.NCVT, nsel),
            ).tocsr()
            Acell = coo_matrix(
                (np.ones(nsel, dtype=np.float64), (sel_cell, sel_idx)),
                shape=(p3.NCELL, nsel),
            ).tocsr()

            nd = p3.NCELL
            zero_d = csr_matrix((p3.NCELL, nd), dtype=np.float64)
            I = eye(nd, format="csr", dtype=np.float64)
            A_cap = hstack([Acell, zero_d], format="csr")
            A_abs_pos = hstack([Acell, -I], format="csr")
            A_abs_neg = hstack([-Acell, -I], format="csr")
            halo_c = (sel_shell > 0).astype(np.float64)
            halo_row = csr_matrix(halo_c.reshape(1, -1))
            zero1 = csr_matrix((1, nd), dtype=np.float64)
            A_halo_pos = hstack([halo_row, zero1], format="csr")
            A_halo_neg = hstack([-halo_row, zero1], format="csr")
            A_ub = vstack(
                [A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg],
                format="csr",
            )
            target = direct_target_rep.reshape(-1)
            b_halo = np.asarray([halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL], dtype=np.float64)
            b_ub = np.concatenate([rep_capacity_flat, target, -target, b_halo])
            Aeq = hstack(
                [Aeq_x, csr_matrix((p3.NCVT, nd), dtype=np.float64)],
                format="csr",
            )
            c = np.concatenate([np.zeros(nsel, dtype=np.float64), np.ones(nd, dtype=np.float64)])
            bounds = [(0.0, None)] * (nsel + nd)

            ts = time.perf_counter()
            lp2 = linprog(
                c,
                A_ub=A_ub,
                b_ub=b_ub,
                A_eq=Aeq,
                b_eq=new_cv_mass.reshape(-1),
                bounds=bounds,
                method="highs-ds",
                options={
                    "presolve": True,
                    "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "time_limit": float(solve_time_limit_seconds),
                },
            )
            solve_wall = time.perf_counter() - ts

            row = {
                "iteration": iteration,
                "selected_edge_count": nsel,
                "selected_shell_edge_count": int(np.count_nonzero(sel_shell > 0)),
                "restricted_variables": int(nsel + nd),
                "restricted_Aub_nnz": int(A_ub.nnz),
                "solve_success": bool(lp2.success),
                "solve_status": int(lp2.status),
                "solve_message": str(lp2.message),
                "solve_wall_seconds": solve_wall,
                "restricted_objective_L1_kg": float(lp2.fun) if lp2.success else None,
            }

            print(
                f"[CG {iteration}] selected={nsel} shell={row['selected_shell_edge_count']} "
                f"success={lp2.success} status={lp2.status} wall={solve_wall:.3f}s",
                flush=True,
            )

            if not lp2.success:
                cg_rows.append(row)
                final_lp = lp2
                final_positions = selected_positions
                break

            # Validate dual pricing formula on selected x columns against HiGHS lower marginals.
            mu = np.asarray(lp2.ineqlin.marginals, dtype=np.float64)
            lam = np.asarray(lp2.eqlin.marginals, dtype=np.float64)
            lower = np.asarray(lp2.lower.marginals, dtype=np.float64)

            mu_cap = mu[0:p3.NCELL]
            mu_pos = mu[p3.NCELL:2*p3.NCELL]
            mu_neg = mu[2*p3.NCELL:3*p3.NCELL]
            mu_hpos = float(mu[3*p3.NCELL])
            mu_hneg = float(mu[3*p3.NCELL + 1])

            pred_selected = -(
                mu_cap[sel_cell]
                + mu_pos[sel_cell]
                - mu_neg[sel_cell]
                + (sel_shell > 0).astype(np.float64) * (mu_hpos - mu_hneg)
            ) - lam[sel_cv]
            pricing_validation_error = float(np.max(np.abs(pred_selected - lower[:nsel])))
            gate_name = f"column_generation_iteration_{iteration}_pricing_formula_validation"
            gate(gate_name, pricing_validation_error <= 1.0e-7, pricing_validation_error)

            selected_shell_mask_global = np.zeros(nedge, dtype=bool)
            if selected_shell:
                selected_shell_mask_global[np.asarray(sorted(selected_shell), dtype=np.int64)] = True
            omitted_mask = shell_mask & (~selected_shell_mask_global)
            omitted_positions = np.where(omitted_mask)[0]

            if omitted_positions.size:
                ocell = edge_cell[omitted_positions]
                ocv = edge_cv[omitted_positions]
                omitted_rc = -(
                    mu_cap[ocell]
                    + mu_pos[ocell]
                    - mu_neg[ocell]
                    + (mu_hpos - mu_hneg)
                ) - lam[ocv]
                min_rc = float(np.min(omitted_rc))
                negative_idx = np.where(omitted_rc < -PRICING_TOL)[0]
                negative_count = int(negative_idx.size)
            else:
                omitted_rc = np.asarray([], dtype=np.float64)
                min_rc = float("inf")
                negative_idx = np.asarray([], dtype=np.int64)
                negative_count = 0

            final_min_omitted_rc = min_rc
            row.update({
                "pricing_validation_max_abs_error": pricing_validation_error,
                "omitted_shell_edge_count": int(omitted_positions.size),
                "minimum_omitted_shell_reduced_cost": min_rc,
                "negative_reduced_cost_omitted_shell_count": negative_count,
                "pricing_tolerance": PRICING_TOL,
            })

            if negative_count == 0:
                row["global_optimality_certified"] = True
                cg_rows.append(row)
                global_certified = True
                final_lp = lp2
                final_positions = selected_positions
                print(
                    f"[CG {iteration}] GLOBAL OPTIMALITY CERTIFIED: no omitted shell reduced cost < {-PRICING_TOL}",
                    flush=True,
                )
                break

            # Add the most negative omitted shell columns.
            order = negative_idx[np.argsort(omitted_rc[negative_idx])]
            take = order[:column_batch_size]
            add_positions = omitted_positions[take]
            for pos in add_positions.tolist():
                selected_shell.add(int(pos))
            row["columns_added"] = int(add_positions.size)
            row["most_negative_reduced_cost_added"] = float(np.min(omitted_rc[take])) if take.size else None
            cg_rows.append(row)

        stage = "restricted_solution_validation"
        result: dict[str, Any] = {
            "restricted_master_success": bool(final_lp.success) if final_lp is not None else False,
            "global_optimality_certified_by_dual_pricing": global_certified,
            "column_generation_iterations_executed": len(cg_rows),
            "final_selected_edge_count": int(final_positions.size) if final_positions is not None else None,
            "final_selected_shell_edge_count": (
                int(np.count_nonzero(shell[final_positions] > 0))
                if final_positions is not None else None
            ),
            "full_support_edge_count": int(nedge),
            "full_shell_edge_count": int(shell_positions.size),
            "final_restricted_objective_L1_kg": (
                float(final_lp.fun) if final_lp is not None and final_lp.success else None
            ),
            "minimum_omitted_shell_reduced_cost": final_min_omitted_rc,
            "pricing_formula_validation_max_abs_error": pricing_validation_error,
            "pricing_tolerance": PRICING_TOL,
            "stage1_halo_optimum_kg": halo_opt,
            "solution_CV_equality_max_abs_error_kg": None,
            "solution_halo_mass_kg": None,
            "solution_L1_recomputed_kg": None,
            "solution_cartesian_min_mass_kg": None,
            "solution_cartesian_capacity_excess_kg": None,
        }

        if final_lp is not None and final_lp.success and final_positions is not None:
            nsel = int(final_positions.size)
            z = np.asarray(final_lp.x, dtype=np.float64)
            x = z[:nsel]
            d = z[nsel:]
            sel_cv = edge_cv[final_positions]
            sel_cell = edge_cell[final_positions]
            sel_shell = shell[final_positions]
            cv_check = np.bincount(sel_cv, weights=x, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
            cell_rep_flat = np.bincount(sel_cell, weights=x, minlength=p3.NCELL)
            halo_mass = float(np.sum(x[sel_shell > 0]))
            cv_err = float(np.max(np.abs(cv_check - new_cv_mass)))
            l1 = float(np.sum(np.abs(cell_rep_flat - direct_target_rep.reshape(-1))))
            aux_err = float(np.max(np.abs(d - np.abs(cell_rep_flat - direct_target_rep.reshape(-1)))))
            candidate_grid = cell_rep_flat.reshape(p3.GRID) + current_residual
            cart_min = float(np.min(candidate_grid))
            cap_excess = float(np.max(candidate_grid - cart_capacity))

            result.update({
                "solution_CV_equality_max_abs_error_kg": cv_err,
                "solution_halo_mass_kg": halo_mass,
                "solution_halo_optimum_gap_kg": halo_mass - halo_opt,
                "solution_L1_recomputed_kg": l1,
                "solution_auxiliary_max_abs_error_kg": aux_err,
                "solution_cartesian_min_mass_kg": cart_min,
                "solution_cartesian_capacity_excess_kg": cap_excess,
            })

            gate("restricted_solution_CV_equalities", cv_err <= MASS_TOL, cv_err)
            gate("restricted_solution_halo_optimum_preserved",
                 abs(halo_mass - halo_opt) <= 2.0 * HALO_OPT_TOL,
                 [halo_mass, halo_opt])
            gate("restricted_solution_L1_objective_exact",
                 abs(float(final_lp.fun) - l1) <= max(1.0e-5, 1.0e-10 * max(l1, 1.0)),
                 [float(final_lp.fun), l1])
            gate("restricted_solution_auxiliary_exact", aux_err <= 1.0e-5, aux_err)
            gate("restricted_solution_cartesian_nonnegative", cart_min >= -MASS_TOL, cart_min)
            gate("restricted_solution_cartesian_capacity",
                 cap_excess <= cart_cap_tol,
                 [cap_excess, cart_cap_tol])

        classification, recommendation, implementation_auth = classify(global_certified, cg_rows, result)

        stage = "publication"
        staging.mkdir(parents=True, exist_ok=False)
        (staging / STAGE1).write_bytes(jb(stage1_info))
        (staging / CG).write_bytes(csvb(cg_rows))
        (staging / RESULT).write_bytes(jb(result))
        (staging / GATES).write_bytes(csvb(gates))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R4_commit": PARENT,
            "R4_status_bound": R4_STATUS,
            "R4_shadow_state_sha256": sha(shadow_path),
            "R4_shadow_state_used_as_diagnostic_evidence_only": True,
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "step3_parent_shadow_day": physical_day,
            "step3_candidate_day_if_committed": physical_day + dt,
            "stage1_localization": stage1_info,
            "restricted_stage2_result": result,
            "column_generation_iterations": cg_rows,
            "recommended_next_action": recommendation,
            "CFL_change_authorized": False,
            "transport_law_change_authorized": False,
            "support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "positive_halo_column_generation_ten_step_implementation_authorized": bool(implementation_auth),
            "Day365_to_Day370_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R32_recurrent_semantics_remain_authoritative": True,
            "P3_R0_remains_authoritative": True,
            "scientific_failure_declared": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "restricted_master_uses_exact_R31_Stage2_constraints_for_selected_columns": True,
            "dual_pricing_must_certify_all_omitted_shell_columns_before_global_equivalence_claim": True,
            "positive_halo_column_generation_ten_step_implementation_authorized": bool(implementation_auth),
            "frozen_generic_XY1_lexicographic_fallback_must_be_preserved": True,
            "Day365_to_Day370_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
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

        print("=" * 220, flush=True)
        print(M, "PASS", flush=True)
        print("Classification                                  :", classification, flush=True)
        print("Step3 Stage1 halo optimum kg                   :", halo_opt, flush=True)
        print("Stage1 positive shell edge count               :", positive_shell_positions.size, flush=True)
        print("Column-generation iterations                   :", len(cg_rows), flush=True)
        print("Global Stage2 optimum certified by dual pricing:", global_certified, flush=True)
        print("Ten-step implementation authorized             :", implementation_auth, flush=True)
        print("Day370 repaired pilot authorized               : False", flush=True)
        print("Full P3-R1 rerun authorized                    : False", flush=True)
        print("P4 authorized                                  : False", flush=True)
        print("=" * 220, flush=True)
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
                "authoritative_physics_state_mutated": False,
                "authoritative_physical_time_advanced": False,
                "Day365_to_Day370_repaired_pilot_authorized": False,
                "P3_R1_full_rerun_authorized": False,
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
    ap.add_argument("--solve-time-limit-seconds", type=float, default=60.0)
    ap.add_argument("--max-cg-iterations", type=int, default=6)
    ap.add_argument("--column-batch-size", type=int, default=5000)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(
        args.project_root,
        args.drive_root,
        args.solve_time_limit_seconds,
        args.max_cg_iterations,
        args.column_batch_size,
    ))
