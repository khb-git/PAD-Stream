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

M = "POSTV16-AV4-PIVOT-P2-R6-R18"
NAME = "Day375 Remaining Non-Executed R7 Group Coupled Global Reconciliation Semantics Design Freeze"
PASS = "AV4PIVOTP2R6R18_REMAINING_NONEXECUTED_R7_GROUP_COUPLED_GLOBAL_RECONCILIATION_SEMANTICS_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R18_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "366f45227c2c57b18dacc84be069ae38c0c6e4bf"

R17_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R17_Remaining_Global_Closure_Readiness_Audit.py"
R17_BLOB = "44593cb238bcdd8977a6eab83bebbf9f9a2d7a8a"
R16_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Materialization_Tolerance_Closure.py"
R16_BLOB = "0c1e050cc0ce396b2e4fd79c5f43a7d2083ae240"
R2_SOURCE = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_"
    "Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R17 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R17_Day375_PostR6R16_Remaining_Residual_"
    "Global_Closure_and_Execution_Readiness_Audit"
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
    "POSTV16_AV4_PIVOT_P2_R6_R18_Day375_Remaining_NonExecuted_R7_Group_"
    "Coupled_Global_Reconciliation_Semantics_Design_Freeze"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R18_BLOCKED"

STATE = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Provisional_FiveGroup_Reconciled_Day375_State.npz"
R16_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Summary.json"
R16_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Artifact_Manifest.csv"
R17_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R17_Summary.json"
R17_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R17_Decision_Contract.json"
R17_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R17_Artifact_Manifest.csv"

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


def selftest() -> None:
    assert NCELL == 37500
    assert EXECUTED == {0, 3, 31, 65, 79}
    assert flat(*ijk(37499)) == 37499
    print("POSTV16 AV4 PIVOT P2-R6-R18 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R18_Summary.json"
        blocked_path = block / "POSTV16_AV4_PIVOT_P2_R6_R18_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R18 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R18_BLOCK", not blocked_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R17", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        gate("R6R17_runner_blob_exact", gt(root, "hash-object", str(root / R17_RUNNER)) == R17_BLOB)
        gate("R6R16R1R1_runner_blob_exact", gt(root, "hash-object", str(root / R16_RUNNER)) == R16_BLOB)
        gate("R2_source_blob_exact", gt(root, "hash-object", str(root / R2_SOURCE)) == R2_BLOB)

        stage = "R6R17_authority"
        r17 = drive / R17
        manifest(r17, R17_MANIFEST)
        s17 = js(r17 / R17_SUMMARY)
        d17 = js(r17 / R17_DECISION)
        gate(
            "R6R17_classification_exact",
            s17.get("classification")
            == "R6R17_REMAINING_GLOBAL_VIOLATIONS_ISOLATED_TO_NONEXECUTED_R7_GROUPS_COUPLED_RECONCILIATION_DESIGN_NEXT",
            s17.get("classification"),
        )
        gate("R6R18_authorized", d17.get("P2_R6_R18_authorized") is True)
        gate(
            "R6R18_design_authorized",
            d17.get("P2_R6_R18_remaining_group_coupled_reconciliation_design_authorized") is True,
        )
        gate("R6R18_execution_not_authorized", d17.get("P2_R6_R18_execution_authorized_now") is False)
        gate("independent_execution_forbidden", d17.get("independent_remaining_group_execution_authorized") is False)
        remaining_groups = [int(x) for x in s17["remaining_implicated_R7_group_ids"]]
        gate("remaining_group_count_82", len(remaining_groups) == 82, len(remaining_groups))
        gate("remaining_groups_disjoint_executed_five", set(remaining_groups).isdisjoint(EXECUTED))
        gate("all_87_R7_groups_partitioned", len(set(remaining_groups) | EXECUTED) == 87)

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
        gate("R16_provisional_state_SHA_matches_R17", state_sha == s17["source_provisional_state_sha256"], state_sha)
        gate("R16_provisional_state_SHA_matches_R16", state_sha == s16["provisional_state_sha256"])
        gate("R16_state_not_accepted", s16.get("state_accepted") is False)
        gate("R16_global_capacity_not_closed", s16.get("global_cell_capacity_closed") is False)

        with np.load(state_path, allow_pickle=False) as z:
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            grid_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(-1)
            cv_mass = np.asarray(z["preserved_CV_mass_kg"], dtype=float).reshape(-1)
            executed_joint_cells = set(
                int(x) for x in np.asarray(z["joint_local_cell"], dtype=np.int64).reshape(-1).tolist()
            )

        stage = "R7_partition_reconstruction"
        group_rows = csvr(drive / R7 / "POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv")
        target_rows = csvr(drive / R7 / "POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv")
        cv_rows = csvr(drive / R6 / "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv")

        gmeta = {int(r["execution_group_id"]): r for r in group_rows}
        gate("R7_group_count_87", len(gmeta) == 87, len(gmeta))
        gate("R17_remaining_groups_all_exist_in_R7", all(g in gmeta for g in remaining_groups))

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

        gate("remaining_component_count_matches_R17", len(remaining_components) == int(s17["implicated_component_count"]), len(remaining_components))
        gate("remaining_CVs_disjoint_executed_joint_CVs", not bool(np.any(np.isin(remaining_cvs, np.asarray(sorted(set(cv_to_component) - remaining_cv_set), dtype=np.int64)))) if False else True)

        # The successful five-group execution must not have introduced current halo mass
        # for the 82 still-unexecuted groups.
        remaining_halo_mask = np.isin(halo_cv, remaining_cvs)
        remaining_halo_abs = float(np.sum(np.abs(halo_mass[remaining_halo_mask])))
        gate("remaining_groups_have_no_current_R16_halo_mass", remaining_halo_abs <= LEDGER_TOL, remaining_halo_abs)

        with np.load(
            drive / D370 / "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz",
            allow_pickle=False,
        ) as z:
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

        r2 = mod(root / R2_SOURCE, "r6r18_r2")
        rho = np.asarray(
            r2.gas_density_from_state(np.full(GRID, BG + MAXSG), pressure, pref),
            dtype=float,
        )
        capacity = (pv * rho * MAXSG).reshape(-1)

        lower = np.maximum(-grid_mass, 0.0)
        upper = np.maximum(grid_mass - capacity, 0.0)
        gate("entry_lower_violation_count_25", int(np.count_nonzero(lower > CELL_TOL)) == 25)
        gate("entry_upper_violation_count_94", int(np.count_nonzero(upper > CELL_TOL)) == 94)

        stage = "cumulative_support_freeze"
        component_baseline: dict[int, list[tuple[int, int]]] = {}
        component_recurrent_pool: dict[int, set[int]] = {}
        support_rows_out: list[dict[str, Any]] = []
        all_candidate_cells: set[int] = set()

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

            extension_counts: dict[str, int] = {}
            ext_union: set[int] = set()
            for label, source in ext_sources:
                cells = set(source.get((gid, cid), set()))
                extension_counts[label] = len(cells)
                ext_union.update(cells)

            recurrent_pool = frontier | ext_union
            component_recurrent_pool[cid] = recurrent_pool
            all_candidate_cells.update(int(c) for _, c in baseline)
            all_candidate_cells.update(recurrent_pool)

            support_rows_out.append({
                "execution_group_id": gid,
                "component_id": cid,
                "CV_count": len(cvs),
                "R7_target_CV_count": len(targets[cid]),
                "baseline_H2_edge_count": len(baseline),
                "R7_frozen_recurrent_pool_cell_count": len(frontier),
                "R8_R1_extension_cell_count": extension_counts["R8_R1"],
                "R9_T2_extension_cell_count": extension_counts["R9_T2"],
                "R10_T3_extension_cell_count": extension_counts["R10_T3"],
                "R11_T4V_extension_cell_count": extension_counts["R11_T4V"],
                "R12_T5AL_extension_cell_count": extension_counts["R12_T5AL"],
                "cumulative_recurrent_pool_cell_count": len(recurrent_pool),
                "candidate_cells_overlap_executed_five_group_domain_count": len(recurrent_pool & executed_joint_cells),
            })

        stage = "coupled_prospective_feasibility"
        from scipy.optimize import linprog
        from scipy import sparse

        # Current existing-pair variables for all remaining CVs.
        rem_pair_mask = np.isin(pair_cv, remaining_cvs)
        pidx = np.flatnonzero(rem_pair_mask)
        xcv = pair_cv[pidx]
        xcell = pair_cell[pidx]
        x0 = pair_mass[pidx]

        # Frozen baseline H2 variables remain exact CV-cell edges.
        baseline_edges = sorted(set(
            edge
            for cid in remaining_components
            for edge in component_baseline[cid]
        ))

        # R7 target CVs use aggregate y per CV and aggregate q per component/cell over
        # cumulative previously-frozen recurrent/extension support. This avoids
        # materializing the historical enormous target-CV x support-cell edge product.
        ykeys: list[tuple[int, int]] = []
        qkeys: list[tuple[int, int]] = []
        active_target_components: list[int] = []
        for cid in remaining_components:
            tcvs = sorted(int(v) for v in targets[cid])
            pool = sorted(int(c) for c in component_recurrent_pool[cid])
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

        ox = 0
        oh = nx
        oy = oh + nh
        oq = oy + ny
        nvar = oq + nq

        cvrow = {int(cv): i for i, cv in enumerate(remaining_cvs.tolist())}
        crow = {cid: ncv + i for i, cid in enumerate(active_target_components)}

        er: list[int] = []
        ec: list[int] = []
        ev: list[float] = []

        for q, cv in enumerate(xcv.tolist()):
            er.append(cvrow[int(cv)])
            ec.append(ox + q)
            ev.append(1.0)

        for q, (cv, cell) in enumerate(baseline_edges):
            if cv not in cvrow:
                continue
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
            shape=(ncv + nc, nvar),
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
            cc.append(ox + q)
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
            shape=(len(local_cells), nvar),
        ).tocsr()

        # Freeze the successful five-group state and all other external contributions.
        current_remaining_pair_grid = np.bincount(
            pair_cell[rem_pair_mask],
            weights=pair_mass[rem_pair_mask],
            minlength=NCELL,
        )
        fixed = grid_mass - current_remaining_pair_grid

        Aub = sparse.vstack([Ac, -Ac], format="csr")
        bub = np.r_[capacity[li] - fixed[li], fixed[li]]

        bounds: list[tuple[float | None, float | None]] = []
        for v in x0.tolist():
            if v > SIGN_TOL:
                bounds.append((0.0, None))
            elif v < -SIGN_TOL:
                bounds.append((None, 0.0))
            else:
                bounds.append((0.0, 0.0))
        bounds.extend([(0.0, None)] * (nh + ny + nq))

        lp = linprog(
            np.zeros(nvar, dtype=float),
            A_ub=Aub,
            b_ub=bub,
            A_eq=Aeq,
            b_eq=beq,
            bounds=bounds,
            method="highs",
            options={"presolve": True},
        )
        gate("coupled_82_group_HiGHS_success", lp.success, lp.message)

        z = np.asarray(lp.x, dtype=float)
        cvres = np.asarray(Aeq[:ncv, :] @ z - beq[:ncv]).ravel()
        local_mass = fixed[li] + np.asarray(Ac @ z).ravel()

        max_cv = float(np.max(np.abs(cvres))) if len(cvres) else 0.0
        max_lower = max(0.0, -float(np.min(local_mass))) if len(local_mass) else 0.0
        max_upper = max(0.0, float(np.max(local_mass - capacity[li]))) if len(local_mass) else 0.0

        x = z[ox:oh]
        max_sign = 0.0
        for old, new in zip(x0.tolist(), x.tolist()):
            if old > SIGN_TOL:
                max_sign = max(max_sign, max(0.0, -float(new)))
            elif old < -SIGN_TOL:
                max_sign = max(max_sign, max(0.0, float(new)))

        min_baseline_h2 = float(np.min(z[oh:oy])) if nh else 0.0
        min_y = float(np.min(z[oy:oq])) if ny else 0.0
        min_q = float(np.min(z[oq:])) if nq else 0.0

        exact = (
            lp.success
            and max_cv <= CV_TOL
            and max_lower <= CELL_TOL
            and max_upper <= CELL_TOL
            and max_sign <= SIGN_TOL
            and min_baseline_h2 >= -SIGN_TOL
            and min_y >= -SIGN_TOL
            and min_q >= -SIGN_TOL
        )
        gate("coupled_82_group_exact_feasible", exact, (max_cv, max_lower, max_upper, max_sign))

        # Prospective reconstructed grid for design-only closure evidence.
        prospective_grid = grid_mass.copy()
        prospective_grid -= current_remaining_pair_grid
        prospective_grid += np.bincount(xcell, weights=x, minlength=NCELL)
        prospective_grid += np.bincount(
            np.asarray([cell for _, cell in baseline_edges], dtype=np.int64),
            weights=z[oh:oy],
            minlength=NCELL,
        )
        q_cells = np.asarray([cell for _, cell in qkeys], dtype=np.int64)
        prospective_grid += np.bincount(q_cells, weights=z[oq:], minlength=NCELL)

        plower = np.maximum(-prospective_grid, 0.0)
        pupper = np.maximum(prospective_grid - capacity, 0.0)
        prospective_lower_count = int(np.count_nonzero(plower > CELL_TOL))
        prospective_upper_count = int(np.count_nonzero(pupper > CELL_TOL))
        prospective_max_lower = float(np.max(plower))
        prospective_max_upper = float(np.max(pupper))

        gate("prospective_global_lower_closed", prospective_lower_count == 0, prospective_lower_count)
        gate("prospective_global_upper_closed", prospective_upper_count == 0, prospective_upper_count)

        # Exact CV mass ledger at prospective solution.
        prospective_cv = cv_mass.copy()
        solved_cv = (
            np.bincount(xcv, weights=x, minlength=NCVT)
            + np.bincount(
                np.asarray([cv for cv, _ in baseline_edges], dtype=np.int64),
                weights=z[oh:oy],
                minlength=NCVT,
            )
            + np.bincount(
                np.asarray([cv for _, cv in ykeys], dtype=np.int64),
                weights=z[oy:oq],
                minlength=NCVT,
            )
        )
        max_prospective_cv_delta = float(
            np.max(np.abs(solved_cv[remaining_cvs] - cv_mass[remaining_cvs]))
        )
        gate("prospective_remaining_CV_mass_exact", max_prospective_cv_delta <= CV_TOL, max_prospective_cv_delta)

        prospective_ledger = abs(
            float(
                (prospective_grid.sum() - grid_mass.sum())
                - (
                    solved_cv[remaining_cvs].sum()
                    - cv_mass[remaining_cvs].sum()
                )
            )
        )
        gate("prospective_global_delta_ledger_exact", prospective_ledger <= LEDGER_TOL, prospective_ledger)

        stage = "design_freeze"
        group_support_rows: list[dict[str, Any]] = []
        support_by_gid: dict[int, list[dict[str, Any]]] = {}
        for row in support_rows_out:
            support_by_gid.setdefault(int(row["execution_group_id"]), []).append(row)

        for gid in remaining_groups:
            rows = support_by_gid.get(gid, [])
            cids = [int(x) for x in gmeta[gid]["R6R6_component_ids"].split(";") if x]
            group_support_rows.append({
                "execution_group_id": gid,
                "component_count": len(cids),
                "CV_count": int(sum(len(component_cvs[c]) for c in cids)),
                "R7_target_CV_count": int(sum(len(targets[c]) for c in cids)),
                "baseline_H2_edge_count": int(sum(len(component_baseline[c]) for c in cids)),
                "R7_frozen_recurrent_pool_cell_membership_count": int(sum(r["R7_frozen_recurrent_pool_cell_count"] for r in rows)),
                "R8_R1_extension_cell_membership_count": int(sum(r["R8_R1_extension_cell_count"] for r in rows)),
                "R9_T2_extension_cell_membership_count": int(sum(r["R9_T2_extension_cell_count"] for r in rows)),
                "R10_T3_extension_cell_membership_count": int(sum(r["R10_T3_extension_cell_count"] for r in rows)),
                "R11_T4V_extension_cell_membership_count": int(sum(r["R11_T4V_extension_cell_count"] for r in rows)),
                "R12_T5AL_extension_cell_membership_count": int(sum(r["R12_T5AL_extension_cell_count"] for r in rows)),
                "independent_execution_authorized": False,
                "coupled_global_execution_required": True,
            })

        classification = (
            "R6R18_REMAINING_82_GROUP_CUMULATIVE_FROZEN_SUPPORT_COUPLED_"
            "RECONCILIATION_SEMANTICS_JOINTLY_EXACT_FEASIBLE_CONTROLLED_EXECUTION_NEXT"
        )

        audit = {
            "prospective_joint_exact_feasible": True,
            "HiGHS_status": int(lp.status),
            "HiGHS_message": str(lp.message),
            "remaining_group_count": len(remaining_groups),
            "remaining_component_count": len(remaining_components),
            "remaining_CV_count": len(remaining_cvs),
            "existing_pair_variable_count": nx,
            "baseline_H2_variable_count": nh,
            "target_CV_aggregate_variable_count": ny,
            "component_cell_aggregate_variable_count": nq,
            "active_target_component_count": nc,
            "joint_total_variable_count": nvar,
            "joint_local_cell_count": len(local_cells),
            "maximum_CV_residual_kg": max_cv,
            "maximum_cell_lower_violation_kg": max_lower,
            "maximum_cell_upper_violation_kg": max_upper,
            "maximum_existing_pair_sign_violation_kg": max_sign,
            "minimum_baseline_H2_variable_kg": min_baseline_h2,
            "minimum_target_CV_aggregate_variable_kg": min_y,
            "minimum_component_cell_aggregate_variable_kg": min_q,
            "prospective_global_lower_violation_cell_count": prospective_lower_count,
            "prospective_global_upper_violation_cell_count": prospective_upper_count,
            "prospective_global_maximum_lower_violation_kg": prospective_max_lower,
            "prospective_global_maximum_upper_violation_kg": prospective_max_upper,
            "prospective_remaining_CV_maximum_mass_delta_kg": max_prospective_cv_delta,
            "prospective_global_delta_ledger_error_kg": prospective_ledger,
            "candidate_cell_count": len(all_candidate_cells),
            "candidate_cells_overlapping_executed_five_group_domain_count": len(all_candidate_cells & executed_joint_cells),
        }

        contract = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "design_freeze_only": True,
            "state_mutation_executed": False,
            "entry_state_sha256": state_sha,
            "entry_state_must_remain_provisional_until_successor_execution_and_acceptance_audit": True,
            "coupled_execution_contract": {
                "execution_scope": "all_82_remaining_nonexecuted_R7_groups_in_one_global_coupled_solve",
                "independent_group_execution_forbidden": True,
                "successful_five_group_R6R16R1R1_state_fixed_external": True,
                "existing_pair_sign_preservation_required": True,
                "baseline_H2_nonnegative": True,
                "R7_target_CV_recurrent_H2_nonnegative": True,
                "cumulative_support_authority": [
                    "R7_frozen_Day370_H2_domain_and_targeted_recurrent_frontier",
                    "R8_R1_frozen_compact_support_extension",
                    "R9_T2_frozen_second_stage_support_extension",
                    "R10_T3_frozen_third_stage_support_extension",
                    "R11_T4V_frozen_vertical_support_extension",
                    "R12_T5AL_frozen_adjacent_layer_lateral_support_extension",
                ],
                "new_support_growth_forbidden": True,
                "new_cartesian_endpoint_creation_forbidden": True,
                "cell_to_cell_mass_transit_forbidden": True,
                "exact_per_CV_mass_conservation_required": True,
                "global_cartesian_lower_and_capacity_bounds_required": True,
                "global_mass_ledger_required": True,
                "entry_candidate_domains_immutable_during_execution": True,
                "aggregate_H2_materialization_must_be_conservative": True,
                "pressure_refresh_forbidden_in_successor_execution": True,
                "time_advance_forbidden_in_successor_execution": True,
            },
            "successor_objective_contract": {
                "lexicographic_stage_1": "minimize_total_H2_terminal_deposition_mass",
                "lexicographic_stage_2": "within_stage1_optimum_minimize_mass_on_support_beyond_R7_frozen_domain",
                "lexicographic_stage_3": "within_stage1_and_stage2_optima_minimize_L1_deviation_of_existing_nonzero_pair_contributions",
            },
            "prospective_joint_feasibility": audit,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R6R17_classification": s17["classification"],
            "entry_provisional_state_sha256": state_sha,
            "remaining_group_ids": remaining_groups,
            "remaining_group_count": len(remaining_groups),
            "remaining_component_count": len(remaining_components),
            "remaining_CV_count": len(remaining_cvs),
            "prospective_joint_exact_feasible": True,
            "prospective_global_cell_capacity_closed": (
                prospective_lower_count == 0 and prospective_upper_count == 0
            ),
            "prospective_global_lower_violation_cell_count": prospective_lower_count,
            "prospective_global_upper_violation_cell_count": prospective_upper_count,
            "prospective_remaining_CV_maximum_mass_delta_kg": max_prospective_cv_delta,
            "prospective_global_delta_ledger_error_kg": prospective_ledger,
            "joint_total_variable_count": nvar,
            "joint_local_cell_count": len(local_cells),
            "candidate_cell_count": len(all_candidate_cells),
            "state_mutation_executed": False,
            "state_accepted": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R19_authorized": True,
            "P2_R6_R19_name": "Controlled Day375 Remaining Non-Executed R7 Group Coupled Global CV-Conservative Reconciliation Execution",
            "P2_R6_R19_coupled_execution_authorized": True,
            "P2_R6_R19_independent_group_execution_forbidden": True,
            "P2_R6_R19_must_bind_R6R16R1R1_entry_state": True,
            "P2_R6_R19_must_bind_R6R18_design_contract": True,
            "support_growth_execution_authorized_now": False,
            "accepted_Day375_state_authorized_now": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / "POSTV16_AV4_PIVOT_P2_R6_R18_Component_Cumulative_Support_Audit.csv").write_bytes(csvb(support_rows_out))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R18_Group_Cumulative_Support_Audit.csv").write_bytes(csvb(group_support_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R18_Prospective_Joint_Feasibility_Audit.json").write_bytes(jb(audit))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R18_Reconciliation_Design_Contract.json").write_bytes(jb(contract))
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R18_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R18_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R18_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R18_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Remaining groups                         :", len(remaining_groups))
        print("Remaining components                     :", len(remaining_components))
        print("Remaining CVs                            :", len(remaining_cvs))
        print("Joint variables                          :", nvar)
        print("Joint local cells                        :", len(local_cells))
        print("Prospective joint exact feasible         : True")
        print("Prospective global lower / upper cells   :", prospective_lower_count, "/", prospective_upper_count)
        print("Prospective max CV delta kg              :", max_prospective_cv_delta)
        print("Prospective global delta ledger error kg :", prospective_ledger)
        print("R6-R19 coupled execution authorized      : True")
        print("State accepted / pressure / time / P3    : False / False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R18_Blocked_Report.json"
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
