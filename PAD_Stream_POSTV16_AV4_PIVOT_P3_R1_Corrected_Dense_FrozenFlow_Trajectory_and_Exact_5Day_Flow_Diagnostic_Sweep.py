#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV4-PIVOT-P3-R1"
NAME = "Corrected Dense Frozen-Flow Trajectory + Exact 5-Day Flow-Diagnostic Sweep Execution"
PASS = (
    "AV4PIVOTP3R1_CORRECTED_DENSE_FROZENFLOW_TRAJECTORY_EXACT_5DAY_FLOW_DIAGNOSTIC_"
    "SWEEP_PASS_28_STATES_28_DIAGNOSTICS_NO_CADENCE_SELECTION"
)
SCI_FAIL = (
    "AV4PIVOTP3R1_CORRECTED_DENSE_FROZENFLOW_TRAJECTORY_SCIENTIFIC_FAIL_"
    "NO_AUTOMATIC_PHYSICS_CHANGE"
)
BLOCK = "AV4PIVOTP3R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "c6c7f62911605e78cd466b9700d7c26ef12fb578"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = int(np.prod(GRID))
NSL = 1078
NN = 201
NCV = 200
NCVT = NSL * NCV

START_DAY = 365.0
END_DAY = 500.0
OBS_DAYS = np.asarray([float(x) for x in range(365, 501, 5)], dtype=np.float64)
CANDIDATE_CADENCES = [50.0, 5.0]
POLICIES = ["frozen flow", "50-day refresh", "5-day refresh"]

DAY_TO_S = 86400.0
BACKGROUND = 0.20
MAX_SAT = 0.80
MAX_SG = 0.60
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HALO_OPT_TOL = 1.0e-6
MAX_RETRIES = 8
RETRY_FACTOR = 0.5
HIGHS_PRIMAL_FEASIBILITY_TOL = 1.0e-10
HIGHS_DUAL_FEASIBILITY_TOL = 1.0e-10

R32_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
A2E_EPOCH_SHA = "b49d48baa9d791b69a9e9c41635e1930fae84114b93ceb15ab5b21d3441ba08d"
A6E_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

# Repository source authorities.
P3R0 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R0_Corrected_Dense_Cadence_Diagnostic_Protocol_Freeze.py"
P3R0_BLOB = "253cddb01acf48767c533e4999f1d7d8d8521841"
R25R3 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py"
R25R3_BLOB = "65cab626419137b191f2c53a4c543d9805ccf68d"
R31 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"
R31_BLOB = "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a"
R32 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"
R32_BLOB = "435f5d6dcba38de7166e41ba9e081b6ef573edcf"
P0 = "PAD_Stream_POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze.py"
P0_BLOB = "74342f6e770803acf66deeff80c62400fd8aa96f"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    P3R0: P3R0_BLOB,
    R25R3: R25R3_BLOB,
    R31: R31_BLOB,
    R32: R32_BLOB,
    P0: P0_BLOB,
    A2E: A2E_BLOB,
    R2SRC: R2SRC_BLOB,
    E37A: E37A_BLOB,
    E36: E36_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    SG7A: SG7A_BLOB,
    SG7D: SG7D_BLOB,
    R3R2R1: R3R2R1_BLOB,
    PERM: PERM_BLOB,
}

# P3-R0 drive authority.
P3R0_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R0_Corrected_Dense_Cadence_Diagnostic_Protocol_Freeze"
P3R0_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R0_Summary.json"
P3R0_TIMESTEP = "POSTV16_AV4_PIVOT_P3_R0_Atomic_Substep_and_Observation_Policy.json"
P3R0_HANDOFF = "POSTV16_AV4_PIVOT_P3_R0_P3_R1_Handoff_Contract.json"
P3R0_DECISION = "POSTV16_AV4_PIVOT_P3_R0_Decision_Contract.json"
P3R0_MANIFEST = "POSTV16_AV4_PIVOT_P3_R0_Artifact_Manifest.csv"
P3R0_STATUS = (
    "AV4PIVOTP3R0_CORRECTED_DENSE_CADENCE_DIAGNOSTIC_PROTOCOL_FREEZE_PASS_"
    "R32_RECURRENT_SEMANTICS_BOUND_NO_PHYSICS_EXECUTION"
)

# P0 cadence-diagnostic science authority.
P0_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze"
P0_ARCH = "POSTV16_AV4_PIVOT_P0_Diagnostic_Architecture.json"
P0_GUARDS = "POSTV16_AV4_PIVOT_P0_Scientific_Guardrails.json"
P0_MANIFEST = "POSTV16_AV4_PIVOT_P0_Artifact_Manifest.csv"

# A2E Day365 exact flow authority.
A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

# AV3 heterogeneous storage/relperm authority.
A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_MANIFEST = "POSTV16_AV3_A6_E_Artifact_Manifest.csv"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1"
OUT_REL = BASE_AV4 / (
    OUT_TOKEN + "_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep"
)
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
FAIL_REL = BASE_AV4 / (OUT_TOKEN + "_SCIENTIFIC_FAIL")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
DENSE_AUDIT = f"{OUT_TOKEN}_Dense_State_Audit.csv"
ATOMIC_AUDIT = f"{OUT_TOKEN}_Atomic_Substep_Audit.csv"
DIAG_METRICS = f"{OUT_TOKEN}_Exact_Flow_Diagnostic_Metrics.csv"
PRODUCER_AUDIT = f"{OUT_TOKEN}_Producer_Component_Mass_Audit.csv"
REPRESENTATION_AUDIT = f"{OUT_TOKEN}_Representation_Repair_Audit.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


class TrialReject(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
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
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    if not result:
        raise GateError(f"manifest_empty:{filename}")
    return result


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_dtype_forbidden:{key}")
            payload = io.BytesIO()
            np.lib.format.write_array(payload, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, payload.getvalue())
    return outer.getvalue()


def build_xy1_support(
    exact_cv: np.ndarray,
    exact_cell: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    exact_cv = np.asarray(exact_cv, dtype=np.int64)
    exact_cell = np.asarray(exact_cell, dtype=np.int64)
    exact_keys = exact_cv * NCELL + exact_cell
    support: dict[int, int] = {int(k): 0 for k in exact_keys.tolist()}

    for cv, cell in zip(exact_cv.tolist(), exact_cell.tolist()):
        k = cell // (NY * NX)
        rem = cell % (NY * NX)
        j = rem // NX
        i = rem % NX
        for dj, di in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            jj = j + dj
            ii = i + di
            if 0 <= jj < NY and 0 <= ii < NX:
                ncell = k * NY * NX + jj * NX + ii
                key = int(cv) * NCELL + int(ncell)
                if key not in support:
                    support[key] = 1

    keys = np.asarray(sorted(support), dtype=np.int64)
    edge_cv = keys // NCELL
    edge_cell = keys % NCELL
    shell = np.asarray([support[int(k)] for k in keys.tolist()], dtype=np.int8)

    pos = {int(k): idx for idx, k in enumerate(keys.tolist())}
    exact_pos = np.asarray([pos[int(k)] for k in exact_keys.tolist()], dtype=np.int64)
    return edge_cv, edge_cell, shell, exact_pos


def selftest() -> None:
    assert len(OBS_DAYS) == 28
    assert OBS_DAYS[0] == 365.0 and OBS_DAYS[-1] == 500.0
    assert CANDIDATE_CADENCES == [50.0, 5.0]
    cv = np.asarray([0, 0, 1], dtype=np.int64)
    cell = np.asarray([0, 1, NX * NY + NX + 1], dtype=np.int64)
    ecv, ecell, shell, pos = build_xy1_support(cv, cell)
    assert len(pos) == 3
    assert np.all(shell[pos] == 0)
    assert np.all((shell == 0) | (shell == 1))
    print("POSTV16 AV4 PIVOT P3-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    staging = drive / STAGE_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL

    stage = "preflight"
    gates: list[dict[str, Any]] = []
    science_started = False
    current_time = START_DAY
    current_observation_index = 0
    accepted_atomic_steps = 0
    representation_repairs = 0

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
            "scientific_execution_gate": True,
            "detail": "" if detail is None else repr(detail),
        })
        if not ok:
            print(f"[FAIL] {name} -- {detail}")
            raise ScientificFail(name, detail)

    def save_npz(path: Path, arrays: dict[str, Any]) -> str:
        path.write_bytes(deterministic_npz_bytes(arrays))
        return sha(path)

    def validate_restart(arrays: dict[str, Any], expected_time: float) -> None:
        payload = deterministic_npz_bytes(arrays)
        with np.load(io.BytesIO(payload), allow_pickle=False) as z:
            if abs(float(np.asarray(z["physical_day"]).reshape(())) - expected_time) > 1.0e-12:
                raise TrialReject("restart_time_mismatch")
            if not np.array_equal(z["cartesian_component_mass_kg"], arrays["cartesian_component_mass_kg"]):
                raise TrialReject("restart_cartesian_mass_mismatch")
            if not np.array_equal(z["transport_CV_component_mass_kg"], arrays["transport_CV_component_mass_kg"]):
                raise TrialReject("restart_CV_mass_mismatch")
            if not np.array_equal(z["grid_residual_component_mass_kg"], arrays["grid_residual_component_mass_kg"]):
                raise TrialReject("restart_residual_mismatch")

    def support_repair(
        *,
        edge_cv: np.ndarray,
        edge_cell: np.ndarray,
        shell: np.ndarray,
        new_cv_mass: np.ndarray,
        rep_capacity_flat: np.ndarray,
        direct_target_rep: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        nedge = len(edge_cv)
        Aeq = coo_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (edge_cv, np.arange(nedge, dtype=np.int64)),
            ),
            shape=(NCVT, nedge),
        ).tocsr()
        beq = new_cv_mass.reshape(-1).copy()

        Acell = coo_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (edge_cell, np.arange(nedge, dtype=np.int64)),
            ),
            shape=(NCELL, nedge),
        ).tocsr()

        c1 = (shell > 0).astype(np.float64)
        lp1 = linprog(
            c1,
            A_ub=Acell,
            b_ub=rep_capacity_flat,
            A_eq=Aeq,
            b_eq=beq,
            bounds=(0.0, None),
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
                "dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
            },
        )
        if not lp1.success:
            raise TrialReject(f"XY1_stage1_infeasible:{lp1.status}:{lp1.message}")
        halo_opt = float(lp1.fun)

        nd = NCELL
        zero_d = csr_matrix((NCELL, nd), dtype=np.float64)
        A_cap = hstack([Acell, zero_d], format="csr")
        I = eye(nd, format="csr", dtype=np.float64)
        A_abs_pos = hstack([Acell, -I], format="csr")
        A_abs_neg = hstack([-Acell, -I], format="csr")
        target = direct_target_rep.reshape(-1)

        halo_row = csr_matrix(c1.reshape(1, -1))
        zero1 = csr_matrix((1, nd), dtype=np.float64)
        A_halo_pos = hstack([halo_row, zero1], format="csr")
        A_halo_neg = hstack([-halo_row, zero1], format="csr")
        b_halo = np.asarray(
            [halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL],
            dtype=np.float64,
        )

        A_ub = vstack([A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg], format="csr")
        b_ub = np.concatenate([rep_capacity_flat, target, -target, b_halo])
        Aeq2 = hstack([Aeq, csr_matrix((NCVT, nd), dtype=np.float64)], format="csr")
        c2 = np.concatenate([np.zeros(nedge), np.ones(nd)])
        bounds = [(0.0, None)] * (nedge + nd)

        lp2 = linprog(
            c2,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=Aeq2,
            b_eq=beq,
            bounds=bounds,
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
                "dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
            },
        )
        if not lp2.success:
            raise TrialReject(f"XY1_stage2_infeasible:{lp2.status}:{lp2.message}")

        z = np.asarray(lp2.x, dtype=np.float64)
        x = z[:nedge]
        d = z[nedge:]
        cv_check = np.bincount(edge_cv, weights=x, minlength=NCVT).reshape(NSL, NCV)
        cv_err = float(np.max(np.abs(cv_check - new_cv_mass)))
        cell_rep = np.bincount(edge_cell, weights=x, minlength=NCELL).reshape(GRID)
        halo_mass = float(np.sum(x[shell > 0]))
        l1_exact = float(np.sum(np.abs(cell_rep - direct_target_rep)))
        d_err = float(np.max(np.abs(d - np.abs(cell_rep.reshape(-1) - target))))

        if cv_err > MASS_TOL:
            raise TrialReject(f"XY1_CV_equality:{cv_err}")
        if abs(halo_mass - halo_opt) > 2.0 * HALO_OPT_TOL:
            raise TrialReject(f"XY1_halo_optimum:{halo_mass}:{halo_opt}")
        if abs(float(lp2.fun) - l1_exact) > max(1e-5, 1e-10 * max(l1_exact, 1.0)):
            raise TrialReject("XY1_L1_objective_mismatch")
        if d_err > 1.0e-5:
            raise TrialReject(f"XY1_abs_auxiliary:{d_err}")

        return x, {
            "mode": "XY1_LEXICOGRAPHIC_REPAIR",
            "stage1_terminal_mass_kg": halo_opt,
            "stage2_terminal_mass_kg": halo_mass,
            "stage2_cell_L1_kg": l1_exact,
            "CV_equality_max_abs_error_kg": cv_err,
        }

    try:
        print("=" * 220)
        print("POSTV16-AV4-PIVOT-P3-R1 — CORRECTED DENSE FROZEN-FLOW TRAJECTORY + EXACT 5-DAY FLOW-DIAGNOSTIC SWEEP")
        print("=" * 220)
        print("COMMON TRANSPORT FLOW EPOCH: DAY365 ONLY.")
        print("DIAGNOSTIC REFRESH: S(t) -> MOBILITY -> ONE EXACT PRESSURE SOLVE -> DARCY -> POLLOCK -> TOF.")
        print("DIAGNOSTIC REFRESH IS NOT A SAME-TIME FIXED-POINT CLAIM AND DOES NOT FEED BACK INTO TRANSPORT.")
        print("NO ML. NO CADENCE SELECTION. P4 REMAINS LOCKED UNTIL FULL P3-R1 PASS.")
        print()

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_FAIL", not (fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json").exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_STAGING", not staging.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "P0_and_P3R0_authority"
        p0d = drive / P0_REL
        p0m = manifest(p0d, P0_MANIFEST)
        p0a = js(p0d / P0_ARCH)
        p0g = js(p0d / P0_GUARDS)
        gate("P0_P3_pipeline_exact",
             p0a["phase_P3"]["pipeline"] ==
             ["S(t)", "spatial mobility", "pressure", "Darcy flux", "Pollock", "TOF"])
        gate("P0_diagnostic_not_fixedpoint",
             p0g.get("diagnostic_refresh_is_not_a_same_time_fixed_point_claim") is True)
        gate("P0_no_transport_feedback",
             p0a["phase_P3"]["transport_restart_from_refreshed_geometry"] is False)

        p3d = drive / P3R0_REL
        p3m = manifest(p3d, P3R0_MANIFEST)
        p3s = js(p3d / P3R0_SUMMARY)
        p3t = js(p3d / P3R0_TIMESTEP)
        p3h = js(p3d / P3R0_HANDOFF)
        p3c = js(p3d / P3R0_DECISION)
        gate("P3R0_status_exact", p3s.get("status") == P3R0_STATUS, p3s.get("status"))
        gate("P3R0_R1_authorized", p3c.get("P3_R1_execution_authorized") is True)
        gate("P3R0_physics_authorized", p3c.get("P3_R1_physics_execution_authorized") is True)
        gate("P3R0_P4_locked", p3c.get("P4_authorized") is False)
        gate("P3R0_observation_days_exact",
             p3h.get("must_use_28_observation_days_exact") == OBS_DAYS.tolist())
        gate("P3R0_A2E_SHA_exact", p3h.get("must_bind_A2E_Day365_flow_epoch_SHA") == A2E_EPOCH_SHA)
        gate("P3R0_R32_SHA_exact", p3h.get("must_bind_R32_authoritative_state_SHA") == R32_STATE_SHA)
        gate("P3R0_atomic_policy_exact",
             p3t["internal_atomic_step_policy"]["retry_factor"] == RETRY_FACTOR
             and p3t["internal_atomic_step_policy"]["maximum_retries_per_atomic_step"] == MAX_RETRIES)
        gate("P3R0_common_flow_epoch_exact", p3s.get("common_transport_flow_epoch_day") == START_DAY)
        gate("P3R0_no_feedback", p3s.get("diagnostic_refresh_feedback_to_transport") is False)

        stage = "drive_input_authority"
        a2ed = drive / A2E_REL
        a2em = manifest(a2ed, A2E_MANIFEST)
        a2ep = a2ed / A2E_EPOCH
        gate("A2E_epoch_manifest_SHA_exact", a2em.get(A2E_EPOCH) == A2E_EPOCH_SHA)
        gate("A2E_epoch_file_SHA_exact", sha(a2ep) == A2E_EPOCH_SHA)

        a6ed = drive / A6E_REL
        a6em = manifest(a6ed, A6E_MANIFEST)
        a6ep = a6ed / A6E_STATE
        gate("A6E_state_manifest_SHA_exact", a6em.get(A6E_STATE) == A6E_SHA)
        gate("A6E_state_file_SHA_exact", sha(a6ep) == A6E_SHA)

        stage = "source_module_binding"
        r25 = load_module(root / R25R3, "p3r1_r25")
        a2e = load_module(root / A2E, "p3r1_a2e")
        r2 = load_module(root / R2SRC, "p3r1_r2")
        e37a = load_module(root / E37A, "p3r1_e37a")
        e36 = load_module(root / E36, "p3r1_e36")
        sg2 = load_module(root / SG2, "p3r1_sg2")
        sg3 = load_module(root / SG3, "p3r1_sg3")
        sg4 = load_module(root / SG4, "p3r1_sg4")
        sg5 = load_module(root / SG5, "p3r1_sg5")
        sg6 = load_module(root / SG6, "p3r1_sg6")
        sg7a = load_module(root / SG7A, "p3r1_sg7a")
        sg7d = load_module(root / SG7D, "p3r1_sg7d")
        r3r2r1 = load_module(root / R3R2R1, "p3r1_r3r2r1")

        with np.load(a2ep, allow_pickle=False) as z:
            grid_mass = np.asarray(z["parent_component_mass_kg"], dtype=np.float64)
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            a2e_reconciled_sat = np.asarray(z["reconciled_saturation"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)
            producer_labels = np.asarray(z["producer_labels"]).astype("U32")

        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
            nw = np.asarray(z["nw"], dtype=np.float64)
            no = np.asarray(z["no"], dtype=np.float64)
            krw_max = np.asarray(z["krw_max"], dtype=np.float64)
            kro_max = np.asarray(z["kro_max"], dtype=np.float64)

        gate("Day365_grid_mass_shape", grid_mass.shape == GRID)
        gate("Day365_pressure_shape", frozen_pressure.shape == GRID)
        gate("Day365_geometry_shape",
             xyz.shape == (NSL, NN, 3)
             and tof_s.shape == (NSL, NN)
             and weights_m3_s.shape == (NSL,)
             and tau_end_s.shape == (NSL,))
        gate("heterogeneous_fields_shape",
             all(a.shape == GRID for a in [phi, nw, no, krw_max, kro_max]))

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        permeability_md = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")

        # Reference transmissibilities for every P3 diagnostic pressure solve.
        kx, ky, kz = sg2.build_directional_permeability(permeability_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        op = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weights_m3_s * DAY_TO_S,
        )
        geometry = e37a.build_control_volume_geometry(
            r2, op, frozen_pressure, p_ref, NSL, NCV
        )
        xi_faces = np.linspace(0.0, 1.0, NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S

        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        dxi = 1.0 / NCV
        dtD_cfl = float(sg7a.CFL * dxi / (float(np.max(u_face)) * max_df + float(sg7a.EPS)))
        nominal_cfl_dt_days = float(dtD_cfl * np.min(tau_end_s / DAY_TO_S))
        gate("nominal_CFL_dt_positive",
             np.isfinite(nominal_cfl_dt_days) and nominal_cfl_dt_days > 0.0,
             nominal_cfl_dt_days)

        # --------------------------------------------------------------------------------------
        # Day365 capacity-limited split-state initialization.
        # --------------------------------------------------------------------------------------
        stage = "Day365_split_state_initialization"
        science_started = True

        exact_cv, exact_cell, target = r25.build_edge_target_and_support(grid_mass, op)

        cv_capacity = np.asarray(
            e37a.cv_mass_from_saturation(
                r2,
                np.full((NSL, NCV), MAX_SAT, dtype=np.float64),
                geometry["cv_pressure_mass_coeff"],
            ),
            dtype=np.float64,
        )
        st1 = r25.stage1_max_representable(
            grid_mass, cv_capacity, exact_cv, exact_cell
        )
        st2 = r25.stage2_min_l1_to_target(
            grid_mass,
            cv_capacity,
            exact_cv,
            exact_cell,
            target,
            float(st1["represented_mass_kg"]),
        )
        exact_mass = np.asarray(st2["x"], dtype=np.float64)
        assigned_cv = np.bincount(exact_cv, weights=exact_mass, minlength=NCVT).reshape(NSL, NCV)
        represented = np.bincount(exact_cell, weights=exact_mass, minlength=NCELL).reshape(GRID)
        residual = grid_mass - represented
        residual[np.abs(residual) < 1.0e-12] = 0.0
        sci_gate("Day365_residual_nonnegative", float(np.min(residual)) >= -MASS_TOL, float(np.min(residual)))
        sci_gate("Day365_split_ledger",
                 abs(float(np.sum(assigned_cv) + np.sum(residual) - np.sum(grid_mass))) <= MASS_TOL,
                 float(np.sum(assigned_cv) + np.sum(residual) - np.sum(grid_mass)))

        cv_sat = np.asarray(
            e37a.invert_cv_mass_to_saturation(r2, assigned_cv, geometry["cv_pressure_mass_coeff"]),
            dtype=np.float64,
        )
        sci_gate("Day365_CV_saturation_bounds",
                 float(np.min(cv_sat)) >= BACKGROUND - SAT_TOL
                 and float(np.max(cv_sat)) <= MAX_SAT + SAT_TOL,
                 [float(np.min(cv_sat)), float(np.max(cv_sat))])

        edge_cv, edge_cell, shell, exact_pos = build_xy1_support(exact_cv, exact_cell)
        edge_mass = np.zeros(len(edge_cv), dtype=np.float64)
        edge_mass[exact_pos] = exact_mass

        initial_cv_check = np.bincount(edge_cv, weights=edge_mass, minlength=NCVT).reshape(NSL, NCV)
        sci_gate("Day365_XY1_CV_equalities",
                 float(np.max(np.abs(initial_cv_check - assigned_cv))) <= MASS_TOL,
                 float(np.max(np.abs(initial_cv_check - assigned_cv))))
        represented_xy1 = np.bincount(edge_cell, weights=edge_mass, minlength=NCELL).reshape(GRID)
        sci_gate("Day365_XY1_representation_exact",
                 float(np.max(np.abs(represented_xy1 - represented))) <= MASS_TOL,
                 float(np.max(np.abs(represented_xy1 - represented))))

        # Map every subsegment to its exact-support edge.
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_key = sub_cv * NCELL + sub_cell
        exact_keys = exact_cv * NCELL + exact_cell
        key_to_exact = {int(k): i for i, k in enumerate(exact_keys.tolist())}
        sub_exact_idx = np.asarray([key_to_exact[int(k)] for k in sub_key.tolist()], dtype=np.int64)

        cart_sg = np.asarray(
            a2e.invert_local_mass(r2, grid_mass, frozen_pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        cart_sat = float(a2e.BACKGROUND) + cart_sg
        sci_gate("Day365_cartesian_saturation_bounds",
                 float(np.min(cart_sat)) >= BACKGROUND - SAT_TOL
                 and float(np.max(cart_sat)) <= MAX_SAT + SAT_TOL)
        sci_gate("Day365_saturation_reproduces_A2E",
                 float(np.max(np.abs(cart_sat - a2e_reconciled_sat))) <= 1.0e-10,
                 float(np.max(np.abs(cart_sat - a2e_reconciled_sat))))

        current_grid_mass = grid_mass.copy()
        current_rep = represented.copy()
        current_residual = residual.copy()
        current_cv_mass = assigned_cv.copy()
        current_cv_sat = cv_sat.copy()
        current_edge_mass = edge_mass.copy()
        current_cart_sat = cart_sat.copy()
        cumulative_injected = 0.0
        cumulative_produced = 0.0

        staging.mkdir(parents=True, exist_ok=False)
        dense_rows: list[dict[str, Any]] = []
        atomic_rows: list[dict[str, Any]] = []
        diag_rows: list[dict[str, Any]] = []
        producer_rows_all: list[dict[str, Any]] = []
        rep_rows: list[dict[str, Any]] = []

        # P0/P3 diagnostic: saturation-conditioned one-shot flow refresh only.
        def run_exact_diagnostic(day: float) -> tuple[dict[str, Any], dict[str, Any]]:
            t0 = time.perf_counter()

            t_pressure0 = time.perf_counter()
            mobility = a2e.spatial_mobility(
                current_cart_sat, nw, no, krw_max, kro_max
            )
            tx, ty, tz, _face_mobility = r3r2r1.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, producer_wi = r3r2r1.assemble_updated_pressure_system(
                sg3, permeability_md, tx, ty, tz, mobility["lambda_total"]
            )
            _ppa, diag_pressure, linear_residual = r3r2r1.solve_updated_pressure(
                sg3, A, b
            )
            diag_pressure = np.asarray(diag_pressure, dtype=np.float64)
            pressure_refresh_s = time.perf_counter() - t_pressure0
            if float(linear_residual) >= float(a2e.PRESSURE_LINEAR_REL_RESIDUAL_MAX):
                raise ScientificFail(
                    f"diagnostic_day_{day}_pressure_linear_residual",
                    linear_residual,
                )

            t_darcy0 = time.perf_counter()
            producer_rates, producer_sink = r3r2r1.producer_rates_updated(
                sg3, diag_pressure, producer_wi
            )
            qx, qy, qz = sg4.compute_face_fluxes(diag_pressure, tx, ty, tz)
            conservation = r3r2r1.flow_conservation_metrics(
                sg3, sg4, qx, qy, qz, producer_sink
            )
            if conservation["local_relative_l2_error"] >= float(a2e.FLOW_LOCAL_REL_L2_MAX):
                raise ScientificFail(
                    f"diagnostic_day_{day}_Darcy_local_conservation",
                    conservation["local_relative_l2_error"],
                )
            if conservation["global_relative_mismatch"] >= float(a2e.FLOW_GLOBAL_REL_MISMATCH_MAX):
                raise ScientificFail(
                    f"diagnostic_day_{day}_Darcy_global_conservation",
                    conservation["global_relative_mismatch"],
                )
            darcy_s = time.perf_counter() - t_darcy0

            t_pollock0 = time.perf_counter()
            vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
            faces, seeds = sg5.build_seeds(qx, qy, qz)
            streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)
            sg5_validation = sg5.validate_streamlines(faces, seeds, streamlines)
            statuses = [str(s["status"]) for s in streamlines]
            if not streamlines or not all(x == "PRODUCER" for x in statuses):
                raise ScientificFail(
                    f"diagnostic_day_{day}_Pollock_terminal_status",
                    {x: statuses.count(x) for x in sorted(set(statuses))},
                )
            pollock_s = time.perf_counter() - t_pollock0

            t_tof0 = time.perf_counter()
            sg6_streamlines = a2e.convert_sg5_to_sg6(streamlines)
            transport_db = sg6.build_transport_database(sg6_streamlines)
            sg6.validate_transport(transport_db)
            dxyz = np.asarray(transport_db["xyz_m"], dtype=np.float64)
            dtof = np.asarray(transport_db["tau_s"], dtype=np.float64)
            dweights = np.asarray(transport_db["weights_m3_s"], dtype=np.float64)
            dtau_end = np.asarray(transport_db["tau_end_s"], dtype=np.float64)
            dlabels = np.asarray(transport_db["producer"]).astype("U32")
            dxi_nodes = np.asarray(transport_db["xi"], dtype=np.float64)
            tof_elapsed = time.perf_counter() - t_tof0

            total = time.perf_counter() - t0
            arrays = {
                "diagnostic_day": np.asarray(day, dtype=np.float64),
                "saturation": np.asarray(current_cart_sat, dtype=np.float64),
                "lambda_total": np.asarray(mobility["lambda_total"], dtype=np.float64),
                "pressure_psi": diag_pressure,
                "Qx": np.asarray(qx, dtype=np.float64),
                "Qy": np.asarray(qy, dtype=np.float64),
                "Qz": np.asarray(qz, dtype=np.float64),
                "streamline_xyz_m": dxyz,
                "streamline_tof_s": dtof,
                "streamline_weight_m3_s": dweights,
                "tau_end_s": dtau_end,
                "producer_labels": dlabels,
                "xi": dxi_nodes,
                "diagnostic_is_same_time_fixed_point": np.asarray(False),
                "diagnostic_transport_feedback": np.asarray(False),
            }
            pressure_vs_day365 = float(
                np.linalg.norm((diag_pressure - frozen_pressure).ravel())
                / max(float(np.linalg.norm(frozen_pressure.ravel())), 1.0e-30)
            )
            metrics = {
                "diagnostic_day": day,
                "pressure_linear_relative_residual": float(linear_residual),
                "pressure_refresh_s": pressure_refresh_s,
                "Darcy_s": darcy_s,
                "Pollock_s": pollock_s,
                "TOF_s": tof_elapsed,
                "total_refresh_s": total,
                "pressure_relative_L2_vs_Day365": pressure_vs_day365,
                "pressure_min_psi": float(np.min(diag_pressure)),
                "pressure_max_psi": float(np.max(diag_pressure)),
                "flow_local_relative_L2_error": float(conservation["local_relative_l2_error"]),
                "flow_global_relative_mismatch": float(conservation["global_relative_mismatch"]),
                "streamline_count": int(dxyz.shape[0]),
                "nodes_per_streamline": int(dxyz.shape[1]),
                "tau_end_min_days": float(np.min(dtau_end) / DAY_TO_S),
                "tau_end_median_days": float(np.median(dtau_end) / DAY_TO_S),
                "tau_end_max_days": float(np.max(dtau_end) / DAY_TO_S),
                "diagnostic_same_time_fixed_point_executed": False,
                "diagnostic_transport_feedback_executed": False,
            }
            return arrays, metrics

        def write_observation(day: float, obs_index: int) -> None:
            nonlocal current_observation_index
            current_observation_index = obs_index

            restart_arrays = {
                "physical_day": np.asarray(day, dtype=np.float64),
                "cartesian_component_mass_kg": current_grid_mass,
                "represented_cartesian_cell_mass_kg": current_rep,
                "grid_residual_component_mass_kg": current_residual,
                "cartesian_saturation": current_cart_sat,
                "transport_CV_component_mass_kg": current_cv_mass,
                "transport_CV_saturation": current_cv_sat,
                "frozen_flow_epoch_day": np.asarray(START_DAY, dtype=np.float64),
                "streamline_xyz_m": xyz,
                "streamline_tof_s": tof_s,
                "streamline_weight_m3_s": weights_m3_s,
                "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
                "cumulative_injected_component_mass_kg": np.asarray(cumulative_injected, dtype=np.float64),
                "cumulative_produced_component_mass_kg": np.asarray(cumulative_produced, dtype=np.float64),
                "XY1_edge_cv": edge_cv,
                "XY1_edge_cell": edge_cell,
                "XY1_edge_shell_cost": shell,
                "XY1_edge_assigned_mass_kg": current_edge_mass,
            }
            validate_restart(restart_arrays, day)

            state_name = f"{OUT_TOKEN}_Day{int(round(day)):04d}_Accepted_Dense_State.npz"
            state_sha = save_npz(staging / state_name, restart_arrays)

            diag_arrays, metrics = run_exact_diagnostic(day)
            diag_name = f"{OUT_TOKEN}_Day{int(round(day)):04d}_Exact_Flow_Diagnostic.npz"
            diag_sha = save_npz(staging / diag_name, diag_arrays)

            split_err = float(np.max(np.abs(current_grid_mass - current_rep - current_residual)))
            cv_edge = np.bincount(edge_cv, weights=current_edge_mass, minlength=NCVT).reshape(NSL, NCV)
            cv_err = float(np.max(np.abs(cv_edge - current_cv_mass)))
            mass_total = float(np.sum(current_grid_mass))
            ledger_expected = float(np.sum(grid_mass)) + cumulative_injected - cumulative_produced
            ledger_resid = mass_total - ledger_expected

            sci_gate(f"obs_{int(day)}_split_identity", split_err <= MASS_TOL, split_err)
            sci_gate(f"obs_{int(day)}_CV_edge_equality", cv_err <= MASS_TOL, cv_err)
            sci_gate(
                f"obs_{int(day)}_global_source_sink",
                abs(ledger_resid) <= max(MASS_TOL, REL_TOL * max(abs(ledger_expected), 1.0)),
                ledger_resid,
            )
            if day == START_DAY:
                sci_gate(
                    "Day365_diagnostic_pressure_reproduces_A2E",
                    metrics["pressure_relative_L2_vs_Day365"] <= 1.0e-10,
                    metrics["pressure_relative_L2_vs_Day365"],
                )

            dense_rows.append({
                "observation_index": obs_index,
                "day": day,
                "state_file": state_name,
                "state_sha256": state_sha,
                "diagnostic_file": diag_name,
                "diagnostic_sha256": diag_sha,
                "cartesian_total_mass_kg": mass_total,
                "represented_total_mass_kg": float(np.sum(current_rep)),
                "residual_total_mass_kg": float(np.sum(current_residual)),
                "transport_CV_total_mass_kg": float(np.sum(current_cv_mass)),
                "cumulative_injected_kg": cumulative_injected,
                "cumulative_produced_kg": cumulative_produced,
                "global_source_sink_residual_kg": ledger_resid,
                "split_identity_max_abs_error_kg": split_err,
                "CV_edge_equality_max_abs_error_kg": cv_err,
                "saturation_min": float(np.min(current_cart_sat)),
                "saturation_max": float(np.max(current_cart_sat)),
            })
            diag_rows.append(metrics)
            print(
                f"[OBS PASS] day={day:.0f} | mass={mass_total:.6f} kg | "
                f"diag={metrics['total_refresh_s']:.3f}s | streamlines={metrics['streamline_count']}"
            )

        write_observation(START_DAY, 0)

        # --------------------------------------------------------------------------------------
        # Common frozen-Day365 transport trajectory.
        # --------------------------------------------------------------------------------------
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)
        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)

        for obs_index, target_day in enumerate(OBS_DAYS[1:], start=1):
            target_day = float(target_day)
            while current_time < target_day - 1.0e-12:
                remaining = target_day - current_time
                nominal = min(nominal_cfl_dt_days, remaining)
                if nominal <= 0.0:
                    raise ScientificFail("nonpositive_nominal_dt", [current_time, target_day, nominal])

                accepted = False
                rejection_reasons: list[str] = []
                for retry in range(MAX_RETRIES + 1):
                    dt = nominal * (RETRY_FACTOR ** retry)
                    trial_start = time.perf_counter()
                    try:
                        old_cv_mass = current_cv_mass
                        old_cv_sat = current_cv_sat
                        old_edge_mass = current_edge_mass
                        old_rep = current_rep
                        old_grid = current_grid_mass

                        # R31 theory-flux law.
                        theory_flux = np.zeros((NSL, NCV + 1), dtype=np.float64)
                        theory_flux[:, 0] = weights_m3_day * rho_ref
                        ff_internal = np.asarray(
                            sg7a.fractional_flow(old_cv_sat[:, :-1]), dtype=np.float64
                        )
                        theory_flux[:, 1:-1] = (
                            weights_m3_day[:, None]
                            * u_face[None, 1:-1]
                            * ff_internal
                            * rho_ref
                        )
                        ff_out = np.asarray(
                            sg7a.fractional_flow(old_cv_sat[:, -1]), dtype=np.float64
                        )
                        theory_flux[:, -1] = (
                            weights_m3_day * float(u_face[-1]) * ff_out * rho_ref
                        )

                        new_cv_mass = old_cv_mass + dt * (
                            theory_flux[:, :-1] - theory_flux[:, 1:]
                        )
                        cv_cap_tol = max(
                            1.0e-9,
                            1.0e-12 * max(float(np.max(np.abs(new_cv_mass))), 1.0),
                        )
                        if float(np.min(new_cv_mass)) < -MASS_TOL:
                            raise TrialReject(f"CV_negative:{float(np.min(new_cv_mass))}")
                        if float(np.max(new_cv_mass - cv_capacity)) > cv_cap_tol:
                            raise TrialReject(
                                f"CV_capacity:{float(np.max(new_cv_mass-cv_capacity))}:{cv_cap_tol}"
                            )

                        new_cv_sat = np.asarray(
                            e37a.invert_cv_mass_to_saturation(
                                r2, new_cv_mass, geometry["cv_pressure_mass_coeff"]
                            ),
                            dtype=np.float64,
                        )
                        if (
                            float(np.min(new_cv_sat)) < BACKGROUND - SAT_TOL
                            or float(np.max(new_cv_sat)) > MAX_SAT + SAT_TOL
                        ):
                            raise TrialReject("CV_saturation_bounds")

                        injected = float(np.sum(theory_flux[:, 0]) * dt)
                        produced = float(np.sum(theory_flux[:, -1]) * dt)
                        cv_delta = float(np.sum(new_cv_mass) - np.sum(old_cv_mass))
                        cv_source_sink = cv_delta - injected + produced
                        if abs(cv_source_sink) > max(MASS_TOL, REL_TOL * max(abs(injected), 1.0)):
                            raise TrialReject(f"CV_source_sink:{cv_source_sink}")

                        old_sub_sat = old_cv_sat.reshape(-1)[geom_cv_id]
                        new_sub_sat = new_cv_sat.reshape(-1)[geom_cv_id]
                        old_sub_sg = np.clip(old_sub_sat - BACKGROUND, 0.0, MAX_SG)
                        new_sub_sg = np.clip(new_sub_sat - BACKGROUND, 0.0, MAX_SG)
                        rho_old = np.asarray(
                            r2.gas_density_from_state(old_sub_sat, pseg, p_ref),
                            dtype=np.float64,
                        )
                        rho_new = np.asarray(
                            r2.gas_density_from_state(new_sub_sat, pseg, p_ref),
                            dtype=np.float64,
                        )
                        sub_delta = sub_pv * (
                            rho_new * new_sub_sg - rho_old * old_sub_sg
                        )
                        if abs(float(np.sum(sub_delta)) - cv_delta) > MASS_TOL:
                            raise TrialReject(
                                f"CV_to_subsegment_delta:{float(np.sum(sub_delta))-cv_delta}"
                            )
                        delta_grid = np.bincount(
                            flat_cell, weights=sub_delta, minlength=NCELL
                        ).reshape(GRID)
                        if abs(float(np.sum(delta_grid)) - float(np.sum(sub_delta))) > MASS_TOL:
                            raise TrialReject("subsegment_to_grid_delta")

                        direct_target_rep = old_rep + delta_grid
                        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
                        cart_capacity = np.asarray(
                            a2e.local_mass(r2, full_sat, frozen_pressure, p_ref, hetero_pv),
                            dtype=np.float64,
                        )
                        rep_capacity = cart_capacity - current_residual
                        cart_cap_tol = max(
                            1.0e-8,
                            1.0e-12 * max(float(np.max(cart_capacity)), 1.0),
                        )
                        if float(np.min(rep_capacity)) < -cart_cap_tol:
                            raise TrialReject("represented_capacity_negative")
                        rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)

                        # Edge-wise exact conservative update. If any representation
                        # hard gate fails, invoke the frozen XY1 lexicographic repair.
                        edge_delta_exact = np.bincount(
                            sub_exact_idx, weights=sub_delta, minlength=len(exact_cv)
                        )
                        candidate_edge = old_edge_mass.copy()
                        candidate_edge[exact_pos] += edge_delta_exact
                        direct_mode = float(np.min(candidate_edge)) >= -MASS_TOL

                        if direct_mode:
                            cv_from_edge = np.bincount(
                                edge_cv, weights=candidate_edge, minlength=NCVT
                            ).reshape(NSL, NCV)
                            cell_from_edge = np.bincount(
                                edge_cell, weights=candidate_edge, minlength=NCELL
                            ).reshape(GRID)
                            cv_err = float(np.max(np.abs(cv_from_edge - new_cv_mass)))
                            cap_excess_rep = float(
                                np.max(cell_from_edge.reshape(-1) - rep_capacity_flat)
                            )
                            direct_l1 = float(np.sum(np.abs(cell_from_edge - direct_target_rep)))
                            if (
                                cv_err > MASS_TOL
                                or cap_excess_rep > cart_cap_tol
                                or direct_l1 > max(
                                    1.0e-5,
                                    1.0e-10 * max(float(np.sum(np.abs(direct_target_rep))), 1.0),
                                )
                            ):
                                direct_mode = False

                        if direct_mode:
                            new_edge_mass = candidate_edge
                            new_rep = np.bincount(
                                edge_cell, weights=new_edge_mass, minlength=NCELL
                            ).reshape(GRID)
                            rep_info = {
                                "mode": "DIRECT_EDGE_EXACT",
                                "stage1_terminal_mass_kg": float(np.sum(new_edge_mass[shell > 0])),
                                "stage2_terminal_mass_kg": float(np.sum(new_edge_mass[shell > 0])),
                                "stage2_cell_L1_kg": float(np.sum(np.abs(new_rep - direct_target_rep))),
                                "CV_equality_max_abs_error_kg": float(
                                    np.max(
                                        np.abs(
                                            np.bincount(
                                                edge_cv, weights=new_edge_mass, minlength=NCVT
                                            ).reshape(NSL, NCV)
                                            - new_cv_mass
                                        )
                                    )
                                ),
                            }
                        else:
                            new_edge_mass, rep_info = support_repair(
                                edge_cv=edge_cv,
                                edge_cell=edge_cell,
                                shell=shell,
                                new_cv_mass=new_cv_mass,
                                rep_capacity_flat=rep_capacity_flat,
                                direct_target_rep=direct_target_rep,
                            )
                            representation_repairs += 1
                            new_rep = np.bincount(
                                edge_cell, weights=new_edge_mass, minlength=NCELL
                            ).reshape(GRID)

                        candidate_grid = new_rep + current_residual
                        cap_excess = float(np.max(candidate_grid - cart_capacity))
                        if cap_excess > cart_cap_tol:
                            raise TrialReject(f"cartesian_capacity:{cap_excess}:{cart_cap_tol}")
                        if float(np.min(new_rep)) < -MASS_TOL:
                            raise TrialReject("represented_negative")
                        if float(np.min(candidate_grid)) < -MASS_TOL:
                            raise TrialReject("cartesian_negative")

                        cand_sg = np.asarray(
                            a2e.invert_local_mass(
                                r2, candidate_grid, frozen_pressure, p_ref, hetero_pv
                            ),
                            dtype=np.float64,
                        )
                        cand_sat = float(a2e.BACKGROUND) + cand_sg
                        if (
                            float(np.min(cand_sat)) < BACKGROUND - SAT_TOL
                            or float(np.max(cand_sat)) > MAX_SAT + SAT_TOL
                        ):
                            raise TrialReject("cartesian_saturation_bounds")
                        recon = np.asarray(
                            a2e.local_mass(
                                r2, cand_sat, frozen_pressure, p_ref, hetero_pv
                            ),
                            dtype=np.float64,
                        )
                        recon_err = float(np.max(np.abs(recon - candidate_grid)))
                        if recon_err > 1.0e-8:
                            raise TrialReject(f"EOS_reconstruction:{recon_err}")

                        expected_total = float(np.sum(old_grid)) + injected - produced
                        source_sink = float(np.sum(candidate_grid)) - expected_total
                        global_tol = max(
                            MASS_TOL, REL_TOL * max(abs(expected_total), 1.0)
                        )
                        if abs(source_sink) > global_tol:
                            raise TrialReject(
                                f"cartesian_source_sink:{source_sink}:{global_tol}"
                            )

                        trial_time = current_time + dt
                        restart_minimal = {
                            "physical_day": np.asarray(trial_time, dtype=np.float64),
                            "cartesian_component_mass_kg": candidate_grid,
                            "represented_cartesian_cell_mass_kg": new_rep,
                            "grid_residual_component_mass_kg": current_residual,
                            "cartesian_saturation": cand_sat,
                            "transport_CV_component_mass_kg": new_cv_mass,
                            "transport_CV_saturation": new_cv_sat,
                        }
                        validate_restart(restart_minimal, trial_time)

                        # Atomic commit.
                        current_grid_mass = candidate_grid
                        current_rep = new_rep
                        current_cv_mass = new_cv_mass
                        current_cv_sat = new_cv_sat
                        current_edge_mass = new_edge_mass
                        current_cart_sat = cand_sat
                        cumulative_injected += injected
                        cumulative_produced += produced
                        current_time = trial_time
                        accepted_atomic_steps += 1

                        prod_rows, aggregate_cut = e37a.producer_rows_from_flux(
                            producer_labels,
                            weights_m3_day,
                            ff_out,
                            theory_flux[:, -1],
                            dt,
                        )
                        for row in prod_rows:
                            producer_rows_all.append({
                                "accepted_step": accepted_atomic_steps,
                                "parent_day": current_time - dt,
                                "accepted_day": current_time,
                                "dt_days": dt,
                                **row,
                            })

                        atomic_rows.append({
                            "accepted_step": accepted_atomic_steps,
                            "parent_day": current_time - dt,
                            "accepted_day": current_time,
                            "target_observation_day": target_day,
                            "accepted_dt_days": dt,
                            "nominal_dt_days": nominal,
                            "retry_count": retry,
                            "representation_mode": rep_info["mode"],
                            "injected_component_mass_kg": injected,
                            "produced_component_mass_kg": produced,
                            "CV_component_mass_delta_kg": cv_delta,
                            "CV_source_sink_residual_kg": cv_source_sink,
                            "cartesian_source_sink_residual_kg": source_sink,
                            "cartesian_capacity_excess_kg": cap_excess,
                            "cartesian_EOS_reconstruction_max_error_kg": recon_err,
                            "stage1_terminal_mass_kg": rep_info["stage1_terminal_mass_kg"],
                            "stage2_terminal_mass_kg": rep_info["stage2_terminal_mass_kg"],
                            "stage2_cell_L1_kg": rep_info["stage2_cell_L1_kg"],
                            "CV_equality_max_abs_error_kg": rep_info["CV_equality_max_abs_error_kg"],
                            "aggregate_producer_CO2_cut": aggregate_cut,
                            "trial_wall_seconds": time.perf_counter() - trial_start,
                        })
                        rep_rows.append({
                            "accepted_step": accepted_atomic_steps,
                            "accepted_day": current_time,
                            **rep_info,
                        })
                        accepted = True
                        if accepted_atomic_steps % 100 == 0 or abs(current_time - target_day) <= 1e-12:
                            print(
                                f"[STEP {accepted_atomic_steps}] t={current_time:.9f} d "
                                f"dt={dt:.9f} retry={retry} rep={rep_info['mode']}"
                            )
                        break

                    except TrialReject as exc:
                        rejection_reasons.append(repr(exc))
                        print(
                            f"[REJECT] t={current_time:.9f} target={target_day:.1f} "
                            f"retry={retry} dt={dt:.9g}: {exc}"
                        )
                        if retry >= MAX_RETRIES:
                            raise ScientificFail(
                                "atomic_retry_budget_exhausted",
                                {
                                    "current_time": current_time,
                                    "target_observation_day": target_day,
                                    "nominal_dt_days": nominal,
                                    "last_trial_dt_days": dt,
                                    "rejections": rejection_reasons,
                                },
                            )

                if not accepted:
                    raise ScientificFail(
                        "atomic_step_not_accepted",
                        [current_time, target_day],
                    )

            if abs(current_time - target_day) > 1.0e-10:
                raise ScientificFail(
                    "observation_day_not_hit_exactly",
                    [current_time, target_day],
                )
            write_observation(target_day, obs_index)

        stage = "full_sweep_closure"
        gate("all_28_dense_states_written", len(dense_rows) == 28, len(dense_rows))
        gate("all_28_diagnostics_written", len(diag_rows) == 28, len(diag_rows))
        gate("final_day_exact", abs(current_time - END_DAY) <= 1.0e-10, current_time)
        gate("diagnostic_fixedpoint_never_executed",
             all(row["diagnostic_same_time_fixed_point_executed"] is False for row in diag_rows))
        gate("diagnostic_feedback_never_executed",
             all(row["diagnostic_transport_feedback_executed"] is False for row in diag_rows))
        gate("cadence_not_selected", True)
        gate("P4_not_executed", True)
        gate("ML_not_executed", True)

        (staging / DENSE_AUDIT).write_bytes(csvb(dense_rows))
        (staging / ATOMIC_AUDIT).write_bytes(csvb(atomic_rows))
        (staging / DIAG_METRICS).write_bytes(csvb(diag_rows))
        (staging / PRODUCER_AUDIT).write_bytes(csvb(producer_rows_all))
        (staging / REPRESENTATION_AUDIT).write_bytes(csvb(rep_rows))
        (staging / GATES).write_bytes(csvb(gates))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": (
                "AV4_COMMON_FROZEN_DAY365_TRANSPORT_TRAJECTORY_AND_28_SATURATION_CONDITIONED_"
                "EXACT_FLOW_DIAGNOSTICS_CERTIFIED_P4_FROZEN_VS_50DAY_VS_5DAY_COMPARISON_AUTHORIZED"
            ),
            "repository_parent": PARENT,
            "A2E_Day365_flow_epoch_sha256": A2E_EPOCH_SHA,
            "R32_authoritative_state_sha256": R32_STATE_SHA,
            "A6E_state_sha256": A6E_SHA,
            "observation_count": 28,
            "observation_start_day": START_DAY,
            "observation_end_day": END_DAY,
            "observation_spacing_days": 5.0,
            "accepted_atomic_step_count": accepted_atomic_steps,
            "nominal_CFL_dt_days": nominal_cfl_dt_days,
            "representation_repair_count": representation_repairs,
            "final_cartesian_component_mass_kg": float(np.sum(current_grid_mass)),
            "cumulative_injected_component_mass_kg": cumulative_injected,
            "cumulative_produced_component_mass_kg": cumulative_produced,
            "final_global_source_sink_residual_kg": (
                float(np.sum(current_grid_mass))
                - (float(np.sum(grid_mass)) + cumulative_injected - cumulative_produced)
            ),
            "common_transport_flow_epoch_day": START_DAY,
            "diagnostic_refresh_pipeline": "S(t)->mobility->single exact pressure solve->Darcy->Pollock->TOF",
            "diagnostic_same_time_fixed_point_executed": False,
            "diagnostic_refresh_feedback_to_transport": False,
            "exact_flow_diagnostic_count": len(diag_rows),
            "candidate_cadences_days": CANDIDATE_CADENCES,
            "policy_set": POLICIES,
            "periodic_cadence_selected_now": False,
            "P4_authorized": True,
            "P4_execution_authorized": True,
            "P5_authorized": False,
            "ML_execution_executed": False,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "P3_R1_complete": True,
            "P4_authorized": True,
            "P4_execution_authorized": True,
            "P4_name": "Frozen Flow vs 50-Day vs 5-Day Refresh Accuracy-Cost Comparison",
            "P4_must_bind_all_28_dense_states": True,
            "P4_must_bind_all_28_exact_flow_diagnostics": True,
            "P4_must_use_policy_set": POLICIES,
            "P4_must_use_candidate_cadences_days": CANDIDATE_CADENCES,
            "P4_must_not_recompute_common_transport_trajectory": True,
            "P4_must_not_select_by_arbitrary_new_threshold": True,
            "P4_diagnostic_reference_is_saturation_conditioned_exact_flow": True,
            "same_time_fixed_point_claim_authorized": False,
            "periodic_cadence_selected_now": False,
            "P5_authorized": False,
            "production_cadence_change_authorized": False,
            "ML_execution_authorized": False,
        }
        (staging / SUMMARY).write_bytes(jb(summary))
        (staging / DECISION).write_bytes(jb(decision))

        rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (staging / MANIFEST).write_bytes(csvb(rows))

        if out.exists():
            raise GateError("final_output_directory_preexists")
        staging.rename(out)

        print()
        print("=" * 220)
        print(M, "PASS")
        print("Dense accepted states                   :", len(dense_rows))
        print("Exact saturation-conditioned diagnostics:", len(diag_rows))
        print("Accepted atomic transport steps         :", accepted_atomic_steps)
        print("XY1 lexicographic representation repairs:", representation_repairs)
        print("Nominal CFL dt days                     :", nominal_cfl_dt_days)
        print("Final day                               :", current_time)
        print("Final source/sink residual kg           :", summary["final_global_source_sink_residual_kg"])
        print("Same-time fixed-point diagnostics       : False")
        print("Cadence selected                        : False")
        print("P4 comparison authorized                : True")
        print("=" * 220)
        return 0

    except ScientificFail as exc:
        if staging.exists():
            shutil.rmtree(staging)
        fail_dir.mkdir(parents=True, exist_ok=True)
        p = fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": SCI_FAIL,
                "failed_stage": stage,
                "failed_gate": exc.gate,
                "detail": exc.detail,
                "science_started": science_started,
                "current_physical_day": current_time,
                "last_completed_observation_index": current_observation_index,
                "accepted_atomic_step_count": accepted_atomic_steps,
                "representation_repair_count": representation_repairs,
                "automatic_physics_change_authorized": False,
                "same_time_fixed_point_diagnostic_authorized": False,
                "cadence_selected": False,
                "P4_authorized": False,
                "ML_execution_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "SCIENTIFIC FAIL")
        print("Stage:", stage)
        print("Gate:", exc.gate)
        print("Detail:", repr(exc.detail))
        return 3

    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging)
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "science_started": science_started,
                "current_physical_day": current_time,
                "last_completed_observation_index": current_observation_index,
                "accepted_atomic_step_count": accepted_atomic_steps,
                "representation_repair_count": representation_repairs,
                "same_time_fixed_point_diagnostic_authorized": False,
                "cadence_selected": False,
                "P4_authorized": False,
                "ML_execution_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
