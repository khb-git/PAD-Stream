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

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R3"
NAME = "First-Iteration Pressure-Induced Local Capacity Loss Diagnostic Freeze"
PASS = "AV4PIVOTP2R6R21R3_FIRST_ITERATION_PRESSURE_INDUCED_CAPACITY_LOSS_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R21R3_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "c84ffae09d8e476767f5c763f84c7e8043acc541"

R21R2_FAIL_SHA = "d2cb21fbddcc1e80fe5732ff56774128aeccc562f0068fc31dcfd60b9cf20117"
R21R2_FAIL_STATUS = "AV4PIVOTP2R6R21R2_CORRECTED_DAY375_ACCEPTED_STATE_PRESSURE_REFRESH_SCIENTIFIC_FAIL"
R21R2_FAIL_STAGE = "same_time_pressure_saturation_fixed_point"
R21R2_FAIL_GATE = "same_time_local_cell_mass_capacity"
R21R2_FAIL_MAX_EXCESS = 0.6205402106697875
R21R2_FAIL_TOL = 1.0e-8

A2E_RUNNER = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3_BLOB = "740c6da03e73906646bf0153633187e749449f31"
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
A2E = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A6E = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"

R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R21R2_FAIL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R2_R2_SCIENTIFIC_FAIL/"
    "POSTV16_AV4_PIVOT_P2_R6_R21_R2_Scientific_Fail_Report.json"
)

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R3_FirstIteration_"
    "PressureInduced_LocalCapacityLoss_Diagnostic_Freeze"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_BLOCKED"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = 37500
DAY = 375.0
CELL_TOL = 1e-8


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


def same_layer_r2(c: int) -> list[int]:
    k, j, i = ijk(c)
    out = []
    for dj in range(-2, 3):
        for di in range(-2, 3):
            if abs(di) + abs(dj) == 0 or abs(di) + abs(dj) > 2:
                continue
            jj, ii = j + dj, i + di
            if 0 <= jj < NY and 0 <= ii < NX:
                out.append(flat(k, jj, ii))
    return out


def selftest() -> None:
    assert NCELL == 37500
    assert face_neighbors(flat(1,1,1))
    assert len(same_layer_r2(flat(1,10,10))) == 12
    print("POSTV16 AV4 PIVOT P2-R6-R21-R3 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R21-R3 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21R3_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R21R2", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, blob, label in [
            (A2E_RUNNER, A2E_BLOB, "A2E"),
            (R2, R2_BLOB, "R2"),
            (SG2, SG2_BLOB, "SG2"),
            (SG3, SG3_BLOB, "SG3"),
            (R3, R3_BLOB, "R3R2R1"),
            (PERM, PERM_BLOB, "PERM"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R6R21R2_scientific_fail_authority"
        fail_path = drive / R21R2_FAIL
        gate("R6R21R2_FAIL_present", fail_path.is_file(), str(fail_path))
        gate("R6R21R2_FAIL_SHA_exact", sha(fail_path) == R21R2_FAIL_SHA, sha(fail_path))
        fail = js(fail_path)
        gate("R6R21R2_FAIL_status_exact", fail.get("status") == R21R2_FAIL_STATUS)
        gate("R6R21R2_FAIL_stage_exact", fail.get("failed_stage") == R21R2_FAIL_STAGE)
        gate("R6R21R2_FAIL_gate_exact", fail.get("failed_gate") == R21R2_FAIL_GATE)
        gate(
            "R6R21R2_FAIL_max_excess_exact",
            abs(float(fail["detail"]["maximum_excess_kg"]) - R21R2_FAIL_MAX_EXCESS) <= 1e-12,
            fail["detail"]["maximum_excess_kg"],
        )
        gate(
            "R6R21R2_FAIL_tolerance_exact",
            abs(float(fail["detail"]["tolerance_kg"]) - R21R2_FAIL_TOL) <= 1e-20,
        )
        gate("accepted_Day375_preserved", fail.get("accepted_Day375_state_preserved") is True)
        gate("pressure_refresh_not_accepted", fail.get("pressure_refresh_accepted") is False)

        stage = "accepted_state_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R6R20_state_accepted", a20.get("accepted_Day375_state") is True)
        gate("R6R20_state_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        state_path = r19 / R19_STATE
        gate("accepted_state_SHA_exact", sha(state_path) == accepted_sha, sha(state_path))

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

        stage = "frozen_property_authority"
        a2e = mod(root / A2E_RUNNER, "r6r21r3_a2e")
        r2 = mod(root / R2, "r6r21r3_r2")
        sg2 = mod(root / SG2, "r6r21r3_sg2")
        sg3 = mod(root / SG3, "r6r21r3_sg3")
        r3 = mod(root / R3, "r6r21r3_r3")

        control_path = drive / A6E / A6E_STATE
        gate("A6E_state_present", control_path.is_file(), str(control_path))
        gate("A6E_state_SHA_exact", sha(control_path) == A6E_STATE_SHA, sha(control_path))
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
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)
            frozen_p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate("inherited_pressure_matches_A2E_epoch", max_abs(inherited_pressure - frozen_pressure) <= 1e-12)
        gate("frozen_reference_pressure_finite", np.isfinite(frozen_p_ref), frozen_p_ref)

        parent_sg = a2e.invert_local_mass(
            r2, accepted_mass, inherited_pressure, frozen_p_ref, pore_volume
        )
        parent_sat = float(a2e.BACKGROUND) + np.asarray(parent_sg, dtype=float)
        parent_reconstructed = np.asarray(
            a2e.local_mass(r2, parent_sat, inherited_pressure, frozen_p_ref, pore_volume),
            dtype=float,
        )
        gate("parent_mass_reconstructs", max_abs(parent_reconstructed - accepted_mass) <= 1e-7)

        stage = "first_iteration_reproduction"
        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=float).reshape(GRID, order="C")
        mobility = a2e.spatial_mobility(parent_sat, nw, no, krw_max, kro_max)
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        tx, ty, tz, _face = r3.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
        )
        A, b, _wi = r3.assemble_updated_pressure_system(
            sg3, permeability, tx, ty, tz, mobility["lambda_total"]
        )
        _ppa, p1, linear_residual = r3.solve_updated_pressure(sg3, A, b)
        gate(
            "iteration1_pressure_linear_residual_matches_scientific_PASS_regime",
            linear_residual < float(a2e.PRESSURE_LINEAR_REL_RESIDUAL_MAX),
            linear_residual,
        )

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=float)
        cap0 = np.asarray(
            a2e.local_mass(r2, full_sat, inherited_pressure, frozen_p_ref, pore_volume),
            dtype=float,
        )
        cap1 = np.asarray(
            a2e.local_mass(r2, full_sat, p1, frozen_p_ref, pore_volume),
            dtype=float,
        )
        excess = accepted_mass - cap1
        tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cap1)), 1.0))
        viol = np.flatnonzero(excess.reshape(-1) > tol)

        gate("iteration1_violation_exists", len(viol) > 0, len(viol))
        max_excess = float(np.max(excess))
        gate(
            "iteration1_max_excess_reproduces_R21R2_FAIL",
            abs(max_excess - R21R2_FAIL_MAX_EXCESS) <= 1e-10,
            max_excess,
        )

        flat_mass = accepted_mass.reshape(-1)
        flat_cap0 = cap0.reshape(-1)
        flat_cap1 = cap1.reshape(-1)
        flat_p0 = inherited_pressure.reshape(-1)
        flat_p1 = p1.reshape(-1)
        flat_sat = parent_sat.reshape(-1)
        flat_excess = excess.reshape(-1)
        flat_slack = np.maximum(flat_cap1 - flat_mass, 0.0)

        total_excess = float(np.sum(flat_excess[viol]))
        global_positive_slack = float(np.sum(flat_slack))
        capacity_change = flat_cap1 - flat_cap0

        # Contribution attribution at violating cells.
        contribution_by_cell: dict[int, dict[int, float]] = {}
        for cv, cell, amount in zip(pair_cv.tolist(), pair_cell.tolist(), pair_mass.tolist()):
            contribution_by_cell.setdefault(int(cell), {})
            d = contribution_by_cell[int(cell)]
            d[int(cv)] = d.get(int(cv), 0.0) + float(amount)
        for cv, cell, amount in zip(halo_cv.tolist(), halo_cell.tolist(), halo_mass.tolist()):
            contribution_by_cell.setdefault(int(cell), {})
            d = contribution_by_cell[int(cell)]
            d[int(cv)] = d.get(int(cv), 0.0) + float(amount)

        rows = []
        implicated_cvs: set[int] = set()
        all_have_face_slack = True
        all_have_r2_slack = True
        for c in viol.tolist():
            k, j, i = ijk(int(c))
            face = face_neighbors(int(c))
            r2cells = same_layer_r2(int(c))
            face_slack = float(np.sum(flat_slack[face])) if face else 0.0
            r2_slack = float(np.sum(flat_slack[r2cells])) if r2cells else 0.0
            e = float(flat_excess[c])
            all_have_face_slack = all_have_face_slack and (face_slack + 1e-12 >= e)
            all_have_r2_slack = all_have_r2_slack and (r2_slack + 1e-12 >= e)

            contrib = contribution_by_cell.get(int(c), {})
            positive_contrib = {cv: m for cv, m in contrib.items() if m > 1e-13}
            implicated_cvs.update(positive_contrib)

            rows.append({
                "flat_cell": int(c),
                "k": k,
                "j": j,
                "i": i,
                "accepted_mass_kg": float(flat_mass[c]),
                "capacity_inherited_pressure_kg": float(flat_cap0[c]),
                "capacity_iteration1_pressure_kg": float(flat_cap1[c]),
                "capacity_change_kg": float(capacity_change[c]),
                "excess_kg": e,
                "inherited_pressure_psi": float(flat_p0[c]),
                "iteration1_pressure_psi": float(flat_p1[c]),
                "pressure_change_psi": float(flat_p1[c] - flat_p0[c]),
                "parent_saturation": float(flat_sat[c]),
                "face_neighbor_positive_slack_kg": face_slack,
                "same_layer_radius2_positive_slack_kg": r2_slack,
                "positive_contributing_CV_count": len(positive_contrib),
                "positive_contributing_CV_ids": ";".join(str(x) for x in sorted(positive_contrib)),
            })

        stage = "diagnostic_classification"
        pressure_delta = p1 - inherited_pressure
        affected_pressure_drop = [float(flat_p1[c] - flat_p0[c]) for c in viol.tolist()]
        affected_capacity_loss = [float(flat_cap1[c] - flat_cap0[c]) for c in viol.tolist()]

        diagnostic = {
            "R21R2_scientific_fail_sha256": R21R2_FAIL_SHA,
            "accepted_Day375_state_sha256": accepted_sha,
            "frozen_A2E_reference_gas_pressure_pa": frozen_p_ref,
            "iteration1_pressure_linear_relative_residual": float(linear_residual),
            "iteration1_pressure_relative_L2_vs_inherited": float(
                np.linalg.norm(pressure_delta.ravel()) /
                max(float(np.linalg.norm(inherited_pressure.ravel())), 1e-30)
            ),
            "iteration1_pressure_max_abs_change_psi": max_abs(pressure_delta),
            "violating_cell_count": int(len(viol)),
            "maximum_capacity_excess_kg": max_excess,
            "total_capacity_excess_kg": total_excess,
            "global_positive_slack_kg": global_positive_slack,
            "minimum_affected_pressure_change_psi": float(min(affected_pressure_drop)),
            "maximum_affected_pressure_change_psi": float(max(affected_pressure_drop)),
            "minimum_affected_capacity_change_kg": float(min(affected_capacity_loss)),
            "maximum_affected_capacity_change_kg": float(max(affected_capacity_loss)),
            "implicated_positive_contributing_CV_count": len(implicated_cvs),
            "all_violating_cells_have_face_neighbor_slack_at_least_local_excess": bool(all_have_face_slack),
            "all_violating_cells_have_same_layer_radius2_slack_at_least_local_excess": bool(all_have_r2_slack),
            "failure_mechanism": (
                "PRESSURE_REFRESH_REDUCES_LOCAL_EOS_CAPACITY_BELOW_ACCEPTED_FIXED_CELL_MASS"
            ),
            "pressure_solver_failure": False,
            "accepted_transport_state_invalidated": False,
            "pressure_compatible_representation_required": True,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": (
                "R6R21R3_PRESSURE_INDUCED_LOCAL_CAPACITY_LOSS_REPRODUCED_"
                "COUPLED_SAME_TIME_RECONCILIATION_SEMANTICS_DESIGN_NEXT"
            ),
            "P2_R6_R21_R4_authorized": True,
            "P2_R6_R21_R4_name": (
                "Day375 Pressure-Capacity Coupled Same-Time Conservative "
                "Reconciliation Semantics Design Freeze"
            ),
            "P2_R6_R21_R4_design_freeze_only": True,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "accepted_Day375_state_sha256": accepted_sha,
            "pressure_refresh_execution_authorized_now": False,
            "redistribution_execution_authorized_now": False,
            "support_growth_authorized_now": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": decision["classification"],
            **diagnostic,
            "state_mutation_executed": False,
            "pressure_refresh_accepted": False,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Violating_Cell_Audit.csv").write_bytes(csvb(rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Diagnostic_Contract.json").write_bytes(jb(diagnostic))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("R21-R2 scientific FAIL reproduced         : True")
        print("Iteration-1 pressure residual             :", linear_residual)
        print("Violating cell count                      :", len(viol))
        print("Maximum local capacity excess kg          :", max_excess)
        print("Total local capacity excess kg            :", total_excess)
        print("Global positive slack kg                  :", global_positive_slack)
        print("Implicated positive-contributing CV count :", len(implicated_cvs))
        print("All cells have face slack >= excess       :", all_have_face_slack)
        print("All cells have same-layer R2 slack        :", all_have_r2_slack)
        print("State mutation executed                   : False")
        print("R6-R21-R4 design freeze authorized        : True")
        print("Pressure / flow / time / P3 execution     : False / False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "accepted_Day375_state_preserved": True,
                "state_mutation_executed": False,
                "pressure_refresh_accepted": False,
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
