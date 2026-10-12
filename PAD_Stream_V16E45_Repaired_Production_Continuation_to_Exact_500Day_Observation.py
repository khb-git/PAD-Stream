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


MILESTONE = "V16E-45"
STATUS = "REPAIRED_PRODUCTION_EXACT_500D_OBSERVATION_VALIDATED"
NEXT = "V16E-46 - Repaired Production Continuation to Exact 750-Day Observation"

TARGET_DAY = 500.0
NEXT_OBSERVATION_DAY = 750.0
MAX_FLOW_EPOCH_DAYS = 4.9417335239115445
PRODUCTION_POLICY = "HALF_OBSERVED_STALE_INTERVAL"

EXPECTED_GRID = (15, 50, 50)
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0

EXPECTED_PARENT_STEP = 10400
EXPECTED_PARENT_TIME_DAYS = 365.0
EXPECTED_PARENT_STATE_SHA256 = (
    "782d852947c29bedb3fa913428779ad14f5f719a861401c6e4fe15fc8944f869"
)

E44R1_RUNNER = (
    "PAD_Stream_V16E44R1_Predecessor_Binding_Repair_and_"
    "Exact_365Day_Observation.py"
)
E44R1_GIT_BLOB = "44db79e0553e7a2853e54f057d66874595d51716"
R3R5_RUNNER = (
    "PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_"
    "Runtime_Refresh_Policy_Calibration.py"
)
R3R5_GIT_BLOB = "15aae3224ba4337cad72f9b4aa9166d602791349"
R3R4R1_RUNNER = (
    "PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
)
R3R4R1_GIT_BLOB = "5f8433437ce111533338ceada922f51abb2edefe"
R2_REPAIR_RUNNER = (
    "PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_"
    "Timestep_Repair.py"
)
R2_REPAIR_GIT_BLOB = "f6961c48dc47c5fb55f2af658ef4ce429eb66533"

E44R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E44R1_PREDECESSOR_BINDING_REPAIR_EXACT_365D_OBSERVATION"
)
E44R1_SUMMARY = "PAD_Stream_V16E44R1_Summary.json"
E44R1_CLOSURE = "V16E44R1_Final_Closure.json"
E44R1_RESTART = (
    "V16E44R1_Authoritative_365d_PostObservation_Refreshed_Restart.npz"
)
EXPECTED_E44R1_STATUS = (
    "PREDECESSOR_BINDING_REPAIRED_EXACT_365D_OBSERVATION_VALIDATED"
)

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E45_REPAIRED_PRODUCTION_EXACT_500D_OBSERVATION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E45_BLOCKED_REPAIRED_PRODUCTION_EXACT_500D_OBSERVATION"
)

OBSERVATION_STATE_NAME = (
    "V16E45_Canonical_Exact_500d_Observation_State_PreRefresh.npz"
)
RESTART_STATE_NAME = (
    "V16E45_Authoritative_500d_PostObservation_Refreshed_Restart.npz"
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


def bool_scalar(a: Any) -> bool:
    return bool(np.asarray(a).reshape(()))


def observation_semantics(
    state: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    out = {k: np.asarray(v).copy() for k, v in state.items()}

    bt_time = scalar(out["breakthrough_time_days"])
    out["physical_time_days"] = np.asarray(TARGET_DAY, dtype=np.float64)
    out["breakthrough_reached"] = np.asarray(True, dtype=bool)
    out["time_since_breakthrough_days"] = np.asarray(
        TARGET_DAY - bt_time,
        dtype=np.float64,
    )

    for key in [
        "first_fixed_observation_checkpoint_reached",
        "second_fixed_observation_checkpoint_reached",
        "third_fixed_observation_checkpoint_reached",
        "fourth_fixed_observation_checkpoint_reached",
        "fifth_fixed_observation_checkpoint_reached",
        "sixth_fixed_observation_checkpoint_reached",
        "seventh_fixed_observation_checkpoint_reached",
    ]:
        out[key] = np.asarray(True, dtype=bool)

    out["last_fixed_observation_day"] = np.asarray(
        TARGET_DAY,
        dtype=np.float64,
    )
    out["observation_cursor_index"] = np.asarray(7, dtype=np.int64)
    out["next_fixed_observation_day"] = np.asarray(
        NEXT_OBSERVATION_DAY,
        dtype=np.float64,
    )

    out["V16E44R1_authoritative_post_observation_restart"] = np.asarray(
        False, dtype=bool
    )
    out["V16E45_rollout_active"] = np.asarray(False, dtype=bool)
    out["V16E45_canonical_500d_observation_state"] = np.asarray(
        True, dtype=bool
    )
    out["V16E45_post_observation_refresh_pending"] = np.asarray(
        True, dtype=bool
    )
    out["V16E45_authoritative_post_observation_restart"] = np.asarray(
        False, dtype=bool
    )
    out["runtime_refresh_policy_name_ascii"] = np.frombuffer(
        PRODUCTION_POLICY.encode("ascii"),
        dtype=np.uint8,
    )
    out["runtime_max_flow_epoch_days"] = np.asarray(
        MAX_FLOW_EPOCH_DAYS,
        dtype=np.float64,
    )
    return out


def self_test() -> None:
    if TARGET_DAY != 500.0:
        raise RuntimeError("target_day_identity")
    if NEXT_OBSERVATION_DAY != 750.0:
        raise RuntimeError("next_observation_identity")
    if EXPECTED_PARENT_TIME_DAYS != 365.0:
        raise RuntimeError("parent_time_identity")
    if EXPECTED_PARENT_STEP != 10400:
        raise RuntimeError("parent_step_identity")
    if abs(MAX_FLOW_EPOCH_DAYS - 4.9417335239115445) > 1.0e-15:
        raise RuntimeError("policy_epoch_identity")
    if INJECTOR_MASS_RATE_KG_DAY * TARGET_DAY != 250_000_000.0:
        raise RuntimeError("500d_injection_identity")

    expected_rel = Path(
        "provenance/hybrid_dp/"
        "V16E44R1_PREDECESSOR_BINDING_REPAIR_EXACT_365D_OBSERVATION"
    )
    if E44R1_REL != expected_rel:
        raise RuntimeError(f"E44R1_predecessor_rel_binding:{E44R1_REL}")
    if E44R1_SUMMARY != "PAD_Stream_V16E44R1_Summary.json":
        raise RuntimeError(f"E44R1_summary_binding:{E44R1_SUMMARY}")
    if E44R1_CLOSURE != "V16E44R1_Final_Closure.json":
        raise RuntimeError(f"E44R1_closure_binding:{E44R1_CLOSURE}")
    if E44R1_RESTART != (
        "V16E44R1_Authoritative_365d_PostObservation_Refreshed_Restart.npz"
    ):
        raise RuntimeError(f"E44R1_restart_binding:{E44R1_RESTART}")
    if EXPECTED_E44R1_STATUS != (
        "PREDECESSOR_BINDING_REPAIRED_EXACT_365D_OBSERVATION_VALIDATED"
    ):
        raise RuntimeError("E44R1_status_binding")
    if OUT_REL == E44R1_REL:
        raise RuntimeError("predecessor_output_path_collision")

    source_text = Path(__file__).read_text(encoding="utf-8")
    main_text = source_text.split("def main(", 1)[1]
    required_source_contracts = [
        'e44r1_closure.get("exact_365d_observation_created") is True',
        'current["V16E44R1_authoritative_post_observation_restart"]',
        '"V16E45_Canonical_Exact_500d_Observation_State_PreRefresh.npz"',
        '"V16E45_Authoritative_500d_PostObservation_Refreshed_Restart.npz"',
    ]
    for token in required_source_contracts:
        if token not in main_text:
            raise RuntimeError(f"source_contract_missing:{token}")
    forbidden_key = 'e44r1_closure.get("exact_' + '500d_observation_created") is True'
    if forbidden_key in main_text:
        raise RuntimeError("predecessor_closure_key_drift")

    print(
        "PAD-Stream V16E-45 repaired production exact-500d continuation "
        "self-test: PASS"
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
        print("\n" + "=" * 164)
        print(
            "PAD-Stream V16E-45 — Repaired Production Continuation "
            "to Exact 500-Day Observation"
        )
        print("=" * 164)
        print(
            f"PARENT     : authoritative 365d post-observation restart, "
            f"step {EXPECTED_PARENT_STEP}"
        )
        print(
            f"POLICY     : {PRODUCTION_POLICY}; "
            f"max flow-epoch age {MAX_FLOW_EPOCH_DAYS:.16g} d"
        )
        print("TARGET     : exact 500.0 d")
        print("NEXT       : 750.0 d")
        print("NEW PHYSICS: none")

        failed_stage = "E44R1_predecessor_and_source_binding"

        source_bindings = {
            "E44R1": (E44R1_RUNNER, E44R1_GIT_BLOB),
            "R3R5": (R3R5_RUNNER, R3R5_GIT_BLOB),
            "R3R4R1": (R3R4R1_RUNNER, R3R4R1_GIT_BLOB),
            "R2_REPAIR": (R2_REPAIR_RUNNER, R2_REPAIR_GIT_BLOB),
        }
        for role, (filename, expected_blob) in source_bindings.items():
            p = root / filename
            gate(f"{role}_runner_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(f"{role}_git_blob_exact", actual == expected_blob, actual)

        e44r1_summary_path = drive / E44R1_REL / E44R1_SUMMARY
        e44r1_closure_path = drive / E44R1_REL / E44R1_CLOSURE
        parent_path = drive / E44R1_REL / E44R1_RESTART

        for p in [e44r1_summary_path, e44r1_closure_path, parent_path]:
            gate(f"predecessor_exists_{p.name}", p.is_file(), p)

        e44r1_summary = load_json(e44r1_summary_path)
        e44r1_closure = load_json(e44r1_closure_path)
        gate(
            "E44R1_status_exact",
            e44r1_summary.get("status") == EXPECTED_E44R1_STATUS,
            e44r1_summary.get("status"),
        )
        gate(
            "E44R1_all_gates_passed",
            e44r1_closure.get("all_gates_passed") is True,
            e44r1_closure.get("all_gates_passed"),
        )
        gate(
            "E44R1_exact_365d_observation_created",
            e44r1_closure.get("exact_365d_observation_created") is True,
            e44r1_closure.get("exact_365d_observation_created"),
        )
        gate(
            "E44R1_restart_created",
            e44r1_closure.get("post_observation_runtime_restart_created") is True,
            e44r1_closure.get("post_observation_runtime_restart_created"),
        )

        parent_sha_before = sha256_file(parent_path)
        gate(
            "parent_restart_SHA_exact",
            parent_sha_before == EXPECTED_PARENT_STATE_SHA256,
            parent_sha_before,
        )
        gate(
            "parent_SHA_matches_E44R1_summary",
            e44r1_summary["post_observation_restart"]["state_sha256"]
            == parent_sha_before,
            e44r1_summary["post_observation_restart"]["state_sha256"],
        )

        r3r5 = load_module(
            root / R3R5_RUNNER,
            "pad_stream_v16e44r1_r3r5",
        )
        r3r4r1 = load_module(
            root / R3R4R1_RUNNER,
            "pad_stream_v16e44r1_r3r4r1",
        )
        repair = load_module(
            root / R2_REPAIR_RUNNER,
            "pad_stream_v16e44r1_r2repair",
        )

        role_modules: dict[str, Any] = {}
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
            actual = git_blob_sha(p, root)
            gate(
                f"source_blob_exact_{role}",
                actual == expected_blob,
                actual,
            )
            role_modules[role] = load_module(
                p,
                f"pad_stream_v16e44r1_{role.lower()}",
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

        current = load_npz(parent_path)
        gate(
            "parent_step_exact",
            int_scalar(current["accepted_step_index"]) == EXPECTED_PARENT_STEP,
            int_scalar(current["accepted_step_index"]),
        )
        gate(
            "parent_time_exact_365d",
            scalar(current["physical_time_days"]) == EXPECTED_PARENT_TIME_DAYS,
            scalar(current["physical_time_days"]),
        )
        gate(
            "parent_cursor_6_last365_next500",
            int_scalar(current["observation_cursor_index"]) == 6
            and scalar(current["last_fixed_observation_day"]) == 365.0
            and scalar(current["next_fixed_observation_day"]) == 500.0,
            (
                f"{int_scalar(current['observation_cursor_index'])}:"
                f"{scalar(current['last_fixed_observation_day'])}:"
                f"{scalar(current['next_fixed_observation_day'])}"
            ),
        )
        gate(
            "parent_is_authoritative_E44R1_restart",
            bool_scalar(
                current["V16E44R1_authoritative_post_observation_restart"]
            ),
        )
        gate(
            "parent_policy_epoch_exact",
            abs(
                scalar(current["runtime_max_flow_epoch_days"])
                - MAX_FLOW_EPOCH_DAYS
            ) <= 1.0e-15,
            scalar(current["runtime_max_flow_epoch_days"]),
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

        initial_injected = scalar(
            current["cumulative_injected_co2_mass_kg"]
        )
        initial_produced = scalar(
            current["cumulative_produced_co2_mass_kg"]
        )
        initial_stored = scalar(
            current["stored_co2_mass_current_kg"]
        )

        failed_stage = "frozen_policy_365_to_500d_rollout"

        refresh_rows: list[dict[str, Any]] = []
        step_rows: list[dict[str, Any]] = []
        capacity_rows: list[dict[str, Any]] = []
        controller_rows: list[dict[str, Any]] = []
        accepted_dts: list[float] = []
        capacity_margins: list[float] = []

        epoch: dict[str, Any] | None = None
        epoch_start_time: float | None = None
        refresh_count = 0
        cadence_refresh_count = 0
        capacity_refresh_count = 0
        capacity_controller_adjustments_total = 0
        capacity_limited_accepted_transitions = 0
        force_refresh_next = False

        def do_refresh(trigger: str) -> None:
            nonlocal current, epoch, epoch_start_time
            nonlocal refresh_count, cadence_refresh_count
            nonlocal capacity_refresh_count

            before_time = scalar(current["physical_time_days"])
            before_step = int_scalar(current["accepted_step_index"])
            before_inj = scalar(
                current["cumulative_injected_co2_mass_kg"]
            )
            before_prod = scalar(
                current["cumulative_produced_co2_mass_kg"]
            )
            before_stored = scalar(
                current["stored_co2_mass_current_kg"]
            )

            try:
                refreshed, new_epoch, _rows = r3r5.build_flow_epoch(
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
            except Exception as exc:
                raise GateError(
                    f"flow_refresh_failed:{trigger}:{before_step}:{repr(exc)}"
                ) from exc

            if scalar(refreshed["physical_time_days"]) != before_time:
                raise GateError("refresh_advanced_time")
            if int_scalar(refreshed["accepted_step_index"]) != before_step:
                raise GateError("refresh_advanced_step")
            if scalar(
                refreshed["cumulative_injected_co2_mass_kg"]
            ) != before_inj:
                raise GateError("refresh_changed_injection_ledger")
            if scalar(
                refreshed["cumulative_produced_co2_mass_kg"]
            ) != before_prod:
                raise GateError("refresh_changed_production_ledger")

            mass_tol = max(
                1.0e-6,
                1.0e-10 * max(abs(before_stored), 1.0),
            )
            if abs(
                scalar(refreshed["stored_co2_mass_current_kg"])
                - before_stored
            ) > mass_tol:
                raise GateError("refresh_changed_stored_mass_ledger")

            current = refreshed
            epoch = new_epoch
            epoch_start_time = before_time
            refresh_count += 1
            if trigger == "CADENCE":
                cadence_refresh_count += 1
            if trigger == "CAPACITY_PREFLIGHT_REJECTION":
                capacity_refresh_count += 1

            refresh_rows.append(
                {
                    "refresh_index": refresh_count,
                    "trigger": trigger,
                    "physical_time_days": before_time,
                    "accepted_step_index": before_step,
                    "fixed_point_iterations": new_epoch[
                        "fixed_point_iterations"
                    ],
                    "CFL_dt_days": new_epoch["cfl_dt_days"],
                    "streamline_count": new_epoch["nstream"],
                    "capture_fraction": new_epoch["capture_fraction"],
                    "flow_local_relative_residual": new_epoch[
                        "flow_local_residual"
                    ],
                    "flow_global_relative_residual": new_epoch[
                        "flow_global_residual"
                    ],
                    "pressure_rel_L2_vs_pre_refresh": new_epoch[
                        "refresh_pressure_rel_L2_vs_parent"
                    ],
                    "saturation_Linf_vs_pre_refresh": new_epoch[
                        "refresh_saturation_Linf_vs_parent"
                    ],
                    "refresh_global_mass_error_kg": new_epoch[
                        "refresh_global_mass_error_kg"
                    ],
                }
            )

        do_refresh("RESTART_OR_INITIALIZATION")

        while scalar(current["physical_time_days"]) < TARGET_DAY - 1.0e-13:
            now = scalar(current["physical_time_days"])
            if epoch is None or epoch_start_time is None:
                raise GateError("missing_active_flow_epoch")

            if force_refresh_next:
                do_refresh("POST_CAPACITY_LIMITED_ACCEPT")
                force_refresh_next = False
                now = scalar(current["physical_time_days"])

            due = epoch_start_time + MAX_FLOW_EPOCH_DAYS
            if now >= due - 1.0e-13:
                do_refresh("CADENCE")
                now = scalar(current["physical_time_days"])
                due = epoch_start_time + MAX_FLOW_EPOCH_DAYS

            intended_target = min(
                TARGET_DAY,
                due,
                now + float(epoch["cfl_dt_days"]),
            )
            base_dt = intended_target - now
            if not np.isfinite(base_dt) or base_dt <= 0.0:
                raise GateError(f"nonpositive_base_dt:{base_dt}")

            same_parent_capacity_refresh_done = False
            capacity_adjustments_step = 0
            candidate_dt = float(base_dt)

            while True:
                parent_time = scalar(current["physical_time_days"])
                parent_step = int_scalar(current["accepted_step_index"])
                parent_sat = np.asarray(
                    current["transport_saturation"],
                    dtype=np.float64,
                )
                pressure = np.asarray(
                    epoch["pressure_psi"],
                    dtype=np.float64,
                )
                p_ref = scalar(
                    current["co2_density_reference_pressure_pa"]
                )
                parent_stored = scalar(
                    current["stored_co2_mass_current_kg"]
                )

                candidate_dt = min(
                    candidate_dt,
                    float(epoch["cfl_dt_days"]),
                    intended_target - parent_time,
                    TARGET_DAY - parent_time,
                )
                if candidate_dt <= 0.0:
                    raise GateError(
                        f"nonpositive_candidate_dt:{candidate_dt}"
                    )

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
                    raise GateError(
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
                    1.0e-10
                    * max(abs(float(np.sum(old_cv_mass))), 1.0),
                )
                if abs(sample_closure) > sample_tol:
                    raise GateError(
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
                    candidate_dt,
                )

                injected_step = float(transport["injected_mass_kg"])
                produced_step = float(transport["produced_mass_kg"])
                physical_injected = (
                    INJECTOR_MASS_RATE_KG_DAY * candidate_dt
                )
                injection_tol = max(
                    1.0e-6,
                    1.0e-12 * max(abs(physical_injected), 1.0),
                )
                if abs(
                    injected_step - physical_injected
                ) > injection_tol:
                    raise GateError(
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
                    parent_stored + injected_step - produced_step
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
                capacity_margins.append(
                    float(preflight["minimum_capacity_margin_kg"])
                )

                if preflight["overcapacity_cell_count"] > 0:
                    capacity_rows.append(
                        {
                            "physical_time_days": parent_time,
                            "accepted_step_index": parent_step,
                            "trial_dt_days": candidate_dt,
                            "same_parent_refresh_done":
                                same_parent_capacity_refresh_done,
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

                    if not same_parent_capacity_refresh_done:
                        do_refresh("CAPACITY_PREFLIGHT_REJECTION")
                        same_parent_capacity_refresh_done = True
                        continue

                    controller = repair.preflight_mapback_capacity(
                        r2=physics,
                        e37a=e37a,
                        parent_grid_saturation=parent_sat,
                        old_cv_saturation=old_cv_sat,
                        new_cv_saturation=transport["new_saturation"],
                        old_cv_mass=old_cv_mass,
                        new_cv_mass=transport["new_mass"],
                        geometry=epoch["geometry"],
                        pressure_psi=pressure,
                        p_ref_gas_pa=p_ref,
                        cell_pore_volume_m3=cell_pore_volume_m3,
                        target_final_mass_kg=target_final_mass,
                        active_dt_days=candidate_dt,
                    )
                    if controller.get("native_failure_required"):
                        raise GateError(
                            "capacity_controller_native_failure_required:"
                            f"{controller.get('reason')}"
                        )
                    if not controller.get("controller_applicable"):
                        raise GateError(
                            "capacity_controller_not_applicable"
                        )

                    recommended = float(
                        controller["recommended_dt_days"]
                    )
                    if (
                        not np.isfinite(recommended)
                        or recommended <= 0.0
                        or recommended >= candidate_dt
                    ):
                        raise GateError(
                            "invalid_capacity_recommended_dt:"
                            f"{recommended}:{candidate_dt}"
                        )

                    capacity_adjustments_step += 1
                    capacity_controller_adjustments_total += 1
                    controller_rows.append(
                        {
                            "physical_time_days": parent_time,
                            "accepted_step_index": parent_step,
                            "adjustment_index_this_step":
                                capacity_adjustments_step,
                            "candidate_dt_days": candidate_dt,
                            "recommended_dt_days": recommended,
                            "raw_admissible_fraction": controller[
                                "raw_admissible_fraction"
                            ],
                            "max_capacity_excess_kg": controller[
                                "max_capacity_excess_kg"
                            ],
                            "limiting_cell_zero_based": str(
                                controller[
                                    "upper_limiting_cell_zero_based"
                                ]
                            ),
                        }
                    )
                    if (
                        capacity_adjustments_step
                        > int(repair.MAX_CAPACITY_ADJUSTMENTS)
                    ):
                        raise GateError(
                            "capacity_adjustment_budget_exhausted:"
                            f"{parent_step+1}"
                        )
                    candidate_dt = recommended
                    continue

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
                    dt_seconds=candidate_dt * DAY_TO_S,
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
                    1.0e-10 * max(abs(target_final_mass), 1.0),
                )
                if abs(
                    capillary["external_mass_change_kg"]
                ) > closure_tol:
                    raise GateError(
                        "capillary_external_mass_change:"
                        f"{capillary['external_mass_change_kg']}"
                    )
                if abs(step_residual) > closure_tol:
                    raise GateError(
                        f"step_component_mass_closure:{step_residual}"
                    )

                _prod_rows, aggregate_cut = e37a.producer_rows_from_flux(
                    epoch["labels"],
                    epoch["weights_m3_day"],
                    transport["outlet_fractional_flow"],
                    transport["face_mass_flux_kg_day"][:, -1],
                    candidate_dt,
                )
                if (
                    not np.isfinite(aggregate_cut)
                    or not 0.0 <= aggregate_cut <= 1.0
                ):
                    raise GateError(
                        f"producer_gas_cut_invalid:{aggregate_cut}"
                    )

                child = e36.make_child_state(
                    current,
                    child_sat,
                    pressure,
                    p_ref,
                    candidate_dt,
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
                child[
                    "transport_control_volume_count"
                ] = np.asarray(
                    epoch["ncv"],
                    dtype=np.int64,
                )
                child[
                    "mass_conservative_flow_refresh_active"
                ] = np.asarray(True, dtype=bool)
                child[
                    "runtime_refresh_policy_name_ascii"
                ] = np.frombuffer(
                    PRODUCTION_POLICY.encode("ascii"),
                    dtype=np.uint8,
                )
                child[
                    "runtime_max_flow_epoch_days"
                ] = np.asarray(
                    MAX_FLOW_EPOCH_DAYS,
                    dtype=np.float64,
                )
                child[
                    "V16E44R1_authoritative_post_observation_restart"
                ] = np.asarray(False, dtype=bool)
                child["V16E45_rollout_active"] = np.asarray(
                    True, dtype=bool
                )
                child[
                    "V16E45_canonical_500d_observation_state"
                ] = np.asarray(False, dtype=bool)
                child[
                    "last_grid_mapback_ledger_residual_kg"
                ] = np.asarray(
                    mapping["ledger_residual_kg"],
                    dtype=np.float64,
                )
                child[
                    "last_capillary_external_mass_change_kg"
                ] = np.asarray(
                    capillary["external_mass_change_kg"],
                    dtype=np.float64,
                )

                accepted_time = scalar(child["physical_time_days"])
                if TARGET_DAY - accepted_time <= 1.0e-13:
                    child["physical_time_days"] = np.asarray(
                        TARGET_DAY,
                        dtype=np.float64,
                    )
                    accepted_time = TARGET_DAY

                accepted_dts.append(candidate_dt)
                step_rows.append(
                    {
                        "accepted_step_index": int_scalar(
                            child["accepted_step_index"]
                        ),
                        "parent_time_days": parent_time,
                        "accepted_time_days": accepted_time,
                        "accepted_dt_days": candidate_dt,
                        "active_epoch_CFL_dt_days": epoch[
                            "cfl_dt_days"
                        ],
                        "epoch_age_before_step_days":
                            parent_time - epoch_start_time,
                        "observation_landing_step":
                            accepted_time == TARGET_DAY,
                        "capacity_same_parent_refresh_used":
                            same_parent_capacity_refresh_done,
                        "capacity_controller_adjustments":
                            capacity_adjustments_step,
                        "raw_minimum_capacity_margin_kg": preflight[
                            "minimum_capacity_margin_kg"
                        ],
                        "injected_CO2_mass_kg": injected_step,
                        "produced_CO2_mass_kg": produced_step,
                        "stored_CO2_mass_kg": final_stored,
                        "step_component_mass_residual_kg":
                            step_residual,
                        "producer_CO2_gas_cut": aggregate_cut,
                    }
                )

                current = {
                    k: np.asarray(v).copy()
                    for k, v in child.items()
                }

                if capacity_adjustments_step > 0:
                    capacity_limited_accepted_transitions += 1
                    force_refresh_next = True
                break

        failed_stage = "exact_500d_observation_checkpoint"

        gate(
            "exact_500d_landing",
            scalar(current["physical_time_days"]) == TARGET_DAY,
            scalar(current["physical_time_days"]),
        )

        observation_state = observation_semantics(current)

        final_step = int_scalar(
            observation_state["accepted_step_index"]
        )
        final_stored = scalar(
            observation_state["stored_co2_mass_current_kg"]
        )
        final_injected = scalar(
            observation_state["cumulative_injected_co2_mass_kg"]
        )
        final_produced = scalar(
            observation_state["cumulative_produced_co2_mass_kg"]
        )
        final_cut = scalar(
            observation_state["current_producer_co2_gas_cut"]
        )
        final_cumulative_residual = (
            final_stored
            - scalar(observation_state["stored_co2_mass_initial_kg"])
            - final_injected
            + final_produced
        )

        expected_injected = INJECTOR_MASS_RATE_KG_DAY * TARGET_DAY
        final_mass_tol = max(
            1.0e-6,
            1.0e-10 * max(abs(final_stored), 1.0),
        )
        injection_tol = max(
            1.0e-6,
            1.0e-12 * expected_injected,
        )

        gate(
            "500d_cumulative_injection_exact_rate",
            abs(final_injected - expected_injected) <= injection_tol,
            final_injected - expected_injected,
        )
        gate(
            "500d_component_mass_closure",
            abs(final_cumulative_residual) <= final_mass_tol,
            final_cumulative_residual,
        )
        gate(
            "500d_observation_cursor_advanced",
            int_scalar(
                observation_state["observation_cursor_index"]
            ) == 7
            and scalar(
                observation_state["last_fixed_observation_day"]
            ) == 500.0
            and scalar(
                observation_state["next_fixed_observation_day"]
            ) == 750.0,
        )
        gate(
            "breakthrough_history_preserved",
            bool_scalar(observation_state["breakthrough_reached"])
            and scalar(
                observation_state["breakthrough_time_days"]
            ) < TARGET_DAY,
            scalar(observation_state["breakthrough_time_days"]),
        )
        gate(
            "parent_restart_immutable",
            sha256_file(parent_path) == parent_sha_before,
            sha256_file(parent_path),
        )

        observation_bytes = deterministic_npz_bytes(
            observation_state
        )
        observation_sha = hashlib.sha256(
            observation_bytes
        ).hexdigest()

        failed_stage = "post_observation_500d_refresh"

        current = {
            k: np.asarray(v).copy()
            for k, v in observation_state.items()
        }
        pre_refresh_sat = np.asarray(
            current["transport_saturation"],
            dtype=np.float64,
        ).copy()
        pre_refresh_pressure = np.asarray(
            current["accepted_pressure_psi"],
            dtype=np.float64,
        ).copy()
        pre_refresh_step = int_scalar(
            current["accepted_step_index"]
        )
        pre_refresh_time = scalar(
            current["physical_time_days"]
        )
        pre_refresh_stored = scalar(
            current["stored_co2_mass_current_kg"]
        )
        pre_refresh_inj = scalar(
            current["cumulative_injected_co2_mass_kg"]
        )
        pre_refresh_prod = scalar(
            current["cumulative_produced_co2_mass_kg"]
        )

        do_refresh("POST_OBSERVATION_CHECKPOINT")

        gate(
            "post_observation_refresh_same_time",
            scalar(current["physical_time_days"])
            == pre_refresh_time
            == TARGET_DAY,
        )
        gate(
            "post_observation_refresh_same_step",
            int_scalar(current["accepted_step_index"])
            == pre_refresh_step,
        )
        gate(
            "post_observation_refresh_injection_ledger_unchanged",
            scalar(
                current["cumulative_injected_co2_mass_kg"]
            ) == pre_refresh_inj,
        )
        gate(
            "post_observation_refresh_production_ledger_unchanged",
            scalar(
                current["cumulative_produced_co2_mass_kg"]
            ) == pre_refresh_prod,
        )
        gate(
            "post_observation_refresh_stored_mass_unchanged",
            abs(
                scalar(current["stored_co2_mass_current_kg"])
                - pre_refresh_stored
            ) <= final_mass_tol,
            scalar(current["stored_co2_mass_current_kg"])
            - pre_refresh_stored,
        )

        current["V16E45_rollout_active"] = np.asarray(
            False, dtype=bool
        )
        current[
            "V16E45_canonical_500d_observation_state"
        ] = np.asarray(False, dtype=bool)
        current[
            "V16E45_post_observation_refresh_pending"
        ] = np.asarray(False, dtype=bool)
        current[
            "V16E45_authoritative_post_observation_restart"
        ] = np.asarray(True, dtype=bool)
        current[
            "V16E45_500d_observation_state_sha256_ascii"
        ] = np.frombuffer(
            observation_sha.encode("ascii"),
            dtype=np.uint8,
        )

        restart_bytes = deterministic_npz_bytes(current)
        restart_sha = hashlib.sha256(
            restart_bytes
        ).hexdigest()

        sat_refresh_linf = float(
            np.max(
                np.abs(
                    np.asarray(
                        current["transport_saturation"],
                        dtype=np.float64,
                    )
                    - pre_refresh_sat
                )
            )
        )
        pressure_refresh_rel_l2 = float(
            np.linalg.norm(
                (
                    np.asarray(
                        current["accepted_pressure_psi"],
                        dtype=np.float64,
                    )
                    - pre_refresh_pressure
                ).ravel()
            )
            / max(
                float(
                    np.linalg.norm(
                        pre_refresh_pressure.ravel()
                    )
                ),
                1.0e-30,
            )
        )

        interval_injected = final_injected - initial_injected
        interval_produced = final_produced - initial_produced
        interval_stored_change = final_stored - initial_stored
        interval_residual = (
            interval_stored_change
            - interval_injected
            + interval_produced
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "production_policy": PRODUCTION_POLICY,
            "maximum_flow_epoch_age_days": MAX_FLOW_EPOCH_DAYS,
            "parent_365d_restart": {
                "step": EXPECTED_PARENT_STEP,
                "time_days": EXPECTED_PARENT_TIME_DAYS,
                "state_sha256": EXPECTED_PARENT_STATE_SHA256,
            },
            "exact_500d_observation": {
                "step": final_step,
                "time_days": TARGET_DAY,
                "state_filename": OBSERVATION_STATE_NAME,
                "state_sha256": observation_sha,
                "stored_co2_mass_kg": final_stored,
                "cumulative_injected_co2_mass_kg": final_injected,
                "cumulative_produced_co2_mass_kg": final_produced,
                "cumulative_mass_residual_kg":
                    final_cumulative_residual,
                "producer_co2_gas_cut": final_cut,
                "observation_cursor_index": 7,
                "last_fixed_observation_day": 500.0,
                "next_fixed_observation_day": 750.0,
            },
            "rollout_365_to_500d": {
                "accepted_transition_count": len(step_rows),
                "refresh_count_before_post_observation":
                    refresh_count - 1,
                "cadence_refresh_count": cadence_refresh_count,
                "capacity_refresh_count": capacity_refresh_count,
                "capacity_controller_adjustments_total":
                    capacity_controller_adjustments_total,
                "capacity_limited_accepted_transitions":
                    capacity_limited_accepted_transitions,
                "min_accepted_dt_days": float(
                    np.min(accepted_dts)
                ),
                "median_accepted_dt_days": float(
                    np.median(accepted_dts)
                ),
                "max_accepted_dt_days": float(
                    np.max(accepted_dts)
                ),
                "minimum_raw_capacity_margin_kg": float(
                    np.min(capacity_margins)
                ),
                "interval_injected_co2_mass_kg":
                    interval_injected,
                "interval_produced_co2_mass_kg":
                    interval_produced,
                "interval_stored_change_kg":
                    interval_stored_change,
                "interval_mass_residual_kg":
                    interval_residual,
            },
            "post_observation_restart": {
                "state_filename": RESTART_STATE_NAME,
                "state_sha256": restart_sha,
                "step": int_scalar(
                    current["accepted_step_index"]
                ),
                "time_days": scalar(
                    current["physical_time_days"]
                ),
                "stored_mass_kg": scalar(
                    current["stored_co2_mass_current_kg"]
                ),
                "same_time_saturation_Linf_change":
                    sat_refresh_linf,
                "same_time_pressure_relative_L2_change":
                    pressure_refresh_rel_l2,
            },
            "next_milestone": NEXT,
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(
                v["passed"] for v in gates.values()
            ),
            "gate_count": len(gates),
            "exact_500d_observation_created": True,
            "canonical_500d_observation_state_sha256":
                observation_sha,
            "post_observation_runtime_restart_created": True,
            "post_observation_runtime_restart_sha256":
                restart_sha,
            "production_policy": PRODUCTION_POLICY,
            "maximum_flow_epoch_age_days":
                MAX_FLOW_EPOCH_DAYS,
            "capacity_controller_fallback_adjustments":
                capacity_controller_adjustments_total,
            "next_milestone": NEXT,
        }

        files = {
            OBSERVATION_STATE_NAME: observation_bytes,
            RESTART_STATE_NAME: restart_bytes,
            "PAD_Stream_V16E45_Summary.json":
                json_bytes(summary),
            "V16E45_Accepted_Transitions.csv":
                csv_bytes(step_rows),
            "V16E45_Flow_Refreshes.csv":
                csv_bytes(refresh_rows),
            "V16E45_Capacity_Preflight_Events.csv":
                csv_bytes(capacity_rows),
            "V16E45_Capacity_Controller_Adjustments.csv":
                csv_bytes(controller_rows),
            "V16E45_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            "V16E45_Final_Closure.json":
                json_bytes(closure),
        }
        immutable_publish(out, files)

        manifest = []
        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name != "V16E45_Artifact_Manifest.csv"
            ):
                manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "V16E45_Artifact_Manifest.csv":
                    csv_bytes(manifest)
            },
        )

        print("\n" + "=" * 164)
        print("PAD-Stream V16E-45: PASS")
        print("=" * 164)
        print(f"{'Status':70}: {STATUS}")
        print(
            f"{'Exact observation step / time':70}: "
            f"{final_step} / {TARGET_DAY:.1f} d"
        )
        print(
            f"{'Accepted transitions 365->500d':70}: "
            f"{len(step_rows)}"
        )
        print(
            f"{'Cadence refreshes':70}: "
            f"{cadence_refresh_count}"
        )
        print(
            f"{'Capacity-triggered refreshes':70}: "
            f"{capacity_refresh_count}"
        )
        print(
            f"{'Capacity-controller adjustments':70}: "
            f"{capacity_controller_adjustments_total}"
        )
        print(
            f"{'Minimum raw capacity margin':70}: "
            f"{float(np.min(capacity_margins)):.12e} kg"
        )
        print(
            f"{'Cumulative injected CO2':70}: "
            f"{final_injected:.12f} kg"
        )
        print(
            f"{'Cumulative produced CO2':70}: "
            f"{final_produced:.12f} kg"
        )
        print(
            f"{'Stored CO2':70}: "
            f"{final_stored:.12f} kg"
        )
        print(
            f"{'Cumulative mass residual':70}: "
            f"{final_cumulative_residual:.12e} kg"
        )
        print(
            f"{'Producer CO2 gas cut':70}: "
            f"{final_cut:.12g}"
        )
        print(
            f"{'500d observation state SHA':70}: "
            f"{observation_sha}"
        )
        print(
            f"{'500d post-observation restart SHA':70}: "
            f"{restart_sha}"
        )
        print(
            f"{'Post-refresh saturation Linf change':70}: "
            f"{sat_refresh_linf:.12e}"
        )
        print(
            f"{'Post-refresh pressure relative L2 change':70}: "
            f"{pressure_refresh_rel_l2:.12e}"
        )
        print(f"{'Next':70}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": (
                "REPAIRED_PRODUCTION_EXACT_500D_OBSERVATION_BLOCKED"
            ),
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E45_Blocked_500d_Rollout.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E45_Blocked_500d_Rollout_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)

        print("\n" + "=" * 164)
        print("PAD-Stream V16E-45: BLOCKED")
        print("=" * 164)
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
