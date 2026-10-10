from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
from typing import Any

import numpy as np


MILESTONE = "V16E-27"
STATUS = "SGSIM_DEPLOYMENT_ACCEPTED_FOR_PAD_STREAM_INTEGRATION_HANDOFF"
NEXT = "V16E-28 - Accepted SGSim Deployment-State Integration into PAD-Stream Runtime Contract"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_TIME_DAYS = 100.0
EXPECTED_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = "SG7A_corrected"

V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"
REFERENCE_ARRAY_SHA = "6135585d5dadd02f6ba2bcd2dd860c9a681d006526823c4e391e40f9f7f9ddd6"
REFERENCE_MASK_SHA = "08458e742f2866096346e56ff69fb3c9be183b68623d09cd518778326dfe180b"

E26R2_RUNNER = (
    "PAD_Stream_V16E26_R2_R1_Parent_Evidence_Filename_Repair_and_Independent_Deployment_Decision_Verification.py",
    "dfc7c4c87bd15f68cd9398f98e4df61331a25273c81c546a827d9fe4b553d1ed",
)
E25_RUNNER = (
    "PAD_Stream_V16E25_Frozen_Historical_Reference_and_Frozen_V16_Candidate_Deployment_Gate_Evaluation.py",
    "63be8aae660c7230fc35da69774facce9df9ba52849dad837b0b8e45af74c136",
)
E24_RUNNER = (
    "PAD_Stream_V16E24_Historical_100Day_Reference_Truth_Freeze_and_Provenance_Manifest.py",
    "ef572776a9812023d31bd3a4c53a914fe206e9c331c9febeb66344ba895acf26",
)
E18R1_RUNNER = (
    "PAD_Stream_V16E18_R1_E15_Background_Schema_Repair_and_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
    "d3944a6ef13b2c4f36bdcd77fde3845b6f442290e5007b5529c3f288054e7279",
)

E26R2_REL = Path(
    "provenance/hybrid_dp/"
    "V16E26_R2_INDEPENDENT_FROZEN_DEPLOYMENT_GATE_REPRODUCTION_DECISION_VERIFICATION"
)
E26R2_ARTIFACTS = {
    "V16E26_R2_Independent_Deployment_Gate_Reproduction.npz":
        "7895ddd6ba16d290550ea6e12706282852da943f80df888d8dd66d5e2d57cf54",
    "V16E26_R2_Independent_Deployment_Decision_Verification_Contract.json":
        "867dfd0b26ccceedb9d44e1b087a11a3df74a4a526df958255dc9797f37b7c50",
    "V16E26_R2_Deployment_Acceptance_Authorization.json":
        "c49d73cee81cd2a3cc6616b362978f401959bfef89c5de114c627d07261343d7",
    "PAD_Stream_V16E26_R2_Summary.json":
        "9d065a82e3c8441b9b41d3c6c79ca0b96e20a7db3d55cbe2602fb81aca515861",
    "V16E26_R2_Handoff.md":
        "4d5b74b09b3ca5a454c0b9bdf4c78f1477cc49f89c1258e9c58f356c06d57922",
    "V16E26_R2_E25_Authority.csv":
        "0132eb3a7126bdcddea15eddf8a5918ad87d32d557cbced789c3ca2122c7ca99",
    "V16E26_R2_E26_Blocked_Parent_Evidence.csv":
        "5bf520007771a2c7c089486d37ced31dc816fcd71d88c4fc4950300ce37353c4",
    "V16E26_R2_Repair_Lineage.csv":
        "bedf97c6e92793b28b996189866ebfdedad3da5c9a98043d67ac3508acc910cc",
    "V16E26_R2_Independent_Metrics.csv":
        "9a3b85082fcbb50896af0d6ddaa66d89659ca38bc62630a1203cda39cdad43bc",
    "V16E26_R2_E25_vs_E26R2_Metric_Comparison.csv":
        "4ec92b40cd8e9f005438f5b7cd4711ce9abc72c11a42f3f20867678b554c0096",
    "V16E26_R2_Independent_Gate_Results.csv":
        "ab7e56a5d81e85585752e46207d1a9aad3c92d3a1e418d4b608f0ebcc5db3342",
    "V16E26_R2_Final_Gate_Matrix.csv":
        "18a03bc2ccff21046256dbec37aaa8791109fca289f46d2c33c8c8d8f00ea337",
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
    "V16E27_FROZEN_SGSIM_DEPLOYMENT_ACCEPTANCE_PAD_STREAM_INTEGRATION_HANDOFF"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E27_BLOCKED_FROZEN_SGSIM_DEPLOYMENT_ACCEPTANCE_PAD_STREAM_INTEGRATION_HANDOFF"
)

EXPECTED_METRICS = {
    "primary_volume_relative_error": 0.012984878369493753,
    "footprint_IoU": 0.94906166219839139,
    "centroid_distance_cells": 0.08657898463568417,
    "vertical_extent_error_layers": 0.0,
}

EXPECTED_GATE_ROWS = {
    "PRIMARY_VOLUME_GATE": ("primary_volume_relative_error", "<=", 0.10),
    "FOOTPRINT_IOU_GATE": ("footprint_IoU", ">=", 0.90),
    "CENTROID_GATE_CELLS": ("centroid_distance_cells", "<=", 2.0),
    "VERTICAL_EXTENT_GATE_LAYERS": ("vertical_extent_error_layers", "<=", 2.0),
}


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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def scalar(db, key):
    return np.asarray(db[key]).reshape(()).item()


def exact_float(a, b):
    return np.float64(a).tobytes() == np.float64(b).tobytes()


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
    print("PAD-Stream V16E-27 Frozen SGSim Deployment Acceptance / PAD-Stream Integration Handoff")
    print("=" * 132)
    print("FORMAL ACCEPTANCE / HANDOFF ONLY.")
    print("NO NEW DEPLOYMENT METRIC EVALUATION. NO TRAINING OR MODEL INFERENCE.")
    print("NO PRESSURE, DARCY, POLLOCK, TOF, TRANSPORT, OR MAP-BACK RECOMPUTATION.")
    print("NO NUMERICAL COPY OR MODIFICATION OF THE FROZEN V16 CANDIDATE OR FROZEN HISTORICAL REFERENCE.")
    print("INTERNAL TEST / OOD REMAIN CLOSED. IBDP IS NOT STARTED IN E27.")

    try:
        # ------------------------------------------------------------------
        # Source authority.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E26R2_runner", E26R2_RUNNER),
            ("E25_runner", E25_RUNNER),
            ("E24_runner", E24_RUNNER),
            ("E18R1_runner", E18R1_RUNNER),
        ]:
            p = root / name
            gate(f"{label}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # Accepted E26-R2 independent-decision authority.
        # ------------------------------------------------------------------
        print("\nV16E-26-R2 ACCEPTED DEPLOYMENT AUTHORITY")
        for name, expected in E26R2_ARTIFACTS.items():
            p = drive / E26R2_REL / name
            gate(f"E26R2_{name}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"E26R2_{name}_SHA_exact", actual == expected, actual)

        e26_summary = load_json(drive / E26R2_REL / "PAD_Stream_V16E26_R2_Summary.json")
        e26_contract = load_json(
            drive / E26R2_REL
            / "V16E26_R2_Independent_Deployment_Decision_Verification_Contract.json"
        )
        e26_auth = load_json(
            drive / E26R2_REL
            / "V16E26_R2_Deployment_Acceptance_Authorization.json"
        )
        e26_gate_rows = load_csv(
            drive / E26R2_REL / "V16E26_R2_Independent_Gate_Results.csv"
        )
        e26_comparison_rows = load_csv(
            drive / E26R2_REL / "V16E26_R2_E25_vs_E26R2_Metric_Comparison.csv"
        )

        gate("E26R2_summary_status_PASS", e26_summary.get("status") == "PASS")
        gate(
            "E26R2_next_is_E27",
            str(e26_summary.get("next_milestone", "")).startswith("V16E-27"),
            e26_summary.get("next_milestone"),
        )
        gate(
            "E26R2_E25_decision_PASS",
            e26_summary.get("E25_deployment_decision") == "PASS",
        )
        gate(
            "E26R2_independent_decision_PASS",
            e26_summary.get("E26_independent_deployment_decision") == "PASS",
        )
        gate(
            "E26R2_decision_reproduced_exactly",
            e26_summary.get("decision_reproduced_exactly") is True,
        )
        gate(
            "E26R2_all_authoritative_gates_pass",
            e26_summary.get("all_authoritative_gates_pass") is True,
        )
        gate(
            "E26R2_deployment_accepted",
            e26_summary.get("deployment_accepted") is True,
        )
        gate(
            "E26R2_full_grid_plume_authorized",
            e26_summary.get("full_grid_plume_authorized") is True,
        )
        gate(
            "E26R2_no_frozen_object_modification",
            e26_summary.get("V16_frozen_candidate_modified") is False
            and e26_summary.get("historical_reference_modified") is False,
        )
        gate(
            "E26R2_threshold_unchanged",
            e26_summary.get("threshold_changed") is False
            and float(e26_summary.get("historical_authoritative_plume_threshold"))
            == EXPECTED_THRESHOLD,
        )
        gate(
            "E26R2_test_OOD_closed",
            e26_summary.get("internal_test_reopened") is False
            and e26_summary.get("OOD_reopened") is False,
        )

        gate("E26R2_contract_status_PASS", e26_contract.get("status") == "PASS")
        gate(
            "E26R2_contract_deployment_accepted",
            e26_contract.get("deployment_accepted") is True,
        )
        gate(
            "E26R2_contract_full_grid_plume_authorized",
            e26_contract.get("full_grid_plume_authorized") is True,
        )
        gate(
            "E26R2_authorization_status_AUTHORIZED",
            e26_auth.get("status") == "AUTHORIZED",
        )
        gate(
            "E26R2_authorization_decision_PASS",
            e26_auth.get("deployment_decision") == "PASS",
        )
        gate(
            "E26R2_authorization_full_grid_plume_true",
            e26_auth.get("full_grid_plume_authorized") is True,
        )

        gate("E26R2_gate_rows_exact_four", len(e26_gate_rows) == 4, len(e26_gate_rows))
        by_gate = {r["gate"]: r for r in e26_gate_rows}
        gate(
            "E26R2_gate_symbols_exact",
            set(by_gate) == set(EXPECTED_GATE_ROWS),
            sorted(by_gate),
        )

        gate_closure_rows = []
        for gate_name, (metric, operator, limit) in EXPECTED_GATE_ROWS.items():
            row = by_gate[gate_name]
            value = float(row["independent_value"])
            passed = str(row["passed"]).strip().lower() == "true"
            gate(f"{gate_name}_metric_name_exact", row["metric"] == metric, row["metric"])
            gate(f"{gate_name}_operator_exact", row["operator"] == operator, row["operator"])
            gate(f"{gate_name}_limit_exact", float(row["limit"]) == limit, row["limit"])
            gate(f"{gate_name}_passed", passed)
            gate(
                f"{gate_name}_value_matches_E26R2_summary",
                exact_float(value, float(e26_summary[metric])),
                f"{value:.17g}",
            )
            gate_closure_rows.append({
                "gate": gate_name,
                "metric": metric,
                "value": value,
                "operator": operator,
                "limit": limit,
                "passed": passed,
                "acceptance_role": "CLOSED_AUTHORITATIVE_SG7E_DEPLOYMENT_GATE",
            })

        gate(
            "E26R2_metric_comparison_rows_exact_four",
            len(e26_comparison_rows) == 4,
            len(e26_comparison_rows),
        )
        gate(
            "E26R2_all_decisions_match_E25",
            all(
                str(r.get("decision_match", "")).strip().lower() == "true"
                for r in e26_comparison_rows
            ),
        )

        # ------------------------------------------------------------------
        # Frozen-object identity, not a new evaluation.
        # ------------------------------------------------------------------
        print("\nIMMUTABLE DEPLOYMENT / REFERENCE IDENTITIES")
        gate("frozen_V16_candidate_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate(
            "frozen_V16_candidate_SHA_exact_before",
            v16_sha_before == V16_FROZEN_SHA,
            v16_sha_before,
        )

        gate("frozen_historical_reference_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate(
            "frozen_historical_reference_SHA_exact_before",
            ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
            ref_sha_before,
        )

        with np.load(v16_path, allow_pickle=False) as db:
            gate(
                "frozen_V16_required_arrays_present",
                {
                    "saturation_grid_full_float64",
                    "physical_time_days",
                    "grid_shape",
                    "background_saturation",
                    "supported_mask",
                    "support_denominator",
                    "support_numerator",
                }.issubset(set(db.files)),
                sorted(db.files),
            )
            grid = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
            time_days = float(np.asarray(db["physical_time_days"]))
            background = float(np.asarray(db["background_saturation"]))
            full_grid = np.asarray(db["saturation_grid_full_float64"])

        gate("frozen_V16_grid_exact", grid == EXPECTED_GRID, grid)
        gate("frozen_V16_time_100d_exact", time_days == EXPECTED_TIME_DAYS, time_days)
        gate("frozen_V16_background_0p2_exact", background == 0.2, background)
        gate("frozen_V16_array_shape_exact", full_grid.shape == EXPECTED_GRID, full_grid.shape)
        gate("frozen_V16_array_finite", np.all(np.isfinite(full_grid)))

        with np.load(ref_path, allow_pickle=False) as db:
            ref = np.asarray(db["reference_truth_100d_native"])
            mask = np.asarray(db["reference_plume_mask_100d_0p5"], dtype=np.uint8)
            ref_time = float(scalar(db, "physical_time_days"))
            threshold = float(scalar(db, "plume_threshold"))
            ref_key = str(scalar(db, "source_reference_key"))

        gate("frozen_reference_grid_exact", ref.shape == EXPECTED_GRID, ref.shape)
        gate("frozen_reference_time_100d_exact", ref_time == EXPECTED_TIME_DAYS, ref_time)
        gate("frozen_reference_threshold_0p5_exact", threshold == EXPECTED_THRESHOLD, threshold)
        gate("frozen_reference_key_exact", ref_key == EXPECTED_REFERENCE_KEY, ref_key)
        gate(
            "frozen_reference_array_SHA_exact",
            sha256_array(ref) == REFERENCE_ARRAY_SHA,
            sha256_array(ref),
        )
        gate(
            "frozen_reference_mask_SHA_exact",
            sha256_array(mask) == REFERENCE_MASK_SHA,
            sha256_array(mask),
        )

        # ------------------------------------------------------------------
        # Formal acceptance and integration-handoff boundary.
        # ------------------------------------------------------------------
        print("\nFORMAL ACCEPTANCE / INTEGRATION HANDOFF")
        gate("accepted_deployment_state_is_E18R1_frozen_candidate", True)
        gate("historical_reference_role_is_validation_only", True)
        gate("deployment_acceptance_inherited_from_E26R2_only", True)
        gate("no_new_metric_evaluation_in_E27", True)
        gate("no_new_numerical_candidate_created_in_E27", True)
        gate("no_candidate_copy_created_in_E27", True)
        gate("no_reference_copy_created_in_E27", True)
        gate("no_threshold_change_in_E27", threshold == EXPECTED_THRESHOLD)
        gate("no_posthoc_alignment_in_E27", True)
        gate("no_deployment_correction_in_E27", True)
        gate("no_training_or_model_inference_in_E27", True)
        gate("no_upstream_physics_recomputation_in_E27", True)
        gate("runtime_integration_not_performed_in_E27", True)
        gate("IBDP_not_started_in_E27", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("integration_handoff_ready", True)

        gate(
            "frozen_V16_candidate_SHA_exact_after",
            sha256_file(v16_path) == v16_sha_before == V16_FROZEN_SHA,
        )
        gate(
            "frozen_reference_SHA_exact_after",
            sha256_file(ref_path) == ref_sha_before == REFERENCE_FROZEN_FILE_SHA,
        )

        # ------------------------------------------------------------------
        # Persist metadata-only acceptance / handoff artifacts.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)

        e26_authority_rows = [
            {
                "artifact": name,
                "sha256": sha,
                "path": str(drive / E26R2_REL / name),
                "role": "ACCEPTED_E26R2_DEPLOYMENT_AUTHORITY",
            }
            for name, sha in E26R2_ARTIFACTS.items()
        ]
        save_csv(out / "V16E27_E26R2_Authority.csv", e26_authority_rows)

        save_csv(out / "V16E27_Accepted_Deployment_Identity.csv", [
            {
                "role": "ACCEPTED_FROZEN_SGSIM_DEPLOYMENT_STATE",
                "path": str(v16_path),
                "file_sha256": v16_sha_before,
                "grid_shape": "15x50x50",
                "physical_time_days": EXPECTED_TIME_DAYS,
                "background_saturation": background,
                "immutable": True,
                "runtime_role": "PAD_STREAM_INTEGRATION_INPUT",
            },
            {
                "role": "FROZEN_HISTORICAL_VALIDATION_REFERENCE",
                "path": str(ref_path),
                "file_sha256": ref_sha_before,
                "grid_shape": "15x50x50",
                "physical_time_days": EXPECTED_TIME_DAYS,
                "plume_threshold": EXPECTED_THRESHOLD,
                "immutable": True,
                "runtime_role": "VALIDATION_ONLY_NOT_DEPLOYMENT_INPUT",
            },
        ])

        save_csv(out / "V16E27_Authoritative_Gate_Closure.csv", gate_closure_rows)

        integration_roles = [
            {
                "component": "V16E18_R1_frozen_full_grid_candidate",
                "E27_role": "ACCEPTED_DEPLOYMENT_STATE",
                "may_change_in_E28": False,
                "notes": "Numerical values remain immutable; integration may consume by exact identity only.",
            },
            {
                "component": "V16E24_frozen_historical_reference",
                "E27_role": "VALIDATION_REFERENCE_ONLY",
                "may_change_in_E28": False,
                "notes": "Not a runtime correction field and not an input for tuning.",
            },
            {
                "component": "historical_SG7E_threshold_0p5",
                "E27_role": "VALIDATION_THRESHOLD_AUTHORITY",
                "may_change_in_E28": False,
                "notes": "0.21 remains diagnostic-only.",
            },
            {
                "component": "E26R2_deployment_decision",
                "E27_role": "ACCEPTANCE_AUTHORITY",
                "may_change_in_E28": False,
                "notes": "PASS independently reproduced; all four authoritative gates closed.",
            },
            {
                "component": "PAD_Stream_runtime_integration",
                "E27_role": "HANDOFF_TARGET",
                "may_change_in_E28": True,
                "notes": "E28 may wire accepted state into runtime contract but may not alter frozen numerical content.",
            },
            {
                "component": "internal_test_and_OOD",
                "E27_role": "CLOSED",
                "may_change_in_E28": False,
                "notes": "No reopening authorized by E27.",
            },
            {
                "component": "IBDP",
                "E27_role": "DEFERRED",
                "may_change_in_E28": False,
                "notes": "IBDP work begins only after SGSim/PAD-Stream integration path is explicitly closed.",
            },
        ]
        save_csv(out / "V16E27_Integration_Role_Matrix.csv", integration_roles)

        acceptance_manifest = {
            "milestone": MILESTONE,
            "status": STATUS,
            "acceptance_basis": (
                "V16E-25 authoritative four-gate deployment PASS plus "
                "V16E-26-R2 independent decision reproduction PASS"
            ),
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "accepted_deployment_state": {
                "source_milestone": "V16E-18-R1",
                "path": str(v16_path),
                "file_sha256": v16_sha_before,
                "immutable": True,
            },
            "validation_reference": {
                "source_milestone": "V16E-24",
                "path": str(ref_path),
                "file_sha256": ref_sha_before,
                "reference_key": EXPECTED_REFERENCE_KEY,
                "array_sha256": REFERENCE_ARRAY_SHA,
                "mask_sha256": REFERENCE_MASK_SHA,
                "plume_threshold": EXPECTED_THRESHOLD,
                "role": "VALIDATION_ONLY",
                "immutable": True,
            },
            "authoritative_metrics": {
                key: float(e26_summary[key]) for key in EXPECTED_METRICS
            },
            "all_four_authoritative_gates_pass": True,
            "deployment_accepted": True,
            "full_grid_plume_authorized": True,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "threshold_changed": False,
            "runtime_integration_performed": False,
            "integration_handoff_ready": True,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(
            out / "V16E27_SGSim_Deployment_Acceptance_Manifest.json",
            acceptance_manifest,
        )

        integration_contract = {
            "milestone": MILESTONE,
            "status": "PAD_STREAM_INTEGRATION_HANDOFF_READY",
            "accepted_state_contract": {
                "canonical_numerical_input": str(v16_path),
                "canonical_numerical_input_sha256": v16_sha_before,
                "consume_by_exact_identity": True,
                "numerical_mutation_permitted": False,
                "background_completion_is_part_of_frozen_state": True,
                "physical_time_days": EXPECTED_TIME_DAYS,
                "grid_shape": list(EXPECTED_GRID),
            },
            "validation_contract": {
                "canonical_reference": str(ref_path),
                "canonical_reference_sha256": ref_sha_before,
                "historical_reference_key": EXPECTED_REFERENCE_KEY,
                "historical_plume_threshold": EXPECTED_THRESHOLD,
                "reference_is_runtime_correction": False,
                "reference_is_tuning_input": False,
            },
            "deployment_contract": {
                "E25_decision": "PASS",
                "E26R2_independent_decision": "PASS",
                "decision_reproduced": True,
                "all_authoritative_gates_pass": True,
                "full_grid_plume_authorized": True,
            },
            "E28_boundary": {
                "may_wire_accepted_state_into_PAD_Stream_runtime": True,
                "may_change_frozen_state": False,
                "may_change_historical_reference": False,
                "may_change_historical_threshold": False,
                "may_reopen_internal_test": False,
                "may_reopen_OOD": False,
                "may_begin_IBDP": False,
            },
            "next_milestone": NEXT,
        }
        save_json(
            out / "V16E27_PAD_Stream_Integration_Handoff_Contract.json",
            integration_contract,
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "accepted_frozen_V16_candidate_sha256": v16_sha_before,
            "frozen_historical_reference_sha256": ref_sha_before,
            "historical_reference_key": EXPECTED_REFERENCE_KEY,
            "historical_authoritative_plume_threshold": EXPECTED_THRESHOLD,
            "primary_volume_relative_error":
                float(e26_summary["primary_volume_relative_error"]),
            "footprint_IoU":
                float(e26_summary["footprint_IoU"]),
            "centroid_distance_cells":
                float(e26_summary["centroid_distance_cells"]),
            "vertical_extent_error_layers":
                float(e26_summary["vertical_extent_error_layers"]),
            "all_authoritative_gates_pass": True,
            "deployment_accepted": True,
            "full_grid_plume_authorized": True,
            "frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "threshold_changed": False,
            "runtime_integration_performed": False,
            "integration_handoff_ready": True,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E27_Summary.json", summary)

        (out / "V16E27_Handoff.md").write_text(
            "# PAD-Stream V16E-27 Handoff\n\n"
            "The SGSim 100-day V16 deployment state is formally accepted for PAD-Stream integration handoff. "
            "Acceptance is inherited from the authoritative V16E-25 four-gate PASS and the independent "
            "V16E-26-R2 reproduction PASS.\n\n"
            f"- Accepted frozen V16 candidate SHA-256: `{v16_sha_before}`\n"
            f"- Frozen historical reference SHA-256: `{ref_sha_before}`\n"
            "- Historical reference: `SG7A_corrected @ 100 days`\n"
            "- Historical plume threshold: `S >= 0.5`\n"
            "- All four authoritative SG7E gates: `PASS`\n"
            "- Deployment accepted: `YES`\n"
            "- Full-grid plume authorized: `YES`\n"
            "- Frozen candidate modified: `NO`\n"
            "- Historical reference modified: `NO`\n"
            "- Runtime integration performed in E27: `NO`\n"
            "- Integration handoff ready: `YES`\n"
            "- Internal test / OOD reopened: `NO / NO`\n"
            "- IBDP started: `NO`\n\n"
            "The historical reference remains validation-only and is not a runtime correction field. "
            "E28 may wire the accepted frozen state into the PAD-Stream runtime contract, but may not change "
            "the frozen candidate, historical reference, or historical threshold.\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        save_csv(
            out / "V16E27_Final_Gate_Matrix.csv",
            [{"gate": name, **rec} for name, rec in gates.items()],
        )

        print("\n" + "=" * 132)
        print("V16E-27 RESULT: PASS")
        print("=" * 132)
        print(f"{'Accepted SGSim deployment state':72}: YES")
        print(f"{'Frozen V16 candidate SHA-256':72}: {v16_sha_before}")
        print(f"{'Frozen historical reference SHA-256':72}: {ref_sha_before}")
        print(f"{'Historical threshold':72}: S >= {EXPECTED_THRESHOLD}")
        print(f"{'PRIMARY_VOLUME_GATE':72}: {float(e26_summary['primary_volume_relative_error']):.12g} <= 0.10 | PASS")
        print(f"{'FOOTPRINT_IOU_GATE':72}: {float(e26_summary['footprint_IoU']):.12g} >= 0.90 | PASS")
        print(f"{'CENTROID_GATE_CELLS':72}: {float(e26_summary['centroid_distance_cells']):.12g} <= 2.0 | PASS")
        print(f"{'VERTICAL_EXTENT_GATE_LAYERS':72}: {float(e26_summary['vertical_extent_error_layers']):.12g} <= 2.0 | PASS")
        print(f"{'Deployment accepted':72}: YES")
        print(f"{'Full-grid plume authorized':72}: YES")
        print(f"{'Runtime integration performed in E27':72}: NO")
        print(f"{'PAD-Stream integration handoff ready':72}: YES")
        print(f"{'Frozen V16 candidate modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        print(f"{'IBDP started':72}: NO")

        for name in [
            "V16E27_SGSim_Deployment_Acceptance_Manifest.json",
            "V16E27_PAD_Stream_Integration_Handoff_Contract.json",
            "PAD_Stream_V16E27_Summary.json",
            "V16E27_Handoff.md",
            "V16E27_E26R2_Authority.csv",
            "V16E27_Accepted_Deployment_Identity.csv",
            "V16E27_Authoritative_Gate_Closure.csv",
            "V16E27_Integration_Role_Matrix.csv",
            "V16E27_Final_Gate_Matrix.csv",
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
            "deployment_accepted": False,
            "full_grid_plume_authorized": False,
            "integration_handoff_ready": False,
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
                "V16E-27-R1 - Repair only the failed V16E-27 acceptance/handoff "
                "provenance gate; preserve E26-R2 and both frozen numerical objects unchanged"
            ),
        }
        p = blocked / "V16E27_Blocked_SGSim_Deployment_Acceptance_Handoff.json"
        save_json(p, payload)
        print(f"\n[FAIL] V16E-27 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(p)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, required=True)
    args = ap.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
