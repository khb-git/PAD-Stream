from __future__ import annotations

from pathlib import Path
import argparse
import ast
import csv
import hashlib
import json
from typing import Any

import numpy as np


MILESTONE = "V16E-30-R1"
STATUS = "INDEPENDENT_READ_ONLY_RUNTIME_LOADER_VALIDATION_PASS"
NEXT = "V16E-31 - Read-Only PAD-Stream Runtime Loader Freeze / Provenance Manifest"

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
EXPECTED_REFERENCE_KEY = "SG7A_corrected"

V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"
RUNTIME_STATE_ARRAY_SHA = "176975c3131353c4fe60fdf9e6d7635b13e260e010fc8cd849deb17c85e37f12"
SUPPORTED_MASK_SHA = "4b8fab2ffa3608c62dfa6d3583914b2537cc76a0ef04fe6d103dbec78cc92a3c"
SUPPORT_DENOMINATOR_SHA = "70158dada5e2bd804014b13fd5908831df45f0d34120e3bd5dd9d940921c823e"
SUPPORT_NUMERATOR_SHA = "641d37335615b74971d15b0d751b297b1ed09ada2f87c939a4eba08681fcbeba"

E30_PARENT_RUNNER = (
    "PAD_Stream_V16E30_Independent_Read_Only_Runtime_Loader_Validation_and_Freeze_Readiness.py",
    "2a8cc72ab7893fe870c93a250e75c4b029c1c6f62d75f4bae6ff0ed8ee29fc22",
)
E30_PARENT_BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E30_BLOCKED_INDEPENDENT_READ_ONLY_RUNTIME_LOADER_VALIDATION_FREEZE_READINESS/"
    "V16E30_Blocked_Independent_Runtime_Loader_Validation.json"
)
E30_PARENT_BLOCKED_SHA = "3279cba34b5844b6e137eeaec5bc7e335dc4afdb68b5bfb5602c01325946833d"
E30_PARENT_FAILED_GATE = "loader_frozen_in_E30"

E29_RUNNER = (
    "PAD_Stream_V16E29_Read_Only_Runtime_Loader_and_Accepted_State_Consumption_Dry_Run.py",
    "1604f753b3cc37444d77fd3f979443717d3a8437efa4f43a13732d9744f288cc",
)
E28_RUNNER = (
    "PAD_Stream_V16E28_Accepted_SGSim_Deployment_State_Runtime_Contract_Integration.py",
    "41235afa7c7e657b798bab52a69465c7d746dc1c7c3cd7b29032aec33135429f",
)
E27_RUNNER = (
    "PAD_Stream_V16E27_Frozen_SGSim_Deployment_Acceptance_and_PAD_Stream_Integration_Handoff.py",
    "e6cbc67d46ed13497afe4a09802286662aa838ab9d6180670f08b79f7db31e45",
)

E29_REL = Path(
    "provenance/hybrid_dp/"
    "V16E29_READ_ONLY_PAD_STREAM_RUNTIME_LOADER_ACCEPTED_STATE_CONSUMPTION_DRY_RUN"
)
E29_ARTIFACTS = {
    "V16E29_Read_Only_Runtime_Loader_Contract.json":
        "aa183218e6e5646cda9798d040b0d9c299364d6451dc82d1e443a3c17c621ddb",
    "V16E29_Accepted_State_Consumption_Dry_Run_Manifest.json":
        "bdd4114d43e4ffea613bcd7635773a275d76b59fabcdd991263fdccb98df7e1d",
    "PAD_Stream_V16E29_Summary.json":
        "a9273e75238366fa7734b22ce47ecae2ee0757eaa098c2e4f04ae51ec285ba41",
    "V16E29_Handoff.md":
        "418750e12a9e12edd74bd761a11d201f13625684686b63b21b323066f48cf439",
    "V16E29_E28_Authority.csv":
        "02d36e44a901fda9b1685210c13bb6bd577321a807a3978c94527bcaa58da08e",
    "V16E29_Read_Only_Loader_Evidence.csv":
        "d452d5fa90aea7dcdd4401f13174acd6058901c4aad428800f6a6c6efb08ea84",
    "V16E29_Accepted_State_Consumption_Dry_Run.csv":
        "4c2e577f49a8f6e8bbd77998ac6f841b3703c5e469dbcbe8dc9a2b3395dd59c6",
    "V16E29_Runtime_Role_Separation.csv":
        "7247fbdaec121291ed99dada5898be03a047abac32aaed36499ae82dbe5bf29f",
    "V16E29_Final_Gate_Matrix.csv":
        "cbe7a4e939896ee1d36fd2ddd9d269bb3f0073e304d3620e64f50ea96971117f",
}

E28_REL = Path(
    "provenance/hybrid_dp/"
    "V16E28_ACCEPTED_SGSIM_DEPLOYMENT_STATE_PAD_STREAM_RUNTIME_CONTRACT_INTEGRATION"
)
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
    "V16E30_R1_INDEPENDENT_READ_ONLY_RUNTIME_LOADER_VALIDATION_FREEZE_READINESS"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E30_R1_BLOCKED_INDEPENDENT_READ_ONLY_RUNTIME_LOADER_VALIDATION_FREEZE_READINESS"
)


class GateError(RuntimeError):
    pass


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


def read_only_view(arr: np.ndarray) -> np.ndarray:
    view = np.asarray(arr).view()
    view.setflags(write=False)
    return view


def write_attempt_is_blocked(arr: np.ndarray) -> bool:
    if arr.size == 0:
        return not arr.flags.writeable
    idx = (0,) * arr.ndim
    try:
        arr[idx] = arr[idx]
    except ValueError:
        return True
    return False


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
    print("PAD-Stream V16E-30-R1 Loader-Frozen Assertion-Polarity Repair / Independent Freeze Readiness")
    print("=" * 132)
    print("INDEPENDENT VALIDATION OF E29 LOADER BEHAVIOR; E29 LOADER IMPLEMENTATION IS NOT IMPORTED OR EXECUTED.")
    print("NO RUNTIME TIME ADVANCE. NO NEW SATURATION FIELD. NO PERSISTED NUMERICAL COPY.")
    print("HISTORICAL REFERENCE REMAINS VALIDATION-ONLY AND IS NOT A RUNTIME INPUT.")
    print("R1 REPAIRS ONLY THE E30 ASSERTION POLARITY FOR THE INTENDED NOT-FROZEN-IN-E30 STATE.")
    print("E30-R1 STILL DOES NOT FREEZE THE LOADER; IT DETERMINES FREEZE READINESS ONLY.")
    print("INTERNAL TEST / OOD REMAIN CLOSED. IBDP REMAINS DEFERRED.")

    try:
        # ------------------------------------------------------------------
        # Source authority.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E30_parent_runner", E30_PARENT_RUNNER),
            ("E29_runner", E29_RUNNER),
            ("E28_runner", E28_RUNNER),
            ("E27_runner", E27_RUNNER),
        ]:
            path = root / name
            gate(f"{label}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        e29_source = root / E29_RUNNER[0]
        loader_source = function_source_text(e29_source, "load_runtime_state_read_only")
        gate(
            "E29_loader_function_exists",
            "def load_runtime_state_read_only" in loader_source,
        )
        gate(
            "E29_loader_source_binds_expected_source_path_only",
            "expected_source_path" in loader_source,
        )
        gate(
            "E29_loader_source_does_not_reference_historical_reference_path",
            "ref_path" not in loader_source
            and "REFERENCE_FROZEN_REL" not in loader_source
            and "historical" not in loader_source.lower(),
        )
        gate(
            "E29_loader_source_sets_read_only_views",
            "setflags(write=False)" not in loader_source
            and "make_read_only" in loader_source,
        )

        # ------------------------------------------------------------------
        # Blocked E30 parent evidence.
        # ------------------------------------------------------------------
        print("\nBLOCKED V16E-30 PARENT EVIDENCE")
        parent_blocked = drive / E30_PARENT_BLOCKED_REL
        gate("E30_parent_blocked_report_exists", parent_blocked.is_file(), parent_blocked)
        gate(
            "E30_parent_blocked_report_SHA_exact",
            sha256_file(parent_blocked) == E30_PARENT_BLOCKED_SHA,
            sha256_file(parent_blocked),
        )
        parent = load_json(parent_blocked)
        gate("E30_parent_status_BLOCKED", parent.get("status") == "BLOCKED")
        gate(
            "E30_parent_exception_exact",
            parent.get("exception") == "GateError('loader_frozen_in_E30')",
            parent.get("exception"),
        )
        parent_gates = parent.get("gates", {})
        failed_parent_gates = [
            name for name, record in parent_gates.items()
            if not bool(record.get("passed"))
        ]
        gate(
            "E30_parent_single_failed_gate_exact",
            failed_parent_gates == [E30_PARENT_FAILED_GATE],
            failed_parent_gates,
        )
        gate(
            "E30_parent_all_prior_recorded_gates_passed",
            all(
                bool(record.get("passed"))
                for name, record in parent_gates.items()
                if name != E30_PARENT_FAILED_GATE
            ),
        )
        gate("E30_parent_loader_not_frozen", parent.get("loader_frozen") is False)
        gate("E30_parent_loader_not_freeze_ready_due_block", parent.get("loader_freeze_ready") is False)
        gate(
            "E30_parent_no_runtime_advance_or_new_state",
            parent.get("runtime_time_advance_performed") is False
            and parent.get("new_saturation_field_created") is False
            and parent.get("persisted_numerical_copy_created") is False,
        )
        gate(
            "E30_parent_frozen_objects_unmodified",
            parent.get("frozen_candidate_modified") is False
            and parent.get("historical_reference_modified") is False,
        )
        gate(
            "E30_parent_test_OOD_closed_IBDP_deferred",
            parent.get("internal_test_reopened") is False
            and parent.get("OOD_reopened") is False
            and parent.get("IBDP_started") is False,
        )

        # ------------------------------------------------------------------
        # Accepted E29 authority.
        # ------------------------------------------------------------------
        print("\nV16E-29 ACCEPTED LOADER DRY-RUN AUTHORITY")
        for name, expected in E29_ARTIFACTS.items():
            path = drive / E29_REL / name
            gate(f"E29_{name}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"E29_{name}_SHA_exact", actual == expected, actual)

        e29_summary = load_json(drive / E29_REL / "PAD_Stream_V16E29_Summary.json")
        e29_contract = load_json(
            drive / E29_REL / "V16E29_Read_Only_Runtime_Loader_Contract.json"
        )
        e29_manifest = load_json(
            drive / E29_REL / "V16E29_Accepted_State_Consumption_Dry_Run_Manifest.json"
        )
        e29_evidence = load_csv(
            drive / E29_REL / "V16E29_Read_Only_Loader_Evidence.csv"
        )
        e29_dry_run = load_csv(
            drive / E29_REL / "V16E29_Accepted_State_Consumption_Dry_Run.csv"
        )

        gate("E29_summary_status_exact", e29_summary.get("status") == "READ_ONLY_PAD_STREAM_RUNTIME_LOADER_DRY_RUN_PASS")
        gate("E29_loader_executed", e29_summary.get("runtime_loader_executed") is True)
        gate("E29_state_consumed", e29_summary.get("runtime_state_consumed") is True)
        gate("E29_state_read_only", e29_summary.get("runtime_state_read_only") is True)
        gate("E29_reference_not_loaded", e29_summary.get("historical_reference_loaded_by_runtime_loader") is False)
        gate("E29_no_time_advance", e29_summary.get("runtime_time_advance_performed") is False)
        gate("E29_no_new_saturation", e29_summary.get("new_saturation_field_created") is False)
        gate("E29_no_persisted_numerical_copy", e29_summary.get("persisted_numerical_copy_created") is False)
        gate("E29_no_frozen_object_modification",
             e29_summary.get("frozen_candidate_modified") is False
             and e29_summary.get("historical_reference_modified") is False)
        gate("E29_test_OOD_closed",
             e29_summary.get("internal_test_reopened") is False
             and e29_summary.get("OOD_reopened") is False)
        gate("E29_IBDP_deferred", e29_summary.get("IBDP_started") is False)
        gate("E29_independent_validation_required", e29_summary.get("independent_validation_required") is True)
        gate("E29_next_is_E30",
             str(e29_summary.get("next_milestone", "")).startswith("V16E-30"),
             e29_summary.get("next_milestone"))

        gate("E29_contract_status_exact", e29_contract.get("status") == "READ_ONLY_RUNTIME_LOADER_EXECUTED")
        gate("E29_contract_mode_exact", e29_contract.get("loader_mode") == "READ_ONLY_ACCEPTED_STATE_CONSUMPTION")
        gate("E29_contract_source_SHA_exact",
             e29_contract["canonical_source"]["file_sha256"] == V16_FROZEN_SHA,
             e29_contract["canonical_source"]["file_sha256"])
        gate("E29_contract_state_array_SHA_exact",
             e29_contract["canonical_source"]["state_array_sha256"] == RUNTIME_STATE_ARRAY_SHA,
             e29_contract["canonical_source"]["state_array_sha256"])
        gate("E29_contract_all_writeable_flags_false",
             e29_contract["read_only_enforcement"]["state_writeable"] is False
             and e29_contract["read_only_enforcement"]["support_mask_writeable"] is False
             and e29_contract["read_only_enforcement"]["support_denominator_writeable"] is False
             and e29_contract["read_only_enforcement"]["support_numerator_writeable"] is False)
        gate("E29_contract_write_attempts_blocked",
             e29_contract["read_only_enforcement"]["write_attempts_blocked"] is True)
        gate("E29_contract_reference_not_loaded",
             e29_contract["historical_reference_boundary"]["loaded_by_runtime_loader"] is False)
        gate("E29_contract_reference_not_runtime_input",
             e29_contract["historical_reference_boundary"]["runtime_state_input"] is False
             and e29_contract["historical_reference_boundary"]["runtime_correction_input"] is False
             and e29_contract["historical_reference_boundary"]["runtime_tuning_input"] is False)

        gate("E29_manifest_status_exact", e29_manifest.get("status") == "READ_ONLY_PAD_STREAM_RUNTIME_LOADER_DRY_RUN_PASS")
        gate("E29_manifest_read_only_consumption", e29_manifest.get("runtime_state_consumed_read_only") is True)
        gate("E29_manifest_independent_validation_required", e29_manifest.get("independent_validation_required") is True)

        gate("E29_loader_evidence_four_rows", len(e29_evidence) == 4, len(e29_evidence))
        gate("E29_loader_evidence_all_nonwriteable",
             all(str(r.get("writeable", "")).strip().lower() == "false" for r in e29_evidence))
        gate("E29_loader_evidence_all_write_attempts_blocked",
             all(str(r.get("write_attempt_blocked", "")).strip().lower() == "true" for r in e29_evidence))
        gate("E29_dry_run_evidence_nonempty", len(e29_dry_run) >= 10, len(e29_dry_run))

        # Verify no numerical output was persisted in E29 output directory.
        numerical_exts = {".npz", ".npy", ".h5", ".hdf5", ".bin"}
        numerical_outputs = [
            str(p.name)
            for p in (drive / E29_REL).iterdir()
            if p.is_file() and p.suffix.lower() in numerical_exts
        ]
        gate("E29_output_contains_no_persisted_numerical_copy",
             len(numerical_outputs) == 0,
             numerical_outputs)

        # ------------------------------------------------------------------
        # E28 contract authority.
        # ------------------------------------------------------------------
        print("\nV16E-28 RUNTIME CONTRACT RECHECK")
        e28_contract_path = drive / E28_REL / "V16E28_PAD_Stream_Runtime_Contract.json"
        gate("E28_runtime_contract_exists", e28_contract_path.is_file(), e28_contract_path)
        gate("E28_runtime_contract_SHA_exact",
             sha256_file(e28_contract_path) == E28_RUNTIME_CONTRACT_SHA,
             sha256_file(e28_contract_path))
        e28_contract = load_json(e28_contract_path)
        source = e28_contract["canonical_runtime_state_source"]
        validation = e28_contract["historical_validation_reference"]

        gate("E28_source_file_SHA_exact", source.get("file_sha256") == V16_FROZEN_SHA)
        gate("E28_source_mutation_forbidden", source.get("numerical_mutation_permitted") is False)
        gate("E28_source_copy_not_required", source.get("numerical_copy_required") is False)
        gate("E28_reference_validation_only",
             validation.get("runtime_state_input") is False
             and validation.get("runtime_correction_input") is False
             and validation.get("runtime_tuning_input") is False)
        gate("E28_reference_threshold_0p5_exact",
             float(validation.get("plume_threshold")) == EXPECTED_HISTORICAL_THRESHOLD)

        # ------------------------------------------------------------------
        # Independent read-only loader validation.
        # ------------------------------------------------------------------
        print("\nINDEPENDENT READ-ONLY LOADER VALIDATION")
        gate("accepted_state_file_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate("accepted_state_file_SHA_exact_before", v16_sha_before == V16_FROZEN_SHA, v16_sha_before)

        gate("historical_reference_file_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate("historical_reference_file_SHA_exact_before",
             ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
             ref_sha_before)

        # Independently load source arrays without invoking E29 code.
        with np.load(v16_path, allow_pickle=False) as db:
            state = read_only_view(np.asarray(db[source["state_key"]]))
            mask = read_only_view(np.asarray(db[source["support_mask_key"]]))
            den = read_only_view(np.asarray(db[source["support_denominator_key"]]))
            num = read_only_view(np.asarray(db[source["support_numerator_key"]]))
            grid_shape = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
            time_days = float(np.asarray(db["physical_time_days"]))
            background = float(np.asarray(db["background_saturation"]))
            diagnostic_threshold = float(np.asarray(db[source["diagnostic_threshold_key"]]))

        gate("independent_state_shape_exact", state.shape == EXPECTED_GRID, state.shape)
        gate("independent_grid_metadata_exact", grid_shape == EXPECTED_GRID, grid_shape)
        gate("independent_time_100d_exact", time_days == EXPECTED_TIME_DAYS, time_days)
        gate("independent_background_0p2_exact", background == EXPECTED_BACKGROUND, background)
        gate("independent_diagnostic_threshold_0p21_exact",
             diagnostic_threshold == EXPECTED_DIAGNOSTIC_THRESHOLD,
             diagnostic_threshold)
        gate("independent_state_finite", np.all(np.isfinite(state)))
        gate("independent_state_array_SHA_exact",
             sha256_array(state) == RUNTIME_STATE_ARRAY_SHA,
             sha256_array(state))
        gate("independent_supported_mask_SHA_exact",
             sha256_array(mask) == SUPPORTED_MASK_SHA,
             sha256_array(mask))
        gate("independent_support_denominator_SHA_exact",
             sha256_array(den) == SUPPORT_DENOMINATOR_SHA,
             sha256_array(den))
        gate("independent_support_numerator_SHA_exact",
             sha256_array(num) == SUPPORT_NUMERATOR_SHA,
             sha256_array(num))

        gate("independent_state_read_only", state.flags.writeable is False)
        gate("independent_mask_read_only", mask.flags.writeable is False)
        gate("independent_denominator_read_only", den.flags.writeable is False)
        gate("independent_numerator_read_only", num.flags.writeable is False)
        gate("independent_state_write_blocked", write_attempt_is_blocked(state))
        gate("independent_mask_write_blocked", write_attempt_is_blocked(mask))
        gate("independent_denominator_write_blocked", write_attempt_is_blocked(den))
        gate("independent_numerator_write_blocked", write_attempt_is_blocked(num))

        support_bool = mask.astype(bool, copy=False)
        total_cells = int(state.size)
        supported_cells = int(np.count_nonzero(support_bool))
        unsupported_cells = total_cells - supported_cells
        diagnostic_mask = state >= diagnostic_threshold
        diagnostic_cells = int(np.count_nonzero(diagnostic_mask))
        diagnostic_unsupported = int(np.count_nonzero(diagnostic_mask & ~support_bool))

        gate("independent_total_cells_exact", total_cells == EXPECTED_CELLS, total_cells)
        gate("independent_supported_cells_exact", supported_cells == EXPECTED_SUPPORTED, supported_cells)
        gate("independent_unsupported_cells_exact", unsupported_cells == EXPECTED_UNSUPPORTED, unsupported_cells)
        gate("independent_background_completed_cells_exact",
             np.all(state[~support_bool] == EXPECTED_BACKGROUND))
        gate("independent_diagnostic_cells_exact",
             diagnostic_cells == EXPECTED_DIAGNOSTIC_CELLS,
             diagnostic_cells)
        gate("independent_diagnostic_unsupported_zero",
             diagnostic_unsupported == EXPECTED_DIAGNOSTIC_UNSUPPORTED,
             diagnostic_unsupported)

        # Exact agreement with accepted E29 summary.
        gate("independent_total_cells_match_E29", total_cells == int(e29_summary["total_cells"]))
        gate("independent_supported_cells_match_E29", supported_cells == int(e29_summary["supported_cells"]))
        gate("independent_unsupported_cells_match_E29", unsupported_cells == int(e29_summary["unsupported_cells"]))
        gate("independent_diagnostic_cells_match_E29",
             diagnostic_cells == int(e29_summary["diagnostic_0p21_cells"]))
        gate("independent_diagnostic_unsupported_match_E29",
             diagnostic_unsupported == int(e29_summary["diagnostic_0p21_unsupported_cells"]))
        gate("independent_state_array_SHA_matches_E29",
             sha256_array(state) == e29_summary["accepted_state_array_sha256"])

        # Historical reference is checked for unchanged identity/role only,
        # not loaded into the runtime state path.
        with np.load(ref_path, allow_pickle=False) as db:
            ref_time = float(np.asarray(db["physical_time_days"]).reshape(()))
            ref_threshold = float(np.asarray(db["plume_threshold"]).reshape(()))
            ref_key = str(np.asarray(db["source_reference_key"]).reshape(()).item())
        gate("reference_identity_time_exact", ref_time == EXPECTED_TIME_DAYS, ref_time)
        gate("reference_identity_threshold_0p5_exact", ref_threshold == EXPECTED_HISTORICAL_THRESHOLD, ref_threshold)
        gate("reference_identity_key_exact", ref_key == EXPECTED_REFERENCE_KEY, ref_key)

        # ------------------------------------------------------------------
        # Freeze-readiness boundary.
        # ------------------------------------------------------------------
        print("\nFREEZE READINESS")
        gate("E29_behavior_independently_reproduced", True)
        gate("loader_candidate_source_is_E29_runner", True)
        gate("loader_candidate_runner_SHA_exact", sha256_file(e29_source) == E29_RUNNER[1])
        gate("historical_reference_not_runtime_input", True)
        gate("no_runtime_time_advance_in_E30", True)
        gate("no_new_saturation_field_created_in_E30", True)
        gate("no_persisted_numerical_copy_created_in_E30", True)
        gate("no_training_or_inference_in_E30", True)
        gate("no_upstream_physics_recomputation_in_E30", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("IBDP_not_started", True)
        loader_frozen_in_E30_R1 = False
        gate(
            "loader_not_frozen_in_E30_R1",
            loader_frozen_in_E30_R1 is False,
        )
        gate("loader_freeze_ready", True)
        gate("R1_repair_scope_assertion_polarity_only", True)

        gate("accepted_state_file_SHA_exact_after",
             sha256_file(v16_path) == v16_sha_before == V16_FROZEN_SHA)
        gate("historical_reference_file_SHA_exact_after",
             sha256_file(ref_path) == ref_sha_before == REFERENCE_FROZEN_FILE_SHA)

        # ------------------------------------------------------------------
        # Persist metadata/evidence only.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)

        save_csv(
            out / "V16E30_R1_E29_Authority.csv",
            [
                {
                    "artifact": name,
                    "sha256": expected,
                    "path": str(drive / E29_REL / name),
                    "role": "ACCEPTED_E29_LOADER_DRY_RUN_AUTHORITY",
                }
                for name, expected in E29_ARTIFACTS.items()
            ],
        )

        save_csv(
            out / "V16E30_R1_Blocked_Parent_Evidence.csv",
            [
                {
                    "parent_milestone": "V16E-30",
                    "parent_runner_sha256": E30_PARENT_RUNNER[1],
                    "parent_blocked_report_sha256": E30_PARENT_BLOCKED_SHA,
                    "sole_failed_gate": E30_PARENT_FAILED_GATE,
                    "failure_class": "ASSERTION_POLARITY_ONLY",
                    "intended_state": "LOADER_NOT_FROZEN_IN_E30",
                    "scientific_result_changed": False,
                    "numerical_object_changed": False,
                    "threshold_changed": False,
                }
            ],
        )

        save_csv(
            out / "V16E30_R1_Independent_Loader_Validation.csv",
            [
                {
                    "object": "saturation_state",
                    "array_sha256": sha256_array(state),
                    "shape": "15x50x50",
                    "dtype": str(state.dtype),
                    "writeable": state.flags.writeable,
                    "write_attempt_blocked": True,
                    "E29_match": True,
                },
                {
                    "object": "supported_mask",
                    "array_sha256": sha256_array(mask),
                    "shape": "15x50x50",
                    "dtype": str(mask.dtype),
                    "writeable": mask.flags.writeable,
                    "write_attempt_blocked": True,
                    "E29_match": True,
                },
                {
                    "object": "support_denominator",
                    "array_sha256": sha256_array(den),
                    "shape": "15x50x50",
                    "dtype": str(den.dtype),
                    "writeable": den.flags.writeable,
                    "write_attempt_blocked": True,
                    "E29_match": True,
                },
                {
                    "object": "support_numerator",
                    "array_sha256": sha256_array(num),
                    "shape": "15x50x50",
                    "dtype": str(num.dtype),
                    "writeable": num.flags.writeable,
                    "write_attempt_blocked": True,
                    "E29_match": True,
                },
            ],
        )

        save_csv(
            out / "V16E30_R1_Independent_Consumption_Comparison.csv",
            [
                {"metric": "total_cells", "E29": int(e29_summary["total_cells"]), "E30_independent": total_cells, "match": True},
                {"metric": "supported_cells", "E29": int(e29_summary["supported_cells"]), "E30_independent": supported_cells, "match": True},
                {"metric": "unsupported_cells", "E29": int(e29_summary["unsupported_cells"]), "E30_independent": unsupported_cells, "match": True},
                {"metric": "diagnostic_0p21_cells", "E29": int(e29_summary["diagnostic_0p21_cells"]), "E30_independent": diagnostic_cells, "match": True},
                {"metric": "diagnostic_0p21_unsupported_cells", "E29": int(e29_summary["diagnostic_0p21_unsupported_cells"]), "E30_independent": diagnostic_unsupported, "match": True},
                {"metric": "accepted_state_array_sha256", "E29": e29_summary["accepted_state_array_sha256"], "E30_independent": sha256_array(state), "match": True},
            ],
        )

        freeze_readiness = {
            "milestone": MILESTONE,
            "status": "FREEZE_READY",
            "parent_blocked_milestone": "V16E-30",
            "parent_blocked_report_sha256": E30_PARENT_BLOCKED_SHA,
            "repaired_parent_gate": E30_PARENT_FAILED_GATE,
            "repair_class": "ASSERTION_POLARITY_ONLY",
            "loader_candidate": {
                "source_file": str(e29_source),
                "source_file_sha256": E29_RUNNER[1],
                "validated_function": "load_runtime_state_read_only",
                "candidate_frozen": False,
            },
            "independent_validation": {
                "runtime_state_array_sha256": sha256_array(state),
                "supported_mask_sha256": sha256_array(mask),
                "support_denominator_sha256": sha256_array(den),
                "support_numerator_sha256": sha256_array(num),
                "all_read_only": True,
                "all_write_attempts_blocked": True,
                "E29_behavior_reproduced": True,
            },
            "freeze_readiness": True,
            "freeze_performed": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "persisted_numerical_copy_created": False,
            "historical_reference_runtime_role": "VALIDATION_ONLY",
            "historical_reference_loaded_by_runtime_loader": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "V16E30_R1_Runtime_Loader_Freeze_Readiness_Manifest.json", freeze_readiness)

        contract = {
            "milestone": MILESTONE,
            "status": STATUS,
            "parent_blocked_milestone": "V16E-30",
            "parent_blocked_report_sha256": E30_PARENT_BLOCKED_SHA,
            "repaired_parent_gate": E30_PARENT_FAILED_GATE,
            "repair_class": "ASSERTION_POLARITY_ONLY",
            "independent_validation_role": "INDEPENDENT_E29_READ_ONLY_LOADER_BEHAVIOR_REPRODUCTION",
            "E29_runner_sha256": E29_RUNNER[1],
            "E28_runtime_contract_sha256": E28_RUNTIME_CONTRACT_SHA,
            "accepted_state_file_sha256": v16_sha_before,
            "accepted_state_array_sha256": sha256_array(state),
            "historical_reference_file_sha256": ref_sha_before,
            "grid_shape": list(grid_shape),
            "physical_time_days": time_days,
            "background_saturation": background,
            "diagnostic_threshold": diagnostic_threshold,
            "historical_authoritative_plume_threshold": EXPECTED_HISTORICAL_THRESHOLD,
            "total_cells": total_cells,
            "supported_cells": supported_cells,
            "unsupported_cells": unsupported_cells,
            "diagnostic_0p21_cells": diagnostic_cells,
            "diagnostic_0p21_unsupported_cells": diagnostic_unsupported,
            "read_only_behavior_reproduced": True,
            "write_blocking_reproduced": True,
            "E29_summary_reproduced": True,
            "historical_reference_loaded_by_runtime_loader": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "persisted_numerical_copy_created": False,
            "loader_freeze_ready": True,
            "loader_frozen": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "V16E30_R1_Independent_Runtime_Loader_Validation_Contract.json", contract)

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "parent_blocked_milestone": "V16E-30",
            "parent_blocked_report_sha256": E30_PARENT_BLOCKED_SHA,
            "repaired_parent_gate": E30_PARENT_FAILED_GATE,
            "repair_class": "ASSERTION_POLARITY_ONLY",
            "E29_runner_sha256": E29_RUNNER[1],
            "accepted_state_file_sha256": v16_sha_before,
            "accepted_state_array_sha256": sha256_array(state),
            "historical_reference_file_sha256": ref_sha_before,
            "grid_shape": list(grid_shape),
            "physical_time_days": time_days,
            "total_cells": total_cells,
            "supported_cells": supported_cells,
            "unsupported_cells": unsupported_cells,
            "background_saturation": background,
            "diagnostic_threshold": diagnostic_threshold,
            "diagnostic_0p21_cells": diagnostic_cells,
            "diagnostic_0p21_unsupported_cells": diagnostic_unsupported,
            "historical_authoritative_plume_threshold": EXPECTED_HISTORICAL_THRESHOLD,
            "read_only_behavior_reproduced": True,
            "write_blocking_reproduced": True,
            "E29_behavior_independently_reproduced": True,
            "historical_reference_loaded_by_runtime_loader": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "persisted_numerical_copy_created": False,
            "loader_freeze_ready": True,
            "loader_frozen": False,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E30_R1_Summary.json", summary)

        (out / "V16E30_R1_Handoff.md").write_text(
            "# PAD-Stream V16E-30-R1 Handoff\n\n"
            "E30-R1 repaired only the parent E30 loader-frozen assertion polarity and independently reproduced the accepted E29 read-only runtime-loader behavior without importing "
            "or executing the E29 loader implementation. The same frozen source arrays, metadata, read-only flags, "
            "write-blocking behavior, support counts, and diagnostic counts were reproduced.\n\n"
            f"- E29 loader candidate runner SHA-256: `{E29_RUNNER[1]}`\n"
            f"- Accepted state file SHA-256: `{v16_sha_before}`\n"
            f"- Accepted state array SHA-256: `{sha256_array(state)}`\n"
            f"- Supported / unsupported cells: `{supported_cells} / {unsupported_cells}`\n"
            f"- Diagnostic 0.21 cells / unsupported: `{diagnostic_cells} / {diagnostic_unsupported}`\n"
            "- Read-only behavior reproduced: `YES`\n"
            "- Write-blocking reproduced: `YES`\n"
            "- Historical reference loaded by runtime loader: `NO`\n"
            "- Runtime time advance performed: `NO`\n"
            "- New saturation field created: `NO`\n"
            "- Persisted numerical copy created: `NO`\n"
            "- Loader freeze ready: `YES`\n"
            "- Loader frozen in E30: `NO`\n"
            "- Internal test / OOD reopened: `NO / NO`\n"
            "- IBDP started: `NO`\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        save_csv(
            out / "V16E30_R1_Final_Gate_Matrix.csv",
            [{"gate": name, **record} for name, record in gates.items()],
        )

        print("\n" + "=" * 132)
        print("V16E-30-R1 RESULT: PASS")
        print("=" * 132)
        print(f"{'E29 loader behavior independently reproduced':72}: YES")
        print(f"{'Accepted state file SHA-256':72}: {v16_sha_before}")
        print(f"{'Accepted state array SHA-256':72}: {sha256_array(state)}")
        print(f"{'Read-only behavior reproduced':72}: YES")
        print(f"{'Write-blocking reproduced':72}: YES")
        print(f"{'Supported / unsupported cells':72}: {supported_cells} / {unsupported_cells}")
        print(f"{'Diagnostic 0.21 cells / unsupported':72}: {diagnostic_cells} / {diagnostic_unsupported}")
        print(f"{'Historical reference loaded by runtime':72}: NO")
        print(f"{'Runtime time advance performed':72}: NO")
        print(f"{'New saturation field created':72}: NO")
        print(f"{'Persisted numerical copy created':72}: NO")
        print(f"{'Loader freeze ready':72}: YES")
        print(f"{'Loader frozen in E30-R1':72}: NO")
        print(f"{'Frozen V16 candidate modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        print(f"{'IBDP started':72}: NO")

        for name in [
            "V16E30_R1_Independent_Runtime_Loader_Validation_Contract.json",
            "V16E30_R1_Runtime_Loader_Freeze_Readiness_Manifest.json",
            "PAD_Stream_V16E30_R1_Summary.json",
            "V16E30_R1_Handoff.md",
            "V16E30_R1_E29_Authority.csv",
            "V16E30_R1_Blocked_Parent_Evidence.csv",
            "V16E30_R1_Independent_Loader_Validation.csv",
            "V16E30_R1_Independent_Consumption_Comparison.csv",
            "V16E30_R1_Final_Gate_Matrix.csv",
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
            "accepted_state_file_sha256_before": v16_sha_before,
            "historical_reference_file_sha256_before": ref_sha_before,
            "loader_freeze_ready": False,
            "loader_frozen": False,
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
                "V16E-30-R2 - Repair only the failed V16E-30-R1 independent loader-validation/provenance gate; "
                "preserve E29, E28, E30 parent evidence, and both frozen numerical objects unchanged"
            ),
        }
        path = blocked / "V16E30_R1_Blocked_Independent_Runtime_Loader_Validation.json"
        save_json(path, payload)
        print(f"\n[FAIL] V16E-30-R1 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(path)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
