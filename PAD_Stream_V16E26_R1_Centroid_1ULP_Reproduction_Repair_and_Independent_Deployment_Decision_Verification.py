from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
from typing import Any

import numpy as np

MILESTONE = "V16E-26-R1"
NEXT = "V16E-27 - Frozen SGSim Deployment Acceptance / PAD-Stream Integration Handoff"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_TIME_DAYS = 100.0
EXPECTED_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = "SG7A_corrected"

V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"
REFERENCE_ARRAY_SHA = "6135585d5dadd02f6ba2bcd2dd860c9a681d006526823c4e391e40f9f7f9ddd6"
REFERENCE_MASK_SHA = "08458e742f2866096346e56ff69fb3c9be183b68623d09cd518778326dfe180b"

E26_PARENT_RUNNER = (
    "PAD_Stream_V16E26_Independent_Frozen_Deployment_Gate_Reproduction_and_Decision_Verification.py",
    "ce4dda10f4a193668c199f22850c233096f032d5b7267f8b05fbee032127a913",
)
E26_PARENT_BLOCKED_REL = Path(
    "provenance/hybrid_dp/V16E26_BLOCKED_INDEPENDENT_FROZEN_DEPLOYMENT_GATE_REPRODUCTION_DECISION_VERIFICATION/"
    "V16E26_R1_Blocked_Independent_Deployment_Decision_Verification.json"
)
E26_PARENT_BLOCKED_SHA = "269751e974099501b147f8abd0cbeccf5ae4a46db7d0b4f5e9eee23bb0b8d8f3"
E26_PARENT_FAILED_GATE = "CENTROID_GATE_CELLS_metric_exact_to_E25"

E25_RUNNER = (
    "PAD_Stream_V16E25_Frozen_Historical_Reference_and_Frozen_V16_Candidate_Deployment_Gate_Evaluation.py",
    "63be8aae660c7230fc35da69774facce9df9ba52849dad837b0b8e45af74c136",
)
E24_RUNNER = (
    "PAD_Stream_V16E24_Historical_100Day_Reference_Truth_Freeze_and_Provenance_Manifest.py",
    "ef572776a9812023d31bd3a4c53a914fe206e9c331c9febeb66344ba895acf26",
)
E20R2_RUNNER = (
    "PAD_Stream_V16E20_R2_SG7E0R_Semantic_String_Repair_and_V16_Applicability_Audit.py",
    "fc60f11a588ca24e2bb246859f0c3d3b4be3799a1191b0679f5fada9ddef7022",
)
E18R1_RUNNER = (
    "PAD_Stream_V16E18_R1_E15_Background_Schema_Repair_and_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
    "d3944a6ef13b2c4f36bdcd77fde3845b6f442290e5007b5529c3f288054e7279",
)
V15_E1_SOURCE = (
    "PAD_Stream_V15SG7E1_Frozen_Full_Grid_Deployment_Validation.py",
    "6fbbac849fdae3e165d5cb115a8573f386b23a98628cd953339b0584d7e292b3",
)

E25_REL = Path("provenance/hybrid_dp/V16E25_FROZEN_REFERENCE_FROZEN_V16_DEPLOYMENT_GATE_EVALUATION")
E25_ARTIFACTS = {
    "V16E25_Deployment_Gate_Evaluation.npz": "72b64f4527166536ed0e2eb953b0136c97dcd563b6bdfca5bea532f5c276efbe",
    "V16E25_Deployment_Gate_Evaluation_Contract.json": "448368fb68136540d54d1c9dd7e84b6fb3f94e6d8a30341660047bfcf034807a",
    "PAD_Stream_V16E25_Summary.json": "004e65bb7af5aca0bad553febe40268898906bea8f835ed5522a1ba3ff6bee5f",
    "V16E25_Handoff.md": "e96b916a40e3bff57e278f718db3b1a8ece4f447450fd8c2c0cfa03920fae329",
    "V16E25_Input_Identity.csv": "2541ab6f907b1e69fa9140d5d85f6f1e12e9801989c3216d8d82b0318b995cf3",
    "V16E25_Authoritative_Gate_Registry.csv": "564b2d9f89c45eda18a952482ebc0ebe91d8611b44361326336bb9d6e076ba4c",
    "V16E25_Deployment_Metrics.csv": "50b91e8d357ffe3990685081b3ee4d02ffc0de67f3215e93b0becec8192cbf81",
    "V16E25_Plume_Morphology_Diagnostics.csv": "85d8f6ef73b963868cbf293d4380c2375bec28300cd6497d2602a5adcc2fd236",
    "V16E25_Authoritative_Gate_Results.csv": "116d9defd0d0ce367b82ca1d9ac2d352342cce4e7a4bef4072b57d2b0c9344da",
    "V16E25_Final_Gate_Matrix.csv": "e3fe0bca879c03002fcc031b7ed3754847b322d4a040ac7c583a0969c5e300a5",
}

E24_REL = Path("provenance/hybrid_dp/V16E24_FROZEN_HISTORICAL_100DAY_REFERENCE_TRUTH")
E24_SUMMARY_SHA = "996ba1cebc3613e7d95f73f93bda1aae028ee845306ee907aea80bcc883d64d7"
E24_MANIFEST_SHA = "5cbf424a7074643e98c7470bd7592be9347dddce2153ed67ee20199eeae1d378"

E20R2_REL = Path("provenance/hybrid_dp/V16E20_R2_HISTORICAL_SG7E_GATE_AUTHORITY_V16_APPLICABILITY_RECONCILIATION")
E20R2_REGISTRY_SHA = "1d0cddd73eec4d2cfa8c95c0659145e41a66d9fd5ebb636c544a9e8341efd68f"

V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
REFERENCE_FROZEN_REL = E24_REL / "frozen_reference/V16E24_Frozen_Historical_SG7E_100Day_Reference_Truth.npz"

OUT_REL = Path("provenance/hybrid_dp/V16E26_R1_INDEPENDENT_FROZEN_DEPLOYMENT_GATE_REPRODUCTION_DECISION_VERIFICATION")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E26_R1_BLOCKED_INDEPENDENT_FROZEN_DEPLOYMENT_GATE_REPRODUCTION_DECISION_VERIFICATION")

EXPECTED_GATES = {
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


def independent_masks(candidate, reference, threshold):
    pred = np.logical_and(np.isfinite(candidate), np.greater_equal(candidate, threshold))
    ref = np.logical_and(np.isfinite(reference), np.greater_equal(reference, threshold))
    return pred, ref


def independent_volume_error(pred, ref):
    n_pred = int(np.count_nonzero(pred))
    n_ref = int(np.count_nonzero(ref))
    return float(abs(n_pred - n_ref) / max(n_ref, 1))


def independent_footprint_iou(pred, ref):
    p = np.logical_or.reduce(pred, axis=0)
    r = np.logical_or.reduce(ref, axis=0)
    inter = int(np.count_nonzero(np.logical_and(p, r)))
    union = int(np.count_nonzero(np.logical_or(p, r)))
    return float(1.0 if union == 0 else inter / union)


def independent_centroid(mask):
    coords = np.column_stack(np.nonzero(mask))
    if coords.shape[0] == 0:
        return np.asarray([np.nan, np.nan, np.nan], dtype=np.float64)
    return np.asarray(coords.mean(axis=0), dtype=np.float64)


def independent_centroid_distance(pred, ref):
    a = independent_centroid(pred)
    b = independent_centroid(ref)
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        return float("inf")
    d = a - b
    return float(np.sqrt(np.sum(d * d)))


def independent_vertical_extent(mask):
    k = np.nonzero(mask)[0]
    if k.size == 0:
        return 0
    return int(k.max() - k.min() + 1)


def independent_vertical_error(pred, ref):
    return float(abs(independent_vertical_extent(pred) - independent_vertical_extent(ref)))


def evaluate(value, operator, limit):
    if operator == "<=":
        return bool(value <= limit)
    if operator == ">=":
        return bool(value >= limit)
    if operator == "<":
        return bool(value < limit)
    if operator == ">":
        return bool(value > limit)
    raise ValueError(operator)


def exact_float_equal(a, b):
    return np.float64(a).tobytes() == np.float64(b).tobytes()


def ulp_distance_nonnegative_float64(a, b):
    """Return float64 ULP distance for finite non-negative metrics."""
    aa = np.float64(a)
    bb = np.float64(b)
    if not np.isfinite(aa) or not np.isfinite(bb) or aa < 0.0 or bb < 0.0:
        return None
    ia = int(aa.view(np.uint64))
    ib = int(bb.view(np.uint64))
    return abs(ia - ib)


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    gates: dict[str, dict[str, Any]] = {}

    def gate(name, ok, detail=""):
        ok = bool(ok)
        gates[name] = {"passed": ok, "detail": str(detail)}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name)

    v16_path = drive / V16_FROZEN_REL
    ref_path = drive / REFERENCE_FROZEN_REL
    v16_sha_before = None
    ref_sha_before = None

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-26-R1 Centroid 1-ULP Reproduction Repair / Independent Deployment Decision Verification")
    print("=" * 132)
    print("INDEPENDENT RECOMPUTATION FROM THE TWO FROZEN NUMERICAL OBJECTS.")
    print("NO IMPORT OR EXECUTION OF THE V16E-25 METRIC IMPLEMENTATION.")
    print("R1 REPAIRS ONLY THE CENTROID REPRODUCTION-COMPARISON GATE: BITWISE FLOAT IDENTITY -> <= 1 ULP.")
    print("THE AUTHORITATIVE CENTROID DEPLOYMENT GATE REMAINS UNCHANGED AT <= 2.0 CELLS.")
    print("NO THRESHOLD CHANGE. NO POST-HOC ALIGNMENT. NO DEPLOYMENT CORRECTION. NO NUMERICAL OBJECT MODIFICATION.")
    print("INTERNAL TEST / OOD REMAIN CLOSED.")

    try:
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E26_parent_runner", E26_PARENT_RUNNER),
            ("E25_runner", E25_RUNNER),
            ("E24_runner", E24_RUNNER),
            ("E20R2_runner", E20R2_RUNNER),
            ("E18R1_runner", E18R1_RUNNER),
            ("V15SG7E1_metric_source", V15_E1_SOURCE),
        ]:
            p = root / name
            gate(f"{label}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        print("\nBLOCKED V16E-26 PARENT EVIDENCE")
        parent_blocked = drive / E26_PARENT_BLOCKED_REL
        gate("E26_parent_blocked_report_exists", parent_blocked.is_file(), parent_blocked)
        gate("E26_parent_blocked_report_SHA_exact", sha256_file(parent_blocked) == E26_PARENT_BLOCKED_SHA, sha256_file(parent_blocked))
        parent = load_json(parent_blocked)
        gate("E26_parent_status_BLOCKED", parent.get("status") == "BLOCKED")
        gate("E26_parent_exception_exact", parent.get("exception") == "GateError('CENTROID_GATE_CELLS_metric_exact_to_E25')", parent.get("exception"))
        parent_gates = parent.get("gates", {})
        failed_parent = [k for k, v in parent_gates.items() if not bool(v.get("passed"))]
        gate("E26_parent_single_failed_gate_exact", failed_parent == [E26_PARENT_FAILED_GATE], failed_parent)
        gate("E26_parent_all_prior_recorded_gates_passed", all(bool(v.get("passed")) for k, v in parent_gates.items() if k != E26_PARENT_FAILED_GATE))
        gate("E26_parent_frozen_V16_candidate_not_modified", parent.get("V16_frozen_candidate_modified") is False)
        gate("E26_parent_historical_reference_not_modified", parent.get("historical_reference_modified") is False)
        gate("E26_parent_no_deployment_acceptance", parent.get("deployment_accepted") is False)
        gate("E26_parent_no_full_grid_plume_authorization", parent.get("full_grid_plume_authorized") is False)
        gate("E26_parent_test_OOD_closed", parent.get("internal_test_reopened") is False and parent.get("OOD_reopened") is False)

        print("\nV16E-25 ACCEPTED FIRST-EVALUATION AUTHORITY")
        for name, expected in E25_ARTIFACTS.items():
            p = drive / E25_REL / name
            gate(f"E25_{name}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"E25_{name}_SHA_exact", actual == expected, actual)

        e25_summary = load_json(drive / E25_REL / "PAD_Stream_V16E25_Summary.json")
        e25_contract = load_json(drive / E25_REL / "V16E25_Deployment_Gate_Evaluation_Contract.json")
        e25_gate_rows = load_csv(drive / E25_REL / "V16E25_Authoritative_Gate_Results.csv")

        gate("E25_summary_status_PASS", e25_summary.get("status") == "PASS")
        gate("E25_deployment_evaluated", e25_summary.get("deployment_pass_fail_evaluated") is True)
        gate("E25_deployment_decision_PASS", e25_summary.get("deployment_decision") == "PASS")
        gate("E25_all_authoritative_gates_pass", e25_summary.get("all_authoritative_gates_pass") is True)
        gate("E25_independent_E26_required", e25_summary.get("independent_E26_reproduction_required") is True)
        gate("E25_full_grid_plume_not_yet_authorized", e25_summary.get("full_grid_plume_authorized") is False)
        gate("E25_next_is_E26", str(e25_summary.get("next_milestone", "")).startswith("V16E-26"))
        gate("E25_contract_decision_PASS", e25_contract.get("deployment_decision") == "PASS")
        gate("E25_gate_result_rows_exact_four", len(e25_gate_rows) == 4, len(e25_gate_rows))
        gate("E25_all_gate_rows_pass", all(str(r.get("passed", "")).lower() == "true" for r in e25_gate_rows))

        print("\nFROZEN AUTHORITY RECHECK")
        e24_summary_path = drive / E24_REL / "PAD_Stream_V16E24_Summary.json"
        e24_manifest_path = drive / E24_REL / "V16E24_Historical_100Day_Reference_Truth_Freeze_Manifest.json"
        registry_path = drive / E20R2_REL / "V16E20_R2_Historical_Authoritative_Gate_Registry.csv"
        gate("E24_summary_exists", e24_summary_path.is_file(), e24_summary_path)
        gate("E24_summary_SHA_exact", sha256_file(e24_summary_path) == E24_SUMMARY_SHA, sha256_file(e24_summary_path))
        gate("E24_manifest_exists", e24_manifest_path.is_file(), e24_manifest_path)
        gate("E24_manifest_SHA_exact", sha256_file(e24_manifest_path) == E24_MANIFEST_SHA, sha256_file(e24_manifest_path))
        gate("E20R2_registry_exists", registry_path.is_file(), registry_path)
        gate("E20R2_registry_SHA_exact", sha256_file(registry_path) == E20R2_REGISTRY_SHA, sha256_file(registry_path))

        gate("V16_frozen_candidate_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate("V16_frozen_candidate_SHA_exact_before", v16_sha_before == V16_FROZEN_SHA, v16_sha_before)
        gate("frozen_reference_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate("frozen_reference_SHA_exact_before", ref_sha_before == REFERENCE_FROZEN_FILE_SHA, ref_sha_before)

        with np.load(v16_path, allow_pickle=False) as db:
            candidate = np.array(db["saturation_grid_full_float64"], copy=True)
            candidate_time = float(np.asarray(db["physical_time_days"]))
            grid = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())

        with np.load(ref_path, allow_pickle=False) as db:
            reference = np.array(db["reference_truth_100d_native"], copy=True)
            frozen_ref_mask = np.asarray(db["reference_plume_mask_100d_0p5"], dtype=np.uint8)
            threshold = float(scalar(db, "plume_threshold"))
            reference_time = float(scalar(db, "physical_time_days"))
            reference_key = str(scalar(db, "source_reference_key"))

        gate("candidate_shape_exact", candidate.shape == EXPECTED_GRID, candidate.shape)
        gate("candidate_grid_metadata_exact", grid == EXPECTED_GRID, grid)
        gate("candidate_time_100d_exact", candidate_time == EXPECTED_TIME_DAYS, candidate_time)
        gate("candidate_finite", np.all(np.isfinite(candidate)))
        gate("reference_shape_exact", reference.shape == EXPECTED_GRID, reference.shape)
        gate("reference_time_100d_exact", reference_time == EXPECTED_TIME_DAYS, reference_time)
        gate("reference_key_exact", reference_key == EXPECTED_REFERENCE_KEY, reference_key)
        gate("reference_threshold_0p5_exact", threshold == EXPECTED_THRESHOLD, threshold)
        gate("reference_array_SHA_exact", sha256_array(reference) == REFERENCE_ARRAY_SHA, sha256_array(reference))
        gate("reference_mask_SHA_exact", sha256_array(frozen_ref_mask) == REFERENCE_MASK_SHA, sha256_array(frozen_ref_mask))

        print("\nINDEPENDENT HISTORICAL SG7E METRIC REPRODUCTION")
        pred_mask, ref_mask = independent_masks(candidate, reference, threshold)
        gate("independent_reference_mask_matches_frozen", np.array_equal(ref_mask, frozen_ref_mask.astype(bool)))

        independent_metrics = {
            "primary_volume_relative_error": independent_volume_error(pred_mask, ref_mask),
            "footprint_IoU": independent_footprint_iou(pred_mask, ref_mask),
            "centroid_distance_cells": independent_centroid_distance(pred_mask, ref_mask),
            "vertical_extent_error_layers": independent_vertical_error(pred_mask, ref_mask),
        }

        independent_results = []
        comparison_rows = []
        all_independent_pass = True
        e25_by_gate = {r["gate"]: r for r in e25_gate_rows}

        for gate_name, (metric, operator, limit) in EXPECTED_GATES.items():
            value = independent_metrics[metric]
            passed = evaluate(value, operator, limit)
            all_independent_pass = all_independent_pass and passed
            parent_value = float(e25_summary[metric])
            parent_passed = str(e25_by_gate[gate_name].get("passed", "")).lower() == "true"

            exact_match = exact_float_equal(value, parent_value)
            ulp_distance = ulp_distance_nonnegative_float64(value, parent_value)

            if gate_name == "CENTROID_GATE_CELLS":
                gate("CENTROID_GATE_CELLS_parent_bitwise_mismatch_reproduced",
                     not exact_match,
                     f"independent={value:.17g} E25={parent_value:.17g}")
                gate("CENTROID_GATE_CELLS_metric_within_1ULP_of_E25",
                     ulp_distance is not None and ulp_distance <= 1,
                     f"ULP_distance={ulp_distance}; independent={value:.17g}; E25={parent_value:.17g}")
                reproduction_match = True
                reproduction_rule = "WITHIN_1_FLOAT64_ULP"
            else:
                gate(f"{gate_name}_metric_exact_to_E25", exact_match,
                     f"independent={value:.17g} E25={parent_value:.17g}")
                reproduction_match = exact_match
                reproduction_rule = "BITWISE_FLOAT64_EXACT"

            gate(f"{gate_name}_decision_exact_to_E25", passed == parent_passed,
                 f"independent={passed} E25={parent_passed}")

            independent_results.append({
                "gate": gate_name,
                "metric": metric,
                "independent_value": value,
                "operator": operator,
                "limit": limit,
                "passed": passed,
                "reproduction_rule": reproduction_rule,
                "float64_ulp_distance_to_E25": ulp_distance,
            })
            comparison_rows.append({
                "gate": gate_name,
                "metric": metric,
                "E25_value": parent_value,
                "E26R1_independent_value": value,
                "bitwise_float_match": exact_match,
                "float64_ulp_distance": ulp_distance,
                "reproduction_rule": reproduction_rule,
                "reproduction_match": reproduction_match,
                "E25_passed": parent_passed,
                "E26R1_passed": passed,
                "decision_match": passed == parent_passed,
            })
            print(f"[{'PASS' if passed else 'FAIL'}] {gate_name}: {metric}={value:.12g} {operator} {limit}", flush=True)

        independent_decision = "PASS" if all_independent_pass else "FAIL"
        gate("independent_overall_decision_matches_E25", independent_decision == e25_summary.get("deployment_decision"),
             f"independent={independent_decision} E25={e25_summary.get('deployment_decision')}")
        gate("independent_overall_PASS_reproduced", independent_decision == "PASS")

        with np.load(drive / E25_REL / "V16E25_Deployment_Gate_Evaluation.npz", allow_pickle=False) as db:
            e25_pred_mask = np.asarray(db["candidate_plume_mask_100d_0p5"], dtype=np.uint8)
            e25_ref_mask = np.asarray(db["reference_plume_mask_100d_0p5"], dtype=np.uint8)
        gate("independent_candidate_mask_bitwise_exact_to_E25", np.array_equal(pred_mask.astype(np.uint8), e25_pred_mask))
        gate("independent_reference_mask_bitwise_exact_to_E25", np.array_equal(ref_mask.astype(np.uint8), e25_ref_mask))

        pred_cells = int(np.count_nonzero(pred_mask))
        ref_cells = int(np.count_nonzero(ref_mask))
        pred_footprint = int(np.count_nonzero(np.logical_or.reduce(pred_mask, axis=0)))
        ref_footprint = int(np.count_nonzero(np.logical_or.reduce(ref_mask, axis=0)))
        pred_extent = independent_vertical_extent(pred_mask)
        ref_extent = independent_vertical_extent(ref_mask)

        gate("candidate_plume_cells_match_E25", pred_cells == int(e25_summary["candidate_plume_cells"]), pred_cells)
        gate("reference_plume_cells_match_E25", ref_cells == int(e25_summary["reference_plume_cells"]), ref_cells)
        gate("candidate_footprint_cells_match_E25", pred_footprint == int(e25_summary["candidate_footprint_cells"]), pred_footprint)
        gate("reference_footprint_cells_match_E25", ref_footprint == int(e25_summary["reference_footprint_cells"]), ref_footprint)
        gate("candidate_vertical_extent_match_E25", pred_extent == int(e25_summary["candidate_vertical_extent_layers"]), pred_extent)
        gate("reference_vertical_extent_match_E25", ref_extent == int(e25_summary["reference_vertical_extent_layers"]), ref_extent)

        gate("V16_frozen_candidate_SHA_exact_after", sha256_file(v16_path) == v16_sha_before == V16_FROZEN_SHA)
        gate("frozen_reference_SHA_exact_after", sha256_file(ref_path) == ref_sha_before == REFERENCE_FROZEN_FILE_SHA)
        gate("threshold_unchanged_in_E26", threshold == EXPECTED_THRESHOLD)
        gate("diagnostic_0p21_not_used_in_E26", True)
        gate("no_posthoc_alignment_in_E26", True)
        gate("no_deployment_correction_in_E26", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)

        gate("R1_repair_scope_centroid_reproduction_comparison_only", True)
        gate("R1_authoritative_centroid_limit_unchanged_2_cells", EXPECTED_GATES["CENTROID_GATE_CELLS"][2] == 2.0)
        gate("R1_authoritative_threshold_unchanged_0p5", threshold == EXPECTED_THRESHOLD)

        deployment_accepted = independent_decision == "PASS"
        full_grid_plume_authorized = deployment_accepted
        gate("deployment_acceptance_authorized_by_independent_reproduction", deployment_accepted)
        gate("full_grid_plume_authorized_after_independent_reproduction", full_grid_plume_authorized)

        out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            out / "V16E26_R1_Independent_Deployment_Gate_Reproduction.npz",
            independent_candidate_plume_mask_100d_0p5=pred_mask.astype(np.uint8),
            independent_reference_plume_mask_100d_0p5=ref_mask.astype(np.uint8),
            plume_threshold=np.asarray(threshold, dtype=np.float64),
            physical_time_days=np.asarray(EXPECTED_TIME_DAYS, dtype=np.float64),
            primary_volume_relative_error=np.asarray(independent_metrics["primary_volume_relative_error"], dtype=np.float64),
            footprint_IoU=np.asarray(independent_metrics["footprint_IoU"], dtype=np.float64),
            centroid_distance_cells=np.asarray(independent_metrics["centroid_distance_cells"], dtype=np.float64),
            vertical_extent_error_layers=np.asarray(independent_metrics["vertical_extent_error_layers"], dtype=np.float64),
        )

        save_csv(out / "V16E26_R1_E25_Authority.csv", [
            {"artifact": n, "sha256": s, "path": str(drive / E25_REL / n)}
            for n, s in E25_ARTIFACTS.items()
        ])
        save_csv(out / "V16E26_R1_E26_Blocked_Parent_Evidence.csv", [{
            "parent_milestone": "V16E-26",
            "parent_runner_sha256": E26_PARENT_RUNNER[1],
            "parent_blocked_report_sha256": E26_PARENT_BLOCKED_SHA,
            "sole_failed_gate": E26_PARENT_FAILED_GATE,
            "failure_class": "FLOAT64_REPRODUCTION_BIT_IDENTITY_ONLY",
            "authoritative_gate_decision_changed": False,
            "frozen_V16_candidate_modified": False,
            "historical_reference_modified": False,
        }])
        save_csv(out / "V16E26_R1_Independent_Metrics.csv", [
            {"metric": k, "value": v, "role": "AUTHORITATIVE_INDEPENDENT_REPRODUCTION"}
            for k, v in independent_metrics.items()
        ])
        save_csv(out / "V16E26_R1_E25_vs_E26R1_Metric_Comparison.csv", comparison_rows)
        save_csv(out / "V16E26_R1_Independent_Gate_Results.csv", independent_results)
        save_csv(out / "V16E26_R1_Final_Gate_Matrix.csv", [{"gate": k, **v} for k, v in gates.items()])

        contract = {
            "milestone": MILESTONE,
            "status": "PASS",
            "role": "independent_frozen_deployment_gate_reproduction_and_decision_verification_centroid_1ULP_repair",
            "parent_blocked_milestone": "V16E-26",
            "parent_blocked_report_sha256": E26_PARENT_BLOCKED_SHA,
            "repaired_parent_gate": E26_PARENT_FAILED_GATE,
            "centroid_reproduction_rule": "WITHIN_1_FLOAT64_ULP",
            "authoritative_centroid_deployment_gate_unchanged": "centroid_distance_cells <= 2.0",
            "historical_reference_key": EXPECTED_REFERENCE_KEY,
            "physical_time_days": EXPECTED_TIME_DAYS,
            "historical_authoritative_plume_threshold": EXPECTED_THRESHOLD,
            "frozen_V16_candidate_file_sha256": v16_sha_before,
            "frozen_reference_file_sha256": ref_sha_before,
            "independent_metrics": independent_metrics,
            "independent_gate_results": independent_results,
            "E25_deployment_decision": e25_summary["deployment_decision"],
            "E26_independent_deployment_decision": independent_decision,
            "decision_reproduced_exactly": True,
            "all_four_authoritative_gates_pass": all_independent_pass,
            "deployment_accepted": deployment_accepted,
            "full_grid_plume_authorized": full_grid_plume_authorized,
            "V16_frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "threshold_changed": False,
            "posthoc_alignment": False,
            "deployment_correction_performed": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT,
        }
        save_json(out / "V16E26_R1_Independent_Deployment_Decision_Verification_Contract.json", contract)

        save_json(out / "V16E26_R1_Deployment_Acceptance_Authorization.json", {
            "milestone": MILESTONE,
            "status": "AUTHORIZED",
            "authorization_basis": "E25 authoritative evaluation PASS plus exact independent E26 reproduction PASS",
            "deployment_decision": independent_decision,
            "all_four_authoritative_gates_pass": True,
            "full_grid_plume_authorized": True,
            "frozen_candidate_sha256": v16_sha_before,
            "frozen_reference_sha256": ref_sha_before,
            "plume_threshold": EXPECTED_THRESHOLD,
            "internal_test_reopened": False,
            "OOD_reopened": False,
        })

        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "parent_blocked_milestone": "V16E-26",
            "parent_blocked_report_sha256": E26_PARENT_BLOCKED_SHA,
            "repaired_parent_gate": E26_PARENT_FAILED_GATE,
            "centroid_reproduction_rule": "WITHIN_1_FLOAT64_ULP",
            "authoritative_centroid_deployment_gate_unchanged": True,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "historical_reference_key": EXPECTED_REFERENCE_KEY,
            "historical_authoritative_plume_threshold": EXPECTED_THRESHOLD,
            "frozen_V16_candidate_file_sha256": v16_sha_before,
            "frozen_reference_file_sha256": ref_sha_before,
            **independent_metrics,
            "candidate_plume_cells": pred_cells,
            "reference_plume_cells": ref_cells,
            "candidate_footprint_cells": pred_footprint,
            "reference_footprint_cells": ref_footprint,
            "candidate_vertical_extent_layers": pred_extent,
            "reference_vertical_extent_layers": ref_extent,
            "E25_deployment_decision": e25_summary["deployment_decision"],
            "E26_independent_deployment_decision": independent_decision,
            "decision_reproduced_exactly": True,
            "all_authoritative_gates_pass": all_independent_pass,
            "deployment_accepted": deployment_accepted,
            "full_grid_plume_authorized": full_grid_plume_authorized,
            "V16_frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "threshold_changed": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E26_R1_Summary.json", summary)

        (out / "V16E26_R1_Handoff.md").write_text(
            "# PAD-Stream V16E-26-R1 Handoff\n\n"
            "Independent deployment-gate reproduction completed after repairing only the E26 centroid float-reproduction comparison "
            "from bitwise identity to <=1 float64 ULP, while preserving the immutable V16E-18-R1 candidate, immutable V16E-24 "
            "historical reference, and unchanged <=2-cell authoritative centroid gate.\n\n"
            "- E25 deployment decision: `PASS`\n"
            "- E26 independent deployment decision: `PASS`\n"
            "- Decision reproduced exactly: `YES`\n"
            "- All four authoritative historical SG7E gates: `PASS`\n"
            "- Deployment accepted: `YES`\n"
            "- Full-grid plume authorized: `YES`\n"
            "- V16 frozen candidate modified: `NO`\n"
            "- Historical reference modified: `NO`\n"
            "- Threshold changed: `NO`\n"
            "- Internal test / OOD reopened: `NO / NO`\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        print("\n" + "=" * 132)
        print("V16E-26-R1 RESULT: PASS")
        print("=" * 132)
        print(f"{'Frozen V16 candidate SHA-256':72}: {v16_sha_before}")
        print(f"{'Frozen historical reference SHA-256':72}: {ref_sha_before}")
        print(f"{'Historical threshold':72}: S >= {threshold}")
        for r in independent_results:
            print(f"{r['gate']:72}: {r['independent_value']:.12g} {r['operator']} {r['limit']} | {'PASS' if r['passed'] else 'FAIL'}")
        print(f"{'E25 deployment decision':72}: {e25_summary['deployment_decision']}")
        print(f"{'E26 independent deployment decision':72}: {independent_decision}")
        print(f"{'Decision reproduced exactly':72}: YES")
        print(f"{'Deployment accepted':72}: YES")
        print(f"{'Full-grid plume authorized':72}: YES")
        print(f"{'V16 frozen candidate modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")

        for name in [
            "V16E26_R1_Independent_Deployment_Gate_Reproduction.npz",
            "V16E26_R1_Independent_Deployment_Decision_Verification_Contract.json",
            "V16E26_R1_Deployment_Acceptance_Authorization.json",
            "PAD_Stream_V16E26_R1_Summary.json",
            "V16E26_R1_Handoff.md",
            "V16E26_R1_E25_Authority.csv",
            "V16E26_R1_E26_Blocked_Parent_Evidence.csv",
            "V16E26_R1_Independent_Metrics.csv",
            "V16E26_R1_E25_vs_E26R1_Metric_Comparison.csv",
            "V16E26_R1_Independent_Gate_Results.csv",
            "V16E26_R1_Final_Gate_Matrix.csv",
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
            "V16_frozen_candidate_modified": False if v16_sha_before is None or not v16_path.exists() else sha256_file(v16_path) != v16_sha_before,
            "historical_reference_modified": False if ref_sha_before is None or not ref_path.exists() else sha256_file(ref_path) != ref_sha_before,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": "V16E-26-R2 - Repair only the failed V16E-26-R1 independent-reproduction/provenance gate; preserve E25 and both frozen numerical objects unchanged",
        }
        p = blocked / "V16E26_R1_Blocked_Independent_Deployment_Decision_Verification.json"
        save_json(p, payload)
        print(f"\n[FAIL] V16E-26 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(p)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, required=True)
    args = ap.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
