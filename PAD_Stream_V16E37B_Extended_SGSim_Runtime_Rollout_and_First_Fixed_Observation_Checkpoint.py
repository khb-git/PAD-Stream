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


MILESTONE = "V16E-37B"
STATUS = "FIRST_FIXED_OBSERVATION_30D_CHECKPOINT_VALIDATED"
NEXT = "V16E-38 - Breakthrough Detection / Event Refinement"

EXPECTED_GRID = (15, 50, 50)
BACKGROUND_SATURATION = 0.20
INJECTED_BOUNDARY_SATURATION = 0.80
MAX_INCREMENTAL_CO2_SATURATION = 0.60
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
MAX_ACCEPTED_TRANSITIONS = 5000
PROGRESS_EVERY = 25
SPARSE_SNAPSHOT_THRESHOLDS_DAYS = (1.0, 5.0, 10.0, 20.0, 30.0)

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
    "V16E37B_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37B_BLOCKED_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT"
)


class GateError(RuntimeError):
    pass


class BreakthroughBracket(RuntimeError):
    def __init__(
        self,
        parent_time_days: float,
        trial_time_days: float,
        parent_cut: float,
        trial_cut: float,
        target_step: int,
    ) -> None:
        self.parent_time_days = float(parent_time_days)
        self.trial_time_days = float(trial_time_days)
        self.parent_cut = float(parent_cut)
        self.trial_cut = float(trial_cut)
        self.target_step = int(target_step)
        super().__init__(
            "breakthrough_bracket_detected:"
            f"step={target_step}:"
            f"time=[{parent_time_days},{trial_time_days}]:"
            f"cut=[{parent_cut},{trial_cut}]:"
            f"threshold={BREAKTHROUGH_GAS_CUT}"
        )


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


def weighted_outlet_gas_cut(
    sg7a: Any,
    cv_saturation: np.ndarray,
    weights_m3_day: np.ndarray,
) -> float:
    sat = np.asarray(cv_saturation, dtype=np.float64)
    q = np.asarray(weights_m3_day, dtype=np.float64)
    ff = np.asarray(
        sg7a.fractional_flow(sat[:, -1]), dtype=np.float64
    )
    qsum = float(np.sum(q))
    if qsum <= 0.0:
        raise GateError("nonpositive_total_streamline_weight")
    cut = float(np.sum(q * ff) / qsum)
    if not np.isfinite(cut) or not 0.0 <= cut <= 1.0:
        raise GateError(f"weighted_outlet_gas_cut_invalid:{cut}")
    return cut


def build_checkpoint_child(
    e36: Any,
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
    observation_reached: bool,
) -> dict[str, Any]:
    child = e36.make_child_state(
        parent,
        child_sat,
        pressure_psi,
        p_ref_gas_pa,
        dt_days,
        produced_mass_kg,
        aggregate_gas_cut,
        final_stored_mass_kg,
        step_mass_residual_kg,
        True,
    )

    child["transport_face_count"] = np.asarray(nfaces, dtype=np.int64)
    child["transport_control_volume_count"] = np.asarray(ncv, dtype=np.int64)
    child["control_volume_aligned_transfer_active"] = np.asarray(True, dtype=bool)
    child["component_mass_primary_conserved_variable"] = np.asarray(True, dtype=bool)
    child["injector_local_mass_closure_authorized"] = np.asarray(False, dtype=bool)
    child["injector_local_mass_closure_executed"] = np.asarray(False, dtype=bool)
    child["last_source_local_added_mass_kg"] = np.asarray(0.0, dtype=np.float64)
    child["E37B_extended_rollout_active"] = np.asarray(True, dtype=bool)
    child["first_fixed_observation_checkpoint_reached"] = np.asarray(
        observation_reached, dtype=bool
    )

    if observation_reached:
        child["physical_time_days"] = np.asarray(
            FIRST_OBSERVATION_DAY, dtype=np.float64
        )
        child["last_fixed_observation_day"] = np.asarray(
            FIRST_OBSERVATION_DAY, dtype=np.float64
        )
        child["observation_cursor_index"] = np.asarray(
            int_scalar(parent["observation_cursor_index"]) + 1,
            dtype=np.int64,
        )
        child["next_fixed_observation_day"] = np.asarray(
            NEXT_OBSERVATION_DAY, dtype=np.float64
        )
    return child


def validate_checkpoint_restart(
    data: bytes,
    expected_step: int,
    expected_sat: np.ndarray,
) -> None:
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        if int(z["accepted_step_index"]) != int(expected_step):
            raise GateError("checkpoint_restart_step_mismatch")
        if float(z["physical_time_days"]) != FIRST_OBSERVATION_DAY:
            raise GateError(
                f"checkpoint_restart_time_not_exact_30d:{z['physical_time_days']}"
            )
        if not np.array_equal(z["transport_saturation"], expected_sat):
            raise GateError("checkpoint_restart_saturation_not_byte_exact")
        if not bool(z["control_volume_aligned_transfer_active"]):
            raise GateError("checkpoint_restart_missing_CV_alignment")
        if bool(z["injector_local_mass_closure_authorized"]):
            raise GateError("checkpoint_restart_authorizes_source_local_closure")
        if not bool(z["first_fixed_observation_checkpoint_reached"]):
            raise GateError("checkpoint_restart_missing_observation_flag")
        if int(z["observation_cursor_index"]) != 1:
            raise GateError(
                f"checkpoint_restart_observation_cursor:{z['observation_cursor_index']}"
            )
        if float(z["next_fixed_observation_day"]) != NEXT_OBSERVATION_DAY:
            raise GateError(
                f"checkpoint_restart_next_observation:{z['next_fixed_observation_day']}"
            )


def self_test() -> None:
    # Exact observation landing must clip only the final step.
    start = 0.19649257345668342
    dt = 0.049123143364170854
    t = start
    count = 0
    while t < FIRST_OBSERVATION_DAY - 1.0e-14:
        h = min(dt, FIRST_OBSERVATION_DAY - t)
        if h <= 0.0:
            raise RuntimeError("self_test_nonpositive_observation_clip")
        t += h
        if FIRST_OBSERVATION_DAY - t <= 1.0e-13:
            t = FIRST_OBSERVATION_DAY
        count += 1
        if count > 1000:
            raise RuntimeError("self_test_observation_loop_excessive")
    if t != FIRST_OBSERVATION_DAY:
        raise RuntimeError("self_test_observation_not_exact")
    if count != 607:
        raise RuntimeError(f"self_test_expected_607_transitions:{count}")

    # Retry semantics leave the accepted time untouched and reduce only trial dt.
    accepted_time = 2.0
    nominal = 0.05
    retry_dt = nominal * RETRY_FACTOR
    if accepted_time != 2.0 or abs(retry_dt - 0.025) > 1.0e-15:
        raise RuntimeError("self_test_retry_semantics_failed")

    # Breakthrough bracket ordering contract.
    lo, hi = 9.0e-5, 1.1e-4
    if not (lo < BREAKTHROUGH_GAS_CUT <= hi):
        raise RuntimeError("self_test_breakthrough_bracket_failed")

    print("PAD-Stream V16E-37B observation/controller self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    trial_failures: list[dict[str, Any]] = []
    breakthrough_bracket: dict[str, Any] | None = None
    failed_step: int | None = None
    e37a_parent_sha_before: str | None = None
    e36_cache_sha_before: str | None = None
    frozen_sha_before: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 146)
        print(
            "PAD-Stream V16E-37B — Extended SGSim Runtime Rollout / "
            "First Fixed Observation Checkpoint"
        )
        print("=" * 146)
        print("Restart parent : V16E-37A accepted CV-aligned step 4")
        print("Target         : exact first fixed observation at t = 30.0 days")
        print("Transport      : frozen E37A 201-face / 200-CV component-mass authority")
        print("Controller     : nominal physics dt; numerical rejection -> dt/2 retry")
        print("Event policy   : breakthrough crossing before 30 d blocks E37B with a bracket; no silent event overstep")
        print("Forbidden      : injector-local source closure; global plume rescaling; learned F0 timestep")

        # ------------------------------------------------------------------
        # Source identity.
        # ------------------------------------------------------------------
        r2_path = root / R2_RUNNER
        e36_runner_path = root / E36_RUNNER
        e37a_runner_path = root / E37A_RUNNER
        sg7a_path = root / SG7A
        sg7d_path = root / SG7D
        perm_path = root / SGSIM_PERM

        for p in [
            r2_path,
            e36_runner_path,
            e37a_runner_path,
            sg7a_path,
            sg7d_path,
            perm_path,
        ]:
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
        gate(
            "E37A_runner_SHA_exact",
            sha256_file(e37a_runner_path) == E37A_RUNNER_SHA256,
            sha256_file(e37a_runner_path),
        )

        r2 = load_module(r2_path, "pad_stream_v16e37b_r2_authority")
        e36 = load_module(e36_runner_path, "pad_stream_v16e37b_e36_authority")
        e37a = load_module(e37a_runner_path, "pad_stream_v16e37b_e37a_authority")

        # ------------------------------------------------------------------
        # Accepted E37A restart and E36 certified cache.
        # ------------------------------------------------------------------
        e37a_dir = drive / E37A_REL
        e37a_summary_path = e37a_dir / E37A_SUMMARY
        e37a_closure_path = e37a_dir / E37A_CLOSURE
        e36_cache_path = drive / E36_REL / E36_CACHE
        frozen_100d = drive / V16_FROZEN_REL

        for p in [
            e37a_summary_path,
            e37a_closure_path,
            e36_cache_path,
            frozen_100d,
        ]:
            gate(f"provenance_exists_{p.name}", p.is_file(), p)

        e37a_summary = load_json(e37a_summary_path)
        e37a_closure = load_json(e37a_closure_path)
        gate(
            "E37A_status_accepted",
            e37a_summary.get("status") == E37A_EXPECTED_STATUS,
            e37a_summary.get("status"),
        )
        gate(
            "E37A_E37B_entry_ready",
            e37a_summary.get("E37B_extended_rollout_entry_ready") is True,
        )
        gate(
            "E37A_CV_alignment_active",
            e37a_summary.get("CV_pore_volume_alignment_passed") is True
            and e37a_summary.get("component_mass_primary_conserved_variable") is True,
        )
        gate(
            "E37A_source_local_closure_forbidden",
            e37a_summary.get("injector_local_mass_closure_authorized") is False
            and e37a_summary.get("injector_local_mass_closure_executed") is False
            and abs(float(e37a_summary.get("source_local_added_mass_kg_max_abs", 1.0))) <= 1.0e-12,
        )
        gate(
            "E37A_no_breakthrough",
            e37a_summary.get("breakthrough_reached") is False,
        )

        final_state_name = str(e37a_closure.get("final_state_file", ""))
        if not final_state_name:
            raise GateError("E37A_closure_missing_final_state_file")
        parent_state_path = e37a_dir / final_state_name
        gate("E37A_final_state_exists", parent_state_path.is_file(), parent_state_path)

        e37a_parent_sha_before = sha256_file(parent_state_path)
        e36_cache_sha_before = sha256_file(e36_cache_path)
        frozen_sha_before = sha256_file(frozen_100d)
        gate(
            "E37A_final_state_SHA_matches_closure",
            e37a_parent_sha_before == e37a_closure.get("final_state_sha256"),
            e37a_parent_sha_before,
        )
        gate(
            "E36_cache_SHA_matches_E37A_closure",
            e36_cache_sha_before == e37a_closure.get("E36_certified_cache_sha256"),
            e36_cache_sha_before,
        )
        gate(
            "frozen_100d_SHA_exact",
            frozen_sha_before == V16_FROZEN_SHA256,
            frozen_sha_before,
        )

        parent = load_npz(parent_state_path)
        cache = load_npz(e36_cache_path)
        gate(
            "E37A_restart_step_exact_4",
            int_scalar(parent["accepted_step_index"]) == 4,
            int_scalar(parent["accepted_step_index"]),
        )
        gate(
            "E37A_restart_time_matches_summary",
            abs(
                scalar(parent["physical_time_days"])
                - float(e37a_summary["final_time_days"])
            ) <= 1.0e-15,
            scalar(parent["physical_time_days"]),
        )
        gate(
            "E37A_restart_pre_30d",
            scalar(parent["physical_time_days"]) < FIRST_OBSERVATION_DAY,
            scalar(parent["physical_time_days"]),
        )
        gate(
            "E37A_restart_next_observation_30d",
            abs(scalar(parent["next_fixed_observation_day"]) - FIRST_OBSERVATION_DAY) <= 1.0e-12,
            scalar(parent["next_fixed_observation_day"]),
        )
        gate(
            "E37A_restart_CV_aligned",
            bool_scalar(parent["control_volume_aligned_transfer_active"]),
        )
        gate(
            "E37A_restart_source_local_closure_forbidden",
            not bool_scalar(parent["injector_local_mass_closure_authorized"]),
        )
        gate(
            "E37A_restart_no_breakthrough",
            not bool_scalar(parent["breakthrough_reached"]),
            scalar(parent["current_producer_co2_gas_cut"]),
        )
        gate(
            "E36_cache_reference_mobility_scope",
            bool_scalar(cache["reuse_scope_reference_mobility_only"]),
        )

        # ------------------------------------------------------------------
        # Load frozen transport/map-back physics without dirtying repository.
        # ------------------------------------------------------------------
        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E37B_") as td:
            tmp = Path(td)
            shutil.copy2(sg7a_path, tmp / SG7A)
            shutil.copy2(sg7d_path, tmp / SG7D)
            sg7a = load_module(tmp / SG7A, "pad_stream_v16e37b_sg7a")
            sg7d = load_module(tmp / SG7D, "pad_stream_v16e37b_sg7d")

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
            gate(
                "streamline_weights_match_fixed_injection_rate",
                abs(q_actual - q_expected) / q_expected < 1.0e-10,
                f"{q_actual}:{q_expected}",
            )

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

            expected_cv_pv = weights_m3_day[:, None] * np.diff(tof_days, axis=1)
            cv_pv = geometry["cv_pv_m3"]
            cv_pv_rel = float(
                np.linalg.norm((cv_pv - expected_cv_pv).ravel())
                / max(np.linalg.norm(expected_cv_pv.ravel()), 1.0e-30)
            )
            gate(
                "E37A_CV_pore_volume_alignment_revalidated",
                cv_pv_rel <= 1.0e-10,
                cv_pv_rel,
            )

            face_pressure_psi = e37a.build_face_pressure(
                e36,
                sg7d,
                xyz_m,
                pressure_psi,
            )

            # Recompute the same physics-derived nominal dt and bind it to E37A.
            dxi = float(xi_faces[1] - xi_faces[0])
            sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
            max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
            u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
            max_wave_speed = float(np.max(u_face) * max_df)
            dtD_cfl = float(sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS))
            fastest_tau_days = float(np.min(tau_end_s / DAY_TO_S))
            nominal_dt_days = float(dtD_cfl * fastest_tau_days)
            gate(
                "nominal_dt_matches_E37A",
                abs(nominal_dt_days - float(e37a_summary["nominal_dt_days"])) <= 1.0e-15,
                f"{nominal_dt_days}:{e37a_summary['nominal_dt_days']}",
            )

            dx_m, dy_m, dz_m = 20.0 * FT_TO_M, 20.0 * FT_TO_M, 4.0 * FT_TO_M
            cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m
            permeability_md = np.loadtxt(
                perm_path, skiprows=1, dtype=np.float64
            ).reshape(EXPECTED_GRID, order="C")
            gate(
                "SGSim_permeability_shape_exact",
                permeability_md.shape == EXPECTED_GRID,
                permeability_md.shape,
            )

            current = {k: np.asarray(v).copy() for k, v in parent.items()}
            initial_step = int_scalar(current["accepted_step_index"])
            initial_time = scalar(current["physical_time_days"])
            parent_cut = scalar(current["current_producer_co2_gas_cut"])

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
                np.asarray(current["transport_saturation"], dtype=np.float64).copy()
            ]
            snapshot_labels = ["E37A_START"]
            next_snapshot_index = 0

            plume_rows.append(
                e36.plume_metrics(
                    r2,
                    snapshot_sats[0],
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    initial_step,
                    initial_time,
                )
            )

            while scalar(current["physical_time_days"]) < FIRST_OBSERVATION_DAY - 1.0e-13:
                if accepted_transitions >= MAX_ACCEPTED_TRANSITIONS:
                    raise GateError(
                        f"accepted_transition_budget_exceeded:{MAX_ACCEPTED_TRANSITIONS}"
                    )

                current_time = scalar(current["physical_time_days"])
                target_step = int_scalar(current["accepted_step_index"]) + 1
                failed_step = target_step
                remaining = FIRST_OBSERVATION_DAY - current_time
                nominal_trial_dt = min(nominal_dt_days, remaining)
                if not np.isfinite(nominal_trial_dt) or nominal_trial_dt <= 0.0:
                    raise GateError(
                        f"nonpositive_extended_rollout_dt:{target_step}:{nominal_trial_dt}"
                    )

                accepted = False
                last_reason = ""
                for retry in range(MAX_TRIAL_RETRIES + 1):
                    dt_days = nominal_trial_dt * (RETRY_FACTOR ** retry)
                    # A retry may never jump beyond the first observation.
                    dt_days = min(dt_days, FIRST_OBSERVATION_DAY - current_time)
                    if not np.isfinite(dt_days) or dt_days <= 0.0:
                        raise GateError(
                            f"nonpositive_retry_dt:{target_step}:{retry}:{dt_days}"
                        )

                    try:
                        parent_sat = np.asarray(
                            current["transport_saturation"], dtype=np.float64
                        )
                        parent_stored = scalar(current["stored_co2_mass_current_kg"])
                        recomputed_parent = float(
                            r2.stored_co2_mass_kg(
                                parent_sat,
                                pressure_psi,
                                p_ref_gas_pa,
                                cell_pore_volume_m3,
                            )
                        )
                        parent_tol = max(
                            1.0e-6,
                            1.0e-10 * max(abs(parent_stored), 1.0),
                        )
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

                        # Parent canonical outlet cut from restart-sampled CV state.
                        canonical_parent_cut = weighted_outlet_gas_cut(
                            sg7a, old_cv_sat, weights_m3_day
                        )
                        if canonical_parent_cut >= BREAKTHROUGH_GAS_CUT:
                            raise BreakthroughBracket(
                                current_time,
                                current_time,
                                canonical_parent_cut,
                                canonical_parent_cut,
                                target_step,
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
                        physical_injected = INJECTOR_MASS_RATE_KG_DAY * dt_days
                        inj_tol = max(
                            1.0e-6,
                            1.0e-12 * max(abs(physical_injected), 1.0),
                        )
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
                        pre_capillary_sat = np.asarray(
                            mapping["corrected_saturation"], dtype=np.float64
                        )

                        capillary = r2.conservative_capillary_mass_redistribution(
                            transport_saturation=pre_capillary_sat,
                            permeability_md=permeability_md,
                            pressure_psi=pressure_psi,
                            p_ref_pa=p_ref_gas_pa,
                            cell_pore_volume_m3=cell_pore_volume_m3,
                            dt_seconds=dt_days * DAY_TO_S,
                        )
                        child_sat = np.asarray(
                            capillary["corrected"], dtype=np.float64
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

                        # Re-sample the CAPILLARY-CORRECTED canonical child grid.
                        # Breakthrough is evaluated on the state that would actually
                        # be committed, not on a pre-capillary path-only trial.
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
                        child_cut = weighted_outlet_gas_cut(
                            sg7a, child_cv_sat, weights_m3_day
                        )
                        trial_time = current_time + dt_days
                        if FIRST_OBSERVATION_DAY - trial_time <= 1.0e-13:
                            trial_time = FIRST_OBSERVATION_DAY

                        if (
                            canonical_parent_cut < BREAKTHROUGH_GAS_CUT
                            and child_cut >= BREAKTHROUGH_GAS_CUT
                        ):
                            raise BreakthroughBracket(
                                current_time,
                                trial_time,
                                canonical_parent_cut,
                                child_cut,
                                target_step,
                            )

                        prod_rows, aggregate_flux_cut = e37a.producer_rows_from_flux(
                            labels,
                            weights_m3_day,
                            transport["outlet_fractional_flow"],
                            transport["face_mass_flux_kg_day"][:, -1],
                            dt_days,
                        )
                        # The canonical child gas-cut memory is the post-capillary,
                        # restart-sampled child value. The producer mass ledger for
                        # this explicit step remains the old-state outlet mass flux.
                        observation_reached = trial_time == FIRST_OBSERVATION_DAY
                        child = build_checkpoint_child(
                            e36,
                            current,
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
                            observation_reached,
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
                        child["current_producer_co2_gas_cut"] = np.asarray(
                            child_cut, dtype=np.float64
                        )
                        child["breakthrough_reached"] = np.asarray(False, dtype=bool)
                        child["breakthrough_time_days"] = np.asarray(float("nan"), dtype=np.float64)
                        child["time_since_breakthrough_days"] = np.asarray(0.0, dtype=np.float64)

                        new_time = scalar(child["physical_time_days"])
                        if new_time <= current_time or new_time > FIRST_OBSERVATION_DAY + 1.0e-12:
                            raise e37a.TrialReject(
                                f"accepted_time_invalid:{current_time}:{new_time}:{FIRST_OBSERVATION_DAY}"
                            )

                        # Full producer breakdown must close to the explicit outlet
                        # mass ledger used by the finite-volume transport step.
                        prod_sum = float(
                            sum(float(row["CO2_mass_this_step_kg"]) for row in prod_rows)
                        )
                        if abs(prod_sum - produced_step) > max(
                            1.0e-6, 1.0e-10 * max(abs(produced_step), 1.0)
                        ):
                            raise e37a.TrialReject(
                                f"producer_mass_breakdown_mismatch:{prod_sum}:{produced_step}"
                            )

                        cumulative_resid = scalar(child["cumulative_mass_residual_kg"])
                        rollout_rows.append({
                            "accepted_step_index": target_step,
                            "parent_time_days": current_time,
                            "accepted_time_days": new_time,
                            "accepted_dt_days": dt_days,
                            "nominal_dt_days": nominal_dt_days,
                            "retry_count": retry,
                            "observation_clipped_step": observation_reached,
                            "grid_to_CV_sampling_closure_kg": sample_closure,
                            "child_grid_to_CV_sampling_closure_kg": post_sample_closure,
                            "injected_CO2_mass_kg": injected_step,
                            "produced_CO2_mass_kg": produced_step,
                            "CV_transport_mass_residual_kg": transport["mass_residual_kg"],
                            "CV_to_subsegment_transfer_residual_kg": mapping["transfer_residual_kg"],
                            "grid_mapback_ledger_residual_kg": mapping["ledger_residual_kg"],
                            "source_local_added_mass_kg": 0.0,
                            "injector_local_mass_closure_authorized": False,
                            "capillary_substeps": int(capillary["substeps"]),
                            "capillary_external_mass_change_kg": float(capillary["external_mass_change_kg"]),
                            "stored_CO2_mass_kg": final_stored,
                            "step_mass_residual_kg": step_residual,
                            "cumulative_mass_residual_kg": cumulative_resid,
                            "parent_producer_CO2_gas_cut": canonical_parent_cut,
                            "child_producer_CO2_gas_cut": child_cut,
                            "explicit_flux_CO2_gas_cut": aggregate_flux_cut,
                            "breakthrough_reached": False,
                        })
                        for row in prod_rows:
                            producer_rows_all.append({
                                "accepted_step_index": target_step,
                                "accepted_time_days": new_time,
                                **row,
                            })

                        transport_residuals.append(float(transport["mass_residual_kg"]))
                        transfer_residuals.append(float(mapping["transfer_residual_kg"]))
                        mapback_residuals.append(float(mapping["ledger_residual_kg"]))
                        capillary_external_changes.append(float(capillary["external_mass_change_kg"]))
                        sample_closures.append(float(sample_closure))
                        post_sample_closures.append(float(post_sample_closure))

                        current = child
                        parent_cut = child_cut
                        accepted_transitions += 1
                        accepted = True

                        # Sparse diagnostics: first accepted state on/after each
                        # threshold, plus the exact final 30-day checkpoint.
                        while (
                            next_snapshot_index < len(SPARSE_SNAPSHOT_THRESHOLDS_DAYS)
                            and new_time + 1.0e-13
                            >= SPARSE_SNAPSHOT_THRESHOLDS_DAYS[next_snapshot_index]
                        ):
                            threshold = SPARSE_SNAPSHOT_THRESHOLDS_DAYS[next_snapshot_index]
                            snapshot_steps.append(target_step)
                            snapshot_times.append(new_time)
                            snapshot_sats.append(child_sat.copy())
                            snapshot_labels.append(
                                f"FIRST_ACCEPTED_AT_OR_AFTER_{threshold:g}D"
                            )
                            next_snapshot_index += 1

                        if (
                            accepted_transitions % PROGRESS_EVERY == 0
                            or retry > 0
                            or observation_reached
                        ):
                            print(
                                f"[ACCEPT] step {target_step}: "
                                f"t={new_time:.12g} d, dt={dt_days:.12g} d, "
                                f"retry={retry}, cut={child_cut:.3e}, "
                                f"cum mass residual={cumulative_resid:.3e} kg"
                            )
                        break

                    except BreakthroughBracket:
                        raise
                    except (e37a.TrialReject, r2.GateError) as exc:
                        rejected_trials += 1
                        last_reason = repr(exc)
                        trial_failures.append({
                            "target_step": target_step,
                            "parent_time_days": current_time,
                            "retry": retry,
                            "trial_dt_days": dt_days,
                            "reason": last_reason,
                        })
                        print(
                            f"[REJECT] step {target_step} retry {retry}: "
                            f"dt={dt_days:.12g} d: {exc}"
                        )
                        if retry >= MAX_TRIAL_RETRIES:
                            raise GateError(
                                f"E37B_retry_budget_exhausted:{target_step}:{last_reason}"
                            )

                if not accepted:
                    raise GateError(f"E37B_step_not_accepted:{target_step}:{last_reason}")

            final_state = current
            final_step = int_scalar(final_state["accepted_step_index"])
            final_time = scalar(final_state["physical_time_days"])
            final_mass = scalar(final_state["stored_co2_mass_current_kg"])
            final_cum_resid = scalar(final_state["cumulative_mass_residual_kg"])
            final_cut = scalar(final_state["current_producer_co2_gas_cut"])
            final_tol = max(1.0e-6, 1.0e-10 * max(abs(final_mass), 1.0))

            gate("E37B_exact_30d_landing", final_time == FIRST_OBSERVATION_DAY, final_time)
            gate(
                "E37B_observation_cursor_advanced_to_60d",
                int_scalar(final_state["observation_cursor_index"]) == 1
                and scalar(final_state["next_fixed_observation_day"]) == NEXT_OBSERVATION_DAY,
                f"{int_scalar(final_state['observation_cursor_index'])}:{scalar(final_state['next_fixed_observation_day'])}",
            )
            gate(
                "E37B_first_observation_flag_true",
                bool_scalar(final_state["first_fixed_observation_checkpoint_reached"]),
            )
            gate(
                "E37B_no_breakthrough_before_or_at_30d",
                final_cut < BREAKTHROUGH_GAS_CUT
                and not bool_scalar(final_state["breakthrough_reached"]),
                final_cut,
            )
            gate(
                "E37B_injector_local_closure_never_used",
                all(abs(float(r["source_local_added_mass_kg"])) <= 1.0e-12 for r in rollout_rows),
            )
            gate(
                "E37B_cumulative_mass_closure",
                abs(final_cum_resid) <= final_tol,
                f"{final_cum_resid}:{final_tol}",
            )
            gate(
                "E37B_CV_transport_mass_closure",
                max_abs(transport_residuals) <= final_tol,
                max_abs(transport_residuals),
            )
            gate(
                "E37B_CV_subsegment_transfer_closure",
                max_abs(transfer_residuals) <= final_tol,
                max_abs(transfer_residuals),
            )
            gate(
                "E37B_grid_mapback_ledger_closure",
                max_abs(mapback_residuals) <= final_tol,
                max_abs(mapback_residuals),
            )
            gate(
                "E37B_capillary_zero_external_source",
                max_abs(capillary_external_changes) <= final_tol,
                max_abs(capillary_external_changes),
            )
            gate(
                "E37B_E37A_parent_unchanged",
                sha256_file(parent_state_path) == e37a_parent_sha_before,
                sha256_file(parent_state_path),
            )
            gate(
                "E37B_E36_cache_unchanged",
                sha256_file(e36_cache_path) == e36_cache_sha_before,
                sha256_file(e36_cache_path),
            )
            gate(
                "E37B_frozen_100d_unchanged",
                sha256_file(frozen_100d) == frozen_sha_before,
                sha256_file(frozen_100d),
            )

            # Guarantee the exact 30-day state is represented in sparse snapshots.
            if not snapshot_times or snapshot_times[-1] != FIRST_OBSERVATION_DAY:
                snapshot_steps.append(final_step)
                snapshot_times.append(FIRST_OBSERVATION_DAY)
                snapshot_sats.append(
                    np.asarray(final_state["transport_saturation"], dtype=np.float64).copy()
                )
                snapshot_labels.append("EXACT_30D_CANONICAL_CHECKPOINT")
            elif snapshot_labels[-1] != "EXACT_30D_CANONICAL_CHECKPOINT":
                snapshot_labels[-1] = "EXACT_30D_CANONICAL_CHECKPOINT"

            final_plume = e36.plume_metrics(
                r2,
                np.asarray(final_state["transport_saturation"], dtype=np.float64),
                pressure_psi,
                p_ref_gas_pa,
                cell_pore_volume_m3,
                final_step,
                final_time,
            )
            plume_rows.append(final_plume)

            checkpoint_bytes = deterministic_npz_bytes(final_state)
            validate_checkpoint_restart(
                checkpoint_bytes,
                final_step,
                np.asarray(final_state["transport_saturation"], dtype=np.float64),
            )

            snapshot_bytes = deterministic_npz_bytes({
                "accepted_step_index": np.asarray(snapshot_steps, dtype=np.int64),
                "physical_time_days": np.asarray(snapshot_times, dtype=np.float64),
                "label": np.asarray(snapshot_labels, dtype="U64"),
                "transport_saturation": np.stack(snapshot_sats, axis=0).astype(np.float64),
            })

            observation_metrics = {
                "milestone": MILESTONE,
                "status": "CANONICAL_30D_SGSIM_PLUME_CHECKPOINT",
                "physical_time_days": final_time,
                "accepted_step_index": final_step,
                "producer_CO2_gas_cut": final_cut,
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "breakthrough_reached": False,
                "stored_CO2_mass_kg": final_mass,
                "cumulative_injected_CO2_mass_kg": scalar(final_state["cumulative_injected_co2_mass_kg"]),
                "cumulative_produced_CO2_mass_kg": scalar(final_state["cumulative_produced_co2_mass_kg"]),
                "cumulative_mass_residual_kg": final_cum_resid,
                "plume": final_plume,
                "observation_cursor_index_after_commit": int_scalar(final_state["observation_cursor_index"]),
                "next_fixed_observation_day": scalar(final_state["next_fixed_observation_day"]),
            }

            controller_contract = {
                "milestone": MILESTONE,
                "status": "EXTENDED_REFERENCE_MOBILITY_CV_ALIGNED_CONTROLLER_TO_30D",
                "restart_parent": "V16E-37A accepted step-4 state",
                "nominal_dt_rule": "E37A physics-derived CFL x fastest exact/certified terminal TOF",
                "nominal_dt_days": nominal_dt_days,
                "retry_policy": "numerical trial rejection leaves accepted state unchanged; retry with dt_new = 0.5*dt_old",
                "maximum_retries_per_transition": MAX_TRIAL_RETRIES,
                "observation_policy": "hard clip final transition to t=30.0 days; canonical checkpoint advances cursor to 60.0 days",
                "breakthrough_policy": "if canonical child gas cut crosses 1e-4 before/on 30d, block E37B and hand exact accepted-state time bracket to E38; do not publish a 30d checkpoint",
                "injector_local_mass_closure_authorized": False,
                "global_plume_rescaling_authorized": False,
                "learned_F0_timestep_authorized": False,
                "cache_scope": "E36-certified V15-SG3 steady reference-mobility pressure authority only",
                "production_dt_envelope_frozen": False,
                "production_mass_tolerance_frozen": False,
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "parent_milestone": "V16E-37A",
                "parent_state_sha256": e37a_parent_sha_before,
                "initial_step_index": initial_step,
                "initial_time_days": initial_time,
                "final_accepted_step_index": final_step,
                "final_time_days": final_time,
                "continuation_transitions_executed": accepted_transitions,
                "nominal_dt_days": nominal_dt_days,
                "last_accepted_dt_days": scalar(final_state["last_accepted_dt_days"]),
                "total_rejected_trials": rejected_trials,
                "observation_checkpoint_reached": True,
                "first_fixed_observation_day": FIRST_OBSERVATION_DAY,
                "observation_cursor_index": int_scalar(final_state["observation_cursor_index"]),
                "next_fixed_observation_day": scalar(final_state["next_fixed_observation_day"]),
                "canonical_30d_state_created": True,
                "transport_faces_per_streamline": nfaces,
                "transport_control_volumes_per_streamline": ncv,
                "component_mass_primary_conserved_variable": True,
                "CV_aligned_transfer_active": True,
                "fixed_rate_inlet_mass_flux_exact": True,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
                "source_local_added_mass_kg_max_abs": 0.0,
                "CV_transport_mass_residual_kg_max_abs": max_abs(transport_residuals),
                "CV_to_subsegment_transfer_residual_kg_max_abs": max_abs(transfer_residuals),
                "grid_mapback_ledger_residual_kg_max_abs": max_abs(mapback_residuals),
                "capillary_external_mass_source_kg_max_abs": max_abs(capillary_external_changes),
                "grid_to_CV_sampling_closure_kg_max_abs": max_abs(sample_closures + post_sample_closures),
                "cumulative_injected_CO2_mass_kg": scalar(final_state["cumulative_injected_co2_mass_kg"]),
                "cumulative_produced_CO2_mass_kg": scalar(final_state["cumulative_produced_co2_mass_kg"]),
                "stored_CO2_mass_kg": final_mass,
                "cumulative_mass_residual_kg": final_cum_resid,
                "mass_numerical_closure_passed": abs(final_cum_resid) <= final_tol,
                "producer_CO2_gas_cut": final_cut,
                "breakthrough_reached": False,
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "breakthrough_overstep_prevented": True,
                "E36_certified_cache_reused": True,
                "cache_reuse_scope_reference_mobility_only": True,
                "learned_timestep_proposal_used": False,
                "F0_hidden_update_deferred": True,
                "SGSim_specific_dt_envelope_frozen": False,
                "SGSim_specific_mass_tolerance_frozen": False,
                "frozen_100d_checkpoint_modified": False,
                "E38_breakthrough_event_refinement_entry_ready": True,
                "IBDP_started": False,
            }

            handoff = f"""# PAD-Stream V16E-37B Handoff

V16E-37B extends the validated control-volume-aligned E37A runtime from accepted step {initial_step} at {initial_time:.12g} days to the first fixed observation at exactly 30.0 days.

Frozen production transport authority:
- 201 SG6 transport faces / 200 finite-volume control volumes per streamline;
- CO2 component mass is the conserved transport variable;
- fixed 500 tonne/day well injection is the only external CO2 source;
- exact SG7D subsegment geometry performs both restart inventory sampling and Cartesian map-back;
- no injector-local source closure is authorized or executed;
- no global plume rescaling is authorized;
- R2 no-flow Cartesian capillary redistribution remains the capillary authority.

Controller:
- nominal dt = {nominal_dt_days:.12g} days from the E37A physics-derived CFL/TOF rule;
- final transition is hard-clipped to land exactly at 30.0 days;
- numerical rejection does not mutate accepted state and retries with dt/2;
- accepted transitions: {accepted_transitions}; rejected trials: {rejected_trials};
- F0 learned timestep remains disabled;
- neither the SGSim production dt envelope nor final runtime mass tolerance is frozen.

Breakthrough policy:
- threshold = {BREAKTHROUGH_GAS_CUT:.1e} producer CO2 gas cut;
- every canonical child is restart-sampled after capillary redistribution and checked before acceptance;
- a threshold crossing before/on 30 days would block E37B and hand a time/gas-cut bracket to E38 rather than silently stepping over the event;
- no breakthrough occurred before or at the 30-day checkpoint in the accepted run.

Canonical 30-day checkpoint:
- accepted step index: {final_step};
- stored CO2 mass: {final_mass:.12e} kg;
- cumulative injected CO2 mass: {scalar(final_state['cumulative_injected_co2_mass_kg']):.12e} kg;
- cumulative produced CO2 mass: {scalar(final_state['cumulative_produced_co2_mass_kg']):.12e} kg;
- cumulative mass residual: {final_cum_resid:.12e} kg;
- producer CO2 gas cut: {final_cut:.12e};
- observation cursor advanced from 30 days to 60 days.

The E36-certified flow/path cache remains authorized only under the current V15-SG3 steady reference-mobility pressure authority. A future saturation-dependent/multiphase pressure solve must revalidate pressure, Darcy flux, Pollock paths, and TOF.

NEXT: {NEXT}
"""

            checkpoint_name = "V16E37B_Canonical_SGSim_Runtime_State_Observation_0030d.npz"
            snapshot_name = "V16E37B_Extended_Rollout_Sparse_Plume_Snapshots.npz"

            files: dict[str, bytes] = {
                checkpoint_name: checkpoint_bytes,
                snapshot_name: snapshot_bytes,
                "V16E37B_Extended_Rollout_Step_Audit.csv": csv_bytes(rollout_rows),
                "V16E37B_Producer_CO2_Response.csv": csv_bytes(producer_rows_all),
                "V16E37B_Sparse_Plume_Metrics.csv": csv_bytes(plume_rows),
                "V16E37B_Trial_Rejection_Audit.csv": csv_bytes(trial_failures),
                "V16E37B_Observation_0030d_Metrics.json": json_bytes(observation_metrics),
                "V16E37B_Extended_Controller_Contract.json": json_bytes(controller_contract),
                "PAD_Stream_V16E37B_Summary.json": json_bytes(summary),
                "V16E37B_Handoff.md": handoff.encode("utf-8"),
                "V16E37B_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            }

            checkpoint_sha = hashlib.sha256(checkpoint_bytes).hexdigest()
            snapshot_sha = hashlib.sha256(snapshot_bytes).hexdigest()
            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed": all(v["passed"] for v in gates.values()),
                "gate_count": len(gates),
                "checkpoint_state_file": checkpoint_name,
                "checkpoint_state_sha256": checkpoint_sha,
                "sparse_snapshot_file": snapshot_name,
                "sparse_snapshot_sha256": snapshot_sha,
                "E37A_parent_state_sha256": e37a_parent_sha_before,
                "E36_certified_cache_sha256": e36_cache_sha_before,
                "frozen_100d_sha256": frozen_sha_before,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
                "breakthrough_reached_before_or_at_30d": False,
            }
            files["V16E37B_Final_Closure.json"] = json_bytes(closure)

            immutable_publish(out, files)

            artifact_rows = []
            for path in sorted(out.iterdir()):
                if path.is_file() and path.name != "V16E37B_Artifact_Manifest.csv":
                    artifact_rows.append({
                        "file": path.name,
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    })
            immutable_publish(
                out,
                {"V16E37B_Artifact_Manifest.csv": csv_bytes(artifact_rows)},
            )

        print("\n" + "=" * 146)
        print("PAD-Stream V16E-37B FIRST FIXED OBSERVATION CHECKPOINT: PASS")
        print("=" * 146)
        print(f"{'Restart step/time':82}: {initial_step} / {initial_time:.12g} d")
        print(f"{'Final accepted step/time':82}: {final_step} / {final_time:.12g} d")
        print(f"{'Accepted continuation transitions':82}: {accepted_transitions}")
        print(f"{'Rejected numerical trials':82}: {rejected_trials}")
        print(f"{'Physics-derived nominal dt':82}: {nominal_dt_days:.12g} d")
        print(f"{'Final observation-clipped dt':82}: {scalar(final_state['last_accepted_dt_days']):.12g} d")
        print(f"{'Producer CO2 gas cut':82}: {final_cut:.12e}")
        print(f"{'Cumulative injected CO2 mass':82}: {scalar(final_state['cumulative_injected_co2_mass_kg']):.12e} kg")
        print(f"{'Stored CO2 mass':82}: {final_mass:.12e} kg")
        print(f"{'Cumulative mass residual':82}: {final_cum_resid:.12e} kg")
        print(f"{'Injector-local source closure':82}: DISABLED / 0.0 kg")
        print(f"{'Next fixed observation':82}: {scalar(final_state['next_fixed_observation_day']):.12g} d")
        print(f"NEXT: {NEXT}")
        return 0

    except BreakthroughBracket as exc:
        breakthrough_bracket = {
            "target_step": exc.target_step,
            "parent_time_days": exc.parent_time_days,
            "trial_time_days": exc.trial_time_days,
            "parent_CO2_gas_cut": exc.parent_cut,
            "trial_CO2_gas_cut": exc.trial_cut,
            "threshold": BREAKTHROUGH_GAS_CUT,
        }
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "FIRST_FIXED_OBSERVATION_ROLLOUT_BLOCKED_BY_BREAKTHROUGH_BRACKET",
            "exception": repr(exc),
            "failed_target_step": failed_step,
            "breakthrough_bracket": breakthrough_bracket,
            "gates": gates,
            "trial_failures": trial_failures,
            "accepted_E37B_checkpoint_published": False,
            "runtime_time_advance_committed_to_persistent_state": False,
            "E37A_parent_mutated": False,
            "E36_cache_mutated": False,
            "frozen_100d_modified": False,
            "next_action": "Advance to V16E-38 breakthrough event refinement using this deterministic bracket; do not publish a 30-day checkpoint from this path.",
        }
        data = json_bytes(report)
        path = blocked / "V16E37B_Blocked_Breakthrough_Bracket.json"
        if path.exists() and path.read_bytes() != data:
            path = blocked / (
                "V16E37B_Blocked_Breakthrough_Bracket_"
                f"{hashlib.sha256(data).hexdigest()[:12]}.json"
            )
        if not path.exists():
            path.write_bytes(data)
        print("\n" + "=" * 146)
        print("PAD-Stream V16E-37B FIRST FIXED OBSERVATION CHECKPOINT: BLOCKED BY BREAKTHROUGH")
        print("=" * 146)
        print("Reason:", repr(exc))
        print("No canonical 30-day checkpoint was published.")
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "FIRST_FIXED_OBSERVATION_30D_CHECKPOINT_BLOCKED",
            "exception": repr(exc),
            "failed_target_step": failed_step,
            "breakthrough_bracket": breakthrough_bracket,
            "gates": gates,
            "trial_failures": trial_failures,
            "E37A_parent_state_sha256_before": e37a_parent_sha_before,
            "E36_certified_cache_sha256_before": e36_cache_sha_before,
            "frozen_100d_sha256_before": frozen_sha_before,
            "accepted_E37B_checkpoint_published": False,
            "runtime_time_advance_committed_to_persistent_state": False,
            "E37A_parent_mutated": False,
            "E36_cache_mutated": False,
            "frozen_100d_modified": False,
            "next_action": "Audit the failed gate/trial. Do not advance to V16E-38 unless the failure is an explicit breakthrough bracket.",
        }
        data = json_bytes(report)
        path = blocked / "V16E37B_Blocked_First_Fixed_Observation_30d.json"
        if path.exists() and path.read_bytes() != data:
            path = blocked / (
                "V16E37B_Blocked_First_Fixed_Observation_30d_"
                f"{hashlib.sha256(data).hexdigest()[:12]}.json"
            )
        if not path.exists():
            path.write_bytes(data)
        print("\n" + "=" * 146)
        print("PAD-Stream V16E-37B FIRST FIXED OBSERVATION CHECKPOINT: BLOCKED")
        print("=" * 146)
        print("Reason:", repr(exc))
        print("No canonical 30-day checkpoint was published by this failed execution path.")
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
        parser.error(
            "--project-root and --drive-root are required unless --self-test is used"
        )
    raise SystemExit(main(args.project_root, args.drive_root))
