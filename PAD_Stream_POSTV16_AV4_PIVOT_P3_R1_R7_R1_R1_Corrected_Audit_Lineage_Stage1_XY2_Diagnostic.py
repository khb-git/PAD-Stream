#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, time
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R7-R1-R1"
NAME = "Corrected Audit-Lineage Stage-1 Infeasibility Localization + Prospective XY2 Feasibility Diagnostic"
PASS = "AV4PIVOTP3R1R7R1R1_CORRECTED_AUDIT_LINEAGE_STAGE1_XY2_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R7R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "1d5dc33646d83a641e24605b40b60c16cf65626c"

R7 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_Day375_to_Day380_ThirdObservation_Pilot.py"
R7_BLOB = "0b42bb4cdd395740742e3784f455a2837f3b7ce2"

R7R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R1_Stage1_Infeasibility_Localization_and_Prospective_XY2_Feasibility_Diagnostic.py"
R7R1_BLOB = "8b3ebe86128003439eb55b836eb40c0f164c5372"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
R7_STAGE_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_STAGING"
R7_BLOCK_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_BLOCKED"
R7_CHECKPOINT = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.npz"
R7_CHECKPOINT_META = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.json"
R7_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R7_Atomic_Step_Audit.csv"
R7_BLOCK_FILE = "POSTV16_AV4_PIVOT_P3_R1_R7_Blocked_Report.json"
R7_BLOCK_STATUS = "AV4PIVOTP3R1R7_TECHNICAL_OR_AUTHORITY_BLOCK"
R7_CHECKPOINT_SHA = "d02fef7ef29d273002c1be613539fc39afac1ff231ad369b5f6571b0adcda83b"
R7_CHECKPOINT_AUDIT_SHA = "77c2a3fc16f4fb56a83d70904780fdf48f5c11226cf65c5d36a5cdce617d16b9"
R7_POST_FAILURE_AUDIT_SHA = "55e875a8e1bb494e14802fe02d84214e499199d7280f4e24f0c364f0a37328af"
R7_PARENT_DAY = 376.9106720614003
R7_ACCEPTED_STEPS = 328

R7R1_BLOCK_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_R1_BLOCKED"
R7R1_BLOCK_FILE = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_Blocked_Report.json"
R7R1_BLOCK_STATUS = "AV4PIVOTP3R1R7R1_TECHNICAL_OR_AUTHORITY_BLOCK"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1"
OUT_REL = BASE / (OUT_TOKEN + "_Corrected_Audit_Lineage_Stage1_Infeasibility_Localization_and_Prospective_XY2_Feasibility_Diagnostic")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
RETRY_TABLE = f"{OUT_TOKEN}_Retry_Capacity_Deficit.csv"
LOCALIZATION = f"{OUT_TOKEN}_Nominal_XY1_Localization.json"
OVERFLOW_CELLS = f"{OUT_TOKEN}_Nominal_Minimum_Capacity_Relaxation_Cells.csv"
XY2_RESULT = f"{OUT_TOKEN}_Prospective_XY2_Result.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HIGHS_FEAS_TOL = 1.0e-10
STRUCTURAL_DEFICIT_TOL = 1.0e-6
MAX_RETRIES = 8
RETRY_FACTOR = 0.5

class GateError(RuntimeError):
    pass

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
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
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")

def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")

def classify(
    checkpoint_feasible: bool,
    all_relaxation_solved: bool,
    all_positive_retry_deficits: bool,
    xy2_nominal_feasible: bool,
    xy2_smallest_feasible: bool,
) -> tuple[str, str, bool, bool]:
    if not checkpoint_feasible:
        return (
            "P3R1_R7_CHECKPOINT_REPRESENTATION_INCONSISTENT_DIAGNOSTIC_STOP",
            "Audit the preserved R7 checkpoint representation before any topology or transport change.",
            False, False,
        )
    if not all_relaxation_solved:
        return (
            "P3R1_R7_XY1_STAGE1_INFEASIBILITY_REPRODUCED_BUT_MINIMUM_CAPACITY_DEFICIT_NOT_FULLY_SOLVED_ADDITIONAL_DIAGNOSTIC_REQUIRED",
            "Preserve the R7 checkpoint and complete the exact XY1 capacity-deficit localization; do not extend transport.",
            False, False,
        )
    if not all_positive_retry_deficits:
        return (
            "P3R1_R7_STAGE1_SOLVER_INFEASIBILITY_NOT_SUPPORTED_BY_POSITIVE_MINIMUM_CAPACITY_DEFICIT_NUMERICAL_SOLVER_DIAGNOSTIC_REQUIRED",
            "Preserve the frozen XY1 topology and investigate Stage1 numerical feasibility before any topology extension.",
            False, False,
        )
    if xy2_nominal_feasible:
        return (
            "P3R1_R7_XY1_POSITIVE_DT_CAPACITY_BOUNDARY_CONFIRMED_PROSPECTIVE_XY2_NOMINAL_STAGE1_FEASIBLE_TOPOLOGY_DESIGN_FREEZE_AUTHORIZED",
            "Freeze the exact prospective XY2 terminal-only same-layer support semantics and lexicographic equivalence before any resumed transport execution.",
            True, False,
        )
    if xy2_smallest_feasible:
        return (
            "P3R1_R7_XY1_POSITIVE_DT_CAPACITY_BOUNDARY_CONFIRMED_PROSPECTIVE_XY2_RETRY_STAGE1_FEASIBLE_TOPOLOGY_DESIGN_FREEZE_AUTHORIZED",
            "Freeze prospective XY2 terminal-only support with the existing adaptive retry semantics before any resumed transport execution.",
            True, False,
        )
    return (
        "P3R1_R7_XY1_POSITIVE_DT_CAPACITY_BOUNDARY_CONFIRMED_PROSPECTIVE_XY2_INSUFFICIENT_DEEPER_TOPOLOGY_DESIGN_REQUIRED",
        "Preserve the R7 checkpoint and diagnose a deeper or alternative support topology; do not resume Day380 transport.",
        False, False,
    )

def selftest() -> None:
    c, _, design, resume = classify(True, True, True, True, True)
    assert "XY2_NOMINAL_STAGE1_FEASIBLE" in c and design and not resume
    c, _, design, resume = classify(True, True, True, False, False)
    assert "XY2_INSUFFICIENT" in c and not design and not resume
    assert PARENT == "1d5dc33646d83a641e24605b40b60c16cf65626c"
    print("POSTV16 AV4 PIVOT P3-R1-R7-R1-R1 structural self-test: PASS")

def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
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
        print("=" * 220)
        print("POSTV16-AV4-PIVOT-P3-R1-R7-R1-R1 — CORRECTED AUDIT-LINEAGE STAGE1 INFEASIBILITY + PROSPECTIVE XY2 FEASIBILITY")
        print("READ-ONLY. NO STATE/TIME ADVANCE. NO TOPOLOGY MUTATION. NO DAY380 AUTHORIZATION.")
        print("=" * 220)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R7R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        r7src = root / R7
        gate("R7_source_present", r7src.is_file(), str(r7src))
        gate("R7_source_blob_exact", gt(root, "hash-object", str(r7src)) == R7_BLOB, gt(root, "hash-object", str(r7src)))
        r7r1src = root / R7R1
        gate("R7R1_source_present", r7r1src.is_file(), str(r7r1src))
        gate("R7R1_source_blob_exact", gt(root, "hash-object", str(r7r1src)) == R7R1_BLOB, gt(root, "hash-object", str(r7r1src)))
        r7 = load_module(r7src, "p3r1_r7r1r1_r7_source")

        stage = "R7_block_checkpoint_authority"
        cp = drive / R7_STAGE_REL / R7_CHECKPOINT
        cpmeta = drive / R7_STAGE_REL / R7_CHECKPOINT_META
        aud = drive / R7_STAGE_REL / R7_AUDIT
        bp = drive / R7_BLOCK_REL / R7_BLOCK_FILE
        gate("R7_checkpoint_exists", cp.is_file(), str(cp))
        gate("R7_checkpoint_meta_exists", cpmeta.is_file(), str(cpmeta))
        gate("R7_step_audit_exists", aud.is_file(), str(aud))
        gate("R7_BLOCK_exists", bp.is_file(), str(bp))
        meta = js(cpmeta)
        b = js(bp)
        gate("R7_checkpoint_SHA_exact", sha(cp) == R7_CHECKPOINT_SHA, sha(cp))
        gate("R7_checkpoint_meta_SHA_exact", meta.get("checkpoint_sha256") == R7_CHECKPOINT_SHA, meta.get("checkpoint_sha256"))
        gate("R7_post_failure_audit_SHA_exact", sha(aud) == R7_POST_FAILURE_AUDIT_SHA, sha(aud))
        gate("R7_checkpoint_meta_pre_failure_audit_SHA_exact",
             meta.get("step_audit_sha256") == R7_CHECKPOINT_AUDIT_SHA,
             meta.get("step_audit_sha256"))
        gate("R7_post_failure_audit_differs_from_checkpoint_snapshot",
             R7_POST_FAILURE_AUDIT_SHA != R7_CHECKPOINT_AUDIT_SHA,
             [R7_CHECKPOINT_AUDIT_SHA, R7_POST_FAILURE_AUDIT_SHA])

        audit_rows = csvr(aud)
        certified_rows = [r for r in audit_rows if r.get("outcome") == "CERTIFIED"]
        rejected_rows = [r for r in audit_rows if r.get("outcome") == "REJECTED_TRIAL"]
        gate("R7_audit_last_certified_step_exact",
             len(certified_rows) > 0 and int(certified_rows[-1].get("accepted_step")) == R7_ACCEPTED_STEPS,
             certified_rows[-1].get("accepted_step") if certified_rows else None)
        parent_rejected = [
            r for r in rejected_rows
            if abs(float(r.get("parent_day")) - R7_PARENT_DAY) <= 1e-12
        ]
        gate("R7_audit_exactly_nine_rejected_trials_at_parent",
             len(parent_rejected) == 9,
             len(parent_rejected))
        gate("R7_audit_retry_indices_0_through_8",
             sorted(int(r.get("retry_index")) for r in parent_rejected) == list(range(9)),
             sorted(int(r.get("retry_index")) for r in parent_rejected))
        gate("R7_audit_all_nine_rejections_are_Stage1_infeasible",
             all("POSITIVE_HALO_STAGE1_NOT_SUCCESS:2:The problem is infeasible." in str(r.get("rejection_reason",""))
                 for r in parent_rejected))
        gate("R7_checkpoint_day_exact", abs(float(meta.get("physical_day")) - R7_PARENT_DAY) <= 1e-12, meta.get("physical_day"))
        gate("R7_checkpoint_steps_exact", int(meta.get("accepted_atomic_steps")) == R7_ACCEPTED_STEPS, meta.get("accepted_atomic_steps"))
        gate("R7_BLOCK_status_exact", b.get("status") == R7_BLOCK_STATUS, b.get("status"))
        gate("R7_BLOCK_no_authoritative_mutation",
             b.get("authoritative_physics_state_mutated") is False and b.get("authoritative_physical_time_advanced") is False)
        exc = str(b.get("exception", ""))
        gate("R7_BLOCK_retry_parent_day_exact", f"atomic_retry_budget_exhausted:{R7_PARENT_DAY}" in exc, exc[:180])
        gate("R7_BLOCK_nine_Stage1_infeasible_retries", exc.count("POSITIVE_HALO_STAGE1_NOT_SUCCESS:2:The problem is infeasible.") == 9,
             exc.count("POSITIVE_HALO_STAGE1_NOT_SUCCESS:2:The problem is infeasible."))

        r7r1bp = drive / R7R1_BLOCK_REL / R7R1_BLOCK_FILE
        gate("R7R1_BLOCK_exists", r7r1bp.is_file(), str(r7r1bp))
        r7r1b = js(r7r1bp)
        gate("R7R1_BLOCK_status_exact", r7r1b.get("status") == R7R1_BLOCK_STATUS, r7r1b.get("status"))
        gate("R7R1_BLOCK_failed_stage_exact", r7r1b.get("failed_stage") == "R7_block_checkpoint_authority", r7r1b.get("failed_stage"))
        gate("R7R1_BLOCK_reason_exact", r7r1b.get("exception") == "GateError('R7_audit_SHA_exact')", r7r1b.get("exception"))
        gate("R7R1_BLOCK_no_authoritative_mutation",
             r7r1b.get("authoritative_physics_state_mutated") is False
             and r7r1b.get("authoritative_physical_time_advanced") is False)

        # Bind exact physics sources needed to reconstruct the next candidate.
        stage = "authoritative_inputs"
        p3 = load_module(root / r7.P3R1, "p3r1_r7r1_p3")
        for fn, expected in [
            (r7.P3R1, r7.P3R1_BLOB),
            (p3.A2E, p3.A2E_BLOB),
            (p3.R2SRC, p3.R2SRC_BLOB),
            (p3.E37A, p3.E37A_BLOB),
            (p3.SG7A, p3.SG7A_BLOB),
            (p3.SG7D, p3.SG7D_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == expected, gt(root, "hash-object", str(fp)))

        a2ep = drive / p3.A2E_REL / p3.A2E_EPOCH
        a6ep = drive / p3.A6E_REL / p3.A6E_STATE
        gate("A2E_epoch_exists", a2ep.is_file(), str(a2ep))
        gate("A2E_epoch_SHA_exact", sha(a2ep) == p3.A2E_EPOCH_SHA, sha(a2ep))
        gate("A6E_state_exists", a6ep.is_file(), str(a6ep))
        gate("A6E_state_SHA_exact", sha(a6ep) == p3.A6E_SHA, sha(a6ep))

        a2e = load_module(root / p3.A2E, "p3r1_r7r1_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1_r7r1_r2src")
        e37a = load_module(root / p3.E37A, "p3r1_r7r1_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1_r7r1_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1_r7r1_sg7d")

        with np.load(a2ep, allow_pickle=False) as z:
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)
        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        with np.load(cp, allow_pickle=False) as z:
            physical_day = float(np.asarray(z["physical_day"]).reshape(()))
            accepted_steps = int(np.asarray(z["accepted_atomic_steps"]).reshape(()))
            current_grid_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            current_edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)

        gate("checkpoint_npz_day_exact", abs(physical_day - R7_PARENT_DAY) <= 1e-12, physical_day)
        gate("checkpoint_npz_steps_exact", accepted_steps == R7_ACCEPTED_STEPS, accepted_steps)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2src, op, frozen_pressure, p_ref, p3.NSL, p3.NCV)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)

        xi_faces = np.linspace(0.0, 1.0, p3.NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S
        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        dtD = float(sg7a.CFL * (1.0 / p3.NCV) / (float(np.max(u_face)) * max_df + float(sg7a.EPS)))
        nominal_dt = float(dtD * np.min(tau_end_s / DAY_TO_S))
        gate("nominal_dt_exact", abs(nominal_dt - 0.03730130768843055) <= 1e-14, nominal_dt)

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2src, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        rep_capacity = cart_capacity - current_residual
        rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)
        cart_cap_tol = max(1e-8, 1e-12 * max(float(np.max(cart_capacity)), 1.0))
        gate("represented_capacity_nonnegative", float(np.min(rep_capacity)) >= -cart_cap_tol, float(np.min(rep_capacity)))

        nedge = int(edge_cv.size)
        idx = np.arange(nedge, dtype=np.int64)
        Aeq_full = coo_matrix((np.ones(nedge), (edge_cv, idx)), shape=(p3.NCVT, nedge)).tocsr()
        Acell_full = coo_matrix((np.ones(nedge), (edge_cell, idx)), shape=(p3.NCELL, nedge)).tocsr()
        c1_full = (shell > 0).astype(np.float64)

        # Prove the accepted checkpoint representation itself is feasible under frozen XY1.
        stage = "checkpoint_representation"
        cv_from_edge = np.bincount(edge_cv, weights=current_edge_mass, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
        cell_from_edge = np.bincount(edge_cell, weights=current_edge_mass, minlength=p3.NCELL)
        checkpoint_cv_err = float(np.max(np.abs(cv_from_edge - current_cv_mass)))
        checkpoint_rep_err = float(np.max(np.abs(cell_from_edge.reshape(p3.GRID) - current_rep)))
        checkpoint_cap_excess = float(np.max(cell_from_edge - rep_capacity_flat))
        checkpoint_edge_min = float(np.min(current_edge_mass))
        checkpoint_feasible = (
            checkpoint_cv_err <= MASS_TOL
            and checkpoint_rep_err <= MASS_TOL
            and checkpoint_cap_excess <= cart_cap_tol
            and checkpoint_edge_min >= -MASS_TOL
        )
        gate("checkpoint_XY1_CV_equality", checkpoint_cv_err <= MASS_TOL, checkpoint_cv_err)
        gate("checkpoint_XY1_represented_identity", checkpoint_rep_err <= MASS_TOL, checkpoint_rep_err)
        gate("checkpoint_XY1_capacity", checkpoint_cap_excess <= cart_cap_tol, checkpoint_cap_excess)
        gate("checkpoint_XY1_nonnegative_edges", checkpoint_edge_min >= -MASS_TOL, checkpoint_edge_min)

        theory_flux = np.zeros((p3.NSL, p3.NCV + 1), dtype=np.float64)
        theory_flux[:, 0] = weights_m3_day * rho_ref
        ff_internal = np.asarray(sg7a.fractional_flow(current_cv_sat[:, :-1]), dtype=np.float64)
        theory_flux[:, 1:-1] = weights_m3_day[:, None] * u_face[None, 1:-1] * ff_internal * rho_ref
        ff_out = np.asarray(sg7a.fractional_flow(current_cv_sat[:, -1]), dtype=np.float64)
        theory_flux[:, -1] = weights_m3_day * float(u_face[-1]) * ff_out * rho_ref
        cv_rate = theory_flux[:, :-1] - theory_flux[:, 1:]

        def demand_for_dt(dt: float) -> np.ndarray:
            return current_cv_mass + dt * cv_rate

        def solve_stage1(demand: np.ndarray, edge_cv_a: np.ndarray, edge_cell_a: np.ndarray, shell_a: np.ndarray, limit: float):
            ne = int(edge_cv_a.size)
            ii = np.arange(ne, dtype=np.int64)
            Aeq = coo_matrix((np.ones(ne), (edge_cv_a, ii)), shape=(p3.NCVT, ne)).tocsr()
            Acell = coo_matrix((np.ones(ne), (edge_cell_a, ii)), shape=(p3.NCELL, ne)).tocsr()
            c = (shell_a > 0).astype(np.float64)
            t0 = time.perf_counter()
            lp = linprog(
                c, A_ub=Acell, b_ub=rep_capacity_flat,
                A_eq=Aeq, b_eq=demand.reshape(-1),
                bounds=(0.0, None), method="highs-ds",
                options={
                    "presolve": True,
                    "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "time_limit": float(limit),
                },
            )
            return lp, time.perf_counter() - t0

        # Minimum fictitious capacity addition required to make current XY1 feasible.
        Icell = eye(p3.NCELL, format="csr", dtype=np.float64)
        A_relax = hstack([Acell_full, -Icell], format="csr")
        Aeq_relax = hstack([Aeq_full, csr_matrix((p3.NCVT, p3.NCELL), dtype=np.float64)], format="csr")
        c_relax = np.concatenate([np.zeros(nedge), np.ones(p3.NCELL)])
        relax_bounds = [(0.0, None)] * (nedge + p3.NCELL)

        def solve_min_capacity_relaxation(demand: np.ndarray, limit: float):
            t0 = time.perf_counter()
            lp = linprog(
                c_relax,
                A_ub=A_relax,
                b_ub=rep_capacity_flat,
                A_eq=Aeq_relax,
                b_eq=demand.reshape(-1),
                bounds=relax_bounds,
                method="highs-ds",
                options={
                    "presolve": True,
                    "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "time_limit": float(limit),
                },
            )
            return lp, time.perf_counter() - t0

        stage = "XY1_infeasibility_reproduction"
        nominal_demand = demand_for_dt(nominal_dt)
        smallest_dt = nominal_dt * (RETRY_FACTOR ** MAX_RETRIES)
        smallest_demand = demand_for_dt(smallest_dt)
        lp_nom, stage1_nom_wall = solve_stage1(nominal_demand, edge_cv, edge_cell, shell, time_limit_seconds)
        lp_small, stage1_small_wall = solve_stage1(smallest_demand, edge_cv, edge_cell, shell, time_limit_seconds)
        gate("XY1_nominal_Stage1_reproduced_infeasible", (not lp_nom.success) and int(lp_nom.status) == 2, [lp_nom.status, lp_nom.message])
        gate("XY1_smallest_retry_Stage1_reproduced_infeasible", (not lp_small.success) and int(lp_small.status) == 2, [lp_small.status, lp_small.message])

        # Exact minimum capacity deficit for every positive retry size.
        stage = "minimum_capacity_relaxation"
        retry_rows: list[dict[str, Any]] = [{
            "retry": "checkpoint_dt0",
            "dt_days": 0.0,
            "candidate_day": physical_day,
            "relaxation_success": True,
            "minimum_added_capacity_kg": 0.0,
            "maximum_cell_overflow_kg": 0.0,
            "positive_overflow_cell_count": 0,
            "direct_local_capacity_violating_CV_count": 0,
            "wall_seconds": 0.0,
        }]
        nominal_overflow = None
        all_relaxation_solved = True
        positive_retry_deficits: list[float] = []

        # Precompute local per-CV reachable-capacity upper bounds (ignores sharing, so negative slack is a direct proof).
        local_capacity_upper = np.bincount(
            edge_cv, weights=rep_capacity_flat[edge_cell], minlength=p3.NCVT
        )

        for retry in range(MAX_RETRIES + 1):
            dt = nominal_dt * (RETRY_FACTOR ** retry)
            demand = demand_for_dt(dt)
            lp, wall = solve_min_capacity_relaxation(demand, time_limit_seconds)
            if lp.success:
                z = np.asarray(lp.x, dtype=np.float64)
                overflow = z[nedge:]
                deficit = float(lp.fun)
                max_overflow = float(np.max(overflow))
                npos = int(np.count_nonzero(overflow > STRUCTURAL_DEFICIT_TOL))
                local_slack = local_capacity_upper - demand.reshape(-1)
                nlocal = int(np.count_nonzero(local_slack < -STRUCTURAL_DEFICIT_TOL))
                if retry == 0:
                    nominal_overflow = overflow.copy()
                positive_retry_deficits.append(deficit)
                retry_rows.append({
                    "retry": retry,
                    "dt_days": dt,
                    "candidate_day": physical_day + dt,
                    "relaxation_success": True,
                    "minimum_added_capacity_kg": deficit,
                    "maximum_cell_overflow_kg": max_overflow,
                    "positive_overflow_cell_count": npos,
                    "direct_local_capacity_violating_CV_count": nlocal,
                    "wall_seconds": wall,
                })
                print(f"[XY1 DEFICIT retry={retry}] dt={dt:.12g} deficit={deficit:.12g} kg cells={npos} wall={wall:.3f}s", flush=True)
            else:
                all_relaxation_solved = False
                positive_retry_deficits.append(float("nan"))
                retry_rows.append({
                    "retry": retry,
                    "dt_days": dt,
                    "candidate_day": physical_day + dt,
                    "relaxation_success": False,
                    "solve_status": int(lp.status),
                    "solve_message": str(lp.message),
                    "minimum_added_capacity_kg": None,
                    "maximum_cell_overflow_kg": None,
                    "positive_overflow_cell_count": None,
                    "direct_local_capacity_violating_CV_count": None,
                    "wall_seconds": wall,
                })
                print(f"[XY1 DEFICIT retry={retry}] UNSOLVED status={lp.status} wall={wall:.3f}s", flush=True)

        all_positive_retry_deficits = (
            all_relaxation_solved
            and len(positive_retry_deficits) == MAX_RETRIES + 1
            and all(np.isfinite(x) and x > STRUCTURAL_DEFICIT_TOL for x in positive_retry_deficits)
        )

        # Nominal overflow-cell localization.
        overflow_rows: list[dict[str, Any]] = []
        if nominal_overflow is not None:
            pos_cells = np.where(nominal_overflow > STRUCTURAL_DEFICIT_TOL)[0]
            if pos_cells.size:
                coords = np.asarray(np.unravel_index(pos_cells, tuple(p3.GRID), order="C")).T
                for cell, coord in zip(pos_cells.tolist(), coords.tolist()):
                    overflow_rows.append({
                        "flat_cell": int(cell),
                        "z": int(coord[0]),
                        "y": int(coord[1]),
                        "x": int(coord[2]),
                        "minimum_capacity_relaxation_kg": float(nominal_overflow[cell]),
                        "represented_capacity_kg": float(rep_capacity_flat[cell]),
                        "checkpoint_represented_mass_kg": float(current_rep.reshape(-1)[cell]),
                        "checkpoint_remaining_slack_kg": float(rep_capacity_flat[cell] - current_rep.reshape(-1)[cell]),
                    })

        # Prospective second same-layer XY terminal halo. DESIGN/DIAGNOSTIC ONLY.
        stage = "prospective_XY2"
        shape = tuple(int(v) for v in p3.GRID)
        gate("grid_is_3D_for_XY2", len(shape) == 3, shape)
        shell_pos = np.where(shell > 0)[0]
        base_cv = edge_cv[shell_pos]
        base_cell = edge_cell[shell_pos]
        zz, yy, xx = np.unravel_index(base_cell, shape, order="C")
        key_blocks = []
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            yn = yy + dy
            xn = xx + dx
            valid = (yn >= 0) & (yn < shape[1]) & (xn >= 0) & (xn < shape[2])
            if not np.any(valid):
                continue
            nc = np.ravel_multi_index((zz[valid], yn[valid], xn[valid]), shape, order="C")
            key_blocks.append(base_cv[valid].astype(np.int64) * np.int64(p3.NCELL) + nc.astype(np.int64))
        candidate_keys = np.unique(np.concatenate(key_blocks)) if key_blocks else np.asarray([], dtype=np.int64)
        existing_keys = np.unique(edge_cv.astype(np.int64) * np.int64(p3.NCELL) + edge_cell.astype(np.int64))
        new_keys = np.setdiff1d(candidate_keys, existing_keys, assume_unique=True)
        xy2_cv = (new_keys // np.int64(p3.NCELL)).astype(np.int64)
        xy2_cell = (new_keys % np.int64(p3.NCELL)).astype(np.int64)
        ext_cv = np.concatenate([edge_cv, xy2_cv])
        ext_cell = np.concatenate([edge_cell, xy2_cell])
        ext_shell = np.concatenate([shell, np.ones(xy2_cv.size, dtype=np.int8)])

        lp_xy2_nom, xy2_nom_wall = solve_stage1(nominal_demand, ext_cv, ext_cell, ext_shell, max(time_limit_seconds, 120.0))
        xy2_nominal_feasible = bool(lp_xy2_nom.success)
        lp_xy2_small = None
        xy2_small_wall = 0.0
        xy2_smallest_feasible = xy2_nominal_feasible
        if not xy2_nominal_feasible:
            lp_xy2_small, xy2_small_wall = solve_stage1(smallest_demand, ext_cv, ext_cell, ext_shell, max(time_limit_seconds, 120.0))
            xy2_smallest_feasible = bool(lp_xy2_small.success)

        xy2_result: dict[str, Any] = {
            "prospective_only": True,
            "topology_mutation_executed": False,
            "existing_XY1_edge_count": int(nedge),
            "existing_terminal_shell_edge_count": int(np.count_nonzero(shell > 0)),
            "prospective_XY2_new_edge_count": int(xy2_cv.size),
            "prospective_total_edge_count": int(ext_cv.size),
            "same_layer_XY_face_neighbor_only": True,
            "new_XY2_edges_terminal_only_if_ever_adopted": True,
            "nominal_dt_days": nominal_dt,
            "nominal_stage1_success": xy2_nominal_feasible,
            "nominal_stage1_status": int(lp_xy2_nom.status),
            "nominal_stage1_message": str(lp_xy2_nom.message),
            "nominal_stage1_wall_seconds": xy2_nom_wall,
            "nominal_terminal_mass_optimum_kg": float(lp_xy2_nom.fun) if lp_xy2_nom.success else None,
            "smallest_retry_dt_days": smallest_dt,
            "smallest_retry_stage1_success": xy2_smallest_feasible if not xy2_nominal_feasible else True,
            "smallest_retry_stage1_status": (
                int(lp_xy2_small.status) if lp_xy2_small is not None else int(lp_xy2_nom.status)
            ),
            "smallest_retry_stage1_message": (
                str(lp_xy2_small.message) if lp_xy2_small is not None else "not_needed_nominal_feasible"
            ),
            "smallest_retry_stage1_wall_seconds": xy2_small_wall,
        }

        if lp_xy2_nom.success:
            x = np.asarray(lp_xy2_nom.x, dtype=np.float64)
            new_part = x[nedge:]
            xy2_result["nominal_positive_XY2_edge_count"] = int(np.count_nonzero(new_part > 1e-10))
            xy2_result["nominal_XY2_assigned_mass_kg"] = float(np.sum(new_part))

        localization = {
            "checkpoint_day": physical_day,
            "accepted_steps": accepted_steps,
            "checkpoint_XY1_CV_equality_max_abs_error_kg": checkpoint_cv_err,
            "checkpoint_XY1_represented_identity_max_abs_error_kg": checkpoint_rep_err,
            "checkpoint_XY1_capacity_excess_kg": checkpoint_cap_excess,
            "checkpoint_XY1_min_edge_mass_kg": checkpoint_edge_min,
            "checkpoint_representation_feasible": checkpoint_feasible,
            "nominal_dt_days": nominal_dt,
            "smallest_retry_dt_days": smallest_dt,
            "XY1_nominal_Stage1_status": int(lp_nom.status),
            "XY1_nominal_Stage1_message": str(lp_nom.message),
            "XY1_nominal_Stage1_wall_seconds": stage1_nom_wall,
            "XY1_smallest_retry_Stage1_status": int(lp_small.status),
            "XY1_smallest_retry_Stage1_message": str(lp_small.message),
            "XY1_smallest_retry_Stage1_wall_seconds": stage1_small_wall,
            "all_minimum_capacity_relaxations_solved": all_relaxation_solved,
            "all_positive_retry_minimum_capacity_deficits_strictly_positive": all_positive_retry_deficits,
            "nominal_minimum_added_capacity_kg": (
                float(positive_retry_deficits[0]) if positive_retry_deficits and np.isfinite(positive_retry_deficits[0]) else None
            ),
            "smallest_retry_minimum_added_capacity_kg": (
                float(positive_retry_deficits[-1]) if positive_retry_deficits and np.isfinite(positive_retry_deficits[-1]) else None
            ),
            "nominal_overflow_cell_count": len(overflow_rows),
        }

        classification, recommendation, xy2_design_authorized, resume_authorized = classify(
            checkpoint_feasible,
            all_relaxation_solved,
            all_positive_retry_deficits,
            xy2_nominal_feasible,
            xy2_smallest_feasible,
        )

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / RETRY_TABLE).write_bytes(csvb(retry_rows))
        (out / LOCALIZATION).write_bytes(jb(localization))
        (out / OVERFLOW_CELLS).write_bytes(csvb(overflow_rows))
        (out / XY2_RESULT).write_bytes(jb(xy2_result))
        (out / GATES).write_bytes(csvb(gates))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R7_commit": PARENT,
            "R7_source_blob": R7_BLOB,
            "R7R1_source_blob": R7R1_BLOB,
            "R7_checkpoint_audit_sha256": R7_CHECKPOINT_AUDIT_SHA,
            "R7_post_failure_audit_sha256": R7_POST_FAILURE_AUDIT_SHA,
            "R7R1_prior_BLOCK_closed_as_audit_lineage_gate_error": True,
            "R7_prior_BLOCK_status": R7_BLOCK_STATUS,
            "R7_checkpoint_sha256": R7_CHECKPOINT_SHA,
            "R7_checkpoint_day": physical_day,
            "R7_checkpoint_accepted_steps": accepted_steps,
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "localization": localization,
            "prospective_XY2": xy2_result,
            "prospective_XY2_topology_design_freeze_authorized": xy2_design_authorized,
            "R7_checkpoint_resume_transport_authorized": resume_authorized,
            "Day380_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_execution_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "recommended_next_action": recommendation,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R7_prior_BLOCK_is_scientific_failure": False,
            "R7R1_prior_BLOCK_is_scientific_failure": False,
            "R7R1_prior_BLOCK_closed_as_audit_lineage_gate_error": True,
            "R7_checkpoint_must_be_preserved": True,
            "restart_from_Day375_authorized": False,
            "R7_checkpoint_resume_transport_authorized": resume_authorized,
            "prospective_XY2_topology_design_freeze_authorized": xy2_design_authorized,
            "prospective_XY2_execution_authorized": False,
            "R32_recurrent_semantics_remain_authoritative": True,
            "frozen_transport_flow_epoch_day": 365.0,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_execution_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "Day380_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "recommended_next_action": recommendation,
        }
        (out / SUMMARY).write_bytes(jb(summary))
        (out / DECISION).write_bytes(jb(decision))
        mr = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                mr.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / MANIFEST).write_bytes(csvb(mr))

        print("=" * 220)
        print(M, "PASS")
        print("Classification:", classification)
        print("Checkpoint representation feasible:", checkpoint_feasible)
        print("All positive retry XY1 deficits positive:", all_positive_retry_deficits)
        print("Prospective XY2 nominal feasible:", xy2_nominal_feasible)
        print("Prospective XY2 smallest-retry feasible:", xy2_smallest_feasible)
        print("XY2 design freeze authorized:", xy2_design_authorized)
        print("R7 resume transport authorized:", resume_authorized)
        print("Day380 pilot authorized: False")
        print("Full P3-R1 rerun authorized: False")
        print("P4 authorized: False")
        print("=" * 220)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        rp = blocked / f"{OUT_TOKEN}_Blocked_Report.json"
        if not rp.exists():
            rp.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "authoritative_physics_state_mutated": False,
                "authoritative_physical_time_advanced": False,
                "R7_checkpoint_resume_transport_authorized": False,
                "Day380_repaired_pilot_authorized": False,
                "P3_R1_full_rerun_authorized": False,
                "P4_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--time-limit-seconds", type=float, default=90.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.time_limit_seconds))
