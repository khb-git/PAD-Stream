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

M = "POSTV16-AV4-PIVOT-P3-R1-R3"
NAME = "Reduced Exact-Support Stage-2 Equivalence / Runtime Diagnostic"
PASS = "AV4PIVOTP3R1R3_REDUCED_EXACT_SUPPORT_STAGE2_EQUIVALENCE_RUNTIME_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R3_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "7cdfb727fc4884165e5f1a4f73980d7758a78af0"

P3R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py"
P3R1_BLOB = "84076001f40ebcf0825bb8d9bcabe060ed0840d2"
R1R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R1_First_Atomic_Step_Runtime_Representation_Localization.py"
R1R1_BLOB = "b45828cf0faf74ec49ca6f31d2a989cc6b72910c"
R31 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"
R31_BLOB = "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a"
R32 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"
R32_BLOB = "435f5d6dcba38de7166e41ba9e081b6ef573edcf"
R2R1R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R2_R1_R1_Corrected_NegativeTarget_L1LowerBound_ExactSupport_Attainability_Diagnostic.py"
R2R1R1_BLOB = "43aefc8b98bb226122b367b4c640b6248d08b3d9"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
P3R1_STAGE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_STAGING"
P3R1_DAY365_STATE = "POSTV16_AV4_PIVOT_P3_R1_Day0365_Accepted_Dense_State.npz"

R1R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R1_First_Atomic_Step_Runtime_Representation_Localization"
R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R1_Summary.json"
R1R1_LP = "POSTV16_AV4_PIVOT_P3_R1_R1_Bounded_XY1_LP_Probe.json"
R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R1_Artifact_Manifest.csv"
R1R1_STATUS = "AV4PIVOTP3R1R1_FIRST_ATOMIC_STEP_RUNTIME_REPRESENTATION_LOCALIZATION_PASS_NO_STATE_MUTATION"

R2R1R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R2_R1_R1_Corrected_NegativeTarget_L1LowerBound_ExactSupport_Attainability_Diagnostic"
R2R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R2_R1_R1_Summary.json"
R2R1R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R2_R1_R1_Decision_Contract.json"
R2R1R1_FEAS = "POSTV16_AV4_PIVOT_P3_R1_R2_R1_R1_LowerBound_ExactSupport_Feasibility.json"
R2R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R2_R1_R1_Artifact_Manifest.csv"
R2R1R1_STATUS = "AV4PIVOTP3R1R2R1R1_CORRECTED_NEGATIVE_TARGET_L1_LOWER_BOUND_EXACT_SUPPORT_ATTAINABILITY_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
R2R1R1_CLASS = "P3R1_ANALYTIC_L1_LOWER_BOUND_NOT_ATTAINABLE_ON_EXACT_SUPPORT_GENERIC_OR_COMPONENT_LOCAL_STAGE2_OPTIMIZATION_REMAINS_REQUIRED"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R3"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Reduced_ExactSupport_Stage2_Equivalence_Runtime_Diagnostic")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
STAGE2 = f"{OUT_TOKEN}_Reduced_Stage2_Result.json"
DIMENSIONS = f"{OUT_TOKEN}_Dimensional_Reduction.json"
METRICS = f"{OUT_TOKEN}_Metrics.csv"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HIGHS_FEAS_TOL = 1.0e-10
DEFAULT_TIME_LIMIT = 90.0


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
    out = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    if not out:
        raise GateError(f"manifest_empty:{filename}")
    return out


def classify(result: dict[str, Any]) -> tuple[str, str, bool]:
    if result.get("success") is True:
        return (
            "P3R1_FIRST_STEP_REDUCED_EXACT_SUPPORT_STAGE2_SOLVED_WITH_FROZEN_LEXICOGRAPHIC_OBJECTIVE_RUNTIME_PATH_CERTIFIED_SHORT_PREFIX_IMPLEMENTATION_AUTHORIZED",
            "Implement the reduced exact-support Stage-2 fast path after zero-halo Stage-1 certification, preserve the frozen generic XY1 fallback, and certify a short recurrent prefix before any full P3-R1 rerun.",
            True,
        )
    if result.get("outcome") == "TIME_LIMIT":
        return (
            "P3R1_REDUCED_EXACT_SUPPORT_STAGE2_STILL_RUNTIME_LIMITED_NATIVE_HIGHS_BASIS_REUSE_OR_SPECIALIZED_MINCOST_EXECUTION_DESIGN_REQUIRED",
            "Keep the exact reduced formulation and design a faster solver execution path; do not alter the R31 objective, support topology, CFL, or transport law.",
            False,
        )
    if result.get("outcome") == "INFEASIBLE":
        return (
            "P3R1_REDUCED_EXACT_SUPPORT_STAGE2_UNEXPECTEDLY_INFEASIBLE_DESPITE_ZERO_HALO_STAGE1_REQUIRES_FORMULATION_AUDIT_NO_EXECUTION_CHANGE_AUTHORIZED",
            "Audit the reduced Stage-2 construction against R31 before any runtime repair implementation.",
            False,
        )
    return (
        "P3R1_REDUCED_EXACT_SUPPORT_STAGE2_DIAGNOSTIC_INCOMPLETE_NO_EXECUTION_CHANGE_AUTHORIZED",
        "Inspect the bounded reduced Stage-2 result before changing execution.",
        False,
    )


def selftest() -> None:
    c, _, ok = classify({"success": True})
    assert "SHORT_PREFIX_IMPLEMENTATION_AUTHORIZED" in c and ok
    c, _, ok = classify({"success": False, "outcome": "TIME_LIMIT"})
    assert "STILL_RUNTIME_LIMITED" in c and not ok
    assert PARENT == "7cdfb727fc4884165e5f1a4f73980d7758a78af0"
    print("POSTV16 AV4 PIVOT P3-R1-R3 structural self-test: PASS")


def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
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
        print("=" * 210, flush=True)
        print("POSTV16-AV4-PIVOT-P3-R1-R3 — REDUCED EXACT-SUPPORT STAGE-2 EQUIVALENCE / RUNTIME DIAGNOSTIC", flush=True)
        print("READ-ONLY. NO STATE COMMIT. NO TIME ADVANCE. NO PHYSICS / CFL / SUPPORT / LEXICOGRAPHIC-OBJECTIVE CHANGE.", flush=True)
        print("ZERO-HALO STAGE1 => SHELL VARIABLES REMOVED FROM STAGE2. INACTIVE-CELL L1 IS A FIXED CONSTANT.", flush=True)
        print("=" * 210, flush=True)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_STAGING", not staging.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R2R1R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [
            (P3R1, P3R1_BLOB),
            (R1R1, R1R1_BLOB),
            (R31, R31_BLOB),
            (R32, R32_BLOB),
            (R2R1R1, R2R1R1_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        p3 = load_module(root / P3R1, "p3r1_r3_authority")

        stage = "prior_diagnostic_authority"
        r1dir = drive / R1R1_REL
        gate("R1R1_dir_exists", r1dir.is_dir(), str(r1dir))
        for fn in [R1R1_SUMMARY, R1R1_LP, R1R1_MANIFEST]:
            gate(f"R1R1_artifact_present:{fn}", (r1dir / fn).is_file())
        verify_manifest(r1dir, R1R1_MANIFEST)
        r1sum = js(r1dir / R1R1_SUMMARY)
        r1lp = js(r1dir / R1R1_LP)
        gate("R1R1_status_exact", r1sum.get("status") == R1R1_STATUS, r1sum.get("status"))
        gate("R1R1_stage1_zero_halo",
             r1lp.get("stage1", {}).get("success") is True
             and abs(float(r1lp["stage1"]["objective_terminal_mass_kg"])) <= 1.0e-8,
             r1lp.get("stage1", {}))
        gate("R1R1_generic_stage2_time_limited",
             r1lp.get("stage2", {}).get("outcome") == "TIME_LIMIT",
             r1lp.get("stage2", {}).get("outcome"))

        r2dir = drive / R2R1R1_REL
        gate("R2R1R1_dir_exists", r2dir.is_dir(), str(r2dir))
        for fn in [R2R1R1_SUMMARY, R2R1R1_DECISION, R2R1R1_FEAS, R2R1R1_MANIFEST]:
            gate(f"R2R1R1_artifact_present:{fn}", (r2dir / fn).is_file())
        verify_manifest(r2dir, R2R1R1_MANIFEST)
        r2sum = js(r2dir / R2R1R1_SUMMARY)
        r2dec = js(r2dir / R2R1R1_DECISION)
        r2feas = js(r2dir / R2R1R1_FEAS)
        gate("R2R1R1_status_exact", r2sum.get("status") == R2R1R1_STATUS, r2sum.get("status"))
        gate("R2R1R1_classification_exact", r2sum.get("classification") == R2R1R1_CLASS, r2sum.get("classification"))
        gate("R2R1R1_lower_bound_infeasible", r2feas.get("outcome") == "INFEASIBLE", r2feas.get("outcome"))
        gate("R2R1R1_no_fast_path_authorized", r2dec.get("equivalent_lower_bound_fast_path_design_authorized") is False)

        stage = "partial_P3R1_evidence"
        state_path = drive / P3R1_STAGE_REL / P3R1_DAY365_STATE
        gate("P3R1_Day365_partial_state_exists", state_path.is_file(), str(state_path))
        gate("P3R1_Day365_partial_state_SHA_matches_R1R1",
             sha(state_path) == r1sum.get("P3R1_partial_Day365_state_sha256"),
             sha(state_path))

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

        a2e = load_module(root / p3.A2E, "p3r1r3_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1r3_r2src")
        e37a = load_module(root / p3.E37A, "p3r1r3_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1r3_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1r3_sg7d")

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
            current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            current_edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)

        gate("physical_day_365_exact", abs(physical_day - 365.0) <= 1.0e-12, physical_day)

        # Reproduce the first P3-R1 atomic candidate.
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
        gate("nominal_dt_matches_R1R1",
             abs(dt - float(r1sum["nominal_CFL_dt_days"])) <= 1.0e-14,
             [dt, r1sum["nominal_CFL_dt_days"]])

        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)
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

        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        old_sub_sat = current_cv_sat.reshape(-1)[geom_cv_id]
        new_sub_sat = new_cv_sat.reshape(-1)[geom_cv_id]
        old_sub_sg = np.clip(old_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        new_sub_sg = np.clip(new_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        rho_old = np.asarray(r2src.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
        rho_new = np.asarray(r2src.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
        sub_delta = sub_pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)
        delta_grid = np.bincount(flat_cell, weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
        direct_target_rep = current_rep + delta_grid

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2src, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        rep_capacity = cart_capacity - current_residual
        cart_cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cart_capacity)), 1.0))
        gate("represented_capacity_nonnegative", float(np.min(rep_capacity)) >= -cart_cap_tol, float(np.min(rep_capacity)))

        stage = "reduced_stage2_construction"
        exact_mask = shell == 0
        ex_cv = edge_cv[exact_mask]
        ex_cell = edge_cell[exact_mask]
        nex = int(ex_cv.size)
        active_cells = np.unique(ex_cell)
        nactive = int(active_cells.size)
        active_lookup = np.full(p3.NCELL, -1, dtype=np.int64)
        active_lookup[active_cells] = np.arange(nactive, dtype=np.int64)
        ex_active_cell = active_lookup[ex_cell]
        inactive_mask = np.ones(p3.NCELL, dtype=bool)
        inactive_mask[active_cells] = False

        target_flat = direct_target_rep.reshape(-1)
        rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)
        target_active = target_flat[active_cells]
        target_inactive = target_flat[inactive_mask]
        constant_inactive_L1 = float(np.sum(np.abs(target_inactive)))

        # Algebraic reduction of frozen R31 Stage2:
        # - Stage1 optimum is exactly zero => exact lexicographic feasible set has all shell masses zero.
        # - Therefore shell variables may be removed.
        # - Exact-support-inactive cells have y_j fixed to zero; their |0 - target_j| term is constant.
        # - Active cells retain the exact R31 capacity and absolute-deviation objective.
        edge_idx = np.arange(nex, dtype=np.int64)
        Aeq_x = coo_matrix(
            (np.ones(nex, dtype=np.float64), (ex_cv, edge_idx)),
            shape=(p3.NCVT, nex),
        ).tocsr()
        Acell = coo_matrix(
            (np.ones(nex, dtype=np.float64), (ex_active_cell, edge_idx)),
            shape=(nactive, nex),
        ).tocsr()

        zero_d = csr_matrix((nactive, nactive), dtype=np.float64)
        I = eye(nactive, format="csr", dtype=np.float64)
        A_cap = hstack([Acell, zero_d], format="csr")
        A_abs_pos = hstack([Acell, -I], format="csr")
        A_abs_neg = hstack([-Acell, -I], format="csr")
        A_ub = vstack([A_cap, A_abs_pos, A_abs_neg], format="csr")
        b_ub = np.concatenate([
            rep_capacity_flat[active_cells],
            target_active,
            -target_active,
        ])
        Aeq = hstack([Aeq_x, csr_matrix((p3.NCVT, nactive), dtype=np.float64)], format="csr")
        beq = new_cv_mass.reshape(-1)
        c = np.concatenate([np.zeros(nex, dtype=np.float64), np.ones(nactive, dtype=np.float64)])
        bounds = [(0.0, None)] * (nex + nactive)

        full_stage2_vars = int(len(edge_cv) + p3.NCELL)
        reduced_vars = int(nex + nactive)
        full_Aub_nnz = int(r1lp["stage2"]["Aub_nnz"])
        reduced_Aub_nnz = int(A_ub.nnz)
        dimensions = {
            "full_XY1_support_edge_count": int(len(edge_cv)),
            "exact_support_edge_count": nex,
            "terminal_shell_edge_count_removed": int(np.count_nonzero(shell > 0)),
            "full_cartesian_L1_aux_count": int(p3.NCELL),
            "active_exact_support_cell_count": nactive,
            "inactive_cell_count_with_constant_L1": int(np.count_nonzero(inactive_mask)),
            "constant_inactive_cell_L1_kg": constant_inactive_L1,
            "full_stage2_variable_count": full_stage2_vars,
            "reduced_stage2_variable_count": reduced_vars,
            "variable_reduction_fraction": 1.0 - reduced_vars / full_stage2_vars,
            "full_stage2_Aub_nnz": full_Aub_nnz,
            "reduced_stage2_Aub_nnz": reduced_Aub_nnz,
            "Aub_nnz_reduction_fraction": 1.0 - reduced_Aub_nnz / full_Aub_nnz,
            "reduced_stage2_CV_equalities": int(p3.NCVT),
            "reduced_stage2_inequalities": int(A_ub.shape[0]),
            "reduced_Aeq_nnz": int(Aeq.nnz),
        }
        print("--- REDUCED STAGE2 DIMENSIONS ---", flush=True)
        for k, v in dimensions.items():
            print(f"{k:52s}: {v}", flush=True)

        stage = "bounded_reduced_stage2_solve"
        t0 = time.perf_counter()
        lp = linprog(
            c,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=Aeq,
            b_eq=beq,
            bounds=bounds,
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                "time_limit": float(time_limit_seconds),
            },
        )
        wall = time.perf_counter() - t0
        if lp.success:
            outcome = "SUCCESS"
        elif int(lp.status) == 1 and "time" in str(lp.message).lower():
            outcome = "TIME_LIMIT"
        elif int(lp.status) == 2:
            outcome = "INFEASIBLE"
        else:
            outcome = "NOT_SUCCESS"

        result: dict[str, Any] = {
            "executed": True,
            "outcome": outcome,
            "success": bool(lp.success),
            "status": int(lp.status),
            "message": str(lp.message),
            "time_limit_seconds": float(time_limit_seconds),
            "wall_seconds": wall,
            "variables": reduced_vars,
            "CV_equalities": int(p3.NCVT),
            "inequalities": int(A_ub.shape[0]),
            "stage1_terminal_mass_kg": 0.0 if lp.success else None,
            "active_L1_objective_kg": float(lp.fun) if lp.success else None,
            "constant_inactive_L1_kg": constant_inactive_L1,
            "total_stage2_L1_kg": None,
            "CV_equality_max_abs_error_kg": None,
            "active_auxiliary_max_abs_error_kg": None,
            "represented_capacity_excess_kg": None,
            "represented_min_mass_kg": None,
            "optimized_cartesian_min_mass_kg": None,
            "optimized_cartesian_capacity_excess_kg": None,
            "global_source_sink_residual_kg": None,
        }

        if lp.success:
            z = np.asarray(lp.x, dtype=np.float64)
            x = z[:nex]
            d = z[nex:]
            cv_check = np.bincount(ex_cv, weights=x, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
            cv_err = float(np.max(np.abs(cv_check - new_cv_mass)))
            cell_rep_flat = np.bincount(ex_cell, weights=x, minlength=p3.NCELL)
            active_rep = cell_rep_flat[active_cells]
            aux_err = float(np.max(np.abs(d - np.abs(active_rep - target_active)))) if nactive else 0.0
            active_l1 = float(np.sum(np.abs(active_rep - target_active)))
            total_l1 = active_l1 + constant_inactive_L1
            objective_total = float(lp.fun) + constant_inactive_L1
            capacity_excess = float(np.max(cell_rep_flat - rep_capacity_flat))
            rep_min = float(np.min(cell_rep_flat))
            candidate_grid = cell_rep_flat.reshape(p3.GRID) + current_residual
            candidate_min = float(np.min(candidate_grid))
            candidate_cap_excess = float(np.max(candidate_grid - cart_capacity))

            injected = float(np.sum(theory_flux[:, 0]) * dt)
            produced = float(np.sum(theory_flux[:, -1]) * dt)
            expected_total = float(np.sum(current_rep + current_residual)) + injected - produced
            global_residual = float(np.sum(candidate_grid)) - expected_total
            global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))

            result.update({
                "active_L1_objective_kg": float(lp.fun),
                "active_L1_recomputed_kg": active_l1,
                "constant_inactive_L1_kg": constant_inactive_L1,
                "total_stage2_L1_kg": total_l1,
                "objective_plus_constant_kg": objective_total,
                "CV_equality_max_abs_error_kg": cv_err,
                "active_auxiliary_max_abs_error_kg": aux_err,
                "represented_capacity_excess_kg": capacity_excess,
                "represented_min_mass_kg": rep_min,
                "optimized_cartesian_min_mass_kg": candidate_min,
                "optimized_cartesian_capacity_excess_kg": candidate_cap_excess,
                "global_source_sink_residual_kg": global_residual,
            })

            gate("reduced_stage2_all_CV_equalities", cv_err <= MASS_TOL, cv_err)
            gate("reduced_stage2_auxiliary_exact", aux_err <= 1.0e-5, aux_err)
            gate("reduced_stage2_objective_exact",
                 abs(objective_total - total_l1) <= max(1.0e-5, 1.0e-10 * max(total_l1, 1.0)),
                 [objective_total, total_l1])
            gate("reduced_stage2_represented_nonnegative", rep_min >= -MASS_TOL, rep_min)
            gate("reduced_stage2_represented_capacity", capacity_excess <= cart_cap_tol, [capacity_excess, cart_cap_tol])
            gate("reduced_stage2_cartesian_nonnegative", candidate_min >= -MASS_TOL, candidate_min)
            gate("reduced_stage2_cartesian_capacity", candidate_cap_excess <= cart_cap_tol, [candidate_cap_excess, cart_cap_tol])
            gate("reduced_stage2_source_sink", abs(global_residual) <= global_tol, [global_residual, global_tol])

        print("--- REDUCED STAGE2 RESULT ---", flush=True)
        for k, v in result.items():
            print(f"{k:52s}: {v}", flush=True)

        classification, recommendation, implementation_auth = classify(result)

        stage = "publication"
        staging.mkdir(parents=True, exist_ok=False)
        (staging / STAGE2).write_bytes(jb(result))
        (staging / DIMENSIONS).write_bytes(jb(dimensions))
        (staging / GATES).write_bytes(csvb(gates))
        (staging / METRICS).write_bytes(csvb([{
            "physical_day_parent": physical_day,
            "nominal_dt_days": dt,
            "full_stage2_variable_count": full_stage2_vars,
            "reduced_stage2_variable_count": reduced_vars,
            "variable_reduction_fraction": dimensions["variable_reduction_fraction"],
            "full_stage2_Aub_nnz": full_Aub_nnz,
            "reduced_stage2_Aub_nnz": reduced_Aub_nnz,
            "Aub_nnz_reduction_fraction": dimensions["Aub_nnz_reduction_fraction"],
            "reduced_stage2_outcome": outcome,
            "reduced_stage2_wall_seconds": wall,
            "reduced_stage2_total_L1_kg": result.get("total_stage2_L1_kg"),
            "optimized_cartesian_min_mass_kg": result.get("optimized_cartesian_min_mass_kg"),
            "optimized_cartesian_capacity_excess_kg": result.get("optimized_cartesian_capacity_excess_kg"),
        }]))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R2R1R1_commit": PARENT,
            "R1R1_stage1_zero_halo_bound": True,
            "R1R1_generic_stage2_outcome": r1lp["stage2"]["outcome"],
            "R2R1R1_lower_bound_outcome": r2feas["outcome"],
            "P3R1_partial_Day365_state_sha256": sha(state_path),
            "physics_state_mutated": False,
            "physical_time_advanced": False,
            "candidate_committed": False,
            "dimensional_reduction": dimensions,
            "reduced_stage2_result": result,
            "recommended_next_action": recommendation,
            "CFL_change_authorized": False,
            "transport_law_change_authorized": False,
            "support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "reduced_stage2_short_prefix_implementation_authorized": bool(implementation_auth),
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
            "stage1_zero_halo_allows_exact_support_stage2_restriction": True,
            "inactive_exact_support_cells_have_fixed_zero_represented_mass": True,
            "inactive_cell_L1_may_be_carried_as_objective_constant": True,
            "reduced_stage2_short_prefix_implementation_authorized": bool(implementation_auth),
            "frozen_generic_XY1_lexicographic_fallback_must_be_preserved": True,
            "short_recurrent_prefix_certification_required_before_full_rerun": True,
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

        print("=" * 210, flush=True)
        print(M, "PASS", flush=True)
        print("Classification                             :", classification, flush=True)
        print("Full Stage2 variables                     :", full_stage2_vars, flush=True)
        print("Reduced Stage2 variables                  :", reduced_vars, flush=True)
        print("Variable reduction fraction               :", dimensions["variable_reduction_fraction"], flush=True)
        print("Reduced Stage2 outcome                    :", outcome, flush=True)
        print("Reduced Stage2 wall seconds               :", wall, flush=True)
        print("Short-prefix implementation authorized    :", implementation_auth, flush=True)
        print("Full P3-R1 rerun authorized               : False", flush=True)
        print("P4 authorized                             : False", flush=True)
        print("=" * 210, flush=True)
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
    ap.add_argument("--time-limit-seconds", type=float, default=DEFAULT_TIME_LIMIT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.time_limit_seconds))
