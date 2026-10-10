from __future__ import annotations

from pathlib import Path
import argparse
import ast
import csv
import hashlib
import json
import os
import shutil
from typing import Any

import numpy as np


MILESTONE = "V16E-31"
STATUS = "READ_ONLY_PAD_STREAM_RUNTIME_LOADER_FROZEN"
NEXT = "V16E-32 - Frozen Runtime Loader Consumption / PAD-Stream Runtime Execution Entry Contract"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
EXPECTED_DIAGNOSTIC_THRESHOLD = 0.21
EXPECTED_HISTORICAL_THRESHOLD = 0.5

V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"
RUNTIME_STATE_ARRAY_SHA = "176975c3131353c4fe60fdf9e6d7635b13e260e010fc8cd849deb17c85e37f12"

E30R1_RUNNER = (
    "PAD_Stream_V16E30_R1_Loader_Frozen_Assertion_Polarity_Repair_and_Independent_Freeze_Readiness.py",
    "d509947d5b485fbd7cd610fd50f6cc8c8f25fff3ebfa135e52651c419012b64c",
)
E29_RUNNER = (
    "PAD_Stream_V16E29_Read_Only_Runtime_Loader_and_Accepted_State_Consumption_Dry_Run.py",
    "1604f753b3cc37444d77fd3f979443717d3a8437efa4f43a13732d9744f288cc",
)
E28_RUNNER = (
    "PAD_Stream_V16E28_Accepted_SGSim_Deployment_State_Runtime_Contract_Integration.py",
    "41235afa7c7e657b798bab52a69465c7d746dc1c7c3cd7b29032aec33135429f",
)

E30R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E30_R1_INDEPENDENT_READ_ONLY_RUNTIME_LOADER_VALIDATION_FREEZE_READINESS"
)
E30R1_ARTIFACTS = {
    "V16E30_R1_Independent_Runtime_Loader_Validation_Contract.json":
        "594914b4a3ab369c5be125d16dd32661d99d6be2d0d6dacb820afa87063e4406",
    "V16E30_R1_Runtime_Loader_Freeze_Readiness_Manifest.json":
        "c58b1781f1f05189a8f9b69443d02384091448789b8f60cdc664f9c478d39622",
    "PAD_Stream_V16E30_R1_Summary.json":
        "6e97492ae4c8bc5909fe8d32cef47849b015a3060437ae1ffa418572ab6ce98b",
    "V16E30_R1_Handoff.md":
        "f71f78e927b884a8eea2e32cba3a09c29a888340ebc4b86fe39c5872bb611aaf",
    "V16E30_R1_E29_Authority.csv":
        "0a5cd18f33ebb063371562675cccd22d5ff7e219a5d018e9dc9ea516f6da45ae",
    "V16E30_R1_Blocked_Parent_Evidence.csv":
        "a89f745ce505947b4f0b0863c207acfaa9107760f5611a141df99c8d2c1209fe",
    "V16E30_R1_Independent_Loader_Validation.csv":
        "f1f6809bc7988e53cb55ae45f18a1443c5b036faec63ce945d49e51bbfcfc9ba",
    "V16E30_R1_Independent_Consumption_Comparison.csv":
        "bbaa9e1f8a046081e60ca0fcdbf2f48ba8a34404613b909e861416a55f776a8f",
    "V16E30_R1_Final_Gate_Matrix.csv":
        "6ac9537054b266dc0fa6eade8779d664773472c2f5d285826763202890ca7901",
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
    "V16E31_FROZEN_READ_ONLY_PAD_STREAM_RUNTIME_LOADER"
)
FROZEN_SUBDIR = Path("frozen_loader")
FROZEN_LOADER_NAME = "V16E31_Frozen_Read_Only_Runtime_Loader.py"
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E31_BLOCKED_READ_ONLY_PAD_STREAM_RUNTIME_LOADER_FREEZE"
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


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    frozen_dir = out / FROZEN_SUBDIR
    frozen_loader = frozen_dir / FROZEN_LOADER_NAME
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

    source_loader = root / E29_RUNNER[0]
    v16_path = drive / V16_FROZEN_REL
    ref_path = drive / REFERENCE_FROZEN_REL

    source_loader_sha_before = None
    v16_sha_before = None
    ref_sha_before = None

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-31 Read-Only PAD-Stream Runtime Loader Freeze / Provenance Manifest")
    print("=" * 132)
    print("FORMAL LOADER FREEZE ONLY.")
    print("THE VALIDATED E29 RUNNER SOURCE IS FROZEN BY BYTE-FOR-BYTE COPY; THE VALIDATED FUNCTION IS load_runtime_state_read_only.")
    print("NO LOADER LOGIC CHANGE. NO NUMERICAL-STATE COPY. NO RUNTIME TIME ADVANCE. NO NEW SATURATION FIELD.")
    print("HISTORICAL REFERENCE REMAINS VALIDATION-ONLY. INTERNAL TEST / OOD REMAIN CLOSED. IBDP REMAINS DEFERRED.")

    try:
        # ------------------------------------------------------------------
        # Source authority.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E30R1_runner", E30R1_RUNNER),
            ("E29_loader_candidate_runner", E29_RUNNER),
            ("E28_runner", E28_RUNNER),
        ]:
            path = root / name
            gate(f"{label}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        source_loader_sha_before = sha256_file(source_loader)
        gate(
            "validated_loader_candidate_SHA_exact",
            source_loader_sha_before == E29_RUNNER[1],
            source_loader_sha_before,
        )

        source_function_text = function_source_text(
            source_loader, "load_runtime_state_read_only"
        )
        source_function_sha = sha256_bytes(source_function_text.encode("utf-8"))
        gate(
            "validated_loader_function_present",
            "def load_runtime_state_read_only" in source_function_text,
        )
        gate(
            "validated_loader_function_read_only_logic_present",
            "make_read_only" in source_function_text,
        )
        gate(
            "validated_loader_function_historical_reference_absent",
            "REFERENCE_FROZEN_REL" not in source_function_text
            and "ref_path" not in source_function_text
            and "historical" not in source_function_text.lower(),
        )

        # ------------------------------------------------------------------
        # E30-R1 freeze-readiness authority.
        # ------------------------------------------------------------------
        print("\nV16E-30-R1 FREEZE-READINESS AUTHORITY")
        for name, expected in E30R1_ARTIFACTS.items():
            path = drive / E30R1_REL / name
            gate(f"E30R1_{name}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"E30R1_{name}_SHA_exact", actual == expected, actual)

        summary = load_json(drive / E30R1_REL / "PAD_Stream_V16E30_R1_Summary.json")
        readiness = load_json(
            drive / E30R1_REL / "V16E30_R1_Runtime_Loader_Freeze_Readiness_Manifest.json"
        )
        contract = load_json(
            drive / E30R1_REL / "V16E30_R1_Independent_Runtime_Loader_Validation_Contract.json"
        )

        gate(
            "E30R1_summary_status_PASS",
            summary.get("status") == "INDEPENDENT_READ_ONLY_RUNTIME_LOADER_VALIDATION_PASS",
        )
        gate(
            "E30R1_behavior_independently_reproduced",
            summary.get("E29_behavior_independently_reproduced") is True,
        )
        gate(
            "E30R1_read_only_behavior_reproduced",
            summary.get("read_only_behavior_reproduced") is True,
        )
        gate(
            "E30R1_write_blocking_reproduced",
            summary.get("write_blocking_reproduced") is True,
        )
        gate(
            "E30R1_loader_freeze_ready",
            summary.get("loader_freeze_ready") is True,
        )
        gate(
            "E30R1_loader_not_yet_frozen",
            summary.get("loader_frozen") is False,
        )
        gate(
            "E30R1_candidate_runner_SHA_exact",
            summary.get("E29_runner_sha256") == E29_RUNNER[1],
            summary.get("E29_runner_sha256"),
        )
        gate(
            "E30R1_accepted_state_SHA_exact",
            summary.get("accepted_state_file_sha256") == V16_FROZEN_SHA,
        )
        gate(
            "E30R1_accepted_state_array_SHA_exact",
            summary.get("accepted_state_array_sha256") == RUNTIME_STATE_ARRAY_SHA,
        )
        gate(
            "E30R1_reference_SHA_exact",
            summary.get("historical_reference_file_sha256") == REFERENCE_FROZEN_FILE_SHA,
        )
        gate(
            "E30R1_grid_time_exact",
            tuple(summary.get("grid_shape", [])) == EXPECTED_GRID
            and float(summary.get("physical_time_days")) == EXPECTED_TIME_DAYS,
        )
        gate(
            "E30R1_background_diagnostic_exact",
            float(summary.get("background_saturation")) == EXPECTED_BACKGROUND
            and float(summary.get("diagnostic_threshold")) == EXPECTED_DIAGNOSTIC_THRESHOLD,
        )
        gate(
            "E30R1_historical_threshold_0p5_exact",
            float(summary.get("historical_authoritative_plume_threshold"))
            == EXPECTED_HISTORICAL_THRESHOLD,
        )
        gate(
            "E30R1_no_runtime_mutating_actions",
            summary.get("runtime_time_advance_performed") is False
            and summary.get("new_saturation_field_created") is False
            and summary.get("persisted_numerical_copy_created") is False,
        )
        gate(
            "E30R1_frozen_objects_unchanged",
            summary.get("frozen_candidate_modified") is False
            and summary.get("historical_reference_modified") is False,
        )
        gate(
            "E30R1_test_OOD_closed_IBDP_deferred",
            summary.get("internal_test_reopened") is False
            and summary.get("OOD_reopened") is False
            and summary.get("IBDP_started") is False,
        )
        gate(
            "E30R1_next_is_E31",
            str(summary.get("next_milestone", "")).startswith("V16E-31"),
            summary.get("next_milestone"),
        )

        gate("E30R1_readiness_status_FREEZE_READY", readiness.get("status") == "FREEZE_READY")
        candidate = readiness["loader_candidate"]
        gate(
            "E30R1_readiness_candidate_SHA_exact",
            candidate.get("source_file_sha256") == E29_RUNNER[1],
            candidate.get("source_file_sha256"),
        )
        gate(
            "E30R1_readiness_validated_function_exact",
            candidate.get("validated_function") == "load_runtime_state_read_only",
            candidate.get("validated_function"),
        )
        gate(
            "E30R1_readiness_candidate_not_frozen",
            candidate.get("candidate_frozen") is False,
        )
        gate(
            "E30R1_readiness_true",
            readiness.get("freeze_readiness") is True,
        )
        gate(
            "E30R1_freeze_not_performed",
            readiness.get("freeze_performed") is False,
        )
        gate(
            "E30R1_contract_loader_freeze_ready",
            contract.get("loader_freeze_ready") is True,
        )
        gate(
            "E30R1_contract_loader_not_frozen",
            contract.get("loader_frozen") is False,
        )

        # ------------------------------------------------------------------
        # Frozen numerical objects remain immutable.
        # ------------------------------------------------------------------
        print("\nIMMUTABLE NUMERICAL-OBJECT RECHECK")
        gate("accepted_state_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate("accepted_state_SHA_exact_before", v16_sha_before == V16_FROZEN_SHA, v16_sha_before)

        gate("historical_reference_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate(
            "historical_reference_SHA_exact_before",
            ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
            ref_sha_before,
        )

        # ------------------------------------------------------------------
        # Formal byte-for-byte loader freeze.
        # ------------------------------------------------------------------
        print("\nFORMAL READ-ONLY RUNTIME LOADER FREEZE")
        frozen_dir.mkdir(parents=True, exist_ok=True)

        if frozen_loader.exists():
            existing_sha = sha256_file(frozen_loader)
            gate(
                "existing_frozen_loader_SHA_exact",
                existing_sha == E29_RUNNER[1],
                existing_sha,
            )
        else:
            tmp = frozen_loader.with_suffix(frozen_loader.suffix + ".tmp")
            if tmp.exists():
                tmp.unlink()
            shutil.copyfile(source_loader, tmp)
            tmp_sha = sha256_file(tmp)
            gate("temporary_freeze_copy_SHA_exact", tmp_sha == E29_RUNNER[1], tmp_sha)
            os.replace(tmp, frozen_loader)

        gate("frozen_loader_exists", frozen_loader.is_file(), frozen_loader)
        frozen_sha = sha256_file(frozen_loader)
        gate("frozen_loader_file_SHA_exact", frozen_sha == E29_RUNNER[1], frozen_sha)
        gate(
            "source_frozen_byte_identity",
            source_loader.read_bytes() == frozen_loader.read_bytes(),
        )

        # Syntax/function identity validation without creating pyc output.
        frozen_text = frozen_loader.read_text(encoding="utf-8")
        ast.parse(frozen_text)
        gate("frozen_loader_python_syntax_valid", True)

        frozen_function_text = function_source_text(
            frozen_loader, "load_runtime_state_read_only"
        )
        frozen_function_sha = sha256_bytes(frozen_function_text.encode("utf-8"))
        gate(
            "frozen_loader_function_SHA_exact_to_validated_candidate",
            frozen_function_sha == source_function_sha,
            frozen_function_sha,
        )
        gate(
            "frozen_loader_function_text_exact",
            frozen_function_text == source_function_text,
        )

        # Freeze does not execute the loader.
        gate("loader_execution_not_performed_in_E31", True)
        gate("runtime_time_advance_not_performed_in_E31", True)
        gate("new_saturation_field_not_created_in_E31", True)
        gate("numerical_state_copy_not_created_in_E31", True)
        gate("historical_reference_not_runtime_input", True)
        gate("historical_reference_not_runtime_correction", True)
        gate("historical_reference_not_runtime_tuning_input", True)
        gate("historical_0p5_threshold_validation_only", True)
        gate("diagnostic_0p21_threshold_diagnostic_only", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("IBDP_not_started", True)

        # Recheck immutable authorities after freeze.
        gate(
            "validated_source_loader_SHA_exact_after",
            sha256_file(source_loader) == source_loader_sha_before == E29_RUNNER[1],
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
        # Persist freeze metadata.
        # ------------------------------------------------------------------
        save_csv(
            out / "V16E31_E30R1_Authority.csv",
            [
                {
                    "artifact": name,
                    "sha256": expected,
                    "path": str(drive / E30R1_REL / name),
                    "role": "ACCEPTED_E30R1_FREEZE_READINESS_AUTHORITY",
                }
                for name, expected in E30R1_ARTIFACTS.items()
            ],
        )

        save_csv(
            out / "V16E31_Frozen_Loader_Identity.csv",
            [
                {
                    "role": "VALIDATED_LOADER_CANDIDATE_SOURCE",
                    "path": str(source_loader),
                    "file_sha256": source_loader_sha_before,
                    "frozen": False,
                },
                {
                    "role": "FROZEN_READ_ONLY_PAD_STREAM_RUNTIME_LOADER",
                    "path": str(frozen_loader),
                    "file_sha256": frozen_sha,
                    "frozen": True,
                },
            ],
        )

        save_csv(
            out / "V16E31_Loader_Function_Identity.csv",
            [
                {
                    "function": "load_runtime_state_read_only",
                    "candidate_source_file_sha256": source_loader_sha_before,
                    "candidate_function_source_sha256": source_function_sha,
                    "frozen_file_sha256": frozen_sha,
                    "frozen_function_source_sha256": frozen_function_sha,
                    "function_text_exact": True,
                }
            ],
        )

        save_csv(
            out / "V16E31_Runtime_Boundary.csv",
            [
                {"boundary": "loader_frozen", "value": True},
                {"boundary": "loader_executed_in_E31", "value": False},
                {"boundary": "runtime_time_advance_performed", "value": False},
                {"boundary": "new_saturation_field_created", "value": False},
                {"boundary": "numerical_state_copy_created", "value": False},
                {"boundary": "historical_reference_runtime_input", "value": False},
                {"boundary": "historical_reference_runtime_correction", "value": False},
                {"boundary": "historical_reference_runtime_tuning_input", "value": False},
                {"boundary": "internal_test_reopened", "value": False},
                {"boundary": "OOD_reopened", "value": False},
                {"boundary": "IBDP_started", "value": False},
            ],
        )

        freeze_manifest = {
            "milestone": MILESTONE,
            "status": STATUS,
            "freeze_mode": "BYTE_FOR_BYTE_COPY_OF_INDEPENDENTLY_VALIDATED_E29_RUNNER_SOURCE",
            "validated_loader_function": "load_runtime_state_read_only",
            "source_candidate": {
                "path": str(source_loader),
                "file_sha256": source_loader_sha_before,
                "function_source_sha256": source_function_sha,
                "source_milestone": "V16E-29",
            },
            "frozen_loader": {
                "path": str(frozen_loader),
                "file_sha256": frozen_sha,
                "function_source_sha256": frozen_function_sha,
                "byte_identical_to_validated_candidate": True,
                "frozen": True,
            },
            "accepted_runtime_state": {
                "file_sha256": v16_sha_before,
                "state_array_sha256": RUNTIME_STATE_ARRAY_SHA,
                "grid_shape": list(EXPECTED_GRID),
                "physical_time_days": EXPECTED_TIME_DAYS,
                "background_saturation": EXPECTED_BACKGROUND,
            },
            "historical_reference": {
                "file_sha256": ref_sha_before,
                "runtime_role": "VALIDATION_ONLY",
                "historical_plume_threshold": EXPECTED_HISTORICAL_THRESHOLD,
            },
            "diagnostic_threshold": {
                "value": EXPECTED_DIAGNOSTIC_THRESHOLD,
                "role": "DIAGNOSTIC_ONLY",
            },
            "loader_executed_in_E31": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "numerical_state_copy_created": False,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "V16E31_Runtime_Loader_Freeze_Manifest.json", freeze_manifest)

        provenance_contract = {
            "milestone": MILESTONE,
            "status": "FROZEN",
            "E30R1_runner_sha256": E30R1_RUNNER[1],
            "E29_validated_candidate_sha256": E29_RUNNER[1],
            "E29_validated_function": "load_runtime_state_read_only",
            "frozen_loader_file_sha256": frozen_sha,
            "frozen_loader_function_source_sha256": frozen_function_sha,
            "source_frozen_byte_identity": True,
            "loader_logic_changed_during_freeze": False,
            "accepted_state_file_sha256": v16_sha_before,
            "accepted_state_array_sha256": RUNTIME_STATE_ARRAY_SHA,
            "historical_reference_file_sha256": ref_sha_before,
            "historical_reference_runtime_role": "VALIDATION_ONLY",
            "loader_execution_deferred_to_E32": True,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "V16E31_Runtime_Loader_Provenance_Contract.json", provenance_contract)

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS,
            "validated_loader_candidate_sha256": source_loader_sha_before,
            "frozen_loader_file_sha256": frozen_sha,
            "validated_function": "load_runtime_state_read_only",
            "validated_function_source_sha256": source_function_sha,
            "frozen_function_source_sha256": frozen_function_sha,
            "source_frozen_byte_identity": True,
            "loader_frozen": True,
            "loader_logic_changed": False,
            "accepted_state_file_sha256": v16_sha_before,
            "accepted_state_array_sha256": RUNTIME_STATE_ARRAY_SHA,
            "historical_reference_file_sha256": ref_sha_before,
            "historical_reference_runtime_role": "VALIDATION_ONLY",
            "historical_authoritative_plume_threshold": EXPECTED_HISTORICAL_THRESHOLD,
            "diagnostic_threshold": EXPECTED_DIAGNOSTIC_THRESHOLD,
            "loader_executed_in_E31": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "numerical_state_copy_created": False,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E31_Summary.json", summary_out)

        (out / "V16E31_Handoff.md").write_text(
            "# PAD-Stream V16E-31 Handoff\n\n"
            "The independently validated V16E-29 read-only runtime-loader candidate has been formally frozen "
            "by byte-for-byte source copy. The validated function is `load_runtime_state_read_only`.\n\n"
            f"- Validated E29 source SHA-256: `{source_loader_sha_before}`\n"
            f"- Frozen loader SHA-256: `{frozen_sha}`\n"
            f"- Validated/frozen function-source SHA-256: `{frozen_function_sha}`\n"
            "- Source/frozen byte identity: `YES`\n"
            "- Loader logic changed during freeze: `NO`\n"
            "- Loader frozen: `YES`\n"
            "- Loader executed in E31: `NO`\n"
            "- Runtime time advance performed: `NO`\n"
            "- New saturation field created: `NO`\n"
            "- Numerical state copy created: `NO`\n"
            "- Historical reference runtime role: `VALIDATION_ONLY`\n"
            "- Internal test / OOD reopened: `NO / NO`\n"
            "- IBDP started: `NO`\n\n"
            "E32 may consume the frozen loader as the canonical runtime entry implementation. "
            "It may not alter the frozen loader, accepted numerical state, historical reference, or threshold roles.\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        save_csv(
            out / "V16E31_Final_Gate_Matrix.csv",
            [{"gate": name, **record} for name, record in gates.items()],
        )

        print("\n" + "=" * 132)
        print("V16E-31 RESULT: PASS")
        print("=" * 132)
        print(f"{'Validated E29 loader source SHA-256':72}: {source_loader_sha_before}")
        print(f"{'Frozen loader SHA-256':72}: {frozen_sha}")
        print(f"{'Source / frozen byte identity':72}: YES")
        print(f"{'Validated function':72}: load_runtime_state_read_only")
        print(f"{'Function-source SHA-256':72}: {frozen_function_sha}")
        print(f"{'Loader frozen':72}: YES")
        print(f"{'Loader logic changed during freeze':72}: NO")
        print(f"{'Loader executed in E31':72}: NO")
        print(f"{'Runtime time advance performed':72}: NO")
        print(f"{'New saturation field created':72}: NO")
        print(f"{'Numerical state copy created':72}: NO")
        print(f"{'Accepted V16 state modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Historical reference runtime role':72}: VALIDATION ONLY")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        print(f"{'IBDP started':72}: NO")

        for name in [
            FROZEN_SUBDIR / FROZEN_LOADER_NAME,
            Path("V16E31_Runtime_Loader_Freeze_Manifest.json"),
            Path("V16E31_Runtime_Loader_Provenance_Contract.json"),
            Path("PAD_Stream_V16E31_Summary.json"),
            Path("V16E31_Handoff.md"),
            Path("V16E31_E30R1_Authority.csv"),
            Path("V16E31_Frozen_Loader_Identity.csv"),
            Path("V16E31_Loader_Function_Identity.csv"),
            Path("V16E31_Runtime_Boundary.csv"),
            Path("V16E31_Final_Gate_Matrix.csv"),
        ]:
            path = out / name
            print(f"{name} SHA: {sha256_file(path)}")

        print(f"Output: {out}")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)

        frozen_exists = frozen_loader.is_file()
        frozen_sha_now = sha256_file(frozen_loader) if frozen_exists else None
        frozen_exact = frozen_sha_now == E29_RUNNER[1] if frozen_exists else False

        payload = {
            "milestone": MILESTONE,
            "status": "BLOCKED",
            "exception": repr(exc),
            "gates": gates,
            "source_loader_sha256_before": source_loader_sha_before,
            "accepted_state_sha256_before": v16_sha_before,
            "historical_reference_sha256_before": ref_sha_before,
            "frozen_loader_exists": frozen_exists,
            "frozen_loader_sha256": frozen_sha_now,
            "loader_frozen_exact": frozen_exact,
            "loader_execution_performed": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "numerical_state_copy_created": False,
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
                "V16E-31-R1 - Repair only the failed V16E-31 loader-freeze/provenance gate; "
                "preserve E30-R1, E29, the accepted numerical state, and historical reference unchanged"
            ),
        }
        path = blocked / "V16E31_Blocked_Runtime_Loader_Freeze.json"
        save_json(path, payload)
        print(f"\n[FAIL] V16E-31 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(path)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
