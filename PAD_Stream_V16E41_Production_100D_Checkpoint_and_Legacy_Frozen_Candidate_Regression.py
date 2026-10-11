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


MILESTONE = "V16E-41"
STATUS = "PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION_COMPLETED"
NEXT = "V16E-42 - Post-100-Day Long-Horizon Fixed-Observation Rollout / 150-Day Checkpoint"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
BACKGROUND_SATURATION = 0.20
BREAKTHROUGH_GAS_CUT = 1.0e-4
TARGET_OBSERVATION_DAY = 100.0
NEXT_OBSERVATION_DAY = 150.0
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
CO2_RHO_REF_KG_M3 = 700.0
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0
EXPECTED_STREAMLINES = 1078
EXPECTED_FACES = 201
EXPECTED_CVS = 200
MAX_TRIAL_RETRIES = 8
RETRY_FACTOR = 0.5
MAX_ACCEPTED_TRANSITIONS = 2500
PROGRESS_EVERY = 100
SPARSE_SNAPSHOT_THRESHOLDS_DAYS = (75.0, 90.0, 100.0)

EXPECTED_E38_BT_TIME_DAYS = 23.380258876143085
EXPECTED_E40_TIME_DAYS = 60.0
EXPECTED_E40_STEP = 1222

LEGACY_EXPECTED_SUPPORTED = 20462
LEGACY_EXPECTED_UNSUPPORTED = 17038
LEGACY_EXPECTED_MIN = 0.20
LEGACY_EXPECTED_MAX = 0.78499960534060065
LEGACY_FREEZE_STATUS = "V16E18_R1_FULL_GRID_CANDIDATE_FREEZE_PASS"
LEGACY_FROZEN_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

ACTIVE_INCREMENT_THRESHOLD = 1.0e-8
VISIBLE_INCREMENT_THRESHOLD = 1.0e-4

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
E37A_EXPECTED_STATUS = "CONTROL_VOLUME_ALIGNED_CONSERVATIVE_TRANSFER_VALIDATED"

E37B_RUNNER = "PAD_Stream_V16E37B_Extended_SGSim_Runtime_Rollout_and_First_Fixed_Observation_Checkpoint.py"
E37B_RUNNER_SHA256 = "8abec0348cb683e7805fd5b847d3f24b88b855edd3386914a6aad9a3a1d87471"
E37B_BLOCKED_REL = Path("provenance/hybrid_dp/V16E37B_BLOCKED_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT")
E37B_BRACKET_REPORT = "V16E37B_Blocked_Breakthrough_Bracket.json"

E38_RUNNER = "PAD_Stream_V16E38_Breakthrough_Event_Refinement_and_Canonical_BT_State.py"
E38_RUNNER_SHA256 = "6ed0ccb552353e25ea5bc6bd4ebc562469d2049b2e81da73e0640eebf2f7b478"

E40_RUNNER = "PAD_Stream_V16E40_Post_Breakthrough_SGSim_Rollout_and_Second_60d_Observation_Checkpoint.py"
E40_RUNNER_SHA256 = "27fe993a140ddfaa919f81124f4ef53ed4058c3b37000b0911810969325b8a28"
E40_REL = Path("provenance/hybrid_dp/V16E40_POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT")
E40_SUMMARY = "PAD_Stream_V16E40_Summary.json"
E40_CLOSURE = "V16E40_Final_Closure.json"
E40_CANONICAL = "V16E40_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0060d.npz"
E40_EXPECTED_STATUS = "POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT_VALIDATED"

LEGACY_REL = Path("provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE")
LEGACY_SUMMARY = "PAD_Stream_V16E18_R1_Summary.json"
LEGACY_MANIFEST = "V16E18_R1_Full_Grid_Freeze_Manifest.json"
LEGACY_SUBDIR = "frozen_full_grid"
LEGACY_FILE = "V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"

OUT_REL = Path("provenance/hybrid_dp/V16E41_PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E41_BLOCKED_PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION")


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def arr_sha(a: np.ndarray) -> str:
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


def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))


def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))


def bool_scalar(a: Any) -> bool:
    return bool(np.asarray(a).reshape(()))


def max_abs(values: list[float]) -> float:
    return max([abs(float(v)) for v in values] + [0.0])


def apply_e41_state_semantics(
    child: dict[str, np.ndarray],
    parent: dict[str, np.ndarray],
    *,
    canonical_breakthrough_time_days: float,
    observation_reached: bool,
) -> dict[str, np.ndarray]:
    out = {k: np.asarray(v).copy() for k, v in child.items()}
    new_time = scalar(out["physical_time_days"])

    out["breakthrough_reached"] = np.asarray(True, dtype=bool)
    out["breakthrough_time_days"] = np.asarray(canonical_breakthrough_time_days, dtype=np.float64)
    out["time_since_breakthrough_days"] = np.asarray(
        max(0.0, new_time - canonical_breakthrough_time_days), dtype=np.float64
    )
    out["E38_breakthrough_event_refined"] = np.asarray(True, dtype=bool)
    out["V16E38_canonical_breakthrough_state"] = np.asarray(False, dtype=bool)

    out["first_fixed_observation_checkpoint_reached"] = np.asarray(True, dtype=bool)
    out["second_fixed_observation_checkpoint_reached"] = np.asarray(True, dtype=bool)
    out["third_fixed_observation_checkpoint_reached"] = np.asarray(observation_reached, dtype=bool)
    out["E40_post_breakthrough_rollout_active"] = np.asarray(False, dtype=bool)
    out["E41_100d_production_rollout_active"] = np.asarray(True, dtype=bool)
    out["last_source_local_added_mass_kg"] = np.asarray(0.0, dtype=np.float64)

    if observation_reached:
        out["physical_time_days"] = np.asarray(TARGET_OBSERVATION_DAY, dtype=np.float64)
        out["time_since_breakthrough_days"] = np.asarray(
            TARGET_OBSERVATION_DAY - canonical_breakthrough_time_days, dtype=np.float64
        )
        out["last_fixed_observation_day"] = np.asarray(TARGET_OBSERVATION_DAY, dtype=np.float64)
        out["observation_cursor_index"] = np.asarray(
            int_scalar(parent["observation_cursor_index"]) + 1, dtype=np.int64
        )
        out["next_fixed_observation_day"] = np.asarray(NEXT_OBSERVATION_DAY, dtype=np.float64)
        out["V16E41_canonical_100d_observation_state"] = np.asarray(True, dtype=bool)
    else:
        out["last_fixed_observation_day"] = np.asarray(
            parent["last_fixed_observation_day"], dtype=np.float64
        )
        out["observation_cursor_index"] = np.asarray(
            parent["observation_cursor_index"], dtype=np.int64
        )
        out["next_fixed_observation_day"] = np.asarray(
            parent["next_fixed_observation_day"], dtype=np.float64
        )
        out["V16E41_canonical_100d_observation_state"] = np.asarray(False, dtype=bool)
    return out


def field_error_metrics(
    new: np.ndarray,
    legacy: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict[str, float | int | bool]:
    a = np.asarray(new, dtype=np.float64)
    b = np.asarray(legacy, dtype=np.float64)
    if a.shape != b.shape:
        raise GateError(f"regression_shape_mismatch:{a.shape}:{b.shape}")

    if mask is None:
        aa = a.ravel()
        bb = b.ravel()
    else:
        m = np.asarray(mask, dtype=bool)
        if m.shape != a.shape:
            raise GateError(f"regression_mask_shape_mismatch:{m.shape}:{a.shape}")
        aa = a[m]
        bb = b[m]

    if aa.size == 0:
        raise GateError("regression_empty_metric_partition")

    d = aa - bb
    absd = np.abs(d)
    denom = float(np.linalg.norm(bb - BACKGROUND_SATURATION))
    num = float(np.linalg.norm(d))
    std_a = float(np.std(aa))
    std_b = float(np.std(bb))
    corr = (
        float(np.corrcoef(aa, bb)[0, 1])
        if std_a > 0.0 and std_b > 0.0
        else float("nan")
    )

    return {
        "count": int(aa.size),
        "bitwise_equal": bool(np.array_equal(aa, bb)),
        "L1_mean_abs": float(np.mean(absd)),
        "L2_rms": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(absd)),
        "signed_mean_bias_new_minus_legacy": float(np.mean(d)),
        "relative_L2_vs_legacy_incremental_norm": (
            float(num / denom) if denom > 0.0 else float("nan")
        ),
        "pearson_correlation": corr,
        "new_mean": float(np.mean(aa)),
        "legacy_mean": float(np.mean(bb)),
        "new_min": float(np.min(aa)),
        "new_max": float(np.max(aa)),
        "legacy_min": float(np.min(bb)),
        "legacy_max": float(np.max(bb)),
    }


def overlap_metrics(
    new_sat: np.ndarray,
    legacy_sat: np.ndarray,
    incremental_threshold: float,
) -> dict[str, float | int]:
    new_mask = (
        np.asarray(new_sat, dtype=np.float64) - BACKGROUND_SATURATION
        > incremental_threshold
    )
    legacy_mask = (
        np.asarray(legacy_sat, dtype=np.float64) - BACKGROUND_SATURATION
        > incremental_threshold
    )
    intersection = int(np.sum(new_mask & legacy_mask))
    union = int(np.sum(new_mask | legacy_mask))
    new_count = int(np.sum(new_mask))
    legacy_count = int(np.sum(legacy_mask))

    return {
        "incremental_threshold": float(incremental_threshold),
        "new_cells": new_count,
        "legacy_cells": legacy_count,
        "intersection_cells": intersection,
        "union_cells": union,
        "intersection_over_union": float(intersection / union) if union > 0 else 1.0,
        "intersection_fraction_of_new": (
            float(intersection / new_count) if new_count > 0 else 1.0
        ),
        "intersection_fraction_of_legacy": (
            float(intersection / legacy_count) if legacy_count > 0 else 1.0
        ),
    }


def saturation_increment_centroid_m(sat: np.ndarray) -> tuple[float, float, float]:
    s = np.asarray(sat, dtype=np.float64)
    w = np.clip(s - BACKGROUND_SATURATION, 0.0, None)
    total = float(np.sum(w))
    if total <= 0.0:
        return (float("nan"), float("nan"), float("nan"))

    dz = 4.0 * FT_TO_M
    dy = 20.0 * FT_TO_M
    dx = 20.0 * FT_TO_M
    z = (np.arange(EXPECTED_GRID[0], dtype=np.float64) + 0.5) * dz
    y = (np.arange(EXPECTED_GRID[1], dtype=np.float64) + 0.5) * dy
    x = (np.arange(EXPECTED_GRID[2], dtype=np.float64) + 0.5) * dx
    zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")

    return (
        float(np.sum(w * xx) / total),
        float(np.sum(w * yy) / total),
        float(np.sum(w * zz) / total),
    )


def layerwise_regression_rows(
    new_sat: np.ndarray,
    legacy_sat: np.ndarray,
    legacy_supported_mask: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for k in range(EXPECTED_GRID[0]):
        n = np.asarray(new_sat[k], dtype=np.float64)
        l = np.asarray(legacy_sat[k], dtype=np.float64)
        m = np.asarray(legacy_supported_mask[k], dtype=bool)
        dn = np.clip(n - BACKGROUND_SATURATION, 0.0, None)
        dl = np.clip(l - BACKGROUND_SATURATION, 0.0, None)

        row = {
            "layer_index_1based": k + 1,
            "layer_center_z_ft": (k + 0.5) * 4.0,
            "new_mean_saturation": float(np.mean(n)),
            "legacy_mean_saturation": float(np.mean(l)),
            "mean_saturation_difference": float(np.mean(n - l)),
            "mean_abs_saturation_difference": float(np.mean(np.abs(n - l))),
            "max_abs_saturation_difference": float(np.max(np.abs(n - l))),
            "new_incremental_saturation_sum": float(np.sum(dn)),
            "legacy_incremental_saturation_sum": float(np.sum(dl)),
            "incremental_saturation_sum_difference": float(np.sum(dn) - np.sum(dl)),
            "new_active_cells_gt_1e-8": int(np.sum(dn > ACTIVE_INCREMENT_THRESHOLD)),
            "legacy_active_cells_gt_1e-8": int(np.sum(dl > ACTIVE_INCREMENT_THRESHOLD)),
            "new_visible_cells_gt_1e-4": int(np.sum(dn > VISIBLE_INCREMENT_THRESHOLD)),
            "legacy_visible_cells_gt_1e-4": int(np.sum(dl > VISIBLE_INCREMENT_THRESHOLD)),
            "legacy_supported_cells": int(np.sum(m)),
            "legacy_background_completed_cells": int(np.sum(~m)),
        }
        if np.any(m):
            ds = n[m] - l[m]
            row["supported_mean_abs_difference"] = float(np.mean(np.abs(ds)))
            row["supported_Linf_difference"] = float(np.max(np.abs(ds)))
        else:
            row["supported_mean_abs_difference"] = float("nan")
            row["supported_Linf_difference"] = float("nan")
        rows.append(row)

    return rows


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
        if float(z["physical_time_days"]) != TARGET_OBSERVATION_DAY:
            raise GateError("checkpoint_restart_time_not_exact_100d")
        if not np.array_equal(z["transport_saturation"], expected_sat):
            raise GateError("checkpoint_restart_saturation_not_byte_exact")
        if not bool(z["breakthrough_reached"]):
            raise GateError("checkpoint_restart_lost_breakthrough_flag")
        if abs(float(z["breakthrough_time_days"]) - expected_bt_time) > 1.0e-12:
            raise GateError("checkpoint_restart_breakthrough_time_changed")
        expected_since = TARGET_OBSERVATION_DAY - expected_bt_time
        if abs(float(z["time_since_breakthrough_days"]) - expected_since) > 1.0e-12:
            raise GateError("checkpoint_restart_time_since_breakthrough_mismatch")
        if not bool(z["first_fixed_observation_checkpoint_reached"]):
            raise GateError("checkpoint_restart_lost_30d_history")
        if not bool(z["second_fixed_observation_checkpoint_reached"]):
            raise GateError("checkpoint_restart_lost_60d_history")
        if not bool(z["third_fixed_observation_checkpoint_reached"]):
            raise GateError("checkpoint_restart_missing_100d_flag")
        if int(z["observation_cursor_index"]) != 3:
            raise GateError("checkpoint_restart_observation_cursor_not_3")
        if float(z["last_fixed_observation_day"]) != TARGET_OBSERVATION_DAY:
            raise GateError("checkpoint_restart_last_observation_not_100d")
        if float(z["next_fixed_observation_day"]) != NEXT_OBSERVATION_DAY:
            raise GateError("checkpoint_restart_next_observation_not_150d")
        if not bool(z["V16E41_canonical_100d_observation_state"]):
            raise GateError("checkpoint_restart_missing_E41_canonical_flag")
        if bool(z["injector_local_mass_closure_authorized"]):
            raise GateError("checkpoint_restart_authorizes_source_local_closure")
        if bool(z["injector_local_mass_closure_executed"]):
            raise GateError("checkpoint_restart_executed_source_local_closure")


def self_test() -> None:
    t = EXPECTED_E40_TIME_DAYS
    dt = 0.049123143364170854
    count = 0
    last_dt = None
    while t < TARGET_OBSERVATION_DAY - 1.0e-13:
        h = min(dt, TARGET_OBSERVATION_DAY - t)
        if h <= 0.0:
            raise RuntimeError("self_test_nonpositive_observation_clip")
        t += h
        if TARGET_OBSERVATION_DAY - t <= 1.0e-13:
            t = TARGET_OBSERVATION_DAY
        last_dt = h
        count += 1
        if count > 2500:
            raise RuntimeError("self_test_transition_budget_exceeded")

    if t != TARGET_OBSERVATION_DAY:
        raise RuntimeError("self_test_observation_not_exact")
    if count != 815:
        raise RuntimeError(f"self_test_expected_815_nominal_transitions:{count}")
    if abs(float(last_dt) - 0.013761301565523354) > 1.0e-12:
        raise RuntimeError(f"self_test_final_clip_mismatch:{last_dt}")

    a = np.array([[[0.2, 0.3], [0.2, 0.4]]], dtype=np.float64)
    b = np.array([[[0.2, 0.25], [0.2, 0.35]]], dtype=np.float64)
    m = np.array([[[True, True], [False, False]]], dtype=bool)
    whole = field_error_metrics(a, b)
    supported = field_error_metrics(a, b, m)
    background = field_error_metrics(a, b, ~m)
    if whole["count"] != 4 or supported["count"] != 2 or background["count"] != 2:
        raise RuntimeError("self_test_regression_partition_failed")
    if whole["bitwise_equal"]:
        raise RuntimeError("self_test_regression_false_equality")

    regression_accuracy_threshold_frozen = False
    if regression_accuracy_threshold_frozen:
        raise RuntimeError("self_test_illegal_regression_threshold")

    print("PAD-Stream V16E-41 100-day production/regression self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    trial_failures: list[dict[str, Any]] = []
    failed_stage: str | None = None

    e40_parent_sha_before: str | None = None
    e36_cache_sha_before: str | None = None
    e37b_bracket_sha_before: str | None = None
    legacy_sha_before: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 148)
        print(
            "PAD-Stream V16E-41 — Production 100-Day Checkpoint / "
            "Legacy Frozen-Candidate Regression"
        )
        print("=" * 148)
        print("Restart        : canonical V16E-40 60-day state")
        print("Target         : exact third fixed observation at 100.0 days")
        print(
            "Regression     : new production 100-day state vs immutable "
            "V16E18-R1 numerical candidate"
        )
        print(
            "Interpretation : legacy candidate is a frozen deployment input, "
            "not declared physical truth"
        )
        print(
            "Partitions     : whole grid + legacy-supported + "
            "legacy-background-completed cells"
        )
        print(
            "Acceptance     : physics/restart/conservation must pass; "
            "regression magnitude is diagnostic"
        )

        failed_stage = "source_and_provenance_binding"

        r2_path = root / R2_RUNNER
        e36_path = root / E36_RUNNER
        e37a_path = root / E37A_RUNNER
        e37b_path = root / E37B_RUNNER
        e38_path = root / E38_RUNNER
        e40_path = root / E40_RUNNER
        sg7a_path = root / SG7A
        sg7d_path = root / SG7D
        perm_path = root / SGSIM_PERM

        for p in [
            r2_path,
            e36_path,
            e37a_path,
            e37b_path,
            e38_path,
            e40_path,
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
            ("E40", e40_path, E40_RUNNER_SHA256),
        ]:
            actual = sha256_file(path)
            gate(f"{name}_runner_SHA_exact", actual == expected, actual)

        r2 = load_module(r2_path, "pad_stream_v16e41_r2")
        e36 = load_module(e36_path, "pad_stream_v16e41_e36")
        e37a = load_module(e37a_path, "pad_stream_v16e41_e37a")
        e37b = load_module(e37b_path, "pad_stream_v16e41_e37b")
        e38 = load_module(e38_path, "pad_stream_v16e41_e38")

        e40_dir = drive / E40_REL
        e40_summary_path = e40_dir / E40_SUMMARY
        e40_closure_path = e40_dir / E40_CLOSURE
        e40_parent_path = e40_dir / E40_CANONICAL

        e36_cache_path = drive / E36_REL / E36_CACHE
        e37b_bracket_path = drive / E37B_BLOCKED_REL / E37B_BRACKET_REPORT
        e37a_summary_path = drive / E37A_REL / E37A_SUMMARY

        legacy_dir = drive / LEGACY_REL
        legacy_summary_path = legacy_dir / LEGACY_SUMMARY
        legacy_manifest_path = legacy_dir / LEGACY_MANIFEST
        legacy_path = legacy_dir / LEGACY_SUBDIR / LEGACY_FILE

        for p in [
            e40_summary_path,
            e40_closure_path,
            e40_parent_path,
            e36_cache_path,
            e37b_bracket_path,
            e37a_summary_path,
            legacy_summary_path,
            legacy_manifest_path,
            legacy_path,
        ]:
            gate(f"provenance_exists_{p.name}", p.is_file(), p)

        e40_summary = load_json(e40_summary_path)
        e40_closure = load_json(e40_closure_path)
        e37a_summary = load_json(e37a_summary_path)
        legacy_summary = load_json(legacy_summary_path)
        legacy_manifest = load_json(legacy_manifest_path)

        gate(
            "E40_status_accepted",
            e40_summary.get("status") == E40_EXPECTED_STATUS,
            e40_summary.get("status"),
        )
        gate(
            "E40_E41_entry_ready",
            e40_summary.get("E41_frozen_100d_regression_entry_ready") is True,
        )
        gate(
            "E40_closure_status_accepted",
            e40_closure.get("status") == E40_EXPECTED_STATUS,
            e40_closure.get("status"),
        )
        gate(
            "E40_all_runtime_gates_passed",
            e40_closure.get("all_runtime_gates_passed") is True,
        )
        gate(
            "E37A_status_accepted",
            e37a_summary.get("status") == E37A_EXPECTED_STATUS,
            e37a_summary.get("status"),
        )

        gate(
            "legacy_summary_PASS",
            legacy_summary.get("status") == "PASS",
            legacy_summary.get("status"),
        )
        gate("legacy_candidate_frozen", legacy_summary.get("candidate_frozen") is True)
        gate(
            "legacy_full_grid_plume_not_authorized",
            legacy_summary.get("full_grid_plume_authorized") is False,
        )
        gate(
            "legacy_manifest_status_exact",
            legacy_manifest.get("status") == LEGACY_FREEZE_STATUS,
            legacy_manifest.get("status"),
        )
        gate(
            "legacy_manifest_candidate_frozen",
            legacy_manifest.get("candidate_frozen") is True,
        )
        gate(
            "legacy_manifest_physical_time_100d",
            float(legacy_manifest.get("physical_time_days", -1.0))
            == TARGET_OBSERVATION_DAY,
            legacy_manifest.get("physical_time_days"),
        )

        e40_parent_sha_before = sha256_file(e40_parent_path)
        e36_cache_sha_before = sha256_file(e36_cache_path)
        e37b_bracket_sha_before = sha256_file(e37b_bracket_path)
        legacy_sha_before = sha256_file(legacy_path)

        gate(
            "E40_parent_SHA_matches_closure",
            e40_parent_sha_before == e40_closure.get("checkpoint_state_sha256"),
            e40_parent_sha_before,
        )
        gate(
            "E36_cache_SHA_matches_E40_closure",
            e36_cache_sha_before == e40_closure.get("E36_certified_cache_sha256"),
            e36_cache_sha_before,
        )
        gate(
            "E37B_bracket_SHA_matches_E40_closure",
            e37b_bracket_sha_before
            == e40_closure.get("E37B_breakthrough_bracket_report_sha256"),
            e37b_bracket_sha_before,
        )
        gate(
            "legacy_frozen_SHA_exact",
            legacy_sha_before == LEGACY_FROZEN_SHA256,
            legacy_sha_before,
        )
        gate(
            "legacy_SHA_matches_manifest",
            legacy_sha_before == legacy_manifest.get("authoritative_frozen_sha256"),
            legacy_manifest.get("authoritative_frozen_sha256"),
        )

        parent = load_npz(e40_parent_path)
        cache = load_npz(e36_cache_path)

        initial_step = int_scalar(parent["accepted_step_index"])
        initial_time = scalar(parent["physical_time_days"])
        initial_cut = scalar(parent["current_producer_co2_gas_cut"])
        canonical_bt_time = scalar(parent["breakthrough_time_days"])

        gate("E40_restart_step_exact", initial_step == EXPECTED_E40_STEP, initial_step)
        gate(
            "E40_restart_time_exact_60d",
            initial_time == EXPECTED_E40_TIME_DAYS,
            initial_time,
        )
        gate("E40_restart_breakthrough_true", bool_scalar(parent["breakthrough_reached"]))
        gate(
            "E40_restart_breakthrough_time_exact",
            abs(canonical_bt_time - EXPECTED_E38_BT_TIME_DAYS) <= 1.0e-12,
            canonical_bt_time,
        )
        gate(
            "E40_restart_first_observation_history_true",
            bool_scalar(parent["first_fixed_observation_checkpoint_reached"]),
        )
        gate(
            "E40_restart_second_observation_history_true",
            bool_scalar(parent["second_fixed_observation_checkpoint_reached"]),
        )
        gate(
            "E40_restart_cursor_2_last60_next100",
            int_scalar(parent["observation_cursor_index"]) == 2
            and scalar(parent["last_fixed_observation_day"]) == 60.0
            and scalar(parent["next_fixed_observation_day"]) == 100.0,
            (
                f"{int_scalar(parent['observation_cursor_index'])}:"
                f"{scalar(parent['last_fixed_observation_day'])}:"
                f"{scalar(parent['next_fixed_observation_day'])}"
            ),
        )
        gate(
            "E40_restart_CV_aligned",
            bool_scalar(parent["control_volume_aligned_transfer_active"])
            and bool_scalar(parent["component_mass_primary_conserved_variable"]),
        )
        gate(
            "E40_restart_source_local_closure_forbidden",
            not bool_scalar(parent["injector_local_mass_closure_authorized"])
            and not bool_scalar(parent["injector_local_mass_closure_executed"])
            and abs(scalar(parent["last_source_local_added_mass_kg"])) <= 1.0e-12,
        )
        gate(
            "E36_cache_reference_mobility_scope",
            bool_scalar(cache["reuse_scope_reference_mobility_only"]),
        )

        failed_stage = "legacy_candidate_schema_binding"

        with np.load(legacy_path, allow_pickle=False) as z:
            required_legacy = [
                "saturation_grid_full_float64",
                "saturation_grid_supported_only_float64",
                "supported_mask",
                "support_denominator",
                "support_numerator",
                "segment_piece_count",
                "streamline_visit_count",
                "background_saturation",
                "physical_time_days",
                "grid_shape",
            ]
            gate(
                "legacy_required_arrays_present",
                all(k in z.files for k in required_legacy),
                str(required_legacy),
            )
            legacy_sat = np.array(
                z["saturation_grid_full_float64"], copy=True, dtype=np.float64
            )
            legacy_supported_only = np.array(
                z["saturation_grid_supported_only_float64"],
                copy=True,
                dtype=np.float64,
            )
            legacy_supported_mask = np.asarray(z["supported_mask"], dtype=bool).copy()
            legacy_denominator = np.array(z["support_denominator"], copy=True)
            legacy_numerator = np.array(z["support_numerator"], copy=True)
            legacy_piece_count = np.array(z["segment_piece_count"], copy=True)
            legacy_visit_count = np.array(z["streamline_visit_count"], copy=True)
            legacy_background = float(np.asarray(z["background_saturation"]))
            legacy_time = float(np.asarray(z["physical_time_days"]))
            legacy_grid = tuple(
                int(x) for x in np.asarray(z["grid_shape"]).tolist()
            )

        gate(
            "legacy_grid_exact",
            legacy_sat.shape == EXPECTED_GRID
            and legacy_grid == EXPECTED_GRID
            and legacy_sat.size == EXPECTED_CELLS,
            f"{legacy_sat.shape}:{legacy_grid}:{legacy_sat.size}",
        )
        gate(
            "legacy_time_exact_100d",
            legacy_time == TARGET_OBSERVATION_DAY,
            legacy_time,
        )
        gate(
            "legacy_background_exact",
            legacy_background == BACKGROUND_SATURATION,
            legacy_background,
        )
        gate(
            "legacy_bounds_exact",
            float(np.min(legacy_sat)) == LEGACY_EXPECTED_MIN
            and float(np.max(legacy_sat)) == LEGACY_EXPECTED_MAX,
            f"{np.min(legacy_sat)}:{np.max(legacy_sat)}",
        )
        gate(
            "legacy_support_counts_exact",
            int(np.sum(legacy_supported_mask)) == LEGACY_EXPECTED_SUPPORTED
            and int(np.sum(~legacy_supported_mask)) == LEGACY_EXPECTED_UNSUPPORTED,
            f"{np.sum(legacy_supported_mask)}:{np.sum(~legacy_supported_mask)}",
        )
        gate(
            "legacy_background_completed_cells_have_zero_support_evidence",
            bool(np.all(legacy_denominator[~legacy_supported_mask] == 0.0))
            and bool(np.all(legacy_numerator[~legacy_supported_mask] == 0.0)),
        )

        failed_stage = "physics_operator_setup"

        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E41_") as td:
            tmp = Path(td)
            shutil.copy2(sg7a_path, tmp / SG7A)
            shutil.copy2(sg7d_path, tmp / SG7D)
            sg7a = load_module(tmp / SG7A, "pad_stream_v16e41_sg7a")
            sg7d = load_module(tmp / SG7D, "pad_stream_v16e41_sg7d")

            pressure_psi = np.asarray(cache["accepted_pressure_psi"], dtype=np.float64)
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

            expected_cv_pv = weights_m3_day[:, None] * np.diff(tof_days, axis=1)
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
                        np.asarray(
                            sg7a.df_dS(sat_scan),
                            dtype=np.float64,
                        )
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
                perm_path,
                skiprows=1,
                dtype=np.float64,
            ).reshape(EXPECTED_GRID, order="C")
            gate(
                "SGSim_permeability_shape_exact",
                permeability_md.shape == EXPECTED_GRID,
                permeability_md.shape,
            )

            failed_stage = "production_60_to_100d_rollout"

            current = {k: np.asarray(v).copy() for k, v in parent.items()}

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
            snapshot_labels = ["E40_CANONICAL_60D_START"]
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
            start_plume["state_label"] = "E40_CANONICAL_60D_START"
            start_plume["producer_CO2_gas_cut"] = initial_cut
            plume_rows.append(start_plume)

            while (
                scalar(current["physical_time_days"])
                < TARGET_OBSERVATION_DAY - 1.0e-13
            ):
                if accepted_transitions >= MAX_ACCEPTED_TRANSITIONS:
                    raise GateError(
                        "accepted_transition_budget_exceeded:"
                        f"{MAX_ACCEPTED_TRANSITIONS}"
                    )

                current_time = scalar(current["physical_time_days"])
                target_step = int_scalar(current["accepted_step_index"]) + 1
                remaining = TARGET_OBSERVATION_DAY - current_time
                nominal_trial_dt = min(nominal_dt_days, remaining)

                if (
                    not np.isfinite(nominal_trial_dt)
                    or nominal_trial_dt <= 0.0
                ):
                    raise GateError(
                        "nonpositive_60to100_dt:"
                        f"{target_step}:{nominal_trial_dt}"
                    )

                accepted = False
                last_reason = ""

                for retry in range(MAX_TRIAL_RETRIES + 1):
                    dt_days = nominal_trial_dt * (RETRY_FACTOR ** retry)
                    dt_days = min(
                        dt_days,
                        TARGET_OBSERVATION_DAY - current_time,
                    )

                    if not np.isfinite(dt_days) or dt_days <= 0.0:
                        raise GateError(
                            "nonpositive_retry_dt:"
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
                        if TARGET_OBSERVATION_DAY - trial_time <= 1.0e-13:
                            trial_time = TARGET_OBSERVATION_DAY

                        observation_reached = (
                            trial_time == TARGET_OBSERVATION_DAY
                        )

                        child = apply_e41_state_semantics(
                            result["child"],
                            current,
                            canonical_breakthrough_time_days=canonical_bt_time,
                            observation_reached=observation_reached,
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

                        new_time = scalar(child["physical_time_days"])
                        if (
                            new_time <= current_time
                            or new_time > TARGET_OBSERVATION_DAY + 1.0e-12
                        ):
                            raise e37a.TrialReject(
                                "accepted_time_invalid:"
                                f"{current_time}:{new_time}"
                            )

                        if not bool_scalar(child["breakthrough_reached"]):
                            raise e37a.TrialReject(
                                "E41_child_lost_breakthrough_flag"
                            )
                        if (
                            abs(
                                scalar(child["breakthrough_time_days"])
                                - canonical_bt_time
                            )
                            > 1.0e-12
                        ):
                            raise e37a.TrialReject(
                                "E41_child_changed_breakthrough_time"
                            )
                        if not bool_scalar(
                            child["first_fixed_observation_checkpoint_reached"]
                        ):
                            raise e37a.TrialReject(
                                "E41_child_lost_30d_history"
                            )
                        if not bool_scalar(
                            child["second_fixed_observation_checkpoint_reached"]
                        ):
                            raise e37a.TrialReject(
                                "E41_child_lost_60d_history"
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
                                "E41_time_since_breakthrough_mismatch"
                            )

                        if not observation_reached:
                            if (
                                int_scalar(child["observation_cursor_index"]) != 2
                                or scalar(
                                    child["last_fixed_observation_day"]
                                )
                                != 60.0
                                or scalar(
                                    child["next_fixed_observation_day"]
                                )
                                != 100.0
                            ):
                                raise e37a.TrialReject(
                                    "E41_pre100_observation_history_mutated"
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
                                "last_fixed_observation_day": scalar(
                                    child["last_fixed_observation_day"]
                                ),
                                "observation_cursor_index": int_scalar(
                                    child["observation_cursor_index"]
                                ),
                                "next_fixed_observation_day": scalar(
                                    child["next_fixed_observation_day"]
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
                            }
                        )

                        for row in result["producer_rows"]:
                            producer_rows_all.append(
                                {
                                    "accepted_step_index": target_step,
                                    "accepted_time_days": new_time,
                                    "time_since_breakthrough_days": scalar(
                                        child["time_since_breakthrough_days"]
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
                            float(result["capillary_external_mass_change_kg"])
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
                                    "EXACT_100D_CANONICAL_CHECKPOINT"
                                    if (
                                        observation_reached
                                        and threshold
                                        == TARGET_OBSERVATION_DAY
                                    )
                                    else
                                    "FIRST_ACCEPTED_AT_OR_AFTER_"
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
                                f"dt={dt_days:.12g} d, "
                                f"retry={retry}, "
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
                                "E41_retry_budget_exhausted:"
                                f"{target_step}:{last_reason}"
                            )

                if not accepted:
                    raise GateError(
                        "E41_step_not_accepted:"
                        f"{target_step}:{last_reason}"
                    )

            failed_stage = "final_100d_checkpoint_validation"

            final_state = current
            final_step = int_scalar(final_state["accepted_step_index"])
            final_time = scalar(final_state["physical_time_days"])
            final_sat = np.asarray(
                final_state["transport_saturation"], dtype=np.float64
            )
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

            interval_injected = final_injected - initial_injected
            interval_produced = final_produced - initial_produced
            interval_stored_change = final_mass - initial_stored

            gate(
                "E41_exact_100d_landing",
                final_time == TARGET_OBSERVATION_DAY,
                final_time,
            )
            gate(
                "E41_observation_cursor_advanced_to_150d",
                int_scalar(final_state["observation_cursor_index"]) == 3
                and scalar(final_state["last_fixed_observation_day"])
                == TARGET_OBSERVATION_DAY
                and scalar(final_state["next_fixed_observation_day"])
                == NEXT_OBSERVATION_DAY,
                (
                    f"{int_scalar(final_state['observation_cursor_index'])}:"
                    f"{scalar(final_state['last_fixed_observation_day'])}:"
                    f"{scalar(final_state['next_fixed_observation_day'])}"
                ),
            )
            gate(
                "E41_30d_history_preserved",
                bool_scalar(
                    final_state[
                        "first_fixed_observation_checkpoint_reached"
                    ]
                ),
            )
            gate(
                "E41_60d_history_preserved",
                bool_scalar(
                    final_state[
                        "second_fixed_observation_checkpoint_reached"
                    ]
                ),
            )
            gate(
                "E41_100d_observation_flag_true",
                bool_scalar(
                    final_state[
                        "third_fixed_observation_checkpoint_reached"
                    ]
                ),
            )
            gate(
                "E41_breakthrough_history_preserved",
                bool_scalar(final_state["breakthrough_reached"])
                and abs(
                    scalar(final_state["breakthrough_time_days"])
                    - canonical_bt_time
                )
                <= 1.0e-12,
                (
                    f"{bool_scalar(final_state['breakthrough_reached'])}:"
                    f"{scalar(final_state['breakthrough_time_days'])}"
                ),
            )
            gate(
                "E41_time_since_breakthrough_exact",
                abs(
                    scalar(final_state["time_since_breakthrough_days"])
                    - (
                        TARGET_OBSERVATION_DAY
                        - canonical_bt_time
                    )
                )
                <= 1.0e-12,
                scalar(final_state["time_since_breakthrough_days"]),
            )
            gate(
                "E41_current_gas_cut_valid",
                np.isfinite(final_cut)
                and 0.0 <= final_cut <= 1.0,
                final_cut,
            )
            gate(
                "E41_cumulative_production_nondecreasing",
                final_produced >= initial_produced - 1.0e-12,
                f"{initial_produced}:{final_produced}",
            )
            gate(
                "E41_injector_local_closure_never_used",
                all(
                    abs(float(r["source_local_added_mass_kg"]))
                    <= 1.0e-12
                    for r in rollout_rows
                ),
            )
            gate(
                "E41_cumulative_mass_closure",
                abs(final_cum_resid) <= final_tol,
                f"{final_cum_resid}:{final_tol}",
            )
            gate(
                "E41_CV_transport_mass_closure",
                max_abs(transport_residuals) <= final_tol,
                max_abs(transport_residuals),
            )
            gate(
                "E41_CV_subsegment_transfer_closure",
                max_abs(transfer_residuals) <= final_tol,
                max_abs(transfer_residuals),
            )
            gate(
                "E41_grid_mapback_ledger_closure",
                max_abs(mapback_residuals) <= final_tol,
                max_abs(mapback_residuals),
            )
            gate(
                "E41_capillary_zero_external_source",
                max_abs(capillary_external_changes) <= final_tol,
                max_abs(capillary_external_changes),
            )
            gate(
                "E41_grid_to_CV_sampling_closure",
                max_abs(sample_closures + post_sample_closures)
                <= final_tol,
                max_abs(sample_closures + post_sample_closures),
            )

            gate(
                "E41_E40_parent_unchanged",
                sha256_file(e40_parent_path) == e40_parent_sha_before,
                sha256_file(e40_parent_path),
            )
            gate(
                "E41_E36_cache_unchanged",
                sha256_file(e36_cache_path) == e36_cache_sha_before,
                sha256_file(e36_cache_path),
            )
            gate(
                "E41_E37B_bracket_unchanged",
                sha256_file(e37b_bracket_path) == e37b_bracket_sha_before,
                sha256_file(e37b_bracket_path),
            )
            gate(
                "E41_legacy_frozen_candidate_unchanged_pre_regression",
                sha256_file(legacy_path) == legacy_sha_before,
                sha256_file(legacy_path),
            )

            if (
                not snapshot_times
                or snapshot_times[-1] != TARGET_OBSERVATION_DAY
            ):
                snapshot_steps.append(final_step)
                snapshot_times.append(TARGET_OBSERVATION_DAY)
                snapshot_sats.append(final_sat.copy())
                snapshot_labels.append(
                    "EXACT_100D_CANONICAL_CHECKPOINT"
                )
                metric = e36.plume_metrics(
                    r2,
                    final_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    final_step,
                    final_time,
                )
                metric["state_label"] = (
                    "EXACT_100D_CANONICAL_CHECKPOINT"
                )
                metric["producer_CO2_gas_cut"] = final_cut
                plume_rows.append(metric)
            else:
                snapshot_labels[-1] = (
                    "EXACT_100D_CANONICAL_CHECKPOINT"
                )

            final_plume = e36.plume_metrics(
                r2,
                final_sat,
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
                expected_sat=final_sat,
            )
            gate(
                "canonical_100d_restart_artifact_validated",
                True,
                final_step,
            )

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

            failed_stage = "formal_100d_legacy_regression"

            gate(
                "new_100d_shape_matches_legacy",
                final_sat.shape == legacy_sat.shape == EXPECTED_GRID,
                f"{final_sat.shape}:{legacy_sat.shape}",
            )
            gate("new_100d_finite", bool(np.all(np.isfinite(final_sat))))
            gate("legacy_100d_finite", bool(np.all(np.isfinite(legacy_sat))))

            whole_metrics = field_error_metrics(final_sat, legacy_sat)
            supported_metrics = field_error_metrics(
                final_sat,
                legacy_sat,
                legacy_supported_mask,
            )
            background_completed_metrics = field_error_metrics(
                final_sat,
                legacy_sat,
                ~legacy_supported_mask,
            )

            active_overlap = overlap_metrics(
                final_sat,
                legacy_sat,
                ACTIVE_INCREMENT_THRESHOLD,
            )
            visible_overlap = overlap_metrics(
                final_sat,
                legacy_sat,
                VISIBLE_INCREMENT_THRESHOLD,
            )

            new_centroid = saturation_increment_centroid_m(final_sat)
            legacy_centroid = saturation_increment_centroid_m(legacy_sat)
            centroid_delta = (
                np.asarray(new_centroid, dtype=np.float64)
                - np.asarray(legacy_centroid, dtype=np.float64)
            )
            centroid_distance = float(np.linalg.norm(centroid_delta))

            new_recomputed_mass = float(
                r2.stored_co2_mass_kg(
                    final_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                )
            )
            legacy_common_evaluator_mass = float(
                r2.stored_co2_mass_kg(
                    legacy_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                )
            )
            gate(
                "new_100d_stored_mass_recompute_matches_state",
                abs(new_recomputed_mass - final_mass) <= final_tol,
                f"{new_recomputed_mass}:{final_mass}:{final_tol}",
            )

            new_cv_sat, _, new_sample_close = (
                e37a.sample_grid_inventory_to_control_volumes(
                    r2,
                    final_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    geometry,
                    nstream,
                    ncv,
                )
            )
            legacy_cv_sat, _, legacy_sample_close = (
                e37a.sample_grid_inventory_to_control_volumes(
                    r2,
                    legacy_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    geometry,
                    nstream,
                    ncv,
                )
            )

            regression_sample_tol = max(
                1.0e-6,
                1.0e-10
                * max(
                    abs(final_mass),
                    abs(legacy_common_evaluator_mass),
                    1.0,
                ),
            )
            gate(
                "new_regression_grid_to_CV_sampling_closure",
                abs(float(new_sample_close)) <= regression_sample_tol,
                new_sample_close,
            )
            gate(
                "legacy_regression_grid_to_CV_sampling_closure",
                abs(float(legacy_sample_close)) <= regression_sample_tol,
                legacy_sample_close,
            )

            new_recomputed_cut = float(
                e37b.weighted_outlet_gas_cut(
                    sg7a,
                    new_cv_sat,
                    weights_m3_day,
                )
            )
            legacy_recomputed_cut = float(
                e37b.weighted_outlet_gas_cut(
                    sg7a,
                    legacy_cv_sat,
                    weights_m3_day,
                )
            )
            gate(
                "new_regression_cut_matches_canonical_state",
                abs(new_recomputed_cut - final_cut) <= 1.0e-12,
                f"{new_recomputed_cut}:{final_cut}",
            )

            new_increment = np.clip(
                final_sat - BACKGROUND_SATURATION,
                0.0,
                None,
            )
            legacy_unsupported = ~legacy_supported_mask
            new_active_in_legacy_unsupported = int(
                np.sum(
                    legacy_unsupported
                    & (
                        new_increment
                        > ACTIVE_INCREMENT_THRESHOLD
                    )
                )
            )
            new_visible_in_legacy_unsupported = int(
                np.sum(
                    legacy_unsupported
                    & (
                        new_increment
                        > VISIBLE_INCREMENT_THRESHOLD
                    )
                )
            )

            layer_rows = layerwise_regression_rows(
                final_sat,
                legacy_sat,
                legacy_supported_mask,
            )

            regression_metrics = {
                "milestone": MILESTONE,
                "status": "100D_LEGACY_NUMERICAL_REGRESSION_COMPUTED",
                "regression_role": (
                    "diagnostic comparison of the new production 100-day state "
                    "against the immutable V16E18-R1 numerical deployment candidate"
                ),
                "legacy_candidate_is_physical_truth": False,
                "legacy_full_grid_plume_claim_authorized_by_E18": False,
                "regression_accuracy_threshold_frozen": False,
                "regression_difference_magnitude_is_blocking": False,
                "legacy_frozen_file_sha256": legacy_sha_before,
                "new_production_state_array_sha256": arr_sha(final_sat),
                "legacy_saturation_array_sha256": arr_sha(legacy_sat),
                "new_and_legacy_arrays_bitwise_equal": bool(
                    np.array_equal(final_sat, legacy_sat)
                ),
                "grid_shape": list(EXPECTED_GRID),
                "physical_time_days": TARGET_OBSERVATION_DAY,
                "legacy_supported_cells": int(np.sum(legacy_supported_mask)),
                "legacy_background_completed_cells": int(
                    np.sum(~legacy_supported_mask)
                ),
                "whole_grid": whole_metrics,
                "legacy_supported_partition": supported_metrics,
                "legacy_background_completed_partition": (
                    background_completed_metrics
                ),
                "active_plume_overlap": active_overlap,
                "visible_plume_overlap": visible_overlap,
                "new_incremental_saturation_centroid_m": {
                    "x": new_centroid[0],
                    "y": new_centroid[1],
                    "z": new_centroid[2],
                },
                "legacy_incremental_saturation_centroid_m": {
                    "x": legacy_centroid[0],
                    "y": legacy_centroid[1],
                    "z": legacy_centroid[2],
                },
                "centroid_shift_new_minus_legacy_m": {
                    "dx": float(centroid_delta[0]),
                    "dy": float(centroid_delta[1]),
                    "dz": float(centroid_delta[2]),
                    "distance": centroid_distance,
                },
                "new_canonical_stored_CO2_mass_kg": final_mass,
                "new_common_evaluator_stored_CO2_mass_kg": new_recomputed_mass,
                "legacy_common_evaluator_implied_stored_CO2_mass_kg": (
                    legacy_common_evaluator_mass
                ),
                "common_evaluator_stored_mass_difference_new_minus_legacy_kg": (
                    new_recomputed_mass
                    - legacy_common_evaluator_mass
                ),
                "new_canonical_producer_CO2_gas_cut": final_cut,
                "new_recomputed_current_metric_producer_CO2_gas_cut": (
                    new_recomputed_cut
                ),
                "legacy_recomputed_current_metric_producer_CO2_gas_cut": (
                    legacy_recomputed_cut
                ),
                "current_metric_producer_cut_difference_new_minus_legacy": (
                    new_recomputed_cut
                    - legacy_recomputed_cut
                ),
                "legacy_breakthrough_time_available_from_single_100d_candidate": False,
                "new_canonical_breakthrough_time_days": canonical_bt_time,
                "new_active_cells_inside_legacy_background_completed_partition": (
                    new_active_in_legacy_unsupported
                ),
                "new_visible_cells_inside_legacy_background_completed_partition": (
                    new_visible_in_legacy_unsupported
                ),
            }

            gate(
                "formal_regression_metrics_finite_core",
                all(
                    np.isfinite(
                        float(
                            whole_metrics[key]
                        )
                    )
                    for key in [
                        "L1_mean_abs",
                        "L2_rms",
                        "Linf",
                        "signed_mean_bias_new_minus_legacy",
                    ]
                )
                and np.isfinite(centroid_distance)
                and np.isfinite(legacy_common_evaluator_mass)
                and np.isfinite(legacy_recomputed_cut),
            )
            gate(
                "regression_no_invented_accuracy_gate",
                regression_metrics[
                    "regression_accuracy_threshold_frozen"
                ]
                is False
                and regression_metrics[
                    "regression_difference_magnitude_is_blocking"
                ]
                is False,
            )

            gate(
                "E41_legacy_frozen_candidate_unchanged_post_regression",
                sha256_file(legacy_path) == legacy_sha_before,
                sha256_file(legacy_path),
            )
            gate(
                "E41_E40_parent_unchanged_post_regression",
                sha256_file(e40_parent_path) == e40_parent_sha_before,
                sha256_file(e40_parent_path),
            )

            observation_metrics = {
                "milestone": MILESTONE,
                "status": "CANONICAL_PRODUCTION_100D_SGSIM_CHECKPOINT",
                "physical_time_days": final_time,
                "accepted_step_index": final_step,
                "breakthrough_reached": True,
                "breakthrough_time_days": canonical_bt_time,
                "time_since_breakthrough_days": scalar(
                    final_state["time_since_breakthrough_days"]
                ),
                "producer_CO2_gas_cut_at_100d": final_cut,
                "stored_CO2_mass_kg": final_mass,
                "cumulative_injected_CO2_mass_kg": final_injected,
                "cumulative_produced_CO2_mass_kg": final_produced,
                "interval_60_to_100d_injected_CO2_mass_kg": (
                    interval_injected
                ),
                "interval_60_to_100d_produced_CO2_mass_kg": (
                    interval_produced
                ),
                "interval_60_to_100d_stored_CO2_mass_change_kg": (
                    interval_stored_change
                ),
                "cumulative_mass_residual_kg": final_cum_resid,
                "plume": final_plume,
                "observation_cursor_index_after_commit": int_scalar(
                    final_state["observation_cursor_index"]
                ),
                "last_fixed_observation_day": scalar(
                    final_state["last_fixed_observation_day"]
                ),
                "next_fixed_observation_day": scalar(
                    final_state["next_fixed_observation_day"]
                ),
            }

            controller_contract = {
                "milestone": MILESTONE,
                "status": (
                    "PRODUCTION_REFERENCE_MOBILITY_CV_ALIGNED_CONTROLLER_"
                    "60_TO_100D"
                ),
                "restart_parent": (
                    "V16E-40 canonical 60-day observation state"
                ),
                "breakthrough_history_policy": (
                    "preserve canonical E38 breakthrough time exactly"
                ),
                "fixed_observation_history_policy": (
                    "30-day and 60-day observations remain historical state; "
                    "only exact 100-day commit advances cursor from 2 to 3"
                ),
                "nominal_dt_days": nominal_dt_days,
                "retry_policy": (
                    "rejected numerical trial does not mutate accepted parent; "
                    "retry with dt_new = 0.5*dt_old"
                ),
                "maximum_retries_per_transition": MAX_TRIAL_RETRIES,
                "observation_policy": (
                    "hard clip final transition to exactly t=100.0 days"
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

            regression_contract = {
                "milestone": MILESTONE,
                "status": "LEGACY_100D_REGRESSION_CONTRACT_ACTIVE",
                "legacy_artifact": str(legacy_path),
                "legacy_artifact_sha256": legacy_sha_before,
                "legacy_artifact_role": (
                    "immutable historical numerical deployment input"
                ),
                "legacy_artifact_is_physical_truth": False,
                "legacy_full_grid_plume_claim_authorized": False,
                "whole_grid_regression_required": True,
                "legacy_supported_partition_regression_required": True,
                "legacy_background_completed_partition_regression_required": True,
                "field_norms_required": [
                    "L1_mean_abs",
                    "L2_rms",
                    "Linf",
                    "signed_mean_bias",
                    "relative_L2",
                    "correlation",
                ],
                "spatial_overlap_required": [
                    "active IoU at incremental saturation > 1e-8",
                    "visible IoU at incremental saturation > 1e-4",
                ],
                "centroid_shift_required": True,
                "layerwise_regression_required": True,
                "common_evaluator_mass_regression_required": True,
                "current_producer_metric_regression_required": True,
                "legacy_breakthrough_time_inference_authorized": False,
                "regression_accuracy_threshold_frozen": False,
                "regression_difference_magnitude_is_blocking": False,
                "reason_no_accuracy_threshold": (
                    "V16E18-R1 and the production runtime have materially "
                    "different transport/map-back semantics; E41 measures "
                    "divergence before any scientific tolerance is proposed."
                ),
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "parent_milestone": "V16E-40",
                "parent_state_sha256": e40_parent_sha_before,
                "initial_step_index": initial_step,
                "initial_time_days": initial_time,
                "initial_producer_CO2_gas_cut": initial_cut,
                "canonical_breakthrough_time_days": canonical_bt_time,
                "final_accepted_step_index": final_step,
                "final_time_days": final_time,
                "continuation_transitions_executed": accepted_transitions,
                "nominal_dt_days": nominal_dt_days,
                "last_accepted_dt_days": scalar(
                    final_state["last_accepted_dt_days"]
                ),
                "total_rejected_trials": rejected_trials,
                "observation_checkpoint_reached": True,
                "first_fixed_observation_checkpoint_reached": True,
                "second_fixed_observation_checkpoint_reached": True,
                "third_fixed_observation_checkpoint_reached": True,
                "observation_cursor_index": int_scalar(
                    final_state["observation_cursor_index"]
                ),
                "last_fixed_observation_day": scalar(
                    final_state["last_fixed_observation_day"]
                ),
                "next_fixed_observation_day": scalar(
                    final_state["next_fixed_observation_day"]
                ),
                "canonical_100d_state_created": True,
                "breakthrough_reached": True,
                "breakthrough_time_preserved_exact": True,
                "time_since_breakthrough_days": scalar(
                    final_state["time_since_breakthrough_days"]
                ),
                "producer_CO2_gas_cut_at_100d": final_cut,
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
                "interval_60_to_100d_injected_CO2_mass_kg": (
                    interval_injected
                ),
                "interval_60_to_100d_produced_CO2_mass_kg": (
                    interval_produced
                ),
                "interval_60_to_100d_stored_CO2_mass_change_kg": (
                    interval_stored_change
                ),
                "legacy_frozen_candidate_sha256": legacy_sha_before,
                "legacy_frozen_candidate_modified": False,
                "legacy_candidate_is_physical_truth": False,
                "legacy_full_grid_plume_claim_authorized": False,
                "regression_completed": True,
                "regression_accuracy_threshold_frozen": False,
                "regression_difference_magnitude_is_blocking": False,
                "whole_grid_L1_mean_abs": whole_metrics["L1_mean_abs"],
                "whole_grid_L2_rms": whole_metrics["L2_rms"],
                "whole_grid_Linf": whole_metrics["Linf"],
                "whole_grid_pearson_correlation": whole_metrics[
                    "pearson_correlation"
                ],
                "legacy_supported_L1_mean_abs": supported_metrics[
                    "L1_mean_abs"
                ],
                "legacy_supported_L2_rms": supported_metrics["L2_rms"],
                "legacy_supported_Linf": supported_metrics["Linf"],
                "legacy_background_completed_L1_mean_abs": (
                    background_completed_metrics["L1_mean_abs"]
                ),
                "active_plume_IoU": active_overlap[
                    "intersection_over_union"
                ],
                "visible_plume_IoU": visible_overlap[
                    "intersection_over_union"
                ],
                "centroid_shift_m": centroid_distance,
                "legacy_common_evaluator_implied_stored_CO2_mass_kg": (
                    legacy_common_evaluator_mass
                ),
                "legacy_recomputed_current_metric_producer_CO2_gas_cut": (
                    legacy_recomputed_cut
                ),
                "E36_certified_cache_reused": True,
                "cache_reuse_scope_reference_mobility_only": True,
                "learned_timestep_proposal_used": False,
                "F0_hidden_update_deferred": True,
                "SGSim_specific_dt_envelope_frozen": False,
                "SGSim_specific_mass_tolerance_frozen": False,
                "E42_long_horizon_150d_entry_ready": True,
                "IBDP_started": False,
            }

            handoff = f"""# PAD-Stream V16E-41 Handoff

V16E-41 restarts from the canonical V16E-40 60-day state and advances the production CV-aligned component-mass runtime to the exact third fixed observation at 100.0 days.

Production 100-day state:
- accepted step: {final_step}
- physical time: {final_time:.12g} days
- canonical breakthrough time retained: {canonical_bt_time:.12g} days
- producer CO2 gas cut: {final_cut:.12e}
- cumulative injected CO2 mass: {final_injected:.12e} kg
- cumulative produced CO2 mass: {final_produced:.12e} kg
- stored CO2 mass: {final_mass:.12e} kg
- cumulative mass residual: {final_cum_resid:.12e} kg
- observation cursor: 3
- last fixed observation: 100.0 days
- next fixed observation: 150.0 days

Legacy regression:
- immutable candidate: {LEGACY_FILE}
- immutable SHA-256: {legacy_sha_before}
- V16E18-R1 explicitly froze this artifact as a numerical deployment input and did not authorize a full-grid plume truth claim.
- legacy supported cells: {int(np.sum(legacy_supported_mask))}
- legacy background-completed unsupported cells: {int(np.sum(~legacy_supported_mask))}
- whole-grid L1 mean absolute saturation difference: {whole_metrics['L1_mean_abs']:.12e}
- whole-grid L2 RMS saturation difference: {whole_metrics['L2_rms']:.12e}
- whole-grid Linf saturation difference: {whole_metrics['Linf']:.12e}
- supported-partition L1 mean absolute saturation difference: {supported_metrics['L1_mean_abs']:.12e}
- active-plume IoU: {active_overlap['intersection_over_union']:.12e}
- visible-plume IoU: {visible_overlap['intersection_over_union']:.12e}
- incremental-saturation centroid shift: {centroid_distance:.12e} m

No regression closeness threshold is frozen in E41. The purpose is to measure the architectural difference first, not force the new production runtime to resemble the old background-completed deployment candidate.

The production runtime remains the authoritative restart path after E41. The legacy V16E18-R1 candidate remains immutable historical regression evidence.

NEXT: {NEXT}
"""

            checkpoint_name = (
                "V16E41_Canonical_Production_SGSim_Runtime_State_"
                "Observation_0100d.npz"
            )
            snapshot_name = "V16E41_60to100d_Sparse_Plume_Snapshots.npz"
            regression_npz_name = (
                "V16E41_100D_Production_vs_Legacy_Regression_Fields.npz"
            )

            regression_npz_bytes = deterministic_npz_bytes(
                {
                    "new_production_saturation_float64": final_sat,
                    "legacy_frozen_saturation_float64": legacy_sat,
                    "difference_new_minus_legacy_float64": (
                        final_sat - legacy_sat
                    ),
                    "legacy_supported_mask": legacy_supported_mask,
                    "legacy_supported_only_float64": legacy_supported_only,
                    "legacy_support_denominator": legacy_denominator,
                    "legacy_support_numerator": legacy_numerator,
                    "legacy_segment_piece_count": legacy_piece_count,
                    "legacy_streamline_visit_count": legacy_visit_count,
                }
            )

            files: dict[str, bytes] = {
                checkpoint_name: checkpoint_bytes,
                snapshot_name: snapshot_bytes,
                regression_npz_name: regression_npz_bytes,
                "V16E41_60to100d_Rollout_Step_Audit.csv": csv_bytes(
                    rollout_rows
                ),
                "V16E41_60to100d_Producer_CO2_Response.csv": csv_bytes(
                    producer_rows_all
                ),
                "V16E41_60to100d_Sparse_Plume_Metrics.csv": csv_bytes(
                    plume_rows
                ),
                "V16E41_Trial_Rejection_Audit.csv": csv_bytes(
                    trial_failures
                ),
                "V16E41_Observation_0100d_Metrics.json": json_bytes(
                    observation_metrics
                ),
                "V16E41_100D_Legacy_Regression_Metrics.json": json_bytes(
                    regression_metrics
                ),
                "V16E41_100D_Layerwise_Regression.csv": csv_bytes(
                    layer_rows
                ),
                "V16E41_60to100d_Controller_Contract.json": json_bytes(
                    controller_contract
                ),
                "V16E41_Legacy_Regression_Contract.json": json_bytes(
                    regression_contract
                ),
                "PAD_Stream_V16E41_Summary.json": json_bytes(summary),
                "V16E41_Handoff.md": handoff.encode("utf-8"),
                "V16E41_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            }

            checkpoint_sha = hashlib.sha256(checkpoint_bytes).hexdigest()
            snapshot_sha = hashlib.sha256(snapshot_bytes).hexdigest()
            regression_fields_sha = hashlib.sha256(
                regression_npz_bytes
            ).hexdigest()

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
                "regression_fields_file": regression_npz_name,
                "regression_fields_sha256": regression_fields_sha,
                "E40_parent_state_sha256": e40_parent_sha_before,
                "E36_certified_cache_sha256": e36_cache_sha_before,
                "E37B_breakthrough_bracket_report_sha256": (
                    e37b_bracket_sha_before
                ),
                "legacy_frozen_candidate_sha256": legacy_sha_before,
                "legacy_frozen_candidate_modified": False,
                "legacy_candidate_is_physical_truth": False,
                "regression_completed": True,
                "regression_accuracy_threshold_frozen": False,
                "breakthrough_reached": True,
                "breakthrough_time_days": canonical_bt_time,
                "breakthrough_time_preserved_exact": True,
                "first_observation_history_preserved": True,
                "second_observation_history_preserved": True,
                "third_observation_committed": True,
                "observation_cursor_index": 3,
                "last_fixed_observation_day": TARGET_OBSERVATION_DAY,
                "next_fixed_observation_day": NEXT_OBSERVATION_DAY,
                "injector_local_mass_closure_authorized": False,
                "injector_local_mass_closure_executed": False,
            }
            files["V16E41_Final_Closure.json"] = json_bytes(closure)

            immutable_publish(out, files)

            manifest_rows = []
            for path in sorted(out.iterdir()):
                if (
                    path.is_file()
                    and path.name != "V16E41_Artifact_Manifest.csv"
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
                    "V16E41_Artifact_Manifest.csv": csv_bytes(
                        manifest_rows
                    )
                },
            )

        print("\n" + "=" * 148)
        print(
            "PAD-Stream V16E-41 PRODUCTION 100-DAY CHECKPOINT / "
            "LEGACY REGRESSION: PASS"
        )
        print("=" * 148)
        print(
            f"{'Restart step/time':84}: "
            f"{initial_step} / {initial_time:.12g} d"
        )
        print(
            f"{'Final accepted step/time':84}: "
            f"{final_step} / {final_time:.12g} d"
        )
        print(
            f"{'Accepted continuation transitions':84}: "
            f"{accepted_transitions}"
        )
        print(
            f"{'Rejected numerical trials':84}: "
            f"{rejected_trials}"
        )
        print(
            f"{'Physics-derived nominal dt':84}: "
            f"{nominal_dt_days:.12g} d"
        )
        print(
            f"{'Final observation-clipped dt':84}: "
            f"{scalar(final_state['last_accepted_dt_days']):.12g} d"
        )
        print(
            f"{'Producer CO2 gas cut at 100 d':84}: "
            f"{final_cut:.12e}"
        )
        print(
            f"{'Cumulative produced CO2 mass':84}: "
            f"{final_produced:.12e} kg"
        )
        print(
            f"{'60-to-100 d produced CO2 mass':84}: "
            f"{interval_produced:.12e} kg"
        )
        print(
            f"{'Stored CO2 mass':84}: "
            f"{final_mass:.12e} kg"
        )
        print(
            f"{'Cumulative mass residual':84}: "
            f"{final_cum_resid:.12e} kg"
        )
        print(
            f"{'Legacy whole-grid L1 mean abs':84}: "
            f"{whole_metrics['L1_mean_abs']:.12e}"
        )
        print(
            f"{'Legacy whole-grid L2 RMS':84}: "
            f"{whole_metrics['L2_rms']:.12e}"
        )
        print(
            f"{'Legacy whole-grid Linf':84}: "
            f"{whole_metrics['Linf']:.12e}"
        )
        print(
            f"{'Legacy supported-partition L1 mean abs':84}: "
            f"{supported_metrics['L1_mean_abs']:.12e}"
        )
        print(
            f"{'Active plume IoU':84}: "
            f"{active_overlap['intersection_over_union']:.12e}"
        )
        print(
            f"{'Visible plume IoU':84}: "
            f"{visible_overlap['intersection_over_union']:.12e}"
        )
        print(
            f"{'Incremental-saturation centroid shift':84}: "
            f"{centroid_distance:.12e} m"
        )
        print(
            f"{'Regression match threshold':84}: "
            "NOT FROZEN / DIAGNOSTIC ONLY"
        )
        print(
            f"{'Legacy frozen artifact':84}: "
            "UNCHANGED"
        )
        print(
            f"{'Observation cursor / next':84}: "
            f"{int_scalar(final_state['observation_cursor_index'])} / "
            f"{scalar(final_state['next_fixed_observation_day']):.12g} d"
        )
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": "PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION_BLOCKED",
            "exception": repr(exc),
            "failed_stage": failed_stage,
            "gates": gates,
            "trial_failures": trial_failures,
            "canonical_100d_checkpoint_published": False,
            "legacy_regression_published": False,
            "E40_parent_mutated": (
                False
                if e40_parent_sha_before is None
                else (
                    not (drive / E40_REL / E40_CANONICAL).is_file()
                    or sha256_file(drive / E40_REL / E40_CANONICAL)
                    != e40_parent_sha_before
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
            "legacy_frozen_candidate_modified": (
                False
                if legacy_sha_before is None
                else (
                    not (
                        drive
                        / LEGACY_REL
                        / LEGACY_SUBDIR
                        / LEGACY_FILE
                    ).is_file()
                    or sha256_file(
                        drive
                        / LEGACY_REL
                        / LEGACY_SUBDIR
                        / LEGACY_FILE
                    )
                    != legacy_sha_before
                )
            ),
            "next_action": (
                "Audit the failed E41 production or regression gate. "
                "Do not advance to the post-100-day long-horizon rollout "
                "until the canonical 100-day production checkpoint and "
                "legacy regression are complete."
            ),
        }

        data = json_bytes(report)
        path = (
            blocked
            / "V16E41_Blocked_100D_Production_Regression.json"
        )
        if path.exists() and path.read_bytes() != data:
            path = blocked / (
                "V16E41_Blocked_100D_Production_Regression_"
                f"{hashlib.sha256(data).hexdigest()[:12]}.json"
            )
        if not path.exists():
            path.write_bytes(data)

        print("\n" + "=" * 148)
        print(
            "PAD-Stream V16E-41 PRODUCTION 100-DAY CHECKPOINT / "
            "LEGACY REGRESSION: BLOCKED"
        )
        print("=" * 148)
        print("Stage :", failed_stage)
        print("Reason:", repr(exc))
        print(
            "No canonical V16E-41 100-day checkpoint or formal regression "
            "was published."
        )
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
            "--project-root and --drive-root are required "
            "unless --self-test is used"
        )

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
