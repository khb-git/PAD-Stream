from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import shutil
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np


MILESTONE = "V16E-37A"
STATUS = "CONTROL_VOLUME_ALIGNED_CONSERVATIVE_TRANSFER_VALIDATED"
NEXT = "V16E-37B - Extended SGSim Runtime Rollout / First Fixed Observation Checkpoint"

EXPECTED_GRID = (15, 50, 50)  # (k, j, i)
BACKGROUND_SATURATION = 0.20
INJECTED_BOUNDARY_SATURATION = 0.80
MAX_INCREMENTAL_CO2_SATURATION = 0.60
BREAKTHROUGH_GAS_CUT = 1.0e-4
DAY_TO_S = 86400.0
PSI_TO_PA = 6894.757293168
FT_TO_M = 0.3048
CO2_RHO_REF_KG_M3 = 700.0
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0
TARGET_FINAL_STEP_INDEX = 4
EXPECTED_STREAMLINES = 1078
EXPECTED_FACES = 201
EXPECTED_CVS = 200

R2_RUNNER = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_"
    "First_Controlled_Transition.py"
)
R2_RUNNER_SHA256 = "3a1bf71ef601308e2fc18168bf2b9fc7c3dc9b0ff98e3735de1d4fa6ee624ab6"
R2_REL = Path(
    "provenance/hybrid_dp/"
    "V16E35_R2_FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_CONSERVATIVE_CAPILLARY_SPLIT"
)
R2_SUMMARY = "PAD_Stream_V16E35_R2_Summary.json"
R2_CLOSURE = "V16E35_R2_Final_Closure.json"
R2_STATE = "V16E35_R2_First_Accepted_SGSim_Runtime_State_Step0001.npz"
R2_EXPECTED_STATUS = "FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_ACCEPTED_R2"

E36_RUNNER = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_RUNNER_SHA256 = "747a4f6ee4a5458624311fe2226773e0db778cc40a0460adfcbc454be22a3a0c"
E36_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
E36_SUMMARY = "PAD_Stream_V16E36_Summary.json"
E36_CLOSURE = "V16E36_Final_Closure.json"
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"
E36_STEP_AUDIT = "V16E36_Rollout_Step_Audit.csv"
E36_REJECTION_AUDIT = "V16E36_Trial_Rejection_Audit.csv"
E36_EXPECTED_STATUS = "SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATED"

V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
V16_FROZEN_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37A_CONTROL_VOLUME_ALIGNED_CONSERVATIVE_STREAMLINE_GRID_TRANSFER"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37A_BLOCKED_CONTROL_VOLUME_ALIGNED_CONSERVATIVE_STREAMLINE_GRID_TRANSFER"
)


class GateError(RuntimeError):
    pass


class TrialReject(RuntimeError):
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
                f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = out / name
        if path.exists():
            if path.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            path.write_bytes(data)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {name: z[name].copy() for name in z.files}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def max_abs(values: list[float]) -> float:
    return max([abs(float(v)) for v in values] + [0.0])


def build_control_volume_geometry(
    r2: Any,
    operator: dict[str, np.ndarray],
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    n_streamlines: int,
    n_cv: int,
) -> dict[str, np.ndarray]:
    streamline = np.asarray(operator["streamline"], dtype=np.int64)
    node = np.asarray(operator["node"], dtype=np.int64)
    pv = np.asarray(operator["pv_m3"], dtype=np.float64)
    flat_cell = np.asarray(operator["flat_cell"], dtype=np.int64)
    kk = np.asarray(operator["k"], dtype=np.int64)
    jj = np.asarray(operator["j"], dtype=np.int64)
    ii = np.asarray(operator["i"], dtype=np.int64)

    if np.any(node < 0) or np.any(node >= n_cv):
        raise GateError(
            f"SG7D_operator_node_not_transport_CV_interval:"
            f"{int(np.min(node))}:{int(np.max(node))}:{n_cv}"
        )

    cv_id = streamline * n_cv + node
    n_total_cv = n_streamlines * n_cv

    cv_pv = np.bincount(
        cv_id, weights=pv, minlength=n_total_cv
    ).reshape(n_streamlines, n_cv)
    if np.any(cv_pv <= 0.0):
        raise GateError(
            f"nonpositive_control_volume_pore_volume:"
            f"{int(np.sum(cv_pv <= 0.0))}"
        )

    pseg_psi = np.asarray(pressure_psi, dtype=np.float64)[kk, jj, ii]
    exponent = np.clip(
        float(r2.CO2_COMPRESSIBILITY_1_PA)
        * (pseg_psi * PSI_TO_PA - float(p_ref_gas_pa)),
        -50.0,
        50.0,
    )
    pressure_density_factor = CO2_RHO_REF_KG_M3 * np.exp(exponent)

    # For a CV-uniform incremental gas saturation sg:
    #
    #   M_cv(sg) =
    #       [sum_sub PV_sub * rho_ref exp(c(p_w-p_ref))]
    #       * exp(c Pc(sg)) * sg
    #
    # so this coefficient lets us invert the exact subsegment component
    # inventory without replacing pressure by an averaged cell pressure.
    cv_pressure_mass_coeff = np.bincount(
        cv_id,
        weights=pv * pressure_density_factor,
        minlength=n_total_cv,
    ).reshape(n_streamlines, n_cv)

    return {
        "cv_id": cv_id,
        "cv_pv_m3": cv_pv,
        "cv_pressure_mass_coeff": cv_pressure_mass_coeff,
        "flat_cell": flat_cell,
        "pv_m3": pv,
        "pseg_psi": pseg_psi,
        "k": kk,
        "j": jj,
        "i": ii,
    }


def cv_mass_from_saturation(
    r2: Any,
    saturation: np.ndarray,
    cv_pressure_mass_coeff: np.ndarray,
) -> np.ndarray:
    sat = np.asarray(saturation, dtype=np.float64)
    coeff = np.asarray(cv_pressure_mass_coeff, dtype=np.float64)
    sg = np.clip(
        sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    pc = np.asarray(
        r2.capillary_pressure_from_incremental_sg(sg),
        dtype=np.float64,
    )
    factor = np.exp(
        np.clip(float(r2.CO2_COMPRESSIBILITY_1_PA) * pc, -50.0, 50.0)
    )
    return coeff * factor * sg


def invert_cv_mass_to_saturation(
    r2: Any,
    target_mass_kg: np.ndarray,
    cv_pressure_mass_coeff: np.ndarray,
) -> np.ndarray:
    target = np.asarray(target_mass_kg, dtype=np.float64)
    coeff = np.asarray(cv_pressure_mass_coeff, dtype=np.float64)
    if target.shape != coeff.shape:
        raise GateError(
            f"cv_mass_shape_mismatch:{target.shape}:{coeff.shape}"
        )
    tol = max(
        1.0e-9,
        1.0e-12 * max(float(np.max(np.abs(target))), 1.0),
    )
    min_mass = float(np.min(target))
    if min_mass < -tol:
        raise TrialReject(f"negative_control_volume_component_mass:{min_mass}")
    target = np.maximum(target, 0.0)

    smax = np.full_like(target, INJECTED_BOUNDARY_SATURATION)
    capacity = cv_mass_from_saturation(r2, smax, coeff)
    max_excess = float(np.max(target - capacity))
    if max_excess > tol:
        raise TrialReject(
            f"control_volume_component_capacity_exceeded:{max_excess}"
        )

    lower = np.zeros_like(target)
    upper = np.full_like(target, MAX_INCREMENTAL_CO2_SATURATION)
    for _ in range(72):
        mid = 0.5 * (lower + upper)
        sat_mid = BACKGROUND_SATURATION + mid
        m_mid = cv_mass_from_saturation(r2, sat_mid, coeff)
        below = m_mid < target
        lower = np.where(below, mid, lower)
        upper = np.where(below, upper, mid)

    sg = 0.5 * (lower + upper)
    sg[target <= 1.0e-18] = 0.0
    sat = BACKGROUND_SATURATION + sg

    reconstructed = cv_mass_from_saturation(r2, sat, coeff)
    residual = float(np.max(np.abs(reconstructed - target)))
    if residual > max(1.0e-6, 1.0e-10 * max(float(np.max(target)), 1.0)):
        raise TrialReject(
            f"control_volume_mass_inversion_residual:{residual}"
        )
    return sat


def sample_grid_inventory_to_control_volumes(
    r2: Any,
    grid_saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    geometry: dict[str, np.ndarray],
    n_streamlines: int,
    n_cv: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    sat_grid = np.asarray(grid_saturation, dtype=np.float64)
    kk = geometry["k"]
    jj = geometry["j"]
    ii = geometry["i"]
    pv = geometry["pv_m3"]
    cv_id = geometry["cv_id"]
    pseg = geometry["pseg_psi"]

    sub_sat = sat_grid[kk, jj, ii]
    sub_sg = np.clip(
        sub_sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    sub_rho = np.asarray(
        r2.gas_density_from_state(sub_sat, pseg, p_ref_gas_pa),
        dtype=np.float64,
    )
    sub_mass = pv * sub_rho * sub_sg

    cv_mass = np.bincount(
        cv_id,
        weights=sub_mass,
        minlength=n_streamlines * n_cv,
    ).reshape(n_streamlines, n_cv)

    cv_sat = invert_cv_mass_to_saturation(
        r2,
        cv_mass,
        geometry["cv_pressure_mass_coeff"],
    )
    reconstructed = cv_mass_from_saturation(
        r2,
        cv_sat,
        geometry["cv_pressure_mass_coeff"],
    )
    closure = float(np.sum(reconstructed) - np.sum(cv_mass))
    return cv_sat, cv_mass, closure


def build_face_pressure(
    e36: Any,
    sg7d: Any,
    xyz_m: np.ndarray,
    pressure_psi: np.ndarray,
) -> np.ndarray:
    k, j, i = e36.node_cell_indices(xyz_m, sg7d)
    return np.asarray(pressure_psi, dtype=np.float64)[k, j, i]


def advance_component_mass_control_volumes(
    r2: Any,
    sg7a: Any,
    old_sat: np.ndarray,
    old_mass: np.ndarray,
    cv_pressure_mass_coeff: np.ndarray,
    face_pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    weights_m3_day: np.ndarray,
    xi_faces: np.ndarray,
    dt_days: float,
) -> dict[str, Any]:
    old_sat = np.asarray(old_sat, dtype=np.float64)
    old_mass = np.asarray(old_mass, dtype=np.float64)
    q = np.asarray(weights_m3_day, dtype=np.float64)
    xi_faces = np.asarray(xi_faces, dtype=np.float64)
    face_p = np.asarray(face_pressure_psi, dtype=np.float64)

    nstream, ncv = old_sat.shape
    if old_mass.shape != old_sat.shape:
        raise GateError("old_cv_mass_shape_mismatch")
    if xi_faces.shape != (ncv + 1,):
        raise GateError(
            f"xi_face_count_mismatch:{xi_faces.shape}:{ncv+1}"
        )
    if face_p.shape != (nstream, ncv + 1):
        raise GateError(
            f"face_pressure_shape_mismatch:{face_p.shape}"
        )

    # Standard Corey fractional flow is monotone over the frozen SG7A
    # saturation interval. Under positive streamline flux, Godunov therefore
    # reduces to the upstream state. We verify that condition instead of
    # silently assuming it.
    scan = np.linspace(
        float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001
    )
    min_df = float(np.min(np.asarray(sg7a.df_dS(scan), dtype=np.float64)))
    if min_df < -1.0e-10:
        raise GateError(f"SG7A_fractional_flow_not_monotone:{min_df}")

    u_face = np.asarray(
        sg7a.u_dimensionless(xi_faces),
        dtype=np.float64,
    )
    flux = np.zeros((nstream, ncv + 1), dtype=np.float64)

    # The well is rate controlled in component mass. This is the only
    # external CO2 source. Sum(q_l)*700 kg/m3 = 500,000 kg/day.
    flux[:, 0] = q * CO2_RHO_REF_KG_M3

    if ncv > 1:
        donor = old_sat[:, :-1]
        ff = np.asarray(sg7a.fractional_flow(donor), dtype=np.float64)
        rho = np.asarray(
            r2.gas_density_from_state(
                donor,
                face_p[:, 1:-1],
                p_ref_gas_pa,
            ),
            dtype=np.float64,
        )
        flux[:, 1:-1] = (
            q[:, None]
            * u_face[None, 1:-1]
            * ff
            * rho
        )

    outlet_sat = old_sat[:, -1]
    outlet_ff = np.asarray(
        sg7a.fractional_flow(outlet_sat),
        dtype=np.float64,
    )
    outlet_rho = np.asarray(
        r2.gas_density_from_state(
            outlet_sat,
            face_p[:, -1],
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    flux[:, -1] = (
        q
        * float(u_face[-1])
        * outlet_ff
        * outlet_rho
    )

    new_mass = old_mass + float(dt_days) * (
        flux[:, :-1] - flux[:, 1:]
    )

    tol = max(
        1.0e-6,
        1.0e-10 * max(float(np.sum(old_mass)), 1.0),
    )
    min_mass = float(np.min(new_mass))
    if min_mass < -tol:
        raise TrialReject(
            f"component_mass_FV_negative_control_volume_mass:{min_mass}"
        )
    new_mass = np.maximum(new_mass, 0.0)

    new_sat = invert_cv_mass_to_saturation(
        r2,
        new_mass,
        cv_pressure_mass_coeff,
    )

    injected = float(np.sum(flux[:, 0]) * float(dt_days))
    produced = float(np.sum(flux[:, -1]) * float(dt_days))
    delta = float(np.sum(new_mass) - np.sum(old_mass))
    residual = delta - injected + produced
    closure_tol = max(
        1.0e-6,
        1.0e-10 * max(abs(injected), abs(delta), 1.0),
    )
    if abs(residual) > closure_tol:
        raise TrialReject(
            f"component_mass_FV_global_closure:{residual}:{closure_tol}"
        )

    return {
        "new_saturation": new_sat,
        "new_mass": new_mass,
        "face_mass_flux_kg_day": flux,
        "injected_mass_kg": injected,
        "produced_mass_kg": produced,
        "delta_mass_kg": delta,
        "mass_residual_kg": float(residual),
        "mass_closure_tolerance_kg": float(closure_tol),
        "outlet_fractional_flow": outlet_ff,
        "minimum_df_dS": min_df,
    }


def map_control_volume_increment_to_grid(
    r2: Any,
    parent_grid_saturation: np.ndarray,
    old_cv_saturation: np.ndarray,
    new_cv_saturation: np.ndarray,
    old_cv_mass: np.ndarray,
    new_cv_mass: np.ndarray,
    geometry: dict[str, np.ndarray],
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    cell_pore_volume_m3: float,
    target_final_mass_kg: float,
) -> dict[str, Any]:
    cv_id = geometry["cv_id"]
    flat = geometry["flat_cell"]
    pv = geometry["pv_m3"]
    pseg = geometry["pseg_psi"]

    old_flat_cv_sat = np.asarray(old_cv_saturation, dtype=np.float64).reshape(-1)
    new_flat_cv_sat = np.asarray(new_cv_saturation, dtype=np.float64).reshape(-1)

    old_sub_sat = old_flat_cv_sat[cv_id]
    new_sub_sat = new_flat_cv_sat[cv_id]
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
        r2.gas_density_from_state(
            old_sub_sat, pseg, p_ref_gas_pa
        ),
        dtype=np.float64,
    )
    rho_new = np.asarray(
        r2.gas_density_from_state(
            new_sub_sat, pseg, p_ref_gas_pa
        ),
        dtype=np.float64,
    )
    sub_delta_mass = pv * (
        rho_new * new_sub_sg - rho_old * old_sub_sg
    )

    ncell = int(np.prod(EXPECTED_GRID))
    deposited_delta_mass = np.bincount(
        flat,
        weights=sub_delta_mass,
        minlength=ncell,
    ).reshape(EXPECTED_GRID)

    cv_delta = float(
        np.sum(np.asarray(new_cv_mass, dtype=np.float64))
        - np.sum(np.asarray(old_cv_mass, dtype=np.float64))
    )
    sub_delta = float(np.sum(sub_delta_mass))
    transfer_residual = sub_delta - cv_delta
    transfer_tol = max(
        1.0e-6,
        1.0e-10 * max(abs(cv_delta), 1.0),
    )
    if abs(transfer_residual) > transfer_tol:
        raise TrialReject(
            f"CV_to_subsegment_component_transfer_closure:"
            f"{transfer_residual}:{transfer_tol}"
        )

    parent_sat = np.asarray(parent_grid_saturation, dtype=np.float64)
    parent_sg = np.clip(
        parent_sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    parent_rho = np.asarray(
        r2.gas_density_from_state(
            parent_sat, pressure_psi, p_ref_gas_pa
        ),
        dtype=np.float64,
    )
    parent_mass = (
        float(cell_pore_volume_m3) * parent_rho * parent_sg
    )
    parent_total = float(np.sum(parent_mass))

    trial_mass = parent_mass + deposited_delta_mass
    roundoff = max(
        1.0e-6,
        1.0e-10 * max(abs(float(target_final_mass_kg)), 1.0),
    )
    min_mass = float(np.min(trial_mass))
    if min_mass < -roundoff:
        raise TrialReject(
            f"aligned_mapback_negative_cell_mass:{min_mass}"
        )
    trial_mass = np.maximum(trial_mass, 0.0)

    mapped_total = float(np.sum(trial_mass))
    ledger_residual = mapped_total - float(target_final_mass_kg)
    if abs(ledger_residual) > roundoff:
        raise TrialReject(
            f"aligned_mapback_component_ledger_residual:"
            f"{ledger_residual}:{roundoff}"
        )

    corrected_sg = np.asarray(
        r2._invert_incremental_sg_from_mass(
            trial_mass,
            pressure_psi,
            p_ref_gas_pa,
            cell_pore_volume_m3,
        ),
        dtype=np.float64,
    )
    corrected_sat = BACKGROUND_SATURATION + corrected_sg
    reconstructed = float(
        r2.stored_co2_mass_kg(
            corrected_sat,
            pressure_psi,
            p_ref_gas_pa,
            cell_pore_volume_m3,
        )
    )
    inversion_residual = reconstructed - mapped_total
    if abs(inversion_residual) > roundoff:
        raise TrialReject(
            f"aligned_grid_mass_inversion_residual:"
            f"{inversion_residual}:{roundoff}"
        )

    return {
        "corrected_saturation": corrected_sat,
        "corrected_mass": trial_mass,
        "parent_grid_mass_kg": parent_total,
        "cv_delta_mass_kg": cv_delta,
        "subsegment_delta_mass_kg": sub_delta,
        "transfer_residual_kg": float(transfer_residual),
        "mapped_final_mass_kg": mapped_total,
        "target_final_mass_kg": float(target_final_mass_kg),
        "ledger_residual_kg": float(ledger_residual),
        "grid_inversion_residual_kg": float(inversion_residual),
        "roundoff_mass_kg": float(roundoff),
        "deposited_delta_mass": deposited_delta_mass,
        "source_local_added_mass_kg": 0.0,
        "source_local_corrected_cells": 0,
    }


def producer_rows_from_flux(
    labels: np.ndarray,
    weights_m3_day: np.ndarray,
    outlet_fractional_flow: np.ndarray,
    outlet_mass_flux_kg_day: np.ndarray,
    dt_days: float,
) -> tuple[list[dict[str, Any]], float]:
    labels = np.asarray(labels).astype(str)
    q = np.asarray(weights_m3_day, dtype=np.float64)
    ff = np.asarray(outlet_fractional_flow, dtype=np.float64)
    mflux = np.asarray(outlet_mass_flux_kg_day, dtype=np.float64)

    rows: list[dict[str, Any]] = []
    aggregate_num = 0.0
    aggregate_den = float(np.sum(q))
    for name in sorted(np.unique(labels)):
        mask = labels == name
        qsum = float(np.sum(q[mask]))
        cut = (
            float(np.sum(q[mask] * ff[mask]) / qsum)
            if qsum > 0.0
            else 0.0
        )
        mass_rate = float(np.sum(mflux[mask]))
        rows.append({
            "producer": str(name),
            "streamline_weight_rate_m3_day": qsum,
            "CO2_cut": cut,
            "CO2_mass_rate_kg_day": mass_rate,
            "CO2_mass_this_step_kg": mass_rate * float(dt_days),
        })
        aggregate_num += qsum * cut

    aggregate = (
        aggregate_num / aggregate_den if aggregate_den > 0.0 else 0.0
    )
    return rows, float(aggregate)


def validate_restart_bytes(
    data: bytes,
    expected_step: int,
    expected_time: float,
    expected_sat: np.ndarray,
) -> None:
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        if int(z["accepted_step_index"]) != int(expected_step):
            raise GateError(
                f"restart_step_mismatch:"
                f"{int(z['accepted_step_index'])}:{expected_step}"
            )
        if float(z["physical_time_days"]) != float(expected_time):
            raise GateError(
                f"restart_time_mismatch:"
                f"{float(z['physical_time_days'])}:{expected_time}"
            )
        if not np.array_equal(
            z["transport_saturation"], expected_sat
        ):
            raise GateError("restart_saturation_not_byte_exact")
        if not bool(z["control_volume_aligned_transfer_active"]):
            raise GateError("restart_missing_CV_aligned_transfer_flag")
        if bool(z["injector_local_mass_closure_authorized"]):
            raise GateError(
                "restart_incorrectly_authorizes_injector_local_closure"
            )


def self_test() -> None:
    # Minimal algebraic conservation test independent of repository data.
    nstream, ncv = 3, 4
    old = np.arange(nstream * ncv, dtype=float).reshape(nstream, ncv) + 100.0
    flux = np.array([
        [10, 8, 7, 6, 4],
        [20, 15, 12, 9, 5],
        [30, 25, 22, 20, 8],
    ], dtype=float)
    dt = 0.1
    new = old + dt * (flux[:, :-1] - flux[:, 1:])
    delta = float(np.sum(new) - np.sum(old))
    boundary = float(dt * (np.sum(flux[:, 0]) - np.sum(flux[:, -1])))
    if abs(delta - boundary) > 1.0e-12:
        raise RuntimeError("self_test_FV_telescoping_failed")

    # Subsegment partition of CV delta must preserve the same total.
    weights = np.array([0.25, 0.75, 0.40, 0.60])
    cv_delta = np.array([3.0, -1.0])
    sub = np.array([
        cv_delta[0] * weights[0],
        cv_delta[0] * weights[1],
        cv_delta[1] * weights[2],
        cv_delta[1] * weights[3],
    ])
    if abs(float(np.sum(sub)) - float(np.sum(cv_delta))) > 1.0e-12:
        raise RuntimeError("self_test_subsegment_partition_failed")

    print("PAD-Stream V16E-37A core conservation self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    trial_failures: list[dict[str, Any]] = []
    r2_parent_sha_before = None
    e36_cache_sha_before = None
    frozen_sha_before = None
    failed_step = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {
            "passed": bool(passed),
            "detail": str(detail),
        }
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 142)
        print(
            "PAD-Stream V16E-37A — Control-Volume-Aligned Conservative "
            "Streamline/Grid Transfer"
        )
        print("=" * 142)
        print(
            "Repair baseline : V16E-35-R2 accepted step 1 "
            "(E36 retained as diagnostic evidence)"
        )
        print(
            "Transport       : 201 SG6 faces -> 200 true streamline "
            "finite-volume control volumes"
        )
        print(
            "Conserved state : CO2 component mass; exact rate-controlled "
            "inlet mass flux"
        )
        print(
            "Map-back        : the same SG7D subsegment overlap partition "
            "used for CV inventory and grid deposition"
        )
        print(
            "Forbidden       : material injector-local source closure; "
            "global plume rescaling"
        )

        # ------------------------------------------------------------------
        # Immutable source/provenance authorities.
        # ------------------------------------------------------------------
        r2_path = root / R2_RUNNER
        e36_runner_path = root / E36_RUNNER
        sg7a_path = root / SG7A
        sg7d_path = root / SG7D
        for p in [r2_path, e36_runner_path, sg7a_path, sg7d_path]:
            gate(f"source_exists_{p.name}", p.is_file(), p)

        gate(
            "R2_runner_SHA_exact",
            sha256_file(r2_path) == R2_RUNNER_SHA256,
            sha256_file(r2_path),
        )
        gate(
            "E36_runner_SHA_exact",
            sha256_file(e36_runner_path) == E36_RUNNER_SHA256,
            sha256_file(e36_runner_path),
        )

        r2 = load_module(
            r2_path, "pad_stream_v16e37a_r2_authority"
        )
        e36 = load_module(
            e36_runner_path, "pad_stream_v16e37a_e36_authority"
        )

        r2_dir = drive / R2_REL
        e36_dir = drive / E36_REL
        r2_summary_path = r2_dir / R2_SUMMARY
        r2_closure_path = r2_dir / R2_CLOSURE
        r2_state_path = r2_dir / R2_STATE
        e36_summary_path = e36_dir / E36_SUMMARY
        e36_closure_path = e36_dir / E36_CLOSURE
        e36_cache_path = e36_dir / E36_CACHE
        e36_step_audit_path = e36_dir / E36_STEP_AUDIT
        e36_reject_path = e36_dir / E36_REJECTION_AUDIT
        frozen_100d = drive / V16_FROZEN_REL

        for p in [
            r2_summary_path,
            r2_closure_path,
            r2_state_path,
            e36_summary_path,
            e36_closure_path,
            e36_cache_path,
            e36_step_audit_path,
            e36_reject_path,
            frozen_100d,
        ]:
            gate(f"provenance_exists_{p.name}", p.is_file(), p)

        r2_summary = load_json(r2_summary_path)
        r2_closure = load_json(r2_closure_path)
        e36_summary = load_json(e36_summary_path)
        e36_closure = load_json(e36_closure_path)

        gate(
            "R2_status_accepted",
            r2_summary.get("status") == R2_EXPECTED_STATUS,
            r2_summary.get("status"),
        )
        gate(
            "E36_status_accepted",
            e36_summary.get("status") == E36_EXPECTED_STATUS,
            e36_summary.get("status"),
        )
        gate(
            "E36_cache_reuse_certified",
            e36_summary.get("cache_reuse_certified") is True,
        )
        gate(
            "E36_cache_scope_reference_mobility_only",
            e36_summary.get(
                "cache_reuse_scope_reference_mobility_only"
            ) is True,
        )
        gate(
            "E36_had_four_rejected_trials",
            int(e36_summary.get("total_rejected_trials", -1)) == 4,
            e36_summary.get("total_rejected_trials"),
        )

        e36_rejections = read_csv(e36_reject_path)
        gate(
            "E36_rejection_count_exact",
            len(e36_rejections) == 4,
            len(e36_rejections),
        )
        gate(
            "E36_all_rejections_were_injector_local_capacity",
            all(
                "continuation_injector_local_capacity_insufficient"
                in row.get("reason", "")
                for row in e36_rejections
            ),
        )

        e36_steps = read_csv(e36_step_audit_path)
        source_fractions = []
        for row in e36_steps:
            inj = float(row["injected_CO2_mass_kg"])
            src = float(row["source_local_added_mass_kg"])
            source_fractions.append(src / inj if inj > 0.0 else 0.0)
        gate(
            "E36_material_source_local_closure_confirmed",
            len(source_fractions) == 3
            and min(source_fractions) > 0.30,
            source_fractions,
        )

        r2_parent_sha_before = sha256_file(r2_state_path)
        e36_cache_sha_before = sha256_file(e36_cache_path)
        frozen_sha_before = sha256_file(frozen_100d)

        gate(
            "R2_parent_SHA_matches_R2_closure",
            r2_parent_sha_before
            == r2_closure.get("child_state_sha256"),
            r2_parent_sha_before,
        )
        gate(
            "E36_cache_SHA_matches_E36_closure",
            e36_cache_sha_before
            == e36_closure.get("certified_cache_sha256"),
            e36_cache_sha_before,
        )
        gate(
            "frozen_100d_SHA_exact",
            frozen_sha_before == V16_FROZEN_SHA256,
            frozen_sha_before,
        )

        parent = load_npz(r2_state_path)
        cache = load_npz(e36_cache_path)
        gate(
            "repair_parent_step_is_R2_step1",
            int_scalar(parent["accepted_step_index"]) == 1,
            int_scalar(parent["accepted_step_index"]),
        )
        gate(
            "repair_parent_time_positive",
            scalar(parent["physical_time_days"]) > 0.0,
            scalar(parent["physical_time_days"]),
        )
        gate(
            "E36_cache_bound_to_R2_step1",
            int_scalar(cache["certified_at_parent_step_index"]) == 1,
            int_scalar(cache["certified_at_parent_step_index"]),
        )
        gate(
            "E36_cache_exact_retrace_certified",
            bool_scalar(cache["certified_by_E36_exact_retrace"]),
        )
        gate(
            "E36_cache_reference_mobility_scope",
            bool_scalar(cache["reuse_scope_reference_mobility_only"]),
        )

        # ------------------------------------------------------------------
        # Load source-authentic transport/map-back physics in an isolated
        # temporary workspace so the Git repository cannot be dirtied by
        # source modules that create output directories on import.
        # ------------------------------------------------------------------
        with tempfile.TemporaryDirectory(
            prefix="PAD_Stream_V16E37A_"
        ) as td:
            tmp = Path(td)
            shutil.copy2(sg7a_path, tmp / SG7A)
            shutil.copy2(sg7d_path, tmp / SG7D)
            sg7a = load_module(
                tmp / SG7A, "pad_stream_v16e37a_sg7a"
            )
            sg7d = load_module(
                tmp / SG7D, "pad_stream_v16e37a_sg7d"
            )

            pressure_psi = np.asarray(
                cache["accepted_pressure_psi"], dtype=np.float64
            )
            xyz_m = np.asarray(
                cache["streamline_xyz_m"], dtype=np.float64
            )
            tau_s = np.asarray(
                cache["streamline_tof_s"], dtype=np.float64
            )
            tau_end_s = np.asarray(
                cache["tau_end_s"], dtype=np.float64
            )
            weights_m3_s = np.asarray(
                cache["streamline_weights_m3_s"], dtype=np.float64
            )
            labels = np.asarray(cache["producer_labels"]).astype(str)
            xi_faces = np.asarray(cache["xi"], dtype=np.float64)

            nstream = len(tau_end_s)
            nfaces = len(xi_faces)
            ncv = nfaces - 1
            gate(
                "streamline_count_exact",
                nstream == EXPECTED_STREAMLINES,
                nstream,
            )
            gate(
                "transport_face_count_exact",
                nfaces == EXPECTED_FACES,
                nfaces,
            )
            gate(
                "transport_control_volume_count_exact",
                ncv == EXPECTED_CVS,
                ncv,
            )
            gate(
                "xi_faces_uniform",
                np.allclose(
                    np.diff(xi_faces),
                    np.diff(xi_faces)[0],
                    rtol=1.0e-12,
                    atol=1.0e-14,
                ),
            )
            gate(
                "xi_face_domain_exact",
                abs(float(xi_faces[0])) <= 1.0e-15
                and abs(float(xi_faces[-1]) - 1.0) <= 1.0e-15,
                f"{xi_faces[0]}:{xi_faces[-1]}",
            )

            weights_m3_day = weights_m3_s * DAY_TO_S
            q_total_m3_day = float(np.sum(weights_m3_day))
            q_expected = (
                INJECTOR_MASS_RATE_KG_DAY / CO2_RHO_REF_KG_M3
            )
            gate(
                "streamline_weights_match_fixed_injection_rate",
                abs(q_total_m3_day - q_expected)
                / q_expected
                < 1.0e-10,
                f"{q_total_m3_day}:{q_expected}",
            )

            tof_days = tau_s / DAY_TO_S
            operator = sg7d.build_subsegment_operator(
                xyz_m,
                tof_days,
                weights_m3_day,
            )
            p_ref_gas_pa = scalar(
                parent["co2_density_reference_pressure_pa"]
            )
            geometry = build_control_volume_geometry(
                r2,
                operator,
                pressure_psi,
                p_ref_gas_pa,
                nstream,
                ncv,
            )

            # Exact CV pore-volume identity: each common xi interval has
            # q_l * Delta tau_l. SG7D subsegment splitting must preserve it.
            expected_cv_pv = (
                weights_m3_day[:, None]
                * np.diff(tof_days, axis=1)
            )
            cv_pv = geometry["cv_pv_m3"]
            cv_pv_rel = (
                float(np.linalg.norm((cv_pv - expected_cv_pv).ravel()))
                / max(
                    float(np.linalg.norm(expected_cv_pv.ravel())),
                    1.0e-30,
                )
            )
            gate(
                "SG7D_subsegments_close_each_transport_CV_pore_volume",
                cv_pv_rel <= 1.0e-10,
                cv_pv_rel,
            )

            face_pressure_psi = build_face_pressure(
                e36,
                sg7d,
                xyz_m,
                pressure_psi,
            )
            gate(
                "face_pressure_shape_exact",
                face_pressure_psi.shape
                == (nstream, nfaces),
                face_pressure_psi.shape,
            )

            # Physics-derived nominal dt for the new 200-CV discretization.
            dxi = float(xi_faces[1] - xi_faces[0])
            sat_scan = np.linspace(
                float(sg7a.S_INITIAL),
                float(sg7a.S_INJECTED),
                4001,
            )
            max_df = float(
                np.max(
                    np.abs(
                        np.asarray(
                            sg7a.df_dS(sat_scan),
                            dtype=np.float64,
                        )
                    )
                )
            )
            u_face = np.asarray(
                sg7a.u_dimensionless(xi_faces),
                dtype=np.float64,
            )
            max_wave_speed = float(np.max(u_face) * max_df)
            dtD_cfl = float(
                sg7a.CFL
                * dxi
                / (max_wave_speed + sg7a.EPS)
            )
            fastest_tau_days = float(
                np.min(tau_end_s / DAY_TO_S)
            )
            nominal_dt_days = float(
                dtD_cfl * fastest_tau_days
            )
            gate(
                "CV_aligned_nominal_dt_positive",
                np.isfinite(nominal_dt_days)
                and nominal_dt_days > 0.0,
                nominal_dt_days,
            )
            gate(
                "CV_aligned_nominal_dt_not_V15_box",
                nominal_dt_days < 0.10,
                nominal_dt_days,
            )

            dx_m = 20.0 * FT_TO_M
            dy_m = 20.0 * FT_TO_M
            dz_m = 4.0 * FT_TO_M
            cell_pore_volume_m3 = (
                0.20 * dx_m * dy_m * dz_m
            )
            permeability_md = np.loadtxt(
                root / "SGSIM_50x50x15_PERM_MD.csv",
                skiprows=1,
                dtype=np.float64,
            ).reshape(EXPECTED_GRID, order="C")
            gate(
                "SGSim_permeability_grid_shape_exact",
                permeability_md.shape == EXPECTED_GRID,
                permeability_md.shape,
            )

            # ------------------------------------------------------------------
            # Rerun the same early continuation from the R2 accepted step-1
            # baseline, but now with 200 exact component-mass FV control
            # volumes and NO source-local grid closure.
            # ------------------------------------------------------------------
            current = {
                k: np.asarray(v).copy()
                for k, v in parent.items()
            }
            child_file_bytes: dict[str, bytes] = {}
            step_rows: list[dict[str, Any]] = []
            producer_rows_all: list[dict[str, Any]] = []
            plume_rows: list[dict[str, Any]] = []
            snapshot_steps = [
                int_scalar(current["accepted_step_index"])
            ]
            snapshot_times = [
                scalar(current["physical_time_days"])
            ]
            snapshot_sats = [
                np.asarray(
                    current["transport_saturation"],
                    dtype=np.float64,
                ).copy()
            ]

            initial_plume = e36.plume_metrics(
                r2,
                snapshot_sats[0],
                pressure_psi,
                p_ref_gas_pa,
                cell_pore_volume_m3,
                snapshot_steps[0],
                snapshot_times[0],
            )
            plume_rows.append(initial_plume)

            transport_residuals: list[float] = []
            transfer_residuals: list[float] = []
            mapback_ledger_residuals: list[float] = []
            capillary_external_changes: list[float] = []
            sample_closures: list[float] = []
            source_local_added: list[float] = []

            for target_step in range(2, TARGET_FINAL_STEP_INDEX + 1):
                failed_step = target_step
                current_time = scalar(
                    current["physical_time_days"]
                )
                next_obs = scalar(
                    current["next_fixed_observation_day"]
                )
                dt_days = min(
                    nominal_dt_days,
                    next_obs - current_time,
                )
                if not np.isfinite(dt_days) or dt_days <= 0.0:
                    raise GateError(
                        f"E37A_nonpositive_dt:"
                        f"{target_step}:{dt_days}"
                    )

                try:
                    parent_sat = np.asarray(
                        current["transport_saturation"],
                        dtype=np.float64,
                    )
                    parent_stored = scalar(
                        current["stored_co2_mass_current_kg"]
                    )
                    recomputed_parent_stored = float(
                        r2.stored_co2_mass_kg(
                            parent_sat,
                            pressure_psi,
                            p_ref_gas_pa,
                            cell_pore_volume_m3,
                        )
                    )
                    parent_mass_tol = max(
                        1.0e-6,
                        1.0e-10
                        * max(abs(parent_stored), 1.0),
                    )
                    if (
                        abs(
                            recomputed_parent_stored
                            - parent_stored
                        )
                        > parent_mass_tol
                    ):
                        raise TrialReject(
                            "parent_grid_component_mass_recompute_mismatch:"
                            f"{recomputed_parent_stored-parent_stored}:"
                            f"{parent_mass_tol}"
                        )

                    old_cv_sat, old_cv_mass, sample_closure = (
                        sample_grid_inventory_to_control_volumes(
                            r2,
                            parent_sat,
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
                        * max(
                            abs(float(np.sum(old_cv_mass))),
                            1.0,
                        ),
                    )
                    if abs(sample_closure) > sample_tol:
                        raise TrialReject(
                            f"grid_to_CV_inventory_sampling_closure:"
                            f"{sample_closure}:{sample_tol}"
                        )

                    transport = (
                        advance_component_mass_control_volumes(
                            r2,
                            sg7a,
                            old_cv_sat,
                            old_cv_mass,
                            geometry[
                                "cv_pressure_mass_coeff"
                            ],
                            face_pressure_psi,
                            p_ref_gas_pa,
                            weights_m3_day,
                            xi_faces,
                            dt_days,
                        )
                    )

                    injected_step = float(
                        transport["injected_mass_kg"]
                    )
                    produced_step = float(
                        transport["produced_mass_kg"]
                    )
                    physical_injected = (
                        INJECTOR_MASS_RATE_KG_DAY * dt_days
                    )
                    injection_tol = max(
                        1.0e-6,
                        1.0e-12
                        * max(abs(physical_injected), 1.0),
                    )
                    if (
                        abs(
                            injected_step - physical_injected
                        )
                        > injection_tol
                    ):
                        raise TrialReject(
                            "fixed_rate_inlet_component_mass_not_exact:"
                            f"{injected_step}:{physical_injected}"
                        )

                    target_final_mass = (
                        parent_stored
                        + injected_step
                        - produced_step
                    )
                    mapping = map_control_volume_increment_to_grid(
                        r2,
                        parent_sat,
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

                    capillary = (
                        r2.conservative_capillary_mass_redistribution(
                            transport_saturation=pre_capillary_sat,
                            permeability_md=permeability_md,
                            pressure_psi=pressure_psi,
                            p_ref_pa=p_ref_gas_pa,
                            cell_pore_volume_m3=cell_pore_volume_m3,
                            dt_seconds=dt_days * DAY_TO_S,
                        )
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
                        - parent_stored
                        - injected_step
                        + produced_step
                    )
                    closure_tol = max(
                        1.0e-6,
                        1.0e-10
                        * max(abs(target_final_mass), 1.0),
                    )
                    if (
                        abs(
                            capillary[
                                "external_mass_change_kg"
                            ]
                        )
                        > closure_tol
                    ):
                        raise TrialReject(
                            "capillary_external_mass_change:"
                            f"{capillary['external_mass_change_kg']}:"
                            f"{closure_tol}"
                        )
                    if abs(step_residual) > closure_tol:
                        raise TrialReject(
                            f"step_component_mass_closure:"
                            f"{step_residual}:{closure_tol}"
                        )
                    if (
                        float(np.min(child_sat))
                        < BACKGROUND_SATURATION - 1.0e-12
                        or float(np.max(child_sat))
                        > INJECTED_BOUNDARY_SATURATION + 1.0e-12
                    ):
                        raise TrialReject(
                            "child_saturation_bounds:"
                            f"{np.min(child_sat)}:"
                            f"{np.max(child_sat)}"
                        )

                    prod_rows, aggregate_cut = (
                        producer_rows_from_flux(
                            labels,
                            weights_m3_day,
                            transport[
                                "outlet_fractional_flow"
                            ],
                            transport[
                                "face_mass_flux_kg_day"
                            ][:, -1],
                            dt_days,
                        )
                    )
                    if (
                        not np.isfinite(aggregate_cut)
                        or not 0.0 <= aggregate_cut <= 1.0
                    ):
                        raise TrialReject(
                            f"producer_CO2_cut_invalid:"
                            f"{aggregate_cut}"
                        )
                    if (
                        aggregate_cut
                        >= BREAKTHROUGH_GAS_CUT
                    ):
                        raise TrialReject(
                            "breakthrough_encountered_during_"
                            f"E37A_transfer_validation:"
                            f"{aggregate_cut}"
                        )

                    child = e36.make_child_state(
                        current,
                        child_sat,
                        pressure_psi,
                        p_ref_gas_pa,
                        dt_days,
                        produced_step,
                        aggregate_cut,
                        final_stored,
                        step_residual,
                        True,
                    )
                    child[
                        "transport_face_count"
                    ] = np.asarray(
                        nfaces, dtype=np.int64
                    )
                    child[
                        "transport_control_volume_count"
                    ] = np.asarray(
                        ncv, dtype=np.int64
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
                    child[
                        "last_source_local_added_mass_kg"
                    ] = np.asarray(0.0, dtype=np.float64)
                    child[
                        "last_CV_transport_mass_residual_kg"
                    ] = np.asarray(
                        transport["mass_residual_kg"],
                        dtype=np.float64,
                    )
                    child[
                        "last_CV_to_grid_transfer_residual_kg"
                    ] = np.asarray(
                        mapping["transfer_residual_kg"],
                        dtype=np.float64,
                    )

                    new_time = scalar(
                        child["physical_time_days"]
                    )
                    if (
                        new_time <= current_time
                        or new_time > next_obs + 1.0e-12
                    ):
                        raise TrialReject(
                            f"accepted_time_invalid:"
                            f"{current_time}:{new_time}:{next_obs}"
                        )

                    child_bytes = deterministic_npz_bytes(
                        child
                    )
                    validate_restart_bytes(
                        child_bytes,
                        target_step,
                        new_time,
                        child_sat,
                    )

                    child_name = (
                        "V16E37A_Accepted_CV_Aligned_"
                        f"SGSim_Runtime_State_Step{target_step:04d}.npz"
                    )
                    child_file_bytes[child_name] = child_bytes
                    snapshot_steps.append(target_step)
                    snapshot_times.append(new_time)
                    snapshot_sats.append(child_sat.copy())
                    plume_rows.append(
                        e36.plume_metrics(
                            r2,
                            child_sat,
                            pressure_psi,
                            p_ref_gas_pa,
                            cell_pore_volume_m3,
                            target_step,
                            new_time,
                        )
                    )
                    for row in prod_rows:
                        producer_rows_all.append({
                            "accepted_step_index": target_step,
                            "time_days": new_time,
                            **row,
                        })

                    cumulative_resid = scalar(
                        child[
                            "cumulative_mass_residual_kg"
                        ]
                    )
                    step_rows.append({
                        "accepted_step_index": target_step,
                        "parent_time_days": current_time,
                        "accepted_time_days": new_time,
                        "accepted_dt_days": dt_days,
                        "nominal_dt_days": nominal_dt_days,
                        "retry_count": 0,
                        "flow_path_mode": (
                            "E36_CERTIFIED_REFERENCE_MOBILITY_CACHE"
                        ),
                        "transport_faces": nfaces,
                        "transport_control_volumes": ncv,
                        "grid_to_CV_sampling_closure_kg": sample_closure,
                        "injected_CO2_mass_kg": injected_step,
                        "produced_CO2_mass_kg": produced_step,
                        "CV_transport_delta_mass_kg": transport[
                            "delta_mass_kg"
                        ],
                        "CV_transport_mass_residual_kg": transport[
                            "mass_residual_kg"
                        ],
                        "CV_to_subsegment_transfer_residual_kg": mapping[
                            "transfer_residual_kg"
                        ],
                        "grid_mapback_ledger_residual_kg": mapping[
                            "ledger_residual_kg"
                        ],
                        "source_local_added_mass_kg": 0.0,
                        "source_local_corrected_cells": 0,
                        "injector_local_mass_closure_authorized": False,
                        "capillary_substeps": int(
                            capillary["substeps"]
                        ),
                        "capillary_external_mass_change_kg": float(
                            capillary[
                                "external_mass_change_kg"
                            ]
                        ),
                        "stored_CO2_mass_kg": final_stored,
                        "step_mass_residual_kg": step_residual,
                        "cumulative_mass_residual_kg": cumulative_resid,
                        "producer_CO2_gas_cut": aggregate_cut,
                        "breakthrough_reached": bool_scalar(
                            child["breakthrough_reached"]
                        ),
                    })

                    sample_closures.append(sample_closure)
                    transport_residuals.append(
                        float(transport["mass_residual_kg"])
                    )
                    transfer_residuals.append(
                        float(mapping["transfer_residual_kg"])
                    )
                    mapback_ledger_residuals.append(
                        float(mapping["ledger_residual_kg"])
                    )
                    capillary_external_changes.append(
                        float(
                            capillary[
                                "external_mass_change_kg"
                            ]
                        )
                    )
                    source_local_added.append(0.0)

                    gates[
                        f"E37A_step_{target_step}_accepted_nominal_dt"
                    ] = {
                        "passed": True,
                        "detail": (
                            f"t={new_time:.12g} d, "
                            f"dt={dt_days:.12g} d"
                        ),
                    }
                    gates[
                        f"E37A_step_{target_step}_source_local_closure_zero"
                    ] = {
                        "passed": True,
                        "detail": "0.0 kg",
                    }
                    current = child
                    print(
                        f"[ACCEPT] step {target_step}: "
                        f"t={new_time:.12g} d, "
                        f"dt={dt_days:.12g} d, "
                        f"CV mass residual="
                        f"{transport['mass_residual_kg']:.3e} kg, "
                        f"map-back residual="
                        f"{mapping['ledger_residual_kg']:.3e} kg"
                    )

                except TrialReject as exc:
                    trial_failures.append({
                        "target_step": target_step,
                        "trial_dt_days": dt_days,
                        "reason": repr(exc),
                    })
                    print(
                        f"[REJECT] step {target_step}: {exc}"
                    )
                    raise GateError(
                        "E37A_nominal_step_rejected:"
                        f"{target_step}:{repr(exc)}"
                    )

            final_state = current
            final_step = int_scalar(
                final_state["accepted_step_index"]
            )
            final_time = scalar(
                final_state["physical_time_days"]
            )
            final_mass = scalar(
                final_state["stored_co2_mass_current_kg"]
            )
            final_cum_resid = scalar(
                final_state["cumulative_mass_residual_kg"]
            )
            final_tol = max(
                1.0e-6,
                1.0e-10 * max(abs(final_mass), 1.0),
            )

            gate(
                "E37A_final_step_index_exact",
                final_step == TARGET_FINAL_STEP_INDEX,
                final_step,
            )
            gate(
                "E37A_all_three_nominal_steps_accepted_without_retry",
                len(step_rows) == 3
                and len(trial_failures) == 0
                and all(
                    int(r["retry_count"]) == 0
                    and abs(
                        float(r["accepted_dt_days"])
                        - nominal_dt_days
                    )
                    <= 1.0e-15
                    for r in step_rows
                ),
                {
                    "accepted": len(step_rows),
                    "rejected": len(trial_failures),
                },
            )
            gate(
                "E37A_injector_local_mass_closure_never_used",
                max_abs(source_local_added) <= 1.0e-12,
                max_abs(source_local_added),
            )
            gate(
                "E37A_CV_transport_mass_closure",
                max_abs(transport_residuals)
                <= max(
                    1.0e-6,
                    1.0e-10
                    * max(
                        abs(
                            INJECTOR_MASS_RATE_KG_DAY
                            * nominal_dt_days
                        ),
                        1.0,
                    ),
                ),
                max_abs(transport_residuals),
            )
            gate(
                "E37A_CV_subsegment_transfer_closure",
                max_abs(transfer_residuals)
                <= max(
                    1.0e-6,
                    1.0e-10
                    * max(abs(final_mass), 1.0),
                ),
                max_abs(transfer_residuals),
            )
            gate(
                "E37A_grid_mapback_component_ledger_closure",
                max_abs(mapback_ledger_residuals)
                <= final_tol,
                max_abs(mapback_ledger_residuals),
            )
            gate(
                "E37A_capillary_zero_external_source",
                max_abs(capillary_external_changes)
                <= final_tol,
                max_abs(capillary_external_changes),
            )
            gate(
                "E37A_cumulative_mass_closure",
                abs(final_cum_resid) <= final_tol,
                f"{final_cum_resid}:{final_tol}",
            )
            gate(
                "E37A_no_breakthrough",
                not bool_scalar(
                    final_state["breakthrough_reached"]
                ),
                scalar(
                    final_state[
                        "current_producer_co2_gas_cut"
                    ]
                ),
            )
            gate(
                "E37A_pre_first_observation",
                final_time < 30.0,
                final_time,
            )
            gate(
                "E37A_next_observation_still_30d",
                abs(
                    scalar(
                        final_state[
                            "next_fixed_observation_day"
                        ]
                    )
                    - 30.0
                )
                <= 1.0e-12,
                scalar(
                    final_state[
                        "next_fixed_observation_day"
                    ]
                ),
            )
            gate(
                "R2_parent_state_unchanged",
                sha256_file(r2_state_path)
                == r2_parent_sha_before,
                sha256_file(r2_state_path),
            )
            gate(
                "E36_certified_cache_unchanged",
                sha256_file(e36_cache_path)
                == e36_cache_sha_before,
                sha256_file(e36_cache_path),
            )
            gate(
                "frozen_100d_unchanged",
                sha256_file(frozen_100d)
                == frozen_sha_before,
                sha256_file(frozen_100d),
            )

            snapshot_bytes = deterministic_npz_bytes({
                "accepted_step_index": np.asarray(
                    snapshot_steps, dtype=np.int64
                ),
                "physical_time_days": np.asarray(
                    snapshot_times, dtype=np.float64
                ),
                "transport_saturation": np.stack(
                    snapshot_sats, axis=0
                ).astype(np.float64),
            })

            transfer_contract = {
                "milestone": MILESTONE,
                "status": (
                    "CONTROL_VOLUME_ALIGNED_COMPONENT_MASS_TRANSFER_FROZEN"
                ),
                "SG6_role": (
                    "201 common xi points are transport FACES"
                ),
                "transport_control_volumes_per_streamline": ncv,
                "transport_faces_per_streamline": nfaces,
                "control_volume_pore_volume": (
                    "PV_lj = q_l * (tau_{j+1}-tau_j)"
                ),
                "restart_sampling": (
                    "exact SG7D subsegment component inventory -> "
                    "CV-uniform saturation by EOS inversion"
                ),
                "transport_update": (
                    "finite-volume CO2 component-mass balance; "
                    "fixed rate-controlled inlet mass flux; "
                    "internal face fluxes cancel pairwise"
                ),
                "mapback": (
                    "CV component-mass increment -> same SG7D "
                    "subsegment partition -> Cartesian cell mass increment"
                ),
                "injector_local_mass_closure_authorized": False,
                "global_plume_rescaling_authorized": False,
                "capillary_operator": (
                    "R2 no-flow Cartesian internal component-mass redistribution"
                ),
                "flow_path_cache_scope": (
                    "E36-certified V15-SG3 steady reference-mobility authority only"
                ),
                "F0_learned_timestep_authorized": False,
            }

            comparison = {
                "milestone": MILESTONE,
                "E36_status_preserved": E36_EXPECTED_STATUS,
                "E36_rejected_trials": len(e36_rejections),
                "E36_rejection_mechanism": (
                    "continuation_injector_local_capacity_insufficient"
                ),
                "E36_accepted_source_local_fraction_of_injection": source_fractions,
                "E37A_repair_baseline": (
                    "R2 accepted step 1"
                ),
                "E37A_nominal_dt_days": nominal_dt_days,
                "E37A_nominal_transitions_attempted": 3,
                "E37A_nominal_transitions_accepted": len(step_rows),
                "E37A_rejected_trials": len(trial_failures),
                "E37A_source_local_added_mass_kg_max_abs": max_abs(
                    source_local_added
                ),
                "interpretation": (
                    "E36 remains accepted diagnostic evidence. "
                    "E37A supersedes its temporary continuation transfer "
                    "operator for subsequent production rollout."
                ),
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "repair_baseline_milestone": "V16E-35-R2",
                "diagnostic_predecessor": "V16E-36",
                "E36_diagnostic_preserved": True,
                "E36_temporary_transfer_operator_superseded": True,
                "initial_step_index": 1,
                "initial_time_days": snapshot_times[0],
                "final_accepted_step_index": final_step,
                "final_time_days": final_time,
                "continuation_transitions_executed": len(step_rows),
                "nominal_dt_days": nominal_dt_days,
                "accepted_dt_days": [
                    float(r["accepted_dt_days"])
                    for r in step_rows
                ],
                "total_rejected_trials": len(trial_failures),
                "all_nominal_steps_accepted_without_retry": True,
                "transport_faces_per_streamline": nfaces,
                "transport_control_volumes_per_streamline": ncv,
                "component_mass_primary_conserved_variable": True,
                "fixed_rate_inlet_mass_flux_exact": True,
                "CV_pore_volume_alignment_passed": True,
                "grid_to_CV_inventory_consistent_sampling": True,
                "same_overlap_operator_used_for_mapback": True,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
                "source_local_added_mass_kg_max_abs": max_abs(
                    source_local_added
                ),
                "CV_transport_mass_residual_kg_max_abs": max_abs(
                    transport_residuals
                ),
                "CV_to_subsegment_transfer_residual_kg_max_abs": max_abs(
                    transfer_residuals
                ),
                "grid_mapback_ledger_residual_kg_max_abs": max_abs(
                    mapback_ledger_residuals
                ),
                "capillary_external_mass_source_kg_max_abs": max_abs(
                    capillary_external_changes
                ),
                "cumulative_injected_CO2_mass_kg": scalar(
                    final_state[
                        "cumulative_injected_co2_mass_kg"
                    ]
                ),
                "cumulative_produced_CO2_mass_kg": scalar(
                    final_state[
                        "cumulative_produced_co2_mass_kg"
                    ]
                ),
                "stored_CO2_mass_kg": final_mass,
                "cumulative_mass_residual_kg": final_cum_resid,
                "mass_numerical_closure_passed": (
                    abs(final_cum_resid) <= final_tol
                ),
                "breakthrough_reached": bool_scalar(
                    final_state["breakthrough_reached"]
                ),
                "next_fixed_observation_day": scalar(
                    final_state[
                        "next_fixed_observation_day"
                    ]
                ),
                "observation_checkpoint_reached": False,
                "E37B_extended_rollout_entry_ready": True,
                "E36_certified_cache_reused": True,
                "cache_reuse_scope_reference_mobility_only": True,
                "learned_timestep_proposal_used": False,
                "F0_hidden_update_deferred": True,
                "SGSim_specific_dt_envelope_frozen": False,
                "SGSim_specific_mass_tolerance_frozen": False,
                "frozen_100d_checkpoint_modified": False,
                "IBDP_started": False,
            }

            handoff = f"""# PAD-Stream V16E-37A Handoff

V16E-37A repairs the numerical transfer limitation exposed by the accepted V16E-36 short rollout.

V16E-36 remains valid diagnostic evidence. Its four rejected trials were all caused by the temporary continuation injector-local capacity closure, and its accepted steps required material source-local corrections equal to approximately {source_fractions[0]:.3%}, {source_fractions[1]:.3%}, and {source_fractions[2]:.3%} of the corresponding injected step mass.

E37A therefore returns to the accepted V16E-35-R2 step-1 state and replaces only the continuation transport/map-back discretization:

- the 201 SG6 common xi points are transport faces;
- the 200 intervals between them are the actual finite-volume transport control volumes;
- each CV pore volume is q_l * Delta tau;
- restart sampling is component-inventory consistent over the exact SG7D subsegments;
- CO2 component mass is the conserved transport variable;
- the inlet component-mass flux is exactly the fixed 500 tonne/day well source;
- internal streamline face mass fluxes cancel pairwise;
- the same exact SG7D subsegment partition maps the CV component-mass increment back to the Cartesian grid;
- no injector-local mass closure is authorized;
- no global plume rescaling is authorized;
- the R2 no-flow Cartesian capillary mass redistribution remains the capillary authority.

Validation target:
- three continuation transitions from R2 step 1 to accepted step 4;
- every transition must accept the full physics-derived nominal dt = {nominal_dt_days:.12g} days;
- zero retry-based timestep collapse is allowed;
- material source-local closure is forbidden;
- component mass must close through transport, map-back, capillary redistribution, and restart.

Accepted final step/time:
- step: {final_step}
- time: {final_time:.12g} days
- rejected trials: {len(trial_failures)}
- maximum source-local added mass: {max_abs(source_local_added):.12e} kg
- cumulative mass residual: {final_cum_resid:.12e} kg
- next fixed observation: {scalar(final_state["next_fixed_observation_day"]):.12g} days

The E36-certified flow/path cache remains valid only under the current V15-SG3 steady reference-mobility pressure authority. A future saturation-dependent/multiphase pressure solve must revalidate pressure, Darcy flux, Pollock paths, and TOF.

F0 remains deferred. Neither the SGSim production timestep envelope nor final runtime mass tolerance is frozen by E37A.

NEXT: {NEXT}
"""

            files: dict[str, bytes] = {}
            files.update(child_file_bytes)
            files[
                "V16E37A_CV_Aligned_Early_Plume_Snapshots.npz"
            ] = snapshot_bytes
            files[
                "V16E37A_CV_Aligned_Rollout_Step_Audit.csv"
            ] = csv_bytes(step_rows)
            files[
                "V16E37A_Producer_CO2_Response.csv"
            ] = csv_bytes(producer_rows_all)
            files[
                "V16E37A_Early_Plume_Metrics.csv"
            ] = csv_bytes(plume_rows)
            files[
                "V16E37A_Transfer_Contract.json"
            ] = json_bytes(transfer_contract)
            files[
                "V16E37A_E36_Repair_Comparison.json"
            ] = json_bytes(comparison)
            files[
                "V16E37A_Trial_Rejection_Audit.csv"
            ] = csv_bytes(trial_failures)
            files[
                "PAD_Stream_V16E37A_Summary.json"
            ] = json_bytes(summary)
            files[
                "V16E37A_Handoff.md"
            ] = handoff.encode("utf-8")
            files[
                "V16E37A_Final_Gate_Matrix.csv"
            ] = csv_bytes([
                {"gate": k, **v}
                for k, v in gates.items()
            ])

            final_state_name = (
                "V16E37A_Accepted_CV_Aligned_"
                f"SGSim_Runtime_State_Step{final_step:04d}.npz"
            )
            final_state_sha = hashlib.sha256(
                files[final_state_name]
            ).hexdigest()
            snapshot_sha = hashlib.sha256(
                snapshot_bytes
            ).hexdigest()

            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed": all(
                    v["passed"] for v in gates.values()
                ),
                "gate_count": len(gates),
                "final_state_file": final_state_name,
                "final_state_sha256": final_state_sha,
                "snapshot_file": (
                    "V16E37A_CV_Aligned_Early_Plume_Snapshots.npz"
                ),
                "snapshot_sha256": snapshot_sha,
                "R2_repair_parent_state_sha256": r2_parent_sha_before,
                "E36_certified_cache_sha256": e36_cache_sha_before,
                "frozen_100d_sha256": frozen_sha_before,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
            }
            files[
                "V16E37A_Final_Closure.json"
            ] = json_bytes(closure)

            immutable_publish(out, files)

            artifact_rows = []
            for path in sorted(out.iterdir()):
                if (
                    path.is_file()
                    and path.name
                    != "V16E37A_Artifact_Manifest.csv"
                ):
                    artifact_rows.append({
                        "file": path.name,
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    })
            immutable_publish(
                out,
                {
                    "V16E37A_Artifact_Manifest.csv":
                    csv_bytes(artifact_rows)
                },
            )

        print("\n" + "=" * 142)
        print(
            "PAD-Stream V16E-37A CONTROL-VOLUME-ALIGNED "
            "CONSERVATIVE TRANSFER: PASS"
        )
        print("=" * 142)
        print(
            f"{'Repair parent step/time':82}: "
            f"1 / {snapshot_times[0]:.12g} d"
        )
        print(
            f"{'Final accepted step/time':82}: "
            f"{final_step} / {final_time:.12g} d"
        )
        print(
            f"{'Transport faces / control volumes':82}: "
            f"{nfaces} / {ncv}"
        )
        print(
            f"{'Physics-derived nominal dt':82}: "
            f"{nominal_dt_days:.12g} d"
        )
        print(
            f"{'Accepted nominal transitions / rejected trials':82}: "
            f"{len(step_rows)} / {len(trial_failures)}"
        )
        print(
            f"{'Maximum source-local added mass':82}: "
            f"{max_abs(source_local_added):.12e} kg"
        )
        print(
            f"{'Maximum CV transport mass residual':82}: "
            f"{max_abs(transport_residuals):.12e} kg"
        )
        print(
            f"{'Maximum CV->grid ledger residual':82}: "
            f"{max_abs(mapback_ledger_residuals):.12e} kg"
        )
        print(
            f"{'Cumulative mass residual':82}: "
            f"{final_cum_resid:.12e} kg"
        )
        print(
            f"{'E37B extended rollout entry ready':82}: YES"
        )
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": (
                "CONTROL_VOLUME_ALIGNED_CONSERVATIVE_TRANSFER_BLOCKED"
            ),
            "exception": repr(exc),
            "failed_target_step": failed_step,
            "gates": gates,
            "trial_failures": trial_failures,
            "R2_repair_parent_state": str(
                drive / R2_REL / R2_STATE
            ),
            "R2_repair_parent_state_sha256_before": (
                r2_parent_sha_before
            ),
            "E36_certified_cache_sha256_before": (
                e36_cache_sha_before
            ),
            "frozen_100d_sha256_before": frozen_sha_before,
            "accepted_E37A_children_published": False,
            "runtime_time_advance_committed_to_persistent_state": False,
            "R2_parent_mutated": False,
            "E36_diagnostic_artifacts_mutated": False,
            "frozen_100d_modified": False,
            "next_action": (
                "Audit the failed CV-aligned transfer gate. "
                "Do not advance to V16E-37B."
            ),
        }
        data = json_bytes(report)
        path = blocked / (
            "V16E37A_Blocked_CV_Aligned_Conservative_Transfer.json"
        )
        if path.exists() and path.read_bytes() != data:
            path = blocked / (
                "V16E37A_Blocked_CV_Aligned_Conservative_Transfer_"
                f"{hashlib.sha256(data).hexdigest()[:12]}.json"
            )
        if not path.exists():
            path.write_bytes(data)

        print("\n" + "=" * 142)
        print(
            "PAD-Stream V16E-37A CONTROL-VOLUME-ALIGNED "
            "CONSERVATIVE TRANSFER: BLOCKED"
        )
        print("=" * 142)
        print("Reason:", repr(exc))
        print(
            "No E37A accepted child state was published by this "
            "failed milestone execution."
        )
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, required=False
    )
    parser.add_argument(
        "--drive-root", type=Path, required=False
    )
    parser.add_argument(
        "--self-test", action="store_true"
    )
    args = parser.parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    if args.project_root is None or args.drive_root is None:
        parser.error(
            "--project-root and --drive-root are required unless --self-test is used"
        )
    raise SystemExit(
        main(args.project_root, args.drive_root)
    )
