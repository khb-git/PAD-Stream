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
from typing import Any, Callable

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, lil_matrix

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1-R4"
NAME = "Split-State CV-Attributed Same-Time Pressure-Reconciliation Semantics and Feasibility Freeze"

PASS = "AV4PIVOTP2R6R21R4R1R4_SPLIT_STATE_CV_ATTRIBUTED_PRESSURE_RECONCILIATION_SEMANTICS_FEASIBILITY_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R21R4R1R4_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "aa90167d52a0ae55fce428b35326f98f15e767f4"

R4R1R3_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Historical_ParentState_Provenance_Match_Diagnostic.py"
R4R1R3_BLOB = "61faf8f76ccfe572309a77f2800583e1d43c5412"

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
R4R1R2 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_"
    "Day370_RepairedLedger_CVCell_Provenance_Recovery_Diagnostic"
)
R4R1R3 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_"
    "Historical_ParentState_Provenance_Match_Diagnostic"
)
A2E = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A6E = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"

F1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F1_R2_Summary.json"
F1R2_PROJECTION = "POSTV16_AV4_F1_R2_Conservative_Grid_to_Streamline_Projection_Protocol.json"
F1R2_RESIDUAL = "POSTV16_AV4_F1_R2_Residual_Grid_State_Sidecar_Contract.json"
F1R2_DECISION = "POSTV16_AV4_F1_R2_Decision_Contract.json"
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
R4R1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Summary.json"
R4R1R2_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Artifact_Manifest.csv"
R4R1R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Summary.json"
R4R1R3_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Decision_Contract.json"
R4R1R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Artifact_Manifest.csv"

A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_"
    "SplitState_CVAttributed_PressureReconciliation_Semantics_Feasibility_Freeze"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_BLOCKED"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = 37500
DAY = 375.0
TOL = 1e-8


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
        kk, jj, ii = k + dk, j + dj, i + di
        if 0 <= kk < NZ and 0 <= jj < NY and 0 <= ii < NX:
            out.append(flat(kk, jj, ii))
    return sorted(out)


def same_layer_r2(c: int) -> list[int]:
    k, j, i = ijk(c)
    out = []
    for dj in range(-2, 3):
        for di in range(-2, 3):
            d = abs(di) + abs(dj)
            if d == 0 or d > 2:
                continue
            jj, ii = j + dj, i + di
            if 0 <= jj < NY and 0 <= ii < NX:
                out.append(flat(k, jj, ii))
    return sorted(set(out))


def graph_r2(c: int) -> list[int]:
    seen = {c}
    frontier = {c}
    for _ in range(2):
        nxt = set()
        for q in frontier:
            nxt.update(face_neighbors(q))
        nxt -= seen
        seen |= nxt
        frontier = nxt
    seen.discard(c)
    return sorted(seen)


def add_ledger(
    ledger: dict[tuple[int, int], float],
    cvs: np.ndarray,
    cells: np.ndarray,
    mass: np.ndarray,
) -> None:
    for cv, cell, amount in zip(cvs.tolist(), cells.tolist(), mass.tolist()):
        key = (int(cv), int(cell))
        ledger[key] = ledger.get(key, 0.0) + float(amount)


def candidate_targets(
    source: int,
    slack: np.ndarray,
    domain_fn: Callable[[int], list[int]],
) -> list[int]:
    sf = np.asarray(slack, dtype=float).reshape(-1)
    return sorted(t for t in set(domain_fn(source)) if sf[t] > TOL)


def solve_cv_lp(
    sources: list[int],
    excess: dict[int, float],
    targets_by_source: dict[int, list[int]],
    slack: np.ndarray,
    ledger: dict[tuple[int, int], float],
) -> dict[str, Any]:
    edges = []
    source_availability: dict[tuple[int, int], float] = {}

    for s in sources:
        positive = sorted(
            (cv, amount)
            for (cv, cell), amount in ledger.items()
            if cell == s and amount > 1e-13
        )
        for cv, amount in positive:
            source_availability[(int(cv), int(s))] = float(amount)
            for t in targets_by_source[s]:
                edges.append((int(cv), int(s), int(t)))

    if not edges:
        return {
            "success": False,
            "status": -999,
            "message": "no_edges",
            "edges": [],
            "x": np.zeros(0),
        }

    targets = sorted(set(t for _cv, _s, t in edges))
    cvsrc = sorted(set((cv, s) for cv, s, _t in edges))
    src_ix = {s: r for r, s in enumerate(sources)}
    tgt_ix = {t: r for r, t in enumerate(targets)}
    cvsrc_ix = {key: r for r, key in enumerate(cvsrc)}

    n = len(edges)

    Aeq = lil_matrix((len(sources), n), dtype=float)
    beq = np.asarray([excess[s] for s in sources], dtype=float)
    for j, (_cv, s, _t) in enumerate(edges):
        Aeq[src_ix[s], j] = 1.0

    Aub = lil_matrix((len(targets) + len(cvsrc), n), dtype=float)
    bub = np.zeros(len(targets) + len(cvsrc), dtype=float)
    sf = np.asarray(slack, dtype=float).reshape(-1)

    for t, r in tgt_ix.items():
        bub[r] = float(sf[t])

    for j, (cv, s, t) in enumerate(edges):
        Aub[tgt_ix[t], j] = 1.0
        Aub[len(targets) + cvsrc_ix[(cv, s)], j] = 1.0

    for key, r in cvsrc_ix.items():
        bub[len(targets) + r] = float(source_availability[key])

    # Feasibility only: total moved mass is already fixed by source equalities.
    res = linprog(
        np.zeros(n, dtype=float),
        A_ub=csr_matrix(Aub),
        b_ub=bub,
        A_eq=csr_matrix(Aeq),
        b_eq=beq,
        bounds=[(0.0, None)] * n,
        method="highs",
    )

    return {
        "success": bool(res.success),
        "status": int(res.status),
        "message": str(res.message),
        "edges": edges,
        "x": np.asarray(res.x, dtype=float) if res.x is not None else np.zeros(n),
        "target_count": len(targets),
        "cv_source_count": len(cvsrc),
        "edge_count": n,
    }


def sidecar_audit(
    lp: dict[str, Any],
    accepted_mass: np.ndarray,
    cap: np.ndarray,
) -> dict[str, Any]:
    if not lp["success"]:
        return {
            "max_per_CV_delta_kg": None,
            "global_sidecar_delta_kg": None,
            "max_lower_violation_kg": None,
            "max_upper_violation_kg": None,
            "used_edge_count": 0,
            "used_CV_count": 0,
            "sidecar": {},
        }

    sidecar: dict[tuple[int, int], float] = {}
    used_cvs = set()
    used_edges = 0

    for (cv, s, t), x in zip(lp["edges"], lp["x"].tolist()):
        x = float(x)
        if x <= 1e-12:
            continue
        used_edges += 1
        used_cvs.add(int(cv))
        sidecar[(cv, s)] = sidecar.get((cv, s), 0.0) - x
        sidecar[(cv, t)] = sidecar.get((cv, t), 0.0) + x

    cv_delta: dict[int, float] = {}
    cell_delta = np.zeros(NCELL, dtype=float)
    for (cv, cell), dm in sidecar.items():
        cv_delta[cv] = cv_delta.get(cv, 0.0) + float(dm)
        cell_delta[cell] += float(dm)

    max_cv = max((abs(v) for v in cv_delta.values()), default=0.0)
    global_delta = float(cell_delta.sum())

    m = np.asarray(accepted_mass, dtype=float).reshape(-1) + cell_delta
    c = np.asarray(cap, dtype=float).reshape(-1)
    lower = max(0.0, -float(np.min(m)))
    upper = max(0.0, float(np.max(m - c)))

    return {
        "max_per_CV_delta_kg": max_cv,
        "global_sidecar_delta_kg": global_delta,
        "max_lower_violation_kg": lower,
        "max_upper_violation_kg": upper,
        "used_edge_count": used_edges,
        "used_CV_count": len(used_cvs),
        "sidecar": sidecar,
    }


def selftest() -> None:
    assert len(face_neighbors(flat(1,1,1))) == 6
    assert len(same_layer_r2(flat(1,10,10))) == 12

    ledger = {(10, 0): 2.0}
    slack = np.zeros(NCELL)
    slack[1] = 2.0
    res = solve_cv_lp([0], {0: 1.0}, {0: [1]}, slack, ledger)
    assert res["success"]
    assert abs(float(res["x"][0]) - 1.0) < 1e-10

    accepted = np.zeros(NCELL)
    accepted[0] = 1.0
    cap = np.ones(NCELL) * 10.0
    aud = sidecar_audit(res, accepted, cap)
    assert aud["max_per_CV_delta_kg"] < 1e-12
    assert abs(aud["global_sidecar_delta_kg"]) < 1e-12

    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1-R4 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R21-R4-R1-R4 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21R4R1R4_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R21R4R1R3", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, blob, label in [
            (R4R1R3_RUNNER, R4R1R3_BLOB, "R4R1R3"),
            (F1R2_RUNNER, F1R2_BLOB, "F1R2"),
            (A2E_RUNNER, A2E_BLOB, "A2E"),
            (R2, R2_BLOB, "R2"),
            (SG2, SG2_BLOB, "SG2"),
            (SG3, SG3_BLOB, "SG3"),
            (R3PHYS, R3PHYS_BLOB, "R3R2R1"),
            (PERM, PERM_BLOB, "PERM"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R4R1R3_authority"
        r413 = drive / R4R1R3
        manifest(r413, R4R1R3_MANIFEST)
        s413 = js(r413 / R4R1R3_SUMMARY)
        d413 = js(r413 / R4R1R3_DECISION)

        gate(
            "R4R1R3_status_exact",
            s413.get("status") ==
            "AV4PIVOTP2R6R21R4R1R3_HISTORICAL_PARENTSTATE_PROVENANCE_MATCH_DIAGNOSTIC_PASS_NO_STATE_MUTATION",
        )
        gate("R4R1R4_authorized", d413.get("P2_R6_R21_R4_R1_R4_authorized") is True)
        gate("R4R1R3_partial_exact_parent_match", s413.get("parent_provenance_recovery_state") == "PARTIAL_EXACT_PARENT_MATCH")
        gate("R4R1R3_exact_grid_match_one", int(s413["exact_residual_grid_match_count"]) == 1)
        gate("R4R1R3_no_exact_CV_match_under_standard_keys", int(s413["exact_residual_CV_match_count"]) == 0)
        gate("R4R1R3_9_sources_positive_repaired_availability", s413.get("all_9_pressure_source_cells_have_positive_repaired_CV_availability") is True)

        stage = "F1R2_split_state_authority"
        f1 = drive / F1R2
        manifest(f1, F1R2_MANIFEST)
        sf1 = js(f1 / F1R2_SUMMARY)
        pf1 = js(f1 / F1R2_PROJECTION)
        rf1 = js(f1 / F1R2_RESIDUAL)
        df1 = js(f1 / F1R2_DECISION)

        gate("F1R2_status_exact", sf1.get("status") == F1R2_STATUS, sf1.get("status"))
        gate("F1R2_split_restart_state_frozen", df1.get("split_restart_state_contract_frozen") is True)
        gate("F1R2_normalized_transpose_frozen", df1.get("normalized_transpose_projection_frozen") is True)
        gate("F1R2_residual_grid_sidecar_frozen", df1.get("residual_grid_sidecar_frozen") is True)
        gate("F1R2_reverse_halo_pullback_false", sf1.get("reverse_halo_pullback") is False)
        gate(
            "F1R2_projection_exact_residual_sidecar",
            pf1.get("name") == "Exact-support normalized-transpose mass projection with residual grid sidecar",
        )
        gate(
            "F1R2_H1_reverse_pullback_forbidden",
            "not" in str(pf1["residual_grid_sidecar"]["H1_policy"]).lower()
            and "reverse" in str(pf1["residual_grid_sidecar"]["H1_policy"]).lower(),
            pf1["residual_grid_sidecar"]["H1_policy"],
        )
        gate(
            "F1R2_global_split_mass_ledger_frozen",
            "sum(M_cv) + sum(R_grid) = sum(M_parent_grid)" ==
            pf1["residual_grid_sidecar"]["global_ledger"],
        )
        state_blocks = {x["name"]: x for x in rf1["state_blocks"]}
        gate("F1R2_transport_CV_state_block_present", "transport_CV_component_mass" in state_blocks)
        gate("F1R2_grid_residual_state_block_present", "grid_residual_component_mass" in state_blocks)

        stage = "accepted_state_and_explicit_ledger_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R20_accepted_state_true", a20.get("accepted_Day375_state") is True)
        gate("R20_state_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        state_path = r19 / R19_STATE
        gate("R19_accepted_state_SHA_exact", sha(state_path) == accepted_sha, sha(state_path))

        with np.load(state_path, allow_pickle=False) as z:
            accepted_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(GRID)
            inherited_pressure = np.asarray(z["parent_pressure_psi"], dtype=float)
            r19_pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            r19_pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            r19_pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            r19_halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            r19_halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            r19_halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)

        d370_path = drive / D370 / D370_STATE
        gate("Day370_state_present", d370_path.is_file(), str(d370_path))
        with np.load(d370_path, allow_pickle=False) as z:
            d370_pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            d370_pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            d370_pair_mass = np.asarray(z["repaired_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            d370_halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            d370_halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            d370_halo_mass = np.asarray(z["repaired_halo_contribution_kg"], dtype=float).reshape(-1)

        ledger: dict[tuple[int, int], float] = {}
        add_ledger(ledger, d370_pair_cv, d370_pair_cell, d370_pair_mass)
        add_ledger(ledger, d370_halo_cv, d370_halo_cell, d370_halo_mass)
        add_ledger(ledger, r19_pair_cv, r19_pair_cell, r19_pair_mass)
        add_ledger(ledger, r19_halo_cv, r19_halo_cell, r19_halo_mass)

        explicit_grid = np.zeros(NCELL, dtype=float)
        for (_cv, cell), amount in ledger.items():
            explicit_grid[cell] += float(amount)

        residual_cartesian = accepted_mass.reshape(-1) - explicit_grid
        explicit_positive_total = float(sum(max(v, 0.0) for v in ledger.values()))
        explicit_net_total = float(sum(ledger.values()))
        residual_cartesian_total = float(residual_cartesian.sum())

        stage = "R3_iteration1_pressure_authority"
        r3dir = drive / R3DIR
        manifest(r3dir, R3_MANIFEST)
        s3 = js(r3dir / R3_SUMMARY)
        rows3 = csvr(r3dir / R3_CELL_AUDIT)
        gate("R3_PASS", s3.get("status") == "AV4PIVOTP2R6R21R3_FIRST_ITERATION_PRESSURE_INDUCED_CAPACITY_LOSS_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION")
        gate("R3_source_count_9", len(rows3) == 9, len(rows3))

        a2e = mod(root / A2E_RUNNER, "r6r21r4r1r4_a2e")
        r2 = mod(root / R2, "r6r21r4r1r4_r2")
        sg2 = mod(root / SG2, "r6r21r4r1r4_sg2")
        sg3 = mod(root / SG3, "r6r21r4r1r4_sg3")
        r3phys = mod(root / R3PHYS, "r6r21r4r1r4_r3phys")

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
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            p0 = np.asarray(z["refreshed_pressure_psi"], dtype=float)

        gate("accepted_inherited_pressure_matches_A2E", max_abs(inherited_pressure - p0) <= 1e-12)

        parent_sg = a2e.invert_local_mass(r2, accepted_mass, p0, p_ref, pore_volume)
        parent_sat = float(a2e.BACKGROUND) + np.asarray(parent_sg, dtype=float)

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=float).reshape(GRID, order="C")
        mobility = a2e.spatial_mobility(parent_sat, nw, no, krw_max, kro_max)
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        tx, ty, tz, _face = r3phys.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
        )
        A, b, _wi = r3phys.assemble_updated_pressure_system(
            sg3, permeability, tx, ty, tz, mobility["lambda_total"]
        )
        _ppa, p1, linear_residual = r3phys.solve_updated_pressure(sg3, A, b)
        gate("iteration1_pressure_residual_healthy", linear_residual < float(a2e.PRESSURE_LINEAR_REL_RESIDUAL_MAX), linear_residual)

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=float)
        cap1 = np.asarray(a2e.local_mass(r2, full_sat, p1, p_ref, pore_volume), dtype=float)
        excess_grid = accepted_mass - cap1
        tol = max(1e-8, 1e-12 * max(float(np.max(cap1)), 1.0))
        sources = sorted(np.flatnonzero(excess_grid.reshape(-1) > tol).astype(int).tolist())
        source_r3 = sorted(int(r["flat_cell"]) for r in rows3)
        gate("source_cells_match_R3", sources == source_r3, {"recomputed": sources, "R3": source_r3})

        ef = excess_grid.reshape(-1)
        slack = np.maximum(cap1.reshape(-1) - accepted_mass.reshape(-1), 0.0)
        excess = {s: float(ef[s]) for s in sources}
        total_excess = float(sum(excess.values()))

        positive_availability = {
            s: float(sum(
                amount for (cv, cell), amount in ledger.items()
                if cell == s and amount > 1e-13
            ))
            for s in sources
        }

        gate(
            "all_9_sources_have_explicit_positive_CV_attributed_availability",
            all(positive_availability[s] + 1e-12 >= excess[s] for s in sources),
            {s: {"available": positive_availability[s], "required": excess[s]} for s in sources},
        )

        stage = "prospective_split_state_feasibility"
        tiers = [
            ("T1_FACE", face_neighbors),
            ("T2_SAME_LAYER_MANHATTAN_R2", same_layer_r2),
            ("T3_3D_FACE_GRAPH_DISTANCE_R2", graph_r2),
        ]

        tier_results: dict[str, dict[str, Any]] = {}
        selected_tier = None
        selected_lp = None
        selected_audit = None
        edge_rows = []

        for tier_name, fn in tiers:
            targets = {s: candidate_targets(s, slack, fn) for s in sources}
            lp = solve_cv_lp(sources, excess, targets, slack, ledger)
            aud = sidecar_audit(lp, accepted_mass, cap1)

            result = {
                "exact_feasible": bool(lp["success"]),
                "solver_status": int(lp["status"]),
                "solver_message": str(lp["message"]),
                "edge_count": int(lp.get("edge_count", 0)),
                "target_count": int(lp.get("target_count", 0)),
                "cv_source_count": int(lp.get("cv_source_count", 0)),
                "max_per_CV_delta_kg": aud["max_per_CV_delta_kg"],
                "global_sidecar_delta_kg": aud["global_sidecar_delta_kg"],
                "max_lower_violation_kg": aud["max_lower_violation_kg"],
                "max_upper_violation_kg": aud["max_upper_violation_kg"],
                "used_edge_count": aud["used_edge_count"],
                "used_CV_count": aud["used_CV_count"],
            }
            tier_results[tier_name] = result

            if lp["success"] and selected_tier is None:
                selected_tier = tier_name
                selected_lp = lp
                selected_audit = aud

            if lp["success"]:
                for (cv, s, t), x in zip(lp["edges"], lp["x"].tolist()):
                    if float(x) <= 1e-12:
                        continue
                    edge_rows.append({
                        "tier": tier_name,
                        "cv_id": int(cv),
                        "source_cell": int(s),
                        "target_cell": int(t),
                        "source_k": ijk(int(s))[0],
                        "source_j": ijk(int(s))[1],
                        "source_i": ijk(int(s))[2],
                        "target_k": ijk(int(t))[0],
                        "target_j": ijk(int(t))[1],
                        "target_i": ijk(int(t))[2],
                        "prospective_move_kg": float(x),
                        "source_required_excess_kg": excess[int(s)],
                        "target_initial_slack_kg": float(slack[int(t)]),
                        "selected_minimal_tier": bool(tier_name == selected_tier),
                    })

        gate("at_least_one_frozen_domain_exact_feasible", selected_tier is not None, tier_results)
        assert selected_audit is not None
        gate("selected_sidecar_per_CV_conservative", float(selected_audit["max_per_CV_delta_kg"]) <= 1e-10, selected_audit["max_per_CV_delta_kg"])
        gate("selected_sidecar_global_mass_conservative", abs(float(selected_audit["global_sidecar_delta_kg"])) <= 1e-10, selected_audit["global_sidecar_delta_kg"])
        gate("selected_sidecar_closes_iteration1_lower_capacity", float(selected_audit["max_lower_violation_kg"]) <= 1e-8, selected_audit["max_lower_violation_kg"])
        gate("selected_sidecar_closes_iteration1_upper_capacity", float(selected_audit["max_upper_violation_kg"]) <= 1e-8, selected_audit["max_upper_violation_kg"])

        stage = "split_state_semantics_freeze"
        semantics = {
            "milestone": M,
            "status": PASS,
            "F1R2_split_state_authority": {
                "transport_CV_component_mass_authoritative_for_CV_attributed_inventory": True,
                "grid_residual_component_mass_preserved_as_independent_Cartesian_sidecar": True,
                "reverse_H1_to_S0_pullback_forbidden": True,
                "global_split_mass_ledger": "sum(M_cv) + sum(R_grid) = sum(M_parent_grid)",
            },
            "accepted_Day375_state": {
                "state_sha256": accepted_sha,
                "immutable_transport_acceptance": True,
                "physical_time_days": DAY,
            },
            "current_explicit_CV_cell_ledger": {
                "layers": [
                    "Day370 repaired existing-pair contributions",
                    "Day370 repaired halo contributions",
                    "R19 Day375 existing-pair contributions",
                    "R19 Day375 halo/H2 contributions",
                ],
                "coalescing": "sum by (cv_id, flat_cell)",
                "positive_source_withdrawal_authority": "positive net explicitly CV-attributed mass only",
                "negative_or_unattributed_mass_withdrawal_forbidden": True,
            },
            "residual_Cartesian_state": {
                "definition_for_pressure_reconciliation": (
                    "accepted_Day375_grid_mass minus current explicit coalesced CV-cell ledger"
                ),
                "immutable_during_pressure_reconciliation": True,
                "CV_identity_imputed": False,
                "reverse_projected_to_streamlines": False,
            },
            "pressure_reconciliation_sidecar": {
                "representation": "signed per-CV per-cell same-time pressure-compatibility sidecar",
                "source_rule": "withdraw only from positive explicit CV-attributed source mass",
                "source_total_rule": "withdraw exactly the current source-cell pressure-capacity excess",
                "destination_rule": "deposit identical CV mass into cells with positive current-pressure capacity slack",
                "per_CV_sum_rule": "exactly zero",
                "global_sum_rule": "exactly zero",
                "physical_transport_claim": False,
                "streamline_geometry_change": False,
                "base_Day370_or_R19_arrays_rewritten": False,
            },
            "domain_tiers": {
                "T1_FACE": "one-hop 3D Cartesian face neighbors",
                "T2_SAME_LAYER_MANHATTAN_R2": "same-layer Manhattan distance <= 2",
                "T3_3D_FACE_GRAPH_DISTANCE_R2": "3D face-graph distance <= 2",
            },
            "selected_minimal_exact_feasible_tier": selected_tier,
            "execution_fixed_domain": True,
            "recursive_support_growth": False,
            "automatic_domain_expansion_after_execution_observation": False,
            "coupled_fixed_point_execution_rule": (
                "At each same-time pressure iterate, apply only additional CV-conservative sidecar "
                "mass inside the frozen selected domain; if a required source/target lies outside "
                "the domain or the LP is infeasible, emit scientific fail with no automatic growth."
            ),
            "R4R1R4_is_design_feasibility_freeze_only": True,
            "state_mutation_executed": False,
        }

        if selected_tier == "T1_FACE":
            classification = "R6R21R4R1R4_SPLIT_STATE_SEMANTICS_FROZEN_T1_FACE_EXACT_FEASIBLE_EXECUTION_NEXT"
            next_name = "Controlled Split-State Day375 Pressure-Capacity Reconciliation Execution — T1 Face Domain"
        elif selected_tier == "T2_SAME_LAYER_MANHATTAN_R2":
            classification = "R6R21R4R1R4_SPLIT_STATE_SEMANTICS_FROZEN_T2_SAME_LAYER_R2_EXACT_FEASIBLE_EXECUTION_NEXT"
            next_name = "Controlled Split-State Day375 Pressure-Capacity Reconciliation Execution — T2 Same-Layer Radius-2"
        else:
            classification = "R6R21R4R1R4_SPLIT_STATE_SEMANTICS_FROZEN_T3_3D_GRAPH_R2_EXACT_FEASIBLE_EXECUTION_NEXT"
            next_name = "Controlled Split-State Day375 Pressure-Capacity Reconciliation Execution — T3 3D Graph Radius-2"

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "accepted_Day375_state_sha256": accepted_sha,
            "F1R2_split_restart_state_contract_bound": True,
            "F1R2_residual_grid_sidecar_bound": True,
            "reverse_H1_to_S0_pullback_forbidden": True,
            "explicit_CV_cell_ledger_entry_count": len(ledger),
            "explicit_CV_cell_ledger_positive_mass_kg": explicit_positive_total,
            "explicit_CV_cell_ledger_net_mass_kg": explicit_net_total,
            "residual_Cartesian_sidecar_net_mass_kg": residual_cartesian_total,
            "residual_Cartesian_sidecar_min_cell_kg": float(np.min(residual_cartesian)),
            "residual_Cartesian_sidecar_max_cell_kg": float(np.max(residual_cartesian)),
            "iteration1_pressure_linear_relative_residual": float(linear_residual),
            "source_cell_count": len(sources),
            "total_pressure_capacity_excess_kg": total_excess,
            "minimum_source_explicit_positive_CV_margin_kg": float(min(
                positive_availability[s] - excess[s] for s in sources
            )),
            "T1_FACE": tier_results["T1_FACE"],
            "T2_SAME_LAYER_MANHATTAN_R2": tier_results["T2_SAME_LAYER_MANHATTAN_R2"],
            "T3_3D_FACE_GRAPH_DISTANCE_R2": tier_results["T3_3D_FACE_GRAPH_DISTANCE_R2"],
            "selected_minimal_exact_feasible_tier": selected_tier,
            "selected_used_edge_count": int(selected_audit["used_edge_count"]),
            "selected_used_CV_count": int(selected_audit["used_CV_count"]),
            "selected_max_per_CV_delta_kg": float(selected_audit["max_per_CV_delta_kg"]),
            "selected_global_sidecar_delta_kg": float(selected_audit["global_sidecar_delta_kg"]),
            "selected_iteration1_max_lower_violation_kg": float(selected_audit["max_lower_violation_kg"]),
            "selected_iteration1_max_upper_violation_kg": float(selected_audit["max_upper_violation_kg"]),
            "state_mutation_executed": False,
            "pressure_refresh_accepted": False,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R21_R4_R1_R5_authorized": True,
            "P2_R6_R21_R4_R1_R5_name": next_name,
            "P2_R6_R21_R4_R1_R5_controlled_execution_authorized": True,
            "P2_R6_R21_R4_R1_R5_must_bind_R4R1R4_semantics_contract": True,
            "P2_R6_R21_R4_R1_R5_frozen_domain_tier": selected_tier,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "residual_Cartesian_sidecar_must_remain_immutable": True,
            "reverse_H1_to_S0_pullback_authorized": False,
            "automatic_domain_growth_authorized": False,
            "pressure_reconciliation_sidecar_execution_authorized": True,
            "pressure_refresh_acceptance_authorized_only_if_coupled_fixed_point_passes": True,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Split_State_Reconciliation_Semantics_Contract.json").write_bytes(jb(semantics))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Prospective_Sidecar_Edge_Audit.csv").write_bytes(csvb(edge_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Accepted Day375 state SHA256                :", accepted_sha)
        print("F1-R2 split-state contract bound            : True")
        print("Reverse H1->S0 pullback                     : False")
        print("Explicit CV-cell ledger entries             :", len(ledger))
        print("Residual Cartesian sidecar net kg           :", residual_cartesian_total)
        print("Iteration-1 pressure residual               :", linear_residual)
        print("Source cells / excess kg                    :", len(sources), "/", total_excess)
        print("T1 face exact feasible                      :", tier_results["T1_FACE"]["exact_feasible"])
        print("T2 same-layer R2 exact feasible             :", tier_results["T2_SAME_LAYER_MANHATTAN_R2"]["exact_feasible"])
        print("T3 3D graph R2 exact feasible               :", tier_results["T3_3D_FACE_GRAPH_DISTANCE_R2"]["exact_feasible"])
        print("Selected minimal exact-feasible tier        :", selected_tier)
        print("Selected max per-CV delta kg                :", selected_audit["max_per_CV_delta_kg"])
        print("Selected max upper violation kg             :", selected_audit["max_upper_violation_kg"])
        print("State mutation / pressure acceptance        : False / False")
        print("R4-R1-R5 controlled execution authorized    : True")
        print("Darcy/Pollock/TOF / time / P3               : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R4_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "accepted_Day375_state_preserved": True,
                "state_mutation_executed": False,
                "automatic_rerun_authorized": False,
                "pressure_refresh_accepted": False,
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
