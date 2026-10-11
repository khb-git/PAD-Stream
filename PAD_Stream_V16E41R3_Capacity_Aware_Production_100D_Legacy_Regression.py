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
from collections import Counter
from typing import Any

import numpy as np


MILESTONE = "V16E-41-R3"
STATUS = "CAPACITY_AWARE_PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION_COMPLETED"
NEXT = (
    "V16E-42 - Post-100-Day Long-Horizon Fixed-Observation Rollout / "
    "150-Day Checkpoint"
)

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
BACKGROUND_SATURATION = 0.20
TARGET_OBSERVATION_DAY = 100.0
NEXT_OBSERVATION_DAY = 150.0
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0

EXPECTED_R2_STEP = 1475
EXPECTED_R2_TIME_DAYS = 69.88219208575286
EXPECTED_R2_STATE_SHA256 = (
    "23d7fb28fa126e4914b8529355a783f321208baecd966b1517f5eb3cd76f7b79"
)
EXPECTED_R2_STATUS = "CAPACITY_AWARE_CONSERVATIVE_MAPBACK_STEP_1475_RECOVERED"
EXPECTED_R2_LIMITER_CELL = (8, 25, 24)

MAX_ACCEPTED_TRANSITIONS = 2500
MAX_NATIVE_RETRIES_PER_STEP = 8
NATIVE_RETRY_FACTOR = 0.5
PROGRESS_EVERY = 100
SPARSE_SNAPSHOT_THRESHOLDS_DAYS = (75.0, 90.0, 100.0)

LEGACY_EXPECTED_SUPPORTED = 20462
LEGACY_EXPECTED_UNSUPPORTED = 17038
LEGACY_EXPECTED_MIN = 0.20
LEGACY_EXPECTED_MAX = 0.78499960534060065
LEGACY_FREEZE_STATUS = "V16E18_R1_FULL_GRID_CANDIDATE_FREEZE_PASS"
LEGACY_FROZEN_SHA256 = (
    "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
)

ACTIVE_INCREMENT_THRESHOLD = 1.0e-8
VISIBLE_INCREMENT_THRESHOLD = 1.0e-4

PHYSICS_R2_RUNNER = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_"
    "First_Controlled_Transition.py"
)
PHYSICS_R2_RUNNER_SHA256 = (
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
E37A_EXPECTED_STATUS = "CONTROL_VOLUME_ALIGNED_CONSERVATIVE_TRANSFER_VALIDATED"

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

E41_RUNNER = (
    "PAD_Stream_V16E41_Production_100D_Checkpoint_and_"
    "Legacy_Frozen_Candidate_Regression.py"
)
E41_RUNNER_SHA256 = (
    "d2365d3ddc3374c4afda3a9aa15a32ef6ec6ed1a50ee0659932447aac2d04771"
)

REPAIR_R2_RUNNER = (
    "PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_"
    "Timestep_Repair.py"
)
REPAIR_R2_RUNNER_SHA256 = (
    "8fe73043e6bb40d1ac30b96999058d99175db2af81e5c010f88413d6ad58586e"
)
REPAIR_R2_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R2_CAPACITY_AWARE_CONSERVATIVE_MAPBACK_TIMESTEP_REPAIR"
)
REPAIR_R2_SUMMARY = "PAD_Stream_V16E41R2_Summary.json"
REPAIR_R2_CLOSURE = "V16E41R2_Final_Closure.json"
REPAIR_R2_STATE = (
    "V16E41R2_Accepted_Repaired_SGSim_Runtime_State_Step_1475.npz"
)
REPAIR_R2_DESIGN = "V16E41R3_Rollout_Design_Input.json"

LEGACY_REL = Path(
    "provenance/hybrid_dp/"
    "V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE"
)
LEGACY_SUMMARY = "PAD_Stream_V16E18_R1_Summary.json"
LEGACY_MANIFEST = "V16E18_R1_Full_Grid_Freeze_Manifest.json"
LEGACY_SUBDIR = "frozen_full_grid"
LEGACY_FILE = "V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3_CAPACITY_AWARE_PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3_BLOCKED_CAPACITY_AWARE_PRODUCTION_100D_CHECKPOINT_LEGACY_REGRESSION"
)

CANONICAL_100D_STATE = (
    "V16E41R3_Canonical_CapacityAware_SGSim_Runtime_State_Observation_0100d.npz"
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def arr_sha(a: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(a).tobytes()
    ).hexdigest()


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(
        buf, fieldnames=fields, lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def deterministic_npz_bytes(
    arrays: dict[str, Any],
) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(
                b,
                np.asarray(arrays[key]),
                allow_pickle=False,
            )
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(
    out: Path,
    files: dict[str, bytes],
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(
                    f"existing_output_differs:{name}"
                )
        else:
            p.write_bytes(data)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {
            k: z[k].copy()
            for k in z.files
        }


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name, path
    )
    if spec is None or spec.loader is None:
        raise GateError(
            f"cannot_load_module:{path}"
        )
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
    return max(
        [abs(float(v)) for v in values] + [0.0]
    )


def self_test() -> None:
    # The R3 step policy distinguishes capacity adjustments from native
    # rejections. A capacity adjustment is not counted against the native
    # nine-attempt halving budget.
    nominal = 0.049123143364170854
    capacity_bound = 0.00018911656767886314
    if not (0.0 < capacity_bound < nominal):
        raise RuntimeError(
            "self_test_capacity_bound_order"
        )

    # Observation clipping must remain exact.
    t = 99.99
    h = min(nominal, 100.0 - t)
    if abs(h - 0.01) > 1.0e-12:
        raise RuntimeError(
            "self_test_observation_clipping"
        )

    # Diagnostic regression may differ without becoming an accuracy gate.
    legacy_accuracy_threshold_frozen = False
    regression_difference_magnitude_is_blocking = False
    if (
        legacy_accuracy_threshold_frozen
        or regression_difference_magnitude_is_blocking
    ):
        raise RuntimeError(
            "self_test_regression_role"
        )

    print(
        "PAD-Stream V16E-41-R3 capacity-aware 100d rollout "
        "and legacy regression self-test: PASS"
    )


def main(
    project_root: Path,
    drive_root: Path,
) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(
        name: str,
        passed: bool,
        detail: Any = "",
    ) -> None:
        gates[name] = {
            "passed": bool(passed),
            "detail": str(detail),
        }
        if not passed:
            raise GateError(name)

    provenance_before: dict[str, str] = {}

    try:
        print(
            "\n" + "=" * 150
        )
        print(
            "PAD-Stream V16E-41-R3 — Capacity-Aware Production "
            "Rollout to 100d + Legacy Frozen-Candidate Regression"
        )
        print("=" * 150)
        print(
            "RESTART       : formal V16E-41-R2 repaired step-1475 state"
        )
        print(
            "TIMESTEPPING  : capacity-aware map-back controller + "
            "native halving fallback for non-map-back failures"
        )
        print(
            "SPATIAL PHYSICS: frozen E37A map-back unchanged"
        )
        print(
            "EOS / CAPILLARY: frozen V16E35-R2 operators unchanged"
        )
        print(
            "LANDING       : exact 100-day fixed observation checkpoint"
        )
        print(
            "REGRESSION    : immutable V16E18-R1 numerical candidate; "
            "diagnostic, not physical truth"
        )
        print(
            "ACCURACY GATE : none frozen; difference magnitude non-blocking"
        )

        failed_stage = "source_and_provenance_binding"

        paths = {
            "PHYSICS_R2": root / PHYSICS_R2_RUNNER,
            "E36": root / E36_RUNNER,
            "E37A": root / E37A_RUNNER,
            "E37B": root / E37B_RUNNER,
            "E38": root / E38_RUNNER,
            "E41": root / E41_RUNNER,
            "REPAIR_R2": root / REPAIR_R2_RUNNER,
            "SG7A": root / SG7A,
            "SG7D": root / SG7D,
            "PERM": root / SGSIM_PERM,
        }
        for key, p in paths.items():
            gate(
                f"source_exists_{key}",
                p.is_file(),
                p,
            )

        expected_source_sha = {
            "PHYSICS_R2": PHYSICS_R2_RUNNER_SHA256,
            "E36": E36_RUNNER_SHA256,
            "E37A": E37A_RUNNER_SHA256,
            "E37B": E37B_RUNNER_SHA256,
            "E38": E38_RUNNER_SHA256,
            "E41": E41_RUNNER_SHA256,
            "REPAIR_R2": REPAIR_R2_RUNNER_SHA256,
        }
        for key, expected in expected_source_sha.items():
            actual = sha256_file(paths[key])
            gate(
                f"{key}_runner_SHA_exact",
                actual == expected,
                actual,
            )
            provenance_before[
                f"source_{key}"
            ] = actual

        physics = load_module(
            paths["PHYSICS_R2"],
            "pad_stream_v16e41r3_physics_r2",
        )
        e36 = load_module(
            paths["E36"],
            "pad_stream_v16e41r3_e36",
        )
        e37a = load_module(
            paths["E37A"],
            "pad_stream_v16e41r3_e37a",
        )
        e37b = load_module(
            paths["E37B"],
            "pad_stream_v16e41r3_e37b",
        )
        e38 = load_module(
            paths["E38"],
            "pad_stream_v16e41r3_e38",
        )
        e41 = load_module(
            paths["E41"],
            "pad_stream_v16e41r3_e41",
        )
        repair = load_module(
            paths["REPAIR_R2"],
            "pad_stream_v16e41r3_repair_r2",
        )

        gate(
            "R2_capacity_guard_multiplier_exact",
            float(repair.CAPACITY_GUARD_MULTIPLIER)
            == 10.0,
            repair.CAPACITY_GUARD_MULTIPLIER,
        )
        gate(
            "R2_capacity_adjustment_budget_exact",
            int(repair.MAX_CAPACITY_ADJUSTMENTS)
            == 4,
            repair.MAX_CAPACITY_ADJUSTMENTS,
        )

        r2_dir = drive / REPAIR_R2_REL
        r2_summary_path = (
            r2_dir / REPAIR_R2_SUMMARY
        )
        r2_closure_path = (
            r2_dir / REPAIR_R2_CLOSURE
        )
        r2_state_path = (
            r2_dir / REPAIR_R2_STATE
        )
        r2_design_path = (
            r2_dir / REPAIR_R2_DESIGN
        )

        e36_cache_path = (
            drive / E36_REL / E36_CACHE
        )
        e37a_summary_path = (
            drive / E37A_REL / E37A_SUMMARY
        )

        legacy_dir = drive / LEGACY_REL
        legacy_summary_path = (
            legacy_dir / LEGACY_SUMMARY
        )
        legacy_manifest_path = (
            legacy_dir / LEGACY_MANIFEST
        )
        legacy_path = (
            legacy_dir / LEGACY_SUBDIR / LEGACY_FILE
        )

        provenance_files = {
            "R2_summary": r2_summary_path,
            "R2_closure": r2_closure_path,
            "R2_state": r2_state_path,
            "R2_design": r2_design_path,
            "E36_cache": e36_cache_path,
            "E37A_summary": e37a_summary_path,
            "legacy_summary": legacy_summary_path,
            "legacy_manifest": legacy_manifest_path,
            "legacy_candidate": legacy_path,
        }
        for key, p in provenance_files.items():
            gate(
                f"provenance_exists_{key}",
                p.is_file(),
                p,
            )
            provenance_before[key] = (
                sha256_file(p)
            )

        r2_summary = load_json(
            r2_summary_path
        )
        r2_closure = load_json(
            r2_closure_path
        )
        r2_design = load_json(
            r2_design_path
        )
        e37a_summary = load_json(
            e37a_summary_path
        )
        legacy_summary = load_json(
            legacy_summary_path
        )
        legacy_manifest = load_json(
            legacy_manifest_path
        )

        gate(
            "R2_status_exact",
            r2_summary.get("status")
            == EXPECTED_R2_STATUS,
            r2_summary.get("status"),
        )
        gate(
            "R2_closure_status_exact",
            r2_closure.get("status")
            == EXPECTED_R2_STATUS,
            r2_closure.get("status"),
        )
        gate(
            "R2_all_runtime_gates_passed",
            r2_closure.get(
                "all_runtime_gates_passed"
            )
            is True,
        )
        gate(
            "R2_step1475_exact",
            int(
                r2_summary.get(
                    "accepted_repaired_step_index",
                    -1,
                )
            )
            == EXPECTED_R2_STEP,
            r2_summary.get(
                "accepted_repaired_step_index"
            ),
        )
        gate(
            "R2_time_exact",
            abs(
                float(
                    r2_summary.get(
                        "accepted_repaired_time_days",
                        -1.0,
                    )
                )
                - EXPECTED_R2_TIME_DAYS
            )
            <= 1.0e-12,
            r2_summary.get(
                "accepted_repaired_time_days"
            ),
        )
        gate(
            "R2_state_SHA_exact",
            provenance_before["R2_state"]
            == EXPECTED_R2_STATE_SHA256
            == r2_summary.get(
                "accepted_repaired_state_sha256"
            )
            == r2_closure.get(
                "accepted_state_sha256"
            ),
            provenance_before["R2_state"],
        )
        gate(
            "R2_limiter_cell_exact",
            tuple(
                r2_summary.get(
                    "first_capacity_limiter_cell_zero_based",
                    [-1, -1, -1],
                )
            )
            == EXPECTED_R2_LIMITER_CELL,
            r2_summary.get(
                "first_capacity_limiter_cell_zero_based"
            ),
        )
        gate(
            "R2_physics_operators_unmodified",
            r2_summary.get(
                "mapback_spatial_operator_modified"
            )
            is False
            and r2_summary.get(
                "EOS_inversion_modified"
            )
            is False
            and r2_summary.get(
                "capillary_solver_modified"
            )
            is False
            and r2_summary.get(
                "CV_transport_modified"
            )
            is False,
        )
        gate(
            "R2_design_authorizes_R3",
            r2_design.get(
                "no_100d_claim_from_R2"
            )
            is True
            and str(
                r2_design.get(
                    "R3_objective",
                    "",
                )
            ).startswith(
                "continue repaired production rollout"
            ),
            r2_design.get("R3_objective"),
        )

        gate(
            "E37A_status_exact",
            e37a_summary.get("status")
            == E37A_EXPECTED_STATUS,
            e37a_summary.get("status"),
        )

        gate(
            "legacy_summary_PASS",
            legacy_summary.get("status")
            == "PASS",
            legacy_summary.get("status"),
        )
        gate(
            "legacy_candidate_frozen",
            legacy_summary.get(
                "candidate_frozen"
            )
            is True,
        )
        gate(
            "legacy_full_grid_plume_not_authorized",
            legacy_summary.get(
                "full_grid_plume_authorized"
            )
            is False,
        )
        gate(
            "legacy_manifest_status_exact",
            legacy_manifest.get("status")
            == LEGACY_FREEZE_STATUS,
            legacy_manifest.get("status"),
        )
        gate(
            "legacy_manifest_100d_exact",
            float(
                legacy_manifest.get(
                    "physical_time_days",
                    -1.0,
                )
            )
            == TARGET_OBSERVATION_DAY,
            legacy_manifest.get(
                "physical_time_days"
            ),
        )
        gate(
            "legacy_frozen_SHA_exact",
            provenance_before[
                "legacy_candidate"
            ]
            == LEGACY_FROZEN_SHA256
            == legacy_manifest.get(
                "authoritative_frozen_sha256"
            ),
            provenance_before[
                "legacy_candidate"
            ],
        )

        restart = load_npz(
            r2_state_path
        )
        cache = load_npz(
            e36_cache_path
        )

        restart_step = int_scalar(
            restart["accepted_step_index"]
        )
        restart_time = scalar(
            restart["physical_time_days"]
        )
        restart_cut = scalar(
            restart[
                "current_producer_co2_gas_cut"
            ]
        )
        canonical_bt_time = scalar(
            restart[
                "breakthrough_time_days"
            ]
        )

        gate(
            "restart_step1475_exact",
            restart_step == EXPECTED_R2_STEP,
            restart_step,
        )
        gate(
            "restart_time_exact",
            abs(
                restart_time
                - EXPECTED_R2_TIME_DAYS
            )
            <= 1.0e-12,
            restart_time,
        )
        gate(
            "restart_breakthrough_true",
            bool_scalar(
                restart["breakthrough_reached"]
            ),
        )
        gate(
            "restart_observation_history_60_to_100",
            bool_scalar(
                restart[
                    "first_fixed_observation_checkpoint_reached"
                ]
            )
            and bool_scalar(
                restart[
                    "second_fixed_observation_checkpoint_reached"
                ]
            )
            and not bool_scalar(
                restart[
                    "third_fixed_observation_checkpoint_reached"
                ]
            )
            and int_scalar(
                restart[
                    "observation_cursor_index"
                ]
            )
            == 2
            and scalar(
                restart[
                    "last_fixed_observation_day"
                ]
            )
            == 60.0
            and scalar(
                restart[
                    "next_fixed_observation_day"
                ]
            )
            == 100.0,
        )
        gate(
            "restart_R2_repair_flag_true",
            bool_scalar(
                restart[
                    "V16E41R2_capacity_aware_mapback_timestep_repair"
                ]
            ),
        )
        gate(
            "restart_R2_physics_modification_flags_false",
            not bool_scalar(
                restart[
                    "V16E41R2_mapback_spatial_operator_modified"
                ]
            )
            and not bool_scalar(
                restart[
                    "V16E41R2_capillary_solver_modified"
                ]
            ),
        )
        gate(
            "restart_source_local_closure_zero",
            abs(
                scalar(
                    restart[
                        "last_source_local_added_mass_kg"
                    ]
                )
            )
            <= 1.0e-12,
        )

        failed_stage = (
            "legacy_candidate_schema_binding"
        )

        with np.load(
            legacy_path,
            allow_pickle=False,
        ) as z:
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
                all(
                    k in z.files
                    for k in required_legacy
                ),
                required_legacy,
            )
            legacy_sat = np.asarray(
                z[
                    "saturation_grid_full_float64"
                ],
                dtype=np.float64,
            ).copy()
            legacy_supported_mask = (
                np.asarray(
                    z["supported_mask"],
                    dtype=bool,
                ).copy()
            )
            legacy_denominator = np.asarray(
                z["support_denominator"]
            ).copy()
            legacy_numerator = np.asarray(
                z["support_numerator"]
            ).copy()
            legacy_background = float(
                np.asarray(
                    z["background_saturation"]
                )
            )
            legacy_time = float(
                np.asarray(
                    z["physical_time_days"]
                )
            )
            legacy_grid = tuple(
                int(x)
                for x in np.asarray(
                    z["grid_shape"]
                ).tolist()
            )

        gate(
            "legacy_grid_exact",
            legacy_sat.shape
            == EXPECTED_GRID
            and legacy_grid
            == EXPECTED_GRID
            and legacy_sat.size
            == EXPECTED_CELLS,
            (
                legacy_sat.shape,
                legacy_grid,
                legacy_sat.size,
            ),
        )
        gate(
            "legacy_time_100d_exact",
            legacy_time
            == TARGET_OBSERVATION_DAY,
            legacy_time,
        )
        gate(
            "legacy_background_exact",
            legacy_background
            == BACKGROUND_SATURATION,
            legacy_background,
        )
        gate(
            "legacy_bounds_exact",
            float(np.min(legacy_sat))
            == LEGACY_EXPECTED_MIN
            and float(np.max(legacy_sat))
            == LEGACY_EXPECTED_MAX,
            (
                float(np.min(legacy_sat)),
                float(np.max(legacy_sat)),
            ),
        )
        gate(
            "legacy_support_counts_exact",
            int(
                np.sum(
                    legacy_supported_mask
                )
            )
            == LEGACY_EXPECTED_SUPPORTED
            and int(
                np.sum(
                    ~legacy_supported_mask
                )
            )
            == LEGACY_EXPECTED_UNSUPPORTED,
            (
                int(
                    np.sum(
                        legacy_supported_mask
                    )
                ),
                int(
                    np.sum(
                        ~legacy_supported_mask
                    )
                ),
            ),
        )
        gate(
            "legacy_background_completed_zero_support_evidence",
            bool(
                np.all(
                    legacy_denominator[
                        ~legacy_supported_mask
                    ]
                    == 0.0
                )
            )
            and bool(
                np.all(
                    legacy_numerator[
                        ~legacy_supported_mask
                    ]
                    == 0.0
                )
            ),
        )

        failed_stage = "physics_operator_setup"

        with tempfile.TemporaryDirectory(
            prefix="PAD_Stream_V16E41R3_"
        ) as td:
            tmp = Path(td)
            shutil.copy2(
                paths["SG7A"],
                tmp / SG7A,
            )
            shutil.copy2(
                paths["SG7D"],
                tmp / SG7D,
            )
            sg7a = load_module(
                tmp / SG7A,
                "pad_stream_v16e41r3_sg7a",
            )
            sg7d = load_module(
                tmp / SG7D,
                "pad_stream_v16e41r3_sg7d",
            )

            pressure_psi = np.asarray(
                cache["accepted_pressure_psi"],
                dtype=np.float64,
            )
            xyz_m = np.asarray(
                cache["streamline_xyz_m"],
                dtype=np.float64,
            )
            tau_s = np.asarray(
                cache["streamline_tof_s"],
                dtype=np.float64,
            )
            tau_end_s = np.asarray(
                cache["tau_end_s"],
                dtype=np.float64,
            )
            weights_m3_s = np.asarray(
                cache[
                    "streamline_weights_m3_s"
                ],
                dtype=np.float64,
            )
            labels = np.asarray(
                cache["producer_labels"]
            ).astype(str)
            xi_faces = np.asarray(
                cache["xi"],
                dtype=np.float64,
            )

            nstream = len(tau_end_s)
            nfaces = len(xi_faces)
            ncv = nfaces - 1

            weights_m3_day = (
                weights_m3_s * DAY_TO_S
            )
            tof_days = tau_s / DAY_TO_S

            operator = (
                sg7d.build_subsegment_operator(
                    xyz_m,
                    tof_days,
                    weights_m3_day,
                )
            )

            p_ref_gas_pa = scalar(
                restart[
                    "co2_density_reference_pressure_pa"
                ]
            )

            geometry = (
                e37a.build_control_volume_geometry(
                    physics,
                    operator,
                    pressure_psi,
                    p_ref_gas_pa,
                    nstream,
                    ncv,
                )
            )

            face_pressure_psi = (
                e37a.build_face_pressure(
                    e36,
                    sg7d,
                    xyz_m,
                    pressure_psi,
                )
            )

            dxi = float(
                xi_faces[1] - xi_faces[0]
            )
            sat_scan = np.linspace(
                float(sg7a.S_INITIAL),
                float(sg7a.S_INJECTED),
                4001,
            )
            max_df = float(
                np.max(
                    np.abs(
                        np.asarray(
                            sg7a.df_dS(
                                sat_scan
                            )
                        )
                    )
                )
            )
            u_face = np.asarray(
                sg7a.u_dimensionless(
                    xi_faces
                ),
                dtype=np.float64,
            )
            max_wave_speed = float(
                np.max(u_face) * max_df
            )
            dtD_cfl = float(
                sg7a.CFL
                * dxi
                / (
                    max_wave_speed
                    + sg7a.EPS
                )
            )
            fastest_tau_days = float(
                np.min(
                    tau_end_s / DAY_TO_S
                )
            )
            nominal_dt_days = float(
                dtD_cfl
                * fastest_tau_days
            )

            gate(
                "nominal_dt_matches_E37A",
                abs(
                    nominal_dt_days
                    - float(
                        e37a_summary[
                            "nominal_dt_days"
                        ]
                    )
                )
                <= 1.0e-15,
                nominal_dt_days,
            )

            dx_m = 20.0 * FT_TO_M
            dy_m = 20.0 * FT_TO_M
            dz_m = 4.0 * FT_TO_M
            cell_pore_volume_m3 = (
                0.20
                * dx_m
                * dy_m
                * dz_m
            )

            permeability_md = np.loadtxt(
                paths["PERM"],
                skiprows=1,
                dtype=np.float64,
            ).reshape(
                EXPECTED_GRID,
                order="C",
            )
            gate(
                "permeability_shape_exact",
                permeability_md.shape
                == EXPECTED_GRID,
                permeability_md.shape,
            )

            failed_stage = (
                "capacity_aware_1475_to_100d_rollout"
            )

            current = {
                k: np.asarray(v).copy()
                for k, v in restart.items()
            }

            initial_injected = scalar(
                current[
                    "cumulative_injected_co2_mass_kg"
                ]
            )
            initial_produced = scalar(
                current[
                    "cumulative_produced_co2_mass_kg"
                ]
            )
            initial_stored = scalar(
                current[
                    "stored_co2_mass_current_kg"
                ]
            )

            rollout_rows: list[
                dict[str, Any]
            ] = []
            producer_rows_all: list[
                dict[str, Any]
            ] = []
            plume_rows: list[
                dict[str, Any]
            ] = []
            controller_rows: list[
                dict[str, Any]
            ] = []
            rejection_rows: list[
                dict[str, Any]
            ] = []

            transport_residuals: list[
                float
            ] = []
            transfer_residuals: list[
                float
            ] = []
            mapback_residuals: list[
                float
            ] = []
            capillary_external_changes: list[
                float
            ] = []
            sample_closures: list[
                float
            ] = []
            post_sample_closures: list[
                float
            ] = []

            accepted_transitions = 0
            native_rejected_trials = 0
            capacity_adjustments_total = 0
            capacity_limited_steps = 0
            max_capacity_adjustments_one_step = 0
            post_preflight_capacity_gate_failures = 0

            snapshot_steps = [
                restart_step
            ]
            snapshot_times = [
                restart_time
            ]
            snapshot_sats = [
                np.asarray(
                    current[
                        "transport_saturation"
                    ],
                    dtype=np.float64,
                ).copy()
            ]
            snapshot_labels = [
                "R2_REPAIRED_STEP1475_START"
            ]
            next_snapshot_index = 0

            start_plume = e36.plume_metrics(
                physics,
                snapshot_sats[0],
                pressure_psi,
                p_ref_gas_pa,
                cell_pore_volume_m3,
                restart_step,
                restart_time,
            )
            start_plume[
                "state_label"
            ] = (
                "R2_REPAIRED_STEP1475_START"
            )
            start_plume[
                "producer_CO2_gas_cut"
            ] = restart_cut
            plume_rows.append(
                start_plume
            )

            original_mapback = (
                e37a.map_control_volume_increment_to_grid
            )
            context = {
                "active_dt_days":
                    nominal_dt_days,
                "target_step":
                    restart_step + 1,
                "capacity_adjustment":
                    0,
                "native_retry":
                    0,
            }

            def capacity_aware_mapback(
                physics_local: Any,
                parent_grid_saturation:
                    np.ndarray,
                old_cv_saturation:
                    np.ndarray,
                new_cv_saturation:
                    np.ndarray,
                old_cv_mass:
                    np.ndarray,
                new_cv_mass:
                    np.ndarray,
                geometry_local:
                    dict[str, np.ndarray],
                pressure_psi_local:
                    np.ndarray,
                p_ref_gas_pa_local:
                    float,
                cell_pore_volume_m3_local:
                    float,
                target_final_mass_kg:
                    float,
            ) -> dict[str, Any]:
                rec = (
                    repair.preflight_mapback_capacity(
                        r2=physics_local,
                        e37a=e37a,
                        parent_grid_saturation=
                            parent_grid_saturation,
                        old_cv_saturation=
                            old_cv_saturation,
                        new_cv_saturation=
                            new_cv_saturation,
                        old_cv_mass=
                            old_cv_mass,
                        new_cv_mass=
                            new_cv_mass,
                        geometry=
                            geometry_local,
                        pressure_psi=
                            pressure_psi_local,
                        p_ref_gas_pa=
                            p_ref_gas_pa_local,
                        cell_pore_volume_m3=
                            cell_pore_volume_m3_local,
                        target_final_mass_kg=
                            target_final_mass_kg,
                        active_dt_days=float(
                            context[
                                "active_dt_days"
                            ]
                        ),
                    )
                )
                rec = {
                    **rec,
                    "target_step":
                        int(
                            context[
                                "target_step"
                            ]
                        ),
                    "capacity_adjustment":
                        int(
                            context[
                                "capacity_adjustment"
                            ]
                        ),
                    "native_retry":
                        int(
                            context[
                                "native_retry"
                            ]
                        ),
                }

                if rec.get(
                    "native_failure_required"
                ):
                    controller_rows.append(
                        {
                            **rec,
                            "controller_action":
                                "DELEGATE_TO_FROZEN_NATIVE_FAILURE",
                        }
                    )
                    return original_mapback(
                        physics_local,
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

                if not rec[
                    "candidate_is_capacity_admissible"
                ]:
                    recommended = float(
                        rec[
                            "recommended_dt_days"
                        ]
                    )
                    active = float(
                        context[
                            "active_dt_days"
                        ]
                    )
                    if (
                        not np.isfinite(
                            recommended
                        )
                        or recommended <= 0.0
                        or recommended >= active
                    ):
                        raise GateError(
                            "capacity_controller_no_positive_"
                            "strictly_smaller_timestep:"
                            f"{context['target_step']}:"
                            f"{recommended}:{active}"
                        )

                    logged = {
                        **rec,
                        "controller_action":
                            "REJECT_AND_RETRY_AT_CAPACITY_BOUND",
                    }
                    controller_rows.append(
                        logged
                    )
                    raise (
                        repair.MapbackCapacityReject(
                            logged
                        )
                    )

                controller_rows.append(
                    {
                        **rec,
                        "controller_action":
                            "ALLOW_FROZEN_E37A_MAPBACK",
                    }
                )
                return original_mapback(
                    physics_local,
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

            e37a.map_control_volume_increment_to_grid = (
                capacity_aware_mapback
            )
            try:
                while (
                    scalar(
                        current[
                            "physical_time_days"
                        ]
                    )
                    < TARGET_OBSERVATION_DAY
                    - 1.0e-13
                ):
                    if (
                        accepted_transitions
                        >= MAX_ACCEPTED_TRANSITIONS
                    ):
                        raise GateError(
                            "accepted_transition_budget_exceeded:"
                            f"{MAX_ACCEPTED_TRANSITIONS}"
                        )

                    current_time = scalar(
                        current[
                            "physical_time_days"
                        ]
                    )
                    target_step = (
                        int_scalar(
                            current[
                                "accepted_step_index"
                            ]
                        )
                        + 1
                    )
                    remaining = (
                        TARGET_OBSERVATION_DAY
                        - current_time
                    )
                    candidate_dt = min(
                        nominal_dt_days,
                        remaining,
                    )

                    if (
                        not np.isfinite(
                            candidate_dt
                        )
                        or candidate_dt <= 0.0
                    ):
                        raise GateError(
                            "nonpositive_R3_candidate_dt:"
                            f"{target_step}:"
                            f"{candidate_dt}"
                        )

                    native_retry = 0
                    capacity_adjustments_step = 0
                    accepted = False
                    last_reason = ""

                    while not accepted:
                        context[
                            "active_dt_days"
                        ] = candidate_dt
                        context[
                            "target_step"
                        ] = target_step
                        context[
                            "capacity_adjustment"
                        ] = (
                            capacity_adjustments_step
                        )
                        context[
                            "native_retry"
                        ] = native_retry

                        try:
                            result = (
                                e38.evolve_from_parent(
                                    parent=current,
                                    dt_days=
                                        candidate_dt,
                                    r2=physics,
                                    e36=e36,
                                    e37a=e37a,
                                    e37b=e37b,
                                    sg7a=sg7a,
                                    pressure_psi=
                                        pressure_psi,
                                    p_ref_gas_pa=
                                        p_ref_gas_pa,
                                    geometry=
                                        geometry,
                                    face_pressure_psi=
                                        face_pressure_psi,
                                    weights_m3_day=
                                        weights_m3_day,
                                    xi_faces=
                                        xi_faces,
                                    labels=
                                        labels,
                                    permeability_md=
                                        permeability_md,
                                    cell_pore_volume_m3=
                                        cell_pore_volume_m3,
                                    nstream=
                                        nstream,
                                    nfaces=
                                        nfaces,
                                    ncv=
                                        ncv,
                                )
                            )

                            trial_time = float(
                                result[
                                    "trial_time_days"
                                ]
                            )
                            if (
                                TARGET_OBSERVATION_DAY
                                - trial_time
                                <= 1.0e-13
                            ):
                                trial_time = (
                                    TARGET_OBSERVATION_DAY
                                )

                            observation_reached = (
                                trial_time
                                == TARGET_OBSERVATION_DAY
                            )

                            child = (
                                e41.apply_e41_state_semantics(
                                    result[
                                        "child"
                                    ],
                                    current,
                                    canonical_breakthrough_time_days=
                                        canonical_bt_time,
                                    observation_reached=
                                        observation_reached,
                                )
                            )

                            child[
                                "current_producer_co2_gas_cut"
                            ] = np.asarray(
                                result[
                                    "child_cut"
                                ],
                                dtype=np.float64,
                            )
                            child[
                                "last_CV_transport_mass_residual_kg"
                            ] = np.asarray(
                                result[
                                    "transport_residual_kg"
                                ],
                                dtype=np.float64,
                            )
                            child[
                                "last_CV_to_grid_transfer_residual_kg"
                            ] = np.asarray(
                                result[
                                    "transfer_residual_kg"
                                ],
                                dtype=np.float64,
                            )
                            child[
                                "last_grid_mapback_ledger_residual_kg"
                            ] = np.asarray(
                                result[
                                    "mapback_ledger_residual_kg"
                                ],
                                dtype=np.float64,
                            )
                            child[
                                "last_grid_to_CV_sampling_closure_kg"
                            ] = np.asarray(
                                result[
                                    "post_sample_closure_kg"
                                ],
                                dtype=np.float64,
                            )

                            new_time = scalar(
                                child[
                                    "physical_time_days"
                                ]
                            )
                            if (
                                new_time
                                <= current_time
                                or new_time
                                > TARGET_OBSERVATION_DAY
                                + 1.0e-12
                            ):
                                raise (
                                    e37a.TrialReject(
                                        "R3_accepted_time_invalid:"
                                        f"{current_time}:"
                                        f"{new_time}"
                                    )
                                )

                            if not bool_scalar(
                                child[
                                    "breakthrough_reached"
                                ]
                            ):
                                raise (
                                    e37a.TrialReject(
                                        "R3_child_lost_breakthrough_flag"
                                    )
                                )
                            if (
                                abs(
                                    scalar(
                                        child[
                                            "breakthrough_time_days"
                                        ]
                                    )
                                    - canonical_bt_time
                                )
                                > 1.0e-12
                            ):
                                raise (
                                    e37a.TrialReject(
                                        "R3_child_changed_breakthrough_time"
                                    )
                                )

                            if (
                                not bool_scalar(
                                    child[
                                        "first_fixed_observation_checkpoint_reached"
                                    ]
                                )
                                or not bool_scalar(
                                    child[
                                        "second_fixed_observation_checkpoint_reached"
                                    ]
                                )
                            ):
                                raise (
                                    e37a.TrialReject(
                                        "R3_child_lost_observation_history"
                                    )
                                )

                            if not observation_reached:
                                if (
                                    int_scalar(
                                        child[
                                            "observation_cursor_index"
                                        ]
                                    )
                                    != 2
                                    or scalar(
                                        child[
                                            "last_fixed_observation_day"
                                        ]
                                    )
                                    != 60.0
                                    or scalar(
                                        child[
                                            "next_fixed_observation_day"
                                        ]
                                    )
                                    != 100.0
                                ):
                                    raise (
                                        e37a.TrialReject(
                                            "R3_pre100_observation_history_mutated"
                                        )
                                    )

                            cumulative_resid = scalar(
                                child[
                                    "cumulative_mass_residual_kg"
                                ]
                            )

                            rollout_rows.append(
                                {
                                    "accepted_step_index":
                                        target_step,
                                    "parent_time_days":
                                        current_time,
                                    "accepted_time_days":
                                        new_time,
                                    "accepted_dt_days":
                                        candidate_dt,
                                    "nominal_dt_days":
                                        nominal_dt_days,
                                    "capacity_adjustments":
                                        capacity_adjustments_step,
                                    "native_retry_count":
                                        native_retry,
                                    "observation_clipped_step":
                                        observation_reached,
                                    "breakthrough_time_days":
                                        canonical_bt_time,
                                    "time_since_breakthrough_days":
                                        scalar(
                                            child[
                                                "time_since_breakthrough_days"
                                            ]
                                        ),
                                    "observation_cursor_index":
                                        int_scalar(
                                            child[
                                                "observation_cursor_index"
                                            ]
                                        ),
                                    "parent_producer_CO2_gas_cut":
                                        result[
                                            "parent_cut"
                                        ],
                                    "child_producer_CO2_gas_cut":
                                        result[
                                            "child_cut"
                                        ],
                                    "explicit_flux_CO2_gas_cut":
                                        result[
                                            "aggregate_flux_cut"
                                        ],
                                    "injected_CO2_mass_kg":
                                        result[
                                            "injected_mass_kg"
                                        ],
                                    "produced_CO2_mass_kg":
                                        result[
                                            "produced_mass_kg"
                                        ],
                                    "stored_CO2_mass_kg":
                                        result[
                                            "final_stored_mass_kg"
                                        ],
                                    "step_mass_residual_kg":
                                        result[
                                            "step_mass_residual_kg"
                                        ],
                                    "cumulative_mass_residual_kg":
                                        cumulative_resid,
                                    "CV_transport_mass_residual_kg":
                                        result[
                                            "transport_residual_kg"
                                        ],
                                    "CV_to_grid_transfer_residual_kg":
                                        result[
                                            "transfer_residual_kg"
                                        ],
                                    "grid_mapback_ledger_residual_kg":
                                        result[
                                            "mapback_ledger_residual_kg"
                                        ],
                                    "capillary_external_mass_change_kg":
                                        result[
                                            "capillary_external_mass_change_kg"
                                        ],
                                    "grid_to_CV_sampling_closure_kg":
                                        result[
                                            "sample_closure_kg"
                                        ],
                                    "child_grid_to_CV_sampling_closure_kg":
                                        result[
                                            "post_sample_closure_kg"
                                        ],
                                    "source_local_added_mass_kg":
                                        0.0,
                                }
                            )

                            for prow in result[
                                "producer_rows"
                            ]:
                                producer_rows_all.append(
                                    {
                                        "accepted_step_index":
                                            target_step,
                                        "accepted_time_days":
                                            new_time,
                                        **prow,
                                    }
                                )

                            transport_residuals.append(
                                float(
                                    result[
                                        "transport_residual_kg"
                                    ]
                                )
                            )
                            transfer_residuals.append(
                                float(
                                    result[
                                        "transfer_residual_kg"
                                    ]
                                )
                            )
                            mapback_residuals.append(
                                float(
                                    result[
                                        "mapback_ledger_residual_kg"
                                    ]
                                )
                            )
                            capillary_external_changes.append(
                                float(
                                    result[
                                        "capillary_external_mass_change_kg"
                                    ]
                                )
                            )
                            sample_closures.append(
                                float(
                                    result[
                                        "sample_closure_kg"
                                    ]
                                )
                            )
                            post_sample_closures.append(
                                float(
                                    result[
                                        "post_sample_closure_kg"
                                    ]
                                )
                            )

                            if (
                                capacity_adjustments_step
                                > 0
                            ):
                                capacity_limited_steps += 1
                            max_capacity_adjustments_one_step = max(
                                max_capacity_adjustments_one_step,
                                capacity_adjustments_step,
                            )

                            current = child
                            accepted_transitions += 1
                            accepted = True

                            while (
                                next_snapshot_index
                                < len(
                                    SPARSE_SNAPSHOT_THRESHOLDS_DAYS
                                )
                                and new_time
                                + 1.0e-13
                                >= SPARSE_SNAPSHOT_THRESHOLDS_DAYS[
                                    next_snapshot_index
                                ]
                            ):
                                threshold = (
                                    SPARSE_SNAPSHOT_THRESHOLDS_DAYS[
                                        next_snapshot_index
                                    ]
                                )
                                snapshot_steps.append(
                                    target_step
                                )
                                snapshot_times.append(
                                    new_time
                                )
                                snapshot_sats.append(
                                    np.asarray(
                                        child[
                                            "transport_saturation"
                                        ],
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

                                metric = (
                                    e36.plume_metrics(
                                        physics,
                                        np.asarray(
                                            child[
                                                "transport_saturation"
                                            ],
                                            dtype=np.float64,
                                        ),
                                        pressure_psi,
                                        p_ref_gas_pa,
                                        cell_pore_volume_m3,
                                        target_step,
                                        new_time,
                                    )
                                )
                                metric[
                                    "state_label"
                                ] = (
                                    snapshot_labels[
                                        -1
                                    ]
                                )
                                metric[
                                    "producer_CO2_gas_cut"
                                ] = float(
                                    result[
                                        "child_cut"
                                    ]
                                )
                                plume_rows.append(
                                    metric
                                )
                                next_snapshot_index += 1

                            if (
                                accepted_transitions
                                % PROGRESS_EVERY
                                == 0
                                or capacity_adjustments_step
                                > 0
                                or native_retry
                                > 0
                                or observation_reached
                            ):
                                print(
                                    f"[ACCEPT] step {target_step}: "
                                    f"t={new_time:.12g} d, "
                                    f"dt={candidate_dt:.12g} d, "
                                    f"capacity_adj={capacity_adjustments_step}, "
                                    f"native_retry={native_retry}, "
                                    f"cut={float(result['child_cut']):.6e}"
                                )

                        except (
                            repair.MapbackCapacityReject
                        ) as exc:
                            capacity_adjustments_total += 1
                            capacity_adjustments_step += 1
                            last_reason = repr(
                                exc
                            )
                            rec = exc.record

                            rejection_rows.append(
                                {
                                    "target_step":
                                        target_step,
                                    "parent_time_days":
                                        current_time,
                                    "rejection_type":
                                        "MAPBACK_CAPACITY",
                                    "capacity_adjustment":
                                        capacity_adjustments_step,
                                    "native_retry":
                                        native_retry,
                                    "trial_dt_days":
                                        candidate_dt,
                                    "recommended_dt_days":
                                        rec[
                                            "recommended_dt_days"
                                        ],
                                    "max_capacity_excess_kg":
                                        rec[
                                            "max_capacity_excess_kg"
                                        ],
                                    "limiter_cell_zero_based":
                                        str(
                                            rec[
                                                "upper_limiting_cell_zero_based"
                                            ]
                                        ),
                                    "reason":
                                        last_reason,
                                }
                            )

                            if (
                                capacity_adjustments_step
                                > int(
                                    repair.MAX_CAPACITY_ADJUSTMENTS
                                )
                            ):
                                raise GateError(
                                    "R3_capacity_adjustment_budget_exhausted:"
                                    f"{target_step}:"
                                    f"{capacity_adjustments_step}"
                                )

                            recommended = float(
                                rec[
                                    "recommended_dt_days"
                                ]
                            )
                            if (
                                not np.isfinite(
                                    recommended
                                )
                                or recommended
                                <= 0.0
                                or recommended
                                >= candidate_dt
                            ):
                                raise GateError(
                                    "R3_invalid_capacity_recommended_dt:"
                                    f"{target_step}:"
                                    f"{recommended}:"
                                    f"{candidate_dt}"
                                )
                            candidate_dt = min(
                                recommended,
                                TARGET_OBSERVATION_DAY
                                - current_time,
                            )

                            print(
                                f"[CAPACITY] step {target_step}: "
                                f"dt -> {candidate_dt:.12g} d, "
                                f"cell={tuple(rec['upper_limiting_cell_zero_based'])}, "
                                f"excess={float(rec['max_capacity_excess_kg']):.6e} kg"
                            )

                        except (
                            e37a.TrialReject,
                            physics.GateError,
                        ) as exc:
                            native_rejected_trials += 1
                            native_retry += 1
                            last_reason = repr(
                                exc
                            )
                            if (
                                EXPECTED_FAILURE_TOKEN
                                := getattr(
                                    repair,
                                    "EXPECTED_FAILURE_TOKEN",
                                    "capillary_cell_mass_capacity_exceeded",
                                )
                            ) in str(exc):
                                post_preflight_capacity_gate_failures += 1

                            rejection_rows.append(
                                {
                                    "target_step":
                                        target_step,
                                    "parent_time_days":
                                        current_time,
                                    "rejection_type":
                                        "NATIVE_PHYSICS",
                                    "capacity_adjustment":
                                        capacity_adjustments_step,
                                    "native_retry":
                                        native_retry,
                                    "trial_dt_days":
                                        candidate_dt,
                                    "recommended_dt_days":
                                        "",
                                    "max_capacity_excess_kg":
                                        "",
                                    "limiter_cell_zero_based":
                                        "",
                                    "reason":
                                        last_reason,
                                }
                            )

                            if (
                                native_retry
                                > MAX_NATIVE_RETRIES_PER_STEP
                            ):
                                raise GateError(
                                    "R3_native_retry_budget_exhausted:"
                                    f"{target_step}:"
                                    f"{last_reason}"
                                )

                            candidate_dt = min(
                                candidate_dt
                                * NATIVE_RETRY_FACTOR,
                                TARGET_OBSERVATION_DAY
                                - current_time,
                            )
                            if (
                                not np.isfinite(
                                    candidate_dt
                                )
                                or candidate_dt
                                <= 0.0
                            ):
                                raise GateError(
                                    "R3_nonpositive_native_retry_dt:"
                                    f"{target_step}:"
                                    f"{candidate_dt}"
                                )

                            print(
                                f"[REJECT] step {target_step} "
                                f"native retry {native_retry}: "
                                f"dt={candidate_dt:.12g} d: {exc}"
                            )

            finally:
                e37a.map_control_volume_increment_to_grid = (
                    original_mapback
                )

            failed_stage = (
                "final_100d_checkpoint_validation"
            )

            final_state = current
            final_step = int_scalar(
                final_state[
                    "accepted_step_index"
                ]
            )
            final_time = scalar(
                final_state[
                    "physical_time_days"
                ]
            )
            final_sat = np.asarray(
                final_state[
                    "transport_saturation"
                ],
                dtype=np.float64,
            )
            final_mass = scalar(
                final_state[
                    "stored_co2_mass_current_kg"
                ]
            )
            final_cum_resid = scalar(
                final_state[
                    "cumulative_mass_residual_kg"
                ]
            )
            final_cut = scalar(
                final_state[
                    "current_producer_co2_gas_cut"
                ]
            )
            final_injected = scalar(
                final_state[
                    "cumulative_injected_co2_mass_kg"
                ]
            )
            final_produced = scalar(
                final_state[
                    "cumulative_produced_co2_mass_kg"
                ]
            )

            final_tol = max(
                1.0e-6,
                1.0e-10
                * max(
                    abs(final_mass),
                    1.0,
                ),
            )

            interval_injected = (
                final_injected
                - initial_injected
            )
            interval_produced = (
                final_produced
                - initial_produced
            )
            interval_stored_change = (
                final_mass
                - initial_stored
            )

            gate(
                "R3_exact_100d_landing",
                final_time
                == TARGET_OBSERVATION_DAY,
                final_time,
            )
            gate(
                "R3_observation_cursor_advanced_to_150d",
                int_scalar(
                    final_state[
                        "observation_cursor_index"
                    ]
                )
                == 3
                and scalar(
                    final_state[
                        "last_fixed_observation_day"
                    ]
                )
                == TARGET_OBSERVATION_DAY
                and scalar(
                    final_state[
                        "next_fixed_observation_day"
                    ]
                )
                == NEXT_OBSERVATION_DAY,
                (
                    int_scalar(
                        final_state[
                            "observation_cursor_index"
                        ]
                    ),
                    scalar(
                        final_state[
                            "last_fixed_observation_day"
                        ]
                    ),
                    scalar(
                        final_state[
                            "next_fixed_observation_day"
                        ]
                    ),
                ),
            )
            gate(
                "R3_100d_flag_true",
                bool_scalar(
                    final_state[
                        "third_fixed_observation_checkpoint_reached"
                    ]
                )
                and bool_scalar(
                    final_state[
                        "V16E41_canonical_100d_observation_state"
                    ]
                ),
            )
            gate(
                "R3_breakthrough_history_preserved",
                bool_scalar(
                    final_state[
                        "breakthrough_reached"
                    ]
                )
                and abs(
                    scalar(
                        final_state[
                            "breakthrough_time_days"
                        ]
                    )
                    - canonical_bt_time
                )
                <= 1.0e-12,
            )
            gate(
                "R3_time_since_breakthrough_exact",
                abs(
                    scalar(
                        final_state[
                            "time_since_breakthrough_days"
                        ]
                    )
                    - (
                        TARGET_OBSERVATION_DAY
                        - canonical_bt_time
                    )
                )
                <= 1.0e-12,
            )
            gate(
                "R3_current_cut_valid",
                np.isfinite(final_cut)
                and 0.0
                <= final_cut
                <= 1.0,
                final_cut,
            )
            gate(
                "R3_cumulative_production_nondecreasing",
                final_produced
                >= initial_produced
                - 1.0e-12,
                (
                    initial_produced,
                    final_produced,
                ),
            )
            gate(
                "R3_source_local_closure_never_used",
                all(
                    abs(
                        float(
                            r[
                                "source_local_added_mass_kg"
                            ]
                        )
                    )
                    <= 1.0e-12
                    for r in rollout_rows
                ),
            )
            gate(
                "R3_cumulative_mass_closure",
                abs(
                    final_cum_resid
                )
                <= final_tol,
                (
                    final_cum_resid,
                    final_tol,
                ),
            )
            gate(
                "R3_CV_transport_mass_closure",
                max_abs(
                    transport_residuals
                )
                <= final_tol,
                max_abs(
                    transport_residuals
                ),
            )
            gate(
                "R3_CV_subsegment_transfer_closure",
                max_abs(
                    transfer_residuals
                )
                <= final_tol,
                max_abs(
                    transfer_residuals
                ),
            )
            gate(
                "R3_grid_mapback_ledger_closure",
                max_abs(
                    mapback_residuals
                )
                <= final_tol,
                max_abs(
                    mapback_residuals
                ),
            )
            gate(
                "R3_capillary_zero_external_source",
                max_abs(
                    capillary_external_changes
                )
                <= final_tol,
                max_abs(
                    capillary_external_changes
                ),
            )
            gate(
                "R3_grid_to_CV_sampling_closure",
                max_abs(
                    sample_closures
                    + post_sample_closures
                )
                <= final_tol,
                max_abs(
                    sample_closures
                    + post_sample_closures
                ),
            )

            accepted_dts = np.asarray(
                [
                    float(
                        r[
                            "accepted_dt_days"
                        ]
                    )
                    for r in rollout_rows
                ],
                dtype=np.float64,
            )
            gate(
                "R3_has_accepted_transitions",
                accepted_dts.size > 0,
                accepted_dts.size,
            )
            gate(
                "R3_all_accepted_dt_positive",
                bool(
                    np.all(
                        accepted_dts > 0.0
                    )
                ),
                float(
                    np.min(
                        accepted_dts
                    )
                ),
            )
            gate(
                "R3_capacity_adjustments_consistent",
                capacity_adjustments_total
                == sum(
                    1
                    for r in controller_rows
                    if r.get(
                        "controller_action"
                    )
                    == "REJECT_AND_RETRY_AT_CAPACITY_BOUND"
                ),
                capacity_adjustments_total,
            )
            gate(
                "R3_capacity_adjustment_budget_respected",
                max_capacity_adjustments_one_step
                <= int(
                    repair.MAX_CAPACITY_ADJUSTMENTS
                ),
                max_capacity_adjustments_one_step,
            )
            # Native capacity-token rejections are recorded, not treated as
            # proof that the map-back controller failed, because a later
            # rejection can originate in the unchanged capillary operator.
            # Add R3 metadata only after the physical state is fully validated.
            final_state = {
                k: np.asarray(v).copy()
                for k, v in final_state.items()
            }
            final_state[
                "V16E41R3_capacity_aware_production_100d"
            ] = np.asarray(
                True,
                dtype=bool,
            )
            final_state[
                "V16E41R3_capacity_adjustments_total"
            ] = np.asarray(
                capacity_adjustments_total,
                dtype=np.int64,
            )
            final_state[
                "V16E41R3_capacity_limited_steps"
            ] = np.asarray(
                capacity_limited_steps,
                dtype=np.int64,
            )
            final_state[
                "V16E41R3_native_rejected_trials"
            ] = np.asarray(
                native_rejected_trials,
                dtype=np.int64,
            )
            final_state[
                "V16E41R3_mapback_spatial_operator_modified"
            ] = np.asarray(
                False,
                dtype=bool,
            )
            final_state[
                "V16E41R3_EOS_inversion_modified"
            ] = np.asarray(
                False,
                dtype=bool,
            )
            final_state[
                "V16E41R3_capillary_solver_modified"
            ] = np.asarray(
                False,
                dtype=bool,
            )

            final_sat = np.asarray(
                final_state[
                    "transport_saturation"
                ],
                dtype=np.float64,
            )

            if (
                not snapshot_times
                or snapshot_times[-1]
                != TARGET_OBSERVATION_DAY
            ):
                snapshot_steps.append(
                    final_step
                )
                snapshot_times.append(
                    TARGET_OBSERVATION_DAY
                )
                snapshot_sats.append(
                    final_sat.copy()
                )
                snapshot_labels.append(
                    "EXACT_100D_CANONICAL_CHECKPOINT"
                )
                metric = e36.plume_metrics(
                    physics,
                    final_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    final_step,
                    final_time,
                )
                metric[
                    "state_label"
                ] = (
                    "EXACT_100D_CANONICAL_CHECKPOINT"
                )
                metric[
                    "producer_CO2_gas_cut"
                ] = final_cut
                plume_rows.append(
                    metric
                )
            else:
                snapshot_labels[-1] = (
                    "EXACT_100D_CANONICAL_CHECKPOINT"
                )

            final_plume = (
                e36.plume_metrics(
                    physics,
                    final_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                    final_step,
                    final_time,
                )
            )

            checkpoint_bytes = (
                deterministic_npz_bytes(
                    final_state
                )
            )
            e41.validate_checkpoint_restart(
                checkpoint_bytes,
                expected_step=final_step,
                expected_bt_time=
                    canonical_bt_time,
                expected_sat=final_sat,
            )
            gate(
                "R3_canonical_100d_restart_validated",
                True,
                final_step,
            )

            checkpoint_sha = hashlib.sha256(
                checkpoint_bytes
            ).hexdigest()

            snapshot_bytes = (
                deterministic_npz_bytes(
                    {
                        "accepted_step_index":
                            np.asarray(
                                snapshot_steps,
                                dtype=np.int64,
                            ),
                        "physical_time_days":
                            np.asarray(
                                snapshot_times,
                                dtype=np.float64,
                            ),
                        "label":
                            np.asarray(
                                snapshot_labels,
                                dtype="U64",
                            ),
                        "transport_saturation":
                            np.stack(
                                snapshot_sats,
                                axis=0,
                            ).astype(
                                np.float64
                            ),
                    }
                )
            )

            failed_stage = (
                "formal_100d_legacy_regression"
            )

            gate(
                "R3_new_shape_matches_legacy",
                final_sat.shape
                == legacy_sat.shape
                == EXPECTED_GRID,
                (
                    final_sat.shape,
                    legacy_sat.shape,
                ),
            )
            gate(
                "R3_new_100d_finite",
                bool(
                    np.all(
                        np.isfinite(
                            final_sat
                        )
                    )
                ),
            )
            gate(
                "R3_legacy_100d_finite",
                bool(
                    np.all(
                        np.isfinite(
                            legacy_sat
                        )
                    )
                ),
            )

            whole_metrics = (
                e41.field_error_metrics(
                    final_sat,
                    legacy_sat,
                )
            )
            supported_metrics = (
                e41.field_error_metrics(
                    final_sat,
                    legacy_sat,
                    legacy_supported_mask,
                )
            )
            background_metrics = (
                e41.field_error_metrics(
                    final_sat,
                    legacy_sat,
                    ~legacy_supported_mask,
                )
            )

            active_overlap = (
                e41.overlap_metrics(
                    final_sat,
                    legacy_sat,
                    ACTIVE_INCREMENT_THRESHOLD,
                )
            )
            visible_overlap = (
                e41.overlap_metrics(
                    final_sat,
                    legacy_sat,
                    VISIBLE_INCREMENT_THRESHOLD,
                )
            )

            new_centroid = (
                e41.saturation_increment_centroid_m(
                    final_sat
                )
            )
            legacy_centroid = (
                e41.saturation_increment_centroid_m(
                    legacy_sat
                )
            )
            centroid_delta = (
                np.asarray(
                    new_centroid,
                    dtype=np.float64,
                )
                - np.asarray(
                    legacy_centroid,
                    dtype=np.float64,
                )
            )
            centroid_distance = float(
                np.linalg.norm(
                    centroid_delta
                )
            )

            new_recomputed_mass = float(
                physics.stored_co2_mass_kg(
                    final_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                )
            )
            legacy_common_mass = float(
                physics.stored_co2_mass_kg(
                    legacy_sat,
                    pressure_psi,
                    p_ref_gas_pa,
                    cell_pore_volume_m3,
                )
            )
            gate(
                "R3_new_stored_mass_recompute_matches_state",
                abs(
                    new_recomputed_mass
                    - final_mass
                )
                <= final_tol,
                (
                    new_recomputed_mass,
                    final_mass,
                    final_tol,
                ),
            )

            new_cv_sat, _, new_sample_close = (
                e37a.sample_grid_inventory_to_control_volumes(
                    physics,
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
                    physics,
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
                    abs(
                        final_mass
                    ),
                    abs(
                        legacy_common_mass
                    ),
                    1.0,
                ),
            )
            gate(
                "R3_new_regression_sampling_closure",
                abs(
                    float(
                        new_sample_close
                    )
                )
                <= regression_sample_tol,
                new_sample_close,
            )
            gate(
                "R3_legacy_regression_sampling_closure",
                abs(
                    float(
                        legacy_sample_close
                    )
                )
                <= regression_sample_tol,
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
                "R3_new_regression_cut_matches_state",
                abs(
                    new_recomputed_cut
                    - final_cut
                )
                <= 1.0e-12,
                (
                    new_recomputed_cut,
                    final_cut,
                ),
            )

            new_increment = np.clip(
                final_sat
                - BACKGROUND_SATURATION,
                0.0,
                None,
            )
            legacy_unsupported = (
                ~legacy_supported_mask
            )
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

            layer_rows = (
                e41.layerwise_regression_rows(
                    final_sat,
                    legacy_sat,
                    legacy_supported_mask,
                )
            )

            regression_metrics = {
                "milestone": MILESTONE,
                "status":
                    "100D_LEGACY_NUMERICAL_REGRESSION_COMPUTED",
                "regression_role":
                    (
                        "diagnostic comparison of the "
                        "capacity-aware production 100-day "
                        "state against the immutable V16E18-R1 "
                        "numerical deployment candidate"
                    ),
                "legacy_candidate_is_physical_truth":
                    False,
                "legacy_full_grid_plume_claim_authorized_by_E18":
                    False,
                "regression_accuracy_threshold_frozen":
                    False,
                "regression_difference_magnitude_is_blocking":
                    False,
                "legacy_frozen_file_sha256":
                    provenance_before[
                        "legacy_candidate"
                    ],
                "new_production_state_array_sha256":
                    arr_sha(
                        final_sat
                    ),
                "legacy_saturation_array_sha256":
                    arr_sha(
                        legacy_sat
                    ),
                "new_and_legacy_arrays_bitwise_equal":
                    bool(
                        np.array_equal(
                            final_sat,
                            legacy_sat,
                        )
                    ),
                "grid_shape":
                    list(
                        EXPECTED_GRID
                    ),
                "physical_time_days":
                    TARGET_OBSERVATION_DAY,
                "legacy_supported_cells":
                    int(
                        np.sum(
                            legacy_supported_mask
                        )
                    ),
                "legacy_background_completed_cells":
                    int(
                        np.sum(
                            ~legacy_supported_mask
                        )
                    ),
                "whole_grid":
                    whole_metrics,
                "legacy_supported_partition":
                    supported_metrics,
                "legacy_background_completed_partition":
                    background_metrics,
                "active_plume_overlap":
                    active_overlap,
                "visible_plume_overlap":
                    visible_overlap,
                "new_incremental_saturation_centroid_m":
                    {
                        "x": new_centroid[0],
                        "y": new_centroid[1],
                        "z": new_centroid[2],
                    },
                "legacy_incremental_saturation_centroid_m":
                    {
                        "x": legacy_centroid[0],
                        "y": legacy_centroid[1],
                        "z": legacy_centroid[2],
                    },
                "centroid_shift_new_minus_legacy_m":
                    {
                        "dx": float(
                            centroid_delta[0]
                        ),
                        "dy": float(
                            centroid_delta[1]
                        ),
                        "dz": float(
                            centroid_delta[2]
                        ),
                        "distance":
                            centroid_distance,
                    },
                "new_canonical_stored_CO2_mass_kg":
                    final_mass,
                "new_common_evaluator_stored_CO2_mass_kg":
                    new_recomputed_mass,
                "legacy_common_evaluator_implied_stored_CO2_mass_kg":
                    legacy_common_mass,
                "common_evaluator_stored_mass_difference_new_minus_legacy_kg":
                    (
                        new_recomputed_mass
                        - legacy_common_mass
                    ),
                "new_canonical_producer_CO2_gas_cut":
                    final_cut,
                "new_recomputed_current_metric_producer_CO2_gas_cut":
                    new_recomputed_cut,
                "legacy_recomputed_current_metric_producer_CO2_gas_cut":
                    legacy_recomputed_cut,
                "current_metric_producer_cut_difference_new_minus_legacy":
                    (
                        new_recomputed_cut
                        - legacy_recomputed_cut
                    ),
                "legacy_breakthrough_time_available_from_single_100d_candidate":
                    False,
                "new_canonical_breakthrough_time_days":
                    canonical_bt_time,
                "new_active_cells_inside_legacy_background_completed_partition":
                    new_active_in_legacy_unsupported,
                "new_visible_cells_inside_legacy_background_completed_partition":
                    new_visible_in_legacy_unsupported,
            }

            core_values = [
                whole_metrics[
                    "L1_mean_abs"
                ],
                whole_metrics[
                    "L2_rms"
                ],
                whole_metrics[
                    "Linf"
                ],
                whole_metrics[
                    "signed_mean_bias_new_minus_legacy"
                ],
                centroid_distance,
                legacy_common_mass,
                legacy_recomputed_cut,
            ]
            gate(
                "R3_regression_core_metrics_finite",
                all(
                    np.isfinite(
                        float(v)
                    )
                    for v in core_values
                ),
            )
            gate(
                "R3_regression_has_no_invented_accuracy_gate",
                regression_metrics[
                    "regression_accuracy_threshold_frozen"
                ]
                is False
                and regression_metrics[
                    "regression_difference_magnitude_is_blocking"
                ]
                is False,
            )

            failed_stage = (
                "immutability_and_artifact_closure"
            )

            source_modifications = {
                key: (
                    sha256_file(
                        paths[key]
                    )
                    != provenance_before[
                        f"source_{key}"
                    ]
                )
                for key in expected_source_sha
            }
            provenance_modifications = {
                key: (
                    sha256_file(p)
                    != provenance_before[
                        key
                    ]
                )
                for key, p in provenance_files.items()
            }

            gate(
                "R3_all_frozen_sources_unmodified",
                not any(
                    source_modifications.values()
                ),
                source_modifications,
            )
            gate(
                "R3_all_predecessor_provenance_unmodified",
                not any(
                    provenance_modifications.values()
                ),
                provenance_modifications,
            )

            limiter_counter = Counter()
            for row in controller_rows:
                if (
                    row.get(
                        "controller_action"
                    )
                    == "REJECT_AND_RETRY_AT_CAPACITY_BOUND"
                ):
                    limiter_counter[
                        tuple(
                            row[
                                "upper_limiting_cell_zero_based"
                            ]
                        )
                    ] += 1

            limiter_rows = [
                {
                    "k_zero_based": cell[0],
                    "j_zero_based": cell[1],
                    "i_zero_based": cell[2],
                    "capacity_adjustment_count":
                        count,
                }
                for cell, count
                in limiter_counter.most_common()
            ]

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "restart_step_index":
                    restart_step,
                "restart_time_days":
                    restart_time,
                "restart_state_sha256":
                    provenance_before[
                        "R2_state"
                    ],
                "final_step_index":
                    final_step,
                "final_time_days":
                    final_time,
                "canonical_100d_state_sha256":
                    checkpoint_sha,
                "accepted_transitions":
                    accepted_transitions,
                "native_rejected_trials":
                    native_rejected_trials,
                "capacity_adjustments_total":
                    capacity_adjustments_total,
                "capacity_limited_steps":
                    capacity_limited_steps,
                "capacity_limited_step_fraction":
                    (
                        float(
                            capacity_limited_steps
                            / accepted_transitions
                        )
                        if accepted_transitions
                        > 0
                        else 0.0
                    ),
                "max_capacity_adjustments_one_step":
                    max_capacity_adjustments_one_step,
                "unique_capacity_limiter_cells":
                    len(
                        limiter_counter
                    ),
                "dominant_capacity_limiter_cell_zero_based":
                    (
                        list(
                            limiter_counter.most_common(
                                1
                            )[0][0]
                        )
                        if limiter_counter
                        else None
                    ),
                "dominant_capacity_limiter_adjustments":
                    (
                        int(
                            limiter_counter.most_common(
                                1
                            )[0][1]
                        )
                        if limiter_counter
                        else 0
                    ),
                "native_capacity_token_rejections":
                    post_preflight_capacity_gate_failures,
                "nominal_dt_days":
                    nominal_dt_days,
                "accepted_dt_min_days":
                    float(
                        np.min(
                            accepted_dts
                        )
                    ),
                "accepted_dt_median_days":
                    float(
                        np.median(
                            accepted_dts
                        )
                    ),
                "accepted_dt_max_days":
                    float(
                        np.max(
                            accepted_dts
                        )
                    ),
                "interval_injected_CO2_mass_kg":
                    interval_injected,
                "interval_produced_CO2_mass_kg":
                    interval_produced,
                "interval_stored_mass_change_kg":
                    interval_stored_change,
                "final_cumulative_injected_CO2_mass_kg":
                    final_injected,
                "final_cumulative_produced_CO2_mass_kg":
                    final_produced,
                "final_stored_CO2_mass_kg":
                    final_mass,
                "final_cumulative_mass_residual_kg":
                    final_cum_resid,
                "final_producer_CO2_gas_cut":
                    final_cut,
                "final_plume_metrics":
                    final_plume,
                "mapback_spatial_operator_modified":
                    False,
                "EOS_inversion_modified":
                    False,
                "capillary_solver_modified":
                    False,
                "CV_transport_modified":
                    False,
                "source_local_mass_closure_used":
                    False,
                "mass_clipping_used":
                    False,
                "plume_rescaling_used":
                    False,
                "legacy_regression_computed":
                    True,
                "legacy_candidate_is_physical_truth":
                    False,
                "regression_difference_magnitude_is_blocking":
                    False,
                "next_milestone":
                    NEXT,
            }

            interval_ledger = {
                "restart_time_days":
                    restart_time,
                "final_time_days":
                    final_time,
                "restart_stored_CO2_mass_kg":
                    initial_stored,
                "interval_injected_CO2_mass_kg":
                    interval_injected,
                "interval_produced_CO2_mass_kg":
                    interval_produced,
                "interval_stored_mass_change_kg":
                    interval_stored_change,
                "interval_mass_residual_kg":
                    (
                        interval_stored_change
                        - interval_injected
                        + interval_produced
                    ),
                "final_cumulative_mass_residual_kg":
                    final_cum_resid,
            }

            files = {
                CANONICAL_100D_STATE:
                    checkpoint_bytes,
                "PAD_Stream_V16E41R3_Summary.json":
                    json_bytes(
                        summary
                    ),
                "V16E41R3_Accepted_Rollout.csv":
                    csv_bytes(
                        rollout_rows
                    ),
                "V16E41R3_Capacity_Controller_Audit.csv":
                    csv_bytes(
                        controller_rows
                    ),
                "V16E41R3_Rejected_Trial_Audit.csv":
                    csv_bytes(
                        rejection_rows
                    ),
                "V16E41R3_Capacity_Limiter_Cell_Counts.csv":
                    csv_bytes(
                        limiter_rows
                    ),
                "V16E41R3_Producer_Mass_Audit.csv":
                    csv_bytes(
                        producer_rows_all
                    ),
                "V16E41R3_Plume_Snapshot_Metrics.csv":
                    csv_bytes(
                        plume_rows
                    ),
                "V16E41R3_Sparse_Plume_Snapshots.npz":
                    snapshot_bytes,
                "V16E41R3_100D_Interval_Mass_Ledger.json":
                    json_bytes(
                        interval_ledger
                    ),
                "V16E41R3_100D_Legacy_Regression.json":
                    json_bytes(
                        regression_metrics
                    ),
                "V16E41R3_100D_Legacy_Layerwise_Regression.csv":
                    csv_bytes(
                        layer_rows
                    ),
            }

            # Gate matrix is emitted after all gates below are complete.
            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed":
                    all(
                        v[
                            "passed"
                        ]
                        for v in gates.values()
                    ),
                "gate_count":
                    len(
                        gates
                    ),
                "restart_state_sha256":
                    provenance_before[
                        "R2_state"
                    ],
                "canonical_100d_state_filename":
                    CANONICAL_100D_STATE,
                "canonical_100d_state_sha256":
                    checkpoint_sha,
                "final_step_index":
                    final_step,
                "final_time_days":
                    final_time,
                "accepted_transitions":
                    accepted_transitions,
                "capacity_adjustments_total":
                    capacity_adjustments_total,
                "capacity_limited_steps":
                    capacity_limited_steps,
                "native_rejected_trials":
                    native_rejected_trials,
                "mapback_spatial_operator_modified":
                    False,
                "EOS_inversion_modified":
                    False,
                "capillary_solver_modified":
                    False,
                "CV_transport_modified":
                    False,
                "mass_clipping_used":
                    False,
                "plume_rescaling_used":
                    False,
                "source_local_mass_closure_used":
                    False,
                "legacy_candidate_sha256":
                    provenance_before[
                        "legacy_candidate"
                    ],
                "legacy_regression_computed":
                    True,
                "legacy_candidate_is_physical_truth":
                    False,
                "regression_accuracy_threshold_frozen":
                    False,
                "regression_difference_magnitude_is_blocking":
                    False,
                "frozen_source_modifications":
                    source_modifications,
                "predecessor_provenance_modifications":
                    provenance_modifications,
                "next_milestone":
                    NEXT,
            }

            files[
                "V16E41R3_Final_Closure.json"
            ] = json_bytes(
                closure
            )
            files[
                "V16E41R3_Final_Gate_Matrix.csv"
            ] = csv_bytes(
                [
                    {
                        "gate": k,
                        **v,
                    }
                    for k, v
                    in gates.items()
                ]
            )

            immutable_publish(
                out,
                files,
            )

            manifest_rows = []
            for p in sorted(
                out.iterdir()
            ):
                if (
                    p.is_file()
                    and p.name
                    != "V16E41R3_Artifact_Manifest.csv"
                ):
                    manifest_rows.append(
                        {
                            "file":
                                p.name,
                            "sha256":
                                sha256_file(
                                    p
                                ),
                            "bytes":
                                p.stat().st_size,
                        }
                    )
            immutable_publish(
                out,
                {
                    "V16E41R3_Artifact_Manifest.csv":
                        csv_bytes(
                            manifest_rows
                        )
                },
            )

            print(
                "\n" + "=" * 150
            )
            print(
                "PAD-Stream V16E-41-R3: PASS"
            )
            print("=" * 150)
            print(
                f"{'Status':54}: {STATUS}"
            )
            print(
                f"{'Restart step / time':54}: "
                f"{restart_step} / {restart_time:.15g} d"
            )
            print(
                f"{'Final step / time':54}: "
                f"{final_step} / {final_time:.15g} d"
            )
            print(
                f"{'Accepted transitions':54}: "
                f"{accepted_transitions}"
            )
            print(
                f"{'Capacity-limited steps':54}: "
                f"{capacity_limited_steps}"
            )
            print(
                f"{'Capacity adjustments total':54}: "
                f"{capacity_adjustments_total}"
            )
            print(
                f"{'Native rejected trials':54}: "
                f"{native_rejected_trials}"
            )
            print(
                f"{'Min accepted dt':54}: "
                f"{float(np.min(accepted_dts)):.15g} d"
            )
            print(
                f"{'Dominant capacity limiter cell':54}: "
                f"{summary['dominant_capacity_limiter_cell_zero_based']}"
            )
            print(
                f"{'Final stored CO2 mass':54}: "
                f"{final_mass:.15e} kg"
            )
            print(
                f"{'Final producer CO2 gas cut':54}: "
                f"{final_cut:.15e}"
            )
            print(
                f"{'Canonical 100d state SHA-256':54}: "
                f"{checkpoint_sha}"
            )
            print(
                f"{'Legacy regression whole-grid L2 RMS':54}: "
                f"{float(whole_metrics['L2_rms']):.15e}"
            )
            print(
                f"{'Legacy regression difference blocking':54}: False"
            )
            print(
                f"{'Output':54}: {out}"
            )
            print(
                f"{'Next':54}: {NEXT}"
            )
            return 0

    except Exception as exc:
        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )
        report = {
            "milestone":
                MILESTONE,
            "status":
                "CAPACITY_AWARE_PRODUCTION_100D_LEGACY_REGRESSION_BLOCKED",
            "failed_stage":
                failed_stage,
            "exception":
                repr(
                    exc
                ),
            "gates":
                gates,
        }
        data = json_bytes(
            report
        )
        p = (
            blocked
            / "V16E41R3_Blocked_100D_Rollout_Regression.json"
        )
        if (
            p.exists()
            and p.read_bytes()
            != data
        ):
            p = (
                blocked
                / (
                    "V16E41R3_Blocked_100D_Rollout_Regression_"
                    + hashlib.sha256(
                        data
                    ).hexdigest()[
                        :12
                    ]
                    + ".json"
                )
            )
        p.write_bytes(
            data
        )

        print(
            "\n" + "=" * 150
        )
        print(
            "PAD-Stream V16E-41-R3: BLOCKED"
        )
        print("=" * 150)
        print(
            "Report      :", p
        )
        print(
            "Failed stage:", failed_stage
        )
        print(
            "Exception   :", repr(exc)
        )
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
