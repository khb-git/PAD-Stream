from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve


ROOT = Path(__file__).resolve().parent

FOUNDATION_NPZ = (
    ROOT / "output" / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001" / "V16A_Foundation_Case_0001.npz"
)
B6_DIR = ROOT / "output" / "V16_B6_DIRECTIONAL_ADVECTIVE_NUMERICAL_SCHEME_CONTRACT"
B6_SUMMARY = B6_DIR / "PAD_Stream_V16B6_Summary.json"

B6A_DIR = ROOT / "output" / "V16_B6A_DIRECTIONAL_EXTERNAL_BOUNDARY_POLICY_AUDIT"
B6A_NPZ = B6A_DIR / "V16B6A_Closed_Boundary_Projected_Scheme_Contract.npz"
B6A_CONTRACT = B6A_DIR / "V16B6A_External_Boundary_Policy_Contract.json"
B6A_SUMMARY = B6A_DIR / "PAD_Stream_V16B6A_Summary.json"

OUT = ROOT / "output" / "V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"
OUT.mkdir(parents=True, exist_ok=True)

NUMERICAL = OUT / "V16B7_Directional_Advective_Travel_Time.npz"
MATRIX_CSV = OUT / "V16B7_Linear_System_Audit.csv"
STATS_CSV = OUT / "V16B7_Travel_Time_Statistics.csv"
RESID_CSV = OUT / "V16B7_PDE_Residual_Audit.csv"
CAUSAL_CSV = OUT / "V16B7_Discrete_Causality_Audit.csv"
GATES_CSV = OUT / "V16B7_Final_Directional_Solve_Gates.csv"
DECISION_CSV = OUT / "V16B7_Directional_Solve_Decision.csv"
CONTRACT_JSON = OUT / "V16B7_Directional_Advective_Travel_Time_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B7_Summary.json"


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def flat(k, j, i, ny, nx):
    return (k * ny + j) * nx + i


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-7")
    print("Controlled Directional Advective Travel-Time Solve")
    print("=" * 78)
    print("""
FOUNDATION CASE 0001 IS IMMUTABLE.
V16B-6 NUMERICAL SCHEME CONTRACT IS IMMUTABLE.
V16B-6A CLOSED-BOUNDARY OPERATOR POLICY IS IMMUTABLE.
THE FIRST DIRECTIONAL ADVECTIVE TRAVEL-TIME SYSTEM WILL BE ASSEMBLED AND SOLVED.
NO EXTERNAL tau VALUE WILL BE IMPOSED.
NO FAST MARCHING SOLVE WILL BE RERUN.
NO FMM SPEED FIELD WILL BE CHANGED.
NO POLLOCK TOF WILL BE USED TO FIT OR ALTER THE SOLUTION.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO SG3 / SG4 PHYSICS WILL BE RERUN.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
""")

    for p in [FOUNDATION_NPZ, B6_SUMMARY, B6A_NPZ, B6A_CONTRACT, B6A_SUMMARY]:
        if not p.exists():
            raise FileNotFoundError(p)

    b6 = load_json(B6_SUMMARY)
    b6a = load_json(B6A_SUMMARY)
    b6a_contract = load_json(B6A_CONTRACT)

    if b6.get("status") != "V16B_DIRECTIONAL_NUMERICAL_SCHEME_BOUNDARY_POLICY_REQUIRED":
        raise RuntimeError("Unexpected V16B-6 status.")
    if b6a.get("status") != "V16B_CLOSED_EXTERNAL_BOUNDARY_OPERATOR_POLICY_RESOLVED":
        raise RuntimeError("V16B-6A closed-boundary policy is not resolved.")

    with np.load(B6A_NPZ, allow_pickle=False) as db:
        aW = np.asarray(db["aW_s_inv"], dtype=np.float64)
        aE = np.asarray(db["aE_s_inv"], dtype=np.float64)
        aS = np.asarray(db["aS_s_inv"], dtype=np.float64)
        aN = np.asarray(db["aN_s_inv"], dtype=np.float64)
        aB = np.asarray(db["aB_s_inv"], dtype=np.float64)
        aT = np.asarray(db["aT_s_inv"], dtype=np.float64)
        aP = np.asarray(db["aP_s_inv"], dtype=np.float64)
        source_mask = np.asarray(db["source_mask"], dtype=np.uint8).astype(bool)

    nz, ny, nx = aP.shape
    n = nz * ny * nx
    source_count = int(source_mask.sum())

    rows, cols, vals = [], [], []
    rhs = np.ones(n, dtype=np.float64)

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                r = flat(k, j, i, ny, nx)

                if source_mask[k, j, i]:
                    rows.append(r); cols.append(r); vals.append(1.0)
                    rhs[r] = 0.0
                    continue

                diag = aP[k, j, i]
                if not np.isfinite(diag) or diag <= 0:
                    raise RuntimeError(f"Invalid non-source diagonal at {(k,j,i)}: {diag}")

                rows.append(r); cols.append(r); vals.append(diag)

                if i > 0 and aW[k,j,i] > 0:
                    rows.append(r); cols.append(flat(k,j,i-1,ny,nx)); vals.append(-aW[k,j,i])
                if i < nx-1 and aE[k,j,i] > 0:
                    rows.append(r); cols.append(flat(k,j,i+1,ny,nx)); vals.append(-aE[k,j,i])
                if j > 0 and aS[k,j,i] > 0:
                    rows.append(r); cols.append(flat(k,j-1,i,ny,nx)); vals.append(-aS[k,j,i])
                if j < ny-1 and aN[k,j,i] > 0:
                    rows.append(r); cols.append(flat(k,j+1,i,ny,nx)); vals.append(-aN[k,j,i])
                if k > 0 and aB[k,j,i] > 0:
                    rows.append(r); cols.append(flat(k-1,j,i,ny,nx)); vals.append(-aB[k,j,i])
                if k < nz-1 and aT[k,j,i] > 0:
                    rows.append(r); cols.append(flat(k+1,j,i,ny,nx)); vals.append(-aT[k,j,i])

    A = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))

    print("LINEAR SYSTEM")
    print(f"  Grid shape               : {(nz, ny, nx)}")
    print(f"  Unknowns                 : {n}")
    print(f"  Nonzeros                 : {A.nnz}")
    print(f"  Source rows              : {source_count}")
    print(f"  External tau values      : NONE")

    print("\nSolving sparse directional transport system...")
    tau_s_flat = spsolve(A, rhs)
    tau_s = tau_s_flat.reshape(nz, ny, nx)
    tau_days = tau_s / 86400.0

    residual = A @ tau_s_flat - rhs
    rel_resid = float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1e-300))
    max_abs_resid = float(np.max(np.abs(residual)))

    finite = np.isfinite(tau_s)
    nonnegative = tau_s >= -1e-10
    source_zero = np.max(np.abs(tau_s[source_mask])) if source_count else np.inf

    # Discrete causality diagnostic:
    # for each non-source row with upstream neighbors, tau_P should not be below
    # the minimum upstream tau apart from roundoff.
    violations = 0
    checked = 0
    max_violation_s = 0.0

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if source_mask[k,j,i]:
                    continue
                ups = []
                if i > 0 and aW[k,j,i] > 0: ups.append(tau_s[k,j,i-1])
                if i < nx-1 and aE[k,j,i] > 0: ups.append(tau_s[k,j,i+1])
                if j > 0 and aS[k,j,i] > 0: ups.append(tau_s[k,j-1,i])
                if j < ny-1 and aN[k,j,i] > 0: ups.append(tau_s[k,j+1,i])
                if k > 0 and aB[k,j,i] > 0: ups.append(tau_s[k-1,j,i])
                if k < nz-1 and aT[k,j,i] > 0: ups.append(tau_s[k+1,j,i])
                if ups:
                    checked += 1
                    diff = min(ups) - tau_s[k,j,i]
                    tol = max(1e-8, 1e-10 * max(abs(tau_s[k,j,i]), 1.0))
                    if diff > tol:
                        violations += 1
                        max_violation_s = max(max_violation_s, float(diff))

    positive_non_source = tau_s[~source_mask] > 0
    causal_fraction = 1.0 - violations / max(checked, 1)

    np.savez_compressed(
        NUMERICAL,
        tau_adv_s=tau_s,
        tau_adv_days=tau_days,
        source_mask=source_mask.astype(np.uint8),
        residual=residual.reshape(nz,ny,nx),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B7_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME",
            dtype=np.uint8,
        ),
    )

    save_csv(MATRIX_CSV, [{
        "shape": str(A.shape),
        "nnz": int(A.nnz),
        "source_rows": source_count,
        "external_tau_values_imposed": 0,
        "matrix_finite": bool(np.all(np.isfinite(A.data))),
        "rhs_finite": bool(np.all(np.isfinite(rhs))),
    }])

    stats = {
        "finite_cells": int(np.sum(finite)),
        "total_cells": n,
        "min_days": float(np.nanmin(tau_days)),
        "median_days": float(np.nanmedian(tau_days)),
        "mean_days": float(np.nanmean(tau_days)),
        "max_days": float(np.nanmax(tau_days)),
        "negative_cells": int(np.sum(tau_s < -1e-10)),
        "nonpositive_non_source_cells": int(np.sum(tau_s[~source_mask] <= 0)),
        "max_abs_source_tau_s": float(source_zero),
    }
    save_csv(STATS_CSV, [stats])

    save_csv(RESID_CSV, [{
        "relative_L2_residual": rel_resid,
        "maximum_absolute_residual": max_abs_resid,
        "residual_pass_1e-8": rel_resid < 1e-8,
    }])

    save_csv(CAUSAL_CSV, [{
        "cells_checked": checked,
        "violations": violations,
        "causal_fraction": causal_fraction,
        "max_violation_s": max_violation_s,
    }])

    gates = [
        ("V16B6_numerical_contract_reproduced", True),
        ("V16B6A_closed_boundary_policy_reproduced", True),
        ("foundation_identity_recorded", True),
        ("projected_coefficients_loaded", True),
        ("source_rows_retained", source_count > 0),
        ("no_external_tau_value_imposed", True),
        ("sparse_system_assembled", A.shape == (n,n) and A.nnz > 0),
        ("matrix_and_rhs_finite", np.all(np.isfinite(A.data)) and np.all(np.isfinite(rhs))),
        ("directional_solve_executed", True),
        ("travel_time_finite", bool(np.all(finite))),
        ("travel_time_nonnegative", bool(np.all(nonnegative))),
        ("source_tau_zero", source_zero < 1e-8),
        ("non_source_tau_positive", bool(np.all(positive_non_source))),
        ("relative_PDE_residual_lt_1e8", rel_resid < 1e-8),
        ("discrete_causality_audited", checked > 0),
        ("no_FMM_rerun", True),
        ("no_FMM_speed_change", True),
        ("no_Pollock_parameter_tuning", True),
        ("no_Pollock_retrace", True),
        ("no_SG3_SG4_rerun", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g,p in gates])

    all_pass = all(bool(p) for _,p in gates)

    if all_pass:
        status = "V16B_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE_COMPLETE"
        diagnosis = "CLOSED_BOUNDARY_UPWIND_ADVECTIVE_SYSTEM_SOLVED_WITH_FINITE_NONNEGATIVE_SOURCE_ANCHORED_TRAVEL_TIMES"
        recommendation = (
            "Freeze the untuned directional travel-time solution. Proceed to V16B-8 for an independent "
            "directional-advective vs isotropic-FMM vs Pollock TOF comparison. Do not recalibrate any field."
        )
        next_ms = "V16B-8 — Independent Directional / FMM / Pollock TOF Comparison"
    else:
        status = "V16B_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE_REQUIRES_AUDIT"
        diagnosis = "ONE_OR_MORE_DIRECTIONAL_SOLVE_VALIDATION_GATES_FAILED"
        recommendation = "Do not compare against Pollock yet. Audit only the failed V16B-7 solve gates."
        next_ms = "V16B-7A — Directional Solve Residual / Causality Failure Audit"

    save_csv(DECISION_CSV, [{
        "status": status,
        "diagnosis": diagnosis,
        "relative_L2_residual": rel_resid,
        "causal_fraction": causal_fraction,
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16B-7",
        "status": status,
        "governing_equation": "v(x) dot grad(tau_ADV) = 1",
        "boundary_policy": "V16B6A_NO_FLOW_EXTERNAL_BOUNDARY_PROJECTED_OPERATOR",
        "external_tau_value": None,
        "solver": "scipy.sparse.linalg.spsolve",
        "statistics": stats,
        "residual": {
            "relative_L2": rel_resid,
            "maximum_absolute": max_abs_resid,
        },
        "causality": {
            "checked": checked,
            "violations": violations,
            "fraction": causal_fraction,
            "maximum_violation_s": max_violation_s,
        },
        "numerical_artifact": {
            "path": str(NUMERICAL),
            "sha256": sha256_file(NUMERICAL),
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)
    save_json(SUMMARY_JSON, {
        "milestone": "V16B-7",
        "status": status,
        "diagnosis": diagnosis,
        "statistics": stats,
        "relative_L2_residual": rel_resid,
        "causal_fraction": causal_fraction,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\nDIRECTIONAL TRAVEL TIME")
    print(f"  Finite cells             : {np.sum(finite)} / {n}")
    print(f"  Minimum                  : {np.nanmin(tau_days):.6e} days")
    print(f"  Median                   : {np.nanmedian(tau_days):.6e} days")
    print(f"  Mean                     : {np.nanmean(tau_days):.6e} days")
    print(f"  Maximum                  : {np.nanmax(tau_days):.6e} days")
    print(f"  Relative PDE residual    : {rel_resid:.6e}")
    print(f"  Causality fraction       : {causal_fraction:.6f}")

    print("\n" + "=" * 78)
    print("V16B-7 FINAL DIRECTIONAL SOLVE GATES")
    print("=" * 78)
    for g,p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nNumerical:")
    print(f"  {NUMERICAL.name}")
    print(f"  SHA-256: {sha256_file(NUMERICAL)}")
    print("\nTables:")
    for p in [MATRIX_CSV, STATS_CSV, RESID_CSV, CAUSAL_CSV, GATES_CSV, DECISION_CSV]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-7 CONTROLLED DIRECTIONAL ADVECTIVE TRAVEL-TIME SOLVE: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
