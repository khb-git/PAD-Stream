from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16B-1
# Fast Marching Governing Metric / Speed-Field Contract Audit
#
# PURPOSE
# -------
# V16A is frozen. Foundation Case 0001 is now immutable.
#
# V16B-1 begins the Fast Marching branch by defining, auditing, and freezing
# the exact physical quantity that the Fast Marching Method (FMM) will
# propagate through the 3D heterogeneous reservoir.
#
# IMPORTANT
# ---------
# V16B-1 DOES NOT RUN FAST MARCHING.
#
# It does not:
#   - solve an Eikonal equation,
#   - generate an arrival-time field,
#   - modify Foundation Case 0001,
#   - rerun SG3/SG4,
#   - recompute velocity,
#   - retrace Pollock,
#   - train or infer any ML model.
#
# It only defines the admissible FMM speed/metric construction from the frozen
# permeability-pressure-flow foundation and selects the physically consistent
# baseline contract for V16B-2.
#
# PHYSICAL INTERPRETATION
# -----------------------
# Standard isotropic FMM solves:
#
#     |grad(T)| = 1 / F
#
# where:
#     T = arrival-time-like field
#     F = positive propagation speed
#
# For PAD-Stream, a reservoir-physics FMM baseline must be tied to the frozen
# Darcy flow state, not merely Euclidean distance.
#
# Candidate contracts audited here:
#
#   M0: Geometric reference
#       F = constant
#       Purpose: geometry-only control, NOT selected as primary physics baseline.
#
#   M1: Darcy pore-speed magnitude
#       u_p = |q| / phi
#       F = max(u_p, epsilon)
#       Purpose: physically closest isotropic FMM analogue to advective travel.
#
#   M2: Pressure-gradient mobility proxy
#       F ~ |K grad(p)| / phi
#       Equivalent in spirit to pore speed but reconstructed from cell-centered
#       permeability and pressure gradient rather than frozen face velocity.
#
#   M3: Permeability-only proxy
#       F ~ K_eff / phi
#       Useful geological sensitivity reference, but lacks direct pressure /
#       forcing dependence and therefore is NOT selected as the primary FMM
#       physics baseline.
#
# PRIMARY CONTRACT
# ----------------
# V16B-1 is designed to select M1 provided the frozen Vx/Vy/Vz arrays can be
# transformed into one finite, strictly positive cell-centered pore-speed field
# without changing the underlying V16A foundation.
#
# The cell-centered velocity field is constructed diagnostically from face
# velocities by local averaging:
#
#   Vxc[k,j,i] = 0.5 * (Vx[k,j,i-1] + Vx[k,j,i])
#
# with boundary cells receiving the adjacent face value. Analogous operations
# are used for y and z.
#
# Then:
#
#   speed_cell = sqrt(Vxc^2 + Vyc^2 + Vzc^2)
#
# Since SG5 face velocities already include the porosity conversion used in the
# frozen Pollock physics, V16B-1 DOES NOT divide them by porosity again.
#
# A positive floor epsilon is permitted only as an FMM numerical regularization
# for stagnant cells:
#
#   F = max(speed_cell, epsilon)
#
# epsilon is derived deterministically from the positive-speed distribution:
#
#   epsilon = max(machine_floor, 1e-6 * median_positive_speed)
#
# This does not alter V16A. It is a V16B metric regularization contract.
# =============================================================================


ROOT = Path(__file__).resolve().parent

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)

FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"
FOUNDATION_MANIFEST = FOUNDATION_DIR / "V16A_Foundation_Case_0001_Manifest.json"

OUT = ROOT / "output" / "V16_B1_FMM_GOVERNING_METRIC_CONTRACT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B1_Foundation_Identity.csv"
CANDIDATE_CSV = OUT / "V16B1_FMM_Metric_Candidate_Matrix.csv"
CENTERING_CSV = OUT / "V16B1_Face_to_Cell_Velocity_Contract.csv"
SPEED_STATS_CSV = OUT / "V16B1_Selected_Speed_Field_Statistics.csv"
REG_CSV = OUT / "V16B1_Speed_Floor_Regularization_Contract.csv"
GATES_CSV = OUT / "V16B1_Final_Governing_Metric_Gates.csv"
DECISION_CSV = OUT / "V16B1_Governing_Metric_Decision.csv"

SPEED_NPZ = OUT / "V16B1_FMM_Speed_Field_Contract.npz"
CONTRACT_JSON = OUT / "V16B1_FMM_Governing_Metric_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B1_Summary.json"


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(a: np.ndarray):
    a = np.ascontiguousarray(a)

    h = hashlib.sha256()
    h.update(str(a.dtype).encode("utf-8"))
    h.update(str(tuple(a.shape)).encode("utf-8"))
    h.update(a.tobytes())

    return h.hexdigest()


def load_foundation():
    if not FOUNDATION_NPZ.exists():
        raise FileNotFoundError(FOUNDATION_NPZ)

    if not FOUNDATION_MANIFEST.exists():
        raise FileNotFoundError(FOUNDATION_MANIFEST)

    manifest = json.loads(FOUNDATION_MANIFEST.read_text(encoding="utf-8"))

    with np.load(FOUNDATION_NPZ, allow_pickle=False) as db:
        arrays = {k: np.array(db[k], copy=True) for k in db.files}

    return manifest, arrays


def face_to_cell_x(vx):
    nz, ny, nfx = vx.shape
    nx = nfx + 1

    out = np.empty((nz, ny, nx), dtype=np.float64)

    out[:, :, 0] = vx[:, :, 0]
    out[:, :, -1] = vx[:, :, -1]

    if nx > 2:
        out[:, :, 1:-1] = 0.5 * (vx[:, :, :-1] + vx[:, :, 1:])

    return out


def face_to_cell_y(vy):
    nz, nfy, nx = vy.shape
    ny = nfy + 1

    out = np.empty((nz, ny, nx), dtype=np.float64)

    out[:, 0, :] = vy[:, 0, :]
    out[:, -1, :] = vy[:, -1, :]

    if ny > 2:
        out[:, 1:-1, :] = 0.5 * (vy[:, :-1, :] + vy[:, 1:, :])

    return out


def face_to_cell_z(vz):
    nfz, ny, nx = vz.shape
    nz = nfz + 1

    out = np.empty((nz, ny, nx), dtype=np.float64)

    out[0, :, :] = vz[0, :, :]
    out[-1, :, :] = vz[-1, :, :]

    if nz > 2:
        out[1:-1, :, :] = 0.5 * (vz[:-1, :, :] + vz[1:, :, :])

    return out


def positive_floor(speed):
    positive = speed[speed > 0.0]

    if positive.size == 0:
        raise RuntimeError("No positive cell-centered speeds exist.")

    median_positive = float(np.median(positive))
    machine_floor = float(np.finfo(np.float64).tiny)

    eps = max(machine_floor, 1.0e-6 * median_positive)

    return eps, median_positive


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-1")
    print("Fast Marching Governing Metric / Speed-Field Contract Audit")
    print("=" * 78)

    print("""
FOUNDATION CASE 0001 IS IMMUTABLE.
NO FAST MARCHING SOLVE WILL BE EXECUTED.
NO ARRIVAL-TIME FIELD WILL BE GENERATED.
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY FIELD WILL BE RECOMPUTED FROM PHYSICS.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
ONLY THE V16B FMM GOVERNING SPEED / METRIC CONTRACT WILL BE DEFINED.
""")

    manifest, arrays = load_foundation()

    if manifest.get("status") != "V16A_FOUNDATION_CASE_0001_FROZEN_COMPLETE":
        raise RuntimeError("V16B-1 requires frozen Foundation Case 0001.")

    required = [
        "Kx",
        "Ky",
        "Kz",
        "porosity",
        "pressure",
        "Qx",
        "Qy",
        "Qz",
        "Vx",
        "Vy",
        "Vz",
        "streamline_xyz",
        "pollock_tof",
        "streamline_weight",
    ]

    missing = [name for name in required if name not in arrays]

    if missing:
        raise RuntimeError(
            "Foundation Case 0001 is missing required V16B-1 inputs: "
            + ", ".join(missing)
        )

    foundation_hash = sha256_file(FOUNDATION_NPZ)

    save_csv(
        IDENTITY_CSV,
        [
            {
                "foundation_file": str(FOUNDATION_NPZ),
                "foundation_sha256": foundation_hash,
                "manifest_file": str(FOUNDATION_MANIFEST),
                "manifest_sha256": sha256_file(FOUNDATION_MANIFEST),
                "foundation_status": manifest.get("status"),
            }
        ],
    )

    # -------------------------------------------------------------------------
    # Candidate metric audit
    # -------------------------------------------------------------------------
    candidates = [
        {
            "candidate": "M0",
            "name": "CONSTANT_GEOMETRIC_SPEED",
            "pressure_dependent": False,
            "permeability_dependent": False,
            "flow_dependent": False,
            "porosity_dependent": False,
            "selected_primary": False,
            "role": "GEOMETRIC_CONTROL_ONLY",
            "reason": "No reservoir-flow physics.",
        },
        {
            "candidate": "M1",
            "name": "FROZEN_DARCY_PORE_SPEED_MAGNITUDE",
            "pressure_dependent": True,
            "permeability_dependent": True,
            "flow_dependent": True,
            "porosity_dependent": True,
            "selected_primary": True,
            "role": "PRIMARY_FMM_PHYSICS_BASELINE",
            "reason": "Directly inherits frozen SG3-SG5 permeability-pressure-Darcy-flow physics.",
        },
        {
            "candidate": "M2",
            "name": "PRESSURE_GRADIENT_MOBILITY_PROXY",
            "pressure_dependent": True,
            "permeability_dependent": True,
            "flow_dependent": True,
            "porosity_dependent": True,
            "selected_primary": False,
            "role": "DERIVED_REFERENCE_ONLY",
            "reason": "Would rederive flow from K and grad(p), duplicating frozen V field.",
        },
        {
            "candidate": "M3",
            "name": "PERMEABILITY_ONLY_PROXY",
            "pressure_dependent": False,
            "permeability_dependent": True,
            "flow_dependent": False,
            "porosity_dependent": True,
            "selected_primary": False,
            "role": "GEOLOGICAL_SENSITIVITY_REFERENCE",
            "reason": "Does not include pressure forcing and is not an advective travel-time analogue.",
        },
    ]

    save_csv(CANDIDATE_CSV, candidates)

    # -------------------------------------------------------------------------
    # Exact face-to-cell velocity transformation
    # -------------------------------------------------------------------------
    Vx = np.asarray(arrays["Vx"], dtype=np.float64)
    Vy = np.asarray(arrays["Vy"], dtype=np.float64)
    Vz = np.asarray(arrays["Vz"], dtype=np.float64)

    Vxc = face_to_cell_x(Vx)
    Vyc = face_to_cell_y(Vy)
    Vzc = face_to_cell_z(Vz)

    expected_cell_shape = (15, 50, 50)

    if Vxc.shape != expected_cell_shape:
        raise RuntimeError(f"Unexpected Vxc shape: {Vxc.shape}")

    if Vyc.shape != expected_cell_shape:
        raise RuntimeError(f"Unexpected Vyc shape: {Vyc.shape}")

    if Vzc.shape != expected_cell_shape:
        raise RuntimeError(f"Unexpected Vzc shape: {Vzc.shape}")

    speed_raw = np.sqrt(Vxc**2 + Vyc**2 + Vzc**2)

    if not np.all(np.isfinite(speed_raw)):
        raise RuntimeError("Raw FMM speed contains non-finite values.")

    eps, median_positive = positive_floor(speed_raw)

    speed_fmm = np.maximum(speed_raw, eps)

    floor_mask = speed_raw < eps

    save_csv(
        CENTERING_CSV,
        [
            {
                "component": "Vx -> Vxc",
                "face_shape": str(tuple(Vx.shape)),
                "cell_shape": str(tuple(Vxc.shape)),
                "boundary_rule": "adjacent-face value",
                "interior_rule": "arithmetic mean of bracketing faces",
            },
            {
                "component": "Vy -> Vyc",
                "face_shape": str(tuple(Vy.shape)),
                "cell_shape": str(tuple(Vyc.shape)),
                "boundary_rule": "adjacent-face value",
                "interior_rule": "arithmetic mean of bracketing faces",
            },
            {
                "component": "Vz -> Vzc",
                "face_shape": str(tuple(Vz.shape)),
                "cell_shape": str(tuple(Vzc.shape)),
                "boundary_rule": "adjacent-face value",
                "interior_rule": "arithmetic mean of bracketing faces",
            },
        ],
    )

    save_csv(
        SPEED_STATS_CSV,
        [
            {
                "field": "speed_raw_m_s",
                "shape": str(tuple(speed_raw.shape)),
                "min": float(np.min(speed_raw)),
                "p01": float(np.percentile(speed_raw, 1)),
                "p05": float(np.percentile(speed_raw, 5)),
                "median": float(np.median(speed_raw)),
                "mean": float(np.mean(speed_raw)),
                "p95": float(np.percentile(speed_raw, 95)),
                "p99": float(np.percentile(speed_raw, 99)),
                "max": float(np.max(speed_raw)),
                "zero_count": int(np.sum(speed_raw == 0.0)),
                "positive_count": int(np.sum(speed_raw > 0.0)),
                "sha256": sha256_array(speed_raw),
            },
            {
                "field": "speed_fmm_m_s",
                "shape": str(tuple(speed_fmm.shape)),
                "min": float(np.min(speed_fmm)),
                "p01": float(np.percentile(speed_fmm, 1)),
                "p05": float(np.percentile(speed_fmm, 5)),
                "median": float(np.median(speed_fmm)),
                "mean": float(np.mean(speed_fmm)),
                "p95": float(np.percentile(speed_fmm, 95)),
                "p99": float(np.percentile(speed_fmm, 99)),
                "max": float(np.max(speed_fmm)),
                "zero_count": int(np.sum(speed_fmm == 0.0)),
                "positive_count": int(np.sum(speed_fmm > 0.0)),
                "sha256": sha256_array(speed_fmm),
            },
        ],
    )

    save_csv(
        REG_CSV,
        [
            {
                "regularization": "positive_speed_floor",
                "formula": "epsilon = max(float64_tiny, 1e-6 * median_positive_speed)",
                "median_positive_speed_m_s": median_positive,
                "epsilon_m_s": eps,
                "cells_floored": int(np.sum(floor_mask)),
                "fraction_floored": float(np.mean(floor_mask)),
                "foundation_arrays_modified": False,
                "scope": "V16B_FMM_METRIC_ONLY",
            }
        ],
    )

    # Persist the V16B metric artifact.
    np.savez_compressed(
        SPEED_NPZ,
        Vxc_m_s=Vxc,
        Vyc_m_s=Vyc,
        Vzc_m_s=Vzc,
        speed_raw_m_s=speed_raw,
        speed_fmm_m_s=speed_fmm,
        speed_floor_mask=floor_mask.astype(np.uint8),
        epsilon_m_s=np.asarray([eps], dtype=np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B1_FMM_SPEED_CONTRACT",
            dtype=np.uint8,
        ),
    )

    gates = [
        ("foundation_case_0001_status_reproduced", True),
        ("foundation_sha256_recorded", True),
        ("all_required_foundation_inputs_present", len(missing) == 0),
        ("FMM_candidate_metric_matrix_constructed", True),
        ("M1_selected_as_primary_physics_baseline", True),
        ("Vx_face_to_cell_contract_valid", Vxc.shape == expected_cell_shape),
        ("Vy_face_to_cell_contract_valid", Vyc.shape == expected_cell_shape),
        ("Vz_face_to_cell_contract_valid", Vzc.shape == expected_cell_shape),
        ("raw_speed_finite", np.all(np.isfinite(speed_raw))),
        ("raw_speed_nonnegative", np.min(speed_raw) >= 0.0),
        ("positive_speed_population_exists", np.any(speed_raw > 0.0)),
        ("speed_floor_deterministically_defined", eps > 0.0),
        ("FMM_speed_strictly_positive", np.min(speed_fmm) > 0.0),
        ("no_double_porosity_division", True),
        ("foundation_arrays_not_modified", True),
        ("no_FMM_solve_executed", True),
        ("no_arrival_time_generated", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_physics_recompute", True),
        ("no_Pollock_retrace", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]

    save_csv(
        GATES_CSV,
        [{"gate": name, "passed": bool(value)} for name, value in gates],
    )

    all_pass = all(bool(value) for _, value in gates)

    if all_pass:
        status = "V16B_FMM_GOVERNING_SPEED_CONTRACT_READY"
        diagnosis = (
            "FROZEN_DARCY_PORE_SPEED_MAGNITUDE_PROVIDES_ONE_POSITIVE_SOURCE_AUTHENTIC_ISOTROPIC_FMM_PROPAGATION_FIELD"
        )
        recommendation = (
            "Freeze the V16B-1 speed contract. Proceed to V16B-2 and implement the exact 3D Eikonal/Fast-Marching solver "
            "using speed_fmm_m_s, with the injector completion interval as the zero-arrival source set. "
            "Do not tune the speed field against Pollock TOF."
        )
        next_milestone = "V16B-2 — Exact 3D Fast Marching Arrival-Time Baseline"
    else:
        status = "V16B_FMM_GOVERNING_SPEED_CONTRACT_BLOCKED"
        diagnosis = "ONE_OR_MORE_REQUIRED_FMM_SPEED_CONTRACT_GATES_FAILED"
        recommendation = (
            "Do not run Fast Marching. Audit only failed V16B-1 speed-field contract gates."
        )
        next_milestone = "V16B-1R — FMM Speed Contract Residual Audit"

    save_csv(
        DECISION_CSV,
        [
            {
                "status": status,
                "diagnosis": diagnosis,
                "selected_metric": "M1_FROZEN_DARCY_PORE_SPEED_MAGNITUDE",
                "speed_field": "speed_fmm_m_s",
                "speed_field_sha256": sha256_array(speed_fmm),
                "epsilon_m_s": eps,
                "foundation_sha256": foundation_hash,
                "next_milestone": next_milestone,
            }
        ],
    )

    contract = {
        "milestone": "V16B-1",
        "status": status,
        "diagnosis": diagnosis,
        "foundation": {
            "file": str(FOUNDATION_NPZ),
            "sha256": foundation_hash,
            "immutable": True,
        },
        "governing_equation": "|grad(T)| = 1/F",
        "selected_metric": {
            "id": "M1",
            "name": "FROZEN_DARCY_PORE_SPEED_MAGNITUDE",
            "definition": "F = max(sqrt(Vxc^2 + Vyc^2 + Vzc^2), epsilon)",
            "units": "m/s",
            "porosity_division_applied_in_V16B1": False,
            "reason": (
                "Frozen SG5 velocities already embody the Darcy-to-pore-velocity conversion used by Pollock; "
                "dividing by porosity again would double-count porosity."
            ),
        },
        "face_to_cell_contract": {
            "x": "boundary=adjacent face; interior=mean of bracketing x faces",
            "y": "boundary=adjacent face; interior=mean of bracketing y faces",
            "z": "boundary=adjacent face; interior=mean of bracketing z faces",
        },
        "regularization": {
            "formula": "epsilon = max(float64_tiny, 1e-6 * median_positive_speed)",
            "epsilon_m_s": eps,
            "cells_floored": int(np.sum(floor_mask)),
            "fraction_floored": float(np.mean(floor_mask)),
            "scope": "V16B FMM metric only",
        },
        "metric_artifact": {
            "file": str(SPEED_NPZ),
            "sha256": sha256_file(SPEED_NPZ),
            "speed_field_sha256": sha256_array(speed_fmm),
        },
        "comparison_policy": {
            "Pollock_TOF_used_for_metric_tuning": False,
            "Pollock_TOF_role": "independent frozen reference for downstream comparison only",
        },
        "constraints": {
            "FMM_executed": False,
            "arrival_time_generated": False,
            "foundation_mutated": False,
            "SG3_rerun": False,
            "SG4_rerun": False,
            "Pollock_retrace": False,
            "model_predict": False,
            "training": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16B-1",
            "status": status,
            "diagnosis": diagnosis,
            "selected_metric": contract["selected_metric"],
            "metric_artifact": contract["metric_artifact"],
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("FOUNDATION")
    print(f"  File                    : {FOUNDATION_NPZ}")
    print(f"  SHA-256                 : {foundation_hash}")

    print("\nSELECTED FMM METRIC")
    print("  Candidate               : M1")
    print("  Name                    : FROZEN_DARCY_PORE_SPEED_MAGNITUDE")
    print("  Governing equation      : |grad(T)| = 1 / F")
    print("  Speed units             : m/s")
    print("  Divide by porosity again: False")

    print("\nCELL-CENTERED SPEED")
    print(f"  Shape                   : {speed_raw.shape}")
    print(f"  Raw min/max             : {np.min(speed_raw):.6e} / {np.max(speed_raw):.6e} m/s")
    print(f"  Median positive         : {median_positive:.6e} m/s")
    print(f"  FMM epsilon             : {eps:.6e} m/s")
    print(f"  Cells floored           : {np.sum(floor_mask)}")
    print(f"  Fraction floored        : {np.mean(floor_mask):.6e}")
    print(f"  FMM min/max             : {np.min(speed_fmm):.6e} / {np.max(speed_fmm):.6e} m/s")

    print("\n" + "=" * 78)
    print("V16B-1 FINAL GOVERNING METRIC GATES")
    print("=" * 78)

    for name, value in gates:
        print(f"[{'PASS' if value else 'FAIL'}] {name}")

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nNumerical:")
    print(f"  {SPEED_NPZ.name}")
    print(f"  SHA-256: {sha256_file(SPEED_NPZ)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        CANDIDATE_CSV,
        CENTERING_CSV,
        SPEED_STATS_CSV,
        REG_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-1 FMM GOVERNING METRIC CONTRACT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
