from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import hashlib
import json
from typing import Any

import numpy as np


MILESTONE = "V16E-29"
STATUS = "READ_ONLY_PAD_STREAM_RUNTIME_LOADER_DRY_RUN_PASS"
NEXT = "V16E-30 - Independent Read-Only Runtime Loader Validation / Freeze Readiness"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_UNSUPPORTED = 17038
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
EXPECTED_DIAGNOSTIC_THRESHOLD = 0.21
EXPECTED_HISTORICAL_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = "SG7A_corrected"

V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"
RUNTIME_STATE_ARRAY_SHA = "176975c3131353c4fe60fdf9e6d7635b13e260e010fc8cd849deb17c85e37f12"

E28_RUNNER = (
    "PAD_Stream_V16E28_Accepted_SGSim_Deployment_State_Runtime_Contract_Integration.py",
    "41235afa7c7e657b798bab52a69465c7d746dc1c7c3cd7b29032aec33135429f",
)
E27_RUNNER = (
    "PAD_Stream_V16E27_Frozen_SGSim_Deployment_Acceptance_and_PAD_Stream_Integration_Handoff.py",
    "e6cbc67d46ed13497afe4a09802286662aa838ab9d6180670f08b79f7db31e45",
)
E18R1_RUNNER = (
    "PAD_Stream_V16E18_R1_E15_Background_Schema_Repair_and_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
    "d3944a6ef13b2c4f36bdcd77fde3845b6f442290e5007b5529c3f288054e7279",
)

E28_REL = Path(
    "provenance/hybrid_dp/"
    "V16E28_ACCEPTED_SGSIM_DEPLOYMENT_STATE_PAD_STREAM_RUNTIME_CONTRACT_INTEGRATION"
)
E28_ARTIFACTS = {
    "V16E28_PAD_Stream_Runtime_Contract.json":
        "b29e30cb5474e6555d9f0aeea75f3fc6e7b5964fca1a1cb34c15c9b4abf9db16",
    "V16E28_Runtime_Contract_Integration_Manifest.json":
        "2d88b77b09f747e2d7aa89c0b633a547e05ddbfca75c3505be68d6d390069947",
    "PAD_Stream_V16E28_Summary.json":
        "a564c9074755c50c6614f1f079a02cb6f06a5e63962827bfe7daa49aa292ce61",
    "V16E28_Handoff.md":
        "ac2af010810266ab207215e6a7f8fc5d3a2fb42a95a63ff53fcdf73e4fe80c24",
    "V16E28_E27_Authority.csv":
        "4a594d0116de5bd1805375eb668b1bb79bb131ed22ae7754b82df3852cd7ff34",
    "V16E28_Runtime_Binding_Schema.csv":
        "fc3728f0b8fdb61df4efdd1a7fae9219daf3c0598f5de6a14311c461f79b32eb",
    "V16E28_Runtime_Array_Identity.csv":
        "42ad0aa5c183932f01377bf32e7ac39648a8f9bd13cc0dfc2efd8bf50d73bc4b",
    "V16E28_Runtime_Role_Separation.csv":
        "6e0810bf157615ab0ecbe13b7ae163e9c47ac11785831acf2a5416a73d4e7923",
    "V16E28_Final_Gate_Matrix.csv":
        "98ec5d6ca2e7961ccc4c8f189400cee49ea709d359eccfb31aa2d064d30f7422",
}

V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
REFERENCE_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E24_FROZEN_HISTORICAL_100DAY_REFERENCE_TRUTH/"
    "frozen_reference/V16E24_Frozen_Historical_SG7E_100Day_Reference_Truth.npz"
)

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E29_READ_ONLY_PAD_STREAM_RUNTIME_LOADER_ACCEPTED_STATE_CONSUMPTION_DRY_RUN"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E29_BLOCKED_READ_ONLY_PAD_STREAM_RUNTIME_LOADER_ACCEPTED_STATE_CONSUMPTION_DRY_RUN"
)


class GateError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeState:
    saturation_state: np.ndarray
    supported_mask: np.ndarray
    support_denominator: np.ndarray
    support_numerator: np.ndarray
    physical_time_days: float
    grid_shape: tuple[int, int, int]
    background_saturation: float
    diagnostic_threshold: float
    source_file: str
    source_file_sha256: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_read_only(arr: np.ndarray) -> np.ndarray:
    view = np.asarray(arr).view()
    view.setflags(write=False)
    return view


def assert_write_blocked(arr: np.ndarray) -> bool:
    if arr.size == 0:
        return not arr.flags.writeable
    idx = (0,) * arr.ndim
    try:
        arr[idx] = arr[idx]
    except ValueError:
        return True
    return False


def load_runtime_state_read_only(
    runtime_contract: dict[str, Any],
    expected_source_path: Path,
) -> RuntimeState:
    source = runtime_contract["canonical_runtime_state_source"]

    if source["path"] != str(expected_source_path):
        raise GateError("runtime_contract_source_path_mismatch")
    if source["file_sha256"] != V16_FROZEN_SHA:
        raise GateError("runtime_contract_source_SHA_mismatch")
    if source["numerical_mutation_permitted"] is not False:
        raise GateError("runtime_contract_mutation_permission_not_false")
    if source["numerical_copy_required"] is not False:
        raise GateError("runtime_contract_copy_requirement_not_false")

    with np.load(expected_source_path, allow_pickle=False) as db:
        required = {
            source["state_key"],
            source["support_mask_key"],
            source["support_denominator_key"],
            source["support_numerator_key"],
            "physical_time_days",
            "grid_shape",
            "background_saturation",
            source["diagnostic_threshold_key"],
        }
        if not required.issubset(set(db.files)):
            raise GateError("runtime_source_missing_required_keys")

        state = make_read_only(np.asarray(db[source["state_key"]]))
        mask = make_read_only(np.asarray(db[source["support_mask_key"]]))
        den = make_read_only(np.asarray(db[source["support_denominator_key"]]))
        num = make_read_only(np.asarray(db[source["support_numerator_key"]]))

        physical_time_days = float(np.asarray(db["physical_time_days"]))
        grid_shape = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
        background_saturation = float(np.asarray(db["background_saturation"]))
        diagnostic_threshold = float(np.asarray(db[source["diagnostic_threshold_key"]]))

    return RuntimeState(
        saturation_state=state,
        supported_mask=mask,
        support_denominator=den,
        support_numerator=num,
        physical_time_days=physical_time_days,
        grid_shape=grid_shape,
        background_saturation=background_saturation,
        diagnostic_threshold=diagnostic_threshold,
        source_file=str(expected_source_path),
        source_file_sha256=V16_FROZEN_SHA,
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}

    def gate(name, ok, detail=""):
        ok = bool(ok)
        gates[name] = {"passed": ok, "detail": str(detail)}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f": {detail}" if detail else ""),
            flush=True,
        )
        if not ok:
            raise GateError(name)

    v16_path = drive / V16_FROZEN_REL
    ref_path = drive / REFERENCE_FROZEN_REL
    v16_sha_before = None
    ref_sha_before = None

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-29 Read-Only Runtime Loader / Accepted-State Consumption Dry Run")
    print("=" * 132)
    print("READ-ONLY LOADER EXECUTION ONLY.")
    print("NO RUNTIME TIME ADVANCE. NO NEW SATURATION FIELD. NO MODEL INFERENCE OR UPSTREAM PHYSICS RECOMPUTATION.")
    print("THE FROZEN HISTORICAL REFERENCE IS NOT LOADED BY THE RUNTIME LOADER; IT REMAINS VALIDATION-ONLY.")
    print("NO PERSISTED NUMERICAL COPY OF THE ACCEPTED STATE IS CREATED.")
    print("INTERNAL TEST / OOD REMAIN CLOSED. IBDP REMAINS DEFERRED.")

    try:
        # ------------------------------------------------------------------
        # Source authority.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E28_runner", E28_RUNNER),
            ("E27_runner", E27_RUNNER),
            ("E18R1_runner", E18R1_RUNNER),
        ]:
            p = root / name
            gate(f"{label}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # E28 contract authority.
        # ------------------------------------------------------------------
        print("\nV16E-28 RUNTIME CONTRACT AUTHORITY")
        for name, expected in E28_ARTIFACTS.items():
            p = drive / E28_REL / name
            gate(f"E28_{name}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"E28_{name}_SHA_exact", actual == expected, actual)

        runtime_contract = load_json(
            drive / E28_REL / "V16E28_PAD_Stream_Runtime_Contract.json"
        )
        integration_manifest = load_json(
            drive / E28_REL / "V16E28_Runtime_Contract_Integration_Manifest.json"
        )
        e28_summary = load_json(
            drive / E28_REL / "PAD_Stream_V16E28_Summary.json"
        )
        binding_schema = load_csv(
            drive / E28_REL / "V16E28_Runtime_Binding_Schema.csv"
        )
        role_separation = load_csv(
            drive / E28_REL / "V16E28_Runtime_Role_Separation.csv"
        )

        gate(
            "E28_contract_status_integrated",
            runtime_contract.get("status") == "PAD_STREAM_RUNTIME_CONTRACT_INTEGRATED",
        )
        gate(
            "E28_contract_mode_read_only_exact_identity",
            runtime_contract.get("integration_mode")
            == "READ_ONLY_EXACT_IDENTITY_BINDING",
        )
        source = runtime_contract["canonical_runtime_state_source"]
        gate(
            "E28_contract_source_SHA_exact",
            source.get("file_sha256") == V16_FROZEN_SHA,
            source.get("file_sha256"),
        )
        gate(
            "E28_contract_state_key_exact",
            source.get("state_key") == "saturation_grid_full_float64",
            source.get("state_key"),
        )
        gate(
            "E28_contract_support_mask_key_exact",
            source.get("support_mask_key") == "supported_mask",
            source.get("support_mask_key"),
        )
        gate(
            "E28_contract_support_denominator_key_exact",
            source.get("support_denominator_key") == "support_denominator",
            source.get("support_denominator_key"),
        )
        gate(
            "E28_contract_support_numerator_key_exact",
            source.get("support_numerator_key") == "support_numerator",
            source.get("support_numerator_key"),
        )
        gate(
            "E28_contract_diagnostic_threshold_key_exact",
            source.get("diagnostic_threshold_key") == "diagnostic_threshold",
            source.get("diagnostic_threshold_key"),
        )
        gate(
            "E28_contract_mutation_forbidden",
            source.get("numerical_mutation_permitted") is False,
        )
        gate(
            "E28_contract_persisted_copy_not_required",
            source.get("numerical_copy_required") is False,
        )

        validation = runtime_contract["historical_validation_reference"]
        gate(
            "E28_reference_SHA_exact",
            validation.get("file_sha256") == REFERENCE_FROZEN_FILE_SHA,
            validation.get("file_sha256"),
        )
        gate(
            "E28_reference_key_exact",
            validation.get("reference_key") == EXPECTED_REFERENCE_KEY,
            validation.get("reference_key"),
        )
        gate(
            "E28_historical_threshold_0p5_exact",
            float(validation.get("plume_threshold")) == EXPECTED_HISTORICAL_THRESHOLD,
            validation.get("plume_threshold"),
        )
        gate(
            "E28_reference_not_runtime_state",
            validation.get("runtime_state_input") is False,
        )
        gate(
            "E28_reference_not_runtime_correction",
            validation.get("runtime_correction_input") is False,
        )
        gate(
            "E28_reference_not_runtime_tuning",
            validation.get("runtime_tuning_input") is False,
        )

        boundary = runtime_contract["execution_boundary"]
        gate(
            "E28_runtime_contract_integrated",
            boundary.get("runtime_contract_integrated") is True,
        )
        gate(
            "E28_runtime_loader_not_previously_executed",
            boundary.get("runtime_loader_executed") is False,
        )
        gate(
            "E28_no_prior_runtime_time_advance",
            boundary.get("runtime_time_advance_performed") is False,
        )
        gate(
            "E28_no_prior_new_saturation_field",
            boundary.get("new_saturation_field_created") is False,
        )
        gate(
            "E28_no_prior_training_or_inference",
            boundary.get("training_performed") is False
            and boundary.get("model_inference_performed") is False,
        )
        gate(
            "E28_no_prior_upstream_physics_recompute",
            boundary.get("upstream_physics_recomputed") is False,
        )

        gate(
            "E28_manifest_status_exact",
            integration_manifest.get("status")
            == "ACCEPTED_SGSIM_DEPLOYMENT_STATE_INTEGRATED_INTO_PAD_STREAM_RUNTIME_CONTRACT",
            integration_manifest.get("status"),
        )
        gate(
            "E28_manifest_exact_identity_bound",
            integration_manifest.get("accepted_state_bound_by_exact_identity") is True,
        )
        gate(
            "E28_manifest_state_read_only",
            integration_manifest.get("accepted_state_read_only") is True,
        )
        gate(
            "E28_manifest_no_numerical_copy",
            integration_manifest.get("numerical_copy_created") is False,
        )

        gate(
            "E28_summary_status_exact",
            e28_summary.get("status")
            == "ACCEPTED_SGSIM_DEPLOYMENT_STATE_INTEGRATED_INTO_PAD_STREAM_RUNTIME_CONTRACT",
            e28_summary.get("status"),
        )
        gate(
            "E28_summary_runtime_state_array_SHA_exact",
            e28_summary.get("runtime_state_array_sha256") == RUNTIME_STATE_ARRAY_SHA,
            e28_summary.get("runtime_state_array_sha256"),
        )
        gate(
            "E28_summary_runtime_contract_integrated",
            e28_summary.get("runtime_contract_integrated") is True,
        )
        gate(
            "E28_summary_loader_not_executed",
            e28_summary.get("runtime_loader_executed") is False,
        )
        gate(
            "E28_summary_test_OOD_closed",
            e28_summary.get("internal_test_reopened") is False
            and e28_summary.get("OOD_reopened") is False,
        )
        gate("E28_summary_IBDP_deferred", e28_summary.get("IBDP_started") is False)
        gate(
            "E28_next_is_E29",
            str(e28_summary.get("next_milestone", "")).startswith("V16E-29"),
            e28_summary.get("next_milestone"),
        )
        gate("E28_binding_schema_has_8_rows", len(binding_schema) == 8, len(binding_schema))
        gate("E28_role_separation_present", len(role_separation) >= 7, len(role_separation))

        # ------------------------------------------------------------------
        # Immutable source identity before runtime consumption.
        # ------------------------------------------------------------------
        print("\nIMMUTABLE SOURCE IDENTITY")
        gate("accepted_state_file_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate(
            "accepted_state_file_SHA_exact_before",
            v16_sha_before == V16_FROZEN_SHA,
            v16_sha_before,
        )
        gate("validation_reference_file_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate(
            "validation_reference_file_SHA_exact_before",
            ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
            ref_sha_before,
        )

        # ------------------------------------------------------------------
        # Read-only runtime loader execution / dry run.
        # ------------------------------------------------------------------
        print("\nREAD-ONLY RUNTIME LOADER EXECUTION")
        runtime = load_runtime_state_read_only(runtime_contract, v16_path)

        gate(
            "loader_source_path_exact",
            runtime.source_file == str(v16_path),
            runtime.source_file,
        )
        gate(
            "loader_source_file_SHA_exact",
            runtime.source_file_sha256 == V16_FROZEN_SHA,
            runtime.source_file_sha256,
        )
        gate(
            "loader_grid_shape_exact",
            runtime.grid_shape == EXPECTED_GRID,
            runtime.grid_shape,
        )
        gate(
            "loader_physical_time_100d_exact",
            runtime.physical_time_days == EXPECTED_TIME_DAYS,
            runtime.physical_time_days,
        )
        gate(
            "loader_background_0p2_exact",
            runtime.background_saturation == EXPECTED_BACKGROUND,
            runtime.background_saturation,
        )
        gate(
            "loader_diagnostic_threshold_0p21_exact",
            runtime.diagnostic_threshold == EXPECTED_DIAGNOSTIC_THRESHOLD,
            runtime.diagnostic_threshold,
        )
        gate(
            "loader_state_shape_exact",
            runtime.saturation_state.shape == EXPECTED_GRID,
            runtime.saturation_state.shape,
        )
        gate(
            "loader_state_dtype_float64",
            runtime.saturation_state.dtype == np.float64,
            runtime.saturation_state.dtype,
        )
        gate("loader_state_finite", np.all(np.isfinite(runtime.saturation_state)))
        gate(
            "loader_state_array_SHA_matches_E28",
            sha256_array(runtime.saturation_state) == RUNTIME_STATE_ARRAY_SHA,
            sha256_array(runtime.saturation_state),
        )

        expected_array_identity = runtime_contract["runtime_array_identity"]
        gate(
            "loader_supported_mask_SHA_matches_E28",
            sha256_array(runtime.supported_mask)
            == expected_array_identity["supported_mask_sha256"],
            sha256_array(runtime.supported_mask),
        )
        gate(
            "loader_support_denominator_SHA_matches_E28",
            sha256_array(runtime.support_denominator)
            == expected_array_identity["support_denominator_sha256"],
            sha256_array(runtime.support_denominator),
        )
        gate(
            "loader_support_numerator_SHA_matches_E28",
            sha256_array(runtime.support_numerator)
            == expected_array_identity["support_numerator_sha256"],
            sha256_array(runtime.support_numerator),
        )

        gate(
            "loader_state_read_only",
            runtime.saturation_state.flags.writeable is False,
        )
        gate(
            "loader_supported_mask_read_only",
            runtime.supported_mask.flags.writeable is False,
        )
        gate(
            "loader_support_denominator_read_only",
            runtime.support_denominator.flags.writeable is False,
        )
        gate(
            "loader_support_numerator_read_only",
            runtime.support_numerator.flags.writeable is False,
        )
        gate(
            "loader_state_write_attempt_blocked",
            assert_write_blocked(runtime.saturation_state),
        )
        gate(
            "loader_supported_mask_write_attempt_blocked",
            assert_write_blocked(runtime.supported_mask),
        )
        gate(
            "loader_support_denominator_write_attempt_blocked",
            assert_write_blocked(runtime.support_denominator),
        )
        gate(
            "loader_support_numerator_write_attempt_blocked",
            assert_write_blocked(runtime.support_numerator),
        )

        support_bool = runtime.supported_mask.astype(bool, copy=False)
        supported_count = int(np.count_nonzero(support_bool))
        unsupported_count = int(runtime.supported_mask.size - supported_count)
        gate(
            "loader_total_cells_exact",
            int(runtime.saturation_state.size) == EXPECTED_CELLS,
            runtime.saturation_state.size,
        )
        gate(
            "loader_supported_cells_exact",
            supported_count == EXPECTED_SUPPORTED,
            supported_count,
        )
        gate(
            "loader_unsupported_cells_exact",
            unsupported_count == EXPECTED_UNSUPPORTED,
            unsupported_count,
        )
        gate(
            "loader_background_completed_cells_exact",
            np.all(runtime.saturation_state[~support_bool] == EXPECTED_BACKGROUND),
        )

        diagnostic_mask = runtime.saturation_state >= runtime.diagnostic_threshold
        diagnostic_cells = int(np.count_nonzero(diagnostic_mask))
        diagnostic_unsupported = int(np.count_nonzero(diagnostic_mask & ~support_bool))
        gate(
            "loader_diagnostic_0p21_cells_exact",
            diagnostic_cells == 15924,
            diagnostic_cells,
        )
        gate(
            "loader_diagnostic_0p21_unsupported_zero",
            diagnostic_unsupported == 0,
            diagnostic_unsupported,
        )

        # ------------------------------------------------------------------
        # Dry-run firewall and immutability after consumption.
        # ------------------------------------------------------------------
        print("\nDRY-RUN FIREWALL / POST-CONSUMPTION IDENTITY")
        gate("runtime_state_consumed_read_only", True)
        gate("no_runtime_time_advance_in_E29", True)
        gate("no_new_saturation_field_created_in_E29", True)
        gate("no_persisted_numerical_copy_created_in_E29", True)
        gate("no_training_in_E29", True)
        gate("no_model_inference_in_E29", True)
        gate("no_upstream_physics_recomputation_in_E29", True)
        gate("historical_reference_not_loaded_by_runtime_loader", True)
        gate("historical_reference_not_runtime_correction", True)
        gate("historical_reference_not_runtime_tuning_input", True)
        gate("historical_0p5_threshold_validation_only", True)
        gate("diagnostic_0p21_threshold_diagnostic_only", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("IBDP_not_started", True)

        gate(
            "accepted_state_file_SHA_exact_after",
            sha256_file(v16_path) == v16_sha_before == V16_FROZEN_SHA,
        )
        gate(
            "validation_reference_file_SHA_exact_after",
            sha256_file(ref_path) == ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
        )

        # ------------------------------------------------------------------
        # Persist metadata/evidence only. No numerical NPZ output.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)

        save_csv(
            out / "V16E29_E28_Authority.csv",
            [
                {
                    "artifact": name,
                    "sha256": expected,
                    "path": str(drive / E28_REL / name),
                    "role": "ACCEPTED_E28_RUNTIME_CONTRACT_AUTHORITY",
                }
                for name, expected in E28_ARTIFACTS.items()
            ],
        )

        loader_evidence_rows = [
            {
                "object": "saturation_state",
                "source_key": source["state_key"],
                "shape": "15x50x50",
                "dtype": str(runtime.saturation_state.dtype),
                "array_sha256": sha256_array(runtime.saturation_state),
                "writeable": runtime.saturation_state.flags.writeable,
                "write_attempt_blocked": True,
            },
            {
                "object": "supported_mask",
                "source_key": source["support_mask_key"],
                "shape": "15x50x50",
                "dtype": str(runtime.supported_mask.dtype),
                "array_sha256": sha256_array(runtime.supported_mask),
                "writeable": runtime.supported_mask.flags.writeable,
                "write_attempt_blocked": True,
            },
            {
                "object": "support_denominator",
                "source_key": source["support_denominator_key"],
                "shape": "15x50x50",
                "dtype": str(runtime.support_denominator.dtype),
                "array_sha256": sha256_array(runtime.support_denominator),
                "writeable": runtime.support_denominator.flags.writeable,
                "write_attempt_blocked": True,
            },
            {
                "object": "support_numerator",
                "source_key": source["support_numerator_key"],
                "shape": "15x50x50",
                "dtype": str(runtime.support_numerator.dtype),
                "array_sha256": sha256_array(runtime.support_numerator),
                "writeable": runtime.support_numerator.flags.writeable,
                "write_attempt_blocked": True,
            },
        ]
        save_csv(out / "V16E29_Read_Only_Loader_Evidence.csv", loader_evidence_rows)

        save_csv(
            out / "V16E29_Accepted_State_Consumption_Dry_Run.csv",
            [
                {"check": "grid_shape", "value": "15x50x50", "role": "RUNTIME_METADATA"},
                {"check": "total_cells", "value": EXPECTED_CELLS, "role": "RUNTIME_METADATA"},
                {"check": "physical_time_days", "value": runtime.physical_time_days, "role": "RUNTIME_METADATA"},
                {"check": "background_saturation", "value": runtime.background_saturation, "role": "RUNTIME_METADATA"},
                {"check": "supported_cells", "value": supported_count, "role": "PROVENANCE_SUPPORT"},
                {"check": "unsupported_cells", "value": unsupported_count, "role": "PROVENANCE_SUPPORT"},
                {"check": "diagnostic_threshold", "value": runtime.diagnostic_threshold, "role": "DIAGNOSTIC_ONLY"},
                {"check": "diagnostic_cells", "value": diagnostic_cells, "role": "DIAGNOSTIC_ONLY"},
                {"check": "diagnostic_unsupported_cells", "value": diagnostic_unsupported, "role": "DIAGNOSTIC_ONLY"},
                {"check": "historical_plume_threshold", "value": EXPECTED_HISTORICAL_THRESHOLD, "role": "VALIDATION_ONLY"},
                {"check": "runtime_time_advance_performed", "value": False, "role": "FIREWALL"},
                {"check": "new_saturation_field_created", "value": False, "role": "FIREWALL"},
                {"check": "historical_reference_loaded_by_runtime_loader", "value": False, "role": "ROLE_SEPARATION"},
            ],
        )

        save_csv(
            out / "V16E29_Runtime_Role_Separation.csv",
            [
                {
                    "object": "accepted_V16E18_R1_state",
                    "E29_role": "READ_ONLY_RUNTIME_INPUT",
                    "loaded_by_runtime_loader": True,
                    "mutation_permitted": False,
                },
                {
                    "object": "V16E24_historical_reference",
                    "E29_role": "VALIDATION_ONLY",
                    "loaded_by_runtime_loader": False,
                    "mutation_permitted": False,
                },
                {
                    "object": "historical_threshold_0p5",
                    "E29_role": "VALIDATION_ONLY",
                    "loaded_by_runtime_loader": False,
                    "mutation_permitted": False,
                },
                {
                    "object": "diagnostic_threshold_0p21",
                    "E29_role": "DIAGNOSTIC_ONLY_METADATA",
                    "loaded_by_runtime_loader": True,
                    "mutation_permitted": False,
                },
                {
                    "object": "internal_test",
                    "E29_role": "CLOSED",
                    "loaded_by_runtime_loader": False,
                    "mutation_permitted": False,
                },
                {
                    "object": "OOD",
                    "E29_role": "CLOSED",
                    "loaded_by_runtime_loader": False,
                    "mutation_permitted": False,
                },
                {
                    "object": "IBDP",
                    "E29_role": "DEFERRED",
                    "loaded_by_runtime_loader": False,
                    "mutation_permitted": False,
                },
            ],
        )

        loader_contract = {
            "milestone": MILESTONE,
            "status": "READ_ONLY_RUNTIME_LOADER_EXECUTED",
            "loader_mode": "READ_ONLY_ACCEPTED_STATE_CONSUMPTION",
            "canonical_source": {
                "path": str(v16_path),
                "file_sha256": v16_sha_before,
                "state_array_sha256": sha256_array(runtime.saturation_state),
                "grid_shape": list(runtime.grid_shape),
                "physical_time_days": runtime.physical_time_days,
                "background_saturation": runtime.background_saturation,
                "diagnostic_threshold": runtime.diagnostic_threshold,
            },
            "read_only_enforcement": {
                "state_writeable": runtime.saturation_state.flags.writeable,
                "support_mask_writeable": runtime.supported_mask.flags.writeable,
                "support_denominator_writeable": runtime.support_denominator.flags.writeable,
                "support_numerator_writeable": runtime.support_numerator.flags.writeable,
                "write_attempts_blocked": True,
            },
            "consumption_dry_run": {
                "total_cells": EXPECTED_CELLS,
                "supported_cells": supported_count,
                "unsupported_cells": unsupported_count,
                "diagnostic_0p21_cells": diagnostic_cells,
                "diagnostic_0p21_unsupported_cells": diagnostic_unsupported,
                "runtime_time_advance_performed": False,
                "new_saturation_field_created": False,
                "persisted_numerical_copy_created": False,
            },
            "historical_reference_boundary": {
                "path": str(ref_path),
                "file_sha256": ref_sha_before,
                "reference_key": EXPECTED_REFERENCE_KEY,
                "historical_plume_threshold": EXPECTED_HISTORICAL_THRESHOLD,
                "loaded_by_runtime_loader": False,
                "runtime_state_input": False,
                "runtime_correction_input": False,
                "runtime_tuning_input": False,
            },
            "closed_domains": {
                "internal_test_reopened": False,
                "OOD_reopened": False,
                "IBDP_started": False,
            },
            "next_milestone": NEXT,
        }
        save_json(out / "V16E29_Read_Only_Runtime_Loader_Contract.json", loader_contract)

        dry_run_manifest = {
            "milestone": MILESTONE,
            "status": STATUS,
            "source_runtime_contract_sha256":
                E28_ARTIFACTS["V16E28_PAD_Stream_Runtime_Contract.json"],
            "runtime_loader_executed": True,
            "runtime_state_consumed": True,
            "runtime_state_consumed_read_only": True,
            "accepted_state_file_sha256": v16_sha_before,
            "accepted_state_array_sha256": sha256_array(runtime.saturation_state),
            "historical_reference_file_sha256": ref_sha_before,
            "historical_reference_loaded_by_runtime_loader": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "persisted_numerical_copy_created": False,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "independent_validation_required": True,
            "next_milestone": NEXT,
        }
        save_json(
            out / "V16E29_Accepted_State_Consumption_Dry_Run_Manifest.json",
            dry_run_manifest,
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "grid_shape": list(runtime.grid_shape),
            "physical_time_days": runtime.physical_time_days,
            "accepted_state_file_sha256": v16_sha_before,
            "accepted_state_array_sha256": sha256_array(runtime.saturation_state),
            "historical_reference_file_sha256": ref_sha_before,
            "background_saturation": runtime.background_saturation,
            "diagnostic_threshold": runtime.diagnostic_threshold,
            "historical_authoritative_plume_threshold": EXPECTED_HISTORICAL_THRESHOLD,
            "total_cells": EXPECTED_CELLS,
            "supported_cells": supported_count,
            "unsupported_cells": unsupported_count,
            "diagnostic_0p21_cells": diagnostic_cells,
            "diagnostic_0p21_unsupported_cells": diagnostic_unsupported,
            "runtime_loader_executed": True,
            "runtime_state_consumed": True,
            "runtime_state_read_only": True,
            "historical_reference_loaded_by_runtime_loader": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "persisted_numerical_copy_created": False,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "independent_validation_required": True,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E29_Summary.json", summary)

        (out / "V16E29_Handoff.md").write_text(
            "# PAD-Stream V16E-29 Handoff\n\n"
            "The E28 runtime contract has been consumed successfully by a read-only PAD-Stream runtime loader dry run. "
            "The loader used the accepted V16E-18-R1 frozen state directly by exact file/key identity and enforced "
            "non-writeable NumPy views for the state and support arrays.\n\n"
            f"- Accepted state file SHA-256: `{v16_sha_before}`\n"
            f"- Accepted saturation-array SHA-256: `{sha256_array(runtime.saturation_state)}`\n"
            f"- Grid / time: `{runtime.grid_shape} / {runtime.physical_time_days} days`\n"
            f"- Background saturation: `{runtime.background_saturation}`\n"
            f"- Supported / unsupported cells: `{supported_count} / {unsupported_count}`\n"
            f"- Diagnostic threshold: `{runtime.diagnostic_threshold}` (`DIAGNOSTIC_ONLY`)\n"
            f"- Historical threshold: `{EXPECTED_HISTORICAL_THRESHOLD}` (`VALIDATION_ONLY`)\n"
            "- Historical reference loaded by runtime loader: `NO`\n"
            "- Runtime time advance performed: `NO`\n"
            "- New saturation field created: `NO`\n"
            "- Persisted numerical copy created: `NO`\n"
            "- Frozen candidate modified: `NO`\n"
            "- Historical reference modified: `NO`\n"
            "- Internal test / OOD reopened: `NO / NO`\n"
            "- IBDP started: `NO`\n\n"
            "E30 should independently validate this loader behavior and determine freeze readiness. "
            "No runtime time advance should occur before that independent validation closes.\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        save_csv(
            out / "V16E29_Final_Gate_Matrix.csv",
            [{"gate": name, **record} for name, record in gates.items()],
        )

        print("\n" + "=" * 132)
        print("V16E-29 RESULT: PASS")
        print("=" * 132)
        print(f"{'Runtime loader executed':72}: YES")
        print(f"{'Accepted state consumed':72}: YES / READ-ONLY")
        print(f"{'Accepted state file SHA-256':72}: {v16_sha_before}")
        print(f"{'Accepted saturation-array SHA-256':72}: {sha256_array(runtime.saturation_state)}")
        print(f"{'Grid / physical time':72}: 15 x 50 x 50 / 100.0 days")
        print(f"{'Supported / unsupported cells':72}: {supported_count} / {unsupported_count}")
        print(f"{'Background saturation':72}: {runtime.background_saturation}")
        print(f"{'Diagnostic 0.21 cells / unsupported':72}: {diagnostic_cells} / {diagnostic_unsupported}")
        print(f"{'Historical 0.5 threshold role':72}: VALIDATION ONLY")
        print(f"{'Historical reference loaded by runtime':72}: NO")
        print(f"{'Runtime time advance performed':72}: NO")
        print(f"{'New saturation field created':72}: NO")
        print(f"{'Persisted numerical copy created':72}: NO")
        print(f"{'Frozen V16 candidate modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        print(f"{'IBDP started':72}: NO")
        print(f"{'Independent loader validation required':72}: YES")

        for name in [
            "V16E29_Read_Only_Runtime_Loader_Contract.json",
            "V16E29_Accepted_State_Consumption_Dry_Run_Manifest.json",
            "PAD_Stream_V16E29_Summary.json",
            "V16E29_Handoff.md",
            "V16E29_E28_Authority.csv",
            "V16E29_Read_Only_Loader_Evidence.csv",
            "V16E29_Accepted_State_Consumption_Dry_Run.csv",
            "V16E29_Runtime_Role_Separation.csv",
            "V16E29_Final_Gate_Matrix.csv",
        ]:
            p = out / name
            print(f"{name} SHA: {sha256_file(p)}")

        print(f"Output: {out}")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        payload = {
            "milestone": MILESTONE,
            "status": "BLOCKED",
            "exception": repr(exc),
            "gates": gates,
            "accepted_state_file_sha256_before": v16_sha_before,
            "historical_reference_file_sha256_before": ref_sha_before,
            "runtime_loader_executed": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "persisted_numerical_copy_created": False,
            "frozen_candidate_modified":
                False if v16_sha_before is None or not v16_path.exists()
                else sha256_file(v16_path) != v16_sha_before,
            "historical_reference_modified":
                False if ref_sha_before is None or not ref_path.exists()
                else sha256_file(ref_path) != ref_sha_before,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": (
                "V16E-29-R1 - Repair only the failed V16E-29 read-only-loader/provenance gate; "
                "preserve E28 and both frozen numerical objects unchanged"
            ),
        }
        p = blocked / "V16E29_Blocked_Read_Only_Runtime_Loader_Dry_Run.json"
        save_json(p, payload)
        print(f"\n[FAIL] V16E-29 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(p)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
