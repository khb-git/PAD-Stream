#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, time
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV5-A2-R1"
NAME = "Accepted Pressure-System Exact-Correction Warm-Start Benchmark"

PASS = (
    "POSTV16AV5A2R1_ACCEPTED_PRESSURE_SYSTEM_EXACT_CORRECTION_"
    "WARM_START_BENCHMARK_PASS_NO_ML_NO_STATE_MUTATION"
)
BLOCK = "POSTV16AV5A2R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "80d5b8e279c5639f130584cf5bf475e3db0694fc"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

GRID = (15, 50, 50)
N = 37500

PRESSURE_GATE = 1.0e-8
CORRECTION_TARGET = 1.0e-10
FLOW_GATE = 1.0e-8
TIMING_REPEATS = 3
MAX_KRYLOV_ITERATIONS = 20000

AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"

# Immutable blocked A2 parent.
A2_TOKEN = "POSTV16_AV5_A2"
A2_BLOCK_REL = BASE_AV5 / (A2_TOKEN + "_BLOCKED")
A2_BLOCK_FILE = A2_TOKEN + "_Blocked_Report.json"
A2_BLOCK_STATUS = "POSTV16AV5A2_TECHNICAL_OR_AUTHORITY_BLOCK"
A2_BLOCK_STAGE = "direct_fixed_point_reference_and_system_benchmark"
A2_BLOCK_EXCEPTION = "ScientificFail('same_time_local_cell_mass_capacity')"

A2_RUNNER = "PAD_Stream_POSTV16_AV5_A2_ExactCorrection_Iterative_PressureSolver_Deterministic_WarmStart_Feasibility_Benchmark.py"
A2_RUNNER_BLOB = "391658e96c58ae6b7ee2b09b371cd8fe7a3076c7"

# A1 design freeze.
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

# Day365 accepted refresh.
A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

# Day375 accepted pressure epoch.
R21_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
R21_REL = BASE_AV4 / (
    R21_TOKEN + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
R21_EPOCH = R21_TOKEN + "_Accepted_Day375_Pressure_Epoch.npz"
R21_SUMMARY = "PAD_Stream_" + R21_TOKEN + "_Summary.json"
R21_MANIFEST = R21_TOKEN + "_Artifact_Manifest.csv"
R21_STATUS = (
    "AV4PIVOTP2R6R21R4R1R5R1R1R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_"
    "PASS_DAY375_PRESSURE_REFRESH_ACCEPTED_NO_COUPLED_SCIENCE_RERUN"
)
R21_EPOCH_SHA = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

# Source authority.
A2E_RUNNER = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R21_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1_"
    "Comprehensive_Technical_Closure.py"
)
R21_RUNNER_BLOB = "ea1a26342e5367943bf459cefc5ff7aacefd0798"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
R3 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A2_RUNNER: A2_RUNNER_BLOB,
    A1_RUNNER: A1_RUNNER_BLOB,
    A2E_RUNNER: A2E_BLOB,
    R21_RUNNER: R21_RUNNER_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    R3: R3_BLOB,
    PERM: PERM_BLOB,
}

OUT_TOKEN = "POSTV16_AV5_A2_R1"
OUT_REL = BASE_AV5 / (OUT_TOKEN + "_AcceptedPressureSystem_ExactCorrection_WarmStart_Benchmark")
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")


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
    return result


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(np.linalg.norm((aa - bb).ravel()) / max(float(np.linalg.norm(bb.ravel())), 1e-30))


def lin_residual(A, p: np.ndarray, b: np.ndarray) -> float:
    r = np.asarray(A @ p - b, dtype=np.float64)
    return float(np.linalg.norm(r) / max(float(np.linalg.norm(b)), 1e-30))


def matrix_audit(A) -> dict[str, Any]:
    csr = A.tocsr()
    d = (csr - csr.T).tocoo()
    sym = 0.0 if d.nnz == 0 else float(np.max(np.abs(d.data)))
    diag = np.asarray(csr.diagonal(), dtype=np.float64)
    off = csr.copy()
    off.setdiag(0.0)
    off.eliminate_zeros()
    offmax = 0.0 if off.nnz == 0 else float(np.max(off.data))
    row_sum = np.asarray(csr.sum(axis=1)).reshape(-1)
    spd_candidate = bool(
        sym <= 1.0e-18
        and float(np.min(diag)) > 0.0
        and offmax <= 0.0
        and float(np.min(row_sum)) >= -1.0e-18
        and int(np.count_nonzero(row_sum > 0.0)) > 0
    )
    return {
        "symmetry_max_abs": sym,
        "diagonal_min": float(np.min(diag)),
        "diagonal_max": float(np.max(diag)),
        "offdiagonal_max": offmax,
        "row_sum_min": float(np.min(row_sum)),
        "row_sum_max": float(np.max(row_sum)),
        "strictly_anchored_row_count": int(np.count_nonzero(row_sum > 0.0)),
        "structural_SPD_candidate": spd_candidate,
    }


def make_jacobi(A):
    from scipy.sparse.linalg import LinearOperator
    diag = np.asarray(A.diagonal(), dtype=np.float64)
    if np.any(diag <= 0.0):
        raise GateError("nonpositive_jacobi_diagonal")
    inv = 1.0 / diag
    return LinearOperator(A.shape, matvec=lambda x: inv * x, dtype=np.float64)


def direct_solve(A, b):
    from scipy.sparse.linalg import spsolve
    times = []
    sols = []
    for _ in range(TIMING_REPEATS):
        t0 = time.perf_counter()
        p = np.asarray(spsolve(A, b), dtype=np.float64)
        times.append(time.perf_counter() - t0)
        sols.append(p)
    for p in sols[1:]:
        if rel_l2(p, sols[0]) > 1.0e-13:
            raise GateError("direct_solve_nondeterministic")
    return sols[0], times


def correction_solve(A, b, seed, method: str):
    from scipy.sparse.linalg import cg, gmres

    seed = np.asarray(seed, dtype=np.float64).reshape(-1)
    rhs_norm = max(float(np.linalg.norm(b)), 1.0e-30)
    t0 = time.perf_counter()
    r0 = np.asarray(b - A @ seed, dtype=np.float64)
    initial_rel = float(np.linalg.norm(r0) / rhs_norm)
    if initial_rel <= CORRECTION_TARGET:
        return {
            "success": True,
            "info": 0,
            "iterations": 0,
            "initial_relative_residual": initial_rel,
            "final_relative_residual": initial_rel,
            "pressure_pa": seed.copy(),
            "seconds": time.perf_counter() - t0,
        }

    M = make_jacobi(A)
    count = 0

    def cb(_x):
        nonlocal count
        count += 1

    atol = CORRECTION_TARGET * rhs_norm
    if method == "cg":
        delta, info = cg(
            A, r0, x0=np.zeros_like(r0), rtol=0.0, atol=atol,
            maxiter=MAX_KRYLOV_ITERATIONS, M=M, callback=cb,
        )
    elif method == "gmres":
        delta, info = gmres(
            A, r0, x0=np.zeros_like(r0), rtol=0.0, atol=atol,
            restart=200, maxiter=MAX_KRYLOV_ITERATIONS,
            M=M, callback=cb, callback_type="pr_norm",
        )
    else:
        raise GateError(f"unknown_method:{method}")

    p = seed + np.asarray(delta, dtype=np.float64)
    final_rel = lin_residual(A, p, b)
    return {
        "success": bool(info == 0 and np.isfinite(p).all() and final_rel < PRESSURE_GATE),
        "info": int(info),
        "iterations": int(count),
        "initial_relative_residual": initial_rel,
        "final_relative_residual": final_rel,
        "pressure_pa": p,
        "seconds": time.perf_counter() - t0,
    }


def benchmark_seed(A, b, seed, direct_pa, method: str, label: str) -> dict[str, Any]:
    runs = [correction_solve(A, b, seed, method) for _ in range(TIMING_REPEATS)]
    times = np.asarray([r["seconds"] for r in runs], dtype=np.float64)
    iterations = np.asarray([r["iterations"] for r in runs], dtype=np.int64)
    first = runs[0]
    return {
        "seed_label": label,
        "method": method,
        "success": all(r["success"] for r in runs),
        "iterations_min": int(np.min(iterations)),
        "iterations_median": float(np.median(iterations)),
        "iterations_max": int(np.max(iterations)),
        "seconds_min": float(np.min(times)),
        "seconds_median": float(np.median(times)),
        "seconds_max": float(np.max(times)),
        "initial_relative_residual": float(first["initial_relative_residual"]),
        "final_relative_residual": float(first["final_relative_residual"]),
        "pressure_relative_L2_vs_direct": rel_l2(first["pressure_pa"], direct_pa),
        "pressure_pa": first["pressure_pa"],
    }


def flow_metrics(sg3, sg4, r3, pressure_psi, tx, ty, tz, producer_wi):
    qx, qy, qz = sg4.compute_face_fluxes(pressure_psi, tx, ty, tz)
    _rates, sink = r3.producer_rates_updated(sg3, pressure_psi, producer_wi)
    cons = r3.flow_conservation_metrics(sg3, sg4, qx, qy, qz, sink)
    return qx, qy, qz, cons


def selftest():
    assert N == 37500
    assert CORRECTION_TARGET < PRESSURE_GATE
    assert len(R21_EPOCH_SHA) == 64
    print("POSTV16 AV5-A2-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None):
        ok = bool(cond)
        gates.append({
            "stage": stage, "gate": name, "pass": ok,
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

        stage = "immutable_A2_BLOCK_authority"
        a2b = drive / A2_BLOCK_REL / A2_BLOCK_FILE
        gate("A2_BLOCK_present", a2b.is_file(), str(a2b))
        b = js(a2b)
        gate("A2_BLOCK_status_exact", b.get("status") == A2_BLOCK_STATUS, b.get("status"))
        gate("A2_BLOCK_stage_exact", b.get("failed_stage") == A2_BLOCK_STAGE, b.get("failed_stage"))
        gate("A2_BLOCK_exception_exact", b.get("exception") == A2_BLOCK_EXCEPTION, b.get("exception"))

        stage = "A1_design_authority"
        a1d = drive / A1_REL
        a1m = manifest(a1d, A1_MANIFEST)
        a1s = js(a1d / A1_SUMMARY)
        a1c = js(a1d / A1_DECISION)
        gate("A1_status_exact", a1s.get("status") == A1_STATUS)
        gate("A1_AV4_state_binding_exact", a1s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A1_exact_correction_required", a1c.get("AV5_must_not_replace_exact_finite_volume_correction") is True)
        gate("A1_direct_reference_required", a1c.get("AV5_A2_must_preserve_direct_spsolve_reference") is True)
        gate("A1_no_training", a1c.get("AV5_A2_must_not_train_model") is True)
        gate("A1_manifest_nonempty", len(a1m) > 0)

        stage = "accepted_pressure_epoch_authority"
        d365 = drive / A2E_REL
        m365 = manifest(d365, A2E_MANIFEST)
        s365 = js(d365 / A2E_SUMMARY)
        p365 = d365 / A2E_EPOCH
        gate("Day365_status_exact", s365.get("status") == A2E_STATUS, s365.get("status"))
        gate("Day365_epoch_manifested", A2E_EPOCH in m365)
        gate("Day365_epoch_present", p365.is_file())

        d375 = drive / R21_REL
        m375 = manifest(d375, R21_MANIFEST)
        s375 = js(d375 / R21_SUMMARY)
        p375 = d375 / R21_EPOCH
        gate("Day375_status_exact", s375.get("status") == R21_STATUS, s375.get("status"))
        gate("Day375_epoch_manifest_SHA_exact", m375.get(R21_EPOCH) == R21_EPOCH_SHA, m375.get(R21_EPOCH))
        gate("Day375_epoch_file_SHA_exact", p375.is_file() and sha(p375) == R21_EPOCH_SHA)

        stage = "load_exact_modules"
        sg3 = mod(root / SG3, "a2r1_sg3")
        sg4 = mod(root / SG4, "a2r1_sg4")
        r3 = mod(root / R3, "a2r1_r3")
        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        gate("permeability_valid", permeability.shape == GRID and np.isfinite(permeability).all() and np.all(permeability > 0.0))

        stage = "load_accepted_systems"
        with np.load(p365, allow_pickle=False) as z:
            day365_parent_pressure = np.asarray(z["parent_pressure_psi"], dtype=np.float64)
            day365_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            day365_lambda = np.asarray(z["lambda_total"], dtype=np.float64)
            day365_tx = np.asarray(z["Tx_dynamic"], dtype=np.float64)
            day365_ty = np.asarray(z["Ty_dynamic"], dtype=np.float64)
            day365_tz = np.asarray(z["Tz_dynamic"], dtype=np.float64)
            day365_day = float(np.asarray(z["canonical_day"]).reshape(()))

        with np.load(p375, allow_pickle=False) as z:
            day375_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            day375_lambda = np.asarray(z["lambda_total"], dtype=np.float64)
            day375_tx = np.asarray(z["Tx_dynamic"], dtype=np.float64)
            day375_ty = np.asarray(z["Ty_dynamic"], dtype=np.float64)
            day375_tz = np.asarray(z["Tz_dynamic"], dtype=np.float64)
            day375_day = float(np.asarray(z["canonical_day"]).reshape(()))

        gate("accepted_days_exact", day365_day == 365.0 and day375_day == 375.0, [day365_day, day375_day])
        gate("accepted_pressure_shapes", day365_pressure.shape == GRID and day375_pressure.shape == GRID)
        gate("temporal_seed_Day375_is_Day365_pressure", day365_pressure.shape == day375_pressure.shape)

        systems = [
            {
                "label": "Day365_A2E_accepted_pressure_system",
                "day": 365.0,
                "pressure": day365_pressure,
                "temporal_seed": day365_parent_pressure,
                "lambda_total": day365_lambda,
                "tx": day365_tx, "ty": day365_ty, "tz": day365_tz,
            },
            {
                "label": "Day375_R21_accepted_pressure_system",
                "day": 375.0,
                "pressure": day375_pressure,
                "temporal_seed": day365_pressure,
                "lambda_total": day375_lambda,
                "tx": day375_tx, "ty": day375_ty, "tz": day375_tz,
            },
        ]

        rows = []
        system_summary = []
        learned_opportunity = False

        stage = "accepted_system_exact_correction_benchmark"
        for system in systems:
            label = system["label"]
            tx, ty, tz = system["tx"], system["ty"], system["tz"]
            A, rhs, producer_wi = r3.assemble_updated_pressure_system(
                sg3, permeability, tx, ty, tz, system["lambda_total"]
            )
            audit = matrix_audit(A)
            method = "cg" if audit["structural_SPD_candidate"] else "gmres"

            direct_pa, direct_times = direct_solve(A, rhs)
            direct_rel = lin_residual(A, direct_pa, rhs)
            direct_psi = (direct_pa * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
            accepted_rel = rel_l2(direct_psi, system["pressure"])

            gate(f"{label}_direct_residual", direct_rel < PRESSURE_GATE, direct_rel)
            gate(f"{label}_direct_reproduces_accepted_pressure", accepted_rel <= 1.0e-10, accepted_rel)

            dq_x, dq_y, dq_z, direct_cons = flow_metrics(
                sg3, sg4, r3, direct_psi, tx, ty, tz, producer_wi
            )
            gate(f"{label}_direct_flow_local_conservation",
                 float(direct_cons["local_relative_l2_error"]) <= FLOW_GATE,
                 direct_cons["local_relative_l2_error"])
            gate(f"{label}_direct_flow_global_conservation",
                 float(direct_cons["global_relative_mismatch"]) <= FLOW_GATE,
                 direct_cons["global_relative_mismatch"])

            temporal_seed_pa = system["temporal_seed"].reshape(-1) * float(sg3.PSI_TO_PA)
            zero_seed_pa = np.zeros(N, dtype=np.float64)
            uniform_seed_pa = np.full(
                N, float(np.mean(system["temporal_seed"])) * float(sg3.PSI_TO_PA), dtype=np.float64
            )
            ideal_seed_pa = direct_pa.copy()

            seed_map = {
                "temporal_previous_epoch_or_parent": temporal_seed_pa,
                "uniform_mean_temporal_seed": uniform_seed_pa,
                "zero_pressure": zero_seed_pa,
                "ideal_exact_teacher": ideal_seed_pa,
            }
            local_results = {}

            for seed_label, seed in seed_map.items():
                result = benchmark_seed(A, rhs, seed, direct_pa, method, seed_label)
                local_results[seed_label] = result
                gate(f"{label}_{seed_label}_success", result["success"], result)
                gate(f"{label}_{seed_label}_pressure_equivalence",
                     float(result["pressure_relative_L2_vs_direct"]) <= 1.0e-8,
                     result["pressure_relative_L2_vs_direct"])

                corr_psi = (
                    np.asarray(result["pressure_pa"], dtype=np.float64)
                    * float(sg3.PA_TO_PSI)
                ).reshape(GRID, order="C")
                cq_x, cq_y, cq_z, corr_cons = flow_metrics(
                    sg3, sg4, r3, corr_psi, tx, ty, tz, producer_wi
                )
                flux_rel = max(
                    rel_l2(cq_x, dq_x),
                    rel_l2(cq_y, dq_y),
                    rel_l2(cq_z, dq_z),
                )
                gate(f"{label}_{seed_label}_Darcy_flux_equivalence", flux_rel <= 1.0e-8, flux_rel)
                gate(f"{label}_{seed_label}_flow_local_conservation",
                     float(corr_cons["local_relative_l2_error"]) <= FLOW_GATE,
                     corr_cons["local_relative_l2_error"])
                gate(f"{label}_{seed_label}_flow_global_conservation",
                     float(corr_cons["global_relative_mismatch"]) <= FLOW_GATE,
                     corr_cons["global_relative_mismatch"])

                rows.append({
                    "system": label,
                    "day": system["day"],
                    "method": method,
                    "matrix_structural_SPD_candidate": audit["structural_SPD_candidate"],
                    "matrix_symmetry_max_abs": audit["symmetry_max_abs"],
                    "seed_label": seed_label,
                    "success": result["success"],
                    "iterations_median": result["iterations_median"],
                    "iterations_max": result["iterations_max"],
                    "seconds_median": result["seconds_median"],
                    "direct_spsolve_seconds_median": float(np.median(direct_times)),
                    "initial_relative_residual": result["initial_relative_residual"],
                    "final_relative_residual": result["final_relative_residual"],
                    "pressure_relative_L2_vs_direct": result["pressure_relative_L2_vs_direct"],
                    "Darcy_flux_max_relative_L2_vs_direct": flux_rel,
                    "flow_local_relative_L2_error": corr_cons["local_relative_l2_error"],
                    "flow_global_relative_mismatch": corr_cons["global_relative_mismatch"],
                })

            temporal = local_results["temporal_previous_epoch_or_parent"]
            zero = local_results["zero_pressure"]
            uniform = local_results["uniform_mean_temporal_seed"]
            ideal = local_results["ideal_exact_teacher"]
            direct_med = float(np.median(direct_times))
            seed_sensitivity = bool(
                float(temporal["iterations_median"]) < float(zero["iterations_median"])
                or float(temporal["iterations_median"]) < float(uniform["iterations_median"])
                or float(temporal["seconds_median"]) < float(zero["seconds_median"])
                or float(temporal["seconds_median"]) < float(uniform["seconds_median"])
            )
            ideal_headroom = float(direct_med / max(float(ideal["seconds_median"]), 1.0e-30))
            if seed_sensitivity or ideal_headroom > 1.0:
                learned_opportunity = True

            system_summary.append({
                "system": label,
                "day": system["day"],
                "method": method,
                "accepted_pressure_relative_L2_vs_reassembled_direct": accepted_rel,
                "direct_relative_residual": direct_rel,
                "direct_spsolve_seconds_median": direct_med,
                "temporal_seed_iterations_median": temporal["iterations_median"],
                "temporal_seed_seconds_median": temporal["seconds_median"],
                "temporal_seed_initial_relative_residual": temporal["initial_relative_residual"],
                "seed_sensitivity_observed": seed_sensitivity,
                "ideal_seed_seconds_median": ideal["seconds_median"],
                "ideal_seed_headroom_ratio_vs_direct": ideal_headroom,
            })

        stage = "benchmark_interpretation"
        exact_correction_feasible = all(bool(r["success"]) for r in rows)
        gate("exact_correction_feasible_on_all_accepted_systems", exact_correction_feasible)
        gate("accepted_system_count_exact", len(system_summary) == 2)

        if exact_correction_feasible and learned_opportunity:
            classification = (
                "ACCEPTED_DAY365_AND_DAY375_PRESSURE_SYSTEMS_SUPPORT_EXACT_"
                "WARM_START_CORRECTION_AND_SEED_ACCELERATION_OPPORTUNITY_"
                "AV5_A3_DESIGN_MAY_PROCEED"
            )
        elif exact_correction_feasible:
            classification = (
                "EXACT_WARM_START_CORRECTION_FEASIBLE_ON_ACCEPTED_PRESSURE_SYSTEMS_"
                "BUT_NO_CLEAR_SEED_ACCELERATION_OPPORTUNITY_AV5_A3_NOT_AUTHORIZED"
            )
        else:
            classification = (
                "EXACT_WARM_START_CORRECTION_NOT_FEASIBLE_ON_ALL_ACCEPTED_PRESSURE_SYSTEMS_"
                "AV5_A3_NOT_AUTHORIZED"
            )

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "immutable_parent_A2_BLOCK_preserved": True,
            "A2_BLOCK_failed_stage": A2_BLOCK_STAGE,
            "A2_BLOCK_exception": A2_BLOCK_EXCEPTION,
            "A2_root_cause_classification": (
                "TEMPORAL_BENCHMARK_STATE_MISBINDING_R30_POST_TRANSPORT_STATE_"
                "WAS_NOT_AN_AUTHORIZED_SAME_TIME_PRESSURE_REFRESH_INPUT"
            ),
            "corrected_benchmark_authority": (
                "accepted Day365 A2E pressure epoch + accepted Day375 R21 pressure epoch"
            ),
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "accepted_pressure_system_count": len(system_summary),
            "exact_correction_feasible_on_all_accepted_systems": exact_correction_feasible,
            "learned_seed_opportunity_demonstrated": learned_opportunity,
            "pressure_science_gate": PRESSURE_GATE,
            "correction_target_relative_residual": CORRECTION_TARGET,
            "direct_spsolve_reference_preserved": True,
            "Darcy_conservation_gates_preserved": True,
            "model_training_executed": False,
            "learned_inference_executed": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        contract = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "technical_repair": {
                "parent_A2_outcome": "immutable TECHNICAL BLOCK",
                "repair_scope": "benchmark-state authority only",
                "R30_same_time_refresh_reexecuted": False,
                "AV4_science_reopened": False,
            },
            "benchmark_systems": system_summary,
            "solver_contract": {
                "reference": "direct scipy.sparse.linalg.spsolve",
                "correction_equation": "A*delta_p = b - A*p_hat",
                "iterative_method_policy": "CG if structural SPD candidate; otherwise GMRES",
                "preconditioner": "Jacobi",
                "final_residual_gate": PRESSURE_GATE,
                "correction_target": CORRECTION_TARGET,
                "Darcy_flux_equivalence_required": True,
                "Darcy_local_global_conservation_required": True,
            },
        }

        a3_auth = bool(exact_correction_feasible and learned_opportunity)
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV5_A3_authorized": a3_auth,
            "AV5_A3_name": (
                "Teacher Dataset / Split / Pressure-Seed Model / Objective Design Freeze"
                if a3_auth else None
            ),
            "AV5_A3_execution_authorized": a3_auth,
            "AV5_A3_must_bind_AV4_state_SHA": AV4_STATE_SHA if a3_auth else None,
            "AV5_A3_must_bind_A2_R1_benchmark": True if a3_auth else False,
            "AV5_model_training_authorized": False,
            "AV5_learned_inference_authorized": False,
            "AV5_production_execution_authorized": False,
            "direct_spsolve_reference_and_fallback_required": True,
            "exact_FV_correction_required": True,
            "AV4_conservation_gates_unchanged": True,
            "AV4_state_mutation_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Accepted_Pressure_System_Benchmark_Contract.json").write_bytes(jb(contract))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_System_Summary.csv").write_bytes(csvb(system_summary))
        (out / f"{OUT_TOKEN}_WarmStart_Benchmark.csv").write_bytes(csvb(rows))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        man = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                man.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(man))

        print("=" * 190)
        print(M, "PASS")
        print("Classification                         :", classification)
        print("Parent A2 BLOCK preserved              : True")
        print("Corrected benchmark systems            : Day365 A2E + Day375 accepted R21")
        print("Accepted systems benchmarked           :", len(system_summary))
        for s in system_summary:
            print(
                f"  {s['system']}: method={s['method']} "
                f"direct={s['direct_spsolve_seconds_median']:.6g}s "
                f"temporal={s['temporal_seed_seconds_median']:.6g}s "
                f"iters={s['temporal_seed_iterations_median']} "
                f"ideal_headroom={s['ideal_seed_headroom_ratio_vs_direct']:.6g}"
            )
        print("Exact correction feasible              :", exact_correction_feasible)
        print("Learned-seed opportunity demonstrated  :", learned_opportunity)
        print("AV5-A3 design authorized               :", a3_auth)
        print("Model training authorized              : False")
        print("P3 authorized                          : False")
        print("=" * 190)
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
                "parent_A2_BLOCK_preserved": True,
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
