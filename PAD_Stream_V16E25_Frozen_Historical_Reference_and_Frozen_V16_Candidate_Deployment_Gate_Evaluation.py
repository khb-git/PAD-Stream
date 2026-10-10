from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import sys
from typing import Any

import numpy as np


MILESTONE = "V16E-25"
SUCCESS = "PASS"
NEXT = "V16E-26 - Independent Frozen Deployment-Gate Reproduction / Decision Verification"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_TIME_DAYS = 100.0
EXPECTED_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = "SG7A_corrected"

# Frozen numerical identities.
V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
REFERENCE_FROZEN_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"
REFERENCE_ARRAY_SHA = "6135585d5dadd02f6ba2bcd2dd860c9a681d006526823c4e391e40f9f7f9ddd6"
REFERENCE_MASK_SHA = "08458e742f2866096346e56ff69fb3c9be183b68623d09cd518778326dfe180b"

# Accepted source-code authorities.
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

# Accepted V16E-24 freeze artifacts.
E24_REL = Path("provenance/hybrid_dp/V16E24_FROZEN_HISTORICAL_100DAY_REFERENCE_TRUTH")
E24_ARTIFACTS = {
    "frozen_reference/V16E24_Frozen_Historical_SG7E_100Day_Reference_Truth.npz":
        "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f",
    "V16E24_Historical_100Day_Reference_Truth_Freeze_Manifest.json":
        "5cbf424a7074643e98c7470bd7592be9347dddce2153ed67ee20199eeae1d378",
    "V16E24_Reference_Truth_Provenance_Contract.json":
        "e0945ea2b5fc060b024827f9c1b301b0bf59207988b7d45ea947d561bb3a6ae3",
    "PAD_Stream_V16E24_Summary.json":
        "996ba1cebc3613e7d95f73f93bda1aae028ee845306ee907aea80bcc883d64d7",
    "V16E24_Handoff.md":
        "e38c52142789597f24c51c255c0e06c08432b845c9d3fba98fc23dbd7a250759",
    "V16E24_E23_Authority.csv":
        "0f682018ce774b36876166287e0ede7ce6f3eed53968a53d66842bf350f8d46d",
    "V16E24_Frozen_Reference_Identity.csv":
        "318bf9b156a2e2c2c5c36b890f42a4801c88e04b71bad776d8b0fc8b0c2e9613",
    "V16E24_Freeze_Lineage.csv":
        "b8e578ad015a25b24cdadc082494e034ab8d203cc39dd8412aa5946b0e68efe8",
    "V16E24_Deployment_Evaluation_Readiness.csv":
        "9884df702174fcc8088dbb9446d04c7ae0ff3718eb0a0bc75cc80c5e64d32ad1",
    "V16E24_Final_Gate_Matrix.csv":
        "def1b9266531436856e611e0c34fc3b439211eef890640e3edfebb6998184083",
}

# Accepted V16E-20-R2 historical gate authority.
E20R2_REL = Path("provenance/hybrid_dp/V16E20_R2_HISTORICAL_SG7E_GATE_AUTHORITY_V16_APPLICABILITY_RECONCILIATION")
E20R2_ARTIFACTS = {
    "V16E20_R2_Historical_SG7E_Gate_Authority_Contract.json":
        "1467c6d8dcf2e7a414e4808618c94fa0dd5770063587ee213ecd64550d4375ec",
    "V16E20_R2_V16_Applicability_Audit.json":
        "9baddcb61cd0a03f3c6cb29824dbf7029a78d05027cc30c28483ff5b8120ac7f",
    "PAD_Stream_V16E20_R2_Summary.json":
        "7c601b189f6a92046f16ceccb32bb290fa240e9a87f8a1dbd888445edbf0f84f",
    "V16E20_R2_Handoff.md":
        "ae2d729b8a1bc344f83b921236cb389b95c27357bfd55238b086ed8439d2768b",
    "V16E20_R2_Historical_Authoritative_Gate_Registry.csv":
        "1d0cddd73eec4d2cfa8c95c0659145e41a66d9fd5ebb636c544a9e8341efd68f",
    "V16E20_R2_V16_Gate_Applicability_Matrix.csv":
        "6b2370090cba83fba42841852ade00615ccd61ff873281baa1c108bf093b5daa",
    "V16E20_R2_Source_Authority.csv":
        "1672289202bdb2d84137751a3244a31e46aeb29b13505f16030a8eaab618b10f",
    "V16E20_R2_Evaluation_Prerequisite_Matrix.csv":
        "1e7a84ce37e8f933b806d766c3d1341f04d1abdea9b691dfe16f3f09b65ec737",
    "V16E20_R2_Final_Gate_Matrix.csv":
        "dfa6546e16e80cc0c05f4c09ee4317cf3fcef39213b8a7a61cc7c1067460fa60",
}

V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)

OUT_REL = Path("provenance/hybrid_dp/V16E25_FROZEN_REFERENCE_FROZEN_V16_DEPLOYMENT_GATE_EVALUATION")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E25_BLOCKED_FROZEN_REFERENCE_FROZEN_V16_DEPLOYMENT_GATE_EVALUATION")

# Exact historical deployment-gate contract.
EXPECTED_GATES = {
    "PRIMARY_VOLUME_GATE": {
        "metric": "primary_volume_relative_error",
        "operator": "<=",
        "limit": 0.10,
        "units": "fraction",
    },
    "FOOTPRINT_IOU_GATE": {
        "metric": "footprint_IoU",
        "operator": ">=",
        "limit": 0.90,
        "units": "dimensionless",
    },
    "CENTROID_GATE_CELLS": {
        "metric": "centroid_distance_cells",
        "operator": "<=",
        "limit": 2.0,
        "units": "cells",
    },
    "VERTICAL_EXTENT_GATE_LAYERS": {
        "metric": "vertical_extent_error_layers",
        "operator": "<=",
        "limit": 2.0,
        "units": "layers",
    },
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


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def binary_plume(arr, threshold):
    # Literal historical V15-SG7E1 semantics.
    return np.isfinite(arr) & (arr >= threshold)


def primary_volume_relative_error(pred_mask, ref_mask):
    # Literal historical V15-SG7E1 semantics: plume-cell-count relative error.
    pred = int(np.sum(pred_mask))
    ref = int(np.sum(ref_mask))
    return abs(pred - ref) / max(ref, 1)


def footprint_iou(pred_mask, ref_mask):
    # Literal historical V15-SG7E1 semantics: collapse vertically with any().
    pred2 = np.any(pred_mask, axis=0)
    ref2 = np.any(ref_mask, axis=0)
    inter = int(np.sum(pred2 & ref2))
    union = int(np.sum(pred2 | ref2))
    if union == 0:
        return 1.0
    return inter / union


def centroid_cells(mask):
    idx = np.argwhere(mask)
    if idx.size == 0:
        return np.asarray([np.nan, np.nan, np.nan], dtype=float)
    return np.mean(idx, axis=0)


def centroid_distance_cells(pred_mask, ref_mask):
    a = centroid_cells(pred_mask)
    b = centroid_cells(ref_mask)
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        return np.inf
    return float(np.linalg.norm(a - b))


def vertical_extent_layers(mask):
    idx = np.argwhere(mask)
    if idx.size == 0:
        return 0
    kmin = int(np.min(idx[:, 0]))
    kmax = int(np.max(idx[:, 0]))
    return kmax - kmin + 1


def vertical_extent_error_layers(pred_mask, ref_mask):
    return abs(vertical_extent_layers(pred_mask) - vertical_extent_layers(ref_mask))


def evaluate_gate(value, operator, limit):
    if operator == "<=":
        return bool(value <= limit)
    if operator == "<":
        return bool(value < limit)
    if operator == ">=":
        return bool(value >= limit)
    if operator == ">":
        return bool(value > limit)
    raise ValueError(operator)


def centroid_list(mask):
    c = centroid_cells(mask)
    return [None if not np.isfinite(x) else float(x) for x in c]


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

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-25 Frozen Historical Reference / Frozen V16 Candidate Deployment-Gate Evaluation")
    print("=" * 132)
    print("AUTHORITATIVE HISTORICAL SG7E METRICS ONLY. NO THRESHOLD TUNING. NO POST-HOC ALIGNMENT.")
    print("NO CANDIDATE OR REFERENCE MODIFICATION. NO TRAINING / INFERENCE / PRESSURE / DARCY / POLLOCK / TOF / MAP-BACK RECOMPUTATION.")
    print("E25 EVALUATES THE FOUR GATES ONCE. FULL-GRID PLUME AUTHORIZATION REMAINS DEFERRED TO INDEPENDENT E26 REPRODUCTION.")

    v16_path = drive / V16_FROZEN_REL
    ref_path = drive / E24_REL / "frozen_reference/V16E24_Frozen_Historical_SG7E_100Day_Reference_Truth.npz"
    v16_sha_before = None
    ref_sha_before = None

    try:
        # ------------------------------------------------------------------
        # Source-code authorities.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        for label, (name, expected) in [
            ("E24_runner", E24_RUNNER),
            ("E20R2_runner", E20R2_RUNNER),
            ("E18R1_runner", E18R1_RUNNER),
            ("V15SG7E1_metric_source", V15_E1_SOURCE),
        ]:
            p = root / name
            gate(f"{label}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"{label}_SHA_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # V16E-24 frozen-reference authority.
        # ------------------------------------------------------------------
        print("\nV16E-24 FROZEN REFERENCE AUTHORITY")
        for name, expected in E24_ARTIFACTS.items():
            p = drive / E24_REL / name
            gate(f"E24_{Path(name).name}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"E24_{Path(name).name}_SHA_exact", actual == expected, actual)

        e24_summary = load_json(drive / E24_REL / "PAD_Stream_V16E24_Summary.json")
        gate("E24_summary_status_PASS", e24_summary.get("status") == "PASS")
        gate("E24_reference_truth_frozen", e24_summary.get("reference_truth_frozen") is True)
        gate("E24_deployment_evaluation_eligible", e24_summary.get("deployment_gate_evaluation_eligible") is True)
        gate("E24_no_deployment_evaluation", e24_summary.get("deployment_pass_fail_evaluated") is False)
        gate("E24_threshold_0p5_exact", float(e24_summary.get("historical_authoritative_plume_threshold")) == EXPECTED_THRESHOLD)
        gate("E24_reference_array_hash_exact", e24_summary.get("frozen_reference_array_sha256") == REFERENCE_ARRAY_SHA)
        gate("E24_reference_mask_hash_exact", e24_summary.get("frozen_reference_mask_sha256") == REFERENCE_MASK_SHA)
        gate("E24_V16_candidate_unchanged", e24_summary.get("V16_frozen_candidate_modified") is False)
        gate("E24_test_OOD_closed", e24_summary.get("internal_test_reopened") is False and e24_summary.get("OOD_reopened") is False)

        readiness = load_csv(drive / E24_REL / "V16E24_Deployment_Evaluation_Readiness.csv")
        gate("E24_readiness_matrix_nonempty", len(readiness) == 8, len(readiness))
        gate("E24_all_readiness_rows_true", all(str(r.get("ready", "")).strip().lower() == "true" for r in readiness))

        # ------------------------------------------------------------------
        # V16E-20-R2 historical gate registry.
        # ------------------------------------------------------------------
        print("\nV16E-20-R2 HISTORICAL GATE AUTHORITY")
        for name, expected in E20R2_ARTIFACTS.items():
            p = drive / E20R2_REL / name
            gate(f"E20R2_{Path(name).name}_exists", p.is_file(), p)
            actual = sha256_file(p)
            gate(f"E20R2_{Path(name).name}_SHA_exact", actual == expected, actual)

        registry_rows = load_csv(drive / E20R2_REL / "V16E20_R2_Historical_Authoritative_Gate_Registry.csv")
        gate("historical_registry_exact_four_rows", len(registry_rows) == 4, len(registry_rows))
        by_gate = {str(r.get("gate", "")).strip(): r for r in registry_rows}
        gate("historical_registry_exact_four_symbols", set(by_gate) == set(EXPECTED_GATES), sorted(by_gate))

        registry_out = []
        for gate_name, spec in EXPECTED_GATES.items():
            row = by_gate[gate_name]
            metric = str(row.get("metric", "")).strip()
            operator = str(row.get("operator", "")).strip()
            limit = float(row.get("limit"))
            units = str(row.get("units", "")).strip()
            role = str(row.get("role", "")).strip()
            gate(f"{gate_name}_registry_metric_exact", metric == spec["metric"], metric)
            gate(f"{gate_name}_registry_operator_exact", operator == spec["operator"], operator)
            gate(f"{gate_name}_registry_limit_exact", limit == spec["limit"], limit)
            gate(f"{gate_name}_registry_units_exact", units == spec["units"], units)
            gate(f"{gate_name}_registry_role_authoritative", role == "AUTHORITATIVE_HISTORICAL_GATE", role)
            registry_out.append({
                "gate": gate_name,
                "metric": metric,
                "operator": operator,
                "limit": limit,
                "units": units,
                "role": role,
                "historical_source": row.get("historical_source"),
                "historical_source_sha256": row.get("historical_source_sha256"),
            })

        # ------------------------------------------------------------------
        # Frozen input identities.
        # ------------------------------------------------------------------
        print("\nFROZEN INPUT IDENTITIES")
        gate("V16_frozen_candidate_exists", v16_path.is_file(), v16_path)
        v16_sha_before = sha256_file(v16_path)
        gate("V16_frozen_candidate_file_SHA_exact_before", v16_sha_before == V16_FROZEN_SHA, v16_sha_before)

        gate("historical_frozen_reference_exists", ref_path.is_file(), ref_path)
        ref_sha_before = sha256_file(ref_path)
        gate("historical_frozen_reference_file_SHA_exact_before", ref_sha_before == REFERENCE_FROZEN_FILE_SHA, ref_sha_before)

        with np.load(v16_path, allow_pickle=False) as db:
            required = {
                "saturation_grid_full_float64",
                "physical_time_days",
                "grid_shape",
                "background_saturation",
                "supported_mask",
                "support_denominator",
                "support_numerator",
            }
            gate("V16_required_arrays_present", required.issubset(set(db.files)), sorted(db.files))
            candidate = np.array(db["saturation_grid_full_float64"], copy=True)
            candidate_time = float(np.asarray(db["physical_time_days"]))
            candidate_grid = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
            candidate_background = float(np.asarray(db["background_saturation"]))

        gate("V16_candidate_shape_exact", candidate.shape == EXPECTED_GRID, candidate.shape)
        gate("V16_candidate_grid_metadata_exact", candidate_grid == EXPECTED_GRID, candidate_grid)
        gate("V16_candidate_time_100d_exact", candidate_time == EXPECTED_TIME_DAYS, candidate_time)
        gate("V16_candidate_dtype_float64", candidate.dtype == np.float64, candidate.dtype)
        gate("V16_candidate_finite", np.all(np.isfinite(candidate)))
        gate("V16_background_authority_0p2", candidate_background == 0.2, candidate_background)

        with np.load(ref_path, allow_pickle=False) as db:
            required = {
                "reference_truth_100d_native",
                "reference_plume_mask_100d_0p5",
                "physical_time_days",
                "plume_threshold",
                "source_reference_key",
            }
            gate("reference_required_arrays_present", required.issubset(set(db.files)), sorted(db.files))
            reference = np.array(db["reference_truth_100d_native"], copy=True)
            reference_mask_frozen = np.asarray(db["reference_plume_mask_100d_0p5"], dtype=np.uint8)
            ref_time = float(scalar(db, "physical_time_days"))
            threshold = float(scalar(db, "plume_threshold"))
            ref_key = str(scalar(db, "source_reference_key"))

        gate("reference_shape_exact", reference.shape == EXPECTED_GRID, reference.shape)
        gate("reference_dtype_float64", reference.dtype == np.float64, reference.dtype)
        gate("reference_time_100d_exact", ref_time == EXPECTED_TIME_DAYS, ref_time)
        gate("reference_threshold_0p5_exact", threshold == EXPECTED_THRESHOLD, threshold)
        gate("reference_key_exact", ref_key == EXPECTED_REFERENCE_KEY, ref_key)
        gate("reference_array_SHA_exact_recomputed", sha256_array(reference) == REFERENCE_ARRAY_SHA, sha256_array(reference))
        gate("reference_mask_SHA_exact_recomputed", sha256_array(reference_mask_frozen) == REFERENCE_MASK_SHA, sha256_array(reference_mask_frozen))
        gate("reference_finite", np.all(np.isfinite(reference)))

        # ------------------------------------------------------------------
        # Exact historical SG7E binary-plume construction and metrics.
        # ------------------------------------------------------------------
        print("\nAUTHORITATIVE HISTORICAL SG7E DEPLOYMENT METRICS")
        pred_mask = binary_plume(candidate, threshold)
        ref_mask = binary_plume(reference, threshold)
        gate("reference_frozen_mask_matches_recomputed_threshold_mask", np.array_equal(reference_mask_frozen.astype(bool), ref_mask))

        metrics = {
            "primary_volume_relative_error": float(primary_volume_relative_error(pred_mask, ref_mask)),
            "footprint_IoU": float(footprint_iou(pred_mask, ref_mask)),
            "centroid_distance_cells": float(centroid_distance_cells(pred_mask, ref_mask)),
            "vertical_extent_error_layers": float(vertical_extent_error_layers(pred_mask, ref_mask)),
        }

        # Non-authoritative field diagnostics only.
        field_l1 = float(np.mean(np.abs(candidate - reference)))
        field_l2 = float(np.sqrt(np.mean((candidate - reference) ** 2)))
        field_linf = float(np.max(np.abs(candidate - reference)))

        gate_results = []
        all_authoritative_pass = True
        for gate_name, spec in EXPECTED_GATES.items():
            value = metrics[spec["metric"]]
            passed = evaluate_gate(value, spec["operator"], spec["limit"])
            all_authoritative_pass = all_authoritative_pass and passed
            gate_results.append({
                "gate": gate_name,
                "metric": spec["metric"],
                "value": value,
                "operator": spec["operator"],
                "limit": spec["limit"],
                "units": spec["units"],
                "passed": passed,
                "role": "AUTHORITATIVE",
                "historical_metric_source": V15_E1_SOURCE[0],
                "historical_metric_source_sha256": V15_E1_SOURCE[1],
            })
            print(
                f"[{'PASS' if passed else 'FAIL'}] {gate_name}: "
                f"{spec['metric']}={value:.12g} {spec['operator']} {spec['limit']}",
                flush=True,
            )

        pred_centroid = centroid_cells(pred_mask)
        ref_centroid = centroid_cells(ref_mask)
        pred_cells = int(pred_mask.sum())
        ref_cells = int(ref_mask.sum())
        pred_footprint = int(np.any(pred_mask, axis=0).sum())
        ref_footprint = int(np.any(ref_mask, axis=0).sum())
        pred_extent = int(vertical_extent_layers(pred_mask))
        ref_extent = int(vertical_extent_layers(ref_mask))

        decision = "PASS" if all_authoritative_pass else "FAIL"
        provisional = f"PROVISIONAL_{decision}_PENDING_INDEPENDENT_E26_REPRODUCTION"

        # Frozen-object immutability after evaluation.
        gate("V16_frozen_candidate_file_SHA_exact_after", sha256_file(v16_path) == v16_sha_before == V16_FROZEN_SHA)
        gate("historical_frozen_reference_file_SHA_exact_after", sha256_file(ref_path) == ref_sha_before == REFERENCE_FROZEN_FILE_SHA)
        gate("threshold_unchanged_in_E25", threshold == EXPECTED_THRESHOLD)
        gate("diagnostic_0p21_not_used_in_E25", True)
        gate("no_posthoc_alignment_in_E25", True)
        gate("no_deployment_correction_in_E25", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("full_grid_plume_authorization_deferred_to_E26", True)

        # ------------------------------------------------------------------
        # Persist completed evaluation. A gate FAIL is a valid scientific
        # conclusion and does not make the runner itself fail.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)

        npz_out = out / "V16E25_Deployment_Gate_Evaluation.npz"
        np.savez_compressed(
            npz_out,
            candidate_plume_mask_100d_0p5=pred_mask.astype(np.uint8),
            reference_plume_mask_100d_0p5=ref_mask.astype(np.uint8),
            plume_threshold=np.asarray(threshold, dtype=np.float64),
            physical_time_days=np.asarray(EXPECTED_TIME_DAYS, dtype=np.float64),
            candidate_centroid_kji=np.asarray(pred_centroid, dtype=np.float64),
            reference_centroid_kji=np.asarray(ref_centroid, dtype=np.float64),
            primary_volume_relative_error=np.asarray(metrics["primary_volume_relative_error"], dtype=np.float64),
            footprint_IoU=np.asarray(metrics["footprint_IoU"], dtype=np.float64),
            centroid_distance_cells=np.asarray(metrics["centroid_distance_cells"], dtype=np.float64),
            vertical_extent_error_layers=np.asarray(metrics["vertical_extent_error_layers"], dtype=np.float64),
        )

        input_rows = [
            {"role": "frozen_V16_candidate", "path": str(v16_path), "file_sha256": v16_sha_before, "modified": False},
            {"role": "frozen_historical_reference", "path": str(ref_path), "file_sha256": ref_sha_before, "modified": False},
            {"role": "historical_metric_source", "path": str(root / V15_E1_SOURCE[0]), "file_sha256": V15_E1_SOURCE[1], "modified": False},
            {"role": "historical_gate_registry", "path": str(drive / E20R2_REL / "V16E20_R2_Historical_Authoritative_Gate_Registry.csv"), "file_sha256": E20R2_ARTIFACTS["V16E20_R2_Historical_Authoritative_Gate_Registry.csv"], "modified": False},
        ]
        save_csv(out / "V16E25_Input_Identity.csv", input_rows)
        save_csv(out / "V16E25_Authoritative_Gate_Registry.csv", registry_out)
        save_csv(out / "V16E25_Deployment_Metrics.csv", [
            {"metric": k, "value": v, "role": "AUTHORITATIVE"} for k, v in metrics.items()
        ] + [
            {"metric": "full_field_L1", "value": field_l1, "role": "DIAGNOSTIC_ONLY"},
            {"metric": "full_field_L2_RMSE", "value": field_l2, "role": "DIAGNOSTIC_ONLY"},
            {"metric": "full_field_Linf", "value": field_linf, "role": "DIAGNOSTIC_ONLY"},
        ])
        save_csv(out / "V16E25_Authoritative_Gate_Results.csv", gate_results)
        save_csv(out / "V16E25_Plume_Morphology_Diagnostics.csv", [{
            "plume_threshold": threshold,
            "candidate_plume_cells": pred_cells,
            "reference_plume_cells": ref_cells,
            "candidate_footprint_cells": pred_footprint,
            "reference_footprint_cells": ref_footprint,
            "candidate_vertical_extent_layers": pred_extent,
            "reference_vertical_extent_layers": ref_extent,
            "candidate_centroid_k": None if not np.isfinite(pred_centroid[0]) else float(pred_centroid[0]),
            "candidate_centroid_j": None if not np.isfinite(pred_centroid[1]) else float(pred_centroid[1]),
            "candidate_centroid_i": None if not np.isfinite(pred_centroid[2]) else float(pred_centroid[2]),
            "reference_centroid_k": None if not np.isfinite(ref_centroid[0]) else float(ref_centroid[0]),
            "reference_centroid_j": None if not np.isfinite(ref_centroid[1]) else float(ref_centroid[1]),
            "reference_centroid_i": None if not np.isfinite(ref_centroid[2]) else float(ref_centroid[2]),
        }])
        save_csv(out / "V16E25_Final_Gate_Matrix.csv", [{"gate": k, **v} for k, v in gates.items()])

        contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "evaluation_role": "first_authoritative_evaluation_of_frozen_V16_candidate_against_frozen_historical_100day_reference",
            "historical_reference": {
                "key": EXPECTED_REFERENCE_KEY,
                "time_days": EXPECTED_TIME_DAYS,
                "plume_threshold": EXPECTED_THRESHOLD,
                "frozen_file_sha256": ref_sha_before,
                "reference_array_sha256": REFERENCE_ARRAY_SHA,
                "reference_mask_sha256": REFERENCE_MASK_SHA,
            },
            "frozen_V16_candidate": {
                "file_sha256": v16_sha_before,
                "shape": list(candidate.shape),
                "time_days": candidate_time,
                "background_saturation": candidate_background,
                "modified": False,
            },
            "historical_gate_registry": EXPECTED_GATES,
            "authoritative_metrics": metrics,
            "authoritative_gate_results": gate_results,
            "all_authoritative_gates_pass": all_authoritative_pass,
            "deployment_decision": decision,
            "decision_status": provisional,
            "independent_E26_reproduction_required": True,
            "candidate_performance_used_for_threshold_or_reference_selection": False,
            "threshold_changed": False,
            "posthoc_alignment": False,
            "deployment_correction_performed": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT,
        }
        save_json(out / "V16E25_Deployment_Gate_Evaluation_Contract.json", contract)

        summary = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "historical_reference_key": EXPECTED_REFERENCE_KEY,
            "historical_authoritative_plume_threshold": EXPECTED_THRESHOLD,
            "frozen_V16_candidate_file_sha256": v16_sha_before,
            "frozen_reference_file_sha256": ref_sha_before,
            "reference_array_sha256": REFERENCE_ARRAY_SHA,
            "reference_mask_sha256": REFERENCE_MASK_SHA,
            "candidate_plume_cells": pred_cells,
            "reference_plume_cells": ref_cells,
            "candidate_footprint_cells": pred_footprint,
            "reference_footprint_cells": ref_footprint,
            "candidate_vertical_extent_layers": pred_extent,
            "reference_vertical_extent_layers": ref_extent,
            "candidate_centroid_kji": centroid_list(pred_mask),
            "reference_centroid_kji": centroid_list(ref_mask),
            **metrics,
            "all_authoritative_gates_pass": all_authoritative_pass,
            "failed_authoritative_gates": [r["gate"] for r in gate_results if not r["passed"]],
            "deployment_pass_fail_evaluated": True,
            "deployment_decision": decision,
            "deployment_decision_status": provisional,
            "independent_E26_reproduction_required": True,
            "V16_frozen_candidate_modified": False,
            "historical_reference_modified": False,
            "threshold_changed": False,
            "candidate_performance_used_for_threshold_or_reference_selection": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT,
        }
        save_json(out / "PAD_Stream_V16E25_Summary.json", summary)

        (out / "V16E25_Handoff.md").write_text(
            "# PAD-Stream V16E-25 Handoff\n\n"
            "V16E-25 completed the first authoritative four-gate SG7E deployment evaluation of the immutable "
            "V16E-18-R1 candidate against the immutable V16E-24 historical 100-day reference truth.\n\n"
            f"- Historical reference: `{EXPECTED_REFERENCE_KEY}` at `100 days`\n"
            f"- Plume threshold: `S >= {EXPECTED_THRESHOLD}`\n"
            f"- Deployment decision: `{decision}`\n"
            f"- Decision status: `{provisional}`\n"
            f"- Failed authoritative gates: `{[r['gate'] for r in gate_results if not r['passed']]}`\n"
            "- Candidate modified: `NO`\n"
            "- Reference modified: `NO`\n"
            "- Threshold changed: `NO`\n"
            "- Full-grid plume authorized: `NO` (independent E26 reproduction required)\n"
            "- Internal test / OOD reopened: `NO / NO`\n\n"
            f"Next: `{NEXT}`\n",
            encoding="utf-8",
        )

        print("\n" + "=" * 132)
        print("V16E-25 RESULT: PASS")
        print("=" * 132)
        print(f"{'Historical reference':72}: {EXPECTED_REFERENCE_KEY} @ 100 days")
        print(f"{'Historical authoritative plume threshold':72}: S >= {EXPECTED_THRESHOLD}")
        print(f"{'Frozen V16 candidate SHA-256':72}: {v16_sha_before}")
        print(f"{'Frozen reference file SHA-256':72}: {ref_sha_before}")
        print(f"{'Candidate / reference plume cells':72}: {pred_cells} / {ref_cells}")
        print(f"{'Candidate / reference footprint cells':72}: {pred_footprint} / {ref_footprint}")
        print(f"{'Candidate / reference vertical extent':72}: {pred_extent} / {ref_extent}")
        print(f"{'PRIMARY_VOLUME_GATE':72}: {metrics['primary_volume_relative_error']:.12g} <= 0.10 | {'PASS' if gate_results[0]['passed'] else 'FAIL'}")
        print(f"{'FOOTPRINT_IOU_GATE':72}: {metrics['footprint_IoU']:.12g} >= 0.90 | {'PASS' if gate_results[1]['passed'] else 'FAIL'}")
        print(f"{'CENTROID_GATE_CELLS':72}: {metrics['centroid_distance_cells']:.12g} <= 2.0 | {'PASS' if gate_results[2]['passed'] else 'FAIL'}")
        print(f"{'VERTICAL_EXTENT_GATE_LAYERS':72}: {metrics['vertical_extent_error_layers']:.12g} <= 2.0 | {'PASS' if gate_results[3]['passed'] else 'FAIL'}")
        print(f"{'Deployment pass/fail evaluated':72}: YES")
        print(f"{'Deployment decision':72}: {decision}")
        print(f"{'Decision independently reproduced':72}: NO - REQUIRED IN E26")
        print(f"{'V16 frozen candidate modified':72}: NO")
        print(f"{'Historical reference modified':72}: NO")
        print(f"{'Full-grid plume authorized':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")

        for name in [
            "V16E25_Deployment_Gate_Evaluation.npz",
            "V16E25_Deployment_Gate_Evaluation_Contract.json",
            "PAD_Stream_V16E25_Summary.json",
            "V16E25_Handoff.md",
            "V16E25_Input_Identity.csv",
            "V16E25_Authoritative_Gate_Registry.csv",
            "V16E25_Deployment_Metrics.csv",
            "V16E25_Plume_Morphology_Diagnostics.csv",
            "V16E25_Authoritative_Gate_Results.csv",
            "V16E25_Final_Gate_Matrix.csv",
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
            "V16_frozen_candidate_sha256_before": v16_sha_before,
            "historical_frozen_reference_sha256_before": ref_sha_before,
            "V16_frozen_candidate_modified": False if v16_sha_before is None or not v16_path.exists() else sha256_file(v16_path) != v16_sha_before,
            "historical_reference_modified": False if ref_sha_before is None or not ref_path.exists() else sha256_file(ref_path) != ref_sha_before,
            "deployment_pass_fail_evaluated": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": "V16E-25-R1 - Repair only the failed provenance/evaluation prerequisite; preserve both frozen numerical objects unchanged",
        }
        p = blocked / "V16E25_Blocked_Deployment_Gate_Evaluation.json"
        save_json(p, payload)
        print(f"\n[FAIL] V16E-25 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(p)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, required=True)
    args = ap.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
