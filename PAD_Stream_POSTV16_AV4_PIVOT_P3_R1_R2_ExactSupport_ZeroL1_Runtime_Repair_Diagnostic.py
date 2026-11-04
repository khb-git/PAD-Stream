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

M = "POSTV16-AV4-PIVOT-P3-R1-R2"
NAME = "Exact-Support Zero-Halo / Zero-L1 Runtime-Repair Diagnostic"
PASS = "AV4PIVOTP3R1R2_EXACT_SUPPORT_ZERO_L1_RUNTIME_REPAIR_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "ea6730970d6788a9a33eae669f97c7ef44079f1c"

P3R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py"
P3R1_BLOB = "84076001f40ebcf0825bb8d9bcabe060ed0840d2"
R1R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R1_First_Atomic_Step_Runtime_Representation_Localization.py"
R1R1_BLOB = "b45828cf0faf74ec49ca6f31d2a989cc6b72910c"
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
R1R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R1_Decision_Contract.json"
R1R1_LP = "POSTV16_AV4_PIVOT_P3_R1_R1_Bounded_XY1_LP_Probe.json"
R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R1_Artifact_Manifest.csv"
R1R1_STATUS = "AV4PIVOTP3R1R1_FIRST_ATOMIC_STEP_RUNTIME_REPRESENTATION_LOCALIZATION_PASS_NO_STATE_MUTATION"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R2"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_ExactSupport_ZeroL1_Runtime_Repair_Diagnostic")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GRAPH = f"{OUT_TOKEN}_ExactSupport_Graph_Localization.json"
FEAS = f"{OUT_TOKEN}_ExactSupport_ZeroL1_Feasibility.json"
METRICS = f"{OUT_TOKEN}_FirstStep_ExactSupport_Metrics.csv"
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


def manifest(directory: Path, filename: str) -> dict[str, str]:
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


def classify(feas: dict[str, Any], graph: dict[str, Any]) -> tuple[str, str, bool]:
    if feas.get("success") and feas.get("cell_L1_kg") is not None and feas["cell_L1_kg"] <= 1.0e-5:
        return (
            "P3R1_FIRST_STEP_EXACT_SUPPORT_ZERO_HALO_ZERO_L1_LEXICOGRAPHIC_OPTIMUM_CERTIFIED_GENERIC_XY1_STAGE2_AUXILIARY_LP_IS_AVOIDABLE_RUNTIME_REPAIR_IMPLEMENTATION_AUTHORIZED",
            "Implement a controlled exact-support zero-L1 fast path with frozen XY1 fallback, then certify a short recurrent prefix before any full P3-R1 rerun.",
            True,
        )
    if feas.get("outcome") == "TIME_LIMIT":
        return (
            "P3R1_EXACT_SUPPORT_ZERO_L1_FEASIBILITY_NOT_RUNTIME_CERTIFIED_WITHIN_BOUNDED_PROBE_COMPONENT_LOCAL_OR_REUSED_BASIS_REPAIR_DESIGN_REQUIRED",
            "Use the exact-support graph localization to design component-local circulation or reusable-basis execution without changing physics or topology.",
            False,
        )
    if feas.get("outcome") == "INFEASIBLE":
        return (
            "P3R1_EXACT_SUPPORT_ZERO_L1_INFEASIBLE_AT_FIRST_STEP_GENERIC_STAGE2_OBJECTIVE_REMAINS_SCIENTIFICALLY_NECESSARY_RUNTIME_SOLVER_REDESIGN_REQUIRED",
            "Preserve the frozen lexicographic objective and redesign its execution; do not replace it with a non-equivalent mapback.",
            False,
        )
    return (
        "P3R1_EXACT_SUPPORT_RUNTIME_REPAIR_DIAGNOSIS_INCOMPLETE_NO_PHYSICS_CHANGE_AUTHORIZED",
        "Inspect the exact-support feasibility and graph-localization evidence before changing execution.",
        False,
    )


def selftest() -> None:
    c, _, auth = classify({"success": True, "cell_L1_kg": 0.0}, {})
    assert "ZERO_HALO_ZERO_L1" in c and auth
    c, _, auth = classify({"success": False, "outcome": "TIME_LIMIT"}, {})
    assert "NOT_RUNTIME_CERTIFIED" in c and not auth
    assert PARENT == "ea6730970d6788a9a33eae669f97c7ef44079f1c"
    print("POSTV16 AV4 PIVOT P3-R1-R2 structural self-test: PASS")


def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, vstack
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
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 200, flush=True)
        print("POSTV16-AV4-PIVOT-P3-R1-R2 — EXACT-SUPPORT ZERO-HALO / ZERO-L1 RUNTIME-REPAIR DIAGNOSTIC", flush=True)
        print("READ-ONLY / SHADOW DIAGNOSTIC. NO AUTHORITATIVE STATE COMMIT. NO TIME ADVANCE. NO CADENCE SELECTION.", flush=True)
        print("TEST: CAN THE FIRST P3-R1 CANDIDATE SATISFY THE FROZEN R31 LEXICOGRAPHIC OPTIMUM ON EXACT SUPPORT ONLY?", flush=True)
        print("=" * 200, flush=True)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_STAGING", not staging.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_P3R1R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [(P3R1, P3R1_BLOB), (R1R1, R1R1_BLOB), (R31, R31_BLOB), (R32, R32_BLOB)]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        p3 = load_module(root / P3R1, "p3r1_r2_authority")
        r1 = load_module(root / R1R1, "p3r1r1_r2_authority")

        stage = "R1R1_formal_authority"
        r1dir = drive / R1R1_REL
        gate("R1R1_output_dir_exists", r1dir.is_dir(), str(r1dir))
        for fn in [R1R1_SUMMARY, R1R1_DECISION, R1R1_LP, R1R1_MANIFEST]:
            gate(f"R1R1_artifact_present:{fn}", (r1dir / fn).is_file())
        manifest(r1dir, R1R1_MANIFEST)
        r1sum = js(r1dir / R1R1_SUMMARY)
        r1dec = js(r1dir / R1R1_DECISION)
        r1lp = js(r1dir / R1R1_LP)
        gate("R1R1_status_exact", r1sum.get("status") == R1R1_STATUS, r1sum.get("status"))
        gate("R1R1_decision_status_exact", r1dec.get("status") == R1R1_STATUS, r1dec.get("status"))
        gate("R1R1_direct_path_rejected", r1sum.get("DIRECT_EDGE_EXACT_admissible_first_step") is False)
        gate("R1R1_only_edge_nonnegativity_failed",
             r1sum.get("direct_path_checks") == {
                 "CV_equality": True,
                 "direct_target_L1": True,
                 "edge_nonnegative": False,
                 "represented_capacity": True,
             },
             r1sum.get("direct_path_checks"))
        gate("R1R1_stage1_success", r1lp.get("stage1", {}).get("success") is True, r1lp.get("stage1", {}))
        gate("R1R1_stage1_zero_halo",
             abs(float(r1lp.get("stage1", {}).get("objective_terminal_mass_kg"))) <= 1.0e-8,
             r1lp.get("stage1", {}).get("objective_terminal_mass_kg"))
        gate("R1R1_stage2_time_limited", r1lp.get("stage2", {}).get("outcome") == "TIME_LIMIT", r1lp.get("stage2", {}).get("outcome"))
        gate("R1R1_R2_authorized", r1dec.get("P3_R1_R2_diagnostic_or_runtime_repair_design_authorized") is True)

        stage = "partial_P3R1_evidence_binding"
        p3stage = drive / P3R1_STAGE_REL
        state_path = p3stage / P3R1_DAY365_STATE
        gate("P3R1_partial_Day365_state_exists", state_path.is_file(), str(state_path))
        gate("P3R1_partial_Day365_state_SHA_matches_R1R1",
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
            (p3.A2E, p3.A2E_BLOB), (p3.R2SRC, p3.R2SRC_BLOB), (p3.E37A, p3.E37A_BLOB),
            (p3.SG7A, p3.SG7A_BLOB), (p3.SG7D, p3.SG7D_BLOB)
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == expected, gt(root, "hash-object", str(fp)))

        a2e = load_module(root / p3.A2E, "p3r1r2_a2e")
        r2 = load_module(root / p3.R2SRC, "p3r1r2_r2")
        e37a = load_module(root / p3.E37A, "p3r1r2_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1r2_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1r2_sg7d")

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
        gate("edge_array_shapes", edge_cv.shape == edge_cell.shape == shell.shape == current_edge_mass.shape, edge_cv.shape)

        # Reproduce first P3-R1 candidate exactly.
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
            e37a.invert_cv_mass_to_saturation(r2, new_cv_mass, geometry["cv_pressure_mass_coeff"]), dtype=np.float64
        )

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
        delta_grid = np.bincount(flat_cell, weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
        direct_target_rep = current_rep + delta_grid

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        rep_capacity = cart_capacity - current_residual
        cart_cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cart_capacity)), 1.0))
        gate("direct_target_nonnegative",
             float(np.min(direct_target_rep)) >= -MASS_TOL,
             float(np.min(direct_target_rep)))
        gate("direct_target_within_represented_capacity",
             float(np.max(direct_target_rep - rep_capacity)) <= cart_cap_tol,
             float(np.max(direct_target_rep - rep_capacity)))

        # Reproduce direct edge candidate and R1-R1 failure signature.
        edge_keys = edge_cv * p3.NCELL + edge_cell
        key_to_edge = {int(k): i for i, k in enumerate(edge_keys.tolist())}
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * p3.NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_keys = sub_cv * p3.NCELL + sub_cell
        sub_edge_pos = np.asarray([key_to_edge[int(k)] for k in sub_keys.tolist()], dtype=np.int64)
        edge_delta = np.bincount(sub_edge_pos, weights=sub_delta, minlength=len(edge_cv))
        candidate_edge = current_edge_mass + edge_delta
        neg_mask = candidate_edge < -MASS_TOL
        neg_count = int(np.count_nonzero(neg_mask))
        neg_deficit = float(np.sum(-candidate_edge[neg_mask])) if neg_count else 0.0
        gate("negative_edge_count_reproduces_R1R1", neg_count == int(r1sum["negative_edge_count"]), [neg_count, r1sum["negative_edge_count"]])
        gate("negative_edge_deficit_reproduces_R1R1",
             abs(neg_deficit - float(r1sum["negative_edge_total_deficit_kg"])) <= 1.0e-6,
             [neg_deficit, r1sum["negative_edge_total_deficit_kg"]])

        stage = "exact_support_graph_localization"
        exact_mask = shell == 0
        ex_cv = edge_cv[exact_mask]
        ex_cell = edge_cell[exact_mask]
        ex_candidate = candidate_edge[exact_mask]
        exact_edge_count = int(ex_cv.size)
        gate("exact_edge_count_matches_R1R1", exact_edge_count == int(r1lp["exact_edge_count"]), [exact_edge_count, r1lp["exact_edge_count"]])
        gate("all_negative_edges_are_exact_support", bool(np.all(shell[neg_mask] == 0)))

        # Active exact-support cells only. Inactive target cells must be zero.
        active_cells = np.unique(ex_cell)
        active_mask = np.zeros(p3.NCELL, dtype=bool)
        active_mask[active_cells] = True
        target_flat = direct_target_rep.reshape(-1)
        inactive_target_max = float(np.max(np.abs(target_flat[~active_mask]))) if np.any(~active_mask) else 0.0
        gate("inactive_exact_support_cells_have_zero_target", inactive_target_max <= MASS_TOL, inactive_target_max)

        # Connected components of exact-support bipartite graph.
        ncv = p3.NCVT
        ncell = p3.NCELL
        rows = np.concatenate([ex_cv, ncv + ex_cell])
        cols = np.concatenate([ncv + ex_cell, ex_cv])
        data = np.ones(rows.size, dtype=np.int8)
        adj = coo_matrix((data, (rows, cols)), shape=(ncv + ncell, ncv + ncell)).tocsr()
        ncomp, labels = connected_components(adj, directed=False, return_labels=True)
        edge_comp = labels[ex_cv]
        gate("exact_edge_component_consistency", bool(np.all(edge_comp == labels[ncv + ex_cell])))

        neg_exact_idx = np.where(ex_candidate < -MASS_TOL)[0]
        affected_comps = np.unique(edge_comp[neg_exact_idx])
        edge_counts = np.bincount(edge_comp, minlength=ncomp)
        cv_counts = np.bincount(labels[:ncv], minlength=ncomp)
        cell_counts = np.bincount(labels[ncv:], minlength=ncomp)
        affected_edge_counts = edge_counts[affected_comps] if affected_comps.size else np.asarray([], dtype=int)
        affected_cv_counts = cv_counts[affected_comps] if affected_comps.size else np.asarray([], dtype=int)
        affected_cell_counts = cell_counts[affected_comps] if affected_comps.size else np.asarray([], dtype=int)

        # Component marginal balance: necessary for exact zero-L1 feasibility.
        cv_mass_flat = new_cv_mass.reshape(-1)
        comp_cv_mass = np.bincount(labels[:ncv], weights=cv_mass_flat, minlength=ncomp)
        comp_cell_mass = np.bincount(labels[ncv:], weights=target_flat, minlength=ncomp)
        comp_balance = comp_cv_mass - comp_cell_mass
        max_comp_balance = float(np.max(np.abs(comp_balance)))
        total_balance = float(np.sum(cv_mass_flat) - np.sum(target_flat))
        gate("global_exact_support_marginal_balance", abs(total_balance) <= MASS_TOL, total_balance)
        gate("component_exact_support_marginal_balance", max_comp_balance <= MASS_TOL, max_comp_balance)

        graph = {
            "exact_edge_count": exact_edge_count,
            "exact_support_active_cell_count": int(active_cells.size),
            "bipartite_node_count": int(ncv + ncell),
            "connected_component_count": int(ncomp),
            "affected_component_count": int(affected_comps.size),
            "largest_component_edge_count": int(edge_counts.max()) if edge_counts.size else 0,
            "largest_component_CV_count": int(cv_counts.max()) if cv_counts.size else 0,
            "largest_component_cell_count": int(cell_counts.max()) if cell_counts.size else 0,
            "largest_affected_component_edge_count": int(affected_edge_counts.max()) if affected_edge_counts.size else 0,
            "largest_affected_component_CV_count": int(affected_cv_counts.max()) if affected_cv_counts.size else 0,
            "largest_affected_component_cell_count": int(affected_cell_counts.max()) if affected_cell_counts.size else 0,
            "negative_exact_edge_count": int(neg_exact_idx.size),
            "negative_edge_total_deficit_kg": neg_deficit,
            "maximum_component_marginal_imbalance_kg": max_comp_balance,
            "affected_component_ids": [int(x) for x in affected_comps[:200].tolist()],
            "affected_component_ids_truncated": bool(affected_comps.size > 200),
        }

        print("--- EXACT SUPPORT GRAPH LOCALIZATION ---", flush=True)
        for k, v in graph.items():
            if k != "affected_component_ids":
                print(f"{k:45s}: {v}", flush=True)

        stage = "exact_support_zeroL1_feasibility"
        # Variables exist only on exact-support edges. Equalities enforce:
        #   (1) every CV mass exactly,
        #   (2) every active Cartesian represented-cell target exactly.
        # Therefore a feasible nonnegative solution proves:
        #   Stage1 terminal-shell optimum = 0 (no shell variables exist),
        #   Stage2 Cartesian L1 optimum = 0 (cell target is exact).
        tbuild = time.perf_counter()
        edge_idx = np.arange(exact_edge_count, dtype=np.int64)
        A_cv = coo_matrix((np.ones(exact_edge_count), (ex_cv, edge_idx)), shape=(ncv, exact_edge_count)).tocsr()
        cell_pos = np.full(ncell, -1, dtype=np.int64)
        cell_pos[active_cells] = np.arange(active_cells.size, dtype=np.int64)
        ex_cell_row = cell_pos[ex_cell]
        A_cell_active = coo_matrix(
            (np.ones(exact_edge_count), (ex_cell_row, edge_idx)),
            shape=(active_cells.size, exact_edge_count),
        ).tocsr()
        Aeq = vstack([A_cv, A_cell_active], format="csr")
        beq = np.concatenate([cv_mass_flat, target_flat[active_cells]])
        c = np.zeros(exact_edge_count, dtype=np.float64)
        build_seconds = time.perf_counter() - tbuild

        print(
            f"[EXACT SUPPORT LP] vars={exact_edge_count} eq={Aeq.shape[0]} nnz={Aeq.nnz} "
            f"build={build_seconds:.3f}s time_limit={time_limit_seconds:.1f}s",
            flush=True,
        )
        tsolve = time.perf_counter()
        lp = linprog(
            c,
            A_eq=Aeq,
            b_eq=beq,
            bounds=(0.0, None),
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                "time_limit": float(time_limit_seconds),
            },
        )
        solve_seconds = time.perf_counter() - tsolve

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
            "matrix_build_seconds": build_seconds,
            "wall_seconds": solve_seconds,
            "variables": int(exact_edge_count),
            "equalities": int(Aeq.shape[0]),
            "Aeq_nnz": int(Aeq.nnz),
            "terminal_shell_variables": 0,
            "stage1_terminal_mass_kg": 0.0 if lp.success else None,
            "cell_L1_kg": None,
            "CV_equality_max_abs_error_kg": None,
            "cell_target_max_abs_error_kg": None,
            "minimum_edge_mass_kg": None,
        }

        if lp.success:
            x = np.asarray(lp.x, dtype=np.float64)
            cv_check = np.bincount(ex_cv, weights=x, minlength=ncv)
            cell_check = np.bincount(ex_cell, weights=x, minlength=ncell)
            cv_err = float(np.max(np.abs(cv_check - cv_mass_flat)))
            cell_err = float(np.max(np.abs(cell_check - target_flat)))
            cell_l1 = float(np.sum(np.abs(cell_check - target_flat)))
            min_x = float(np.min(x))
            feas.update({
                "cell_L1_kg": cell_l1,
                "CV_equality_max_abs_error_kg": cv_err,
                "cell_target_max_abs_error_kg": cell_err,
                "minimum_edge_mass_kg": min_x,
            })
            gate("exact_support_solution_nonnegative", min_x >= -MASS_TOL, min_x)
            gate("exact_support_all_CV_equalities", cv_err <= MASS_TOL, cv_err)
            gate("exact_support_cell_target_exact", cell_err <= MASS_TOL, cell_err)
            gate("exact_support_zero_L1_certified", cell_l1 <= 1.0e-5, cell_l1)

        print("--- EXACT SUPPORT ZERO-L1 FEASIBILITY ---", flush=True)
        for k, v in feas.items():
            print(f"{k:45s}: {v}", flush=True)

        classification, recommendation, impl_auth = classify(feas, graph)

        stage = "publication"
        staging.mkdir(parents=True, exist_ok=False)
        (staging / GRAPH).write_bytes(jb(graph))
        (staging / FEAS).write_bytes(jb(feas))
        (staging / METRICS).write_bytes(csvb([{
            "physical_day_parent": physical_day,
            "nominal_dt_days": dt,
            "negative_edge_count": neg_count,
            "negative_edge_total_deficit_kg": neg_deficit,
            "exact_edge_count": exact_edge_count,
            "connected_component_count": graph["connected_component_count"],
            "affected_component_count": graph["affected_component_count"],
            "largest_affected_component_edge_count": graph["largest_affected_component_edge_count"],
            "exact_support_feasibility_outcome": outcome,
            "exact_support_feasibility_wall_seconds": solve_seconds,
            "exact_support_cell_L1_kg": feas.get("cell_L1_kg"),
            "exact_support_CV_error_kg": feas.get("CV_equality_max_abs_error_kg"),
            "exact_support_cell_error_kg": feas.get("cell_target_max_abs_error_kg"),
        }]))
        (staging / GATES).write_bytes(csvb(gates))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_P3R1R1_commit": PARENT,
            "R1R1_status_bound": R1R1_STATUS,
            "R1R1_stage1_terminal_mass_kg": float(r1lp["stage1"]["objective_terminal_mass_kg"]),
            "R1R1_stage2_outcome": r1lp["stage2"]["outcome"],
            "P3R1_partial_Day365_state_sha256": sha(state_path),
            "physics_state_mutated": False,
            "physical_time_advanced": False,
            "candidate_committed": False,
            "nominal_CFL_dt_days": dt,
            "negative_edge_count_reproduced": neg_count,
            "negative_edge_total_deficit_kg_reproduced": neg_deficit,
            "exact_support_graph": graph,
            "exact_support_zeroL1_feasibility": feas,
            "recommended_next_action": recommendation,
            "CFL_change_authorized": False,
            "transport_law_change_authorized": False,
            "support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "exact_support_zeroL1_fast_path_implementation_authorized": bool(impl_auth),
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R32_recurrent_semantics_remain_authoritative": True,
            "P3_R0_remains_authoritative": True,
            "P3_R1_prior_manual_termination_is_PASS": False,
            "P3_R1_prior_manual_termination_is_scientific_failure": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "exact_support_zeroL1_fast_path_implementation_authorized": bool(impl_auth),
            "fast_path_must_use_only_frozen_exact_support": True,
            "fast_path_must_preserve_all_CV_equalities": True,
            "fast_path_must_match_direct_target_cell_mass_exactly": True,
            "fast_path_implies_stage1_terminal_mass_kg": 0.0 if impl_auth else None,
            "fast_path_implies_stage2_cell_L1_kg": 0.0 if impl_auth else None,
            "frozen_XY1_generic_lexicographic_fallback_must_be_preserved": True,
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

        print("=" * 200, flush=True)
        print(M, "PASS", flush=True)
        print("Classification                           :", classification, flush=True)
        print("Exact-support zero-L1 outcome           :", outcome, flush=True)
        print("Exact-support solve wall seconds         :", solve_seconds, flush=True)
        print("Affected exact-support components        :", graph["affected_component_count"], flush=True)
        print("Largest affected component edges         :", graph["largest_affected_component_edge_count"], flush=True)
        print("Fast-path implementation authorized      :", impl_auth, flush=True)
        print("Full P3-R1 rerun authorized              : False", flush=True)
        print("P4 authorized                            : False", flush=True)
        print("=" * 200, flush=True)
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
