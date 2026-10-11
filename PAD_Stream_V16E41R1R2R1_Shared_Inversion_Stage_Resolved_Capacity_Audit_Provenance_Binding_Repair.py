from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import inspect
import io
import json
import shutil
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np


MILESTONE = "V16E-41-R1-R2-R1"
STATUS = "SHARED_INVERSION_STAGE_RESOLVED_CAPACITY_FAILURE_AUDITED_R1"
NEXT = "V16E-41-R2 - Stage-Appropriate Bound-Preserving Conservative Capacity Repair"

EXPECTED_GRID = (15, 50, 50)
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
CO2_RHO_REF_KG_M3 = 700.0
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0

EXPECTED_E40_STEP = 1222
EXPECTED_E40_TIME_DAYS = 60.0
EXPECTED_TARGET_STEP = 1475
EXPECTED_PARENT_STEP = 1474
# Parent time is bound dynamically to the formal V16E-41 blocked report.
EXPECTED_RETRY_COUNT = 9
EXPECTED_LAST_RETRY_EXCESS_KG = 0.00034387635241728276
EXPECTED_FAILURE_TOKEN = "capillary_cell_mass_capacity_exceeded"

MAX_TRIAL_RETRIES = 8
RETRY_FACTOR = 0.5

R2_RUNNER = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_"
    "First_Controlled_Transition.py"
)
R2_RUNNER_SHA256 = "3a1bf71ef601308e2fc18168bf2b9fc7c3dc9b0ff98e3735de1d4fa6ee624ab6"

E36_RUNNER = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_RUNNER_SHA256 = "747a4f6ee4a5458624311fe2226773e0db778cc40a0460adfcbc454be22a3a0c"
E36_REL = Path("provenance/hybrid_dp/V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION")
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"

E37A_RUNNER = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_RUNNER_SHA256 = "d2f0a006569846048c647cfccac3df9bb8a7ed970c3431c2291a617ea455ec59"
E37A_REL = Path("provenance/hybrid_dp/V16E37A_CONTROL_VOLUME_ALIGNED_CONSERVATIVE_STREAMLINE_GRID_TRANSFER")
E37A_SUMMARY = "PAD_Stream_V16E37A_Summary.json"

E37B_RUNNER = "PAD_Stream_V16E37B_Extended_SGSim_Runtime_Rollout_and_First_Fixed_Observation_Checkpoint.py"
E37B_RUNNER_SHA256 = "8abec0348cb683e7805fd5b847d3f24b88b855edd3386914a6aad9a3a1d87471"

E38_RUNNER = "PAD_Stream_V16E38_Breakthrough_Event_Refinement_and_Canonical_BT_State.py"
E38_RUNNER_SHA256 = "6ed0ccb552353e25ea5bc6bd4ebc562469d2049b2e81da73e0640eebf2f7b478"

E40_RUNNER = "PAD_Stream_V16E40_Post_Breakthrough_SGSim_Rollout_and_Second_60d_Observation_Checkpoint.py"
E40_RUNNER_SHA256 = "27fe993a140ddfaa919f81124f4ef53ed4058c3b37000b0911810969325b8a28"
E40_REL = Path("provenance/hybrid_dp/V16E40_POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT")
E40_SUMMARY = "PAD_Stream_V16E40_Summary.json"
E40_CLOSURE = "V16E40_Final_Closure.json"
E40_CANONICAL = "V16E40_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0060d.npz"

E41_RUNNER = "PAD_Stream_V16E41_Production_100D_Checkpoint_and_Legacy_Frozen_Candidate_Regression.py"
E41_RUNNER_SHA256 = "d2365d3ddc3374c4afda3a9aa15a32ef6ec6ed1a50ee0659932447aac2d04771"

R1_RUNNER = "PAD_Stream_V16E41R1_Long_Horizon_Capillary_Cell_Mass_Capacity_Failure_Audit.py"
R1_RUNNER_SHA256 = "d37be55dd7ea9eccc1fa3988fcba70dfe4a9da874e7790c1a0872f8bd97f81c8"

R1R1_RUNNER = "PAD_Stream_V16E41R1R1_Formal_E41_Trajectory_Bound_Capillary_Capacity_Failure_Audit.py"
R1R1_RUNNER_SHA256 = "7abcbe900fd266326023be7ddd7a7a6bed40b4ec9424d9305583f82a6cb9436d"

R1R2_RUNNER = "PAD_Stream_V16E41R1R2_Shared_Inversion_Stage_Resolved_Capacity_Failure_Audit.py"
R1R2_RUNNER_SHA256 = "5b522e43ae4751eb73cc00f50010b8de34b259997ab7a475ed278a169d1c06a9"
R1R1_BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R1R1_BLOCKED_FORMAL_E41_TRAJECTORY_BOUND_CAPILLARY_CAPACITY_AUDIT"
)
R1R1_BLOCKED_REPORT = "V16E41R1R1_Blocked_Audit.json"
R1_BLOCKED_REL = Path("provenance/hybrid_dp/V16E41R1_BLOCKED_CAPILLARY_CELL_MASS_CAPACITY_FAILURE_AUDIT")
R1_BLOCKED_REPORT = "V16E41R1_Blocked_Audit.json"
E41_BLOCKED_REL = Path("provenance/hybrid_dp/V16E41_BLOCKED_PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION")
E41_BLOCKED_REPORT = "V16E41_Blocked_100D_Production_Regression.json"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"

OUT_REL = Path("provenance/hybrid_dp/V16E41R1R2R1_SHARED_INVERSION_STAGE_RESOLVED_CAPACITY_FAILURE_AUDIT_PROVENANCE_REPAIR")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E41R1R2R1_BLOCKED_SHARED_INVERSION_STAGE_RESOLVED_CAPACITY_AUDIT_PROVENANCE_REPAIR")


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
        outer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
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


def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))


def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))


def bool_scalar(a: Any) -> bool:
    return bool(np.asarray(a).reshape(()))


def self_test() -> None:
    dt = 0.049123143364170854
    retries = [dt * (0.5 ** r) for r in range(9)]
    if len(retries) != EXPECTED_RETRY_COUNT:
        raise RuntimeError("self_test_retry_count")
    if abs(retries[-1] * DAY_TO_S - 16.579060885407664) > 1.0e-9:
        raise RuntimeError("self_test_last_retry_seconds")

    mass = 10.0
    capacity = 10.2
    div_mass = -0.01
    h_cap = (capacity - mass) / (-div_mass)
    if abs(h_cap - 20.0) > 1.0e-12:
        raise RuntimeError("self_test_capacity_dt")
    trial = mass - 25.0 * div_mass
    if not trial > capacity:
        raise RuntimeError("self_test_capacity_violation")

    print("PAD-Stream V16E-41-R1-R2-R1 provenance-binding repair self-test: PASS")


def build_stage_detail_rows(
    *,
    retry: int,
    k0: int,
    j0: int,
    i0: int,
    S: np.ndarray,
    mass: np.ndarray,
    capacity: np.ndarray,
    trial_mass: np.ndarray,
    div_mass: np.ndarray,
    pressure_psi: np.ndarray,
    permeability_md: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    nz, ny, nx = S.shape
    for kk in range(max(0, k0 - 1), min(nz, k0 + 2)):
        for jj in range(max(0, j0 - 1), min(ny, j0 + 2)):
            for ii in range(max(0, i0 - 1), min(nx, i0 + 2)):
                rows.append(
                    {
                        "retry": retry,
                        "dk": kk - k0,
                        "dj": jj - j0,
                        "di": ii - i0,
                        "k_zero_based": kk,
                        "j_zero_based": jj,
                        "i_zero_based": ii,
                        "k_one_based": kk + 1,
                        "j_one_based": jj + 1,
                        "i_one_based": ii + 1,
                        "transport_saturation_before_substep": float(S[kk, jj, ii]),
                        "cell_mass_before_kg": float(mass[kk, jj, ii]),
                        "cell_capacity_kg": float(capacity[kk, jj, ii]),
                        "trial_cell_mass_kg": float(trial_mass[kk, jj, ii]),
                        "trial_excess_kg": float(trial_mass[kk, jj, ii] - capacity[kk, jj, ii]),
                        "div_mass_kg_s": float(div_mass[kk, jj, ii]),
                        "pressure_psi": float(pressure_psi[kk, jj, ii]),
                        "permeability_md": float(permeability_md[kk, jj, ii]),
                    }
                )
    return rows


def make_audited_capillary(
    *,
    r2: Any,
    retry_index: int,
    outer_dt_days: float,
    inversion_records: list[dict[str, Any]],
    stage_detail_rows: list[dict[str, Any]],
    failure_arrays: list[dict[str, np.ndarray]],
):
    def audited(
        transport_saturation: np.ndarray,
        permeability_md: np.ndarray,
        pressure_psi: np.ndarray,
        p_ref_pa: float,
        cell_pore_volume_m3: float,
        dt_seconds: float,
        cfl_number: float = 0.25,
    ) -> dict[str, Any]:
        S = np.asarray(transport_saturation, dtype=np.float64).copy()
        k_md = np.asarray(permeability_md, dtype=np.float64)
        p = np.asarray(pressure_psi, dtype=np.float64)

        if S.shape != EXPECTED_GRID or k_md.shape != EXPECTED_GRID or p.shape != EXPECTED_GRID:
            raise r2.GateError("capillary_grid_shape_mismatch")

        sg = np.clip(
            S - r2.BACKGROUND_SATURATION,
            0.0,
            r2.MAX_INCREMENTAL_CO2_SATURATION,
        )
        rho = r2.gas_density_from_state(S, p, p_ref_pa)
        mass = float(cell_pore_volume_m3) * rho * sg
        initial_total_mass = float(np.sum(mass))

        dx_m = 20.0 * r2.FT_TO_M
        dy_m = 20.0 * r2.FT_TO_M
        dz_m = 4.0 * r2.FT_TO_M
        ax_m2 = dy_m * dz_m
        ay_m2 = dx_m * dz_m
        az_m2 = dx_m * dy_m

        smax_field = np.full(
            EXPECTED_GRID,
            r2.INJECTED_BOUNDARY_SATURATION,
            dtype=np.float64,
        )
        rho_max = r2.gas_density_from_state(smax_field, p, p_ref_pa)
        capacity = (
            float(cell_pore_volume_m3)
            * rho_max
            * r2.MAX_INCREMENTAL_CO2_SATURATION
        )

        remaining = float(dt_seconds)
        substeps = 0
        max_local_mass_drift = 0.0

        while remaining > 1.0e-12 * max(float(dt_seconds), 1.0):
            Dx, Dy, Dz = r2._capillary_diffusion_coefficients_kji(S, k_md)

            tx = ax_m2 * 0.5 * (Dx[:, :, :-1] + Dx[:, :, 1:]) / dx_m
            ty = ay_m2 * 0.5 * (Dy[:, :-1, :] + Dy[:, 1:, :]) / dy_m
            tz = az_m2 * 0.5 * (Dz[:-1, :, :] + Dz[1:, :, :]) / dz_m

            conductance = np.zeros(EXPECTED_GRID, dtype=np.float64)
            conductance[:, :, :-1] += tx
            conductance[:, :, 1:] += tx
            conductance[:, :-1, :] += ty
            conductance[:, 1:, :] += ty
            conductance[:-1, :, :] += tz
            conductance[1:, :, :] += tz

            active = conductance > 1.0e-30
            if not np.any(active):
                break

            hstable = float(
                cfl_number
                * np.min(float(cell_pore_volume_m3) / conductance[active])
            )
            h = min(remaining, hstable)
            if not np.isfinite(h) or h <= 0.0:
                raise r2.GateError(f"capillary_invalid_substep:{h}")

            qx = -tx * (S[:, :, 1:] - S[:, :, :-1])
            qy = -ty * (S[:, 1:, :] - S[:, :-1, :])
            qz = -tz * (S[1:, :, :] - S[:-1, :, :])

            rho = r2.gas_density_from_state(S, p, p_ref_pa)
            mx = qx * np.where(qx >= 0.0, rho[:, :, :-1], rho[:, :, 1:])
            my = qy * np.where(qy >= 0.0, rho[:, :-1, :], rho[:, 1:, :])
            mz = qz * np.where(qz >= 0.0, rho[:-1, :, :], rho[1:, :, :])

            div_mass = np.zeros(EXPECTED_GRID, dtype=np.float64)
            div_mass[:, :, :-1] += mx
            div_mass[:, :, 1:] -= mx
            div_mass[:, :-1, :] += my
            div_mass[:, 1:, :] -= my
            div_mass[:-1, :, :] += mz
            div_mass[1:, :, :] -= mz

            before = float(np.sum(mass))
            trial_mass = mass - h * div_mass
            min_mass = float(np.min(trial_mass))
            mass_tol = max(1.0e-8, 1.0e-12 * max(before, 1.0))
            if min_mass < -mass_tol:
                raise r2.GateError(
                    f"capillary_negative_mass_after_flux_update:{min_mass}"
                )
            trial_mass = np.maximum(trial_mass, 0.0)

            excess = trial_mass - capacity
            max_excess = float(np.max(excess))
            cap_tol = max(
                1.0e-8,
                1.0e-12 * max(float(np.max(capacity)), 1.0),
            )

            if max_excess > cap_tol:
                flat = int(np.argmax(excess))
                k0, j0, i0 = np.unravel_index(flat, EXPECTED_GRID)

                margin = float(capacity[k0, j0, i0] - mass[k0, j0, i0])
                div0 = float(div_mass[k0, j0, i0])
                net_in = float(-div0)

                h_capacity = float("inf")
                if net_in > 0.0:
                    h_capacity = max(margin, 0.0) / net_in

                h_empty = float("inf")
                if div0 > 0.0:
                    h_empty = float(mass[k0, j0, i0]) / div0

                face_in = {
                    "i_minus_face_in_kg_s": float(mx[k0, j0, i0 - 1]) if i0 > 0 else 0.0,
                    "i_plus_face_in_kg_s": float(-mx[k0, j0, i0]) if i0 < EXPECTED_GRID[2] - 1 else 0.0,
                    "j_minus_face_in_kg_s": float(my[k0, j0 - 1, i0]) if j0 > 0 else 0.0,
                    "j_plus_face_in_kg_s": float(-my[k0, j0, i0]) if j0 < EXPECTED_GRID[1] - 1 else 0.0,
                    "k_minus_face_in_kg_s": float(mz[k0 - 1, j0, i0]) if k0 > 0 else 0.0,
                    "k_plus_face_in_kg_s": float(-mz[k0, j0, i0]) if k0 < EXPECTED_GRID[0] - 1 else 0.0,
                }

                record = {
                    "retry": int(retry_index),
                    "outer_trial_dt_days": float(outer_dt_days),
                    "outer_trial_dt_seconds": float(outer_dt_days * DAY_TO_S),
                    "capillary_requested_dt_seconds": float(dt_seconds),
                    "failed_capillary_substep_index_zero_based": int(substeps),
                    "failed_capillary_substep_number_one_based": int(substeps + 1),
                    "remaining_before_failed_substep_seconds": float(remaining),
                    "capillary_CFL_hstable_seconds": float(hstable),
                    "attempted_capillary_substep_h_seconds": float(h),
                    "receiver_capacity_h_seconds": float(h_capacity),
                    "donor_emptying_h_seconds_for_offending_cell": float(h_empty),
                    "attempted_to_capacity_h_ratio": (
                        float(h / h_capacity)
                        if np.isfinite(h_capacity) and h_capacity > 0.0
                        else float("inf")
                    ),
                    "k_zero_based": int(k0),
                    "j_zero_based": int(j0),
                    "i_zero_based": int(i0),
                    "k_one_based": int(k0 + 1),
                    "j_one_based": int(j0 + 1),
                    "i_one_based": int(i0 + 1),
                    "transport_saturation_before_failed_substep": float(S[k0, j0, i0]),
                    "incremental_gas_saturation_before_failed_substep": float(
                        np.clip(
                            S[k0, j0, i0] - r2.BACKGROUND_SATURATION,
                            0.0,
                            r2.MAX_INCREMENTAL_CO2_SATURATION,
                        )
                    ),
                    "pressure_psi": float(p[k0, j0, i0]),
                    "permeability_md": float(k_md[k0, j0, i0]),
                    "gas_density_before_kg_m3": float(rho[k0, j0, i0]),
                    "cell_mass_before_kg": float(mass[k0, j0, i0]),
                    "cell_capacity_kg": float(capacity[k0, j0, i0]),
                    "capacity_margin_before_kg": float(margin),
                    "net_capillary_mass_inflow_rate_kg_s": float(net_in),
                    "trial_cell_mass_kg": float(trial_mass[k0, j0, i0]),
                    "capacity_excess_kg": float(max_excess),
                    "capacity_tolerance_kg": float(cap_tol),
                    "cell_div_mass_kg_s": float(div0),
                    "conductance": float(conductance[k0, j0, i0]),
                    **face_in,
                    "failure_token": EXPECTED_FAILURE_TOKEN,
                }
                inversion_records.append(record)

                stage_detail_rows.extend(
                    build_stage_detail_rows(
                        retry=retry_index,
                        k0=k0,
                        j0=j0,
                        i0=i0,
                        S=S,
                        mass=mass,
                        capacity=capacity,
                        trial_mass=trial_mass,
                        div_mass=div_mass,
                        pressure_psi=p,
                        permeability_md=k_md,
                    )
                )

                failure_arrays.append(
                    {
                        "S_before": S.copy(),
                        "mass_before_kg": mass.copy(),
                        "capacity_kg": capacity.copy(),
                        "trial_mass_kg": trial_mass.copy(),
                        "div_mass_kg_s": div_mass.copy(),
                    }
                )

                raise r2.GateError(
                    f"capillary_cell_mass_capacity_exceeded:{max_excess}"
                )

            sg = r2._invert_incremental_sg_from_mass(
                trial_mass,
                p,
                p_ref_pa,
                cell_pore_volume_m3,
            )
            S = r2.BACKGROUND_SATURATION + sg
            mass = trial_mass

            after = float(np.sum(mass))
            max_local_mass_drift = max(
                max_local_mass_drift,
                abs(after - before),
            )
            remaining -= h
            substeps += 1

            if substeps > 200000:
                raise r2.GateError("capillary_subcycling_exceeded_200000_steps")

        final_total_mass_array = float(np.sum(mass))
        final_total_mass_state = r2.stored_co2_mass_kg(
            S,
            p,
            p_ref_pa,
            cell_pore_volume_m3,
        )

        return {
            "corrected": S,
            "substeps": int(substeps),
            "initial_mass_kg": initial_total_mass,
            "final_mass_array_kg": final_total_mass_array,
            "final_mass_state_kg": float(final_total_mass_state),
            "external_mass_change_kg": float(
                final_total_mass_array - initial_total_mass
            ),
            "state_inversion_residual_kg": float(
                final_total_mass_state - final_total_mass_array
            ),
            "max_substep_total_mass_drift_kg": float(max_local_mass_drift),
            "changed_mask": np.abs(S - transport_saturation) > 1.0e-14,
        }

    return audited


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 146)
        print(
            "PAD-Stream V16E-41-R1 — Long-Horizon Capillary "
            "Cell-Mass Capacity Failure Audit"
        )
        print("=" * 146)
        print("MODE           : DIAGNOSTIC ONLY")
        print("SOLVER REPAIR  : NONE")
        print("RESTART        : immutable V16E-40 canonical 60-day state")
        print("TARGET         : reproduce V16E-41 failure at step 1475")
        print("AUDIT          : all retries 0..8 + exact local capillary capacity mechanics")
        print("PROHIBITED     : state clipping, mass deletion/addition, plume rescaling, retry expansion")

        failed_stage = "provenance_binding"

        paths = {
            "R2": root / R2_RUNNER,
            "E36": root / E36_RUNNER,
            "E37A": root / E37A_RUNNER,
            "E37B": root / E37B_RUNNER,
            "E38": root / E38_RUNNER,
            "E40": root / E40_RUNNER,
            "E41": root / E41_RUNNER,
            "R1": root / R1_RUNNER,
            "R1R1": root / R1R1_RUNNER,
            "R1R2": root / R1R2_RUNNER,
            "SG7A": root / SG7A,
            "SG7D": root / SG7D,
            "PERM": root / SGSIM_PERM,
        }

        for key, p in paths.items():
            gate(f"source_exists_{key}", p.is_file(), p)

        for key, expected in [
            ("R2", R2_RUNNER_SHA256),
            ("E36", E36_RUNNER_SHA256),
            ("E37A", E37A_RUNNER_SHA256),
            ("E37B", E37B_RUNNER_SHA256),
            ("E38", E38_RUNNER_SHA256),
            ("E40", E40_RUNNER_SHA256),
            ("E41", E41_RUNNER_SHA256),
            ("R1", R1_RUNNER_SHA256),
            ("R1R1", R1R1_RUNNER_SHA256),
            ("R1R2", R1R2_RUNNER_SHA256),
        ]:
            actual = sha256_file(paths[key])
            gate(f"{key}_runner_SHA_exact", actual == expected, actual)

        r2 = load_module(paths["R2"], "pad_stream_v16e41r1_r2")
        e36 = load_module(paths["E36"], "pad_stream_v16e41r1_e36")
        e37a = load_module(paths["E37A"], "pad_stream_v16e41r1_e37a")
        e37b = load_module(paths["E37B"], "pad_stream_v16e41r1_e37b")
        e38 = load_module(paths["E38"], "pad_stream_v16e41r1_e38")
        e41 = load_module(paths["E41"], "pad_stream_v16e41r1_e41")

        e40_dir = drive / E40_REL
        e40_summary_path = e40_dir / E40_SUMMARY
        e40_closure_path = e40_dir / E40_CLOSURE
        e40_parent_path = e40_dir / E40_CANONICAL
        e36_cache_path = drive / E36_REL / E36_CACHE
        e37a_summary_path = drive / E37A_REL / E37A_SUMMARY
        e41_blocked_report_path = drive / E41_BLOCKED_REL / E41_BLOCKED_REPORT
        r1_blocked_report_path = drive / R1_BLOCKED_REL / R1_BLOCKED_REPORT
        r1r1_blocked_report_path = drive / R1R1_BLOCKED_REL / R1R1_BLOCKED_REPORT

        for p in [
            e40_summary_path,
            e40_closure_path,
            e40_parent_path,
            e36_cache_path,
            e37a_summary_path,
            e41_blocked_report_path,
            r1_blocked_report_path,
            r1r1_blocked_report_path,
        ]:
            gate(f"provenance_exists_{p.name}", p.is_file(), p)

        e40_summary = load_json(e40_summary_path)
        e40_closure = load_json(e40_closure_path)
        e37a_summary = load_json(e37a_summary_path)
        blocked_report = load_json(e41_blocked_report_path)
        r1_blocked_report = load_json(r1_blocked_report_path)
        r1r1_blocked_report = load_json(r1r1_blocked_report_path)

        gate(
            "E40_status_exact",
            e40_summary.get("status")
            == "POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT_VALIDATED",
            e40_summary.get("status"),
        )
        gate(
            "E40_closure_all_pass",
            e40_closure.get("all_runtime_gates_passed") is True,
        )
        gate(
            "E41_blocked_status_exact",
            blocked_report.get("status")
            == "PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION_BLOCKED",
            blocked_report.get("status"),
        )
        gate(
            "E41_failed_stage_exact",
            blocked_report.get("failed_stage")
            == "production_60_to_100d_rollout",
            blocked_report.get("failed_stage"),
        )
        blocked_exception = str(blocked_report.get("exception", ""))
        gate(
            "E41_failure_token_present",
            EXPECTED_FAILURE_TOKEN in blocked_exception,
            blocked_exception,
        )
        gate(
            "E41_target_step_1475_present",
            "1475" in blocked_exception,
            blocked_exception,
        )

        gate(
            "R1_blocked_status_exact",
            r1_blocked_report.get("status")
            == "LONG_HORIZON_CAPILLARY_CAPACITY_AUDIT_BLOCKED",
            r1_blocked_report.get("status"),
        )
        gate(
            "R1_failed_only_on_hardcoded_parent_time_gate",
            r1_blocked_report.get("failed_stage")
            == "reproduce_accepted_parent_1474"
            and "accepted_parent_time_expected"
            in str(r1_blocked_report.get("exception", "")),
            (
                f"{r1_blocked_report.get('failed_stage')}:"
                f"{r1_blocked_report.get('exception')}"
            ),
        )

        gate(
            "R1R1_blocked_status_exact",
            r1r1_blocked_report.get("status")
            == "FORMAL_E41_TRAJECTORY_BOUND_CAPILLARY_CAPACITY_AUDIT_BLOCKED",
            r1r1_blocked_report.get("status"),
        )
        gate(
            "R1R1_reached_retry_audit_and_failed_only_on_capture_count",
            r1r1_blocked_report.get("failed_stage")
            == "audit_step_1475_all_retries"
            and "all_nine_retry_failures_captured"
            in str(r1r1_blocked_report.get("exception", "")),
            (
                f"{r1r1_blocked_report.get('failed_stage')}:"
                f"{r1r1_blocked_report.get('exception')}"
            ),
        )

        formal_trials = [
            row
            for row in blocked_report.get("trial_failures", [])
            if int(row.get("target_step", -1)) == EXPECTED_TARGET_STEP
        ]
        formal_trials = sorted(
            formal_trials,
            key=lambda row: int(row.get("retry", -1)),
        )
        gate(
            "formal_E41_step1475_has_nine_retry_records",
            len(formal_trials) == EXPECTED_RETRY_COUNT
            and [int(r.get("retry", -1)) for r in formal_trials]
            == list(range(EXPECTED_RETRY_COUNT)),
            str(formal_trials),
        )

        formal_parent_times = {
            float(row["parent_time_days"])
            for row in formal_trials
        }
        gate(
            "formal_E41_step1475_single_parent_time",
            len(formal_parent_times) == 1,
            str(sorted(formal_parent_times)),
        )
        formal_parent_time_days = float(next(iter(formal_parent_times)))
        formal_retry_dt_days = [
            float(row["trial_dt_days"])
            for row in formal_trials
        ]
        gate(
            "formal_E41_retry_schedule_positive_strictly_decreasing",
            all(x > 0.0 for x in formal_retry_dt_days)
            and all(
                formal_retry_dt_days[i + 1] < formal_retry_dt_days[i]
                for i in range(len(formal_retry_dt_days) - 1)
            ),
            str(formal_retry_dt_days),
        )

        e40_parent_sha = sha256_file(e40_parent_path)
        e36_cache_sha = sha256_file(e36_cache_path)
        blocked_report_sha = sha256_file(e41_blocked_report_path)
        r1_blocked_report_sha = sha256_file(r1_blocked_report_path)
        r1r1_blocked_report_sha = sha256_file(r1r1_blocked_report_path)

        gate(
            "E40_parent_SHA_matches_closure",
            e40_parent_sha == e40_closure.get("checkpoint_state_sha256"),
            e40_parent_sha,
        )
        gate(
            "E36_cache_SHA_matches_E40_closure",
            e36_cache_sha == e40_closure.get("E36_certified_cache_sha256"),
            e36_cache_sha,
        )

        parent = load_npz(e40_parent_path)
        cache = load_npz(e36_cache_path)

        gate(
            "restart_step_exact",
            int_scalar(parent["accepted_step_index"]) == EXPECTED_E40_STEP,
            int_scalar(parent["accepted_step_index"]),
        )
        gate(
            "restart_time_exact",
            scalar(parent["physical_time_days"]) == EXPECTED_E40_TIME_DAYS,
            scalar(parent["physical_time_days"]),
        )
        gate(
            "restart_breakthrough_history_present",
            bool_scalar(parent["breakthrough_reached"]),
        )

        failed_stage = "physics_setup"

        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E41R1_") as td:
            tmp = Path(td)
            shutil.copy2(paths["SG7A"], tmp / SG7A)
            shutil.copy2(paths["SG7D"], tmp / SG7D)
            sg7a = load_module(tmp / SG7A, "pad_stream_v16e41r1_sg7a")
            sg7d = load_module(tmp / SG7D, "pad_stream_v16e41r1_sg7d")

            pressure_psi = np.asarray(cache["accepted_pressure_psi"], dtype=np.float64)
            xyz_m = np.asarray(cache["streamline_xyz_m"], dtype=np.float64)
            tau_s = np.asarray(cache["streamline_tof_s"], dtype=np.float64)
            tau_end_s = np.asarray(cache["tau_end_s"], dtype=np.float64)
            weights_m3_s = np.asarray(cache["streamline_weights_m3_s"], dtype=np.float64)
            labels = np.asarray(cache["producer_labels"]).astype(str)
            xi_faces = np.asarray(cache["xi"], dtype=np.float64)

            nstream = len(tau_end_s)
            nfaces = len(xi_faces)
            ncv = nfaces - 1

            weights_m3_day = weights_m3_s * DAY_TO_S
            tof_days = tau_s / DAY_TO_S
            operator = sg7d.build_subsegment_operator(
                xyz_m,
                tof_days,
                weights_m3_day,
            )
            p_ref_gas_pa = scalar(parent["co2_density_reference_pressure_pa"])
            geometry = e37a.build_control_volume_geometry(
                r2,
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

            dxi = float(xi_faces[1] - xi_faces[0])
            sat_scan = np.linspace(
                float(sg7a.S_INITIAL),
                float(sg7a.S_INJECTED),
                4001,
            )
            max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan)))))
            u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
            max_wave_speed = float(np.max(u_face) * max_df)
            dtD_cfl = float(
                sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS)
            )
            fastest_tau_days = float(np.min(tau_end_s / DAY_TO_S))
            nominal_dt_days = float(dtD_cfl * fastest_tau_days)

            gate(
                "nominal_dt_matches_E37A",
                abs(nominal_dt_days - float(e37a_summary["nominal_dt_days"]))
                <= 1.0e-15,
                nominal_dt_days,
            )

            dx_m = 20.0 * FT_TO_M
            dy_m = 20.0 * FT_TO_M
            dz_m = 4.0 * FT_TO_M
            cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m

            permeability_md = np.loadtxt(
                paths["PERM"],
                skiprows=1,
                dtype=np.float64,
            ).reshape(EXPECTED_GRID, order="C")
            gate(
                "permeability_shape_exact",
                permeability_md.shape == EXPECTED_GRID,
                permeability_md.shape,
            )

            failed_stage = "reproduce_accepted_parent_1474"

            current = {k: np.asarray(v).copy() for k, v in parent.items()}
            pre_failure_rejections: list[dict[str, Any]] = []

            while int_scalar(current["accepted_step_index"]) < EXPECTED_PARENT_STEP:
                current_time = scalar(current["physical_time_days"])
                target_step = int_scalar(current["accepted_step_index"]) + 1
                nominal_trial_dt = nominal_dt_days
                accepted = False
                last_reason = ""

                for retry in range(MAX_TRIAL_RETRIES + 1):
                    dt_days = nominal_trial_dt * (RETRY_FACTOR ** retry)

                    try:
                        result = e38.evolve_from_parent(
                            parent=current,
                            dt_days=dt_days,
                            r2=r2,
                            e36=e36,
                            e37a=e37a,
                            e37b=e37b,
                            sg7a=sg7a,
                            pressure_psi=pressure_psi,
                            p_ref_gas_pa=p_ref_gas_pa,
                            geometry=geometry,
                            face_pressure_psi=face_pressure_psi,
                            weights_m3_day=weights_m3_day,
                            xi_faces=xi_faces,
                            labels=labels,
                            permeability_md=permeability_md,
                            cell_pore_volume_m3=cell_pore_volume_m3,
                            nstream=nstream,
                            nfaces=nfaces,
                            ncv=ncv,
                        )

                        child = e41.apply_e41_state_semantics(
                            result["child"],
                            current,
                            canonical_breakthrough_time_days=scalar(
                                parent["breakthrough_time_days"]
                            ),
                            observation_reached=False,
                        )
                        child["current_producer_co2_gas_cut"] = np.asarray(
                            result["child_cut"], dtype=np.float64
                        )
                        child["last_CV_transport_mass_residual_kg"] = np.asarray(
                            result["transport_residual_kg"], dtype=np.float64
                        )
                        child["last_CV_to_grid_transfer_residual_kg"] = np.asarray(
                            result["transfer_residual_kg"], dtype=np.float64
                        )
                        child["last_grid_mapback_ledger_residual_kg"] = np.asarray(
                            result["mapback_ledger_residual_kg"], dtype=np.float64
                        )
                        child["last_grid_to_CV_sampling_closure_kg"] = np.asarray(
                            result["post_sample_closure_kg"], dtype=np.float64
                        )

                        current = child
                        accepted = True
                        break

                    except (e37a.TrialReject, r2.GateError) as exc:
                        last_reason = repr(exc)
                        pre_failure_rejections.append(
                            {
                                "target_step": target_step,
                                "parent_time_days": current_time,
                                "retry": retry,
                                "trial_dt_days": dt_days,
                                "reason": last_reason,
                            }
                        )
                        if retry >= MAX_TRIAL_RETRIES:
                            raise GateError(
                                "unexpected_failure_before_step_1475:"
                                f"{target_step}:{last_reason}"
                            )

                if not accepted:
                    raise GateError(
                        f"accepted_parent_reproduction_failed:{target_step}:{last_reason}"
                    )

            accepted_parent = current
            accepted_parent_time = scalar(accepted_parent["physical_time_days"])

            gate(
                "accepted_parent_step_1474_reproduced",
                int_scalar(accepted_parent["accepted_step_index"])
                == EXPECTED_PARENT_STEP,
                int_scalar(accepted_parent["accepted_step_index"]),
            )
            gate(
                "accepted_parent_time_matches_formal_E41_blocked_trajectory",
                abs(accepted_parent_time - formal_parent_time_days)
                <= 1.0e-12,
                f"{accepted_parent_time}:{formal_parent_time_days}",
            )

            accepted_parent_bytes = deterministic_npz_bytes(accepted_parent)
            accepted_parent_sha = hashlib.sha256(accepted_parent_bytes).hexdigest()

            failed_stage = "audit_step_1475_all_retries"

            original_inversion = r2._invert_incremental_sg_from_mass
            inversion_records: list[dict[str, Any]] = []
            failure_arrays: list[dict[str, np.ndarray]] = []
            retry_exceptions: list[str] = []

            def make_inversion_auditor(
                retry_index: int,
                outer_dt_days: float,
            ):
                def audited_inversion(
                    target_mass_kg: np.ndarray,
                    pressure_psi_local: np.ndarray,
                    p_ref_pa_local: float,
                    cell_pore_volume_m3_local: float,
                ) -> np.ndarray:
                    target = np.asarray(target_mass_kg, dtype=np.float64)
                    p_local = np.asarray(pressure_psi_local, dtype=np.float64)

                    caller = inspect.currentframe().f_back.f_code.co_name
                    stack_names = [
                        frame.function
                        for frame in inspect.stack(context=0)[1:8]
                    ]

                    if caller == "map_control_volume_increment_to_grid":
                        stage = "CV_TO_GRID_MAPBACK"
                    elif caller == "conservative_capillary_mass_redistribution":
                        stage = "CAPILLARY_REDISTRIBUTION"
                    else:
                        stage = f"OTHER:{caller}"

                    smax_field = np.full(
                        EXPECTED_GRID,
                        r2.INJECTED_BOUNDARY_SATURATION,
                        dtype=np.float64,
                    )
                    rho_max = r2.gas_density_from_state(
                        smax_field,
                        p_local,
                        p_ref_pa_local,
                    )
                    capacity = (
                        float(cell_pore_volume_m3_local)
                        * rho_max
                        * r2.MAX_INCREMENTAL_CO2_SATURATION
                    )
                    excess = target - capacity
                    max_excess = float(np.max(excess))
                    cap_tol = max(
                        1.0e-8,
                        1.0e-12
                        * max(float(np.max(capacity)), 1.0),
                    )

                    if max_excess > cap_tol:
                        flat = int(np.argmax(excess))
                        k0, j0, i0 = np.unravel_index(flat, EXPECTED_GRID)

                        inversion_records.append(
                            {
                                "retry": int(retry_index),
                                "outer_trial_dt_days": float(outer_dt_days),
                                "outer_trial_dt_seconds": float(
                                    outer_dt_days * DAY_TO_S
                                ),
                                "failure_stage": stage,
                                "direct_caller": caller,
                                "call_stack": " > ".join(stack_names),
                                "k_zero_based": int(k0),
                                "j_zero_based": int(j0),
                                "i_zero_based": int(i0),
                                "k_one_based": int(k0 + 1),
                                "j_one_based": int(j0 + 1),
                                "i_one_based": int(i0 + 1),
                                "target_cell_mass_kg": float(
                                    target[k0, j0, i0]
                                ),
                                "cell_capacity_kg": float(
                                    capacity[k0, j0, i0]
                                ),
                                "capacity_excess_kg": float(max_excess),
                                "capacity_tolerance_kg": float(cap_tol),
                                "pressure_psi": float(
                                    p_local[k0, j0, i0]
                                ),
                                "rho_at_saturation_ceiling_kg_m3": float(
                                    rho_max[k0, j0, i0]
                                ),
                                "failure_token": EXPECTED_FAILURE_TOKEN,
                            }
                        )

                        failure_arrays.append(
                            {
                                "target_mass_kg": target.copy(),
                                "capacity_kg": capacity.copy(),
                                "excess_kg": excess.copy(),
                            }
                        )

                    # Preserve exact production behavior and exact exception.
                    return original_inversion(
                        target_mass_kg,
                        pressure_psi_local,
                        p_ref_pa_local,
                        cell_pore_volume_m3_local,
                    )

                return audited_inversion

            for retry in range(MAX_TRIAL_RETRIES + 1):
                dt_days = formal_retry_dt_days[retry]
                before_count = len(inversion_records)
                r2._invert_incremental_sg_from_mass = make_inversion_auditor(
                    retry,
                    dt_days,
                )

                try:
                    _ = e38.evolve_from_parent(
                        parent=accepted_parent,
                        dt_days=dt_days,
                        r2=r2,
                        e36=e36,
                        e37a=e37a,
                        e37b=e37b,
                        sg7a=sg7a,
                        pressure_psi=pressure_psi,
                        p_ref_gas_pa=p_ref_gas_pa,
                        geometry=geometry,
                        face_pressure_psi=face_pressure_psi,
                        weights_m3_day=weights_m3_day,
                        xi_faces=xi_faces,
                        labels=labels,
                        permeability_md=permeability_md,
                        cell_pore_volume_m3=cell_pore_volume_m3,
                        nstream=nstream,
                        nfaces=nfaces,
                        ncv=ncv,
                    )
                    raise GateError(
                        f"step_1475_retry_unexpectedly_accepted:{retry}"
                    )
                except r2.GateError as exc:
                    retry_exceptions.append(repr(exc))
                    if EXPECTED_FAILURE_TOKEN not in str(exc):
                        raise GateError(
                            f"unexpected_retry_failure_type:{retry}:{repr(exc)}"
                        )
                finally:
                    r2._invert_incremental_sg_from_mass = original_inversion

                after_count = len(inversion_records)
                if after_count - before_count != 1:
                    raise GateError(
                        "retry_did_not_produce_exactly_one_shared_inversion_"
                        f"capacity_record:{retry}:{before_count}:{after_count}"
                    )

            gate(
                "all_nine_retry_failures_captured_at_shared_inversion",
                len(inversion_records) == EXPECTED_RETRY_COUNT
                and len(failure_arrays) == EXPECTED_RETRY_COUNT,
                f"{len(inversion_records)}:{len(failure_arrays)}",
            )
            gate(
                "all_retry_failures_are_capacity_gate",
                all(EXPECTED_FAILURE_TOKEN in x for x in retry_exceptions),
                str(retry_exceptions),
            )

            last_excess = float(inversion_records[-1]["capacity_excess_kg"])
            gate(
                "final_retry_excess_matches_formal_E41_failure",
                abs(last_excess - EXPECTED_LAST_RETRY_EXCESS_KG) <= 1.0e-12,
                f"{last_excess}:{EXPECTED_LAST_RETRY_EXCESS_KG}",
            )

            offender_cells = {
                (
                    int(r["k_zero_based"]),
                    int(r["j_zero_based"]),
                    int(r["i_zero_based"]),
                )
                for r in inversion_records
            }
            same_offender_all_retries = len(offender_cells) == 1

            stage_counts: dict[str, int] = {}
            for rec in inversion_records:
                stage = str(rec["failure_stage"])
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

            gate(
                "all_failures_at_known_production_stage",
                all(
                    rec["failure_stage"]
                    in {
                        "CV_TO_GRID_MAPBACK",
                        "CAPILLARY_REDISTRIBUTION",
                    }
                    for rec in inversion_records
                ),
                str(stage_counts),
            )

            retry_dt_seconds = np.asarray(
                [
                    float(r["outer_trial_dt_seconds"])
                    for r in inversion_records
                ],
                dtype=np.float64,
            )
            excesses = np.asarray(
                [
                    float(r["capacity_excess_kg"])
                    for r in inversion_records
                ],
                dtype=np.float64,
            )

            decreasing_excess = bool(
                np.all(np.diff(excesses) <= 1.0e-15)
            )

            positive = retry_dt_seconds > 0.0
            A = np.column_stack(
                [
                    retry_dt_seconds[positive],
                    np.ones(np.sum(positive)),
                ]
            )
            slope, intercept = np.linalg.lstsq(
                A,
                excesses[positive],
                rcond=None,
            )[0]
            fitted = slope * retry_dt_seconds + intercept
            ss_res = float(np.sum((excesses - fitted) ** 2))
            ss_tot = float(np.sum((excesses - np.mean(excesses)) ** 2))
            r2_fit = (
                1.0 - ss_res / ss_tot
                if ss_tot > 0.0
                else float("nan")
            )

            mapback_failure_count = int(
                stage_counts.get("CV_TO_GRID_MAPBACK", 0)
            )
            capillary_failure_count = int(
                stage_counts.get("CAPILLARY_REDISTRIBUTION", 0)
            )

            if mapback_failure_count > 0 and capillary_failure_count > 0:
                diagnosis = "MIXED_MAPBACK_AND_CAPILLARY_CAPACITY_FAILURES"
                repair_direction = (
                    "Design stage-specific conservative admissibility bounds "
                    "for both CV-to-grid map-back and capillary redistribution."
                )
            elif mapback_failure_count == EXPECTED_RETRY_COUNT:
                diagnosis = "MAPBACK_CAPACITY_FAILURE_ONLY"
                repair_direction = (
                    "Repair conservative CV-to-grid increment deposition / "
                    "admissibility before changing the capillary solver."
                )
            elif capillary_failure_count == EXPECTED_RETRY_COUNT:
                diagnosis = "CAPILLARY_REDISTRIBUTION_CAPACITY_FAILURE_ONLY"
                repair_direction = (
                    "Add receiver-capacity/donor-emptying substep bounds to "
                    "the conservative capillary redistribution."
                )
            else:
                diagnosis = "UNEXPECTED_STAGE_CLASSIFICATION"
                repair_direction = (
                    "Do not implement a production repair until stage "
                    "classification is reconciled."
                )

            arrays_npz: dict[str, Any] = {
                "retry": np.arange(EXPECTED_RETRY_COUNT, dtype=np.int64),
                "outer_trial_dt_days": np.asarray(
                    [r["outer_trial_dt_days"] for r in inversion_records],
                    dtype=np.float64,
                ),
                "outer_trial_dt_seconds": retry_dt_seconds,
                "capacity_excess_kg": excesses,
                "failure_stage": np.asarray(
                    [r["failure_stage"] for r in inversion_records],
                    dtype="U32",
                ),
                "accepted_parent_transport_saturation": np.asarray(
                    accepted_parent["transport_saturation"],
                    dtype=np.float64,
                ),
            }

            for idx, arrs in enumerate(failure_arrays):
                for key, value in arrs.items():
                    arrays_npz[f"retry{idx}_{key}"] = value

            failure_arrays_bytes = deterministic_npz_bytes(arrays_npz)

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "diagnostic_only": True,
                "solver_repair_performed": False,
                "canonical_100d_state_created": False,
                "legacy_regression_started": False,
                "source_E41_blocked_report_sha256": blocked_report_sha,
                "source_blocked_R1_report_sha256": r1_blocked_report_sha,
                "source_blocked_R1R1_report_sha256": r1r1_blocked_report_sha,
                "formal_E41_parent_time_days": formal_parent_time_days,
                "formal_E41_retry_dt_days": formal_retry_dt_days,
                "trajectory_binding_repair_only": True,
                "provenance_filename_binding_repair_only": True,
                "provenance_filename_binding_repair_only": True,
                "source_E40_parent_sha256": e40_parent_sha,
                "source_E36_cache_sha256": e36_cache_sha,
                "accepted_parent_step_index": EXPECTED_PARENT_STEP,
                "accepted_parent_time_days": accepted_parent_time,
                "accepted_parent_state_sha256": accepted_parent_sha,
                "pre_failure_rejected_trials": len(pre_failure_rejections),
                "failed_target_step": EXPECTED_TARGET_STEP,
                "retry_count_audited": len(inversion_records),
                "same_offending_cell_all_retries": same_offender_all_retries,
                "offending_cells_zero_based": [list(x) for x in sorted(offender_cells)],
                "capacity_excess_strictly_or_weakly_decreasing_with_outer_retry": decreasing_excess,
                "shared_inversion_capacity_failure_captured_each_retry": True,
                "failure_stage_counts": stage_counts,
                "mapback_failure_count": mapback_failure_count,
                "capillary_failure_count": capillary_failure_count,
                "stage_resolved_diagnosis": diagnosis,
                "last_retry_capacity_excess_kg": last_excess,
                "formal_E41_last_retry_capacity_excess_kg": EXPECTED_LAST_RETRY_EXCESS_KG,
                "outer_dt_vs_excess_linear_fit_slope_kg_per_s": float(slope),
                "outer_dt_vs_excess_linear_fit_intercept_kg": float(intercept),
                "outer_dt_vs_excess_linear_fit_R2": float(r2_fit),
                "capacity_limiter_diagnosis": diagnosis,
                "recommended_R2_repair_direction": repair_direction,
            }

            repair_contract = {
                "milestone": NEXT,
                "status": "DESIGN_INPUT_FROM_R1_R2",
                "stage_resolved_diagnosis": diagnosis,
                "failure_stage_counts": stage_counts,
                "mapback_failure_count": mapback_failure_count,
                "capillary_failure_count": capillary_failure_count,
                "recommended_repair_direction": repair_direction,
                "must_preserve": [
                    "exact fixed-rate source mass",
                    "component-mass conservation",
                    "zero external capillary source",
                    "0 <= incremental gas saturation <= 0.60",
                    "nonlinear EOS/capillary inversion",
                    "accepted-parent rollback on rejected outer trial",
                ],
                "must_not_do": [
                    "increase saturation ceiling",
                    "clip or delete over-capacity mass",
                    "add artificial source or sink",
                    "global plume rescale",
                    "weaken the capacity gate",
                    "declare blocked E41 state accepted",
                ],
                "implementation_not_authorized_until_this_audit_passes": False,
                "R1_R2_authorizes_stage_appropriate_R2_design": True,
            }

            files = {
                "PAD_Stream_V16E41R1R2R1_Summary.json": json_bytes(summary),
                "V16E41R1R2R1_Shared_Inversion_Capacity_Audit.csv": csv_bytes(inversion_records),
                "V16E41R1R2R1_PreFailure_Rejection_Audit.csv": csv_bytes(pre_failure_rejections),
                "V16E41R1R2R1_Failure_State_Arrays.npz": failure_arrays_bytes,
                "V16E41R2_Repair_Design_Input.json": json_bytes(repair_contract),
                "V16E41R1R2R1_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            }

            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_audit_gates_passed": all(v["passed"] for v in gates.values()),
                "gate_count": len(gates),
                "solver_modified": False,
                "E40_parent_modified": sha256_file(e40_parent_path) != e40_parent_sha,
                "E36_cache_modified": sha256_file(e36_cache_path) != e36_cache_sha,
                "E41_blocked_report_modified": sha256_file(e41_blocked_report_path)
                != blocked_report_sha,
                "R1_blocked_report_modified": sha256_file(r1_blocked_report_path)
                != r1_blocked_report_sha,
                "R1R1_blocked_report_modified": sha256_file(r1r1_blocked_report_path)
                != r1r1_blocked_report_sha,
                "trajectory_binding_repair_only": True,
                "accepted_parent_step_index": EXPECTED_PARENT_STEP,
                "failed_target_step": EXPECTED_TARGET_STEP,
                "retry_failures_reproduced": EXPECTED_RETRY_COUNT,
                "last_retry_excess_match": abs(
                    last_excess - EXPECTED_LAST_RETRY_EXCESS_KG
                )
                <= 1.0e-12,
                "shared_inversion_capacity_failure_captured_each_retry": True,
                "failure_stage_counts": stage_counts,
                "mapback_failure_count": mapback_failure_count,
                "capillary_failure_count": capillary_failure_count,
                "stage_resolved_diagnosis": diagnosis,
                "same_offending_cell_all_retries": same_offender_all_retries,
                "next_milestone": NEXT,
            }
            files["V16E41R1R2R1_Final_Closure.json"] = json_bytes(closure)

            immutable_publish(out, files)

            manifest_rows = []
            for p in sorted(out.iterdir()):
                if p.is_file() and p.name != "V16E41R1R2R1_Artifact_Manifest.csv":
                    manifest_rows.append(
                        {
                            "file": p.name,
                            "sha256": sha256_file(p),
                            "bytes": p.stat().st_size,
                        }
                    )

            immutable_publish(
                out,
                {
                    "V16E41R1R2R1_Artifact_Manifest.csv": csv_bytes(manifest_rows)
                },
            )

        print("\n" + "=" * 146)
        print("PAD-Stream V16E-41-R1-R2-R1 SHARED-INVERSION STAGE-RESOLVED CAPACITY AUDIT: PASS")
        print("=" * 146)
        print(f"{'Accepted parent step/time':76}: {EXPECTED_PARENT_STEP} / {accepted_parent_time:.12g} d")
        print(f"{'Failed target step':76}: {EXPECTED_TARGET_STEP}")
        print(f"{'Retries reproduced':76}: {len(inversion_records)}")
        print(f"{'Same offending cell all retries':76}: {same_offender_all_retries}")
        print(f"{'Offending cell(s) zero-based':76}: {sorted(offender_cells)}")
        print(f"{'Last retry capacity excess':76}: {last_excess:.12e} kg")
        print(f"{'Failure stage counts':76}: {stage_counts}")
        print(f"{'Stage-resolved diagnosis':76}: {diagnosis}")
        print(f"{'Formal E41 last retry excess':76}: {EXPECTED_LAST_RETRY_EXCESS_KG:.12e} kg")
        print(f"{'Outer-dt/excess linear fit R^2':76}: {r2_fit:.12e}")
        print(f"{'Solver repair performed':76}: NO")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "SHARED_INVERSION_STAGE_RESOLVED_CAPACITY_AUDIT_PROVENANCE_REPAIR_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
            "solver_repair_performed": False,
            "next_action": (
                "Audit why R1 could not reproduce the exact E41 capacity failure. "
                "Do not modify the capillary solver until the failure is reproduced."
            ),
        }
        data = json_bytes(report)
        p = blocked / "V16E41R1R2R1_Blocked_Audit.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E41R1R2R1_Blocked_Audit_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 146)
        print("PAD-Stream V16E-41-R1-R2-R1 SHARED-INVERSION STAGE-RESOLVED CAPACITY AUDIT: BLOCKED")
        print("=" * 146)
        print("Stage :", failed_stage)
        print("Reason:", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path)
    p.add_argument("--drive-root", type=Path)
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    if args.project_root is None or args.drive_root is None:
        raise SystemExit(
            "--project-root and --drive-root are required unless --self-test is used"
        )

    raise SystemExit(main(args.project_root, args.drive_root))
