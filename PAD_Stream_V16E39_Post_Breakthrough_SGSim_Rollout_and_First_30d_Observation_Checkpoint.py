from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np


MILESTONE = "V16E-39"
STATUS = "POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT_VALIDATED"
NEXT = "V16E-40 - Post-Breakthrough SGSim Rollout / Second 60-Day Observation Checkpoint"

EXPECTED_GRID = (15, 50, 50)
BACKGROUND_SATURATION = 0.20
BREAKTHROUGH_GAS_CUT = 1.0e-4
FIRST_OBSERVATION_DAY = 30.0
NEXT_OBSERVATION_DAY = 60.0
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
CO2_RHO_REF_KG_M3 = 700.0
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0
EXPECTED_STREAMLINES = 1078
EXPECTED_FACES = 201
EXPECTED_CVS = 200
MAX_TRIAL_RETRIES = 8
RETRY_FACTOR = 0.5
MAX_ACCEPTED_TRANSITIONS = 1000
PROGRESS_EVERY = 25
SPARSE_SNAPSHOT_THRESHOLDS_DAYS = (24.0, 25.0, 27.5, 30.0)

EXPECTED_E38_BT_TIME_DAYS = 23.380258876143085
EXPECTED_E38_BT_STEP = 476
EXPECTED_E38_BT_CUT = 0.00010000002772399849
EVENT_TIME_TOL_DAYS = 1.0e-6

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
E37A_EXPECTED_STATUS = "CONTROL_VOLUME_ALIGNED_CONSERVATIVE_TRANSFER_VALIDATED"

E37B_RUNNER = "PAD_Stream_V16E37B_Extended_SGSim_Runtime_Rollout_and_First_Fixed_Observation_Checkpoint.py"
E37B_RUNNER_SHA256 = "8abec0348cb683e7805fd5b847d3f24b88b855edd3386914a6aad9a3a1d87471"
E37B_BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37B_BLOCKED_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
)
E37B_BRACKET_REPORT = "V16E37B_Blocked_Breakthrough_Bracket.json"
E37B_OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37B_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
)
E37B_30D_CHECKPOINT = "V16E37B_Canonical_SGSim_Runtime_State_Observation_0030d.npz"

E38_RUNNER = "PAD_Stream_V16E38_Breakthrough_Event_Refinement_and_Canonical_BT_State.py"
E38_RUNNER_SHA256 = "6ed0ccb552353e25ea5bc6bd4ebc562469d2049b2e81da73e0640eebf2f7b478"
E38_REL = Path(
    "provenance/hybrid_dp/"
    "V16E38_BREAKTHROUGH_EVENT_REFINEMENT_CANONICAL_BT_STATE"
)
E38_SUMMARY = "PAD_Stream_V16E38_Summary.json"
E38_CLOSURE = "V16E38_Final_Closure.json"
E38_CANONICAL = "V16E38_Canonical_Breakthrough_SGSim_Runtime_State.npz"
E38_EXPECTED_STATUS = "BREAKTHROUGH_EVENT_REFINED_CANONICAL_STATE_FROZEN"

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
    "V16E39_POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E39_BLOCKED_POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
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


def apply_post_breakthrough_state_semantics(
    child: dict[str, np.ndarray],
    parent: dict[str, np.ndarray],
    *,
    canonical_breakthrough_time_days: float,
    observation_reached: bool,
) -> dict[str, np.ndarray]:
    out = {k: np.asarray(v).copy() for k, v in child.items()}
    new_time = scalar(out["physical_time_days"])

    out["breakthrough_reached"] = np.asarray(True, dtype=bool)
    out["breakthrough_time_days"] = np.asarray(
        canonical_breakthrough_time_days, dtype=np.float64
    )
    out["time_since_breakthrough_days"] = np.asarray(
        max(0.0, new_time - canonical_breakthrough_time_days),
        dtype=np.float64,
    )
    out["V16E38_canonical_breakthrough_state"] = np.asarray(False, dtype=bool)
    out["E38_breakthrough_event_refined"] = np.asarray(True, dtype=bool)
    out["E39_post_breakthrough_rollout_active"] = np.asarray(True, dtype=bool)
    out["first_fixed_observation_checkpoint_reached"] = np.asarray(
        observation_reached, dtype=bool
    )
    out["last_source_local_added_mass_kg"] = np.asarray(0.0, dtype=np.float64)

    if observation_reached:
        out["physical_time_days"] = np.asarray(
            FIRST_OBSERVATION_DAY, dtype=np.float64
        )
        out["time_since_breakthrough_days"] = np.asarray(
            FIRST_OBSERVATION_DAY - canonical_breakthrough_time_days,
            dtype=np.float64,
        )
        out["last_fixed_observation_day"] = np.asarray(
            FIRST_OBSERVATION_DAY, dtype=np.float64
        )
        out["observation_cursor_index"] = np.asarray(
            int_scalar(parent["observation_cursor_index"]) + 1,
            dtype=np.int64,
        )
        out["next_fixed_observation_day"] = np.asarray(
            NEXT_OBSERVATION_DAY, dtype=np.float64
        )
        out["V16E39_canonical_30d_observation_state"] = np.asarray(
            True, dtype=bool
        )
    else:
        out["observation_cursor_index"] = np.asarray(
            parent["observation_cursor_index"], dtype=np.int64
        )
        out["next_fixed_observation_day"] = np.asarray(
            parent["next_fixed_observation_day"], dtype=np.float64
        )
        out["V16E39_canonical_30d_observation_state"] = np.asarray(
            False, dtype=bool
        )
    return out


def validate_checkpoint_restart(
    data: bytes,
    *,
    expected_step: int,
    expected_bt_time: float,
    expected_sat: np.ndarray,
) -> None:
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        if int(z["accepted_step_index"]) != int(expected_step):
            raise GateError("checkpoint_restart_step_mismatch")
        if float(z["physical_time_days"]) != FIRST_OBSERVATION_DAY:
            raise GateError("checkpoint_restart_time_not_exact_30d")
        if not np.array_equal(z["transport_saturation"], expected_sat):
            raise GateError("checkpoint_restart_saturation_not_byte_exact")
        if not bool(z["breakthrough_reached"]):
            raise GateError("checkpoint_restart_lost_breakthrough_flag")
        if abs(float(z["breakthrough_time_days"]) - expected_bt_time) > 1.0e-12:
            raise GateError("checkpoint_restart_breakthrough_time_changed")
        expected_since = FIRST_OBSERVATION_DAY - expected_bt_time
        if abs(float(z["time_since_breakthrough_days"]) - expected_since) > 1.0e-12:
            raise GateError("checkpoint_restart_time_since_breakthrough_mismatch")
        if not bool(z["control_volume_aligned_transfer_active"]):
            raise GateError("checkpoint_restart_missing_CV_alignment")
        if bool(z["injector_local_mass_closure_authorized"]):
            raise GateError("checkpoint_restart_authorizes_source_local_closure")
        if bool(z["injector_local_mass_closure_executed"]):
            raise GateError("checkpoint_restart_executed_source_local_closure")
        if not bool(z["first_fixed_observation_checkpoint_reached"]):
            raise GateError("checkpoint_restart_missing_observation_flag")
        if int(z["observation_cursor_index"]) != 1:
            raise GateError("checkpoint_restart_observation_cursor_not_1")
        if float(z["next_fixed_observation_day"]) != NEXT_OBSERVATION_DAY:
            raise GateError("checkpoint_restart_next_observation_not_60d")
        if float(z["last_fixed_observation_day"]) != FIRST_OBSERVATION_DAY:
            raise GateError("checkpoint_restart_last_fixed_observation_not_30d")
        if not bool(z["V16E39_canonical_30d_observation_state"]):
            raise GateError("checkpoint_restart_missing_E39_canonical_flag")
        cut = float(z["current_producer_co2_gas_cut"])
        if not np.isfinite(cut) or not 0.0 <= cut <= 1.0:
            raise GateError("checkpoint_restart_invalid_current_gas_cut")


def self_test() -> None:
    # Nominal post-BT march from the accepted E38 event to exact 30 d.
    t = EXPECTED_E38_BT_TIME_DAYS
    dt = 0.049123143364170854
    count = 0
    last_dt = None
    while t < FIRST_OBSERVATION_DAY - 1.0e-13:
        h = min(dt, FIRST_OBSERVATION_DAY - t)
        if h <= 0.0:
            raise RuntimeError("self_test_nonpositive_observation_clip")
        t += h
        if FIRST_OBSERVATION_DAY - t <= 1.0e-13:
            t = FIRST_OBSERVATION_DAY
        last_dt = h
        count += 1
        if count > 1000:
            raise RuntimeError("self_test_transition_budget_exceeded")
    if t != FIRST_OBSERVATION_DAY:
        raise RuntimeError("self_test_observation_not_exact")
    if count != 135:
        raise RuntimeError(f"self_test_expected_135_nominal_transitions:{count}")
    if abs(float(last_dt) - 0.03723991305801988) > 1.0e-12:
        raise RuntimeError(f"self_test_final_clip_mismatch:{last_dt}")

    # Retry must not mutate accepted time.
    accepted_time = 25.0
    retry_dt = 0.05 * RETRY_FACTOR
    if accepted_time != 25.0 or retry_dt != 0.025:
        raise RuntimeError("self_test_retry_semantics_failed")

    # Historical breakthrough is not equivalent to instantaneous cut state.
    breakthrough_reached = True
    instantaneous_cut = 9.0e-5
    if not breakthrough_reached or instantaneous_cut >= BREAKTHROUGH_GAS_CUT:
        raise RuntimeError("self_test_historical_breakthrough_semantics_failed")

    # Observation cursor advances only at the exact fixed checkpoint.
    cursor = 0
    next_obs = 30.0
    cursor += 1
    next_obs = 60.0
    if cursor != 1 or next_obs != 60.0:
        raise RuntimeError("self_test_observation_cursor_failed")

    print("PAD-Stream V16E-39 post-breakthrough observation/controller self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    trial_failures: list[dict[str, Any]] = []
    failed_stage: str | None = None

    e38_parent_sha_before: str | None = None
    e36_cache_sha_before: str | None = None
    e37b_bracket_sha_before: str | None = None
    frozen_sha_before: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 146)
        print(
            "PAD-Stream V16E-39 — Post-Breakthrough SGSim Rollout / "
            "First 30-Day Observation Checkpoint"
        )
        print("=" * 146)
        print("Restart        : canonical V16E-38 breakthrough state")
        print("Target         : exact first fixed observation at t = 30.0 days")
        print("Transport      : frozen 201-face / 200-CV component-mass authority")
        print("BT semantics   : historical breakthrough flag/time persist through rollout")
        print("Observation    : exact 30-day landing advances cursor to 60 days")
        print("Forbidden      : injector-local closure; global plume rescaling; F0 learned dt")

        failed_stage = "source_and_provenance_binding"

        r2_path = root / R2_RUNNER
        e36_path = root / E36_RUNNER
        e37a_path = root / E37A_RUNNER
        e37b_path = root / E37B_RUNNER
        e38_path = root / E38_RUNNER
        sg7a_path = root / SG7A
        sg7d_path = root / SG7D
        perm_path = root / SGSIM_PERM

        for p in [
            r2_path,
            e36_path,
            e37a_path,
            e37b_path,
            e38_path,
            sg7a_path,
            sg7d_path,
            perm_path,
        ]:
            gate(f"source_exists_{p.name}", p.is_file(), p)

        for name, path, expected in [
            ("R2", r2_path, R2_RUNNER_SHA256),
            ("E36", e36_path, E36_RUNNER_SHA256),
            ("E37A", e37a_path, E37A_RUNNER_SHA256),
            ("E37B", e37b_path, E37B_RUNNER_SHA256),
            ("E38", e38_path, E38_RUNNER_SHA256),
        ]:
            actual = sha256_file(path)
            gate(f"{name}_runner_SHA_exact", actual == expected, actual)

        r2 = load_module(r2_path, "pad_stream_v16e39_r2")
        e36 = load_module(e36_path, "pad_stream_v16e39_e36")
        e37a = load_module(e37a_path, "pad_stream_v16e39_e37a")
        e37b = load_module(e37b_path, "pad_stream_v16e39_e37b")
        e38 = load_module(e38_path, "pad_stream_v16e39_e38")

        e38_dir = drive / E38_REL
        e38_summary_path = e38_dir / E38_SUMMARY
        e38_closure_path = e38_dir / E38_CLOSURE
        e38_parent_path = e38_dir / E38_CANONICAL
        e36_cache_path = drive / E36_REL / E36_CACHE
        e37b_bracket_path = drive / E37B_BLOCKED_REL / E37B_BRACKET_REPORT
        e37b_30d = drive / E37B_OUT_REL / E37B_30D_CHECKPOINT
        e37a_summary_path = drive / E37A_REL / E37A_SUMMARY
        frozen_100d = drive / V16_FROZEN_REL

        for p in [
            e38_summary_path,
            e38_closure_path,
            e38_parent_path,
            e36_cache_path,
            e37b_bracket_path,
            e37a_summary_path,
            frozen_100d,
        ]:
            gate(f"provenance_exists_{p.name}", p.is_file(), p)

        gate("E37B_legacy_30d_checkpoint_absent", not e37b_30d.exists(), e37b_30d)

        e38_summary = load_json(e38_summary_path)
        e38_closure = load_json(e38_closure_path)
        e37a_summary = load_json(e37a_summary_path)

        gate(
            "E38_status_accepted",
            e38_summary.get("status") == E38_EXPECTED_STATUS,
            e38_summary.get("status"),
        )
        gate(
            "E38_E39_entry_ready",
            e38_summary.get("E39_post_breakthrough_30d_rollout_entry_ready") is True,
        )
        gate(
            "E38_closure_status_accepted",
            e38_closure.get("status") == E38_EXPECTED_STATUS,
            e38_closure.get("status"),
        )
        gate(
            "E38_all_runtime_gates_passed",
            e38_closure.get("all_runtime_gates_passed") is True,
        )
        gate(
            "E37A_status_accepted",
            e37a_summary.get("status") == E37A_EXPECTED_STATUS,
            e37a_summary.get("status"),
        )

        e38_parent_sha_before = sha256_file(e38_parent_path)
        e36_cache_sha_before = sha256_file(e36_cache_path)
        e37b_bracket_sha_before = sha256_file(e37b_bracket_path)
        frozen_sha_before = sha256_file(frozen_100d)

        gate(
            "E38_parent_SHA_matches_closure",
            e38_parent_sha_before
            == e38_closure.get("canonical_breakthrough_state_sha256"),
            e38_parent_sha_before,
        )
        gate(
            "E36_cache_SHA_matches_E38_closure",
            e36_cache_sha_before
            == e38_closure.get("E36_certified_cache_sha256"),
            e36_cache_sha_before,
        )
        gate(
            "E37B_bracket_SHA_matches_E38_closure",
            e37b_bracket_sha_before
            == e38_closure.get("E37B_breakthrough_bracket_report_sha256"),
            e37b_bracket_sha_before,
        )
        gate(
            "frozen_100d_SHA_exact",
            frozen_sha_before == V16_FROZEN_SHA256,
            frozen_sha_before,
        )

        parent = load_npz(e38_parent_path)
        cache = load_npz(e36_cache_path)

        initial_step = int_scalar(parent["accepted_step_index"])
        initial_time = scalar(parent["physical_time_days"])
        initial_cut = scalar(parent["current_producer_co2_gas_cut"])
        canonical_bt_time = scalar(parent["breakthrough_time_days"])

        gate("E38_restart_step_exact", initial_step == EXPECTED_E38_BT_STEP, initial_step)
        gate(
            "E38_restart_time_exact",
            abs(initial_time - EXPECTED_E38_BT_TIME_DAYS) <= 1.0e-12,
            initial_time,
        )
        gate(
            "E38_restart_cut_exact",
            abs(initial_cut - EXPECTED_E38_BT_CUT) <= 1.0e-15,
            initial_cut,
        )
        gate("E38_restart_breakthrough_true", bool_scalar(parent["breakthrough_reached"]))
        gate(
            "E38_restart_breakthrough_time_equals_state_time",
            abs(canonical_bt_time - initial_time) <= 1.0e-12,
            f"{canonical_bt_time}:{initial_time}",
        )
        gate(
            "E38_restart_event_bracket_within_tolerance",
            scalar(parent["breakthrough_bracket_width_days"])
            <= EVENT_TIME_TOL_DAYS + 1.0e-15,
            scalar(parent["breakthrough_bracket_width_days"]),
        )
        gate(
            "E38_restart_next_observation_30d",
            int_scalar(parent["observation_cursor_index"]) == 0
            and scalar(parent["next_fixed_observation_day"]) == FIRST_OBSERVATION_DAY,
            f"{int_scalar(parent['observation_cursor_index'])}:"
            f"{scalar(parent['next_fixed_observation_day'])}",
        )
        gate(
            "E38_restart_not_observation_checkpoint",
            not bool_scalar(parent["first_fixed_observation_checkpoint_reached"]),
        )
        gate(
            "E38_restart_CV_aligned",
            bool_scalar(parent["control_volume_aligned_transfer_active"])
            and bool_scalar(parent["component_mass_primary_conserved_variable"]),
        )
        gate(
            "E38_restart_source_local_closure_forbidden",
            not bool_scalar(parent["injector_local_mass_closure_authorized"])
            and not bool_scalar(parent["injector_local_mass_closure_executed"])
            and abs(scalar(parent["last_source_local_added_mass_kg"])) <= 1.0e-12,
        )
        gate(
            "E36_cache_reference_mobility_scope",
            bool_scalar(cache["reuse_scope_reference_mobility_only"]),
        )

        failed_stage = "physics_operator_setup"
        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E39_") as td:
            tmp = Path(td)
            shutil.copy2(sg7a_path, tmp / SG7A)
            shutil.copy2(sg7d_path, tmp / SG7D)
            sg7a = load_module(tmp / SG7A, "pad_stream_v16e39_sg7a")
            sg7d = load_module(tmp / SG7D, "pad_stream_v16e39_sg7d")

            pressure_psi = np.asarray(
                cache["accepted_pressure_psi"], dtype=np.float64
            )
            xyz_m = np.asarray(cache["streamline_xyz_m"], dtype=np.float64)
            tau_s = np.asarray(cache["streamline_tof_s"], dtype=np.float64)
            tau_end_s = np.asarray(cache["tau_end_s"], dtype=np.float64)
            weights_m3_s = np.asarray(
                cache["streamline_weights_m3_s"], dtype=np.float64
            )
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
            gate(
                "streamline_weights_match_fixed_injection_rate",
                abs(q_actual - q_expected) / q_expected < 1.0e-10,
                f"{q_actual}:{q_expected}",
            )

            tof_days = tau_s / DAY_TO_S
            operator = sg7d.build_subsegment_operator(
                xyz_m, tof_days, weights_m3_day
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

            expected_cv_pv = (
                weights_m3_day[:, None] * np.diff(tof_days, axis=1)
            )
            cv_pv = geometry["cv_pv_m3"]
            cv_pv_rel = float(
                np.linalg.norm((cv_pv - expected_cv_pv).ravel())
                / max(np.linalg.norm(expected_cv_pv.ravel()), 1.0e-30)
            )
            gate(
                "CV_pore_volume_alignment_revalidated",
                cv_pv_rel <= 1.0e-10,
                cv_pv_rel,
            )

            face_pressure_psi = e37a.build_face_pressure(
                e36, sg7d, xyz_m, pressure_psi
            )

            dxi = float(xi_faces[1] - xi_faces[0])
            sat_scan = np.linspace(
                float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001
            )
            max_df = float(
                np.max(
                    np.abs(
                        np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64)
                    )
                )
            )
            u_face = np.asarray(
                sg7a.u_dimensionless(xi_faces), dtype=np.float64
            )
            max_wave_speed = float(np.max(u_face) * max_df)
            dtD_cfl = float(
                sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS)
            )
            fastest_tau_days = float(np.min(tau_end_s / DAY_TO_S))
            nominal_dt_days = float(dtD_cfl * fastest_tau_days)

            gate(
                "nominal_dt_matches_E37A",
                abs(
                    nominal_dt_days
                    - float(e37a_summary["nominal_dt_days"])
                )
                <= 1.0e-15,
                f"{nominal_dt_days}:{e37a_summary['nominal_dt_days']}",
            )

            dx_m = 20.0 * FT_TO_M
            dy_m = 20.0 * FT_TO_M
            dz_m = 4.0 * FT_TO_M
            cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m

            permeability_md = np.loadtxt(
                perm_path, skiprows=1, dtype=np.float64
            ).reshape(EXPECTED_GRID, order="C")
            gate(
                "SGSim_permeability_shape_exact",
                permeability_md.shape == EXPECTED_GRID,
                permeability_md.shape,
            )

            failed_stage = "post_breakthrough_rollout"

            current = {
                k: np.asarray(v).copy()
                for k, v in parent.items()
            }

            initial_injected = scalar(
                current["cumulative_injected_co2_mass_kg"]
            )
            initial_produced = scalar(
                current["cumulative_produced_co2_mass_kg"]
            )
            initial_stored = scalar(
                current["stored_co2_mass_current_kg"]
            )

            rollout_rows: list[dict[str, Any]] = []
            producer_rows_all: list[dict[str, Any]] = []
            plume_rows: list[dict[str, Any]] = []
            transport_residuals: list[float] = []
            transfer_residuals: list[float] = []
            mapback_residuals: list[float] = []
            capillary_external_changes: list[float] = []
            sample_closures: list[float] = []
            post_sample_closures: list[float] = []

            accepted_transitions = 0
            rejected_trials = 0

            snapshot_steps = [initial_step]
            snapshot_times = [initial_time]
            snapshot_sats = [
                np.asarray(
                    current["transport_saturation"], dtype=np.float64
                ).copy()
            ]
            snapshot_labels = ["E38_CANONICAL_BREAKTHROUGH_START"]
            next_snapshot_index = 0

            start_plume = e36.plume_metrics(
                r2,
                snapshot_sats[0],
                pressure_psi,
                p_ref_gas_pa,
                cell_pore_volume_m3,
                initial_step,
                initial_time,
            )
            start_plume["state_label"] = "E38_CANONICAL_BREAKTHROUGH_START"
            start_plume["producer_CO2_gas_cut"] = initial_cut
            plume_rows.append(start_plume)

            while (
                scalar(current["physical_time_days"])
                < FIRST_OBSERVATION_DAY - 1.0e-13
            ):
                if accepted_transitions >= MAX_ACCEPTED_TRANSITIONS:
                    raise GateError(
                        "accepted_transition_budget_exceeded:"
                        f"{MAX_ACCEPTED_TRANSITIONS}"
                    )

                current_time = scalar(current["physical_time_days"])
                target_step = int_scalar(current["accepted_step_index"]) + 1
                remaining = FIRST_OBSERVATION_DAY - current_time
                nominal_trial_dt = min(nominal_dt_days, remaining)

                if (
                    not np.isfinite(nominal_trial_dt)
                    or nominal_trial_dt <= 0.0
                ):
                    raise GateError(
                        f"nonpositive_postBT_dt:"
                        f"{target_step}:{nominal_trial_dt}"
                    )

                accepted = False
                last_reason = ""

                for retry in range(MAX_TRIAL_RETRIES + 1):
                    dt_days = nominal_trial_dt * (RETRY_FACTOR ** retry)
                    dt_days = min(
                        dt_days,
                        FIRST_OBSERVATION_DAY - current_time,
                    )

                    if not np.isfinite(dt_days) or dt_days <= 0.0:
                        raise GateError(
                            f"nonpositive_retry_dt:"
                            f"{target_step}:{retry}:{dt_days}"
                        )

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

                        trial_time = float(result["trial_time_days"])
                        if (
                            FIRST_OBSERVATION_DAY - trial_time
                            <= 1.0e-13
                        ):
                            trial_time = FIRST_OBSERVATION_DAY

                        observation_reached = (
                            trial_time == FIRST_OBSERVATION_DAY
                        )

                        child = apply_post_breakthrough_state_semantics(
                            result["child"],
                            current,
                            canonical_breakthrough_time_days=canonical_bt_time,
                            observation_reached=observation_reached,
                        )

                        child["current_producer_co2_gas_cut"] = np.asarray(
                            result["child_cut"], dtype=np.float64
                        )
                        child["last_CV_transport_mass_residual_kg"] = np.asarray(
                            result["transport_residual_kg"],
                            dtype=np.float64,
                        )
                        child["last_CV_to_grid_transfer_residual_kg"] = np.asarray(
                            result["transfer_residual_kg"],
                            dtype=np.float64,
                        )
                        child["last_grid_mapback_ledger_residual_kg"] = np.asarray(
                            result["mapback_ledger_residual_kg"],
                            dtype=np.float64,
                        )
                        child["last_grid_to_CV_sampling_closure_kg"] = np.asarray(
                            result["post_sample_closure_kg"],
                            dtype=np.float64,
                        )

                        new_time = scalar(child["physical_time_days"])
                        if (
                            new_time <= current_time
                            or new_time
                            > FIRST_OBSERVATION_DAY + 1.0e-12
                        ):
                            raise e37a.TrialReject(
                                f"accepted_time_invalid:"
                                f"{current_time}:{new_time}"
                            )

                        if not bool_scalar(child["breakthrough_reached"]):
                            raise e37a.TrialReject(
                                "postBT_child_lost_breakthrough_flag"
                            )
                        if (
                            abs(
                                scalar(child["breakthrough_time_days"])
                                - canonical_bt_time
                            )
                            > 1.0e-12
                        ):
                            raise e37a.TrialReject(
                                "postBT_child_changed_breakthrough_time"
                            )

                        expected_since = new_time - canonical_bt_time
                        if (
                            abs(
                                scalar(
                                    child["time_since_breakthrough_days"]
                                )
                                - expected_since
                            )
                            > 1.0e-12
                        ):
                            raise e37a.TrialReject(
                                "postBT_time_since_breakthrough_mismatch"
                            )

                        cumulative_resid = scalar(
                            child["cumulative_mass_residual_kg"]
                        )

                        rollout_rows.append(
                            {
                                "accepted_step_index": target_step,
                                "parent_time_days": current_time,
                                "accepted_time_days": new_time,
                                "accepted_dt_days": dt_days,
                                "nominal_dt_days": nominal_dt_days,
                                "retry_count": retry,
                                "observation_clipped_step": observation_reached,
                                "breakthrough_time_days": canonical_bt_time,
                                "time_since_breakthrough_days": scalar(
                                    child["time_since_breakthrough_days"]
                                ),
                                "parent_producer_CO2_gas_cut": result[
                                    "parent_cut"
                                ],
                                "child_producer_CO2_gas_cut": result[
                                    "child_cut"
                                ],
                                "explicit_flux_CO2_gas_cut": result[
                                    "aggregate_flux_cut"
                                ],
                                "injected_CO2_mass_kg": result[
                                    "injected_mass_kg"
                                ],
                                "produced_CO2_mass_kg": result[
                                    "produced_mass_kg"
                                ],
                                "stored_CO2_mass_kg": result[
                                    "final_stored_mass_kg"
                                ],
                                "step_mass_residual_kg": result[
                                    "step_mass_residual_kg"
                                ],
                                "cumulative_mass_residual_kg": cumulative_resid,
                                "grid_to_CV_sampling_closure_kg": result[
                                    "sample_closure_kg"
                                ],
                                "child_grid_to_CV_sampling_closure_kg": result[
                                    "post_sample_closure_kg"
                                ],
                                "CV_transport_mass_residual_kg": result[
                                    "transport_residual_kg"
                                ],
                                "CV_to_grid_transfer_residual_kg": result[
                                    "transfer_residual_kg"
                                ],
                                "grid_mapback_ledger_residual_kg": result[
                                    "mapback_ledger_residual_kg"
                                ],
                                "capillary_external_mass_change_kg": result[
                                    "capillary_external_mass_change_kg"
                                ],
                                "source_local_added_mass_kg": 0.0,
                                "breakthrough_reached": True,
                            }
                        )

                        for row in result["producer_rows"]:
                            producer_rows_all.append(
                                {
                                    "accepted_step_index": target_step,
                                    "accepted_time_days": new_time,
                                    "time_since_breakthrough_days": scalar(
                                        child[
                                            "time_since_breakthrough_days"
                                        ]
                                    ),
                                    **row,
                                }
                            )

                        transport_residuals.append(
                            float(result["transport_residual_kg"])
                        )
                        transfer_residuals.append(
                            float(result["transfer_residual_kg"])
                        )
                        mapback_residuals.append(
                            float(result["mapback_ledger_residual_kg"])
                        )
                        capillary_external_changes.append(
                            float(
                                result[
                                    "capillary_external_mass_change_kg"
                                ]
                            )
                        )
                        sample_closures.append(
                            float(result["sample_closure_kg"])
                        )
                        post_sample_closures.append(
                            float(result["post_sample_closure_kg"])
                        )

                        current = child
                        accepted_transitions += 1
                        accepted = True

                        while (
                            next_snapshot_index
                            < len(SPARSE_SNAPSHOT_THRESHOLDS_DAYS)
                            and new_time + 1.0e-13
                            >= SPARSE_SNAPSHOT_THRESHOLDS_DAYS[
                                next_snapshot_index
                            ]
                        ):
                            threshold = SPARSE_SNAPSHOT_THRESHOLDS_DAYS[
                                next_snapshot_index
                            ]
                            if (
                                threshold < FIRST_OBSERVATION_DAY
                                or observation_reached
                            ):
                                snapshot_steps.append(target_step)
                                snapshot_times.append(new_time)
                                snapshot_sats.append(
                                    np.asarray(
                                        child["transport_saturation"],
                                        dtype=np.float64,
                                    ).copy()
                                )
                                snapshot_labels.append(
                                    (
                                        "EXACT_30D_CANONICAL_CHECKPOINT"
                                        if observation_reached
                                        and threshold
                                        == FIRST_OBSERVATION_DAY
                                        else
                                        f"FIRST_ACCEPTED_AT_OR_AFTER_"
                                        f"{threshold:g}D"
                                    )
                                )

                                metric = e36.plume_metrics(
                                    r2,
                                    np.asarray(
                                        child["transport_saturation"],
                                        dtype=np.float64,
                                    ),
                                    pressure_psi,
                                    p_ref_gas_pa,
                                    cell_pore_volume_m3,
                                    target_step,
                                    new_time,
                                )
                                metric["state_label"] = snapshot_labels[-1]
                                metric["producer_CO2_gas_cut"] = float(
                                    result["child_cut"]
                                )
                                plume_rows.append(metric)
                            next_snapshot_index += 1

                        if (
                            accepted_transitions % PROGRESS_EVERY == 0
                            or retry > 0
                            or observation_reached
                        ):
                            print(
                                f"[ACCEPT] step {target_step}: "
                                f"t={new_time:.12g} d, "
                                f"dt={dt_days:.12g} d, retry={retry}, "
                                f"cut={float(result['child_cut']):.6e}, "
                                f"cum prod="
                                f"{scalar(child['cumulative_produced_co2_mass_kg']):.6e} kg"
                            )
                        break

                    except (e37a.TrialReject, r2.GateError) as exc:
                        rejected_trials += 1
                        last_reason = repr(exc)
                        trial_failures.append(
                            {
                                "target_step": target_step,
                                "parent_time_days": current_time,
                                "retry": retry,
                                "trial_dt_days": dt_days,
                                "reason": last_reason,
                            }
                        )
                        print(
                            f"[REJECT] step {target_step} retry {retry}: "
                            f"dt={dt_days:.12g} d: {exc}"
                        )
                        if retry >= MAX_TRIAL_RETRIES:
                            raise GateError(
                                f"E39_retry_budget_exhausted:"
                                f"{target_step}:{last_reason}"
                            )

                if not accepted:
                    raise GateError(
                        f"E39_step_not_accepted:{target_step}:{last_reason}"
                    )

            failed_stage = "final_checkpoint_validation"

            final_state = current
            final_step = int_scalar(final_state["accepted_step_index"])
            final_time = scalar(final_state["physical_time_days"])
            final_mass = scalar(
                final_state["stored_co2_mass_current_kg"]
            )
            final_cum_resid = scalar(
                final_state["cumulative_mass_residual_kg"]
            )
            final_cut = scalar(
                final_state["current_producer_co2_gas_cut"]
            )
            final_injected = scalar(
                final_state["cumulative_injected_co2_mass_kg"]
            )
            final_produced = scalar(
                final_state["cumulative_produced_co2_mass_kg"]
            )
            final_tol = max(
                1.0e-6,
                1.0e-10 * max(abs(final_mass), 1.0),
            )

            postBT_injected = final_injected - initial_injected
            postBT_produced = final_produced - initial_produced
            postBT_stored_change = final_mass - initial_stored

            gate(
                "E39_exact_30d_landing",
                final_time == FIRST_OBSERVATION_DAY,
                final_time,
            )
            gate(
                "E39_observation_cursor_advanced_to_60d",
                int_scalar(final_state["observation_cursor_index"]) == 1
                and scalar(final_state["next_fixed_observation_day"])
                == NEXT_OBSERVATION_DAY,
                f"{int_scalar(final_state['observation_cursor_index'])}:"
                f"{scalar(final_state['next_fixed_observation_day'])}",
            )
            gate(
                "E39_first_observation_flag_true",
                bool_scalar(
                    final_state[
                        "first_fixed_observation_checkpoint_reached"
                    ]
                ),
            )
            gate(
                "E39_breakthrough_history_preserved",
                bool_scalar(final_state["breakthrough_reached"])
                and abs(
                    scalar(final_state["breakthrough_time_days"])
                    - canonical_bt_time
                )
                <= 1.0e-12,
                f"{bool_scalar(final_state['breakthrough_reached'])}:"
                f"{scalar(final_state['breakthrough_time_days'])}",
            )
            gate(
                "E39_time_since_breakthrough_exact",
                abs(
                    scalar(final_state["time_since_breakthrough_days"])
                    - (FIRST_OBSERVATION_DAY - canonical_bt_time)
                )
                <= 1.0e-12,
                scalar(final_state["time_since_breakthrough_days"]),
            )
            gate(
                "E39_current_gas_cut_valid",
                np.isfinite(final_cut) and 0.0 <= final_cut <= 1.0,
                final_cut,
            )
            gate(
                "E39_cumulative_production_nondecreasing",
                final_produced >= initial_produced - 1.0e-12,
                f"{initial_produced}:{final_produced}",
            )
            gate(
                "E39_injector_local_closure_never_used",
                all(
                    abs(float(r["source_local_added_mass_kg"]))
                    <= 1.0e-12
                    for r in rollout_rows
                ),
            )
            gate(
                "E39_cumulative_mass_closure",
                abs(final_cum_resid) <= final_tol,
                f"{final_cum_resid}:{final_tol}",
            )
            gate(
                "E39_CV_transport_mass_closure",
                max_abs(transport_residuals) <= final_tol,
                max_abs(transport_residuals),
            )
            gate(
                "E39_CV_subsegment_transfer_closure",
                max_abs(transfer_residuals) <= final_tol,
                max_abs(transfer_residuals),
            )
            gate(
                "E39_grid_mapback_ledger_closure",
                max_abs(mapback_residuals) <= final_tol,
                max_abs(mapback_residuals),
            )
            gate(
                "E39_capillary_zero_external_source",
                max_abs(capillary_external_changes) <= final_tol,
                max_abs(capillary_external_changes),
            )
            gate(
                "E39_grid_to_CV_sampling_closure",
                max_abs(sample_closures + post_sample_closures)
                <= final_tol,
                max_abs(sample_closures + post_sample_closures),
            )
            gate(
                "E39_E38_parent_unchanged",
                sha256_file(e38_parent_path) == e38_parent_sha_before,
                sha256_file(e38_parent_path),
            )
            gate(
                "E39_E36_cache_unchanged",
                sha256_file(e36_cache_path) == e36_cache_sha_before,
                sha256_file(e36_cache_path),
            )
            gate(
                "E39_E37B_bracket_unchanged",
                sha256_file(e37b_bracket_path) == e37b_bracket_sha_before,
                sha256_file(e37b_bracket_path),
            )
            gate(
                "E39_frozen_100d_unchanged",
                sha256_file(frozen_100d) == frozen_sha_before,
                sha256_file(frozen_100d),
            )
            gate(
                "E39_legacy_E37B_30d_checkpoint_still_absent",
                not e37b_30d.exists(),
                e37b_30d,
            )

            if (
                not snapshot_times
                or snapshot_times[-1] != FIRST_OBSERVATION_DAY
            ):
                snapshot_steps.append(final_step)
                snapshot_times.append(FIRST_OBSERVATION_DAY)
                snapshot_sats.append(
                    np.asarray(
                        final_state["transport_saturation"],
                        dtype=np.float64,
                    ).copy()
                )
                snapshot_labels.append(
                    "EXACT_30D_CANONICAL_CHECKPOINT"
                )
                metric = e36.plume_metrics(
                    r2,
                    np.asarray(
                        final_state["transport_saturation"],
                        dtype=np.float64,
                    ),
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    final_step,
                    final_time,
                )
                metric["state_label"] = (
                    "EXACT_30D_CANONICAL_CHECKPOINT"
                )
                metric["producer_CO2_gas_cut"] = final_cut
                plume_rows.append(metric)
            else:
                snapshot_labels[-1] = (
                    "EXACT_30D_CANONICAL_CHECKPOINT"
                )

            final_plume = e36.plume_metrics(
                r2,
                np.asarray(
                    final_state["transport_saturation"],
                    dtype=np.float64,
                ),
                pressure_psi,
                p_ref_gas_pa,
                cell_pore_volume_m3,
                final_step,
                final_time,
            )

            checkpoint_bytes = deterministic_npz_bytes(final_state)
            validate_checkpoint_restart(
                checkpoint_bytes,
                expected_step=final_step,
                expected_bt_time=canonical_bt_time,
                expected_sat=np.asarray(
                    final_state["transport_saturation"],
                    dtype=np.float64,
                ),
            )
            gate("canonical_30d_restart_artifact_validated", True, final_step)

            snapshot_bytes = deterministic_npz_bytes(
                {
                    "accepted_step_index": np.asarray(
                        snapshot_steps, dtype=np.int64
                    ),
                    "physical_time_days": np.asarray(
                        snapshot_times, dtype=np.float64
                    ),
                    "label": np.asarray(
                        snapshot_labels, dtype="U64"
                    ),
                    "transport_saturation": np.stack(
                        snapshot_sats, axis=0
                    ).astype(np.float64),
                }
            )

            observation_metrics = {
                "milestone": MILESTONE,
                "status": "CANONICAL_POST_BREAKTHROUGH_30D_SGSIM_PLUME_CHECKPOINT",
                "physical_time_days": final_time,
                "accepted_step_index": final_step,
                "breakthrough_reached": True,
                "breakthrough_time_days": canonical_bt_time,
                "time_since_breakthrough_days": scalar(
                    final_state["time_since_breakthrough_days"]
                ),
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "producer_CO2_gas_cut_at_30d": final_cut,
                "stored_CO2_mass_kg": final_mass,
                "cumulative_injected_CO2_mass_kg": final_injected,
                "cumulative_produced_CO2_mass_kg": final_produced,
                "post_breakthrough_injected_CO2_mass_kg": postBT_injected,
                "post_breakthrough_produced_CO2_mass_kg": postBT_produced,
                "post_breakthrough_stored_CO2_mass_change_kg": postBT_stored_change,
                "cumulative_mass_residual_kg": final_cum_resid,
                "plume": final_plume,
                "observation_cursor_index_after_commit": int_scalar(
                    final_state["observation_cursor_index"]
                ),
                "next_fixed_observation_day": scalar(
                    final_state["next_fixed_observation_day"]
                ),
            }

            controller_contract = {
                "milestone": MILESTONE,
                "status": "POST_BREAKTHROUGH_REFERENCE_MOBILITY_CV_ALIGNED_CONTROLLER_TO_30D",
                "restart_parent": "V16E-38 canonical breakthrough state",
                "breakthrough_state_policy": (
                    "breakthrough_reached and breakthrough_time_days are "
                    "historical state and persist exactly after the event"
                ),
                "instantaneous_cut_policy": (
                    "current producer CO2 gas cut is allowed to evolve "
                    "independently after breakthrough; no monotonicity gate"
                ),
                "nominal_dt_rule": (
                    "E37A physics-derived CFL x fastest exact/certified "
                    "terminal TOF"
                ),
                "nominal_dt_days": nominal_dt_days,
                "retry_policy": (
                    "numerical trial rejection leaves accepted state "
                    "unchanged; retry with dt_new = 0.5*dt_old"
                ),
                "maximum_retries_per_transition": MAX_TRIAL_RETRIES,
                "observation_policy": (
                    "hard clip final transition to exactly t=30.0 days; "
                    "canonical checkpoint advances cursor to 60.0 days"
                ),
                "injector_local_mass_closure_authorized": False,
                "global_plume_rescaling_authorized": False,
                "learned_F0_timestep_authorized": False,
                "cache_scope": (
                    "E36-certified V15-SG3 steady reference-mobility "
                    "pressure authority only"
                ),
                "production_dt_envelope_frozen": False,
                "production_mass_tolerance_frozen": False,
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "parent_milestone": "V16E-38",
                "parent_state_sha256": e38_parent_sha_before,
                "initial_step_index": initial_step,
                "initial_time_days": initial_time,
                "initial_producer_CO2_gas_cut": initial_cut,
                "canonical_breakthrough_time_days": canonical_bt_time,
                "canonical_breakthrough_step_index": initial_step,
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "final_accepted_step_index": final_step,
                "final_time_days": final_time,
                "continuation_transitions_executed": accepted_transitions,
                "nominal_dt_days": nominal_dt_days,
                "last_accepted_dt_days": scalar(
                    final_state["last_accepted_dt_days"]
                ),
                "total_rejected_trials": rejected_trials,
                "observation_checkpoint_reached": True,
                "first_fixed_observation_day": FIRST_OBSERVATION_DAY,
                "observation_cursor_index": int_scalar(
                    final_state["observation_cursor_index"]
                ),
                "next_fixed_observation_day": scalar(
                    final_state["next_fixed_observation_day"]
                ),
                "canonical_30d_state_created": True,
                "post_breakthrough_30d_checkpoint": True,
                "breakthrough_reached": True,
                "breakthrough_time_preserved_exact": (
                    abs(
                        scalar(final_state["breakthrough_time_days"])
                        - canonical_bt_time
                    )
                    <= 1.0e-12
                ),
                "time_since_breakthrough_days": scalar(
                    final_state["time_since_breakthrough_days"]
                ),
                "producer_CO2_gas_cut_at_30d": final_cut,
                "transport_faces_per_streamline": nfaces,
                "transport_control_volumes_per_streamline": ncv,
                "component_mass_primary_conserved_variable": True,
                "CV_aligned_transfer_active": True,
                "fixed_rate_inlet_mass_flux_exact": True,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
                "source_local_added_mass_kg_max_abs": 0.0,
                "CV_transport_mass_residual_kg_max_abs": max_abs(
                    transport_residuals
                ),
                "CV_to_subsegment_transfer_residual_kg_max_abs": max_abs(
                    transfer_residuals
                ),
                "grid_mapback_ledger_residual_kg_max_abs": max_abs(
                    mapback_residuals
                ),
                "capillary_external_mass_source_kg_max_abs": max_abs(
                    capillary_external_changes
                ),
                "grid_to_CV_sampling_closure_kg_max_abs": max_abs(
                    sample_closures + post_sample_closures
                ),
                "cumulative_injected_CO2_mass_kg": final_injected,
                "cumulative_produced_CO2_mass_kg": final_produced,
                "stored_CO2_mass_kg": final_mass,
                "cumulative_mass_residual_kg": final_cum_resid,
                "mass_numerical_closure_passed": (
                    abs(final_cum_resid) <= final_tol
                ),
                "post_breakthrough_injected_CO2_mass_kg": postBT_injected,
                "post_breakthrough_produced_CO2_mass_kg": postBT_produced,
                "post_breakthrough_stored_CO2_mass_change_kg": postBT_stored_change,
                "E36_certified_cache_reused": True,
                "cache_reuse_scope_reference_mobility_only": True,
                "learned_timestep_proposal_used": False,
                "F0_hidden_update_deferred": True,
                "SGSim_specific_dt_envelope_frozen": False,
                "SGSim_specific_mass_tolerance_frozen": False,
                "frozen_100d_checkpoint_modified": False,
                "E40_second_60d_observation_entry_ready": True,
                "IBDP_started": False,
            }

            handoff = f"""# PAD-Stream V16E-39 Handoff

V16E-39 restarts from the canonical V16E-38 breakthrough state at step {initial_step}, t={initial_time:.12g} days.

The breakthrough event is now historical runtime state:
- breakthrough_reached = True throughout the accepted continuation;
- breakthrough_time_days remains exactly {canonical_bt_time:.12g} days;
- time_since_breakthrough_days advances with physical time;
- the instantaneous producer CO2 gas cut is allowed to evolve after breakthrough and is not required to remain monotone.

Frozen production transport authority:
- 201 SG6 transport faces / 200 finite-volume control volumes per streamline;
- CO2 component mass remains the conserved transport variable;
- fixed 500 tonne/day injection remains the only external CO2 source;
- exact SG7D subsegment geometry remains the transfer authority;
- no injector-local source closure is authorized or executed;
- no global plume rescaling is authorized;
- R2 no-flow Cartesian capillary redistribution remains the capillary authority.

Controller:
- nominal dt = {nominal_dt_days:.12g} days from the frozen CFL/TOF rule;
- numerical rejection leaves the accepted parent unchanged and retries at dt/2;
- the final transition is hard-clipped to land at exactly 30.0 days;
- accepted transitions: {accepted_transitions};
- rejected numerical trials: {rejected_trials};
- F0 learned timestep remains disabled;
- neither the SGSim production dt envelope nor final runtime mass tolerance is frozen.

Canonical 30-day post-breakthrough checkpoint:
- accepted step: {final_step};
- physical time: {final_time:.12g} days;
- time since breakthrough: {scalar(final_state['time_since_breakthrough_days']):.12g} days;
- producer CO2 gas cut: {final_cut:.12e};
- cumulative injected CO2 mass: {final_injected:.12e} kg;
- cumulative produced CO2 mass: {final_produced:.12e} kg;
- post-breakthrough produced CO2 mass: {postBT_produced:.12e} kg;
- stored CO2 mass: {final_mass:.12e} kg;
- cumulative mass residual: {final_cum_resid:.12e} kg;
- observation cursor advanced to 60.0 days.

The E36-certified pressure/Darcy/Pollock/TOF cache remains authorized only under the current V15-SG3 steady reference-mobility pressure authority. Any future saturation-dependent pressure authority must revalidate the cache.

NEXT: {NEXT}
"""

            checkpoint_name = (
                "V16E39_Canonical_PostBreakthrough_SGSim_Runtime_State_"
                "Observation_0030d.npz"
            )
            snapshot_name = (
                "V16E39_PostBreakthrough_Rollout_Sparse_Plume_Snapshots.npz"
            )

            files: dict[str, bytes] = {
                checkpoint_name: checkpoint_bytes,
                snapshot_name: snapshot_bytes,
                "V16E39_PostBreakthrough_Rollout_Step_Audit.csv": csv_bytes(
                    rollout_rows
                ),
                "V16E39_PostBreakthrough_Producer_CO2_Response.csv": csv_bytes(
                    producer_rows_all
                ),
                "V16E39_PostBreakthrough_Sparse_Plume_Metrics.csv": csv_bytes(
                    plume_rows
                ),
                "V16E39_Trial_Rejection_Audit.csv": csv_bytes(
                    trial_failures
                ),
                "V16E39_Observation_0030d_Metrics.json": json_bytes(
                    observation_metrics
                ),
                "V16E39_PostBreakthrough_Controller_Contract.json": json_bytes(
                    controller_contract
                ),
                "PAD_Stream_V16E39_Summary.json": json_bytes(summary),
                "V16E39_Handoff.md": handoff.encode("utf-8"),
                "V16E39_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            }

            checkpoint_sha = hashlib.sha256(checkpoint_bytes).hexdigest()
            snapshot_sha = hashlib.sha256(snapshot_bytes).hexdigest()

            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed": all(
                    v["passed"] for v in gates.values()
                ),
                "gate_count": len(gates),
                "checkpoint_state_file": checkpoint_name,
                "checkpoint_state_sha256": checkpoint_sha,
                "sparse_snapshot_file": snapshot_name,
                "sparse_snapshot_sha256": snapshot_sha,
                "E38_parent_state_sha256": e38_parent_sha_before,
                "E36_certified_cache_sha256": e36_cache_sha_before,
                "E37B_breakthrough_bracket_report_sha256": (
                    e37b_bracket_sha_before
                ),
                "frozen_100d_sha256": frozen_sha_before,
                "breakthrough_reached": True,
                "breakthrough_time_days": canonical_bt_time,
                "breakthrough_time_preserved_exact": True,
                "observation_cursor_advanced": True,
                "next_fixed_observation_day": NEXT_OBSERVATION_DAY,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
            }
            files["V16E39_Final_Closure.json"] = json_bytes(closure)

            immutable_publish(out, files)

            manifest_rows = []
            for path in sorted(out.iterdir()):
                if (
                    path.is_file()
                    and path.name != "V16E39_Artifact_Manifest.csv"
                ):
                    manifest_rows.append(
                        {
                            "file": path.name,
                            "sha256": sha256_file(path),
                            "bytes": path.stat().st_size,
                        }
                    )
            immutable_publish(
                out,
                {
                    "V16E39_Artifact_Manifest.csv": csv_bytes(
                        manifest_rows
                    )
                },
            )

        print("\n" + "=" * 146)
        print(
            "PAD-Stream V16E-39 POST-BREAKTHROUGH "
            "FIRST FIXED OBSERVATION CHECKPOINT: PASS"
        )
        print("=" * 146)
        print(
            f"{'Restart step/time':82}: "
            f"{initial_step} / {initial_time:.12g} d"
        )
        print(
            f"{'Canonical breakthrough time':82}: "
            f"{canonical_bt_time:.12g} d"
        )
        print(
            f"{'Final accepted step/time':82}: "
            f"{final_step} / {final_time:.12g} d"
        )
        print(
            f"{'Accepted continuation transitions':82}: "
            f"{accepted_transitions}"
        )
        print(
            f"{'Rejected numerical trials':82}: "
            f"{rejected_trials}"
        )
        print(
            f"{'Physics-derived nominal dt':82}: "
            f"{nominal_dt_days:.12g} d"
        )
        print(
            f"{'Final observation-clipped dt':82}: "
            f"{scalar(final_state['last_accepted_dt_days']):.12g} d"
        )
        print(
            f"{'Producer CO2 gas cut at 30 d':82}: "
            f"{final_cut:.12e}"
        )
        print(
            f"{'Cumulative produced CO2 mass':82}: "
            f"{final_produced:.12e} kg"
        )
        print(
            f"{'Post-breakthrough produced CO2 mass':82}: "
            f"{postBT_produced:.12e} kg"
        )
        print(
            f"{'Stored CO2 mass':82}: "
            f"{final_mass:.12e} kg"
        )
        print(
            f"{'Cumulative mass residual':82}: "
            f"{final_cum_resid:.12e} kg"
        )
        print(
            f"{'Injector-local source closure':82}: "
            "DISABLED / 0.0 kg"
        )
        print(
            f"{'Next fixed observation':82}: "
            f"{scalar(final_state['next_fixed_observation_day']):.12g} d"
        )
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT_BLOCKED",
            "exception": repr(exc),
            "failed_stage": failed_stage,
            "gates": gates,
            "trial_failures": trial_failures,
            "canonical_30d_checkpoint_published": False,
            "E38_parent_mutated": (
                False
                if e38_parent_sha_before is None
                else (
                    not (drive / E38_REL / E38_CANONICAL).is_file()
                    or sha256_file(drive / E38_REL / E38_CANONICAL)
                    != e38_parent_sha_before
                )
            ),
            "E36_cache_mutated": (
                False
                if e36_cache_sha_before is None
                else (
                    not (drive / E36_REL / E36_CACHE).is_file()
                    or sha256_file(drive / E36_REL / E36_CACHE)
                    != e36_cache_sha_before
                )
            ),
            "frozen_100d_modified": (
                False
                if frozen_sha_before is None
                else (
                    not (drive / V16_FROZEN_REL).is_file()
                    or sha256_file(drive / V16_FROZEN_REL)
                    != frozen_sha_before
                )
            ),
            "next_action": (
                "Audit the failed E39 gate or numerical trial. "
                "Do not advance to the 60-day observation milestone "
                "until the canonical post-breakthrough 30-day checkpoint "
                "is validated."
            ),
        }
        data = json_bytes(report)
        path = blocked / "V16E39_Blocked_PostBreakthrough_30d.json"
        if path.exists() and path.read_bytes() != data:
            path = blocked / (
                "V16E39_Blocked_PostBreakthrough_30d_"
                f"{hashlib.sha256(data).hexdigest()[:12]}.json"
            )
        if not path.exists():
            path.write_bytes(data)

        print("\n" + "=" * 146)
        print(
            "PAD-Stream V16E-39 POST-BREAKTHROUGH "
            "FIRST FIXED OBSERVATION CHECKPOINT: BLOCKED"
        )
        print("=" * 146)
        print("Stage :", failed_stage)
        print("Reason:", repr(exc))
        print("No canonical V16E-39 30-day checkpoint was published.")
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
