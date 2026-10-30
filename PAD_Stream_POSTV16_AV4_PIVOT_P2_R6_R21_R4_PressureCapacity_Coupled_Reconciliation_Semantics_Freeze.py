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
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, lil_matrix

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4"
NAME = "Day375 Pressure-Capacity Coupled Same-Time Conservative Reconciliation Semantics Design Freeze"

PASS = "AV4PIVOTP2R6R21R4_PRESSURE_CAPACITY_COUPLED_SAME_TIME_CONSERVATIVE_RECONCILIATION_SEMANTICS_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R21R4_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "2386752269d77f8936fb354ec390db17b5c7b3d0"

R3_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_FirstIteration_PressureInduced_CapacityLoss_Diagnostic_Freeze.py"
R3_BLOB = "380ffb9f0a8a2f6141e2fd2362d57fe5c9d1ec1c"

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

R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"

R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_Summary.json"
R3_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Decision_Contract.json"
R3_CELL_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Violating_Cell_Audit.csv"
R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Artifact_Manifest.csv"

A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_"
    "PressureCapacity_Coupled_SameTime_Conservative_Reconciliation_Semantics_Design_Freeze"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_BLOCKED"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = 37500
DAY = 375.0
TOL = 1.0e-8

R3_STATUS = "AV4PIVOTP2R6R21R3_FIRST_ITERATION_PRESSURE_INDUCED_CAPACITY_LOSS_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION"
R3_CLASS = "R6R21R3_PRESSURE_INDUCED_LOCAL_CAPACITY_LOSS_REPRODUCED_COUPLED_SAME_TIME_RECONCILIATION_SEMANTICS_DESIGN_NEXT"


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


def ijk(flat: int) -> tuple[int, int, int]:
    k = flat // 2500
    rem = flat % 2500
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


def coalesced_positive_support(
    pair_cv: np.ndarray,
    pair_cell: np.ndarray,
    pair_mass: np.ndarray,
    halo_cv: np.ndarray,
    halo_cell: np.ndarray,
    halo_mass: np.ndarray,
) -> tuple[dict[tuple[int, int], float], dict[int, set[int]]]:
    ledger: dict[tuple[int, int], float] = {}
    for cv, c, m in zip(pair_cv.tolist(), pair_cell.tolist(), pair_mass.tolist()):
        key = (int(cv), int(c))
        ledger[key] = ledger.get(key, 0.0) + float(m)
    for cv, c, m in zip(halo_cv.tolist(), halo_cell.tolist(), halo_mass.tolist()):
        key = (int(cv), int(c))
        ledger[key] = ledger.get(key, 0.0) + float(m)

    support: dict[int, set[int]] = {}
    for (cv, c), m in ledger.items():
        if m > 1.0e-13:
            support.setdefault(cv, set()).add(c)
    return ledger, support


def build_edges(
    source_cells: list[int],
    excess_by_source: dict[int, float],
    ledger: dict[tuple[int, int], float],
    support: dict[int, set[int]],
    slack: np.ndarray,
    allow_new_support: bool,
) -> list[dict[str, Any]]:
    edges = []
    sflat = np.asarray(slack, dtype=float).reshape(-1)
    for source in source_cells:
        positive_source = sorted(
            (cv, m)
            for (cv, c), m in ledger.items()
            if c == source and m > 1.0e-13
        )
        for cv, source_mass in positive_source:
            for target in face_neighbors(source):
                if sflat[target] <= TOL:
                    continue
                existing_positive = target in support.get(cv, set())
                if not existing_positive and not allow_new_support:
                    continue
                edges.append({
                    "cv": int(cv),
                    "source": int(source),
                    "target": int(target),
                    "source_positive_mass_kg": float(source_mass),
                    "target_slack_kg": float(sflat[target]),
                    "existing_positive_support": bool(existing_positive),
                    "new_support_edge": bool(not existing_positive),
                    "source_excess_kg": float(excess_by_source[source]),
                })
    return edges


def solve_transport_lp(
    edges: list[dict[str, Any]],
    source_cells: list[int],
    excess_by_source: dict[int, float],
    slack: np.ndarray,
    objective_new_support: bool,
) -> dict[str, Any]:
    if not edges:
        return {
            "success": False,
            "status": -999,
            "message": "no_edges",
            "x": np.zeros(0),
            "objective": None,
        }

    n = len(edges)
    src_index = {c: r for r, c in enumerate(source_cells)}
    targets = sorted(set(int(e["target"]) for e in edges))
    tgt_index = {c: r for r, c in enumerate(targets)}

    # Source equality: exactly shed the current local excess.
    Aeq = lil_matrix((len(source_cells), n), dtype=float)
    beq = np.asarray([excess_by_source[c] for c in source_cells], dtype=float)
    for j, e in enumerate(edges):
        Aeq[src_index[int(e["source"])], j] = 1.0

    # Target capacity and per-(CV,source) availability.
    cvsrc = sorted(set((int(e["cv"]), int(e["source"])) for e in edges))
    cvsrc_index = {key: r for r, key in enumerate(cvsrc)}
    n_t = len(targets)
    n_s = len(cvsrc)
    Aub = lil_matrix((n_t + n_s, n), dtype=float)
    bub = np.zeros(n_t + n_s, dtype=float)

    sflat = np.asarray(slack, dtype=float).reshape(-1)
    for t, r in tgt_index.items():
        bub[r] = float(sflat[t])

    source_avail: dict[tuple[int, int], float] = {}
    for j, e in enumerate(edges):
        t = int(e["target"])
        key = (int(e["cv"]), int(e["source"]))
        Aub[tgt_index[t], j] = 1.0
        Aub[n_t + cvsrc_index[key], j] = 1.0
        source_avail[key] = float(e["source_positive_mass_kg"])

    for key, r in cvsrc_index.items():
        bub[n_t + r] = source_avail[key]

    if objective_new_support:
        cvec = np.asarray([1.0 if e["new_support_edge"] else 0.0 for e in edges], dtype=float)
    else:
        cvec = np.zeros(n, dtype=float)

    result = linprog(
        cvec,
        A_ub=csr_matrix(Aub),
        b_ub=bub,
        A_eq=csr_matrix(Aeq),
        b_eq=beq,
        bounds=[(0.0, None)] * n,
        method="highs",
    )

    return {
        "success": bool(result.success),
        "status": int(result.status),
        "message": str(result.message),
        "objective": None if result.fun is None else float(result.fun),
        "x": np.asarray(result.x, dtype=float) if result.x is not None else np.zeros(n),
        "targets": targets,
        "cvsrc": cvsrc,
    }


def selftest() -> None:
    assert face_neighbors(flat(1, 1, 1))
    assert len(face_neighbors(flat(1, 1, 1))) == 6

    # Tiny feasibility sanity check: one source CV, one target.
    edges = [{
        "cv": 1, "source": 0, "target": 1,
        "source_positive_mass_kg": 2.0,
        "target_slack_kg": 3.0,
        "existing_positive_support": True,
        "new_support_edge": False,
        "source_excess_kg": 1.0,
    }]
    slack = np.zeros(NCELL)
    slack[1] = 3.0
    res = solve_transport_lp(edges, [0], {0: 1.0}, slack, False)
    assert res["success"]
    assert abs(float(res["x"][0]) - 1.0) < 1e-10

    print("POSTV16 AV4 PIVOT P2-R6-R21-R4 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R21-R4 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21R4_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R21R3", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, blob, label in [
            (R3_RUNNER, R3_BLOB, "R6R21R3"),
            (A2E_RUNNER, A2E_BLOB, "A2E"),
            (R2, R2_BLOB, "R2"),
            (SG2, SG2_BLOB, "SG2"),
            (SG3, SG3_BLOB, "SG3"),
            (R3PHYS, R3PHYS_BLOB, "R3R2R1"),
            (PERM, PERM_BLOB, "PERM"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R6R21R3_authority"
        r3dir = drive / R3DIR
        manifest(r3dir, R3_MANIFEST)
        s3 = js(r3dir / R3_SUMMARY)
        d3 = js(r3dir / R3_DECISION)
        rows3 = csvr(r3dir / R3_CELL_AUDIT)

        gate("R6R21R3_status_exact", s3.get("status") == R3_STATUS, s3.get("status"))
        gate("R6R21R3_classification_exact", s3.get("classification") == R3_CLASS)
        gate("R6R21R4_authorized", d3.get("P2_R6_R21_R4_authorized") is True)
        gate("R6R21R4_design_freeze_only", d3.get("P2_R6_R21_R4_design_freeze_only") is True)
        gate("R6R21R3_no_state_mutation", s3.get("state_mutation_executed") is False)
        gate("R6R21R3_violating_cell_count_9", int(s3["violating_cell_count"]) == 9)
        gate("R6R21R3_cell_audit_count_9", len(rows3) == 9, len(rows3))

        stage = "accepted_state_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("accepted_state_true", a20.get("accepted_Day375_state") is True)
        gate("accepted_state_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

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
        ledger, positive_support = coalesced_positive_support(
            pair_cv, pair_cell, pair_mass, halo_cv, halo_cell, halo_mass
        )

        stage = "iteration1_capacity_authority"
        a2e = mod(root / A2E_RUNNER, "r6r21r4_a2e")
        r2 = mod(root / R2, "r6r21r4_r2")
        sg2 = mod(root / SG2, "r6r21r4_sg2")
        sg3 = mod(root / SG3, "r6r21r4_sg3")
        r3phys = mod(root / R3PHYS, "r6r21r4_r3phys")

        control_path = drive / A6E / A6E_STATE
        gate("A6E_state_present", control_path.is_file())
        gate("A6E_state_SHA_exact", sha(control_path) == A6E_STATE_SHA)
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
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)

        gate("inherited_pressure_matches_A2E", max_abs(inherited_pressure - frozen_pressure) <= 1e-12)

        parent_sg = a2e.invert_local_mass(
            r2, accepted_mass, inherited_pressure, frozen_p_ref, pore_volume
        )
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
        cap1 = np.asarray(
            a2e.local_mass(r2, full_sat, p1, frozen_p_ref, pore_volume),
            dtype=float,
        )
        excess = accepted_mass - cap1
        tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cap1)), 1.0))
        viol = sorted(np.flatnonzero(excess.reshape(-1) > tol).astype(int).tolist())
        source_from_r3 = sorted(int(r["flat_cell"]) for r in rows3)
        gate("source_cells_match_R6R21R3", viol == source_from_r3, {"recomputed": viol, "R3": source_from_r3})

        flat_excess = excess.reshape(-1)
        flat_slack = np.maximum(cap1.reshape(-1) - accepted_mass.reshape(-1), 0.0)
        excess_by_source = {c: float(flat_excess[c]) for c in viol}

        stage = "prospective_T0_existing_positive_face_support"
        t0_edges = build_edges(
            viol, excess_by_source, ledger, positive_support, flat_slack, allow_new_support=False
        )
        t0 = solve_transport_lp(
            t0_edges, viol, excess_by_source, flat_slack, objective_new_support=False
        )

        stage = "prospective_T1_onehop_face_extension"
        t1_edges = build_edges(
            viol, excess_by_source, ledger, positive_support, flat_slack, allow_new_support=True
        )
        t1 = solve_transport_lp(
            t1_edges, viol, excess_by_source, flat_slack, objective_new_support=True
        )
        gate("T1_exact_feasible", t1["success"], {"status": t1["status"], "message": t1["message"]})

        x1 = t1["x"]
        total_move = float(np.sum(x1))
        total_excess = float(sum(excess_by_source.values()))
        gate("T1_total_move_equals_total_excess", abs(total_move - total_excess) <= 1e-8, {"move": total_move, "excess": total_excess})

        new_support_mass = float(sum(
            float(x) for x, e in zip(x1.tolist(), t1_edges) if e["new_support_edge"]
        ))
        used_edges = [
            (idx, e, float(x))
            for idx, (e, x) in enumerate(zip(t1_edges, x1.tolist()))
            if float(x) > 1.0e-12
        ]
        used_new_edges = [(e, x) for _, e, x in used_edges if e["new_support_edge"]]
        used_existing_edges = [(e, x) for _, e, x in used_edges if not e["new_support_edge"]]

        # Verify prospective sidecar conservation exactly by CV and cell.
        sidecar: dict[tuple[int, int], float] = {}
        for _, e, x in used_edges:
            cv = int(e["cv"])
            s = int(e["source"])
            t = int(e["target"])
            sidecar[(cv, s)] = sidecar.get((cv, s), 0.0) - x
            sidecar[(cv, t)] = sidecar.get((cv, t), 0.0) + x

        cv_delta: dict[int, float] = {}
        cell_delta = np.zeros(NCELL, dtype=float)
        for (cv, c), dm in sidecar.items():
            cv_delta[cv] = cv_delta.get(cv, 0.0) + dm
            cell_delta[c] += dm

        max_cv_delta = max(abs(v) for v in cv_delta.values()) if cv_delta else 0.0
        prospective_mass = accepted_mass.reshape(-1) + cell_delta
        lower_violation = float(max(0.0, -float(np.min(prospective_mass))))
        upper_violation = float(max(0.0, float(np.max(prospective_mass - cap1.reshape(-1)))))

        gate("prospective_sidecar_CV_conservative", max_cv_delta <= 1e-10, max_cv_delta)
        gate("prospective_iteration1_cell_lower_closed", lower_violation <= 1e-8, lower_violation)
        gate("prospective_iteration1_cell_upper_closed", upper_violation <= 1e-8, upper_violation)

        stage = "semantics_freeze"
        tier = "T0_EXISTING_POSITIVE_FACE_SUPPORT_ONLY" if t0["success"] else "T1_ONEHOP_FACE_EXTENSION"
        support_extension_required = not bool(t0["success"])

        semantics = {
            "milestone": M,
            "status": PASS,
            "accepted_transport_base": {
                "state_sha256": accepted_sha,
                "base_state_immutable": True,
                "state_day": DAY,
                "transport_acceptance_not_revoked": True,
            },
            "pressure_authority": {
                "reference_gas_pressure_pa": frozen_p_ref,
                "reference_pressure_source": "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz",
                "pressure_solver": "frozen_A2_E_fixed_point_pressure_physics",
                "physical_time_advance": False,
            },
            "pressure_compatible_representation": {
                "representation": "signed_per_CV_per_cell_pressure_reconciliation_sidecar",
                "base_R19_pair_halo_arrays_rewritten": False,
                "base_R19_cartesian_mass_rewritten": False,
                "effective_cell_mass": "accepted_R19_cell_mass + cumulative_pressure_reconciliation_sidecar_cell_sum",
                "per_CV_sidecar_sum_exact_zero": True,
                "global_sidecar_sum_exact_zero": True,
            },
            "source_semantics": {
                "source_cells": "cells exceeding EOS capacity at the current pressure iterate",
                "withdrawal_only_from_positive_current_CV_contribution": True,
                "withdrawal_per_CV_source_bounded_by_positive_current_contribution": True,
                "source_cell_total_withdrawal": "exact current capacity excess",
            },
            "destination_semantics": {
                "frozen_initial_domain": "R3 nine source cells plus their one-hop Cartesian face neighbors",
                "target_must_have_positive_pressure_iterate_capacity_slack": True,
                "T0": "same CV already has positive support in target face-neighbor cell",
                "T1": "same CV may create a new terminal one-hop face-neighbor sidecar edge",
                "recursive_support_growth": False,
                "second_ring_growth": False,
                "automatic_domain_expansion_during_execution": False,
            },
            "coupled_iteration_semantics": {
                "sequence": [
                    "apply cumulative sidecar to immutable accepted base mass",
                    "EOS-invert mass at current pressure to saturation",
                    "compute spatial Corey mobility",
                    "solve pressure with frozen A2-E pressure physics",
                    "compute pressure-dependent cell capacities",
                    "if capacity violation exists inside frozen domain, solve minimal conservative sidecar increment",
                    "EOS-invert corrected mass at same pressure",
                    "repeat pressure/mass compatibility fixed point",
                ],
                "if_new_overcapacity_outside_frozen_domain": "scientific_fail_no_automatic_growth",
                "if_sidecar_LP_infeasible": "scientific_fail_no_automatic_growth",
                "if_pressure_or_saturation_fixed_point_nonconvergent": "scientific_fail",
                "same_time_only": True,
            },
            "lexicographic_objective": [
                "exactly remove required source-cell capacity excess",
                "minimize new-support deposited mass",
                "minimize total active sidecar edges",
            ],
            "execution_tier_selected_from_R4_prospective_feasibility": tier,
            "support_extension_required_for_first_iteration": support_extension_required,
            "R4_is_design_freeze_only": True,
            "state_mutation_executed": False,
        }

        edge_rows = []
        for e, x in [(e, float(x)) for e, x in zip(t1_edges, x1.tolist())]:
            edge_rows.append({
                **e,
                "prospective_mass_kg": x,
                "prospective_used": bool(x > 1e-12),
            })

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": (
                "R6R21R4_PRESSURE_CAPACITY_COUPLED_SIDE_CAR_SEMANTICS_FROZEN_"
                + ("EXISTING_SUPPORT_EXECUTION_NEXT" if t0["success"] else "ONEHOP_EXTENSION_EXECUTION_NEXT")
            ),
            "accepted_Day375_state_sha256": accepted_sha,
            "R3_violating_cell_count": len(viol),
            "R3_total_capacity_excess_kg": total_excess,
            "T0_existing_positive_face_support_edge_count": len(t0_edges),
            "T0_exact_feasible": bool(t0["success"]),
            "T0_solver_status": int(t0["status"]),
            "T1_onehop_face_edge_count": len(t1_edges),
            "T1_exact_feasible": bool(t1["success"]),
            "T1_solver_status": int(t1["status"]),
            "T1_minimum_new_support_mass_kg": new_support_mass,
            "T1_used_edge_count": len(used_edges),
            "T1_used_existing_support_edge_count": len(used_existing_edges),
            "T1_used_new_support_edge_count": len(used_new_edges),
            "prospective_max_per_CV_mass_delta_kg": max_cv_delta,
            "prospective_iteration1_max_lower_violation_kg": lower_violation,
            "prospective_iteration1_max_upper_violation_kg": upper_violation,
            "execution_tier": tier,
            "support_extension_required": support_extension_required,
            "state_mutation_executed": False,
            "pressure_refresh_executed": False,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        if t0["success"]:
            next_name = "Controlled Day375 Pressure-Capacity Coupled Same-Time Reconciliation Execution — Existing Support"
        else:
            next_name = "Controlled Day375 Pressure-Capacity Coupled Same-Time Reconciliation Execution — One-Hop Face Extension"

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "P2_R6_R21_R5_authorized": True,
            "P2_R6_R21_R5_name": next_name,
            "P2_R6_R21_R5_execution_authorized": True,
            "P2_R6_R21_R5_execution_tier": tier,
            "P2_R6_R21_R5_must_bind_R4_semantics_contract": True,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "pressure_compatible_sidecar_execution_authorized": True,
            "support_extension_authorized": bool(support_extension_required),
            "support_extension_scope": (
                "one-hop Cartesian face-neighbor terminal sidecar edges only"
                if support_extension_required else
                "none; existing positive CV support only"
            ),
            "recursive_support_growth_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Semantics_Contract.json").write_bytes(jb(semantics))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Prospective_Edge_Plan.csv").write_bytes(csvb(edge_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Accepted Day375 state SHA256             :", accepted_sha)
        print("Source violating cells                   :", len(viol))
        print("Total required moved mass kg             :", total_excess)
        print("T0 existing-support exact feasible       :", t0["success"])
        print("T1 one-hop face exact feasible           :", t1["success"])
        print("Minimum new-support mass kg              :", new_support_mass)
        print("Selected execution tier                  :", tier)
        print("Support extension required               :", support_extension_required)
        print("Prospective max per-CV delta kg          :", max_cv_delta)
        print("Prospective max upper violation kg       :", upper_violation)
        print("State mutation / pressure refresh        : False / False")
        print("R6-R21-R5 execution authorized           : True")
        print("Darcy/Pollock/TOF / time / P3            : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "accepted_Day375_state_preserved": True,
                "state_mutation_executed": False,
                "automatic_rerun_authorized": False,
                "pressure_refresh_execution_authorized": False,
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
