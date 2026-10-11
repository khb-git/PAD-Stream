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


MILESTONE = "V16E-41-R2"
STATUS = "CAPACITY_AWARE_CONSERVATIVE_MAPBACK_STEP_1475_RECOVERED"
NEXT = (
    "V16E-41-R3 - Capacity-Aware Production Rollout to 100d "
    "and Legacy Frozen-Candidate Regression"
)

EXPECTED_GRID = (15, 50, 50)
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0

EXPECTED_E40_STEP = 1222
EXPECTED_E40_TIME_DAYS = 60.0
EXPECTED_PARENT_STEP = 1474
EXPECTED_TARGET_STEP = 1475
EXPECTED_PARENT_TIME_DAYS = 69.88200296918518
EXPECTED_PARENT_STATE_SHA256 = (
    "a38d2892624ad242ffcbfaf50824284faca31f0106b8307b72aeccb6aa72cebc"
)
EXPECTED_OFFENDING_CELL_ZERO_BASED = (8, 25, 24)
EXPECTED_LAST_RETRY_EXCESS_KG = 0.00034387635241728276
EXPECTED_FAILURE_TOKEN = "capillary_cell_mass_capacity_exceeded"

MAX_TRIAL_RETRIES = 8
RETRY_FACTOR = 0.5
EXPECTED_PRE_FAILURE_REJECTIONS = 262

# We intentionally stay several production inversion tolerances below the
# nonlinear Sg=0.60 cell-mass ceiling. This is a timestep margin only; it does
# not alter mass, saturation, the map-back weights, or the capillary operator.
CAPACITY_GUARD_MULTIPLIER = 10.0
MAX_CAPACITY_ADJUSTMENTS = 4

R2_RUNNER = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_"
    "First_Controlled_Transition.py"
)
R2_RUNNER_SHA256 = (
    "3a1bf71ef601308e2fc18168bf2b9fc7c3dc9b0ff98e3735de1d4fa6ee624ab6"
)

E36_RUNNER = (
    "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_"
    "Snapshot_Validation.py"
)
E36_RUNNER_SHA256 = (
    "747a4f6ee4a5458624311fe2226773e0db778cc40a0460adfcbc454be22a3a0c"
)
E36_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"

E37A_RUNNER = (
    "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_"
    "Streamline_Grid_Transfer.py"
)
E37A_RUNNER_SHA256 = (
    "d2f0a006569846048c647cfccac3df9bb8a7ed970c3431c2291a617ea455ec59"
)
E37A_REL = Path(
    "provenance/hybrid_dp/"
    "V16E37A_CONTROL_VOLUME_ALIGNED_CONSERVATIVE_STREAMLINE_GRID_TRANSFER"
)
E37A_SUMMARY = "PAD_Stream_V16E37A_Summary.json"

E37B_RUNNER = (
    "PAD_Stream_V16E37B_Extended_SGSim_Runtime_Rollout_and_First_"
    "Fixed_Observation_Checkpoint.py"
)
E37B_RUNNER_SHA256 = (
    "8abec0348cb683e7805fd5b847d3f24b88b855edd3386914a6aad9a3a1d87471"
)

E38_RUNNER = (
    "PAD_Stream_V16E38_Breakthrough_Event_Refinement_and_Canonical_BT_State.py"
)
E38_RUNNER_SHA256 = (
    "6ed0ccb552353e25ea5bc6bd4ebc562469d2049b2e81da73e0640eebf2f7b478"
)

E40_RUNNER = (
    "PAD_Stream_V16E40_Post_Breakthrough_SGSim_Rollout_and_Second_"
    "60d_Observation_Checkpoint.py"
)
E40_RUNNER_SHA256 = (
    "27fe993a140ddfaa919f81124f4ef53ed4058c3b37000b0911810969325b8a28"
)
E40_REL = Path(
    "provenance/hybrid_dp/"
    "V16E40_POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT"
)
E40_SUMMARY = "PAD_Stream_V16E40_Summary.json"
E40_CLOSURE = "V16E40_Final_Closure.json"
E40_CANONICAL = (
    "V16E40_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0060d.npz"
)

E41_RUNNER = (
    "PAD_Stream_V16E41_Production_100D_Checkpoint_and_"
    "Legacy_Frozen_Candidate_Regression.py"
)
E41_RUNNER_SHA256 = (
    "d2365d3ddc3374c4afda3a9aa15a32ef6ec6ed1a50ee0659932447aac2d04771"
)
E41_BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41_BLOCKED_PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION"
)
E41_BLOCKED_REPORT = "V16E41_Blocked_100D_Production_Regression.json"

R1R2R1_RUNNER = (
    "PAD_Stream_V16E41R1R2R1_Shared_Inversion_Stage_Resolved_"
    "Capacity_Audit_Provenance_Binding_Repair.py"
)
R1R2R1_RUNNER_SHA256 = (
    "104ce828c2b1887e96e769933aedcc4360bd4e09267f106173b1aec52ff1c475"
)
R1R2R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R1R2R1_SHARED_INVERSION_STAGE_RESOLVED_CAPACITY_FAILURE_"
    "AUDIT_PROVENANCE_REPAIR"
)
R1R2R1_SUMMARY = "PAD_Stream_V16E41R1R2R1_Summary.json"
R1R2R1_CLOSURE = "V16E41R1R2R1_Final_Closure.json"
R1R2R1_REPAIR_INPUT = "V16E41R2_Repair_Design_Input.json"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R2_CAPACITY_AWARE_CONSERVATIVE_MAPBACK_TIMESTEP_REPAIR"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R2_BLOCKED_CAPACITY_AWARE_CONSERVATIVE_MAPBACK_TIMESTEP_REPAIR"
)

STATE_NAME = "V16E41R2_Accepted_Repaired_SGSim_Runtime_State_Step_1475.npz"


class GateError(RuntimeError):
    pass


class MapbackCapacityReject(RuntimeError):
    def __init__(self, record: dict[str, Any]):
        super().__init__(
            "mapback_capacity_preflight_reject:"
            f"{record['max_capacity_excess_kg']}:"
            f"{record['recommended_dt_days']}"
        )
        self.record = record


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


def parse_capacity_excess(exc: BaseException) -> float:
    s = str(exc)
    token = EXPECTED_FAILURE_TOKEN + ":"
    if token not in s:
        raise GateError(f"capacity_failure_token_not_found:{s}")
    tail = s.split(token, 1)[1]
    # Native GateError text is exactly token:value; be conservative if a
    # wrapper adds punctuation.
    value = ""
    for ch in tail:
        if ch in "0123456789+-.eE":
            value += ch
        else:
            break
    return float(value)


def self_test() -> None:
    # Receiver-limited case.
    parent = np.array([9.0, 2.0], dtype=np.float64)
    capacity = np.array([10.0, 10.0], dtype=np.float64)
    delta = np.array([2.0, -0.25], dtype=np.float64)
    cap_tol = 1.0e-8
    guard = CAPACITY_GUARD_MULTIPLIER * cap_tol

    upper = np.full(2, np.inf, dtype=np.float64)
    pos = delta > 0.0
    upper[pos] = (capacity[pos] - guard - parent[pos]) / delta[pos]

    lower = np.full(2, np.inf, dtype=np.float64)
    neg = delta < 0.0
    lower[neg] = parent[neg] / (-delta[neg])

    alpha = min(1.0, float(np.min(upper)), float(np.min(lower)))
    if not (0.49 < alpha < 0.51):
        raise RuntimeError(f"self_test_receiver_alpha:{alpha}")

    # At the recommended fraction, the receiving cell must retain the guard.
    trial = parent + alpha * delta
    if trial[0] > capacity[0] - guard + 1.0e-12:
        raise RuntimeError("self_test_guard_not_respected")

    # Reproduce the formal last-halving timestep scale.
    nominal = 0.049123143364170854
    retry8 = nominal * (0.5 ** 8)
    if abs(retry8 * DAY_TO_S - 16.579060885407664) > 1.0e-9:
        raise RuntimeError("self_test_retry8_seconds")

    print(
        "PAD-Stream V16E-41-R2 capacity-aware map-back timestep repair "
        "self-test: PASS"
    )


def preflight_mapback_capacity(
    *,
    r2: Any,
    e37a: Any,
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
    active_dt_days: float,
) -> dict[str, Any]:
    """
    Reproduce the frozen E37A map-back mass algebra through the nonlinear
    cell-capacity check, without changing any mass or saturation.

    The returned admissible timestep is a controller decision only. If the
    candidate is admissible, the original frozen E37A map-back is still called
    byte-for-byte as the spatial operator.
    """
    cv_id = geometry["cv_id"]
    flat = geometry["flat_cell"]
    pv = geometry["pv_m3"]
    pseg = geometry["pseg_psi"]

    old_flat_cv_sat = np.asarray(old_cv_saturation, dtype=np.float64).reshape(-1)
    new_flat_cv_sat = np.asarray(new_cv_saturation, dtype=np.float64).reshape(-1)

    old_sub_sat = old_flat_cv_sat[cv_id]
    new_sub_sat = new_flat_cv_sat[cv_id]
    old_sub_sg = np.clip(
        old_sub_sat - e37a.BACKGROUND_SATURATION,
        0.0,
        e37a.MAX_INCREMENTAL_CO2_SATURATION,
    )
    new_sub_sg = np.clip(
        new_sub_sat - e37a.BACKGROUND_SATURATION,
        0.0,
        e37a.MAX_INCREMENTAL_CO2_SATURATION,
    )

    rho_old = np.asarray(
        r2.gas_density_from_state(old_sub_sat, pseg, p_ref_gas_pa),
        dtype=np.float64,
    )
    rho_new = np.asarray(
        r2.gas_density_from_state(new_sub_sat, pseg, p_ref_gas_pa),
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
    transfer_tol = max(1.0e-6, 1.0e-10 * max(abs(cv_delta), 1.0))

    # The controller must never mask an upstream transfer-closure failure.
    if abs(transfer_residual) > transfer_tol:
        return {
            "controller_applicable": False,
            "native_failure_required": True,
            "reason": "CV_to_subsegment_component_transfer_closure",
            "transfer_residual_kg": transfer_residual,
            "transfer_tolerance_kg": transfer_tol,
        }

    parent_sat = np.asarray(parent_grid_saturation, dtype=np.float64)
    parent_sg = np.clip(
        parent_sat - e37a.BACKGROUND_SATURATION,
        0.0,
        e37a.MAX_INCREMENTAL_CO2_SATURATION,
    )
    parent_rho = np.asarray(
        r2.gas_density_from_state(
            parent_sat,
            pressure_psi,
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    parent_mass = float(cell_pore_volume_m3) * parent_rho * parent_sg
    trial_mass = parent_mass + deposited_delta_mass

    roundoff = max(
        1.0e-6,
        1.0e-10 * max(abs(float(target_final_mass_kg)), 1.0),
    )
    mapped_total = float(np.sum(np.maximum(trial_mass, 0.0)))
    ledger_residual = mapped_total - float(target_final_mass_kg)

    # Preserve native ordering for non-capacity failures.
    if float(np.min(trial_mass)) < -roundoff:
        return {
            "controller_applicable": False,
            "native_failure_required": True,
            "reason": "aligned_mapback_negative_cell_mass",
            "min_trial_mass_kg": float(np.min(trial_mass)),
            "roundoff_mass_kg": roundoff,
        }
    if abs(ledger_residual) > roundoff:
        return {
            "controller_applicable": False,
            "native_failure_required": True,
            "reason": "aligned_mapback_component_ledger_residual",
            "ledger_residual_kg": ledger_residual,
            "roundoff_mass_kg": roundoff,
        }

    smax_field = np.full(
        EXPECTED_GRID,
        r2.INJECTED_BOUNDARY_SATURATION,
        dtype=np.float64,
    )
    rho_max = np.asarray(
        r2.gas_density_from_state(
            smax_field,
            pressure_psi,
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    capacity = (
        float(cell_pore_volume_m3)
        * rho_max
        * r2.MAX_INCREMENTAL_CO2_SATURATION
    )
    excess = trial_mass - capacity
    max_excess = float(np.max(excess))
    cap_tol = max(
        1.0e-8,
        1.0e-12 * max(float(np.max(capacity)), 1.0),
    )
    guard_kg = CAPACITY_GUARD_MULTIPLIER * cap_tol

    positive = deposited_delta_mass > 0.0
    negative = deposited_delta_mass < 0.0

    upper_alpha = np.full(EXPECTED_GRID, np.inf, dtype=np.float64)
    upper_room = capacity - guard_kg - parent_mass
    upper_alpha[positive] = (
        upper_room[positive] / deposited_delta_mass[positive]
    )

    lower_alpha = np.full(EXPECTED_GRID, np.inf, dtype=np.float64)
    lower_alpha[negative] = (
        parent_mass[negative] / (-deposited_delta_mass[negative])
    )

    upper_flat = int(np.argmin(upper_alpha))
    lower_flat = int(np.argmin(lower_alpha))
    upper_min = float(upper_alpha.reshape(-1)[upper_flat])
    lower_min = float(lower_alpha.reshape(-1)[lower_flat])

    raw_alpha = min(1.0, upper_min, lower_min)
    if not np.isfinite(raw_alpha):
        raw_alpha = 1.0

    max_flat = int(np.argmax(excess))
    max_cell = tuple(int(x) for x in np.unravel_index(max_flat, EXPECTED_GRID))
    upper_cell = tuple(
        int(x) for x in np.unravel_index(upper_flat, EXPECTED_GRID)
    )
    lower_cell = tuple(
        int(x) for x in np.unravel_index(lower_flat, EXPECTED_GRID)
    )

    if raw_alpha <= 0.0:
        recommended_dt_days = 0.0
    else:
        recommended_dt_days = float(active_dt_days) * min(1.0, raw_alpha)

    return {
        "controller_applicable": True,
        "native_failure_required": False,
        "candidate_dt_days": float(active_dt_days),
        "candidate_dt_seconds": float(active_dt_days * DAY_TO_S),
        "candidate_target_final_mass_kg": float(target_final_mass_kg),
        "candidate_cv_delta_mass_kg": cv_delta,
        "candidate_subsegment_delta_mass_kg": sub_delta,
        "transfer_residual_kg": transfer_residual,
        "transfer_tolerance_kg": transfer_tol,
        "mapback_ledger_residual_kg": ledger_residual,
        "mapback_roundoff_mass_kg": roundoff,
        "max_capacity_excess_kg": max_excess,
        "capacity_tolerance_kg": cap_tol,
        "capacity_guard_kg": guard_kg,
        "raw_admissible_fraction": float(raw_alpha),
        "recommended_dt_days": recommended_dt_days,
        "recommended_dt_seconds": float(recommended_dt_days * DAY_TO_S),
        "max_excess_cell_zero_based": list(max_cell),
        "upper_limiting_cell_zero_based": list(upper_cell),
        "lower_limiting_cell_zero_based": list(lower_cell),
        "upper_limiting_alpha": upper_min,
        "lower_limiting_alpha": lower_min,
        "upper_limiting_parent_mass_kg": float(parent_mass[upper_cell]),
        "upper_limiting_capacity_kg": float(capacity[upper_cell]),
        "upper_limiting_candidate_delta_mass_kg": float(
            deposited_delta_mass[upper_cell]
        ),
        "upper_limiting_candidate_trial_mass_kg": float(trial_mass[upper_cell]),
        "upper_limiting_candidate_excess_kg": float(excess[upper_cell]),
        "candidate_min_trial_mass_kg": float(np.min(trial_mass)),
        "candidate_max_trial_mass_kg": float(np.max(trial_mass)),
        "candidate_max_capacity_kg": float(np.max(capacity)),
        "candidate_is_capacity_admissible": bool(max_excess <= cap_tol),
    }


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

    provenance_sha_before: dict[str, str] = {}

    try:
        print("\n" + "=" * 146)
        print(
            "PAD-Stream V16E-41-R2 — Capacity-Aware Conservative "
            "CV-to-Grid Map-Back Timestep Repair"
        )
        print("=" * 146)
        print("SCOPE          : recover blocked production transition step 1475 only")
        print("PARENT         : exact reproduced E41 step-1474 state")
        print("NEW MECHANISM  : capacity-aware map-back timestep preflight")
        print("MAP-BACK       : frozen E37A spatial operator unchanged")
        print("CAPILLARY      : frozen R2 conservative capillary operator unchanged")
        print("PROHIBITED     : clipping, mass deletion/addition, plume rescaling")
        print("100-DAY CLAIM  : NONE")
        print("LEGACY REGRESS : NOT STARTED")

        failed_stage = "source_and_provenance_binding"

        paths = {
            "R2": root / R2_RUNNER,
            "E36": root / E36_RUNNER,
            "E37A": root / E37A_RUNNER,
            "E37B": root / E37B_RUNNER,
            "E38": root / E38_RUNNER,
            "E40": root / E40_RUNNER,
            "E41": root / E41_RUNNER,
            "R1R2R1": root / R1R2R1_RUNNER,
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
            ("R1R2R1", R1R2R1_RUNNER_SHA256),
        ]:
            actual = sha256_file(paths[key])
            gate(f"{key}_runner_SHA_exact", actual == expected, actual)
            provenance_sha_before[f"source_{key}"] = actual

        r2 = load_module(paths["R2"], "pad_stream_v16e41r2_r2")
        e36 = load_module(paths["E36"], "pad_stream_v16e41r2_e36")
        e37a = load_module(paths["E37A"], "pad_stream_v16e41r2_e37a")
        e37b = load_module(paths["E37B"], "pad_stream_v16e41r2_e37b")
        e38 = load_module(paths["E38"], "pad_stream_v16e41r2_e38")
        e41 = load_module(paths["E41"], "pad_stream_v16e41r2_e41")

        e40_dir = drive / E40_REL
        e40_summary_path = e40_dir / E40_SUMMARY
        e40_closure_path = e40_dir / E40_CLOSURE
        e40_parent_path = e40_dir / E40_CANONICAL
        e36_cache_path = drive / E36_REL / E36_CACHE
        e37a_summary_path = drive / E37A_REL / E37A_SUMMARY
        e41_blocked_path = drive / E41_BLOCKED_REL / E41_BLOCKED_REPORT
        r1r2r1_dir = drive / R1R2R1_REL
        r1r2r1_summary_path = r1r2r1_dir / R1R2R1_SUMMARY
        r1r2r1_closure_path = r1r2r1_dir / R1R2R1_CLOSURE
        r1r2r1_repair_path = r1r2r1_dir / R1R2R1_REPAIR_INPUT

        provenance_files = {
            "E40_summary": e40_summary_path,
            "E40_closure": e40_closure_path,
            "E40_parent": e40_parent_path,
            "E36_cache": e36_cache_path,
            "E37A_summary": e37a_summary_path,
            "E41_blocked": e41_blocked_path,
            "R1R2R1_summary": r1r2r1_summary_path,
            "R1R2R1_closure": r1r2r1_closure_path,
            "R1R2R1_repair_input": r1r2r1_repair_path,
        }
        for key, p in provenance_files.items():
            gate(f"provenance_exists_{key}", p.is_file(), p)
            provenance_sha_before[key] = sha256_file(p)

        e40_summary = load_json(e40_summary_path)
        e40_closure = load_json(e40_closure_path)
        e37a_summary = load_json(e37a_summary_path)
        e41_blocked = load_json(e41_blocked_path)
        diagnosis = load_json(r1r2r1_summary_path)
        diagnosis_closure = load_json(r1r2r1_closure_path)
        repair_input = load_json(r1r2r1_repair_path)

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
            "E41_originally_blocked",
            e41_blocked.get("status")
            == "PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION_BLOCKED",
            e41_blocked.get("status"),
        )
        gate(
            "R1R2R1_formally_closed",
            diagnosis.get("status")
            == "SHARED_INVERSION_STAGE_RESOLVED_CAPACITY_FAILURE_AUDITED_R1",
            diagnosis.get("status"),
        )
        gate(
            "R1R2R1_all_audit_gates_passed",
            diagnosis_closure.get("all_audit_gates_passed") is True,
        )
        gate(
            "diagnosis_mapback_only",
            diagnosis.get("stage_resolved_diagnosis")
            == "MAPBACK_CAPACITY_FAILURE_ONLY"
            and int(diagnosis.get("mapback_failure_count", -1)) == 9
            and int(diagnosis.get("capillary_failure_count", -1)) == 0,
            diagnosis.get("failure_stage_counts"),
        )
        gate(
            "diagnosis_same_cell_all_retries",
            diagnosis.get("same_offending_cell_all_retries") is True,
            diagnosis.get("offending_cells_zero_based"),
        )
        offender = tuple(
            int(x)
            for x in diagnosis.get("offending_cells_zero_based", [[-1, -1, -1]])[0]
        )
        gate(
            "diagnosis_offending_cell_exact",
            offender == EXPECTED_OFFENDING_CELL_ZERO_BASED,
            offender,
        )
        gate(
            "diagnosis_parent_time_exact",
            abs(float(diagnosis.get("accepted_parent_time_days", -1.0))
                - EXPECTED_PARENT_TIME_DAYS)
            <= 1.0e-12,
            diagnosis.get("accepted_parent_time_days"),
        )
        gate(
            "diagnosis_parent_state_SHA_exact",
            diagnosis.get("accepted_parent_state_sha256")
            == EXPECTED_PARENT_STATE_SHA256,
            diagnosis.get("accepted_parent_state_sha256"),
        )
        gate(
            "diagnosis_final_excess_exact",
            abs(float(diagnosis.get("last_retry_capacity_excess_kg", -1.0))
                - EXPECTED_LAST_RETRY_EXCESS_KG)
            <= 1.0e-12,
            diagnosis.get("last_retry_capacity_excess_kg"),
        )
        gate(
            "diagnosis_authorizes_stage_appropriate_R2_design",
            repair_input.get("R1_R2_authorizes_stage_appropriate_R2_design")
            is True,
        )

        formal_trials = [
            row
            for row in e41_blocked.get("trial_failures", [])
            if int(row.get("target_step", -1)) == EXPECTED_TARGET_STEP
        ]
        formal_trials = sorted(
            formal_trials,
            key=lambda row: int(row.get("retry", -1)),
        )
        gate(
            "formal_step1475_has_nine_retries",
            len(formal_trials) == 9
            and [int(r["retry"]) for r in formal_trials] == list(range(9)),
            formal_trials,
        )
        formal_retry_dt_days = [
            float(row["trial_dt_days"]) for row in formal_trials
        ]
        formal_parent_times = {
            float(row["parent_time_days"]) for row in formal_trials
        }
        gate(
            "formal_step1475_parent_time_exact",
            len(formal_parent_times) == 1
            and abs(next(iter(formal_parent_times)) - EXPECTED_PARENT_TIME_DAYS)
            <= 1.0e-12,
            formal_parent_times,
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

        failed_stage = "physics_setup_and_parent_reproduction"

        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E41R2_") as td:
            tmp = Path(td)
            shutil.copy2(paths["SG7A"], tmp / SG7A)
            shutil.copy2(paths["SG7D"], tmp / SG7D)
            sg7a = load_module(tmp / SG7A, "pad_stream_v16e41r2_sg7a")
            sg7d = load_module(tmp / SG7D, "pad_stream_v16e41r2_sg7d")

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

            weights_m3_day = weights_m3_s * DAY_TO_S
            tof_days = tau_s / DAY_TO_S
            operator = sg7d.build_subsegment_operator(
                xyz_m,
                tof_days,
                weights_m3_day,
            )

            p_ref_gas_pa = scalar(
                parent["co2_density_reference_pressure_pa"]
            )
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
            max_df = float(
                np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan))))
            )
            u_face = np.asarray(
                sg7a.u_dimensionless(xi_faces),
                dtype=np.float64,
            )
            max_wave_speed = float(np.max(u_face) * max_df)
            dtD_cfl = float(
                sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS)
            )
            fastest_tau_days = float(
                np.min(tau_end_s / DAY_TO_S)
            )
            nominal_dt_days = float(
                dtD_cfl * fastest_tau_days
            )

            gate(
                "nominal_dt_matches_E37A",
                abs(
                    nominal_dt_days
                    - float(e37a_summary["nominal_dt_days"])
                )
                <= 1.0e-15,
                nominal_dt_days,
            )

            dx_m = 20.0 * FT_TO_M
            dy_m = 20.0 * FT_TO_M
            dz_m = 4.0 * FT_TO_M
            cell_pore_volume_m3 = (
                0.20 * dx_m * dy_m * dz_m
            )

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

            current = {
                k: np.asarray(v).copy()
                for k, v in parent.items()
            }
            pre_failure_rejections = 0

            while (
                int_scalar(current["accepted_step_index"])
                < EXPECTED_PARENT_STEP
            ):
                target_step = (
                    int_scalar(current["accepted_step_index"]) + 1
                )
                accepted = False
                last_reason = ""

                for retry in range(MAX_TRIAL_RETRIES + 1):
                    dt_days = (
                        nominal_dt_days * (RETRY_FACTOR ** retry)
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

                        child = e41.apply_e41_state_semantics(
                            result["child"],
                            current,
                            canonical_breakthrough_time_days=scalar(
                                parent["breakthrough_time_days"]
                            ),
                            observation_reached=False,
                        )
                        child[
                            "current_producer_co2_gas_cut"
                        ] = np.asarray(
                            result["child_cut"],
                            dtype=np.float64,
                        )
                        child[
                            "last_CV_transport_mass_residual_kg"
                        ] = np.asarray(
                            result["transport_residual_kg"],
                            dtype=np.float64,
                        )
                        child[
                            "last_CV_to_grid_transfer_residual_kg"
                        ] = np.asarray(
                            result["transfer_residual_kg"],
                            dtype=np.float64,
                        )
                        child[
                            "last_grid_mapback_ledger_residual_kg"
                        ] = np.asarray(
                            result["mapback_ledger_residual_kg"],
                            dtype=np.float64,
                        )
                        child[
                            "last_grid_to_CV_sampling_closure_kg"
                        ] = np.asarray(
                            result["post_sample_closure_kg"],
                            dtype=np.float64,
                        )

                        current = child
                        accepted = True
                        break

                    except (e37a.TrialReject, r2.GateError) as exc:
                        pre_failure_rejections += 1
                        last_reason = repr(exc)
                        if retry >= MAX_TRIAL_RETRIES:
                            raise GateError(
                                "unexpected_failure_before_step1475:"
                                f"{target_step}:{last_reason}"
                            )

                if not accepted:
                    raise GateError(
                        "parent_reproduction_step_not_accepted:"
                        f"{target_step}:{last_reason}"
                    )

            accepted_parent = current
            accepted_parent_time = scalar(
                accepted_parent["physical_time_days"]
            )
            accepted_parent_bytes = deterministic_npz_bytes(
                accepted_parent
            )
            accepted_parent_sha = hashlib.sha256(
                accepted_parent_bytes
            ).hexdigest()

            gate(
                "accepted_parent_step1474_exact",
                int_scalar(
                    accepted_parent["accepted_step_index"]
                )
                == EXPECTED_PARENT_STEP,
                int_scalar(
                    accepted_parent["accepted_step_index"]
                ),
            )
            gate(
                "accepted_parent_time_exact",
                abs(
                    accepted_parent_time
                    - EXPECTED_PARENT_TIME_DAYS
                )
                <= 1.0e-12,
                accepted_parent_time,
            )
            gate(
                "accepted_parent_state_SHA_exact",
                accepted_parent_sha
                == EXPECTED_PARENT_STATE_SHA256,
                accepted_parent_sha,
            )
            gate(
                "pre_failure_rejection_count_exact",
                pre_failure_rejections
                == int(
                    diagnosis.get(
                        "pre_failure_rejected_trials",
                        EXPECTED_PRE_FAILURE_REJECTIONS,
                    )
                )
                == EXPECTED_PRE_FAILURE_REJECTIONS,
                pre_failure_rejections,
            )

            failed_stage = "original_step1475_failure_reproduction"

            original_last_dt = formal_retry_dt_days[-1]
            original_failure_record: dict[str, Any] = {
                "parent_step_index": EXPECTED_PARENT_STEP,
                "parent_time_days": accepted_parent_time,
                "target_step": EXPECTED_TARGET_STEP,
                "formal_retry_index": 8,
                "formal_retry_dt_days": original_last_dt,
                "formal_retry_dt_seconds": original_last_dt * DAY_TO_S,
                "expected_failure_token": EXPECTED_FAILURE_TOKEN,
                "expected_capacity_excess_kg": EXPECTED_LAST_RETRY_EXCESS_KG,
            }

            try:
                _ = e38.evolve_from_parent(
                    parent=accepted_parent,
                    dt_days=original_last_dt,
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
                    "original_step1475_last_retry_unexpectedly_accepted"
                )
            except r2.GateError as exc:
                if EXPECTED_FAILURE_TOKEN not in str(exc):
                    raise
                reproduced_excess = parse_capacity_excess(exc)
                original_failure_record["actual_exception"] = repr(exc)
                original_failure_record[
                    "actual_capacity_excess_kg"
                ] = reproduced_excess
                gate(
                    "original_last_retry_excess_reproduced",
                    abs(
                        reproduced_excess
                        - EXPECTED_LAST_RETRY_EXCESS_KG
                    )
                    <= 1.0e-12,
                    reproduced_excess,
                )

            failed_stage = "capacity_aware_step1475_repair"

            original_mapback = (
                e37a.map_control_volume_increment_to_grid
            )
            controller_records: list[dict[str, Any]] = []
            context = {
                "active_dt_days": nominal_dt_days,
                "attempt": 0,
            }

            def capacity_aware_mapback(
                r2_local: Any,
                parent_grid_saturation: np.ndarray,
                old_cv_saturation: np.ndarray,
                new_cv_saturation: np.ndarray,
                old_cv_mass: np.ndarray,
                new_cv_mass: np.ndarray,
                geometry_local: dict[str, np.ndarray],
                pressure_psi_local: np.ndarray,
                p_ref_gas_pa_local: float,
                cell_pore_volume_m3_local: float,
                target_final_mass_kg: float,
            ) -> dict[str, Any]:
                record = preflight_mapback_capacity(
                    r2=r2_local,
                    e37a=e37a,
                    parent_grid_saturation=parent_grid_saturation,
                    old_cv_saturation=old_cv_saturation,
                    new_cv_saturation=new_cv_saturation,
                    old_cv_mass=old_cv_mass,
                    new_cv_mass=new_cv_mass,
                    geometry=geometry_local,
                    pressure_psi=pressure_psi_local,
                    p_ref_gas_pa=p_ref_gas_pa_local,
                    cell_pore_volume_m3=cell_pore_volume_m3_local,
                    target_final_mass_kg=target_final_mass_kg,
                    active_dt_days=float(
                        context["active_dt_days"]
                    ),
                )
                record["controller_attempt"] = int(
                    context["attempt"]
                )

                if record.get("native_failure_required"):
                    controller_records.append(
                        {
                            **record,
                            "controller_action":
                            "DELEGATE_TO_FROZEN_NATIVE_FAILURE",
                        }
                    )
                    return original_mapback(
                        r2_local,
                        parent_grid_saturation,
                        old_cv_saturation,
                        new_cv_saturation,
                        old_cv_mass,
                        new_cv_mass,
                        geometry_local,
                        pressure_psi_local,
                        p_ref_gas_pa_local,
                        cell_pore_volume_m3_local,
                        target_final_mass_kg,
                    )

                if not record[
                    "candidate_is_capacity_admissible"
                ]:
                    recommended = float(
                        record["recommended_dt_days"]
                    )
                    if (
                        not np.isfinite(recommended)
                        or recommended <= 0.0
                        or recommended
                        >= float(context["active_dt_days"])
                    ):
                        raise GateError(
                            "capacity_controller_no_positive_"
                            "strictly_smaller_timestep:"
                            f"{recommended}:"
                            f"{context['active_dt_days']}"
                        )

                    controller_records.append(
                        {
                            **record,
                            "controller_action":
                            "REJECT_AND_RETRY_AT_CAPACITY_BOUND",
                        }
                    )
                    raise MapbackCapacityReject(
                        controller_records[-1]
                    )

                controller_records.append(
                    {
                        **record,
                        "controller_action":
                        "ALLOW_FROZEN_E37A_MAPBACK",
                    }
                )
                return original_mapback(
                    r2_local,
                    parent_grid_saturation,
                    old_cv_saturation,
                    new_cv_saturation,
                    old_cv_mass,
                    new_cv_mass,
                    geometry_local,
                    pressure_psi_local,
                    p_ref_gas_pa_local,
                    cell_pore_volume_m3_local,
                    target_final_mass_kg,
                )

            repaired_result = None
            repaired_dt_days = nominal_dt_days
            capacity_adjustments = 0

            e37a.map_control_volume_increment_to_grid = (
                capacity_aware_mapback
            )
            try:
                for attempt in range(
                    MAX_CAPACITY_ADJUSTMENTS + 1
                ):
                    context["attempt"] = attempt
                    context["active_dt_days"] = (
                        repaired_dt_days
                    )
                    try:
                        repaired_result = e38.evolve_from_parent(
                            parent=accepted_parent,
                            dt_days=repaired_dt_days,
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
                        break

                    except MapbackCapacityReject as exc:
                        capacity_adjustments += 1
                        repaired_dt_days = float(
                            exc.record[
                                "recommended_dt_days"
                            ]
                        )
                        if (
                            capacity_adjustments
                            > MAX_CAPACITY_ADJUSTMENTS
                        ):
                            raise GateError(
                                "capacity_adjustment_budget_exhausted"
                            )

                    except (
                        e37a.TrialReject,
                        r2.GateError,
                    ) as exc:
                        raise GateError(
                            "unexpected_non_mapback_failure_during_"
                            f"capacity_repair:{repr(exc)}"
                        )
            finally:
                e37a.map_control_volume_increment_to_grid = (
                    original_mapback
                )

            gate(
                "repaired_step1475_result_created",
                repaired_result is not None,
            )
            gate(
                "capacity_controller_adjusted_at_least_once",
                capacity_adjustments >= 1,
                capacity_adjustments,
            )
            gate(
                "capacity_controller_within_budget",
                capacity_adjustments
                <= MAX_CAPACITY_ADJUSTMENTS,
                capacity_adjustments,
            )

            reject_records = [
                r
                for r in controller_records
                if r.get("controller_action")
                == "REJECT_AND_RETRY_AT_CAPACITY_BOUND"
            ]
            allow_records = [
                r
                for r in controller_records
                if r.get("controller_action")
                == "ALLOW_FROZEN_E37A_MAPBACK"
            ]
            gate(
                "controller_has_reject_and_final_allow",
                len(reject_records) >= 1
                and len(allow_records) == 1,
                f"{len(reject_records)}:{len(allow_records)}",
            )

            first_reject = reject_records[0]
            final_allow = allow_records[-1]

            gate(
                "first_capacity_limiter_cell_matches_diagnosis",
                tuple(
                    first_reject[
                        "upper_limiting_cell_zero_based"
                    ]
                )
                == EXPECTED_OFFENDING_CELL_ZERO_BASED,
                first_reject[
                    "upper_limiting_cell_zero_based"
                ],
            )
            gate(
                "first_capacity_bound_beats_old_retry8",
                float(
                    first_reject["recommended_dt_days"]
                )
                < original_last_dt,
                first_reject["recommended_dt_days"],
            )
            gate(
                "final_preflight_capacity_admissible",
                final_allow[
                    "candidate_is_capacity_admissible"
                ]
                is True,
                final_allow["max_capacity_excess_kg"],
            )
            gate(
                "final_preflight_strict_guard_below_ceiling",
                float(
                    final_allow["max_capacity_excess_kg"]
                )
                <= 0.0,
                final_allow["max_capacity_excess_kg"],
            )

            result = repaired_result
            child = e41.apply_e41_state_semantics(
                result["child"],
                accepted_parent,
                canonical_breakthrough_time_days=scalar(
                    parent["breakthrough_time_days"]
                ),
                observation_reached=False,
            )
            child[
                "current_producer_co2_gas_cut"
            ] = np.asarray(
                result["child_cut"],
                dtype=np.float64,
            )
            child[
                "last_CV_transport_mass_residual_kg"
            ] = np.asarray(
                result["transport_residual_kg"],
                dtype=np.float64,
            )
            child[
                "last_CV_to_grid_transfer_residual_kg"
            ] = np.asarray(
                result["transfer_residual_kg"],
                dtype=np.float64,
            )
            child[
                "last_grid_mapback_ledger_residual_kg"
            ] = np.asarray(
                result["mapback_ledger_residual_kg"],
                dtype=np.float64,
            )
            child[
                "last_grid_to_CV_sampling_closure_kg"
            ] = np.asarray(
                result["post_sample_closure_kg"],
                dtype=np.float64,
            )

            # R2 metadata; no physics state is replaced or rescaled.
            child[
                "V16E41R2_capacity_aware_mapback_timestep_repair"
            ] = np.asarray(True, dtype=bool)
            child[
                "V16E41R2_parent_step_index"
            ] = np.asarray(
                EXPECTED_PARENT_STEP,
                dtype=np.int64,
            )
            child[
                "V16E41R2_nominal_trial_dt_days"
            ] = np.asarray(
                nominal_dt_days,
                dtype=np.float64,
            )
            child[
                "V16E41R2_accepted_dt_days"
            ] = np.asarray(
                repaired_dt_days,
                dtype=np.float64,
            )
            child[
                "V16E41R2_capacity_adjustments"
            ] = np.asarray(
                capacity_adjustments,
                dtype=np.int64,
            )
            child[
                "V16E41R2_capacity_guard_multiplier"
            ] = np.asarray(
                CAPACITY_GUARD_MULTIPLIER,
                dtype=np.float64,
            )
            child[
                "V16E41R2_mapback_spatial_operator_modified"
            ] = np.asarray(False, dtype=bool)
            child[
                "V16E41R2_capillary_solver_modified"
            ] = np.asarray(False, dtype=bool)

            failed_stage = "repaired_step1475_validation"

            child_step = int_scalar(
                child["accepted_step_index"]
            )
            child_time = scalar(
                child["physical_time_days"]
            )
            child_sat = np.asarray(
                child["transport_saturation"],
                dtype=np.float64,
            )

            gate(
                "repaired_child_step1475_exact",
                child_step == EXPECTED_TARGET_STEP,
                child_step,
            )
            gate(
                "repaired_child_time_forward",
                child_time > accepted_parent_time,
                child_time,
            )
            gate(
                "repaired_child_time_matches_accepted_dt",
                abs(
                    child_time
                    - (
                        accepted_parent_time
                        + repaired_dt_days
                    )
                )
                <= 1.0e-12,
                child_time,
            )
            gate(
                "repaired_dt_positive",
                repaired_dt_days > 0.0,
                repaired_dt_days,
            )
            gate(
                "repaired_dt_below_old_retry8",
                repaired_dt_days < original_last_dt,
                repaired_dt_days,
            )
            gate(
                "repaired_saturation_lower_bound",
                float(np.min(child_sat))
                >= r2.BACKGROUND_SATURATION - 1.0e-12,
                float(np.min(child_sat)),
            )
            gate(
                "repaired_saturation_upper_bound",
                float(np.max(child_sat))
                <= r2.INJECTED_BOUNDARY_SATURATION
                + 1.0e-12,
                float(np.max(child_sat)),
            )
            gate(
                "capillary_external_mass_zero_within_roundoff",
                abs(
                    float(
                        result[
                            "capillary_external_mass_change_kg"
                        ]
                    )
                )
                <= max(
                    1.0e-6,
                    1.0e-10
                    * max(
                        abs(
                            float(
                                result[
                                    "final_stored_mass_kg"
                                ]
                            )
                        ),
                        1.0,
                    ),
                ),
                result[
                    "capillary_external_mass_change_kg"
                ],
            )

            injected_expected = (
                INJECTOR_MASS_RATE_KG_DAY
                * repaired_dt_days
            )
            gate(
                "fixed_rate_injected_mass_exact",
                abs(
                    float(result["injected_mass_kg"])
                    - injected_expected
                )
                <= max(
                    1.0e-6,
                    1.0e-12
                    * max(abs(injected_expected), 1.0),
                ),
                result["injected_mass_kg"],
            )

            parent_stored = scalar(
                accepted_parent[
                    "stored_co2_mass_current_kg"
                ]
            )
            step_ledger = (
                float(result["final_stored_mass_kg"])
                - parent_stored
                - float(result["injected_mass_kg"])
                + float(result["produced_mass_kg"])
            )
            gate(
                "repaired_step_component_mass_closure",
                abs(step_ledger)
                <= max(
                    1.0e-6,
                    1.0e-10
                    * max(
                        abs(
                            float(
                                result[
                                    "final_stored_mass_kg"
                                ]
                            )
                        ),
                        1.0,
                    ),
                ),
                step_ledger,
            )

            gate(
                "source_local_closure_still_zero",
                abs(
                    scalar(
                        child["last_source_local_added_mass_kg"]
                    )
                )
                <= 0.0,
                scalar(
                    child["last_source_local_added_mass_kg"]
                ),
            )
            gate(
                "100d_not_reached",
                child_time < 100.0,
                child_time,
            )
            gate(
                "100d_canonical_flag_false",
                not bool_scalar(
                    child[
                        "V16E41_canonical_100d_observation_state"
                    ]
                ),
            )

            child_bytes = deterministic_npz_bytes(child)
            child_sha = hashlib.sha256(
                child_bytes
            ).hexdigest()

            mass_ledger_rows = [
                {
                    "parent_step": EXPECTED_PARENT_STEP,
                    "child_step": EXPECTED_TARGET_STEP,
                    "parent_time_days": accepted_parent_time,
                    "child_time_days": child_time,
                    "accepted_dt_days": repaired_dt_days,
                    "accepted_dt_seconds": repaired_dt_days
                    * DAY_TO_S,
                    "parent_stored_CO2_mass_kg": parent_stored,
                    "injected_CO2_mass_kg": float(
                        result["injected_mass_kg"]
                    ),
                    "produced_CO2_mass_kg": float(
                        result["produced_mass_kg"]
                    ),
                    "child_stored_CO2_mass_kg": float(
                        result["final_stored_mass_kg"]
                    ),
                    "step_mass_residual_kg": step_ledger,
                    "CV_transport_mass_residual_kg": float(
                        result["transport_residual_kg"]
                    ),
                    "CV_to_grid_transfer_residual_kg": float(
                        result["transfer_residual_kg"]
                    ),
                    "grid_mapback_ledger_residual_kg": float(
                        result["mapback_ledger_residual_kg"]
                    ),
                    "grid_to_CV_sampling_closure_kg": float(
                        result["post_sample_closure_kg"]
                    ),
                    "capillary_external_mass_change_kg": float(
                        result[
                            "capillary_external_mass_change_kg"
                        ]
                    ),
                    "source_local_added_mass_kg": 0.0,
                }
            ]

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "diagnostic_basis":
                    "V16E-41-R1-R2-R1 MAPBACK_CAPACITY_FAILURE_ONLY",
                "repair_scope":
                    "capacity-aware timestep selection before frozen E37A map-back inversion",
                "accepted_parent_step_index":
                    EXPECTED_PARENT_STEP,
                "accepted_parent_time_days":
                    accepted_parent_time,
                "accepted_parent_state_sha256":
                    accepted_parent_sha,
                "target_step": EXPECTED_TARGET_STEP,
                "original_failure_reproduced": True,
                "original_formal_retry8_dt_days":
                    original_last_dt,
                "original_formal_retry8_dt_seconds":
                    original_last_dt * DAY_TO_S,
                "original_formal_retry8_capacity_excess_kg":
                    EXPECTED_LAST_RETRY_EXCESS_KG,
                "nominal_dt_days": nominal_dt_days,
                "capacity_guard_multiplier":
                    CAPACITY_GUARD_MULTIPLIER,
                "capacity_adjustments":
                    capacity_adjustments,
                "first_capacity_bound_raw_fraction":
                    first_reject[
                        "raw_admissible_fraction"
                    ],
                "first_capacity_bound_dt_days":
                    first_reject[
                        "recommended_dt_days"
                    ],
                "first_capacity_bound_dt_seconds":
                    first_reject[
                        "recommended_dt_seconds"
                    ],
                "first_capacity_limiter_cell_zero_based":
                    first_reject[
                        "upper_limiting_cell_zero_based"
                    ],
                "accepted_repaired_dt_days":
                    repaired_dt_days,
                "accepted_repaired_dt_seconds":
                    repaired_dt_days * DAY_TO_S,
                "accepted_repaired_time_days":
                    child_time,
                "accepted_repaired_step_index":
                    child_step,
                "accepted_repaired_state_sha256":
                    child_sha,
                "final_preflight_max_capacity_excess_kg":
                    final_allow[
                        "max_capacity_excess_kg"
                    ],
                "final_preflight_capacity_tolerance_kg":
                    final_allow[
                        "capacity_tolerance_kg"
                    ],
                "final_preflight_capacity_guard_kg":
                    final_allow[
                        "capacity_guard_kg"
                    ],
                "injected_CO2_mass_kg":
                    float(result["injected_mass_kg"]),
                "produced_CO2_mass_kg":
                    float(result["produced_mass_kg"]),
                "stored_CO2_mass_kg":
                    float(result["final_stored_mass_kg"]),
                "step_mass_residual_kg":
                    step_ledger,
                "producer_CO2_gas_cut":
                    float(result["child_cut"]),
                "mapback_spatial_operator_modified": False,
                "EOS_inversion_modified": False,
                "capillary_solver_modified": False,
                "CV_transport_modified": False,
                "source_local_mass_closure_used": False,
                "mass_clipping_used": False,
                "plume_rescaling_used": False,
                "100d_state_created": False,
                "legacy_regression_started": False,
                "next_milestone": NEXT,
            }

            r3_design = {
                "milestone": NEXT,
                "restart_state_filename": STATE_NAME,
                "restart_state_sha256": child_sha,
                "restart_step_index": child_step,
                "restart_time_days": child_time,
                "controller":
                    "capacity-aware CV-to-grid map-back timestep preflight",
                "controller_guard_multiplier":
                    CAPACITY_GUARD_MULTIPLIER,
                "preserve_unchanged": [
                    "E37A control-volume aligned spatial map-back",
                    "R2 nonlinear EOS mass-to-saturation inversion",
                    "R2 conservative no-flow capillary redistribution",
                    "E38 component-mass state transition",
                    "fixed-rate 500 tonnes/day injection",
                ],
                "R3_objective":
                    "continue repaired production rollout to exactly 100 days; only after the 100d checkpoint passes, run diagnostic regression against immutable V16E18-R1 legacy numerical candidate",
                "no_100d_claim_from_R2": True,
            }

            files = {
                STATE_NAME: child_bytes,
                "PAD_Stream_V16E41R2_Summary.json":
                    json_bytes(summary),
                "V16E41R2_Original_Failure_Reproduction.json":
                    json_bytes(original_failure_record),
                "V16E41R2_Capacity_Controller_Audit.csv":
                    csv_bytes(controller_records),
                "V16E41R2_Repaired_Transition_Mass_Ledger.csv":
                    csv_bytes(mass_ledger_rows),
                "V16E41R3_Rollout_Design_Input.json":
                    json_bytes(r3_design),
                "V16E41R2_Final_Gate_Matrix.csv":
                    csv_bytes(
                        [
                            {"gate": k, **v}
                            for k, v in gates.items()
                        ]
                    ),
            }

            failed_stage = "immutability_and_closure"

            # All predecessor files and all frozen source runners must still be
            # byte-identical after the repaired transition.
            source_modifications = {}
            for key in [
                "R2",
                "E36",
                "E37A",
                "E37B",
                "E38",
                "E40",
                "E41",
                "R1R2R1",
            ]:
                source_modifications[key] = (
                    sha256_file(paths[key])
                    != provenance_sha_before[
                        f"source_{key}"
                    ]
                )

            provenance_modifications = {}
            for key, p in provenance_files.items():
                provenance_modifications[key] = (
                    sha256_file(p)
                    != provenance_sha_before[key]
                )

            gate(
                "all_frozen_sources_unmodified",
                not any(source_modifications.values()),
                source_modifications,
            )
            gate(
                "all_predecessor_provenance_unmodified",
                not any(
                    provenance_modifications.values()
                ),
                provenance_modifications,
            )

            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed":
                    all(
                        v["passed"]
                        for v in gates.values()
                    ),
                "gate_count": len(gates),
                "accepted_state_filename": STATE_NAME,
                "accepted_state_sha256": child_sha,
                "accepted_step_index": child_step,
                "accepted_time_days": child_time,
                "accepted_dt_days": repaired_dt_days,
                "capacity_adjustments":
                    capacity_adjustments,
                "first_capacity_limiter_cell_zero_based":
                    first_reject[
                        "upper_limiting_cell_zero_based"
                    ],
                "mapback_spatial_operator_modified": False,
                "EOS_inversion_modified": False,
                "capillary_solver_modified": False,
                "CV_transport_modified": False,
                "mass_clipping_used": False,
                "plume_rescaling_used": False,
                "source_local_mass_closure_used": False,
                "100d_state_created": False,
                "legacy_regression_started": False,
                "frozen_source_modifications":
                    source_modifications,
                "predecessor_provenance_modifications":
                    provenance_modifications,
                "next_milestone": NEXT,
            }
            files[
                "V16E41R2_Final_Closure.json"
            ] = json_bytes(closure)

            immutable_publish(out, files)

            manifest_rows = []
            for p in sorted(out.iterdir()):
                if (
                    p.is_file()
                    and p.name
                    != "V16E41R2_Artifact_Manifest.csv"
                ):
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
                    "V16E41R2_Artifact_Manifest.csv":
                        csv_bytes(manifest_rows)
                },
            )

            print("\n" + "=" * 146)
            print("PAD-Stream V16E-41-R2: PASS")
            print("=" * 146)
            print(f"{'Status':50}: {STATUS}")
            print(
                f"{'Parent step / time':50}: "
                f"{EXPECTED_PARENT_STEP} / "
                f"{accepted_parent_time:.15g} d"
            )
            print(
                f"{'Original retry-8 failure excess':50}: "
                f"{EXPECTED_LAST_RETRY_EXCESS_KG:.15e} kg"
            )
            print(
                f"{'Capacity adjustments':50}: "
                f"{capacity_adjustments}"
            )
            print(
                f"{'First limiter cell (k,j,i)':50}: "
                f"{tuple(first_reject['upper_limiting_cell_zero_based'])}"
            )
            print(
                f"{'First capacity-bound dt':50}: "
                f"{float(first_reject['recommended_dt_days']):.15g} d "
                f"({float(first_reject['recommended_dt_seconds']):.15g} s)"
            )
            print(
                f"{'Accepted repaired dt':50}: "
                f"{repaired_dt_days:.15g} d "
                f"({repaired_dt_days * DAY_TO_S:.15g} s)"
            )
            print(
                f"{'Accepted repaired time':50}: "
                f"{child_time:.15g} d"
            )
            print(
                f"{'Accepted state SHA-256':50}: "
                f"{child_sha}"
            )
            print(
                f"{'Map-back spatial operator modified':50}: False"
            )
            print(
                f"{'Capillary solver modified':50}: False"
            )
            print(
                f"{'100-day state created':50}: False"
            )
            print(
                f"{'Legacy regression started':50}: False"
            )
            print(f"{'Output':50}: {out}")
            print(f"{'Next':50}: {NEXT}")

            return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status":
                "CAPACITY_AWARE_CONSERVATIVE_MAPBACK_TIMESTEP_REPAIR_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        p = blocked / "V16E41R2_Blocked_Repair.json"
        if p.exists() and p.read_bytes() != json_bytes(report):
            p = blocked / (
                "V16E41R2_Blocked_Repair_"
                + hashlib.sha256(
                    json_bytes(report)
                ).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(json_bytes(report))

        print("\n" + "=" * 146)
        print("PAD-Stream V16E-41-R2: BLOCKED")
        print("=" * 146)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )
    p.add_argument(
        "--self-test",
        action="store_true",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
