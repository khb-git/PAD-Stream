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

M = "POSTV16-AV4-PIVOT-P2-R6-R20"
NAME = "Day375 Globally Reconciled Provisional State Closure and Acceptance Audit"
PASS = "AV4PIVOTP2R6R20_DAY375_GLOBAL_CLOSURE_AND_ACCEPTANCE_AUDIT_PASS_ACCEPTED_STATE"
BLOCK = "AV4PIVOTP2R6R20_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "0059384fa98e6c028330582012d942d5cc0b6fe1"

R19_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_"
    "Controlled_Remaining_Group_Coupled_Global_Reconciliation_Execution.py"
)
R19_BLOB = "2626e4a08660a907752be5aca70d29f69dd2a71e"

R16_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Materialization_Tolerance_Closure.py"
R16_BLOB = "0c1e050cc0ce396b2e4fd79c5f43a7d2083ae240"

R2_SOURCE = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_"
    "Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R19 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Day375_Remaining_NonExecuted_R7_"
    "Group_Coupled_Global_CVConservative_Reconciliation_Execution"
)
R16 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Controlled_Day375_FiveGroup_"
    "BottleneckSpecific_Joint_CVConservative_Reconciliation_Execution"
)
D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
A2 = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R20_BLOCKED"

R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_Summary.json"
R19_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R19_Decision_Contract.json"
R19_CONTRACT = "POSTV16_AV4_PIVOT_P2_R6_R19_Execution_Contract.json"
R19_OBJECTIVE = "POSTV16_AV4_PIVOT_P2_R6_R19_Lexicographic_Objective_Audit.json"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"

R16_STATE = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Provisional_FiveGroup_Reconciled_Day375_State.npz"
R16_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Summary.json"
R16_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Artifact_Manifest.csv"

GRID = (15, 50, 50)
NCELL = 37500
NCV = 200
NCVT = 1078 * NCV
BG = 0.20
MAXSG = 0.60

CELL_TOL = 1e-7
CV_TOL = 1e-7
LEDGER_TOL = 1e-6
PRESSURE_TOL = 1e-12
DAY_TOL = 1e-12
OBJECTIVE_TOL = 1e-8


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


def contribution_map(cvs: np.ndarray, cells: np.ndarray, mass: np.ndarray) -> dict[tuple[int, int], float]:
    out: dict[tuple[int, int], float] = {}
    for cv, cell, amount in zip(cvs.tolist(), cells.tolist(), mass.tolist()):
        k = (int(cv), int(cell))
        out[k] = out.get(k, 0.0) + float(amount)
    return out


def selftest() -> None:
    assert NCELL == 37500
    assert NCVT == 215600
    assert CELL_TOL == CV_TOL == 1e-7
    print("POSTV16 AV4 PIVOT P2-R6-R20 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R20_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R20 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R20_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R19", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        gate("R6R19_runner_blob_exact", gt(root, "hash-object", str(root / R19_RUNNER)) == R19_BLOB)
        gate("R6R16R1R1_runner_blob_exact", gt(root, "hash-object", str(root / R16_RUNNER)) == R16_BLOB)
        gate("R2_source_blob_exact", gt(root, "hash-object", str(root / R2_SOURCE)) == R2_BLOB)

        stage = "R6R19_authority"
        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        s19 = js(r19 / R19_SUMMARY)
        d19 = js(r19 / R19_DECISION)
        c19 = js(r19 / R19_CONTRACT)
        o19 = js(r19 / R19_OBJECTIVE)
        state_path = r19 / R19_STATE
        state_sha = sha(state_path)

        gate(
            "R6R19_status_exact",
            s19.get("status")
            == "AV4PIVOTP2R6R19_REMAINING_GROUP_COUPLED_GLOBAL_RECONCILIATION_EXECUTION_PASS_PROVISIONAL_GLOBAL_CLOSED_STATE",
        )
        gate("R6R19_global_cell_capacity_closed", s19.get("global_cell_capacity_closed") is True)
        gate("R6R19_state_mutation_executed", s19.get("state_mutation_executed") is True)
        gate("R6R19_state_not_yet_accepted", s19.get("state_accepted") is False)
        gate("R6R20_authorized", d19.get("P2_R6_R20_authorized") is True)
        gate("R6R20_acceptance_audit_authorized", d19.get("P2_R6_R20_state_acceptance_audit_authorized") is True)
        gate("R6R20_must_bind_state_SHA", d19.get("P2_R6_R20_must_bind_R6R19_state_SHA") is True)
        gate("R6R19_state_SHA_exact", state_sha == s19["provisional_global_closed_state_sha256"], state_sha)

        gate(
            "R6R19_execution_contract_global_capacity",
            c19["execution_contract"].get("global_cartesian_capacity_enforced") is True,
        )
        gate(
            "R6R19_execution_contract_exact_CV",
            c19["execution_contract"].get("exact_per_CV_mass_conservation_enforced") is True,
        )
        gate(
            "R6R19_execution_contract_global_ledger",
            c19["execution_contract"].get("global_mass_ledger_enforced") is True,
        )
        gate(
            "R6R19_execution_contract_R16_fixed",
            c19["execution_contract"].get("successful_R16_five_group_contributions_fixed") is True,
        )

        stage = "lexicographic_objective_audit"
        gate(
            "stage1_final_within_frozen_optimum",
            float(o19["stage1_final_value_kg"])
            <= float(o19["stage1_minimum_total_H2_terminal_deposition_kg"])
            + float(o19["stage1_tolerance_kg"]) * 1.01,
            (
                o19["stage1_final_value_kg"],
                o19["stage1_minimum_total_H2_terminal_deposition_kg"],
            ),
        )
        gate(
            "stage2_final_within_frozen_optimum",
            float(o19["stage2_final_value_kg"])
            <= float(o19["stage2_minimum_extension_support_mass_kg"])
            + float(o19["stage2_tolerance_kg"]) * 1.01,
            (
                o19["stage2_final_value_kg"],
                o19["stage2_minimum_extension_support_mass_kg"],
            ),
        )
        gate(
            "stage3_summary_matches_objective_audit",
            abs(
                float(s19["stage3_minimum_existing_pair_L1_deviation_kg"])
                - float(o19["stage3_minimum_existing_pair_L1_deviation_kg"])
            ) <= OBJECTIVE_TOL,
        )

        stage = "state_structural_audit"
        with np.load(state_path, allow_pickle=False) as z:
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            stored_grid = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(-1)
            stored_cv = np.asarray(z["preserved_CV_mass_kg"], dtype=float).reshape(-1)
            parent_pressure = np.asarray(z["parent_pressure_psi"], dtype=float)
            remaining_groups = np.asarray(z["executed_remaining_group_ids"], dtype=np.int64).reshape(-1)
            remaining_components = np.asarray(z["executed_remaining_component_ids"], dtype=np.int64).reshape(-1)
            source_r16_sha = str(np.asarray(z["source_R16_state_sha256"]).reshape(()))
            state_day = float(np.asarray(z["state_day"]).reshape(()))
            embedded_state_accepted = bool(np.asarray(z["state_accepted"]).reshape(()))

        gate("state_day_exact_375", abs(state_day - 375.0) <= DAY_TOL, state_day)
        gate("embedded_state_flag_remains_provisional_historical_fact", embedded_state_accepted is False)
        gate("remaining_group_count_82", len(remaining_groups) == 82, len(remaining_groups))
        gate("remaining_component_count_87", len(remaining_components) == 87, len(remaining_components))
        gate("source_R16_state_SHA_matches_R19_summary", source_r16_sha == s19["entry_R6R16R1R1_state_sha256"])

        gate("pair_array_lengths_consistent", len(pair_cv) == len(pair_cell) == len(pair_mass))
        gate("halo_array_lengths_consistent", len(halo_cv) == len(halo_cell) == len(halo_mass))
        gate("grid_length_exact", len(stored_grid) == NCELL, len(stored_grid))
        gate("CV_length_exact", len(stored_cv) == NCVT, len(stored_cv))
        gate("pair_CV_bounds", np.all((pair_cv >= 0) & (pair_cv < NCVT)))
        gate("halo_CV_bounds", np.all((halo_cv >= 0) & (halo_cv < NCVT)))
        gate("pair_cell_bounds", np.all((pair_cell >= 0) & (pair_cell < NCELL)))
        gate("halo_cell_bounds", np.all((halo_cell >= 0) & (halo_cell < NCELL)))

        stage = "independent_reconstruction"
        with np.load(
            drive / D370 / "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz",
            allow_pickle=False,
        ) as z:
            old_grid = np.asarray(z["grid_component_mass_kg"], dtype=float).reshape(-1)

        recomputed_grid = (
            old_grid
            + np.bincount(pair_cell, weights=pair_mass, minlength=NCELL)
            + np.bincount(halo_cell, weights=halo_mass, minlength=NCELL)
        )
        max_grid_reconstruction = float(np.max(np.abs(recomputed_grid - stored_grid)))
        gate("Cartesian_grid_reconstructs_from_contributions", max_grid_reconstruction <= CELL_TOL, max_grid_reconstruction)

        recomputed_cv = (
            np.bincount(pair_cv, weights=pair_mass, minlength=NCVT)
            + np.bincount(halo_cv, weights=halo_mass, minlength=NCVT)
        )
        max_cv_reconstruction = float(np.max(np.abs(recomputed_cv - stored_cv)))
        gate("CV_mass_reconstructs_from_contributions", max_cv_reconstruction <= CV_TOL, max_cv_reconstruction)

        global_cv_delta_from_R19 = float(np.max(np.abs(recomputed_cv - stored_cv)))
        ledger = abs(float((recomputed_grid.sum() - old_grid.sum()) - recomputed_cv.sum()))
        gate("independent_global_mass_ledger_closed", ledger <= LEDGER_TOL, ledger)

        stage = "physical_capacity_audit"
        with np.load(
            drive / A2 / "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz",
            allow_pickle=False,
        ) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)
            pv = np.asarray(z["pore_volume_m3"], dtype=float)
            pref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        max_pressure_delta = float(np.max(np.abs(parent_pressure - pressure)))
        gate("parent_pressure_matches_frozen_Day365_flow_epoch", max_pressure_delta <= PRESSURE_TOL, max_pressure_delta)

        r2 = mod(root / R2_SOURCE, "r6r20_r2")
        rho = np.asarray(
            r2.gas_density_from_state(np.full(GRID, BG + MAXSG), pressure, pref),
            dtype=float,
        )
        capacity = (pv * rho * MAXSG).reshape(-1)

        lower = np.maximum(-recomputed_grid, 0.0)
        upper = np.maximum(recomputed_grid - capacity, 0.0)
        lower_cells = np.flatnonzero(lower > CELL_TOL)
        upper_cells = np.flatnonzero(upper > CELL_TOL)
        lower_count = int(len(lower_cells))
        upper_count = int(len(upper_cells))
        max_lower = float(np.max(lower)) if len(lower) else 0.0
        max_upper = float(np.max(upper)) if len(upper) else 0.0

        gate("global_lower_cell_capacity_closed", lower_count == 0, lower_count)
        gate("global_upper_cell_capacity_closed", upper_count == 0, upper_count)
        gate("global_max_lower_within_tolerance", max_lower <= CELL_TOL, max_lower)
        gate("global_max_upper_within_tolerance", max_upper <= CELL_TOL, max_upper)

        gate(
            "R19_summary_global_CV_delta_within_tolerance",
            float(s19["maximum_global_CV_mass_delta_kg"]) <= CV_TOL,
            s19["maximum_global_CV_mass_delta_kg"],
        )
        gate(
            "R19_summary_ledger_within_tolerance",
            float(s19["global_mass_ledger_error_kg"]) <= LEDGER_TOL,
            s19["global_mass_ledger_error_kg"],
        )
        gate("R19_summary_zero_lower_cells", int(s19["global_lower_violation_cell_count"]) == 0)
        gate("R19_summary_zero_upper_cells", int(s19["global_upper_violation_cell_count"]) == 0)

        stage = "R16_contribution_immutability_audit"
        r16 = drive / R16
        manifest(r16, R16_MANIFEST)
        s16 = js(r16 / R16_SUMMARY)
        r16_state_path = r16 / R16_STATE
        r16_state_sha = sha(r16_state_path)
        gate("R16_source_state_SHA_exact", r16_state_sha == source_r16_sha, r16_state_sha)

        with np.load(r16_state_path, allow_pickle=False) as z:
            r16_pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            r16_pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            r16_pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            r16_halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            r16_halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            r16_halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            r16_joint_cvs = np.asarray(z["joint_union_cv"], dtype=np.int64).reshape(-1)

        gate("pair_topology_identity_R16_to_R19", np.array_equal(r16_pair_cv, pair_cv) and np.array_equal(r16_pair_cell, pair_cell))

        joint_mask_r16 = np.isin(r16_pair_cv, r16_joint_cvs)
        joint_mask_r19 = np.isin(pair_cv, r16_joint_cvs)
        gate("R16_joint_pair_masks_same_size", int(np.count_nonzero(joint_mask_r16)) == int(np.count_nonzero(joint_mask_r19)))

        max_r16_pair_change = float(
            np.max(np.abs(r16_pair_mass[joint_mask_r16] - pair_mass[joint_mask_r19]))
        ) if np.any(joint_mask_r16) else 0.0
        gate("R16_five_group_existing_pair_contributions_unchanged", max_r16_pair_change == 0.0, max_r16_pair_change)

        r16_hmap = contribution_map(r16_halo_cv, r16_halo_cell, r16_halo_mass)
        r19_hmap = contribution_map(halo_cv, halo_cell, halo_mass)
        r16_joint_cv_set = set(int(x) for x in r16_joint_cvs.tolist())

        missing_or_changed = []
        extra_for_r16_cvs = []
        for k, mass in r16_hmap.items():
            if k[0] not in r16_joint_cv_set:
                continue
            if k not in r19_hmap or r19_hmap[k] != mass:
                missing_or_changed.append((k, mass, r19_hmap.get(k)))
        for k, mass in r19_hmap.items():
            if k[0] in r16_joint_cv_set and k not in r16_hmap:
                extra_for_r16_cvs.append((k, mass))

        gate("R16_five_group_halo_contributions_unchanged", len(missing_or_changed) == 0, missing_or_changed[:5])
        gate("no_new_R19_halo_edges_for_R16_five_group_CVs", len(extra_for_r16_cvs) == 0, extra_for_r16_cvs[:5])

        gate(
            "R19_summary_R16_pair_immutability_exact",
            float(s19["R16_entry_five_group_existing_pair_max_change_kg"]) == 0.0,
        )
        gate(
            "R19_summary_R16_halo_immutability_exact",
            float(s19["R16_entry_halo_max_change_kg"]) == 0.0,
        )

        stage = "acceptance"
        acceptance_contract = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "accepted_Day375_state": True,
            "accepted_Day375_day": 375.0,
            "accepted_Day375_state_sha256": state_sha,
            "accepted_Day375_state_artifact": R19_STATE,
            "accepted_Day375_state_source_milestone": "POSTV16-AV4-PIVOT-P2-R6-R19",
            "acceptance_semantics": {
                "numerical_state_rewritten": False,
                "source_NPZ_remains_immutable": True,
                "source_NPZ_embedded_state_accepted_flag_remains_false_as_historical_provisional_marker": True,
                "acceptance_is_contractual_promotion_of_exact_state_SHA": True,
                "downstream_milestones_must_bind_both_R19_state_SHA_and_R20_acceptance_contract": True,
            },
            "closure_evidence": {
                "independent_Cartesian_grid_reconstruction_max_abs_kg": max_grid_reconstruction,
                "independent_CV_reconstruction_max_abs_kg": max_cv_reconstruction,
                "independent_global_mass_ledger_error_kg": ledger,
                "global_lower_violation_cell_count": lower_count,
                "global_upper_violation_cell_count": upper_count,
                "global_maximum_lower_violation_kg": max_lower,
                "global_maximum_upper_violation_kg": max_upper,
                "parent_pressure_max_abs_delta_psi": max_pressure_delta,
                "R16_five_group_existing_pair_max_change_kg": max_r16_pair_change,
                "R16_five_group_halo_changed_or_missing_count": len(missing_or_changed),
                "R16_five_group_new_halo_edge_count": len(extra_for_r16_cvs),
            },
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": "R6R20_DAY375_GLOBALLY_RECONCILED_STATE_ACCEPTED_PRESSURE_REFRESH_NEXT",
            "accepted_Day375_state_sha256": state_sha,
            "accepted_Day375_state_source_milestone": "POSTV16-AV4-PIVOT-P2-R6-R19",
            "accepted_Day375_state": True,
            "numerical_state_rewritten": False,
            "independent_Cartesian_grid_reconstruction_max_abs_kg": max_grid_reconstruction,
            "independent_CV_reconstruction_max_abs_kg": max_cv_reconstruction,
            "independent_global_mass_ledger_error_kg": ledger,
            "global_lower_violation_cell_count": lower_count,
            "global_upper_violation_cell_count": upper_count,
            "global_maximum_lower_violation_kg": max_lower,
            "global_maximum_upper_violation_kg": max_upper,
            "R16_five_group_existing_pair_max_change_kg": max_r16_pair_change,
            "R16_five_group_halo_changed_or_missing_count": len(missing_or_changed),
            "R16_five_group_new_halo_edge_count": len(extra_for_r16_cvs),
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "accepted_Day375_state_authorized_now": True,
            "accepted_Day375_state_sha256": state_sha,
            "P2_R6_R21_authorized": True,
            "P2_R6_R21_name": "Controlled Day375 Accepted-State Pressure Refresh",
            "P2_R6_R21_pressure_refresh_execution_authorized": True,
            "P2_R6_R21_must_bind_R6R19_state_SHA": True,
            "P2_R6_R21_must_bind_R6R20_acceptance_contract": True,
            "pressure_refresh_authorized": True,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)

        acceptance_path = out / "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
        acceptance_path.write_bytes(jb(acceptance_contract))
        acceptance_sha = sha(acceptance_path)

        summary["acceptance_contract_sha256"] = acceptance_sha
        decision["R6R20_acceptance_contract_sha256"] = acceptance_sha

        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R20_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R20_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Accepted Day375 state SHA256              :", state_sha)
        print("Acceptance contract SHA256                :", acceptance_sha)
        print("Numerical state rewritten                 : False")
        print("Independent grid reconstruction max kg    :", max_grid_reconstruction)
        print("Independent CV reconstruction max kg      :", max_cv_reconstruction)
        print("Independent global ledger error kg        :", ledger)
        print("Global lower / upper violating cells      :", lower_count, "/", upper_count)
        print("R16 five-group pair max change kg         :", max_r16_pair_change)
        print("R16 halo changed/new edge counts          :", len(missing_or_changed), "/", len(extra_for_r16_cvs))
        print("Day375 state accepted                     : True")
        print("R6-R21 pressure refresh authorized        : True")
        print("Darcy/Pollock/TOF / time / P3             : False / False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R20_Blocked_Report.json"
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
