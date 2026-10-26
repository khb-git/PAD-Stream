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
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4_CONTROLLED_ADAPTIVE_FEASIBILITY_PRESERVING_"
    "STABILIZED_COUPLED_FIXED_POINT_EXECUTION_PASS_ORIGINAL_UNDAMPED_CLOSURE_"
    "CERTIFIED_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R6R4_CONTROLLED_ADAPTIVE_FEASIBILITY_PRESERVING_"
    "STABILIZED_COUPLED_EXECUTION_SCIENTIFIC_FAIL_NO_SUPPORT_EXPANSION_"
    "NO_AUTOMATIC_RERUN_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3_COMMIT = "b66b938f05bff23cc93bf0af69ef5e1b61f38435"
EVENT_DAY = 413.78677770818403

GRID = (15, 50, 50)
NCELL = 37500
NSL = 1078
NCV = 200
NCVTOTAL = 215600
EXPECTED_E0 = 269721
EXPECTED_E2 = 3091073
EXPECTED_ACTIVE = 3012452
BACKGROUND = 0.20
INJECTED = 0.80

MAX_NONLINEAR_ITERATIONS = 100
PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_LINF_TOL = 1.0e-10
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8
GLOBAL_MASS_REL_TOL = 1.0e-10

FEASIBILITY_UNSERVED_TOL_KG = 1.0e-6
FEASIBILITY_CV_LINF_TOL_KG = 1.0e-6
FEASIBILITY_CAPACITY_EXCESS_TOL_KG = 1.0e-6
LINE_SEARCH_DEN = 1024
MIN_POSITIVE_OMEGA_INDEX = 1

R2R2_FIRST_FEASIBLE_INDEX = 147
R2R2_FIRST_FEASIBLE_OMEGA = R2R2_FIRST_FEASIBLE_INDEX / LINE_SEARCH_DEN
R2R2_FIRST_INFEASIBLE_INDEX = 148

# -------------------------------------------------------------------------------------------------
# Source authority
# -------------------------------------------------------------------------------------------------
R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze.py"
)
R3_BLOB = "c118972a991e4ae0ce7200a9f880a73407450b8b"
O3R6 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_"
    "Controlled_Coupled_Pressure_SameH2_Reassignment_Fixed_Point_Execution.py"
)
O3R6_BLOB = "368cfa24dd395e3e07df033c9ed95ab4024a3a4b"
O3R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_"
    "Exact_Frozen_E2_First_Refresh_Capacity_Feasibility_Audit.py"
)
O3R4_BLOB = "4446ca612d1f6a00472327818aff674d568f9ede"
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
    R3: R3_BLOB,
    O3R6: O3R6_BLOB,
    O3R4: O3R4_BLOB,
    O2: O2_BLOB,
    A2E: A2E_BLOB,
    R2PHYS: R2PHYS_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    R3R2R1: R3R2R1_BLOB,
    PERM: PERM_BLOB,
}

# -------------------------------------------------------------------------------------------------
# Persistent artifact authority
# -------------------------------------------------------------------------------------------------
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze"
)
R3_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Summary.json"
R3_OPERATOR = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Adaptive_Stabilization_Operator_Contract.json"
R3_CONVERGENCE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Undamped_Convergence_and_Final_Closure_Contract.json"
R3_CHECKPOINT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Stabilized_Checkpoint_Restart_Policy.json"
R3_FAILURE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Failure_Semantics.json"
R3_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Decision_Contract.json"
R3_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Final_Gate_Matrix.csv"
R3_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Artifact_Manifest.csv"
EXPECTED_R3_FILES = {
    R3_SUMMARY, R3_OPERATOR, R3_CONVERGENCE, R3_CHECKPOINT,
    R3_FAILURE, R3_DECISION, R3_GATES,
}

R1R1_CP_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Durable_Checkpoints"
)
R1R1_CP1_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Certified_State.npz"
R1R1_CP1_META = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Certified_State.json"
R1R1_CP1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Checkpoint_Manifest.csv"

R2R2_POINTS_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_"
    "Boundary_Audit_Point_Checkpoints"
)

O2_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution"
)
O2_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz"
O2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Artifact_Manifest.csv"

A2E_REL = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
    "Controlled_Adaptive_Feasibility_Preserving_Stabilized_Coupled_Execution"
)
RECOVERY_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Recovery_Checkpoints"
)
FAIL_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_SCIENTIFIC_FAIL"
BLOCK_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_BLOCKED"

FINAL_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Summary.json"
FINAL_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Certified_Nonlinear_Fixed_Point_State.npz"
FINAL_NONLIN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Nonlinear_Telemetry.csv"
FINAL_ASSIGN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Assignment_Stage_Telemetry.csv"
FINAL_LINE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Line_Search_Telemetry.csv"
FINAL_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Decision_Contract.json"
FINAL_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Final_Gate_Matrix.csv"
FINAL_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Artifact_Manifest.csv"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any):
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
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def array_sha256(a: np.ndarray) -> str:
    aa = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(aa.dtype).encode("ascii"))
    h.update(b"|")
    h.update(repr(tuple(aa.shape)).encode("ascii"))
    h.update(b"|")
    h.update(memoryview(aa).cast("B"))
    return h.hexdigest()


def point_names(prefix: str, iteration: int, omega_index: int) -> tuple[str, str, str]:
    stem = f"{prefix}_Iteration_{iteration:03d}_Omega_{omega_index:04d}_of_{LINE_SEARCH_DEN}"
    return stem + "_State.npz", stem + "_Result.json", stem + "_Manifest.csv"


def r2r2_point_names(index: int) -> tuple[str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_"
        f"Omega_{index:04d}_of_{LINE_SEARCH_DEN}"
    )
    return stem + "_State.npz", stem + "_Result.json", stem + "_Manifest.csv"


def stage_names(iteration: int, stage: int) -> tuple[str, str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
        f"Iteration_{iteration:03d}_Stage_{stage}"
    )
    return (
        stem + "_Resume_State.npz",
        stem + "_Resume_Metadata.json",
        stem + "_HiGHS_Basis.bas",
        stem + "_Manifest.csv",
    )


def map_names(iteration: int) -> tuple[str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
        f"Iteration_{iteration:03d}_Physical_Map_Candidate"
    )
    return stem + ".npz", stem + ".json", stem + "_Manifest.csv"


def accepted_names(iteration: int) -> tuple[str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
        f"Iteration_{iteration:03d}_Computational_Iterate_Accepted"
    )
    return stem + ".npz", stem + ".json", stem + "_Manifest.csv"


def recovery_dir(root: Path, kind: str, iteration: int) -> Path:
    return root / kind / f"iteration_{iteration:03d}"


def manifest_valid(r3, d: Path, manifest_name: str, expected: set[str]) -> bool:
    if not d.is_dir() or not (d / manifest_name).is_file():
        return False
    try:
        return set(r3.verify_manifest(d, manifest_name)) == expected
    except Exception:
        return False


def status_code_payload(basis) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    col_names = [str(x).split(".")[-1] for x in basis.col_status]
    row_names = [str(x).split(".")[-1] for x in basis.row_status]
    names = sorted(set(col_names) | set(row_names))
    if len(names) > 255:
        raise GateError("basis_status_vocabulary_too_large")
    mapping = {name: i for i, name in enumerate(names)}
    col = np.asarray([mapping[n] for n in col_names], dtype=np.uint8)
    row = np.asarray([mapping[n] for n in row_names], dtype=np.uint8)
    return col, row, mapping


def decode_status_names(codes: np.ndarray, mapping: dict[str, int]) -> list[str]:
    inv = {int(v): k for k, v in mapping.items()}
    return [inv[int(x)] for x in np.asarray(codes).ravel()]


def basis_matches_checkpoint(highspy, basis, col_codes, row_codes, mapping) -> bool:
    actual_col = [str(x).split(".")[-1] for x in basis.col_status]
    actual_row = [str(x).split(".")[-1] for x in basis.row_status]
    return (
        actual_col == decode_status_names(col_codes, mapping)
        and actual_row == decode_status_names(row_codes, mapping)
    )


def highspy_basis_roundtrip_self_test(highspy) -> dict[str, Any]:
    # Tiny deterministic LP: min x, x >= 1.
    lp = highspy.HighsLp()
    lp.num_col_ = 1
    lp.num_row_ = 1
    lp.sense_ = highspy.ObjSense.kMinimize
    lp.col_cost_ = np.asarray([1.0], dtype=np.float64)
    lp.col_lower_ = np.asarray([0.0], dtype=np.float64)
    lp.col_upper_ = np.asarray([highspy.kHighsInf], dtype=np.float64)
    lp.row_lower_ = np.asarray([1.0], dtype=np.float64)
    lp.row_upper_ = np.asarray([highspy.kHighsInf], dtype=np.float64)
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.asarray([0, 1], dtype=np.int64)
    lp.a_matrix_.index_ = np.asarray([0], dtype=np.int64)
    lp.a_matrix_.value_ = np.asarray([1.0], dtype=np.float64)

    h1 = highspy.Highs()
    h1.setOptionValue("output_flag", False)
    if h1.passModel(lp) == highspy.HighsStatus.kError:
        raise GateError("basis_selftest_passModel_1")
    if h1.run() == highspy.HighsStatus.kError:
        raise GateError("basis_selftest_run_1")
    if h1.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise GateError("basis_selftest_not_optimal_1")
    b = h1.getBasis()
    x1 = float(h1.getSolution().col_value[0])
    obj1 = float(h1.getObjectiveValue())

    h2 = highspy.Highs()
    h2.setOptionValue("output_flag", False)
    if h2.passModel(lp) == highspy.HighsStatus.kError:
        raise GateError("basis_selftest_passModel_2")
    sb = h2.setBasis(b)
    if sb == highspy.HighsStatus.kError:
        raise GateError("basis_selftest_setBasis_rejected")
    if h2.run() == highspy.HighsStatus.kError:
        raise GateError("basis_selftest_run_2")
    if h2.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise GateError("basis_selftest_not_optimal_2")
    x2 = float(h2.getSolution().col_value[0])
    obj2 = float(h2.getObjectiveValue())
    if abs(x1 - x2) > 1.0e-12 or abs(obj1 - obj2) > 1.0e-12:
        raise GateError("basis_selftest_solution_mismatch")

    if not hasattr(h2, "writeBasis") or not hasattr(h2, "readBasis"):
        raise GateError("highspy_basis_file_API_unavailable")
    with tempfile.TemporaryDirectory() as td:
        bp = Path(td) / "tiny.bas"
        ws = h2.writeBasis(str(bp))
        if ws == highspy.HighsStatus.kError or not bp.is_file():
            raise GateError("basis_selftest_writeBasis_failure")
        h3 = highspy.Highs()
        h3.setOptionValue("output_flag", False)
        if h3.passModel(lp) == highspy.HighsStatus.kError:
            raise GateError("basis_selftest_passModel_3")
        rs = h3.readBasis(str(bp))
        if rs == highspy.HighsStatus.kError:
            raise GateError("basis_selftest_readBasis_failure")
        if h3.run() == highspy.HighsStatus.kError:
            raise GateError("basis_selftest_run_3")
        if h3.getModelStatus() != highspy.HighsModelStatus.kOptimal:
            raise GateError("basis_selftest_not_optimal_3")
        x3 = float(h3.getSolution().col_value[0])
        obj3 = float(h3.getObjectiveValue())
        if abs(x1 - x3) > 1.0e-12 or abs(obj1 - obj3) > 1.0e-12:
            raise GateError("basis_file_roundtrip_solution_mismatch")

    return {
        "getBasis_setBasis_roundtrip": True,
        "writeBasis_readBasis_roundtrip": True,
        "test_solution": x1,
        "test_objective": obj1,
    }


class RestartableLexSolver:
    def __init__(
        self,
        *,
        component_id: int,
        comp: dict[str, Any],
        model_data: dict[str, Any],
        highspy,
        o2,
        o3r6,
        recovery_root: Path,
        graph_identity: str,
        output_flag: bool,
    ):
        self.component_id = int(component_id)
        self.comp = comp
        self.md = model_data
        self.highspy = highspy
        self.o2 = o2
        self.o3r6 = o3r6
        self.recovery_root = recovery_root
        self.graph_identity = graph_identity
        self.output_flag = bool(output_flag)
        self.h = highspy.Highs()
        self.h.setOptionValue("solver", "simplex")
        self.h.setOptionValue("presolve", "on")
        self.h.setOptionValue("output_flag", bool(output_flag))
        if self.h.passModel(model_data["lp"]) == highspy.HighsStatus.kError:
            raise GateError(f"component_{component_id}_passModel_error")
        self.inf = highspy.kHighsInf
        self.n = int(model_data["n"])
        self.m = int(model_data["m"])
        self.ncol = int(model_data["ncol"])
        self.nrow = int(model_data["nrow"])
        self.up_idx = np.arange(model_data["up0"], model_data["up0"] + self.m, dtype=np.int32)
        self.uq_idx = np.arange(model_data["uq0"], model_data["uq0"] + self.m, dtype=np.int32)
        self.cell_rows = model_data["ncv"] + np.arange(model_data["ncell"], dtype=np.int32)
        self.previous_basis = None
        self.local_available = None

    def _activate_parent(self):
        if not self.m:
            return
        md, o2, hs = self.md, self.o2, self.highspy
        o2.set_col_bounds(
            self.h, hs, self.up_idx,
            np.zeros(self.m), np.full(self.m, self.inf),
        )
        p_rows = np.concatenate([
            np.arange(md["r_pp0"], md["r_pp0"] + self.m, dtype=np.int32),
            np.arange(md["r_pm0"], md["r_pm0"] + self.m, dtype=np.int32),
        ])
        o2.set_row_bounds(
            self.h, hs, p_rows,
            np.full(2 * self.m, -self.inf),
            np.concatenate([self.comp["target"], -self.comp["target"]]),
        )

    def _activate_raw(self):
        if not self.m:
            return
        md, o2, hs = self.md, self.o2, self.highspy
        o2.set_col_bounds(
            self.h, hs, self.uq_idx,
            np.zeros(self.m), np.full(self.m, self.inf),
        )
        q_rows = np.concatenate([
            np.arange(md["r_qp0"], md["r_qp0"] + self.m, dtype=np.int32),
            np.arange(md["r_qm0"], md["r_qm0"] + self.m, dtype=np.int32),
        ])
        o2.set_row_bounds(
            self.h, hs, q_rows,
            np.full(2 * self.m, -self.inf),
            np.concatenate([self.comp["qtarget"], -self.comp["qtarget"]]),
        )

    def reset_iteration(self, available_global: np.ndarray):
        md, o2, hs = self.md, self.o2, self.highspy
        self.local_available = np.asarray(
            available_global[self.comp["cell_ids"]], dtype=np.float64
        )
        o2.set_row_bounds(
            self.h, hs, self.cell_rows,
            np.full(len(self.cell_rows), -self.inf),
            self.local_available,
        )
        agg_rows = np.asarray(
            [md["r_shell"], md["r_extension"], md["r_parent"], md["r_raw"]],
            dtype=np.int32,
        )
        o2.set_row_bounds(
            self.h, hs, agg_rows,
            np.full(4, -self.inf),
            np.full(4, self.inf),
        )
        if self.m:
            zero = np.zeros(self.m)
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
                np.full(abs_rows.size, -self.inf),
                np.full(abs_rows.size, self.inf),
            )
        self.previous_basis = None

    def stage_cost(self, stage: int) -> np.ndarray:
        cost = np.zeros(self.ncol, dtype=np.float64)
        if stage == 1:
            cost[:self.n] = self.comp["is_shell"].astype(np.float64)
        elif stage == 2:
            cost[:self.n] = self.comp["is_extension"].astype(np.float64)
        elif stage == 3:
            if self.m:
                cost[self.md["up0"]: self.md["up0"] + self.m] = 1.0
        elif stage == 4:
            if self.m:
                cost[self.md["uq0"]: self.md["uq0"] + self.m] = 1.0
        elif stage == 5:
            cost[:self.n] = self.comp["global_rank"]
        else:
            raise GateError(f"invalid_stage:{stage}")
        return cost

    def stage_name(self, stage: int) -> str:
        return {
            1: "MINIMUM_H2_SECOND_SHELL_MASS",
            2: "MINIMUM_TOTAL_EXTENSION_MASS",
            3: "MINIMUM_PARENT_OWNERSHIP_L1",
            4: "MINIMUM_RAW_EVENT_EOS_L1",
            5: "DETERMINISTIC_GLOBAL_PAIR_RANK_TIEBREAK",
        }[stage]

    def objective_from_solution(self, stage: int, sol: np.ndarray) -> float:
        x = sol[:self.n]
        if stage == 1:
            return float(np.sum(x[self.comp["is_shell"]]))
        if stage == 2:
            return float(np.sum(x[self.comp["is_extension"]]))
        if stage == 3:
            return float(np.sum(sol[self.md["up0"]: self.md["up0"] + self.m]))
        if stage == 4:
            return float(np.sum(sol[self.md["uq0"]: self.md["uq0"] + self.m]))
        if stage == 5:
            return float(np.dot(self.comp["global_rank"], x))
        raise GateError(f"invalid_stage:{stage}")

    def apply_completed_stage_freezes(self, objectives: dict[str, float], through_stage: int):
        md = self.md
        if through_stage >= 1:
            v = objectives["stage1_shell_kg"]
            self.h.changeRowBounds(md["r_shell"], -self.inf, v + self.o3r6.objective_tol(v))
        if through_stage >= 2:
            v = objectives["stage2_extension_kg"]
            self.h.changeRowBounds(md["r_extension"], -self.inf, v + self.o3r6.objective_tol(v))
        if through_stage >= 3:
            self._activate_parent()
            v = objectives["stage3_parent_L1_kg"]
            self.h.changeRowBounds(md["r_parent"], -self.inf, v + self.o3r6.objective_tol(v))
        if through_stage >= 4:
            self._activate_raw()
            v = objectives["stage4_raw_L1_kg"]
            self.h.changeRowBounds(md["r_raw"], -self.inf, v + self.o3r6.objective_tol(v))

    def _stage_dir(self, iteration: int, stage: int) -> Path:
        return recovery_dir(self.recovery_root, "lex_stages", iteration) / f"stage_{stage}"

    def _stage_checkpoint_status(self, r3, iteration: int, stage: int) -> str:
        d = self._stage_dir(iteration, stage)
        sn, mn, bn, man = stage_names(iteration, stage)
        if not d.exists():
            return "absent"
        if manifest_valid(r3, d, man, {sn, mn, bn}):
            return "valid"
        raise GateError(f"invalid_or_partial_stage_checkpoint:iteration={iteration},stage={stage}")

    def highest_valid_stage(self, r3, iteration: int) -> int:
        highest = 0
        seen_absent = False
        for stage in range(1, 6):
            st = self._stage_checkpoint_status(r3, iteration, stage)
            if st == "valid":
                if seen_absent:
                    raise GateError(
                        f"noncontiguous_stage_checkpoints:iteration={iteration},stage={stage}"
                    )
                highest = stage
            else:
                seen_absent = True
        return highest

    def load_stage_checkpoint(self, r3, iteration: int, stage: int):
        d = self._stage_dir(iteration, stage)
        sn, mn, bn, man = stage_names(iteration, stage)
        r3.verify_manifest(d, man)
        meta = r3.load_json(d / mn)
        with np.load(d / sn, allow_pickle=False) as z:
            state = {k: np.asarray(z[k]).copy() for k in z.files}
        return d, meta, state, d / bn

    def publish_stage_checkpoint(
        self,
        *,
        r3,
        iteration: int,
        stage: int,
        sol: np.ndarray,
        objective: float,
        objectives: dict[str, float],
        telemetry: dict[str, Any],
        capacity_hash: str,
    ):
        d = self._stage_dir(iteration, stage)
        d.mkdir(parents=True, exist_ok=True)
        sn, mn, bn, man = stage_names(iteration, stage)

        basis = self.h.getBasis()
        col_codes, row_codes, mapping = status_code_payload(basis)
        state = {
            "full_solution": np.asarray(sol, dtype=np.float64),
            "basis_col_status_codes": col_codes,
            "basis_row_status_codes": row_codes,
        }
        meta = {
            "milestone": MILESTONE,
            "checkpoint_classification": "COMPUTATIONAL_RESUME_ONLY",
            "nonlinear_iteration": int(iteration),
            "component_id": self.component_id,
            "completed_stage": int(stage),
            "stage_name": self.stage_name(stage),
            "stage_objective": float(objective),
            "objectives_through_stage": {k: float(v) for k, v in objectives.items()},
            "capacity_vector_sha256": capacity_hash,
            "graph_identity_sha256": self.graph_identity,
            "model": {
                "edges": self.n,
                "E0_edges": self.m,
                "variables": self.ncol,
                "rows": self.nrow,
                "CVs": int(self.md["ncv"]),
                "cells": int(self.md["ncell"]),
                "nonzeros": int(self.md["nnz"]),
            },
            "basis_status_mapping": mapping,
            "telemetry": telemetry,
            "physical_state_authority": False,
            "physical_time_advanced": False,
        }

        r3.immutable_publish(
            d,
            {
                sn: self.o3r6.deterministic_npz_bytes(state),
                mn: r3.json_bytes(meta),
            },
        )

        # Basis file is generated by HiGHS; publish it immutably and manifest it last.
        if not (d / bn).exists():
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td) / bn
                ws = self.h.writeBasis(str(tmp))
                if ws == self.highspy.HighsStatus.kError or not tmp.is_file():
                    raise GateError(
                        f"writeBasis_failed:iteration={iteration},stage={stage}"
                    )
                (d / bn).write_bytes(tmp.read_bytes())

        rows = [
            {"file": n, "sha256": r3.sha256_file(d / n), "bytes": (d / n).stat().st_size}
            for n in (sn, mn, bn)
        ]
        r3.immutable_publish(d, {man: r3.csv_bytes(rows)})
        if not manifest_valid(r3, d, man, {sn, mn, bn}):
            raise GateError(
                f"stage_checkpoint_publish_verification_failed:iteration={iteration},stage={stage}"
            )
        print(
            f"[CHECKPOINT] iteration={iteration:03d} stage={stage} "
            f"{self.stage_name(stage)} COMPUTATIONAL_RESUME_ONLY"
        )
        sys.stdout.flush()

    def recertify_loaded_stage(
        self,
        *,
        iteration: int,
        stage: int,
        meta: dict[str, Any],
        state: dict[str, np.ndarray],
        capacity_hash: str,
        cv_tol: float,
        grid_tol: float,
    ) -> np.ndarray:
        if meta.get("checkpoint_classification") != "COMPUTATIONAL_RESUME_ONLY":
            raise GateError("stage_checkpoint_classification_mismatch")
        if int(meta.get("nonlinear_iteration", -1)) != iteration:
            raise GateError("stage_checkpoint_iteration_mismatch")
        if int(meta.get("completed_stage", -1)) != stage:
            raise GateError("stage_checkpoint_stage_mismatch")
        if meta.get("capacity_vector_sha256") != capacity_hash:
            raise GateError("stage_checkpoint_capacity_hash_mismatch")
        if meta.get("graph_identity_sha256") != self.graph_identity:
            raise GateError("stage_checkpoint_graph_identity_mismatch")

        sol = np.asarray(state["full_solution"], dtype=np.float64)
        if sol.shape != (self.ncol,):
            raise GateError("stage_checkpoint_solution_shape_mismatch")
        x = sol[:self.n]
        cv_sum = np.bincount(
            self.comp["cv_inv"], weights=x, minlength=len(self.comp["cv_ids"])
        ).astype(np.float64)
        cell_sum = np.bincount(
            self.comp["cell_inv"], weights=x, minlength=len(self.comp["cell_ids"])
        ).astype(np.float64)
        cv_linf = float(np.max(np.abs(cv_sum - self.comp["demand"])))
        cap_excess = float(np.max(cell_sum - self.local_available))
        if cv_linf > cv_tol or cap_excess > grid_tol or float(np.min(x)) < -1.0e-8:
            raise GateError("stage_checkpoint_primal_recertification_failure")

        objective = self.objective_from_solution(stage, sol)
        expected = float(meta["stage_objective"])
        if abs(objective - expected) > self.o3r6.objective_tol(expected):
            raise GateError(
                f"stage_checkpoint_objective_recertification_failure:{objective}:{expected}"
            )
        return sol

    def restore_stage_basis(
        self,
        *,
        r3,
        iteration: int,
        stage: int,
        meta: dict[str, Any],
        state: dict[str, np.ndarray],
        basis_path: Path,
    ):
        rs = self.h.readBasis(str(basis_path))
        if rs == self.highspy.HighsStatus.kError:
            raise GateError(
                f"stage_basis_read_failure:iteration={iteration},stage={stage}"
            )
        basis = self.h.getBasis()
        if not basis_matches_checkpoint(
            self.highspy,
            basis,
            state["basis_col_status_codes"],
            state["basis_row_status_codes"],
            meta["basis_status_mapping"],
        ):
            raise GateError(
                f"stage_basis_status_recertification_failure:iteration={iteration},stage={stage}"
            )
        self.previous_basis = basis

    def solve_one_stage(
        self,
        *,
        iteration: int,
        stage: int,
        cv_tol: float,
        grid_tol: float,
    ) -> tuple[np.ndarray, float, dict[str, Any]]:
        if stage == 3:
            self._activate_parent()
        elif stage == 4:
            self._activate_raw()

        cost = self.stage_cost(stage)
        self.o2.set_full_costs(self.h, self.highspy, cost)
        warm_requested = self.previous_basis is not None
        warm_applied = False
        warm_status = "not_requested"
        if warm_requested:
            sb = self.h.setBasis(self.previous_basis)
            if sb == self.highspy.HighsStatus.kError:
                raise GateError(
                    f"basis_rejected_after_validated_restore:iteration={iteration},stage={stage}"
                )
            warm_applied = True
            warm_status = str(sb)

        t0 = time.perf_counter()
        rs = self.h.run()
        wall = time.perf_counter() - t0
        if rs == self.highspy.HighsStatus.kError:
            raise GateError(
                f"highs_run_error:iteration={iteration},stage={stage}"
            )
        model_status = self.h.getModelStatus()
        model_text = self.h.modelStatusToString(model_status)
        if model_status != self.highspy.HighsModelStatus.kOptimal:
            if "infeasible" in model_text.lower():
                raise ScientificFail(
                    "frozen_E2_lexicographic_assignment_infeasible",
                    {
                        "iteration": iteration,
                        "component": self.component_id,
                        "stage": stage,
                        "stage_name": self.stage_name(stage),
                        "model_status": model_text,
                    },
                )
            raise GateError(
                f"stage_not_optimal:iteration={iteration},stage={stage},status={model_text}"
            )

        sol = np.asarray(list(self.h.getSolution().col_value), dtype=np.float64)
        x = sol[:self.n]
        cv_sum = np.bincount(
            self.comp["cv_inv"], weights=x, minlength=len(self.comp["cv_ids"])
        ).astype(np.float64)
        cell_sum = np.bincount(
            self.comp["cell_inv"], weights=x, minlength=len(self.comp["cell_ids"])
        ).astype(np.float64)
        cv_linf = float(np.max(np.abs(cv_sum - self.comp["demand"])))
        cap_excess = float(np.max(cell_sum - self.local_available))
        min_x = float(np.min(x))
        if cv_linf > cv_tol or cap_excess > grid_tol or min_x < -1.0e-8:
            raise ScientificFail(
                "assignment_stage_primal_certification_failure",
                {
                    "iteration": iteration,
                    "stage": stage,
                    "CV_Linf_kg": cv_linf,
                    "max_capacity_excess_kg": cap_excess,
                    "minimum_x_kg": min_x,
                },
            )

        objective = self.objective_from_solution(stage, sol)
        if stage == 1:
            self.h.changeRowBounds(
                self.md["r_shell"], -self.inf,
                objective + self.o3r6.objective_tol(objective),
            )
        elif stage == 2:
            self.h.changeRowBounds(
                self.md["r_extension"], -self.inf,
                objective + self.o3r6.objective_tol(objective),
            )
        elif stage == 3:
            self.h.changeRowBounds(
                self.md["r_parent"], -self.inf,
                objective + self.o3r6.objective_tol(objective),
            )
        elif stage == 4:
            self.h.changeRowBounds(
                self.md["r_raw"], -self.inf,
                objective + self.o3r6.objective_tol(objective),
            )

        self.previous_basis = self.h.getBasis()
        info = self.h.getInfo()
        telemetry = {
            "nonlinear_iteration": int(iteration),
            "component_id": self.component_id,
            "stage": int(stage),
            "stage_name": self.stage_name(stage),
            "warm_start_requested": bool(warm_requested),
            "warm_start_applied": bool(warm_applied),
            "warm_start_status": warm_status,
            "model_status": model_text,
            "wall_time_s": float(wall),
            "objective": float(objective),
            "simplex_iterations": int(getattr(info, "simplex_iteration_count", -1)),
            "ipm_iterations": int(getattr(info, "ipm_iteration_count", -1)),
            "CV_equality_Linf_kg": cv_linf,
            "max_capacity_excess_kg": cap_excess,
            "minimum_x_kg": min_x,
        }
        print(
            f"[PASS] iter={iteration:03d} stage={stage} {self.stage_name(stage)} "
            f"wall={wall:.3f}s obj={objective:.12g} "
            f"CV={cv_linf:.3e} cap={cap_excess:.3e} warm={warm_applied}"
        )
        sys.stdout.flush()
        return sol, objective, telemetry

    def solve_iteration(
        self,
        *,
        r3,
        iteration: int,
        available_global: np.ndarray,
        cv_tol: float,
        grid_tol: float,
        prior_stage5_basis: Path | None,
    ) -> dict[str, Any]:
        self.reset_iteration(available_global)
        capacity_hash = array_sha256(np.asarray(available_global, dtype=np.float64))

        highest = self.highest_valid_stage(r3, iteration)
        objectives: dict[str, float] = {}
        telemetry: list[dict[str, Any]] = []
        final_sol = None

        if highest:
            d, meta, state, bp = self.load_stage_checkpoint(r3, iteration, highest)
            objectives = {
                str(k): float(v)
                for k, v in meta["objectives_through_stage"].items()
            }
            self.apply_completed_stage_freezes(objectives, highest)
            final_sol = self.recertify_loaded_stage(
                iteration=iteration,
                stage=highest,
                meta=meta,
                state=state,
                capacity_hash=capacity_hash,
                cv_tol=cv_tol,
                grid_tol=grid_tol,
            )
            self.restore_stage_basis(
                r3=r3, iteration=iteration, stage=highest,
                meta=meta, state=state, basis_path=bp,
            )
            print(
                f"[REUSE] iteration={iteration:03d} completed lex stages 1..{highest}"
            )
            sys.stdout.flush()
        elif prior_stage5_basis is not None and prior_stage5_basis.is_file():
            # Same model dimensions/graph; row/column bounds have already been reset.
            rs = self.h.readBasis(str(prior_stage5_basis))
            if rs == self.highspy.HighsStatus.kError:
                raise GateError(
                    f"prior_iteration_stage5_basis_restore_failure:iteration={iteration}"
                )
            self.previous_basis = self.h.getBasis()
            print(
                f"[REUSE] iteration={iteration:03d} prior iteration Stage-5 basis warm start"
            )

        stage_key = {
            1: "stage1_shell_kg",
            2: "stage2_extension_kg",
            3: "stage3_parent_L1_kg",
            4: "stage4_raw_L1_kg",
            5: "stage5_tiebreak",
        }

        # Recover telemetry from already completed stages.
        for s in range(1, highest + 1):
            _, meta_s, _, _ = self.load_stage_checkpoint(r3, iteration, s)
            telemetry.append(meta_s["telemetry"])

        for stage in range(highest + 1, 6):
            sol, obj, tel = self.solve_one_stage(
                iteration=iteration,
                stage=stage,
                cv_tol=cv_tol,
                grid_tol=grid_tol,
            )
            objectives[stage_key[stage]] = float(obj)
            self.publish_stage_checkpoint(
                r3=r3,
                iteration=iteration,
                stage=stage,
                sol=sol,
                objective=obj,
                objectives=objectives,
                telemetry=tel,
                capacity_hash=capacity_hash,
            )
            telemetry.append(tel)
            final_sol = sol

        if final_sol is None:
            raise GateError("no_final_stage_solution")
        return {
            "edge_idx": self.comp["edge_idx"],
            "x": np.asarray(final_sol[:self.n], dtype=np.float64).copy(),
            "objectives": objectives,
            "telemetry": telemetry,
            "stage5_basis_path": self._stage_dir(iteration, 5) / stage_names(iteration, 5)[2],
        }

    def close(self):
        try:
            self.h.releaseMemory()
        except Exception:
            pass


def self_test() -> None:
    assert GRID == (15, 50, 50)
    assert NCVTOTAL == 215600
    assert EXPECTED_E2 == 3091073
    assert EXPECTED_ACTIVE == 3012452
    assert LINE_SEARCH_DEN == 1024
    assert R2R2_FIRST_FEASIBLE_INDEX == 147
    assert MAX_NONLINEAR_ITERATIONS == 100
    assert len(PARENT_R3_COMMIT) == 40
    print(
        "POSTV16 O3-R6-R4 controlled adaptive stabilized execution structural self-test: PASS"
    )


def main(project_root: Path, drive_root: Path, verbose_solver: bool = False) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    recovery = drive / RECOVERY_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    nonlinear_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []
    solvers: list[RestartableLexSolver] = []

    pressure_solve_executed = False
    assignment_executed = False
    stabilized_iteration_executed = False
    converged = False
    current_iteration = 0

    def gate(name: str, cond: bool, detail: Any = None):
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    def sci_gate(name: str, cond: bool, detail: Any = None):
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise ScientificFail(name, detail)
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    # Never silently rerun a completed formal outcome.
    if (out / FINAL_MANIFEST).is_file():
        print("[PASS] existing immutable O3-R6-R4 PASS output detected; no rerun")
        return 0
    fail_report = failed / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Scientific_Fail_Report.json"
    if fail_report.is_file():
        print("[FAIL] existing immutable O3-R6-R4 scientific FAIL detected; automatic rerun prohibited")
        return 3
    block_report = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Blocked_Report.json"
    if block_report.is_file():
        print("[BLOCK] existing immutable O3-R6-R4 technical/authority block detected")
        return 2

    print("=" * 214)
    print(MILESTONE + " -- CONTROLLED ADAPTIVE FEASIBILITY-PRESERVING STABILIZED COUPLED EXECUTION")
    print("=" * 214)
    print("ONE SAME-TIME EVENT COUPLING EXECUTION AT THE FROZEN EVENT DAY.")
    print("FROZEN E2/H2 SUPPORT. EXACT FIVE-STAGE LEXICOGRAPHIC ASSIGNMENT.")
    print("ADAPTIVE FEASIBILITY-PRESERVING COMPUTATIONAL SATURATION ITERATES ONLY.")
    print("FINAL PASS REQUIRES ORIGINAL UNDAMPED FIXED POINT + FROZEN FINAL CLOSURE.")
    print("NO SUPPORT EXPANSION. NO MASS/CAPACITY RELAXATION. NO DARCY/POLLOCK/TOF. NO TIME ADVANCE.")
    print()

    try:
        # --------------------------------------------------------------------------------------
        # Repository/source authority and frozen R3 contract.
        # --------------------------------------------------------------------------------------
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R3_commit", parent == PARENT_R3_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        r3 = load_module(root / R3, "postv16_o3r6r4_r3")
        o3r6 = load_module(root / O3R6, "postv16_o3r6r4_o3r6")
        o3r4 = load_module(root / O3R4, "postv16_o3r6r4_o3r4")
        o2 = load_module(root / O2, "postv16_o3r6r4_o2")
        a2e = load_module(root / A2E, "postv16_o3r6r4_a2e")
        r2phys = load_module(root / R2PHYS, "postv16_o3r6r4_r2")
        sg2 = load_module(root / SG2, "postv16_o3r6r4_sg2")
        sg3 = load_module(root / SG3, "postv16_o3r6r4_sg3")
        r3r2r1 = load_module(root / R3R2R1, "postv16_o3r6r4_r3r2r1")

        import highspy
        from scipy.sparse import coo_matrix

        gate("highspy_version_exact_1_15_1", highspy.Highs().version() == "1.15.1", highspy.Highs().version())

        stage = "R3_contract_binding"
        r3d = drive / R3_REL
        gate("R3_output_present", r3d.is_dir(), str(r3d))
        m3 = r3.verify_manifest(r3d, R3_MANIFEST)
        gate("R3_manifest_exact_7", len(m3) == 7, len(m3))
        gate("R3_manifest_payload_file_set_exact", set(m3) == EXPECTED_R3_FILES, sorted(m3))

        s3 = r3.load_json(r3d / R3_SUMMARY)
        op3 = r3.load_json(r3d / R3_OPERATOR)
        cv3 = r3.load_json(r3d / R3_CONVERGENCE)
        cp3 = r3.load_json(r3d / R3_CHECKPOINT)
        d3 = r3.load_json(r3d / R3_DECISION)

        gate(
            "R3_stabilization_semantics_exact",
            s3.get("design_only") is True
            and s3.get("stabilization_operator_frozen") is True
            and s3.get("adaptive_line_search_frozen") is True
            and s3.get("original_undamped_convergence_preserved") is True
            and s3.get("support_domain_changed") is False
            and s3.get("physical_time_advanced") is False
            and op3.get("operator_id") == "PAD_STREAM_ADAPTIVE_FEASIBILITY_PRESERVING_FIXED_POINT_V1"
            and op3.get("support_domain") == "unchanged frozen E2/H2"
            and int(op3.get("max_nonlinear_iterations", -1)) == MAX_NONLINEAR_ITERATIONS
            and cv3.get("convergence_id") == "PAD_STREAM_ORIGINAL_UNDAMPED_FIXED_POINT_CLOSURE_V1"
            and cp3.get("policy_id") == "PAD_STREAM_DURABLE_CHECKPOINT_POLICY_V2_STABILIZED_SOLVER",
        )
        gate(
            "R3_authorizes_R4_only",
            d3.get("O3R6R4_controlled_execution_authorized") is True
            and d3.get("O3R6R4_must_use_frozen_R3_semantics") is True
            and d3.get("fixed_global_damping_authorized") is False
            and d3.get("support_expansion_authorized") is False
            and d3.get("capacity_relaxation_authorized") is False
            and d3.get("per_CV_mass_relaxation_authorized") is False
            and d3.get("O3R7_authorized") is False
            and d3.get("R3R3R4_authorized") is False,
        )

        # Basis restart gate happens before any expensive assignment solve.
        stage = "basis_roundtrip_gate"
        basis_gate = highspy_basis_roundtrip_self_test(highspy)
        gate("highspy_basis_roundtrip_gate", bool(basis_gate["getBasis_setBasis_roundtrip"]), basis_gate)
        gate("highspy_basis_file_roundtrip_gate", bool(basis_gate["writeBasis_readBasis_roundtrip"]), basis_gate)

        # --------------------------------------------------------------------------------------
        # Bind immutable O2/A2-E state and bootstrap R1-R1 physical map / R2-R2 accepted iterate.
        # --------------------------------------------------------------------------------------
        stage = "state_authority_binding"
        o2d = drive / O2_REL
        r3.verify_manifest(o2d, O2_MANIFEST)
        with np.load(o2d / O2_STATE, allow_pickle=False) as z:
            event_grid0 = np.asarray(z["event_grid_component_mass_kg"], dtype=np.float64)
            residual_grid = np.asarray(z["frozen_residual_grid_component_mass_kg"], dtype=np.float64)
            event_cv_mass = np.asarray(z["event_CV_component_mass_kg"], dtype=np.float64)
            e0_cv = np.asarray(z["E0_pair_cv_id"], dtype=np.int64)
            e0_cell = np.asarray(z["E0_pair_flat_cell"], dtype=np.int64)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            is_e0 = np.asarray(z["E2_pair_is_E0"], dtype=bool)
            is_e1 = np.asarray(z["E2_pair_is_E1"], dtype=bool)
            target0 = np.asarray(z["E0_parent_continuity_target_kg"], dtype=np.float64)
            qtarget0 = np.asarray(z["E0_raw_event_EOS_target_kg"], dtype=np.float64)
            parent_pressure = np.asarray(z["parent_pressure_psi"], dtype=np.float64)
            grid_pv = np.asarray(z["grid_pore_volume_m3"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        a2d = drive / A2E_REL
        r3.verify_manifest(a2d, A2E_MANIFEST)
        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)

        r1cp = drive / R1R1_CP_REL
        r3.verify_manifest(r1cp, R1R1_CP1_MANIFEST)
        cp1_meta = r3.load_json(r1cp / R1R1_CP1_META)
        with np.load(r1cp / R1R1_CP1_STATE, allow_pickle=False) as z:
            P1 = np.asarray(z["P1_pressure_psi"], dtype=np.float64)
            cap1 = np.asarray(z["P1_cell_capacity_kg"], dtype=np.float64)
            x1 = np.asarray(z["iteration1_E2_assignment_mass_kg"], dtype=np.float64)
            mapped1 = np.asarray(z["iteration1_event_mapped_grid_mass_kg"], dtype=np.float64)
            m1 = np.asarray(z["iteration1_event_grid_mass_kg"], dtype=np.float64)
            S1 = np.asarray(z["iteration1_saturation"], dtype=np.float64)
        gate(
            "R1R1_physical_map_candidate_certified",
            cp1_meta.get("checkpoint_kind") == "CERTIFIED_NONLINEAR_ITERATION_STATE"
            and cp1_meta.get("scientific_state_certified") is True
            and x1.shape == (EXPECTED_E2,)
            and P1.shape == GRID and S1.shape == GRID and m1.shape == GRID,
        )

        r2root = drive / R2R2_POINTS_REL
        r2dir = r2root / f"omega_{R2R2_FIRST_FEASIBLE_INDEX:04d}_of_{LINE_SEARCH_DEN}"
        r2sn, r2rn, r2mn = r2r2_point_names(R2R2_FIRST_FEASIBLE_INDEX)
        gate(
            "R2R2_first_feasible_checkpoint_present",
            manifest_valid(r3, r2dir, r2mn, {r2sn, r2rn}),
            str(r2dir),
        )
        r2res = r3.load_json(r2dir / r2rn)
        with np.load(r2dir / r2sn, allow_pickle=False) as z:
            S_iter = np.asarray(z["diagnostic_saturation"], dtype=np.float64)
            P_iter_checkpoint = np.asarray(z["pressure_psi"], dtype=np.float64)
            cap_iter_checkpoint = np.asarray(z["cell_capacity_kg"], dtype=np.float64)
        gate(
            "R2R2_first_feasible_checkpoint_exact",
            r2res.get("exact_frozen_E2_feasible") is True
            and int(r2res.get("omega_index", -1)) == R2R2_FIRST_FEASIBLE_INDEX
            and abs(float(r2res.get("omega", -1.0)) - R2R2_FIRST_FEASIBLE_OMEGA) <= 1.0e-15,
        )

        demand = event_cv_mass.reshape(-1).astype(np.float64)
        residual = residual_grid.reshape(-1).astype(np.float64)
        cv_tol = max(1.0e-6, 1.0e-10 * max(float(np.max(np.abs(demand))), 1.0))

        # Exact graph.
        e0_idx = np.flatnonzero(is_e0).astype(np.int64)
        gate("E0_count_exact", e0_idx.size == EXPECTED_E0, int(e0_idx.size))
        support = {
            "e2_cv": e2_cv,
            "e2_cell": e2_cell,
            "is_e0": is_e0,
            "is_e1": is_e1,
            "is_h2_shell": (~is_e0) & (~is_e1),
            "is_any_extension": (~is_e0),
        }
        target_by_edge = np.zeros(EXPECTED_E2, dtype=np.float64)
        qtarget_by_edge = np.zeros(EXPECTED_E2, dtype=np.float64)
        target_by_edge[e0_idx] = target0
        qtarget_by_edge[e0_idx] = qtarget0
        prep = o2.preprocess_active_graph(
            e2_cv=e2_cv,
            e2_cell=e2_cell,
            demand=demand,
            available_raw=np.ones(NCELL, dtype=np.float64),
        )
        gate("active_frozen_E2_edge_count_exact", prep["active_edge_count"] == EXPECTED_ACTIVE, prep["active_edge_count"])
        gate("single_connected_component_exact", prep["component_count"] == 1, prep["component_count"])
        graph_identity = array_sha256(np.asarray(prep["sorted_edge_idx"], dtype=np.int64))

        # Pressure physics.
        permeability_md = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        def pressure_step(saturation: np.ndarray) -> tuple[np.ndarray, float]:
            nonlocal pressure_solve_executed
            mobility = a2e.spatial_mobility(
                saturation, grid_nw, grid_no, grid_krw, grid_kro
            )
            tx, ty, tz, _ = r3r2r1.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, _ = r3r2r1.assemble_updated_pressure_system(
                sg3, permeability_md, tx, ty, tz, mobility["lambda_total"]
            )
            _ppa, ppsi, linear_residual = r3r2r1.solve_updated_pressure(sg3, A, b)
            pressure_solve_executed = True
            return np.asarray(ppsi, dtype=np.float64), float(linear_residual)

        # Bootstrap recertification from R2-R2 point.
        p_boot, boot_resid = pressure_step(S_iter)
        gate("bootstrap_pressure_linear_residual", boot_resid < PRESSURE_LINEAR_REL_RESIDUAL_MAX, boot_resid)
        gate("bootstrap_pressure_matches_R2R2", o3r6.max_abs(p_boot - P_iter_checkpoint) <= 1.0e-8, o3r6.max_abs(p_boot - P_iter_checkpoint))
        cap_boot = np.asarray(
            a2e.local_mass(r2phys, np.full(GRID, INJECTED), p_boot, p_ref, grid_pv),
            dtype=np.float64,
        )
        gate("bootstrap_capacity_matches_R2R2", o3r6.max_abs(cap_boot - cap_iter_checkpoint) <= 1.0e-8, o3r6.max_abs(cap_boot - cap_iter_checkpoint))

        # Bootstrap accepted iterate checkpoint (iteration 0) is local R4 recovery authority.
        bootstrap_dir = recovery_dir(recovery, "accepted_iterates", 0)
        bsn, bmn, bman = accepted_names(0)
        if bootstrap_dir.exists() and not manifest_valid(r3, bootstrap_dir, bman, {bsn, bmn}):
            raise GateError("invalid_bootstrap_accepted_iterate_checkpoint")
        if not bootstrap_dir.exists():
            r3.immutable_publish(
                bootstrap_dir,
                {
                    bsn: o3r6.deterministic_npz_bytes({
                        "S_iter_next": S_iter,
                        "selected_omega_index": np.asarray(R2R2_FIRST_FEASIBLE_INDEX, dtype=np.int64),
                        "selected_omega": np.asarray(R2R2_FIRST_FEASIBLE_OMEGA),
                        "selected_trial_pressure_psi": p_boot,
                        "previous_physical_map_pressure_psi": P1,
                        "previous_physical_map_mass_kg": m1,
                    }),
                    bmn: r3.json_bytes({
                        "milestone": MILESTONE,
                        "checkpoint_classification": "COMPUTATIONAL_ITERATE_ACCEPTED",
                        "source": "R1R1 physical map + R2R2 omega=147/1024 certified point",
                        "completed_iteration": 0,
                        "next_iteration": 1,
                        "selected_omega_index": R2R2_FIRST_FEASIBLE_INDEX,
                        "selected_omega": R2R2_FIRST_FEASIBLE_OMEGA,
                        "provisional_converged": False,
                        "physical_state_authority": False,
                        "physical_time_advanced": False,
                    }),
                },
            )
            rows = [
                {"file": n, "sha256": r3.sha256_file(bootstrap_dir / n), "bytes": (bootstrap_dir / n).stat().st_size}
                for n in (bsn, bmn)
            ]
            r3.immutable_publish(bootstrap_dir, {bman: r3.csv_bytes(rows)})
        gate("bootstrap_accepted_iterate_checkpoint_valid", manifest_valid(r3, bootstrap_dir, bman, {bsn, bmn}))

        # --------------------------------------------------------------------------------------
        # Model build: one exact frozen-E2 component.
        # --------------------------------------------------------------------------------------
        stage = "persistent_model_build"
        parent_cap = np.asarray(
            a2e.local_mass(r2phys, np.full(GRID, INJECTED), parent_pressure, p_ref, grid_pv),
            dtype=np.float64,
        )
        initial_available = np.maximum(parent_cap.reshape(-1) - residual, 0.0)
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
            solvers.append(
                RestartableLexSolver(
                    component_id=cid,
                    comp=comp,
                    model_data=md,
                    highspy=highspy,
                    o2=o2,
                    o3r6=o3r6,
                    recovery_root=recovery,
                    graph_identity=graph_identity,
                    output_flag=verbose_solver,
                )
            )
        gate("persistent_component_count_exact_1", len(solvers) == 1, len(solvers))

        # --------------------------------------------------------------------------------------
        # Recovery discovery: accepted iterate checkpoints are the durable nonlinear frontier.
        # --------------------------------------------------------------------------------------
        stage = "recovery_frontier_discovery"
        accepted_root = recovery / "accepted_iterates"
        accepted_iters = []
        if accepted_root.is_dir():
            for d in sorted(accepted_root.glob("iteration_*")):
                try:
                    i = int(d.name.split("_")[1])
                except Exception:
                    continue
                sn, mn, man = accepted_names(i)
                if manifest_valid(r3, d, man, {sn, mn}):
                    accepted_iters.append(i)
                else:
                    raise GateError(f"invalid_accepted_iterate_checkpoint:{d}")
        gate("bootstrap_iteration_zero_present", 0 in accepted_iters, accepted_iters)
        frontier = max(accepted_iters)
        fsn, fmn, fman = accepted_names(frontier)
        fdir = recovery_dir(recovery, "accepted_iterates", frontier)
        fmeta = r3.load_json(fdir / fmn)
        with np.load(fdir / fsn, allow_pickle=False) as z:
            S_iter = np.asarray(z["S_iter_next"], dtype=np.float64)
            previous_map_pressure = np.asarray(z["previous_physical_map_pressure_psi"], dtype=np.float64)
            previous_map_mass = np.asarray(z["previous_physical_map_mass_kg"], dtype=np.float64)
        current_iteration = int(fmeta["next_iteration"])
        gate("recovery_frontier_next_iteration_valid", 1 <= current_iteration <= MAX_NONLINEAR_ITERATIONS + 1, current_iteration)

        # If an accepted full-step iterate was already provisionally converged, resume closure directly.
        resume_closure_iteration = None
        if fmeta.get("provisional_converged") is True:
            resume_closure_iteration = frontier
            current_iteration = frontier

        # --------------------------------------------------------------------------------------
        # Helpers for physical map and line search checkpoints.
        # --------------------------------------------------------------------------------------
        def map_checkpoint_valid(iteration: int) -> bool:
            d = recovery_dir(recovery, "physical_maps", iteration)
            sn, mn, man = map_names(iteration)
            if not d.exists():
                return False
            if not manifest_valid(r3, d, man, {sn, mn}):
                raise GateError(f"invalid_physical_map_checkpoint:iteration={iteration}")
            return True

        def load_map(iteration: int):
            d = recovery_dir(recovery, "physical_maps", iteration)
            sn, mn, man = map_names(iteration)
            r3.verify_manifest(d, man)
            meta = r3.load_json(d / mn)
            with np.load(d / sn, allow_pickle=False) as z:
                state = {k: np.asarray(z[k]).copy() for k in z.files}
            return meta, state

        def publish_map(iteration: int, meta: dict[str, Any], arrays: dict[str, Any]):
            d = recovery_dir(recovery, "physical_maps", iteration)
            sn, mn, man = map_names(iteration)
            r3.immutable_publish(
                d,
                {
                    sn: o3r6.deterministic_npz_bytes(arrays),
                    mn: r3.json_bytes(meta),
                },
            )
            rows = [
                {"file": n, "sha256": r3.sha256_file(d / n), "bytes": (d / n).stat().st_size}
                for n in (sn, mn)
            ]
            r3.immutable_publish(d, {man: r3.csv_bytes(rows)})
            if not manifest_valid(r3, d, man, {sn, mn}):
                raise GateError(f"physical_map_checkpoint_publish_failure:iteration={iteration}")
            print(f"[CHECKPOINT] iteration={iteration:03d} PHYSICAL_MAP_CANDIDATE")
            sys.stdout.flush()

        def line_checkpoint_dir(iteration: int, omega_index: int) -> Path:
            return recovery_dir(recovery, "line_search", iteration) / f"omega_{omega_index:04d}_of_{LINE_SEARCH_DEN}"

        def line_checkpoint_valid(iteration: int, omega_index: int) -> bool:
            d = line_checkpoint_dir(iteration, omega_index)
            sn, rn, man = point_names(
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4",
                iteration,
                omega_index,
            )
            if not d.exists():
                return False
            if not manifest_valid(r3, d, man, {sn, rn}):
                raise GateError(
                    f"invalid_line_search_checkpoint:iteration={iteration},omega={omega_index}"
                )
            return True

        def evaluate_line_point(
            *,
            iteration: int,
            omega_index: int,
            S_base: np.ndarray,
            S_map: np.ndarray,
        ) -> dict[str, Any]:
            omega = float(omega_index) / float(LINE_SEARCH_DEN)
            S_trial = S_base + omega * (S_map - S_base)
            p_trial, p_resid = pressure_step(S_trial)
            if p_resid >= PRESSURE_LINEAR_REL_RESIDUAL_MAX:
                raise ScientificFail(
                    "line_search_pressure_linear_residual",
                    {"iteration": iteration, "omega_index": omega_index, "residual": p_resid},
                )
            cap = np.asarray(
                a2e.local_mass(
                    r2phys, np.full(GRID, INJECTED), p_trial, p_ref, grid_pv
                ),
                dtype=np.float64,
            )
            available_raw = cap.reshape(-1) - residual
            cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(np.abs(cap))), 1.0))
            residual_bad = float(np.min(available_raw)) < -cap_tol
            available = np.maximum(available_raw, 0.0)

            d = line_checkpoint_dir(iteration, omega_index)
            sn, rn, man = point_names(
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4",
                iteration,
                omega_index,
            )

            if line_checkpoint_valid(iteration, omega_index):
                result = r3.load_json(d / rn)
                with np.load(d / sn, allow_pickle=False) as z:
                    saved_p = np.asarray(z["pressure_psi"], dtype=np.float64)
                    saved_cap = np.asarray(z["cell_capacity_kg"], dtype=np.float64)
                if o3r6.max_abs(saved_p - p_trial) > 1.0e-8:
                    raise GateError("line_search_checkpoint_pressure_recertification_failure")
                if o3r6.max_abs(saved_cap - cap) > 1.0e-8:
                    raise GateError("line_search_checkpoint_capacity_recertification_failure")
                result = dict(result)
                result["checkpoint_reused"] = True
                print(
                    f"[REUSE] iter={iteration:03d} omega={omega:.9f} "
                    f"feasible={result['exact_frozen_E2_feasible']}"
                )
                return result

            solver_tel = None
            cv_linf = 0.0
            cap_excess = 0.0
            active_edges = None
            if residual_bad:
                feasible = False
                unserved = None
                ids = np.asarray([], dtype=np.int64)
                vals = np.asarray([], dtype=np.float64)
                source = "IMMUTABLE_RESIDUAL_CAPACITY_INFEASIBILITY"
            else:
                lp, active, cv_e, cell_e, nedge, nnz = o3r4.build_feasibility_lp(
                    highspy, coo_matrix, e2_cv, e2_cell, demand, available
                )
                active_edges = int(nedge)
                x, u, solver_tel = o3r4.run_highs_feasibility(highspy, lp, nedge)
                del lp
                gc.collect()
                assigned = np.bincount(cv_e, weights=x, minlength=NCVTOTAL).astype(np.float64)
                mapped = np.bincount(cell_e, weights=x, minlength=NCELL).astype(np.float64)
                cv_linf = float(np.max(np.abs(assigned + u - demand)))
                cap_excess = float(np.max(mapped - available))
                if (
                    cv_linf > FEASIBILITY_CV_LINF_TOL_KG
                    or cap_excess > FEASIBILITY_CAPACITY_EXCESS_TOL_KG
                ):
                    raise ScientificFail(
                        "line_search_feasibility_LP_certification_failure",
                        {
                            "iteration": iteration,
                            "omega_index": omega_index,
                            "CV_Linf_kg": cv_linf,
                            "capacity_excess_kg": cap_excess,
                        },
                    )
                unserved = float(np.sum(u))
                ids = np.flatnonzero(u > FEASIBILITY_UNSERVED_TOL_KG).astype(np.int64)
                vals = u[ids].astype(np.float64)
                feasible = unserved <= FEASIBILITY_UNSERVED_TOL_KG
                source = "EXACT_MINIMUM_UNSERVED_LP"

            result = {
                "milestone": MILESTONE,
                "nonlinear_iteration": int(iteration),
                "omega_index": int(omega_index),
                "omega_denominator": LINE_SEARCH_DEN,
                "omega": omega,
                "exact_frozen_E2_feasible": bool(feasible),
                "minimum_unserved_mass_kg": unserved,
                "unserved_CV_count_above_1e-6_kg": int(ids.size),
                "unserved_CV_ids": [int(v) for v in ids],
                "unserved_CV_values_kg": [float(v) for v in vals],
                "pressure_linear_relative_residual": float(p_resid),
                "minimum_available_mapped_capacity_kg": float(np.min(available_raw)),
                "CV_equality_Linf_kg": float(cv_linf),
                "maximum_cell_capacity_excess_kg": float(cap_excess),
                "active_exact_zero_pruned_E2_edges": active_edges,
                "classification_source": source,
                "solver_telemetry": solver_tel,
                "checkpoint_reused": False,
                "physical_state_authority": False,
                "physical_time_advanced": False,
            }
            arrays = {
                "S_trial": S_trial,
                "pressure_psi": p_trial,
                "cell_capacity_kg": cap,
                "available_mapped_capacity_kg": available.reshape(GRID),
                "unserved_CV_ids": ids,
                "unserved_CV_values_kg": vals,
            }
            r3.immutable_publish(
                d,
                {
                    sn: o3r6.deterministic_npz_bytes(arrays),
                    rn: r3.json_bytes(result),
                },
            )
            rows = [
                {"file": n, "sha256": r3.sha256_file(d / n), "bytes": (d / n).stat().st_size}
                for n in (sn, rn)
            ]
            r3.immutable_publish(d, {man: r3.csv_bytes(rows)})
            print(
                f"[CHECKPOINT] iter={iteration:03d} omega={omega:.9f} "
                f"feasible={feasible} unserved={unserved}"
            )
            sys.stdout.flush()
            return result

        def monotonicity_guard(results: dict[int, dict[str, Any]], iteration: int):
            ordered = sorted(results)
            seen_infeasible = False
            for idx in ordered:
                feasible = bool(results[idx]["exact_frozen_E2_feasible"])
                if not feasible:
                    seen_infeasible = True
                elif seen_infeasible:
                    raise ScientificFail(
                        "sampled_line_search_nonmonotonic_feasibility",
                        {
                            "iteration": iteration,
                            "ordered_points": [
                                [int(i), bool(results[i]["exact_frozen_E2_feasible"])]
                                for i in ordered
                            ],
                        },
                    )

        def perform_line_search(
            *,
            iteration: int,
            S_base: np.ndarray,
            S_map: np.ndarray,
        ) -> tuple[int, dict[int, dict[str, Any]]]:
            results: dict[int, dict[str, Any]] = {}
            idx = LINE_SEARCH_DEN
            results[idx] = evaluate_line_point(
                iteration=iteration, omega_index=idx, S_base=S_base, S_map=S_map
            )
            if results[idx]["exact_frozen_E2_feasible"]:
                return idx, results

            upper = idx
            lower = None
            idx //= 2
            while idx >= MIN_POSITIVE_OMEGA_INDEX:
                results[idx] = evaluate_line_point(
                    iteration=iteration, omega_index=idx, S_base=S_base, S_map=S_map
                )
                monotonicity_guard(results, iteration)
                if results[idx]["exact_frozen_E2_feasible"]:
                    lower = idx
                    break
                upper = idx
                if idx == MIN_POSITIVE_OMEGA_INDEX:
                    break
                idx //= 2

            if lower is None:
                raise ScientificFail(
                    "no_positive_feasible_omega_at_or_above_1_over_1024",
                    {"iteration": iteration, "minimum_omega": 1.0 / LINE_SEARCH_DEN},
                )

            while upper - lower > 1:
                mid = (upper + lower) // 2
                if mid not in results:
                    results[mid] = evaluate_line_point(
                        iteration=iteration, omega_index=mid,
                        S_base=S_base, S_map=S_map,
                    )
                monotonicity_guard(results, iteration)
                if results[mid]["exact_frozen_E2_feasible"]:
                    lower = mid
                else:
                    upper = mid

            return lower, results

        def publish_accepted(
            *,
            iteration: int,
            selected_idx: int,
            selected_result: dict[str, Any],
            S_next: np.ndarray,
            previous_map_pressure_for_next: np.ndarray,
            previous_map_mass_for_next: np.ndarray,
            raw_sat_residual: float,
            pressure_delta: float,
            grid_mass_delta: float,
            mass_conv_tol: float,
            provisional_converged: bool,
            all_line_results: dict[int, dict[str, Any]],
        ):
            d = recovery_dir(recovery, "accepted_iterates", iteration)
            sn, mn, man = accepted_names(iteration)
            meta = {
                "milestone": MILESTONE,
                "checkpoint_classification": "COMPUTATIONAL_ITERATE_ACCEPTED",
                "completed_iteration": int(iteration),
                "next_iteration": int(iteration + 1),
                "selected_omega_index": int(selected_idx),
                "selected_omega": float(selected_idx / LINE_SEARCH_DEN),
                "raw_fixed_point_saturation_Linf": float(raw_sat_residual),
                "pressure_relative_L2_change": float(pressure_delta),
                "grid_mass_Linf_change_kg": float(grid_mass_delta),
                "grid_mass_convergence_tolerance_kg": float(mass_conv_tol),
                "provisional_converged": bool(provisional_converged),
                "line_search_indices": [int(i) for i in sorted(all_line_results)],
                "line_search_feasibility": [
                    bool(all_line_results[i]["exact_frozen_E2_feasible"])
                    for i in sorted(all_line_results)
                ],
                "physical_state_authority": False,
                "physical_time_advanced": False,
            }
            arrays = {
                "S_iter_next": S_next,
                "selected_omega_index": np.asarray(selected_idx, dtype=np.int64),
                "selected_omega": np.asarray(selected_idx / LINE_SEARCH_DEN),
                "selected_trial_pressure_psi": np.asarray(
                    selected_result.get("_pressure_for_checkpoint"), dtype=np.float64
                ),
                "previous_physical_map_pressure_psi": previous_map_pressure_for_next,
                "previous_physical_map_mass_kg": previous_map_mass_for_next,
            }
            r3.immutable_publish(
                d,
                {sn: o3r6.deterministic_npz_bytes(arrays), mn: r3.json_bytes(meta)},
            )
            rows = [
                {"file": n, "sha256": r3.sha256_file(d / n), "bytes": (d / n).stat().st_size}
                for n in (sn, mn)
            ]
            r3.immutable_publish(d, {man: r3.csv_bytes(rows)})
            if not manifest_valid(r3, d, man, {sn, mn}):
                raise GateError(f"accepted_iterate_publish_failure:iteration={iteration}")
            print(
                f"[CHECKPOINT] iteration={iteration:03d} COMPUTATIONAL_ITERATE_ACCEPTED "
                f"omega={selected_idx}/{LINE_SEARCH_DEN}"
            )
            sys.stdout.flush()

        # --------------------------------------------------------------------------------------
        # Main stabilized fixed-point loop.
        # --------------------------------------------------------------------------------------
        if resume_closure_iteration is None:
            for iteration in range(current_iteration, MAX_NONLINEAR_ITERATIONS + 1):
                current_iteration = iteration
                stabilized_iteration_executed = True
                stage = f"iteration_{iteration:03d}_physical_map"

                # Existing physical map candidate means the expensive lex assignment is already done.
                if map_checkpoint_valid(iteration):
                    map_meta, map_state = load_map(iteration)
                    if o3r6.max_abs(map_state["S_iter"] - S_iter) > 1.0e-12:
                        raise GateError(
                            f"physical_map_checkpoint_S_iter_mismatch:iteration={iteration}"
                        )
                    p_map_check, p_res_check = pressure_step(S_iter)
                    if p_res_check >= PRESSURE_LINEAR_REL_RESIDUAL_MAX:
                        raise ScientificFail(
                            "reused_map_pressure_linear_residual",
                            {"iteration": iteration, "residual": p_res_check},
                        )
                    if o3r6.max_abs(p_map_check - map_state["P_map_psi"]) > 1.0e-8:
                        raise GateError(
                            f"physical_map_pressure_recertification_failure:iteration={iteration}"
                        )
                    P_map = map_state["P_map_psi"]
                    cap = map_state["cell_capacity_kg"]
                    full_x = map_state["E2_assignment_mass_kg"]
                    m_map = map_state["event_grid_mass_kg"]
                    S_map = map_state["S_map"]
                    mapped = map_state["mapped_grid_mass_kg"]
                    objectives = {
                        k: float(v) for k, v in map_meta["objectives"].items()
                    }
                    map_telemetry = list(map_meta["assignment_telemetry"])
                    map_metrics = dict(map_meta["metrics"])
                    stage5_basis_path = Path(map_meta["stage5_basis_path"])
                    print(f"[REUSE] iteration={iteration:03d} PHYSICAL_MAP_CANDIDATE")
                else:
                    P_map, p_linear_resid = pressure_step(S_iter)
                    sci_gate(
                        f"iteration_{iteration:03d}_pressure_linear_residual",
                        p_linear_resid < PRESSURE_LINEAR_REL_RESIDUAL_MAX,
                        p_linear_resid,
                    )
                    cap = np.asarray(
                        a2e.local_mass(
                            r2phys, np.full(GRID, INJECTED), P_map, p_ref, grid_pv
                        ),
                        dtype=np.float64,
                    )
                    cap_tol = max(
                        1.0e-8, 1.0e-12 * max(float(np.max(np.abs(cap))), 1.0)
                    )
                    available_raw = cap.reshape(-1) - residual
                    sci_gate(
                        f"iteration_{iteration:03d}_residual_sidecar_capacity",
                        float(np.min(available_raw)) >= -cap_tol,
                        {
                            "minimum_available_mapped_capacity_kg": float(np.min(available_raw)),
                            "tolerance_kg": cap_tol,
                        },
                    )
                    available = np.maximum(available_raw, 0.0)
                    grid_tol = max(
                        1.0e-6, 1.0e-10 * max(float(np.max(np.abs(cap))), 1.0)
                    )

                    full_x = np.zeros(EXPECTED_E2, dtype=np.float64)
                    objectives = {
                        "stage1_shell_kg": 0.0,
                        "stage2_extension_kg": 0.0,
                        "stage3_parent_L1_kg": 0.0,
                        "stage4_raw_L1_kg": 0.0,
                        "stage5_tiebreak": 0.0,
                    }
                    map_telemetry = []
                    prior_basis = None
                    if iteration > 1:
                        prior_basis_candidate = (
                            recovery_dir(recovery, "lex_stages", iteration - 1)
                            / "stage_5"
                            / stage_names(iteration - 1, 5)[2]
                        )
                        if prior_basis_candidate.is_file():
                            prior_basis = prior_basis_candidate

                    for solver in solvers:
                        result = solver.solve_iteration(
                            r3=r3,
                            iteration=iteration,
                            available_global=available,
                            cv_tol=cv_tol,
                            grid_tol=grid_tol,
                            prior_stage5_basis=prior_basis,
                        )
                        assignment_executed = True
                        full_x[result["edge_idx"]] = result["x"]
                        map_telemetry.extend(result["telemetry"])
                        for k, v in result["objectives"].items():
                            objectives[k] += float(v)
                        stage5_basis_path = result["stage5_basis_path"]

                    mapped_flat = np.bincount(
                        e2_cell, weights=full_x, minlength=NCELL
                    ).astype(np.float64)
                    mapped = mapped_flat.reshape(GRID)
                    cv_reconstructed = np.bincount(
                        e2_cv, weights=full_x, minlength=NCVTOTAL
                    ).astype(np.float64)
                    m_map = residual_grid + mapped
                    cv_linf = o3r6.max_abs(cv_reconstructed - demand)
                    max_capacity_excess = float(np.max(m_map - cap))
                    global_assignment_residual = (
                        o3r6.fsum_array(m_map)
                        - o3r6.fsum_array(residual)
                        - o3r6.fsum_array(demand)
                    )
                    sci_gate(
                        f"iteration_{iteration:03d}_assignment_global_certification",
                        cv_linf <= cv_tol
                        and max_capacity_excess <= grid_tol
                        and abs(global_assignment_residual)
                            <= max(
                                1.0e-5,
                                1.0e-10 * max(o3r6.fsum_array(m_map), 1.0),
                            ),
                        {
                            "CV_Linf_kg": cv_linf,
                            "max_capacity_excess_kg": max_capacity_excess,
                            "global_assignment_residual_kg": global_assignment_residual,
                        },
                    )

                    try:
                        sg_map = a2e.invert_local_mass(
                            r2phys, m_map, P_map, p_ref, grid_pv
                        )
                    except Exception as exc:
                        raise ScientificFail(
                            "iterate_EOS_mass_inversion_failure",
                            {"iteration": iteration, "exception": repr(exc)},
                        ) from exc
                    S_map = BACKGROUND + np.asarray(sg_map, dtype=np.float64)
                    sci_gate(
                        f"iteration_{iteration:03d}_saturation_bounds",
                        np.isfinite(S_map).all()
                        and float(np.min(S_map)) >= BACKGROUND - 1.0e-10
                        and float(np.max(S_map)) <= INJECTED + 1.0e-10,
                        [float(np.min(S_map)), float(np.max(S_map))],
                    )
                    reconstructed_mass = np.asarray(
                        a2e.local_mass(r2phys, S_map, P_map, p_ref, grid_pv),
                        dtype=np.float64,
                    )
                    cell_mass_error = o3r6.max_abs(reconstructed_mass - m_map)
                    global_mass_rel = (
                        abs(
                            o3r6.fsum_array(reconstructed_mass)
                            - o3r6.fsum_array(m_map)
                        )
                        / max(abs(o3r6.fsum_array(m_map)), 1.0)
                    )
                    mass_conv_tol = max(
                        1.0e-8,
                        1.0e-10 * max(float(np.max(np.abs(m_map))), 1.0),
                    )
                    sci_gate(
                        f"iteration_{iteration:03d}_mass_closure",
                        cell_mass_error <= mass_conv_tol
                        and global_mass_rel <= GLOBAL_MASS_REL_TOL,
                        {
                            "cellwise_error_kg": cell_mass_error,
                            "cellwise_tolerance_kg": mass_conv_tol,
                            "global_relative_error": global_mass_rel,
                        },
                    )
                    raw_sat_residual = o3r6.max_abs(S_map - S_iter)
                    pressure_delta = o3r6.relative_l2(P_map, previous_map_pressure)
                    grid_mass_delta = o3r6.max_abs(m_map - previous_map_mass)

                    map_metrics = {
                        "pressure_linear_relative_residual": float(p_linear_resid),
                        "CV_mass_Linf_error_kg": float(cv_linf),
                        "maximum_cell_capacity_excess_kg": float(max_capacity_excess),
                        "cellwise_EOS_mass_error_kg": float(cell_mass_error),
                        "global_EOS_mass_relative_error": float(global_mass_rel),
                        "global_assignment_residual_kg": float(global_assignment_residual),
                        "raw_fixed_point_saturation_Linf": float(raw_sat_residual),
                        "pressure_relative_L2_change": float(pressure_delta),
                        "grid_mass_Linf_change_kg": float(grid_mass_delta),
                        "grid_mass_convergence_tolerance_kg": float(mass_conv_tol),
                    }
                    map_meta = {
                        "milestone": MILESTONE,
                        "checkpoint_classification": "PHYSICAL_MAP_CANDIDATE",
                        "nonlinear_iteration": int(iteration),
                        "objectives": {k: float(v) for k, v in objectives.items()},
                        "metrics": map_metrics,
                        "assignment_telemetry": map_telemetry,
                        "stage5_basis_path": str(stage5_basis_path),
                        "physical_state_authority": True,
                        "physical_time_advanced": False,
                    }
                    publish_map(
                        iteration,
                        map_meta,
                        {
                            "S_iter": S_iter,
                            "P_map_psi": P_map,
                            "cell_capacity_kg": cap,
                            "E2_assignment_mass_kg": full_x,
                            "mapped_grid_mass_kg": mapped,
                            "event_grid_mass_kg": m_map,
                            "S_map": S_map,
                        },
                    )

                # Recompute convergence metrics against prior physical map on reused checkpoints.
                raw_sat_residual = o3r6.max_abs(S_map - S_iter)
                pressure_delta = o3r6.relative_l2(P_map, previous_map_pressure)
                grid_mass_delta = o3r6.max_abs(m_map - previous_map_mass)
                mass_conv_tol = max(
                    1.0e-8,
                    1.0e-10 * max(float(np.max(np.abs(m_map))), 1.0),
                )

                # Collect assignment telemetry from map checkpoint.
                for rec in map_telemetry:
                    assignment_rows.append(dict(rec))

                stage = f"iteration_{iteration:03d}_line_search"
                selected_idx, line_results = perform_line_search(
                    iteration=iteration,
                    S_base=S_iter,
                    S_map=S_map,
                )

                # Collect unique line-search telemetry for final report.
                for idx in sorted(line_results):
                    rr = dict(line_results[idx])
                    line_rows.append({
                        "iteration": iteration,
                        "omega_index": idx,
                        "omega": rr["omega"],
                        "feasible": rr["exact_frozen_E2_feasible"],
                        "minimum_unserved_mass_kg": rr["minimum_unserved_mass_kg"],
                        "unserved_CV_count": rr["unserved_CV_count_above_1e-6_kg"],
                        "pressure_linear_relative_residual": rr["pressure_linear_relative_residual"],
                        "minimum_available_mapped_capacity_kg": rr["minimum_available_mapped_capacity_kg"],
                        "CV_equality_Linf_kg": rr["CV_equality_Linf_kg"],
                        "maximum_cell_capacity_excess_kg": rr["maximum_cell_capacity_excess_kg"],
                        "checkpoint_reused": rr.get("checkpoint_reused", False),
                    })

                selected = line_results[selected_idx]
                selected_dir = line_checkpoint_dir(iteration, selected_idx)
                sel_sn, sel_rn, sel_man = point_names(
                    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4",
                    iteration,
                    selected_idx,
                )
                with np.load(selected_dir / sel_sn, allow_pickle=False) as z:
                    selected_pressure = np.asarray(z["pressure_psi"], dtype=np.float64)
                    S_next = np.asarray(z["S_trial"], dtype=np.float64)

                selected = dict(selected)
                selected["_pressure_for_checkpoint"] = selected_pressure
                full_step = selected_idx == LINE_SEARCH_DEN

                provisional_converged = (
                    full_step
                    and raw_sat_residual <= SATURATION_LINF_TOL
                    and pressure_delta <= PRESSURE_REL_L2_TOL
                    and grid_mass_delta <= mass_conv_tol
                )

                publish_accepted(
                    iteration=iteration,
                    selected_idx=selected_idx,
                    selected_result=selected,
                    S_next=S_next,
                    previous_map_pressure_for_next=P_map,
                    previous_map_mass_for_next=m_map,
                    raw_sat_residual=raw_sat_residual,
                    pressure_delta=pressure_delta,
                    grid_mass_delta=grid_mass_delta,
                    mass_conv_tol=mass_conv_tol,
                    provisional_converged=provisional_converged,
                    all_line_results=line_results,
                )

                row = {
                    "iteration": iteration,
                    "selected_omega_index": selected_idx,
                    "selected_omega": selected_idx / LINE_SEARCH_DEN,
                    "full_step_accepted": full_step,
                    "raw_fixed_point_saturation_Linf": raw_sat_residual,
                    "pressure_relative_L2_change": pressure_delta,
                    "grid_mass_Linf_change_kg": grid_mass_delta,
                    "grid_mass_convergence_tolerance_kg": mass_conv_tol,
                    "provisional_converged": provisional_converged,
                    **{k: float(v) for k, v in objectives.items()},
                }
                nonlinear_rows.append(row)
                print(
                    f"[ITER {iteration:03d}] omega={selected_idx}/{LINE_SEARCH_DEN} "
                    f"raw_dS={raw_sat_residual:.6e} dP={pressure_delta:.6e} "
                    f"dM={grid_mass_delta:.6e} provisional={provisional_converged}"
                )
                sys.stdout.flush()

                if provisional_converged:
                    converged = True
                    resume_closure_iteration = iteration
                    break

                # Advance only computational iterate; physical map remains separately checkpointed.
                S_iter = S_next
                previous_map_pressure = P_map
                previous_map_mass = m_map

            if not converged and resume_closure_iteration is None:
                raise ScientificFail(
                    "stabilized_coupled_fixed_point_nonconvergence",
                    {
                        "maximum_iterations": MAX_NONLINEAR_ITERATIONS,
                        "last_iteration": nonlinear_rows[-1] if nonlinear_rows else None,
                    },
                )

        # --------------------------------------------------------------------------------------
        # Original undamped final closure.
        # --------------------------------------------------------------------------------------
        closure_iteration = int(resume_closure_iteration)
        stage = "final_undamped_closure"
        map_meta, map_state = load_map(closure_iteration)
        P_map = np.asarray(map_state["P_map_psi"], dtype=np.float64)
        S_map = np.asarray(map_state["S_map"], dtype=np.float64)
        m_map = np.asarray(map_state["event_grid_mass_kg"], dtype=np.float64)
        full_x = np.asarray(map_state["E2_assignment_mass_kg"], dtype=np.float64)

        adir = recovery_dir(recovery, "accepted_iterates", closure_iteration)
        asn, amn, aman = accepted_names(closure_iteration)
        r3.verify_manifest(adir, aman)
        ameta = r3.load_json(adir / amn)
        sci_gate("closure_requires_full_omega", int(ameta["selected_omega_index"]) == LINE_SEARCH_DEN, ameta["selected_omega_index"])
        sci_gate("closure_requires_provisional_convergence", ameta.get("provisional_converged") is True, ameta.get("provisional_converged"))
        sci_gate(
            "closure_raw_fixed_point_saturation",
            float(ameta["raw_fixed_point_saturation_Linf"]) <= SATURATION_LINF_TOL,
            ameta["raw_fixed_point_saturation_Linf"],
        )
        sci_gate(
            "closure_pressure_iteration_delta",
            float(ameta["pressure_relative_L2_change"]) <= PRESSURE_REL_L2_TOL,
            ameta["pressure_relative_L2_change"],
        )
        sci_gate(
            "closure_grid_mass_iteration_delta",
            float(ameta["grid_mass_Linf_change_kg"]) <= float(ameta["grid_mass_convergence_tolerance_kg"]),
            {
                "delta": ameta["grid_mass_Linf_change_kg"],
                "tol": ameta["grid_mass_convergence_tolerance_kg"],
            },
        )

        closure_pressure, closure_linear_resid = pressure_step(S_map)
        sci_gate("closure_pressure_linear_residual", closure_linear_resid < PRESSURE_LINEAR_REL_RESIDUAL_MAX, closure_linear_resid)
        closure_pressure_delta = o3r6.relative_l2(closure_pressure, P_map)
        sci_gate("closure_pressure_fixed_point", closure_pressure_delta <= PRESSURE_REL_L2_TOL, closure_pressure_delta)

        closure_cap = np.asarray(
            a2e.local_mass(
                r2phys, np.full(GRID, INJECTED), closure_pressure, p_ref, grid_pv
            ),
            dtype=np.float64,
        )
        closure_cap_tol = max(
            1.0e-6, 1.0e-10 * max(float(np.max(np.abs(closure_cap))), 1.0)
        )
        closure_available_raw = closure_cap.reshape(-1) - residual
        sci_gate(
            "closure_residual_sidecar_capacity",
            float(np.min(closure_available_raw)) >= -closure_cap_tol,
            {
                "minimum_available_mapped_capacity_kg": float(np.min(closure_available_raw)),
                "tolerance_kg": closure_cap_tol,
            },
        )
        closure_grid_excess = float(np.max(m_map - closure_cap))
        sci_gate(
            "closure_assignment_within_capacity",
            closure_grid_excess <= closure_cap_tol,
            {"maximum_excess_kg": closure_grid_excess, "tolerance_kg": closure_cap_tol},
        )

        try:
            closure_sg = a2e.invert_local_mass(
                r2phys, m_map, closure_pressure, p_ref, grid_pv
            )
        except Exception as exc:
            raise ScientificFail("closure_EOS_mass_inversion_failure", repr(exc)) from exc
        closure_sat = BACKGROUND + np.asarray(closure_sg, dtype=np.float64)
        sci_gate(
            "closure_saturation_bounds",
            np.isfinite(closure_sat).all()
            and float(np.min(closure_sat)) >= BACKGROUND - 1.0e-10
            and float(np.max(closure_sat)) <= INJECTED + 1.0e-10,
            [float(np.min(closure_sat)), float(np.max(closure_sat))],
        )
        closure_sat_delta = o3r6.max_abs(closure_sat - S_map)
        sci_gate("closure_saturation_fixed_point", closure_sat_delta <= SATURATION_LINF_TOL, closure_sat_delta)

        reconstructed_mass = np.asarray(
            a2e.local_mass(r2phys, closure_sat, closure_pressure, p_ref, grid_pv),
            dtype=np.float64,
        )
        final_mass_tol = max(
            1.0e-8, 1.0e-10 * max(float(np.max(np.abs(m_map))), 1.0)
        )
        closure_cell_mass_error = o3r6.max_abs(reconstructed_mass - m_map)
        closure_global_rel = (
            abs(o3r6.fsum_array(reconstructed_mass) - o3r6.fsum_array(m_map))
            / max(abs(o3r6.fsum_array(m_map)), 1.0)
        )
        sci_gate(
            "closure_cellwise_mass_error",
            closure_cell_mass_error <= final_mass_tol,
            {"error_kg": closure_cell_mass_error, "tolerance_kg": final_mass_tol},
        )
        sci_gate(
            "closure_global_mass_relative_error",
            closure_global_rel <= GLOBAL_MASS_REL_TOL,
            closure_global_rel,
        )

        final_mapped = np.bincount(
            e2_cell, weights=full_x, minlength=NCELL
        ).astype(np.float64)
        final_cv = np.bincount(
            e2_cv, weights=full_x, minlength=NCVTOTAL
        ).astype(np.float64)
        final_cv_linf = o3r6.max_abs(final_cv - demand)
        sci_gate(
            "final_per_CV_mass_exact",
            final_cv_linf <= cv_tol,
            {"Linf_kg": final_cv_linf, "tolerance_kg": cv_tol},
        )
        sci_gate(
            "final_grid_reconstruction_exact",
            o3r6.max_abs(
                (residual + final_mapped).reshape(GRID) - m_map
            ) <= 1.0e-8,
            o3r6.max_abs((residual + final_mapped).reshape(GRID) - m_map),
        )

        # --------------------------------------------------------------------------------------
        # Final scientific fixed-point publication. No Darcy/Pollock/TOF.
        # --------------------------------------------------------------------------------------
        stage = "artifact_publication"
        checkpoint = o3r6.deterministic_npz_bytes({
            "event_day": np.asarray(EVENT_DAY),
            "physical_time_advanced_in_O3R6R4": np.asarray(False),
            "stabilized_fixed_point_iteration_count": np.asarray(closure_iteration, dtype=np.int64),
            "converged_pressure_psi": closure_pressure,
            "converged_saturation": closure_sat,
            "converged_event_grid_component_mass_kg": m_map,
            "converged_event_mapped_grid_mass_kg": final_mapped.reshape(GRID),
            "frozen_residual_grid_component_mass_kg": residual_grid,
            "converged_cell_capacity_kg": closure_cap,
            "event_CV_component_mass_kg": event_cv_mass,
            "E2_pair_cv_id": e2_cv,
            "E2_pair_flat_cell": e2_cell,
            "E2_pair_is_E0": is_e0,
            "E2_pair_is_E1": is_e1,
            "E2_pair_converged_mass_kg": full_x,
            "grid_pore_volume_m3": grid_pv,
            "reference_gas_pressure_pa": np.asarray(p_ref),
        })

        # Rebuild telemetry from immutable recovery checkpoints so restarts do not lose report history.
        nonlinear_rows = []
        assignment_rows = []
        line_rows = []
        for i in range(1, closure_iteration + 1):
            ad = recovery_dir(recovery, "accepted_iterates", i)
            asn_i, amn_i, aman_i = accepted_names(i)
            if manifest_valid(r3, ad, aman_i, {asn_i, amn_i}):
                mm = r3.load_json(ad / amn_i)
                nonlinear_rows.append({
                    "iteration": i,
                    "selected_omega_index": mm["selected_omega_index"],
                    "selected_omega": mm["selected_omega"],
                    "full_step_accepted": int(mm["selected_omega_index"]) == LINE_SEARCH_DEN,
                    "raw_fixed_point_saturation_Linf": mm["raw_fixed_point_saturation_Linf"],
                    "pressure_relative_L2_change": mm["pressure_relative_L2_change"],
                    "grid_mass_Linf_change_kg": mm["grid_mass_Linf_change_kg"],
                    "grid_mass_convergence_tolerance_kg": mm["grid_mass_convergence_tolerance_kg"],
                    "provisional_converged": mm["provisional_converged"],
                })
            for s in range(1, 6):
                sd = recovery_dir(recovery, "lex_stages", i) / f"stage_{s}"
                ssn, smn, sbn, sman = stage_names(i, s)
                if manifest_valid(r3, sd, sman, {ssn, smn, sbn}):
                    assignment_rows.append(r3.load_json(sd / smn)["telemetry"])
            lroot = recovery_dir(recovery, "line_search", i)
            if lroot.is_dir():
                for d in sorted(lroot.glob(f"omega_*_of_{LINE_SEARCH_DEN}")):
                    try:
                        idx = int(d.name.split("_")[1])
                    except Exception:
                        continue
                    psn, prn, pman = point_names(
                        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4", i, idx
                    )
                    if manifest_valid(r3, d, pman, {psn, prn}):
                        rr = r3.load_json(d / prn)
                        line_rows.append({
                            "iteration": i,
                            "omega_index": idx,
                            "omega": rr["omega"],
                            "feasible": rr["exact_frozen_E2_feasible"],
                            "minimum_unserved_mass_kg": rr["minimum_unserved_mass_kg"],
                            "unserved_CV_count": rr["unserved_CV_count_above_1e-6_kg"],
                            "pressure_linear_relative_residual": rr["pressure_linear_relative_residual"],
                            "minimum_available_mapped_capacity_kg": rr["minimum_available_mapped_capacity_kg"],
                            "CV_equality_Linf_kg": rr["CV_equality_Linf_kg"],
                            "maximum_cell_capacity_excess_kg": rr["maximum_cell_capacity_excess_kg"],
                        })

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "highspy_version": highspy.Highs().version(),
            "stabilized_fixed_point_converged": True,
            "stabilized_fixed_point_iteration_count": closure_iteration,
            "original_undamped_convergence_certified": True,
            "final_closure_pressure_relative_L2": closure_pressure_delta,
            "final_closure_saturation_Linf_change": closure_sat_delta,
            "final_CV_mass_Linf_error_kg": final_cv_linf,
            "final_maximum_cell_capacity_excess_kg": closure_grid_excess,
            "final_cellwise_EOS_mass_error_kg": closure_cell_mass_error,
            "final_global_EOS_mass_relative_error": closure_global_rel,
            "adaptive_line_search_used": any(
                int(r["selected_omega_index"]) < LINE_SEARCH_DEN
                for r in nonlinear_rows
            ),
            "minimum_selected_omega": min(
                float(r["selected_omega"]) for r in nonlinear_rows
            ) if nonlinear_rows else None,
            "lex_stage_checkpointing_enabled": True,
            "line_search_checkpointing_enabled": True,
            "physical_map_checkpointing_enabled": True,
            "accepted_iterate_checkpointing_enabled": True,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "Darcy_Pollock_TOF_executed": False,
            "reprojection_executed": False,
            "physical_time_advanced": False,
        }
        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R7 — "
                "single converged-state Darcy / Pollock / TOF flow-geometry refresh"
            ),
            "O3R7_authorized": True,
            "O3R7_must_use_R4_certified_fixed_point": True,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "automatic_second_event_refresh_authorized": False,
            "physical_time_advance_authorized": False,
        }

        files = {
            FINAL_SUMMARY: r3.json_bytes(summary),
            FINAL_STATE: checkpoint,
            FINAL_NONLIN: r3.csv_bytes(nonlinear_rows),
            FINAL_ASSIGN: r3.csv_bytes(assignment_rows),
            FINAL_LINE: r3.csv_bytes(line_rows),
            FINAL_DECISION: r3.json_bytes(decision),
            FINAL_GATES: r3.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        r3.immutable_publish(out, files)
        rows = [
            {"file": p.name, "sha256": r3.sha256_file(p), "bytes": p.stat().st_size}
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != FINAL_MANIFEST
        ]
        r3.immutable_publish(out, {FINAL_MANIFEST: r3.csv_bytes(rows)})

        print()
        print("=" * 214)
        print(MILESTONE + ": PASS")
        print("=" * 214)
        print("Converged iteration             :", closure_iteration)
        print("Undamped fixed point            : CERTIFIED")
        print("Final frozen closure            : CERTIFIED")
        print("Minimum selected omega          :", summary["minimum_selected_omega"])
        print("Stage-level checkpointing       : ENABLED")
        print("O3-R7                           : AUTHORIZED")
        print("Darcy/Pollock/TOF in R4         : NOT EXECUTED")
        print("Physical-time advance           : False")
        print("=" * 214)
        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "current_iteration": int(current_iteration),
            "pressure_solve_executed": pressure_solve_executed,
            "assignment_executed": assignment_executed,
            "stabilized_iteration_executed": stabilized_iteration_executed,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "Darcy_Pollock_TOF_executed": False,
            "reprojection_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "recovery_checkpoints_preserved": True,
        }
        r3.immutable_publish(
            failed,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Scientific_Fail_Report.json":
                    r3.json_bytes(report)
            },
        )
        print()
        print(MILESTONE + ": SCIENTIFIC FAIL")
        print("Stage:", stage)
        print("Gate :", exc.gate)
        print("Detail:", exc.detail)
        print("RECOVERY CHECKPOINTS PRESERVED. NO AUTOMATIC RERUN AUTHORIZED.")
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "current_iteration": int(current_iteration),
            "pressure_solve_executed": pressure_solve_executed,
            "assignment_executed": assignment_executed,
            "stabilized_iteration_executed": stabilized_iteration_executed,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "recovery_checkpoints_preserved": True,
        }
        r3.immutable_publish(
            blocked,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Blocked_Report.json":
                    r3.json_bytes(report)
            },
        )
        print()
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        print("RECOVERY CHECKPOINTS PRESERVED.")
        return 2

    finally:
        for solver in solvers:
            try:
                solver.close()
            except Exception:
                pass
        gc.collect()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--verbose-solver", action="store_true")
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.verbose_solver))
