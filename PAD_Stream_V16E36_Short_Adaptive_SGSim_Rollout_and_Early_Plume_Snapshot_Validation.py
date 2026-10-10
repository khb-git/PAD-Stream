from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np


MILESTONE = "V16E-36"
STATUS = "SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATED"
NEXT = "V16E-37 - Extended SGSim Runtime Rollout / First Fixed Observation Checkpoint"

EXPECTED_GRID = (15, 50, 50)  # (k, j, i)
BACKGROUND_SATURATION = 0.20
INJECTED_BOUNDARY_SATURATION = 0.80
MAX_INCREMENTAL_CO2_SATURATION = 0.60
BREAKTHROUGH_GAS_CUT = 1.0e-4
TARGET_FINAL_STEP_INDEX = 4
MAX_TRIAL_RETRIES = 6
RETRY_FACTOR = 0.5

DAY_TO_S = 86400.0
PSI_TO_PA = 6894.757293168
FT_TO_M = 0.3048
CO2_RHO_REF_KG_M3 = 700.0
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0
INJECTOR_I = 24
INJECTOR_J = 24
COMPLETION_K = list(range(5, 10))
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}

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
R2_CACHE = "V16E35_R2_First_Accepted_Physics_Cache_Step0001.npz"
R2_EXPECTED_STATUS = "FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_ACCEPTED_R2"

V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
V16_FROZEN_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_BLOCKED_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
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


def sha256_array(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


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
    with zipfile.ZipFile(outer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_source_stage(path: Path, cwd: Path, label: str) -> None:
    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout, flush=True)
        raise GateError(f"{label}_source_execution_failed")
    tail = "\n".join(proc.stdout.splitlines()[-8:])
    print(f"\n[{label}] source-authentic execution PASS")
    if tail:
        print(tail, flush=True)


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = max(float(np.linalg.norm(b.ravel())), 1.0e-30)
    return float(np.linalg.norm((a - b).ravel()) / denom)


def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))


def bool_scalar(a: Any) -> bool:
    return bool(np.asarray(a).reshape(()))


def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))


def node_cell_indices(xyz_m: np.ndarray, sg7d: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xyz = np.asarray(xyz_m, dtype=np.float64)
    x = np.clip(xyz[..., 0], 0.0, float(sg7d.LX_M))
    y = np.clip(xyz[..., 1], 0.0, float(sg7d.LY_M))
    z = np.clip(xyz[..., 2], 0.0, float(sg7d.LZ_M))
    i = np.clip(np.floor(x / float(sg7d.DX_M)).astype(np.int64), 0, int(sg7d.NX) - 1)
    j = np.clip(np.floor(y / float(sg7d.DY_M)).astype(np.int64), 0, int(sg7d.NY) - 1)
    k = np.clip(np.floor(z / float(sg7d.DZ_M)).astype(np.int64), 0, int(sg7d.NZ) - 1)
    return k, j, i


def sample_grid_to_streamlines(grid_saturation: np.ndarray, node_kji: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    k, j, i = node_kji
    return np.asarray(grid_saturation, dtype=np.float64)[k, j, i]


def advance_streamline_advection(
    sg7a: Any,
    parent_streamline_saturation: np.ndarray,
    dt_days: float,
    tau_end_days: np.ndarray,
    xi: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    xi = np.asarray(xi, dtype=np.float64)
    old = np.asarray(parent_streamline_saturation, dtype=np.float64)
    tau = np.asarray(tau_end_days, dtype=np.float64)
    dxi = float(xi[1] - xi[0])
    u_face = np.asarray(sg7a.u_dimensionless(np.linspace(0.0, 1.0, len(xi) + 1)), dtype=np.float64)
    tD = float(dt_days) / tau
    new = np.empty_like(old)
    for s in range(old.shape[0]):
        new[s] = np.asarray(
            sg7a.advective_step(old[s], float(tD[s]), dxi, u_face),
            dtype=np.float64,
        )
    return new, tD


def producer_response(
    r2: Any,
    sg7a: Any,
    streamline_saturation: np.ndarray,
    labels: np.ndarray,
    weights_m3_s: np.ndarray,
    sg3_summary: dict[str, Any],
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    dt_days: float,
) -> tuple[list[dict[str, Any]], float, float]:
    outlet = np.asarray(streamline_saturation[:, -1], dtype=np.float64)
    ff = np.asarray(sg7a.fractional_flow(outlet), dtype=np.float64)
    labels = np.asarray(labels).astype(str)
    weights = np.asarray(weights_m3_s, dtype=np.float64)

    rows: list[dict[str, Any]] = []
    produced_mass = 0.0
    qprod_total = 0.0
    qprod_gas_weighted = 0.0

    for name in PRODUCERS:
        mask = labels == name
        if not np.any(mask):
            raise TrialReject(f"producer_missing_from_streamline_labels:{name}")
        w = weights[mask]
        cut = float(np.sum(w * ff[mask]) / np.sum(w))
        qprod = float(sg3_summary["producer_rates"][name]["m3_day"])
        qprod_total += qprod
        qprod_gas_weighted += qprod * cut

        sout = float(np.sum(w * outlet[mask]) / np.sum(w))
        sgout = max(0.0, min(MAX_INCREMENTAL_CO2_SATURATION, sout - BACKGROUND_SATURATION))
        pc_prod = float(r2.capillary_pressure_from_incremental_sg(sgout))
        p_g_prod_pa = 2000.0 * PSI_TO_PA + pc_prod
        rho_prod = float(
            CO2_RHO_REF_KG_M3
            * math.exp(
                max(-50.0, min(50.0, float(r2.CO2_COMPRESSIBILITY_1_PA) * (p_g_prod_pa - p_ref_gas_pa)))
            )
        )
        rate = qprod * cut * rho_prod
        produced = rate * float(dt_days)
        produced_mass += produced
        rows.append({
            "producer": name,
            "volumetric_rate_m3_day": qprod,
            "CO2_cut": cut,
            "outlet_transport_saturation": sout,
            "CO2_density_kg_m3": rho_prod,
            "CO2_mass_rate_kg_day": rate,
            "CO2_mass_this_step_kg": produced,
        })

    aggregate = qprod_gas_weighted / qprod_total if qprod_total > 0.0 else 0.0
    return rows, float(aggregate), float(produced_mass)


def incremental_mass_mapback(
    r2: Any,
    sg7d: Any,
    parent_grid_saturation: np.ndarray,
    old_streamline_saturation: np.ndarray,
    new_streamline_saturation: np.ndarray,
    operator: dict[str, np.ndarray],
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    cell_pore_volume_m3: float,
    target_final_mass_kg: float,
) -> dict[str, Any]:
    old_seg = np.asarray(sg7d.evaluate_subsegment_saturation(old_streamline_saturation, operator), dtype=np.float64)
    new_seg = np.asarray(sg7d.evaluate_subsegment_saturation(new_streamline_saturation, operator), dtype=np.float64)
    flat = np.asarray(operator["flat_cell"], dtype=np.int64)
    pv = np.asarray(operator["pv_m3"], dtype=np.float64)
    kk = np.asarray(operator["k"], dtype=np.int64)
    jj = np.asarray(operator["j"], dtype=np.int64)
    ii = np.asarray(operator["i"], dtype=np.int64)
    pseg = np.asarray(pressure_psi, dtype=np.float64)[kk, jj, ii]

    old_sg = np.clip(old_seg - BACKGROUND_SATURATION, 0.0, MAX_INCREMENTAL_CO2_SATURATION)
    new_sg = np.clip(new_seg - BACKGROUND_SATURATION, 0.0, MAX_INCREMENTAL_CO2_SATURATION)
    rho_old = np.asarray(r2.gas_density_from_state(old_seg, pseg, p_ref_gas_pa), dtype=np.float64)
    rho_new = np.asarray(r2.gas_density_from_state(new_seg, pseg, p_ref_gas_pa), dtype=np.float64)
    seg_delta_mass = pv * (rho_new * new_sg - rho_old * old_sg)

    ncell = int(np.prod(EXPECTED_GRID))
    deposited_delta_mass = np.bincount(flat, weights=seg_delta_mass, minlength=ncell).reshape(EXPECTED_GRID)

    parent_sat = np.asarray(parent_grid_saturation, dtype=np.float64)
    parent_sg = np.clip(parent_sat - BACKGROUND_SATURATION, 0.0, MAX_INCREMENTAL_CO2_SATURATION)
    parent_rho = np.asarray(r2.gas_density_from_state(parent_sat, pressure_psi, p_ref_gas_pa), dtype=np.float64)
    parent_mass = float(cell_pore_volume_m3) * parent_rho * parent_sg
    parent_total = float(np.sum(parent_mass))

    trial_mass = parent_mass + deposited_delta_mass
    roundoff = max(1.0e-6, 1.0e-10 * max(abs(float(target_final_mass_kg)), 1.0))
    min_mass = float(np.min(trial_mass))
    if min_mass < -roundoff:
        raise TrialReject(f"incremental_mapback_negative_cell_mass:{min_mass}")
    trial_mass = np.maximum(trial_mass, 0.0)

    path_final_total = float(np.sum(trial_mass))
    path_delta_mass = path_final_total - parent_total
    excess = path_final_total - float(target_final_mass_kg)
    if excess > roundoff:
        raise TrialReject(
            "incremental_path_mass_exceeds_available_component_mass:"
            f"{path_final_total}:{target_final_mass_kg}:{excess}"
        )

    injector_mask = np.zeros(EXPECTED_GRID, dtype=bool)
    for k in COMPLETION_K:
        injector_mask[k, INJECTOR_J, INJECTOR_I] = True

    max_sat = np.full(EXPECTED_GRID, INJECTED_BOUNDARY_SATURATION, dtype=np.float64)
    rho_max = np.asarray(r2.gas_density_from_state(max_sat, pressure_psi, p_ref_gas_pa), dtype=np.float64)
    capacity = float(cell_pore_volume_m3) * rho_max * MAX_INCREMENTAL_CO2_SATURATION

    if np.any(trial_mass - capacity > roundoff):
        raise TrialReject(
            f"incremental_mapback_cell_capacity_exceeded:{float(np.max(trial_mass-capacity))}"
        )

    missing = max(float(target_final_mass_kg) - path_final_total, 0.0)
    corrected_mass = trial_mass.copy()
    source_added = 0.0
    corrected_cells = 0
    if missing > roundoff:
        spare = np.maximum(capacity[injector_mask] - corrected_mass[injector_mask], 0.0)
        spare_total = float(np.sum(spare))
        if spare_total < missing - roundoff:
            raise TrialReject(
                f"continuation_injector_local_capacity_insufficient:{spare_total}:{missing}"
            )
        fraction = min(1.0, missing / max(spare_total, 1.0e-30))
        additions = fraction * spare
        corrected_mass[injector_mask] += additions
        source_added = float(np.sum(additions))
        corrected_cells = int(np.sum(additions > 1.0e-14))

    corrected_sg = np.asarray(
        r2._invert_incremental_sg_from_mass(
            corrected_mass,
            pressure_psi,
            p_ref_gas_pa,
            cell_pore_volume_m3,
        ),
        dtype=np.float64,
    )
    corrected_sat = BACKGROUND_SATURATION + corrected_sg
    final_mass = float(r2.stored_co2_mass_kg(
        corrected_sat, pressure_psi, p_ref_gas_pa, cell_pore_volume_m3
    ))
    residual = final_mass - float(target_final_mass_kg)
    if abs(residual) > roundoff:
        raise TrialReject(f"continuation_source_local_mass_closure_failed:{residual}:{roundoff}")

    return {
        "corrected_saturation": corrected_sat,
        "corrected_mass": corrected_mass,
        "parent_mass_kg": parent_total,
        "path_delta_mass_kg": float(path_delta_mass),
        "path_final_mass_kg": path_final_total,
        "target_final_mass_kg": float(target_final_mass_kg),
        "source_local_added_mass_kg": source_added,
        "source_local_corrected_cells": corrected_cells,
        "final_mass_kg": final_mass,
        "residual_kg": float(residual),
        "roundoff_mass_kg": float(roundoff),
        "deposited_delta_mass": deposited_delta_mass,
        "old_segment_saturation": old_seg,
        "new_segment_saturation": new_seg,
    }


def plume_metrics(
    r2: Any,
    saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    cell_pore_volume_m3: float,
    step_index: int,
    time_days: float,
) -> dict[str, Any]:
    sat = np.asarray(saturation, dtype=np.float64)
    sg = np.clip(sat - BACKGROUND_SATURATION, 0.0, MAX_INCREMENTAL_CO2_SATURATION)
    rho = np.asarray(r2.gas_density_from_state(sat, pressure_psi, p_ref_gas_pa), dtype=np.float64)
    mass = float(cell_pore_volume_m3) * rho * sg
    total = float(np.sum(mass))

    dz = 4.0 * FT_TO_M
    dy = 20.0 * FT_TO_M
    dx = 20.0 * FT_TO_M
    k = (np.arange(EXPECTED_GRID[0], dtype=np.float64) + 0.5) * dz
    j = (np.arange(EXPECTED_GRID[1], dtype=np.float64) + 0.5) * dy
    i = (np.arange(EXPECTED_GRID[2], dtype=np.float64) + 0.5) * dx
    zz, yy, xx = np.meshgrid(k, j, i, indexing="ij")

    if total > 0.0:
        cx = float(np.sum(mass * xx) / total)
        cy = float(np.sum(mass * yy) / total)
        cz = float(np.sum(mass * zz) / total)
    else:
        cx = cy = cz = float("nan")

    active = sg > 1.0e-8
    visible = sg > 1.0e-4
    return {
        "accepted_step_index": int(step_index),
        "time_days": float(time_days),
        "stored_CO2_mass_kg": total,
        "transport_saturation_min": float(np.min(sat)),
        "transport_saturation_max": float(np.max(sat)),
        "incremental_CO2_saturation_max": float(np.max(sg)),
        "active_cells_gt_1e-8": int(np.sum(active)),
        "plume_cells_gt_1e-4": int(np.sum(visible)),
        "mass_centroid_x_m": cx,
        "mass_centroid_y_m": cy,
        "mass_centroid_z_m": cz,
        "mass_in_injector_column_kg": float(np.sum(mass[:, INJECTOR_J, INJECTOR_I])),
    }


def make_child_state(
    parent: dict[str, np.ndarray],
    child_sat: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    dt_days: float,
    produced_mass_kg: float,
    aggregate_gas_cut: float,
    final_stored_mass_kg: float,
    step_mass_residual_kg: float,
    cache_reuse_certified: bool,
) -> dict[str, Any]:
    parent_time = scalar(parent["physical_time_days"])
    parent_step = int_scalar(parent["accepted_step_index"])
    new_time = parent_time + float(dt_days)
    new_step = parent_step + 1

    cum_inj = scalar(parent["cumulative_injected_co2_mass_kg"]) + INJECTOR_MASS_RATE_KG_DAY * float(dt_days)
    cum_prod = scalar(parent["cumulative_produced_co2_mass_kg"]) + float(produced_mass_kg)
    initial_stored = scalar(parent["stored_co2_mass_initial_kg"])
    cumulative_residual = final_stored_mass_kg - initial_stored - cum_inj + cum_prod

    prior_bt = bool_scalar(parent["breakthrough_reached"])
    current_bt = aggregate_gas_cut >= BREAKTHROUGH_GAS_CUT
    if current_bt and not prior_bt:
        raise TrialReject(
            f"breakthrough_encountered_during_E36_without_event_refinement:{new_time}:{aggregate_gas_cut}"
        )

    if prior_bt:
        bt_time = scalar(parent["breakthrough_time_days"])
        time_since_bt = new_time - bt_time
    else:
        bt_time = float("nan")
        time_since_bt = 0.0

    hist = np.maximum(np.asarray(parent["transport_saturation_history"], dtype=np.float64), child_sat)
    return {
        "physical_time_days": np.asarray(new_time, dtype=np.float64),
        "accepted_step_index": np.asarray(new_step, dtype=np.int64),
        "grid_shape": np.asarray(EXPECTED_GRID, dtype=np.int64),
        "background_saturation": np.asarray(BACKGROUND_SATURATION, dtype=np.float64),
        "injected_boundary_saturation": np.asarray(INJECTED_BOUNDARY_SATURATION, dtype=np.float64),
        "transport_saturation": np.asarray(child_sat, dtype=np.float64),
        "transport_saturation_history": hist.astype(np.float64),
        "co2_incremental_saturation": (np.asarray(child_sat, dtype=np.float64) - BACKGROUND_SATURATION),
        "initial_pressure_reference_psi": np.asarray(parent["initial_pressure_reference_psi"], dtype=np.float64),
        "accepted_pressure_psi": np.asarray(pressure_psi, dtype=np.float64),
        "f0_hidden_state": np.asarray(parent["f0_hidden_state"], dtype=np.float32).copy(),
        "cumulative_injected_co2_mass_kg": np.asarray(cum_inj, dtype=np.float64),
        "cumulative_produced_co2_mass_kg": np.asarray(cum_prod, dtype=np.float64),
        "cumulative_boundary_co2_mass_kg": np.asarray(0.0, dtype=np.float64),
        "stored_co2_mass_initial_kg": np.asarray(initial_stored, dtype=np.float64),
        "stored_co2_mass_current_kg": np.asarray(final_stored_mass_kg, dtype=np.float64),
        "last_step_mass_residual_kg": np.asarray(step_mass_residual_kg, dtype=np.float64),
        "cumulative_mass_residual_kg": np.asarray(cumulative_residual, dtype=np.float64),
        "current_producer_co2_gas_cut": np.asarray(aggregate_gas_cut, dtype=np.float64),
        "breakthrough_reached": np.asarray(prior_bt, dtype=bool),
        "breakthrough_time_days": np.asarray(bt_time, dtype=np.float64),
        "time_since_breakthrough_days": np.asarray(time_since_bt, dtype=np.float64),
        "last_accepted_dt_days": np.asarray(dt_days, dtype=np.float64),
        "last_accepted_dt_defined": np.asarray(True, dtype=bool),
        "observation_cursor_index": np.asarray(parent["observation_cursor_index"], dtype=np.int64),
        "next_fixed_observation_day": np.asarray(parent["next_fixed_observation_day"], dtype=np.float64),
        "path_cache_valid": np.asarray(True, dtype=bool),
        "tof_cache_valid": np.asarray(True, dtype=bool),
        "exact_retrace_required": np.asarray(False, dtype=bool),
        "cache_reuse_certified_under_reference_mobility": np.asarray(cache_reuse_certified, dtype=bool),
        "operational_pressure_state_ready": np.asarray(True, dtype=bool),
        "darcy_flux_state_ready": np.asarray(True, dtype=bool),
        "first_step_full_exact_preflight_required": np.asarray(False, dtype=bool),
        "first_transition_full_exact_cold_start_completed": np.asarray(True, dtype=bool),
        "f0_hidden_update_deferred_for_SGSim_feature_revalidation": np.asarray(True, dtype=bool),
        "co2_density_reference_pressure_pa": np.asarray(p_ref_gas_pa, dtype=np.float64),
        "co2_density_reference_kg_m3": np.asarray(parent["co2_density_reference_kg_m3"], dtype=np.float64),
        "co2_compressibility_1_pa": np.asarray(parent["co2_compressibility_1_pa"], dtype=np.float64),
    }


def validate_restart_bytes(data: bytes, expected_step: int, expected_time: float, expected_sat: np.ndarray) -> None:
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        if int(z["accepted_step_index"]) != int(expected_step):
            raise GateError(f"restart_step_index_mismatch:{z['accepted_step_index']}:{expected_step}")
        if float(z["physical_time_days"]) != float(expected_time):
            raise GateError(f"restart_time_mismatch:{z['physical_time_days']}:{expected_time}")
        if not np.array_equal(z["transport_saturation"], expected_sat):
            raise GateError("restart_saturation_not_byte_exact")
        if not bool(z["path_cache_valid"]) or not bool(z["tof_cache_valid"]):
            raise GateError("restart_cache_flags_invalid")
        if bool(z["exact_retrace_required"]):
            raise GateError("restart_unexpected_retrace_requirement_after_E36_certification")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    gates: dict[str, dict[str, Any]] = {}
    trial_failures: list[dict[str, Any]] = []
    parent_sha_before = None
    cache_sha_before = None
    frozen_sha_before = None
    current_step_for_failure = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 138)
        print("PAD-Stream V16E-36 — Short Adaptive SGSim Rollout / Early Plume Snapshot Validation")
        print("=" * 138)
        print("Restart parent : V16E-35-R2 accepted step 1")
        print("Target          : accepted step 4 (three continuation transitions)")
        print("Controller      : classical SG7A CFL x exact/certified fastest TOF; rejection -> dt/2")
        print("Cache policy    : mandatory exact retrace first, then reuse only if source-authentic invariance passes")
        print("F0 learned dt   : disabled / SGSim feature revalidation still pending")

        r2_path = root / R2_RUNNER
        gate("R2_runner_exists", r2_path.is_file(), r2_path)
        gate("R2_runner_SHA_exact", sha256_file(r2_path) == R2_RUNNER_SHA256, sha256_file(r2_path))
        r2 = load_module(r2_path, "pad_stream_v16e36_r2_authority")

        parent_dir = drive / R2_REL
        summary_path = parent_dir / R2_SUMMARY
        closure_path = parent_dir / R2_CLOSURE
        parent_state_path = parent_dir / R2_STATE
        parent_cache_path = parent_dir / R2_CACHE
        for p in [summary_path, closure_path, parent_state_path, parent_cache_path]:
            gate(f"R2_parent_artifact_exists_{p.name}", p.is_file(), p)

        r2_summary = load_json(summary_path)
        r2_closure = load_json(closure_path)
        gate("R2_status_accepted", r2_summary.get("status") == R2_EXPECTED_STATUS, r2_summary.get("status"))
        gate("R2_E36_entry_ready", r2_summary.get("E36_short_rollout_entry_ready") is True)
        gate("R2_closure_status_accepted", r2_closure.get("status") == R2_EXPECTED_STATUS, r2_closure.get("status"))
        gate("R2_closure_all_gates_passed", r2_closure.get("all_runtime_gates_passed") is True)

        parent_sha_before = sha256_file(parent_state_path)
        cache_sha_before = sha256_file(parent_cache_path)
        gate("R2_parent_state_SHA_matches_closure", parent_sha_before == r2_closure.get("child_state_sha256"), parent_sha_before)
        gate("R2_parent_cache_SHA_matches_closure", cache_sha_before == r2_closure.get("physics_cache_sha256"), cache_sha_before)

        parent = load_npz(parent_state_path)
        parent_cache = load_npz(parent_cache_path)
        gate("R2_parent_step_index_exact", int_scalar(parent["accepted_step_index"]) == 1, int_scalar(parent["accepted_step_index"]))
        gate("R2_parent_time_positive", scalar(parent["physical_time_days"]) > 0.0, scalar(parent["physical_time_days"]))
        gate("R2_parent_retrace_required", bool_scalar(parent["exact_retrace_required"]))
        gate("R2_parent_path_cache_valid", bool_scalar(parent["path_cache_valid"]))
        gate("R2_parent_tof_cache_valid", bool_scalar(parent["tof_cache_valid"]))
        gate("R2_parent_saturation_shape", np.asarray(parent["transport_saturation"]).shape == EXPECTED_GRID, np.asarray(parent["transport_saturation"]).shape)
        gate("R2_parent_prebreakthrough", not bool_scalar(parent["breakthrough_reached"]))

        frozen_100d = drive / V16_FROZEN_REL
        gate("frozen_100d_exists", frozen_100d.is_file(), frozen_100d)
        frozen_sha_before = sha256_file(frozen_100d)
        gate("frozen_100d_SHA_exact_before", frozen_sha_before == V16_FROZEN_SHA256, frozen_sha_before)

        required = [SGSIM_PERM, SG2, SG3, SG4, SG5, SG6, SG7A, SG7D]
        for rel in required:
            gate(f"source_exists_{rel}", (root / rel).is_file(), root / rel)

        # Mandatory exact retrace after the R2 accepted saturation change.
        print("\nMANDATORY E36 EXACT RETRACE / CACHE REVALIDATION")
        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E36_retrace_") as td:
            tmp = Path(td)
            for rel in required:
                shutil.copy2(root / rel, tmp / rel)
            for label, script in [("V15-SG2", SG2), ("V15-SG3", SG3), ("V15-SG4", SG4), ("V15-SG5", SG5), ("V15-SG6", SG6)]:
                run_source_stage(tmp / script, tmp, label)

            pressure_psi = np.load(tmp / "output/V15_SG3/PRESSURE_PSI.npy").astype(np.float64)
            qx = np.load(tmp / "output/V15_SG4/QX_M3_S.npy").astype(np.float64)
            qy = np.load(tmp / "output/V15_SG4/QY_M3_S.npy").astype(np.float64)
            qz = np.load(tmp / "output/V15_SG4/QZ_M3_S.npy").astype(np.float64)
            sg3_summary = load_json(tmp / "output/V15_SG3/PAD_Stream_V15SG3_Summary.json")
            with np.load(tmp / "output/V15_SG6/STREAMLINE_TRANSPORT_COORDINATES.npz", allow_pickle=False) as z:
                sg6 = {name: z[name].copy() for name in z.files}

            sg7a = load_module(tmp / SG7A, "pad_stream_v16e36_sg7a")
            sg7d = load_module(tmp / SG7D, "pad_stream_v16e36_sg7d")
            permeability_md = np.loadtxt(tmp / SGSIM_PERM, skiprows=1, dtype=np.float64).reshape(EXPECTED_GRID, order="C")

            labels = np.asarray(sg6["producer"]).astype(str)
            weights_m3_s = np.asarray(sg6["weights_m3_s"], dtype=np.float64)
            xyz_m = np.asarray(sg6["xyz_m"], dtype=np.float64)
            tau_s = np.asarray(sg6["tau_s"], dtype=np.float64)
            tau_end_s = np.asarray(sg6["tau_end_s"], dtype=np.float64)
            xi = np.asarray(sg6["xi"], dtype=np.float64)

            cache_metrics = {
                "pressure_relative_l2": relative_l2(pressure_psi, parent_cache["accepted_pressure_psi"]),
                "qx_relative_l2": relative_l2(qx, parent_cache["qx_m3_s"]),
                "qy_relative_l2": relative_l2(qy, parent_cache["qy_m3_s"]),
                "qz_relative_l2": relative_l2(qz, parent_cache["qz_m3_s"]),
                "xyz_relative_l2": relative_l2(xyz_m, parent_cache["streamline_xyz_m"]),
                "tof_relative_l2": relative_l2(tau_s, parent_cache["streamline_tof_s"]),
                "tau_end_relative_l2": relative_l2(tau_end_s, parent_cache["tau_end_s"]),
                "weights_relative_l2": relative_l2(weights_m3_s, parent_cache["streamline_weights_m3_s"]),
                "producer_labels_exact": bool(np.array_equal(labels, np.asarray(parent_cache["producer_labels"]).astype(str))),
            }
            for key, value in cache_metrics.items():
                if key == "producer_labels_exact":
                    gate(f"cache_revalidation_{key}", bool(value), value)
                else:
                    gate(f"cache_revalidation_{key}", float(value) <= 1.0e-12, value)

            cache_reuse_certified = True
            gate("cache_reuse_certified_under_current_reference_mobility_authority", cache_reuse_certified)
            gate(
                "cache_reuse_scope_not_generalized_to_future_multiphase_pressure",
                True,
                "Certification applies only while V15-SG3 steady reference-mobility pressure authority remains active.",
            )

            # Geometry/operator and CFL controller are frozen only for this E36 execution.
            tof_days = tau_s / DAY_TO_S
            weights_m3_day = weights_m3_s * DAY_TO_S
            operator = sg7d.build_subsegment_operator(xyz_m, tof_days, weights_m3_day)
            coverage = sg7d.build_coverage(operator)
            node_kji = node_cell_indices(xyz_m, sg7d)

            dxi = float(xi[1] - xi[0])
            sat_scan = np.linspace(sg7a.S_INITIAL, sg7a.S_INJECTED, 4001)
            max_df = float(np.max(np.abs(sg7a.df_dS(sat_scan))))
            u_face = np.asarray(sg7a.u_dimensionless(np.linspace(0.0, 1.0, len(xi) + 1)), dtype=np.float64)
            max_wave_speed = float(np.max(u_face) * max_df)
            dtD_cfl = float(sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS))
            tau_end_days = tau_end_s / DAY_TO_S
            fastest_tau_days = float(np.min(tau_end_days))
            nominal_dt_days = float(dtD_cfl * fastest_tau_days)
            gate("E36_nominal_dt_positive", np.isfinite(nominal_dt_days) and nominal_dt_days > 0.0, nominal_dt_days)

            injection_pc = float(r2.capillary_pressure_from_incremental_sg(MAX_INCREMENTAL_CO2_SATURATION))
            injector_pw_pa = np.array(
                [pressure_psi[k, INJECTOR_J, INJECTOR_I] * PSI_TO_PA for k in COMPLETION_K],
                dtype=np.float64,
            )
            p_ref_gas_pa = float(np.mean(injector_pw_pa) + injection_pc)
            gate(
                "R2_density_reference_pressure_reproduced",
                abs(p_ref_gas_pa - scalar(parent["co2_density_reference_pressure_pa"])) <= 1.0e-8,
                f"{p_ref_gas_pa}:{scalar(parent['co2_density_reference_pressure_pa'])}",
            )

            dx_m, dy_m, dz_m = 20.0 * FT_TO_M, 20.0 * FT_TO_M, 4.0 * FT_TO_M
            cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m
            recomputed_parent_mass = float(r2.stored_co2_mass_kg(
                np.asarray(parent["transport_saturation"], dtype=np.float64),
                pressure_psi,
                p_ref_gas_pa,
                cell_pore_volume_m3,
            ))
            parent_mass_tol = max(
                1.0e-6,
                1.0e-10 * max(abs(scalar(parent["stored_co2_mass_current_kg"])), 1.0),
            )
            gate(
                "R2_parent_stored_mass_recomputed_exactly_under_E36_authority",
                abs(recomputed_parent_mass - scalar(parent["stored_co2_mass_current_kg"])) <= parent_mass_tol,
                f"{recomputed_parent_mass - scalar(parent['stored_co2_mass_current_kg']):.12e} kg",
            )

            accepted_states: list[dict[str, Any]] = [parent]
            snapshot_sats: list[np.ndarray] = [np.asarray(parent["transport_saturation"], dtype=np.float64).copy()]
            snapshot_steps = [int_scalar(parent["accepted_step_index"])]
            snapshot_times = [scalar(parent["physical_time_days"])]
            plume_rows: list[dict[str, Any]] = [
                plume_metrics(
                    r2,
                    parent["transport_saturation"],
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    int_scalar(parent["accepted_step_index"]),
                    scalar(parent["physical_time_days"]),
                )
            ]
            step_rows: list[dict[str, Any]] = []
            producer_rows_all: list[dict[str, Any]] = []
            child_file_bytes: dict[str, bytes] = {}

            current = parent
            for target_step in range(2, TARGET_FINAL_STEP_INDEX + 1):
                current_step_for_failure = target_step
                current_time = scalar(current["physical_time_days"])
                next_obs = scalar(current["next_fixed_observation_day"])
                nominal = min(nominal_dt_days, max(next_obs - current_time, 0.0))
                if nominal <= 0.0:
                    raise GateError(f"E36_no_positive_time_before_observation_step_{target_step}")

                mode = "EXACT_RETRACE" if target_step == 2 else "CERTIFIED_CACHE_REUSE"
                accepted = False
                rejection_reasons: list[str] = []

                for retry in range(MAX_TRIAL_RETRIES + 1):
                    dt_days = nominal * (RETRY_FACTOR ** retry)
                    try:
                        parent_sat = np.asarray(current["transport_saturation"], dtype=np.float64)
                        old_stream = sample_grid_to_streamlines(parent_sat, node_kji)
                        if not np.all(np.isfinite(old_stream)):
                            raise TrialReject("sampled_parent_streamline_state_nonfinite")
                        if float(np.min(old_stream)) < BACKGROUND_SATURATION - 1.0e-10 or float(np.max(old_stream)) > INJECTED_BOUNDARY_SATURATION + 1.0e-10:
                            raise TrialReject("sampled_parent_streamline_state_out_of_bounds")

                        new_stream, tD = advance_streamline_advection(
                            sg7a, old_stream, dt_days, tau_end_days, xi
                        )
                        if not np.all(np.isfinite(new_stream)):
                            raise TrialReject("continuation_streamline_state_nonfinite")
                        if float(np.min(new_stream)) < BACKGROUND_SATURATION - 1.0e-10 or float(np.max(new_stream)) > INJECTED_BOUNDARY_SATURATION + 1.0e-10:
                            raise TrialReject("continuation_streamline_state_out_of_bounds")

                        prod_rows, aggregate_cut, produced_step = producer_response(
                            r2, sg7a, new_stream, labels, weights_m3_s,
                            sg3_summary, pressure_psi, p_ref_gas_pa, dt_days,
                        )
                        if not (0.0 <= aggregate_cut <= 1.0) or not np.isfinite(aggregate_cut):
                            raise TrialReject(f"producer_CO2_cut_invalid:{aggregate_cut}")

                        injected_step = INJECTOR_MASS_RATE_KG_DAY * dt_days
                        parent_stored = scalar(current["stored_co2_mass_current_kg"])
                        target_final_mass = parent_stored + injected_step - produced_step
                        if target_final_mass <= parent_stored:
                            raise TrialReject(f"nonpositive_preBT_storage_increment:{target_final_mass-parent_stored}")

                        mapping = incremental_mass_mapback(
                            r2, sg7d,
                            parent_sat,
                            old_stream,
                            new_stream,
                            operator,
                            pressure_psi,
                            p_ref_gas_pa,
                            cell_pore_volume_m3,
                            target_final_mass,
                        )
                        if float(np.max(tD)) > dtD_cfl * (1.0 + 1.0e-12):
                            raise TrialReject(
                                f"continuation_CFL_violation:{float(np.max(tD))}:{dtD_cfl}"
                            )
                        if mapping["path_delta_mass_kg"] < -mapping["roundoff_mass_kg"]:
                            raise TrialReject(
                                f"preBT_path_delta_mass_negative:{mapping['path_delta_mass_kg']}"
                            )
                        if mapping["source_local_added_mass_kg"] > injected_step + mapping["roundoff_mass_kg"]:
                            raise TrialReject(
                                "source_local_closure_exceeds_physical_step_injection:"
                                f"{mapping['source_local_added_mass_kg']}:{injected_step}"
                            )

                        capillary = r2.conservative_capillary_mass_redistribution(
                            transport_saturation=mapping["corrected_saturation"],
                            permeability_md=permeability_md,
                            pressure_psi=pressure_psi,
                            p_ref_pa=p_ref_gas_pa,
                            cell_pore_volume_m3=cell_pore_volume_m3,
                            dt_seconds=dt_days * DAY_TO_S,
                        )
                        child_sat = np.asarray(capillary["corrected"], dtype=np.float64)
                        final_stored = float(capillary["final_mass_state_kg"])
                        closure_tol = max(1.0e-6, 1.0e-10 * max(abs(target_final_mass), 1.0))
                        step_resid = final_stored - parent_stored - injected_step + produced_step

                        if abs(float(capillary["external_mass_change_kg"])) > closure_tol:
                            raise TrialReject(f"capillary_external_mass_change:{capillary['external_mass_change_kg']}:{closure_tol}")
                        if abs(float(capillary["state_inversion_residual_kg"])) > closure_tol:
                            raise TrialReject(f"capillary_state_inversion_residual:{capillary['state_inversion_residual_kg']}:{closure_tol}")
                        if abs(step_resid) > closure_tol:
                            raise TrialReject(f"step_mass_closure:{step_resid}:{closure_tol}")
                        if float(np.min(child_sat)) < BACKGROUND_SATURATION - 1.0e-12 or float(np.max(child_sat)) > INJECTED_BOUNDARY_SATURATION + 1.0e-12:
                            raise TrialReject(f"child_saturation_bounds:{np.min(child_sat)}:{np.max(child_sat)}")

                        child = make_child_state(
                            current,
                            child_sat,
                            pressure_psi,
                            p_ref_gas_pa,
                            dt_days,
                            produced_step,
                            aggregate_cut,
                            final_stored,
                            step_resid,
                            cache_reuse_certified,
                        )

                        new_time = scalar(child["physical_time_days"])
                        if not (new_time > current_time and new_time <= next_obs + 1.0e-12):
                            raise TrialReject(f"accepted_time_invalid:{current_time}:{new_time}:{next_obs}")

                        state_bytes = deterministic_npz_bytes(child)
                        validate_restart_bytes(state_bytes, target_step, new_time, child_sat)

                        step_name = f"V16E36_Accepted_SGSim_Runtime_State_Step{target_step:04d}.npz"
                        child_file_bytes[step_name] = state_bytes
                        accepted_states.append(child)
                        snapshot_sats.append(child_sat.copy())
                        snapshot_steps.append(target_step)
                        snapshot_times.append(new_time)
                        plume_rows.append(plume_metrics(
                            r2, child_sat, pressure_psi, p_ref_gas_pa,
                            cell_pore_volume_m3, target_step, new_time,
                        ))

                        for row in prod_rows:
                            producer_rows_all.append({
                                "accepted_step_index": target_step,
                                "time_days": new_time,
                                **row,
                            })

                        cumulative_residual = scalar(child["cumulative_mass_residual_kg"])
                        step_rows.append({
                            "accepted_step_index": target_step,
                            "parent_time_days": current_time,
                            "accepted_time_days": new_time,
                            "accepted_dt_days": dt_days,
                            "nominal_dt_days": nominal,
                            "retry_count": retry,
                            "flow_path_mode": mode,
                            "cache_reuse_certified": cache_reuse_certified,
                            "dimensionless_dt_max": float(np.max(tD)),
                            "injected_CO2_mass_kg": injected_step,
                            "produced_CO2_mass_kg": produced_step,
                            "path_delta_mass_kg": mapping["path_delta_mass_kg"],
                            "source_local_added_mass_kg": mapping["source_local_added_mass_kg"],
                            "source_local_corrected_cells": mapping["source_local_corrected_cells"],
                            "capillary_substeps": int(capillary["substeps"]),
                            "capillary_external_mass_change_kg": float(capillary["external_mass_change_kg"]),
                            "stored_CO2_mass_kg": final_stored,
                            "step_mass_residual_kg": step_resid,
                            "cumulative_mass_residual_kg": cumulative_residual,
                            "producer_CO2_gas_cut": aggregate_cut,
                            "breakthrough_reached": bool_scalar(child["breakthrough_reached"]),
                        })
                        gates[f"E36_step_{target_step}_accepted"] = {
                            "passed": True,
                            "detail": f"t={new_time:.12g} d, dt={dt_days:.12g} d, retry={retry}",
                        }
                        gates[f"E36_step_{target_step}_mass_closure"] = {
                            "passed": True,
                            "detail": f"{step_resid:.12e} kg",
                        }
                        current = child
                        accepted = True
                        print(
                            f"[ACCEPT] step {target_step}: t={new_time:.12g} d, "
                            f"dt={dt_days:.12g} d, retries={retry}, "
                            f"mass residual={step_resid:.3e} kg, mode={mode}"
                        )
                        break

                    except TrialReject as exc:
                        rejection_reasons.append(repr(exc))
                        trial_failures.append({
                            "target_step": target_step,
                            "retry": retry,
                            "trial_dt_days": dt_days,
                            "reason": repr(exc),
                        })
                        print(f"[REJECT] step {target_step} retry {retry}: {exc}")
                        if retry >= MAX_TRIAL_RETRIES:
                            raise GateError(
                                f"E36_step_{target_step}_retry_budget_exhausted:{rejection_reasons[-1]}"
                            )

                if not accepted:
                    raise GateError(f"E36_step_{target_step}_not_accepted")

            final_state = current
            final_step = int_scalar(final_state["accepted_step_index"])
            final_time = scalar(final_state["physical_time_days"])
            gate("E36_final_step_index_exact", final_step == TARGET_FINAL_STEP_INDEX, final_step)
            gate("E36_final_time_pre_30d_observation", final_time < 30.0, final_time)
            gate("E36_no_breakthrough", not bool_scalar(final_state["breakthrough_reached"]), scalar(final_state["current_producer_co2_gas_cut"]))
            gate("E36_history_monotone_by_definition", np.all(np.asarray(final_state["transport_saturation_history"]) >= np.asarray(parent["transport_saturation_history"]) - 1.0e-15))

            final_cum_resid = scalar(final_state["cumulative_mass_residual_kg"])
            final_mass = scalar(final_state["stored_co2_mass_current_kg"])
            final_tol = max(1.0e-6, 1.0e-10 * max(abs(final_mass), 1.0))
            gate("E36_cumulative_mass_closure_numeric", abs(final_cum_resid) <= final_tol, f"{final_cum_resid}:{final_tol}")
            gate("E36_parent_state_unchanged", sha256_file(parent_state_path) == parent_sha_before, sha256_file(parent_state_path))
            gate("E36_parent_cache_unchanged", sha256_file(parent_cache_path) == cache_sha_before, sha256_file(parent_cache_path))
            gate("E36_frozen_100d_unchanged", sha256_file(frozen_100d) == frozen_sha_before, sha256_file(frozen_100d))

            certified_cache_arrays = {
                "certified_at_parent_step_index": np.asarray(1, dtype=np.int64),
                "certified_by_E36_exact_retrace": np.asarray(True, dtype=bool),
                "reuse_scope_reference_mobility_only": np.asarray(True, dtype=bool),
                "accepted_pressure_psi": pressure_psi.astype(np.float64),
                "qx_m3_s": qx.astype(np.float64),
                "qy_m3_s": qy.astype(np.float64),
                "qz_m3_s": qz.astype(np.float64),
                "streamline_xyz_m": xyz_m.astype(np.float64),
                "streamline_tof_s": tau_s.astype(np.float64),
                "tau_end_s": tau_end_s.astype(np.float64),
                "streamline_weights_m3_s": weights_m3_s.astype(np.float64),
                "producer_labels": labels.astype("U32"),
                "xi": xi.astype(np.float64),
            }
            cache_bytes = deterministic_npz_bytes(certified_cache_arrays)

            snapshot_bytes = deterministic_npz_bytes({
                "accepted_step_index": np.asarray(snapshot_steps, dtype=np.int64),
                "physical_time_days": np.asarray(snapshot_times, dtype=np.float64),
                "transport_saturation": np.stack(snapshot_sats, axis=0).astype(np.float64),
            })

            cache_report = {
                "milestone": MILESTONE,
                "status": "CACHE_REUSE_CERTIFIED_UNDER_CURRENT_REFERENCE_MOBILITY_AUTHORITY",
                "mandatory_retrace_performed": True,
                "parent_requested_exact_retrace": True,
                "comparison_to_R2_cache": cache_metrics,
                "reuse_certified": True,
                "reuse_scope": "V15-SG3 steady reference-mobility pressure authority with unchanged SGSim geology/wells/rates only",
                "not_certified_for": "future saturation-dependent/multiphase pressure authority",
                "step_2_mode": "EXACT_RETRACE",
                "steps_3_to_4_mode": "CERTIFIED_CACHE_REUSE",
            }

            controller_contract = {
                "milestone": MILESTONE,
                "status": "SGSIM_CLASSICAL_ADAPTIVE_CONTROLLER_VALIDATED_FOR_SHORT_ROLLOUT",
                "nominal_rule": "dt = SG7A_CFL_dimensionless_dt * fastest_exact_or_certified_terminal_TOF",
                "nominal_dt_days": nominal_dt_days,
                "rejection_policy": "trial rejection leaves accepted state unchanged; retry with dt_new = 0.5 * dt_old",
                "maximum_retries_per_transition": MAX_TRIAL_RETRIES,
                "observation_clip": "never cross next_fixed_observation_day",
                "V15_numeric_dt_bounds_inherited": False,
                "learned_F0_timestep_proposal_used": False,
                "F0_hidden_update": "deferred pending SGSim feature revalidation/retraining",
                "production_dt_envelope_frozen": False,
                "production_mass_tolerance_frozen": False,
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "parent_milestone": "V16E-35-R2",
                "parent_state_sha256": parent_sha_before,
                "parent_cache_sha256": cache_sha_before,
                "initial_step_index": 1,
                "final_accepted_step_index": final_step,
                "continuation_transitions_executed": TARGET_FINAL_STEP_INDEX - 1,
                "initial_time_days": snapshot_times[0],
                "final_time_days": final_time,
                "accepted_dt_days": [float(r["accepted_dt_days"]) for r in step_rows],
                "nominal_dt_days": nominal_dt_days,
                "total_rejected_trials": len(trial_failures),
                "mandatory_exact_retrace_performed": True,
                "cache_reuse_certified": True,
                "cache_reuse_scope_reference_mobility_only": True,
                "cache_reuse_transitions": sum(1 for r in step_rows if r["flow_path_mode"] == "CERTIFIED_CACHE_REUSE"),
                "exact_retrace_transitions": sum(1 for r in step_rows if r["flow_path_mode"] == "EXACT_RETRACE"),
                "classical_adaptive_controller_used": True,
                "learned_timestep_proposal_used": False,
                "F0_hidden_update_deferred": True,
                "V15_numeric_dt_bounds_inherited_without_revalidation": False,
                "SGSim_specific_dt_envelope_frozen": False,
                "SGSim_specific_mass_tolerance_frozen": False,
                "source_conservative_continuation_transport_executed": True,
                "incremental_mass_mapback_executed": True,
                "injector_local_mass_closure_executed": True,
                "conservative_grid_capillary_mass_redistribution_executed": True,
                "capillary_external_mass_source_kg_max_abs": max(abs(float(r["capillary_external_mass_change_kg"])) for r in step_rows),
                "cumulative_injected_CO2_mass_kg": scalar(final_state["cumulative_injected_co2_mass_kg"]),
                "cumulative_produced_CO2_mass_kg": scalar(final_state["cumulative_produced_co2_mass_kg"]),
                "stored_CO2_mass_kg": final_mass,
                "cumulative_mass_residual_kg": final_cum_resid,
                "mass_numerical_closure_passed": abs(final_cum_resid) <= final_tol,
                "breakthrough_reached": bool_scalar(final_state["breakthrough_reached"]),
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "early_plume_snapshot_count": len(snapshot_steps),
                "observation_checkpoint_reached": False,
                "next_fixed_observation_day": scalar(final_state["next_fixed_observation_day"]),
                "E37_extended_rollout_entry_ready": True,
                "frozen_100d_checkpoint_modified": False,
                "IBDP_started": False,
            }

            handoff = f"""# PAD-Stream V16E-36 Handoff\n\nV16E-36 is the first multi-step SGSim runtime rollout. It restarts from the accepted V16E-35-R2 child and advances three additional accepted transitions to step {final_step}.\n\nThe mandatory first continuation transition performs an exact SG2->SG6 retrace because the R2 child explicitly required it. That retrace reproduces the R2 pressure/Darcy/Pollock/TOF cache to the frozen numerical tolerances. Cache reuse is therefore certified only under the current V15-SG3 steady reference-mobility pressure authority; this is not a claim that a future saturation-dependent multiphase pressure solve may reuse the same paths.\n\nContinuation transport does not restart the plume from t=0. The accepted Cartesian parent is sampled onto the exact streamline nodes, SG7A conservative compressible Godunov advection advances only the new dt, and the incremental CO2-mass change is mapped through the exact SG7D subsegment geometry. Any finite source inventory not represented downstream closes only in the five injector completion cells. The no-flow Cartesian capillary operator then redistributes mass internally with zero external capillary source.\n\nAdaptive-controller contract:\n- nominal dt = SG7A dimensionless CFL dt x fastest exact/certified terminal TOF;\n- no inherited V15 0.10-2.00 day dt box;\n- trial rejection does not mutate the accepted state;\n- retry is dt/2, up to {MAX_TRIAL_RETRIES} retries;\n- fixed observations are hard time clips;\n- F0 learned dt remains disabled pending SGSim feature revalidation.\n\nAccepted rollout:\n- initial step/time: 1 / {snapshot_times[0]:.12g} d\n- final step/time: {final_step} / {final_time:.12g} d\n- transitions executed: {TARGET_FINAL_STEP_INDEX - 1}\n- rejected trials: {len(trial_failures)}\n- cumulative mass residual: {final_cum_resid:.12e} kg\n- breakthrough reached: {bool_scalar(final_state['breakthrough_reached'])}\n- next observation remains: {scalar(final_state['next_fixed_observation_day']):.12g} d\n\nThe production SGSim dt envelope and final runtime mass tolerance remain unfrozen. E37 extends this validated restart/controller path toward the first fixed observation checkpoint.\n\nNEXT: {NEXT}\n"""

            files: dict[str, bytes] = {}
            files.update(child_file_bytes)
            files["V16E36_Certified_Physics_Cache.npz"] = cache_bytes
            files["V16E36_Early_Plume_Snapshots.npz"] = snapshot_bytes
            files["V16E36_Rollout_Step_Audit.csv"] = csv_bytes(step_rows)
            files["V16E36_Producer_CO2_Response.csv"] = csv_bytes(producer_rows_all)
            files["V16E36_Early_Plume_Metrics.csv"] = csv_bytes(plume_rows)
            files["V16E36_Cache_Revalidation.json"] = json_bytes(cache_report)
            files["V16E36_SGSim_Adaptive_Controller_Contract.json"] = json_bytes(controller_contract)
            files["V16E36_Trial_Rejection_Audit.csv"] = csv_bytes(trial_failures)
            files["PAD_Stream_V16E36_Summary.json"] = json_bytes(summary)
            files["V16E36_Handoff.md"] = handoff.encode("utf-8")
            files["V16E36_Final_Gate_Matrix.csv"] = csv_bytes([{"gate": k, **v} for k, v in gates.items()])

            # Final state is the last step file already present in child_file_bytes.
            final_state_name = f"V16E36_Accepted_SGSim_Runtime_State_Step{final_step:04d}.npz"
            final_state_sha = hashlib.sha256(files[final_state_name]).hexdigest()
            cache_sha = hashlib.sha256(cache_bytes).hexdigest()
            snapshots_sha = hashlib.sha256(snapshot_bytes).hexdigest()

            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed": all(v["passed"] for v in gates.values()),
                "gate_count": len(gates),
                "final_state_file": final_state_name,
                "final_state_sha256": final_state_sha,
                "certified_cache_sha256": cache_sha,
                "early_plume_snapshots_sha256": snapshots_sha,
                "R2_parent_state_sha256": parent_sha_before,
                "R2_parent_cache_sha256": cache_sha_before,
                "frozen_100d_sha256": frozen_sha_before,
            }
            files["V16E36_Final_Closure.json"] = json_bytes(closure)

            immutable_publish(out, files)

            artifact_rows = []
            for path in sorted(out.iterdir()):
                if path.is_file() and path.name != "V16E36_Artifact_Manifest.csv":
                    artifact_rows.append({
                        "file": path.name,
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    })
            immutable_publish(out, {"V16E36_Artifact_Manifest.csv": csv_bytes(artifact_rows)})

        print("\n" + "=" * 138)
        print("PAD-Stream V16E-36 SHORT ADAPTIVE SGSIM ROLLOUT: PASS")
        print("=" * 138)
        print(f"{'Parent step/time':78}: 1 / {snapshot_times[0]:.12g} d")
        print(f"{'Final accepted step/time':78}: {final_step} / {final_time:.12g} d")
        print(f"{'Continuation transitions':78}: {TARGET_FINAL_STEP_INDEX - 1}")
        print(f"{'Nominal classical dt':78}: {nominal_dt_days:.12g} d")
        print(f"{'Rejected trials':78}: {len(trial_failures)}")
        print(f"{'Exact retrace transitions':78}: {sum(1 for r in step_rows if r['flow_path_mode'] == 'EXACT_RETRACE')}")
        print(f"{'Certified cache reuse transitions':78}: {sum(1 for r in step_rows if r['flow_path_mode'] == 'CERTIFIED_CACHE_REUSE')}")
        print(f"{'Cumulative injected CO2 mass':78}: {scalar(final_state['cumulative_injected_co2_mass_kg']):.12e} kg")
        print(f"{'Stored CO2 mass':78}: {final_mass:.12e} kg")
        print(f"{'Cumulative mass residual':78}: {final_cum_resid:.12e} kg")
        print(f"{'Breakthrough reached':78}: NO")
        print(f"{'Next fixed observation':78}: {scalar(final_state['next_fixed_observation_day']):.12g} d")
        print(f"{'E37 extended rollout entry ready':78}: YES")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "SHORT_ADAPTIVE_SGSIM_ROLLOUT_BLOCKED",
            "exception": repr(exc),
            "failed_target_step": current_step_for_failure,
            "gates": gates,
            "trial_failures": trial_failures,
            "R2_parent_state": str((drive / R2_REL / R2_STATE)),
            "R2_parent_state_sha256_before": parent_sha_before,
            "R2_parent_cache_sha256_before": cache_sha_before,
            "frozen_100d_sha256_before": frozen_sha_before,
            "accepted_E36_children_published": False,
            "runtime_time_advance_committed_to_persistent_state": False,
            "R2_parent_mutated": False,
            "frozen_100d_modified": False,
            "next_action": "Audit the failed gate/trial. Do not advance to V16E-37.",
        }
        data = json_bytes(report)
        path = blocked / "V16E36_Blocked_Short_Adaptive_Rollout.json"
        if path.exists() and path.read_bytes() != data:
            path = blocked / f"V16E36_Blocked_Short_Adaptive_Rollout_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not path.exists():
            path.write_bytes(data)
        print("\n" + "=" * 138)
        print("PAD-Stream V16E-36 SHORT ADAPTIVE SGSIM ROLLOUT: BLOCKED")
        print("=" * 138)
        print("Reason:", repr(exc))
        print("No E36 accepted child state was published by this failed milestone execution.")
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
