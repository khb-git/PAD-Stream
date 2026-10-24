#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6_COUPLED_PRESSURE_SAME_H2_REASSIGNMENT_"
    "FIXED_POINT_EXECUTION_PASS_CONVERGED_EVENT_STATE_CERTIFIED_"
    "NO_DARCY_POLLOCK_TOF_NO_REPROJECTION_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R6_COUPLED_PRESSURE_SAME_H2_REASSIGNMENT_"
    "FIXED_POINT_SCIENTIFIC_FAIL_NO_DAMPING_NO_SUPPORT_EXPANSION_NO_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3O3R6_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_O3R5_COMMIT = "d12576bdb0937fbf5d605974d7c906834cc34e0b"
EVENT_DAY = 413.78677770818403
GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NCV = 200
NCVTOTAL = NSL * NCV
BACKGROUND = 0.20
INJECTED = 0.80
EXPECTED_E0_PAIRS = 269721
EXPECTED_E2_PAIRS = 3091073
EXPECTED_ACTIVE_EDGES = 3012452

MAX_FIXED_POINT_ITERATIONS = 100
PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_LINF_TOL = 1.0e-10
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8
GLOBAL_MASS_REL_TOL = 1.0e-10

# Repository authorities.
O3R5 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_"
    "Coupled_Pressure_SameH2_Reassignment_Fixed_Point_Semantics_Design_Freeze.py"
)
O3R5_BLOB = "0fa323244439e93cca020a4837c60d88bfbf3480"
O3R5_STATUS = (
    "AV4F4R3R3R3R3R3O3R5_COUPLED_PRESSURE_SAME_H2_REASSIGNMENT_"
    "FIXED_POINT_SEMANTICS_DESIGN_FREEZE_PASS_NO_EXECUTION_NO_STATE_MUTATION_NO_TIME_ADVANCE"
)
O2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution.py"
)
O2_BLOB = "2e04f77750add23f9cfe5143119668450201354f"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2PHYS = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_"
    "Capillary_Split_First_Controlled_Transition.py"
)
R2PHYS_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"
SOURCE_BLOBS = {
    O3R5: O3R5_BLOB,
    O2: O2_BLOB,
    A2E: A2E_BLOB,
    R2PHYS: R2PHYS_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    R3R2R1: R3R2R1_BLOB,
    PERM: PERM_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
O3R5_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_"
      "Coupled_Pressure_SameH2_Fixed_Point_Semantics_Design_Freeze"
)
O3R5_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Summary.json"
O3R5_SEMANTICS = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Coupled_Fixed_Point_Semantics_Contract.json"
O3R5_CONVERGENCE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Convergence_and_Failure_Contract.json"
O3R5_HANDOFF = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_O3R6_Handoff_Contract.json"
O3R5_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Decision_Contract.json"
O3R5_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Final_Gate_Matrix.csv"
O3R5_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Artifact_Manifest.csv"
EXPECTED_O3R5_FILES = {
    O3R5_SUMMARY, O3R5_SEMANTICS, O3R5_CONVERGENCE,
    O3R5_HANDOFF, O3R5_DECISION, O3R5_GATES,
}

O2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
      "Persistent_Native_HiGHS_H2_Assignment_Execution"
)
O2_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz"
O2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Artifact_Manifest.csv"
EXPECTED_O2_FILES = {
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Summary.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimization_Audit.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Stage_Telemetry.csv",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Component_Summary.csv",
    O2_STATE,
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_O3_Handoff_Contract.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Decision_Contract.json",
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Final_Gate_Matrix.csv",
}

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_"
      "Controlled_Coupled_Pressure_SameH2_Fixed_Point_Execution"
)
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_BLOCKED"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def publish_evidence(directory: Path, name: str, data: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    if p.exists() and p.read_bytes() != data:
        digest = hashlib.sha256(data).hexdigest()[:12]
        p = directory / (p.stem + "_" + digest + p.suffix)
    if not p.exists():
        p.write_bytes(data)
    return p


def fsum_array(a: np.ndarray) -> float:
    return float(math.fsum(float(x) for x in np.asarray(a, dtype=np.float64).ravel()))


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=np.float64))))


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(np.linalg.norm((aa - bb).ravel()) / max(float(np.linalg.norm(bb.ravel())), 1.0e-30))


def objective_tol(v: float) -> float:
    return max(1.0e-7, 1.0e-12 * max(abs(float(v)), 1.0))


class PersistentComponentSolver:
    def __init__(self, *, component_id: int, comp: dict[str, Any], model_data: dict[str, Any],
                 highspy, o2, output_flag: bool):
        self.component_id = int(component_id)
        self.comp = comp
        self.md = model_data
        self.highspy = highspy
        self.o2 = o2
        self.h = highspy.Highs()
        self.h.setOptionValue("solver", "simplex")
        self.h.setOptionValue("presolve", "on")
        self.h.setOptionValue("output_flag", bool(output_flag))
        if self.h.passModel(model_data["lp"]) == highspy.HighsStatus.kError:
            raise GateError(f"component_{component_id}_passModel_error")
        self.previous_basis = None
        self.inf = highspy.kHighsInf
        self.n = int(model_data["n"])
        self.m = int(model_data["m"])
        self.ncol = int(model_data["ncol"])
        self.up_idx = np.arange(model_data["up0"], model_data["up0"] + self.m, dtype=np.int32)
        self.uq_idx = np.arange(model_data["uq0"], model_data["uq0"] + self.m, dtype=np.int32)
        self.cell_rows = model_data["ncv"] + np.arange(model_data["ncell"], dtype=np.int32)

    def _reset_iteration(self, available_global: np.ndarray) -> np.ndarray:
        md, o2, hs = self.md, self.o2, self.highspy
        local_available = np.asarray(available_global[self.comp["cell_ids"]], dtype=np.float64)
        o2.set_row_bounds(
            self.h, hs, self.cell_rows,
            np.full(len(self.cell_rows), -self.inf, dtype=np.float64),
            local_available,
        )
        agg_rows = np.asarray([
            md["r_shell"], md["r_extension"], md["r_parent"], md["r_raw"]
        ], dtype=np.int32)
        o2.set_row_bounds(
            self.h, hs, agg_rows,
            np.full(4, -self.inf, dtype=np.float64),
            np.full(4, self.inf, dtype=np.float64),
        )
        if self.m:
            zero = np.zeros(self.m, dtype=np.float64)
            o2.set_col_bounds(self.h, hs, self.up_idx, zero, zero)
            o2.set_col_bounds(self.h, hs, self.uq_idx, zero, zero)
            abs_rows = np.concatenate([
                np.arange(md["r_pp0"], md["r_pp0"] + self.m, dtype=np.int32),
                np.arange(md["r_pm0"], md["r_pm0"] + self.m, dtype=np.int32),
                np.arange(md["r_qp0"], md["r_qp0"] + self.m, dtype=np.int32),
                np.arange(md["r_qm0"], md["r_qm0"] + self.m, dtype=np.int32),
            ])
            o2.set_row_bounds(
                self.h, hs, abs_rows,
                np.full(abs_rows.size, -self.inf, dtype=np.float64),
                np.full(abs_rows.size, self.inf, dtype=np.float64),
            )
        return local_available

    def _solve_stage(self, *, nonlinear_iteration: int, stage_no: int, stage_name: str,
                     cost: np.ndarray, local_available: np.ndarray,
                     cv_tol: float, grid_tol: float) -> tuple[np.ndarray, dict[str, Any]]:
        o2, hs = self.o2, self.highspy
        o2.set_full_costs(self.h, hs, cost)
        warm_requested = self.previous_basis is not None
        warm_applied = False
        warm_status = "not_requested"
        if warm_requested:
            status = self.h.setBasis(self.previous_basis)
            if status == hs.HighsStatus.kError:
                self.h.clearSolver()
                warm_status = "basis_rejected_cold_resolve"
            else:
                warm_applied = True
                warm_status = str(status)
        t0 = time.perf_counter()
        run_status = self.h.run()
        wall = time.perf_counter() - t0
        if run_status == hs.HighsStatus.kError:
            raise GateError(
                f"component_{self.component_id}_iteration_{nonlinear_iteration}_stage_{stage_no}_highs_run_error"
            )
        model_status = self.h.getModelStatus()
        model_text = self.h.modelStatusToString(model_status)
        if model_status != hs.HighsModelStatus.kOptimal:
            if "infeasible" in model_text.lower():
                raise ScientificFail(
                    "frozen_E2_lexicographic_assignment_infeasible",
                    {"iteration": nonlinear_iteration, "component": self.component_id,
                     "stage": stage_no, "stage_name": stage_name, "model_status": model_text},
                )
            raise GateError(
                f"component_{self.component_id}_iteration_{nonlinear_iteration}_stage_{stage_no}_not_optimal:{model_text}"
            )
        sol = np.asarray(list(self.h.getSolution().col_value), dtype=np.float64)
        x = sol[:self.n]
        cv_sum = np.bincount(
            self.comp["cv_inv"], weights=x, minlength=len(self.comp["cv_ids"])
        ).astype(np.float64)
        cell_sum = np.bincount(
            self.comp["cell_inv"], weights=x, minlength=len(self.comp["cell_ids"])
        ).astype(np.float64)
        cv_linf = float(np.max(np.abs(cv_sum - self.comp["demand"]))) if cv_sum.size else 0.0
        cap_excess = float(np.max(cell_sum - local_available)) if cell_sum.size else 0.0
        min_x = float(np.min(x)) if x.size else 0.0
        if cv_linf > cv_tol or cap_excess > grid_tol or min_x < -1.0e-8:
            raise ScientificFail(
                "assignment_stage_primal_certification_failure",
                {"iteration": nonlinear_iteration, "component": self.component_id,
                 "stage": stage_no, "CV_Linf_kg": cv_linf,
                 "max_capacity_excess_kg": cap_excess, "minimum_x_kg": min_x,
                 "CV_tolerance_kg": cv_tol, "capacity_tolerance_kg": grid_tol},
            )
        info = self.h.getInfo()
        obj = float(self.h.getObjectiveValue())
        self.previous_basis = self.h.getBasis()
        telemetry = {
            "nonlinear_iteration": int(nonlinear_iteration),
            "component_id": self.component_id,
            "stage": int(stage_no),
            "stage_name": stage_name,
            "warm_start_requested": bool(warm_requested),
            "warm_start_applied": bool(warm_applied),
            "warm_start_status": warm_status,
            "model_status": model_text,
            "wall_time_s": float(wall),
            "objective": obj,
            "simplex_iterations": int(getattr(info, "simplex_iteration_count", -1)),
            "ipm_iterations": int(getattr(info, "ipm_iteration_count", -1)),
            "CV_equality_Linf_kg": cv_linf,
            "max_capacity_excess_kg": cap_excess,
            "minimum_x_kg": min_x,
        }
        print(
            f"[PASS] iter={nonlinear_iteration:03d} component={self.component_id} "
            f"stage={stage_no} {stage_name} wall={wall:.6f}s obj={obj:.12g} "
            f"CV_Linf={cv_linf:.3e} cap_excess={cap_excess:.3e} warm={warm_applied}"
        )
        sys.stdout.flush()
        return sol, telemetry

    def solve_iteration(self, *, nonlinear_iteration: int, available_global: np.ndarray,
                        cv_tol: float, grid_tol: float) -> dict[str, Any]:
        hs, o2, md = self.highspy, self.o2, self.md
        local_available = self._reset_iteration(available_global)
        telemetry: list[dict[str, Any]] = []

        cost = np.zeros(self.ncol, dtype=np.float64)
        cost[:self.n] = self.comp["is_shell"].astype(np.float64)
        sol1, t = self._solve_stage(
            nonlinear_iteration=nonlinear_iteration, stage_no=1,
            stage_name="MINIMUM_H2_SECOND_SHELL_MASS", cost=cost,
            local_available=local_available, cv_tol=cv_tol, grid_tol=grid_tol,
        )
        telemetry.append(t)
        x1 = sol1[:self.n]
        obj1 = float(np.sum(x1[self.comp["is_shell"]]))
        self.h.changeRowBounds(md["r_shell"], -self.inf, obj1 + objective_tol(obj1))

        cost = np.zeros(self.ncol, dtype=np.float64)
        cost[:self.n] = self.comp["is_extension"].astype(np.float64)
        sol2, t = self._solve_stage(
            nonlinear_iteration=nonlinear_iteration, stage_no=2,
            stage_name="MINIMUM_TOTAL_EXTENSION_MASS", cost=cost,
            local_available=local_available, cv_tol=cv_tol, grid_tol=grid_tol,
        )
        telemetry.append(t)
        x2 = sol2[:self.n]
        obj2 = float(np.sum(x2[self.comp["is_extension"]]))
        self.h.changeRowBounds(md["r_extension"], -self.inf, obj2 + objective_tol(obj2))

        if self.m:
            o2.set_col_bounds(
                self.h, hs, self.up_idx,
                np.zeros(self.m), np.full(self.m, self.inf),
            )
            p_rows = np.concatenate([
                np.arange(md["r_pp0"], md["r_pp0"] + self.m, dtype=np.int32),
                np.arange(md["r_pm0"], md["r_pm0"] + self.m, dtype=np.int32),
            ])
            p_lo = np.full(2 * self.m, -self.inf)
            p_up = np.concatenate([self.comp["target"], -self.comp["target"]])
            o2.set_row_bounds(self.h, hs, p_rows, p_lo, p_up)
        cost = np.zeros(self.ncol, dtype=np.float64)
        if self.m:
            cost[md["up0"]: md["up0"] + self.m] = 1.0
        sol3, t = self._solve_stage(
            nonlinear_iteration=nonlinear_iteration, stage_no=3,
            stage_name="MINIMUM_PARENT_OWNERSHIP_L1", cost=cost,
            local_available=local_available, cv_tol=cv_tol, grid_tol=grid_tol,
        )
        telemetry.append(t)
        up3 = sol3[md["up0"]: md["up0"] + self.m]
        obj3 = float(np.sum(up3))
        self.h.changeRowBounds(md["r_parent"], -self.inf, obj3 + objective_tol(obj3))

        if self.m:
            o2.set_col_bounds(
                self.h, hs, self.uq_idx,
                np.zeros(self.m), np.full(self.m, self.inf),
            )
            q_rows = np.concatenate([
                np.arange(md["r_qp0"], md["r_qp0"] + self.m, dtype=np.int32),
                np.arange(md["r_qm0"], md["r_qm0"] + self.m, dtype=np.int32),
            ])
            q_lo = np.full(2 * self.m, -self.inf)
            q_up = np.concatenate([self.comp["qtarget"], -self.comp["qtarget"]])
            o2.set_row_bounds(self.h, hs, q_rows, q_lo, q_up)
        cost = np.zeros(self.ncol, dtype=np.float64)
        if self.m:
            cost[md["uq0"]: md["uq0"] + self.m] = 1.0
        sol4, t = self._solve_stage(
            nonlinear_iteration=nonlinear_iteration, stage_no=4,
            stage_name="MINIMUM_RAW_EVENT_EOS_L1", cost=cost,
            local_available=local_available, cv_tol=cv_tol, grid_tol=grid_tol,
        )
        telemetry.append(t)
        uq4 = sol4[md["uq0"]: md["uq0"] + self.m]
        obj4 = float(np.sum(uq4))
        self.h.changeRowBounds(md["r_raw"], -self.inf, obj4 + objective_tol(obj4))

        cost = np.zeros(self.ncol, dtype=np.float64)
        cost[:self.n] = self.comp["global_rank"]
        sol5, t = self._solve_stage(
            nonlinear_iteration=nonlinear_iteration, stage_no=5,
            stage_name="DETERMINISTIC_GLOBAL_PAIR_RANK_TIEBREAK", cost=cost,
            local_available=local_available, cv_tol=cv_tol, grid_tol=grid_tol,
        )
        telemetry.append(t)
        x5 = sol5[:self.n].copy()
        obj5 = float(np.dot(self.comp["global_rank"], x5))
        return {
            "edge_idx": self.comp["edge_idx"],
            "x": x5,
            "objectives": {
                "stage1_shell_kg": obj1,
                "stage2_extension_kg": obj2,
                "stage3_parent_L1_kg": obj3,
                "stage4_raw_L1_kg": obj4,
                "stage5_tiebreak": obj5,
            },
            "telemetry": telemetry,
        }

    def close(self) -> None:
        try:
            self.h.releaseMemory()
        except Exception:
            pass


def self_test() -> None:
    assert GRID == (15, 50, 50)
    assert NCVTOTAL == 215600
    assert EXPECTED_E2_PAIRS == 3091073
    assert MAX_FIXED_POINT_ITERATIONS == 100
    assert PRESSURE_REL_L2_TOL == 1.0e-10
    assert SATURATION_LINF_TOL == 1.0e-10
    payload = {"b": np.array([2, 3]), "a": np.array([1.0])}
    assert deterministic_npz_bytes(payload) == deterministic_npz_bytes(payload)
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6 controlled coupled fixed-point "
        "execution structural self-test: PASS"
    )


def solver_self_test() -> None:
    import highspy
    h = highspy.Highs()
    assert tuple(int(x) for x in h.version().split(".")[:2]) >= (1, 13)
    print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6 native HiGHS API self-test: PASS", h.version())


def main(project_root: Path, drive_root: Path, verbose_solver: bool = False) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    nonlinear_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    pressure_solve_executed = False
    assignment_executed = False
    converged = False
    current_iteration = 0
    current_pressure = None
    current_sat = None
    current_mass = None
    current_full_x = None

    def gate(name: str, cond: bool, detail: Any = None) -> None:
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    def sci_gate(name: str, cond: bool, detail: Any = None) -> None:
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise ScientificFail(name, detail)
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    print("=" * 210)
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6 -- CONTROLLED COUPLED PRESSURE / "
        "SAME-H2 REASSIGNMENT FIXED-POINT EXECUTION"
    )
    print("=" * 210)
    print("ONE SAME-TIME EVENT COUPLING EXECUTION AT THE FROZEN EVENT DAY.")
    print("FROZEN E2/H2 SUPPORT. EXACT PER-CV MASS. IMMUTABLE RESIDUAL SIDECAR.")
    print("O2 FIVE-STAGE LEXICOGRAPHIC OBJECTIVES PRESERVED AT EVERY PRESSURE ITERATE.")
    print("NO DAMPING. NO SUPPORT EXPANSION. NO DARCY/POLLOCK/TOF. NO REPROJECTION. NO TIME ADVANCE.")
    print()

    solvers: list[PersistentComponentSolver] = []
    try:
        # Authority and O3-R5 handoff.
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_O3R5_commit", parent == PARENT_O3R5_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "O3R5_contract_binding"
        r5d = drive / O3R5_REL
        gate("O3R5_output_present", r5d.is_dir(), str(r5d))
        m5 = verify_manifest(r5d, O3R5_MANIFEST)
        gate("O3R5_manifest_exact_6", len(m5) == 6, len(m5))
        gate("O3R5_manifest_payload_file_set_exact", set(m5) == EXPECTED_O3R5_FILES, sorted(m5))
        s5 = load_json(r5d / O3R5_SUMMARY)
        h5 = load_json(r5d / O3R5_HANDOFF)
        d5 = load_json(r5d / O3R5_DECISION)
        gate(
            "O3R5_status_and_semantics_exact",
            s5.get("status") == O3R5_STATUS
            and s5.get("coupled_fixed_point_semantics_frozen") is True
            and s5.get("O2_lexicographic_objectives_preserved") is True
            and s5.get("frozen_E2_support_preserved") is True
            and s5.get("per_CV_mass_preserved") is True
            and s5.get("residual_sidecar_preserved") is True
            and int(s5.get("maximum_fixed_point_iterations", -1)) == MAX_FIXED_POINT_ITERATIONS
            and float(s5.get("pressure_relative_L2_tolerance", 1.0)) == PRESSURE_REL_L2_TOL
            and float(s5.get("saturation_Linf_tolerance", 1.0)) == SATURATION_LINF_TOL
            and s5.get("physical_time_advanced") is False,
        )
        gate(
            "O3R5_authorizes_O3R6_execution_only",
            h5.get("O3R6_execution_authorized") is True
            and h5.get("O3R7_authorized") is False
            and h5.get("R3R3R4_authorized") is False
            and d5.get("under_relaxation_authorized") is False
            and d5.get("support_domain_changed") is False
            and d5.get("physical_time_advance_authorized") is False,
        )

        # Bind immutable O2 assignment state and A2-E parent epoch.
        stage = "state_authority_binding"
        o2d = drive / O2_REL
        gate("O2_output_present", o2d.is_dir(), str(o2d))
        m2 = verify_manifest(o2d, O2_MANIFEST)
        gate("O2_manifest_exact_8", len(m2) == 8, len(m2))
        gate("O2_manifest_payload_file_set_exact", set(m2) == EXPECTED_O2_FILES, sorted(m2))
        with np.load(o2d / O2_STATE, allow_pickle=False) as z:
            event_day = float(np.asarray(z["event_day"]).reshape(()))
            physical_time_o2 = bool(np.asarray(z["physical_time_advanced_in_O2"]).reshape(()))
            event_grid0 = np.asarray(z["event_grid_component_mass_kg"], dtype=np.float64)
            event_mapped0 = np.asarray(z["event_mapped_grid_mass_kg"], dtype=np.float64)
            residual_grid = np.asarray(z["frozen_residual_grid_component_mass_kg"], dtype=np.float64)
            event_cv_mass = np.asarray(z["event_CV_component_mass_kg"], dtype=np.float64)
            e0_cv = np.asarray(z["E0_pair_cv_id"], dtype=np.int64)
            e0_cell = np.asarray(z["E0_pair_flat_cell"], dtype=np.int64)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            is_e0 = np.asarray(z["E2_pair_is_E0"], dtype=bool)
            is_e1 = np.asarray(z["E2_pair_is_E1"], dtype=bool)
            full_x0 = np.asarray(z["E2_pair_event_mass_kg"], dtype=np.float64)
            target0 = np.asarray(z["E0_parent_continuity_target_kg"], dtype=np.float64)
            qtarget0 = np.asarray(z["E0_raw_event_EOS_target_kg"], dtype=np.float64)
            parent_pressure_o2 = np.asarray(z["parent_pressure_psi"], dtype=np.float64)
            grid_pv_o2 = np.asarray(z["grid_pore_volume_m3"], dtype=np.float64)
            p_ref_o2 = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
        gate(
            "O2_state_shapes_exact",
            event_grid0.shape == GRID and event_mapped0.shape == GRID and residual_grid.shape == GRID
            and event_cv_mass.shape == (NSL, NCV)
            and e0_cv.shape == (EXPECTED_E0_PAIRS,) and e0_cell.shape == (EXPECTED_E0_PAIRS,)
            and e2_cv.shape == (EXPECTED_E2_PAIRS,) and e2_cell.shape == (EXPECTED_E2_PAIRS,)
            and is_e0.shape == (EXPECTED_E2_PAIRS,) and is_e1.shape == (EXPECTED_E2_PAIRS,)
            and full_x0.shape == (EXPECTED_E2_PAIRS,)
            and target0.shape == (EXPECTED_E0_PAIRS,) and qtarget0.shape == (EXPECTED_E0_PAIRS,)
            and parent_pressure_o2.shape == GRID and grid_pv_o2.shape == GRID,
        )
        gate("O2_event_identity_exact", abs(event_day - EVENT_DAY) <= 1.0e-12 and physical_time_o2 is False,
             {"event_day": event_day, "physical_time_advanced_in_O2": physical_time_o2})
        gate("O2_grid_split_exact", max_abs(event_mapped0 + residual_grid - event_grid0) <= 1.0e-8,
             max_abs(event_mapped0 + residual_grid - event_grid0))

        a2d = drive / A2E_REL
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        verify_manifest(a2d, A2E_MANIFEST)
        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}
        parent_pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        grid_pv = np.asarray(epoch["pore_volume_m3"], dtype=np.float64)
        p_ref = float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)
        gate("O2_parent_pressure_matches_A2E", max_abs(parent_pressure - parent_pressure_o2) <= 1.0e-12,
             max_abs(parent_pressure - parent_pressure_o2))
        gate("O2_grid_PV_matches_A2E", max_abs(grid_pv - grid_pv_o2) <= 1.0e-12,
             max_abs(grid_pv - grid_pv_o2))
        gate("O2_reference_pressure_matches_A2E", abs(p_ref - p_ref_o2) <= 1.0e-9, abs(p_ref - p_ref_o2))

        # Load exact source-authentic helpers.
        stage = "source_module_binding"
        o2 = load_module(root / O2, "postv16_o3r6_o2")
        a2e = load_module(root / A2E, "postv16_o3r6_a2e")
        r2 = load_module(root / R2PHYS, "postv16_o3r6_r2")
        sg2 = load_module(root / SG2, "postv16_o3r6_sg2")
        sg3 = load_module(root / SG3, "postv16_o3r6_sg3")
        r3r2r1 = load_module(root / R3R2R1, "postv16_o3r6_r3r2r1")
        gate(
            "required_execution_helpers_present",
            all([
                hasattr(o2, "preprocess_active_graph"), hasattr(o2, "make_component"),
                hasattr(o2, "build_component_model"), hasattr(o2, "set_full_costs"),
                hasattr(o2, "set_col_bounds"), hasattr(o2, "set_row_bounds"),
                hasattr(a2e, "invert_local_mass"), hasattr(a2e, "local_mass"),
                hasattr(a2e, "spatial_mobility"),
                hasattr(sg2, "build_directional_permeability"), hasattr(sg2, "build_face_permeabilities"),
                hasattr(sg3, "construct_si_transmissibilities"),
                hasattr(r3r2r1, "build_updated_transmissibilities"),
                hasattr(r3r2r1, "assemble_updated_pressure_system"),
                hasattr(r3r2r1, "solve_updated_pressure"),
            ]),
        )
        import highspy
        highspy_version = highspy.Highs().version()
        gate("highspy_version_exact_1_15_1", highspy_version == "1.15.1", highspy_version)

        # Exact frozen E2 support semantics reconstructed from O2 state.
        stage = "frozen_E2_model_construction"
        e0_indices = np.flatnonzero(is_e0).astype(np.int64)
        gate("E0_indices_in_E2_count_exact", e0_indices.size == EXPECTED_E0_PAIRS, int(e0_indices.size))
        gate(
            "E0_order_matches_E2_embedded_support",
            np.array_equal(e2_cv[e0_indices], e0_cv) and np.array_equal(e2_cell[e0_indices], e0_cell),
        )
        support = {
            "e2_cv": e2_cv,
            "e2_cell": e2_cell,
            "is_e0": is_e0,
            "is_e1": is_e1,
            "is_h2_shell": (~is_e0) & (~is_e1),
            "is_any_extension": (~is_e0),
        }
        demand = event_cv_mass.reshape(-1).astype(np.float64)
        residual = residual_grid.reshape(-1).astype(np.float64)
        target_by_edge = np.zeros(EXPECTED_E2_PAIRS, dtype=np.float64)
        qtarget_by_edge = np.zeros(EXPECTED_E2_PAIRS, dtype=np.float64)
        target_by_edge[e0_indices] = target0
        qtarget_by_edge[e0_indices] = qtarget0

        # Build the graph once. Capacity is represented by row bounds, never by support deletion.
        prep = o2.preprocess_active_graph(
            e2_cv=e2_cv,
            e2_cell=e2_cell,
            demand=demand,
            available_raw=np.ones(NCELL, dtype=np.float64),
        )
        gate("frozen_E2_active_edge_count_exact", prep["active_edge_count"] == EXPECTED_ACTIVE_EDGES,
             prep["active_edge_count"])
        gate("frozen_E2_component_count_positive", prep["component_count"] >= 1, prep["component_count"])

        # Reference transmissibilities are fixed rock properties; only mobility scales them per iterate.
        permeability_md = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        # Initial O2 event state under parent pressure.
        try:
            event_sg0 = a2e.invert_local_mass(r2, event_grid0, parent_pressure, p_ref, grid_pv)
        except Exception as exc:
            raise ScientificFail("initial_parent_pressure_mass_inversion_failure", repr(exc)) from exc
        current_pressure = parent_pressure.copy()
        current_sat = BACKGROUND + np.asarray(event_sg0, dtype=np.float64)
        current_mass = event_grid0.copy()
        current_full_x = full_x0.copy()
        sci_gate("initial_event_saturation_bounds", np.isfinite(current_sat).all()
                 and float(np.min(current_sat)) >= BACKGROUND - 1.0e-10
                 and float(np.max(current_sat)) <= INJECTED + 1.0e-10,
                 [float(np.min(current_sat)), float(np.max(current_sat))])

        parent_capacity = np.asarray(
            a2e.local_mass(r2, np.full(GRID, INJECTED), parent_pressure, p_ref, grid_pv),
            dtype=np.float64,
        )
        initial_available = np.maximum(parent_capacity.reshape(-1) - residual, 0.0)

        # Build one persistent native-HiGHS model per exact disconnected component.
        build_t0 = time.perf_counter()
        for cid in range(prep["component_count"]):
            a = int(prep["component_starts"][cid])
            b = int(prep["component_starts"][cid + 1])
            edge_idx = prep["sorted_edge_idx"][a:b]
            comp = o2.make_component(
                component_id=cid,
                edge_idx=edge_idx,
                support=support,
                demand=demand,
                available_safe=initial_available,
                target_by_edge=target_by_edge,
                qtarget_by_edge=qtarget_by_edge,
            )
            md = o2.build_component_model(comp, highspy)
            solvers.append(PersistentComponentSolver(
                component_id=cid, comp=comp, model_data=md,
                highspy=highspy, o2=o2, output_flag=verbose_solver,
            ))
            print(
                f"[PASS] persistent component model {cid}: CVs={len(comp['cv_ids'])} "
                f"cells={len(comp['cell_ids'])} edges={len(comp['edge_idx'])} "
                f"vars={md['ncol']} rows={md['nrow']} nnz={md['nnz']}"
            )
        model_build_wall = time.perf_counter() - build_t0
        gate("persistent_component_models_built", len(solvers) == prep["component_count"], len(solvers))

        def pressure_step(saturation: np.ndarray) -> tuple[np.ndarray, float]:
            mobility = a2e.spatial_mobility(
                saturation, grid_nw, grid_no, grid_krw, grid_kro
            )
            tx, ty, tz, _ = r3r2r1.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, _wi = r3r2r1.assemble_updated_pressure_system(
                sg3, permeability_md, tx, ty, tz, mobility["lambda_total"]
            )
            _ppa, ppsi, linear_resid = r3r2r1.solve_updated_pressure(sg3, A, b)
            return np.asarray(ppsi, dtype=np.float64), float(linear_resid)

        # Controlled coupled fixed point.
        stage = "coupled_pressure_sameH2_fixed_point"
        total_event_component_mass = fsum_array(demand)
        cv_tol = max(1.0e-6, 1.0e-10 * max(float(np.max(np.abs(demand))), 1.0))
        provisional_pressure = provisional_sat = provisional_mass = provisional_cap = None
        provisional_x = None

        for iteration in range(1, MAX_FIXED_POINT_ITERATIONS + 1):
            current_iteration = iteration
            print()
            print("-" * 180)
            print(f"[START] COUPLED NONLINEAR ITERATION {iteration}/{MAX_FIXED_POINT_ITERATIONS}")
            print("-" * 180)
            p_next, pressure_linear_residual = pressure_step(current_sat)
            pressure_solve_executed = True
            sci_gate(
                f"iteration_{iteration:03d}_pressure_linear_residual",
                pressure_linear_residual < PRESSURE_LINEAR_REL_RESIDUAL_MAX,
                pressure_linear_residual,
            )
            cap = np.asarray(
                a2e.local_mass(r2, np.full(GRID, INJECTED), p_next, p_ref, grid_pv),
                dtype=np.float64,
            )
            cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(np.abs(cap))), 1.0))
            available_raw = cap.reshape(-1) - residual
            if float(np.min(available_raw)) < -cap_tol:
                raise ScientificFail(
                    "immutable_residual_sidecar_exceeds_iterate_capacity",
                    {"iteration": iteration, "minimum_available_mapped_capacity_kg": float(np.min(available_raw)),
                     "tolerance_kg": cap_tol},
                )
            available = np.maximum(available_raw, 0.0)
            grid_tol = max(1.0e-6, 1.0e-10 * max(float(np.max(np.abs(cap))), 1.0))

            full_x = np.zeros(EXPECTED_E2_PAIRS, dtype=np.float64)
            iteration_objectives = {
                "stage1_shell_kg": 0.0,
                "stage2_extension_kg": 0.0,
                "stage3_parent_L1_kg": 0.0,
                "stage4_raw_L1_kg": 0.0,
                "stage5_tiebreak": 0.0,
            }
            for solver in solvers:
                result = solver.solve_iteration(
                    nonlinear_iteration=iteration,
                    available_global=available,
                    cv_tol=cv_tol,
                    grid_tol=grid_tol,
                )
                assignment_executed = True
                full_x[result["edge_idx"]] = result["x"]
                assignment_rows.extend(result["telemetry"])
                for key, value in result["objectives"].items():
                    iteration_objectives[key] += float(value)

            mapped = np.bincount(e2_cell, weights=full_x, minlength=NCELL).astype(np.float64)
            cv_reconstructed = np.bincount(e2_cv, weights=full_x, minlength=NCVTOTAL).astype(np.float64)
            m_next = (residual + mapped).reshape(GRID)
            cv_linf = max_abs(cv_reconstructed - demand)
            max_capacity_excess = float(np.max(m_next - cap))
            global_assignment_residual = fsum_array(m_next) - fsum_array(residual) - fsum_array(demand)
            if cv_linf > cv_tol or max_capacity_excess > grid_tol or abs(global_assignment_residual) > max(1.0e-5, 1.0e-10 * max(fsum_array(m_next), 1.0)):
                raise ScientificFail(
                    "iteration_assignment_global_certification_failure",
                    {"iteration": iteration, "CV_Linf_kg": cv_linf,
                     "max_capacity_excess_kg": max_capacity_excess,
                     "global_assignment_residual_kg": global_assignment_residual,
                     "CV_tolerance_kg": cv_tol, "capacity_tolerance_kg": grid_tol},
                )

            try:
                sg_next = a2e.invert_local_mass(r2, m_next, p_next, p_ref, grid_pv)
            except Exception as exc:
                raise ScientificFail(
                    "iterate_EOS_mass_inversion_failure",
                    {"iteration": iteration, "exception": repr(exc)},
                ) from exc
            s_next = BACKGROUND + np.asarray(sg_next, dtype=np.float64)
            if not (np.isfinite(s_next).all()
                    and float(np.min(s_next)) >= BACKGROUND - 1.0e-10
                    and float(np.max(s_next)) <= INJECTED + 1.0e-10):
                raise ScientificFail(
                    "iterate_saturation_bounds_failure",
                    {"iteration": iteration, "min": float(np.min(s_next)), "max": float(np.max(s_next))},
                )

            reconstructed_mass = np.asarray(
                a2e.local_mass(r2, s_next, p_next, p_ref, grid_pv), dtype=np.float64
            )
            cell_mass_error = max_abs(reconstructed_mass - m_next)
            global_mass_relative_error = abs(fsum_array(reconstructed_mass) - fsum_array(m_next)) / max(abs(fsum_array(m_next)), 1.0)
            mass_conv_tol = max(1.0e-8, 1.0e-10 * max(float(np.max(np.abs(m_next))), 1.0))
            pressure_delta = relative_l2(p_next, current_pressure)
            saturation_delta = max_abs(s_next - current_sat)
            grid_mass_delta = max_abs(m_next - current_mass)

            row = {
                "iteration": iteration,
                "pressure_relative_L2_change": pressure_delta,
                "saturation_Linf_change": saturation_delta,
                "grid_mass_Linf_change_kg": grid_mass_delta,
                "grid_mass_convergence_tolerance_kg": mass_conv_tol,
                "pressure_linear_relative_residual": pressure_linear_residual,
                "CV_mass_Linf_error_kg": cv_linf,
                "maximum_cell_capacity_excess_kg": max_capacity_excess,
                "cellwise_EOS_mass_error_kg": cell_mass_error,
                "global_EOS_mass_relative_error": global_mass_relative_error,
                "global_assignment_residual_kg": global_assignment_residual,
                "pressure_min_psi": float(np.min(p_next)),
                "pressure_max_psi": float(np.max(p_next)),
                "saturation_min": float(np.min(s_next)),
                "saturation_max": float(np.max(s_next)),
                "capacity_min_kg": float(np.min(cap)),
                "capacity_max_kg": float(np.max(cap)),
                **iteration_objectives,
            }
            nonlinear_rows.append(row)
            print(
                f"[ITER {iteration:03d}] dP={pressure_delta:.6e} dS={saturation_delta:.6e} "
                f"dM={grid_mass_delta:.6e} kg CV={cv_linf:.3e} cap={max_capacity_excess:.3e} "
                f"EOS={cell_mass_error:.3e} kg"
            )
            sys.stdout.flush()

            if cell_mass_error > mass_conv_tol or global_mass_relative_error > GLOBAL_MASS_REL_TOL:
                raise ScientificFail(
                    "iterate_mass_closure_failure",
                    {"iteration": iteration, "cellwise_error_kg": cell_mass_error,
                     "cellwise_tolerance_kg": mass_conv_tol,
                     "global_relative_error": global_mass_relative_error,
                     "global_tolerance": GLOBAL_MASS_REL_TOL},
                )

            provisional_pressure = p_next.copy()
            provisional_sat = s_next.copy()
            provisional_mass = m_next.copy()
            provisional_cap = cap.copy()
            provisional_x = full_x.copy()

            if (pressure_delta <= PRESSURE_REL_L2_TOL
                    and saturation_delta <= SATURATION_LINF_TOL
                    and grid_mass_delta <= mass_conv_tol):
                converged = True
                print(f"[PASS] provisional coupled fixed point converged at iteration {iteration}")
                break

            current_pressure = p_next
            current_sat = s_next
            current_mass = m_next
            current_full_x = full_x

        if not converged:
            raise ScientificFail(
                "coupled_pressure_assignment_fixed_point_nonconvergence",
                {"maximum_iterations": MAX_FIXED_POINT_ITERATIONS,
                 "last": nonlinear_rows[-1] if nonlinear_rows else None},
            )

        # Frozen final closure: one pressure solve, no assignment change.
        stage = "final_closure_recertification"
        closure_pressure, closure_linear_residual = pressure_step(provisional_sat)
        sci_gate("closure_pressure_linear_residual", closure_linear_residual < PRESSURE_LINEAR_REL_RESIDUAL_MAX,
                 closure_linear_residual)
        closure_pressure_delta = relative_l2(closure_pressure, provisional_pressure)
        sci_gate("closure_pressure_fixed_point", closure_pressure_delta <= PRESSURE_REL_L2_TOL,
                 {"relative_L2": closure_pressure_delta, "tolerance": PRESSURE_REL_L2_TOL})
        closure_cap = np.asarray(
            a2e.local_mass(r2, np.full(GRID, INJECTED), closure_pressure, p_ref, grid_pv),
            dtype=np.float64,
        )
        closure_cap_tol = max(1.0e-6, 1.0e-10 * max(float(np.max(np.abs(closure_cap))), 1.0))
        closure_available_raw = closure_cap.reshape(-1) - residual
        sci_gate("closure_residual_sidecar_capacity", float(np.min(closure_available_raw)) >= -closure_cap_tol,
                 {"minimum_available_mapped_capacity_kg": float(np.min(closure_available_raw)),
                  "tolerance_kg": closure_cap_tol})
        closure_grid_excess = float(np.max(provisional_mass - closure_cap))
        sci_gate("closure_assignment_within_capacity", closure_grid_excess <= closure_cap_tol,
                 {"maximum_excess_kg": closure_grid_excess, "tolerance_kg": closure_cap_tol})
        try:
            closure_sg = a2e.invert_local_mass(r2, provisional_mass, closure_pressure, p_ref, grid_pv)
        except Exception as exc:
            raise ScientificFail("closure_EOS_mass_inversion_failure", repr(exc)) from exc
        closure_sat = BACKGROUND + np.asarray(closure_sg, dtype=np.float64)
        sci_gate("closure_saturation_bounds", np.isfinite(closure_sat).all()
                 and float(np.min(closure_sat)) >= BACKGROUND - 1.0e-10
                 and float(np.max(closure_sat)) <= INJECTED + 1.0e-10,
                 [float(np.min(closure_sat)), float(np.max(closure_sat))])
        closure_reconstructed_mass = np.asarray(
            a2e.local_mass(r2, closure_sat, closure_pressure, p_ref, grid_pv), dtype=np.float64
        )
        final_mass_tol = max(1.0e-8, 1.0e-10 * max(float(np.max(np.abs(provisional_mass))), 1.0))
        closure_cell_mass_error = max_abs(closure_reconstructed_mass - provisional_mass)
        closure_global_rel = abs(fsum_array(closure_reconstructed_mass) - fsum_array(provisional_mass)) / max(abs(fsum_array(provisional_mass)), 1.0)
        sci_gate("closure_cellwise_mass_error", closure_cell_mass_error <= final_mass_tol,
                 {"error_kg": closure_cell_mass_error, "tolerance_kg": final_mass_tol})
        sci_gate("closure_global_mass_relative_error", closure_global_rel <= GLOBAL_MASS_REL_TOL, closure_global_rel)
        closure_sat_delta = max_abs(closure_sat - provisional_sat)

        # Final assignment recertification under closure capacity.
        final_mapped = np.bincount(e2_cell, weights=provisional_x, minlength=NCELL).astype(np.float64)
        final_cv = np.bincount(e2_cv, weights=provisional_x, minlength=NCVTOTAL).astype(np.float64)
        final_cv_linf = max_abs(final_cv - demand)
        sci_gate("final_per_CV_mass_exact", final_cv_linf <= cv_tol,
                 {"Linf_kg": final_cv_linf, "tolerance_kg": cv_tol})
        sci_gate("final_grid_reconstruction_exact",
                 max_abs((residual + final_mapped).reshape(GRID) - provisional_mass) <= 1.0e-8,
                 max_abs((residual + final_mapped).reshape(GRID) - provisional_mass))

        # Publish coupled state checkpoint. No Darcy/Pollock/TOF/reprojection.
        stage = "artifact_publication"
        checkpoint = deterministic_npz_bytes({
            "event_day": np.asarray(EVENT_DAY),
            "physical_time_advanced_in_O3R6": np.asarray(False),
            "coupled_fixed_point_iteration_count": np.asarray(current_iteration),
            "converged_pressure_psi": closure_pressure,
            "converged_saturation": closure_sat,
            "converged_event_grid_component_mass_kg": provisional_mass,
            "converged_event_mapped_grid_mass_kg": final_mapped.reshape(GRID),
            "frozen_residual_grid_component_mass_kg": residual_grid,
            "converged_cell_capacity_kg": closure_cap,
            "event_CV_component_mass_kg": event_cv_mass,
            "E2_pair_cv_id": e2_cv,
            "E2_pair_flat_cell": e2_cell,
            "E2_pair_is_E0": is_e0,
            "E2_pair_is_E1": is_e1,
            "E2_pair_converged_mass_kg": provisional_x,
            "grid_pore_volume_m3": grid_pv,
            "reference_gas_pressure_pa": np.asarray(p_ref),
        })

        total_assignment_wall = float(sum(r["wall_time_s"] for r in assignment_rows))
        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "highspy_version": highspy_version,
            "coupled_fixed_point_converged": True,
            "coupled_fixed_point_iteration_count": int(current_iteration),
            "maximum_fixed_point_iterations": MAX_FIXED_POINT_ITERATIONS,
            "pressure_relative_L2_tolerance": PRESSURE_REL_L2_TOL,
            "saturation_Linf_tolerance": SATURATION_LINF_TOL,
            "final_closure_pressure_relative_L2": closure_pressure_delta,
            "final_closure_saturation_Linf_change": closure_sat_delta,
            "final_CV_mass_Linf_error_kg": final_cv_linf,
            "final_maximum_cell_capacity_excess_kg": closure_grid_excess,
            "final_cellwise_EOS_mass_error_kg": closure_cell_mass_error,
            "final_global_EOS_mass_relative_error": closure_global_rel,
            "persistent_component_count": int(len(solvers)),
            "persistent_model_build_wall_time_s": float(model_build_wall),
            "assignment_stage_total_wall_time_s": total_assignment_wall,
            "assignment_stage_solve_count": int(len(assignment_rows)),
            "frozen_E2_support_preserved": True,
            "O2_lexicographic_objectives_preserved": True,
            "per_CV_mass_preserved": True,
            "residual_sidecar_preserved": True,
            "under_relaxation_used": False,
            "support_domain_changed": False,
            "pressure_solve_executed": True,
            "assignment_executed": True,
            "Darcy_Pollock_TOF_regenerated": False,
            "reprojection_executed": False,
            "flow_refresh_completed": False,
            "physical_time_advanced": False,
        }
        audit = {
            **summary,
            "initial_O2_event_grid_total_kg": fsum_array(event_grid0),
            "final_event_grid_total_kg": fsum_array(provisional_mass),
            "frozen_residual_total_kg": fsum_array(residual_grid),
            "frozen_CV_total_kg": total_event_component_mass,
            "initial_to_final_grid_mass_Linf_kg": max_abs(provisional_mass - event_grid0),
            "initial_to_final_pressure_relative_L2": relative_l2(closure_pressure, parent_pressure),
            "initial_to_final_saturation_Linf": max_abs(closure_sat - (BACKGROUND + event_sg0)),
            "active_E2_edge_count": int(prep["active_edge_count"]),
            "raw_E2_edge_count": EXPECTED_E2_PAIRS,
            "component_count": int(prep["component_count"]),
            "gates": gates,
        }
        handoff = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R7 — "
                "single final Darcy/Pollock/TOF refresh and refreshed-geometry reprojection design freeze"
            ),
            "O3R7_design_authorized": True,
            "O3R7_execution_authorized": False,
            "required_O3R6_checkpoint": "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Converged_Coupled_Event_State.npz",
            "physical_time_advance_before_O3R7": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "scientific_constraints_relaxed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "under_relaxation_used": False,
            "support_domain_changed": False,
            "coupled_fixed_point_execution_pass": True,
            "Darcy_Pollock_TOF_regenerated": False,
            "reprojection_executed": False,
            "physical_time_advanced": False,
            "O3R7_design_authorized": True,
            "O3R7_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Summary.json": json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Coupled_Fixed_Point_Audit.json": json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Nonlinear_Iteration_Telemetry.csv": csv_bytes(nonlinear_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Assignment_Stage_Telemetry.csv": csv_bytes(assignment_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Converged_Coupled_Event_State.npz": checkpoint,
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_O3R7_Handoff_Contract.json": json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Final_Gate_Matrix.csv": csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)
        manifest_name = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Artifact_Manifest.csv"
        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != manifest_name:
                manifest_rows.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
        immutable_publish(out, {manifest_name: csv_bytes(manifest_rows)})

        print()
        print("=" * 210)
        print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6: COUPLED FIXED-POINT EXECUTION PASS")
        print("=" * 210)
        print("Event day                              :", EVENT_DAY)
        print("Coupled nonlinear iterations          :", current_iteration)
        print("Final closure pressure relative L2    :", closure_pressure_delta)
        print("Final CV mass Linf kg                 :", final_cv_linf)
        print("Final max cell capacity excess kg     :", closure_grid_excess)
        print("Final EOS cellwise mass error kg      :", closure_cell_mass_error)
        print("Under-relaxation                      : False")
        print("Darcy/Pollock/TOF                     : NOT EXECUTED")
        print("Refreshed-geometry reprojection       : NOT EXECUTED")
        print("Physical-time advance                 : False")
        print("O3-R7 design                          : AUTHORIZED")
        print("O3-R7 execution / R3-R3-R4            : NOT AUTHORIZED")
        print("F5 / training                         : NOT AUTHORIZED")
        print("=" * 210)
        return 0

    except ScientificFail as exc:
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "current_iteration": int(current_iteration),
            "gates": gates,
            "pressure_solve_executed": pressure_solve_executed,
            "assignment_executed": assignment_executed,
            "coupled_fixed_point_converged": False,
            "under_relaxation_used": False,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "Darcy_Pollock_TOF_regenerated": False,
            "reprojection_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        rp = publish_evidence(
            failed,
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Scientific_Fail_Report.json",
            json_bytes(report),
        )
        if nonlinear_rows:
            publish_evidence(failed, "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Fail_Nonlinear_Telemetry.csv", csv_bytes(nonlinear_rows))
        if assignment_rows:
            publish_evidence(failed, "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Fail_Assignment_Telemetry.csv", csv_bytes(assignment_rows))
        print()
        print("=" * 210)
        print(MILESTONE + ": SCIENTIFIC FAIL")
        print("Stage :", stage)
        print("Gate  :", exc.gate)
        print("Detail:", exc.detail)
        print("Report:", rp)
        print("NO DAMPING, SUPPORT EXPANSION, DARCY/POLLOCK/TOF, REPROJECTION, TIME ADVANCE, OR AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 210)
        return 3

    except Exception as exc:
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "current_iteration": int(current_iteration),
            "gates": gates,
            "pressure_solve_executed": pressure_solve_executed,
            "assignment_executed": assignment_executed,
            "coupled_fixed_point_converged": False,
            "support_domain_changed": False,
            "Darcy_Pollock_TOF_regenerated": False,
            "reprojection_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        rp = publish_evidence(
            blocked,
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Blocked_Report.json",
            json_bytes(report),
        )
        print()
        print("=" * 210)
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("Report   :", rp)
        print("NO SCIENTIFIC PASS/FAIL CLAIM BEYOND THE RECORDED COMPLETED GATES. NO AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 210)
        return 2

    finally:
        for solver in solvers:
            solver.close()
        gc.collect()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--verbose-solver", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--solver-self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    if args.solver_self_test:
        solver_self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.verbose_solver))
