#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import itertools
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, lil_matrix

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1"
NAME = "Day375 Face-Domain Hall Bottleneck Localization and Minimal Non-Recursive Extension Diagnostic"

PASS = "AV4PIVOTP2R6R21R4R1_FACE_DOMAIN_HALL_BOTTLENECK_LOCALIZATION_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R21R4R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "e3df4a54835f18337f7590348d2d586ca1710cd8"

R4_BLOCK_STATUS = "AV4PIVOTP2R6R21R4_TECHNICAL_OR_AUTHORITY_BLOCK"
R4_BLOCK_STAGE = "prospective_T1_onehop_face_extension"
R4_BLOCK_EXCEPTION = "GateError('T1_exact_feasible')"

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

R4_BLOCK = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_BLOCKED/"
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Blocked_Report.json"
)

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
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_"
    "FaceDomain_Hall_Bottleneck_Localization"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_BLOCKED"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = 37500
TOL = 1.0e-8


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
    return out


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
    return out


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
    seen.remove(c)
    return sorted(seen)


def coalesced_ledger(
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    pair_mass: np.ndarray,
    halo_cv: np.ndarray,
    halo_cell: np.ndarray,
    halo_mass: np.ndarray,
) -> dict[tuple[int, int], float]:
    d: dict[tuple[int, int], float] = {}
    for cv, c, m in zip(pair_cv.tolist(), pair_cell.tolist(), pair_mass.tolist()):
        key = (int(cv), int(c))
        d[key] = d.get(key, 0.0) + float(m)
    for cv, c, m in zip(halo_cv.tolist(), halo_cell.tolist(), halo_mass.tolist()):
        key = (int(cv), int(c))
        d[key] = d.get(key, 0.0) + float(m)
    return d


def candidate_targets(
    source: int,
    slack: np.ndarray,
    domain_fn: Callable[[int], list[int]],
) -> list[int]:
    sf = np.asarray(slack, dtype=float).reshape(-1)
    return sorted(t for t in set(domain_fn(source)) if sf[t] > TOL)


def hall_audit(
    sources: list[int],
    excess: dict[int, float],
    targets_by_source: dict[int, list[int]],
    slack: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sf = np.asarray(slack, dtype=float).reshape(-1)
    rows: list[dict[str, Any]] = []
    worst = None
    deficient_count = 0

    n = len(sources)
    for mask in range(1, 1 << n):
        subset = [sources[i] for i in range(n) if mask & (1 << i)]
        union_targets = sorted(set().union(*(set(targets_by_source[s]) for s in subset)))
        demand = float(sum(excess[s] for s in subset))
        capacity = float(sum(sf[t] for t in union_targets))
        deficit = demand - capacity
        if deficit > TOL:
            deficient_count += 1
        row = {
            "subset_mask": mask,
            "subset_size": len(subset),
            "source_cells": ";".join(map(str, subset)),
            "source_demand_kg": demand,
            "union_target_count": len(union_targets),
            "union_targets": ";".join(map(str, union_targets)),
            "union_target_capacity_kg": capacity,
            "hall_deficit_kg": deficit,
            "hall_deficient": bool(deficit > TOL),
        }
        rows.append(row)
        if worst is None or deficit > float(worst["hall_deficit_kg"]):
            worst = row

    assert worst is not None
    summary = {
        "subset_count": len(rows),
        "deficient_subset_count": deficient_count,
        "maximum_hall_deficit_kg": float(worst["hall_deficit_kg"]),
        "worst_subset_size": int(worst["subset_size"]),
        "worst_source_cells": str(worst["source_cells"]),
        "worst_union_target_count": int(worst["union_target_count"]),
        "worst_union_target_capacity_kg": float(worst["union_target_capacity_kg"]),
        "worst_source_demand_kg": float(worst["source_demand_kg"]),
    }
    return rows, summary


def aggregate_flow_lp(
    sources: list[int],
    excess: dict[int, float],
    targets_by_source: dict[int, list[int]],
    slack: np.ndarray,
) -> dict[str, Any]:
    edges = [(s, t) for s in sources for t in targets_by_source[s]]
    if not edges:
        return {"success": False, "max_routable_kg": 0.0, "unmet_kg": float(sum(excess.values()))}

    targets = sorted(set(t for _, t in edges))
    src_ix = {s: r for r, s in enumerate(sources)}
    tgt_ix = {t: r for r, t in enumerate(targets)}
    n_x = len(edges)
    n_u = len(sources)
    n = n_x + n_u

    # Variables x_edges >=0 and unmet_u >=0.
    c = np.zeros(n)
    c[n_x:] = 1.0

    Aeq = lil_matrix((len(sources), n), dtype=float)
    beq = np.asarray([excess[s] for s in sources], dtype=float)
    for j, (s, _t) in enumerate(edges):
        Aeq[src_ix[s], j] = 1.0
    for r in range(len(sources)):
        Aeq[r, n_x + r] = 1.0

    Aub = lil_matrix((len(targets), n), dtype=float)
    bub = np.asarray([float(np.asarray(slack).reshape(-1)[t]) for t in targets], dtype=float)
    for j, (_s, t) in enumerate(edges):
        Aub[tgt_ix[t], j] = 1.0

    res = linprog(
        c,
        A_ub=csr_matrix(Aub),
        b_ub=bub,
        A_eq=csr_matrix(Aeq),
        b_eq=beq,
        bounds=[(0.0, None)] * n,
        method="highs",
    )
    if not res.success:
        return {
            "success": False,
            "status": int(res.status),
            "message": str(res.message),
            "max_routable_kg": 0.0,
            "unmet_kg": float(sum(excess.values())),
        }

    x = np.asarray(res.x, dtype=float)
    unmet = x[n_x:]
    total_demand = float(sum(excess.values()))
    unmet_total = float(np.sum(unmet))
    routed = total_demand - unmet_total

    per_source = []
    for r, s in enumerate(sources):
        per_source.append({
            "source_cell": s,
            "demand_kg": float(excess[s]),
            "unmet_kg": float(unmet[r]),
            "routed_kg": float(excess[s] - unmet[r]),
            "target_count": len(targets_by_source[s]),
        })

    target_load = {t: 0.0 for t in targets}
    for j, (_s, t) in enumerate(edges):
        target_load[t] += float(x[j])
    sf = np.asarray(slack, dtype=float).reshape(-1)
    saturated = [
        t for t in targets
        if sf[t] > TOL and abs(target_load[t] - sf[t]) <= 1e-8
    ]

    return {
        "success": True,
        "status": int(res.status),
        "message": str(res.message),
        "max_routable_kg": routed,
        "unmet_kg": unmet_total,
        "total_demand_kg": total_demand,
        "source_rows": per_source,
        "saturated_target_count": len(saturated),
        "saturated_targets": saturated,
    }


def full_cv_lp(
    sources: list[int],
    excess: dict[int, float],
    targets_by_source: dict[int, list[int]],
    slack: np.ndarray,
    ledger: dict[tuple[int, int], float],
) -> dict[str, Any]:
    edges = []
    for s in sources:
        positive_cvs = sorted(
            (cv, m) for (cv, c), m in ledger.items()
            if c == s and m > 1.0e-13
        )
        for cv, avail in positive_cvs:
            for t in targets_by_source[s]:
                edges.append((int(cv), int(s), int(t), float(avail)))

    if not edges:
        return {"success": False, "status": -999, "message": "no_edges"}

    targets = sorted(set(t for _cv, _s, t, _a in edges))
    cvsrc = sorted(set((cv, s) for cv, s, _t, _a in edges))
    src_ix = {s: r for r, s in enumerate(sources)}
    tgt_ix = {t: r for r, t in enumerate(targets)}
    cvsrc_ix = {x: r for r, x in enumerate(cvsrc)}

    n = len(edges)
    Aeq = lil_matrix((len(sources), n), dtype=float)
    beq = np.asarray([excess[s] for s in sources], dtype=float)
    for j, (_cv, s, _t, _a) in enumerate(edges):
        Aeq[src_ix[s], j] = 1.0

    Aub = lil_matrix((len(targets) + len(cvsrc), n), dtype=float)
    sf = np.asarray(slack, dtype=float).reshape(-1)
    bub = np.zeros(len(targets) + len(cvsrc), dtype=float)
    for t, r in tgt_ix.items():
        bub[r] = sf[t]

    availability: dict[tuple[int, int], float] = {}
    for j, (cv, s, t, avail) in enumerate(edges):
        Aub[tgt_ix[t], j] = 1.0
        Aub[len(targets) + cvsrc_ix[(cv, s)], j] = 1.0
        availability[(cv, s)] = avail
    for key, r in cvsrc_ix.items():
        bub[len(targets) + r] = availability[key]

    res = linprog(
        np.zeros(n),
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
        "edge_count": n,
        "target_count": len(targets),
        "cv_source_count": len(cvsrc),
    }


def selftest() -> None:
    assert len(face_neighbors(flat(1, 1, 1))) == 6
    assert len(same_layer_r2(flat(1, 10, 10))) == 12
    assert len(graph_r2(flat(2, 10, 10))) > 12

    sources = [0, 2]
    excess = {0: 1.0, 2: 1.0}
    slack = np.zeros(NCELL)
    slack[1] = 1.5
    targets = {0: [1], 2: [1]}
    rows, s = hall_audit(sources, excess, targets, slack)
    assert len(rows) == 3
    assert abs(s["maximum_hall_deficit_kg"] - 0.5) < 1e-12

    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R21-R4-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21R4R1_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R21R4", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, blob, label in [
            (A2E_RUNNER, A2E_BLOB, "A2E"),
            (R2, R2_BLOB, "R2"),
            (SG2, SG2_BLOB, "SG2"),
            (SG3, SG3_BLOB, "SG3"),
            (R3PHYS, R3PHYS_BLOB, "R3R2R1"),
            (PERM, PERM_BLOB, "PERM"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R6R21R4_BLOCK_authority"
        r4block = drive / R4_BLOCK
        gate("R6R21R4_BLOCK_present", r4block.is_file(), str(r4block))
        r4sha = sha(r4block)
        r4 = js(r4block)
        gate("R6R21R4_BLOCK_status_exact", r4.get("status") == R4_BLOCK_STATUS, r4.get("status"))
        gate("R6R21R4_BLOCK_stage_exact", r4.get("failed_stage") == R4_BLOCK_STAGE, r4.get("failed_stage"))
        gate("R6R21R4_BLOCK_exception_exact", r4.get("exception") == R4_BLOCK_EXCEPTION, r4.get("exception"))
        gate("R6R21R4_accepted_state_preserved", r4.get("accepted_Day375_state_preserved") is True)
        gate("R6R21R4_no_state_mutation", r4.get("state_mutation_executed") is False)

        stage = "R6R21R3_and_accepted_state_authority"
        r3dir = drive / R3DIR
        manifest(r3dir, R3_MANIFEST)
        s3 = js(r3dir / R3_SUMMARY)
        rows3 = csvr(r3dir / R3_CELL_AUDIT)
        gate("R6R21R3_PASS", s3.get("status") == "AV4PIVOTP2R6R21R3_FIRST_ITERATION_PRESSURE_INDUCED_CAPACITY_LOSS_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION")
        gate("R6R21R3_violating_cell_count_9", int(s3["violating_cell_count"]) == 9)
        gate("R6R21R3_cell_audit_9", len(rows3) == 9)

        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R6R20_accepted_state_true", a20.get("accepted_Day375_state") is True)
        gate("accepted_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        state_path = r19 / R19_STATE
        gate("accepted_state_file_SHA_exact", sha(state_path) == accepted_sha, sha(state_path))

        with np.load(state_path, allow_pickle=False) as z:
            accepted_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(GRID)
            inherited_pressure = np.asarray(z["parent_pressure_psi"], dtype=float)
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)

        accepted_mass = np.maximum(accepted_mass, 0.0)
        ledger = coalesced_ledger(pair_cv, pair_cell, pair_mass, halo_cv, halo_cell, halo_mass)

        stage = "first_iteration_reproduction"
        a2e = mod(root / A2E_RUNNER, "r6r21r4r1_a2e")
        r2 = mod(root / R2, "r6r21r4r1_r2")
        sg2 = mod(root / SG2, "r6r21r4r1_sg2")
        sg3 = mod(root / SG3, "r6r21r4r1_sg3")
        r3phys = mod(root / R3PHYS, "r6r21r4r1_r3phys")

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
        gate("inherited_pressure_matches_A2E", max_abs(inherited_pressure - p0) <= 1e-12)

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

        source_positive_available = {
            s: float(sum(m for (cv, c), m in ledger.items() if c == s and m > 1e-13))
            for s in sources
        }
        gate(
            "all_sources_have_positive_contribution_availability",
            all(source_positive_available[s] + 1e-12 >= excess[s] for s in sources),
            {s: (source_positive_available[s], excess[s]) for s in sources},
        )

        # Tier diagnostics.
        tier_defs = [
            ("T1_FACE", face_neighbors),
            ("T2_SAME_LAYER_MANHATTAN_R2", same_layer_r2),
            ("T3_3D_FACE_GRAPH_DISTANCE_R2", graph_r2),
        ]

        tier_summaries = {}
        hall_rows_all = []
        source_rows_all = []

        for tier_name, fn in tier_defs:
            stage = f"{tier_name}_Hall_and_flow_diagnostic"
            targets = {s: candidate_targets(s, slack, fn) for s in sources}
            hall_rows, hall_summary = hall_audit(sources, excess, targets, slack)
            for r in hall_rows:
                r["tier"] = tier_name
                hall_rows_all.append(r)

            agg = aggregate_flow_lp(sources, excess, targets, slack)
            full = full_cv_lp(sources, excess, targets, slack, ledger)

            if "source_rows" in agg:
                for r in agg["source_rows"]:
                    rr = dict(r)
                    rr["tier"] = tier_name
                    source_rows_all.append(rr)

            tier_summaries[tier_name] = {
                **hall_summary,
                "aggregate_flow_success": bool(agg.get("success", False)),
                "aggregate_max_routable_kg": float(agg.get("max_routable_kg", 0.0)),
                "aggregate_unmet_kg": float(agg.get("unmet_kg", total_excess)),
                "aggregate_saturated_target_count": int(agg.get("saturated_target_count", 0)),
                "aggregate_saturated_targets": agg.get("saturated_targets", []),
                "full_CV_LP_success": bool(full.get("success", False)),
                "full_CV_LP_status": int(full.get("status", -999)),
                "full_CV_LP_message": str(full.get("message", "")),
                "full_CV_edge_count": int(full.get("edge_count", 0)),
                "target_union_count": len(set().union(*(set(v) for v in targets.values()))),
            }

        stage = "bottleneck_classification"
        t1 = tier_summaries["T1_FACE"]
        t2 = tier_summaries["T2_SAME_LAYER_MANHATTAN_R2"]
        t3 = tier_summaries["T3_3D_FACE_GRAPH_DISTANCE_R2"]

        gate("T1_face_domain_reproduces_infeasibility", not t1["full_CV_LP_success"], t1)
        # At least one prospective tier must resolve or we preserve the diagnostic for broader design.
        first_feasible = None
        for name in ("T2_SAME_LAYER_MANHATTAN_R2", "T3_3D_FACE_GRAPH_DISTANCE_R2"):
            if tier_summaries[name]["full_CV_LP_success"]:
                first_feasible = name
                break

        if first_feasible == "T2_SAME_LAYER_MANHATTAN_R2":
            classification = "R6R21R4R1_FACE_HALL_BOTTLENECK_LOCALIZED_SAME_LAYER_R2_EXACT_FEASIBLE_DESIGN_FREEZE_NEXT"
            next_name = "Minimal Same-Layer Radius-2 Pressure-Capacity Reconciliation Semantics Design Freeze"
        elif first_feasible == "T3_3D_FACE_GRAPH_DISTANCE_R2":
            classification = "R6R21R4R1_FACE_HALL_BOTTLENECK_LOCALIZED_3D_GRAPH_R2_EXACT_FEASIBLE_DESIGN_FREEZE_NEXT"
            next_name = "Minimal 3D Graph-Distance-2 Pressure-Capacity Reconciliation Semantics Design Freeze"
        else:
            classification = "R6R21R4R1_FACE_HALL_BOTTLENECK_LOCALIZED_RADIUS2_STILL_INFEASIBLE_BROADER_DOMAIN_DIAGNOSTIC_NEXT"
            next_name = "Broader Pressure-Capacity Reconciliation Support-Domain Diagnostic"

        diagnostic = {
            "R6R21R4_BLOCK_sha256": r4sha,
            "accepted_Day375_state_sha256": accepted_sha,
            "source_cell_count": len(sources),
            "total_excess_kg": total_excess,
            "source_positive_available_kg": source_positive_available,
            "T1_face_domain": t1,
            "T2_same_layer_manhattan_radius2": t2,
            "T3_3D_face_graph_distance2": t3,
            "first_exact_feasible_extension_tier": first_feasible,
            "failure_interpretation": (
                "FACE_NEIGHBOR_DOMAIN_HAS_COUPLED_SHARED_TARGET_CAPACITY_BOTTLENECK"
                if t1["maximum_hall_deficit_kg"] > TOL
                else "FACE_NEIGHBOR_FULL_CV_LP_INFEASIBLE_WITHOUT_AGGREGATE_HALL_DEFICIT"
            ),
            "R4_design_semantics_accepted": False,
            "accepted_transport_state_invalidated": False,
            "state_mutation_executed": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            **diagnostic,
            "pressure_refresh_accepted": False,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R21_R4_R2_authorized": True,
            "P2_R6_R21_R4_R2_name": next_name,
            "P2_R6_R21_R4_R2_design_or_diagnostic_only": True,
            "first_exact_feasible_extension_tier": first_feasible,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "pressure_reconciliation_execution_authorized_now": False,
            "support_growth_execution_authorized_now": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Diagnostic_Contract.json").write_bytes(jb(diagnostic))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Hall_Subset_Audit.csv").write_bytes(csvb(hall_rows_all))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Source_Flow_Audit.csv").write_bytes(csvb(source_rows_all))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("R4 BLOCK SHA256                         :", r4sha)
        print("Source cells                            :", len(sources))
        print("Total excess kg                         :", total_excess)
        print("T1 deficient subset count              :", t1["deficient_subset_count"])
        print("T1 maximum Hall deficit kg             :", t1["maximum_hall_deficit_kg"])
        print("T1 worst source cells                  :", t1["worst_source_cells"])
        print("T1 aggregate unmet kg                  :", t1["aggregate_unmet_kg"])
        print("T1 full CV LP feasible                 :", t1["full_CV_LP_success"])
        print("T2 same-layer R2 full CV LP feasible   :", t2["full_CV_LP_success"])
        print("T3 3D graph R2 full CV LP feasible     :", t3["full_CV_LP_success"])
        print("First exact feasible extension tier     :", first_feasible)
        print("State mutation / pressure acceptance    : False / False")
        print("R4-R2 design/diagnostic authorized      : True")
        print("Darcy/Pollock/TOF / time / P3           : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Blocked_Report.json"
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
