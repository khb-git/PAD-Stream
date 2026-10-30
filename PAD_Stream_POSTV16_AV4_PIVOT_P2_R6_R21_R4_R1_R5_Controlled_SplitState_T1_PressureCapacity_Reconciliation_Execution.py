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
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, lil_matrix

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1-R5"
NAME = "Controlled Split-State Day375 Pressure-Capacity Reconciliation Execution — T1 Face Domain"

PASS = (
    "AV4PIVOTP2R6R21R4R1R5_CONTROLLED_SPLIT_STATE_T1_DAY375_"
    "PRESSURE_CAPACITY_RECONCILIATION_EXECUTION_PASS_PRESSURE_REFRESH_ACCEPTED_NO_TIME_ADVANCE"
)
FAIL = (
    "AV4PIVOTP2R6R21R4R1R5_CONTROLLED_SPLIT_STATE_T1_DAY375_"
    "PRESSURE_CAPACITY_RECONCILIATION_SCIENTIFIC_FAIL_NO_AUTOMATIC_GROWTH"
)
BLOCK = "AV4PIVOTP2R6R21R4R1R5_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "de3b149e2da2f8ec06b2cfa21f4f70823937d7f7"

R4_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_"
    "SplitState_CVAttributed_PressureReconciliation_Semantics_Feasibility_Freeze.py"
)
R4_BLOB = "063e5b937b7494d5338c5564a248939bcdf0acee"

F1R2_RUNNER = "PAD_Stream_POSTV16_AV4_F1_R2_Corrected_Restart_State_and_Conservative_Parent_Projection_Freeze.py"
F1R2_BLOB = "51f86f3591bf66148ef468b304c18fb4fc668e77"

A2E_RUNNER = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3PHYS = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3PHYS_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R4 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_"
    "SplitState_CVAttributed_PressureReconciliation_Semantics_Feasibility_Freeze"
)
F1R2 = BASE / "POSTV16_AV4_F1_R2_Restart_State_and_Conservative_Parent_Projection_Freeze"
D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
R19 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Day375_Remaining_NonExecuted_R7_"
    "Group_Coupled_Global_CVConservative_Reconciliation_Execution"
)
R20 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
R3DIR = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R3_FirstIteration_"
    "PressureInduced_LocalCapacityLoss_Diagnostic_Freeze"
)
A2E = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A6E = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"

R4_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Summary.json"
R4_SEMANTICS = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Split_State_Reconciliation_Semantics_Contract.json"
R4_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Decision_Contract.json"
R4_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Artifact_Manifest.csv"

F1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F1_R2_Summary.json"
F1R2_PROJECTION = "POSTV16_AV4_F1_R2_Conservative_Grid_to_Streamline_Projection_Protocol.json"
F1R2_RESIDUAL = "POSTV16_AV4_F1_R2_Residual_Grid_State_Sidecar_Contract.json"
F1R2_MANIFEST = "POSTV16_AV4_F1_R2_Artifact_Manifest.csv"
F1R2_STATUS = (
    "AV4F1R2_F1R1_TECHNICAL_CLOSURE_BOUND_E1R2_STRUCTURAL_RESTART_"
    "INCOMPATIBILITY_BOUND_RESTART_STATE_REPRESENTATION_CONSERVATIVE_"
    "SPLIT_PARENT_PROJECTION_AND_TEMPORAL_SEMANTICS_PROSPECTIVELY_"
    "FROZEN_NO_PROJECTION_EXECUTION"
)

D370_STATE = "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"
R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_Summary.json"
R3_CELL_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Violating_Cell_Audit.csv"
R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Artifact_Manifest.csv"

A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_"
    "Controlled_SplitState_T1_Day375_PressureCapacity_Reconciliation_Execution"
)
SCI = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_SCIENTIFIC_FAIL"
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_BLOCKED"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = 37500
DAY = 375.0

MAX_ITER = 100
PRESSURE_TOL = 1e-10
SAT_TOL = 1e-10
LINEAR_TOL = 1e-8
CELL_CAP_TOL_FLOOR = 1e-8
CV_TOL = 1e-10
GLOBAL_TOL = 1e-10
EDGE_SLACK_TOL = 1e-12

R4_STATUS = (
    "AV4PIVOTP2R6R21R4R1R4_SPLIT_STATE_CV_ATTRIBUTED_"
    "PRESSURE_RECONCILIATION_SEMANTICS_FEASIBILITY_FREEZE_PASS_NO_STATE_MUTATION"
)
R4_CLASS = "R6R21R4R1R4_SPLIT_STATE_SEMANTICS_FROZEN_T1_FACE_EXACT_FEASIBLE_EXECUTION_NEXT"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_array(a: np.ndarray) -> str:
    arr = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode())
    h.update(repr(arr.shape).encode())
    h.update(arr.tobytes(order="C"))
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
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


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


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=float))))


def relative_l2(new: np.ndarray, old: np.ndarray) -> float:
    a = np.asarray(new, dtype=float)
    b = np.asarray(old, dtype=float)
    return float(np.linalg.norm((a-b).ravel()) / max(float(np.linalg.norm(b.ravel())), 1e-30))


def ijk(c: int) -> tuple[int, int, int]:
    k = c // 2500
    rem = c % 2500
    j = rem // 50
    i = rem % 50
    return int(k), int(j), int(i)


def flat(k: int, j: int, i: int) -> int:
    return int(k * 2500 + j * 50 + i)


def face_neighbors(c: int) -> list[int]:
    k, j, i = ijk(c)
    out = []
    for dk, dj, di in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
        kk, jj, ii = k+dk, j+dj, i+di
        if 0 <= kk < NZ and 0 <= jj < NY and 0 <= ii < NX:
            out.append(flat(kk,jj,ii))
    return sorted(out)


def add_ledger(
    ledger: dict[tuple[int,int], float],
    cvs: np.ndarray,
    cells: np.ndarray,
    mass: np.ndarray,
) -> None:
    for cv, cell, amount in zip(cvs.tolist(), cells.tolist(), mass.tolist()):
        key = (int(cv), int(cell))
        ledger[key] = ledger.get(key, 0.0) + float(amount)


def combine_ledger(
    base: dict[tuple[int,int], float],
    delta: dict[tuple[int,int], float],
) -> dict[tuple[int,int], float]:
    out = dict(base)
    for key, value in delta.items():
        out[key] = out.get(key, 0.0) + float(value)
    return out


def ledger_cell_grid(ledger: dict[tuple[int,int], float]) -> np.ndarray:
    out = np.zeros(NCELL, dtype=float)
    for (_cv, cell), amount in ledger.items():
        out[int(cell)] += float(amount)
    return out


def sidecar_cell_grid(sidecar: dict[tuple[int,int], float]) -> np.ndarray:
    return ledger_cell_grid(sidecar)


def sidecar_cv_residual(sidecar: dict[tuple[int,int], float]) -> tuple[float, float]:
    d: dict[int, float] = {}
    total = 0.0
    for (cv, _cell), amount in sidecar.items():
        d[int(cv)] = d.get(int(cv), 0.0) + float(amount)
        total += float(amount)
    return max((abs(x) for x in d.values()), default=0.0), abs(total)


def capacity_tol(capacity: np.ndarray) -> float:
    return max(CELL_CAP_TOL_FLOOR, 1e-12 * max(float(np.max(capacity)), 1.0))


def solve_increment(
    *,
    sources: list[int],
    excess: dict[int,float],
    current_ledger: dict[tuple[int,int], float],
    current_mass: np.ndarray,
    capacity: np.ndarray,
    frozen_domain: set[int],
) -> dict[str, Any]:

    cf = np.asarray(capacity, dtype=float).reshape(-1)
    mf = np.asarray(current_mass, dtype=float).reshape(-1)
    slack = np.maximum(cf - mf, 0.0)

    edges: list[tuple[int,int,int]] = []
    availability: dict[tuple[int,int], float] = {}

    for source in sources:
        positive = sorted(
            (cv, amount)
            for (cv, cell), amount in current_ledger.items()
            if cell == source and amount > 1e-13
        )
        for cv, amount in positive:
            availability[(int(cv), int(source))] = float(amount)
            for target in face_neighbors(source):
                if target not in frozen_domain:
                    continue
                if slack[target] <= EDGE_SLACK_TOL:
                    continue
                edges.append((int(cv), int(source), int(target)))

    if not edges:
        raise ScientificFail(
            "frozen_T1_no_admissible_CV_target_edges",
            {"source_cells": sources, "excess_kg": excess},
        )

    targets = sorted(set(t for _cv,_s,t in edges))
    cvsrc = sorted(set((cv,s) for cv,s,_t in edges))
    src_ix = {s:r for r,s in enumerate(sources)}
    tgt_ix = {t:r for r,t in enumerate(targets)}
    cvsrc_ix = {x:r for r,x in enumerate(cvsrc)}
    n = len(edges)

    Aeq = lil_matrix((len(sources), n), dtype=float)
    beq = np.asarray([excess[s] for s in sources], dtype=float)
    for j, (_cv,s,_t) in enumerate(edges):
        Aeq[src_ix[s],j] = 1.0

    Aub = lil_matrix((len(targets)+len(cvsrc), n), dtype=float)
    bub = np.zeros(len(targets)+len(cvsrc), dtype=float)
    for t,r in tgt_ix.items():
        bub[r] = float(slack[t])

    for j,(cv,s,t) in enumerate(edges):
        Aub[tgt_ix[t],j] = 1.0
        Aub[len(targets)+cvsrc_ix[(cv,s)],j] = 1.0

    for key,r in cvsrc_ix.items():
        bub[len(targets)+r] = float(availability[key])

    # Deterministic weak tie-breaker inside the already frozen face domain.
    cvec = np.asarray(
        [
            1e-12 * (1 + tgt_ix[t])
            + 1e-15 * (1 + cvsrc_ix[(cv,s)])
            for cv,s,t in edges
        ],
        dtype=float,
    )

    res = linprog(
        cvec,
        A_ub=csr_matrix(Aub),
        b_ub=bub,
        A_eq=csr_matrix(Aeq),
        b_eq=beq,
        bounds=[(0.0,None)]*n,
        method="highs",
    )

    if not res.success:
        raise ScientificFail(
            "frozen_T1_CV_reconciliation_LP_infeasible",
            {
                "solver_status": int(res.status),
                "solver_message": str(res.message),
                "source_cells": sources,
                "total_excess_kg": float(sum(excess.values())),
                "edge_count": n,
                "target_count": len(targets),
            },
        )

    x = np.asarray(res.x, dtype=float)
    increment: dict[tuple[int,int], float] = {}
    used = []
    for (cv,s,t), amount in zip(edges, x.tolist()):
        amount = float(amount)
        if amount <= 1e-12:
            continue
        increment[(cv,s)] = increment.get((cv,s),0.0) - amount
        increment[(cv,t)] = increment.get((cv,t),0.0) + amount
        used.append((cv,s,t,amount))

    return {
        "increment": increment,
        "used": used,
        "edge_count": n,
        "target_count": len(targets),
        "cv_source_count": len(cvsrc),
        "objective": float(res.fun),
    }


def selftest() -> None:
    assert len(face_neighbors(flat(1,1,1))) == 6

    ledger = {(10,0):2.0}
    mass = np.zeros(NCELL)
    cap = np.ones(NCELL)*10.0
    mass[0] = 11.0
    cap[0] = 10.0
    frozen = {0,1}
    out = solve_increment(
        sources=[0],
        excess={0:1.0},
        current_ledger=ledger,
        current_mass=mass,
        capacity=cap,
        frozen_domain=frozen,
    )
    inc = out["increment"]
    maxcv, glob = sidecar_cv_residual(inc)
    assert maxcv < 1e-12
    assert glob < 1e-12
    delta = sidecar_cell_grid(inc)
    repaired = mass + delta
    assert repaired[0] <= cap[0] + 1e-12
    assert repaired[1] <= cap[1] + 1e-12

    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1-R5 structural self-test: PASS")


def main(root: Path, drive: Path) -> int:
    root = root.resolve()
    drive = drive.resolve()

    out = drive / OUT
    sci = drive / SCI
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

    def sci_gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise ScientificFail(name, detail)

    try:
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Summary.json"
        sci_path = sci / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Scientific_Fail_Report.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Blocked_Report.json"

        if summary_path.is_file():
            print("[PASS] formal R6-R21-R4-R1-R5 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R5_SCIENTIFIC_FAIL", not sci_path.exists())
        gate("no_preexisting_R5_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R4R1R4", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, blob, label in [
            (R4_RUNNER, R4_BLOB, "R4R1R4"),
            (F1R2_RUNNER, F1R2_BLOB, "F1R2"),
            (A2E_RUNNER, A2E_BLOB, "A2E"),
            (R2, R2_BLOB, "R2"),
            (SG2, SG2_BLOB, "SG2"),
            (SG3, SG3_BLOB, "SG3"),
            (R3PHYS, R3PHYS_BLOB, "R3R2R1"),
            (PERM, PERM_BLOB, "PERM"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R4R1R4_execution_authority"
        r4 = drive / R4
        manifest(r4, R4_MANIFEST)
        s4 = js(r4 / R4_SUMMARY)
        c4 = js(r4 / R4_SEMANTICS)
        d4 = js(r4 / R4_DECISION)

        gate("R4_status_exact", s4.get("status") == R4_STATUS, s4.get("status"))
        gate("R4_classification_exact", s4.get("classification") == R4_CLASS, s4.get("classification"))
        gate("R5_authorized", d4.get("P2_R6_R21_R4_R1_R5_authorized") is True)
        gate("R5_controlled_execution_authorized", d4.get("P2_R6_R21_R4_R1_R5_controlled_execution_authorized") is True)
        gate("R5_frozen_domain_T1", d4.get("P2_R6_R21_R4_R1_R5_frozen_domain_tier") == "T1_FACE")
        gate("residual_Cartesian_sidecar_must_remain_immutable", d4.get("residual_Cartesian_sidecar_must_remain_immutable") is True)
        gate("reverse_H1_to_S0_forbidden", d4.get("reverse_H1_to_S0_pullback_authorized") is False)
        gate("automatic_domain_growth_forbidden", d4.get("automatic_domain_growth_authorized") is False)
        gate("pressure_sidecar_execution_authorized", d4.get("pressure_reconciliation_sidecar_execution_authorized") is True)
        gate("R4_no_state_mutation", s4.get("state_mutation_executed") is False)
        gate("R4_semantics_selected_T1", c4.get("selected_minimal_exact_feasible_tier") == "T1_FACE")

        stage = "F1R2_split_state_binding"
        f1 = drive / F1R2
        manifest(f1, F1R2_MANIFEST)
        sf1 = js(f1 / F1R2_SUMMARY)
        pf1 = js(f1 / F1R2_PROJECTION)
        rf1 = js(f1 / F1R2_RESIDUAL)
        gate("F1R2_status_exact", sf1.get("status") == F1R2_STATUS)
        gate("F1R2_reverse_halo_pullback_false", sf1.get("reverse_halo_pullback") is False)
        gate(
            "F1R2_global_split_mass_ledger_exact",
            pf1["residual_grid_sidecar"]["global_ledger"] ==
            "sum(M_cv) + sum(R_grid) = sum(M_parent_grid)",
        )
        state_blocks = {x["name"] for x in rf1["state_blocks"]}
        gate("F1R2_transport_CV_state_present", "transport_CV_component_mass" in state_blocks)
        gate("F1R2_grid_residual_state_present", "grid_residual_component_mass" in state_blocks)

        stage = "accepted_Day375_state_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R20_state_accepted", a20.get("accepted_Day375_state") is True)
        gate("R20_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        state_path = r19 / R19_STATE
        gate("R19_state_SHA_exact", sha(state_path) == accepted_sha, sha(state_path))

        with np.load(state_path, allow_pickle=False) as z:
            accepted_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(GRID)
            inherited_pressure = np.asarray(z["parent_pressure_psi"], dtype=float)
            r19_pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            r19_pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            r19_pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            r19_halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            r19_halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            r19_halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            state_day = float(np.asarray(z["state_day"]).reshape(()))

        gate("accepted_state_day_375", state_day == DAY, state_day)

        d370_path = drive / D370 / D370_STATE
        gate("Day370_state_present", d370_path.is_file(), str(d370_path))
        with np.load(d370_path, allow_pickle=False) as z:
            d370_pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            d370_pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            d370_pair_mass = np.asarray(z["repaired_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            d370_halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            d370_halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            d370_halo_mass = np.asarray(z["repaired_halo_contribution_kg"], dtype=float).reshape(-1)

        base_ledger: dict[tuple[int,int], float] = {}
        add_ledger(base_ledger, d370_pair_cv, d370_pair_cell, d370_pair_mass)
        add_ledger(base_ledger, d370_halo_cv, d370_halo_cell, d370_halo_mass)
        add_ledger(base_ledger, r19_pair_cv, r19_pair_cell, r19_pair_mass)
        add_ledger(base_ledger, r19_halo_cv, r19_halo_cell, r19_halo_mass)

        base_explicit_grid = ledger_cell_grid(base_ledger)
        residual_cartesian = accepted_mass.reshape(-1) - base_explicit_grid
        residual_sha = sha_array(residual_cartesian)

        stage = "R3_source_domain_binding"
        r3dir = drive / R3DIR
        manifest(r3dir, R3_MANIFEST)
        s3 = js(r3dir / R3_SUMMARY)
        rows3 = csvr(r3dir / R3_CELL_AUDIT)
        gate("R3_PASS", s3.get("status") == "AV4PIVOTP2R6R21R3_FIRST_ITERATION_PRESSURE_INDUCED_CAPACITY_LOSS_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION")
        original_sources = sorted(int(r["flat_cell"]) for r in rows3)
        gate("R3_source_count_9", len(original_sources) == 9, original_sources)

        frozen_domain = set(original_sources)
        for s in original_sources:
            frozen_domain.update(face_neighbors(s))
        frozen_domain_sorted = sorted(frozen_domain)

        gate("frozen_T1_domain_nonempty", len(frozen_domain_sorted) >= 9, len(frozen_domain_sorted))

        stage = "physics_authority"
        a2e = mod(root / A2E_RUNNER, "r6r21r4r1r5_a2e")
        r2 = mod(root / R2, "r6r21r4r1r5_r2")
        sg2 = mod(root / SG2, "r6r21r4r1r5_sg2")
        sg3 = mod(root / SG3, "r6r21r4r1r5_sg3")
        r3phys = mod(root / R3PHYS, "r6r21r4r1r5_r3phys")

        gate("A2E_iteration_limit_exact", int(a2e.MAX_FIXED_POINT_ITERATIONS) == MAX_ITER)
        gate("A2E_pressure_tol_exact", float(a2e.PRESSURE_REL_L2_TOL) == PRESSURE_TOL)
        gate("A2E_saturation_tol_exact", float(a2e.SATURATION_LINF_TOL) == SAT_TOL)
        gate("A2E_pressure_linear_tol_exact", float(a2e.PRESSURE_LINEAR_REL_RESIDUAL_MAX) == LINEAR_TOL)

        control_path = drive / A6E / A6E_STATE
        gate("A6E_state_SHA_exact", control_path.is_file() and sha(control_path) == A6E_STATE_SHA)
        with np.load(control_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=float)
            nw = np.asarray(z["nw"], dtype=float)
            no = np.asarray(z["no"], dtype=float)
            krw_max = np.asarray(z["krw_max"], dtype=float)
            kro_max = np.asarray(z["kro_max"], dtype=float)

        pore_volume = phi * float(a2e.BULK_VOLUME_M3)

        a2edir = drive / A2E
        manifest(a2edir, A2E_MANIFEST)
        with np.load(a2edir / A2E_EPOCH, allow_pickle=False) as z:
            frozen_p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            p0 = np.asarray(z["refreshed_pressure_psi"], dtype=float)

        gate("accepted_inherited_pressure_matches_A2E", max_abs(inherited_pressure - p0) <= 1e-12)

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=float).reshape(GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        # Initial accepted saturation at the inherited pressure.
        try:
            sg0 = a2e.invert_local_mass(r2, accepted_mass, p0, frozen_p_ref, pore_volume)
        except Exception as exc:
            raise ScientificFail("accepted_state_initial_EOS_inversion_failure", repr(exc)) from exc

        working_sat = float(a2e.BACKGROUND) + np.asarray(sg0, dtype=float)
        previous_pressure = np.asarray(p0, dtype=float).copy()
        cumulative_sidecar: dict[tuple[int,int], float] = {}

        total_base_mass = float(np.sum(accepted_mass))
        cell_mass_tol = max(
            1e-8,
            1e-10 * max(float(np.max(accepted_mass)), 1.0),
        )

        iteration_rows = []
        sidecar_rows = []
        final_pressure = None
        final_sat = None
        final_mass = None
        final_tx = final_ty = final_tz = final_wi = None
        final_mobility = None

        stage = "coupled_split_state_fixed_point"

        for iteration in range(1, MAX_ITER + 1):
            current_ledger = combine_ledger(base_ledger, cumulative_sidecar)
            current_mass_flat = accepted_mass.reshape(-1) + sidecar_cell_grid(cumulative_sidecar)
            current_mass = current_mass_flat.reshape(GRID)

            # Split-state identity: residual Cartesian sidecar must not change.
            residual_now = current_mass_flat - ledger_cell_grid(current_ledger)
            sci_gate(
                f"iteration_{iteration:03d}_residual_cartesian_sidecar_immutable",
                max_abs(residual_now - residual_cartesian) <= 1e-10,
                max_abs(residual_now - residual_cartesian),
            )

            mobility = a2e.spatial_mobility(working_sat, nw, no, krw_max, kro_max)
            tx, ty, tz, _face = r3phys.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )

            try:
                A, b, wi = r3phys.assemble_updated_pressure_system(
                    sg3, permeability, tx, ty, tz, mobility["lambda_total"]
                )
                _ppa, pressure, linear_residual = r3phys.solve_updated_pressure(sg3, A, b)
            except Exception as exc:
                raise ScientificFail(
                    "pressure_solve_failure",
                    {"iteration": iteration, "exception": repr(exc)},
                ) from exc

            sci_gate(
                f"iteration_{iteration:03d}_pressure_linear_residual",
                float(linear_residual) < LINEAR_TOL,
                float(linear_residual),
            )

            full_sat = np.full(GRID, float(a2e.INJECTED), dtype=float)
            capacity = np.asarray(
                a2e.local_mass(r2, full_sat, pressure, frozen_p_ref, pore_volume),
                dtype=float,
            )
            ctol = capacity_tol(capacity)
            excess_arr = current_mass_flat - capacity.reshape(-1)
            violating = sorted(
                np.flatnonzero(excess_arr > ctol).astype(int).tolist()
            )

            outside = sorted(set(violating) - frozen_domain)
            if outside:
                raise ScientificFail(
                    "new_overcapacity_cell_outside_frozen_T1_domain",
                    {
                        "iteration": iteration,
                        "outside_cell_count": len(outside),
                        "outside_cells": outside,
                        "frozen_domain_cell_count": len(frozen_domain),
                    },
                )

            increment: dict[tuple[int,int], float] = {}
            used = []
            lp_edge_count = 0
            lp_target_count = 0
            lp_cvsrc_count = 0
            increment_abs = 0.0

            if violating:
                excess = {c: float(excess_arr[c]) for c in violating}

                current_positive = {
                    c: float(sum(
                        amount for (cv,cell), amount in current_ledger.items()
                        if cell == c and amount > 1e-13
                    ))
                    for c in violating
                }

                short = {
                    c: {
                        "available_kg": current_positive[c],
                        "required_kg": excess[c],
                    }
                    for c in violating
                    if current_positive[c] + 1e-12 < excess[c]
                }
                if short:
                    raise ScientificFail(
                        "frozen_T1_source_positive_CV_availability_insufficient",
                        {"iteration": iteration, "sources": short},
                    )

                lp = solve_increment(
                    sources=violating,
                    excess=excess,
                    current_ledger=current_ledger,
                    current_mass=current_mass,
                    capacity=capacity,
                    frozen_domain=frozen_domain,
                )
                increment = lp["increment"]
                used = lp["used"]
                lp_edge_count = int(lp["edge_count"])
                lp_target_count = int(lp["target_count"])
                lp_cvsrc_count = int(lp["cv_source_count"])
                increment_abs = float(sum(x[3] for x in used))

                for cv,s,t,amount in used:
                    sidecar_rows.append({
                        "iteration": iteration,
                        "cv_id": int(cv),
                        "source_cell": int(s),
                        "target_cell": int(t),
                        "source_k": ijk(int(s))[0],
                        "source_j": ijk(int(s))[1],
                        "source_i": ijk(int(s))[2],
                        "target_k": ijk(int(t))[0],
                        "target_j": ijk(int(t))[1],
                        "target_i": ijk(int(t))[2],
                        "increment_mass_kg": float(amount),
                    })

                for key, value in increment.items():
                    cumulative_sidecar[key] = cumulative_sidecar.get(key, 0.0) + float(value)

                # Recompute after same-pressure conservative repair.
                current_ledger = combine_ledger(base_ledger, cumulative_sidecar)
                current_mass_flat = accepted_mass.reshape(-1) + sidecar_cell_grid(cumulative_sidecar)
                current_mass = current_mass_flat.reshape(GRID)

                residual_now = current_mass_flat - ledger_cell_grid(current_ledger)
                sci_gate(
                    f"iteration_{iteration:03d}_postrepair_residual_sidecar_immutable",
                    max_abs(residual_now - residual_cartesian) <= 1e-10,
                    max_abs(residual_now - residual_cartesian),
                )

                post_excess = current_mass_flat - capacity.reshape(-1)
                sci_gate(
                    f"iteration_{iteration:03d}_postrepair_cell_capacity_closed",
                    float(np.max(post_excess)) <= ctol,
                    {
                        "maximum_excess_kg": float(np.max(post_excess)),
                        "tolerance_kg": ctol,
                    },
                )

            max_cv_sidecar, global_sidecar = sidecar_cv_residual(cumulative_sidecar)
            sci_gate(
                f"iteration_{iteration:03d}_cumulative_per_CV_sidecar_conservation",
                max_cv_sidecar <= CV_TOL,
                max_cv_sidecar,
            )
            sci_gate(
                f"iteration_{iteration:03d}_cumulative_global_sidecar_conservation",
                global_sidecar <= GLOBAL_TOL,
                global_sidecar,
            )

            try:
                sg_new = a2e.invert_local_mass(
                    r2,
                    current_mass,
                    pressure,
                    frozen_p_ref,
                    pore_volume,
                )
            except Exception as exc:
                raise ScientificFail(
                    "same_time_EOS_inversion_after_T1_reconciliation_failure",
                    {"iteration": iteration, "exception": repr(exc)},
                ) from exc

            reconciled_sat = float(a2e.BACKGROUND) + np.asarray(sg_new, dtype=float)
            reconstructed = np.asarray(
                a2e.local_mass(r2, reconciled_sat, pressure, frozen_p_ref, pore_volume),
                dtype=float,
            )

            cell_error = max_abs(reconstructed - current_mass)
            global_rel = abs(float(np.sum(reconstructed) - total_base_mass)) / max(abs(total_base_mass), 1.0)
            pressure_delta = relative_l2(pressure, previous_pressure)
            sat_delta = max_abs(reconciled_sat - working_sat)

            iteration_rows.append({
                "iteration": iteration,
                "violating_cell_count_before_repair": len(violating),
                "violating_cells_before_repair": ";".join(map(str, violating)),
                "sidecar_increment_mass_kg": increment_abs,
                "LP_candidate_edge_count": lp_edge_count,
                "LP_target_count": lp_target_count,
                "LP_CV_source_count": lp_cvsrc_count,
                "LP_used_edge_count": len(used),
                "pressure_relative_L2_change": pressure_delta,
                "saturation_Linf_change": sat_delta,
                "pressure_linear_relative_residual": float(linear_residual),
                "max_cell_mass_reconstruction_error_kg": cell_error,
                "global_mass_relative_error": global_rel,
                "cumulative_sidecar_abs_mass_kg": float(sum(abs(v) for v in cumulative_sidecar.values())) / 2.0,
                "cumulative_sidecar_nonzero_entry_count": int(sum(abs(v) > 1e-13 for v in cumulative_sidecar.values())),
                "cumulative_per_CV_residual_kg": max_cv_sidecar,
                "cumulative_global_sidecar_residual_kg": global_sidecar,
                "pressure_min_psi": float(np.min(pressure)),
                "pressure_max_psi": float(np.max(pressure)),
                "saturation_min": float(np.min(reconciled_sat)),
                "saturation_max": float(np.max(reconciled_sat)),
            })

            final_pressure = np.asarray(pressure, dtype=float)
            final_sat = np.asarray(reconciled_sat, dtype=float)
            final_mass = np.asarray(current_mass, dtype=float)
            final_tx, final_ty, final_tz, final_wi = tx, ty, tz, wi
            final_mobility = mobility

            if (
                pressure_delta <= PRESSURE_TOL
                and sat_delta <= SAT_TOL
                and increment_abs <= ctol
            ):
                sci_gate(
                    "fixed_point_cellwise_mass_error",
                    cell_error <= cell_mass_tol,
                    {"error_kg": cell_error, "tolerance_kg": cell_mass_tol},
                )
                sci_gate(
                    "fixed_point_global_mass_relative_error",
                    global_rel <= float(a2e.GLOBAL_MASS_REL_TOL),
                    global_rel,
                )
                break

            previous_pressure = np.asarray(pressure, dtype=float)
            working_sat = np.asarray(reconciled_sat, dtype=float)

        else:
            raise ScientificFail(
                "split_state_pressure_capacity_fixed_point_nonconvergence",
                {
                    "maximum_iterations": MAX_ITER,
                    "last_iteration": iteration_rows[-1] if iteration_rows else None,
                },
            )

        assert final_pressure is not None
        assert final_sat is not None
        assert final_mass is not None

        stage = "final_consistency"

        # Re-solve pressure from the accepted saturation, exactly as A2-E does.
        mobility_final = a2e.spatial_mobility(final_sat, nw, no, krw_max, kro_max)
        tx_final, ty_final, tz_final, _face_final = r3phys.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility_final["lambda_total"]
        )
        try:
            A, b, wi_final = r3phys.assemble_updated_pressure_system(
                sg3, permeability, tx_final, ty_final, tz_final, mobility_final["lambda_total"]
            )
            _ppa, pressure_check, linear_check = r3phys.solve_updated_pressure(sg3, A, b)
        except Exception as exc:
            raise ScientificFail("final_consistency_pressure_solve_failure", repr(exc)) from exc

        sci_gate("final_pressure_linear_residual", float(linear_check) < LINEAR_TOL, float(linear_check))

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=float)
        cap_check = np.asarray(
            a2e.local_mass(r2, full_sat, pressure_check, frozen_p_ref, pore_volume),
            dtype=float,
        )
        ctol_final = capacity_tol(cap_check)
        final_cap_excess = float(np.max(final_mass.reshape(-1) - cap_check.reshape(-1)))
        sci_gate(
            "final_fixed_domain_capacity_consistency",
            final_cap_excess <= ctol_final,
            {"maximum_excess_kg": final_cap_excess, "tolerance_kg": ctol_final},
        )

        try:
            sg_check = a2e.invert_local_mass(
                r2, final_mass, pressure_check, frozen_p_ref, pore_volume
            )
        except Exception as exc:
            raise ScientificFail("final_EOS_inversion_failure", repr(exc)) from exc

        sat_check = float(a2e.BACKGROUND) + np.asarray(sg_check, dtype=float)

        pressure_consistency = relative_l2(pressure_check, final_pressure)
        saturation_consistency = max_abs(sat_check - final_sat)

        sci_gate(
            "final_pressure_fixed_point_consistency",
            pressure_consistency <= PRESSURE_TOL,
            pressure_consistency,
        )
        sci_gate(
            "final_saturation_fixed_point_consistency",
            saturation_consistency <= SAT_TOL,
            saturation_consistency,
        )

        reconstructed_final = np.asarray(
            a2e.local_mass(r2, sat_check, pressure_check, frozen_p_ref, pore_volume),
            dtype=float,
        )
        final_cell_error = max_abs(reconstructed_final - final_mass)
        final_global_rel = abs(float(np.sum(reconstructed_final) - total_base_mass)) / max(abs(total_base_mass), 1.0)

        sci_gate(
            "final_cellwise_mass_reconstruction",
            final_cell_error <= cell_mass_tol,
            {"error_kg": final_cell_error, "tolerance_kg": cell_mass_tol},
        )
        sci_gate(
            "final_global_mass_relative_closure",
            final_global_rel <= float(a2e.GLOBAL_MASS_REL_TOL),
            final_global_rel,
        )
        sci_gate(
            "final_saturation_bounds",
            float(np.min(sat_check)) >= float(a2e.BACKGROUND) - 1e-12
            and float(np.max(sat_check)) <= float(a2e.INJECTED) + 1e-12,
            [float(np.min(sat_check)), float(np.max(sat_check))],
        )

        max_cv_sidecar, global_sidecar = sidecar_cv_residual(cumulative_sidecar)
        sci_gate("final_per_CV_sidecar_conservation", max_cv_sidecar <= CV_TOL, max_cv_sidecar)
        sci_gate("final_global_sidecar_conservation", global_sidecar <= GLOBAL_TOL, global_sidecar)

        final_delta = sidecar_cell_grid(cumulative_sidecar)
        final_mass_from_base = accepted_mass.reshape(-1) + final_delta
        sci_gate(
            "final_pressure_compatible_mass_matches_sidecar_definition",
            max_abs(final_mass_from_base - final_mass.reshape(-1)) <= 1e-12,
            max_abs(final_mass_from_base - final_mass.reshape(-1)),
        )
        sci_gate(
            "final_global_accepted_mass_unchanged",
            abs(float(np.sum(final_mass)) - total_base_mass) <= 1e-7,
            float(np.sum(final_mass) - total_base_mass),
        )

        final_ledger = combine_ledger(base_ledger, cumulative_sidecar)
        residual_final = final_mass.reshape(-1) - ledger_cell_grid(final_ledger)
        sci_gate(
            "final_residual_Cartesian_sidecar_immutable",
            max_abs(residual_final - residual_cartesian) <= 1e-10,
            max_abs(residual_final - residual_cartesian),
        )
        sci_gate(
            "final_residual_Cartesian_sidecar_SHA_exact",
            sha_array(residual_final) == residual_sha,
            {"expected": residual_sha, "actual": sha_array(residual_final)},
        )

        sidecar_keys = sorted(k for k,v in cumulative_sidecar.items() if abs(v) > 1e-13)
        sidecar_cv = np.asarray([k[0] for k in sidecar_keys], dtype=np.int64)
        sidecar_cell = np.asarray([k[1] for k in sidecar_keys], dtype=np.int64)
        sidecar_mass = np.asarray([cumulative_sidecar[k] for k in sidecar_keys], dtype=float)

        final_mass = np.asarray(final_mass, dtype=float)
        final_pressure = np.asarray(pressure_check, dtype=float)
        final_sat = np.asarray(sat_check, dtype=float)

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)

        state_name = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_PressureCompatible_Day375_State.npz"
        epoch_name = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_Day375_Pressure_Epoch.npz"

        state_bytes = deterministic_npz_bytes({
            "state_day": np.asarray(DAY),
            "source_R20_accepted_state_sha256": np.asarray(accepted_sha),
            "base_accepted_grid_mass_kg": accepted_mass,
            "pressure_reconciliation_sidecar_cv": sidecar_cv,
            "pressure_reconciliation_sidecar_cell": sidecar_cell,
            "pressure_reconciliation_sidecar_mass_kg": sidecar_mass,
            "pressure_compatible_grid_mass_kg": final_mass,
            "residual_cartesian_sidecar_kg": residual_cartesian.reshape(GRID),
            "residual_cartesian_sidecar_sha256": np.asarray(residual_sha),
            "pressure_compatible_saturation": final_sat,
            "refreshed_pressure_psi": final_pressure,
            "reference_gas_pressure_pa": np.asarray(frozen_p_ref),
            "frozen_T1_domain_flat_cell": np.asarray(frozen_domain_sorted, dtype=np.int64),
            "pressure_refresh_accepted": np.asarray(True),
            "physical_time_advanced": np.asarray(False),
        })
        (out / state_name).write_bytes(state_bytes)
        state_sha = sha(out / state_name)

        epoch_bytes = deterministic_npz_bytes({
            "canonical_day": np.asarray(DAY),
            "refreshed_pressure_psi": final_pressure,
            "reconciled_saturation": final_sat,
            "pressure_compatible_grid_mass_kg": final_mass,
            "reference_gas_pressure_pa": np.asarray(frozen_p_ref),
            "tx": np.asarray(tx_final),
            "ty": np.asarray(ty_final),
            "tz": np.asarray(tz_final),
            "producer_wi": np.asarray(wi_final),
            "lambda_total": np.asarray(mobility_final["lambda_total"]),
            "pressure_reconciliation_sidecar_cv": sidecar_cv,
            "pressure_reconciliation_sidecar_cell": sidecar_cell,
            "pressure_reconciliation_sidecar_mass_kg": sidecar_mass,
            "physical_time_advanced": np.asarray(False),
            "Darcy_Pollock_TOF_regenerated": np.asarray(False),
        })
        (out / epoch_name).write_bytes(epoch_bytes)
        epoch_sha = sha(out / epoch_name)

        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Fixed_Point_Iteration_Audit.csv").write_bytes(
            csvb(iteration_rows)
        )
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Sidecar_Increment_Audit.csv").write_bytes(
            csvb(sidecar_rows)
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": (
                "R6R21R4R1R5_SPLIT_STATE_T1_COUPLED_FIXED_POINT_PASS_"
                "DAY375_PRESSURE_REFRESH_ACCEPTED_DARCY_POLLOCK_TOF_REGENERATION_NEXT"
            ),
            "source_R20_accepted_state_sha256": accepted_sha,
            "pressure_compatible_state_sha256": state_sha,
            "accepted_pressure_epoch_sha256": epoch_sha,
            "residual_Cartesian_sidecar_sha256": residual_sha,
            "residual_Cartesian_sidecar_immutable": True,
            "reverse_H1_to_S0_pullback_used": False,
            "frozen_domain_tier": "T1_FACE",
            "frozen_domain_cell_count": len(frozen_domain_sorted),
            "coupled_fixed_point_iterations": len(iteration_rows),
            "total_sidecar_moved_mass_kg": float(np.sum(np.maximum(sidecar_mass, 0.0))),
            "sidecar_nonzero_entry_count": int(len(sidecar_mass)),
            "sidecar_unique_CV_count": int(len(set(sidecar_cv.tolist()))),
            "sidecar_unique_cell_count": int(len(set(sidecar_cell.tolist()))),
            "maximum_per_CV_sidecar_residual_kg": max_cv_sidecar,
            "global_sidecar_residual_kg": global_sidecar,
            "final_pressure_linear_relative_residual": float(linear_check),
            "final_pressure_fixed_point_consistency": pressure_consistency,
            "final_saturation_fixed_point_consistency": saturation_consistency,
            "final_cellwise_mass_reconstruction_error_kg": final_cell_error,
            "final_global_mass_relative_error": final_global_rel,
            "final_cell_capacity_max_excess_kg": final_cap_excess,
            "final_pressure_min_psi": float(np.min(final_pressure)),
            "final_pressure_max_psi": float(np.max(final_pressure)),
            "final_saturation_min": float(np.min(final_sat)),
            "final_saturation_max": float(np.max(final_sat)),
            "pressure_relative_L2_vs_inherited_Day365_epoch": relative_l2(final_pressure, inherited_pressure),
            "saturation_Linf_vs_inherited_Day375_at_Day365_pressure": max_abs(final_sat - (float(a2e.BACKGROUND) + sg0)),
            "accepted_Day375_transport_state_remains_authoritative": True,
            "pressure_refresh_accepted": True,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        contract = {
            "milestone": M,
            "status": PASS,
            "accepted_pressure_compatible_state_sha256": state_sha,
            "accepted_pressure_epoch_sha256": epoch_sha,
            "split_state_contract": {
                "base_transport_state_sha256": accepted_sha,
                "residual_Cartesian_sidecar_sha256": residual_sha,
                "residual_Cartesian_sidecar_immutable": True,
                "CV_sidecar_per_CV_conservation_exact": True,
                "CV_sidecar_global_conservation_exact": True,
                "reverse_H1_to_S0_pullback": False,
                "automatic_support_growth": False,
            },
            "pressure_refresh_contract": {
                "same_physical_time_days": DAY,
                "reference_gas_pressure_pa": frozen_p_ref,
                "fixed_domain": "T1_FACE",
                "pressure_relative_L2_tolerance": PRESSURE_TOL,
                "saturation_Linf_tolerance": SAT_TOL,
                "pressure_linear_relative_residual_max": LINEAR_TOL,
                "maximum_iterations": MAX_ITER,
                "pressure_refresh_accepted": True,
            },
            "downstream_firewall": {
                "Darcy_Pollock_TOF_regenerated": False,
                "physical_time_advanced": False,
                "P3_authorized": False,
            },
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "P2_R6_R22_authorized": True,
            "P2_R6_R22_name": "Controlled Day375 Accepted-State Darcy/Pollock/TOF Regeneration",
            "P2_R6_R22_must_bind_R4R1R5_pressure_epoch_SHA": True,
            "P2_R6_R22_Darcy_flux_regeneration_authorized": True,
            "P2_R6_R22_Pollock_streamline_regeneration_authorized": True,
            "P2_R6_R22_TOF_regeneration_authorized": True,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "accepted_Day375_pressure_refresh": True,
            "physical_time_advance_authorized": False,
            "transport_time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_Pressure_Refresh_Contract.json").write_bytes(jb(contract))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Accepted Day375 base state SHA256           :", accepted_sha)
        print("Pressure-compatible state SHA256            :", state_sha)
        print("Accepted pressure epoch SHA256              :", epoch_sha)
        print("Residual Cartesian sidecar SHA256           :", residual_sha)
        print("Coupled fixed-point iterations              :", len(iteration_rows))
        print("Total CV-sidecar moved mass kg              :", summary["total_sidecar_moved_mass_kg"])
        print("Sidecar unique CV / cell count              :", summary["sidecar_unique_CV_count"], "/", summary["sidecar_unique_cell_count"])
        print("Max per-CV / global sidecar residual kg     :", max_cv_sidecar, "/", global_sidecar)
        print("Final pressure fixed-point consistency      :", pressure_consistency)
        print("Final saturation fixed-point consistency    :", saturation_consistency)
        print("Final cell-capacity max excess kg           :", final_cap_excess)
        print("Pressure refresh accepted                   : True")
        print("Darcy/Pollock/TOF regenerated               : False")
        print("Physical time advanced                      : False")
        print("P2-R6-R22 authorized                        : True")
        print("P3 authorized                               : False")
        print("=" * 190)
        return 0

    except ScientificFail as exc:
        sci.mkdir(parents=True, exist_ok=True)
        p = sci / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": FAIL,
                "failed_stage": stage,
                "failed_gate": exc.gate,
                "detail": exc.detail,
                "accepted_Day375_state_preserved": True,
                "pressure_refresh_accepted": False,
                "residual_Cartesian_sidecar_preserved": True,
                "automatic_adaptation_or_domain_growth_authorized": False,
                "Darcy_Pollock_TOF_regeneration_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "SCIENTIFIC FAIL")
        print("Stage:", stage)
        print("Gate :", exc.gate)
        print("Detail:", exc.detail)
        return 3

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "accepted_Day375_state_preserved": True,
                "pressure_refresh_accepted": False,
                "residual_Cartesian_sidecar_preserved": True,
                "automatic_rerun_authorized": False,
                "Darcy_Pollock_TOF_regeneration_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
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
