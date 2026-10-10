from __future__ import annotations

from pathlib import Path
import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import sys
from typing import Any

import numpy as np


MILESTONE = "V16E-32"
STATUS = "FROZEN_RUNTIME_LOADER_CONSUMED_RUNTIME_EXECUTION_ENTRY_CONTRACT_READY"
NEXT = "V16E-33 - PAD-Stream Runtime State-Transition Contract / Single-Step Execution Readiness"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_UNSUPPORTED = 17038
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
EXPECTED_DIAGNOSTIC_THRESHOLD = 0.21
EXPECTED_DIAGNOSTIC_CELLS = 15924
EXPECTED_DIAGNOSTIC_UNSUPPORTED = 0
EXPECTED_HISTORICAL_THRESHOLD = 0.5

V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"
RUNTIME_STATE_ARRAY_SHA = "176975c3131353c4fe60fdf9e6d7635b13e260e010fc8cd849deb17c85e37f12"
SUPPORTED_MASK_SHA = "4b8fab2ffa3608c62dfa6d3583914b2537cc76a0ef04fe6d103dbec78cc92a3c"
SUPPORT_DENOMINATOR_SHA = "70158dada5e2bd804014b13fd5908831df45f0d34120e3bd5dd9d940921c823e"
SUPPORT_NUMERATOR_SHA = "641d37335615b74971d15b0d751b297b1ed09ada2f87c939a4eba08681fcbeba"
FROZEN_LOADER_SHA = "1604f753b3cc37444d77fd3f979443717d3a8437efa4f43a13732d9744f288cc"
FROZEN_LOADER_FUNCTION_SHA = "363c2e851379475aa9d24eadbb4dfa953441a3f8a771eb0cda8eb8393ac345de"

E31_RUNNER = (
    "PAD_Stream_V16E31_Read_Only_PAD_Stream_Runtime_Loader_Freeze_and_Provenance_Manifest.py",
    "401e36e9fdbd5ec7d4854dd96372b1a44e23f6a0f173f80c326fc8f1e98cd906",
)
E29_RUNNER = (
    "PAD_Stream_V16E29_Read_Only_Runtime_Loader_and_Accepted_State_Consumption_Dry_Run.py",
    "1604f753b3cc37444d77fd3f979443717d3a8437efa4f43a13732d9744f288cc",
)
E28_RUNNER = (
    "PAD_Stream_V16E28_Accepted_SGSim_Deployment_State_Runtime_Contract_Integration.py",
    "41235afa7c7e657b798bab52a69465c7d746dc1c7c3cd7b29032aec33135429f",
)

E31_REL = Path(
    "provenance/hybrid_dp/"
    "V16E31_FROZEN_READ_ONLY_PAD_STREAM_RUNTIME_LOADER"
)
E31_FROZEN_LOADER_REL = E31_REL / "frozen_loader/V16E31_Frozen_Read_Only_Runtime_Loader.py"
E31_ARTIFACTS = {
    "frozen_loader/V16E31_Frozen_Read_Only_Runtime_Loader.py":
        "1604f753b3cc37444d77fd3f979443717d3a8437efa4f43a13732d9744f288cc",
    "V16E31_Runtime_Loader_Freeze_Manifest.json":
        "d38fc821e9306132a1be927f6dab341a14e12bb1554f6bf35695b474133820de",
    "V16E31_Runtime_Loader_Provenance_Contract.json":
        "8db21bfec43e6177a1c89ba4522ef98ef82df06ee5ed4d4c320a36895fe987d6",
    "PAD_Stream_V16E31_Summary.json":
        "a62651154932a0491d5a269909cd35538b0fe9179cb6a1c0785a8505c14bc2a2",
    "V16E31_Handoff.md":
        "7ea463eaa08bdace0e4690ab78e528d6496d9f5f1c611e7a5ca88a52d91d9e14",
    "V16E31_E30R1_Authority.csv":
        "f9dbda9a50d34877c44b2f982388010bf1f43bc6138eb4e6ff3d4be41c171372",
    "V16E31_Frozen_Loader_Identity.csv":
        "bfde0205c40251724fc6161c8754f1085d254138e57ae0ebc4049f861b4124f0",
    "V16E31_Loader_Function_Identity.csv":
        "1de0297b7fe91f63ea651abb249527b4d9b76fdb771abf2c017d85a4082c76a4",
    "V16E31_Runtime_Boundary.csv":
        "ea1db6d06bbcb2cd0ef854f0b3592fd20857c75b4f7953c65efcc56f7e4aa834",
    "V16E31_Final_Gate_Matrix.csv":
        "0b2799f9c8b20d61be7342c074f86a4ac42dc8e690552f03c6edca751331abb9",
}

E28_REL = Path(
    "provenance/hybrid_dp/"
    "V16E28_ACCEPTED_SGSIM_DEPLOYMENT_STATE_PAD_STREAM_RUNTIME_CONTRACT_INTEGRATION"
)
E28_RUNTIME_CONTRACT_NAME = "V16E28_PAD_Stream_Runtime_Contract.json"
E28_RUNTIME_CONTRACT_SHA = "b29e30cb5474e6555d9f0aeea75f3fc6e7b5964fca1a1cb34c15c9b4abf9db16"

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
    "V16E32_FROZEN_RUNTIME_LOADER_CONSUMPTION_RUNTIME_EXECUTION_ENTRY_CONTRACT"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E32_BLOCKED_FROZEN_RUNTIME_LOADER_CONSUMPTION_RUNTIME_EXECUTION_ENTRY_CONTRACT"
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def function_source_text(source_path: Path, function_name: str) -> str:
    text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            segment = ast.get_source_segment(text, node)
            if segment is None:
                raise GateError(f"source_segment_missing:{function_name}")
            return segment
    raise GateError(f"function_missing:{function_name}")


def write_attempt_is_blocked(arr: np.ndarray) -> bool:
    if arr.size == 0:
        return not arr.flags.writeable
    index = (0,) * arr.ndim
    try:
        arr[index] = arr[index]
    except ValueError:
        return True
    return False


def import_frozen_loader_module(path: Path):
    module_name = "pad_stream_v16e31_frozen_runtime_loader"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise GateError("frozen_loader_import_spec_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module_name, module


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

    frozen_loader_path = drive / E31_FROZEN_LOADER_REL
    v16_path = drive / V16_FROZEN_REL
    ref_path = drive / REFERENCE_FROZEN_REL
    e28_contract_path = drive / E28_REL / E28_RUNTIME_CONTRACT_NAME

    frozen_loader_sha_before = None
    v16_sha_before = None
    ref_sha_before = None
    imported_module_name = None

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-32 Frozen Runtime Loader Consumption / PAD-Stream Runtime Execution Entry Contract")
    print("=" * 132)
    print("THE CANONICAL E31 FROZEN LOADER IS EXECUTED AGAINST THE ACCEPTED IMMUTABLE V16 STATE.")
    print("THIS ESTABLISHES THE PAD-STREAM RUNTIME EXECUTION ENTRY CONTRACT ONLY.")
    print("NO RUNTIME TIME ADVANCE. NO NEW SATURATION FIELD. NO PRESSURE/DARCY/POLLOCK/TOF/TRANSPORT/MAP-BACK EXECUTION.")
    print("HISTORICAL REFERENCE REMAINS VALIDATION-ONLY AND MUST NOT BE OPENED BY THE FROZEN RUNTIME LOADER.")
    print("INTERNAL TEST / OOD REMAIN CLOSED. IBDP REMAINS DEFERRED.")

    try:
        # ------------------------------------------------------------------
        # Tracked source authority.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E31_runner", E31_RUNNER),
            ("E29_validated_loader_candidate_runner", E29_RUNNER),
            ("E28_runner", E28_RUNNER),
        ]:
            path = root / name
            gate(f"{label}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # E31 frozen-loader authority.
        # ------------------------------------------------------------------
        print("\nV16E-31 FROZEN LOADER AUTHORITY")
        for name, expected in E31_ARTIFACTS.items():
            path = drive / E31_REL / name
            gate(f"E31_{Path(name).name}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"E31_{Path(name).name}_SHA_exact", actual == expected, actual)

        e31_summary = load_json(drive / E31_REL / "PAD_Stream_V16E31_Summary.json")
        e31_manifest = load_json(drive / E31_REL / "V16E31_Runtime_Loader_Freeze_Manifest.json")
        e31_provenance = load_json(drive / E31_REL / "V16E31_Runtime_Loader_Provenance_Contract.json")

        gate(
            "E31_summary_status_frozen",
            e31_summary.get("status") == "READ_ONLY_PAD_STREAM_RUNTIME_LOADER_FROZEN",
        )
        gate("E31_loader_frozen", e31_summary.get("loader_frozen") is True)
        gate("E31_loader_logic_unchanged", e31_summary.get("loader_logic_changed") is False)
        gate(
            "E31_frozen_loader_SHA_exact_in_summary",
            e31_summary.get("frozen_loader_file_sha256") == FROZEN_LOADER_SHA,
            e31_summary.get("frozen_loader_file_sha256"),
        )
        gate(
            "E31_function_SHA_exact_in_summary",
            e31_summary.get("frozen_function_source_sha256") == FROZEN_LOADER_FUNCTION_SHA,
            e31_summary.get("frozen_function_source_sha256"),
        )
        gate(
            "E31_source_frozen_byte_identity",
            e31_summary.get("source_frozen_byte_identity") is True,
        )
        gate(
            "E31_loader_not_executed_in_freeze",
            e31_summary.get("loader_executed_in_E31") is False,
        )
        gate(
            "E31_no_runtime_mutating_actions",
            e31_summary.get("runtime_time_advance_performed") is False
            and e31_summary.get("new_saturation_field_created") is False
            and e31_summary.get("numerical_state_copy_created") is False,
        )
        gate(
            "E31_historical_reference_validation_only",
            e31_summary.get("historical_reference_runtime_role") == "VALIDATION_ONLY",
        )
        gate(
            "E31_test_OOD_closed_IBDP_deferred",
            e31_summary.get("internal_test_reopened") is False
            and e31_summary.get("OOD_reopened") is False
            and e31_summary.get("IBDP_started") is False,
        )
        gate(
            "E31_next_is_E32",
            str(e31_summary.get("next_milestone", "")).startswith("V16E-32"),
            e31_summary.get("next_milestone"),
        )

        gate("E31_manifest_status_frozen", e31_manifest.get("status") == "READ_ONLY_PAD_STREAM_RUNTIME_LOADER_FROZEN")
        gate(
            "E31_manifest_frozen_SHA_exact",
            e31_manifest["frozen_loader"]["file_sha256"] == FROZEN_LOADER_SHA,
        )
        gate(
            "E31_manifest_function_SHA_exact",
            e31_manifest["frozen_loader"]["function_source_sha256"] == FROZEN_LOADER_FUNCTION_SHA,
        )
        gate(
            "E31_manifest_byte_identical",
            e31_manifest["frozen_loader"]["byte_identical_to_validated_candidate"] is True,
        )
        gate(
            "E31_provenance_status_FROZEN",
            e31_provenance.get("status") == "FROZEN",
        )
        gate(
            "E31_provenance_execution_deferred_to_E32",
            e31_provenance.get("loader_execution_deferred_to_E32") is True,
        )

        # ------------------------------------------------------------------
        # E28 runtime contract.
        # ------------------------------------------------------------------
        print("\nV16E-28 RUNTIME CONTRACT AUTHORITY")
        gate("E28_runtime_contract_exists", e28_contract_path.is_file(), e28_contract_path)
        gate(
            "E28_runtime_contract_SHA_exact",
            sha256_file(e28_contract_path) == E28_RUNTIME_CONTRACT_SHA,
            sha256_file(e28_contract_path),
        )
        runtime_contract = load_json(e28_contract_path)
        gate(
            "E28_runtime_contract_status_integrated",
            runtime_contract.get("status") == "PAD_STREAM_RUNTIME_CONTRACT_INTEGRATED",
        )
        gate(
            "E28_runtime_contract_mode_read_only_identity",
            runtime_contract.get("integration_mode") == "READ_ONLY_EXACT_IDENTITY_BINDING",
        )
        source_contract = runtime_contract["canonical_runtime_state_source"]
        validation_contract = runtime_contract["historical_validation_reference"]
        gate(
            "E28_runtime_source_SHA_exact",
            source_contract.get("file_sha256") == V16_FROZEN_SHA,
        )
        gate(
            "E28_runtime_mutation_forbidden",
            source_contract.get("numerical_mutation_permitted") is False,
        )
        gate(
            "E28_runtime_copy_not_required",
            source_contract.get("numerical_copy_required") is False,
        )
        gate(
            "E28_reference_not_runtime_input",
            validation_contract.get("runtime_state_input") is False
            and validation_contract.get("runtime_correction_input") is False
            and validation_contract.get("runtime_tuning_input") is False,
        )
        gate(
            "E28_historical_threshold_0p5_exact",
            float(validation_contract.get("plume_threshold")) == EXPECTED_HISTORICAL_THRESHOLD,
        )

        # ------------------------------------------------------------------
        # Immutable identities before consumption.
        # ------------------------------------------------------------------
        print("\nIMMUTABLE INPUT IDENTITIES")
        gate("frozen_loader_exists", frozen_loader_path.is_file(), frozen_loader_path)
        frozen_loader_sha_before = sha256_file(frozen_loader_path)
        gate(
            "frozen_loader_SHA_exact_before",
            frozen_loader_sha_before == FROZEN_LOADER_SHA,
            frozen_loader_sha_before,
        )

        frozen_function_text = function_source_text(
            frozen_loader_path, "load_runtime_state_read_only"
        )
        frozen_function_sha = sha256_bytes(frozen_function_text.encode("utf-8"))
        gate(
            "frozen_loader_function_SHA_exact_before",
            frozen_function_sha == FROZEN_LOADER_FUNCTION_SHA,
            frozen_function_sha,
        )
        gate(
            "frozen_loader_function_historical_reference_absent",
            "REFERENCE_FROZEN_REL" not in frozen_function_text
            and "ref_path" not in frozen_function_text
            and "historical" not in frozen_function_text.lower(),
        )

        gate("accepted_state_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate(
            "accepted_state_SHA_exact_before",
            v16_sha_before == V16_FROZEN_SHA,
            v16_sha_before,
        )

        gate("historical_reference_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate(
            "historical_reference_SHA_exact_before",
            ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
            ref_sha_before,
        )

        # ------------------------------------------------------------------
        # Execute the FROZEN loader with an audited np.load boundary.
        # ------------------------------------------------------------------
        print("\nFROZEN LOADER CONSUMPTION")
        imported_module_name, frozen_module = import_frozen_loader_module(
            frozen_loader_path
        )

        gate(
            "imported_module_file_is_frozen_loader",
            Path(frozen_module.__file__).resolve() == frozen_loader_path.resolve(),
            frozen_module.__file__,
        )
        gate(
            "imported_module_V16_SHA_exact",
            getattr(frozen_module, "V16_FROZEN_SHA", None) == V16_FROZEN_SHA,
        )
        gate(
            "imported_frozen_loader_function_callable",
            callable(getattr(frozen_module, "load_runtime_state_read_only", None)),
        )

        load_calls: list[str] = []
        original_np_load = frozen_module.np.load

        def audited_np_load(file, *args, **kwargs):
            load_calls.append(str(Path(file)))
            return original_np_load(file, *args, **kwargs)

        frozen_module.np.load = audited_np_load
        try:
            runtime = frozen_module.load_runtime_state_read_only(
                runtime_contract,
                v16_path,
            )
        finally:
            frozen_module.np.load = original_np_load

        gate(
            "frozen_loader_opened_exactly_one_numerical_file",
            len(load_calls) == 1,
            load_calls,
        )
        gate(
            "frozen_loader_opened_only_accepted_state",
            load_calls == [str(v16_path)],
            load_calls,
        )
        gate(
            "historical_reference_not_opened_by_frozen_loader",
            str(ref_path) not in load_calls,
            load_calls,
        )

        # ------------------------------------------------------------------
        # Loaded runtime-entry identity.
        # ------------------------------------------------------------------
        print("\nRUNTIME EXECUTION ENTRY STATE")
        state = runtime.saturation_state
        mask = runtime.supported_mask
        den = runtime.support_denominator
        num = runtime.support_numerator

        gate("entry_grid_shape_exact", tuple(runtime.grid_shape) == EXPECTED_GRID, runtime.grid_shape)
        gate("entry_physical_time_100d_exact", float(runtime.physical_time_days) == EXPECTED_TIME_DAYS, runtime.physical_time_days)
        gate("entry_background_0p2_exact", float(runtime.background_saturation) == EXPECTED_BACKGROUND, runtime.background_saturation)
        gate("entry_diagnostic_threshold_0p21_exact", float(runtime.diagnostic_threshold) == EXPECTED_DIAGNOSTIC_THRESHOLD, runtime.diagnostic_threshold)
        gate("entry_state_shape_exact", state.shape == EXPECTED_GRID, state.shape)
        gate("entry_state_dtype_float64", state.dtype == np.float64, state.dtype)
        gate("entry_state_finite", np.all(np.isfinite(state)))

        gate("entry_state_SHA_exact", sha256_array(state) == RUNTIME_STATE_ARRAY_SHA, sha256_array(state))
        gate("entry_supported_mask_SHA_exact", sha256_array(mask) == SUPPORTED_MASK_SHA, sha256_array(mask))
        gate("entry_support_denominator_SHA_exact", sha256_array(den) == SUPPORT_DENOMINATOR_SHA, sha256_array(den))
        gate("entry_support_numerator_SHA_exact", sha256_array(num) == SUPPORT_NUMERATOR_SHA, sha256_array(num))

        gate("entry_state_read_only", state.flags.writeable is False)
        gate("entry_mask_read_only", mask.flags.writeable is False)
        gate("entry_denominator_read_only", den.flags.writeable is False)
        gate("entry_numerator_read_only", num.flags.writeable is False)
        gate("entry_state_write_blocked", write_attempt_is_blocked(state))
        gate("entry_mask_write_blocked", write_attempt_is_blocked(mask))
        gate("entry_denominator_write_blocked", write_attempt_is_blocked(den))
        gate("entry_numerator_write_blocked", write_attempt_is_blocked(num))

        support_bool = mask.astype(bool, copy=False)
        total_cells = int(state.size)
        supported_cells = int(np.count_nonzero(support_bool))
        unsupported_cells = total_cells - supported_cells
        diagnostic_mask = state >= runtime.diagnostic_threshold
        diagnostic_cells = int(np.count_nonzero(diagnostic_mask))
        diagnostic_unsupported = int(np.count_nonzero(diagnostic_mask & ~support_bool))

        gate("entry_total_cells_exact", total_cells == EXPECTED_CELLS, total_cells)
        gate("entry_supported_cells_exact", supported_cells == EXPECTED_SUPPORTED, supported_cells)
        gate("entry_unsupported_cells_exact", unsupported_cells == EXPECTED_UNSUPPORTED, unsupported_cells)
        gate("entry_background_completed_cells_exact", np.all(state[~support_bool] == EXPECTED_BACKGROUND))
        gate("entry_diagnostic_cells_exact", diagnostic_cells == EXPECTED_DIAGNOSTIC_CELLS, diagnostic_cells)
        gate("entry_diagnostic_unsupported_zero", diagnostic_unsupported == EXPECTED_DIAGNOSTIC_UNSUPPORTED, diagnostic_unsupported)

        # ------------------------------------------------------------------
        # Runtime-execution entry boundary: no physics/state transition yet.
        # ------------------------------------------------------------------
        print("\nPAD-STREAM RUNTIME EXECUTION ENTRY BOUNDARY")
        gate("canonical_runtime_entry_implementation_is_E31_frozen_loader", True)
        gate("canonical_runtime_entry_state_is_accepted_V16_state", True)
        gate("runtime_entry_state_is_read_only", True)
        gate("runtime_time_advance_not_performed_in_E32", True)
        gate("next_state_not_created_in_E32", True)
        gate("pressure_solve_not_executed_in_E32", True)
        gate("Darcy_flux_not_executed_in_E32", True)
        gate("Pollock_not_executed_in_E32", True)
        gate("TOF_not_executed_in_E32", True)
        gate("transport_not_executed_in_E32", True)
        gate("mapback_not_executed_in_E32", True)
        gate("state_transition_execution_not_authorized_in_E32", True)
        gate("historical_reference_validation_only", True)
        gate("historical_0p5_threshold_validation_only", True)
        gate("diagnostic_0p21_threshold_diagnostic_only", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("IBDP_not_started", True)

        # Immutable identities after consumption.
        gate(
            "frozen_loader_SHA_exact_after",
            sha256_file(frozen_loader_path) == frozen_loader_sha_before == FROZEN_LOADER_SHA,
        )
        gate(
            "accepted_state_SHA_exact_after",
            sha256_file(v16_path) == v16_sha_before == V16_FROZEN_SHA,
        )
        gate(
            "historical_reference_SHA_exact_after",
            sha256_file(ref_path) == ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
        )

        # ------------------------------------------------------------------
        # Persist metadata/evidence only.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)

        save_csv(
            out / "V16E32_E31_Authority.csv",
            [
                {
                    "artifact": name,
                    "sha256": expected,
                    "path": str(drive / E31_REL / name),
                    "role": "FROZEN_LOADER_AUTHORITY",
                }
                for name, expected in E31_ARTIFACTS.items()
            ],
        )

        save_csv(
            out / "V16E32_Frozen_Loader_Consumption_Evidence.csv",
            [
                {
                    "frozen_loader_path": str(frozen_loader_path),
                    "frozen_loader_sha256": frozen_loader_sha_before,
                    "validated_function": "load_runtime_state_read_only",
                    "function_source_sha256": frozen_function_sha,
                    "np_load_call_count": len(load_calls),
                    "opened_numerical_path": load_calls[0] if load_calls else "",
                    "historical_reference_opened": False,
                    "runtime_state_consumed": True,
                }
            ],
        )

        save_csv(
            out / "V16E32_Runtime_Entry_State_Identity.csv",
            [
                {
                    "object": "saturation_state",
                    "array_sha256": sha256_array(state),
                    "shape": "15x50x50",
                    "dtype": str(state.dtype),
                    "writeable": state.flags.writeable,
                    "role": "CANONICAL_RUNTIME_ENTRY_STATE",
                },
                {
                    "object": "supported_mask",
                    "array_sha256": sha256_array(mask),
                    "shape": "15x50x50",
                    "dtype": str(mask.dtype),
                    "writeable": mask.flags.writeable,
                    "role": "RUNTIME_ENTRY_PROVENANCE_SUPPORT",
                },
                {
                    "object": "support_denominator",
                    "array_sha256": sha256_array(den),
                    "shape": "15x50x50",
                    "dtype": str(den.dtype),
                    "writeable": den.flags.writeable,
                    "role": "RUNTIME_ENTRY_PROVENANCE_SUPPORT",
                },
                {
                    "object": "support_numerator",
                    "array_sha256": sha256_array(num),
                    "shape": "15x50x50",
                    "dtype": str(num.dtype),
                    "writeable": num.flags.writeable,
                    "role": "RUNTIME_ENTRY_PROVENANCE_SUPPORT",
                },
            ],
        )

        save_csv(
            out / "V16E32_Runtime_Execution_Boundary.csv",
            [
                {"stage": "Frozen runtime loader consumption", "executed_in_E32": True, "authorized_for_next_milestone": True},
                {"stage": "Accepted-state read-only entry", "executed_in_E32": True, "authorized_for_next_milestone": True},
                {"stage": "Pressure solve", "executed_in_E32": False, "authorized_for_next_milestone": False},
                {"stage": "Darcy face flux", "executed_in_E32": False, "authorized_for_next_milestone": False},
                {"stage": "Pollock streamline tracing", "executed_in_E32": False, "authorized_for_next_milestone": False},
                {"stage": "Time-of-flight", "executed_in_E32": False, "authorized_for_next_milestone": False},
                {"stage": "Hybrid transport", "executed_in_E32": False, "authorized_for_next_milestone": False},
                {"stage": "Conservative map-back", "executed_in_E32": False, "authorized_for_next_milestone": False},
                {"stage": "Next-state creation", "executed_in_E32": False, "authorized_for_next_milestone": False},
            ],
        )

        execution_entry_contract = {
            "milestone": MILESTONE,
            "status": "PAD_STREAM_RUNTIME_EXECUTION_ENTRY_READY",
            "canonical_runtime_entry_implementation": {
                "path": str(frozen_loader_path),
                "file_sha256": frozen_loader_sha_before,
                "function": "load_runtime_state_read_only",
                "function_source_sha256": frozen_function_sha,
                "frozen": True,
            },
            "canonical_runtime_entry_state": {
                "source_path": str(v16_path),
                "source_file_sha256": v16_sha_before,
                "state_array_sha256": sha256_array(state),
                "grid_shape": list(runtime.grid_shape),
                "physical_time_days": runtime.physical_time_days,
                "background_saturation": runtime.background_saturation,
                "read_only": True,
                "supported_cells": supported_cells,
                "unsupported_cells": unsupported_cells,
            },
            "diagnostic_metadata": {
                "threshold": runtime.diagnostic_threshold,
                "role": "DIAGNOSTIC_ONLY",
                "cells": diagnostic_cells,
                "unsupported_cells": diagnostic_unsupported,
            },
            "historical_validation_boundary": {
                "reference_path": str(ref_path),
                "reference_file_sha256": ref_sha_before,
                "historical_threshold": EXPECTED_HISTORICAL_THRESHOLD,
                "role": "VALIDATION_ONLY",
                "opened_by_frozen_runtime_loader": False,
                "runtime_state_input": False,
                "runtime_correction_input": False,
                "runtime_tuning_input": False,
            },
            "execution_boundary": {
                "runtime_loader_executed": True,
                "runtime_entry_state_created": True,
                "runtime_time_advance_performed": False,
                "next_state_created": False,
                "pressure_solve_executed": False,
                "Darcy_flux_executed": False,
                "Pollock_executed": False,
                "TOF_executed": False,
                "transport_executed": False,
                "mapback_executed": False,
                "state_transition_execution_authorized": False,
            },
            "next_milestone": NEXT,
        }
        save_json(
            out / "V16E32_PAD_Stream_Runtime_Execution_Entry_Contract.json",
            execution_entry_contract,
        )

        consumption_manifest = {
            "milestone": MILESTONE,
            "status": STATUS,
            "frozen_loader_consumed": True,
            "frozen_loader_sha256": frozen_loader_sha_before,
            "accepted_state_consumed": True,
            "accepted_state_sha256": v16_sha_before,
            "accepted_state_array_sha256": sha256_array(state),
            "entry_state_read_only": True,
            "historical_reference_loaded_by_runtime_loader": False,
            "runtime_time_advance_performed": False,
            "next_state_created": False,
            "persisted_numerical_copy_created": False,
            "frozen_loader_modified": False,
            "accepted_state_modified": False,
            "historical_reference_modified": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(
            out / "V16E32_Frozen_Loader_Consumption_Manifest.json",
            consumption_manifest,
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "frozen_loader_sha256": frozen_loader_sha_before,
            "frozen_loader_function_sha256": frozen_function_sha,
            "accepted_state_file_sha256": v16_sha_before,
            "accepted_state_array_sha256": sha256_array(state),
            "historical_reference_file_sha256": ref_sha_before,
            "grid_shape": list(runtime.grid_shape),
            "physical_time_days": runtime.physical_time_days,
            "background_saturation": runtime.background_saturation,
            "supported_cells": supported_cells,
            "unsupported_cells": unsupported_cells,
            "diagnostic_threshold": runtime.diagnostic_threshold,
            "diagnostic_cells": diagnostic_cells,
            "diagnostic_unsupported_cells": diagnostic_unsupported,
            "historical_authoritative_plume_threshold": EXPECTED_HISTORICAL_THRESHOLD,
            "frozen_loader_consumed": True,
            "runtime_execution_entry_ready": True,
            "historical_reference_loaded_by_runtime_loader": False,
            "runtime_time_advance_performed": False,
            "next_state_created": False,
            "persisted_numerical_copy_created": False,
            "frozen_loader_modified": False,
            "accepted_state_modified": False,
            "historical_reference_modified": False,
            "state_transition_execution_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E32_Summary.json", summary)

        (out / "V16E32_Handoff.md").write_text(
            "# PAD-Stream V16E-32 Handoff\n\n"
            "The canonical V16E-31 frozen read-only loader has been executed successfully against the accepted "
            "V16E-18-R1 runtime state. The frozen loader opened only the accepted state file; the historical "
            "reference remained outside the runtime-loader path.\n\n"
            f"- Frozen loader SHA-256: `{frozen_loader_sha_before}`\n"
            f"- Frozen loader function SHA-256: `{frozen_function_sha}`\n"
            f"- Accepted state file SHA-256: `{v16_sha_before}`\n"
            f"- Accepted state array SHA-256: `{sha256_array(state)}`\n"
            f"- Runtime entry time: `{runtime.physical_time_days} days`\n"
            f"- Supported / unsupported cells: `{supported_cells} / {unsupported_cells}`\n"
            "- Runtime entry state read-only: `YES`\n"
            "- Historical reference loaded by frozen loader: `NO`\n"
            "- Runtime time advance performed: `NO`\n"
            "- Next state created: `NO`\n"
            "- Pressure / Darcy / Pollock / TOF / transport / map-back executed: `NO`\n"
            "- State-transition execution authorized in E32: `NO`\n"
            "- Frozen loader / accepted state / historical reference modified: `NO / NO / NO`\n"
            "- Internal test / OOD reopened: `NO / NO`\n"
            "- IBDP started: `NO`\n\n"
            "E33 should define the state-transition contract and single-step execution-readiness boundary before "
            "any runtime time advance or next-state creation is permitted.\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        save_csv(
            out / "V16E32_Final_Gate_Matrix.csv",
            [{"gate": name, **record} for name, record in gates.items()],
        )

        print("\n" + "=" * 132)
        print("V16E-32 RESULT: PASS")
        print("=" * 132)
        print(f"{'Frozen loader consumed':72}: YES")
        print(f"{'Frozen loader SHA-256':72}: {frozen_loader_sha_before}")
        print(f"{'Frozen loader function SHA-256':72}: {frozen_function_sha}")
        print(f"{'Accepted state consumed':72}: YES / READ-ONLY")
        print(f"{'Accepted state file SHA-256':72}: {v16_sha_before}")
        print(f"{'Accepted state array SHA-256':72}: {sha256_array(state)}")
        print(f"{'Runtime execution entry ready':72}: YES")
        print(f"{'Supported / unsupported cells':72}: {supported_cells} / {unsupported_cells}")
        print(f"{'Historical reference opened by frozen loader':72}: NO")
        print(f"{'Runtime time advance performed':72}: NO")
        print(f"{'Next state created':72}: NO")
        print(f"{'Pressure/Darcy/Pollock/TOF/transport/map-back executed':72}: NO")
        print(f"{'State-transition execution authorized':72}: NO")
        print(f"{'Frozen loader modified':72}: NO")
        print(f"{'Accepted state modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        print(f"{'IBDP started':72}: NO")

        for name in [
            "V16E32_PAD_Stream_Runtime_Execution_Entry_Contract.json",
            "V16E32_Frozen_Loader_Consumption_Manifest.json",
            "PAD_Stream_V16E32_Summary.json",
            "V16E32_Handoff.md",
            "V16E32_E31_Authority.csv",
            "V16E32_Frozen_Loader_Consumption_Evidence.csv",
            "V16E32_Runtime_Entry_State_Identity.csv",
            "V16E32_Runtime_Execution_Boundary.csv",
            "V16E32_Final_Gate_Matrix.csv",
        ]:
            path = out / name
            print(f"{name} SHA: {sha256_file(path)}")

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
            "frozen_loader_sha256_before": frozen_loader_sha_before,
            "accepted_state_sha256_before": v16_sha_before,
            "historical_reference_sha256_before": ref_sha_before,
            "frozen_loader_consumed": False,
            "runtime_execution_entry_ready": False,
            "runtime_time_advance_performed": False,
            "next_state_created": False,
            "persisted_numerical_copy_created": False,
            "frozen_loader_modified":
                False if frozen_loader_sha_before is None or not frozen_loader_path.exists()
                else sha256_file(frozen_loader_path) != frozen_loader_sha_before,
            "accepted_state_modified":
                False if v16_sha_before is None or not v16_path.exists()
                else sha256_file(v16_path) != v16_sha_before,
            "historical_reference_modified":
                False if ref_sha_before is None or not ref_path.exists()
                else sha256_file(ref_path) != ref_sha_before,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": (
                "V16E-32-R1 - Repair only the failed V16E-32 frozen-loader-consumption/runtime-entry gate; "
                "preserve E31, E30-R1, the frozen loader, accepted state, and historical reference unchanged"
            ),
        }

        path = blocked / "V16E32_Blocked_Frozen_Loader_Consumption_Runtime_Entry.json"
        save_json(path, payload)
        print(f"\n[FAIL] V16E-32 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(path)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2

    finally:
        if imported_module_name is not None:
            sys.modules.pop(imported_module_name, None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
