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
import time
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV5-A2"
NAME = "Exact-Correction Iterative Pressure Solver + Deterministic Warm-Start Feasibility Benchmark"

PASS = (
    "POSTV16AV5A2_EXACT_CORRECTION_ITERATIVE_PRESSURE_SOLVER_"
    "DETERMINISTIC_WARM_START_FEASIBILITY_BENCHMARK_PASS_NO_ML_NO_STATE_MUTATION"
)
BLOCK = "POSTV16AV5A2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "9313c12c68da7ae74f0e1c7d276f7d7a25ec771e"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

GRID = (15, 50, 50)
N = 37500

PRESSURE_GATE = 1.0e-8              # unchanged AV4 scientific gate
CORRECTION_TARGET = 1.0e-10         # tighter numerical target; does not relax science
PRESSURE_FIXED_POINT_TOL = 1.0e-10
SATURATION_FIXED_POINT_TOL = 1.0e-10
MAX_FIXED_POINT_ITERATIONS = 100
MAX_KRYLOV_ITERATIONS = 20000
TIMING_REPEATS = 3

AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
AV4_DAY = 375.0372167312886

# AV5-A1 authority.
A1_TOKEN = "POSTV16_AV5_A1"
A1_REL = BASE_AV5 / (A1_TOKEN + "_Learned_Pressure_Acceleration_Architecture_ExactCorrection_Design_Freeze")
A1_SUMMARY = "PAD_Stream_" + A1_TOKEN + "_Summary.json"
A1_DECISION = A1_TOKEN + "_Decision_Contract.json"
A1_MANIFEST = A1_TOKEN + "_Artifact_Manifest.csv"
A1_STATUS = (
    "POSTV16AV5A1_LEARNED_PRESSURE_ACCELERATION_ARCHITECTURE_AND_"
    "EXACT_FINITE_VOLUME_CORRECTION_DESIGN_FREEZE_PASS_NO_TRAINING_NO_EXECUTION"
)

A1_RUNNER = "PAD_Stream_POSTV16_AV5_A1_Learned_Pressure_Acceleration_Architecture_and_Exact_Correction_Design_Freeze.py"
A1_RUNNER_BLOB = "5a8e4d5642d85c1cacdf053d99aa8a5dd7467d17"

# R30 authoritative state.
R30_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R30"
R30_REL = BASE_AV4 / (R30_TOKEN + "_Atomic_Physical_Time_Commit_Accepted_AllCV_XY1_Candidate")
R30_MANIFEST = R30_TOKEN + "_Artifact_Manifest.csv"
R30_STATE = R30_TOKEN + "_Committed_State_Day375p0372167312886.npz"
R30_STATE_SHA = AV4_STATE_SHA

# Heterogeneous state.
A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

# Exact source authority.
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"
R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A1_RUNNER: A1_RUNNER_BLOB,
    A2E: A2E_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    R3R2R1: R3R2R1_BLOB,
    R2SRC: R2SRC_BLOB,
    PERM: PERM_BLOB,
}

OUT_TOKEN = "POSTV16_AV5_A2"
OUT_REL = BASE_AV5 / (OUT_TOKEN + "_ExactCorrection_IterativePressureSolver_DeterministicWarmStart_Benchmark")
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
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


def manifest(directory: Path, filename: str) -> dict[str, str]:
    out = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(np.linalg.norm((aa - bb).ravel()) / max(float(np.linalg.norm(bb.ravel())), 1.0e-30))


def lin_residual(A, p: np.ndarray, b: np.ndarray) -> float:
    r = np.asarray(A @ p - b, dtype=np.float64)
    return float(np.linalg.norm(r) / max(float(np.linalg.norm(b)), 1.0e-30))


def sparse_symmetry_max(A) -> float:
    d = (A - A.T).tocoo()
    if d.nnz == 0:
        return 0.0
    return float(np.max(np.abs(d.data)))


def matrix_structure(A) -> dict[str, Any]:
    csr = A.tocsr()
    diag = np.asarray(csr.diagonal(), dtype=np.float64)
    off = csr.copy()
    off.setdiag(0.0)
    off.eliminate_zeros()
    off_max = float(np.max(off.data)) if off.nnz else 0.0
    row_sum = np.asarray(csr.sum(axis=1)).reshape(-1)
    strict_rows = int(np.count_nonzero(row_sum > 0.0))
    return {
        "symmetry_max_abs": sparse_symmetry_max(csr),
        "diagonal_min": float(np.min(diag)),
        "diagonal_max": float(np.max(diag)),
        "offdiagonal_max": off_max,
        "row_sum_min": float(np.min(row_sum)),
        "row_sum_max": float(np.max(row_sum)),
        "strictly_anchored_row_count": strict_rows,
        "structural_SPD_candidate": bool(
            sparse_symmetry_max(csr) <= 1.0e-18
            and float(np.min(diag)) > 0.0
            and off_max <= 0.0
            and float(np.min(row_sum)) >= -1.0e-18
            and strict_rows > 0
        ),
    }


def timed_spsolve(A, b, repeats: int):
    from scipy.sparse.linalg import spsolve

    solutions = []
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        p = np.asarray(spsolve(A, b), dtype=np.float64)
        times.append(time.perf_counter() - t0)
        solutions.append(p)
    ref = solutions[0]
    for p in solutions[1:]:
        if rel_l2(p, ref) > 1.0e-13:
            raise GateError("nondeterministic_spsolve_result")
    return ref, times


def make_jacobi(A):
    from scipy.sparse.linalg import LinearOperator
    diag = np.asarray(A.diagonal(), dtype=np.float64)
    if np.any(diag <= 0.0) or not np.all(np.isfinite(diag)):
        raise GateError("invalid_jacobi_diagonal")
    inv = 1.0 / diag
    return LinearOperator(A.shape, matvec=lambda x: inv * x, dtype=np.float64)


def correction_cg(A, b, seed_pa, M, target_rel: float):
    from scipy.sparse.linalg import cg

    p0 = np.asarray(seed_pa, dtype=np.float64).reshape(-1)
    rhs_norm = max(float(np.linalg.norm(b)), 1.0e-30)

    t0 = time.perf_counter()
    r0 = np.asarray(b - A @ p0, dtype=np.float64)
    initial_rel = float(np.linalg.norm(r0) / rhs_norm)

    if initial_rel <= target_rel:
        elapsed = time.perf_counter() - t0
        return {
            "success": True,
            "info": 0,
            "iterations": 0,
            "initial_relative_residual": initial_rel,
            "final_relative_residual": initial_rel,
            "pressure_pa": p0.copy(),
            "seconds": elapsed,
        }

    count = 0

    def cb(_x):
        nonlocal count
        count += 1

    atol = target_rel * rhs_norm
    delta, info = cg(
        A,
        r0,
        x0=np.zeros_like(r0),
        rtol=0.0,
        atol=atol,
        maxiter=MAX_KRYLOV_ITERATIONS,
        M=M,
        callback=cb,
    )
    p = p0 + np.asarray(delta, dtype=np.float64)
    elapsed = time.perf_counter() - t0
    final_rel = lin_residual(A, p, b)
    return {
        "success": bool(info == 0 and np.all(np.isfinite(p)) and final_rel <= PRESSURE_GATE),
        "info": int(info),
        "iterations": int(count),
        "initial_relative_residual": initial_rel,
        "final_relative_residual": final_rel,
        "pressure_pa": p,
        "seconds": elapsed,
    }


def benchmark_seed(A, b, seed_pa, M, direct_pa, label: str, repeats: int) -> dict[str, Any]:
    runs = [correction_cg(A, b, seed_pa, M, CORRECTION_TARGET) for _ in range(repeats)]
    good = all(r["success"] for r in runs)
    times = np.asarray([r["seconds"] for r in runs], dtype=np.float64)
    iters = np.asarray([r["iterations"] for r in runs], dtype=np.int64)
    final = runs[0]["pressure_pa"]
    return {
        "label": label,
        "success": bool(good),
        "iterations_min": int(np.min(iters)),
        "iterations_median": float(np.median(iters)),
        "iterations_max": int(np.max(iters)),
        "seconds_min": float(np.min(times)),
        "seconds_median": float(np.median(times)),
        "seconds_max": float(np.max(times)),
        "initial_relative_residual": float(runs[0]["initial_relative_residual"]),
        "final_relative_residual": float(runs[0]["final_relative_residual"]),
        "pressure_relative_L2_vs_direct": rel_l2(final, direct_pa),
    }


def selftest():
    assert N == 37500
    assert CORRECTION_TARGET < PRESSURE_GATE
    assert AV4_STATE_SHA == R30_STATE_SHA
    print("POSTV16 AV5-A2 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []

    def gate(name: str, cond: Any, detail: Any = None):
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
        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "A1_design_authority"
        a1d = drive / A1_REL
        a1m = manifest(a1d, A1_MANIFEST)
        a1s = js(a1d / A1_SUMMARY)
        a1c = js(a1d / A1_DECISION)

        gate("A1_status_exact", a1s.get("status") == A1_STATUS, a1s.get("status"))
        gate("A1_AV4_state_SHA_exact", a1s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A1_A2_authorized", a1c.get("AV5_A2_authorized") is True)
        gate("A1_A2_execution_authorized", a1c.get("AV5_A2_execution_authorized") is True)
        gate("A1_A2_state_binding_exact", a1c.get("AV5_A2_must_bind_AV4_state_SHA") == AV4_STATE_SHA)
        gate("A1_direct_reference_required", a1c.get("AV5_A2_must_preserve_direct_spsolve_reference") is True)
        gate("A1_no_training", a1c.get("AV5_A2_must_not_train_model") is True)
        gate("A1_exact_correction_required", a1c.get("AV5_must_not_replace_exact_finite_volume_correction") is True)
        gate("A1_conservation_gates_frozen", a1c.get("AV5_must_not_relax_conservation_gates") is True)
        gate("A1_manifest_nonempty", len(a1m) > 0)

        stage = "R30_state_authority"
        r30d = drive / R30_REL
        r30m = manifest(r30d, R30_MANIFEST)
        r30p = r30d / R30_STATE
        gate("R30_state_manifested", R30_STATE in r30m)
        gate("R30_state_manifest_SHA_exact", r30m.get(R30_STATE) == R30_STATE_SHA)
        gate("R30_state_file_SHA_exact", r30p.is_file() and sha(r30p) == R30_STATE_SHA)

        with np.load(r30p, allow_pickle=False) as z:
            parent_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            parent_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            physical_day = float(np.asarray(z["physical_day"]).reshape(()))
            time_committed = bool(np.asarray(z["physical_time_committed"]).reshape(()))

        gate("R30_day_exact", abs(physical_day - AV4_DAY) <= 1.0e-12)
        gate("R30_time_committed", time_committed is True)
        gate("R30_mass_pressure_shapes", parent_mass.shape == GRID and parent_pressure.shape == GRID)

        stage = "heterogeneity_authority"
        a6ep = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6ep.is_file() and sha(a6ep) == A6E_SHA)
        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
            nw = np.asarray(z["nw"], dtype=np.float64)
            no = np.asarray(z["no"], dtype=np.float64)
            krw_max = np.asarray(z["krw_max"], dtype=np.float64)
            kro_max = np.asarray(z["kro_max"], dtype=np.float64)

        gate("heterogeneity_shapes_exact",
             all(a.shape == GRID for a in (phi, nw, no, krw_max, kro_max)))

        stage = "module_binding"
        a2e = load_module(root / A2E, "av5a2_a2e")
        sg2 = load_module(root / SG2, "av5a2_sg2")
        sg3 = load_module(root / SG3, "av5a2_sg3")
        r3 = load_module(root / R3R2R1, "av5a2_r3")
        r2 = load_module(root / R2SRC, "av5a2_r2")

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        gate("permeability_valid", permeability.shape == GRID and np.all(np.isfinite(permeability)) and np.all(permeability > 0.0))

        pore_volume = phi * float(a2e.BULK_VOLUME_M3)
        parent_sg = np.asarray(
            a2e.invert_local_mass(r2, parent_mass, parent_pressure, p_ref, pore_volume),
            dtype=np.float64,
        )
        parent_sat = float(a2e.BACKGROUND) + parent_sg
        gate("reconstructed_parent_saturation_bounds",
             float(np.min(parent_sat)) >= float(a2e.BACKGROUND) - 1.0e-12
             and float(np.max(parent_sat)) <= float(a2e.INJECTED) + 1.0e-12,
             [float(np.min(parent_sat)), float(np.max(parent_sat))])

        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        stage = "direct_fixed_point_reference_and_system_benchmark"
        working_sat = parent_sat.copy()
        previous_pressure = parent_pressure.copy()
        parent_seed_pa = parent_pressure.reshape(-1) * float(sg3.PSI_TO_PA)
        uniform_seed_pa = np.full(N, float(np.mean(parent_pressure)) * float(sg3.PSI_TO_PA), dtype=np.float64)
        zero_seed_pa = np.zeros(N, dtype=np.float64)

        reference_rows = []
        benchmark_rows = []
        direct_solve_seconds_total = 0.0
        direct_wall_start = time.perf_counter()

        accepted_pressure = None
        accepted_sat = None
        fixed_point_systems = []

        for iteration in range(1, MAX_FIXED_POINT_ITERATIONS + 1):
            mobility = a2e.spatial_mobility(working_sat, nw, no, krw_max, kro_max)
            tx, ty, tz, _face = r3.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, _wi = r3.assemble_updated_pressure_system(
                sg3, permeability, tx, ty, tz, mobility["lambda_total"]
            )

            ms = matrix_structure(A)
            gate(f"iter_{iteration:03d}_matrix_structural_SPD_candidate",
                 ms["structural_SPD_candidate"], ms)

            direct_pa, direct_times = timed_spsolve(A, b, TIMING_REPEATS)
            direct_median = float(np.median(np.asarray(direct_times, dtype=np.float64)))
            direct_solve_seconds_total += direct_median
            direct_rel = lin_residual(A, direct_pa, b)
            gate(f"iter_{iteration:03d}_direct_residual", direct_rel < PRESSURE_GATE, direct_rel)

            Mj = make_jacobi(A)
            prev_seed_pa = previous_pressure.reshape(-1) * float(sg3.PSI_TO_PA)

            # Benchmark all important seeds on the first system, and the two realistic
            # recurrent seeds on every subsequent system.
            seeds = {
                "previous_pressure": prev_seed_pa,
                "parent_pressure": parent_seed_pa,
            }
            if iteration == 1:
                seeds["uniform_mean_pressure"] = uniform_seed_pa
                seeds["zero_pressure"] = zero_seed_pa
                seeds["ideal_exact_teacher"] = direct_pa

            seed_results = {}
            for label, seed in seeds.items():
                res = benchmark_seed(A, b, seed, Mj, direct_pa, label, TIMING_REPEATS)
                seed_results[label] = res
                benchmark_rows.append({
                    "fixed_point_iteration": iteration,
                    **{k: v for k, v in res.items() if k != "label"},
                    "seed_label": label,
                    "direct_spsolve_seconds_median": direct_median,
                    "direct_relative_residual": direct_rel,
                    "matrix_symmetry_max_abs": ms["symmetry_max_abs"],
                    "matrix_diagonal_min": ms["diagonal_min"],
                    "matrix_strictly_anchored_row_count": ms["strictly_anchored_row_count"],
                })
                gate(f"iter_{iteration:03d}_{label}_correction_success", res["success"], res)
                gate(f"iter_{iteration:03d}_{label}_pressure_equivalence",
                     float(res["pressure_relative_L2_vs_direct"]) <= 1.0e-8,
                     res["pressure_relative_L2_vs_direct"])

            direct_psi = (direct_pa * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
            sg_new = np.asarray(a2e.invert_local_mass(r2, parent_mass, direct_psi, p_ref, pore_volume), dtype=np.float64)
            sat_new = float(a2e.BACKGROUND) + sg_new

            pressure_delta = rel_l2(direct_psi, previous_pressure)
            saturation_delta = float(np.max(np.abs(sat_new - working_sat)))

            reference_rows.append({
                "fixed_point_iteration": iteration,
                "direct_relative_residual": direct_rel,
                "direct_spsolve_seconds_median": direct_median,
                "pressure_relative_L2_change": pressure_delta,
                "saturation_Linf_change": saturation_delta,
                "previous_seed_iterations_median": seed_results["previous_pressure"]["iterations_median"],
                "previous_seed_seconds_median": seed_results["previous_pressure"]["seconds_median"],
                "previous_seed_initial_relative_residual": seed_results["previous_pressure"]["initial_relative_residual"],
                "previous_seed_final_relative_residual": seed_results["previous_pressure"]["final_relative_residual"],
            })

            fixed_point_systems.append({
                "A": A,
                "b": b,
                "direct_pa": direct_pa,
                "direct_psi": direct_psi,
                "working_sat": working_sat.copy(),
                "previous_pressure": previous_pressure.copy(),
                "new_sat": sat_new.copy(),
            })

            accepted_pressure = direct_psi
            accepted_sat = sat_new

            if pressure_delta <= PRESSURE_FIXED_POINT_TOL and saturation_delta <= SATURATION_FIXED_POINT_TOL:
                break

            previous_pressure = direct_psi
            working_sat = sat_new
        else:
            raise GateError("direct_fixed_point_did_not_converge")

        direct_fixed_point_wall = time.perf_counter() - direct_wall_start
        direct_iterations = len(reference_rows)

        stage = "direct_final_consistency"
        mobility_final = a2e.spatial_mobility(accepted_sat, nw, no, krw_max, kro_max)
        txf, tyf, tzf, _ = r3.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility_final["lambda_total"]
        )
        Af, bf, _ = r3.assemble_updated_pressure_system(
            sg3, permeability, txf, tyf, tzf, mobility_final["lambda_total"]
        )
        msf = matrix_structure(Af)
        gate("final_matrix_structural_SPD_candidate", msf["structural_SPD_candidate"], msf)
        final_direct_pa, final_direct_times = timed_spsolve(Af, bf, TIMING_REPEATS)
        final_direct_psi = (final_direct_pa * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
        final_direct_rel = lin_residual(Af, final_direct_pa, bf)
        gate("final_direct_residual", final_direct_rel < PRESSURE_GATE, final_direct_rel)
        final_sg = np.asarray(a2e.invert_local_mass(r2, parent_mass, final_direct_psi, p_ref, pore_volume), dtype=np.float64)
        final_sat = float(a2e.BACKGROUND) + final_sg
        gate("direct_final_pressure_consistency",
             rel_l2(final_direct_psi, accepted_pressure) <= PRESSURE_FIXED_POINT_TOL,
             rel_l2(final_direct_psi, accepted_pressure))
        gate("direct_final_saturation_consistency",
             float(np.max(np.abs(final_sat - accepted_sat))) <= SATURATION_FIXED_POINT_TOL,
             float(np.max(np.abs(final_sat - accepted_sat))))

        Mjf = make_jacobi(Af)
        final_prev_pa = accepted_pressure.reshape(-1) * float(sg3.PSI_TO_PA)
        final_bench = benchmark_seed(Af, bf, final_prev_pa, Mjf, final_direct_pa, "previous_pressure_final_consistency", TIMING_REPEATS)
        gate("final_previous_seed_correction_success", final_bench["success"], final_bench)
        gate("final_previous_seed_pressure_equivalence",
             final_bench["pressure_relative_L2_vs_direct"] <= 1.0e-8,
             final_bench["pressure_relative_L2_vs_direct"])
        benchmark_rows.append({
            "fixed_point_iteration": direct_iterations + 1,
            **{k: v for k, v in final_bench.items() if k != "label"},
            "seed_label": "previous_pressure_final_consistency",
            "direct_spsolve_seconds_median": float(np.median(final_direct_times)),
            "direct_relative_residual": final_direct_rel,
            "matrix_symmetry_max_abs": msf["symmetry_max_abs"],
            "matrix_diagonal_min": msf["diagonal_min"],
            "matrix_strictly_anchored_row_count": msf["strictly_anchored_row_count"],
        })

        stage = "iterative_full_fixed_point_replay"
        # Replay the same nonlinear fixed point using exact-corrected CG pressure solves.
        iter_wall_start = time.perf_counter()
        working_sat_i = parent_sat.copy()
        previous_pressure_i = parent_pressure.copy()
        iterative_rows = []
        iterative_pressure = None
        iterative_sat = None
        iterative_solve_seconds_total = 0.0

        for iteration in range(1, MAX_FIXED_POINT_ITERATIONS + 1):
            mobility = a2e.spatial_mobility(working_sat_i, nw, no, krw_max, kro_max)
            tx, ty, tz, _ = r3.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, _ = r3.assemble_updated_pressure_system(
                sg3, permeability, tx, ty, tz, mobility["lambda_total"]
            )
            Mj = make_jacobi(A)
            seed_pa = previous_pressure_i.reshape(-1) * float(sg3.PSI_TO_PA)
            corr = correction_cg(A, b, seed_pa, Mj, CORRECTION_TARGET)
            gate(f"iterative_replay_{iteration:03d}_correction_success", corr["success"], corr)
            iterative_solve_seconds_total += float(corr["seconds"])
            ppsi = (corr["pressure_pa"] * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")

            sg_new = np.asarray(a2e.invert_local_mass(r2, parent_mass, ppsi, p_ref, pore_volume), dtype=np.float64)
            sat_new = float(a2e.BACKGROUND) + sg_new
            pd = rel_l2(ppsi, previous_pressure_i)
            sd = float(np.max(np.abs(sat_new - working_sat_i)))

            iterative_rows.append({
                "fixed_point_iteration": iteration,
                "iterations": corr["iterations"],
                "seconds": corr["seconds"],
                "initial_relative_residual": corr["initial_relative_residual"],
                "final_relative_residual": corr["final_relative_residual"],
                "pressure_relative_L2_change": pd,
                "saturation_Linf_change": sd,
            })

            iterative_pressure = ppsi
            iterative_sat = sat_new

            if pd <= PRESSURE_FIXED_POINT_TOL and sd <= SATURATION_FIXED_POINT_TOL:
                break

            previous_pressure_i = ppsi
            working_sat_i = sat_new
        else:
            raise GateError("iterative_fixed_point_did_not_converge")

        iterative_fixed_point_wall = time.perf_counter() - iter_wall_start
        iterative_iterations = len(iterative_rows)

        stage = "iterative_final_consistency"
        mobility_i_final = a2e.spatial_mobility(iterative_sat, nw, no, krw_max, kro_max)
        txi, tyi, tzi, _ = r3.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility_i_final["lambda_total"]
        )
        Ai, bi, _ = r3.assemble_updated_pressure_system(
            sg3, permeability, txi, tyi, tzi, mobility_i_final["lambda_total"]
        )
        Mi = make_jacobi(Ai)
        ci = correction_cg(
            Ai, bi,
            iterative_pressure.reshape(-1) * float(sg3.PSI_TO_PA),
            Mi, CORRECTION_TARGET
        )
        gate("iterative_final_consistency_correction_success", ci["success"], ci)
        ip_final = (ci["pressure_pa"] * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
        isg_final = np.asarray(a2e.invert_local_mass(r2, parent_mass, ip_final, p_ref, pore_volume), dtype=np.float64)
        isat_final = float(a2e.BACKGROUND) + isg_final
        gate("iterative_final_pressure_self_consistency",
             rel_l2(ip_final, iterative_pressure) <= PRESSURE_FIXED_POINT_TOL,
             rel_l2(ip_final, iterative_pressure))
        gate("iterative_final_saturation_self_consistency",
             float(np.max(np.abs(isat_final - iterative_sat))) <= SATURATION_FIXED_POINT_TOL,
             float(np.max(np.abs(isat_final - iterative_sat))))

        stage = "trajectory_equivalence"
        final_pressure_rel = rel_l2(ip_final, final_direct_psi)
        final_sat_linf = float(np.max(np.abs(isat_final - final_sat)))
        gate("iterative_vs_direct_final_pressure_equivalent", final_pressure_rel <= 1.0e-8, final_pressure_rel)
        gate("iterative_vs_direct_final_saturation_equivalent", final_sat_linf <= 1.0e-10, final_sat_linf)

        stage = "benchmark_interpretation"
        previous_rows = [r for r in benchmark_rows if r["seed_label"].startswith("previous_pressure")]
        previous_all_success = all(bool(r["success"]) for r in previous_rows)
        previous_iterations = np.asarray([float(r["iterations_median"]) for r in previous_rows], dtype=np.float64)
        previous_seconds = np.asarray([float(r["seconds_median"]) for r in previous_rows], dtype=np.float64)
        direct_seconds = np.asarray([float(r["direct_spsolve_seconds_median"]) for r in previous_rows], dtype=np.float64)

        first = [r for r in benchmark_rows if int(r["fixed_point_iteration"]) == 1]
        first_map = {str(r["seed_label"]): r for r in first}
        seed_sensitivity_observed = False
        if "zero_pressure" in first_map and "previous_pressure" in first_map:
            seed_sensitivity_observed = (
                float(first_map["previous_pressure"]["iterations_median"])
                < float(first_map["zero_pressure"]["iterations_median"])
                or float(first_map["previous_pressure"]["seconds_median"])
                < float(first_map["zero_pressure"]["seconds_median"])
            )

        ideal = first_map.get("ideal_exact_teacher")
        ideal_floor_seconds = float(ideal["seconds_median"]) if ideal else None
        direct_first_seconds = float(first_map["previous_pressure"]["direct_spsolve_seconds_median"]) if "previous_pressure" in first_map else None
        ideal_headroom_ratio = (
            float(direct_first_seconds / max(ideal_floor_seconds, 1.0e-30))
            if ideal_floor_seconds is not None and direct_first_seconds is not None
            else None
        )

        solve_only_speed_ratio = float(
            np.sum(direct_seconds) / max(float(np.sum(previous_seconds)), 1.0e-30)
        )
        full_refresh_speed_ratio = float(
            direct_fixed_point_wall / max(iterative_fixed_point_wall, 1.0e-30)
        )

        iterative_exact_correction_feasible = bool(
            previous_all_success
            and final_pressure_rel <= 1.0e-8
            and final_sat_linf <= 1.0e-10
        )

        # Training design is justified only when exact correction is feasible and
        # there is measurable seed-dependent or ideal-seed headroom. No minimum
        # production speedup target is invented here.
        learned_seed_opportunity_demonstrated = bool(
            iterative_exact_correction_feasible
            and (
                seed_sensitivity_observed
                or (ideal_headroom_ratio is not None and ideal_headroom_ratio > 1.0)
            )
        )

        if iterative_exact_correction_feasible and learned_seed_opportunity_demonstrated:
            classification = (
                "ITERATIVE_EXACT_CORRECTION_FEASIBLE_AND_SEED_DEPENDENT_ACCELERATION_"
                "OPPORTUNITY_DEMONSTRATED_ML_DATASET_MODEL_DESIGN_MAY_PROCEED"
            )
        elif iterative_exact_correction_feasible:
            classification = (
                "ITERATIVE_EXACT_CORRECTION_FEASIBLE_BUT_NO_CLEAR_SEED_ACCELERATION_"
                "OPPORTUNITY_DEMONSTRATED_ML_TRAINING_REMAINS_UNAUTHORIZED"
            )
        else:
            classification = (
                "ITERATIVE_EXACT_CORRECTION_NOT_EQUIVALENT_ON_FROZEN_AV4_TRAJECTORY_"
                "ML_TRAINING_REMAINS_UNAUTHORIZED"
            )

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "AV4_authoritative_physical_day": AV4_DAY,
            "direct_fixed_point_iterations": direct_iterations,
            "iterative_fixed_point_iterations": iterative_iterations,
            "direct_fixed_point_wall_seconds": direct_fixed_point_wall,
            "iterative_fixed_point_wall_seconds": iterative_fixed_point_wall,
            "direct_solve_median_seconds_sum_over_benchmarked_systems": float(np.sum(direct_seconds)),
            "iterative_previous_seed_median_seconds_sum_over_benchmarked_systems": float(np.sum(previous_seconds)),
            "solve_only_direct_over_iterative_speed_ratio": solve_only_speed_ratio,
            "full_fixed_point_direct_over_iterative_speed_ratio": full_refresh_speed_ratio,
            "previous_seed_iterations_median_across_systems": float(np.median(previous_iterations)),
            "previous_seed_iterations_max_across_systems": float(np.max(previous_iterations)),
            "seed_sensitivity_observed": seed_sensitivity_observed,
            "ideal_exact_seed_residual_check_seconds_median_first_system": ideal_floor_seconds,
            "direct_spsolve_seconds_median_first_system": direct_first_seconds,
            "ideal_seed_headroom_ratio_vs_direct_first_system": ideal_headroom_ratio,
            "iterative_exact_correction_feasible": iterative_exact_correction_feasible,
            "learned_seed_opportunity_demonstrated": learned_seed_opportunity_demonstrated,
            "final_pressure_relative_L2_iterative_vs_direct": final_pressure_rel,
            "final_saturation_Linf_iterative_vs_direct": final_sat_linf,
            "pressure_science_gate": PRESSURE_GATE,
            "correction_target_relative_residual": CORRECTION_TARGET,
            "direct_spsolve_reference_preserved": True,
            "model_training_executed": False,
            "learned_inference_executed": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        benchmark_contract = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "solver_architecture": {
                "reference": "scipy.sparse.linalg.spsolve",
                "iterative_candidate": "CG with Jacobi preconditioner",
                "correction_equation": "A*delta_p = b - A*p_hat",
                "corrected_pressure": "p_hat + delta_p",
                "final_acceptance_residual": "||A*p-b||/||b|| < 1e-8",
                "numerical_correction_target": CORRECTION_TARGET,
            },
            "benchmark_policy": {
                "same_A_and_b": True,
                "same_parent_mass_and_EOS_reconciliation": True,
                "same_fixed_point_tolerances": True,
                "direct_reference_repeated": TIMING_REPEATS,
                "iterative_seed_repeated": TIMING_REPEATS,
                "seed_set": [
                    "previous pressure",
                    "parent R30 pressure",
                    "uniform mean parent pressure (first system)",
                    "zero pressure (first system)",
                    "ideal exact teacher residual-check floor (first system)",
                ],
                "no_speedup_threshold_invented": True,
            },
            "interpretation": {
                "iterative_exact_correction_feasible": iterative_exact_correction_feasible,
                "seed_sensitivity_observed": seed_sensitivity_observed,
                "ideal_seed_headroom_ratio_vs_direct": ideal_headroom_ratio,
                "learned_seed_opportunity_demonstrated": learned_seed_opportunity_demonstrated,
            },
        }

        model_design_authorized = bool(learned_seed_opportunity_demonstrated)

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV5_A3_authorized": model_design_authorized,
            "AV5_A3_name": (
                "Teacher Dataset / Split / Pressure-Seed Model / Objective Design Freeze"
                if model_design_authorized else None
            ),
            "AV5_A3_scope": (
                "freeze exact-teacher dataset generation, leakage-safe realization/trajectory split, "
                "pressure-seed model inputs/outputs, objectives, and acceptance protocol; no training"
                if model_design_authorized else None
            ),
            "AV5_A3_execution_authorized": model_design_authorized,
            "AV5_model_training_authorized": False,
            "AV5_learned_inference_authorized": False,
            "AV5_production_execution_authorized": False,
            "direct_spsolve_reference_and_fallback_required": True,
            "exact_FV_correction_required": True,
            "AV4_conservation_gates_unchanged": True,
            "AV4_fixed_point_tolerances_unchanged": True,
            "AV4_authoritative_state_SHA": AV4_STATE_SHA,
            "AV4_state_mutation_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Numerical_Feasibility_Benchmark_Contract.json").write_bytes(jb(benchmark_contract))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Direct_FixedPoint_Reference.csv").write_bytes(csvb(reference_rows))
        (out / f"{OUT_TOKEN}_WarmStart_Benchmark.csv").write_bytes(csvb(benchmark_rows))
        (out / f"{OUT_TOKEN}_Iterative_FixedPoint_Replay.csv").write_bytes(csvb(iterative_rows))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                               :", classification)
        print("AV4 state SHA256                             :", AV4_STATE_SHA)
        print("Direct fixed-point iterations                :", direct_iterations)
        print("Iterative fixed-point iterations             :", iterative_iterations)
        print("Direct full fixed-point wall seconds         :", direct_fixed_point_wall)
        print("Iterative full fixed-point wall seconds      :", iterative_fixed_point_wall)
        print("Full fixed-point direct/iterative speed ratio:", full_refresh_speed_ratio)
        print("Solve-only direct/iterative speed ratio      :", solve_only_speed_ratio)
        print("Previous-seed median Krylov iterations       :", float(np.median(previous_iterations)))
        print("Previous-seed max Krylov iterations          :", float(np.max(previous_iterations)))
        print("Seed sensitivity observed                    :", seed_sensitivity_observed)
        print("Ideal-seed headroom ratio vs direct          :", ideal_headroom_ratio)
        print("Exact-correction feasible                    :", iterative_exact_correction_feasible)
        print("Learned-seed opportunity demonstrated        :", learned_seed_opportunity_demonstrated)
        print("Final pressure relative L2 vs direct         :", final_pressure_rel)
        print("Final saturation Linf vs direct              :", final_sat_linf)
        print("AV5-A3 design authorized                     :", model_design_authorized)
        print("Model training authorized                    : False")
        print("P3 authorized                                : False")
        print("=" * 200)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "AV4_authoritative_state_preserved": True,
                "model_training_executed": False,
                "learned_inference_executed": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
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
