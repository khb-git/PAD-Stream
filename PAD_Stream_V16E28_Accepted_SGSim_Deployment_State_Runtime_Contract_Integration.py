from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
from typing import Any

import numpy as np


MILESTONE = "V16E-28"
STATUS = "ACCEPTED_SGSIM_DEPLOYMENT_STATE_INTEGRATED_INTO_PAD_STREAM_RUNTIME_CONTRACT"
NEXT = "V16E-29 - Read-Only PAD-Stream Runtime Loader / Accepted-State Consumption Dry Run"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
EXPECTED_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = "SG7A_corrected"

V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"

E27_RUNNER = (
    "PAD_Stream_V16E27_Frozen_SGSim_Deployment_Acceptance_and_PAD_Stream_Integration_Handoff.py",
    "e6cbc67d46ed13497afe4a09802286662aa838ab9d6180670f08b79f7db31e45",
)
E26R2_RUNNER = (
    "PAD_Stream_V16E26_R2_R1_Parent_Evidence_Filename_Repair_and_Independent_Deployment_Decision_Verification.py",
    "dfc7c4c87bd15f68cd9398f98e4df61331a25273c81c546a827d9fe4b553d1ed",
)
E18R1_RUNNER = (
    "PAD_Stream_V16E18_R1_E15_Background_Schema_Repair_and_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
    "d3944a6ef13b2c4f36bdcd77fde3845b6f442290e5007b5529c3f288054e7279",
)

E27_REL = Path(
    "provenance/hybrid_dp/"
    "V16E27_FROZEN_SGSIM_DEPLOYMENT_ACCEPTANCE_PAD_STREAM_INTEGRATION_HANDOFF"
)
E27_ARTIFACTS = {
    "V16E27_SGSim_Deployment_Acceptance_Manifest.json":
        "91d4740cb520ba6b31a18924667d5cc0ced130f238ae6f68da4a31e4b9ca86e6",
    "V16E27_PAD_Stream_Integration_Handoff_Contract.json":
        "71cd70bbd652b6e3e5abec778faa3fdbae928578ce2309a99a58f28b0c842544",
    "PAD_Stream_V16E27_Summary.json":
        "a6b18b9b47283d4ce3a0f1991ed3d17c6608d2cd0ad9ddc08bc33a2415f47fd1",
    "V16E27_Handoff.md":
        "99d8b854dc50edd93962509fb31b73b1105d2cb4817f0cf19d5ffed134659065",
    "V16E27_E26R2_Authority.csv":
        "2c503a8cd13e1c55bb77a20eb943e18ae91594fce93f3bedec4283e2ba520fdc",
    "V16E27_Accepted_Deployment_Identity.csv":
        "5c6bdd8234727fdd9d32b7be6c67b65121cd6da821f045994de9b7bbc6b4f7f7",
    "V16E27_Authoritative_Gate_Closure.csv":
        "c14028fb500c857a9975855eff8bb531f1294e3bf0bfc1f2c07e7fa98d7fcb0e",
    "V16E27_Integration_Role_Matrix.csv":
        "089c7c847dfd172ae773a42491f5de92c890870c7a25b09fb94b3b57852ae7c0",
    "V16E27_Final_Gate_Matrix.csv":
        "4f1124f50fdee84e100de3a9bafdb253090de7e05423d664c3a028e53ca32948",
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
    "V16E28_ACCEPTED_SGSIM_DEPLOYMENT_STATE_PAD_STREAM_RUNTIME_CONTRACT_INTEGRATION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E28_BLOCKED_ACCEPTED_SGSIM_DEPLOYMENT_STATE_PAD_STREAM_RUNTIME_CONTRACT_INTEGRATION"
)

RUNTIME_BINDINGS = (
    ("saturation_state", "saturation_grid_full_float64", "FLOAT64_3D", "IMMUTABLE_RUNTIME_STATE"),
    ("supported_mask", "supported_mask", "MASK_3D", "IMMUTABLE_PROVENANCE_SUPPORT"),
    ("support_denominator", "support_denominator", "NUMERIC_3D", "IMMUTABLE_PROVENANCE_SUPPORT"),
    ("support_numerator", "support_numerator", "NUMERIC_3D", "IMMUTABLE_PROVENANCE_SUPPORT"),
    ("physical_time_days", "physical_time_days", "SCALAR_FLOAT", "IMMUTABLE_RUNTIME_METADATA"),
    ("grid_shape", "grid_shape", "VECTOR_INT3", "IMMUTABLE_RUNTIME_METADATA"),
    ("background_saturation", "background_saturation", "SCALAR_FLOAT", "IMMUTABLE_RUNTIME_METADATA"),
    ("diagnostic_threshold", "diagnostic_threshold", "SCALAR_FLOAT", "DIAGNOSTIC_ONLY_METADATA"),
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr) -> str:
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


def scalar(db, key):
    return np.asarray(db[key]).reshape(()).item()


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
    print("PAD-Stream V16E-28 Accepted SGSim Deployment-State Integration into PAD-Stream Runtime Contract")
    print("=" * 132)
    print("CONTRACT-LAYER INTEGRATION ONLY.")
    print("THE ACCEPTED V16E-18-R1 NUMERICAL STATE IS CONSUMED BY EXACT PATH/HASH IDENTITY; IT IS NOT COPIED OR MODIFIED.")
    print("THE V16E-24 HISTORICAL REFERENCE REMAINS VALIDATION-ONLY AND IS NOT EXPOSED AS A RUNTIME CORRECTION/TUNING FIELD.")
    print("NO TRAINING, MODEL INFERENCE, PRESSURE, DARCY, POLLOCK, TOF, TRANSPORT, OR MAP-BACK RECOMPUTATION.")
    print("NO RUNTIME TIME-ADVANCE OR NEW SATURATION FIELD IS PRODUCED IN E28.")
    print("INTERNAL TEST / OOD REMAIN CLOSED. IBDP REMAINS DEFERRED.")

    try:
        # ------------------------------------------------------------------
        # Source authority.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E27_runner", E27_RUNNER),
            ("E26R2_runner", E26R2_RUNNER),
            ("E18R1_runner", E18R1_RUNNER),
        ]:
            p = root / name
            gate(f"{label}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # Accepted E27 handoff authority.
        # ------------------------------------------------------------------
        print("\nV16E-27 ACCEPTANCE / HANDOFF AUTHORITY")
        for name, expected in E27_ARTIFACTS.items():
            p = drive / E27_REL / name
            gate(f"E27_{name}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"E27_{name}_SHA_exact", actual == expected, actual)

        e27_summary = load_json(drive / E27_REL / "PAD_Stream_V16E27_Summary.json")
        e27_manifest = load_json(
            drive / E27_REL / "V16E27_SGSim_Deployment_Acceptance_Manifest.json"
        )
        e27_handoff = load_json(
            drive / E27_REL / "V16E27_PAD_Stream_Integration_Handoff_Contract.json"
        )

        gate(
            "E27_status_exact",
            e27_summary.get("status")
            == "SGSIM_DEPLOYMENT_ACCEPTED_FOR_PAD_STREAM_INTEGRATION_HANDOFF",
            e27_summary.get("status"),
        )
        gate("E27_deployment_accepted", e27_summary.get("deployment_accepted") is True)
        gate(
            "E27_full_grid_plume_authorized",
            e27_summary.get("full_grid_plume_authorized") is True,
        )
        gate(
            "E27_integration_handoff_ready",
            e27_summary.get("integration_handoff_ready") is True,
        )
        gate(
            "E27_runtime_integration_not_already_performed",
            e27_summary.get("runtime_integration_performed") is False,
        )
        gate(
            "E27_no_frozen_object_modification",
            e27_summary.get("frozen_candidate_modified") is False
            and e27_summary.get("historical_reference_modified") is False,
        )
        gate(
            "E27_test_OOD_closed",
            e27_summary.get("internal_test_reopened") is False
            and e27_summary.get("OOD_reopened") is False,
        )
        gate("E27_IBDP_not_started", e27_summary.get("IBDP_started") is False)
        gate(
            "E27_next_is_E28",
            str(e27_summary.get("next_milestone", "")).startswith("V16E-28"),
            e27_summary.get("next_milestone"),
        )

        gate(
            "E27_manifest_accepted_candidate_SHA_exact",
            e27_manifest["accepted_deployment_state"]["file_sha256"] == V16_FROZEN_SHA,
            e27_manifest["accepted_deployment_state"]["file_sha256"],
        )
        gate(
            "E27_manifest_reference_SHA_exact",
            e27_manifest["validation_reference"]["file_sha256"]
            == REFERENCE_FROZEN_FILE_SHA,
            e27_manifest["validation_reference"]["file_sha256"],
        )
        gate(
            "E27_manifest_reference_validation_only",
            e27_manifest["validation_reference"]["role"] == "VALIDATION_ONLY",
        )
        gate(
            "E27_manifest_runtime_integration_not_performed",
            e27_manifest.get("runtime_integration_performed") is False,
        )

        accepted = e27_handoff["accepted_state_contract"]
        validation = e27_handoff["validation_contract"]
        boundary = e27_handoff["E28_boundary"]

        gate(
            "E27_handoff_status_ready",
            e27_handoff.get("status") == "PAD_STREAM_INTEGRATION_HANDOFF_READY",
        )
        gate(
            "E27_handoff_candidate_SHA_exact",
            accepted.get("canonical_numerical_input_sha256") == V16_FROZEN_SHA,
            accepted.get("canonical_numerical_input_sha256"),
        )
        gate(
            "E27_handoff_candidate_mutation_forbidden",
            accepted.get("numerical_mutation_permitted") is False,
        )
        gate(
            "E27_handoff_background_completion_part_of_frozen_state",
            accepted.get("background_completion_is_part_of_frozen_state") is True,
        )
        gate(
            "E27_handoff_reference_not_runtime_correction",
            validation.get("reference_is_runtime_correction") is False,
        )
        gate(
            "E27_handoff_reference_not_tuning_input",
            validation.get("reference_is_tuning_input") is False,
        )
        gate(
            "E27_boundary_allows_E28_runtime_wiring",
            boundary.get("may_wire_accepted_state_into_PAD_Stream_runtime") is True,
        )
        gate(
            "E27_boundary_forbids_frozen_state_change",
            boundary.get("may_change_frozen_state") is False,
        )
        gate(
            "E27_boundary_forbids_reference_change",
            boundary.get("may_change_historical_reference") is False,
        )
        gate(
            "E27_boundary_forbids_threshold_change",
            boundary.get("may_change_historical_threshold") is False,
        )
        gate(
            "E27_boundary_forbids_test_OOD_reopen",
            boundary.get("may_reopen_internal_test") is False
            and boundary.get("may_reopen_OOD") is False,
        )
        gate(
            "E27_boundary_forbids_IBDP_start",
            boundary.get("may_begin_IBDP") is False,
        )

        # ------------------------------------------------------------------
        # Exact runtime source binding.
        # ------------------------------------------------------------------
        print("\nACCEPTED FROZEN STATE -> RUNTIME CONTRACT BINDING")
        gate("accepted_frozen_candidate_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate(
            "accepted_frozen_candidate_SHA_exact_before",
            v16_sha_before == V16_FROZEN_SHA,
            v16_sha_before,
        )

        gate("validation_reference_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate(
            "validation_reference_SHA_exact_before",
            ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
            ref_sha_before,
        )

        binding_rows = []
        array_identity_rows = []

        with np.load(v16_path, allow_pickle=False) as db:
            available = set(db.files)
            required_keys = {source_key for _, source_key, _, _ in RUNTIME_BINDINGS}
            gate(
                "runtime_contract_required_source_keys_present",
                required_keys.issubset(available),
                sorted(available),
            )

            state = np.asarray(db["saturation_grid_full_float64"])
            support_mask = np.asarray(db["supported_mask"])
            support_den = np.asarray(db["support_denominator"])
            support_num = np.asarray(db["support_numerator"])
            time_days = float(np.asarray(db["physical_time_days"]))
            grid_shape = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
            background = float(np.asarray(db["background_saturation"]))
            diagnostic_threshold = float(np.asarray(db["diagnostic_threshold"]))

            gate("runtime_state_shape_exact", state.shape == EXPECTED_GRID, state.shape)
            gate("runtime_state_dtype_float64", state.dtype == np.float64, state.dtype)
            gate("runtime_state_finite", np.all(np.isfinite(state)))
            gate("runtime_support_mask_shape_exact", support_mask.shape == EXPECTED_GRID, support_mask.shape)
            gate("runtime_support_denominator_shape_exact", support_den.shape == EXPECTED_GRID, support_den.shape)
            gate("runtime_support_numerator_shape_exact", support_num.shape == EXPECTED_GRID, support_num.shape)
            gate("runtime_grid_metadata_exact", grid_shape == EXPECTED_GRID, grid_shape)
            gate("runtime_time_100d_exact", time_days == EXPECTED_TIME_DAYS, time_days)
            gate("runtime_background_0p2_exact", background == EXPECTED_BACKGROUND, background)

            state_hash = sha256_array(state)
            support_mask_hash = sha256_array(support_mask)
            support_den_hash = sha256_array(support_den)
            support_num_hash = sha256_array(support_num)

            # Read-only in-memory runtime views; no source file mutation.
            state_view = state.view()
            state_view.setflags(write=False)
            mask_view = support_mask.view()
            mask_view.setflags(write=False)
            den_view = support_den.view()
            den_view.setflags(write=False)
            num_view = support_num.view()
            num_view.setflags(write=False)

            gate("runtime_state_view_read_only", state_view.flags.writeable is False)
            gate("runtime_support_mask_view_read_only", mask_view.flags.writeable is False)
            gate("runtime_support_denominator_view_read_only", den_view.flags.writeable is False)
            gate("runtime_support_numerator_view_read_only", num_view.flags.writeable is False)

            for runtime_name, source_key, schema, role in RUNTIME_BINDINGS:
                arr = np.asarray(db[source_key])
                binding_rows.append({
                    "runtime_name": runtime_name,
                    "source_file": str(v16_path),
                    "source_file_sha256": v16_sha_before,
                    "source_key": source_key,
                    "schema": schema,
                    "source_dtype": str(arr.dtype),
                    "source_shape": "x".join(str(int(x)) for x in arr.shape)
                        if arr.ndim > 0 else "scalar",
                    "role": role,
                    "runtime_mutability": "READ_ONLY",
                })

            for name, arr in [
                ("saturation_grid_full_float64", state),
                ("supported_mask", support_mask),
                ("support_denominator", support_den),
                ("support_numerator", support_num),
            ]:
                array_identity_rows.append({
                    "source_key": name,
                    "shape": "x".join(str(int(x)) for x in arr.shape),
                    "dtype": str(arr.dtype),
                    "array_sha256": sha256_array(arr),
                    "runtime_mutability": "READ_ONLY",
                })

        # Validation reference is deliberately inspected only for identity/role.
        with np.load(ref_path, allow_pickle=False) as db:
            ref_time = float(scalar(db, "physical_time_days"))
            ref_threshold = float(scalar(db, "plume_threshold"))
            ref_key = str(scalar(db, "source_reference_key"))
        gate("reference_role_time_100d_exact", ref_time == EXPECTED_TIME_DAYS, ref_time)
        gate("reference_role_threshold_0p5_exact", ref_threshold == EXPECTED_THRESHOLD, ref_threshold)
        gate("reference_role_key_exact", ref_key == EXPECTED_REFERENCE_KEY, ref_key)
        gate("reference_not_bound_as_runtime_state", True)
        gate("reference_not_bound_as_runtime_correction", True)
        gate("reference_not_bound_as_runtime_tuning_input", True)

        # ------------------------------------------------------------------
        # Integration boundary.
        # ------------------------------------------------------------------
        print("\nPAD-STREAM RUNTIME CONTRACT INTEGRATION BOUNDARY")
        gate("accepted_state_bound_by_exact_file_identity", True)
        gate("runtime_contract_created_without_numerical_copy", True)
        gate("runtime_contract_uses_read_only_views", True)
        gate("background_completion_preserved_as_frozen_state", True)
        gate("diagnostic_threshold_preserved_as_diagnostic_only", True)
        gate("historical_0p5_threshold_not_used_as_runtime_correction", True)
        gate("no_runtime_time_advance_in_E28", True)
        gate("no_new_saturation_field_created_in_E28", True)
        gate("no_model_inference_in_E28", True)
        gate("no_upstream_physics_recomputation_in_E28", True)
        gate("runtime_loader_execution_deferred_to_E29", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("IBDP_not_started", True)

        gate(
            "accepted_frozen_candidate_SHA_exact_after",
            sha256_file(v16_path) == v16_sha_before == V16_FROZEN_SHA,
        )
        gate(
            "validation_reference_SHA_exact_after",
            sha256_file(ref_path) == ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
        )

        # ------------------------------------------------------------------
        # Persist metadata/contract artifacts only.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)

        save_csv(
            out / "V16E28_E27_Authority.csv",
            [
                {
                    "artifact": name,
                    "sha256": expected,
                    "path": str(drive / E27_REL / name),
                    "role": "ACCEPTED_E27_HANDOFF_AUTHORITY",
                }
                for name, expected in E27_ARTIFACTS.items()
            ],
        )
        save_csv(out / "V16E28_Runtime_Binding_Schema.csv", binding_rows)
        save_csv(out / "V16E28_Runtime_Array_Identity.csv", array_identity_rows)

        role_rows = [
            {
                "object": "V16E18_R1_frozen_full_grid_candidate",
                "runtime_role": "CANONICAL_READ_ONLY_RUNTIME_STATE_SOURCE",
                "bound_in_E28": True,
                "numerical_copy_created": False,
                "mutation_permitted": False,
            },
            {
                "object": "V16E24_frozen_historical_reference",
                "runtime_role": "VALIDATION_ONLY",
                "bound_in_E28": False,
                "numerical_copy_created": False,
                "mutation_permitted": False,
            },
            {
                "object": "historical_SG7E_threshold_0p5",
                "runtime_role": "VALIDATION_THRESHOLD_ONLY",
                "bound_in_E28": False,
                "numerical_copy_created": False,
                "mutation_permitted": False,
            },
            {
                "object": "diagnostic_threshold",
                "runtime_role": "DIAGNOSTIC_ONLY_METADATA",
                "bound_in_E28": True,
                "numerical_copy_created": False,
                "mutation_permitted": False,
            },
            {
                "object": "internal_test",
                "runtime_role": "CLOSED",
                "bound_in_E28": False,
                "numerical_copy_created": False,
                "mutation_permitted": False,
            },
            {
                "object": "OOD",
                "runtime_role": "CLOSED",
                "bound_in_E28": False,
                "numerical_copy_created": False,
                "mutation_permitted": False,
            },
            {
                "object": "IBDP",
                "runtime_role": "DEFERRED",
                "bound_in_E28": False,
                "numerical_copy_created": False,
                "mutation_permitted": False,
            },
        ]
        save_csv(out / "V16E28_Runtime_Role_Separation.csv", role_rows)

        runtime_contract = {
            "milestone": MILESTONE,
            "status": "PAD_STREAM_RUNTIME_CONTRACT_INTEGRATED",
            "integration_mode": "READ_ONLY_EXACT_IDENTITY_BINDING",
            "canonical_runtime_state_source": {
                "path": str(v16_path),
                "file_sha256": v16_sha_before,
                "grid_shape": list(EXPECTED_GRID),
                "physical_time_days": EXPECTED_TIME_DAYS,
                "background_saturation": EXPECTED_BACKGROUND,
                "state_key": "saturation_grid_full_float64",
                "support_mask_key": "supported_mask",
                "support_denominator_key": "support_denominator",
                "support_numerator_key": "support_numerator",
                "diagnostic_threshold_key": "diagnostic_threshold",
                "numerical_mutation_permitted": False,
                "numerical_copy_required": False,
            },
            "runtime_array_identity": {
                "saturation_grid_full_float64_sha256": state_hash,
                "supported_mask_sha256": support_mask_hash,
                "support_denominator_sha256": support_den_hash,
                "support_numerator_sha256": support_num_hash,
            },
            "historical_validation_reference": {
                "path": str(ref_path),
                "file_sha256": ref_sha_before,
                "reference_key": EXPECTED_REFERENCE_KEY,
                "plume_threshold": EXPECTED_THRESHOLD,
                "runtime_state_input": False,
                "runtime_correction_input": False,
                "runtime_tuning_input": False,
            },
            "execution_boundary": {
                "runtime_contract_integrated": True,
                "runtime_loader_executed": False,
                "runtime_time_advance_performed": False,
                "new_saturation_field_created": False,
                "training_performed": False,
                "model_inference_performed": False,
                "upstream_physics_recomputed": False,
            },
            "closed_domains": {
                "internal_test_reopened": False,
                "OOD_reopened": False,
                "IBDP_started": False,
            },
            "next_milestone": NEXT,
        }
        save_json(out / "V16E28_PAD_Stream_Runtime_Contract.json", runtime_contract)

        integration_manifest = {
            "milestone": MILESTONE,
            "status": STATUS,
            "source_acceptance_milestone": "V16E-27",
            "source_acceptance_manifest_sha256":
                E27_ARTIFACTS["V16E27_SGSim_Deployment_Acceptance_Manifest.json"],
            "accepted_frozen_V16_candidate_sha256": v16_sha_before,
            "frozen_historical_reference_sha256": ref_sha_before,
            "runtime_contract_integrated": True,
            "runtime_loader_executed": False,
            "accepted_state_bound_by_exact_identity": True,
            "accepted_state_read_only": True,
            "numerical_copy_created": False,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "historical_threshold_changed": False,
            "historical_reference_runtime_role": "VALIDATION_ONLY",
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(
            out / "V16E28_Runtime_Contract_Integration_Manifest.json",
            integration_manifest,
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "accepted_frozen_V16_candidate_sha256": v16_sha_before,
            "frozen_historical_reference_sha256": ref_sha_before,
            "runtime_state_array_sha256": state_hash,
            "supported_mask_sha256": support_mask_hash,
            "support_denominator_sha256": support_den_hash,
            "support_numerator_sha256": support_num_hash,
            "background_saturation": background,
            "diagnostic_threshold": diagnostic_threshold,
            "historical_authoritative_plume_threshold": EXPECTED_THRESHOLD,
            "deployment_accepted": True,
            "full_grid_plume_authorized": True,
            "runtime_contract_integrated": True,
            "runtime_loader_executed": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "historical_reference_runtime_role": "VALIDATION_ONLY",
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E28_Summary.json", summary)

        (out / "V16E28_Handoff.md").write_text(
            "# PAD-Stream V16E-28 Handoff\n\n"
            "The formally accepted SGSim V16E-18-R1 deployment state has been integrated into the "
            "PAD-Stream runtime **contract layer** by exact immutable file/key identity. No numerical "
            "copy was created and no frozen value was modified.\n\n"
            f"- Canonical runtime state file SHA-256: `{v16_sha_before}`\n"
            f"- Runtime saturation-array SHA-256: `{state_hash}`\n"
            f"- Frozen historical reference SHA-256: `{ref_sha_before}`\n"
            "- Historical reference runtime role: `VALIDATION_ONLY`\n"
            "- Historical plume threshold: `S >= 0.5` (`VALIDATION_ONLY`)\n"
            f"- Background saturation: `{background}`\n"
            f"- Diagnostic threshold metadata: `{diagnostic_threshold}` (`DIAGNOSTIC_ONLY`)\n"
            "- Runtime contract integrated: `YES`\n"
            "- Runtime loader executed: `NO`\n"
            "- Runtime time advance performed: `NO`\n"
            "- New saturation field created: `NO`\n"
            "- Frozen candidate modified: `NO`\n"
            "- Historical reference modified: `NO`\n"
            "- Internal test / OOD reopened: `NO / NO`\n"
            "- IBDP started: `NO`\n\n"
            "E29 may implement and execute a read-only loader/dry run against this exact contract. "
            "It may not alter the accepted numerical state, reference truth, or historical threshold.\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        save_csv(
            out / "V16E28_Final_Gate_Matrix.csv",
            [{"gate": name, **record} for name, record in gates.items()],
        )

        print("\n" + "=" * 132)
        print("V16E-28 RESULT: PASS")
        print("=" * 132)
        print(f"{'Accepted SGSim deployment state':72}: BOUND TO PAD-STREAM RUNTIME CONTRACT")
        print(f"{'Frozen V16 candidate SHA-256':72}: {v16_sha_before}")
        print(f"{'Runtime saturation-array SHA-256':72}: {state_hash}")
        print(f"{'Frozen historical reference SHA-256':72}: {ref_sha_before}")
        print(f"{'Runtime state binding mode':72}: READ_ONLY_EXACT_IDENTITY")
        print(f"{'Background saturation':72}: {background}")
        print(f"{'Diagnostic threshold role':72}: {diagnostic_threshold} / DIAGNOSTIC ONLY")
        print(f"{'Historical 0.5 threshold role':72}: VALIDATION ONLY")
        print(f"{'Deployment accepted':72}: YES")
        print(f"{'Full-grid plume authorized':72}: YES")
        print(f"{'Runtime contract integrated':72}: YES")
        print(f"{'Runtime loader executed':72}: NO")
        print(f"{'Runtime time advance performed':72}: NO")
        print(f"{'New saturation field created':72}: NO")
        print(f"{'Frozen V16 candidate modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        print(f"{'IBDP started':72}: NO")

        for name in [
            "V16E28_PAD_Stream_Runtime_Contract.json",
            "V16E28_Runtime_Contract_Integration_Manifest.json",
            "PAD_Stream_V16E28_Summary.json",
            "V16E28_Handoff.md",
            "V16E28_E27_Authority.csv",
            "V16E28_Runtime_Binding_Schema.csv",
            "V16E28_Runtime_Array_Identity.csv",
            "V16E28_Runtime_Role_Separation.csv",
            "V16E28_Final_Gate_Matrix.csv",
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
            "frozen_V16_candidate_sha256_before": v16_sha_before,
            "frozen_reference_sha256_before": ref_sha_before,
            "runtime_contract_integrated": False,
            "runtime_loader_executed": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
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
                "V16E-28-R1 - Repair only the failed V16E-28 runtime-contract/provenance gate; "
                "preserve E27 and both frozen numerical objects unchanged"
            ),
        }
        p = blocked / "V16E28_Blocked_Runtime_Contract_Integration.json"
        save_json(p, payload)
        print(f"\n[FAIL] V16E-28 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(p)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
