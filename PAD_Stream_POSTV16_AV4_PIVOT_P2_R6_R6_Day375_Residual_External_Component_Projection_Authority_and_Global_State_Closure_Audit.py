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
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-PIVOT-P2-R6-R6"
MILESTONE_NAME = "Day375 Residual External-Component Projection Authority and Global State-Closure Audit"

STATUS_PASS = (
    "AV4PIVOTP2R6R6_DAY375_RESIDUAL_EXTERNAL_COMPONENT_PROJECTION_AUTHORITY_"
    "AND_GLOBAL_STATE_CLOSURE_AUDIT_PASS_READ_ONLY"
)
STATUS_BLOCKED = "AV4PIVOTP2R6R6_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_BRANCH = "postv16-av4-pivot"
EXPECTED_PARENT = "90dec7bcf84afac9d1ff4751a55a2ef06e4f1600"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NCV = 200
NCV_TOTAL = NSL * NCV

DAY = 375.0
BACKGROUND = 0.20
MAX_SG = 0.60

CELL_TOL_KG = 1.0e-7
CV_TOL_KG = 1.0e-7
LEDGER_TOL_KG = 1.0e-6
SIGN_TOL_KG = 1.0e-10
SHA256_R5_PROVISIONAL = "1553445022f7267d7802f8833d5440d7521433a4cd8b7c06652cffeb6d693e57"

EXPECTED_RESIDUAL_CELLS = 3456
EXPECTED_RESIDUAL_LOWER_CELLS = 60
EXPECTED_RESIDUAL_UPPER_CELLS = 3396
EXPECTED_RESIDUAL_CVS = 58187
EXPECTED_R5_LOCAL_CVS = 78

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R5_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_FixedExternal_Local_Projection"
R5_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R5_Summary.json"
R5_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R5_Decision_Contract.json"
R5_STATE = "POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz"
R5_RESIDUAL_CELLS = "POSTV16_AV4_PIVOT_P2_R6_R5_Residual_Cell_Bound_Audit.csv"
R5_RESIDUAL_CVS = "POSTV16_AV4_PIVOT_P2_R6_R5_Residual_CV_Audit.csv"
R5_ACCEPTED_STATE = "POSTV16_AV4_PIVOT_P2_R6_R5_Accepted_Day375_State.npz"

R5_STATUS = (
    "AV4PIVOTP2R6R5_CONTROLLED_DAY375_TERMINAL_SINK_FIXED_EXTERNAL_RECURRENT_"
    "ELIGIBILITY_EXACT_CV_CONSERVATIVE_LOCAL_PROJECTION_EXECUTION_PASS"
)
R5_CLASSIFICATION = "R5_LOCAL_REPAIR_PASS_RESIDUAL_EXTERNAL_COMPONENT_VIOLATIONS_REQUIRE_STATE_CLOSURE"
R5_EXPECTED_NEXT_NAME = MILESTONE_NAME

DAY370_REL = BASE_AV4 / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
DAY370_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"
DAY370_STATE = "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
DAY370_STATUS = (
    "AV4PIVOTP2R5G2AR4R1R1R1_COMPLETED_COMPONENT_CELL_MEMBERSHIP_IDENTITY_"
    "REPAIR_AND_COMPONENT_FRONTIER_PROJECTION_EXECUTION_PASS"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL = BASE_AV4 / (
    "POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_"
    "Projection_Authority_and_Global_State_Closure_Audit"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R6_BLOCKED"

R5_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_"
    "TerminalSink_FixedExternal_RecurrentEligibility_Exact_CVConservative_"
    "Projection_Execution.py"
)
R5_RUNNER_BLOB = "f71002179eddc7636693c5a91abdbcc0222a33c6"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R5_RUNNER: R5_RUNNER_BLOB,
    R2SRC: R2SRC_BLOB,
}


class GateError(RuntimeError):
    pass


class DSU:
    def __init__(self, n: int):
        self.p = np.arange(n, dtype=np.int64)
        self.r = np.zeros(n, dtype=np.int8)

    def find(self, x: int) -> int:
        while int(self.p[x]) != x:
            self.p[x] = self.p[int(self.p[x])]
            x = int(self.p[x])
        return x

    def union(self, a: int, b: int) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        if self.r[ra] == self.r[rb]:
            self.r[ra] += 1


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    sio = io.StringIO(newline="")
    writer = csv.DictWriter(sio, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return sio.getvalue().encode("utf-8")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def scalar(x: Any) -> float:
    return float(np.asarray(x).reshape(()))


def as_int_set(x: np.ndarray) -> set[int]:
    return set(int(v) for v in np.asarray(x, dtype=np.int64).reshape(-1).tolist())


def self_test() -> None:
    assert NCELL == 37500
    assert NCV_TOTAL == 215600
    assert EXPECTED_RESIDUAL_CELLS == 3456
    assert EXPECTED_RESIDUAL_CVS == 58187
    # Tiny deterministic bipartite-component test.
    cvs = [10, 11, 12]
    cells = [100, 101, 200]
    cv_local = {v: i for i, v in enumerate(cvs)}
    cell_local = {v: i for i, v in enumerate(cells)}
    dsu = DSU(len(cvs) + len(cells))
    off = len(cvs)
    dsu.union(cv_local[10], off + cell_local[100])
    dsu.union(cv_local[11], off + cell_local[100])
    dsu.union(cv_local[12], off + cell_local[200])
    roots = {dsu.find(cv_local[v]) for v in cvs}
    assert len(roots) == 2
    # Aggregate relaxed bound test.
    fixed = np.asarray([2.0, 3.0])
    cap = np.asarray([10.0, 20.0])
    lo = float(np.sum(-fixed))
    hi = float(np.sum(cap - fixed))
    mass = 12.0
    assert lo <= mass <= hi
    print("POSTV16 AV4 PIVOT P2-R6-R6 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gate_rows: list[dict[str, Any]] = []

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        detail = "" if value is None else repr(value)
        gate_rows.append({"stage": stage, "gate": name, "pass": ok, "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("=" * 204)
    print("POSTV16-AV4-PIVOT-P2-R6-R6 -- DAY375 RESIDUAL EXTERNAL-COMPONENT PROJECTION AUTHORITY AND GLOBAL STATE-CLOSURE AUDIT")
    print("=" * 204)
    print("READ-ONLY AUTHORITY AUDIT. THE SUCCESSFUL R5 78-CV LOCAL REPAIR IS IMMUTABLE.")
    print("NO PROJECTION SOLVE. NO STATE MUTATION. NO NEW H2 CELLS. NO SUPPORT GROWTH. NO PRESSURE REFRESH. NO TIME ADVANCE. NO P3.")
    print("R6-R6 DECOMPOSES THE EXACT R5 RESIDUAL CV/CELL GRAPH AND FREEZES THE INPUT AUTHORITY FOR THE NEXT PROJECTION-SEMANTICS MILESTONE.")
    print()

    try:
        stage = "formal_outcome_firewall"
        pass_summary = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R6_Summary.json"
        block_report = block_dir / "POSTV16_AV4_PIVOT_P2_R6_R6_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6-R6 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R6R6_BLOCK", not block_report.exists(), str(block_report))

        stage = "repository_authority"
        gate("repository_branch_exact", git_text(root, "branch", "--show-current") == EXPECTED_BRANCH)
        gate(
            "repository_parent_is_R5_PASS_commit",
            git_text(root, "rev-parse", "HEAD^") == EXPECTED_PARENT,
            git_text(root, "rev-parse", "HEAD^"),
        )
        gate("repository_clean", git_text(root, "status", "--porcelain") == "", repr(git_text(root, "status", "--porcelain")))
        for filename, expected_blob in SOURCE_BLOBS.items():
            p = root / filename
            actual = git_text(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_git_blob_exact", actual == expected_blob, actual)

        stage = "R5_PASS_binding"
        r5dir = drive / R5_REL
        r5_summary_path = r5dir / R5_SUMMARY
        r5_decision_path = r5dir / R5_DECISION
        r5_state_path = r5dir / R5_STATE
        r5_cell_csv = r5dir / R5_RESIDUAL_CELLS
        r5_cv_csv = r5dir / R5_RESIDUAL_CVS
        r5_accepted = r5dir / R5_ACCEPTED_STATE

        for label, path in (
            ("R5_summary", r5_summary_path),
            ("R5_decision", r5_decision_path),
            ("R5_provisional_state", r5_state_path),
            ("R5_residual_cell_audit", r5_cell_csv),
            ("R5_residual_CV_audit", r5_cv_csv),
        ):
            gate(label + "_present", path.is_file(), str(path))
        gate("R5_accepted_state_absent", not r5_accepted.exists(), str(r5_accepted))

        r5s = load_json(r5_summary_path)
        r5d = load_json(r5_decision_path)

        gate("R5_status_exact", r5s.get("status") == R5_STATUS, r5s.get("status"))
        gate("R5_classification_exact", r5s.get("classification") == R5_CLASSIFICATION, r5s.get("classification"))
        gate("R5_full_Day375_state_not_accepted", r5s.get("full_Day375_state_accepted") is False)
        gate("R5_local_component_CV_count_exact", int(r5s.get("local_component_CV_count", -1)) == EXPECTED_R5_LOCAL_CVS)
        gate("R5_residual_cell_count_exact", int(r5s.get("post_R5_residual_violation_cell_count", -1)) == EXPECTED_RESIDUAL_CELLS)
        gate("R5_residual_lower_count_exact", int(r5s.get("post_R5_residual_lower_violation_count", -1)) == EXPECTED_RESIDUAL_LOWER_CELLS)
        gate("R5_residual_upper_count_exact", int(r5s.get("post_R5_residual_upper_violation_count", -1)) == EXPECTED_RESIDUAL_UPPER_CELLS)
        gate("R5_residual_culprit_CV_count_exact", int(r5s.get("post_R5_residual_culprit_CV_count", -1)) == EXPECTED_RESIDUAL_CVS)
        gate("R5_global_CV_residual_within_tolerance", float(r5s.get("maximum_global_CV_residual_kg", 1.0)) <= CV_TOL_KG)
        gate("R5_global_mass_ledger_within_tolerance", abs(float(r5s.get("global_mass_residual_kg", 1.0))) <= LEDGER_TOL_KG)
        gate("R5_residuals_outside_local_authority", r5s.get("all_residual_violations_outside_R5_local_authority") is True)
        gate("R5_no_new_cells", int(r5s.get("new_cartesian_cell_count", -1)) == 0)
        gate("R5_no_vertical_support", r5s.get("vertical_support_used") is False)
        gate("R5_no_diagonal_support", r5s.get("diagonal_support_used") is False)
        gate("R5_no_halo_transit", r5s.get("halo_transit_used") is False)
        gate("R5_no_pressure_refresh", r5s.get("pressure_refresh_executed") is False)

        gate("R5_decision_classification_exact", r5d.get("classification") == R5_CLASSIFICATION)
        gate("R5_R6R6_authorized", r5d.get("P2_R6_R6_authorized") is True)
        gate("R5_R6R6_name_exact", r5d.get("P2_R6_R6_name") == R5_EXPECTED_NEXT_NAME, r5d.get("P2_R6_R6_name"))
        gate("R5_restart_not_authorized", r5d.get("P2_continuation_restart_authorized_now") is False)
        gate("R5_external_state_closure_required", r5d.get("residual_external_state_closure_required") is True)
        gate("R5_support_growth_not_authorized", r5d.get("support_growth_authorized") is False)
        gate("R5_new_H2_cells_not_authorized", r5d.get("new_H2_cells_authorized") is False)
        gate("R5_pressure_refresh_not_authorized", r5d.get("pressure_refresh_authorized") is False)
        gate("R5_P3_false", r5d.get("P3_authorized") is False)
        gate("R5_P4_false", r5d.get("P4_authorized") is False)
        gate("R5_P5_false", r5d.get("P5_training_authorized") is False)

        state_sha_before = sha256_file(r5_state_path)
        gate("R5_provisional_SHA_hard_bound", state_sha_before == SHA256_R5_PROVISIONAL, state_sha_before)
        gate("R5_provisional_SHA_summary_exact", state_sha_before == r5s.get("provisional_state_sha256"), state_sha_before)
        gate("R5_provisional_SHA_decision_exact", state_sha_before == r5d.get("provisional_local_repair_state_sha256"), state_sha_before)

        with np.load(r5_state_path, allow_pickle=False) as z:
            r5state = {k: np.asarray(z[k]).copy() for k in z.files}

        gate("R5_state_day_exact", abs(scalar(r5state["day"]) - DAY) <= 1.0e-12, scalar(r5state["day"]))

        pair_cv = np.asarray(r5state["existing_pair_cv"], dtype=np.int64).reshape(-1)
        pair_cell = np.asarray(r5state["existing_pair_cell"], dtype=np.int64).reshape(-1)
        pair_original = np.asarray(r5state["original_existing_pair_contribution_kg"], dtype=np.float64).reshape(-1)
        pair_current = np.asarray(r5state["locally_repaired_existing_pair_contribution_kg"], dtype=np.float64).reshape(-1)
        local_hcv = np.asarray(r5state["local_halo_cv"], dtype=np.int64).reshape(-1)
        local_hcell = np.asarray(r5state["local_halo_cell"], dtype=np.int64).reshape(-1)
        local_hmass = np.asarray(r5state["local_halo_contribution_kg"], dtype=np.float64).reshape(-1)
        local_component_cv = np.asarray(r5state["local_component_cv"], dtype=np.int64).reshape(-1)
        provisional = np.asarray(r5state["provisional_grid_component_mass_kg"], dtype=np.float64).reshape(-1)
        residual_lower_state = np.asarray(r5state["residual_lower_cell"], dtype=np.int64).reshape(-1)
        residual_upper_state = np.asarray(r5state["residual_upper_cell"], dtype=np.int64).reshape(-1)
        residual_lower_cv_state = np.asarray(r5state["residual_lower_cv"], dtype=np.int64).reshape(-1)
        residual_upper_cv_state = np.asarray(r5state["residual_upper_cv"], dtype=np.int64).reshape(-1)
        parent_pressure_state = np.asarray(r5state["parent_pressure_psi"], dtype=np.float64)

        gate("pair_array_lengths_exact", len(pair_cv) == len(pair_cell) == len(pair_original) == len(pair_current))
        gate("local_H2_array_lengths_exact", len(local_hcv) == len(local_hcell) == len(local_hmass))
        gate("provisional_grid_shape_exact", provisional.size == NCELL, provisional.shape)
        gate("R5_local_component_size_exact", len(np.unique(local_component_cv)) == EXPECTED_R5_LOCAL_CVS)
        gate("pair_CV_range", bool(np.all((pair_cv >= 0) & (pair_cv < NCV_TOTAL))))
        gate("pair_cell_range", bool(np.all((pair_cell >= 0) & (pair_cell < NCELL))))
        gate("local_H2_CV_range", bool(np.all((local_hcv >= 0) & (local_hcv < NCV_TOTAL))))
        gate("local_H2_cell_range", bool(np.all((local_hcell >= 0) & (local_hcell < NCELL))))

        stage = "Day370_frozen_H2_binding"
        d370dir = drive / DAY370_REL
        d370sum_path = d370dir / DAY370_SUMMARY
        d370state_path = d370dir / DAY370_STATE
        gate("Day370_summary_present", d370sum_path.is_file(), str(d370sum_path))
        gate("Day370_state_present", d370state_path.is_file(), str(d370state_path))
        d370s = load_json(d370sum_path)
        gate("Day370_status_exact", d370s.get("status") == DAY370_STATUS, d370s.get("status"))
        gate("Day370_state_SHA_exact", sha256_file(d370state_path) == d370s.get("accepted_state_sha256"))

        with np.load(d370state_path, allow_pickle=False) as z:
            d370 = {k: np.asarray(z[k]).copy() for k in z.files}
        old_grid = np.asarray(d370["grid_component_mass_kg"], dtype=np.float64).reshape(-1)
        frozen_halo_cv = np.asarray(d370["halo_cv"], dtype=np.int64).reshape(-1)
        frozen_halo_cell = np.asarray(d370["halo_cell"], dtype=np.int64).reshape(-1)
        gate("Day370_day_exact", abs(scalar(d370["day"]) - 370.0) <= 1.0e-12)
        gate("Day370_grid_shape_exact", old_grid.size == NCELL)
        gate("frozen_H2_array_lengths_exact", len(frozen_halo_cv) == len(frozen_halo_cell))
        gate("frozen_H2_CV_range", bool(np.all((frozen_halo_cv >= 0) & (frozen_halo_cv < NCV_TOTAL))))
        gate("frozen_H2_cell_range", bool(np.all((frozen_halo_cell >= 0) & (frozen_halo_cell < NCELL))))

        stage = "physical_capacity_reconstruction"
        a2dir = drive / A2E_REL
        a2sum_path = a2dir / A2E_SUMMARY
        a2epoch_path = a2dir / A2E_EPOCH
        gate("A2E_summary_present", a2sum_path.is_file(), str(a2sum_path))
        gate("A2E_epoch_present", a2epoch_path.is_file(), str(a2epoch_path))
        a2s = load_json(a2sum_path)
        gate("A2E_status_exact", a2s.get("status") == A2E_STATUS, a2s.get("status"))
        with np.load(a2epoch_path, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}
        parent_pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        grid_pv = np.asarray(epoch["pore_volume_m3"], dtype=np.float64)
        p_ref = scalar(epoch["reference_gas_pressure_pa"])
        gate("parent_pressure_shape_exact", parent_pressure.shape == GRID, parent_pressure.shape)
        gate("grid_pv_shape_exact", grid_pv.shape == GRID, grid_pv.shape)
        gate(
            "R5_parent_pressure_identity",
            float(np.max(np.abs(parent_pressure_state - parent_pressure))) <= 1.0e-12,
            float(np.max(np.abs(parent_pressure_state - parent_pressure))),
        )

        r2 = load_module(root / R2SRC, "p2r6r6_r2")
        sat_max = np.full(GRID, BACKGROUND + MAX_SG, dtype=np.float64)
        rho_max = np.asarray(r2.gas_density_from_state(sat_max, parent_pressure, p_ref), dtype=np.float64)
        capacity = (grid_pv * rho_max * MAX_SG).reshape(-1)
        gate("capacity_finite", bool(np.all(np.isfinite(capacity))))
        gate("capacity_positive", bool(np.all(capacity > 0.0)), float(np.min(capacity)))

        stage = "R5_residual_exact_reproduction"
        post_lower = provisional < -CELL_TOL_KG
        post_upper = provisional > capacity + CELL_TOL_KG
        residual_lower = np.flatnonzero(post_lower).astype(np.int64)
        residual_upper = np.flatnonzero(post_upper).astype(np.int64)
        residual_cells = np.union1d(residual_lower, residual_upper).astype(np.int64)

        gate("recomputed_residual_lower_exact", np.array_equal(residual_lower, np.sort(np.unique(residual_lower_state))))
        gate("recomputed_residual_upper_exact", np.array_equal(residual_upper, np.sort(np.unique(residual_upper_state))))
        gate("recomputed_residual_cell_count_exact", len(residual_cells) == EXPECTED_RESIDUAL_CELLS, len(residual_cells))
        gate("recomputed_residual_lower_count_exact", len(residual_lower) == EXPECTED_RESIDUAL_LOWER_CELLS, len(residual_lower))
        gate("recomputed_residual_upper_count_exact", len(residual_upper) == EXPECTED_RESIDUAL_UPPER_CELLS, len(residual_upper))

        lower_culprit = np.unique(
            pair_cv[post_lower[pair_cell] & (pair_current < -SIGN_TOL_KG)]
        ).astype(np.int64)
        upper_culprit = np.unique(
            pair_cv[post_upper[pair_cell] & (pair_current > SIGN_TOL_KG)]
        ).astype(np.int64)
        residual_cvs = np.union1d(lower_culprit, upper_culprit).astype(np.int64)
        gate("recomputed_lower_culprit_CVs_exact", np.array_equal(lower_culprit, np.sort(np.unique(residual_lower_cv_state))))
        gate("recomputed_upper_culprit_CVs_exact", np.array_equal(upper_culprit, np.sort(np.unique(residual_upper_cv_state))))
        gate("recomputed_residual_CV_count_exact", len(residual_cvs) == EXPECTED_RESIDUAL_CVS, len(residual_cvs))

        local_set = as_int_set(local_component_cv)
        residual_set = as_int_set(residual_cvs)
        gate("residual_CVs_disjoint_from_R5_local_component", residual_set.isdisjoint(local_set))
        gate("residual_CVs_have_no_R5_local_H2_mass", not bool(np.any(np.isin(local_hcv, residual_cvs))))
        nonlocal_pair = np.isin(pair_cv, residual_cvs)
        gate(
            "R5_nonlocal_existing_pair_values_immutable",
            float(np.max(np.abs(pair_current[nonlocal_pair] - pair_original[nonlocal_pair]))) <= 1.0e-12,
            float(np.max(np.abs(pair_current[nonlocal_pair] - pair_original[nonlocal_pair]))),
        )

        cell_rows_r5 = read_csv(r5_cell_csv)
        cv_rows_r5 = read_csv(r5_cv_csv)
        csv_cells = np.asarray(sorted(int(r["flat_cell"]) for r in cell_rows_r5), dtype=np.int64)
        csv_cvs = np.asarray(sorted(int(r["cv_id"]) for r in cv_rows_r5), dtype=np.int64)
        gate("R5_residual_cell_CSV_exact", np.array_equal(csv_cells, residual_cells))
        gate("R5_residual_CV_CSV_exact", np.array_equal(csv_cvs, residual_cvs))

        current_cv_transfer = np.bincount(pair_cv, weights=pair_current, minlength=NCV_TOTAL)
        current_cv_transfer += np.bincount(local_hcv, weights=local_hmass, minlength=NCV_TOTAL)
        reconstructed_grid = old_grid + np.bincount(pair_cell, weights=pair_current, minlength=NCELL)
        reconstructed_grid += np.bincount(local_hcell, weights=local_hmass, minlength=NCELL)
        gate(
            "R5_provisional_grid_exactly_reconstructed",
            float(np.max(np.abs(reconstructed_grid - provisional))) <= CELL_TOL_KG,
            float(np.max(np.abs(reconstructed_grid - provisional))),
        )
        global_ledger = float(np.sum(provisional) - (np.sum(old_grid) + np.sum(current_cv_transfer)))
        gate("R5_global_mass_ledger_reproduced", abs(global_ledger) <= LEDGER_TOL_KG, global_ledger)

        stage = "residual_bipartite_component_decomposition"
        residual_mask_cv = np.zeros(NCV_TOTAL, dtype=bool)
        residual_mask_cv[residual_cvs] = True

        pair_mask = residual_mask_cv[pair_cv]
        res_pair_cv = pair_cv[pair_mask]
        res_pair_cell = pair_cell[pair_mask]

        halo_mask = residual_mask_cv[frozen_halo_cv]
        raw_hcv = frozen_halo_cv[halo_mask]
        raw_hcell = frozen_halo_cell[halo_mask]
        frozen_edge_keys = np.unique(raw_hcv.astype(np.int64) * NCELL + raw_hcell.astype(np.int64))
        res_hcv = (frozen_edge_keys // NCELL).astype(np.int64)
        res_hcell = (frozen_edge_keys % NCELL).astype(np.int64)

        candidate_cells = np.union1d(np.unique(res_pair_cell), np.unique(res_hcell)).astype(np.int64)
        gate("residual_candidate_cell_domain_nonempty", len(candidate_cells) > 0)
        gate("all_residual_CVs_have_existing_pair_support", len(np.unique(res_pair_cv)) == len(residual_cvs))
        gate("all_residual_violation_cells_inside_candidate_domain", set(residual_cells.tolist()).issubset(set(candidate_cells.tolist())))

        cv_local = {int(cv): i for i, cv in enumerate(residual_cvs.tolist())}
        cell_local = {int(c): i for i, c in enumerate(candidate_cells.tolist())}
        dsu = DSU(len(residual_cvs) + len(candidate_cells))
        off = len(residual_cvs)

        for cv, c in zip(res_pair_cv.tolist(), res_pair_cell.tolist()):
            dsu.union(cv_local[int(cv)], off + cell_local[int(c)])
        for cv, c in zip(res_hcv.tolist(), res_hcell.tolist()):
            dsu.union(cv_local[int(cv)], off + cell_local[int(c)])

        root_to_cvs: dict[int, list[int]] = {}
        for cv in residual_cvs.tolist():
            root = dsu.find(cv_local[int(cv)])
            root_to_cvs.setdefault(root, []).append(int(cv))

        root_to_cells: dict[int, set[int]] = {r: set() for r in root_to_cvs}
        for cv, c in zip(res_pair_cv.tolist(), res_pair_cell.tolist()):
            root = dsu.find(cv_local[int(cv)])
            root_to_cells[root].add(int(c))
        for cv, c in zip(res_hcv.tolist(), res_hcell.tolist()):
            root = dsu.find(cv_local[int(cv)])
            root_to_cells[root].add(int(c))

        roots_sorted = sorted(root_to_cvs, key=lambda r: min(root_to_cvs[r]))
        root_to_component = {root: i for i, root in enumerate(roots_sorted)}
        cv_to_component: dict[int, int] = {}
        cell_to_component: dict[int, int] = {}
        for root in roots_sorted:
            cid = root_to_component[root]
            for cv in root_to_cvs[root]:
                cv_to_component[cv] = cid
            for c in root_to_cells[root]:
                if c in cell_to_component and cell_to_component[c] != cid:
                    raise GateError(f"candidate_cell_owned_by_multiple_components:{c}")
                cell_to_component[c] = cid

        gate("every_residual_CV_has_one_component", len(cv_to_component) == len(residual_cvs))
        gate("every_residual_cell_has_one_component", all(int(c) in cell_to_component for c in residual_cells.tolist()))
        gate("component_count_positive", len(roots_sorted) > 0, len(roots_sorted))

        # R5 local cell footprint is fixed external occupancy for every residual component.
        local_pair_cells = pair_cell[np.isin(pair_cv, local_component_cv)]
        r5_local_cells = set(np.unique(np.r_[local_pair_cells, local_hcell]).astype(np.int64).tolist())

        residual_lower_set = set(residual_lower.tolist())
        residual_upper_set = set(residual_upper.tolist())
        lower_culprit_set = set(lower_culprit.tolist())
        upper_culprit_set = set(upper_culprit.tolist())

        component_rows: list[dict[str, Any]] = []
        cv_owner_rows: list[dict[str, Any]] = []
        cell_owner_rows: list[dict[str, Any]] = []

        aggregate_deficit_components = 0
        no_h2_edge_components = 0
        no_positive_h2_slack_components = 0
        upper_excess_no_positive_h2_slack_components = 0
        total_current_h2_slack = 0.0
        total_residual_lower_kg = 0.0
        total_residual_upper_kg = 0.0

        for root in roots_sorted:
            cid = root_to_component[root]
            comp_cvs = np.asarray(sorted(root_to_cvs[root]), dtype=np.int64)
            comp_cells = np.asarray(sorted(root_to_cells[root]), dtype=np.int64)
            comp_mask = np.isin(pair_cv, comp_cvs)
            comp_pair_idx = np.flatnonzero(comp_mask)
            comp_pair_cv = pair_cv[comp_pair_idx]
            comp_pair_cell = pair_cell[comp_pair_idx]
            comp_pair_val = pair_current[comp_pair_idx]
            comp_nonzero = np.abs(comp_pair_val) > SIGN_TOL_KG

            hmask = np.isin(res_hcv, comp_cvs)
            comp_hcv = res_hcv[hmask]
            comp_hcell = res_hcell[hmask]
            comp_hcells_unique = np.unique(comp_hcell).astype(np.int64)

            current_component_delta = np.bincount(
                comp_pair_cell, weights=comp_pair_val, minlength=NCELL
            )
            fixed_mass = provisional[comp_cells] - current_component_delta[comp_cells]
            lo_bound = float(np.sum(-fixed_mass))
            hi_bound = float(np.sum(capacity[comp_cells] - fixed_mass))
            transfer_mass = float(np.sum(current_cv_transfer[comp_cvs]))
            lo_margin = transfer_mass - lo_bound
            hi_margin = hi_bound - transfer_mass
            aggregate_ok = (lo_margin >= -CELL_TOL_KG) and (hi_margin >= -CELL_TOL_KG)
            if not aggregate_ok:
                aggregate_deficit_components += 1

            comp_res_cells = np.asarray(
                sorted(c for c in comp_cells.tolist() if c in residual_lower_set or c in residual_upper_set),
                dtype=np.int64,
            )
            lower_kg = float(np.sum(np.maximum(0.0, -provisional[comp_res_cells]))) if len(comp_res_cells) else 0.0
            upper_kg = float(np.sum(np.maximum(0.0, provisional[comp_res_cells] - capacity[comp_res_cells]))) if len(comp_res_cells) else 0.0
            total_residual_lower_kg += lower_kg
            total_residual_upper_kg += upper_kg

            if len(comp_hcells_unique):
                current_h2_slack = float(np.sum(np.maximum(0.0, capacity[comp_hcells_unique] - provisional[comp_hcells_unique])))
                h2_lower_recovery = float(np.sum(np.maximum(0.0, -provisional[comp_hcells_unique])))
            else:
                current_h2_slack = 0.0
                h2_lower_recovery = 0.0
                no_h2_edge_components += 1
            total_current_h2_slack += current_h2_slack
            if current_h2_slack <= CELL_TOL_KG:
                no_positive_h2_slack_components += 1
                if upper_kg > CELL_TOL_KG:
                    upper_excess_no_positive_h2_slack_components += 1

            cvs_with_h2 = len(np.unique(comp_hcv))
            shared_r5_cells = len(set(comp_cells.tolist()).intersection(r5_local_cells))
            residual_violation_h2_cells = len(
                set(comp_hcells_unique.tolist()).intersection(set(comp_res_cells.tolist()))
            )

            if not aggregate_ok:
                component_classification = "RELAXED_SAME_SUPPORT_AGGREGATE_CAPACITY_DEFICIT"
            elif len(comp_hcv) == 0:
                component_classification = "RELAXED_SAME_SUPPORT_AGGREGATE_OK_NO_BASELINE_H2_EDGES"
            elif current_h2_slack <= CELL_TOL_KG:
                component_classification = "RELAXED_SAME_SUPPORT_AGGREGATE_OK_NO_CURRENT_POSITIVE_H2_SLACK"
            else:
                component_classification = "RELAXED_SAME_SUPPORT_AGGREGATE_OK_BASELINE_H2_SLACK_PRESENT"

            component_rows.append({
                "component_id": cid,
                "minimum_cv_id": int(comp_cvs[0]),
                "maximum_cv_id": int(comp_cvs[-1]),
                "cv_count": int(len(comp_cvs)),
                "existing_pair_count": int(len(comp_pair_idx)),
                "nonzero_existing_variable_count": int(np.sum(comp_nonzero)),
                "baseline_H2_candidate_edge_count": int(len(comp_hcv)),
                "CVs_with_baseline_H2_edges": int(cvs_with_h2),
                "CVs_without_baseline_H2_edges": int(len(comp_cvs) - cvs_with_h2),
                "candidate_cell_count": int(len(comp_cells)),
                "candidate_H2_unique_cell_count": int(len(comp_hcells_unique)),
                "candidate_cells_shared_with_fixed_R5_local_footprint": int(shared_r5_cells),
                "residual_violation_cell_count": int(len(comp_res_cells)),
                "residual_lower_cell_count": int(sum(int(c) in residual_lower_set for c in comp_res_cells.tolist())),
                "residual_upper_cell_count": int(sum(int(c) in residual_upper_set for c in comp_res_cells.tolist())),
                "residual_lower_deficit_kg": lower_kg,
                "residual_upper_excess_kg": upper_kg,
                "component_total_CV_transfer_kg": transfer_mass,
                "relaxed_same_support_lower_bound_kg": lo_bound,
                "relaxed_same_support_upper_bound_kg": hi_bound,
                "relaxed_lower_margin_kg": lo_margin,
                "relaxed_upper_margin_kg": hi_margin,
                "relaxed_same_support_aggregate_capacity_sufficient": bool(aggregate_ok),
                "current_positive_H2_mapped_slack_kg": current_h2_slack,
                "current_H2_mapped_lower_recovery_room_kg": h2_lower_recovery,
                "residual_violation_cells_in_H2_domain": int(residual_violation_h2_cells),
                "classification": component_classification,
            })

            for cv in comp_cvs.tolist():
                cv_owner_rows.append({
                    "cv_id": int(cv),
                    "streamline": int(cv // NCV),
                    "cv_node": int(cv % NCV),
                    "component_id": cid,
                    "lower_residual_culprit": bool(int(cv) in lower_culprit_set),
                    "upper_residual_culprit": bool(int(cv) in upper_culprit_set),
                    "baseline_H2_candidate_edge_count": int(np.sum(comp_hcv == int(cv))),
                    "current_step_transfer_kg": float(current_cv_transfer[int(cv)]),
                    "R5_local_component": False,
                })

        for c in residual_cells.tolist():
            cid = cell_to_component[int(c)]
            cell_owner_rows.append({
                "flat_cell": int(c),
                "k": int(c // (NY * NX)),
                "j": int((c % (NY * NX)) // NX),
                "i": int(c % NX),
                "component_id": int(cid),
                "provisional_mass_kg": float(provisional[int(c)]),
                "capacity_kg": float(capacity[int(c)]),
                "lower_violation_kg": max(0.0, -float(provisional[int(c)])),
                "upper_violation_kg": max(0.0, float(provisional[int(c)] - capacity[int(c)])),
                "inside_fixed_R5_local_footprint": bool(int(c) in r5_local_cells),
            })

        gate("component_CV_rows_exact", len(cv_owner_rows) == EXPECTED_RESIDUAL_CVS, len(cv_owner_rows))
        gate("component_residual_cell_rows_exact", len(cell_owner_rows) == EXPECTED_RESIDUAL_CELLS, len(cell_owner_rows))
        gate(
            "component_lower_deficit_reconciles_global",
            abs(total_residual_lower_kg - float(np.sum(np.maximum(0.0, -provisional[residual_lower])))) <= 1.0e-8,
        )
        gate(
            "component_upper_excess_reconciles_global",
            abs(total_residual_upper_kg - float(np.sum(np.maximum(0.0, provisional[residual_upper] - capacity[residual_upper])))) <= 1.0e-8,
        )

        all_aggregate_ok = aggregate_deficit_components == 0

        stage = "authority_freeze_artifact_publication"
        local = Path("/content") / "PAD_Stream_AV4_PIVOT_P2_R6_R6_Final_Artifacts"
        if local.exists():
            shutil.rmtree(local)
        local.mkdir(parents=True)

        component_path = local / "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_Component_Audit.csv"
        cv_owner_path = local / "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv"
        cell_owner_path = local / "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_Cell_Component_Ownership.csv"
        component_path.write_bytes(csv_bytes(component_rows))
        cv_owner_path.write_bytes(csv_bytes(cv_owner_rows))
        cell_owner_path.write_bytes(csv_bytes(cell_owner_rows))

        component_sha = sha256_file(component_path)
        cv_owner_sha = sha256_file(cv_owner_path)
        cell_owner_sha = sha256_file(cell_owner_path)

        if all_aggregate_ok:
            classification = (
                "R6R6_RESIDUAL_GRAPH_AUDITED_EXISTING_H2_TOPOLOGY_RELAXED_AGGREGATE_"
                "CAPACITY_SUFFICIENT_EXACT_PROJECTION_SEMANTICS_FREEZE_REQUIRED"
            )
        else:
            classification = (
                "R6R6_RESIDUAL_GRAPH_AUDITED_RELAXED_SAME_SUPPORT_CAPACITY_DEFICIT_"
                "TARGETED_ELIGIBILITY_SEMANTICS_FREEZE_REQUIRED"
            )

        projection_authority = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "audit_only": True,
            "projection_solve_executed": False,
            "state_mutation_executed": False,
            "immutable_parent_state": {
                "R5_provisional_state_sha256": state_sha_before,
                "R5_local_component_CV_count": EXPECTED_R5_LOCAL_CVS,
                "R5_local_repair_must_remain_fixed": True,
            },
            "successor_variable_ownership": {
                "variable_CVs": "exact residual CVs listed in POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv",
                "component_partition": "exact connected components of residual CVs through existing pair cells plus frozen Day370 H2 candidate cells",
                "existing_pair_variables": "only nonzero existing pair contributions belonging to the selected residual component; original sign must be preserved",
                "baseline_H2_variables": "only frozen Day370 H2 edges belonging to the selected residual component; contribution must be nonnegative",
                "R5_local_existing_pair_values": "fixed exactly at R5 accepted local-repair values",
                "R5_local_H2_values": "fixed exactly at R5 accepted local-repair values",
                "all_other_components": "fixed external occupancy during a component-local solve unless a later freeze explicitly authorizes a coupled solve",
                "shared_R5_cells": "allowed only as fixed external occupancy; no variable ownership transfers to or from the R5 local component",
            },
            "required_exact_successor_constraints": [
                "per-CV component-mass equality",
                "Cartesian cell lower mass bound",
                "Cartesian pressure-dependent upper mass capacity",
                "existing-pair sign preservation",
                "baseline-H2 nonnegativity",
                "exact R5 local-repair immutability",
                "global component-mass ledger closure",
            ],
            "forbidden_in_R6_R6": [
                "projection optimization",
                "accepted-state publication",
                "continuation restart",
                "new Cartesian cells",
                "new H2 cells",
                "support growth",
                "vertical support",
                "diagonal support",
                "halo transit",
                "pressure refresh",
                "Darcy/Pollock/TOF regeneration",
                "time advance",
                "P3",
                "P4",
                "P5 training",
            ],
            "audit_interpretation": {
                "relaxed_same_support_aggregate_capacity_test_is_not_exact_projection_feasibility": True,
                "exact_sign_preserving_CV_level_feasibility_remains_for_successor_freeze_and_execution": True,
                "component_count": len(component_rows),
                "aggregate_deficit_component_count": aggregate_deficit_components,
                "all_components_relaxed_same_support_aggregate_capacity_sufficient": all_aggregate_ok,
            },
            "manifest_sha256": {
                "component_audit": component_sha,
                "CV_component_ownership": cv_owner_sha,
                "cell_component_ownership": cell_owner_sha,
            },
        }
        authority_path = local / "POSTV16_AV4_PIVOT_P2_R6_R6_Projection_Authority_Contract.json"
        authority_path.write_bytes(json_bytes(projection_authority))
        authority_sha = sha256_file(authority_path)

        summary = {
            "milestone": MILESTONE,
            "name": MILESTONE_NAME,
            "status": STATUS_PASS,
            "classification": classification,
            "read_only_audit": True,
            "projection_solve_executed": False,
            "state_mutation_executed": False,
            "R5_provisional_state_sha256": state_sha_before,
            "R5_local_repair_held_fixed": True,
            "residual_violation_cell_count": len(residual_cells),
            "residual_lower_violation_cell_count": len(residual_lower),
            "residual_upper_violation_cell_count": len(residual_upper),
            "residual_culprit_CV_count": len(residual_cvs),
            "residual_connected_component_count": len(component_rows),
            "residual_candidate_cell_count": len(candidate_cells),
            "residual_frozen_H2_candidate_edge_count": len(res_hcv),
            "components_without_baseline_H2_edges": no_h2_edge_components,
            "components_without_positive_current_H2_slack": no_positive_h2_slack_components,
            "components_with_upper_excess_and_no_positive_current_H2_slack": upper_excess_no_positive_h2_slack_components,
            "components_with_relaxed_same_support_aggregate_capacity_deficit": aggregate_deficit_components,
            "all_components_relaxed_same_support_aggregate_capacity_sufficient": all_aggregate_ok,
            "total_current_positive_H2_mapped_slack_kg": total_current_h2_slack,
            "total_residual_lower_deficit_kg": total_residual_lower_kg,
            "total_residual_upper_excess_kg": total_residual_upper_kg,
            "component_audit_sha256": component_sha,
            "CV_component_ownership_sha256": cv_owner_sha,
            "cell_component_ownership_sha256": cell_owner_sha,
            "projection_authority_contract_sha256": authority_sha,
            "new_cartesian_cell_count": 0,
            "support_growth_executed": False,
            "vertical_support_used": False,
            "diagonal_support_used": False,
            "halo_transit_used": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "R5_provisional_state_sha256": state_sha_before,
            "R5_local_repair_remains_immutable": True,
            "P2_R6_R7_authorized": True,
            "P2_R6_R7_name": "Day375 Residual External-Component Exact Projection Semantics Freeze",
            "P2_R6_R7_execution_authorized": False,
            "P2_R6_R7_may_design_targeted_recurrent_eligibility_if_required": bool(not all_aggregate_ok),
            "P2_R6_R7_must_bind_R6R6_component_manifest": True,
            "P2_continuation_restart_authorized_now": False,
            "projection_execution_authorized_now": False,
            "accepted_Day375_state_authorized_now": False,
            "support_growth_execution_authorized": False,
            "new_H2_cells_execution_authorized": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (local / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R6_Summary.json").write_bytes(json_bytes(summary))
        (local / "POSTV16_AV4_PIVOT_P2_R6_R6_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local / "POSTV16_AV4_PIVOT_P2_R6_R6_Final_Gate_Matrix.csv").write_bytes(csv_bytes(gate_rows))

        # Verify read-only parent-state identity again immediately before publication.
        state_sha_after = sha256_file(r5_state_path)
        gate("R5_provisional_state_SHA_unchanged_after_audit", state_sha_after == state_sha_before, state_sha_after)

        manifest_rows: list[dict[str, Any]] = []
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest_rows.append({
                    "file": str(p.relative_to(local)).replace("\\", "/"),
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        (local / "POSTV16_AV4_PIVOT_P2_R6_R6_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest_rows))

        if out.exists():
            raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(local, out)

        print()
        print("=" * 204)
        print("POSTV16-AV4-PIVOT-P2-R6-R6: PASS")
        print("Classification                                      :", classification)
        print("R5 provisional SHA                                  :", state_sha_before)
        print("Residual CVs / cells                                :", len(residual_cvs), "/", len(residual_cells))
        print("Residual lower / upper cells                        :", len(residual_lower), "/", len(residual_upper))
        print("Residual connected components                       :", len(component_rows))
        print("Frozen residual H2 candidate edges                  :", len(res_hcv))
        print("Relaxed aggregate-deficit components                :", aggregate_deficit_components)
        print("Components without baseline H2 edges                :", no_h2_edge_components)
        print("Components upper-excess / no positive H2 slack      :", upper_excess_no_positive_h2_slack_components)
        print("Projection solve executed                            : False")
        print("R5 local repair changed                              : False")
        print("P2-R6-R7 authorized                                 : True")
        print("Continuation restart authorized                      : False")
        print("P3 authorized                                       : False")
        print("=" * 204)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        report = block_dir / "POSTV16_AV4_PIVOT_P2_R6_R6_Blocked_Report.json"
        if not report.exists():
            report.write_text(
                json.dumps({
                    "milestone": MILESTONE,
                    "status": STATUS_BLOCKED,
                    "failed_stage": stage,
                    "exception": repr(exc),
                    "read_only_audit": True,
                    "state_mutation_executed": False,
                    "automatic_rerun_authorized": False,
                    "support_growth_authorized": False,
                    "new_H2_cells_authorized": False,
                    "pressure_refresh_authorized": False,
                    "time_advance_authorized": False,
                    "P3_authorized": False,
                    "P4_authorized": False,
                    "P5_training_authorized": False,
                    "gates_completed": gate_rows,
                }, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(MILESTONE + ": BLOCKED")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
