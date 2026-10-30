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

MILESTONE = "POSTV16-AV4-PIVOT-P2-R6-R16-R1-R1"
NAME = (
    "Aggregate-to-Explicit Transport Floating-Point Materialization "
    "Tolerance Closure and Corrected Joint Execution"
)
STATUS_PASS = (
    "AV4PIVOTP2R6R16R1R1_AGGREGATE_TO_EXPLICIT_TRANSPORT_FLOATING_POINT_"
    "MATERIALIZATION_TOLERANCE_CLOSURE_PASS_PROVISIONAL_STATE"
)
STATUS_BLOCK = "AV4PIVOTP2R6R16R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
EXPECTED_PARENT = "f5ba6c8a03f51315d34b8075f3234b50a3127935"

R15_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R15_"
    "Day375_Residual_BottleneckSpecific_Projection_Support_"
    "Reconciliation_Design_Freeze.py"
)
R15_RUNNER_BLOB = "5a04c7a2063d624fc01916705bde30968b1f226a"

R16_ORIGINAL_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_"
    "Controlled_Day375_FiveGroup_BottleneckSpecific_Joint_"
    "CVConservative_Reconciliation_Execution.py"
)
R16_ORIGINAL_RUNNER_BLOB = "2f8c2899dbd293592ff48d5949ae70dbe579d7d5"
R16_ORIGINAL_BLOCK_STATUS = "AV4PIVOTP2R6R16_TECHNICAL_OR_AUTHORITY_BLOCK"
R16_ORIGINAL_BLOCK_STAGE = "explicit_state_reconstruction"
R16_ORIGINAL_BLOCK_EXCEPTION = "GateError('transport_cell_leftover_bounded')"

R16R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_"
    "AggregateToExplicit_Transport_CellSide_NumericalResidual_"
    "Technical_Closure_and_Corrected_Joint_Execution.py"
)
R16R1_RUNNER_BLOB = "ae66752ec4ab3a73da3dcbee21a78b6358a191fc"
R16R1_BLOCK_STATUS = "AV4PIVOTP2R6R16R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R16R1_BLOCK_STAGE = "explicit_state_reconstruction"
R16R1_BLOCK_EXCEPTION = "GateError('group_0_aggregate_transport_balance_repaired')"

R2_SOURCE = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_"
    "Split_First_Controlled_Transition.py"
)
R2_SOURCE_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R16_ORIGINAL_OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R16_Controlled_Day375_FiveGroup_"
    "BottleneckSpecific_Joint_CVConservative_Reconciliation_Execution"
)
R16_ORIGINAL_BLOCK_DIR = BASE / "POSTV16_AV4_PIVOT_P2_R6_R16_BLOCKED"
R16_ORIGINAL_BLOCK_FILE = "POSTV16_AV4_PIVOT_P2_R6_R16_Blocked_Report.json"

R16R1_OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R16_R1_Controlled_Day375_FiveGroup_"
    "BottleneckSpecific_Joint_CVConservative_Reconciliation_Execution"
)
R16R1_BLOCK_DIR = BASE / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_BLOCKED"
R16R1_BLOCK_FILE = "POSTV16_AV4_PIVOT_P2_R6_R16_R1_Blocked_Report.json"

R15 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R15_Day375_Residual_BottleneckSpecific_"
    "Projection_Support_Reconciliation_Design_Freeze"
)
R14 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R14_Day375_Residual_FullAdmissibleDomain_"
    "Capacity_Ownership_Bottleneck_Diagnostic_Freeze"
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
R5 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_"
    "FixedExternal_Local_Projection"
)
D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
A2 = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Controlled_Day375_FiveGroup_"
    "BottleneckSpecific_Joint_CVConservative_Reconciliation_Execution"
)
BLOCK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_BLOCKED"

UNRES = [0, 3, 31, 65, 79]
GRID = (15, 50, 50)
NCELL = 37500
NCV = 200
NCVT = 1078 * NCV

BG = 0.20
MAXSG = 0.60
CELL_TOL = 1e-7
CV_TOL = 1e-7
LEDGER_TOL = 1e-6
SIGN_TOL = 1e-10
ROOM_TOL = 1e-8
ASSIGN_TOL = 1e-13
MATERIALIZATION_TOL = CELL_TOL

R5SHA = "1553445022f7267d7802f8833d5440d7521433a4cd8b7c06652cffeb6d693e57"


class GateError(RuntimeError):
    pass


def git_text(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
    ).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
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


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def verify_manifest(directory: Path, filename: str) -> None:
    rows = read_csv(directory / filename)
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p}")
        if sha256_file(p) != row["sha256"]:
            raise GateError(f"manifest_SHA:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def h2(cells: np.ndarray, s0: set[int]) -> set[int]:
    out: set[int] = set()
    for c in np.asarray(cells, dtype=np.int64).reshape(-1):
        k = int(c) // 2500
        rem = int(c) % 2500
        j, i = rem // 50, rem % 50
        for dj in range(-2, 3):
            for di in range(-2, 3):
                if not (1 <= abs(di) + abs(dj) <= 2):
                    continue
                jj, ii = j + dj, i + di
                if 0 <= jj < 50 and 0 <= ii < 50:
                    x = k * 2500 + jj * 50 + ii
                    if x not in s0:
                        out.add(int(x))
    return out


def extra_map(rows: list[dict[str, str]]) -> dict[tuple[int, int], set[int]]:
    result: dict[tuple[int, int], set[int]] = {}
    for row in rows:
        if row.get("flat_cell", "") == "":
            continue
        key = (int(row["execution_group_id"]), int(row["component_id"]))
        result.setdefault(key, set()).add(int(row["flat_cell"]))
    return result


def deterministic_transport(
    cv_keys: list[int],
    cv_mass: np.ndarray,
    cell_keys: list[int],
    cell_mass: np.ndarray,
) -> tuple[list[int], list[int], list[float], float, float]:
    cv_rem = np.maximum(np.asarray(cv_mass, dtype=float).copy(), 0.0)
    cell_rem = np.maximum(np.asarray(cell_mass, dtype=float).copy(), 0.0)
    out_cv: list[int] = []
    out_cell: list[int] = []
    out_mass: list[float] = []

    i = j = 0
    while i < len(cv_keys) and j < len(cell_keys):
        if cv_rem[i] <= ASSIGN_TOL:
            i += 1
            continue
        if cell_rem[j] <= ASSIGN_TOL:
            j += 1
            continue
        amount = min(float(cv_rem[i]), float(cell_rem[j]))
        if amount > 0.0:
            out_cv.append(int(cv_keys[i]))
            out_cell.append(int(cell_keys[j]))
            out_mass.append(amount)
            cv_rem[i] -= amount
            cell_rem[j] -= amount

    max_cv_left = float(np.max(cv_rem)) if len(cv_rem) else 0.0
    max_cell_left = float(np.max(cell_rem)) if len(cell_rem) else 0.0
    return out_cv, out_cell, out_mass, max_cv_left, max_cell_left


def self_test() -> None:
    assert UNRES == [0, 3, 31, 65, 79]
    c, h, m, a, b = deterministic_transport(
        [1, 2], np.array([2.0, 3.0]),
        [10, 11], np.array([1.0, 4.0]),
    )
    assert abs(sum(m) - 5.0) < 1e-12
    assert a < 1e-12 and b < 1e-12
    assert NCELL == 37500
    print("POSTV16 AV4 PIVOT P2-R6-R16-R1-R1 structural self-test: PASS")


def main(root: Path, drive: Path) -> int:
    root = Path(root).resolve()
    drive = Path(drive).resolve()
    out = drive / OUT
    block = drive / BLOCK
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, passed: Any, detail: Any = None) -> None:
        ok = bool(passed)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" +
              ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R16 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R16R1R1_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", git_text(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R16R1", git_text(root, "rev-parse", "HEAD^") == EXPECTED_PARENT)
        gate("repository_clean", git_text(root, "status", "--porcelain") == "")
        gate(
            "R6R15_runner_blob_exact",
            git_text(root, "hash-object", str(root / R15_RUNNER)) == R15_RUNNER_BLOB,
        )
        gate(
            "R6R16_original_runner_blob_exact",
            git_text(root, "hash-object", str(root / R16_ORIGINAL_RUNNER))
            == R16_ORIGINAL_RUNNER_BLOB,
        )
        gate(
            "R6R16R1_runner_blob_exact",
            git_text(root, "hash-object", str(root / R16R1_RUNNER))
            == R16R1_RUNNER_BLOB,
        )

        r16r1_block_path = drive / R16R1_BLOCK_DIR / R16R1_BLOCK_FILE
        gate(
            "R6R16R1_BLOCK_present",
            r16r1_block_path.is_file(),
            str(r16r1_block_path),
        )
        gate(
            "R6R16R1_PASS_absent",
            not (
                drive / R16R1_OUT /
                "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_Summary.json"
            ).is_file(),
        )
        r16r1_block = load_json(r16r1_block_path)
        gate(
            "R6R16R1_BLOCK_status_exact",
            r16r1_block.get("status") == R16R1_BLOCK_STATUS,
            r16r1_block.get("status"),
        )
        gate(
            "R6R16R1_failed_stage_exact",
            r16r1_block.get("failed_stage") == R16R1_BLOCK_STAGE,
            r16r1_block.get("failed_stage"),
        )
        gate(
            "R6R16R1_exception_exact",
            r16r1_block.get("exception") == R16R1_BLOCK_EXCEPTION,
            r16r1_block.get("exception"),
        )
        r16r1_failed = [
            g for g in r16r1_block.get("gates_completed", [])
            if not bool(g.get("pass"))
        ]
        gate(
            "R6R16R1_single_failed_gate_exact",
            len(r16r1_failed) == 1
            and r16r1_failed[0].get("gate")
            == "group_0_aggregate_transport_balance_repaired",
            r16r1_failed,
        )
        r16r1_block_sha256 = sha256_file(r16r1_block_path)

        original_r16_block_path = (
            drive / R16_ORIGINAL_BLOCK_DIR / R16_ORIGINAL_BLOCK_FILE
        )
        gate(
            "R6R16_original_BLOCK_present",
            original_r16_block_path.is_file(),
            str(original_r16_block_path),
        )
        gate(
            "R6R16_original_PASS_absent",
            not (
                drive / R16_ORIGINAL_OUT /
                "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_Summary.json"
            ).is_file(),
        )
        original_r16_block = load_json(original_r16_block_path)
        gate(
            "R6R16_original_BLOCK_status_exact",
            original_r16_block.get("status") == R16_ORIGINAL_BLOCK_STATUS,
            original_r16_block.get("status"),
        )
        gate(
            "R6R16_original_failed_stage_exact",
            original_r16_block.get("failed_stage") == R16_ORIGINAL_BLOCK_STAGE,
            original_r16_block.get("failed_stage"),
        )
        gate(
            "R6R16_original_exception_exact",
            original_r16_block.get("exception") == R16_ORIGINAL_BLOCK_EXCEPTION,
            original_r16_block.get("exception"),
        )
        completed = original_r16_block.get("gates_completed", [])
        failed = [g for g in completed if not bool(g.get("pass"))]
        gate(
            "R6R16_original_single_failed_gate_exact",
            len(failed) == 1
            and failed[0].get("gate") == "transport_cell_leftover_bounded",
            failed,
        )
        original_r16_block_sha256 = sha256_file(original_r16_block_path)
        gate(
            "R2_source_blob_exact",
            git_text(root, "hash-object", str(root / R2_SOURCE)) == R2_SOURCE_BLOB,
        )

        stage = "R6R15_authority"
        r15 = drive / R15
        verify_manifest(r15, "POSTV16_AV4_PIVOT_P2_R6_R15_Artifact_Manifest.csv")
        s15 = load_json(r15 / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R15_Summary.json")
        d15 = load_json(r15 / "POSTV16_AV4_PIVOT_P2_R6_R15_Decision_Contract.json")
        c15 = load_json(r15 / "POSTV16_AV4_PIVOT_P2_R6_R15_Reconciliation_Design_Contract.json")
        sem_rows = read_csv(r15 / "POSTV16_AV4_PIVOT_P2_R6_R15_Group_Reconciliation_Semantics.csv")
        domain_rows = read_csv(r15 / "POSTV16_AV4_PIVOT_P2_R6_R15_Candidate_Domain_Audit.csv")
        audit15 = load_json(r15 / "POSTV16_AV4_PIVOT_P2_R6_R15_Prospective_Joint_Feasibility_Audit.json")

        gate("R6R15_status_exact", str(s15.get("status", "")).startswith("AV4PIVOTP2R6R15_"))
        gate("R6R15_joint_feasible", s15.get("prospective_joint_exact_feasible") is True)
        gate("R6R15_audit_joint_feasible", audit15.get("prospective_joint_exact_feasible") is True)
        gate("R6R16R1R1_authorized", d15.get("P2_R6_R16_authorized") is True)
        gate("R6R16R1R1_execution_authorized", d15.get("P2_R6_R16_joint_reconciliation_execution_authorized") is True)
        gate("independent_group_execution_forbidden", d15.get("P2_R6_R16_independent_group_execution_forbidden") is True)
        gate(
            "secondary_sign_objective_required",
            c15["joint_execution_contract"]["R16_secondary_objective_must_minimize_sign_relaxation_magnitude_for_groups_0_3"] is True,
        )

        plan = {int(r["execution_group_id"]): r for r in sem_rows}
        gate("R6R15_semantics_five_groups", sorted(plan) == UNRES, sorted(plan))
        expected_domain_counts = {
            int(r["execution_group_id"]): int(r["candidate_pool_cell_count"])
            for r in domain_rows
        }

        stage = "prior_support_authority"
        for rel, manifest in (
            (R12, "POSTV16_AV4_PIVOT_P2_R6_R12_Artifact_Manifest.csv"),
            (R11, "POSTV16_AV4_PIVOT_P2_R6_R11_Artifact_Manifest.csv"),
            (R10, "POSTV16_AV4_PIVOT_P2_R6_R10_Artifact_Manifest.csv"),
            (R9, "POSTV16_AV4_PIVOT_P2_R6_R9_Artifact_Manifest.csv"),
            (R8, "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Artifact_Manifest.csv"),
        ):
            verify_manifest(drive / rel, manifest)

        support_sources = [
            extra_map(read_csv(drive / R8 / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Frozen_Compact_Support_Extension.csv")),
            extra_map(read_csv(drive / R9 / "POSTV16_AV4_PIVOT_P2_R6_R9_Frozen_SecondStage_Support_Extension.csv")),
            extra_map(read_csv(drive / R10 / "POSTV16_AV4_PIVOT_P2_R6_R10_Frozen_ThirdStage_Support_Extension.csv")),
            extra_map(read_csv(drive / R11 / "POSTV16_AV4_PIVOT_P2_R6_R11_Frozen_Vertical_Support_Extension.csv")),
            extra_map(read_csv(drive / R12 / "POSTV16_AV4_PIVOT_P2_R6_R12_Frozen_AdjacentLayerLateral_Support_Extension.csv")),
        ]

        stage = "state_reconstruction"
        group_rows = read_csv(drive / R7 / "POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv")
        target_rows = read_csv(drive / R7 / "POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv")
        cv_rows = read_csv(drive / R6 / "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv")
        gmeta = {int(r["execution_group_id"]): r for r in group_rows}

        component_to_group: dict[int, int] = {}
        for gid, row in gmeta.items():
            for cid in [int(x) for x in row["R6R6_component_ids"].split(";") if x]:
                component_to_group[cid] = gid

        cv_to_component = {int(r["cv_id"]): int(r["component_id"]) for r in cv_rows}
        component_cvs = {
            cid: np.asarray(
                sorted(cv for cv, owner in cv_to_component.items() if owner == cid),
                dtype=np.int64,
            )
            for cid in range(158)
        }
        targets = {
            cid: set(int(r["cv_id"]) for r in target_rows if int(r["component_id"]) == cid)
            for cid in range(158)
        }

        r5_state = drive / R5 / "POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz"
        gate("R5_state_SHA_exact", sha256_file(r5_state) == R5SHA)
        with np.load(r5_state, allow_pickle=False) as z:
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_val = np.asarray(z["locally_repaired_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            r5_provisional = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(-1)
            r5_local_cv = np.asarray(z["local_component_cv"], dtype=np.int64).reshape(-1)
            r5_halo_cv = np.asarray(z["local_halo_cv"], dtype=np.int64).reshape(-1)
            r5_halo_cell = np.asarray(z["local_halo_cell"], dtype=np.int64).reshape(-1)
            r5_halo_mass = np.asarray(z["local_halo_contribution_kg"], dtype=float).reshape(-1)
            parent_pressure = np.asarray(z["parent_pressure_psi"], dtype=float)

        with np.load(
            drive / D370 / "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz",
            allow_pickle=False,
        ) as z:
            old_grid = np.asarray(z["grid_component_mass_kg"], dtype=float).reshape(-1)
            frozen_halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            frozen_halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)

        keys = np.unique(frozen_halo_cv * NCELL + frozen_halo_cell)
        frozen_halo_cv = (keys // NCELL).astype(np.int64)
        frozen_halo_cell = (keys % NCELL).astype(np.int64)
        frozen_domain = set(int(x) for x in np.unique(frozen_halo_cell).tolist())

        with np.load(
            drive / A2 / "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz",
            allow_pickle=False,
        ) as z:
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)
            pore_volume = np.asarray(z["pore_volume_m3"], dtype=float)
            reference_pressure = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate("pressure_identity", float(np.max(np.abs(pressure - parent_pressure))) <= 1e-12)

        r2 = load_module(root / R2_SOURCE, "r6r16r1r1_r2")
        rho = np.asarray(
            r2.gas_density_from_state(
                np.full(GRID, BG + MAXSG),
                pressure,
                reference_pressure,
            ),
            dtype=float,
        )
        capacity = (pore_volume * rho * MAXSG).reshape(-1)

        current_cv_mass = (
            np.bincount(pair_cv, weights=pair_val, minlength=NCVT) +
            np.bincount(r5_halo_cv, weights=r5_halo_mass, minlength=NCVT)
        )
        reconstructed_r5 = (
            old_grid +
            np.bincount(pair_cell, weights=pair_val, minlength=NCELL) +
            np.bincount(r5_halo_cell, weights=r5_halo_mass, minlength=NCELL)
        )
        gate("R5_provisional_reconstruct", float(np.max(np.abs(reconstructed_r5 - r5_provisional))) <= CELL_TOL)
        gate(
            "R5_global_mass_ledger",
            abs(float(r5_provisional.sum() - (old_grid.sum() + current_cv_mass.sum()))) <= LEDGER_TOL,
        )

        global_s0 = set(int(x) for x in np.unique(pair_cell).tolist())
        r5_fixed = set(int(x) for x in np.unique(
            np.r_[pair_cell[np.isin(pair_cv, r5_local_cv)], r5_halo_cell]
        ).tolist())

        frontier: dict[int, set[int]] = {}
        baseline: dict[int, list[tuple[int, int]]] = {}
        for cid in range(158):
            cvs = component_cvs[cid]
            s0_cells = np.unique(pair_cell[np.isin(pair_cv, cvs)])
            frontier[cid] = set(
                x for x in h2(s0_cells, global_s0) if x in frozen_domain
            )
            mask = np.isin(frozen_halo_cv, cvs)
            baseline[cid] = sorted(set(
                (int(a), int(b))
                for a, b in zip(frozen_halo_cv[mask], frozen_halo_cell[mask])
            ))

        component_pool: dict[int, set[int]] = {}
        owners: dict[int, set[int]] = {}
        for cid in range(158):
            gid = component_to_group[cid]
            pool = set(frontier[cid])
            pool.update(h for _, h in baseline[cid])
            for source in support_sources:
                pool.update(source.get((gid, cid), set()))
            component_pool[cid] = pool
            for cell in pool:
                owners.setdefault(int(cell), set()).add(gid)

        pools: dict[int, set[int]] = {}
        all_cells = np.arange(NCELL, dtype=np.int64)
        union_cv_set: set[int] = set()

        for gid in UNRES:
            cids = [int(x) for x in gmeta[gid]["R6R6_component_ids"].split(";") if x]
            group_cvs = np.asarray(
                sorted(int(v) for cid in cids for v in component_cvs[cid].tolist()),
                dtype=np.int64,
            )
            union_cv_set.update(int(x) for x in group_cvs.tolist())
            current_pool = set(int(x) for cid in cids for x in component_pool[cid])

            group_mask = np.isin(pair_cv, group_cvs)
            fixed_group = (
                old_grid +
                np.bincount(
                    pair_cell[~group_mask],
                    weights=pair_val[~group_mask],
                    minlength=NCELL,
                ) +
                np.bincount(
                    r5_halo_cell,
                    weights=r5_halo_mass,
                    minlength=NCELL,
                )
            )
            room = capacity - fixed_group
            mode = plan[gid]["support_domain"]

            if mode == "CURRENT_FROZEN_GROUP_SUPPORT_ONLY":
                pools[gid] = current_pool
            elif mode == "STRICT_FULL_UNOWNED_POSITIVE_ROOM_DOMAIN_AT_ENTRY":
                extra = set(
                    int(c) for c in all_cells[room > ROOM_TOL]
                    if int(c) not in global_s0
                    and int(c) not in r5_fixed
                    and int(c) not in owners
                )
                pools[gid] = current_pool | extra
            elif mode == "OWNERSHIP_RELAXED_FULL_POSITIVE_ROOM_DOMAIN":
                extra = set(
                    int(c) for c in all_cells[room > ROOM_TOL]
                    if int(c) not in global_s0
                    and int(c) not in r5_fixed
                )
                pools[gid] = current_pool | extra
            else:
                raise GateError(f"unknown_support_domain:{mode}")

            gate(
                f"group_{gid}_candidate_domain_count_exact",
                len(pools[gid]) == expected_domain_counts[gid],
                (len(pools[gid]), expected_domain_counts[gid]),
            )

        stage = "joint_execution_lp"
        from scipy.optimize import linprog
        from scipy import sparse

        union_cvs = np.asarray(sorted(union_cv_set), dtype=np.int64)
        gate(
            "R6R16R1R1_union_CVs_disjoint_R5_local_repair",
            set(int(x) for x in union_cvs.tolist()).isdisjoint(
                set(int(x) for x in r5_local_cv.tolist())
            ),
        )
        gate(
            "R6R16R1R1_union_CVs_absent_from_R5_local_halo",
            not bool(np.any(np.isin(r5_halo_cv, union_cvs))),
        )
        union_pair_mask = np.isin(pair_cv, union_cvs)
        pidx = np.flatnonzero(
            union_pair_mask & (np.abs(pair_val) > SIGN_TOL)
        )
        xcv = pair_cv[pidx]
        xcell = pair_cell[pidx]
        x0 = pair_val[pidx]

        cv_group = {
            int(cv): component_to_group[cv_to_component[int(cv)]]
            for cv in union_cvs.tolist()
        }

        bindiv: list[tuple[int, int]] = []
        ykeys: list[tuple[int, int]] = []
        qkeys: list[tuple[int, int]] = []

        for gid in UNRES:
            cids = [int(x) for x in gmeta[gid]["R6R6_component_ids"].split(";") if x]
            if plan[gid]["H2_eligibility"] == "ALL_RESIDUAL_CVS_IN_GROUP":
                eligible = set(
                    int(v) for cid in cids for v in component_cvs[cid].tolist()
                )
            else:
                eligible = set(
                    int(v) for cid in cids for v in targets[cid]
                )

            pset = pools[gid]
            for cid in cids:
                for cv, cell in baseline[cid]:
                    if cv in eligible and cell in pset:
                        continue
                    bindiv.append((int(cv), int(cell)))

            ykeys.extend((gid, int(cv)) for cv in sorted(eligible))
            qkeys.extend((gid, int(cell)) for cell in sorted(pset))

        bindiv = sorted(set(bindiv))
        ykeys = sorted(set(ykeys))
        qkeys = sorted(set(qkeys))

        nx, nb, ny, nq = len(pidx), len(bindiv), len(ykeys), len(qkeys)
        ncv = len(union_cvs)
        ox = 0
        ob = nx
        oy = ob + nb
        oq = oy + ny
        base_nvar = oq + nq

        cvrow = {int(cv): row for row, cv in enumerate(union_cvs.tolist())}
        grow = {gid: ncv + i for i, gid in enumerate(UNRES)}

        er: list[int] = []
        ec: list[int] = []
        ev: list[float] = []

        for q, cv in enumerate(xcv.tolist()):
            er.append(cvrow[int(cv)])
            ec.append(ox + q)
            ev.append(1.0)
        for q, (cv, cell) in enumerate(bindiv):
            er.append(cvrow[cv])
            ec.append(ob + q)
            ev.append(1.0)
        for q, (gid, cv) in enumerate(ykeys):
            er += [cvrow[cv], grow[gid]]
            ec += [oy + q, oy + q]
            ev += [1.0, 1.0]
        for q, (gid, cell) in enumerate(qkeys):
            er.append(grow[gid])
            ec.append(oq + q)
            ev.append(-1.0)

        Aeq_base = sparse.coo_matrix(
            (np.asarray(ev), (np.asarray(er), np.asarray(ec))),
            shape=(ncv + len(UNRES), base_nvar),
        ).tocsr()
        beq = np.r_[current_cv_mass[union_cvs], np.zeros(len(UNRES))]

        local_cells = set(int(x) for x in xcell.tolist())
        local_cells.update(cell for _, cell in bindiv)
        local_cells.update(cell for _, cell in qkeys)
        local = np.asarray(sorted(local_cells), dtype=np.int64)
        cellrow = {int(cell): row for row, cell in enumerate(local.tolist())}

        rr: list[int] = []
        cc: list[int] = []
        vv: list[float] = []
        for q, cell in enumerate(xcell.tolist()):
            rr.append(cellrow[int(cell)])
            cc.append(ox + q)
            vv.append(1.0)
        for q, (cv, cell) in enumerate(bindiv):
            rr.append(cellrow[cell])
            cc.append(ob + q)
            vv.append(1.0)
        for q, (gid, cell) in enumerate(qkeys):
            rr.append(cellrow[cell])
            cc.append(oq + q)
            vv.append(1.0)

        Ac_base = sparse.coo_matrix(
            (np.asarray(vv), (np.asarray(rr), np.asarray(cc))),
            shape=(len(local), base_nvar),
        ).tocsr()

        fixed = (
            old_grid +
            np.bincount(
                pair_cell[~union_pair_mask],
                weights=pair_val[~union_pair_mask],
                minlength=NCELL,
            ) +
            np.bincount(
                r5_halo_cell,
                weights=r5_halo_mass,
                minlength=NCELL,
            )
        )

        Aub_base = sparse.vstack([Ac_base, -Ac_base], format="csr")
        bub_base = np.r_[capacity[local] - fixed[local], fixed[local]]

        base_bounds: list[tuple[float | None, float | None]] = []
        relaxed_x_indices: list[int] = []
        relaxed_x_original: list[float] = []
        relaxed_x_group: list[int] = []

        for q, (v, cv) in enumerate(zip(x0.tolist(), xcv.tolist())):
            gid = cv_group[int(cv)]
            if str(plan[gid]["existing_pair_sign_relaxed"]).lower() == "true":
                base_bounds.append((None, None))
                relaxed_x_indices.append(q)
                relaxed_x_original.append(float(v))
                relaxed_x_group.append(gid)
            elif v > SIGN_TOL:
                base_bounds.append((0.0, None))
            elif v < -SIGN_TOL:
                base_bounds.append((None, 0.0))
            else:
                base_bounds.append((0.0, 0.0))
        base_bounds += [(0.0, None)] * (nb + ny + nq)

        # Stage A: reproduce R15 exact feasibility.
        lp_feas = linprog(
            np.zeros(base_nvar),
            A_ub=Aub_base,
            b_ub=bub_base,
            A_eq=Aeq_base,
            b_eq=beq,
            bounds=base_bounds,
            method="highs",
            options={"presolve": True},
        )
        gate("stageA_joint_feasibility_success", lp_feas.success, lp_feas.message)

        # Stage B: add one nonnegative penalty variable per sign-relaxed existing pair.
        # For original + pair: penalty >= -x. For original - pair: penalty >= +x.
        npen = len(relaxed_x_indices)
        total_nvar = base_nvar + npen
        Aeq = sparse.hstack(
            [Aeq_base, sparse.csr_matrix((Aeq_base.shape[0], npen))],
            format="csr",
        )
        Ac = sparse.hstack(
            [Ac_base, sparse.csr_matrix((Ac_base.shape[0], npen))],
            format="csr",
        )
        Aub_capacity = sparse.vstack([Ac, -Ac], format="csr")
        bub_capacity = bub_base.copy()

        pen_rows: list[int] = []
        pen_cols: list[int] = []
        pen_vals: list[float] = []
        for row, (x_index, original) in enumerate(
            zip(relaxed_x_indices, relaxed_x_original)
        ):
            if original > SIGN_TOL:
                # -x - p <= 0
                pen_rows += [row, row]
                pen_cols += [x_index, base_nvar + row]
                pen_vals += [-1.0, -1.0]
            elif original < -SIGN_TOL:
                # +x - p <= 0
                pen_rows += [row, row]
                pen_cols += [x_index, base_nvar + row]
                pen_vals += [1.0, -1.0]
            else:
                raise GateError("unexpected_zero_original_in_relaxed_pair")

        Apen = sparse.coo_matrix(
            (np.asarray(pen_vals), (np.asarray(pen_rows), np.asarray(pen_cols))),
            shape=(npen, total_nvar),
        ).tocsr()
        Aub = sparse.vstack([Aub_capacity, Apen], format="csr")
        bub = np.r_[bub_capacity, np.zeros(npen)]
        bounds = base_bounds + [(0.0, None)] * npen

        objective = np.zeros(total_nvar)
        objective[base_nvar:] = 1.0

        lp = linprog(
            objective,
            A_ub=Aub,
            b_ub=bub,
            A_eq=Aeq,
            b_eq=beq,
            bounds=bounds,
            method="highs",
            options={"presolve": True},
        )
        gate("stageB_sign_minimization_success", lp.success, lp.message)

        z = np.asarray(lp.x)
        zbase = z[:base_nvar]
        cv_residual = np.asarray(
            Aeq_base[:ncv, :] @ zbase - beq[:ncv]
        ).ravel()
        cell_mass_local = fixed[local] + np.asarray(Ac_base @ zbase).ravel()
        max_cv_residual = float(np.max(np.abs(cv_residual))) if len(cv_residual) else 0.0
        max_lower = max(0.0, -float(np.min(cell_mass_local))) if len(cell_mass_local) else 0.0
        max_upper = max(
            0.0,
            float(np.max(cell_mass_local - capacity[local])),
        ) if len(cell_mass_local) else 0.0

        gate("stageB_CV_exact", max_cv_residual <= CV_TOL, max_cv_residual)
        gate("stageB_cell_lower_exact", max_lower <= CELL_TOL, max_lower)
        gate("stageB_cell_upper_exact", max_upper <= CELL_TOL, max_upper)

        sign_penalty = z[base_nvar:]
        total_sign_crossing_kg = float(np.sum(sign_penalty))
        max_sign_crossing_kg = float(np.max(sign_penalty)) if len(sign_penalty) else 0.0

        stage = "explicit_state_reconstruction"
        new_pair_val = pair_val.copy()
        new_pair_val[pidx] = zbase[ox:ob]

        bi_val = zbase[ob:oy]
        y_val = zbase[oy:oq]
        q_val = zbase[oq:oq + nq]

        explicit_cv: list[int] = [int(x) for x in r5_halo_cv.tolist()]
        explicit_cell: list[int] = [int(x) for x in r5_halo_cell.tolist()]
        explicit_mass: list[float] = [float(x) for x in r5_halo_mass.tolist()]
        explicit_class: list[str] = ["R5_LOCAL_HALO"] * len(explicit_cv)

        for (cv, cell), amount in zip(bindiv, bi_val.tolist()):
            if amount > ASSIGN_TOL:
                explicit_cv.append(int(cv))
                explicit_cell.append(int(cell))
                explicit_mass.append(float(amount))
                explicit_class.append("R6R16R1R1_BASELINE_INDIVIDUAL_H2")

        transport_rows: list[dict[str, Any]] = []
        aggregate_repair_rows: list[dict[str, Any]] = []
        max_transport_cv_left = 0.0
        max_transport_cell_left = 0.0

        for gid in UNRES:
            y_idx = [i for i, (g, cv) in enumerate(ykeys) if g == gid]
            q_idx = [i for i, (g, cell) in enumerate(qkeys) if g == gid]
            y_cvs = [int(ykeys[i][1]) for i in y_idx]
            q_cells = [int(qkeys[i][1]) for i in q_idx]
            y_mass = np.asarray([y_val[i] for i in y_idx], dtype=float)
            q_mass = np.asarray([q_val[i] for i in q_idx], dtype=float)

            raw_balance = float(y_mass.sum() - q_mass.sum())
            gate(
                f"group_{gid}_aggregate_transport_balance_within_solver_tolerance",
                abs(raw_balance) <= LEDGER_TOL,
                raw_balance,
            )

            # R6-R16-R1 technical closure:
            # R6-R16 failed because HiGHS returned a tiny group equality residual
            # (observed group 0: q exceeded y by ~6.29e-09 kg). The CV-side y
            # solution is preserved exactly. When q > y by <= LEDGER_TOL,
            # remove only that numerical excess from positive q entries,
            # deterministically in descending q-mass / ascending cell order.
            #
            # This is not support growth and not a scientific-semantic change:
            # it is a materialization closure of the aggregate equality row.
            correction_applied = 0.0
            q_mass_corrected = q_mass.copy()

            if raw_balance < -ASSIGN_TOL:
                remaining = -raw_balance
                order = sorted(
                    range(len(q_mass_corrected)),
                    key=lambda idx: (-float(q_mass_corrected[idx]), int(q_cells[idx])),
                )
                for idx in order:
                    if remaining <= ASSIGN_TOL:
                        break
                    available = max(0.0, float(q_mass_corrected[idx]))
                    if available <= 0.0:
                        continue
                    take = min(available, remaining)
                    q_mass_corrected[idx] -= take
                    remaining -= take
                    correction_applied += take

                gate(
                    f"group_{gid}_cellside_numerical_excess_fully_removed",
                    remaining <= ASSIGN_TOL,
                    remaining,
                )

            elif raw_balance > ASSIGN_TOL:
                raise GateError(
                    f"group_{gid}_positive_cellside_deficit_requires_capacity_aware_scientific_repair"
                )

            repaired_balance = float(
                y_mass.sum() - q_mass_corrected.sum()
            )
            gate(
                f"group_{gid}_aggregate_transport_balance_repaired",
                abs(repaired_balance) <= MATERIALIZATION_TOL,
                repaired_balance,
            )

            aggregate_repair_rows.append({
                "execution_group_id": gid,
                "raw_y_minus_q_kg": raw_balance,
                "cellside_q_excess_removed_kg": correction_applied,
                "repaired_y_minus_q_kg": repaired_balance,
                "CV_side_y_modified": False,
                "support_domain_modified": False,
                "scientific_LP_reexecuted": True,
                "scientific_semantics_modified": False,
                "materialization_tolerance_kg": MATERIALIZATION_TOL,
                "materialization_tolerance_basis": "CELL_TOL",
            })

            tc, th, tm, cv_left, cell_left = deterministic_transport(
                y_cvs, y_mass, q_cells, q_mass_corrected
            )
            max_transport_cv_left = max(max_transport_cv_left, cv_left)
            max_transport_cell_left = max(max_transport_cell_left, cell_left)

            for cv, cell, amount in zip(tc, th, tm):
                if amount <= ASSIGN_TOL:
                    continue
                explicit_cv.append(int(cv))
                explicit_cell.append(int(cell))
                explicit_mass.append(float(amount))
                explicit_class.append(f"R6R16R1R1_GROUP_{gid}_AGGREGATE_TRANSPORT")
                transport_rows.append({
                    "execution_group_id": gid,
                    "cv_id": int(cv),
                    "flat_cell": int(cell),
                    "contribution_kg": float(amount),
                    "transport_rule": "deterministic_sorted_complete_bipartite_transport",
                })

        gate("transport_CV_leftover_bounded", max_transport_cv_left <= ASSIGN_TOL, max_transport_cv_left)
        gate(
            "transport_cell_leftover_bounded",
            max_transport_cell_left <= MATERIALIZATION_TOL,
            max_transport_cell_left,
        )

        # Coalesce duplicate explicit CV-cell contributions.
        coalesced: dict[tuple[int, int], float] = {}
        for cv, cell, amount in zip(explicit_cv, explicit_cell, explicit_mass):
            coalesced[(int(cv), int(cell))] = (
                coalesced.get((int(cv), int(cell)), 0.0) + float(amount)
            )
        halo_keys = sorted(k for k, v in coalesced.items() if v > ASSIGN_TOL)
        halo_cv = np.asarray([k[0] for k in halo_keys], dtype=np.int64)
        halo_cell = np.asarray([k[1] for k in halo_keys], dtype=np.int64)
        halo_mass = np.asarray([coalesced[k] for k in halo_keys], dtype=float)

        executed_cv_mass = (
            np.bincount(pair_cv, weights=new_pair_val, minlength=NCVT) +
            np.bincount(halo_cv, weights=halo_mass, minlength=NCVT)
        )
        max_global_cv_delta = float(np.max(np.abs(executed_cv_mass - current_cv_mass)))

        executed_grid = (
            old_grid +
            np.bincount(pair_cell, weights=new_pair_val, minlength=NCELL) +
            np.bincount(halo_cell, weights=halo_mass, minlength=NCELL)
        )
        lower_excess = np.maximum(-executed_grid, 0.0)
        upper_excess = np.maximum(executed_grid - capacity, 0.0)
        lower_count = int(np.count_nonzero(lower_excess > CELL_TOL))
        upper_count = int(np.count_nonzero(upper_excess > CELL_TOL))
        max_global_lower = float(np.max(lower_excess))
        max_global_upper = float(np.max(upper_excess))

        ledger_error = abs(
            float(
                (executed_grid.sum() - old_grid.sum()) -
                current_cv_mass.sum()
            )
        )

        gate("all_CV_mass_preserved", max_global_cv_delta <= CV_TOL, max_global_cv_delta)
        gate("global_mass_ledger_after_R6R16", ledger_error <= LEDGER_TOL, ledger_error)

        # Scope-specific groups must now be capacity exact; the global grid may still
        # contain residual violations from the remaining previously-designed groups.
        joint_local_mass = executed_grid[local]
        joint_local_lower = max(0.0, -float(np.min(joint_local_mass)))
        joint_local_upper = max(
            0.0,
            float(np.max(joint_local_mass - capacity[local])),
        )
        gate("executed_joint_local_lower_exact", joint_local_lower <= CELL_TOL, joint_local_lower)
        gate("executed_joint_local_upper_exact", joint_local_upper <= CELL_TOL, joint_local_upper)

        stage = "sign_relaxation_audit"
        sign_rows: list[dict[str, Any]] = []
        crossing_count = 0
        for q, original, gid, penalty in zip(
            relaxed_x_indices,
            relaxed_x_original,
            relaxed_x_group,
            sign_penalty.tolist(),
        ):
            new_value = float(zbase[q])
            crossed = (
                (original > SIGN_TOL and new_value < -SIGN_TOL) or
                (original < -SIGN_TOL and new_value > SIGN_TOL)
            )
            if crossed:
                crossing_count += 1
            sign_rows.append({
                "execution_group_id": int(gid),
                "joint_existing_pair_variable_index": int(q),
                "cv_id": int(xcv[q]),
                "flat_cell": int(xcell[q]),
                "original_contribution_kg": float(original),
                "executed_contribution_kg": new_value,
                "sign_crossed": bool(crossed),
                "sign_crossing_penalty_kg": float(penalty),
            })

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)

        state_path = out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Provisional_FiveGroup_Reconciled_Day375_State.npz"
        np.savez_compressed(
            state_path,
            existing_pair_cv=pair_cv,
            existing_pair_cell=pair_cell,
            reconciled_existing_pair_contribution_kg=new_pair_val,
            halo_cv=halo_cv,
            halo_cell=halo_cell,
            halo_contribution_kg=halo_mass,
            provisional_grid_component_mass_kg=executed_grid,
            preserved_CV_mass_kg=executed_cv_mass,
            parent_pressure_psi=parent_pressure,
            joint_execution_group_ids=np.asarray(UNRES, dtype=np.int64),
            joint_union_cv=union_cvs,
            joint_local_cell=local,
            state_day=np.asarray(375.0),
            state_accepted=np.asarray(False),
        )
        state_sha = sha256_file(state_path)

        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Explicit_H2_Transport.csv").write_bytes(
            csv_bytes(transport_rows)
        )
        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Aggregate_Transport_Numerical_Closure_Audit.csv").write_bytes(
            csv_bytes(aggregate_repair_rows)
        )
        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Sign_Relaxation_Audit.csv").write_bytes(
            csv_bytes(sign_rows)
        )

        group_exec_rows: list[dict[str, Any]] = []
        for gid in UNRES:
            group_exec_rows.append({
                "execution_group_id": gid,
                "support_domain": plan[gid]["support_domain"],
                "H2_eligibility": plan[gid]["H2_eligibility"],
                "existing_pair_sign_relaxed": plan[gid]["existing_pair_sign_relaxed"],
                "candidate_pool_cell_count": len(pools[gid]),
                "joint_execution": True,
                "independent_execution": False,
            })
        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Group_Execution_Audit.csv").write_bytes(
            csv_bytes(group_exec_rows)
        )

        global_closed = lower_count == 0 and upper_count == 0
        if global_closed:
            classification = (
                "R6R16R1R1_FIVE_GROUP_JOINT_EXECUTION_PASS_GLOBAL_CELL_CAPACITY_CLOSED_"
                "STATE_ACCEPTANCE_AUDIT_NEXT"
            )
            next_name = "Day375 R6-R16 Provisional State Global Closure and Acceptance Audit"
            next_acceptance_audit = True
            next_remaining_audit = False
        else:
            classification = (
                "R6R16R1R1_FIVE_GROUP_JOINT_EXECUTION_PASS_PROVISIONAL_STATE_"
                "REMAINING_GLOBAL_CELL_VIOLATIONS_REQUIRE_CLOSURE_READINESS_AUDIT"
            )
            next_name = "Day375 Post-R6-R16 Remaining Residual Global Closure and Execution Readiness Audit"
            next_acceptance_audit = False
            next_remaining_audit = True

        summary = {
            "milestone": MILESTONE,
            "name": NAME,
            "status": STATUS_PASS,
            "classification": classification,
            "executed_group_ids": UNRES,
            "repair_parent_milestone": "POSTV16-AV4-PIVOT-P2-R6-R16-R1",
            "repair_grandparent_milestone": "POSTV16-AV4-PIVOT-P2-R6-R16",
            "original_R6R16R1_BLOCK_sha256": r16r1_block_sha256,
            "original_R6R16R1_failed_stage": R16R1_BLOCK_STAGE,
            "original_R6R16R1_failed_gate": "group_0_aggregate_transport_balance_repaired",
            "materialization_tolerance_kg": MATERIALIZATION_TOL,
            "materialization_tolerance_basis": "CELL_TOL",
            "original_R6R16_BLOCK_sha256": original_r16_block_sha256,
            "original_R6R16_failed_stage": R16_ORIGINAL_BLOCK_STAGE,
            "original_R6R16_failed_gate": "transport_cell_leftover_bounded",
            "aggregate_transport_numerical_closure_executed": True,
            "aggregate_transport_CV_side_modified": False,
            "aggregate_transport_support_domain_modified": False,
            "joint_execution": True,
            "independent_group_execution": False,
            "stageA_feasibility_success": bool(lp_feas.success),
            "stageB_sign_minimization_success": bool(lp.success),
            "sign_relaxed_existing_pair_variable_count": npen,
            "sign_crossing_pair_count": crossing_count,
            "minimum_total_sign_crossing_kg": total_sign_crossing_kg,
            "maximum_single_pair_sign_crossing_kg": max_sign_crossing_kg,
            "maximum_joint_CV_residual_kg": max_cv_residual,
            "maximum_joint_cell_lower_violation_kg": max_lower,
            "maximum_joint_cell_upper_violation_kg": max_upper,
            "explicit_H2_transport_edge_count": len(transport_rows),
            "coalesced_halo_edge_count": len(halo_mass),
            "maximum_global_CV_mass_delta_kg": max_global_cv_delta,
            "global_mass_ledger_error_kg": ledger_error,
            "post_execution_global_lower_violation_cell_count": lower_count,
            "post_execution_global_upper_violation_cell_count": upper_count,
            "post_execution_global_maximum_lower_violation_kg": max_global_lower,
            "post_execution_global_maximum_upper_violation_kg": max_global_upper,
            "global_cell_capacity_closed": global_closed,
            "provisional_state_sha256": state_sha,
            "state_mutation_executed": True,
            "state_accepted": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        contract = {
            "milestone": MILESTONE,
            "name": NAME,
            "status": STATUS_PASS,
            "classification": classification,
            "repair_parent_milestone": "POSTV16-AV4-PIVOT-P2-R6-R16-R1",
            "original_R6R16R1_BLOCK_sha256": r16r1_block_sha256,
            "original_R6R16_BLOCK_sha256": original_r16_block_sha256,
            "technical_repair_contract": {
                "repair_scope": "floating_point_materialization_tolerance_only",
                "materialization_tolerance_kg": MATERIALIZATION_TOL,
                "materialization_tolerance_basis": "CELL_TOL",
                "CV_side_y_solution_immutable": True,
                "support_domains_immutable": True,
                "R6R15_scientific_semantics_immutable": True,
                "q_excess_subtraction_allowed_only_within_LEDGER_TOL": True,
                "positive_q_deficit_repair_forbidden": True,
            },
            "execution_contract": {
                "single_coupled_five_group_LP_executed": True,
                "global_cell_capacity_constraints_enforced": True,
                "single_global_mass_ledger_enforced": True,
                "independent_group_execution_forbidden": True,
                "entry_candidate_domains_immutable": True,
                "cell_to_cell_mass_transit_used": False,
                "sign_relaxation_scope_limited_to_groups_0_3": True,
                "sign_relaxation_magnitude_minimized": True,
                "explicit_CV_to_cell_transport_reconstructed": True,
                "provisional_state_only": True,
            },
            "provisional_state_sha256": state_sha,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "P2_R6_R17_authorized": True,
            "P2_R6_R17_name": next_name,
            "P2_R6_R17_state_acceptance_audit_authorized": next_acceptance_audit,
            "P2_R6_R17_remaining_global_closure_readiness_audit_authorized": next_remaining_audit,
            "P2_R6_R17_must_bind_R6R15_design_contract": True,
            "P2_R6_R17_must_bind_R6R16R1R1_provisional_state": True,
            "accepted_Day375_state_authorized_now": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Summary.json").write_bytes(
            json_bytes(summary)
        )
        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Execution_Contract.json").write_bytes(
            json_bytes(contract)
        )
        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Decision_Contract.json").write_bytes(
            json_bytes(decision)
        )

        gate("R5_authority_unchanged_after_execution", sha256_file(r5_state) == R5SHA)

        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Final_Gate_Matrix.csv").write_bytes(
            csv_bytes(gates)
        )

        manifest_rows: list[dict[str, Any]] = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        (out / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Artifact_Manifest.csv").write_bytes(
            csv_bytes(manifest_rows)
        )

        print("=" * 190)
        print("POSTV16-AV4-PIVOT-P2-R6-R16-R1-R1: PASS")
        print("Executed groups                         :", UNRES)
        print("Minimum total sign crossing kg          :", total_sign_crossing_kg)
        print("Sign-crossing pair count                :", crossing_count)
        print("Maximum global CV delta kg              :", max_global_cv_delta)
        print("Global mass ledger error kg             :", ledger_error)
        print("Remaining lower-violation cells         :", lower_count)
        print("Remaining upper-violation cells         :", upper_count)
        print("Global cell capacity closed              :", global_closed)
        print("Provisional state SHA256                 :", state_sha)
        print("State accepted                           : False")
        print("Pressure / time / P3                     : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        rp = block / "POSTV16_AV4_PIVOT_P2_R6_R16_R1_R1_Blocked_Report.json"
        if not rp.exists():
            rp.write_bytes(json_bytes({
                "milestone": MILESTONE,
                "status": STATUS_BLOCK,
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
        print(MILESTONE + ": BLOCKED")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    raise SystemExit(main(args.project_root, args.drive_root))
