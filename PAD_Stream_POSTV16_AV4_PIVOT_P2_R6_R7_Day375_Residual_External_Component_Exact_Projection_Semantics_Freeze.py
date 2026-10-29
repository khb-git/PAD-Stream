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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R6-R7"
MILESTONE_NAME = "Day375 Residual External-Component Exact Projection Semantics Freeze"

STATUS_PASS = (
    "AV4PIVOTP2R6R7_DAY375_RESIDUAL_EXTERNAL_COMPONENT_EXACT_PROJECTION_"
    "SEMANTICS_FREEZE_PASS_NO_STATE_MUTATION"
)
STATUS_BLOCKED = "AV4PIVOTP2R6R7_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_BRANCH = "postv16-av4-pivot"
EXPECTED_PARENT = "b508bd80f9d0d0e48927ed6940c5c21526a10b8c"

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
SLACK_CV_TOL_KG = 1.0e-7
SLACK_TOTAL_ABS_TOL_KG = 1.0e-6
SLACK_TOTAL_REL_TOL = 1.0e-12

EXPECTED_R6R6_COMPONENTS = 158
EXPECTED_RESIDUAL_CVS = 58187
EXPECTED_RESIDUAL_CELLS = 3456
EXPECTED_R6R6_AGGREGATE_DEFICIT_COMPONENTS = 17
EXPECTED_R6R6_NO_BASELINE_H2_COMPONENTS = 108
EXPECTED_R6R6_UPPER_NO_SLACK_COMPONENTS = 85

R5_PROVISIONAL_SHA256 = "1553445022f7267d7802f8833d5440d7521433a4cd8b7c06652cffeb6d693e57"

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R6R6_REL = BASE_AV4 / (
    "POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_"
    "Projection_Authority_and_Global_State_Closure_Audit"
)
R6R6_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R6_Summary.json"
R6R6_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R6_Decision_Contract.json"
R6R6_COMPONENTS = "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_Component_Audit.csv"
R6R6_CV_OWNERS = "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv"
R6R6_CELL_OWNERS = "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_Cell_Component_Ownership.csv"
R6R6_AUTHORITY = "POSTV16_AV4_PIVOT_P2_R6_R6_Projection_Authority_Contract.json"

R6R6_STATUS = (
    "AV4PIVOTP2R6R6_DAY375_RESIDUAL_EXTERNAL_COMPONENT_PROJECTION_AUTHORITY_"
    "AND_GLOBAL_STATE_CLOSURE_AUDIT_PASS_READ_ONLY"
)
R6R6_CLASSIFICATION = (
    "R6R6_RESIDUAL_GRAPH_AUDITED_RELAXED_SAME_SUPPORT_CAPACITY_DEFICIT_"
    "TARGETED_ELIGIBILITY_SEMANTICS_FREEZE_REQUIRED"
)
R6R7_NAME = MILESTONE_NAME

R5_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_FixedExternal_Local_Projection"
R5_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R5_Summary.json"
R5_STATE = "POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz"
R5_STATUS = (
    "AV4PIVOTP2R6R5_CONTROLLED_DAY375_TERMINAL_SINK_FIXED_EXTERNAL_RECURRENT_"
    "ELIGIBILITY_EXACT_CV_CONSERVATIVE_LOCAL_PROJECTION_EXECUTION_PASS"
)

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
    "POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_"
    "Exact_Projection_Semantics_Freeze"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R7_BLOCKED"

R6R6_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_"
    "Projection_Authority_and_Global_State_Closure_Audit.py"
)
R6R6_RUNNER_BLOB = "c46c8c3cdb35087fcbd2879b8121b2154cae0b0d"

R4_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R4_Day375_TerminalSink_FixedExternal_"
    "RecurrentEligibility_Prospective_Repair_Semantics_Freeze.py"
)
R4_RUNNER_BLOB = "02c5cc227075c4e64b856909545cd1ecbc1daf23"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R6R6_RUNNER: R6R6_RUNNER_BLOB,
    R4_RUNNER: R4_RUNNER_BLOB,
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
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (p.stdout or "").strip()


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


def ijk(flat: int) -> tuple[int, int, int]:
    k = flat // (NY * NX)
    rem = flat % (NY * NX)
    j = rem // NX
    i = rem % NX
    return k, j, i


def flat_of(k: int, j: int, i: int) -> int:
    return k * (NY * NX) + j * NX + i


def h2xy_from_cells(cells: np.ndarray, global_s0_set: set[int]) -> set[int]:
    out: set[int] = set()
    for c in np.asarray(cells, dtype=np.int64).reshape(-1).tolist():
        k, j, i = ijk(int(c))
        for dj in range(-2, 3):
            for di in range(-2, 3):
                d = abs(di) + abs(dj)
                if not (1 <= d <= 2):
                    continue
                jj = j + dj
                ii = i + di
                if not (0 <= jj < NY and 0 <= ii < NX):
                    continue
                h = flat_of(k, jj, ii)
                if h in global_s0_set:
                    continue
                out.add(int(h))
    return out


def self_test() -> None:
    assert EXPECTED_R6R6_COMPONENTS == 158
    assert EXPECTED_RESIDUAL_CVS == 58187
    assert EXPECTED_RESIDUAL_CELLS == 3456
    assert EXPECTED_R6R6_AGGREGATE_DEFICIT_COMPONENTS == 17
    assert flat_of(*ijk(12345)) == 12345
    # Same-layer-only radius-2 geometry.
    s0 = {flat_of(3, 20, 20)}
    h = h2xy_from_cells(np.asarray(list(s0), dtype=np.int64), s0)
    assert all(ijk(x)[0] == 3 for x in h)
    assert flat_of(3, 20, 22) in h
    assert flat_of(4, 20, 20) not in h
    print("POSTV16 AV4 PIVOT P2-R6-R7 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gate_rows: list[dict[str, Any]] = []

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gate_rows.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if value is None else repr(value),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("=" * 210)
    print("POSTV16-AV4-PIVOT-P2-R6-R7 -- DAY375 RESIDUAL EXTERNAL-COMPONENT EXACT PROJECTION SEMANTICS FREEZE")
    print("=" * 210)
    print("DESIGN/FREEZE + READ-ONLY FEASIBILITY AUDIT ONLY. NO DAY375 STATE MUTATION. NO ACCEPTED STATE.")
    print("R5 LOCAL REPAIR IS IMMUTABLE. NO NEW CARTESIAN CELLS. NO PRESSURE REFRESH. NO TIME ADVANCE. NO P3.")
    print("TARGETED RECURRENT ELIGIBILITY MAY BE DESIGNED ONLY INSIDE THE ALREADY FROZEN DAY370 H2 CELL DOMAIN.")
    print()

    try:
        stage = "formal_outcome_firewall"
        pass_summary = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R7_Summary.json"
        block_report = block_dir / "POSTV16_AV4_PIVOT_P2_R6_R7_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6-R7 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R6R7_BLOCK", not block_report.exists(), str(block_report))

        stage = "repository_authority"
        gate("repository_branch_exact", git_text(root, "branch", "--show-current") == EXPECTED_BRANCH)
        gate(
            "repository_parent_is_R6R6_PASS_commit",
            git_text(root, "rev-parse", "HEAD^") == EXPECTED_PARENT,
            git_text(root, "rev-parse", "HEAD^"),
        )
        gate("repository_clean", git_text(root, "status", "--porcelain") == "", repr(git_text(root, "status", "--porcelain")))
        for filename, expected_blob in SOURCE_BLOBS.items():
            p = root / filename
            actual = git_text(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_git_blob_exact", actual == expected_blob, actual)

        stage = "R6R6_PASS_binding"
        r6dir = drive / R6R6_REL
        paths = {
            "summary": r6dir / R6R6_SUMMARY,
            "decision": r6dir / R6R6_DECISION,
            "components": r6dir / R6R6_COMPONENTS,
            "cv_owners": r6dir / R6R6_CV_OWNERS,
            "cell_owners": r6dir / R6R6_CELL_OWNERS,
            "authority": r6dir / R6R6_AUTHORITY,
        }
        for label, p in paths.items():
            gate(f"R6R6_{label}_present", p.is_file(), str(p))

        r6s = load_json(paths["summary"])
        r6d = load_json(paths["decision"])
        r6a = load_json(paths["authority"])
        comp_rows = read_csv(paths["components"])
        cv_owner_rows = read_csv(paths["cv_owners"])
        cell_owner_rows = read_csv(paths["cell_owners"])

        gate("R6R6_status_exact", r6s.get("status") == R6R6_STATUS, r6s.get("status"))
        gate("R6R6_classification_exact", r6s.get("classification") == R6R6_CLASSIFICATION, r6s.get("classification"))
        gate("R6R6_component_count_exact", int(r6s["residual_connected_component_count"]) == EXPECTED_R6R6_COMPONENTS)
        gate("R6R6_residual_CVs_exact", int(r6s["residual_culprit_CV_count"]) == EXPECTED_RESIDUAL_CVS)
        gate("R6R6_residual_cells_exact", int(r6s["residual_violation_cell_count"]) == EXPECTED_RESIDUAL_CELLS)
        gate(
            "R6R6_aggregate_deficit_components_exact",
            int(r6s["components_with_relaxed_same_support_aggregate_capacity_deficit"]) == EXPECTED_R6R6_AGGREGATE_DEFICIT_COMPONENTS,
        )
        gate(
            "R6R6_no_baseline_H2_components_exact",
            int(r6s["components_without_baseline_H2_edges"]) == EXPECTED_R6R6_NO_BASELINE_H2_COMPONENTS,
        )
        gate(
            "R6R6_upper_no_slack_components_exact",
            int(r6s["components_with_upper_excess_and_no_positive_current_H2_slack"]) == EXPECTED_R6R6_UPPER_NO_SLACK_COMPONENTS,
        )
        gate("R6R6_projection_not_executed", r6s.get("projection_solve_executed") is False)
        gate("R6R6_R5_local_fixed", r6s.get("R5_local_repair_held_fixed") is True)
        gate("R6R6_P3_false", r6s.get("P3_authorized") is False)
        gate("R6R6_R7_authorized", r6d.get("P2_R6_R7_authorized") is True)
        gate("R6R6_R7_name_exact", r6d.get("P2_R6_R7_name") == R6R7_NAME, r6d.get("P2_R6_R7_name"))
        gate("R6R6_R7_execution_false", r6d.get("P2_R6_R7_execution_authorized") is False)
        gate("R6R6_restart_false", r6d.get("P2_continuation_restart_authorized_now") is False)
        gate("R6R6_projection_execution_false", r6d.get("projection_execution_authorized_now") is False)
        gate("R6R6_support_growth_false", r6d.get("support_growth_execution_authorized") is False)
        gate("R6R6_new_H2_cells_false", r6d.get("new_H2_cells_execution_authorized") is False)
        gate("R6R6_pressure_false", r6d.get("pressure_refresh_authorized") is False)
        gate("R6R6_authority_audit_only", r6a.get("audit_only") is True)
        gate("R6R6_authority_R5_fixed", r6a["immutable_parent_state"]["R5_local_repair_must_remain_fixed"] is True)

        component_sha = sha256_file(paths["components"])
        cv_owner_sha = sha256_file(paths["cv_owners"])
        cell_owner_sha = sha256_file(paths["cell_owners"])
        authority_sha = sha256_file(paths["authority"])
        gate("R6R6_component_manifest_SHA_exact", component_sha == r6s["component_audit_sha256"], component_sha)
        gate("R6R6_CV_owner_manifest_SHA_exact", cv_owner_sha == r6s["CV_component_ownership_sha256"], cv_owner_sha)
        gate("R6R6_cell_owner_manifest_SHA_exact", cell_owner_sha == r6s["cell_component_ownership_sha256"], cell_owner_sha)
        gate("R6R6_authority_contract_SHA_exact", authority_sha == r6s["projection_authority_contract_sha256"], authority_sha)

        gate("R6R6_component_rows_exact", len(comp_rows) == EXPECTED_R6R6_COMPONENTS, len(comp_rows))
        gate("R6R6_CV_owner_rows_exact", len(cv_owner_rows) == EXPECTED_RESIDUAL_CVS, len(cv_owner_rows))
        gate("R6R6_cell_owner_rows_exact", len(cell_owner_rows) == EXPECTED_RESIDUAL_CELLS, len(cell_owner_rows))

        component_ids = sorted(int(r["component_id"]) for r in comp_rows)
        gate("R6R6_component_ids_contiguous", component_ids == list(range(EXPECTED_R6R6_COMPONENTS)), component_ids[:8])

        stage = "R5_and_Day370_state_binding"
        r5dir = drive / R5_REL
        r5sum_path = r5dir / R5_SUMMARY
        r5state_path = r5dir / R5_STATE
        gate("R5_summary_present", r5sum_path.is_file(), str(r5sum_path))
        gate("R5_state_present", r5state_path.is_file(), str(r5state_path))
        r5s = load_json(r5sum_path)
        gate("R5_status_exact", r5s.get("status") == R5_STATUS, r5s.get("status"))
        r5_sha_before = sha256_file(r5state_path)
        gate("R5_provisional_SHA_exact", r5_sha_before == R5_PROVISIONAL_SHA256, r5_sha_before)

        with np.load(r5state_path, allow_pickle=False) as z:
            state = {k: np.asarray(z[k]).copy() for k in z.files}
        gate("R5_day_exact", abs(scalar(state["day"]) - DAY) <= 1.0e-12)

        pair_cv = np.asarray(state["existing_pair_cv"], dtype=np.int64).reshape(-1)
        pair_cell = np.asarray(state["existing_pair_cell"], dtype=np.int64).reshape(-1)
        pair_current = np.asarray(state["locally_repaired_existing_pair_contribution_kg"], dtype=np.float64).reshape(-1)
        provisional = np.asarray(state["provisional_grid_component_mass_kg"], dtype=np.float64).reshape(-1)
        r5_local_cv = np.asarray(state["local_component_cv"], dtype=np.int64).reshape(-1)
        r5_local_hcv = np.asarray(state["local_halo_cv"], dtype=np.int64).reshape(-1)
        r5_local_hcell = np.asarray(state["local_halo_cell"], dtype=np.int64).reshape(-1)
        r5_local_hmass = np.asarray(state["local_halo_contribution_kg"], dtype=np.float64).reshape(-1)
        parent_pressure_state = np.asarray(state["parent_pressure_psi"], dtype=np.float64)

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
        frozen_edge_keys = np.unique(frozen_halo_cv.astype(np.int64) * NCELL + frozen_halo_cell.astype(np.int64))
        frozen_hcv = (frozen_edge_keys // NCELL).astype(np.int64)
        frozen_hcell = (frozen_edge_keys % NCELL).astype(np.int64)
        frozen_edge_set = set((int(a), int(b)) for a, b in zip(frozen_hcv.tolist(), frozen_hcell.tolist()))
        frozen_halo_domain = set(int(x) for x in np.unique(frozen_hcell).tolist())

        stage = "capacity_reconstruction"
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
        gate("parent_pressure_identity", float(np.max(np.abs(parent_pressure - parent_pressure_state))) <= 1.0e-12)

        r2 = load_module(root / R2SRC, "p2r6r7_r2")
        sat_max = np.full(GRID, BACKGROUND + MAX_SG, dtype=np.float64)
        rho_max = np.asarray(r2.gas_density_from_state(sat_max, parent_pressure, p_ref), dtype=np.float64)
        capacity = (grid_pv * rho_max * MAX_SG).reshape(-1)
        gate("capacity_finite_positive", bool(np.all(np.isfinite(capacity)) and np.all(capacity > 0.0)))

        # Exact R6-R6 CV ownership.
        cv_to_component = {int(r["cv_id"]): int(r["component_id"]) for r in cv_owner_rows}
        residual_cvs = np.asarray(sorted(cv_to_component), dtype=np.int64)
        residual_set = set(int(x) for x in residual_cvs.tolist())
        gate("R6R6_CV_owner_unique_exact", len(cv_to_component) == EXPECTED_RESIDUAL_CVS)
        gate("residual_CVs_disjoint_R5_local", residual_set.isdisjoint(set(int(x) for x in r5_local_cv.tolist())))
        gate("residual_CVs_no_R5_local_H2", not bool(np.any(np.isin(r5_local_hcv, residual_cvs))))

        component_cvs: dict[int, np.ndarray] = {}
        for cid in range(EXPECTED_R6R6_COMPONENTS):
            component_cvs[cid] = np.asarray(
                sorted(cv for cv, owner in cv_to_component.items() if owner == cid),
                dtype=np.int64,
            )
            gate(f"component_{cid}_nonempty", len(component_cvs[cid]) > 0)

        # Reconstruct current required per-CV Day375 transfer for residual CVs.
        current_cv_transfer = np.bincount(pair_cv, weights=pair_current, minlength=NCV_TOTAL)
        current_cv_transfer += np.bincount(r5_local_hcv, weights=r5_local_hmass, minlength=NCV_TOTAL)
        reconstructed = old_grid + np.bincount(pair_cell, weights=pair_current, minlength=NCELL)
        reconstructed += np.bincount(r5_local_hcell, weights=r5_local_hmass, minlength=NCELL)
        gate(
            "R5_provisional_grid_reconstruction_exact",
            float(np.max(np.abs(reconstructed - provisional))) <= CELL_TOL_KG,
            float(np.max(np.abs(reconstructed - provisional))),
        )
        ledger = float(np.sum(provisional) - (np.sum(old_grid) + np.sum(current_cv_transfer)))
        gate("R5_global_ledger_exact", abs(ledger) <= LEDGER_TOL_KG, ledger)

        global_s0_set = set(int(x) for x in np.unique(pair_cell).tolist())

        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:" + repr(exc)) from exc
        print("SciPy version:", scipy.__version__)

        def build_lp_inputs(cvs: np.ndarray, h_edges: list[tuple[int, int]], add_slack: bool):
            cvs = np.asarray(cvs, dtype=np.int64)
            cv_set = set(int(x) for x in cvs.tolist())
            pair_mask = np.isin(pair_cv, cvs)
            pidx = np.flatnonzero(pair_mask & (np.abs(pair_current) > SIGN_TOL_KG))
            xcv = pair_cv[pidx]
            xcell = pair_cell[pidx]
            x0 = pair_current[pidx]

            h_edges = sorted(set((int(a), int(b)) for a, b in h_edges if int(a) in cv_set))
            hcv = np.asarray([a for a, _ in h_edges], dtype=np.int64)
            hcell = np.asarray([b for _, b in h_edges], dtype=np.int64)

            local_cells = np.unique(np.r_[xcell, hcell]).astype(np.int64)
            if len(local_cells) == 0:
                raise GateError("empty_local_cell_domain")

            fixed_delta = np.bincount(
                pair_cell[~np.isin(pair_cv, cvs)],
                weights=pair_current[~np.isin(pair_cv, cvs)],
                minlength=NCELL,
            )
            fixed_mass = old_grid + fixed_delta + np.bincount(
                r5_local_hcell, weights=r5_local_hmass, minlength=NCELL
            )

            # If any R5-local CV were in the selected group, they would have been double-counted.
            # R6-R6 guarantees residual CVs are disjoint from R5 local authority.
            n_x = len(pidx)
            n_h = len(h_edges)
            n_cv = len(cvs)
            n_slack = 2 * n_cv if add_slack else 0
            nvar = n_x + n_h + n_slack

            cv_row = {int(cv): r for r, cv in enumerate(cvs.tolist())}
            er: list[int] = []
            ec: list[int] = []
            ev: list[float] = []
            for q, cv in enumerate(xcv.tolist()):
                er.append(cv_row[int(cv)])
                ec.append(q)
                ev.append(1.0)
            for q, cv in enumerate(hcv.tolist()):
                er.append(cv_row[int(cv)])
                ec.append(n_x + q)
                ev.append(1.0)
            if add_slack:
                splus0 = n_x + n_h
                sminus0 = splus0 + n_cv
                for r in range(n_cv):
                    er.extend([r, r])
                    ec.extend([splus0 + r, sminus0 + r])
                    ev.extend([1.0, -1.0])
            Aeq = sparse.coo_matrix(
                (np.asarray(ev), (np.asarray(er), np.asarray(ec))),
                shape=(n_cv, nvar),
            ).tocsr()
            beq = current_cv_transfer[cvs]

            cell_row = {int(c): r for r, c in enumerate(local_cells.tolist())}
            cr: list[int] = []
            cc: list[int] = []
            vv: list[float] = []
            for q, c in enumerate(xcell.tolist()):
                cr.append(cell_row[int(c)])
                cc.append(q)
                vv.append(1.0)
            for q, c in enumerate(hcell.tolist()):
                cr.append(cell_row[int(c)])
                cc.append(n_x + q)
                vv.append(1.0)
            Acell = sparse.coo_matrix(
                (np.asarray(vv), (np.asarray(cr), np.asarray(cc))),
                shape=(len(local_cells), nvar),
            ).tocsr()
            A_ub = sparse.vstack([Acell, -Acell], format="csr")
            b_ub = np.r_[
                capacity[local_cells] - fixed_mass[local_cells],
                fixed_mass[local_cells],
            ]

            bounds: list[tuple[float | None, float | None]] = []
            for v in x0.tolist():
                if v > SIGN_TOL_KG:
                    bounds.append((0.0, None))
                elif v < -SIGN_TOL_KG:
                    bounds.append((None, 0.0))
                else:
                    bounds.append((0.0, 0.0))
            bounds.extend([(0.0, None)] * n_h)
            if add_slack:
                bounds.extend([(0.0, None)] * (2 * n_cv))

            return {
                "cvs": cvs,
                "pidx": pidx,
                "xcv": xcv,
                "xcell": xcell,
                "x0": x0,
                "h_edges": h_edges,
                "hcv": hcv,
                "hcell": hcell,
                "local_cells": local_cells,
                "fixed_mass": fixed_mass,
                "n_x": n_x,
                "n_h": n_h,
                "n_cv": n_cv,
                "nvar": nvar,
                "Aeq": Aeq,
                "beq": beq,
                "Acell": Acell,
                "A_ub": A_ub,
                "b_ub": b_ub,
                "bounds": bounds,
            }

        stage = "component_baseline_exact_feasibility_and_target_diagnostics"
        baseline_rows: list[dict[str, Any]] = []
        target_manifest: list[dict[str, Any]] = []
        recurrent_edge_manifest: list[dict[str, Any]] = []
        component_baseline_edges: dict[int, list[tuple[int, int]]] = {}
        component_recurrent_edges: dict[int, list[tuple[int, int]]] = {}
        component_target_cvs: dict[int, np.ndarray] = {}
        component_prospective_cells: dict[int, np.ndarray] = {}

        baseline_exact_feasible_count = 0
        targeted_component_count = 0
        diagnostic_infeasible_count = 0

        for cid in range(EXPECTED_R6R6_COMPONENTS):
            cvs = component_cvs[cid]
            cv_set = set(int(x) for x in cvs.tolist())
            baseline_mask = np.isin(frozen_hcv, cvs)
            baseline_edges = sorted(set(
                (int(a), int(b))
                for a, b in zip(frozen_hcv[baseline_mask].tolist(), frozen_hcell[baseline_mask].tolist())
            ))
            component_baseline_edges[cid] = baseline_edges

            lpdata = build_lp_inputs(cvs, baseline_edges, add_slack=True)
            c = np.zeros(lpdata["nvar"], dtype=np.float64)
            slack0 = lpdata["n_x"] + lpdata["n_h"]
            c[slack0:] = 1.0

            lp = linprog(
                c,
                A_ub=lpdata["A_ub"],
                b_ub=lpdata["b_ub"],
                A_eq=lpdata["Aeq"],
                b_eq=lpdata["beq"],
                bounds=lpdata["bounds"],
                method="highs",
                options={"presolve": True},
            )

            diag_success = bool(lp.success)
            if diag_success:
                z = np.asarray(lp.x, dtype=np.float64)
                ncv = lpdata["n_cv"]
                splus = z[slack0:slack0 + ncv]
                sminus = z[slack0 + ncv:slack0 + 2 * ncv]
                per_cv_slack = splus + sminus
                total_slack = float(np.sum(per_cv_slack))
                max_slack = float(np.max(per_cv_slack)) if ncv else 0.0
                total_tol = max(
                    SLACK_TOTAL_ABS_TOL_KG,
                    abs(float(np.sum(lpdata["beq"]))) * SLACK_TOTAL_REL_TOL,
                )
                exact_baseline = (total_slack <= total_tol) and (max_slack <= SLACK_CV_TOL_KG)
                targets = cvs[per_cv_slack > SLACK_CV_TOL_KG]
                if exact_baseline:
                    targets = np.asarray([], dtype=np.int64)
            else:
                diagnostic_infeasible_count += 1
                total_slack = float("nan")
                max_slack = float("nan")
                exact_baseline = False
                # If fixed-external cell bounds make the slack diagnostic itself infeasible,
                # every CV in this R6-R6 component is retained as a conservative target.
                targets = cvs.copy()

            if exact_baseline:
                baseline_exact_feasible_count += 1
            else:
                targeted_component_count += 1

            component_target_cvs[cid] = np.asarray(sorted(set(int(x) for x in targets.tolist())), dtype=np.int64)

            s0_cells = np.unique(pair_cell[np.isin(pair_cv, cvs)]).astype(np.int64)
            frontier = sorted(
                int(h)
                for h in h2xy_from_cells(s0_cells, global_s0_set)
                if int(h) in frozen_halo_domain
            )
            recurrent_edges: set[tuple[int, int]] = set()
            for cv in component_target_cvs[cid].tolist():
                for h in frontier:
                    e = (int(cv), int(h))
                    if e not in frozen_edge_set:
                        recurrent_edges.add(e)
            component_recurrent_edges[cid] = sorted(recurrent_edges)

            prospective_cells = np.unique(np.r_[
                pair_cell[np.isin(pair_cv, cvs)],
                np.asarray([h for _, h in baseline_edges], dtype=np.int64),
                np.asarray([h for _, h in component_recurrent_edges[cid]], dtype=np.int64),
            ]).astype(np.int64)
            component_prospective_cells[cid] = prospective_cells

            aggregate_row = comp_rows[cid]
            baseline_rows.append({
                "component_id": cid,
                "cv_count": int(len(cvs)),
                "existing_pair_variable_count": int(lpdata["n_x"]),
                "baseline_H2_edge_count": int(len(baseline_edges)),
                "baseline_local_cell_count": int(len(lpdata["local_cells"])),
                "R6R6_relaxed_aggregate_capacity_sufficient": str(
                    aggregate_row["relaxed_same_support_aggregate_capacity_sufficient"]
                ),
                "diagnostic_LP_success": diag_success,
                "diagnostic_LP_status": int(lp.status),
                "diagnostic_LP_message": str(lp.message),
                "diagnostic_total_absolute_CV_slack_kg": total_slack,
                "diagnostic_max_absolute_CV_slack_kg": max_slack,
                "exact_baseline_support_feasible": bool(exact_baseline),
                "target_CV_count": int(len(component_target_cvs[cid])),
                "prospective_recurrent_edge_count": int(len(component_recurrent_edges[cid])),
                "prospective_recurrent_unique_sink_count": int(len(set(h for _, h in component_recurrent_edges[cid]))),
                "prospective_cell_domain_count": int(len(prospective_cells)),
            })

            for cv in component_target_cvs[cid].tolist():
                target_manifest.append({
                    "component_id": cid,
                    "cv_id": int(cv),
                    "streamline": int(cv // NCV),
                    "cv_node": int(cv % NCV),
                    "required_Day375_transfer_kg": float(current_cv_transfer[int(cv)]),
                    "baseline_H2_edge_count": int(sum(1 for a, _ in baseline_edges if a == int(cv))),
                    "new_recurrent_edge_count": int(sum(1 for a, _ in component_recurrent_edges[cid] if a == int(cv))),
                    "target_reason": (
                        "diagnostic_LP_cell_domain_infeasible_all_component_CVs_retained"
                        if not diag_success else
                        "nonzero_exact_CV_conservation_slack_under_baseline_support"
                    ),
                })

            for cv, h in component_recurrent_edges[cid]:
                k, j, i = ijk(int(h))
                recurrent_edge_manifest.append({
                    "component_id": cid,
                    "cv_id": int(cv),
                    "streamline": int(cv // NCV),
                    "cv_node": int(cv % NCV),
                    "halo_flat_cell": int(h),
                    "k": int(k),
                    "j": int(j),
                    "i": int(i),
                    "same_layer_radius2": True,
                    "endpoint_in_frozen_Day370_H2_domain": True,
                    "edge_not_in_frozen_Day370_H2_graph": True,
                    "terminal_sink_only": True,
                    "nonnegative_mass_only": True,
                })

        gate("baseline_component_audit_rows_exact", len(baseline_rows) == EXPECTED_R6R6_COMPONENTS)
        gate("targeted_component_count_nonzero", targeted_component_count > 0, targeted_component_count)
        gate(
            "all_recurrent_endpoints_in_frozen_H2_domain",
            all(int(r["halo_flat_cell"]) in frozen_halo_domain for r in recurrent_edge_manifest),
        )
        gate(
            "no_recurrent_edge_already_frozen",
            all((int(r["cv_id"]), int(r["halo_flat_cell"])) not in frozen_edge_set for r in recurrent_edge_manifest),
        )

        stage = "prospective_shared_sink_execution_group_freeze"
        comp_dsu = DSU(EXPECTED_R6R6_COMPONENTS)
        cell_to_components: dict[int, list[int]] = {}
        for cid in range(EXPECTED_R6R6_COMPONENTS):
            for c in component_prospective_cells[cid].tolist():
                cell_to_components.setdefault(int(c), []).append(cid)
        for comps in cell_to_components.values():
            unique = sorted(set(comps))
            for other in unique[1:]:
                comp_dsu.union(unique[0], other)

        root_to_components: dict[int, list[int]] = {}
        for cid in range(EXPECTED_R6R6_COMPONENTS):
            root_to_components.setdefault(comp_dsu.find(cid), []).append(cid)
        roots = sorted(root_to_components, key=lambda r: min(root_to_components[r]))
        root_to_gid = {r: i for i, r in enumerate(roots)}

        component_to_group: dict[int, int] = {}
        for r in roots:
            gid = root_to_gid[r]
            for cid in root_to_components[r]:
                component_to_group[cid] = gid

        group_rows: list[dict[str, Any]] = []
        group_feasibility_rows: list[dict[str, Any]] = []
        frozen_domain_infeasible_groups = 0
        frozen_domain_feasible_groups = 0
        groups_with_recurrent_edges = 0

        for r in roots:
            gid = root_to_gid[r]
            cids = sorted(root_to_components[r])
            cvs = np.asarray(
                sorted(
                    int(cv)
                    for cid in cids
                    for cv in component_cvs[cid].tolist()
                ),
                dtype=np.int64,
            )
            all_edges = sorted(set(
                edge
                for cid in cids
                for edge in (component_baseline_edges[cid] + component_recurrent_edges[cid])
            ))
            recurrent_edges_group = sorted(set(
                edge
                for cid in cids
                for edge in component_recurrent_edges[cid]
            ))
            if recurrent_edges_group:
                groups_with_recurrent_edges += 1

            lpdata = build_lp_inputs(cvs, all_edges, add_slack=False)
            c = np.zeros(lpdata["nvar"], dtype=np.float64)
            lp = linprog(
                c,
                A_ub=lpdata["A_ub"],
                b_ub=lpdata["b_ub"],
                A_eq=lpdata["Aeq"],
                b_eq=lpdata["beq"],
                bounds=lpdata["bounds"],
                method="highs",
                options={"presolve": True},
            )

            feasible = bool(lp.success)
            max_cv_residual = None
            max_lower_violation = None
            max_upper_violation = None
            max_sign_violation = None
            min_h2 = None

            if feasible:
                z = np.asarray(lp.x, dtype=np.float64)
                cv_res = np.asarray(lpdata["Aeq"] @ z - lpdata["beq"]).ravel()
                cell_mass = lpdata["fixed_mass"][lpdata["local_cells"]] + np.asarray(lpdata["Acell"] @ z).ravel()
                max_cv_residual = float(np.max(np.abs(cv_res))) if len(cv_res) else 0.0
                max_lower_violation = max(0.0, -float(np.min(cell_mass)))
                max_upper_violation = max(
                    0.0,
                    float(np.max(cell_mass - capacity[lpdata["local_cells"]])),
                )
                x = z[:lpdata["n_x"]]
                sign_v = 0.0
                for oldv, newv in zip(lpdata["x0"].tolist(), x.tolist()):
                    if oldv > SIGN_TOL_KG:
                        sign_v = max(sign_v, max(0.0, -float(newv)))
                    elif oldv < -SIGN_TOL_KG:
                        sign_v = max(sign_v, max(0.0, float(newv)))
                max_sign_violation = sign_v
                h = z[lpdata["n_x"]:lpdata["n_x"] + lpdata["n_h"]]
                min_h2 = float(np.min(h)) if len(h) else 0.0
                feasible = (
                    max_cv_residual <= CV_TOL_KG
                    and max_lower_violation <= CELL_TOL_KG
                    and max_upper_violation <= CELL_TOL_KG
                    and max_sign_violation <= SIGN_TOL_KG
                    and min_h2 >= -SIGN_TOL_KG
                )

            if feasible:
                frozen_domain_feasible_groups += 1
            else:
                frozen_domain_infeasible_groups += 1

            prospective_cells = np.unique(np.r_[
                *[component_prospective_cells[cid] for cid in cids]
            ]).astype(np.int64)
            shared_cells = sum(
                1 for c in prospective_cells.tolist()
                if len(set(cell_to_components.get(int(c), []))) > 1
            )
            group_rows.append({
                "execution_group_id": gid,
                "R6R6_component_count": int(len(cids)),
                "minimum_R6R6_component_id": int(min(cids)),
                "maximum_R6R6_component_id": int(max(cids)),
                "R6R6_component_ids": ";".join(str(x) for x in cids),
                "CV_count": int(len(cvs)),
                "candidate_cell_count": int(len(prospective_cells)),
                "shared_candidate_cell_count": int(shared_cells),
                "baseline_H2_edge_count": int(sum(len(component_baseline_edges[cid]) for cid in cids)),
                "new_recurrent_edge_count": int(len(recurrent_edges_group)),
                "target_CV_count": int(sum(len(component_target_cvs[cid]) for cid in cids)),
            })
            group_feasibility_rows.append({
                "execution_group_id": gid,
                "component_count": int(len(cids)),
                "CV_count": int(len(cvs)),
                "existing_pair_variable_count": int(lpdata["n_x"]),
                "total_H2_edge_count": int(lpdata["n_h"]),
                "local_cell_count": int(len(lpdata["local_cells"])),
                "new_recurrent_edge_count": int(len(recurrent_edges_group)),
                "exact_frozen_domain_feasible": bool(feasible),
                "HiGHS_success": bool(lp.success),
                "HiGHS_status": int(lp.status),
                "HiGHS_message": str(lp.message),
                "maximum_CV_residual_kg": max_cv_residual,
                "maximum_cell_lower_violation_kg": max_lower_violation,
                "maximum_cell_upper_violation_kg": max_upper_violation,
                "maximum_existing_sign_violation_kg": max_sign_violation,
                "minimum_H2_variable_kg": min_h2,
            })

        gate("execution_group_partition_complete", sum(int(r["R6R6_component_count"]) for r in group_rows) == EXPECTED_R6R6_COMPONENTS)
        gate("execution_group_count_positive", len(group_rows) > 0, len(group_rows))

        all_groups_feasible = frozen_domain_infeasible_groups == 0

        stage = "artifact_publication"
        local = Path("/content") / "PAD_Stream_AV4_PIVOT_P2_R6_R7_Final_Artifacts"
        if local.exists():
            shutil.rmtree(local)
        local.mkdir(parents=True)

        baseline_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Baseline_Exact_Feasibility_Audit.csv"
        target_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv"
        edge_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Recurrent_Eligibility_Edges.csv"
        group_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv"
        group_feas_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Group_Exact_Feasibility_Audit.csv"

        baseline_path.write_bytes(csv_bytes(baseline_rows))
        target_path.write_bytes(csv_bytes(target_manifest))
        edge_path.write_bytes(csv_bytes(recurrent_edge_manifest))
        group_path.write_bytes(csv_bytes(group_rows))
        group_feas_path.write_bytes(csv_bytes(group_feasibility_rows))

        hashes = {
            "baseline_exact_feasibility": sha256_file(baseline_path),
            "target_CVs": sha256_file(target_path),
            "recurrent_eligibility_edges": sha256_file(edge_path),
            "prospective_execution_groups": sha256_file(group_path),
            "group_exact_feasibility": sha256_file(group_feas_path),
        }

        if all_groups_feasible:
            classification = (
                "R6R7_EXACT_FROZEN_DOMAIN_PROJECTION_SEMANTICS_FROZEN_"
                "ALL_PROSPECTIVE_EXECUTION_GROUPS_FEASIBLE_EXECUTION_NEXT"
            )
            next_name = "Controlled Day375 Residual External-Component Exact CV-Conservative Projection Execution"
            successor_execution_authorized = True
            support_extension_design_authorized = False
        else:
            classification = (
                "R6R7_EXACT_FROZEN_DOMAIN_PROJECTION_SEMANTICS_FROZEN_"
                "RESIDUAL_GROUPS_REMAIN_INFEASIBLE_MINIMAL_SUPPORT_EXTENSION_DESIGN_REQUIRED"
            )
            next_name = "Day375 Residual Frozen-Domain Infeasibility Localization and Minimal Support-Extension Design Freeze"
            successor_execution_authorized = False
            support_extension_design_authorized = True

        design = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "design_freeze_only": True,
            "state_mutation_executed": False,
            "immutable_authority": {
                "R6R6_parent_commit": EXPECTED_PARENT,
                "R5_provisional_state_sha256": r5_sha_before,
                "R5_local_repair_must_remain_fixed": True,
                "R6R6_component_manifest_sha256": component_sha,
                "R6R6_CV_component_ownership_sha256": cv_owner_sha,
                "R6R6_cell_component_ownership_sha256": cell_owner_sha,
                "R6R6_projection_authority_sha256": authority_sha,
            },
            "baseline_exact_feasibility_semantics": {
                "variable_existing_pairs": "nonzero exact existing CV-cell contributions for the selected R6R6 component/group only",
                "existing_pair_sign_preservation": True,
                "existing_zero_pairs_remain_zero": True,
                "baseline_H2_edges": "exact frozen Day370 H2 edges belonging to selected CVs",
                "baseline_H2_nonnegative": True,
                "per_CV_mass_equality": True,
                "cartesian_lower_mass_bound_kg": 0.0,
                "cartesian_upper_mass_bound": "exact Day365-pressure physical gas capacity",
                "all_external_contributions_fixed": True,
                "R5_local_repair_fixed": True,
            },
            "targeted_recurrent_eligibility_semantics": {
                "target_selection": "CVs with diagnostic absolute conservation slack > 1e-7 kg; if diagnostic LP itself is cell-domain infeasible, retain all CVs in that component",
                "geometry": "same-layer XY Manhattan graph radius 1-2 from exact component existing-pair S0 support",
                "endpoint_domain": "already frozen Day370 H2 cell domain only",
                "new_cartesian_cells": 0,
                "vertical_edges": False,
                "diagonal_edges": False,
                "halo_transit": False,
                "new_edge_mass_sign": "nonnegative terminal deposition only",
                "fixed_external_terminal_sink_capacity": True,
                "shared_new_sink_rule": "components whose prospective variable cell domains overlap are coupled into one exact execution group",
            },
            "successor_execution_semantics_if_authorized": {
                "solve_unit": "exact R6R7 prospective execution group",
                "groups_independent_only_when_variable_cell_domains_are_disjoint": True,
                "lexicographic_objective": [
                    "1_minimize_total_H2_terminal_deposition_mass_over_baseline_plus_R6R7_recurrent_edges",
                    "2_within_stage1_optimum_minimize_total_mass_on_R6R7_new_recurrent_edges",
                    "3_within_stage1_and_stage2_optima_minimize_L1_deviation_of_existing_nonzero_pair_contributions",
                ],
                "hard_constraints": [
                    "exact per-CV mass conservation",
                    "exact Cartesian lower/upper mass bounds",
                    "existing-pair sign preservation",
                    "baseline and recurrent H2 nonnegativity",
                    "R5 local repair immutability",
                    "global component-mass ledger closure",
                ],
                "no_clipping": True,
                "no_global_renormalization": True,
                "pressure_refresh": False,
            },
            "manifests": {
                "baseline_exact_feasibility": baseline_path.name,
                "baseline_exact_feasibility_sha256": hashes["baseline_exact_feasibility"],
                "target_CVs": target_path.name,
                "target_CVs_sha256": hashes["target_CVs"],
                "recurrent_eligibility_edges": edge_path.name,
                "recurrent_eligibility_edges_sha256": hashes["recurrent_eligibility_edges"],
                "prospective_execution_groups": group_path.name,
                "prospective_execution_groups_sha256": hashes["prospective_execution_groups"],
                "group_exact_feasibility": group_feas_path.name,
                "group_exact_feasibility_sha256": hashes["group_exact_feasibility"],
            },
        }

        summary = {
            "milestone": MILESTONE,
            "name": MILESTONE_NAME,
            "status": STATUS_PASS,
            "classification": classification,
            "design_freeze_only": True,
            "state_mutation_executed": False,
            "accepted_Day375_state_created": False,
            "R5_provisional_state_sha256": r5_sha_before,
            "R5_local_repair_held_fixed": True,
            "R6R6_component_count": EXPECTED_R6R6_COMPONENTS,
            "residual_CV_count": EXPECTED_RESIDUAL_CVS,
            "baseline_exact_feasible_component_count": baseline_exact_feasible_count,
            "targeted_recurrent_component_count": targeted_component_count,
            "diagnostic_LP_infeasible_component_count": diagnostic_infeasible_count,
            "target_CV_count": len(target_manifest),
            "new_recurrent_eligibility_edge_count": len(recurrent_edge_manifest),
            "new_recurrent_unique_sink_count": len(set(int(r["halo_flat_cell"]) for r in recurrent_edge_manifest)),
            "prospective_execution_group_count": len(group_rows),
            "prospective_groups_with_recurrent_edges": groups_with_recurrent_edges,
            "exact_frozen_domain_feasible_group_count": frozen_domain_feasible_groups,
            "exact_frozen_domain_infeasible_group_count": frozen_domain_infeasible_groups,
            "all_prospective_execution_groups_exact_frozen_domain_feasible": all_groups_feasible,
            "new_cartesian_cell_count": 0,
            "H2_endpoint_domain_changed": False,
            "vertical_support_used": False,
            "diagonal_support_used": False,
            "halo_transit_used": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "baseline_exact_feasibility_sha256": hashes["baseline_exact_feasibility"],
            "target_CVs_sha256": hashes["target_CVs"],
            "recurrent_eligibility_edges_sha256": hashes["recurrent_eligibility_edges"],
            "prospective_execution_groups_sha256": hashes["prospective_execution_groups"],
            "group_exact_feasibility_sha256": hashes["group_exact_feasibility"],
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "P2_R6_R8_authorized": True,
            "P2_R6_R8_name": next_name,
            "P2_R6_R8_projection_execution_authorized": successor_execution_authorized,
            "P2_R6_R8_minimal_support_extension_design_authorized": support_extension_design_authorized,
            "P2_R6_R8_must_bind_R6R7_manifests": True,
            "P2_continuation_restart_authorized_now": False,
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

        design_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Design_Contract.json"
        summary_path = local / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R7_Summary.json"
        decision_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Decision_Contract.json"
        design_path.write_bytes(json_bytes(design))
        summary_path.write_bytes(json_bytes(summary))
        decision_path.write_bytes(json_bytes(decision))

        # Recheck immutable R5 state after all read-only LP audits.
        r5_sha_after = sha256_file(r5state_path)
        gate("R5_provisional_state_SHA_unchanged_after_R7", r5_sha_after == r5_sha_before, r5_sha_after)

        gate_matrix_path = local / "POSTV16_AV4_PIVOT_P2_R6_R7_Final_Gate_Matrix.csv"
        gate_matrix_path.write_bytes(csv_bytes(gate_rows))

        manifest_rows: list[dict[str, Any]] = []
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest_rows.append({
                    "file": str(p.relative_to(local)).replace("\\", "/"),
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        (local / "POSTV16_AV4_PIVOT_P2_R6_R7_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest_rows))

        if out.exists():
            raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(local, out)

        print()
        print("=" * 210)
        print("POSTV16-AV4-PIVOT-P2-R6-R7: PASS")
        print("Classification                                      :", classification)
        print("R6R6 components                                     :", EXPECTED_R6R6_COMPONENTS)
        print("Baseline exact-feasible components                  :", baseline_exact_feasible_count)
        print("Targeted recurrent components                       :", targeted_component_count)
        print("Target CVs                                          :", len(target_manifest))
        print("New recurrent eligibility edges                     :", len(recurrent_edge_manifest))
        print("Prospective execution groups                        :", len(group_rows))
        print("Exact frozen-domain feasible groups                 :", frozen_domain_feasible_groups)
        print("Exact frozen-domain infeasible groups               :", frozen_domain_infeasible_groups)
        print("R5 local repair changed                             : False")
        print("Day375 state mutation                               : False")
        print("P2-R6-R8 projection execution authorized            :", successor_execution_authorized)
        print("P2-R6-R8 support-extension design authorized        :", support_extension_design_authorized)
        print("P3 authorized                                       : False")
        print("=" * 210)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        report = block_dir / "POSTV16_AV4_PIVOT_P2_R6_R7_Blocked_Report.json"
        if not report.exists():
            report.write_text(
                json.dumps({
                    "milestone": MILESTONE,
                    "status": STATUS_BLOCKED,
                    "failed_stage": stage,
                    "exception": repr(exc),
                    "design_freeze_only": True,
                    "state_mutation_executed": False,
                    "automatic_rerun_authorized": False,
                    "support_growth_execution_authorized": False,
                    "new_H2_cells_execution_authorized": False,
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
