#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R1"

STATUS_PASS = (
    "AV4F4R3R3R3R3R1_R3R3R3R3_E1_SINGLE_RING_HALL_DEFICIT_BOUND_"
    "PROSPECTIVE_SUPPORT_CLASS_FEASIBILITY_AUDIT_COMPLETE_NO_REPAIR_SELECTED"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R1_PROSPECTIVE_SUPPORT_FEASIBILITY_AUDIT_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R3R3R3_COMMIT = "d01a87f9b4fab74e197b4804da2785de1a9fb0ce"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NCV = 200
NCVTOTAL = NSL * NCV
INJECTED = 0.80

EXPECTED_E1_MIN_UNSERVED_KG = 563162.189227371
EXPECTED_E1_HALL_CV_COUNT = 9787
EXPECTED_E1_HALL_CELL_COUNT = 1355
EXPECTED_E1_HALL_DEMAND_KG = 3384530.384180404
EXPECTED_E1_HALL_CAPACITY_KG = 2821368.1949598324
EXPECTED_E1_HALL_DEFICIT_KG = 563162.1892205714

R3R3R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_"
    "Per_CV_Horizontal_Face_Occupancy_Extension_Execution.py"
)
R3R3R3R3_BLOB = "a20a31bd48d4331b50dc71488ceaa5dc611acf25"

R3R3R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R2_"
    "Per_CV_Horizontal_Face_Occupancy_Extension_Freeze.py"
)
R3R3R3R2_BLOB = "3768e7b2793b959be83629bc3299e81353ca4af2"

R3R3R3R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R1_"
    "S0_CV_Cell_Capacity_Hall_Deficit_Localization.py"
)
R3R3R3R1_BLOB = "304f68abf78a55cf00917667cff33e20b415db46"

F2R3 = (
    "PAD_Stream_POSTV16_AV4_F2_R3_"
    "Bounded_Physical_Occupancy_Projection_Execution.py"
)
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

A2E = (
    "PAD_Stream_POSTV16_AV4_A2_E_"
    "Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
)
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_"
    "Capillary_Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R3R3R3R3: R3R3R3R3_BLOB,
    R3R3R3R2: R3R3R3R2_BLOB,
    R3R3R3R1: R3R3R3R1_BLOB,
    F2R3: F2R3_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R3R3R3_FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_SCIENTIFIC_FAIL"
R3R3R3R3_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_Scientific_Fail_Report.json"
R3R3R3R3_FAIL_STATUS = (
    "AV4F4R3R3R3R3_FROZEN_E1_ASSIGNMENT_OR_SINGLE_FLOW_REFRESH_OR_REPROJECTION_"
    "SCIENTIFIC_FAIL_NO_H2_NO_VERTICAL_OR_DIAGONAL_EXTENSION_NO_ALTERNATE_REPAIR"
)

F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"
F2R3_MANIFEST = "POSTV16_AV4_F2_R3_Artifact_Manifest.csv"

R3R1R2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R1_R2_Corrected_Interior_Bound_Failure_Localization"
)
R3R1R2_STATE = "POSTV16_AV4_F4_R3_R1_R2_Partial_Teacher_State_at_Failure.npz"
R3R1R2_MANIFEST = "POSTV16_AV4_F4_R3_R1_R2_Artifact_Manifest.csv"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Prospective_Support_Class_Feasibility_Audit"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R1_BLOCKED"


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    manifest = {r["file"]: r["sha256"] for r in rows}
    if not manifest:
        raise GateError("manifest_empty:" + name)
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA_mismatch:" + fn)
    return manifest


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
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
    return s.getvalue().encode()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def near(a: Any, b: Any, rtol: float = 1e-10, atol: float = 1e-5) -> bool:
    aa = float(a)
    bb = float(b)
    return abs(aa - bb) <= max(atol, rtol * max(abs(bb), 1.0))


def build_support_from_offsets(
    e0_cv: np.ndarray,
    e0_cell: np.ndarray,
    offsets: list[tuple[int, int, int]],
) -> dict[str, np.ndarray]:
    cv = np.asarray(e0_cv, dtype=np.int64).reshape(-1)
    cell = np.asarray(e0_cell, dtype=np.int64).reshape(-1)
    k = cell // (NY * NX)
    rem = cell % (NY * NX)
    j = rem // NX
    i = rem % NX

    keys = []
    for dk, dj, di in offsets:
        kk = k + dk
        jj = j + dj
        ii = i + di
        mask = (
            (kk >= 0) & (kk < NZ)
            & (jj >= 0) & (jj < NY)
            & (ii >= 0) & (ii < NX)
        )
        cc = kk[mask] * (NY * NX) + jj[mask] * NX + ii[mask]
        keys.append(cv[mask] * NCELL + cc)

    key = np.unique(np.concatenate(keys))
    out_cv = (key // NCELL).astype(np.int64)
    out_cell = (key % NCELL).astype(np.int64)

    e0_key = np.unique(cv * NCELL + cell)
    pos = np.searchsorted(key, e0_key)
    if np.any(pos >= len(key)) or not np.array_equal(key[pos], e0_key):
        raise GateError("E0_not_subset_of_candidate")

    e0_global = np.unique(cell)
    cand_global = np.unique(out_cell)
    new_global = np.setdiff1d(cand_global, e0_global, assume_unique=True)
    return {
        "key": key,
        "cv": out_cv,
        "cell": out_cell,
        "pair_count": int(len(key)),
        "global_cell_count": int(len(cand_global)),
        "globally_new_cell_count": int(len(new_global)),
    }


def h1_offsets() -> list[tuple[int, int, int]]:
    return [
        (0, 0, 0),
        (0, 0, -1), (0, 0, 1),
        (0, -1, 0), (0, 1, 0),
    ]


def h2_offsets() -> list[tuple[int, int, int]]:
    # Horizontal Cartesian graph distance <= 2 from E0 using face steps only.
    offsets = []
    for dj in range(-2, 3):
        for di in range(-2, 3):
            if abs(dj) + abs(di) <= 2:
                offsets.append((0, dj, di))
    return offsets


def h1v1_offsets() -> list[tuple[int, int, int]]:
    return h1_offsets() + [(-1, 0, 0), (1, 0, 0)]


def h2v1_offsets() -> list[tuple[int, int, int]]:
    # H2 horizontally plus one direct vertical face step from E0.
    return h2_offsets() + [(-1, 0, 0), (1, 0, 0)]


def evaluate_candidate(
    name: str,
    support: dict[str, np.ndarray],
    demand: np.ndarray,
    available: np.ndarray,
    r1mod: Any,
) -> dict[str, Any]:
    sol = r1mod.minimum_unserved_lp(
        support["cv"],
        support["cell"],
        demand,
        available,
        NCVTOTAL,
        NCELL,
    )
    total_demand = float(math.fsum(float(x) for x in demand))
    tol = max(1e-6, 1e-10 * max(total_demand, 1.0))
    deficit = float(sol["minimum_unserved_mass"])

    row: dict[str, Any] = {
        "candidate": name,
        "pair_count": support["pair_count"],
        "global_cell_count": support["global_cell_count"],
        "globally_new_cell_count": support["globally_new_cell_count"],
        "minimum_unserved_mass_kg": deficit,
        "feasible": deficit <= tol,
        "tolerance_kg": tol,
        "Hall_CV_count": 0,
        "Hall_cell_count": 0,
        "Hall_streamline_count": 0,
        "Hall_demand_kg": 0.0,
        "Hall_capacity_kg": 0.0,
        "Hall_deficit_kg": 0.0,
    }

    if deficit > tol:
        witness = r1mod.residual_mincut_witness(
            support["cv"],
            support["cell"],
            sol["pair_flow"],
            sol["unserved_cv"],
            demand,
            available,
            NCVTOTAL,
            NCELL,
            flow_tol=max(1e-8, 1e-12 * max(total_demand, 1.0)),
        )
        cv_mask = np.asarray(witness["cv_reachable"], dtype=bool)
        cv_ids = np.flatnonzero(cv_mask)
        row.update(
            {
                "Hall_CV_count": int(np.sum(cv_mask)),
                "Hall_cell_count": int(np.sum(witness["cell_reachable"])),
                "Hall_streamline_count":
                    int(np.unique(cv_ids // NCV).size) if cv_ids.size else 0,
                "Hall_demand_kg": float(witness["demand_U"]),
                "Hall_capacity_kg": float(witness["capacity_N"]),
                "Hall_deficit_kg": float(witness["hall_deficit"]),
            }
        )
    return row


def self_test() -> None:
    assert set(h1_offsets()) == {
        (0, 0, 0), (0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0)
    }
    assert len(h2_offsets()) == 13
    assert (-1, 0, 0) in h1v1_offsets() and (1, 0, 0) in h1v1_offsets()
    assert all(abs(dk) <= 1 for dk, _, _ in h2v1_offsets())
    assert all(not (dk != 0 and (dj != 0 or di != 0)) for dk, dj, di in h2v1_offsets())

    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R1 prospective support-class "
        "feasibility audit self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R1 — PROSPECTIVE SUPPORT-CLASS "
        "FEASIBILITY AUDIT AFTER E1 HALL DEFICIT"
    )
    print("=" * 214)
    print("DIAGNOSTIC ONLY. R3-R3-R3-R3 SCIENTIFIC FAIL REMAINS IMMUTABLE.")
    print("NO MAPBACK ASSIGNMENT. NO FLOW REFRESH. NO PHYSICAL-TIME ADVANCE.")
    print("NO CANDIDATE SELECTED IN THIS RUNNER. NO F5. NO TRAINING. NO CMG.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_R3R3R3R3_commit",
            parent == PARENT_R3R3R3R3_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "R3R3R3R3_fail_binding"
        fail_path = drive / R3R3R3R3_FAIL_REL / R3R3R3R3_FAIL_REPORT
        gate("R3R3R3R3_fail_report_present", fail_path.is_file(), str(fail_path))
        fail = load_json(fail_path)
        gate(
            "R3R3R3R3_fail_status_exact",
            fail["status"] == R3R3R3R3_FAIL_STATUS,
            fail["status"],
        )
        gate(
            "R3R3R3R3_fail_stage_exact",
            fail["failed_stage"] == "frozen_E1_assignment",
            fail["failed_stage"],
        )
        gate(
            "R3R3R3R3_fail_gate_exact",
            fail["failed_gate"] == "E1_SINGLE_RING_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT",
            fail["failed_gate"],
        )
        detail = fail["detail"]
        gate(
            "R3R3R3R3_E1_min_unserved_exact",
            near(detail["minimum_unserved_mass_kg"], EXPECTED_E1_MIN_UNSERVED_KG),
            detail["minimum_unserved_mass_kg"],
        )
        gate(
            "R3R3R3R3_E1_Hall_exact",
            int(detail["Hall_CV_count"]) == EXPECTED_E1_HALL_CV_COUNT
            and int(detail["Hall_cell_count"]) == EXPECTED_E1_HALL_CELL_COUNT
            and near(detail["Hall_demand_kg"], EXPECTED_E1_HALL_DEMAND_KG)
            and near(detail["Hall_capacity_kg"], EXPECTED_E1_HALL_CAPACITY_KG)
            and near(detail["Hall_deficit_kg"], EXPECTED_E1_HALL_DEFICIT_KG),
            detail,
        )
        gate(
            "R3R3R3R3_fail_no_fallback",
            fail["H2_or_vertical_or_diagonal_expansion"] is False
            and fail["automatic_fallback_authorized"] is False
            and fail["R3R3R4_authorized"] is False
            and fail["F5_dataset_generation_authorized"] is False
            and fail["physical_time_advanced"] is False,
        )

        stage = "state_authority_binding"
        f2d = drive / F2R3_REL
        evd = drive / R3R1R2_REL
        a2d = drive / A2E_REL
        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        gate("R3R1R2_output_present", evd.is_dir(), str(evd))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        verify_manifest(f2d, F2R3_MANIFEST)
        verify_manifest(evd, R3R1R2_MANIFEST)
        verify_manifest(a2d, A2E_MANIFEST)

        with np.load(f2d / F2R3_STATE, allow_pickle=False) as z:
            sub_flat = np.asarray(z["subsegment_flat_cell"], dtype=np.int64)
            sub_stream = np.asarray(z["subsegment_streamline"], dtype=np.int64)
            sub_cv = np.asarray(z["subsegment_control_volume"], dtype=np.int64)
            residual_grid = np.asarray(z["residual_grid_component_mass_kg"], dtype=np.float64)

        with np.load(evd / R3R1R2_STATE, allow_pickle=False) as z:
            event_cv_mass = np.asarray(z["partial_CV_component_mass_kg"], dtype=np.float64)

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            parent_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            grid_pv = np.asarray(z["pore_volume_m3"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate(
            "authority_shapes_exact",
            residual_grid.shape == GRID
            and event_cv_mass.shape == (NSL, NCV)
            and parent_pressure.shape == GRID
            and grid_pv.shape == GRID
            and len(sub_flat) == len(sub_stream) == len(sub_cv),
        )

        stage = "prospective_support_evaluation"
        r1mod = load_module(root / R3R3R3R1, "postv16_av4_r3r3r3r3r1_r1")
        a2e = load_module(root / A2E, "postv16_av4_r3r3r3r3r1_a2e")
        r2 = load_module(root / R2, "postv16_av4_r3r3r3r3r1_r2")

        e0_cv_raw = sub_stream * NCV + sub_cv
        e0_key = np.unique(e0_cv_raw * NCELL + sub_flat)
        e0_cv = (e0_key // NCELL).astype(np.int64)
        e0_cell = (e0_key % NCELL).astype(np.int64)
        gate("E0_pair_count_exact_269721", len(e0_key) == 269721, len(e0_key))

        cell_capacity = np.asarray(
            a2e.local_mass(
                r2,
                np.full(GRID, INJECTED, dtype=np.float64),
                parent_pressure,
                p_ref,
                grid_pv,
            ),
            dtype=np.float64,
        ).reshape(-1)
        available = cell_capacity - residual_grid.reshape(-1)
        cap_tol = max(1e-7, 1e-12 * max(float(np.max(np.abs(cell_capacity))), 1.0))
        gate(
            "residual_sidecar_within_capacity",
            float(np.min(available)) >= -cap_tol,
            {
                "minimum_available_capacity_kg": float(np.min(available)),
                "tolerance_kg": cap_tol,
            },
        )
        available = np.maximum(available, 0.0)
        demand = event_cv_mass.reshape(-1)

        candidates = [
            ("H1_REPRODUCTION", h1_offsets()),
            ("H2_HORIZONTAL_GRAPH_RADIUS_2", h2_offsets()),
            ("H1_PLUS_V1_DIRECT_3D_FACE_RING", h1v1_offsets()),
            ("H2_PLUS_V1", h2v1_offsets()),
        ]

        rows = []
        for name, offsets in candidates:
            support = build_support_from_offsets(e0_cv, e0_cell, offsets)
            row = evaluate_candidate(name, support, demand, available, r1mod)
            rows.append(row)
            print(
                f"[CANDIDATE] {name} — feasible={row['feasible']} "
                f"min_unserved={row['minimum_unserved_mass_kg']:.12g} kg "
                f"pairs={row['pair_count']} cells={row['global_cell_count']}"
            )

        h1 = rows[0]
        gate(
            "H1_reproduces_formal_R3R3R3R3_fail",
            near(h1["minimum_unserved_mass_kg"], EXPECTED_E1_MIN_UNSERVED_KG)
            and h1["feasible"] is False,
            {
                "minimum_unserved_mass_kg": h1["minimum_unserved_mass_kg"],
                "Hall_deficit_kg": h1["Hall_deficit_kg"],
            },
        )

        feasible_rows = [r for r in rows[1:] if r["feasible"]]
        classification = (
            "AT_LEAST_ONE_PROSPECTIVE_EXTENSION_CLASS_FEASIBLE"
            if feasible_rows
            else "ALL_TESTED_PROSPECTIVE_EXTENSION_CLASSES_INFEASIBLE"
        )

        # Diagnostic ranking only; not a repair selection.
        diagnostic_order = sorted(
            rows[1:],
            key=lambda r: (
                0 if r["feasible"] else 1,
                r["minimum_unserved_mass_kg"],
                r["pair_count"],
                r["globally_new_cell_count"],
                r["candidate"],
            ),
        )
        best_diagnostic = diagnostic_order[0]

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "H1_minimum_unserved_mass_kg": h1["minimum_unserved_mass_kg"],
            "prospective_feasible_candidate_count": len(feasible_rows),
            "diagnostic_best_candidate_by_feasibility_deficit_support_size":
                best_diagnostic["candidate"],
            "repair_selected": False,
            "repair_execution_authorized": False,
            "R3R3R3R3R2_design_freeze_authorized": True,
            "R3R3R4_authorized": False,
            "F5_authorized": False,
        }

        diagnosis = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "candidate_matrix": rows,
            "diagnostic_ranking": diagnostic_order,
            "interpretation": (
                "This audit compares prospective reachability classes only. "
                "Feasibility does not itself authorize execution. A separate freeze "
                "must select one candidate and define its lexicographic mapback semantics."
            ),
            "repair_selected": False,
            "mapback_executed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
        }

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R3-R3-R2",
            "name": "Prospective Support Extension Selection / Design Freeze",
            "authorized": True,
            "execution": False,
            "required_R3R3R3R3R1_status": STATUS_PASS,
            "candidate_matrix": rows,
            "repair_selected": False,
            "repair_execution_authorized": False,
            "automatic_candidate_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "repair_selected": False,
            "repair_execution_performed": False,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "R3R3R3R3R2_design_freeze_authorized": True,
            "R3R3R3R3R2_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Prospective_Support_Feasibility_Diagnosis.json":
                json_bytes(diagnosis),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Candidate_Matrix.csv":
                csv_bytes(rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R1_R3R3R3R3R2_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R3-R1: PROSPECTIVE SUPPORT-CLASS "
            "FEASIBILITY AUDIT PASS"
        )
        print("=" * 214)
        print("R3-R3-R3-R3 scientific FAIL               : PRESERVED")
        print("H1 minimum unassignable mass kg            :", h1["minimum_unserved_mass_kg"])
        for row in rows[1:]:
            print(
                f"{row['candidate']:<42}: "
                f"feasible={row['feasible']}  "
                f"min_unserved={row['minimum_unserved_mass_kg']} kg  "
                f"pairs={row['pair_count']}"
            )
        print("Diagnostic classification                  :", classification)
        print("Diagnostic best candidate                  :", best_diagnostic["candidate"])
        print("Repair selected                            : False")
        print("POSTV16-AV4-F4-R3-R3-R3-R3-R2 design     : AUTHORIZED")
        print("Repair execution / R3-R3-R4 / F5          : NOT AUTHORIZED")
        print("=" * 214)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "repair_selected": False,
            "repair_execution_authorized": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R3R3R2_design_freeze_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("R3-R3-R3-R3 scientific FAIL remains immutable.")
        print("NO REPAIR SELECTION, MAPBACK, FLOW REFRESH, OR AUTO-RERUN AUTHORIZED.")
        print("=" * 214)
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
