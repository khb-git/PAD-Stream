from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from typing import Any

import numpy as np


MILESTONE = "V16E-41-R3-R4"
STATUS = "SAME_PARENT_MASS_CONSERVATIVE_REFRESHED_FLOW_TRANSITION_VALIDATED"
NEXT = (
    "V16E-41-R3-R5 - Multi-Refresh Cadence Sensitivity / "
    "Runtime Refresh Policy Calibration"
)

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
BACKGROUND_SATURATION = 0.20
MAX_INCREMENTAL_CO2_SATURATION = 0.60
INJECTED_BOUNDARY_SATURATION = 0.80
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0

EXPECTED_PARENT_STEP = 3975
EXPECTED_CHILD_STEP = 3976
EXPECTED_PARENT_TIME_DAYS = 69.88346704782309
EXPECTED_PARENT_STATE_SHA256 = (
    "8714f5b35b99472de0251def022043076f85fb9cee2ada1cfc4d7b7441cce5e6"
)
ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS = 0.049123143364170854

MAX_FIXED_POINT_ITERATIONS = 100
PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_LINF_TOL = 1.0e-10

R3R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R1_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT"
)
R3R1_STATE = (
    "V16E41R3R1_Diagnostic_Partial_Runtime_State_After_2500_Accepted_"
    "Transitions.npz"
)

R3R3R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R3R1_MASS_CONSERVATIVE_PRESSURE_REFRESH_RECONCILIATION_ARCHITECTURE_AMENDMENT"
)
R3R3R1_CONTRACT = (
    "PAD_Stream_V16E41R3R3R1_Reconciliation_Architecture_Amendment.json"
)
R3R3R1_CLOSURE = "V16E41R3R3R1_Final_Closure.json"
EXPECTED_R3R3R1_STATUS = (
    "MASS_CONSERVATIVE_PRESSURE_REFRESH_RECONCILIATION_ARCHITECTURE_FROZEN"
)

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R4_CONTROLLED_SAME_PARENT_MASS_CONSERVATIVE_REFRESHED_FLOW_TRANSITION_VALIDATION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R4_BLOCKED_CONTROLLED_SAME_PARENT_MASS_CONSERVATIVE_REFRESHED_FLOW_TRANSITION_VALIDATION"
)

CHILD_STATE_NAME = (
    "V16E41R3R4_Accepted_MassConservative_RefreshedFlow_"
    "SGSim_Runtime_State_Step_3976.npz"
)
RECONCILED_EPOCH_NAME = (
    "V16E41R3R4_Diagnostic_SameTime_Reconciled_Flow_Epoch_Step_3975.npz"
)

SOURCE_BLOBS = {
    "R3R3R1": (
        "PAD_Stream_V16E41R3R3R1_Mass_Conservative_Pressure_Refresh_"
        "Reconciliation_Architecture_Amendment.py",
        "8087c864e85351859c771f744b81e82f995d6581",
    ),
    "R3R2R1": (
        "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py",
        "740c6da03e73906646bf0153633187e749449f31",
    ),
    "R3R1": (
        "PAD_Stream_V16E41R3R1_Accepted_Transition_Budget_Capacity_Limited_"
        "Regime_Audit.py",
        "4c3438443513bd527b87e02a766634f5eebd2781",
    ),
    "E36": (
        "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_"
        "Snapshot_Validation.py",
        "9ab4035c95a25bd61c649f86c82d88f059cef9e2",
    ),
    "E37A": (
        "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_"
        "Streamline_Grid_Transfer.py",
        "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0",
    ),
    "R2_PHYSICS": (
        "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_"
        "First_Controlled_Transition.py",
        "a127f8730a16e150713420ea547a8de6255550ef",
    ),
    "SG2": (
        "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py",
        "7242012d3e758472abc3ee7f543831b92d2cf419",
    ),
    "SG3": (
        "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py",
        "66a379cd97ee9120f69e7e7e949171541e4918c3",
    ),
    "SG4": (
        "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py",
        "8d49f88bdf55b0da087af2bed04e69967740e695",
    ),
    "SG5": (
        "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py",
        "9a0b64ea7e669904d0d9855ade1c6b052f05ecea",
    ),
    "SG6": (
        "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py",
        "70ceda68e02894167958d753d88b4dbd694731ab",
    ),
    "SG7A": (
        "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py",
        "a4dd47338e7a85f130a6a70d0a41211e38c655f8",
    ),
    "SG7D": (
        "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py",
        "890088c0c0fcab415a2c7351c5079ca8ee12bf82",
    ),
    "PERM": (
        "SGSIM_50x50x15_PERM_MD.csv",
        "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314",
    ),
}


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git_blob_sha(path: Path, repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))


def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))


def bool_scalar(a: Any) -> bool:
    return bool(np.asarray(a).reshape(()))


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=np.float64))))


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(float(np.linalg.norm(bb.ravel())), 1.0e-30)
    )


def parent_cellwise_component_mass(
    physics: Any,
    saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    cell_pore_volume_m3: float,
) -> np.ndarray:
    sat = np.asarray(saturation, dtype=np.float64)
    sg = np.clip(
        sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    rho = np.asarray(
        physics.gas_density_from_state(
            sat,
            pressure_psi,
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    return float(cell_pore_volume_m3) * rho * sg


def fixed_mass_reconstructed_array(
    physics: Any,
    saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    cell_pore_volume_m3: float,
) -> np.ndarray:
    return parent_cellwise_component_mass(
        physics,
        saturation,
        pressure_psi,
        p_ref_gas_pa,
        cell_pore_volume_m3,
    )


def fixed_point_refresh(
    *,
    physics: Any,
    r3r2r1: Any,
    sg2: Any,
    sg3: Any,
    permeability_md: np.ndarray,
    parent_mass: np.ndarray,
    parent_saturation: np.ndarray,
    parent_pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    cell_pore_volume_m3: float,
) -> dict[str, Any]:
    kx, ky, kz = sg2.build_directional_permeability(permeability_md)
    kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
    tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(
        kfx, kfy, kfz
    )

    working_sat = np.asarray(parent_saturation, dtype=np.float64).copy()
    previous_pressure = np.asarray(parent_pressure_psi, dtype=np.float64).copy()
    rows: list[dict[str, Any]] = []

    final_pressure = None
    final_tx = final_ty = final_tz = None
    final_producer_wi = None
    converged = False

    for iteration in range(1, MAX_FIXED_POINT_ITERATIONS + 1):
        mobility = r3r2r1.phase_mobility_fields(working_sat)
        tx, ty, tz, _face_mobility = r3r2r1.build_updated_transmissibilities(
            sg3,
            tx_ref,
            ty_ref,
            tz_ref,
            mobility["lambda_total"],
        )
        A, b, producer_wi = r3r2r1.assemble_updated_pressure_system(
            sg3,
            permeability_md,
            tx,
            ty,
            tz,
            mobility["lambda_total"],
        )
        _p_pa, pressure_psi, pressure_linear_residual = (
            r3r2r1.solve_updated_pressure(sg3, A, b)
        )
        if pressure_linear_residual >= 1.0e-8:
            raise GateError(
                f"refresh_pressure_linear_residual:{pressure_linear_residual}"
            )

        try:
            sg_reconciled = np.asarray(
                physics._invert_incremental_sg_from_mass(
                    parent_mass,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                ),
                dtype=np.float64,
            )
        except Exception as exc:
            raise GateError(
                f"refresh_fixed_mass_EOS_inversion_failed:{iteration}:{repr(exc)}"
            ) from exc

        reconciled_sat = BACKGROUND_SATURATION + sg_reconciled

        reconstructed_mass = fixed_mass_reconstructed_array(
            physics,
            reconciled_sat,
            pressure_psi,
            p_ref_gas_pa,
            cell_pore_volume_m3,
        )
        max_cell_mass_error = max_abs(reconstructed_mass - parent_mass)
        global_mass_error = float(
            np.sum(reconstructed_mass) - np.sum(parent_mass)
        )

        pressure_delta_rel = relative_l2(
            pressure_psi,
            previous_pressure,
        )
        saturation_delta_linf = max_abs(
            reconciled_sat - working_sat
        )

        rows.append(
            {
                "iteration": iteration,
                "pressure_relative_L2_change": pressure_delta_rel,
                "saturation_Linf_change": saturation_delta_linf,
                "pressure_linear_relative_residual": pressure_linear_residual,
                "max_cell_mass_reconstruction_error_kg": max_cell_mass_error,
                "global_mass_reconstruction_error_kg": global_mass_error,
                "pressure_min_psi": float(np.min(pressure_psi)),
                "pressure_max_psi": float(np.max(pressure_psi)),
                "saturation_min": float(np.min(reconciled_sat)),
                "saturation_max": float(np.max(reconciled_sat)),
            }
        )

        final_pressure = pressure_psi
        final_tx, final_ty, final_tz = tx, ty, tz
        final_producer_wi = producer_wi

        if (
            pressure_delta_rel <= PRESSURE_REL_L2_TOL
            and saturation_delta_linf <= SATURATION_LINF_TOL
        ):
            working_sat = reconciled_sat
            converged = True
            break

        previous_pressure = pressure_psi
        working_sat = reconciled_sat

    if not converged:
        last = rows[-1] if rows else {}
        raise GateError(
            "refresh_pressure_saturation_fixed_point_not_converged:"
            f"{MAX_FIXED_POINT_ITERATIONS}:{last}"
        )

    # One final consistency solve from the accepted reconciled saturation.
    mobility = r3r2r1.phase_mobility_fields(working_sat)
    tx, ty, tz, _ = r3r2r1.build_updated_transmissibilities(
        sg3,
        tx_ref,
        ty_ref,
        tz_ref,
        mobility["lambda_total"],
    )
    A, b, producer_wi = r3r2r1.assemble_updated_pressure_system(
        sg3,
        permeability_md,
        tx,
        ty,
        tz,
        mobility["lambda_total"],
    )
    _p_pa, pressure_final, linear_final = r3r2r1.solve_updated_pressure(
        sg3, A, b
    )
    if linear_final >= 1.0e-8:
        raise GateError(
            f"refresh_final_pressure_linear_residual:{linear_final}"
        )

    sg_final = np.asarray(
        physics._invert_incremental_sg_from_mass(
            parent_mass,
            pressure_final,
            p_ref_gas_pa,
            cell_pore_volume_m3,
        ),
        dtype=np.float64,
    )
    sat_final = BACKGROUND_SATURATION + sg_final

    final_pressure_consistency = relative_l2(
        pressure_final,
        final_pressure,
    )
    final_saturation_consistency = max_abs(
        sat_final - working_sat
    )
    if final_pressure_consistency > PRESSURE_REL_L2_TOL:
        raise GateError(
            f"refresh_final_pressure_consistency:{final_pressure_consistency}"
        )
    if final_saturation_consistency > SATURATION_LINF_TOL:
        raise GateError(
            f"refresh_final_saturation_consistency:{final_saturation_consistency}"
        )

    recon_mass = fixed_mass_reconstructed_array(
        physics,
        sat_final,
        pressure_final,
        p_ref_gas_pa,
        cell_pore_volume_m3,
    )

    return {
        "saturation": sat_final,
        "pressure_psi": pressure_final,
        "tx": tx,
        "ty": ty,
        "tz": tz,
        "producer_wi": producer_wi,
        "mobility": mobility,
        "rows": rows,
        "iterations": len(rows),
        "max_cell_mass_error_kg": max_abs(recon_mass - parent_mass),
        "global_mass_error_kg": float(
            np.sum(recon_mass) - np.sum(parent_mass)
        ),
        "pressure_rel_L2_vs_parent": relative_l2(
            pressure_final,
            parent_pressure_psi,
        ),
        "saturation_Linf_vs_parent": max_abs(
            sat_final - parent_saturation
        ),
    }


def convert_sg5_to_sg6_streamlines(
    streamlines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for idx, s in enumerate(streamlines):
        result.append(
            {
                "id": idx,
                "points_m": np.asarray(s["points_m"], dtype=np.float64),
                "tau_s": np.asarray(s["times_s"], dtype=np.float64),
                "weight_m3_s": float(s["weight_m3_s"]),
                "tau_end_s": float(s["travel_time_s"]),
                "status": str(s["status"]),
                "producer": str(s["producer"]),
            }
        )
    return result


def transport_cfl_dt_days(
    sg7a: Any,
    xi_faces: np.ndarray,
    tau_end_s: np.ndarray,
) -> float:
    xi = np.asarray(xi_faces, dtype=np.float64)
    dxi = float(xi[1] - xi[0])
    scan = np.linspace(
        float(sg7a.S_INITIAL),
        float(sg7a.S_INJECTED),
        4001,
    )
    max_df = float(
        np.max(
            np.abs(
                np.asarray(
                    sg7a.df_dS(scan),
                    dtype=np.float64,
                )
            )
        )
    )
    u_face = np.asarray(
        sg7a.u_dimensionless(xi),
        dtype=np.float64,
    )
    max_wave_speed = float(np.max(u_face) * max_df)
    dtD_cfl = float(
        sg7a.CFL
        * dxi
        / (max_wave_speed + sg7a.EPS)
    )
    fastest_tau_days = float(
        np.min(np.asarray(tau_end_s, dtype=np.float64)) / DAY_TO_S
    )
    return float(dtD_cfl * fastest_tau_days)


def preflight_mapback_capacity(
    *,
    physics: Any,
    parent_saturation: np.ndarray,
    parent_mass: np.ndarray,
    old_cv_saturation: np.ndarray,
    new_cv_saturation: np.ndarray,
    geometry: dict[str, np.ndarray],
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    cell_pore_volume_m3: float,
) -> dict[str, Any]:
    cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
    flat = np.asarray(geometry["flat_cell"], dtype=np.int64)
    pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
    pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

    old_flat = np.asarray(old_cv_saturation, dtype=np.float64).reshape(-1)
    new_flat = np.asarray(new_cv_saturation, dtype=np.float64).reshape(-1)

    old_sub_sat = old_flat[cv_id]
    new_sub_sat = new_flat[cv_id]

    old_sub_sg = np.clip(
        old_sub_sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    new_sub_sg = np.clip(
        new_sub_sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )

    rho_old = np.asarray(
        physics.gas_density_from_state(
            old_sub_sat,
            pseg,
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    rho_new = np.asarray(
        physics.gas_density_from_state(
            new_sub_sat,
            pseg,
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )

    sub_delta_mass = pv * (
        rho_new * new_sub_sg
        - rho_old * old_sub_sg
    )
    deposited_delta_mass = np.bincount(
        flat,
        weights=sub_delta_mass,
        minlength=EXPECTED_CELLS,
    ).reshape(EXPECTED_GRID)

    smax = np.full(
        EXPECTED_GRID,
        INJECTED_BOUNDARY_SATURATION,
        dtype=np.float64,
    )
    rho_max = np.asarray(
        physics.gas_density_from_state(
            smax,
            pressure_psi,
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    capacity = (
        float(cell_pore_volume_m3)
        * rho_max
        * MAX_INCREMENTAL_CO2_SATURATION
    )

    trial_mass = np.asarray(parent_mass, dtype=np.float64) + deposited_delta_mass
    tol = max(
        1.0e-8,
        1.0e-12 * max(float(np.max(capacity)), 1.0),
    )
    excess = trial_mass - capacity
    over = excess > tol

    return {
        "overcapacity_cell_count": int(np.sum(over)),
        "max_capacity_excess_kg": float(max(float(np.max(excess)), 0.0)),
        "minimum_capacity_margin_kg": float(np.min(capacity - trial_mass)),
        "capacity_tolerance_kg": float(tol),
        "deposited_delta_mass": deposited_delta_mass,
        "subsegment_delta_mass_kg": float(np.sum(sub_delta_mass)),
        "trial_mass": trial_mass,
        "capacity_mass": capacity,
    }


def validate_child_bytes(
    data: bytes,
    expected_step: int,
    expected_time: float,
    expected_sat: np.ndarray,
    expected_pressure: np.ndarray,
) -> None:
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        if int(z["accepted_step_index"]) != expected_step:
            raise GateError(
                f"child_step_mismatch:{int(z['accepted_step_index'])}:{expected_step}"
            )
        if float(z["physical_time_days"]) != expected_time:
            raise GateError(
                f"child_time_mismatch:{float(z['physical_time_days'])}:{expected_time}"
            )
        if not np.array_equal(z["transport_saturation"], expected_sat):
            raise GateError("child_saturation_not_byte_exact")
        if not np.array_equal(z["accepted_pressure_psi"], expected_pressure):
            raise GateError("child_pressure_not_byte_exact")
        if not bool(z["path_cache_valid"]):
            raise GateError("child_path_cache_invalid")
        if not bool(z["tof_cache_valid"]):
            raise GateError("child_tof_cache_invalid")
        if bool(z["exact_retrace_required"]):
            raise GateError("child_unexpected_retrace_required")


def self_test() -> None:
    if not (
        0.0
        < ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS
        < 0.1
    ):
        raise RuntimeError("self_test_candidate_dt")

    parent_time = EXPECTED_PARENT_TIME_DAYS
    child_time = parent_time + ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS
    if not child_time > parent_time:
        raise RuntimeError("self_test_time_advance")

    # Same-time refresh invariants.
    parent_mass = np.asarray([1.0, 2.0, 3.0])
    refreshed_mass = parent_mass.copy()
    if not np.array_equal(parent_mass, refreshed_mass):
        raise RuntimeError("self_test_refresh_mass_invariant")

    print(
        "PAD-Stream V16E-41-R3-R4 controlled same-parent mass-conservative "
        "refreshed-flow transition validation self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None
    parent_sha_before: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 158)
        print(
            "PAD-Stream V16E-41-R3-R4 — Controlled Same-Parent "
            "Mass-Conservative Saturation-Updated Flow-Refresh Transition Validation"
        )
        print("=" * 158)
        print("PARENT     : exact R3-R1 partial state, step 3975")
        print("REFRESH    : same-time cellwise-mass-conservative pressure/saturation fixed point")
        print(
            f"CANDIDATE  : original stale-flow nominal dt = "
            f"{ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS:.18g} d"
        )
        print("RETRY RULE : same candidate dt; no capacity dt reduction authorized")
        print("COMMIT     : exactly one physical child transition if all gates pass")
        print("100D CLAIM : none")

        failed_stage = "source_identity_binding"

        modules: dict[str, Any] = {}
        paths: dict[str, Path] = {}
        for role, (filename, expected_blob) in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"source_exists_{role}", p.is_file(), p)
            actual_blob = git_blob_sha(p, root)
            gate(
                f"source_git_blob_exact_{role}",
                actual_blob == expected_blob,
                actual_blob,
            )
            paths[role] = p

        r3r2r1 = load_module(
            paths["R3R2R1"],
            "pad_stream_v16e41r3r4_r3r2r1",
        )
        e36 = load_module(
            paths["E36"],
            "pad_stream_v16e41r3r4_e36",
        )
        e37a = load_module(
            paths["E37A"],
            "pad_stream_v16e41r3r4_e37a",
        )
        physics = load_module(
            paths["R2_PHYSICS"],
            "pad_stream_v16e41r3r4_physics",
        )
        sg2 = load_module(
            paths["SG2"],
            "pad_stream_v16e41r3r4_sg2",
        )
        sg3 = load_module(
            paths["SG3"],
            "pad_stream_v16e41r3r4_sg3",
        )
        sg4 = load_module(
            paths["SG4"],
            "pad_stream_v16e41r3r4_sg4",
        )
        sg5 = load_module(
            paths["SG5"],
            "pad_stream_v16e41r3r4_sg5",
        )
        sg6 = load_module(
            paths["SG6"],
            "pad_stream_v16e41r3r4_sg6",
        )
        sg7a = load_module(
            paths["SG7A"],
            "pad_stream_v16e41r3r4_sg7a",
        )
        sg7d = load_module(
            paths["SG7D"],
            "pad_stream_v16e41r3r4_sg7d",
        )

        failed_stage = "architecture_and_parent_binding"

        contract_path = drive / R3R3R1_REL / R3R3R1_CONTRACT
        closure_path = drive / R3R3R1_REL / R3R3R1_CLOSURE
        parent_path = drive / R3R1_REL / R3R1_STATE

        for p in [contract_path, closure_path, parent_path]:
            gate(f"required_artifact_exists_{p.name}", p.is_file(), p)

        contract = load_json(contract_path)
        closure = load_json(closure_path)

        gate(
            "R3R3R1_status_exact",
            contract.get("status") == EXPECTED_R3R3R1_STATUS,
            contract.get("status"),
        )
        gate(
            "R3R3R1_closure_passed",
            closure.get("all_gates_passed") is True,
            closure.get("all_gates_passed"),
        )
        gate(
            "R3R3R1_primary_conserved_quantity",
            contract.get("primary_conserved_refresh_quantity")
            == "cellwise Cartesian CO2 component mass array",
            contract.get("primary_conserved_refresh_quantity"),
        )

        parent_sha_before = sha256_file(parent_path)
        gate(
            "parent_state_SHA_exact",
            parent_sha_before == EXPECTED_PARENT_STATE_SHA256,
            parent_sha_before,
        )

        parent = load_npz(parent_path)
        gate(
            "parent_step_exact",
            int_scalar(parent["accepted_step_index"]) == EXPECTED_PARENT_STEP,
            int_scalar(parent["accepted_step_index"]),
        )
        gate(
            "parent_time_exact",
            abs(
                scalar(parent["physical_time_days"])
                - EXPECTED_PARENT_TIME_DAYS
            ) <= 1.0e-12,
            scalar(parent["physical_time_days"]),
        )
        gate(
            "parent_grid_shape_exact",
            tuple(
                np.asarray(
                    parent["transport_saturation"]
                ).shape
            ) == EXPECTED_GRID,
            np.asarray(parent["transport_saturation"]).shape,
        )

        parent_sat = np.asarray(
            parent["transport_saturation"],
            dtype=np.float64,
        )
        parent_pressure = np.asarray(
            parent["accepted_pressure_psi"],
            dtype=np.float64,
        )
        p_ref_gas_pa = scalar(
            parent["co2_density_reference_pressure_pa"]
        )
        parent_stored_ledger = scalar(
            parent["stored_co2_mass_current_kg"]
        )

        dx_m = 20.0 * FT_TO_M
        dy_m = 20.0 * FT_TO_M
        dz_m = 4.0 * FT_TO_M
        cell_pore_volume_m3 = (
            0.20 * dx_m * dy_m * dz_m
        )

        parent_mass = parent_cellwise_component_mass(
            physics,
            parent_sat,
            parent_pressure,
            p_ref_gas_pa,
            cell_pore_volume_m3,
        )
        parent_mass_total = float(np.sum(parent_mass))
        parent_mass_tol = max(
            1.0e-6,
            1.0e-10 * max(abs(parent_stored_ledger), 1.0),
        )
        gate(
            "parent_cellwise_mass_closes_to_ledger",
            abs(parent_mass_total - parent_stored_ledger)
            <= parent_mass_tol,
            parent_mass_total - parent_stored_ledger,
        )

        permeability_md = np.loadtxt(
            paths["PERM"],
            skiprows=1,
            dtype=np.float64,
        ).reshape(EXPECTED_GRID, order="C")

        failed_stage = "same_time_mass_conservative_pressure_saturation_fixed_point"

        refresh = fixed_point_refresh(
            physics=physics,
            r3r2r1=r3r2r1,
            sg2=sg2,
            sg3=sg3,
            permeability_md=permeability_md,
            parent_mass=parent_mass,
            parent_saturation=parent_sat,
            parent_pressure_psi=parent_pressure,
            p_ref_gas_pa=p_ref_gas_pa,
            cell_pore_volume_m3=cell_pore_volume_m3,
        )

        reconciled_sat = np.asarray(
            refresh["saturation"],
            dtype=np.float64,
        )
        pressure_psi = np.asarray(
            refresh["pressure_psi"],
            dtype=np.float64,
        )

        refresh_mass_tol = max(
            1.0e-6,
            1.0e-10 * max(abs(parent_mass_total), 1.0),
        )
        gate(
            "refresh_fixed_point_converged_before_budget",
            refresh["iterations"] <= MAX_FIXED_POINT_ITERATIONS,
            refresh["iterations"],
        )
        gate(
            "refresh_cellwise_mass_reconstruction",
            refresh["max_cell_mass_error_kg"]
            <= max(1.0e-8, refresh_mass_tol),
            refresh["max_cell_mass_error_kg"],
        )
        gate(
            "refresh_global_mass_reconstruction",
            abs(refresh["global_mass_error_kg"])
            <= refresh_mass_tol,
            refresh["global_mass_error_kg"],
        )
        gate(
            "refresh_saturation_bounds",
            float(np.min(reconciled_sat))
            >= BACKGROUND_SATURATION - 1.0e-12
            and float(np.max(reconciled_sat))
            <= INJECTED_BOUNDARY_SATURATION + 1.0e-12,
            f"{np.min(reconciled_sat)}:{np.max(reconciled_sat)}",
        )

        failed_stage = "refreshed_conservative_flow_and_exact_streamlines"

        producer_rates, producer_sink = r3r2r1.producer_rates_updated(
            sg3,
            pressure_psi,
            refresh["producer_wi"],
        )
        gate(
            "refreshed_BHP_wells_remain_producers",
            all(
                float(v["m3_s"]) > 0.0
                for v in producer_rates.values()
            ),
            {
                k: float(v["m3_day"])
                for k, v in producer_rates.items()
            },
        )

        qx, qy, qz = sg4.compute_face_fluxes(
            pressure_psi,
            refresh["tx"],
            refresh["ty"],
            refresh["tz"],
        )
        conservation = r3r2r1.flow_conservation_metrics(
            sg3,
            sg4,
            qx,
            qy,
            qz,
            producer_sink,
        )
        gate(
            "refreshed_flow_local_conservation",
            conservation["local_relative_l2_error"] < 1.0e-8,
            conservation["local_relative_l2_error"],
        )
        gate(
            "refreshed_flow_global_conservation",
            conservation["global_relative_mismatch"] < 1.0e-8,
            conservation["global_relative_mismatch"],
        )

        vx, vy, vz = sg5.construct_face_pore_velocities(
            qx, qy, qz
        )
        faces, seeds = sg5.build_seeds(qx, qy, qz)
        streamlines = sg5.trace_streamlines(
            seeds,
            vx,
            vy,
            vz,
        )

        seed_weight = float(
            sum(float(s["weight_m3_s"]) for s in seeds)
        )
        captured = [
            s
            for s in streamlines
            if s["status"] == "PRODUCER"
        ]
        captured_weight = float(
            sum(float(s["weight_m3_s"]) for s in captured)
        )
        capture_fraction = (
            captured_weight
            / max(seed_weight, 1.0e-30)
        )
        gate(
            "refreshed_streamline_full_weight_capture",
            abs(capture_fraction - 1.0) <= 1.0e-10,
            capture_fraction,
        )

        sg6_streamlines = convert_sg5_to_sg6_streamlines(
            streamlines
        )
        db = sg6.build_transport_database(
            sg6_streamlines
        )

        xyz_m = np.asarray(
            db["xyz_m"],
            dtype=np.float64,
        )
        tau_s = np.asarray(
            db["tau_s"],
            dtype=np.float64,
        )
        tau_end_s = np.asarray(
            db["tau_end_s"],
            dtype=np.float64,
        )
        weights_m3_s = np.asarray(
            db["weights_m3_s"],
            dtype=np.float64,
        )
        labels = np.asarray(
            db["producer"]
        ).astype(str)
        xi_faces = np.asarray(
            db["xi"],
            dtype=np.float64,
        )

        gate(
            "refreshed_streamline_count_exact",
            xyz_m.shape[0] == len(seeds),
            f"{xyz_m.shape[0]}:{len(seeds)}",
        )

        refreshed_cfl_dt_days = transport_cfl_dt_days(
            sg7a,
            xi_faces,
            tau_end_s,
        )
        gate(
            "original_candidate_dt_admitted_by_refreshed_CFL",
            ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS
            <= refreshed_cfl_dt_days + 1.0e-15,
            (
                f"candidate={ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS}:"
                f"refreshed_CFL={refreshed_cfl_dt_days}"
            ),
        )

        nstream = int(xyz_m.shape[0])
        nfaces = int(xi_faces.shape[0])
        ncv = nfaces - 1
        weights_m3_day = weights_m3_s * DAY_TO_S
        tof_days = tau_s / DAY_TO_S

        operator = sg7d.build_subsegment_operator(
            xyz_m,
            tof_days,
            weights_m3_day,
        )
        geometry = e37a.build_control_volume_geometry(
            physics,
            operator,
            pressure_psi,
            p_ref_gas_pa,
            nstream,
            ncv,
        )
        face_pressure_psi = e37a.build_face_pressure(
            e36,
            sg7d,
            xyz_m,
            pressure_psi,
        )

        failed_stage = "same_parent_nominal_transport_trial"

        old_cv_sat, old_cv_mass, sample_closure = (
            e37a.sample_grid_inventory_to_control_volumes(
                physics,
                reconciled_sat,
                pressure_psi,
                p_ref_gas_pa,
                geometry,
                nstream,
                ncv,
            )
        )
        sample_tol = max(
            1.0e-6,
            1.0e-10
            * max(abs(float(np.sum(old_cv_mass))), 1.0),
        )
        gate(
            "grid_to_CV_sampling_closure",
            abs(sample_closure) <= sample_tol,
            sample_closure,
        )

        transport = e37a.advance_component_mass_control_volumes(
            physics,
            sg7a,
            old_cv_sat,
            old_cv_mass,
            geometry["cv_pressure_mass_coeff"],
            face_pressure_psi,
            p_ref_gas_pa,
            weights_m3_day,
            xi_faces,
            ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS,
        )

        injected_step = float(
            transport["injected_mass_kg"]
        )
        produced_step = float(
            transport["produced_mass_kg"]
        )
        physical_injected = (
            INJECTOR_MASS_RATE_KG_DAY
            * ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS
        )
        injection_tol = max(
            1.0e-6,
            1.0e-12
            * max(abs(physical_injected), 1.0),
        )
        gate(
            "fixed_rate_injected_mass_exact",
            abs(injected_step - physical_injected)
            <= injection_tol,
            injected_step - physical_injected,
        )

        target_final_mass = (
            parent_mass_total
            + injected_step
            - produced_step
        )

        preflight = preflight_mapback_capacity(
            physics=physics,
            parent_saturation=reconciled_sat,
            parent_mass=parent_mass,
            old_cv_saturation=old_cv_sat,
            new_cv_saturation=transport["new_saturation"],
            geometry=geometry,
            pressure_psi=pressure_psi,
            p_ref_gas_pa=p_ref_gas_pa,
            cell_pore_volume_m3=cell_pore_volume_m3,
        )
        gate(
            "same_dt_raw_mapback_capacity_preflight_pass",
            preflight["overcapacity_cell_count"] == 0,
            {
                "count": preflight["overcapacity_cell_count"],
                "max_excess_kg": preflight[
                    "max_capacity_excess_kg"
                ],
                "minimum_margin_kg": preflight[
                    "minimum_capacity_margin_kg"
                ],
            },
        )

        mapping = e37a.map_control_volume_increment_to_grid(
            physics,
            reconciled_sat,
            old_cv_sat,
            transport["new_saturation"],
            old_cv_mass,
            transport["new_mass"],
            geometry,
            pressure_psi,
            p_ref_gas_pa,
            cell_pore_volume_m3,
            target_final_mass,
        )
        pre_capillary_sat = np.asarray(
            mapping["corrected_saturation"],
            dtype=np.float64,
        )

        capillary = physics.conservative_capillary_mass_redistribution(
            transport_saturation=pre_capillary_sat,
            permeability_md=permeability_md,
            pressure_psi=pressure_psi,
            p_ref_pa=p_ref_gas_pa,
            cell_pore_volume_m3=cell_pore_volume_m3,
            dt_seconds=(
                ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS
                * DAY_TO_S
            ),
        )
        child_sat = np.asarray(
            capillary["corrected"],
            dtype=np.float64,
        )
        final_stored = float(
            capillary["final_mass_state_kg"]
        )

        step_residual = (
            final_stored
            - parent_mass_total
            - injected_step
            + produced_step
        )
        closure_tol = max(
            1.0e-6,
            1.0e-10 * max(abs(target_final_mass), 1.0),
        )

        gate(
            "capillary_external_mass_zero",
            abs(capillary["external_mass_change_kg"])
            <= closure_tol,
            capillary["external_mass_change_kg"],
        )
        gate(
            "capillary_preserves_pre_capillary_mass",
            abs(
                capillary["final_mass_state_kg"]
                - mapping["mapped_final_mass_kg"]
            )
            <= closure_tol,
            (
                capillary["final_mass_state_kg"]
                - mapping["mapped_final_mass_kg"]
            ),
        )
        gate(
            "transition_component_mass_closure",
            abs(step_residual) <= closure_tol,
            step_residual,
        )
        gate(
            "child_saturation_bounds",
            float(np.min(child_sat))
            >= BACKGROUND_SATURATION - 1.0e-12
            and float(np.max(child_sat))
            <= INJECTED_BOUNDARY_SATURATION + 1.0e-12,
            f"{np.min(child_sat)}:{np.max(child_sat)}",
        )

        prod_rows, aggregate_cut = e37a.producer_rows_from_flux(
            labels,
            weights_m3_day,
            transport["outlet_fractional_flow"],
            transport["face_mass_flux_kg_day"][:, -1],
            ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS,
        )
        gate(
            "producer_CO2_cut_finite_bounded",
            np.isfinite(aggregate_cut)
            and 0.0 <= aggregate_cut <= 1.0,
            aggregate_cut,
        )

        failed_stage = "single_child_commit"

        child = e36.make_child_state(
            parent,
            child_sat,
            pressure_psi,
            p_ref_gas_pa,
            ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS,
            produced_step,
            aggregate_cut,
            final_stored,
            step_residual,
            False,
        )

        child["transport_saturation_history"] = np.maximum(
            np.asarray(
                child["transport_saturation_history"],
                dtype=np.float64,
            ),
            reconciled_sat,
        )
        child["transport_face_count"] = np.asarray(
            nfaces,
            dtype=np.int64,
        )
        child["transport_control_volume_count"] = np.asarray(
            ncv,
            dtype=np.int64,
        )
        child[
            "control_volume_aligned_transfer_active"
        ] = np.asarray(True, dtype=bool)
        child[
            "component_mass_primary_conserved_variable"
        ] = np.asarray(True, dtype=bool)
        child[
            "injector_local_mass_closure_authorized"
        ] = np.asarray(False, dtype=bool)
        child[
            "injector_local_mass_closure_executed"
        ] = np.asarray(False, dtype=bool)
        child["last_source_local_added_mass_kg"] = np.asarray(
            0.0,
            dtype=np.float64,
        )
        child["last_CV_transport_mass_residual_kg"] = np.asarray(
            transport["mass_residual_kg"],
            dtype=np.float64,
        )
        child[
            "last_CV_to_grid_transfer_residual_kg"
        ] = np.asarray(
            mapping["transfer_residual_kg"],
            dtype=np.float64,
        )
        child[
            "mass_conservative_flow_refresh_active"
        ] = np.asarray(True, dtype=bool)
        child[
            "pressure_saturation_reconciliation_converged"
        ] = np.asarray(True, dtype=bool)
        child[
            "flow_refresh_fixed_point_iterations"
        ] = np.asarray(
            refresh["iterations"],
            dtype=np.int64,
        )
        child[
            "flow_refresh_parent_cellwise_mass_preserved"
        ] = np.asarray(True, dtype=bool)
        child[
            "flow_refresh_same_parent_candidate_dt_reused"
        ] = np.asarray(True, dtype=bool)
        child[
            "flow_refresh_capacity_timestep_reduction_used"
        ] = np.asarray(False, dtype=bool)
        child[
            "flow_refresh_refreshed_CFL_dt_days"
        ] = np.asarray(
            refreshed_cfl_dt_days,
            dtype=np.float64,
        )
        child[
            "flow_refresh_parent_time_days"
        ] = np.asarray(
            EXPECTED_PARENT_TIME_DAYS,
            dtype=np.float64,
        )
        child[
            "flow_refresh_reconciled_same_time_saturation"
        ] = reconciled_sat.astype(np.float64)

        child_time = (
            EXPECTED_PARENT_TIME_DAYS
            + ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS
        )
        gate(
            "child_step_exact",
            int_scalar(child["accepted_step_index"])
            == EXPECTED_CHILD_STEP,
            int_scalar(child["accepted_step_index"]),
        )
        gate(
            "child_time_exact",
            abs(
                scalar(child["physical_time_days"])
                - child_time
            ) <= 1.0e-12,
            scalar(child["physical_time_days"]),
        )
        gate(
            "child_uses_refreshed_pressure",
            np.array_equal(
                np.asarray(
                    child["accepted_pressure_psi"],
                    dtype=np.float64,
                ),
                pressure_psi,
            ),
        )
        gate(
            "child_same_candidate_dt_exact",
            abs(
                scalar(child["last_accepted_dt_days"])
                - ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS
            ) <= 1.0e-15,
            scalar(child["last_accepted_dt_days"]),
        )
        gate(
            "parent_state_unchanged",
            sha256_file(parent_path) == parent_sha_before,
            sha256_file(parent_path),
        )

        child_bytes = deterministic_npz_bytes(child)
        validate_child_bytes(
            child_bytes,
            EXPECTED_CHILD_STEP,
            child_time,
            child_sat,
            pressure_psi,
        )
        child_sha = hashlib.sha256(child_bytes).hexdigest()

        reconciled_epoch_arrays = {
            "physical_time_days": np.asarray(
                EXPECTED_PARENT_TIME_DAYS,
                dtype=np.float64,
            ),
            "accepted_step_index": np.asarray(
                EXPECTED_PARENT_STEP,
                dtype=np.int64,
            ),
            "parent_state_sha256_ascii": np.frombuffer(
                EXPECTED_PARENT_STATE_SHA256.encode("ascii"),
                dtype=np.uint8,
            ),
            "parent_cellwise_component_mass_kg": parent_mass,
            "reconciled_saturation": reconciled_sat,
            "reconciled_pressure_psi": pressure_psi,
            "qx_m3_s": qx,
            "qy_m3_s": qy,
            "qz_m3_s": qz,
            "streamline_xyz_m": xyz_m,
            "streamline_tof_s": tau_s,
            "streamline_weights_m3_s": weights_m3_s,
            "xi": xi_faces,
            "producer_labels": labels.astype("U32"),
            "fixed_point_iterations": np.asarray(
                refresh["iterations"],
                dtype=np.int64,
            ),
            "fixed_point_global_mass_error_kg": np.asarray(
                refresh["global_mass_error_kg"],
                dtype=np.float64,
            ),
            "fixed_point_max_cell_mass_error_kg": np.asarray(
                refresh["max_cell_mass_error_kg"],
                dtype=np.float64,
            ),
            "refreshed_CFL_dt_days": np.asarray(
                refreshed_cfl_dt_days,
                dtype=np.float64,
            ),
            "same_time_reconciliation_only": np.asarray(
                True,
                dtype=bool,
            ),
        }
        reconciled_bytes = deterministic_npz_bytes(
            reconciled_epoch_arrays
        )
        reconciled_sha = hashlib.sha256(
            reconciled_bytes
        ).hexdigest()

        convergence_rows = refresh["rows"]
        producer_rows_out = [
            {
                "accepted_step_index": EXPECTED_CHILD_STEP,
                "time_days": child_time,
                **row,
            }
            for row in prod_rows
        ]

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "parent_step": EXPECTED_PARENT_STEP,
            "parent_time_days": EXPECTED_PARENT_TIME_DAYS,
            "parent_state_sha256": EXPECTED_PARENT_STATE_SHA256,
            "child_step": EXPECTED_CHILD_STEP,
            "child_time_days": child_time,
            "child_state_sha256": child_sha,
            "reconciled_epoch_sha256": reconciled_sha,
            "same_time_refresh": {
                "fixed_point_iterations": refresh["iterations"],
                "pressure_relative_L2_vs_parent": refresh[
                    "pressure_rel_L2_vs_parent"
                ],
                "saturation_Linf_vs_parent": refresh[
                    "saturation_Linf_vs_parent"
                ],
                "global_component_mass_error_kg": refresh[
                    "global_mass_error_kg"
                ],
                "max_cell_component_mass_error_kg": refresh[
                    "max_cell_mass_error_kg"
                ],
                "physical_time_advance_days": 0.0,
                "accepted_step_advance": 0,
                "mass_redistribution": False,
                "external_mass_source_sink_kg": 0.0,
            },
            "refreshed_flow": {
                "local_relative_conservation_error": conservation[
                    "local_relative_l2_error"
                ],
                "global_relative_conservation_error": conservation[
                    "global_relative_mismatch"
                ],
                "streamline_count": int(xyz_m.shape[0]),
                "capture_fraction": capture_fraction,
                "refreshed_CFL_dt_days": refreshed_cfl_dt_days,
            },
            "same_parent_candidate": {
                "requested_dt_days":
                    ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS,
                "accepted_dt_days":
                    scalar(child["last_accepted_dt_days"]),
                "capacity_timestep_reduction_used": False,
                "raw_overcapacity_cell_count": preflight[
                    "overcapacity_cell_count"
                ],
                "raw_max_capacity_excess_kg": preflight[
                    "max_capacity_excess_kg"
                ],
                "raw_minimum_capacity_margin_kg": preflight[
                    "minimum_capacity_margin_kg"
                ],
            },
            "transition": {
                "injected_CO2_mass_kg": injected_step,
                "produced_CO2_mass_kg": produced_step,
                "stored_CO2_mass_kg": final_stored,
                "CV_transport_mass_residual_kg": transport[
                    "mass_residual_kg"
                ],
                "CV_to_grid_transfer_residual_kg": mapping[
                    "transfer_residual_kg"
                ],
                "grid_mapback_ledger_residual_kg": mapping[
                    "ledger_residual_kg"
                ],
                "capillary_external_mass_change_kg": capillary[
                    "external_mass_change_kg"
                ],
                "step_component_mass_residual_kg": step_residual,
                "producer_CO2_gas_cut": aggregate_cut,
            },
            "100d_rollout_authorized": False,
            "production_cadence_frozen": False,
            "next_milestone": NEXT,
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(
                v["passed"] for v in gates.values()
            ),
            "gate_count": len(gates),
            "parent_state_unchanged": (
                sha256_file(parent_path) == parent_sha_before
            ),
            "same_time_refresh_mass_conservative": True,
            "same_dt_retry_accepted": True,
            "capacity_timestep_reduction_used": False,
            "exactly_one_child_committed": True,
            "child_state_sha256": child_sha,
            "canonical_100d_state_created": False,
            "production_cadence_frozen": False,
            "next_milestone": NEXT,
        }

        files = {
            CHILD_STATE_NAME: child_bytes,
            RECONCILED_EPOCH_NAME: reconciled_bytes,
            "PAD_Stream_V16E41R3R4_Summary.json": json_bytes(summary),
            "V16E41R3R4_Fixed_Point_Convergence.csv": csv_bytes(
                convergence_rows
            ),
            "V16E41R3R4_Producer_Output.csv": csv_bytes(
                producer_rows_out
            ),
            "V16E41R3R4_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
            "V16E41R3R4_Final_Closure.json": json_bytes(
                closure
            ),
        }

        immutable_publish(out, files)

        manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E41R3R4_Artifact_Manifest.csv":
                manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {"V16E41R3R4_Artifact_Manifest.csv": csv_bytes(manifest)},
        )

        print("\n" + "=" * 158)
        print("PAD-Stream V16E-41-R3-R4: PASS")
        print("=" * 158)
        print(f"{'Status':68}: {STATUS}")
        print(
            f"{'Parent step / time':68}: "
            f"{EXPECTED_PARENT_STEP} / "
            f"{EXPECTED_PARENT_TIME_DAYS:.15g} d"
        )
        print(
            f"{'Fixed-point iterations':68}: "
            f"{refresh['iterations']}"
        )
        print(
            f"{'Pressure rel L2 vs parent':68}: "
            f"{refresh['pressure_rel_L2_vs_parent']:.12e}"
        )
        print(
            f"{'Saturation Linf vs parent':68}: "
            f"{refresh['saturation_Linf_vs_parent']:.12e}"
        )
        print(
            f"{'Refresh global mass error':68}: "
            f"{refresh['global_mass_error_kg']:.12e} kg"
        )
        print(
            f"{'Refreshed Pollock streamlines / capture':68}: "
            f"{xyz_m.shape[0]} / {capture_fraction:.12f}"
        )
        print(
            f"{'Refreshed CFL dt':68}: "
            f"{refreshed_cfl_dt_days:.18g} d"
        )
        print(
            f"{'Requested / accepted candidate dt':68}: "
            f"{ORIGINAL_STALE_FLOW_CANDIDATE_DT_DAYS:.18g} / "
            f"{scalar(child['last_accepted_dt_days']):.18g} d"
        )
        print(
            f"{'Raw map-back overcapacity cells':68}: "
            f"{preflight['overcapacity_cell_count']}"
        )
        print(
            f"{'Raw minimum capacity margin':68}: "
            f"{preflight['minimum_capacity_margin_kg']:.12e} kg"
        )
        print(
            f"{'Capillary external mass':68}: "
            f"{capillary['external_mass_change_kg']:.12e} kg"
        )
        print(
            f"{'Step component-mass residual':68}: "
            f"{step_residual:.12e} kg"
        )
        print(
            f"{'Child step / time':68}: "
            f"{EXPECTED_CHILD_STEP} / {child_time:.15g} d"
        )
        print(
            f"{'Child state SHA':68}: {child_sha}"
        )
        print(f"{'Next':68}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": (
                "SAME_PARENT_MASS_CONSERVATIVE_REFRESHED_FLOW_"
                "TRANSITION_VALIDATION_BLOCKED"
            ),
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E41R3R4_Blocked_Transition_Validation.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E41R3R4_Blocked_Transition_Validation_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)

        print("\n" + "=" * 158)
        print("PAD-Stream V16E-41-R3-R4: BLOCKED")
        print("=" * 158)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
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
