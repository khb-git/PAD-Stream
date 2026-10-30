#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R19"
NAME = "Controlled Day375 Remaining Non-Executed R7 Group Coupled Global CV-Conservative Reconciliation Execution"
PASS = "AV4PIVOTP2R6R19_REMAINING_GROUP_COUPLED_GLOBAL_RECONCILIATION_EXECUTION_PASS_PROVISIONAL_GLOBAL_CLOSED_STATE"
BLOCK = "AV4PIVOTP2R6R19_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "5f300f563022cd944ddfe129c2122079f32d617c"

R18_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R18_Remaining_NonExecuted_R7_Group_Coupled_Reconciliation_Semantics_Design_Freeze.py"
R18_BLOB = "66015f04134aa155915e24c504c93ed8d4b275d3"
R16_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Materialization_Tolerance_Closure.py"
R16_BLOB = "0c1e050cc0ce396b2e4fd79c5f43a7d2083ae240"
R2_SOURCE = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_"
    "Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R18 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R18_Day375_Remaining_NonExecuted_R7_Group_"
    "Coupled_Global_Reconciliation_Semantics_Design_Freeze"
)
R16 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Controlled_Day375_FiveGroup_"
    "BottleneckSpecific_Joint_CVConservative_Reconciliation_Execution"
)
R12 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R12_Day375_Residual_AdjacentLayer_"
    "FaceConnected_Lateral_Topology_Design_Freeze"
)
R11 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R11_Day375_Residual_BeyondSameLayer_"
    "Topology_Design_Freeze"
)
R10 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R10_Day375_Residual_ThirdStage_"
    "SupportExtension_Topology_Design_Freeze"
)
R9 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R9_Day375_Residual_SecondStage_"
    "SupportExtension_Topology_Design_Freeze"
)
R8 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Day375_Residual_FrozenDomain_"
    "Infeasibility_Localization_and_Minimal_SupportExtension_Design_Freeze"
)
R7 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_"
    "Exact_Projection_Semantics_Freeze"
)
R6 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_"
    "Projection_Authority_and_Global_State_Closure_Audit"
)
D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
A2 = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Day375_Remaining_NonExecuted_R7_"
    "Group_Coupled_Global_CVConservative_Reconciliation_Execution"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R19_BLOCKED"

R18_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R18_Summary.json"
R18_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R18_Decision_Contract.json"
R18_CONTRACT = "POSTV16_AV4_PIVOT_P2_R6_R18_Reconciliation_Design_Contract.json"
R18_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R18_Prospective_Joint_Feasibility_Audit.json"
R18_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R18_Artifact_Manifest.csv"

STATE = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Provisional_FiveGroup_Reconciled_Day375_State.npz"
R16_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Summary.json"
R16_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Artifact_Manifest.csv"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NCV = 200
NCVT = 1078 * NCV
BG = 0.20
MAXSG = 0.60

CELL_TOL = 1e-7
CV_TOL = 1e-7
LEDGER_TOL = 1e-6
SIGN_TOL = 1e-10
ASSIGN_TOL = 1e-13
MATERIALIZATION_TOL = CELL_TOL
OBJECTIVE_TOL = 1e-8
EXECUTED = {0, 3, 31, 65, 79}


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> None:
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def ijk(flat: int) -> tuple[int, int, int]:
    k = flat // 2500
    rem = flat % 2500
    j = rem // 50
    i = rem % 50
    return k, j, i


def flat(k: int, j: int, i: int) -> int:
    return k * 2500 + j * 50 + i


def h2(cells: np.ndarray, global_s0: set[int]) -> set[int]:
    out: set[int] = set()
    for c in np.asarray(cells, dtype=np.int64).reshape(-1).tolist():
        k, j, i = ijk(int(c))
        for dj in range(-2, 3):
            for di in range(-2, 3):
                if not (1 <= abs(di) + abs(dj) <= 2):
                    continue
                jj, ii = j + dj, i + di
                if not (0 <= jj < 50 and 0 <= ii < 50):
                    continue
                x = flat(k, jj, ii)
                if x not in global_s0:
                    out.add(int(x))
    return out


def extmap(rows: list[dict[str, str]]) -> dict[tuple[int, int], set[int]]:
    out: dict[tuple[int, int], set[int]] = {}
    for r in rows:
        if r.get("flat_cell", "") == "":
            continue
        key = (int(r["execution_group_id"]), int(r["component_id"]))
        out.setdefault(key, set()).add(int(r["flat_cell"]))
    return out


def deterministic_transport(
    cvs: list[int],
    supply: np.ndarray,
    cells: list[int],
    demand: np.ndarray,
) -> tuple[list[int], list[int], list[float], float, float]:
    s = np.asarray(supply, dtype=float).copy()
    d = np.asarray(demand, dtype=float).copy()
    out_cv: list[int] = []
    out_cell: list[int] = []
    out_mass: list[float] = []
    i = 0
    j = 0
    while i < len(s) and j < len(d):
        if s[i] <= ASSIGN_TOL:
            i += 1
            continue
        if d[j] <= ASSIGN_TOL:
            j += 1
            continue
        amount = min(float(s[i]), float(d[j]))
        if amount > 0.0:
            out_cv.append(int(cvs[i]))
            out_cell.append(int(cells[j]))
            out_mass.append(amount)
            s[i] -= amount
            d[j] -= amount
    cv_left = float(np.max(np.abs(s))) if len(s) else 0.0
    cell_left = float(np.max(np.abs(d))) if len(d) else 0.0
    return out_cv, out_cell, out_mass, cv_left, cell_left


def selftest() -> None:
    assert NCELL == 37500
    assert EXECUTED == {0, 3, 31, 65, 79}
    assert MATERIALIZATION_TOL == CELL_TOL
    tc, th, tm, cl, hl = deterministic_transport(
        [1, 2], np.asarray([1.0, 2.0]), [10, 11], np.asarray([2.5, 0.5])
    )
    assert abs(sum(tm) - 3.0) < 1e-12 and cl < 1e-12 and hl < 1e-12
    print("POSTV16 AV4 PIVOT P2-R6-R19 structural self-test: PASS")


def main(root: Path, drive: Path) -> int:
    root = root.resolve()
    drive = drive.resolve()
    out = drive / OUT
    block = drive / BLK
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
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R19_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R19 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R19_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R18", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        gate("R6R18_runner_blob_exact", gt(root, "hash-object", str(root / R18_RUNNER)) == R18_BLOB)
        gate("R6R16R1R1_runner_blob_exact", gt(root, "hash-object", str(root / R16_RUNNER)) == R16_BLOB)
        gate("R2_source_blob_exact", gt(root, "hash-object", str(root / R2_SOURCE)) == R2_BLOB)

        stage = "R6R18_authority"
        r18 = drive / R18
        manifest(r18, R18_MANIFEST)
        s18 = js(r18 / R18_SUMMARY)
        d18 = js(r18 / R18_DECISION)
        c18 = js(r18 / R18_CONTRACT)
        a18 = js(r18 / R18_AUDIT)

        gate(
            "R6R18_status_exact",
            s18.get("status") == "AV4PIVOTP2R6R18_REMAINING_NONEXECUTED_R7_GROUP_COUPLED_GLOBAL_RECONCILIATION_SEMANTICS_DESIGN_FREEZE_PASS_NO_STATE_MUTATION",
        )
        gate("R6R18_joint_exact_feasible", s18.get("prospective_joint_exact_feasible") is True)
        gate("R6R18_prospective_global_closed", s18.get("prospective_global_cell_capacity_closed") is True)
        gate("R6R19_authorized", d18.get("P2_R6_R19_authorized") is True)
        gate("R6R19_execution_authorized", d18.get("P2_R6_R19_coupled_execution_authorized") is True)
        gate("independent_execution_forbidden", d18.get("P2_R6_R19_independent_group_execution_forbidden") is True)
        gate("R18_design_no_state_mutation", s18.get("state_mutation_executed") is False)
        gate("R18_entry_state_binding_required", d18.get("P2_R6_R19_must_bind_R6R16R1R1_entry_state") is True)

        remaining_groups = [int(x) for x in s18["remaining_group_ids"]]
        gate("remaining_group_count_82", len(remaining_groups) == 82)
        gate("remaining_groups_disjoint_executed_five", set(remaining_groups).isdisjoint(EXECUTED))

        stage = "frozen_support_authority"
        support_specs = [
            (R8, "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Artifact_Manifest.csv",
             "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Frozen_Compact_Support_Extension.csv", "R8_R1"),
            (R9, "POSTV16_AV4_PIVOT_P2_R6_R9_Artifact_Manifest.csv",
             "POSTV16_AV4_PIVOT_P2_R6_R9_Frozen_SecondStage_Support_Extension.csv", "R9_T2"),
            (R10, "POSTV16_AV4_PIVOT_P2_R6_R10_Artifact_Manifest.csv",
             "POSTV16_AV4_PIVOT_P2_R6_R10_Frozen_ThirdStage_Support_Extension.csv", "R10_T3"),
            (R11, "POSTV16_AV4_PIVOT_P2_R6_R11_Artifact_Manifest.csv",
             "POSTV16_AV4_PIVOT_P2_R6_R11_Frozen_Vertical_Support_Extension.csv", "R11_T4V"),
            (R12, "POSTV16_AV4_PIVOT_P2_R6_R12_Artifact_Manifest.csv",
             "POSTV16_AV4_PIVOT_P2_R6_R12_Frozen_AdjacentLayerLateral_Support_Extension.csv", "R12_T5AL"),
        ]
        ext_sources: list[tuple[str, dict[tuple[int, int], set[int]]]] = []
        for rel, man, filename, label in support_specs:
            manifest(drive / rel, man)
            ext_sources.append((label, extmap(csvr(drive / rel / filename))))
        manifest(drive / R7, "POSTV16_AV4_PIVOT_P2_R6_R7_Artifact_Manifest.csv")
        manifest(drive / R6, "POSTV16_AV4_PIVOT_P2_R6_R6_Artifact_Manifest.csv")

        stage = "entry_state_authority"
        r16 = drive / R16
        manifest(r16, R16_MANIFEST)
        s16 = js(r16 / R16_SUMMARY)
        state_path = r16 / STATE
        state_sha = sha(state_path)
        gate("entry_state_SHA_matches_R18", state_sha == s18["entry_provisional_state_sha256"], state_sha)
        gate("entry_state_SHA_matches_R16", state_sha == s16["provisional_state_sha256"])
        gate("entry_state_not_accepted", s16.get("state_accepted") is False)

        with np.load(state_path, allow_pickle=False) as z:
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            grid_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(-1)
            cv_mass = np.asarray(z["preserved_CV_mass_kg"], dtype=float).reshape(-1)
            parent_pressure = np.asarray(z["parent_pressure_psi"], dtype=float)
            executed_joint_cvs = set(
                int(x) for x in np.asarray(z["joint_union_cv"], dtype=np.int64).reshape(-1).tolist()
            )
            executed_joint_cells = set(
                int(x) for x in np.asarray(z["joint_local_cell"], dtype=np.int64).reshape(-1).tolist()
            )

        stage = "R7_partition_reconstruction"
        group_rows = csvr(drive / R7 / "POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv")
        target_rows = csvr(drive / R7 / "POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv")
        cv_rows = csvr(drive / R6 / "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv")

        gmeta = {int(r["execution_group_id"]): r for r in group_rows}
        cv_to_component = {int(r["cv_id"]): int(r["component_id"]) for r in cv_rows}
        component_cvs = {
            cid: np.asarray(sorted(cv for cv, owner in cv_to_component.items() if owner == cid), dtype=np.int64)
            for cid in range(158)
        }
        targets = {
            cid: set(int(r["cv_id"]) for r in target_rows if int(r["component_id"]) == cid)
            for cid in range(158)
        }

        component_to_group: dict[int, int] = {}
        for gid, row in gmeta.items():
            for token in row["R6R6_component_ids"].split(";"):
                if token:
                    component_to_group[int(token)] = gid

        remaining_components = sorted(
            cid for cid, gid in component_to_group.items() if gid in set(remaining_groups)
        )
        remaining_cvs = np.asarray(
            sorted(int(cv) for cid in remaining_components for cv in component_cvs[cid].tolist()),
            dtype=np.int64,
        )
        remaining_cv_set = set(int(x) for x in remaining_cvs.tolist())

        gate("remaining_component_count_matches_R18", len(remaining_components) == int(s18["remaining_component_count"]))
        gate("remaining_CV_count_matches_R18", len(remaining_cvs) == int(s18["remaining_CV_count"]))
        gate("remaining_CVs_disjoint_executed_five", remaining_cv_set.isdisjoint(executed_joint_cvs))

        remaining_halo_mask = np.isin(halo_cv, remaining_cvs)
        remaining_halo_abs = float(np.sum(np.abs(halo_mass[remaining_halo_mask])))
        gate("remaining_groups_have_no_entry_halo_mass", remaining_halo_abs <= LEDGER_TOL, remaining_halo_abs)

        with np.load(
            drive / D370 / "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz",
            allow_pickle=False,
        ) as z:
            old_grid = np.asarray(z["grid_component_mass_kg"], dtype=float).reshape(-1)
            frozen_hcv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            frozen_hcell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)

        key = np.unique(frozen_hcv * NCELL + frozen_hcell)
        frozen_hcv = (key // NCELL).astype(np.int64)
        frozen_hcell = (key % NCELL).astype(np.int64)
        frozen_domain = set(int(x) for x in np.unique(frozen_hcell).tolist())
        global_s0 = set(int(x) for x in np.unique(pair_cell).tolist())

        stage = "capacity_authority"
        with np.load(
            drive / A2 / "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz",
            allow_pickle=False,
        ) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)
            pv = np.asarray(z["pore_volume_m3"], dtype=float)
            pref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate("pressure_identity", float(np.max(np.abs(pressure - parent_pressure))) <= 1e-12)

        r2 = mod(root / R2_SOURCE, "r6r19_r2")
        rho = np.asarray(
            r2.gas_density_from_state(np.full(GRID, BG + MAXSG), pressure, pref),
            dtype=float,
        )
        capacity = (pv * rho * MAXSG).reshape(-1)

        stage = "cumulative_support_reconstruction"
        component_baseline: dict[int, list[tuple[int, int]]] = {}
        component_r7_pool: dict[int, set[int]] = {}
        component_pool: dict[int, set[int]] = {}
        extension_membership: dict[int, dict[int, set[str]]] = {}

        for cid in remaining_components:
            gid = component_to_group[cid]
            cvs = component_cvs[cid]
            mask = np.isin(frozen_hcv, cvs)
            baseline = sorted(set(
                (int(cv), int(cell))
                for cv, cell in zip(frozen_hcv[mask].tolist(), frozen_hcell[mask].tolist())
            ))
            component_baseline[cid] = baseline

            s0_cells = np.unique(pair_cell[np.isin(pair_cv, cvs)])
            frontier = set(
                x for x in h2(s0_cells, global_s0)
                if x in frozen_domain
            )
            component_r7_pool[cid] = frontier

            pool = set(frontier)
            membership: dict[int, set[str]] = {int(c): {"R7"} for c in frontier}
            for label, source in ext_sources:
                for c in source.get((gid, cid), set()):
                    pool.add(int(c))
                    membership.setdefault(int(c), set()).add(label)

            component_pool[cid] = pool
            extension_membership[cid] = membership

        stage = "coupled_lexicographic_execution"
        from scipy.optimize import linprog
        from scipy import sparse

        rem_pair_mask = np.isin(pair_cv, remaining_cvs)
        pidx = np.flatnonzero(rem_pair_mask)
        xcv = pair_cv[pidx]
        xcell = pair_cell[pidx]
        x0 = pair_mass[pidx]

        baseline_edges = sorted(set(
            edge
            for cid in remaining_components
            for edge in component_baseline[cid]
        ))

        ykeys: list[tuple[int, int]] = []
        qkeys: list[tuple[int, int]] = []
        active_target_components: list[int] = []
        for cid in remaining_components:
            tcvs = sorted(int(v) for v in targets[cid])
            pool = sorted(int(c) for c in component_pool[cid])
            if tcvs and pool:
                active_target_components.append(cid)
                ykeys.extend((cid, cv) for cv in tcvs)
                qkeys.extend((cid, cell) for cell in pool)

        baseline_edges = sorted(set(baseline_edges))
        ykeys = sorted(set(ykeys))
        qkeys = sorted(set(qkeys))

        nx = len(pidx)
        nh = len(baseline_edges)
        ny = len(ykeys)
        nq = len(qkeys)
        ncv = len(remaining_cvs)
        nc = len(active_target_components)
        oh = nx
        oy = oh + nh
        oq = oy + ny
        nbase = oq + nq

        gate("R18_existing_pair_variable_count_reproduced", nx == int(a18["existing_pair_variable_count"]), nx)
        gate("R18_baseline_H2_variable_count_reproduced", nh == int(a18["baseline_H2_variable_count"]), nh)
        gate("R18_target_CV_aggregate_variable_count_reproduced", ny == int(a18["target_CV_aggregate_variable_count"]), ny)
        gate("R18_component_cell_aggregate_variable_count_reproduced", nq == int(a18["component_cell_aggregate_variable_count"]), nq)
        gate("R18_joint_total_variable_count_reproduced", nbase == int(a18["joint_total_variable_count"]), nbase)

        cvrow = {int(cv): i for i, cv in enumerate(remaining_cvs.tolist())}
        crow = {cid: ncv + i for i, cid in enumerate(active_target_components)}

        er: list[int] = []
        ec: list[int] = []
        ev: list[float] = []

        for q, cv in enumerate(xcv.tolist()):
            er.append(cvrow[int(cv)])
            ec.append(q)
            ev.append(1.0)
        for q, (cv, cell) in enumerate(baseline_edges):
            er.append(cvrow[cv])
            ec.append(oh + q)
            ev.append(1.0)
        for q, (cid, cv) in enumerate(ykeys):
            er.extend([cvrow[cv], crow[cid]])
            ec.extend([oy + q, oy + q])
            ev.extend([1.0, 1.0])
        for q, (cid, cell) in enumerate(qkeys):
            er.append(crow[cid])
            ec.append(oq + q)
            ev.append(-1.0)

        Aeq = sparse.coo_matrix(
            (np.asarray(ev), (np.asarray(er), np.asarray(ec))),
            shape=(ncv + nc, nbase),
        ).tocsr()
        beq = np.r_[cv_mass[remaining_cvs], np.zeros(nc)]

        local_cells = sorted(
            set(int(x) for x in xcell.tolist())
            | set(int(cell) for _, cell in baseline_edges)
            | set(int(cell) for _, cell in qkeys)
        )
        li = np.asarray(local_cells, dtype=np.int64)
        lrow = {cell: i for i, cell in enumerate(local_cells)}

        rr: list[int] = []
        cc: list[int] = []
        vv: list[float] = []
        for q, cell in enumerate(xcell.tolist()):
            rr.append(lrow[int(cell)])
            cc.append(q)
            vv.append(1.0)
        for q, (cv, cell) in enumerate(baseline_edges):
            rr.append(lrow[cell])
            cc.append(oh + q)
            vv.append(1.0)
        for q, (cid, cell) in enumerate(qkeys):
            rr.append(lrow[cell])
            cc.append(oq + q)
            vv.append(1.0)

        Ac = sparse.coo_matrix(
            (np.asarray(vv), (np.asarray(rr), np.asarray(cc))),
            shape=(len(local_cells), nbase),
        ).tocsr()

        current_remaining_pair_grid = np.bincount(
            pair_cell[rem_pair_mask],
            weights=pair_mass[rem_pair_mask],
            minlength=NCELL,
        )
        fixed = grid_mass - current_remaining_pair_grid

        capacity_Aub = sparse.vstack([Ac, -Ac], format="csr")
        capacity_bub = np.r_[capacity[li] - fixed[li], fixed[li]]

        bounds: list[tuple[float | None, float | None]] = []
        for v in x0.tolist():
            if v > SIGN_TOL:
                bounds.append((0.0, None))
            elif v < -SIGN_TOL:
                bounds.append((None, 0.0))
            else:
                bounds.append((0.0, 0.0))
        bounds.extend([(0.0, None)] * (nh + ny + nq))

        # Stage 1: minimize total H2 terminal deposition = exact baseline H2 + target aggregate y.
        c1 = np.zeros(nbase, dtype=float)
        c1[oh:oy] = 1.0
        c1[oy:oq] = 1.0
        lp1 = linprog(
            c1,
            A_ub=capacity_Aub,
            b_ub=capacity_bub,
            A_eq=Aeq,
            b_eq=beq,
            bounds=bounds,
            method="highs",
            options={"presolve": True},
        )
        gate("stage1_H2_minimization_success", lp1.success, lp1.message)
        opt1 = float(lp1.fun)

        # Stage 2: within stage-1 optimum, minimize q mass routed to support beyond the R7 pool.
        c2 = np.zeros(nbase, dtype=float)
        beyond_r7_q_indices: list[int] = []
        for q, (cid, cell) in enumerate(qkeys):
            if int(cell) not in component_r7_pool[cid]:
                c2[oq + q] = 1.0
                beyond_r7_q_indices.append(q)

        row1 = sparse.csr_matrix(c1.reshape(1, -1))
        Aub2 = sparse.vstack([capacity_Aub, row1], format="csr")
        bub2 = np.r_[capacity_bub, opt1 + OBJECTIVE_TOL]
        lp2 = linprog(
            c2,
            A_ub=Aub2,
            b_ub=bub2,
            A_eq=Aeq,
            b_eq=beq,
            bounds=bounds,
            method="highs",
            options={"presolve": True},
        )
        gate("stage2_extension_support_minimization_success", lp2.success, lp2.message)
        opt2 = float(lp2.fun)

        # Stage 3: within stages 1 and 2, minimize L1 deviation from entry existing-pair contributions.
        npen = nx
        ntotal = nbase + npen
        Aeq3 = sparse.hstack([Aeq, sparse.csr_matrix((Aeq.shape[0], npen))], format="csr")
        cap3 = sparse.hstack([capacity_Aub, sparse.csr_matrix((capacity_Aub.shape[0], npen))], format="csr")
        r1_3 = sparse.hstack([row1, sparse.csr_matrix((1, npen))], format="csr")
        row2 = sparse.csr_matrix(c2.reshape(1, -1))
        r2_3 = sparse.hstack([row2, sparse.csr_matrix((1, npen))], format="csr")

        pr: list[int] = []
        pc: list[int] = []
        pv_: list[float] = []
        pb: list[float] = []
        for q, old in enumerate(x0.tolist()):
            # +x - p <= old
            row = 2 * q
            pr += [row, row]
            pc += [q, nbase + q]
            pv_ += [1.0, -1.0]
            pb.append(float(old))
            # -x - p <= -old
            row = 2 * q + 1
            pr += [row, row]
            pc += [q, nbase + q]
            pv_ += [-1.0, -1.0]
            pb.append(-float(old))

        Apen = sparse.coo_matrix(
            (np.asarray(pv_), (np.asarray(pr), np.asarray(pc))),
            shape=(2 * npen, ntotal),
        ).tocsr()

        Aub3 = sparse.vstack([cap3, r1_3, r2_3, Apen], format="csr")
        bub3 = np.r_[capacity_bub, opt1 + OBJECTIVE_TOL, opt2 + OBJECTIVE_TOL, np.asarray(pb)]
        bounds3 = bounds + [(0.0, None)] * npen
        c3 = np.zeros(ntotal, dtype=float)
        c3[nbase:] = 1.0

        lp3 = linprog(
            c3,
            A_ub=Aub3,
            b_ub=bub3,
            A_eq=Aeq3,
            b_eq=beq,
            bounds=bounds3,
            method="highs",
            options={"presolve": True},
        )
        gate("stage3_existing_pair_L1_minimization_success", lp3.success, lp3.message)

        z = np.asarray(lp3.x[:nbase], dtype=float)
        x = z[:oh]
        h = z[oh:oy]
        y = z[oy:oq]
        qv = z[oq:]

        stage1_value = float(c1 @ z)
        stage2_value = float(c2 @ z)
        stage3_value = float(lp3.fun)

        gate("stage1_optimum_preserved", stage1_value <= opt1 + OBJECTIVE_TOL * 1.01, (stage1_value, opt1))
        gate("stage2_optimum_preserved", stage2_value <= opt2 + OBJECTIVE_TOL * 1.01, (stage2_value, opt2))

        cvres = np.asarray(Aeq[:ncv, :] @ z - beq[:ncv]).ravel()
        local_mass = fixed[li] + np.asarray(Ac @ z).ravel()
        max_cv = float(np.max(np.abs(cvres))) if len(cvres) else 0.0
        max_lower = max(0.0, -float(np.min(local_mass))) if len(local_mass) else 0.0
        max_upper = max(0.0, float(np.max(local_mass - capacity[li]))) if len(local_mass) else 0.0
        max_sign = 0.0
        for old, new in zip(x0.tolist(), x.tolist()):
            if old > SIGN_TOL:
                max_sign = max(max_sign, max(0.0, -float(new)))
            elif old < -SIGN_TOL:
                max_sign = max(max_sign, max(0.0, float(new)))

        gate("final_joint_CV_exact", max_cv <= CV_TOL, max_cv)
        gate("final_joint_cell_lower_exact", max_lower <= CELL_TOL, max_lower)
        gate("final_joint_cell_upper_exact", max_upper <= CELL_TOL, max_upper)
        gate("final_existing_pair_sign_exact", max_sign <= SIGN_TOL, max_sign)
        gate("final_H2_nonnegative", min(float(np.min(h)) if len(h) else 0.0, float(np.min(y)) if len(y) else 0.0, float(np.min(qv)) if len(qv) else 0.0) >= -SIGN_TOL)

        stage = "aggregate_to_explicit_materialization"
        new_pair_mass = pair_mass.copy()
        new_pair_mass[pidx] = x

        explicit_cv: list[int] = [int(v) for v in halo_cv.tolist()]
        explicit_cell: list[int] = [int(v) for v in halo_cell.tolist()]
        explicit_mass: list[float] = [float(v) for v in halo_mass.tolist()]
        explicit_class: list[str] = ["R16_ENTRY_FIXED_HALO"] * len(explicit_cv)

        # Exact baseline H2 variables.
        for (cv, cell), amount in zip(baseline_edges, h.tolist()):
            if amount > ASSIGN_TOL:
                explicit_cv.append(int(cv))
                explicit_cell.append(int(cell))
                explicit_mass.append(float(amount))
                explicit_class.append("R19_BASELINE_H2")

        materialization_rows: list[dict[str, Any]] = []
        transport_rows: list[dict[str, Any]] = []
        max_cv_left = 0.0
        max_cell_left = 0.0

        y_index_by_component: dict[int, list[int]] = {}
        q_index_by_component: dict[int, list[int]] = {}
        for idx, (cid, cv) in enumerate(ykeys):
            y_index_by_component.setdefault(cid, []).append(idx)
        for idx, (cid, cell) in enumerate(qkeys):
            q_index_by_component.setdefault(cid, []).append(idx)

        for cid in active_target_components:
            yi = y_index_by_component[cid]
            qi = q_index_by_component[cid]
            cvs = [int(ykeys[i][1]) for i in yi]
            cells = [int(qkeys[i][1]) for i in qi]
            ym = np.asarray([y[i] for i in yi], dtype=float)
            qm = np.asarray([qv[i] for i in qi], dtype=float)

            raw = float(ym.sum() - qm.sum())
            gate(f"component_{cid}_aggregate_balance_within_ledger_tol", abs(raw) <= LEDGER_TOL, raw)

            corrected = qm.copy()
            removed = 0.0
            if raw < -ASSIGN_TOL:
                remaining = -raw
                order = sorted(
                    range(len(corrected)),
                    key=lambda idx: (-float(corrected[idx]), int(cells[idx])),
                )
                for idx in order:
                    if remaining <= ASSIGN_TOL:
                        break
                    available = max(0.0, float(corrected[idx]))
                    if available <= 0.0:
                        continue
                    take = min(available, remaining)
                    corrected[idx] -= take
                    remaining -= take
                    removed += take
                gate(f"component_{cid}_q_excess_removed", remaining <= MATERIALIZATION_TOL, remaining)
            elif raw > MATERIALIZATION_TOL:
                raise GateError(f"component_{cid}_positive_q_deficit_requires_capacity_aware_repair")

            repaired = float(ym.sum() - corrected.sum())
            gate(f"component_{cid}_aggregate_balance_materialized", abs(repaired) <= MATERIALIZATION_TOL, repaired)

            tc, th, tm, cv_left, cell_left = deterministic_transport(cvs, ym, cells, corrected)
            max_cv_left = max(max_cv_left, cv_left)
            max_cell_left = max(max_cell_left, cell_left)

            for cv, cell, amount in zip(tc, th, tm):
                if amount <= ASSIGN_TOL:
                    continue
                explicit_cv.append(int(cv))
                explicit_cell.append(int(cell))
                explicit_mass.append(float(amount))
                explicit_class.append(f"R19_COMPONENT_{cid}_AGGREGATE_H2")
                transport_rows.append({
                    "component_id": cid,
                    "execution_group_id": component_to_group[cid],
                    "cv_id": int(cv),
                    "flat_cell": int(cell),
                    "contribution_kg": float(amount),
                    "cell_in_R7_pool": int(cell) in component_r7_pool[cid],
                    "cell_in_executed_five_group_domain": int(cell) in executed_joint_cells,
                })

            materialization_rows.append({
                "component_id": cid,
                "execution_group_id": component_to_group[cid],
                "raw_y_minus_q_kg": raw,
                "q_excess_removed_kg": removed,
                "repaired_y_minus_q_kg": repaired,
                "materialization_tolerance_kg": MATERIALIZATION_TOL,
                "CV_side_y_modified": False,
                "support_domain_modified": False,
            })

        gate("transport_CV_leftover_bounded", max_cv_left <= MATERIALIZATION_TOL, max_cv_left)
        gate("transport_cell_leftover_bounded", max_cell_left <= MATERIALIZATION_TOL, max_cell_left)

        # Coalesce all fixed-entry and newly materialized halo contributions.
        coalesced: dict[tuple[int, int], float] = {}
        for cv, cell, amount in zip(explicit_cv, explicit_cell, explicit_mass):
            key = (int(cv), int(cell))
            coalesced[key] = coalesced.get(key, 0.0) + float(amount)

        halo_keys = sorted(k for k, v in coalesced.items() if abs(v) > ASSIGN_TOL)
        new_halo_cv = np.asarray([k[0] for k in halo_keys], dtype=np.int64)
        new_halo_cell = np.asarray([k[1] for k in halo_keys], dtype=np.int64)
        new_halo_mass = np.asarray([coalesced[k] for k in halo_keys], dtype=float)

        stage = "global_execution_validation"
        final_cv_mass = (
            np.bincount(pair_cv, weights=new_pair_mass, minlength=NCVT)
            + np.bincount(new_halo_cv, weights=new_halo_mass, minlength=NCVT)
        )
        max_global_cv_delta = float(np.max(np.abs(final_cv_mass - cv_mass)))

        final_grid = (
            old_grid
            + np.bincount(pair_cell, weights=new_pair_mass, minlength=NCELL)
            + np.bincount(new_halo_cell, weights=new_halo_mass, minlength=NCELL)
        )
        lower = np.maximum(-final_grid, 0.0)
        upper = np.maximum(final_grid - capacity, 0.0)
        lower_count = int(np.count_nonzero(lower > CELL_TOL))
        upper_count = int(np.count_nonzero(upper > CELL_TOL))
        max_global_lower = float(np.max(lower))
        max_global_upper = float(np.max(upper))
        ledger = abs(float((final_grid.sum() - old_grid.sum()) - final_cv_mass.sum()))

        gate("all_CV_mass_preserved", max_global_cv_delta <= CV_TOL, max_global_cv_delta)
        gate("global_mass_ledger_closed", ledger <= LEDGER_TOL, ledger)
        gate("global_lower_capacity_closed", lower_count == 0, lower_count)
        gate("global_upper_capacity_closed", upper_count == 0, upper_count)

        # Entry five-group contribution-level immutability.
        entry_pair_for_executed = pair_mass[np.isin(pair_cv, np.asarray(sorted(executed_joint_cvs), dtype=np.int64))]
        final_pair_for_executed = new_pair_mass[np.isin(pair_cv, np.asarray(sorted(executed_joint_cvs), dtype=np.int64))]
        max_executed_pair_change = float(np.max(np.abs(entry_pair_for_executed - final_pair_for_executed))) if len(entry_pair_for_executed) else 0.0
        gate("executed_five_group_existing_pairs_unchanged", max_executed_pair_change == 0.0, max_executed_pair_change)

        entry_halo_map = {(int(c), int(h)): float(m) for c, h, m in zip(halo_cv, halo_cell, halo_mass)}
        max_entry_halo_change = 0.0
        for key, mass in entry_halo_map.items():
            max_entry_halo_change = max(max_entry_halo_change, abs(coalesced.get(key, 0.0) - mass))
        gate("R16_entry_halo_contributions_preserved", max_entry_halo_change == 0.0, max_entry_halo_change)

        overlap_transport_mass = float(sum(
            float(r["contribution_kg"])
            for r in transport_rows
            if bool(r["cell_in_executed_five_group_domain"])
        ))

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)

        state_out = out / "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
        np.savez_compressed(
            state_out,
            existing_pair_cv=pair_cv,
            existing_pair_cell=pair_cell,
            reconciled_existing_pair_contribution_kg=new_pair_mass,
            halo_cv=new_halo_cv,
            halo_cell=new_halo_cell,
            halo_contribution_kg=new_halo_mass,
            provisional_grid_component_mass_kg=final_grid,
            preserved_CV_mass_kg=final_cv_mass,
            parent_pressure_psi=parent_pressure,
            executed_remaining_group_ids=np.asarray(remaining_groups, dtype=np.int64),
            executed_remaining_component_ids=np.asarray(remaining_components, dtype=np.int64),
            source_R16_state_sha256=np.asarray(state_sha),
            state_day=np.asarray(375.0),
            state_accepted=np.asarray(False),
        )
        state_out_sha = sha(state_out)

        (out / "POSTV16_AV4_PIVOT_P2_R6_R19_Aggregate_H2_Materialization_Audit.csv").write_bytes(
            csvb(materialization_rows)
        )
        (out / "POSTV16_AV4_PIVOT_P2_R6_R19_Explicit_H2_Transport.csv").write_bytes(
            csvb(transport_rows)
        )

        objective = {
            "stage1_minimum_total_H2_terminal_deposition_kg": opt1,
            "stage1_final_value_kg": stage1_value,
            "stage2_minimum_extension_support_mass_kg": opt2,
            "stage2_final_value_kg": stage2_value,
            "stage3_minimum_existing_pair_L1_deviation_kg": stage3_value,
            "stage1_tolerance_kg": OBJECTIVE_TOL,
            "stage2_tolerance_kg": OBJECTIVE_TOL,
            "beyond_R7_q_variable_count": len(beyond_r7_q_indices),
        }
        (out / "POSTV16_AV4_PIVOT_P2_R6_R19_Lexicographic_Objective_Audit.json").write_bytes(
            jb(objective)
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": "R6R19_REMAINING_82_GROUP_COUPLED_EXECUTION_PASS_GLOBAL_CELL_CAPACITY_CLOSED_PROVISIONAL_STATE_ACCEPTANCE_AUDIT_NEXT",
            "entry_R6R16R1R1_state_sha256": state_sha,
            "provisional_global_closed_state_sha256": state_out_sha,
            "executed_remaining_group_count": len(remaining_groups),
            "executed_remaining_component_count": len(remaining_components),
            "executed_remaining_CV_count": len(remaining_cvs),
            "stage1_minimum_total_H2_terminal_deposition_kg": opt1,
            "stage2_minimum_extension_support_mass_kg": opt2,
            "stage3_minimum_existing_pair_L1_deviation_kg": stage3_value,
            "maximum_joint_CV_residual_kg": max_cv,
            "maximum_joint_cell_lower_violation_kg": max_lower,
            "maximum_joint_cell_upper_violation_kg": max_upper,
            "maximum_global_CV_mass_delta_kg": max_global_cv_delta,
            "global_mass_ledger_error_kg": ledger,
            "global_lower_violation_cell_count": lower_count,
            "global_upper_violation_cell_count": upper_count,
            "global_maximum_lower_violation_kg": max_global_lower,
            "global_maximum_upper_violation_kg": max_global_upper,
            "global_cell_capacity_closed": True,
            "R16_entry_five_group_existing_pair_max_change_kg": max_executed_pair_change,
            "R16_entry_halo_max_change_kg": max_entry_halo_change,
            "new_transport_mass_into_R16_joint_cell_domain_kg": overlap_transport_mass,
            "state_mutation_executed": True,
            "state_accepted": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        contract = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": summary["classification"],
            "source_R6R18_design_contract_sha256": sha(r18 / R18_CONTRACT),
            "source_R6R16R1R1_state_sha256": state_sha,
            "execution_contract": {
                "all_82_remaining_groups_executed_in_one_coupled_solve": True,
                "independent_group_execution_used": False,
                "new_support_growth_used": False,
                "successful_R16_five_group_contributions_fixed": True,
                "existing_pair_sign_preservation_enforced": True,
                "global_cartesian_capacity_enforced": True,
                "exact_per_CV_mass_conservation_enforced": True,
                "global_mass_ledger_enforced": True,
                "aggregate_H2_materialization_conservative": True,
                "pressure_refresh_executed": False,
                "time_advance_executed": False,
                "state_remains_provisional": True,
            },
            "lexicographic_objective_audit": objective,
            "provisional_state_sha256": state_out_sha,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "P2_R6_R20_authorized": True,
            "P2_R6_R20_name": "Day375 Globally Reconciled Provisional State Closure and Acceptance Audit",
            "P2_R6_R20_state_acceptance_audit_authorized": True,
            "P2_R6_R20_must_bind_R6R19_state_SHA": True,
            "accepted_Day375_state_authorized_now": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R19_Execution_Contract.json").write_bytes(jb(contract))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R19_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R19_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Executed remaining groups                 :", len(remaining_groups))
        print("Stage1 H2 minimum kg                     :", opt1)
        print("Stage2 extension-support minimum kg      :", opt2)
        print("Stage3 existing-pair L1 deviation kg     :", stage3_value)
        print("Maximum global CV delta kg               :", max_global_cv_delta)
        print("Global mass ledger error kg              :", ledger)
        print("Global lower / upper violating cells     :", lower_count, "/", upper_count)
        print("R16 entry pair / halo max change kg      :", max_executed_pair_change, "/", max_entry_halo_change)
        print("New mass into shared R16-domain cells kg :", overlap_transport_mass)
        print("Provisional globally closed state SHA256 :", state_out_sha)
        print("State accepted                           : False")
        print("R6-R20 acceptance audit authorized       : True")
        print("Pressure / time / P3                     : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R19_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "state_mutation_executed": False,
                "accepted_Day375_state_authorized": False,
                "pressure_refresh_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
                "automatic_rerun_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "BLOCKED")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
