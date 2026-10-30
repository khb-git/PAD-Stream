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

M = "POSTV16-AV4-PIVOT-P2-R6-R17"
NAME = "Day375 Post-R6-R16 Remaining Residual Global Closure and Execution Readiness Audit"
PASS = "AV4PIVOTP2R6R17_REMAINING_GLOBAL_CLOSURE_AND_EXECUTION_READINESS_AUDIT_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R17_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "0d43c882294cb558a22768d92fc8abe40ca6b9f9"

R16R1R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Materialization_Tolerance_Closure.py"
R16R1R1_BLOB = "0c1e050cc0ce396b2e4fd79c5f43a7d2083ae240"

R2_SOURCE = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_"
    "Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R16 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Controlled_Day375_FiveGroup_"
    "BottleneckSpecific_Joint_CVConservative_Reconciliation_Execution"
)
R6 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_"
    "Projection_Authority_and_Global_State_Closure_Audit"
)
R7 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_"
    "Exact_Projection_Semantics_Freeze"
)
D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
A2 = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R17_Day375_PostR6R16_Remaining_Residual_"
    "Global_Closure_and_Execution_Readiness_Audit"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R17_BLOCKED"

STATE_NAME = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Provisional_FiveGroup_Reconciled_Day375_State.npz"
SUMMARY_NAME = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Summary.json"
DECISION_NAME = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Decision_Contract.json"
MANIFEST_NAME = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Artifact_Manifest.csv"

GRID = (15, 50, 50)
NCELL = 37500
NCVT = 1078 * 200
BG = 0.20
MAXSG = 0.60
CELL_TOL = 1e-7
CV_TOL = 1e-7
LEDGER_TOL = 1e-6
EXECUTED_GROUPS = {0, 3, 31, 65, 79}


class GateError(RuntimeError):
    pass


def git_text(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


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


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def ijk(cell: int) -> tuple[int, int, int]:
    k = cell // 2500
    r = cell % 2500
    j = r // 50
    i = r % 50
    return i, j, k


def selftest() -> None:
    assert NCELL == 37500
    assert ijk(0) == (0, 0, 0)
    assert ijk(37499) == (49, 49, 14)
    assert EXECUTED_GROUPS == {0, 3, 31, 65, 79}
    print("POSTV16 AV4 PIVOT P2-R6-R17 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R17_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R17_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R17 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R17_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", git_text(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R16R1R1", git_text(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", git_text(root, "status", "--porcelain") == "")
        gate(
            "R6R16R1R1_runner_blob_exact",
            git_text(root, "hash-object", str(root / R16R1R1_RUNNER)) == R16R1R1_BLOB,
        )
        gate(
            "R2_source_blob_exact",
            git_text(root, "hash-object", str(root / R2_SOURCE)) == R2_BLOB,
        )

        stage = "R6R16R1R1_authority"
        r16 = drive / R16
        manifest(r16, MANIFEST_NAME)
        s16 = loadj(r16 / SUMMARY_NAME)
        d16 = loadj(r16 / DECISION_NAME)
        state_path = r16 / STATE_NAME

        gate("R6R16R1R1_PASS_status_exact", str(s16.get("status", "")).startswith("AV4PIVOTP2R6R16R1R1_"))
        gate("R6R16R1R1_state_mutation_executed", s16.get("state_mutation_executed") is True)
        gate("R6R16R1R1_state_not_accepted", s16.get("state_accepted") is False)
        gate("R6R16R1R1_global_not_closed", s16.get("global_cell_capacity_closed") is False)
        gate("R6R17_authorized", d16.get("P2_R6_R17_authorized") is True)
        gate(
            "R6R17_remaining_global_audit_authorized",
            d16.get("P2_R6_R17_remaining_global_closure_readiness_audit_authorized") is True,
        )
        gate("R6R17_acceptance_audit_not_authorized", d16.get("P2_R6_R17_state_acceptance_audit_authorized") is False)
        gate("state_present", state_path.is_file())
        state_sha = sha(state_path)
        gate("provisional_state_SHA_exact", state_sha == s16["provisional_state_sha256"], state_sha)

        stage = "state_reconstruction"
        with np.load(state_path, allow_pickle=False) as z:
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            grid_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(-1)
            preserved_cv_mass = np.asarray(z["preserved_CV_mass_kg"], dtype=float).reshape(-1)
            joint_cvs = set(int(x) for x in np.asarray(z["joint_union_cv"], dtype=np.int64).reshape(-1).tolist())
            joint_cells = set(int(x) for x in np.asarray(z["joint_local_cell"], dtype=np.int64).reshape(-1).tolist())
            state_accepted = bool(np.asarray(z["state_accepted"]).reshape(()))
            state_day = float(np.asarray(z["state_day"]).reshape(()))

        gate("state_day_375", abs(state_day - 375.0) <= 1e-12, state_day)
        gate("state_acceptance_false", state_accepted is False)

        with np.load(
            drive / D370 / "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz",
            allow_pickle=False,
        ) as z:
            old_grid = np.asarray(z["grid_component_mass_kg"], dtype=float).reshape(-1)

        with np.load(
            drive / A2 / "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz",
            allow_pickle=False,
        ) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)
            pv = np.asarray(z["pore_volume_m3"], dtype=float)
            pref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        r2 = mod(root / R2_SOURCE, "r6r17_r2")
        rho = np.asarray(
            r2.gas_density_from_state(np.full(GRID, BG + MAXSG), pressure, pref),
            dtype=float,
        )
        capacity = (pv * rho * MAXSG).reshape(-1)

        reconstructed = (
            old_grid
            + np.bincount(pair_cell, weights=pair_mass, minlength=NCELL)
            + np.bincount(halo_cell, weights=halo_mass, minlength=NCELL)
        )
        max_grid_reconstruction = float(np.max(np.abs(reconstructed - grid_mass)))
        gate("provisional_grid_reconstructs", max_grid_reconstruction <= CELL_TOL, max_grid_reconstruction)

        recomputed_cv = (
            np.bincount(pair_cv, weights=pair_mass, minlength=NCVT)
            + np.bincount(halo_cv, weights=halo_mass, minlength=NCVT)
        )
        max_cv_delta = float(np.max(np.abs(recomputed_cv - preserved_cv_mass)))
        gate("preserved_CV_mass_reconstructs", max_cv_delta <= CV_TOL, max_cv_delta)

        ledger = abs(float((grid_mass.sum() - old_grid.sum()) - preserved_cv_mass.sum()))
        gate("global_mass_ledger_recomputes", ledger <= LEDGER_TOL, ledger)

        lower = np.maximum(-grid_mass, 0.0)
        upper = np.maximum(grid_mass - capacity, 0.0)
        lower_cells = np.flatnonzero(lower > CELL_TOL).astype(np.int64)
        upper_cells = np.flatnonzero(upper > CELL_TOL).astype(np.int64)
        violating = np.asarray(sorted(set(lower_cells.tolist()) | set(upper_cells.tolist())), dtype=np.int64)

        lower_count = int(len(lower_cells))
        upper_count = int(len(upper_cells))
        max_lower = float(np.max(lower)) if len(lower) else 0.0
        max_upper = float(np.max(upper)) if len(upper) else 0.0
        total_lower = float(np.sum(lower[lower_cells]))
        total_upper = float(np.sum(upper[upper_cells]))

        gate("lower_count_matches_R16", lower_count == int(s16["post_execution_global_lower_violation_cell_count"]), lower_count)
        gate("upper_count_matches_R16", upper_count == int(s16["post_execution_global_upper_violation_cell_count"]), upper_count)
        gate(
            "max_lower_matches_R16",
            abs(max_lower - float(s16["post_execution_global_maximum_lower_violation_kg"])) <= CELL_TOL,
            max_lower,
        )
        gate(
            "max_upper_matches_R16",
            abs(max_upper - float(s16["post_execution_global_maximum_upper_violation_kg"])) <= CELL_TOL,
            max_upper,
        )

        stage = "ownership_attribution"
        cv_rows = csvr(drive / R6 / "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv")
        group_rows = csvr(drive / R7 / "POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv")

        cv_to_component = {int(r["cv_id"]): int(r["component_id"]) for r in cv_rows}
        component_to_group: dict[int, int] = {}
        for row in group_rows:
            gid = int(row["execution_group_id"])
            for token in row["R6R6_component_ids"].split(";"):
                if token:
                    component_to_group[int(token)] = gid

        violation_set = set(int(x) for x in violating.tolist())

        contrib_rows: list[dict[str, Any]] = []
        cell_groups: dict[int, set[int]] = {int(c): set() for c in violating.tolist()}
        cell_components: dict[int, set[int]] = {int(c): set() for c in violating.tolist()}
        cell_residual_cvs: dict[int, set[int]] = {int(c): set() for c in violating.tolist()}
        cell_executed_cvs: dict[int, set[int]] = {int(c): set() for c in violating.tolist()}
        group_abs: dict[int, float] = {}
        group_net: dict[int, float] = {}
        group_cells: dict[int, set[int]] = {}
        component_cells: dict[int, set[int]] = {}

        def consume(kind: str, cvs: np.ndarray, cells: np.ndarray, masses: np.ndarray) -> None:
            mask = np.isin(cells, violating)
            for cv, cell, mass in zip(cvs[mask], cells[mask], masses[mask]):
                cvi = int(cv)
                ci = int(cell)
                mi = float(mass)
                comp = cv_to_component.get(cvi)
                gid = component_to_group.get(comp) if comp is not None else None
                is_joint_cv = cvi in joint_cvs
                if comp is not None:
                    cell_components[ci].add(int(comp))
                    cell_residual_cvs[ci].add(cvi)
                    component_cells.setdefault(int(comp), set()).add(ci)
                if gid is not None:
                    cell_groups[ci].add(int(gid))
                    group_abs[int(gid)] = group_abs.get(int(gid), 0.0) + abs(mi)
                    group_net[int(gid)] = group_net.get(int(gid), 0.0) + mi
                    group_cells.setdefault(int(gid), set()).add(ci)
                if is_joint_cv:
                    cell_executed_cvs[ci].add(cvi)
                contrib_rows.append({
                    "flat_cell": ci,
                    "contribution_kind": kind,
                    "cv_id": cvi,
                    "component_id": "" if comp is None else int(comp),
                    "execution_group_id": "" if gid is None else int(gid),
                    "contribution_kg": mi,
                    "is_R6_residual_CV": comp is not None,
                    "is_executed_five_group_CV": is_joint_cv,
                })

        consume("existing_pair", pair_cv, pair_cell, pair_mass)
        consume("halo", halo_cv, halo_cell, halo_mass)

        violating_in_joint = sorted(violation_set & joint_cells)
        cells_with_executed_cv = sorted(c for c, cvs in cell_executed_cvs.items() if cvs)
        cells_without_residual_group = sorted(c for c, gs in cell_groups.items() if not gs)

        remaining_groups = sorted(
            set(g for gs in cell_groups.values() for g in gs) - EXECUTED_GROUPS
        )
        executed_groups_on_violations = sorted(
            set(g for gs in cell_groups.values() for g in gs) & EXECUTED_GROUPS
        )

        cell_rows: list[dict[str, Any]] = []
        overlap_pairs: set[tuple[int, int]] = set()
        multi_group_cells = 0

        for cell in violating.tolist():
            ci = int(cell)
            i, j, k = ijk(ci)
            kind = "LOWER" if lower[ci] > CELL_TOL else "UPPER"
            signed = -float(lower[ci]) if kind == "LOWER" else float(upper[ci])
            gs = sorted(cell_groups[ci])
            if len(gs) > 1:
                multi_group_cells += 1
                for a in range(len(gs)):
                    for b in range(a + 1, len(gs)):
                        overlap_pairs.add((gs[a], gs[b]))
            cell_rows.append({
                "flat_cell": ci,
                "i": i,
                "j": j,
                "k": k,
                "violation_type": kind,
                "grid_mass_kg": float(grid_mass[ci]),
                "capacity_kg": float(capacity[ci]),
                "signed_violation_kg": signed,
                "old_grid_mass_kg": float(old_grid[ci]),
                "in_R6R16_joint_local_cell_domain": ci in joint_cells,
                "residual_component_ids": ";".join(str(x) for x in sorted(cell_components[ci])),
                "R7_execution_group_ids": ";".join(str(x) for x in gs),
                "residual_CV_count": len(cell_residual_cvs[ci]),
                "executed_five_group_CV_count": len(cell_executed_cvs[ci]),
            })

        group_rows_out: list[dict[str, Any]] = []
        for gid in sorted(group_cells):
            group_rows_out.append({
                "execution_group_id": gid,
                "is_executed_five_group": gid in EXECUTED_GROUPS,
                "violating_cell_count": len(group_cells[gid]),
                "absolute_contribution_on_violating_cells_kg": group_abs.get(gid, 0.0),
                "net_contribution_on_violating_cells_kg": group_net.get(gid, 0.0),
            })

        component_rows_out: list[dict[str, Any]] = []
        for cid in sorted(component_cells):
            component_rows_out.append({
                "component_id": cid,
                "execution_group_id": component_to_group.get(cid, ""),
                "is_executed_five_group": component_to_group.get(cid) in EXECUTED_GROUPS,
                "violating_cell_count": len(component_cells[cid]),
            })

        all_outside_joint = len(violating_in_joint) == 0
        no_executed_cv_on_violations = len(cells_with_executed_cv) == 0
        all_have_residual_group = len(cells_without_residual_group) == 0
        no_executed_group_attribution = len(executed_groups_on_violations) == 0

        stage = "readiness_classification"
        if lower_count == 0 and upper_count == 0:
            classification = "R6R17_GLOBAL_CELL_CAPACITY_CLOSED_STATE_ACCEPTANCE_AUDIT_NEXT"
            next_name = "Day375 Provisional State Global Closure and Acceptance Audit"
            next_design = False
            next_acceptance = True
        elif (
            all_outside_joint
            and no_executed_cv_on_violations
            and all_have_residual_group
            and no_executed_group_attribution
        ):
            classification = (
                "R6R17_REMAINING_GLOBAL_VIOLATIONS_ISOLATED_TO_NONEXECUTED_R7_GROUPS_"
                "COUPLED_RECONCILIATION_DESIGN_NEXT"
            )
            next_name = "Day375 Remaining Non-Executed R7 Group Coupled Global Reconciliation Semantics Design Freeze"
            next_design = True
            next_acceptance = False
        else:
            classification = (
                "R6R17_REMAINING_GLOBAL_VIOLATIONS_REQUIRE_INTERACTION_OWNERSHIP_"
                "RECONCILIATION_DESIGN_NEXT"
            )
            next_name = "Day375 Remaining Global Violation Interaction and Ownership Reconciliation Design Freeze"
            next_design = True
            next_acceptance = False

        stage = "publish"
        out.mkdir(parents=True, exist_ok=False)

        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_Violating_Cell_Audit.csv").write_bytes(csvb(cell_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_Violating_Cell_Contribution_Attribution.csv").write_bytes(csvb(contrib_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_Implicated_R7_Group_Audit.csv").write_bytes(csvb(group_rows_out))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_Implicated_Component_Audit.csv").write_bytes(csvb(component_rows_out))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_R7_Group_Overlap_Pairs.csv").write_bytes(
            csvb([{"execution_group_id_a": a, "execution_group_id_b": b} for a, b in sorted(overlap_pairs)])
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_provisional_state_sha256": state_sha,
            "state_mutation_executed": False,
            "state_accepted": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "recomputed_global_mass_ledger_error_kg": ledger,
            "recomputed_maximum_CV_mass_delta_kg": max_cv_delta,
            "lower_violation_cell_count": lower_count,
            "upper_violation_cell_count": upper_count,
            "total_violation_cell_count": int(len(violating)),
            "maximum_lower_violation_kg": max_lower,
            "maximum_upper_violation_kg": max_upper,
            "total_lower_deficit_kg": total_lower,
            "total_upper_excess_kg": total_upper,
            "violating_cells_in_executed_joint_local_domain_count": len(violating_in_joint),
            "violating_cells_with_executed_five_group_CV_contribution_count": len(cells_with_executed_cv),
            "violating_cells_without_R6_residual_group_attribution_count": len(cells_without_residual_group),
            "executed_five_group_ids_on_violations": executed_groups_on_violations,
            "remaining_implicated_R7_group_ids": remaining_groups,
            "remaining_implicated_R7_group_count": len(remaining_groups),
            "implicated_component_count": len(component_cells),
            "multi_R7_group_violating_cell_count": multi_group_cells,
            "R7_group_overlap_pair_count_on_violating_cells": len(overlap_pairs),
            "all_violations_outside_executed_joint_local_domain": all_outside_joint,
            "no_executed_five_group_CV_contribution_on_violations": no_executed_cv_on_violations,
            "all_violations_have_R6_residual_group_attribution": all_have_residual_group,
            "no_executed_five_group_R7_attribution_on_violations": no_executed_group_attribution,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R18_authorized": True,
            "P2_R6_R18_name": next_name,
            "P2_R6_R18_remaining_group_coupled_reconciliation_design_authorized": next_design,
            "P2_R6_R18_state_acceptance_audit_authorized": next_acceptance,
            "P2_R6_R18_execution_authorized_now": False,
            "independent_remaining_group_execution_authorized": False,
            "accepted_Day375_state_authorized_now": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R17_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R17_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Classification                              :", classification)
        print("Lower / upper violating cells               :", lower_count, "/", upper_count)
        print("Total lower deficit kg                       :", total_lower)
        print("Total upper excess kg                        :", total_upper)
        print("Violations in executed joint local domain    :", len(violating_in_joint))
        print("Violations with executed five-group CVs      :", len(cells_with_executed_cv))
        print("Violations without residual-group attribution:", len(cells_without_residual_group))
        print("Remaining implicated R7 groups               :", remaining_groups)
        print("Multi-group violating cells                   :", multi_group_cells)
        print("R7 overlap pairs on violating cells           :", len(overlap_pairs))
        print("R6-R18 next                                   :", next_name)
        print("State accepted / pressure / time / P3         : False / False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R17_Blocked_Report.json"
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
