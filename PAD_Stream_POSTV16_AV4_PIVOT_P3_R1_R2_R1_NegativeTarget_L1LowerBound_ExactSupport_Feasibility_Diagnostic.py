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

M = "POSTV16-AV4-PIVOT-P3-R1-R2-R1"
NAME = "Negative-Target L1 Lower-Bound / Exact-Support Attainability Diagnostic"
PASS = "AV4PIVOTP3R1R2R1_NEGATIVE_TARGET_L1_LOWER_BOUND_EXACT_SUPPORT_ATTAINABILITY_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R2R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "fd1ac526ff7db6ecfae2aa4aaab76de347618f1a"

P3R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py"
P3R1_BLOB = "84076001f40ebcf0825bb8d9bcabe060ed0840d2"
R1R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R1_First_Atomic_Step_Runtime_Representation_Localization.py"
R1R1_BLOB = "b45828cf0faf74ec49ca6f31d2a989cc6b72910c"
R2 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R2_ExactSupport_ZeroL1_Runtime_Repair_Diagnostic.py"
R2_BLOB = "853563a1eee8a74f151fed2496f44287bd2bff9e"
R31 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"
R31_BLOB = "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a"
R32 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"
R32_BLOB = "435f5d6dcba38de7166e41ba9e081b6ef573edcf"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

P3R1_STAGE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_STAGING"
P3R1_DAY365_STATE = "POSTV16_AV4_PIVOT_P3_R1_Day0365_Accepted_Dense_State.npz"

R1R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R1_First_Atomic_Step_Runtime_Representation_Localization"
R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R1_Summary.json"
R1R1_LP = "POSTV16_AV4_PIVOT_P3_R1_R1_Bounded_XY1_LP_Probe.json"
R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R1_Artifact_Manifest.csv"
R1R1_STATUS = "AV4PIVOTP3R1R1_FIRST_ATOMIC_STEP_RUNTIME_REPRESENTATION_LOCALIZATION_PASS_NO_STATE_MUTATION"

R2_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R2_BLOCKED"
R2_BLOCK_FILE = "POSTV16_AV4_PIVOT_P3_R1_R2_Blocked_Report.json"
R2_BLOCK_STATUS = "AV4PIVOTP3R1R2_TECHNICAL_OR_AUTHORITY_BLOCK"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R2_R1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_NegativeTarget_L1LowerBound_ExactSupport_Attainability_Diagnostic")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
TARGET = f"{OUT_TOKEN}_Negative_Target_Diagnostics.json"
FEAS = f"{OUT_TOKEN}_LowerBound_ExactSupport_Feasibility.json"
GRAPH = f"{OUT_TOKEN}_ExactSupport_Graph_Localization.json"
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


def classify(feas: dict[str, Any]) -> tuple[str, str, bool]:
    if (
        feas.get("success") is True
        and feas.get("lower_bound_attained") is True
        and feas.get("stage1_terminal_mass_kg") == 0.0
    ):
        return (
            "P3R1_FIRST_STEP_ZERO_HALO_ANALYTIC_L1_LOWER_BOUND_ATTAINED_ON_EXACT_SUPPORT_EQUIVALENT_LEXICOGRAPHIC_FAST_PATH_DESIGN_AUTHORIZED",
            "Implement the analytically equivalent exact-support lower-bound fast path with frozen generic XY1 lexicographic fallback, then certify a short recurrent prefix before any full P3-R1 rerun.",
            True,
        )
    if feas.get("outcome") == "TIME_LIMIT":
        return (
            "P3R1_EXACT_SUPPORT_L1_LOWER_BOUND_ATTAINABILITY_NOT_CERTIFIED_WITHIN_BOUNDED_SOLVE_COMPONENT_LOCAL_RUNTIME_DESIGN_REQUIRED",
            "Use the graph localization and negative-target structure to design a component-local exact-support circulation solve; preserve the frozen lexicographic objective.",
            False,
        )
    if feas.get("outcome") == "INFEASIBLE":
        return (
            "P3R1_ANALYTIC_L1_LOWER_BOUND_NOT_ATTAINABLE_ON_EXACT_SUPPORT_GENERIC_OR_COMPONENT_LOCAL_STAGE2_OPTIMIZATION_REMAINS_REQUIRED",
            "Preserve the frozen R31 lexicographic objective and design a faster equivalent Stage-2 solve; do not force a zero-halo lower-bound shortcut.",
            False,
        )
    return (
        "P3R1_NEGATIVE_TARGET_STAGE2_STRUCTURE_LOCALIZED_ADDITIONAL_RUNTIME_DIAGNOSIS_REQUIRED",
        "Inspect the bounded exact-support attainability result before changing execution.",
        False,
    )


def selftest() -> None:
    c, _, ok = classify({"success": True, "lower_bound_attained": True, "stage1_terminal_mass_kg": 0.0})
    assert "LOWER_BOUND_ATTAINED" in c and ok
    c, _, ok = classify({"success": False, "outcome": "INFEASIBLE"})
    assert "NOT_ATTAINABLE" in c and not ok
    assert PARENT == "fd1ac526ff7db6ecfae2aa4aaab76de347618f1a"
    print("POSTV16 AV4 PIVOT P3-R1-R2-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

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
        print("POSTV16-AV4-PIVOT-P3-R1-R2-R1 — NEGATIVE-TARGET L1 LOWER-BOUND / EXACT-SUPPORT ATTAINABILITY DIAGNOSTIC", flush=True)
        print("READ-ONLY. NO STATE COMMIT. NO TIME ADVANCE. NO PHYSICS / CFL / TOPOLOGY / LEXICOGRAPHIC-OBJECTIVE CHANGE.", flush=True)
        print("=" * 210, flush=True)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_STAGING", not staging.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R2_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [
            (P3R1, P3R1_BLOB),
            (R1R1, R1R1_BLOB),
            (R2, R2_BLOB),
            (R31, R31_BLOB),
            (R32, R32_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        p3 = load_module(root / P3R1, "p3r1_r2r1_authority")

        stage = "R2_block_binding"
        r2block = drive / R2_BLOCK_REL / R2_BLOCK_FILE
        gate("R2_BLOCK_report_exists", r2block.is_file(), str(r2block))
        r2b = js(r2block)
        gate("R2_BLOCK_status_exact", r2b.get("status") == R2_BLOCK_STATUS, r2b.get("status"))
        gate("R2_BLOCK_stage_exact", r2b.get("failed_stage") == "authoritative_inputs", r2b.get("failed_stage"))
        gate("R2_BLOCK_reason_exact", r2b.get("exception") == "GateError('direct_target_nonnegative')", r2b.get("exception"))
        gate("R2_BLOCK_no_state_mutation", r2b.get("physics_state_mutated") is False and r2b.get("physical_time_advanced") is False)
        gate("R2_BLOCK_P4_locked", r2b.get("P4_authorized") is False)

        stage = "R1R1_authority"
        r1dir = drive / R1R1_REL
        gate("R1R1_output_exists", r1dir.is_dir(), str(r1dir))
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
        gate("R1R1_only_edge_nonnegativity_failed",
             r1sum.get("direct_path_checks") == {
                 "CV_equality": True,
                 "direct_target_L1": True,
                 "edge_nonnegative": False,
                 "represented_capacity": True,
             },
             r1sum.get("direct_path_checks"))

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

        a2e = load_module(root / p3.A2E, "p3r1r2r1_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1r2r1_r2src")
        e37a = load_module(root / p3.E37A, "p3r1r2r1_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1r2r1_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1r2r1_sg7d")

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

        # Reproduce first P3-R1 atomic candidate exactly.
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
        direct_target = current_rep + delta_grid

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2src, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        rep_capacity = cart_capacity - current_residual
        cart_cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cart_capacity)), 1.0))

        target_flat = direct_target.reshape(-1)
        cv_flat = new_cv_mass.reshape(-1)
        total_target = float(np.sum(target_flat))
        total_cv = float(np.sum(cv_flat))
        gate("direct_target_total_matches_CV_total", abs(total_target - total_cv) <= MASS_TOL, total_target - total_cv)

        # Reproduce R1-R1 direct edge failure.
        edge_keys = edge_cv * p3.NCELL + edge_cell
        key_to_edge = {int(k): i for i, k in enumerate(edge_keys.tolist())}
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * p3.NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_keys = sub_cv * p3.NCELL + sub_cell
        sub_edge_pos = np.asarray([key_to_edge[int(k)] for k in sub_keys.tolist()], dtype=np.int64)
        edge_delta = np.bincount(sub_edge_pos, weights=sub_delta, minlength=len(edge_cv))
        candidate_edge = current_edge_mass + edge_delta
        neg_edge_mask = candidate_edge < -MASS_TOL
        neg_edge_count = int(np.count_nonzero(neg_edge_mask))
        neg_edge_deficit = float(np.sum(-candidate_edge[neg_edge_mask]))
        gate("negative_edge_count_reproduces_R1R1", neg_edge_count == int(r1sum["negative_edge_count"]),
             [neg_edge_count, r1sum["negative_edge_count"]])
        gate("negative_edge_deficit_reproduces_R1R1",
             abs(neg_edge_deficit - float(r1sum["negative_edge_total_deficit_kg"])) <= 1.0e-6,
             [neg_edge_deficit, r1sum["negative_edge_total_deficit_kg"]])

        stage = "negative_target_structure"
        negative_mask = target_flat < 0.0
        negative_tol_mask = target_flat < -MASS_TOL
        positive_mask = target_flat > 0.0
        zero_mask = target_flat == 0.0
        negative_count = int(np.count_nonzero(negative_mask))
        negative_count_tol = int(np.count_nonzero(negative_tol_mask))
        D = float(np.sum(-target_flat[negative_mask]))
        lower_bound = 2.0 * D
        min_target = float(np.min(target_flat))
        positive_target_max_capacity_excess = float(np.max(np.maximum(target_flat, 0.0) - rep_capacity.reshape(-1)))
        full_candidate = direct_target + current_residual
        full_candidate_min = float(np.min(full_candidate))
        full_candidate_cap_excess = float(np.max(full_candidate - cart_capacity))

        target_diag = {
            "minimum_direct_target_represented_mass_kg": min_target,
            "negative_target_cell_count_exact": negative_count,
            "negative_target_cell_count_below_minus_MASS_TOL": negative_count_tol,
            "negative_target_total_deficit_D_kg": D,
            "analytic_L1_lower_bound_2D_kg": lower_bound,
            "positive_target_cell_count": int(np.count_nonzero(positive_mask)),
            "zero_target_cell_count_exact": int(np.count_nonzero(zero_mask)),
            "target_total_mass_kg": total_target,
            "CV_total_mass_kg": total_cv,
            "positive_target_capacity_excess_kg": positive_target_max_capacity_excess,
            "full_cartesian_candidate_min_mass_kg": full_candidate_min,
            "full_cartesian_candidate_capacity_excess_kg": full_candidate_cap_excess,
        }
        print("--- NEGATIVE DIRECT-TARGET STRUCTURE ---", flush=True)
        for k, v in target_diag.items():
            print(f"{k:52s}: {v}", flush=True)

        gate("negative_target_reproduced", min_target < -MASS_TOL, min_target)
        gate("positive_target_within_represented_capacity",
             positive_target_max_capacity_excess <= cart_cap_tol,
             [positive_target_max_capacity_excess, cart_cap_tol])
        gate("full_cartesian_candidate_nonnegative",
             full_candidate_min >= -MASS_TOL,
             full_candidate_min)
        gate("full_cartesian_candidate_within_capacity",
             full_candidate_cap_excess <= cart_cap_tol,
             [full_candidate_cap_excess, cart_cap_tol])

        stage = "exact_support_graph_localization"
        exact_mask = shell == 0
        ex_cv = edge_cv[exact_mask]
        ex_cell = edge_cell[exact_mask]
        exact_edge_count = int(ex_cv.size)
        ncv = p3.NCVT
        ncell = p3.NCELL

        rows = np.concatenate([ex_cv, ncv + ex_cell])
        cols = np.concatenate([ncv + ex_cell, ex_cv])
        data = np.ones(rows.size, dtype=np.int8)
        adj = coo_matrix((data, (rows, cols)), shape=(ncv + ncell, ncv + ncell)).tocsr()
        ncomp, labels = connected_components(adj, directed=False, return_labels=True)
        edge_comp = labels[ex_cv]
        gate("exact_support_component_consistency", bool(np.all(edge_comp == labels[ncv + ex_cell])))

        # Components touched by the negative direct edge candidate.
        neg_exact_local = np.where(candidate_edge[exact_mask] < -MASS_TOL)[0]
        affected_comps = np.unique(edge_comp[neg_exact_local])
        edge_counts = np.bincount(edge_comp, minlength=ncomp)
        cv_counts = np.bincount(labels[:ncv], minlength=ncomp)
        cell_counts = np.bincount(labels[ncv:], minlength=ncomp)
        graph = {
            "exact_support_edge_count": exact_edge_count,
            "connected_component_count": int(ncomp),
            "negative_edge_affected_component_count": int(affected_comps.size),
            "largest_component_edge_count": int(edge_counts.max()) if edge_counts.size else 0,
            "largest_affected_component_edge_count": int(edge_counts[affected_comps].max()) if affected_comps.size else 0,
            "largest_affected_component_CV_count": int(cv_counts[affected_comps].max()) if affected_comps.size else 0,
            "largest_affected_component_cell_count": int(cell_counts[affected_comps].max()) if affected_comps.size else 0,
        }

        stage = "lower_bound_exact_support_attainability"
        # Exact-support variables only => terminal shell mass exactly zero.
        # Cell upper bounds y_j <= max(t_j,0) imply:
        #   y_j = 0 on negative target cells,
        #   no positive cell may exceed its target.
        # Since total represented mass is fixed by CV equalities and equals sum(t),
        # any feasible solution necessarily attains L1 = 2*D, the global nonnegative lower bound.
        tbuild = time.perf_counter()
        idx = np.arange(exact_edge_count, dtype=np.int64)
        Aeq = coo_matrix(
            (np.ones(exact_edge_count), (ex_cv, idx)),
            shape=(ncv, exact_edge_count),
        ).tocsr()
        Aub = coo_matrix(
            (np.ones(exact_edge_count), (ex_cell, idx)),
            shape=(ncell, exact_edge_count),
        ).tocsr()
        b_ub = np.maximum(target_flat, 0.0)
        build_s = time.perf_counter() - tbuild

        print(
            f"[LOWER-BOUND FEASIBILITY] vars={exact_edge_count} eq={Aeq.shape[0]} "
            f"ub={Aub.shape[0]} nnz_eq={Aeq.nnz} nnz_ub={Aub.nnz} "
            f"build={build_s:.3f}s limit={time_limit_seconds:.1f}s",
            flush=True,
        )

        tsolve = time.perf_counter()
        lp = linprog(
            np.zeros(exact_edge_count, dtype=np.float64),
            A_ub=Aub,
            b_ub=b_ub,
            A_eq=Aeq,
            b_eq=cv_flat,
            bounds=(0.0, None),
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                "time_limit": float(time_limit_seconds),
            },
        )
        solve_s = time.perf_counter() - tsolve

        if lp.success:
            outcome = "SUCCESS"
        elif int(lp.status) == 1 and "time" in str(lp.message).lower():
            outcome = "TIME_LIMIT"
        elif int(lp.status) == 2:
            outcome = "INFEASIBLE"
        else:
            outcome = "NOT_SUCCESS"

        feas: dict[str, Any] = {
            "executed": True,
            "outcome": outcome,
            "success": bool(lp.success),
            "status": int(lp.status),
            "message": str(lp.message),
            "time_limit_seconds": float(time_limit_seconds),
            "matrix_build_seconds": build_s,
            "wall_seconds": solve_s,
            "variables": exact_edge_count,
            "CV_equalities": int(ncv),
            "cell_upper_bound_constraints": int(ncell),
            "Aeq_nnz": int(Aeq.nnz),
            "Aub_nnz": int(Aub.nnz),
            "stage1_terminal_mass_kg": 0.0 if lp.success else None,
            "analytic_L1_lower_bound_kg": lower_bound,
            "achieved_L1_kg": None,
            "lower_bound_attained": False,
            "CV_equality_max_abs_error_kg": None,
            "cell_upper_bound_max_excess_kg": None,
            "minimum_edge_mass_kg": None,
            "negative_target_assigned_mass_kg": None,
        }

        if lp.success:
            x = np.asarray(lp.x, dtype=np.float64)
            y = np.bincount(ex_cell, weights=x, minlength=ncell)
            cv_check = np.bincount(ex_cv, weights=x, minlength=ncv)
            cv_err = float(np.max(np.abs(cv_check - cv_flat)))
            ub_excess = float(np.max(y - b_ub))
            l1 = float(np.sum(np.abs(y - target_flat)))
            min_x = float(np.min(x))
            negative_assigned = float(np.sum(y[negative_mask]))
            l1_tol = max(1.0e-5, 1.0e-10 * max(lower_bound, 1.0))
            attained = abs(l1 - lower_bound) <= l1_tol
            feas.update({
                "achieved_L1_kg": l1,
                "lower_bound_attained": bool(attained),
                "L1_lower_bound_gap_kg": l1 - lower_bound,
                "L1_lower_bound_tolerance_kg": l1_tol,
                "CV_equality_max_abs_error_kg": cv_err,
                "cell_upper_bound_max_excess_kg": ub_excess,
                "minimum_edge_mass_kg": min_x,
                "negative_target_assigned_mass_kg": negative_assigned,
            })
            gate("lower_bound_solution_edge_nonnegative", min_x >= -MASS_TOL, min_x)
            gate("lower_bound_solution_CV_equalities", cv_err <= MASS_TOL, cv_err)
            gate("lower_bound_solution_cell_caps", ub_excess <= MASS_TOL, ub_excess)
            gate("lower_bound_solution_negative_cells_zero", negative_assigned <= MASS_TOL, negative_assigned)
            gate("analytic_L1_lower_bound_attained", attained, [l1, lower_bound, l1_tol])

        print("--- LOWER-BOUND EXACT-SUPPORT FEASIBILITY ---", flush=True)
        for k, v in feas.items():
            print(f"{k:52s}: {v}", flush=True)

        classification, recommendation, impl_auth = classify(feas)

        stage = "publication"
        staging.mkdir(parents=True, exist_ok=False)
        (staging / TARGET).write_bytes(jb(target_diag))
        (staging / FEAS).write_bytes(jb(feas))
        (staging / GRAPH).write_bytes(jb(graph))
        (staging / GATES).write_bytes(csvb(gates))
        (staging / METRICS).write_bytes(csvb([{
            "physical_day_parent": physical_day,
            "nominal_dt_days": dt,
            "negative_edge_count": neg_edge_count,
            "negative_edge_total_deficit_kg": neg_edge_deficit,
            "minimum_direct_target_mass_kg": min_target,
            "negative_target_cell_count": negative_count_tol,
            "negative_target_total_deficit_D_kg": D,
            "analytic_L1_lower_bound_2D_kg": lower_bound,
            "exact_support_edge_count": exact_edge_count,
            "affected_component_count": graph["negative_edge_affected_component_count"],
            "feasibility_outcome": outcome,
            "feasibility_wall_seconds": solve_s,
            "achieved_L1_kg": feas.get("achieved_L1_kg"),
            "lower_bound_attained": feas.get("lower_bound_attained"),
        }]))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R2_commit": PARENT,
            "R2_prior_block_status": R2_BLOCK_STATUS,
            "R2_prior_block_reason": r2b.get("exception"),
            "R2_prior_block_is_scientific_failure": False,
            "R1R1_stage1_zero_halo_remains_valid": True,
            "P3R1_partial_Day365_state_sha256": sha(state_path),
            "physics_state_mutated": False,
            "physical_time_advanced": False,
            "candidate_committed": False,
            "negative_target_diagnostics": target_diag,
            "exact_support_graph": graph,
            "lower_bound_exact_support_feasibility": feas,
            "recommended_next_action": recommendation,
            "CFL_change_authorized": False,
            "transport_law_change_authorized": False,
            "support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "equivalent_lower_bound_fast_path_design_authorized": bool(impl_auth),
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R32_recurrent_semantics_remain_authoritative": True,
            "P3_R0_remains_authoritative": True,
            "R2_block_closed_as_diagnostic_design_premise_error": True,
            "scientific_failure_declared": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "equivalent_lower_bound_fast_path_design_authorized": bool(impl_auth),
            "fast_path_must_use_frozen_exact_support": True,
            "fast_path_must_preserve_all_CV_equalities": True,
            "fast_path_must_preserve_nonnegative_edge_mass": True,
            "fast_path_must_certify_global_L1_lower_bound": True,
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
        print("Classification                              :", classification, flush=True)
        print("Minimum direct represented target kg        :", min_target, flush=True)
        print("Negative target deficit D kg                :", D, flush=True)
        print("Analytic Stage2 L1 lower bound 2D kg        :", lower_bound, flush=True)
        print("Exact-support lower-bound feasibility       :", outcome, flush=True)
        print("Feasibility wall seconds                    :", solve_s, flush=True)
        print("Equivalent fast-path design authorized      :", impl_auth, flush=True)
        print("Full P3-R1 rerun authorized                 : False", flush=True)
        print("P4 authorized                               : False", flush=True)
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
