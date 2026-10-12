from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import zipfile
from typing import Any

import numpy as np


MILESTONE = "V16E-41-R3-R5"
STATUS = "MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATED"
NEXT = "V16E-41-R3-R6 - Production Runtime Refresh Policy Freeze"

EXPECTED_GRID = (15, 50, 50)
BACKGROUND_SATURATION = 0.20
VISIBLE_INCREMENT_THRESHOLD = 1.0e-4
ACTIVE_INCREMENT_THRESHOLD = 1.0e-8
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0

CALIBRATION_TARGET_DAY = 80.0

EXPECTED_PARENT_STEP = 3975
EXPECTED_PARENT_TIME_DAYS = 69.88346704782309
EXPECTED_PARENT_STATE_SHA256 = (
    "8714f5b35b99472de0251def022043076f85fb9cee2ada1cfc4d7b7441cce5e6"
)

EXPECTED_R3R4R1_STATUS = (
    "SAME_PARENT_MASS_CONSERVATIVE_REFRESHED_FLOW_CFL_ALIGNED_TRANSITION_VALIDATED"
)
EXPECTED_R3R4R1_CHILD_SHA256 = (
    "41206353364266360752d078d5c74666cf0ab07a39a312f5f30a3d13df5b4f45"
)

R3R4R1_RUNNER = "PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4R1_GIT_BLOB = "5f8433437ce111533338ceada922f51abb2edefe"

R3R4R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R4R1_REFRESHED_FLOW_CFL_ALIGNMENT_REPAIR"
)
R3R4R1_SUMMARY = "PAD_Stream_V16E41R3R4R1_Summary.json"
R3R4R1_CLOSURE = "V16E41R3R4R1_Final_Closure.json"

R3R3_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R3_SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FREEZE"
)
R3R3_CONTRACT = "PAD_Stream_V16E41R3R3_Architecture_Contract.json"
EXPECTED_R3R3_STATUS = "SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FROZEN"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R5_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R5_BLOCKED_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION"
)

POLICY_ORDER = [
    "EVENT_ONLY_BASELINE",
    "HALF_OBSERVED_STALE_INTERVAL",
    "QUARTER_OBSERVED_STALE_INTERVAL",
    "EIGHTH_OBSERVED_STALE_INTERVAL",
]
REFERENCE_POLICY = "EIGHTH_OBSERVED_STALE_INTERVAL"

# Calibration tolerances against the finest finite-cadence reference.
# These are runtime-policy convergence gates, not physical truth tolerances.
CONVERGENCE_TOLERANCES = {
    "saturation_relative_L2": 5.0e-3,
    "saturation_Linf": 2.0e-2,
    "pressure_relative_L2": 1.0e-2,
    "stored_mass_relative": 1.0e-4,
    "cumulative_produced_mass_relative": 5.0e-3,
    "producer_gas_cut_absolute": 5.0e-3,
    "active_cell_count_relative": 2.0e-2,
    "visible_cell_count_relative": 2.0e-2,
}


class GateError(RuntimeError):
    pass


class PolicyDisqualified(RuntimeError):
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


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(float(np.linalg.norm(bb.ravel())), 1.0e-30)
    )


def relative_scalar(a: float, b: float) -> float:
    return float(abs(float(a) - float(b)) / max(abs(float(b)), 1.0))


def terminal_plume_metrics(saturation: np.ndarray) -> dict[str, Any]:
    sat = np.asarray(saturation, dtype=np.float64)
    inc = np.maximum(sat - BACKGROUND_SATURATION, 0.0)
    return {
        "saturation_min": float(np.min(sat)),
        "saturation_max": float(np.max(sat)),
        "saturation_mean": float(np.mean(sat)),
        "active_cell_count": int(np.sum(inc > ACTIVE_INCREMENT_THRESHOLD)),
        "visible_cell_count": int(np.sum(inc > VISIBLE_INCREMENT_THRESHOLD)),
        "incremental_saturation_sum": float(np.sum(inc)),
    }


def make_same_time_reconciled_state(
    current: dict[str, np.ndarray],
    reconciled_saturation: np.ndarray,
    pressure_psi: np.ndarray,
) -> dict[str, np.ndarray]:
    out = {
        k: np.asarray(v).copy()
        for k, v in current.items()
    }
    sat = np.asarray(reconciled_saturation, dtype=np.float64)
    out["transport_saturation"] = sat
    out["co2_incremental_saturation"] = sat - BACKGROUND_SATURATION
    out["accepted_pressure_psi"] = np.asarray(pressure_psi, dtype=np.float64)
    if "transport_saturation_history" in out:
        out["transport_saturation_history"] = np.maximum(
            np.asarray(out["transport_saturation_history"], dtype=np.float64),
            sat,
        )
    out["mass_conservative_flow_refresh_active"] = np.asarray(True, dtype=bool)
    out["pressure_saturation_reconciliation_converged"] = np.asarray(True, dtype=bool)
    out["path_cache_valid"] = np.asarray(True, dtype=bool)
    out["tof_cache_valid"] = np.asarray(True, dtype=bool)
    out["exact_retrace_required"] = np.asarray(False, dtype=bool)
    return out


def build_flow_epoch(
    *,
    current: dict[str, np.ndarray],
    r3r4r1: Any,
    physics: Any,
    r3r2r1: Any,
    e36: Any,
    e37a: Any,
    sg2: Any,
    sg3: Any,
    sg4: Any,
    sg5: Any,
    sg6: Any,
    sg7a: Any,
    sg7d: Any,
    permeability_md: np.ndarray,
    cell_pore_volume_m3: float,
) -> tuple[dict[str, np.ndarray], dict[str, Any], list[dict[str, Any]]]:
    parent_sat = np.asarray(
        current["transport_saturation"],
        dtype=np.float64,
    )
    parent_pressure = np.asarray(
        current["accepted_pressure_psi"],
        dtype=np.float64,
    )
    p_ref = scalar(current["co2_density_reference_pressure_pa"])
    parent_stored = scalar(current["stored_co2_mass_current_kg"])

    parent_mass = r3r4r1.parent_cellwise_component_mass(
        physics,
        parent_sat,
        parent_pressure,
        p_ref,
        cell_pore_volume_m3,
    )
    mass_tol = max(
        1.0e-6,
        1.0e-10 * max(abs(parent_stored), 1.0),
    )
    if abs(float(np.sum(parent_mass)) - parent_stored) > mass_tol:
        raise PolicyDisqualified(
            "refresh_parent_cellwise_mass_ledger_mismatch:"
            f"{float(np.sum(parent_mass))-parent_stored}"
        )

    refresh = r3r4r1.fixed_point_refresh(
        physics=physics,
        r3r2r1=r3r2r1,
        sg2=sg2,
        sg3=sg3,
        permeability_md=permeability_md,
        parent_mass=parent_mass,
        parent_saturation=parent_sat,
        parent_pressure_psi=parent_pressure,
        p_ref_gas_pa=p_ref,
        cell_pore_volume_m3=cell_pore_volume_m3,
    )

    sat = np.asarray(refresh["saturation"], dtype=np.float64)
    pressure = np.asarray(refresh["pressure_psi"], dtype=np.float64)

    producer_rates, producer_sink = r3r2r1.producer_rates_updated(
        sg3,
        pressure,
        refresh["producer_wi"],
    )
    if not all(float(v["m3_s"]) > 0.0 for v in producer_rates.values()):
        raise PolicyDisqualified("refresh_BHP_well_not_producing")

    qx, qy, qz = sg4.compute_face_fluxes(
        pressure,
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
    if conservation["local_relative_l2_error"] >= 1.0e-8:
        raise PolicyDisqualified(
            "refresh_local_flow_conservation:"
            f"{conservation['local_relative_l2_error']}"
        )
    if conservation["global_relative_mismatch"] >= 1.0e-8:
        raise PolicyDisqualified(
            "refresh_global_flow_conservation:"
            f"{conservation['global_relative_mismatch']}"
        )

    vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
    _faces, seeds = sg5.build_seeds(qx, qy, qz)
    streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)

    seed_weight = float(sum(float(s["weight_m3_s"]) for s in seeds))
    captured_weight = float(
        sum(
            float(s["weight_m3_s"])
            for s in streamlines
            if s["status"] == "PRODUCER"
        )
    )
    capture_fraction = captured_weight / max(seed_weight, 1.0e-30)
    if abs(capture_fraction - 1.0) > 1.0e-10:
        raise PolicyDisqualified(
            f"refresh_streamline_capture_fraction:{capture_fraction}"
        )

    sg6_streamlines = r3r4r1.convert_sg5_to_sg6_streamlines(streamlines)
    db = sg6.build_transport_database(sg6_streamlines)

    xyz_m = np.asarray(db["xyz_m"], dtype=np.float64)
    tau_s = np.asarray(db["tau_s"], dtype=np.float64)
    tau_end_s = np.asarray(db["tau_end_s"], dtype=np.float64)
    weights_m3_s = np.asarray(db["weights_m3_s"], dtype=np.float64)
    labels = np.asarray(db["producer"]).astype(str)
    xi_faces = np.asarray(db["xi"], dtype=np.float64)

    cfl_dt_days = r3r4r1.transport_cfl_dt_days(
        sg7a,
        xi_faces,
        tau_end_s,
    )
    if not np.isfinite(cfl_dt_days) or cfl_dt_days <= 0.0:
        raise PolicyDisqualified(f"refresh_invalid_CFL_dt:{cfl_dt_days}")

    weights_m3_day = weights_m3_s * DAY_TO_S
    tof_days = tau_s / DAY_TO_S
    nstream = int(xyz_m.shape[0])
    nfaces = int(xi_faces.shape[0])
    ncv = nfaces - 1

    operator = sg7d.build_subsegment_operator(
        xyz_m,
        tof_days,
        weights_m3_day,
    )
    geometry = e37a.build_control_volume_geometry(
        physics,
        operator,
        pressure,
        p_ref,
        nstream,
        ncv,
    )
    face_pressure = e37a.build_face_pressure(
        e36,
        sg7d,
        xyz_m,
        pressure,
    )

    reconciled_current = make_same_time_reconciled_state(
        current,
        sat,
        pressure,
    )

    epoch = {
        "pressure_psi": pressure,
        "qx": qx,
        "qy": qy,
        "qz": qz,
        "geometry": geometry,
        "face_pressure_psi": face_pressure,
        "weights_m3_day": weights_m3_day,
        "labels": labels,
        "xi_faces": xi_faces,
        "cfl_dt_days": float(cfl_dt_days),
        "nstream": nstream,
        "nfaces": nfaces,
        "ncv": ncv,
        "capture_fraction": float(capture_fraction),
        "flow_local_residual": float(
            conservation["local_relative_l2_error"]
        ),
        "flow_global_residual": float(
            conservation["global_relative_mismatch"]
        ),
        "fixed_point_iterations": int(refresh["iterations"]),
        "refresh_pressure_rel_L2_vs_parent": float(
            refresh["pressure_rel_L2_vs_parent"]
        ),
        "refresh_saturation_Linf_vs_parent": float(
            refresh["saturation_Linf_vs_parent"]
        ),
        "refresh_global_mass_error_kg": float(
            refresh["global_mass_error_kg"]
        ),
        "refresh_max_cell_mass_error_kg": float(
            refresh["max_cell_mass_error_kg"]
        ),
    }
    return reconciled_current, epoch, refresh["rows"]


def run_policy(
    *,
    policy_name: str,
    max_epoch_days: float | None,
    parent: dict[str, np.ndarray],
    r3r4r1: Any,
    physics: Any,
    r3r2r1: Any,
    e36: Any,
    e37a: Any,
    sg2: Any,
    sg3: Any,
    sg4: Any,
    sg5: Any,
    sg6: Any,
    sg7a: Any,
    sg7d: Any,
    permeability_md: np.ndarray,
    cell_pore_volume_m3: float,
) -> dict[str, Any]:
    current = {
        k: np.asarray(v).copy()
        for k, v in parent.items()
    }

    refresh_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    capacity_event_rows: list[dict[str, Any]] = []
    accepted_dts: list[float] = []
    raw_capacity_margins: list[float] = []

    refresh_count = 0
    cadence_refresh_count = 0
    capacity_refresh_count = 0
    total_fixed_point_iterations = 0
    last_refresh_time: float | None = None
    epoch_start_time: float | None = None
    epoch: dict[str, Any] | None = None
    last_gas_cut = scalar(current["current_producer_co2_gas_cut"])

    def do_refresh(trigger: str) -> None:
        nonlocal current
        nonlocal epoch
        nonlocal refresh_count
        nonlocal cadence_refresh_count
        nonlocal capacity_refresh_count
        nonlocal total_fixed_point_iterations
        nonlocal last_refresh_time
        nonlocal epoch_start_time

        before_time = scalar(current["physical_time_days"])
        before_step = int_scalar(current["accepted_step_index"])
        before_inj = scalar(current["cumulative_injected_co2_mass_kg"])
        before_prod = scalar(current["cumulative_produced_co2_mass_kg"])
        before_stored = scalar(current["stored_co2_mass_current_kg"])

        current_new, epoch_new, fp_rows = build_flow_epoch(
            current=current,
            r3r4r1=r3r4r1,
            physics=physics,
            r3r2r1=r3r2r1,
            e36=e36,
            e37a=e37a,
            sg2=sg2,
            sg3=sg3,
            sg4=sg4,
            sg5=sg5,
            sg6=sg6,
            sg7a=sg7a,
            sg7d=sg7d,
            permeability_md=permeability_md,
            cell_pore_volume_m3=cell_pore_volume_m3,
        )

        if scalar(current_new["physical_time_days"]) != before_time:
            raise PolicyDisqualified("refresh_advanced_time")
        if int_scalar(current_new["accepted_step_index"]) != before_step:
            raise PolicyDisqualified("refresh_advanced_step")
        if scalar(current_new["cumulative_injected_co2_mass_kg"]) != before_inj:
            raise PolicyDisqualified("refresh_changed_injection_ledger")
        if scalar(current_new["cumulative_produced_co2_mass_kg"]) != before_prod:
            raise PolicyDisqualified("refresh_changed_production_ledger")
        if abs(
            scalar(current_new["stored_co2_mass_current_kg"]) - before_stored
        ) > max(1.0e-6, 1.0e-10 * max(abs(before_stored), 1.0)):
            raise PolicyDisqualified("refresh_changed_stored_mass_ledger")

        current = current_new
        epoch = epoch_new
        refresh_count += 1
        if trigger == "CADENCE":
            cadence_refresh_count += 1
        if trigger == "CAPACITY_PREFLIGHT_REJECTION":
            capacity_refresh_count += 1
        total_fixed_point_iterations += epoch_new["fixed_point_iterations"]
        last_refresh_time = before_time
        epoch_start_time = before_time

        refresh_rows.append(
            {
                "policy": policy_name,
                "refresh_index": refresh_count,
                "trigger": trigger,
                "physical_time_days": before_time,
                "accepted_step_index": before_step,
                "fixed_point_iterations": epoch_new["fixed_point_iterations"],
                "CFL_dt_days": epoch_new["cfl_dt_days"],
                "streamline_count": epoch_new["nstream"],
                "capture_fraction": epoch_new["capture_fraction"],
                "flow_local_relative_residual": epoch_new[
                    "flow_local_residual"
                ],
                "flow_global_relative_residual": epoch_new[
                    "flow_global_residual"
                ],
                "pressure_rel_L2_vs_pre_refresh": epoch_new[
                    "refresh_pressure_rel_L2_vs_parent"
                ],
                "saturation_Linf_vs_pre_refresh": epoch_new[
                    "refresh_saturation_Linf_vs_parent"
                ],
                "refresh_global_mass_error_kg": epoch_new[
                    "refresh_global_mass_error_kg"
                ],
            }
        )

    # Hard initialization refresh.
    do_refresh("RESTART_OR_INITIALIZATION")

    persistent_capacity_guard_time: float | None = None

    while scalar(current["physical_time_days"]) < CALIBRATION_TARGET_DAY - 1.0e-13:
        now = scalar(current["physical_time_days"])
        if epoch is None or epoch_start_time is None:
            raise PolicyDisqualified("missing_active_flow_epoch")

        # Finite-cadence refreshes happen at exact epoch-age boundaries.
        if max_epoch_days is not None:
            due = epoch_start_time + float(max_epoch_days)
            if now >= due - 1.0e-13 and now < CALIBRATION_TARGET_DAY - 1.0e-13:
                do_refresh("CADENCE")
                persistent_capacity_guard_time = None
                continue

        remaining = CALIBRATION_TARGET_DAY - now
        dt = min(float(epoch["cfl_dt_days"]), remaining)

        if max_epoch_days is not None:
            due = epoch_start_time + float(max_epoch_days)
            if due > now + 1.0e-13:
                dt = min(dt, due - now)

        if not np.isfinite(dt) or dt <= 0.0:
            raise PolicyDisqualified(f"nonpositive_transport_dt:{dt}")

        parent_sat = np.asarray(
            current["transport_saturation"],
            dtype=np.float64,
        )
        pressure = np.asarray(
            epoch["pressure_psi"],
            dtype=np.float64,
        )
        p_ref = scalar(current["co2_density_reference_pressure_pa"])
        parent_stored = scalar(current["stored_co2_mass_current_kg"])

        recomputed_parent = float(
            physics.stored_co2_mass_kg(
                parent_sat,
                pressure,
                p_ref,
                cell_pore_volume_m3,
            )
        )
        parent_mass_tol = max(
            1.0e-6,
            1.0e-10 * max(abs(parent_stored), 1.0),
        )
        if abs(recomputed_parent - parent_stored) > parent_mass_tol:
            raise PolicyDisqualified(
                "transport_parent_mass_pressure_mismatch:"
                f"{recomputed_parent-parent_stored}"
            )

        old_cv_sat, old_cv_mass, sample_closure = (
            e37a.sample_grid_inventory_to_control_volumes(
                physics,
                parent_sat,
                pressure,
                p_ref,
                epoch["geometry"],
                epoch["nstream"],
                epoch["ncv"],
            )
        )
        sample_tol = max(
            1.0e-6,
            1.0e-10 * max(abs(float(np.sum(old_cv_mass))), 1.0),
        )
        if abs(sample_closure) > sample_tol:
            raise PolicyDisqualified(
                f"grid_to_CV_sampling_closure:{sample_closure}"
            )

        transport = e37a.advance_component_mass_control_volumes(
            physics,
            sg7a,
            old_cv_sat,
            old_cv_mass,
            epoch["geometry"]["cv_pressure_mass_coeff"],
            epoch["face_pressure_psi"],
            p_ref,
            epoch["weights_m3_day"],
            epoch["xi_faces"],
            dt,
        )

        injected_step = float(transport["injected_mass_kg"])
        produced_step = float(transport["produced_mass_kg"])
        physical_injected = INJECTOR_MASS_RATE_KG_DAY * dt
        injection_tol = max(
            1.0e-6,
            1.0e-12 * max(abs(physical_injected), 1.0),
        )
        if abs(injected_step - physical_injected) > injection_tol:
            raise PolicyDisqualified(
                "fixed_rate_injection_mismatch:"
                f"{injected_step-physical_injected}"
            )

        parent_mass = r3r4r1.parent_cellwise_component_mass(
            physics,
            parent_sat,
            pressure,
            p_ref,
            cell_pore_volume_m3,
        )
        target_final_mass = (
            parent_stored
            + injected_step
            - produced_step
        )

        preflight = r3r4r1.preflight_mapback_capacity(
            physics=physics,
            parent_saturation=parent_sat,
            parent_mass=parent_mass,
            old_cv_saturation=old_cv_sat,
            new_cv_saturation=transport["new_saturation"],
            geometry=epoch["geometry"],
            pressure_psi=pressure,
            p_ref_gas_pa=p_ref,
            cell_pore_volume_m3=cell_pore_volume_m3,
        )
        raw_capacity_margins.append(
            float(preflight["minimum_capacity_margin_kg"])
        )

        if preflight["overcapacity_cell_count"] > 0:
            capacity_event_rows.append(
                {
                    "policy": policy_name,
                    "physical_time_days": now,
                    "accepted_step_index": int_scalar(
                        current["accepted_step_index"]
                    ),
                    "trial_dt_days": dt,
                    "overcapacity_cell_count": preflight[
                        "overcapacity_cell_count"
                    ],
                    "max_capacity_excess_kg": preflight[
                        "max_capacity_excess_kg"
                    ],
                    "minimum_capacity_margin_kg": preflight[
                        "minimum_capacity_margin_kg"
                    ],
                }
            )
            if (
                persistent_capacity_guard_time is not None
                and abs(now - persistent_capacity_guard_time) <= 1.0e-13
            ):
                raise PolicyDisqualified(
                    "persistent_capacity_after_same_parent_refresh:"
                    f"{now}"
                )

            persistent_capacity_guard_time = now
            do_refresh("CAPACITY_PREFLIGHT_REJECTION")
            continue

        persistent_capacity_guard_time = None

        mapping = e37a.map_control_volume_increment_to_grid(
            physics,
            parent_sat,
            old_cv_sat,
            transport["new_saturation"],
            old_cv_mass,
            transport["new_mass"],
            epoch["geometry"],
            pressure,
            p_ref,
            cell_pore_volume_m3,
            target_final_mass,
        )
        pre_cap_sat = np.asarray(
            mapping["corrected_saturation"],
            dtype=np.float64,
        )

        capillary = physics.conservative_capillary_mass_redistribution(
            transport_saturation=pre_cap_sat,
            permeability_md=permeability_md,
            pressure_psi=pressure,
            p_ref_pa=p_ref,
            cell_pore_volume_m3=cell_pore_volume_m3,
            dt_seconds=dt * DAY_TO_S,
        )
        child_sat = np.asarray(
            capillary["corrected"],
            dtype=np.float64,
        )
        final_stored = float(capillary["final_mass_state_kg"])
        step_residual = (
            final_stored
            - parent_stored
            - injected_step
            + produced_step
        )
        closure_tol = max(
            1.0e-6,
            1.0e-10 * max(abs(target_final_mass), 1.0),
        )
        if abs(capillary["external_mass_change_kg"]) > closure_tol:
            raise PolicyDisqualified(
                "capillary_external_mass_change:"
                f"{capillary['external_mass_change_kg']}"
            )
        if abs(step_residual) > closure_tol:
            raise PolicyDisqualified(
                f"step_component_mass_closure:{step_residual}"
            )

        prod_rows, aggregate_cut = e37a.producer_rows_from_flux(
            epoch["labels"],
            epoch["weights_m3_day"],
            transport["outlet_fractional_flow"],
            transport["face_mass_flux_kg_day"][:, -1],
            dt,
        )
        if not np.isfinite(aggregate_cut) or not 0.0 <= aggregate_cut <= 1.0:
            raise PolicyDisqualified(
                f"producer_gas_cut_invalid:{aggregate_cut}"
            )

        child = e36.make_child_state(
            current,
            child_sat,
            pressure,
            p_ref,
            dt,
            produced_step,
            aggregate_cut,
            final_stored,
            step_residual,
            False,
        )
        child["transport_face_count"] = np.asarray(
            epoch["nfaces"],
            dtype=np.int64,
        )
        child["transport_control_volume_count"] = np.asarray(
            epoch["ncv"],
            dtype=np.int64,
        )
        child["mass_conservative_flow_refresh_active"] = np.asarray(
            True,
            dtype=bool,
        )
        child["runtime_refresh_policy_name_ascii"] = np.frombuffer(
            policy_name.encode("ascii"),
            dtype=np.uint8,
        )

        accepted_dts.append(float(dt))
        last_gas_cut = float(aggregate_cut)

        step_rows.append(
            {
                "policy": policy_name,
                "accepted_step_index": int_scalar(
                    child["accepted_step_index"]
                ),
                "parent_time_days": now,
                "accepted_time_days": scalar(
                    child["physical_time_days"]
                ),
                "accepted_dt_days": dt,
                "active_epoch_CFL_dt_days": epoch["cfl_dt_days"],
                "epoch_age_before_step_days": now - epoch_start_time,
                "raw_minimum_capacity_margin_kg": preflight[
                    "minimum_capacity_margin_kg"
                ],
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
            }
        )
        current = {
            k: np.asarray(v).copy()
            for k, v in child.items()
        }

    if abs(scalar(current["physical_time_days"]) - CALIBRATION_TARGET_DAY) > 1.0e-12:
        raise PolicyDisqualified(
            "policy_failed_exact_target_landing:"
            f"{scalar(current['physical_time_days'])}"
        )

    # Standardized terminal same-time refresh for fair state comparison.
    before_terminal_step = int_scalar(current["accepted_step_index"])
    before_terminal_time = scalar(current["physical_time_days"])
    current, terminal_epoch, terminal_fp_rows = build_flow_epoch(
        current=current,
        r3r4r1=r3r4r1,
        physics=physics,
        r3r2r1=r3r2r1,
        e36=e36,
        e37a=e37a,
        sg2=sg2,
        sg3=sg3,
        sg4=sg4,
        sg5=sg5,
        sg6=sg6,
        sg7a=sg7a,
        sg7d=sg7d,
        permeability_md=permeability_md,
        cell_pore_volume_m3=cell_pore_volume_m3,
    )
    if int_scalar(current["accepted_step_index"]) != before_terminal_step:
        raise PolicyDisqualified("terminal_refresh_advanced_step")
    if scalar(current["physical_time_days"]) != before_terminal_time:
        raise PolicyDisqualified("terminal_refresh_advanced_time")

    terminal_sat = np.asarray(
        current["transport_saturation"],
        dtype=np.float64,
    )
    terminal_pressure = np.asarray(
        current["accepted_pressure_psi"],
        dtype=np.float64,
    )
    plume = terminal_plume_metrics(terminal_sat)

    final_stored = scalar(current["stored_co2_mass_current_kg"])
    final_prod = scalar(current["cumulative_produced_co2_mass_kg"])
    final_inj = scalar(current["cumulative_injected_co2_mass_kg"])
    initial_stored = scalar(current["stored_co2_mass_initial_kg"])
    cumulative_residual = (
        final_stored
        - initial_stored
        - final_inj
        + final_prod
    )

    return {
        "policy": policy_name,
        "max_epoch_days": max_epoch_days,
        "completed": True,
        "terminal_state": current,
        "terminal_saturation": terminal_sat,
        "terminal_pressure": terminal_pressure,
        "terminal_plume": plume,
        "terminal_gas_cut": float(last_gas_cut),
        "final_stored_mass_kg": final_stored,
        "final_cumulative_produced_mass_kg": final_prod,
        "final_cumulative_injected_mass_kg": final_inj,
        "cumulative_mass_residual_kg": cumulative_residual,
        "accepted_transition_count": len(step_rows),
        "refresh_count_policy_runtime": refresh_count,
        "cadence_refresh_count": cadence_refresh_count,
        "capacity_refresh_count": capacity_refresh_count,
        "terminal_standardization_refresh_count": 1,
        "total_refresh_count_including_terminal": refresh_count + 1,
        "total_fixed_point_iterations_policy_runtime": total_fixed_point_iterations,
        "terminal_fixed_point_iterations": int(
            terminal_epoch["fixed_point_iterations"]
        ),
        "total_fixed_point_iterations_including_terminal": (
            total_fixed_point_iterations
            + int(terminal_epoch["fixed_point_iterations"])
        ),
        "min_accepted_dt_days": float(np.min(accepted_dts)),
        "median_accepted_dt_days": float(np.median(accepted_dts)),
        "max_accepted_dt_days": float(np.max(accepted_dts)),
        "min_raw_capacity_margin_kg": float(np.min(raw_capacity_margins)),
        "step_rows": step_rows,
        "refresh_rows": refresh_rows,
        "capacity_event_rows": capacity_event_rows,
    }


def convergence_metrics(
    case: dict[str, Any],
    ref: dict[str, Any],
) -> dict[str, float]:
    sat = case["terminal_saturation"]
    sat_ref = ref["terminal_saturation"]
    pressure = case["terminal_pressure"]
    pressure_ref = ref["terminal_pressure"]

    active = case["terminal_plume"]["active_cell_count"]
    active_ref = ref["terminal_plume"]["active_cell_count"]
    visible = case["terminal_plume"]["visible_cell_count"]
    visible_ref = ref["terminal_plume"]["visible_cell_count"]

    return {
        "saturation_relative_L2": relative_l2(sat, sat_ref),
        "saturation_Linf": float(
            np.max(np.abs(np.asarray(sat) - np.asarray(sat_ref)))
        ),
        "pressure_relative_L2": relative_l2(
            pressure,
            pressure_ref,
        ),
        "stored_mass_relative": relative_scalar(
            case["final_stored_mass_kg"],
            ref["final_stored_mass_kg"],
        ),
        "cumulative_produced_mass_relative": relative_scalar(
            case["final_cumulative_produced_mass_kg"],
            ref["final_cumulative_produced_mass_kg"],
        ),
        "producer_gas_cut_absolute": abs(
            case["terminal_gas_cut"] - ref["terminal_gas_cut"]
        ),
        "active_cell_count_relative": float(
            abs(active - active_ref) / max(abs(active_ref), 1)
        ),
        "visible_cell_count_relative": float(
            abs(visible - visible_ref) / max(abs(visible_ref), 1)
        ),
    }


def passes_convergence(metrics: dict[str, float]) -> bool:
    return all(
        float(metrics[name]) <= float(limit)
        for name, limit in CONVERGENCE_TOLERANCES.items()
    )


def self_test() -> None:
    observed = EXPECTED_PARENT_TIME_DAYS - 60.0
    vals = [
        observed / 2.0,
        observed / 4.0,
        observed / 8.0,
    ]
    if not (vals[0] > vals[1] > vals[2] > 0.0):
        raise RuntimeError("self_test_cadence_order")
    if not CALIBRATION_TARGET_DAY > EXPECTED_PARENT_TIME_DAYS + observed:
        raise RuntimeError("self_test_horizon_too_short")
    if REFERENCE_POLICY != "EIGHTH_OBSERVED_STALE_INTERVAL":
        raise RuntimeError("self_test_reference_policy")
    print(
        "PAD-Stream V16E-41-R3-R5 multi-refresh cadence sensitivity / "
        "runtime refresh policy calibration self-test: PASS"
    )


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
        print("\n" + "=" * 160)
        print(
            "PAD-Stream V16E-41-R3-R5 — Multi-Refresh Cadence Sensitivity / "
            "Runtime Refresh Policy Calibration"
        )
        print("=" * 160)
        print(
            f"PARENT     : step {EXPECTED_PARENT_STEP} at "
            f"{EXPECTED_PARENT_TIME_DAYS:.15g} d"
        )
        print(
            f"HORIZON    : exact {CALIBRATION_TARGET_DAY:.1f} d "
            "(calibration only; not a canonical observation)"
        )
        print(
            "VARIABLE   : maximum active flow-epoch age only"
        )
        print(
            "REFERENCE  : finest finite cadence "
            "(EIGHTH_OBSERVED_STALE_INTERVAL)"
        )
        print(
            "SELECTION  : coarsest finite cadence passing all convergence gates"
        )
        print(
            "100D CLAIM : none"
        )

        failed_stage = "predecessor_and_architecture_binding"

        r3r4r1_path = root / R3R4R1_RUNNER
        gate("R3R4R1_runner_exists", r3r4r1_path.is_file(), r3r4r1_path)
        gate(
            "R3R4R1_runner_git_blob_exact",
            git_blob_sha(r3r4r1_path, root) == R3R4R1_GIT_BLOB,
            git_blob_sha(r3r4r1_path, root),
        )
        r3r4r1 = load_module(
            r3r4r1_path,
            "pad_stream_v16e41r3r5_r3r4r1",
        )

        pred_summary_path = drive / R3R4R1_REL / R3R4R1_SUMMARY
        pred_closure_path = drive / R3R4R1_REL / R3R4R1_CLOSURE
        gate("R3R4R1_summary_exists", pred_summary_path.is_file(), pred_summary_path)
        gate("R3R4R1_closure_exists", pred_closure_path.is_file(), pred_closure_path)

        pred_summary = load_json(pred_summary_path)
        pred_closure = load_json(pred_closure_path)
        gate(
            "R3R4R1_status_exact",
            pred_summary.get("status") == EXPECTED_R3R4R1_STATUS,
            pred_summary.get("status"),
        )
        gate(
            "R3R4R1_child_SHA_exact",
            pred_summary.get("child_state_sha256") == EXPECTED_R3R4R1_CHILD_SHA256,
            pred_summary.get("child_state_sha256"),
        )
        gate(
            "R3R4R1_closure_passed",
            pred_closure.get("all_gates_passed") is True,
            pred_closure.get("all_gates_passed"),
        )
        gate(
            "R3R4R1_capacity_controller_unused",
            pred_closure.get("capacity_timestep_reduction_used") is False,
            pred_closure.get("capacity_timestep_reduction_used"),
        )

        r3r3_contract_path = drive / R3R3_REL / R3R3_CONTRACT
        gate("R3R3_contract_exists", r3r3_contract_path.is_file(), r3r3_contract_path)
        r3r3_contract = load_json(r3r3_contract_path)
        gate(
            "R3R3_status_exact",
            r3r3_contract.get("status") == EXPECTED_R3R3_STATUS,
            r3r3_contract.get("status"),
        )

        candidate_dict = r3r3_contract[
            "calibration_policy"
        ]["candidate_max_epoch_days"]
        for name in POLICY_ORDER:
            gate(
                f"R3R3_candidate_policy_present_{name}",
                name in candidate_dict,
                candidate_dict,
            )

        policy_cadences: dict[str, float | None] = {
            name: (
                None
                if candidate_dict[name] is None
                else float(candidate_dict[name])
            )
            for name in POLICY_ORDER
        }
        gate(
            "reference_policy_finite",
            policy_cadences[REFERENCE_POLICY] is not None,
            policy_cadences[REFERENCE_POLICY],
        )

        # Load exact source modules through the validated R3-R4-R1 authority.
        role_modules = {}
        for role in [
            "R3R2R1",
            "E36",
            "E37A",
            "R2_PHYSICS",
            "SG2",
            "SG3",
            "SG4",
            "SG5",
            "SG6",
            "SG7A",
            "SG7D",
        ]:
            filename, expected_blob = r3r4r1.SOURCE_BLOBS[role]
            p = root / filename
            gate(f"source_exists_{role}", p.is_file(), p)
            actual_blob = git_blob_sha(p, root)
            gate(
                f"source_blob_exact_{role}",
                actual_blob == expected_blob,
                actual_blob,
            )
            role_modules[role] = load_module(
                p,
                f"pad_stream_v16e41r3r5_{role.lower()}",
            )

        r3r2r1 = role_modules["R3R2R1"]
        e36 = role_modules["E36"]
        e37a = role_modules["E37A"]
        physics = role_modules["R2_PHYSICS"]
        sg2 = role_modules["SG2"]
        sg3 = role_modules["SG3"]
        sg4 = role_modules["SG4"]
        sg5 = role_modules["SG5"]
        sg6 = role_modules["SG6"]
        sg7a = role_modules["SG7A"]
        sg7d = role_modules["SG7D"]

        perm_filename, perm_blob = r3r4r1.SOURCE_BLOBS["PERM"]
        perm_path = root / perm_filename
        gate("PERM_exists", perm_path.is_file(), perm_path)
        gate(
            "PERM_blob_exact",
            git_blob_sha(perm_path, root) == perm_blob,
            git_blob_sha(perm_path, root),
        )

        parent_path = (
            drive
            / r3r4r1.R3R1_REL
            / r3r4r1.R3R1_STATE
        )
        gate("parent_state_exists", parent_path.is_file(), parent_path)
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

        dx_m = 20.0 * FT_TO_M
        dy_m = 20.0 * FT_TO_M
        dz_m = 4.0 * FT_TO_M
        cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m

        permeability_md = np.loadtxt(
            perm_path,
            skiprows=1,
            dtype=np.float64,
        ).reshape(EXPECTED_GRID, order="C")

        failed_stage = "four_policy_controlled_rollout"

        results: dict[str, dict[str, Any]] = {}
        policy_status_rows: list[dict[str, Any]] = []
        all_step_rows: list[dict[str, Any]] = []
        all_refresh_rows: list[dict[str, Any]] = []
        all_capacity_rows: list[dict[str, Any]] = []

        for policy_name in POLICY_ORDER:
            cadence = policy_cadences[policy_name]
            print(
                f"\n[POLICY] {policy_name} | "
                f"max_epoch_days={cadence}"
            )
            try:
                result = run_policy(
                    policy_name=policy_name,
                    max_epoch_days=cadence,
                    parent=parent,
                    r3r4r1=r3r4r1,
                    physics=physics,
                    r3r2r1=r3r2r1,
                    e36=e36,
                    e37a=e37a,
                    sg2=sg2,
                    sg3=sg3,
                    sg4=sg4,
                    sg5=sg5,
                    sg6=sg6,
                    sg7a=sg7a,
                    sg7d=sg7d,
                    permeability_md=permeability_md,
                    cell_pore_volume_m3=cell_pore_volume_m3,
                )
                results[policy_name] = result
                all_step_rows.extend(result["step_rows"])
                all_refresh_rows.extend(result["refresh_rows"])
                all_capacity_rows.extend(result["capacity_event_rows"])
                policy_status_rows.append(
                    {
                        "policy": policy_name,
                        "max_epoch_days": cadence,
                        "status": "COMPLETED",
                        "disqualification_reason": "",
                        "accepted_transition_count": result[
                            "accepted_transition_count"
                        ],
                        "refresh_count_policy_runtime": result[
                            "refresh_count_policy_runtime"
                        ],
                        "cadence_refresh_count": result[
                            "cadence_refresh_count"
                        ],
                        "capacity_refresh_count": result[
                            "capacity_refresh_count"
                        ],
                        "min_raw_capacity_margin_kg": result[
                            "min_raw_capacity_margin_kg"
                        ],
                        "cumulative_mass_residual_kg": result[
                            "cumulative_mass_residual_kg"
                        ],
                    }
                )
                print(
                    f"[PASS] {policy_name}: "
                    f"steps={result['accepted_transition_count']}, "
                    f"refreshes={result['refresh_count_policy_runtime']}, "
                    f"capacity_refreshes={result['capacity_refresh_count']}"
                )
            except PolicyDisqualified as exc:
                policy_status_rows.append(
                    {
                        "policy": policy_name,
                        "max_epoch_days": cadence,
                        "status": "DISQUALIFIED",
                        "disqualification_reason": str(exc),
                    }
                )
                print(
                    f"[DISQUALIFIED] {policy_name}: {exc}"
                )

        gate(
            "reference_policy_completed",
            REFERENCE_POLICY in results,
            [r["policy"] + ":" + r["status"] for r in policy_status_rows],
        )

        failed_stage = "convergence_comparison_and_policy_selection"

        ref = results[REFERENCE_POLICY]
        comparison_rows: list[dict[str, Any]] = []
        finite_eligible_passes: list[str] = []

        for policy_name in POLICY_ORDER:
            if policy_name not in results:
                comparison_rows.append(
                    {
                        "policy": policy_name,
                        "max_epoch_days": policy_cadences[policy_name],
                        "completed": False,
                        "eligible_for_production_selection": (
                            policy_name != "EVENT_ONLY_BASELINE"
                        ),
                        "passes_all_convergence_gates": False,
                    }
                )
                continue

            case = results[policy_name]
            metrics = convergence_metrics(case, ref)
            passes = passes_convergence(metrics)
            eligible = (
                policy_name != "EVENT_ONLY_BASELINE"
                and policy_cadences[policy_name] is not None
            )
            if eligible and passes:
                finite_eligible_passes.append(policy_name)

            comparison_rows.append(
                {
                    "policy": policy_name,
                    "max_epoch_days": policy_cadences[policy_name],
                    "completed": True,
                    "eligible_for_production_selection": eligible,
                    "passes_all_convergence_gates": passes,
                    **metrics,
                    "accepted_transition_count": case[
                        "accepted_transition_count"
                    ],
                    "refresh_count_policy_runtime": case[
                        "refresh_count_policy_runtime"
                    ],
                    "cadence_refresh_count": case[
                        "cadence_refresh_count"
                    ],
                    "capacity_refresh_count": case[
                        "capacity_refresh_count"
                    ],
                    "total_fixed_point_iterations_including_terminal": case[
                        "total_fixed_point_iterations_including_terminal"
                    ],
                    "min_accepted_dt_days": case[
                        "min_accepted_dt_days"
                    ],
                    "median_accepted_dt_days": case[
                        "median_accepted_dt_days"
                    ],
                    "max_accepted_dt_days": case[
                        "max_accepted_dt_days"
                    ],
                    "min_raw_capacity_margin_kg": case[
                        "min_raw_capacity_margin_kg"
                    ],
                    "terminal_gas_cut": case[
                        "terminal_gas_cut"
                    ],
                    "final_stored_mass_kg": case[
                        "final_stored_mass_kg"
                    ],
                    "final_cumulative_produced_mass_kg": case[
                        "final_cumulative_produced_mass_kg"
                    ],
                    "active_cell_count": case[
                        "terminal_plume"
                    ]["active_cell_count"],
                    "visible_cell_count": case[
                        "terminal_plume"
                    ]["visible_cell_count"],
                }
            )

        gate(
            "at_least_one_finite_cadence_passes",
            len(finite_eligible_passes) >= 1,
            finite_eligible_passes,
        )

        # Coarsest passing finite cadence wins.
        selected_policy = max(
            finite_eligible_passes,
            key=lambda name: float(policy_cadences[name]),
        )
        selected_max_epoch_days = float(
            policy_cadences[selected_policy]
        )

        selected_result = results[selected_policy]
        selected_terminal_state = selected_result["terminal_state"]

        selected_state_arrays = {
            k: np.asarray(v).copy()
            for k, v in selected_terminal_state.items()
        }
        selected_state_arrays[
            "R3R5_calibration_policy_name_ascii"
        ] = np.frombuffer(
            selected_policy.encode("ascii"),
            dtype=np.uint8,
        )
        selected_state_arrays[
            "R3R5_calibrated_max_flow_epoch_days"
        ] = np.asarray(
            selected_max_epoch_days,
            dtype=np.float64,
        )
        selected_state_arrays[
            "R3R5_calibration_target_day"
        ] = np.asarray(
            CALIBRATION_TARGET_DAY,
            dtype=np.float64,
        )
        selected_state_arrays[
            "R3R5_calibration_state_not_canonical_observation"
        ] = np.asarray(True, dtype=bool)

        selected_state_bytes = deterministic_npz_bytes(
            selected_state_arrays
        )
        selected_state_sha = hashlib.sha256(
            selected_state_bytes
        ).hexdigest()

        terminal_files: dict[str, bytes] = {}
        for policy_name, result in results.items():
            safe = policy_name.replace("EVENT_ONLY_BASELINE", "EVENT_ONLY")
            terminal_files[
                f"V16E41R3R5_Terminal80d_{safe}.npz"
            ] = deterministic_npz_bytes(
                {
                    "physical_time_days": np.asarray(
                        scalar(
                            result["terminal_state"][
                                "physical_time_days"
                            ]
                        ),
                        dtype=np.float64,
                    ),
                    "accepted_step_index": np.asarray(
                        int_scalar(
                            result["terminal_state"][
                                "accepted_step_index"
                            ]
                        ),
                        dtype=np.int64,
                    ),
                    "transport_saturation": result[
                        "terminal_saturation"
                    ],
                    "accepted_pressure_psi": result[
                        "terminal_pressure"
                    ],
                    "stored_co2_mass_current_kg": np.asarray(
                        result["final_stored_mass_kg"],
                        dtype=np.float64,
                    ),
                    "cumulative_produced_co2_mass_kg": np.asarray(
                        result[
                            "final_cumulative_produced_mass_kg"
                        ],
                        dtype=np.float64,
                    ),
                    "current_producer_co2_gas_cut": np.asarray(
                        result["terminal_gas_cut"],
                        dtype=np.float64,
                    ),
                }
            )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "calibration_parent": {
                "step": EXPECTED_PARENT_STEP,
                "time_days": EXPECTED_PARENT_TIME_DAYS,
                "state_sha256": EXPECTED_PARENT_STATE_SHA256,
            },
            "calibration_target_day": CALIBRATION_TARGET_DAY,
            "target_is_canonical_observation": False,
            "policy_order": POLICY_ORDER,
            "policy_max_epoch_days": policy_cadences,
            "reference_policy": REFERENCE_POLICY,
            "event_only_baseline_eligible_for_selection": False,
            "convergence_tolerances": CONVERGENCE_TOLERANCES,
            "finite_policies_passing": finite_eligible_passes,
            "selected_policy": selected_policy,
            "selected_max_flow_epoch_days": selected_max_epoch_days,
            "selected_calibration_state_sha256": selected_state_sha,
            "selected_policy_terminal_metrics": {
                "accepted_transition_count": selected_result[
                    "accepted_transition_count"
                ],
                "refresh_count_policy_runtime": selected_result[
                    "refresh_count_policy_runtime"
                ],
                "cadence_refresh_count": selected_result[
                    "cadence_refresh_count"
                ],
                "capacity_refresh_count": selected_result[
                    "capacity_refresh_count"
                ],
                "min_raw_capacity_margin_kg": selected_result[
                    "min_raw_capacity_margin_kg"
                ],
                "terminal_gas_cut": selected_result[
                    "terminal_gas_cut"
                ],
                "final_stored_mass_kg": selected_result[
                    "final_stored_mass_kg"
                ],
                "final_cumulative_produced_mass_kg": selected_result[
                    "final_cumulative_produced_mass_kg"
                ],
                "cumulative_mass_residual_kg": selected_result[
                    "cumulative_mass_residual_kg"
                ],
            },
            "selection_rule": (
                "Choose the coarsest completed finite maximum-flow-epoch "
                "policy that passes every predeclared convergence tolerance "
                "against the EIGHTH_OBSERVED_STALE_INTERVAL reference. "
                "EVENT_ONLY_BASELINE is diagnostic only."
            ),
            "production_policy_frozen": False,
            "100d_rollout_authorized": False,
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
            "reference_policy_completed": (
                REFERENCE_POLICY in results
            ),
            "finite_cadence_selected": selected_policy,
            "selected_max_flow_epoch_days": selected_max_epoch_days,
            "selected_calibration_state_sha256": selected_state_sha,
            "event_only_not_selectable": True,
            "production_policy_frozen": False,
            "canonical_100d_state_created": False,
            "next_milestone": NEXT,
        }

        files = {
            "PAD_Stream_V16E41R3R5_Summary.json": json_bytes(summary),
            "V16E41R3R5_Policy_Status.csv": csv_bytes(policy_status_rows),
            "V16E41R3R5_Cadence_Convergence_Comparison.csv": csv_bytes(
                comparison_rows
            ),
            "V16E41R3R5_All_Accepted_Transitions.csv": csv_bytes(
                all_step_rows
            ),
            "V16E41R3R5_All_Flow_Refreshes.csv": csv_bytes(
                all_refresh_rows
            ),
            "V16E41R3R5_Capacity_Trigger_Audit.csv": csv_bytes(
                all_capacity_rows
            ),
            "V16E41R3R5_Selected_Calibration_State_80d.npz":
                selected_state_bytes,
            "V16E41R3R5_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
            "V16E41R3R5_Final_Closure.json": json_bytes(closure),
            **terminal_files,
        }

        immutable_publish(out, files)

        manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E41R3R5_Artifact_Manifest.csv":
                manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {"V16E41R3R5_Artifact_Manifest.csv": csv_bytes(manifest)},
        )

        print("\n" + "=" * 160)
        print("PAD-Stream V16E-41-R3-R5: PASS")
        print("=" * 160)
        print(f"{'Status':66}: {STATUS}")
        print(
            f"{'Calibration horizon':66}: "
            f"{EXPECTED_PARENT_TIME_DAYS:.12g} -> {CALIBRATION_TARGET_DAY:.12g} d"
        )
        print(
            f"{'Reference policy':66}: {REFERENCE_POLICY}"
        )
        print(
            f"{'Finite policies passing':66}: {finite_eligible_passes}"
        )
        print(
            f"{'Selected policy':66}: {selected_policy}"
        )
        print(
            f"{'Selected max flow-epoch age':66}: "
            f"{selected_max_epoch_days:.15g} d"
        )
        print(
            f"{'Selected runtime refreshes':66}: "
            f"{selected_result['refresh_count_policy_runtime']}"
        )
        print(
            f"{'Selected capacity refreshes':66}: "
            f"{selected_result['capacity_refresh_count']}"
        )
        print(
            f"{'Selected minimum raw capacity margin':66}: "
            f"{selected_result['min_raw_capacity_margin_kg']:.12e} kg"
        )
        print(
            f"{'Selected terminal gas cut':66}: "
            f"{selected_result['terminal_gas_cut']:.12g}"
        )
        print(
            f"{'Selected calibration state SHA':66}: "
            f"{selected_state_sha}"
        )
        print(
            f"{'Production policy frozen':66}: False"
        )
        print(
            f"{'100-day rollout authorized':66}: False"
        )
        print(f"{'Next':66}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E41R3R5_Blocked_Cadence_Calibration.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E41R3R5_Blocked_Cadence_Calibration_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)
        print("\n" + "=" * 160)
        print("PAD-Stream V16E-41-R3-R5: BLOCKED")
        print("=" * 160)
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
