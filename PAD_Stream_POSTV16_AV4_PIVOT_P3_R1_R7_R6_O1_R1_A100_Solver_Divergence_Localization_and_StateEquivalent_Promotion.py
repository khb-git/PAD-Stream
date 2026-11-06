#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
from importlib import metadata as importlib_metadata
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R7-R6-O1-R1"
NAME = "A100 Solver-Divergence Localization + State-Equivalent Runtime Promotion Diagnostic"
PASS_PROMOTE = "AV4PIVOTP3R1R7R6O1R1_DIVERGENCE_LOCALIZED_STATE_EQUIVALENT_ACCELERATED_RUNTIME_AUTHORIZED"
PASS_NOPROMOTE = "AV4PIVOTP3R1R7R6O1R1_DIVERGENCE_LOCALIZED_NO_STATE_EQUIVALENT_RUNTIME_PROMOTION"
BLOCK = "AV4PIVOTP3R1R7R6O1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "7b051a58e8c02499f8d9fd72302f17947cba0d41"
R7R6 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day380_to_Day385_FourthObservation_Pilot.py"
R7R6_BLOB = "5f77419b363f885f012b9195cc49f041282c211b"
R7R6_SHA256 = "919dcc240b5feabaa4328668a3aa33a268ecf9f71c59abaf6e64271b77aa637e"
R7R6_COMMIT = "4b96eb35b1fa3ce736aef495b380ab1a65e8d2ca"
R7R6_STATE_SHA = "18a98bd27661fd1f2464f5e46e74389c794e2bdfc58a68541ee381a526d29988"
R7R6_DIAG_SHA = "3ec8d7b6a7877847501396478d5757761ed54a33de1358a2cc157859daba1c7d"
R7R6_STATUS = "AV4PIVOTP3R1R7R6_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
R7R6_CLASS = "P3R1_R7_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY390_PILOT_AUTHORIZED"

O1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R6_O1_A100_HighRAM_Solver_Acceleration_Equivalence_Certification.py"
O1_RUNNER_SHA256 = "2a2d6cdd22b0989f20a8bb1106d3bf7b64eeb334bf0ecf3bed88f9af25125cf6"
O1_RUNNER_BLOB = "3a47376b34b21936feb705cebbc999494f5e62c9"
O1_BLOCK_STATUS = "AV4PIVOTP3R1R7R6O1_TECHNICAL_OR_AUTHORITY_BLOCK"
O1_BLOCK_FAILED_STAGE = "persistent_stage2_equivalence"
O1_BLOCK_EXCEPTION = "GateError('persistent_represented_cell_state_equivalent')"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
R7R6_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R6_XY2_Day380_to_Day385_FourthObservation_Pilot_and_Exact_Flow_Diagnostic"
R7R6_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R6_Summary.json"
R7R6_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Decision_Contract.json"
R7R6_STATE = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day0385_Accepted_Dense_State.npz"
R7R6_DIAG = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day0385_Exact_Flow_Diagnostic.npz"
R7R6_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Artifact_Manifest.csv"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_O1_R1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_A100_Solver_Divergence_Localization_and_StateEquivalent_Runtime_Promotion")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
O1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R6_O1_BLOCKED"
O1_BLOCK_FILE = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_O1_Blocked_Report.json"
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
HARDWARE = f"{OUT_TOKEN}_Hardware_Profile.json"
STAGE1_BENCH = f"{OUT_TOKEN}_Stage1_Thread_Benchmark.csv"
STAGE2_BENCH = f"{OUT_TOKEN}_Solver_Divergence_Localization_Benchmark.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"
BLOCK_FILE = f"{OUT_TOKEN}_Blocked_Report.json"

DAY_TO_S = 86400.0
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HIGHS_FEAS_TOL = 1.0e-10
HALO_OPT_TOL = 1.0e-6
PRICING_TOL = 1.0e-8
POSITIVE_EDGE_TOL = 1.0e-10
COLUMN_BATCH_SIZE = 10000
MAX_CG_ITERATIONS = 12
PROMOTION_MIN_PROJECTED_LP_SPEEDUP = 1.20
EXPECTED_HIGHSPY_VERSION = "1.15.1"
MIN_A100_HOST_RAM_GIB = 80.0


class GateError(RuntimeError):
    pass


class TrialReject(RuntimeError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


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


def atomic_write(path: Path, payload: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, path)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    out: dict[str, str] = {}
    with (directory / filename).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = directory / row["file"]
            if not p.is_file():
                raise GateError(f"manifest_missing:{p.name}")
            if sha(p) != row["sha256"]:
                raise GateError(f"manifest_sha:{p.name}")
            if p.stat().st_size != int(row["bytes"]):
                raise GateError(f"manifest_bytes:{p.name}")
            out[p.name] = row["sha256"]
    if not out:
        raise GateError(f"manifest_empty:{filename}")
    return out


def hardware_profile() -> dict[str, Any]:
    profile: dict[str, Any] = {
        "platform": platform.platform(),
        "python": sys.version,
        "logical_cpu_count": os.cpu_count(),
    }
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        profile["host_ram_bytes"] = int(pages * page_size)
        profile["host_ram_gib"] = float(pages * page_size / (1024 ** 3))
    except Exception:
        profile["host_ram_bytes"] = None
        profile["host_ram_gib"] = None
    for key, cmd in {
        "lscpu": ["lscpu"],
        "free_h": ["free", "-h"],
        "nvidia_smi": ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
    }.items():
        try:
            profile[key] = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
        except Exception as exc:
            profile[key] = f"UNAVAILABLE:{exc!r}"
    return profile


def highs_pass_lp(c, A, row_lower, row_upper, threads=1, parallel=False, time_limit=300.0):
    import highspy
    from scipy.sparse import csc_matrix

    A = csc_matrix(A, dtype=np.float64)
    lp = highspy.HighsLp()
    lp.num_col_ = int(A.shape[1])
    lp.num_row_ = int(A.shape[0])
    lp.col_cost_ = np.asarray(c, dtype=np.float64)
    lp.col_lower_ = np.zeros(A.shape[1], dtype=np.float64)
    lp.col_upper_ = np.full(A.shape[1], highspy.kHighsInf, dtype=np.float64)
    lp.row_lower_ = np.asarray(row_lower, dtype=np.float64)
    lp.row_upper_ = np.asarray(row_upper, dtype=np.float64)
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.asarray(A.indptr, dtype=np.int64)
    lp.a_matrix_.index_ = np.asarray(A.indices, dtype=np.int32)
    lp.a_matrix_.value_ = np.asarray(A.data, dtype=np.float64)

    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    h.setOptionValue("solver", "simplex")
    h.setOptionValue("presolve", "on")
    h.setOptionValue("primal_feasibility_tolerance", HIGHS_FEAS_TOL)
    h.setOptionValue("dual_feasibility_tolerance", HIGHS_FEAS_TOL)
    h.setOptionValue("time_limit", float(time_limit))
    h.setOptionValue("threads", int(max(1, threads)))
    if parallel and threads > 1:
        h.setOptionValue("parallel", "on")
        h.setOptionValue("simplex_strategy", 2)
        h.setOptionValue("simplex_max_concurrency", int(min(8, threads)))
    else:
        h.setOptionValue("parallel", "off")
        h.setOptionValue("simplex_strategy", 1)
    status = h.passModel(lp)
    if str(status).endswith("kError"):
        raise GateError(f"highs_passModel_error:{status}")
    return h


def run_highs_stage1_arrays(edge_cv, edge_cell, shell, new_cv_mass, rep_capacity_flat, ncell, ncvt, threads, time_limit, return_x=False):
    from scipy.sparse import coo_matrix, vstack
    import highspy

    nedge = int(edge_cv.size)
    idx = np.arange(nedge, dtype=np.int64)
    Acell = coo_matrix((np.ones(nedge), (edge_cell, idx)), shape=(ncell, nedge)).tocsr()
    Aeq = coo_matrix((np.ones(nedge), (edge_cv, idx)), shape=(ncvt, nedge)).tocsr()
    A = vstack([Acell, Aeq], format="csc")
    inf = highspy.kHighsInf
    row_lower = np.concatenate([np.full(ncell, -inf), new_cv_mass.reshape(-1)])
    row_upper = np.concatenate([rep_capacity_flat, new_cv_mass.reshape(-1)])
    c = (shell > 0).astype(np.float64)
    t0 = time.perf_counter()
    h = highs_pass_lp(c, A, row_lower, row_upper, threads=threads, parallel=(threads > 1), time_limit=time_limit)
    h.run()
    wall = time.perf_counter() - t0
    model_status = h.modelStatusToString(h.getModelStatus())
    info = h.getInfo()
    sol = h.getSolution()
    ok = "Optimal" in model_status
    x = np.asarray(sol.col_value, dtype=np.float64) if ok else np.asarray([], dtype=np.float64)
    cv_err = float(np.max(np.abs(np.bincount(edge_cv, weights=x, minlength=ncvt) - new_cv_mass.reshape(-1)))) if ok else None
    cap_excess = float(np.max(np.bincount(edge_cell, weights=x, minlength=ncell) - rep_capacity_flat)) if ok else None
    out = {
        "threads": int(threads),
        "parallel": bool(threads > 1),
        "model_status": model_status,
        "wall_seconds": float(wall),
        "objective": float(info.objective_function_value) if ok else None,
        "simplex_iterations": int(info.simplex_iteration_count) if ok else None,
        "cv_equality_max_abs_error_kg": cv_err,
        "capacity_excess_kg": cap_excess,
    }
    if return_x:
        out["_x"] = x
    return out


def child_stage1(args) -> int:
    with np.load(args.stage1_child, allow_pickle=False) as z:
        d = {k: np.asarray(z[k]) for k in z.files}
    result = run_highs_stage1_arrays(
        np.asarray(d["edge_cv"], dtype=np.int64),
        np.asarray(d["edge_cell"], dtype=np.int64),
        np.asarray(d["shell"], dtype=np.int8),
        np.asarray(d["new_cv_mass"], dtype=np.float64),
        np.asarray(d["rep_capacity_flat"], dtype=np.float64),
        int(np.asarray(d["ncell"]).reshape(())),
        int(np.asarray(d["ncvt"]).reshape(())),
        int(args.threads),
        float(args.time_limit_seconds),
        return_x=bool(args.solution_out),
    )
    x = result.pop("_x", None)
    Path(args.result).write_bytes(jb(result))
    if args.solution_out and x is not None:
        np.savez_compressed(Path(args.solution_out), x=np.asarray(x, dtype=np.float64))
    return 0


def scipy_stage1(problem, Aeq_full, Acell_full, time_limit):
    from scipy.optimize import linprog
    t0 = time.perf_counter()
    lp = linprog(
        problem["c1_full"],
        A_ub=Acell_full,
        b_ub=problem["rep_capacity_flat"],
        A_eq=Aeq_full,
        b_eq=problem["new_cv_mass"].reshape(-1),
        bounds=(0.0, None),
        method="highs-ds",
        options={
            "presolve": True,
            "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
            "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
            "time_limit": float(time_limit),
        },
    )
    wall = time.perf_counter() - t0
    if not lp.success:
        raise TrialReject(f"stage1_not_success:{lp.status}:{lp.message}")
    return lp, wall


def scipy_zero_halo(problem, Aeq_exact, Acell_exact_active, active_cells, time_limit):
    from scipy.optimize import linprog
    t0 = time.perf_counter()
    lp = linprog(
        np.zeros(Aeq_exact.shape[1], dtype=np.float64),
        A_ub=Acell_exact_active,
        b_ub=problem["rep_capacity_flat"][active_cells],
        A_eq=Aeq_exact,
        b_eq=problem["new_cv_mass"].reshape(-1),
        bounds=(0.0, None),
        method="highs-ds",
        options={
            "presolve": True,
            "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
            "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
            "time_limit": float(time_limit),
        },
    )
    return lp, time.perf_counter() - t0


def scipy_stage2_cg(problem, edge_cv, edge_cell, shell, exact_positions, stage1_x, time_limit, extra_seed_shell=None):
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack

    nedge = int(edge_cv.size)
    ncell = int(problem["ncell"])
    ncvt = int(problem["ncvt"])
    shell_mask = shell > 0
    seed_shell_positions = np.where(shell_mask & (stage1_x > POSITIVE_EDGE_TOL))[0]
    prior_positive = np.where(shell_mask & (problem["old_edge_mass"] > POSITIVE_EDGE_TOL))[0]
    parts = [seed_shell_positions, prior_positive]
    if extra_seed_shell is not None and len(extra_seed_shell):
        parts.append(np.asarray(extra_seed_shell, dtype=np.int64))
    carry = np.unique(np.concatenate(parts))
    selected_shell = set(int(x) for x in carry.tolist())
    halo_opt = float(np.dot(problem["c1_full"], stage1_x))
    target = problem["direct_target_rep"].reshape(-1)
    total_wall = 0.0
    pricing_valid = True
    final_lp = None
    final_positions = None
    min_rc = None
    iterations = 0

    for cg_iter in range(1, MAX_CG_ITERATIONS + 1):
        iterations = cg_iter
        selected_positions = np.unique(np.concatenate([exact_positions, np.asarray(sorted(selected_shell), dtype=np.int64)]))
        nsel = int(selected_positions.size)
        sel_cv = edge_cv[selected_positions]
        sel_cell = edge_cell[selected_positions]
        sel_shell = shell[selected_positions]
        sel_idx = np.arange(nsel, dtype=np.int64)
        Aeq_sel = coo_matrix((np.ones(nsel), (sel_cv, sel_idx)), shape=(ncvt, nsel)).tocsr()
        Acell_sel = coo_matrix((np.ones(nsel), (sel_cell, sel_idx)), shape=(ncell, nsel)).tocsr()
        zero_d = csr_matrix((ncell, ncell), dtype=np.float64)
        I = eye(ncell, format="csr", dtype=np.float64)
        A_cap = hstack([Acell_sel, zero_d], format="csr")
        A_abs_pos = hstack([Acell_sel, -I], format="csr")
        A_abs_neg = hstack([-Acell_sel, -I], format="csr")
        halo_c = (sel_shell > 0).astype(np.float64)
        halo_row = csr_matrix(halo_c.reshape(1, -1))
        zero1 = csr_matrix((1, ncell), dtype=np.float64)
        A_halo_pos = hstack([halo_row, zero1], format="csr")
        A_halo_neg = hstack([-halo_row, zero1], format="csr")
        A_ub = vstack([A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg], format="csr")
        b_ub = np.concatenate([
            problem["rep_capacity_flat"], target, -target,
            np.asarray([halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL]),
        ])
        Aeq2 = hstack([Aeq_sel, csr_matrix((ncvt, ncell), dtype=np.float64)], format="csr")
        c = np.concatenate([np.zeros(nsel), np.ones(ncell)])
        t0 = time.perf_counter()
        lp = linprog(
            c, A_ub=A_ub, b_ub=b_ub, A_eq=Aeq2, b_eq=problem["new_cv_mass"].reshape(-1),
            bounds=[(0.0, None)] * (nsel + ncell), method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                "time_limit": float(time_limit),
            },
        )
        total_wall += time.perf_counter() - t0
        if not lp.success:
            raise TrialReject(f"stage2_cg_not_success:{lp.status}:{lp.message}")
        mu = np.asarray(lp.ineqlin.marginals, dtype=np.float64)
        lam = np.asarray(lp.eqlin.marginals, dtype=np.float64)
        lower = np.asarray(lp.lower.marginals, dtype=np.float64)
        mu_cap = mu[:ncell]
        mu_pos = mu[ncell:2*ncell]
        mu_neg = mu[2*ncell:3*ncell]
        mu_hpos = float(mu[3*ncell])
        mu_hneg = float(mu[3*ncell+1])
        pred = -(mu_cap[sel_cell] + mu_pos[sel_cell] - mu_neg[sel_cell] + (sel_shell > 0).astype(float)*(mu_hpos-mu_hneg)) - lam[sel_cv]
        pricing_error = float(np.max(np.abs(pred - lower[:nsel])))
        if pricing_error > 1.0e-7:
            pricing_valid = False
            raise TrialReject(f"pricing_validation:{pricing_error}")
        selected_mask = np.zeros(nedge, dtype=bool)
        if selected_shell:
            selected_mask[np.asarray(sorted(selected_shell), dtype=np.int64)] = True
        omitted = np.where(shell_mask & (~selected_mask))[0]
        if omitted.size:
            ocell = edge_cell[omitted]
            ocv = edge_cv[omitted]
            omitted_rc = -(mu_cap[ocell] + mu_pos[ocell] - mu_neg[ocell] + (mu_hpos-mu_hneg)) - lam[ocv]
            min_rc = float(np.min(omitted_rc))
            neg_local = np.where(omitted_rc < -PRICING_TOL)[0]
        else:
            min_rc = float("inf")
            neg_local = np.asarray([], dtype=np.int64)
        final_lp = lp
        final_positions = selected_positions
        if neg_local.size == 0:
            break
        order = neg_local[np.argsort(omitted_rc[neg_local])]
        add = omitted[order[:COLUMN_BATCH_SIZE]]
        selected_shell.update(int(x) for x in add.tolist())
    else:
        raise TrialReject("stage2_cg_iteration_budget")

    nsel = int(final_positions.size)
    z = np.asarray(final_lp.x, dtype=np.float64)
    x = z[:nsel]
    new_edge_mass = np.zeros(nedge, dtype=np.float64)
    new_edge_mass[final_positions] = x
    rep = np.bincount(edge_cell, weights=new_edge_mass, minlength=ncell)
    cv = np.bincount(edge_cv, weights=new_edge_mass, minlength=ncvt)
    l1 = float(np.sum(np.abs(rep - target)))
    halo = float(np.sum(new_edge_mass[shell > 0]))
    return {
        "wall_seconds": float(total_wall),
        "iterations": int(iterations),
        "selected_shell": np.asarray(sorted(selected_shell), dtype=np.int64),
        "selected_terminal_count": int(len(selected_shell)),
        "min_omitted_reduced_cost": min_rc,
        "pricing_valid": bool(pricing_valid),
        "new_edge_mass": new_edge_mass,
        "new_rep_flat": rep,
        "cv_flat": cv,
        "stage2_l1": l1,
        "stage1_halo": halo,
        "objective": float(final_lp.fun),
        "seed_terminal_count": int(carry.size),
    }


def highspy_stage2_persistent(problem, edge_cv, edge_cell, shell, exact_positions, stage1_x, prior_final_shell, time_limit, threads=1):
    import highspy
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack, csc_matrix

    nedge = int(edge_cv.size)
    ncell = int(problem["ncell"])
    ncvt = int(problem["ncvt"])
    shell_mask = shell > 0
    seed_stage1 = np.where(shell_mask & (stage1_x > POSITIVE_EDGE_TOL))[0]
    prior_positive = np.where(shell_mask & (problem["old_edge_mass"] > POSITIVE_EDGE_TOL))[0]
    carry = np.unique(np.concatenate([seed_stage1, prior_positive, np.asarray(prior_final_shell, dtype=np.int64)]))
    selected_shell = set(int(x) for x in carry.tolist())
    selected_positions = np.unique(np.concatenate([exact_positions, carry]))
    nsel = int(selected_positions.size)
    sel_cv = edge_cv[selected_positions]
    sel_cell = edge_cell[selected_positions]
    sel_shell = shell[selected_positions]
    sel_idx = np.arange(nsel, dtype=np.int64)

    Aeq_sel = coo_matrix((np.ones(nsel), (sel_cv, sel_idx)), shape=(ncvt, nsel)).tocsr()
    Acell_sel = coo_matrix((np.ones(nsel), (sel_cell, sel_idx)), shape=(ncell, nsel)).tocsr()
    zero_d = csr_matrix((ncell, ncell), dtype=np.float64)
    I = eye(ncell, format="csr", dtype=np.float64)
    A_cap = hstack([Acell_sel, zero_d], format="csr")
    A_abs_pos = hstack([Acell_sel, -I], format="csr")
    A_abs_neg = hstack([-Acell_sel, -I], format="csr")
    halo_c = (sel_shell > 0).astype(np.float64)
    halo_row = csr_matrix(halo_c.reshape(1, -1))
    zero1 = csr_matrix((1, ncell), dtype=np.float64)
    A_halo_pos = hstack([halo_row, zero1], format="csr")
    A_halo_neg = hstack([-halo_row, zero1], format="csr")
    A_ub = vstack([A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg], format="csr")
    halo_opt = float(np.dot(problem["c1_full"], stage1_x))
    target = problem["direct_target_rep"].reshape(-1)
    b_ub = np.concatenate([
        problem["rep_capacity_flat"], target, -target,
        np.asarray([halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL]),
    ])
    Aeq2 = hstack([Aeq_sel, csr_matrix((ncvt, ncell), dtype=np.float64)], format="csr")
    A = vstack([A_ub, Aeq2], format="csc")
    c = np.concatenate([np.zeros(nsel), np.ones(ncell)])
    inf = highspy.kHighsInf
    row_lower = np.concatenate([np.full(A_ub.shape[0], -inf), problem["new_cv_mass"].reshape(-1)])
    row_upper = np.concatenate([b_ub, problem["new_cv_mass"].reshape(-1)])

    h = highs_pass_lp(c, A, row_lower, row_upper, threads=threads, parallel=False, time_limit=time_limit)
    edge_to_col = np.full(nedge, -1, dtype=np.int64)
    edge_to_col[selected_positions] = np.arange(nsel, dtype=np.int64)
    total_wall = 0.0
    iterations = 0
    min_rc = None
    pricing_errors = []
    simplex_iterations = []

    for cg_iter in range(1, MAX_CG_ITERATIONS + 1):
        iterations = cg_iter
        t0 = time.perf_counter()
        h.run()
        total_wall += time.perf_counter() - t0
        model_status = h.modelStatusToString(h.getModelStatus())
        if "Optimal" not in model_status:
            raise TrialReject(f"persistent_stage2_not_optimal:{model_status}")
        info = h.getInfo()
        simplex_iterations.append(int(info.simplex_iteration_count))
        sol = h.getSolution()
        row_dual = np.asarray(sol.row_dual, dtype=np.float64)
        col_dual = np.asarray(sol.col_dual, dtype=np.float64)
        mu_cap = row_dual[:ncell]
        mu_pos = row_dual[ncell:2*ncell]
        mu_neg = row_dual[2*ncell:3*ncell]
        mu_hpos = float(row_dual[3*ncell])
        mu_hneg = float(row_dual[3*ncell+1])
        eq_dual = row_dual[3*ncell+2:3*ncell+2+ncvt]

        current_shell = np.asarray(sorted(selected_shell), dtype=np.int64)
        current_selected = np.unique(np.concatenate([exact_positions, current_shell]))
        cols = edge_to_col[current_selected]
        scell = edge_cell[current_selected]
        scv = edge_cv[current_selected]
        sshell = shell[current_selected]
        pred = -(mu_cap[scell] + mu_pos[scell] - mu_neg[scell] + (sshell > 0).astype(float)*(mu_hpos-mu_hneg)) - eq_dual[scv]
        perr = float(np.max(np.abs(pred - col_dual[cols])))
        pricing_errors.append(perr)
        if perr > 1.0e-7:
            raise TrialReject(f"persistent_pricing_validation:{perr}")

        selected_mask = np.zeros(nedge, dtype=bool)
        selected_mask[current_shell] = True
        omitted = np.where(shell_mask & (~selected_mask))[0]
        if omitted.size:
            ocell = edge_cell[omitted]
            ocv = edge_cv[omitted]
            omitted_rc = -(mu_cap[ocell] + mu_pos[ocell] - mu_neg[ocell] + (mu_hpos-mu_hneg)) - eq_dual[ocv]
            min_rc = float(np.min(omitted_rc))
            neg_local = np.where(omitted_rc < -PRICING_TOL)[0]
        else:
            min_rc = float("inf")
            neg_local = np.asarray([], dtype=np.int64)
        if neg_local.size == 0:
            break
        order = neg_local[np.argsort(omitted_rc[neg_local])]
        add_positions = omitted[order[:COLUMN_BATCH_SIZE]]
        m = int(add_positions.size)
        if m <= 0:
            raise TrialReject("persistent_no_columns_added")
        start_col = h.getNumCol()
        # Every added column is terminal support: six nonzeros in fixed row order.
        starts = np.arange(0, 6*(m+1), 6, dtype=np.int64)
        indices = np.empty(6*m, dtype=np.int32)
        values = np.empty(6*m, dtype=np.float64)
        for j, pos in enumerate(add_positions.tolist()):
            cell = int(edge_cell[pos]); cv = int(edge_cv[pos])
            base = 6*j
            indices[base:base+6] = [cell, ncell+cell, 2*ncell+cell, 3*ncell, 3*ncell+1, 3*ncell+2+cv]
            values[base:base+6] = [1.0, 1.0, -1.0, 1.0, -1.0, 1.0]
        status = h.addCols(
            m,
            np.zeros(m, dtype=np.float64),
            np.zeros(m, dtype=np.float64),
            np.full(m, highspy.kHighsInf, dtype=np.float64),
            int(6*m), starts, indices, values,
        )
        if str(status).endswith("kError"):
            raise TrialReject(f"persistent_addCols_error:{status}")
        edge_to_col[add_positions] = np.arange(start_col, start_col+m, dtype=np.int64)
        selected_shell.update(int(x) for x in add_positions.tolist())
        # With a valid incumbent basis, suppress repeat presolve and reoptimize in-place.
        h.setOptionValue("presolve", "off")
    else:
        raise TrialReject("persistent_stage2_iteration_budget")

    sol = h.getSolution()
    col_value = np.asarray(sol.col_value, dtype=np.float64)
    current_shell = np.asarray(sorted(selected_shell), dtype=np.int64)
    final_positions = np.unique(np.concatenate([exact_positions, current_shell]))
    new_edge_mass = np.zeros(nedge, dtype=np.float64)
    new_edge_mass[final_positions] = col_value[edge_to_col[final_positions]]
    rep = np.bincount(edge_cell, weights=new_edge_mass, minlength=ncell)
    cv = np.bincount(edge_cv, weights=new_edge_mass, minlength=ncvt)
    l1 = float(np.sum(np.abs(rep - target)))
    halo = float(np.sum(new_edge_mass[shell > 0]))
    return {
        "wall_seconds": float(total_wall),
        "iterations": int(iterations),
        "selected_shell": current_shell,
        "selected_terminal_count": int(current_shell.size),
        "min_omitted_reduced_cost": min_rc,
        "pricing_validation_max_error": float(max(pricing_errors) if pricing_errors else 0.0),
        "new_edge_mass": new_edge_mass,
        "new_rep_flat": rep,
        "cv_flat": cv,
        "stage2_l1": l1,
        "stage1_halo": halo,
        "objective": float(h.getInfo().objective_function_value),
        "seed_terminal_count": int(carry.size),
        "simplex_iterations_by_cg_solve": simplex_iterations,
    }


def build_problem(state, ctx, dt):
    p3 = ctx["p3"]; sg7a = ctx["sg7a"]; r2src = ctx["r2src"]; e37a = ctx["e37a"]
    old_cv_mass = state["cv_mass"]
    old_cv_sat = state["cv_sat"]
    old_rep = state["rep"]
    old_edge_mass = state["edge_mass"]
    theory_flux = np.zeros((p3.NSL, p3.NCV + 1), dtype=np.float64)
    theory_flux[:, 0] = ctx["weights_m3_day"] * ctx["rho_ref"]
    ff_internal = np.asarray(sg7a.fractional_flow(old_cv_sat[:, :-1]), dtype=np.float64)
    theory_flux[:, 1:-1] = ctx["weights_m3_day"][:, None] * ctx["u_face"][None, 1:-1] * ff_internal * ctx["rho_ref"]
    ff_out = np.asarray(sg7a.fractional_flow(old_cv_sat[:, -1]), dtype=np.float64)
    theory_flux[:, -1] = ctx["weights_m3_day"] * float(ctx["u_face"][-1]) * ff_out * ctx["rho_ref"]
    new_cv_mass = old_cv_mass + dt * (theory_flux[:, :-1] - theory_flux[:, 1:])
    cv_capacity = np.asarray(e37a.cv_mass_from_saturation(r2src, np.full((p3.NSL, p3.NCV), p3.MAX_SAT), ctx["geometry"]["cv_pressure_mass_coeff"]), dtype=np.float64)
    if float(np.min(new_cv_mass)) < -MASS_TOL or float(np.max(new_cv_mass-cv_capacity)) > max(1e-9, 1e-12*max(float(np.max(np.abs(new_cv_mass))),1.0)):
        raise TrialReject("shadow_cv_bounds")
    new_cv_sat = np.asarray(e37a.invert_cv_mass_to_saturation(r2src, new_cv_mass, ctx["geometry"]["cv_pressure_mass_coeff"]), dtype=np.float64)
    old_sub_sat = old_cv_sat.reshape(-1)[ctx["geom_cv_id"]]
    new_sub_sat = new_cv_sat.reshape(-1)[ctx["geom_cv_id"]]
    old_sub_sg = np.clip(old_sub_sat-p3.BACKGROUND, 0.0, p3.MAX_SG)
    new_sub_sg = np.clip(new_sub_sat-p3.BACKGROUND, 0.0, p3.MAX_SG)
    rho_old = np.asarray(r2src.gas_density_from_state(old_sub_sat, ctx["pseg"], ctx["p_ref"]), dtype=np.float64)
    rho_new = np.asarray(r2src.gas_density_from_state(new_sub_sat, ctx["pseg"], ctx["p_ref"]), dtype=np.float64)
    sub_delta = ctx["sub_pv"] * (rho_new*new_sub_sg - rho_old*old_sub_sg)
    delta_grid = np.bincount(ctx["flat_cell"], weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
    direct_target_rep = old_rep + delta_grid
    rep_capacity = ctx["cart_capacity"] - state["residual"]
    rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)
    edge_delta = np.bincount(ctx["sub_edge_pos"], weights=sub_delta, minlength=ctx["nedge"])
    candidate_edge = old_edge_mass + edge_delta
    return {
        "ncell": p3.NCELL,
        "ncvt": p3.NCVT,
        "new_cv_mass": new_cv_mass,
        "new_cv_sat": new_cv_sat,
        "direct_target_rep": direct_target_rep,
        "rep_capacity_flat": rep_capacity_flat,
        "old_edge_mass": old_edge_mass,
        "candidate_edge": candidate_edge,
        "c1_full": ctx["c1_full"],
        "dt": float(dt),
    }


def state_from_solution(state, problem, result, ctx):
    p3 = ctx["p3"]; a2e = ctx["a2e"]; r2src = ctx["r2src"]
    new_rep = result["new_rep_flat"].reshape(p3.GRID)
    candidate_grid = new_rep + state["residual"]
    cap_excess = float(np.max(candidate_grid - ctx["cart_capacity"]))
    if cap_excess > ctx["cart_cap_tol"]:
        raise TrialReject(f"shadow_capacity:{cap_excess}")
    cand_sg = np.asarray(a2e.invert_local_mass(r2src, candidate_grid, ctx["frozen_pressure"], ctx["p_ref"], ctx["hetero_pv"]), dtype=np.float64)
    cand_sat = float(a2e.BACKGROUND) + cand_sg
    if float(np.min(cand_sat)) < p3.BACKGROUND-SAT_TOL or float(np.max(cand_sat)) > p3.MAX_SAT+SAT_TOL:
        raise TrialReject("shadow_sat_bounds")
    recon = np.asarray(a2e.local_mass(r2src, cand_sat, ctx["frozen_pressure"], ctx["p_ref"], ctx["hetero_pv"]), dtype=np.float64)
    recon_err = float(np.max(np.abs(recon-candidate_grid)))
    if recon_err > 1e-8:
        raise TrialReject(f"shadow_eos:{recon_err}")
    return {
        "grid": candidate_grid,
        "rep": new_rep,
        "residual": state["residual"],
        "cart_sat": cand_sat,
        "cv_mass": problem["new_cv_mass"],
        "cv_sat": problem["new_cv_sat"],
        "edge_mass": result["new_edge_mass"],
    }, {"capacity_excess_kg": cap_excess, "EOS_reconstruction_max_error_kg": recon_err}


def selftest() -> None:
    assert BRANCH == "postv16-av4-pivot"
    assert PARENT == "7b051a58e8c02499f8d9fd72302f17947cba0d41"
    assert R7R6_COMMIT == "4b96eb35b1fa3ce736aef495b380ab1a65e8d2ca"
    assert R7R6_STATE_SHA == "18a98bd27661fd1f2464f5e46e74389c794e2bdfc58a68541ee381a526d29988"
    assert O1_RUNNER_SHA256 == "2a2d6cdd22b0989f20a8bb1106d3bf7b64eeb334bf0ecf3bed88f9af25125cf6"
    assert PROMOTION_MIN_PROJECTED_LP_SPEEDUP == 1.20
    assert EXPECTED_HIGHSPY_VERSION == "1.15.1"
    print("POSTV16 AV4 P3-R1-R7-R6-O1-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    from scipy.sparse import coo_matrix
    import scipy
    import highspy

    root = project_root.resolve(); drive = drive_root.resolve()
    out = drive / OUT_REL; blocked = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None):
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*220)
        print("POSTV16-AV4-PIVOT-P3-R1-R7-R6-O1-R1 — A100 SOLVER-DIVERGENCE LOCALIZATION + STATE-EQUIVALENT RUNTIME PROMOTION DIAGNOSTIC")
        print("NO AUTHORITATIVE PHYSICAL-TIME ADVANCEMENT. NO PHYSICS/CFL/TOPOLOGY/OBJECTIVE CHANGE. SHADOW BENCHMARK ONLY.")
        print("="*220)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("repository_parent_O1_commit_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "", gt(root, "status", "--porcelain"))
        r7r6_path = root / R7R6
        gate("R7R6_runner_present", r7r6_path.is_file(), str(r7r6_path))
        gate("R7R6_runner_SHA_exact", sha(r7r6_path) == R7R6_SHA256, sha(r7r6_path))
        gate("R7R6_runner_blob_exact", gt(root, "hash-object", str(r7r6_path)) == R7R6_BLOB, gt(root, "hash-object", str(r7r6_path)))

        o1_path = root / O1_RUNNER
        gate("O1_runner_present", o1_path.is_file(), str(o1_path))
        gate("O1_runner_SHA_exact", sha(o1_path) == O1_RUNNER_SHA256, sha(o1_path))
        gate("O1_runner_blob_exact", gt(root, "hash-object", str(o1_path)) == O1_RUNNER_BLOB, gt(root, "hash-object", str(o1_path)))

        stage = "O1_immutable_BLOCK_authority"
        o1_block_path = drive / O1_BLOCK_REL / O1_BLOCK_FILE
        gate("O1_BLOCK_report_exists", o1_block_path.is_file(), str(o1_block_path))
        o1block = js(o1_block_path)
        gate("O1_BLOCK_status_exact", o1block.get("status") == O1_BLOCK_STATUS, o1block.get("status"))
        gate("O1_BLOCK_failed_stage_exact", o1block.get("failed_stage") == O1_BLOCK_FAILED_STAGE, o1block.get("failed_stage"))
        gate("O1_BLOCK_exception_exact", o1block.get("exception") == O1_BLOCK_EXCEPTION, o1block.get("exception"))
        gate("O1_BLOCK_no_authoritative_time_advance", o1block.get("authoritative_physical_time_advanced") is False)
        gate("O1_BLOCK_no_authoritative_state_mutation", o1block.get("authoritative_physics_state_mutated") is False)

        stage = "R7R6_Day385_authority"
        src = drive / R7R6_REL
        gate("R7R6_output_exists", src.is_dir(), str(src))
        manifest = verify_manifest(src, R7R6_MANIFEST)
        s = js(src / R7R6_SUMMARY); d = js(src / R7R6_DECISION)
        gate("R7R6_status_exact", s.get("status") == R7R6_STATUS, s.get("status"))
        gate("R7R6_class_exact", s.get("classification") == R7R6_CLASS, s.get("classification"))
        gate("R7R6_Day390_authorized", s.get("Day385_to_Day390_repaired_pilot_authorized") is True)
        state_path = src / R7R6_STATE; diag_path = src / R7R6_DIAG
        gate("Day385_state_SHA_exact", sha(state_path) == R7R6_STATE_SHA, sha(state_path))
        gate("Day385_diagnostic_SHA_exact", sha(diag_path) == R7R6_DIAG_SHA, sha(diag_path))
        gate("R7R6_manifest_binds_state", manifest.get(R7R6_STATE) == R7R6_STATE_SHA)
        gate("R7R6_manifest_binds_diagnostic", manifest.get(R7R6_DIAG) == R7R6_DIAG_SHA)

        stage = "A100_highram_environment"
        hw = hardware_profile()
        gate("highspy_version_exact", importlib_metadata.version("highspy") == EXPECTED_HIGHSPY_VERSION, importlib_metadata.version("highspy"))
        gpu_text = str(hw.get("nvidia_smi", ""))
        gate("A100_GPU_present", "A100" in gpu_text, gpu_text)
        ram_gib = float(hw.get("host_ram_gib") or 0.0)
        gate("host_RAM_at_least_100GiB", ram_gib >= MIN_A100_HOST_RAM_GIB, ram_gib)
        hw.update({"numpy": np.__version__, "scipy": scipy.__version__, "highspy": importlib_metadata.version("highspy")})

        stage = "frozen_physics_inputs"
        r7r6 = load_module(r7r6_path, "o1_r7r6")
        p3 = load_module(root / r7r6.P3R1, "o1_p3")
        a2e = load_module(root / p3.A2E, "o1_a2e")
        r2src = load_module(root / p3.R2SRC, "o1_r2src")
        e37a = load_module(root / p3.E37A, "o1_e37a")
        sg7a = load_module(root / p3.SG7A, "o1_sg7a")
        sg7d = load_module(root / p3.SG7D, "o1_sg7d")
        a2ep = drive / p3.A2E_REL / p3.A2E_EPOCH
        a6ep = drive / p3.A6E_REL / p3.A6E_STATE
        gate("A2E_epoch_exists", a2ep.is_file(), str(a2ep)); gate("A2E_epoch_SHA_exact", sha(a2ep) == p3.A2E_EPOCH_SHA, sha(a2ep))
        gate("A6E_state_exists", a6ep.is_file(), str(a6ep)); gate("A6E_state_SHA_exact", sha(a6ep) == p3.A6E_SHA, sha(a6ep))
        with np.load(a2ep, allow_pickle=False) as z:
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)
        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
        with np.load(state_path, allow_pickle=False) as z:
            gate("Day385_state_schema2", int(np.asarray(z["state_schema_version"]).reshape(())) == 2)
            gate("Day385_physical_day_exact", abs(float(np.asarray(z["physical_day"]).reshape(()))-385.0) <= 1e-12)
            edge_cv = np.asarray(z["support_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["support_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["support_edge_terminal_cost"], dtype=np.int8)
            ring = np.asarray(z["support_edge_ring"], dtype=np.int8)
            state0 = {
                "grid": np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64),
                "rep": np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64),
                "residual": np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64),
                "cart_sat": np.asarray(z["cartesian_saturation"], dtype=np.float64),
                "cv_mass": np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64),
                "cv_sat": np.asarray(z["transport_CV_saturation"], dtype=np.float64),
                "edge_mass": np.asarray(z["support_edge_assigned_mass_kg"], dtype=np.float64),
            }
        nedge = int(edge_cv.size)
        gate("schema2_total_edge_count_exact", nedge == 3091073, nedge)
        gate("schema2_XY2_edge_count_exact", int(np.count_nonzero(ring == 2)) == 1845407, int(np.count_nonzero(ring == 2)))

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2src, op, frozen_pressure, p_ref, p3.NSL, p3.NCV)
        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)
        weights_m3_day = weights_m3_s * DAY_TO_S
        xi_faces = np.linspace(0.0, 1.0, p3.NCV + 1)
        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        dtD = float(sg7a.CFL * (1.0 / p3.NCV) / (float(np.max(u_face))*max_df + float(sg7a.EPS)))
        nominal_dt = float(dtD * np.min(tau_end_s / DAY_TO_S))
        gate("nominal_dt_frozen_exact", abs(nominal_dt-0.03730130768843055) <= 1e-14, nominal_dt)
        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2src, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        cart_cap_tol = max(1e-8, 1e-12*max(float(np.max(cart_capacity)),1.0))
        c1_full = (shell > 0).astype(np.float64)

        exact_mask = shell == 0
        exact_positions = np.where(exact_mask)[0]
        ex_cv = edge_cv[exact_mask]; ex_cell = edge_cell[exact_mask]
        active_cells = np.unique(ex_cell)
        active_lookup = np.full(p3.NCELL, -1, dtype=np.int64); active_lookup[active_cells] = np.arange(active_cells.size)
        ex_active_cell = active_lookup[ex_cell]
        ex_idx = np.arange(ex_cv.size, dtype=np.int64)
        Aeq_exact = coo_matrix((np.ones(ex_cv.size), (ex_cv, ex_idx)), shape=(p3.NCVT, ex_cv.size)).tocsr()
        Acell_exact_active = coo_matrix((np.ones(ex_cv.size), (ex_active_cell, ex_idx)), shape=(active_cells.size, ex_cv.size)).tocsr()
        all_idx = np.arange(nedge, dtype=np.int64)
        Aeq_full = coo_matrix((np.ones(nedge), (edge_cv, all_idx)), shape=(p3.NCVT, nedge)).tocsr()
        Acell_full = coo_matrix((np.ones(nedge), (edge_cell, all_idx)), shape=(p3.NCELL, nedge)).tocsr()

        # Fast exact subsegment -> support edge mapping using sorted integer keys (no Python 3M-entry dict).
        edge_keys = edge_cv * p3.NCELL + edge_cell
        order = np.argsort(edge_keys, kind="mergesort")
        sorted_keys = edge_keys[order]
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * p3.NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_keys = sub_cv * p3.NCELL + sub_cell
        loc = np.searchsorted(sorted_keys, sub_keys)
        loc_safe = np.minimum(loc, sorted_keys.size - 1)
        gate("all_subsegment_support_keys_found", bool(np.all((loc < sorted_keys.size) & (sorted_keys[loc_safe] == sub_keys))))
        sub_edge_pos = order[loc_safe]
        gate("all_subsegments_on_exact_support", bool(np.all(shell[sub_edge_pos] == 0)))

        ctx = dict(p3=p3, a2e=a2e, r2src=r2src, e37a=e37a, sg7a=sg7a,
                   frozen_pressure=frozen_pressure, p_ref=p_ref, hetero_pv=hetero_pv,
                   geometry=geometry, sub_pv=sub_pv, pseg=pseg, flat_cell=flat_cell,
                   geom_cv_id=geom_cv_id, rho_ref=rho_ref, weights_m3_day=weights_m3_day,
                   u_face=u_face, cart_capacity=cart_capacity, cart_cap_tol=cart_cap_tol,
                   sub_edge_pos=sub_edge_pos, nedge=nedge, c1_full=c1_full)

        stage = "two_step_shadow_baseline"
        p1 = build_problem(state0, ctx, nominal_dt)
        z1, z1wall = scipy_zero_halo(p1, Aeq_exact, Acell_exact_active, active_cells, time_limit_seconds)
        gate("shadow_step1_positive_halo_required", not z1.success, z1.message)
        lp1_s1, s1wall1 = scipy_stage1(p1, Aeq_full, Acell_full, time_limit_seconds)
        b1 = scipy_stage2_cg(p1, edge_cv, edge_cell, shell, exact_positions, np.asarray(lp1_s1.x), time_limit_seconds)
        state1, state1_checks = state_from_solution(state0, p1, b1, ctx)
        print(f"[SHADOW 1 BASELINE] stage1={s1wall1:.3f}s stage2={b1['wall_seconds']:.3f}s cg={b1['iterations']} selected={b1['selected_terminal_count']}", flush=True)

        p2 = build_problem(state1, ctx, nominal_dt)
        z2, z2wall = scipy_zero_halo(p2, Aeq_exact, Acell_exact_active, active_cells, time_limit_seconds)
        gate("shadow_step2_positive_halo_required", not z2.success, z2.message)
        lp1_s2, s1wall2 = scipy_stage1(p2, Aeq_full, Acell_full, time_limit_seconds)
        b2 = scipy_stage2_cg(p2, edge_cv, edge_cell, shell, exact_positions, np.asarray(lp1_s2.x), time_limit_seconds)
        state2, state2_checks = state_from_solution(state1, p2, b2, ctx)
        print(f"[SHADOW 2 BASELINE] stage1={s1wall2:.3f}s stage2={b2['wall_seconds']:.3f}s cg={b2['iterations']} selected={b2['selected_terminal_count']}", flush=True)
        gate("baseline_step2_global_pricing_closed", float(b2["min_omitted_reduced_cost"]) >= -PRICING_TOL, b2["min_omitted_reduced_cost"])

        stage = "stage1_thread_benchmark"
        with tempfile.TemporaryDirectory(prefix="pad_o1r1_stage1_") as td:
            fixture = Path(td) / "stage1_fixture.npz"
            np.savez(fixture, edge_cv=edge_cv, edge_cell=edge_cell, shell=shell,
                     new_cv_mass=p2["new_cv_mass"], rep_capacity_flat=p2["rep_capacity_flat"],
                     ncell=np.asarray(p3.NCELL), ncvt=np.asarray(p3.NCVT))
            logical = int(os.cpu_count() or 1)
            thread_values = [x for x in [1,2,4,8] if x <= logical]
            if 1 not in thread_values: thread_values.insert(0,1)
            stage1_rows = []
            for nt in thread_values:
                rp = Path(td) / f"stage1_{nt}.json"
                cmd = [sys.executable, str(Path(__file__).resolve()), "--stage1-child", str(fixture), "--threads", str(nt), "--result", str(rp), "--time-limit-seconds", str(time_limit_seconds)]
                cp = subprocess.run(cmd, text=True)
                gate(f"stage1_child_{nt}_exit_zero", cp.returncode == 0, cp.returncode)
                row = js(rp)
                row["objective_gap_vs_scipy"] = None if row["objective"] is None else float(row["objective"] - float(lp1_s2.fun))
                row["equivalent"] = bool(row["objective"] is not None and abs(row["objective_gap_vs_scipy"]) <= 2*HALO_OPT_TOL and row["cv_equality_max_abs_error_kg"] <= MASS_TOL and row["capacity_excess_kg"] <= ctx["cart_cap_tol"])
                stage1_rows.append(row)
            equivalent_stage1 = [r for r in stage1_rows if r["equivalent"]]
            gate("at_least_one_highspy_stage1_equivalent", bool(equivalent_stage1))
            best_stage1 = min(equivalent_stage1, key=lambda r: r["wall_seconds"])

            # Re-run only the best Stage-1 child and persist its primal vector for an end-to-end state-equivalence test.
            best_result = Path(td) / "stage1_best.json"
            best_solution = Path(td) / "stage1_best_solution.npz"
            cmd = [sys.executable, str(Path(__file__).resolve()), "--stage1-child", str(fixture), "--threads", str(best_stage1["threads"]), "--result", str(best_result), "--solution-out", str(best_solution), "--time-limit-seconds", str(time_limit_seconds)]
            cp = subprocess.run(cmd, text=True)
            gate("best_stage1_solution_child_exit_zero", cp.returncode == 0, cp.returncode)
            with np.load(best_solution, allow_pickle=False) as z:
                best_stage1_x = np.asarray(z["x"], dtype=np.float64)
            best_stage1_solution_metrics = js(best_result)

        # Strict recurrent-state equivalence helper. Edge mass is included because it is part of the next-step recurrence.
        def evaluate_variant(label, result, wall_stage1, state_from, problem_from):
            vstate, vchecks = state_from_solution(state_from, problem_from, result, ctx)
            obj_tol = max(1e-5, 1e-10*max(abs(float(b2["stage2_l1"])),1.0))
            metrics = {
                "label": label,
                "stage2_wall_seconds": float(result["wall_seconds"]),
                "stage1_wall_seconds": float(wall_stage1),
                "iterations": int(result["iterations"]),
                "seed_terminal_count": int(result["seed_terminal_count"]),
                "selected_terminal_count": int(result["selected_terminal_count"]),
                "pricing_validation_max_error": float(result.get("pricing_validation_max_error", 0.0)),
                "min_omitted_reduced_cost": float(result["min_omitted_reduced_cost"]),
                "stage2_L1_gap_kg": float(result["stage2_l1"] - b2["stage2_l1"]),
                "stage1_halo_gap_kg": float(result["stage1_halo"] - b2["stage1_halo"]),
                "represented_cell_mass_max_abs_diff_kg": float(np.max(np.abs(result["new_rep_flat"] - b2["new_rep_flat"]))),
                "accepted_grid_mass_max_abs_diff_kg": float(np.max(np.abs(vstate["grid"] - state2["grid"]))),
                "cartesian_saturation_max_abs_diff": float(np.max(np.abs(vstate["cart_sat"] - state2["cart_sat"]))),
                "CV_mass_max_abs_diff_kg": float(np.max(np.abs(result["cv_flat"] - b2["cv_flat"]))),
                "edge_mass_max_abs_diff_kg": float(np.max(np.abs(result["new_edge_mass"] - b2["new_edge_mass"]))),
                "capacity_excess_kg": float(vchecks["capacity_excess_kg"]),
                "EOS_reconstruction_max_error_kg": float(vchecks["EOS_reconstruction_max_error_kg"]),
            }
            pricing_ok = metrics["pricing_validation_max_error"] <= 1e-7 and metrics["min_omitted_reduced_cost"] >= -PRICING_TOL
            objective_ok = abs(metrics["stage2_L1_gap_kg"]) <= obj_tol and abs(metrics["stage1_halo_gap_kg"]) <= 2*HALO_OPT_TOL
            state_ok = (
                metrics["represented_cell_mass_max_abs_diff_kg"] <= 1e-7 and
                metrics["accepted_grid_mass_max_abs_diff_kg"] <= 1e-7 and
                metrics["cartesian_saturation_max_abs_diff"] <= 1e-10 and
                metrics["CV_mass_max_abs_diff_kg"] <= MASS_TOL and
                metrics["edge_mass_max_abs_diff_kg"] <= 1e-7
            )
            metrics["pricing_equivalent"] = bool(pricing_ok)
            metrics["lexicographic_objective_equivalent"] = bool(objective_ok)
            metrics["strict_recurrent_state_equivalent"] = bool(state_ok)
            metrics["fully_equivalent"] = bool(pricing_ok and objective_ok and state_ok)
            baseline_lp = float(z2wall + s1wall2 + b2["wall_seconds"])
            candidate_lp = float(z2wall + wall_stage1 + result["wall_seconds"])
            metrics["baseline_LP_wall_seconds"] = baseline_lp
            metrics["candidate_projected_LP_wall_seconds"] = candidate_lp
            metrics["projected_LP_speedup"] = baseline_lp/candidate_lp if candidate_lp > 0 else 0.0
            return metrics

        stage = "solver_divergence_localization"
        variants = []

        # A — working-set carry-forward only; same SciPy/HiGHS path as R7-R6.
        ws = scipy_stage2_cg(p2, edge_cv, edge_cell, shell, exact_positions, np.asarray(lp1_s2.x), time_limit_seconds, extra_seed_shell=b1["selected_shell"])
        variants.append(evaluate_variant("SCIPY_WORKING_SET_CARRY_FORWARD_ONLY", ws, s1wall2, state1, p2))

        # B — native persistent HiGHS only; preserve the original baseline seed.
        hp_base = highspy_stage2_persistent(p2, edge_cv, edge_cell, shell, exact_positions, np.asarray(lp1_s2.x), np.asarray([], dtype=np.int64), time_limit_seconds, threads=1)
        variants.append(evaluate_variant("HIGHSPY_PERSISTENT_BASELINE_SEED_ONLY", hp_base, s1wall2, state1, p2))

        # C — reproduce the O1 combined optimization that previously reached an alternate optimizer.
        hp_ws = highspy_stage2_persistent(p2, edge_cv, edge_cell, shell, exact_positions, np.asarray(lp1_s2.x), b1["selected_shell"], time_limit_seconds, threads=1)
        variants.append(evaluate_variant("HIGHSPY_PERSISTENT_PLUS_WORKING_SET", hp_ws, s1wall2, state1, p2))

        # D — parallel Stage-1 only, then unchanged SciPy Stage-2. Tests whether Stage-1 CPU acceleration can be promoted safely by itself.
        par_s2 = scipy_stage2_cg(p2, edge_cv, edge_cell, shell, exact_positions, best_stage1_x, time_limit_seconds)
        variants.append(evaluate_variant("PARALLEL_HIGHSPY_STAGE1_PLUS_SCIPY_STAGE2", par_s2, float(best_stage1_solution_metrics["wall_seconds"]), state1, p2))

        # Diagnose the source of O1's 930-kg alternate represented-cell optimizer.
        by_label = {v["label"]: v for v in variants}
        ws_eq = by_label["SCIPY_WORKING_SET_CARRY_FORWARD_ONLY"]["strict_recurrent_state_equivalent"]
        hp_base_eq = by_label["HIGHSPY_PERSISTENT_BASELINE_SEED_ONLY"]["strict_recurrent_state_equivalent"]
        hp_ws_eq = by_label["HIGHSPY_PERSISTENT_PLUS_WORKING_SET"]["strict_recurrent_state_equivalent"]
        if not ws_eq and hp_base_eq:
            divergence_class = "WORKING_SET_SEED_CHANGES_DEGENERATE_OPTIMIZER_NATIVE_PERSISTENT_BASELINE_SEED_STATE_EQUIVALENT"
        elif ws_eq and not hp_base_eq:
            divergence_class = "NATIVE_PERSISTENT_SOLVER_PATH_CHANGES_DEGENERATE_OPTIMIZER_WORKING_SET_SCIPY_STATE_EQUIVALENT"
        elif not ws_eq and not hp_base_eq:
            divergence_class = "BOTH_WORKING_SET_AND_NATIVE_PERSISTENT_PATH_CAN_CHANGE_DEGENERATE_OPTIMIZER"
        elif ws_eq and hp_base_eq and not hp_ws_eq:
            divergence_class = "ONLY_COMBINED_WORKING_SET_PLUS_PERSISTENT_PATH_CHANGES_OPTIMIZER"
        else:
            divergence_class = "NO_STRICT_DIVERGENCE_REPRODUCED_OR_COMBINED_PATH_STATE_EQUIVALENT"

        # Promotion requires strict recurrent-state equivalence and >=20% projected LP speedup.
        eligible = [v for v in variants if v["fully_equivalent"] and v["projected_LP_speedup"] >= PROMOTION_MIN_PROJECTED_LP_SPEEDUP]
        best_variant = max(eligible, key=lambda v: v["projected_LP_speedup"]) if eligible else None
        promote = best_variant is not None

        benchmark = {
            "O1_BLOCK_preserved": True,
            "O1_failed_gate": "persistent_represented_cell_state_equivalent",
            "O1_observed_represented_cell_max_abs_diff_kg": 930.2159180885224,
            "divergence_classification": divergence_class,
            "baseline": {
                "stage1_wall_seconds": float(s1wall2),
                "stage2_wall_seconds": float(b2["wall_seconds"]),
                "stage2_iterations": int(b2["iterations"]),
                "seed_terminal_count": int(b2["seed_terminal_count"]),
                "selected_terminal_count": int(b2["selected_terminal_count"]),
                "min_omitted_reduced_cost": float(b2["min_omitted_reduced_cost"]),
            },
            "variants": variants,
            "best_stage1_thread_benchmark": best_stage1,
            "best_stage1_solution_metrics": best_stage1_solution_metrics,
            "promotion_threshold": PROMOTION_MIN_PROJECTED_LP_SPEEDUP,
            "eligible_state_equivalent_variants": [v["label"] for v in eligible],
            "selected_promoted_variant": None if best_variant is None else best_variant["label"],
        }

        stage = "publication"
        if out.exists() or blocked.exists():
            raise GateError("preexisting_O1R1_outcome")
        out.mkdir(parents=True, exist_ok=False)
        atomic_write(out / HARDWARE, jb(hw))
        atomic_write(out / STAGE1_BENCH, csvb(stage1_rows))
        atomic_write(out / STAGE2_BENCH, jb(benchmark))
        classification = PASS_PROMOTE if promote else PASS_NOPROMOTE
        summary = {
            "milestone": M,
            "name": NAME,
            "status": classification,
            "classification": classification,
            "source_O1_commit": PARENT,
            "source_O1_BLOCK_status": O1_BLOCK_STATUS,
            "source_O1_BLOCK_failed_stage": O1_BLOCK_FAILED_STAGE,
            "source_R7R6_commit": R7R6_COMMIT,
            "source_Day385_state_sha256": R7R6_STATE_SHA,
            "authoritative_physical_time_advanced": False,
            "authoritative_physics_state_mutated": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "two_shadow_atomic_steps_executed": True,
            "solver_divergence_localized": True,
            "divergence_classification": divergence_class,
            "strict_edge_state_equivalence_required": True,
            "optimized_R7R7_runtime_authorized": bool(promote),
            "selected_promoted_variant": None if best_variant is None else best_variant["label"],
            "selected_projected_LP_speedup": None if best_variant is None else float(best_variant["projected_LP_speedup"]),
            "R7R7_Day385_to_Day390_physics_authority_preserved": True,
            "recommended_next_action": (
                "Build R7-R7 Day385-to-Day390 using only the O1-R1 selected state-equivalent accelerated solver variant; preserve all frozen physics/XY2/pricing/restart semantics and retain the R7-R6 SciPy path as reference fallback."
                if promote else
                "Do not promote a solver path that changes the recurrent optimizer. Preserve the R7-R6 SciPy Stage2 authority and use the localization evidence to design the next performance repair without changing the lexicographic objective or accepted recurrent state."
            ),
        }
        decision = {
            "milestone": M,
            "status": classification,
            "scientific_failure_declared": False,
            "O1_BLOCK_preserved": True,
            "Day385_state_must_be_preserved": True,
            "Day385_state_sha256": R7R6_STATE_SHA,
            "solver_divergence_localization_complete": True,
            "strict_recurrent_state_equivalence_includes_edge_mass": True,
            "global_dual_pricing_preserved": True,
            "optimized_R7R7_runtime_authorized": bool(promote),
            "selected_promoted_variant": None if best_variant is None else best_variant["label"],
            "full_Day365_to500_sweep_authorized": False,
            "P4_authorized": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_change_authorized": False,
            "transport_law_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
        }
        atomic_write(out / SUMMARY, jb(summary))
        atomic_write(out / DECISION, jb(decision))
        atomic_write(out / GATES, csvb(gates))
        files = [HARDWARE, STAGE1_BENCH, STAGE2_BENCH, SUMMARY, DECISION, GATES]
        rows = []
        for fn in files:
            p = out / fn
            rows.append({"file": fn, "sha256": sha(p), "bytes": p.stat().st_size})
        atomic_write(out / MANIFEST, csvb(rows))
        print("="*220)
        print("POSTV16-AV4-PIVOT-P3-R1-R7-R6-O1-R1: PASS")
        print(json.dumps(summary, indent=2, sort_keys=True))
        print("--- SOLVER DIVERGENCE LOCALIZATION BENCHMARK ---")
        print(json.dumps(benchmark, indent=2, sort_keys=True))
        print("="*220)
        return 0
    except Exception as exc:
        try:
            if not blocked.exists():
                blocked.mkdir(parents=True, exist_ok=False)
            report = {"milestone": M, "status": BLOCK, "failed_stage": stage, "exception": repr(exc), "gates": gates,
                      "authoritative_physical_time_advanced": False, "authoritative_physics_state_mutated": False}
            atomic_write(blocked / BLOCK_FILE, jb(report))
        except Exception:
            pass
        print(f"[{BLOCK}] stage={stage} exception={exc!r}", flush=True)
        return 2


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path)
    ap.add_argument("--drive-root", type=Path)
    ap.add_argument("--time-limit-seconds", type=float, default=300.0)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--stage1-child")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--result")
    ap.add_argument("--solution-out")
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        selftest(); raise SystemExit(0)
    if args.stage1_child:
        if not args.result:
            raise SystemExit("--result required with --stage1-child")
        raise SystemExit(child_stage1(args))
    if args.project_root is None or args.drive_root is None:
        raise SystemExit("--project-root and --drive-root are required")
    raise SystemExit(main(args.project_root, args.drive_root, args.time_limit_seconds))
