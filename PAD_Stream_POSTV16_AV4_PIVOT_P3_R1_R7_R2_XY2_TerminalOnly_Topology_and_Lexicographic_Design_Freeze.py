#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, time
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R7-R2"
NAME = "XY2 Terminal-Only Same-Layer Topology + Frozen Lexicographic Stage1/Stage2 Design Freeze"
PASS = "AV4PIVOTP3R1R7R2_XY2_TERMINAL_ONLY_TOPOLOGY_LEXICOGRAPHIC_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R7R2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "008e09a5976abbc8be4ef4efa3fc7d3959633d98"

R7 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_Day375_to_Day380_ThirdObservation_Pilot.py"
R7_BLOB = "0b42bb4cdd395740742e3784f455a2837f3b7ce2"
R7R1R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Corrected_Audit_Lineage_Stage1_XY2_Diagnostic.py"
R7R1R1_BLOB = "3f9a508f5193e83bc62092e8ffd4f8f4f14349be"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R7_STAGE_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_STAGING"
R7_CHECKPOINT = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.npz"
R7_CHECKPOINT_META = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.json"
R7_CHECKPOINT_SHA = "d02fef7ef29d273002c1be613539fc39afac1ff231ad369b5f6571b0adcda83b"
R7_PARENT_DAY = 376.9106720614003
R7_ACCEPTED_STEPS = 328

R7R1R1_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Corrected_Audit_Lineage_Stage1_Infeasibility_Localization_and_Prospective_XY2_Feasibility_Diagnostic"
R7R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Summary.json"
R7R1R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Decision_Contract.json"
R7R1R1_XY2 = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Prospective_XY2_Result.json"
R7R1R1_LOCAL = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Nominal_XY1_Localization.json"
R7R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Artifact_Manifest.csv"
R7R1R1_STATUS = "AV4PIVOTP3R1R7R1R1_CORRECTED_AUDIT_LINEAGE_STAGE1_XY2_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
R7R1R1_CLASS = "P3R1_R7_XY1_POSITIVE_DT_CAPACITY_BOUNDARY_CONFIRMED_PROSPECTIVE_XY2_NOMINAL_STAGE1_FEASIBLE_TOPOLOGY_DESIGN_FREEZE_AUTHORIZED"

EXPECTED_EXISTING_EDGE_COUNT = 1245666
EXPECTED_EXISTING_SHELL_EDGE_COUNT = 975945
EXPECTED_XY2_NEW_EDGE_COUNT = 1845407
EXPECTED_TOTAL_EDGE_COUNT = 3091073
EXPECTED_XY2_POSITIVE_NOMINAL_EDGE_COUNT = 9114
EXPECTED_XY2_NOMINAL_ASSIGNED_MASS_KG = 1614134.4851971744
EXPECTED_NOMINAL_TERMINAL_OPT_KG = 2358503.612633198
EXPECTED_XY1_NOMINAL_DEFICIT_KG = 13.989265426676269
EXPECTED_XY1_SMALLEST_DEFICIT_KG = 0.040589185368389735

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R2"
OUT_REL = BASE / (OUT_TOKEN + "_XY2_TerminalOnly_Topology_and_Lexicographic_Design_Freeze")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
TOPOLOGY = f"{OUT_TOKEN}_XY2_Topology_Contract.json"
LEXICOGRAPHIC = f"{OUT_TOKEN}_Lexicographic_Stage1_Stage2_Contract.json"
PRICING = f"{OUT_TOKEN}_Restricted_Master_Dual_Pricing_Contract.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1e-6
HIGHS_FEAS_TOL = 1e-10
HALO_OPT_TOL = 1e-6
PRICING_TOL = 1e-8
POSITIVE_EDGE_TOL = 1e-10

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
    return s.getvalue().encode()

def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()

def verify_manifest(directory: Path, filename: str) -> None:
    rows = csvr(directory / filename)
    if not rows:
        raise GateError("manifest_empty")
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")

def selftest() -> None:
    assert PARENT == "008e09a5976abbc8be4ef4efa3fc7d3959633d98"
    assert EXPECTED_TOTAL_EDGE_COUNT == EXPECTED_EXISTING_EDGE_COUNT + EXPECTED_XY2_NEW_EDGE_COUNT
    assert EXPECTED_XY1_NOMINAL_DEFICIT_KG > 0.0
    assert EXPECTED_XY1_SMALLEST_DEFICIT_KG > 0.0
    print("POSTV16 AV4 PIVOT P3-R1-R7-R2 structural self-test: PASS")

def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix

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
        print("POSTV16-AV4-PIVOT-P3-R1-R7-R2 — XY2 TERMINAL-ONLY TOPOLOGY + LEXICOGRAPHIC DESIGN FREEZE")
        print("DESIGN/FREEZE + READ-ONLY SHADOW STAGE1 RECONSTRUCTION. NO STAGE2 EXECUTION. NO STATE/TIME ADVANCE.")
        print("=" * 220)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R7R1R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [(R7, R7_BLOB), (R7R1R1, R7R1R1_BLOB)]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        r7 = load_module(root / R7, "p3r1_r7r2_r7_source")
        p3 = load_module(root / r7.P3R1, "p3r1_r7r2_p3")

        stage = "R7R1R1_authority"
        srcdir = drive / R7R1R1_REL
        gate("R7R1R1_dir_exists", srcdir.is_dir(), str(srcdir))
        for fn in [R7R1R1_SUMMARY, R7R1R1_DECISION, R7R1R1_XY2, R7R1R1_LOCAL, R7R1R1_MANIFEST]:
            gate(f"R7R1R1_artifact_present:{fn}", (srcdir / fn).is_file())
        verify_manifest(srcdir, R7R1R1_MANIFEST)
        s = js(srcdir / R7R1R1_SUMMARY)
        d = js(srcdir / R7R1R1_DECISION)
        xy2_prior = js(srcdir / R7R1R1_XY2)
        local_prior = js(srcdir / R7R1R1_LOCAL)
        gate("R7R1R1_status_exact", s.get("status") == R7R1R1_STATUS, s.get("status"))
        gate("R7R1R1_classification_exact", s.get("classification") == R7R1R1_CLASS, s.get("classification"))
        gate("R7R1R1_design_freeze_authorized", d.get("prospective_XY2_topology_design_freeze_authorized") is True)
        gate("R7R1R1_XY2_execution_locked", d.get("prospective_XY2_execution_authorized") is False)
        gate("R7R1R1_transport_resume_locked", d.get("R7_checkpoint_resume_transport_authorized") is False)
        gate("R7R1R1_Day380_locked", d.get("Day380_repaired_pilot_authorized") is False)
        gate("R7R1R1_full_P3R1_locked", d.get("P3_R1_full_rerun_authorized") is False)
        gate("R7R1R1_P4_locked", d.get("P4_authorized") is False)
        gate("R7R1R1_XY1_nominal_deficit_exact",
             abs(float(local_prior.get("nominal_minimum_added_capacity_kg")) - EXPECTED_XY1_NOMINAL_DEFICIT_KG) <= 1e-9,
             local_prior.get("nominal_minimum_added_capacity_kg"))
        gate("R7R1R1_XY1_smallest_deficit_exact",
             abs(float(local_prior.get("smallest_retry_minimum_added_capacity_kg")) - EXPECTED_XY1_SMALLEST_DEFICIT_KG) <= 1e-9,
             local_prior.get("smallest_retry_minimum_added_capacity_kg"))
        gate("R7R1R1_XY2_nominal_feasible", xy2_prior.get("nominal_stage1_success") is True)
        gate("R7R1R1_XY2_new_edge_count_exact", int(xy2_prior.get("prospective_XY2_new_edge_count")) == EXPECTED_XY2_NEW_EDGE_COUNT)
        gate("R7R1R1_total_edge_count_exact", int(xy2_prior.get("prospective_total_edge_count")) == EXPECTED_TOTAL_EDGE_COUNT)
        gate("R7R1R1_XY2_terminal_only", xy2_prior.get("new_XY2_edges_terminal_only_if_ever_adopted") is True)
        gate("R7R1R1_XY2_same_layer_XY_only", xy2_prior.get("same_layer_XY_face_neighbor_only") is True)

        stage = "checkpoint_authority"
        cp = drive / R7_STAGE_REL / R7_CHECKPOINT
        cpmeta = drive / R7_STAGE_REL / R7_CHECKPOINT_META
        gate("R7_checkpoint_exists", cp.is_file(), str(cp))
        gate("R7_checkpoint_meta_exists", cpmeta.is_file(), str(cpmeta))
        meta = js(cpmeta)
        gate("R7_checkpoint_SHA_exact", sha(cp) == R7_CHECKPOINT_SHA, sha(cp))
        gate("R7_checkpoint_meta_SHA_exact", meta.get("checkpoint_sha256") == R7_CHECKPOINT_SHA, meta.get("checkpoint_sha256"))
        gate("R7_checkpoint_day_exact", abs(float(meta.get("physical_day")) - R7_PARENT_DAY) <= 1e-12, meta.get("physical_day"))
        gate("R7_checkpoint_steps_exact", int(meta.get("accepted_atomic_steps")) == R7_ACCEPTED_STEPS, meta.get("accepted_atomic_steps"))

        stage = "authoritative_inputs"
        a2ep = drive / p3.A2E_REL / p3.A2E_EPOCH
        a6ep = drive / p3.A6E_REL / p3.A6E_STATE
        gate("A2E_epoch_exists", a2ep.is_file(), str(a2ep))
        gate("A2E_epoch_SHA_exact", sha(a2ep) == p3.A2E_EPOCH_SHA, sha(a2ep))
        gate("A6E_state_exists", a6ep.is_file(), str(a6ep))
        gate("A6E_state_SHA_exact", sha(a6ep) == p3.A6E_SHA, sha(a6ep))
        for fn, expected in [
            (p3.A2E, p3.A2E_BLOB), (p3.R2SRC, p3.R2SRC_BLOB),
            (p3.E37A, p3.E37A_BLOB), (p3.SG7A, p3.SG7A_BLOB),
            (p3.SG7D, p3.SG7D_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == expected, gt(root, "hash-object", str(fp)))

        a2e = load_module(root / p3.A2E, "p3r1_r7r2_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1_r7r2_r2src")
        e37a = load_module(root / p3.E37A, "p3r1_r7r2_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1_r7r2_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1_r7r2_sg7d")

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
            current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            current_edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2src, op, frozen_pressure, p_ref, p3.NSL, p3.NCV)
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

        stage = "XY2_topology_reconstruction"
        gate("existing_edge_count_exact", int(edge_cv.size) == EXPECTED_EXISTING_EDGE_COUNT, int(edge_cv.size))
        gate("existing_terminal_shell_count_exact", int(np.count_nonzero(shell > 0)) == EXPECTED_EXISTING_SHELL_EDGE_COUNT,
             int(np.count_nonzero(shell > 0)))
        gate("existing_shell_binary", set(np.unique(shell).tolist()).issubset({0, 1}), np.unique(shell).tolist())

        shape = tuple(int(v) for v in p3.GRID)
        shell_pos = np.where(shell > 0)[0]
        base_cv = edge_cv[shell_pos]
        base_cell = edge_cell[shell_pos]
        zz, yy, xx = np.unravel_index(base_cell, shape, order="C")
        key_blocks = []
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            yn = yy + dy
            xn = xx + dx
            valid = (yn >= 0) & (yn < shape[1]) & (xn >= 0) & (xn < shape[2])
            if np.any(valid):
                nc = np.ravel_multi_index((zz[valid], yn[valid], xn[valid]), shape, order="C")
                key_blocks.append(base_cv[valid].astype(np.int64) * np.int64(p3.NCELL) + nc.astype(np.int64))
        candidate_keys = np.unique(np.concatenate(key_blocks))
        existing_keys = np.unique(edge_cv.astype(np.int64) * np.int64(p3.NCELL) + edge_cell.astype(np.int64))
        new_keys = np.setdiff1d(candidate_keys, existing_keys, assume_unique=True)
        xy2_cv = (new_keys // np.int64(p3.NCELL)).astype(np.int64)
        xy2_cell = (new_keys % np.int64(p3.NCELL)).astype(np.int64)
        ext_cv = np.concatenate([edge_cv, xy2_cv])
        ext_cell = np.concatenate([edge_cell, xy2_cell])
        ext_shell = np.concatenate([shell, np.ones(xy2_cv.size, dtype=np.int8)])

        gate("XY2_new_edge_count_exact", int(xy2_cv.size) == EXPECTED_XY2_NEW_EDGE_COUNT, int(xy2_cv.size))
        gate("XY2_total_edge_count_exact", int(ext_cv.size) == EXPECTED_TOTAL_EDGE_COUNT, int(ext_cv.size))
        gate("XY2_new_edges_unique", int(np.unique(new_keys).size) == int(new_keys.size))
        gate("XY2_new_edges_disjoint_existing", np.intersect1d(new_keys, existing_keys).size == 0)
        gate("XY2_new_shell_cost_one", bool(np.all(ext_shell[edge_cv.size:] == 1)))
        gate("exact_support_cost_zero_preserved", bool(np.all(ext_shell[:edge_cv.size][shell == 0] == 0)))
        gate("existing_XY1_terminal_cost_one_preserved", bool(np.all(ext_shell[:edge_cv.size][shell > 0] == 1)))

        # Transport support is unchanged: every mapped subsegment remains exact support, and XY2 is representation-only.
        edge_keys = edge_cv.astype(np.int64) * np.int64(p3.NCELL) + edge_cell.astype(np.int64)
        key_to_shell = {int(k): int(v) for k, v in zip(edge_keys.tolist(), shell.tolist())}
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * p3.NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_keys = sub_cv.astype(np.int64) * np.int64(p3.NCELL) + sub_cell.astype(np.int64)
        gate("all_transport_subsegments_remain_existing_exact_support",
             all(key_to_shell.get(int(k), -1) == 0 for k in sub_keys.tolist()))
        gate("no_transport_subsegment_uses_XY2", np.intersect1d(np.unique(sub_keys), new_keys).size == 0)

        stage = "nominal_Stage1_shadow"
        theory_flux = np.zeros((p3.NSL, p3.NCV + 1), dtype=np.float64)
        theory_flux[:, 0] = weights_m3_day * rho_ref
        ff_internal = np.asarray(sg7a.fractional_flow(current_cv_sat[:, :-1]), dtype=np.float64)
        theory_flux[:, 1:-1] = weights_m3_day[:, None] * u_face[None, 1:-1] * ff_internal * rho_ref
        ff_out = np.asarray(sg7a.fractional_flow(current_cv_sat[:, -1]), dtype=np.float64)
        theory_flux[:, -1] = weights_m3_day * float(u_face[-1]) * ff_out * rho_ref
        nominal_demand = current_cv_mass + nominal_dt * (theory_flux[:, :-1] - theory_flux[:, 1:])

        ne = int(ext_cv.size)
        ii = np.arange(ne, dtype=np.int64)
        Aeq = coo_matrix((np.ones(ne), (ext_cv, ii)), shape=(p3.NCVT, ne)).tocsr()
        Acell = coo_matrix((np.ones(ne), (ext_cell, ii)), shape=(p3.NCELL, ne)).tocsr()
        c1 = (ext_shell > 0).astype(np.float64)
        t0 = time.perf_counter()
        lp1 = linprog(
            c1, A_ub=Acell, b_ub=rep_capacity_flat,
            A_eq=Aeq, b_eq=nominal_demand.reshape(-1),
            bounds=(0.0, None), method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                "time_limit": float(time_limit_seconds),
            },
        )
        stage1_wall = time.perf_counter() - t0
        gate("XY2_nominal_Stage1_success", lp1.success, [lp1.status, lp1.message])
        halo_opt = float(lp1.fun)
        x1 = np.asarray(lp1.x, dtype=np.float64)
        gate("XY2_nominal_terminal_optimum_matches_prior",
             abs(halo_opt - EXPECTED_NOMINAL_TERMINAL_OPT_KG) <= 2e-6,
             [halo_opt, EXPECTED_NOMINAL_TERMINAL_OPT_KG])
        positive_xy2 = int(np.count_nonzero(x1[edge_cv.size:] > POSITIVE_EDGE_TOL))
        assigned_xy2 = float(np.sum(x1[edge_cv.size:]))
        gate("XY2_nominal_positive_new_edge_count_matches_prior",
             positive_xy2 == EXPECTED_XY2_POSITIVE_NOMINAL_EDGE_COUNT,
             positive_xy2)
        gate("XY2_nominal_assigned_mass_matches_prior",
             abs(assigned_xy2 - EXPECTED_XY2_NOMINAL_ASSIGNED_MASS_KG) <= 2e-6,
             [assigned_xy2, EXPECTED_XY2_NOMINAL_ASSIGNED_MASS_KG])

        stage = "design_contract_freeze"
        topology_contract = {
            "topology_name": "XY2_terminal_only_same_layer_XY_face_neighbor_extension",
            "base_support": "existing_R7_XY1_support",
            "generation_source": "existing_XY1_terminal_edges_only",
            "generation_rule": "one_nonrecursive_same_layer_plus_minus_X_plus_minus_Y_face_neighbor_ring",
            "z_neighbor_extension": False,
            "recursive_growth": False,
            "new_edge_count": int(xy2_cv.size),
            "total_edge_count": int(ext_cv.size),
            "exact_support_edge_count": int(np.count_nonzero(ext_shell == 0)),
            "terminal_edge_count": int(np.count_nonzero(ext_shell > 0)),
            "XY2_terminal_only": True,
            "XY2_transit_allowed": False,
            "transport_subsegment_mapping_changed": False,
            "transport_flow_epoch_day": 365.0,
            "residual_sidecar_semantics_changed": False,
            "CFL_changed": False,
            "physics_changed": False,
        }
        lexicographic_contract = {
            "Stage1": {
                "decision_variables": "nonnegative edge component masses on exact+XY1+XY2 representation support",
                "CV_equality": "sum edge mass per transport CV equals candidate CV component mass",
                "Cartesian_capacity": "sum edge mass per Cartesian cell <= represented capacity",
                "objective": "minimize total terminal occupancy mass",
                "exact_support_cost": 0.0,
                "XY1_terminal_cost": 1.0,
                "XY2_terminal_cost": 1.0,
                "ring_preference_penalty_added": False,
            },
            "Stage2": {
                "Stage1_optimum_fixed": True,
                "Stage1_optimum_tolerance_kg": HALO_OPT_TOL,
                "objective": "minimize full Cartesian-cell L1 distance to direct subsegment delta target",
                "objective_changed_from_R31": False,
                "capacity_constraints_changed": False,
                "CV_equalities_changed": False,
                "only_feasible_domain_changed": "add frozen XY2 terminal-only representation edges",
            },
            "lexicographic_order": [
                "1_minimize_total_terminal_occupancy_mass",
                "2_fix_Stage1_optimum_with_tolerance",
                "3_minimize_full_Cartesian_cell_L1",
            ],
        }
        pricing_contract = {
            "restricted_master_global_equivalence_condition": "all omitted terminal-edge reduced costs >= -PRICING_TOL",
            "PRICING_TOL": PRICING_TOL,
            "all_exact_support_edges_always_selected": True,
            "initial_terminal_seed": [
                "Stage1_positive_terminal_edges_XY1_or_XY2",
                "prior_accepted_positive_XY1_terminal_edges",
            ],
            "prior_XY2_mass_at_checkpoint": 0.0,
            "omitted_pricing_domain": "all unselected XY1+XY2 terminal edges",
            "selected_column_pricing_identity_must_be_validated": True,
            "omitted_terminal_reduced_cost_formula":
                "-(mu_capacity[cell] + mu_abs_pos[cell] - mu_abs_neg[cell] + (mu_halo_pos-mu_halo_neg)) - lambda_CV",
            "negative_reduced_cost_columns_added_in_batches": True,
            "full_generic_XY2_Stage2_fallback_semantics": "same frozen lexicographic LP on complete exact+XY1+XY2 support",
            "generic_fallback_execution_required_for_design_freeze": False,
        }

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / TOPOLOGY).write_bytes(jb(topology_contract))
        (out / LEXICOGRAPHIC).write_bytes(jb(lexicographic_contract))
        (out / PRICING).write_bytes(jb(pricing_contract))
        (out / GATES).write_bytes(csvb(gates))

        classification = "P3R1_R7_XY2_TERMINAL_ONLY_SAME_LAYER_TOPOLOGY_AND_FROZEN_LEXICOGRAPHIC_STAGE1_STAGE2_DESIGN_CERTIFIED_NOMINAL_XY2_SHADOW_MAPBACK_AUTHORIZED"
        recommendation = (
            "Execute one read-only nominal XY2 shadow mapback from the preserved R7 checkpoint: "
            "solve frozen XY2 Stage1, then the frozen Stage2 Cartesian-L1 restricted master with full XY1+XY2 omitted-column pricing. "
            "Do not mutate the checkpoint or resume Day380 transport until global Stage2 optimality is certified."
        )
        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R7R1R1_commit": PARENT,
            "R7_checkpoint_sha256": R7_CHECKPOINT_SHA,
            "R7_checkpoint_day": R7_PARENT_DAY,
            "R7_checkpoint_accepted_steps": R7_ACCEPTED_STEPS,
            "R7R1R1_status_bound": R7R1R1_STATUS,
            "R7R1R1_classification_bound": R7R1R1_CLASS,
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "topology_contract": TOPOLOGY,
            "lexicographic_contract": LEXICOGRAPHIC,
            "pricing_contract": PRICING,
            "XY2_new_edge_count": int(xy2_cv.size),
            "XY2_total_edge_count": int(ext_cv.size),
            "nominal_Stage1_terminal_mass_optimum_kg": halo_opt,
            "nominal_Stage1_wall_seconds": stage1_wall,
            "nominal_positive_XY2_edge_count": positive_xy2,
            "nominal_XY2_assigned_mass_kg": assigned_xy2,
            "XY2_topology_design_frozen": True,
            "lexicographic_objective_design_frozen": True,
            "nominal_XY2_shadow_mapback_authorized": True,
            "XY2_execution_in_recurrent_transport_authorized": False,
            "R7_checkpoint_resume_transport_authorized": False,
            "Day380_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "recommended_next_action": recommendation,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R32_recurrent_semantics_remain_authoritative": True,
            "R7_checkpoint_must_be_preserved": True,
            "restart_from_Day375_authorized": False,
            "XY2_topology_design_frozen": True,
            "XY2_terminal_only": True,
            "XY2_transit_forbidden": True,
            "XY2_same_layer_XY_face_neighbor_only": True,
            "XY2_nonrecursive_single_additional_ring": True,
            "Stage1_exact_cost_zero": True,
            "Stage1_XY1_and_XY2_terminal_cost_equal_one": True,
            "Stage2_full_Cartesian_L1_objective_preserved": True,
            "Stage2_full_omitted_XY1_XY2_dual_pricing_required": True,
            "nominal_XY2_shadow_mapback_authorized": True,
            "XY2_execution_in_recurrent_transport_authorized": False,
            "R7_checkpoint_resume_transport_authorized": False,
            "Day380_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "residual_sidecar_change_authorized": False,
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
        print("XY2 new edges:", int(xy2_cv.size))
        print("Nominal Stage1 terminal optimum kg:", halo_opt)
        print("XY2 topology design frozen: True")
        print("Lexicographic design frozen: True")
        print("Nominal XY2 shadow mapback authorized: True")
        print("R7 transport resume authorized: False")
        print("Day380 pilot authorized: False")
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
                "nominal_XY2_shadow_mapback_authorized": False,
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
    ap.add_argument("--time-limit-seconds", type=float, default=120.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.time_limit_seconds))
