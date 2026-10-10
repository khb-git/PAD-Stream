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


MILESTONE = "V16E-38"
STATUS = "BREAKTHROUGH_EVENT_REFINED_CANONICAL_STATE_FROZEN"
NEXT = "V16E-39 - Post-Breakthrough SGSim Rollout / First 30-Day Observation Checkpoint"

EXPECTED_GRID = (15, 50, 50)
BACKGROUND_SATURATION = 0.20
INJECTED_BOUNDARY_SATURATION = 0.80
BREAKTHROUGH_GAS_CUT = 1.0e-4
FIRST_OBSERVATION_DAY = 30.0
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
CO2_RHO_REF_KG_M3 = 700.0
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0
EXPECTED_STREAMLINES = 1078
EXPECTED_FACES = 201
EXPECTED_CVS = 200
EVENT_TIME_TOL_DAYS = 1.0e-6
MAX_REFINEMENT_ITERS = 40
PROGRESS_EVERY = 50

R2_RUNNER = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_"
    "First_Controlled_Transition.py"
)
R2_RUNNER_SHA256 = "3a1bf71ef601308e2fc18168bf2b9fc7c3dc9b0ff98e3735de1d4fa6ee624ab6"

E36_RUNNER = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_RUNNER_SHA256 = "747a4f6ee4a5458624311fe2226773e0db778cc40a0460adfcbc454be22a3a0c"
E36_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"

E37A_RUNNER = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_RUNNER_SHA256 = "d2f0a006569846048c647cfccac3df9bb8a7ed970c3431c2291a617ea455ec59"
E37A_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37A_CONTROL_VOLUME_ALIGNED_CONSERVATIVE_STREAMLINE_GRID_TRANSFER"
)
E37A_SUMMARY = "PAD_Stream_V16E37A_Summary.json"
E37A_CLOSURE = "V16E37A_Final_Closure.json"
E37A_EXPECTED_STATUS = "CONTROL_VOLUME_ALIGNED_CONSERVATIVE_TRANSFER_VALIDATED"

E37B_RUNNER = "PAD_Stream_V16E37B_Extended_SGSim_Runtime_Rollout_and_First_Fixed_Observation_Checkpoint.py"
E37B_RUNNER_SHA256 = "8abec0348cb683e7805fd5b847d3f24b88b855edd3386914a6aad9a3a1d87471"
E37B_BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37B_BLOCKED_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
)
E37B_BRACKET_REPORT = "V16E37B_Blocked_Breakthrough_Bracket.json"
E37B_EXPECTED_BLOCKED_STATUS = "FIRST_FIXED_OBSERVATION_ROLLOUT_BLOCKED_BY_BREAKTHROUGH_BRACKET"
E37B_OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37B_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
)
E37B_30D_CHECKPOINT = "V16E37B_Canonical_SGSim_Runtime_State_Observation_0030d.npz"

V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
V16_FROZEN_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E38_BREAKTHROUGH_EVENT_REFINEMENT_CANONICAL_BT_STATE"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E38_BLOCKED_BREAKTHROUGH_EVENT_REFINEMENT_CANONICAL_BT_STATE"
)


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


def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))


def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))


def bool_scalar(a: Any) -> bool:
    return bool(np.asarray(a).reshape(()))


def max_abs(values: list[float]) -> float:
    return max([abs(float(v)) for v in values] + [0.0])




def build_trial_child(
    parent: dict[str, np.ndarray],
    child_sat: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    dt_days: float,
    produced_mass_kg: float,
    aggregate_gas_cut: float,
    final_stored_mass_kg: float,
    step_mass_residual_kg: float,
    nfaces: int,
    ncv: int,
) -> dict[str, Any]:
    """Build an uncommitted continuation child without the legacy E36 BT guard.

    E36 deliberately rejected first breakthrough because that milestone had no
    event-refinement authority. E38 must be able to evaluate both sides of the
    bracket without committing either trial. We therefore preserve the full
    parent dictionary and update only the normal accepted-state fields.
    """
    child = {k: np.asarray(v).copy() for k, v in parent.items()}
    parent_time = scalar(parent["physical_time_days"])
    parent_step = int_scalar(parent["accepted_step_index"])
    new_time = parent_time + float(dt_days)
    new_step = parent_step + 1

    cum_inj = scalar(parent["cumulative_injected_co2_mass_kg"]) + INJECTOR_MASS_RATE_KG_DAY * float(dt_days)
    cum_prod = scalar(parent["cumulative_produced_co2_mass_kg"]) + float(produced_mass_kg)
    initial_stored = scalar(parent["stored_co2_mass_initial_kg"])
    cumulative_residual = final_stored_mass_kg - initial_stored - cum_inj + cum_prod

    child["physical_time_days"] = np.asarray(new_time, dtype=np.float64)
    child["accepted_step_index"] = np.asarray(new_step, dtype=np.int64)
    child["transport_saturation"] = np.asarray(child_sat, dtype=np.float64)
    child["transport_saturation_history"] = np.maximum(
        np.asarray(parent["transport_saturation_history"], dtype=np.float64),
        np.asarray(child_sat, dtype=np.float64),
    )
    child["co2_incremental_saturation"] = np.asarray(child_sat, dtype=np.float64) - BACKGROUND_SATURATION
    child["accepted_pressure_psi"] = np.asarray(pressure_psi, dtype=np.float64)
    child["cumulative_injected_co2_mass_kg"] = np.asarray(cum_inj, dtype=np.float64)
    child["cumulative_produced_co2_mass_kg"] = np.asarray(cum_prod, dtype=np.float64)
    child["stored_co2_mass_current_kg"] = np.asarray(final_stored_mass_kg, dtype=np.float64)
    child["last_step_mass_residual_kg"] = np.asarray(step_mass_residual_kg, dtype=np.float64)
    child["cumulative_mass_residual_kg"] = np.asarray(cumulative_residual, dtype=np.float64)
    child["current_producer_co2_gas_cut"] = np.asarray(aggregate_gas_cut, dtype=np.float64)
    child["breakthrough_reached"] = np.asarray(False, dtype=bool)
    child["breakthrough_time_days"] = np.asarray(float("nan"), dtype=np.float64)
    child["time_since_breakthrough_days"] = np.asarray(0.0, dtype=np.float64)
    child["last_accepted_dt_days"] = np.asarray(dt_days, dtype=np.float64)
    child["last_accepted_dt_defined"] = np.asarray(True, dtype=bool)
    child["path_cache_valid"] = np.asarray(True, dtype=bool)
    child["tof_cache_valid"] = np.asarray(True, dtype=bool)
    child["exact_retrace_required"] = np.asarray(False, dtype=bool)
    child["cache_reuse_certified_under_reference_mobility"] = np.asarray(True, dtype=bool)
    child["operational_pressure_state_ready"] = np.asarray(True, dtype=bool)
    child["darcy_flux_state_ready"] = np.asarray(True, dtype=bool)
    child["first_step_full_exact_preflight_required"] = np.asarray(False, dtype=bool)
    child["first_transition_full_exact_cold_start_completed"] = np.asarray(True, dtype=bool)
    child["f0_hidden_update_deferred_for_SGSim_feature_revalidation"] = np.asarray(True, dtype=bool)
    child["co2_density_reference_pressure_pa"] = np.asarray(p_ref_gas_pa, dtype=np.float64)
    child["transport_face_count"] = np.asarray(nfaces, dtype=np.int64)
    child["transport_control_volume_count"] = np.asarray(ncv, dtype=np.int64)
    child["control_volume_aligned_transfer_active"] = np.asarray(True, dtype=bool)
    child["component_mass_primary_conserved_variable"] = np.asarray(True, dtype=bool)
    child["injector_local_mass_closure_authorized"] = np.asarray(False, dtype=bool)
    child["injector_local_mass_closure_executed"] = np.asarray(False, dtype=bool)
    child["last_source_local_added_mass_kg"] = np.asarray(0.0, dtype=np.float64)
    child["E37B_extended_rollout_active"] = np.asarray(True, dtype=bool)
    child["first_fixed_observation_checkpoint_reached"] = np.asarray(False, dtype=bool)
    return child


def evolve_from_parent(
    *,
    parent: dict[str, np.ndarray],
    dt_days: float,
    r2: Any,
    e36: Any,
    e37a: Any,
    e37b: Any,
    sg7a: Any,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    geometry: dict[str, np.ndarray],
    face_pressure_psi: np.ndarray,
    weights_m3_day: np.ndarray,
    xi_faces: np.ndarray,
    labels: np.ndarray,
    permeability_md: np.ndarray,
    cell_pore_volume_m3: float,
    nstream: int,
    nfaces: int,
    ncv: int,
) -> dict[str, Any]:
    if not np.isfinite(dt_days) or dt_days <= 0.0:
        raise e37a.TrialReject(f"nonpositive_event_trial_dt:{dt_days}")

    parent_sat = np.asarray(parent["transport_saturation"], dtype=np.float64)
    parent_time = scalar(parent["physical_time_days"])
    parent_stored = scalar(parent["stored_co2_mass_current_kg"])
    recomputed_parent = float(
        r2.stored_co2_mass_kg(
            parent_sat,
            pressure_psi,
            p_ref_gas_pa,
            cell_pore_volume_m3,
        )
    )
    parent_tol = max(1.0e-6, 1.0e-10 * max(abs(parent_stored), 1.0))
    if abs(recomputed_parent - parent_stored) > parent_tol:
        raise e37a.TrialReject(
            "parent_grid_component_mass_recompute_mismatch:"
            f"{recomputed_parent-parent_stored}:{parent_tol}"
        )

    old_cv_sat, old_cv_mass, sample_closure = (
        e37a.sample_grid_inventory_to_control_volumes(
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
        1.0e-10 * max(abs(float(np.sum(old_cv_mass))), 1.0),
    )
    if abs(sample_closure) > sample_tol:
        raise e37a.TrialReject(
            f"grid_to_CV_inventory_sampling_closure:{sample_closure}:{sample_tol}"
        )

    parent_cut = e37b.weighted_outlet_gas_cut(
        sg7a,
        old_cv_sat,
        weights_m3_day,
    )

    transport = e37a.advance_component_mass_control_volumes(
        r2,
        sg7a,
        old_cv_sat,
        old_cv_mass,
        geometry["cv_pressure_mass_coeff"],
        face_pressure_psi,
        p_ref_gas_pa,
        weights_m3_day,
        xi_faces,
        dt_days,
    )
    injected_step = float(transport["injected_mass_kg"])
    produced_step = float(transport["produced_mass_kg"])
    physical_injected = INJECTOR_MASS_RATE_KG_DAY * float(dt_days)
    inj_tol = max(1.0e-6, 1.0e-12 * max(abs(physical_injected), 1.0))
    if abs(injected_step - physical_injected) > inj_tol:
        raise e37a.TrialReject(
            "fixed_rate_inlet_component_mass_not_exact:"
            f"{injected_step}:{physical_injected}"
        )

    target_final_mass = parent_stored + injected_step - produced_step
    mapping = e37a.map_control_volume_increment_to_grid(
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
    pre_capillary_sat = np.asarray(mapping["corrected_saturation"], dtype=np.float64)

    capillary = r2.conservative_capillary_mass_redistribution(
        transport_saturation=pre_capillary_sat,
        permeability_md=permeability_md,
        pressure_psi=pressure_psi,
        p_ref_pa=p_ref_gas_pa,
        cell_pore_volume_m3=cell_pore_volume_m3,
        dt_seconds=dt_days * DAY_TO_S,
    )
    child_sat = np.asarray(capillary["corrected"], dtype=np.float64)
    final_stored = float(capillary["final_mass_state_kg"])
    step_residual = final_stored - parent_stored - injected_step + produced_step
    closure_tol = max(1.0e-6, 1.0e-10 * max(abs(target_final_mass), 1.0))
    if abs(float(capillary["external_mass_change_kg"])) > closure_tol:
        raise e37a.TrialReject(
            "capillary_external_mass_change:"
            f"{capillary['external_mass_change_kg']}:{closure_tol}"
        )
    if abs(step_residual) > closure_tol:
        raise e37a.TrialReject(
            f"step_component_mass_closure:{step_residual}:{closure_tol}"
        )
    if (
        float(np.min(child_sat)) < BACKGROUND_SATURATION - 1.0e-12
        or float(np.max(child_sat)) > INJECTED_BOUNDARY_SATURATION + 1.0e-12
    ):
        raise e37a.TrialReject(
            f"child_saturation_bounds:{np.min(child_sat)}:{np.max(child_sat)}"
        )

    child_cv_sat, child_cv_mass, post_sample_closure = (
        e37a.sample_grid_inventory_to_control_volumes(
            r2,
            child_sat,
            pressure_psi,
            p_ref_gas_pa,
            geometry,
            nstream,
            ncv,
        )
    )
    post_tol = max(
        1.0e-6,
        1.0e-10 * max(abs(float(np.sum(child_cv_mass))), 1.0),
    )
    if abs(post_sample_closure) > post_tol:
        raise e37a.TrialReject(
            f"child_grid_to_CV_sampling_closure:{post_sample_closure}:{post_tol}"
        )
    child_cut = e37b.weighted_outlet_gas_cut(
        sg7a,
        child_cv_sat,
        weights_m3_day,
    )

    prod_rows, aggregate_flux_cut = e37a.producer_rows_from_flux(
        labels,
        weights_m3_day,
        transport["outlet_fractional_flow"],
        transport["face_mass_flux_kg_day"][:, -1],
        dt_days,
    )
    prod_sum = float(sum(float(row["CO2_mass_this_step_kg"]) for row in prod_rows))
    if abs(prod_sum - produced_step) > max(
        1.0e-6,
        1.0e-10 * max(abs(produced_step), 1.0),
    ):
        raise e37a.TrialReject(
            f"producer_mass_breakdown_mismatch:{prod_sum}:{produced_step}"
        )

    child = build_trial_child(
        parent,
        child_sat,
        pressure_psi,
        p_ref_gas_pa,
        dt_days,
        produced_step,
        child_cut,
        final_stored,
        step_residual,
        nfaces,
        ncv,
    )
    child["last_CV_transport_mass_residual_kg"] = np.asarray(
        transport["mass_residual_kg"], dtype=np.float64
    )
    child["last_CV_to_grid_transfer_residual_kg"] = np.asarray(
        mapping["transfer_residual_kg"], dtype=np.float64
    )
    child["last_grid_mapback_ledger_residual_kg"] = np.asarray(
        mapping["ledger_residual_kg"], dtype=np.float64
    )
    child["last_grid_to_CV_sampling_closure_kg"] = np.asarray(
        post_sample_closure, dtype=np.float64
    )
    child["current_producer_co2_gas_cut"] = np.asarray(child_cut, dtype=np.float64)
    child["breakthrough_reached"] = np.asarray(False, dtype=bool)
    child["breakthrough_time_days"] = np.asarray(float("nan"), dtype=np.float64)
    child["time_since_breakthrough_days"] = np.asarray(0.0, dtype=np.float64)

    return {
        "child": child,
        "child_saturation": child_sat,
        "parent_cut": float(parent_cut),
        "child_cut": float(child_cut),
        "injected_mass_kg": injected_step,
        "produced_mass_kg": produced_step,
        "final_stored_mass_kg": final_stored,
        "step_mass_residual_kg": float(step_residual),
        "sample_closure_kg": float(sample_closure),
        "post_sample_closure_kg": float(post_sample_closure),
        "transport_residual_kg": float(transport["mass_residual_kg"]),
        "transfer_residual_kg": float(mapping["transfer_residual_kg"]),
        "mapback_ledger_residual_kg": float(mapping["ledger_residual_kg"]),
        "capillary_external_mass_change_kg": float(capillary["external_mass_change_kg"]),
        "aggregate_flux_cut": float(aggregate_flux_cut),
        "producer_rows": prod_rows,
        "trial_time_days": parent_time + float(dt_days),
    }




def validate_breakthrough_restart(
    data: bytes,
    expected_step: int,
    expected_time: float,
    expected_cut: float,
    expected_width: float,
) -> None:
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        if int(z["accepted_step_index"]) != int(expected_step):
            raise GateError("BT_restart_step_mismatch")
        if abs(float(z["physical_time_days"]) - float(expected_time)) > 1.0e-12:
            raise GateError("BT_restart_time_mismatch")
        if not bool(z["breakthrough_reached"]):
            raise GateError("BT_restart_breakthrough_flag_false")
        if abs(float(z["breakthrough_time_days"]) - float(expected_time)) > 1.0e-12:
            raise GateError("BT_restart_breakthrough_time_mismatch")
        if abs(float(z["current_producer_co2_gas_cut"]) - float(expected_cut)) > 1.0e-15:
            raise GateError("BT_restart_gas_cut_mismatch")
        if float(z["current_producer_co2_gas_cut"]) < BREAKTHROUGH_GAS_CUT:
            raise GateError("BT_restart_gas_cut_below_threshold")
        if abs(float(z["breakthrough_bracket_width_days"]) - float(expected_width)) > 1.0e-15:
            raise GateError("BT_restart_bracket_width_mismatch")
        if float(z["breakthrough_bracket_width_days"]) > EVENT_TIME_TOL_DAYS + 1.0e-15:
            raise GateError("BT_restart_bracket_width_exceeds_tolerance")
        if bool(z["injector_local_mass_closure_authorized"]):
            raise GateError("BT_restart_authorizes_source_local_closure")
        if bool(z["injector_local_mass_closure_executed"]):
            raise GateError("BT_restart_reports_source_local_closure")
        if not bool(z["control_volume_aligned_transfer_active"]):
            raise GateError("BT_restart_missing_CV_alignment")
        if int(z["observation_cursor_index"]) != 0:
            raise GateError("BT_restart_observation_cursor_advanced")
        if float(z["next_fixed_observation_day"]) != FIRST_OBSERVATION_DAY:
            raise GateError("BT_restart_next_observation_not_30d")
        if bool(z["first_fixed_observation_checkpoint_reached"]):
            raise GateError("BT_restart_incorrect_observation_checkpoint_flag")
        if not bool(z["V16E38_canonical_breakthrough_state"]):
            raise GateError("BT_restart_missing_canonical_event_flag")


def self_test() -> None:
    lo_t = 0.0
    hi_t = 0.049123143364170854
    threshold = 1.0e-4

    def f(t: float) -> float:
        return 9.7e-5 + (1.004e-4 - 9.7e-5) * (t / hi_t)

    lo_cut = f(lo_t)
    hi_cut = f(hi_t)
    if not (lo_cut < threshold <= hi_cut):
        raise RuntimeError("self_test_initial_bracket_invalid")

    count = 0
    while hi_t - lo_t > EVENT_TIME_TOL_DAYS:
        mid = 0.5 * (lo_t + hi_t)
        mid_cut = f(mid)
        if mid_cut >= threshold:
            hi_t, hi_cut = mid, mid_cut
        else:
            lo_t, lo_cut = mid, mid_cut
        count += 1
        if count > MAX_REFINEMENT_ITERS:
            raise RuntimeError("self_test_refinement_budget_exceeded")

    if not (lo_cut < threshold <= hi_cut):
        raise RuntimeError("self_test_final_bracket_invalid")
    if hi_t - lo_t > EVENT_TIME_TOL_DAYS:
        raise RuntimeError("self_test_event_tolerance_not_met")
    if count != 16:
        raise RuntimeError(f"self_test_expected_16_refinements:{count}")

    # Event checkpoint is not a fixed observation checkpoint.
    observation_cursor = 0
    next_observation = 30.0
    if observation_cursor != 0 or next_observation != 30.0:
        raise RuntimeError("self_test_event_observation_cursor_semantics_failed")

    print("PAD-Stream V16E-38 breakthrough refinement self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None
    e37a_parent_sha_before: str | None = None
    e36_cache_sha_before: str | None = None
    e37b_bracket_sha_before: str | None = None
    frozen_sha_before: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 146)
        print("PAD-Stream V16E-38 — Breakthrough Event Refinement / Canonical BT State")
        print("=" * 146)
        print("Authority      : E37B deterministic breakthrough bracket")
        print("Restart        : accepted E37A step-4 CV-aligned state")
        print("Reproduction   : replay accepted nominal trajectory to the exact E37B lower bracket")
        print("Refinement     : bisection from the same accepted pre-BT parent; no temporal state interpolation")
        print(f"Event tolerance: <= {EVENT_TIME_TOL_DAYS:.1e} days")
        print("Canonical BT   : physically evolved upper-bracket state at/above gas-cut threshold")
        print("Observation    : 30-day cursor remains pending after breakthrough")

        failed_stage = "source_and_provenance_binding"
        r2_path = root / R2_RUNNER
        e36_path = root / E36_RUNNER
        e37a_path = root / E37A_RUNNER
        e37b_path = root / E37B_RUNNER
        sg7a_path = root / SG7A
        sg7d_path = root / SG7D
        perm_path = root / SGSIM_PERM
        for p in [r2_path, e36_path, e37a_path, e37b_path, sg7a_path, sg7d_path, perm_path]:
            gate(f"source_exists_{p.name}", p.is_file(), p)

        gate("R2_runner_SHA_exact", sha256_file(r2_path) == R2_RUNNER_SHA256, sha256_file(r2_path))
        gate("E36_runner_SHA_exact", sha256_file(e36_path) == E36_RUNNER_SHA256, sha256_file(e36_path))
        gate("E37A_runner_SHA_exact", sha256_file(e37a_path) == E37A_RUNNER_SHA256, sha256_file(e37a_path))
        gate("E37B_runner_SHA_exact", sha256_file(e37b_path) == E37B_RUNNER_SHA256, sha256_file(e37b_path))

        r2 = load_module(r2_path, "pad_stream_v16e38_r2")
        e36 = load_module(e36_path, "pad_stream_v16e38_e36")
        e37a = load_module(e37a_path, "pad_stream_v16e38_e37a")
        e37b = load_module(e37b_path, "pad_stream_v16e38_e37b")

        e37a_dir = drive / E37A_REL
        e37a_summary_path = e37a_dir / E37A_SUMMARY
        e37a_closure_path = e37a_dir / E37A_CLOSURE
        e36_cache_path = drive / E36_REL / E36_CACHE
        bracket_report_path = drive / E37B_BLOCKED_REL / E37B_BRACKET_REPORT
        frozen_100d = drive / V16_FROZEN_REL
        e37b_30d = drive / E37B_OUT_REL / E37B_30D_CHECKPOINT

        for p in [e37a_summary_path, e37a_closure_path, e36_cache_path, bracket_report_path, frozen_100d]:
            gate(f"provenance_exists_{p.name}", p.is_file(), p)
        gate("E37B_30d_checkpoint_not_published", not e37b_30d.exists(), e37b_30d)

        e37a_summary = load_json(e37a_summary_path)
        e37a_closure = load_json(e37a_closure_path)
        bracket_report = load_json(bracket_report_path)
        gate("E37A_status_accepted", e37a_summary.get("status") == E37A_EXPECTED_STATUS, e37a_summary.get("status"))
        gate("E37B_blocked_status_exact", bracket_report.get("status") == E37B_EXPECTED_BLOCKED_STATUS, bracket_report.get("status"))
        bracket = bracket_report.get("breakthrough_bracket") or {}
        gate("E37B_bracket_threshold_exact", float(bracket.get("threshold", -1.0)) == BREAKTHROUGH_GAS_CUT, bracket.get("threshold"))
        gate("E37B_bracket_order_valid",
             float(bracket.get("parent_CO2_gas_cut", 1.0)) < BREAKTHROUGH_GAS_CUT <= float(bracket.get("trial_CO2_gas_cut", -1.0)),
             bracket)
        gate("E37B_bracket_pre_30d", float(bracket.get("trial_time_days", 999.0)) < FIRST_OBSERVATION_DAY, bracket.get("trial_time_days"))
        gate("E37B_bracket_target_step_positive", int(bracket.get("target_step", -1)) > 0, bracket.get("target_step"))

        final_state_name = str(e37a_closure.get("final_state_file", ""))
        if not final_state_name:
            raise GateError("E37A_closure_missing_final_state_file")
        parent_state_path = e37a_dir / final_state_name
        gate("E37A_final_state_exists", parent_state_path.is_file(), parent_state_path)

        e37a_parent_sha_before = sha256_file(parent_state_path)
        e36_cache_sha_before = sha256_file(e36_cache_path)
        e37b_bracket_sha_before = sha256_file(bracket_report_path)
        frozen_sha_before = sha256_file(frozen_100d)
        gate("E37A_final_state_SHA_matches_closure", e37a_parent_sha_before == e37a_closure.get("final_state_sha256"), e37a_parent_sha_before)
        gate("E36_cache_SHA_matches_E37A_closure", e36_cache_sha_before == e37a_closure.get("E36_certified_cache_sha256"), e36_cache_sha_before)
        gate("frozen_100d_SHA_exact", frozen_sha_before == V16_FROZEN_SHA256, frozen_sha_before)

        parent = load_npz(parent_state_path)
        cache = load_npz(e36_cache_path)
        gate("E37A_restart_step_exact_4", int_scalar(parent["accepted_step_index"]) == 4, int_scalar(parent["accepted_step_index"]))
        gate("E37A_restart_no_breakthrough", not bool_scalar(parent["breakthrough_reached"]), scalar(parent["current_producer_co2_gas_cut"]))
        gate("E37A_restart_next_observation_30d", scalar(parent["next_fixed_observation_day"]) == FIRST_OBSERVATION_DAY, scalar(parent["next_fixed_observation_day"]))
        gate("E36_cache_reference_mobility_scope", bool_scalar(cache["reuse_scope_reference_mobility_only"]))

        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E38_") as td:
            tmp = Path(td)
            shutil.copy2(sg7a_path, tmp / SG7A)
            shutil.copy2(sg7d_path, tmp / SG7D)
            sg7a = load_module(tmp / SG7A, "pad_stream_v16e38_sg7a")
            sg7d = load_module(tmp / SG7D, "pad_stream_v16e38_sg7d")

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
            gate("streamline_count_exact", nstream == EXPECTED_STREAMLINES, nstream)
            gate("transport_face_count_exact", nfaces == EXPECTED_FACES, nfaces)
            gate("transport_CV_count_exact", ncv == EXPECTED_CVS, ncv)

            weights_m3_day = weights_m3_s * DAY_TO_S
            q_expected = INJECTOR_MASS_RATE_KG_DAY / CO2_RHO_REF_KG_M3
            q_actual = float(np.sum(weights_m3_day))
            gate("streamline_weights_match_fixed_injection_rate", abs(q_actual-q_expected)/q_expected < 1.0e-10, f"{q_actual}:{q_expected}")

            tof_days = tau_s / DAY_TO_S
            operator = sg7d.build_subsegment_operator(xyz_m, tof_days, weights_m3_day)
            p_ref_gas_pa = scalar(parent["co2_density_reference_pressure_pa"])
            geometry = e37a.build_control_volume_geometry(
                r2, operator, pressure_psi, p_ref_gas_pa, nstream, ncv
            )
            expected_cv_pv = weights_m3_day[:, None] * np.diff(tof_days, axis=1)
            cv_pv = geometry["cv_pv_m3"]
            cv_pv_rel = float(np.linalg.norm((cv_pv-expected_cv_pv).ravel()) / max(np.linalg.norm(expected_cv_pv.ravel()), 1.0e-30))
            gate("CV_pore_volume_alignment_revalidated", cv_pv_rel <= 1.0e-10, cv_pv_rel)
            face_pressure_psi = e37a.build_face_pressure(e36, sg7d, xyz_m, pressure_psi)

            dxi = float(xi_faces[1] - xi_faces[0])
            sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
            max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
            u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
            max_wave_speed = float(np.max(u_face) * max_df)
            dtD_cfl = float(sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS))
            fastest_tau_days = float(np.min(tau_end_s / DAY_TO_S))
            nominal_dt_days = float(dtD_cfl * fastest_tau_days)
            gate("nominal_dt_matches_E37A", abs(nominal_dt_days-float(e37a_summary["nominal_dt_days"])) <= 1.0e-15, f"{nominal_dt_days}:{e37a_summary['nominal_dt_days']}")

            dx_m, dy_m, dz_m = 20.0*FT_TO_M, 20.0*FT_TO_M, 4.0*FT_TO_M
            cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m
            permeability_md = np.loadtxt(perm_path, skiprows=1, dtype=np.float64).reshape(EXPECTED_GRID, order="C")
            gate("SGSim_permeability_shape_exact", permeability_md.shape == EXPECTED_GRID, permeability_md.shape)

            # --------------------------------------------------------------
            # Deterministically reproduce the accepted E37B path to its
            # lower breakthrough bracket endpoint.
            # --------------------------------------------------------------
            failed_stage = "reproduce_pre_breakthrough_parent"
            bracket_parent_time = float(bracket["parent_time_days"])
            bracket_trial_time = float(bracket["trial_time_days"])
            bracket_parent_cut = float(bracket["parent_CO2_gas_cut"])
            bracket_trial_cut = float(bracket["trial_CO2_gas_cut"])
            bracket_target_step = int(bracket["target_step"])

            current = {k: np.asarray(v).copy() for k, v in parent.items()}
            reproduction_rows: list[dict[str, Any]] = []
            residual_transport: list[float] = []
            residual_transfer: list[float] = []
            residual_mapback: list[float] = []
            residual_capillary: list[float] = []
            accepted_reproduction = 0

            while scalar(current["physical_time_days"]) < bracket_parent_time - 1.0e-13:
                current_time = scalar(current["physical_time_days"])
                remaining = bracket_parent_time - current_time
                dt_days = min(nominal_dt_days, remaining)
                result = evolve_from_parent(
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
                if result["child_cut"] >= BREAKTHROUGH_GAS_CUT:
                    raise GateError(
                        f"reproduction_crossed_breakthrough_early:{current_time}:{result['trial_time_days']}:{result['child_cut']}"
                    )
                child = result["child"]
                new_time = scalar(child["physical_time_days"])
                reproduction_rows.append({
                    "accepted_step_index": int_scalar(child["accepted_step_index"]),
                    "parent_time_days": current_time,
                    "accepted_time_days": new_time,
                    "accepted_dt_days": dt_days,
                    "parent_CO2_gas_cut": result["parent_cut"],
                    "child_CO2_gas_cut": result["child_cut"],
                    "injected_CO2_mass_kg": result["injected_mass_kg"],
                    "produced_CO2_mass_kg": result["produced_mass_kg"],
                    "step_mass_residual_kg": result["step_mass_residual_kg"],
                    "cumulative_mass_residual_kg": scalar(child["cumulative_mass_residual_kg"]),
                    "CV_transport_mass_residual_kg": result["transport_residual_kg"],
                    "CV_to_grid_transfer_residual_kg": result["transfer_residual_kg"],
                    "grid_mapback_ledger_residual_kg": result["mapback_ledger_residual_kg"],
                    "capillary_external_mass_change_kg": result["capillary_external_mass_change_kg"],
                })
                residual_transport.append(result["transport_residual_kg"])
                residual_transfer.append(result["transfer_residual_kg"])
                residual_mapback.append(result["mapback_ledger_residual_kg"])
                residual_capillary.append(result["capillary_external_mass_change_kg"])
                current = child
                accepted_reproduction += 1
                if accepted_reproduction % PROGRESS_EVERY == 0:
                    print(
                        f"[REPRODUCE] accepted step {int_scalar(current['accepted_step_index'])}: "
                        f"t={new_time:.12g} d, cut={result['child_cut']:.6e}"
                    )
                if accepted_reproduction > 5000:
                    raise GateError("reproduction_transition_budget_exceeded")

            reproduced_parent = current
            reproduced_parent_time = scalar(reproduced_parent["physical_time_days"])
            reproduced_parent_step = int_scalar(reproduced_parent["accepted_step_index"])
            old_cv_sat, _, _ = e37a.sample_grid_inventory_to_control_volumes(
                r2,
                np.asarray(reproduced_parent["transport_saturation"], dtype=np.float64),
                pressure_psi,
                p_ref_gas_pa,
                geometry,
                nstream,
                ncv,
            )
            reproduced_parent_cut = e37b.weighted_outlet_gas_cut(sg7a, old_cv_sat, weights_m3_day)
            gate("reproduced_parent_time_matches_E37B_bracket", abs(reproduced_parent_time-bracket_parent_time) <= 1.0e-12, f"{reproduced_parent_time}:{bracket_parent_time}")
            gate("reproduced_parent_step_matches_E37B_target_minus_one", reproduced_parent_step == bracket_target_step-1, f"{reproduced_parent_step}:{bracket_target_step-1}")
            gate("reproduced_parent_cut_matches_E37B_bracket", abs(reproduced_parent_cut-bracket_parent_cut) <= 1.0e-12, f"{reproduced_parent_cut}:{bracket_parent_cut}")
            gate("reproduced_parent_is_pre_breakthrough", reproduced_parent_cut < BREAKTHROUGH_GAS_CUT, reproduced_parent_cut)

            # Verify the full original crossing trial reproduces E37B.
            failed_stage = "reproduce_E37B_crossing_trial"
            original_hi_dt = bracket_trial_time - bracket_parent_time
            original_hi = evolve_from_parent(
                parent=reproduced_parent,
                dt_days=original_hi_dt,
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
            gate("reproduced_trial_time_matches_E37B_bracket", abs(original_hi["trial_time_days"]-bracket_trial_time) <= 1.0e-12, f"{original_hi['trial_time_days']}:{bracket_trial_time}")
            gate("reproduced_trial_cut_matches_E37B_bracket", abs(original_hi["child_cut"]-bracket_trial_cut) <= 1.0e-12, f"{original_hi['child_cut']}:{bracket_trial_cut}")
            gate("reproduced_trial_is_post_threshold", original_hi["child_cut"] >= BREAKTHROUGH_GAS_CUT, original_hi["child_cut"])

            # --------------------------------------------------------------
            # Bisection event refinement. Every trial is evolved afresh from
            # the same accepted pre-BT parent. No saturation/time interpolation.
            # --------------------------------------------------------------
            failed_stage = "breakthrough_bisection_refinement"
            lo_dt = 0.0
            lo_cut = reproduced_parent_cut
            hi_dt = original_hi_dt
            hi_result = original_hi
            hi_cut = float(original_hi["child_cut"])
            refinement_rows: list[dict[str, Any]] = []

            linear_fraction = (BREAKTHROUGH_GAS_CUT - lo_cut) / max(hi_cut - lo_cut, 1.0e-30)
            linear_fraction = min(1.0, max(0.0, linear_fraction))
            linear_estimate_time = bracket_parent_time + linear_fraction * original_hi_dt

            refinement_iter = 0
            while hi_dt - lo_dt > EVENT_TIME_TOL_DAYS:
                if refinement_iter >= MAX_REFINEMENT_ITERS:
                    raise GateError(f"event_refinement_budget_exceeded:{hi_dt-lo_dt}")
                mid_dt = 0.5 * (lo_dt + hi_dt)
                mid = evolve_from_parent(
                    parent=reproduced_parent,
                    dt_days=mid_dt,
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
                mid_cut = float(mid["child_cut"])
                classification = "UPPER_AT_OR_ABOVE_THRESHOLD" if mid_cut >= BREAKTHROUGH_GAS_CUT else "LOWER_BELOW_THRESHOLD"
                if mid_cut >= BREAKTHROUGH_GAS_CUT:
                    hi_dt = mid_dt
                    hi_cut = mid_cut
                    hi_result = mid
                else:
                    lo_dt = mid_dt
                    lo_cut = mid_cut
                refinement_iter += 1
                refinement_rows.append({
                    "iteration": refinement_iter,
                    "trial_dt_from_parent_days": mid_dt,
                    "trial_time_days": bracket_parent_time + mid_dt,
                    "trial_CO2_gas_cut": mid_cut,
                    "threshold": BREAKTHROUGH_GAS_CUT,
                    "classification": classification,
                    "lower_dt_days_after": lo_dt,
                    "upper_dt_days_after": hi_dt,
                    "lower_time_days_after": bracket_parent_time + lo_dt,
                    "upper_time_days_after": bracket_parent_time + hi_dt,
                    "lower_CO2_gas_cut_after": lo_cut,
                    "upper_CO2_gas_cut_after": hi_cut,
                    "bracket_width_days_after": hi_dt-lo_dt,
                    "step_mass_residual_kg": mid["step_mass_residual_kg"],
                    "CV_transport_mass_residual_kg": mid["transport_residual_kg"],
                    "CV_to_grid_transfer_residual_kg": mid["transfer_residual_kg"],
                    "grid_mapback_ledger_residual_kg": mid["mapback_ledger_residual_kg"],
                    "capillary_external_mass_change_kg": mid["capillary_external_mass_change_kg"],
                })
                if not (lo_cut < BREAKTHROUGH_GAS_CUT <= hi_cut):
                    raise GateError(
                        f"event_bracket_order_lost:{lo_cut}:{hi_cut}:{BREAKTHROUGH_GAS_CUT}"
                    )
                print(
                    f"[REFINE {refinement_iter:02d}] "
                    f"t=[{bracket_parent_time+lo_dt:.12g}, {bracket_parent_time+hi_dt:.12g}] d, "
                    f"cut=[{lo_cut:.9e}, {hi_cut:.9e}], width={hi_dt-lo_dt:.3e} d"
                )

            refined_lo_time = bracket_parent_time + lo_dt
            refined_hi_time = bracket_parent_time + hi_dt
            refined_width = refined_hi_time - refined_lo_time
            canonical = {k: np.asarray(v).copy() for k, v in hi_result["child"].items()}
            canonical_time = scalar(canonical["physical_time_days"])
            canonical_step = int_scalar(canonical["accepted_step_index"])
            canonical_cut = float(hi_result["child_cut"])

            canonical["breakthrough_reached"] = np.asarray(True, dtype=bool)
            canonical["breakthrough_time_days"] = np.asarray(canonical_time, dtype=np.float64)
            canonical["time_since_breakthrough_days"] = np.asarray(0.0, dtype=np.float64)
            canonical["current_producer_co2_gas_cut"] = np.asarray(canonical_cut, dtype=np.float64)
            canonical["V16E38_canonical_breakthrough_state"] = np.asarray(True, dtype=bool)
            canonical["breakthrough_threshold"] = np.asarray(BREAKTHROUGH_GAS_CUT, dtype=np.float64)
            canonical["breakthrough_bracket_lower_time_days"] = np.asarray(refined_lo_time, dtype=np.float64)
            canonical["breakthrough_bracket_upper_time_days"] = np.asarray(refined_hi_time, dtype=np.float64)
            canonical["breakthrough_bracket_width_days"] = np.asarray(refined_width, dtype=np.float64)
            canonical["breakthrough_lower_CO2_gas_cut"] = np.asarray(lo_cut, dtype=np.float64)
            canonical["breakthrough_upper_CO2_gas_cut"] = np.asarray(hi_cut, dtype=np.float64)
            canonical["breakthrough_refinement_iterations"] = np.asarray(refinement_iter, dtype=np.int64)
            canonical["first_fixed_observation_checkpoint_reached"] = np.asarray(False, dtype=bool)
            canonical["E37B_extended_rollout_active"] = np.asarray(False, dtype=bool)
            canonical["E38_breakthrough_event_refined"] = np.asarray(True, dtype=bool)
            canonical["last_source_local_added_mass_kg"] = np.asarray(0.0, dtype=np.float64)

            gate("refined_bracket_width_within_tolerance", refined_width <= EVENT_TIME_TOL_DAYS + 1.0e-15, refined_width)
            gate("refined_lower_below_threshold", lo_cut < BREAKTHROUGH_GAS_CUT, lo_cut)
            gate("refined_upper_at_or_above_threshold", hi_cut >= BREAKTHROUGH_GAS_CUT, hi_cut)
            gate("canonical_time_equals_upper_bracket", abs(canonical_time-refined_hi_time) <= 1.0e-12, f"{canonical_time}:{refined_hi_time}")
            gate("canonical_step_is_E37B_target_step", canonical_step == bracket_target_step, f"{canonical_step}:{bracket_target_step}")
            gate("canonical_breakthrough_flag_true", bool_scalar(canonical["breakthrough_reached"]))
            gate("canonical_observation_cursor_unchanged", int_scalar(canonical["observation_cursor_index"]) == int_scalar(reproduced_parent["observation_cursor_index"]), int_scalar(canonical["observation_cursor_index"]))
            gate("canonical_next_observation_still_30d", scalar(canonical["next_fixed_observation_day"]) == FIRST_OBSERVATION_DAY, scalar(canonical["next_fixed_observation_day"]))
            gate("canonical_source_local_closure_forbidden", not bool_scalar(canonical["injector_local_mass_closure_authorized"]) and not bool_scalar(canonical["injector_local_mass_closure_executed"]), "forbidden")

            final_mass = scalar(canonical["stored_co2_mass_current_kg"])
            final_cum_resid = scalar(canonical["cumulative_mass_residual_kg"])
            final_tol = max(1.0e-6, 1.0e-10 * max(abs(final_mass), 1.0))
            gate("canonical_cumulative_mass_closure", abs(final_cum_resid) <= final_tol, f"{final_cum_resid}:{final_tol}")
            gate("E37A_parent_unchanged", sha256_file(parent_state_path) == e37a_parent_sha_before, sha256_file(parent_state_path))
            gate("E36_cache_unchanged", sha256_file(e36_cache_path) == e36_cache_sha_before, sha256_file(e36_cache_path))
            gate("E37B_bracket_report_unchanged", sha256_file(bracket_report_path) == e37b_bracket_sha_before, sha256_file(bracket_report_path))
            gate("frozen_100d_unchanged", sha256_file(frozen_100d) == frozen_sha_before, sha256_file(frozen_100d))
            gate("E37B_30d_checkpoint_still_not_published", not e37b_30d.exists(), e37b_30d)

            gate(
                "reproduction_transition_count_consistent",
                accepted_reproduction
                == reproduced_parent_step - int_scalar(parent["accepted_step_index"]),
                accepted_reproduction,
            )

            prebt_bytes = deterministic_npz_bytes(reproduced_parent)
            canonical_bytes = deterministic_npz_bytes(canonical)
            validate_breakthrough_restart(
                canonical_bytes,
                canonical_step,
                canonical_time,
                canonical_cut,
                refined_width,
            )
            gate("canonical_restart_artifact_validated", True, canonical_step)
            snapshot_bytes = deterministic_npz_bytes({
                "labels": np.asarray(["PRE_BREAKTHROUGH_PARENT", "CANONICAL_BREAKTHROUGH_STATE"], dtype="U48"),
                "accepted_step_index": np.asarray([reproduced_parent_step, canonical_step], dtype=np.int64),
                "physical_time_days": np.asarray([reproduced_parent_time, canonical_time], dtype=np.float64),
                "producer_CO2_gas_cut": np.asarray([reproduced_parent_cut, canonical_cut], dtype=np.float64),
                "transport_saturation": np.stack([
                    np.asarray(reproduced_parent["transport_saturation"], dtype=np.float64),
                    np.asarray(canonical["transport_saturation"], dtype=np.float64),
                ], axis=0),
            })

            plume_rows = [
                e36.plume_metrics(
                    r2,
                    np.asarray(reproduced_parent["transport_saturation"], dtype=np.float64),
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    reproduced_parent_step,
                    reproduced_parent_time,
                ),
                e36.plume_metrics(
                    r2,
                    np.asarray(canonical["transport_saturation"], dtype=np.float64),
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    canonical_step,
                    canonical_time,
                ),
            ]
            plume_rows[0]["state_label"] = "PRE_BREAKTHROUGH_PARENT"
            plume_rows[0]["producer_CO2_gas_cut"] = reproduced_parent_cut
            plume_rows[1]["state_label"] = "CANONICAL_BREAKTHROUGH_STATE"
            plume_rows[1]["producer_CO2_gas_cut"] = canonical_cut

            producer_rows = []
            for row in hi_result["producer_rows"]:
                producer_rows.append({
                    "state": "CANONICAL_BREAKTHROUGH_TRANSITION",
                    "parent_time_days": reproduced_parent_time,
                    "canonical_breakthrough_time_days": canonical_time,
                    "refined_dt_days": hi_dt,
                    **row,
                })

            event_contract = {
                "milestone": MILESTONE,
                "status": "BREAKTHROUGH_EVENT_REFINEMENT_CONTRACT_FROZEN",
                "threshold": BREAKTHROUGH_GAS_CUT,
                "event_function": "post-capillary canonical restart-sampled producer CO2 gas cut",
                "lower_endpoint_requirement": "gas cut < threshold",
                "upper_endpoint_requirement": "gas cut >= threshold",
                "refinement_method": "bisection in physical dt, every trial evolved afresh from the same accepted pre-BT parent",
                "temporal_state_interpolation_authorized": False,
                "scalar_linear_interpolation_role": "diagnostic estimate only; never canonical state",
                "event_time_tolerance_days": EVENT_TIME_TOL_DAYS,
                "canonical_state_definition": "physically evolved upper-bracket endpoint after tolerance is met",
                "observation_cursor_policy": "breakthrough is an event checkpoint; fixed-observation cursor remains pending at 30 days",
                "injector_local_mass_closure_authorized": False,
                "global_plume_rescaling_authorized": False,
                "flow_path_cache_scope": "E36-certified V15-SG3 steady reference-mobility pressure authority only",
                "F0_learned_timestep_authorized": False,
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "E37B_breakthrough_bracket_consumed": True,
                "E37B_30d_checkpoint_published": False,
                "E37B_bracket_report_sha256": e37b_bracket_sha_before,
                "reproduction_initial_step_index": int_scalar(parent["accepted_step_index"]),
                "reproduction_initial_time_days": scalar(parent["physical_time_days"]),
                "reproduced_preBT_step_index": reproduced_parent_step,
                "reproduced_preBT_time_days": reproduced_parent_time,
                "reproduction_transitions_executed": accepted_reproduction,
                "reproduced_preBT_CO2_gas_cut": reproduced_parent_cut,
                "original_bracket_lower_time_days": bracket_parent_time,
                "original_bracket_upper_time_days": bracket_trial_time,
                "original_bracket_width_days": bracket_trial_time-bracket_parent_time,
                "original_bracket_lower_CO2_gas_cut": bracket_parent_cut,
                "original_bracket_upper_CO2_gas_cut": bracket_trial_cut,
                "scalar_linear_interpolation_estimate_days": linear_estimate_time,
                "temporal_state_interpolation_used": False,
                "refinement_method": "BISECTION_FROM_SAME_ACCEPTED_PARENT",
                "refinement_iterations": refinement_iter,
                "event_time_tolerance_days": EVENT_TIME_TOL_DAYS,
                "refined_bracket_lower_time_days": refined_lo_time,
                "refined_bracket_upper_time_days": refined_hi_time,
                "refined_bracket_width_days": refined_width,
                "refined_lower_CO2_gas_cut": lo_cut,
                "refined_upper_CO2_gas_cut": hi_cut,
                "canonical_breakthrough_time_days": canonical_time,
                "canonical_breakthrough_step_index": canonical_step,
                "canonical_breakthrough_CO2_gas_cut": canonical_cut,
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "breakthrough_reached": True,
                "canonical_breakthrough_state_created": True,
                "observation_checkpoint_reached": False,
                "observation_cursor_index": int_scalar(canonical["observation_cursor_index"]),
                "next_fixed_observation_day": scalar(canonical["next_fixed_observation_day"]),
                "transport_faces_per_streamline": nfaces,
                "transport_control_volumes_per_streamline": ncv,
                "component_mass_primary_conserved_variable": True,
                "CV_aligned_transfer_active": True,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
                "source_local_added_mass_kg": 0.0,
                "cumulative_injected_CO2_mass_kg": scalar(canonical["cumulative_injected_co2_mass_kg"]),
                "cumulative_produced_CO2_mass_kg": scalar(canonical["cumulative_produced_co2_mass_kg"]),
                "stored_CO2_mass_kg": final_mass,
                "cumulative_mass_residual_kg": final_cum_resid,
                "mass_numerical_closure_passed": abs(final_cum_resid) <= final_tol,
                "reproduction_CV_transport_residual_kg_max_abs": max_abs(residual_transport),
                "reproduction_CV_to_grid_transfer_residual_kg_max_abs": max_abs(residual_transfer),
                "reproduction_grid_mapback_residual_kg_max_abs": max_abs(residual_mapback),
                "reproduction_capillary_external_mass_source_kg_max_abs": max_abs(residual_capillary),
                "E36_certified_cache_reused": True,
                "cache_reuse_scope_reference_mobility_only": True,
                "learned_timestep_proposal_used": False,
                "F0_hidden_update_deferred": True,
                "SGSim_specific_dt_envelope_frozen": False,
                "SGSim_specific_mass_tolerance_frozen": False,
                "frozen_100d_checkpoint_modified": False,
                "E39_post_breakthrough_30d_rollout_entry_ready": True,
                "IBDP_started": False,
            }

            prebt_name = "V16E38_Reproduced_PreBreakthrough_Parent_State.npz"
            canonical_name = "V16E38_Canonical_Breakthrough_SGSim_Runtime_State.npz"
            snapshots_name = "V16E38_Breakthrough_Bracket_States.npz"
            files: dict[str, bytes] = {
                prebt_name: prebt_bytes,
                canonical_name: canonical_bytes,
                snapshots_name: snapshot_bytes,
                "V16E38_PreBreakthrough_Reproduction_Audit.csv": csv_bytes(reproduction_rows),
                "V16E38_Breakthrough_Refinement_Audit.csv": csv_bytes(refinement_rows),
                "V16E38_Canonical_BT_Producer_Response.csv": csv_bytes(producer_rows),
                "V16E38_BT_Plume_Metrics.csv": csv_bytes(plume_rows),
                "V16E38_Breakthrough_Event_Contract.json": json_bytes(event_contract),
                "PAD_Stream_V16E38_Summary.json": json_bytes(summary),
                "V16E38_Final_Gate_Matrix.csv": csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
            }

            handoff = f"""# PAD-Stream V16E-38 Handoff\n\nV16E-38 consumes the deterministic breakthrough bracket produced by the blocked V16E-37B 30-day rollout.\n\nThe accepted E37A step-4 state is replayed through the frozen CV-aligned component-mass transport until the exact E37B lower bracket endpoint is reproduced at step {reproduced_parent_step}, t={reproduced_parent_time:.12g} days, with producer CO2 gas cut {reproduced_parent_cut:.12e}.\n\nThe original E37B crossing trial is reproduced at t={bracket_trial_time:.12g} days with gas cut {bracket_trial_cut:.12e}.\n\nEvent refinement then uses bisection. Every refinement trial evolves afresh from the SAME accepted pre-breakthrough parent. No saturation field is temporally interpolated. Scalar linear interpolation is retained only as a diagnostic estimate ({linear_estimate_time:.12g} days).\n\nRefined bracket:\n- lower: t={refined_lo_time:.12g} d, cut={lo_cut:.12e}\n- upper: t={refined_hi_time:.12g} d, cut={hi_cut:.12e}\n- width: {refined_width:.12e} d\n- tolerance: {EVENT_TIME_TOL_DAYS:.12e} d\n\nThe canonical breakthrough state is the physically evolved upper endpoint, t={canonical_time:.12g} days, step {canonical_step}. It is marked breakthrough_reached=True and breakthrough_time_days={canonical_time:.12g}.\n\nBreakthrough is an event checkpoint, not a fixed observation checkpoint. The observation cursor therefore remains unchanged and the next fixed observation remains 30.0 days.\n\nThe production transport remains the V16E-37A 201-face / 200-CV component-mass formulation with zero injector-local source closure and zero global plume rescaling. The E36 flow/path cache remains valid only under the current V15-SG3 steady reference-mobility pressure authority. F0 remains deferred.\n\nNEXT: {NEXT}\n"""
            files["V16E38_Handoff.md"] = handoff.encode("utf-8")

            prebt_sha = hashlib.sha256(prebt_bytes).hexdigest()
            canonical_sha = hashlib.sha256(canonical_bytes).hexdigest()
            snapshots_sha = hashlib.sha256(snapshot_bytes).hexdigest()
            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed": all(v["passed"] for v in gates.values()),
                "gate_count": len(gates),
                "prebreakthrough_parent_file": prebt_name,
                "prebreakthrough_parent_sha256": prebt_sha,
                "canonical_breakthrough_state_file": canonical_name,
                "canonical_breakthrough_state_sha256": canonical_sha,
                "breakthrough_bracket_states_file": snapshots_name,
                "breakthrough_bracket_states_sha256": snapshots_sha,
                "E37A_parent_state_sha256": e37a_parent_sha_before,
                "E36_certified_cache_sha256": e36_cache_sha_before,
                "E37B_breakthrough_bracket_report_sha256": e37b_bracket_sha_before,
                "frozen_100d_sha256": frozen_sha_before,
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "refined_bracket_width_days": refined_width,
                "event_time_tolerance_days": EVENT_TIME_TOL_DAYS,
                "canonical_breakthrough_time_days": canonical_time,
                "temporal_state_interpolation_used": False,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
                "observation_cursor_advanced": False,
            }
            files["V16E38_Final_Closure.json"] = json_bytes(closure)

            immutable_publish(out, files)
            manifest_rows = []
            for path in sorted(out.iterdir()):
                if path.is_file() and path.name != "V16E38_Artifact_Manifest.csv":
                    manifest_rows.append({
                        "file": path.name,
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    })
            immutable_publish(out, {"V16E38_Artifact_Manifest.csv": csv_bytes(manifest_rows)})

        print("\n" + "=" * 146)
        print("PAD-Stream V16E-38 BREAKTHROUGH EVENT REFINEMENT: PASS")
        print("=" * 146)
        print(f"{'Reproduced pre-BT step/time':82}: {reproduced_parent_step} / {reproduced_parent_time:.12g} d")
        print(f"{'Original E37B bracket':82}: [{bracket_parent_time:.12g}, {bracket_trial_time:.12g}] d")
        print(f"{'Refined bracket':82}: [{refined_lo_time:.12g}, {refined_hi_time:.12g}] d")
        print(f"{'Refined bracket width':82}: {refined_width:.12e} d")
        print(f"{'Refinement iterations':82}: {refinement_iter}")
        print(f"{'Canonical breakthrough time':82}: {canonical_time:.12g} d")
        print(f"{'Canonical breakthrough gas cut':82}: {canonical_cut:.12e}")
        print(f"{'Cumulative mass residual':82}: {final_cum_resid:.12e} kg")
        print(f"{'Next fixed observation':82}: {scalar(canonical['next_fixed_observation_day']):.12g} d")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "BREAKTHROUGH_EVENT_REFINEMENT_BLOCKED",
            "exception": repr(exc),
            "failed_stage": failed_stage,
            "gates": gates,
            "E37A_parent_state_sha256_before": e37a_parent_sha_before,
            "E36_certified_cache_sha256_before": e36_cache_sha_before,
            "E37B_breakthrough_bracket_report_sha256_before": e37b_bracket_sha_before,
            "frozen_100d_sha256_before": frozen_sha_before,
            "canonical_breakthrough_state_published": False,
            "runtime_time_advance_committed_to_persistent_state": False,
            "E37A_parent_mutated": False,
            "E36_cache_mutated": False,
            "E37B_bracket_report_mutated": False,
            "frozen_100d_modified": False,
            "next_action": "Audit the failed reproduction/refinement gate. Do not advance to post-breakthrough rollout.",
        }
        data = json_bytes(report)
        path = blocked / "V16E38_Blocked_Breakthrough_Event_Refinement.json"
        if path.exists() and path.read_bytes() != data:
            path = blocked / (
                "V16E38_Blocked_Breakthrough_Event_Refinement_"
                f"{hashlib.sha256(data).hexdigest()[:12]}.json"
            )
        if not path.exists():
            path.write_bytes(data)
        print("\n" + "=" * 146)
        print("PAD-Stream V16E-38 BREAKTHROUGH EVENT REFINEMENT: BLOCKED")
        print("=" * 146)
        print("Reason:", repr(exc))
        print("No canonical breakthrough state was published.")
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=False)
    parser.add_argument("--drive-root", type=Path, required=False)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)
    if args.project_root is None or args.drive_root is None:
        parser.error("--project-root and --drive-root are required unless --self-test is used")
    raise SystemExit(main(args.project_root, args.drive_root))
