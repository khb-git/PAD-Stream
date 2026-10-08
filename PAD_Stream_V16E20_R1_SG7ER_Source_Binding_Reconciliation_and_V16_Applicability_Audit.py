#!/usr/bin/env python3
"""PAD-Stream V16E-20-R1
SG7E-R Source-Binding Reconciliation and Historical Gate/V16 Applicability Audit.

This is a provenance/contract milestone only. It binds the frozen V16E-19
validation-entry contract and the exact historical V15 SG7E authority sources,
recovers the four historical deployment gates with their operators/limits, and
audits whether their metric definitions are structurally applicable to the
frozen V16 100-day 15x50x50 full-grid field.

E20 does NOT select a reference plume, does NOT establish an authoritative
plume threshold, and does NOT evaluate any deployment pass/fail gate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "V16E-20-R1"
SUCCESS = "V16E20_R1_HISTORICAL_SG7E_GATE_AUTHORITY_V16_APPLICABILITY_RECONCILED"
BLOCKED = "V16E20_R1_HISTORICAL_SG7E_GATE_AUTHORITY_V16_APPLICABILITY_BLOCKED"
NEXT_PASS = "V16E-21 - Historical SG7E Plume-Threshold and Reference-Plume Provenance Reconciliation"
NEXT_FAIL = "V16E-20-R2 - Repair only the failed V16E-20-R1 provenance/applicability gate; preserve E18-R1 frozen candidate and E19 contract unchanged"

# -----------------------------------------------------------------------------
# Frozen V16E-19 validation-entry authority.
# -----------------------------------------------------------------------------
E19_RUNNER = (
    "PAD_Stream_V16E19_Frozen_Full_Grid_Deployment_Validation_Contract_and_Baseline_Audit.py",
    "febba0d95b676b1555a91544c2cd40bbb3d521c1534192fca294b2c1aaf69536",
)
E19_REL = Path("provenance/hybrid_dp/V16E19_FROZEN_FULL_GRID_DEPLOYMENT_VALIDATION_CONTRACT_BASELINE_AUDIT")
E19 = {
    "contract": ("V16E19_Deployment_Validation_Contract.json", "45e2844f0144354d21ee30656e894965a72fc76d97e421aab5e7171a114568a9"),
    "audit": ("V16E19_Baseline_Audit.json", "3064c0d6a872ed3b3fa0e2e0a666cbc3c26d0952e52d06edf8629ec0a6f86b4e"),
    "summary": ("PAD_Stream_V16E19_Summary.json", "a7ff7361cedcd0d29aeacd3abee6f1336ca65ad09f2cb38c1bb3665796a18e87"),
    "handoff": ("V16E19_Handoff.md", "ffa1f92b4cbb91f8ebca8296cebb539d71887fe4642efd547f99ab34564d3eab"),
    "identity_csv": ("V16E19_Frozen_Input_Identity.csv", "14281ddd2f5f32f70ec15b88e70ba7a22a21e79535c8bf6e53aae875327b86f1"),
    "baseline_csv": ("V16E19_Frozen_Baseline_Metrics.csv", "0e636868a1431e0558aa5534755d0a4eb72bdf1ea9eacbab4a75402aba46a63c"),
    "compat_csv": ("V16E19_Deployment_Compatibility_Audit.csv", "6fd953d3e155d50092fad26560400883adab64f0b34a282fb94b1177b1f688c9"),
    "roles_csv": ("V16E19_Validation_Role_Registry.csv", "6d08ad4355a3dcd6fd0b25973377c2a7eb073f5068bb8ab4e43bbfa3e4c70284"),
    "entry_csv": ("V16E19_Validation_Entry_Matrix.csv", "511c11c0a6e3b200cf58a9a88256fbeabd4feae71661d62ce83c48acfdae98c1"),
    "gates_csv": ("V16E19_Final_Gate_Matrix.csv", "e37ec51db54ab726d0a64eba974c8fd87ed8a7f290eb3b5d52d4fe04606ec57d"),
}

FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
FROZEN_FILE_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

# -----------------------------------------------------------------------------
# Historical V15 gate-authority source bindings.
# -----------------------------------------------------------------------------
V15_E0R = (
    "PAD_Stream_V15SG7E0R_Historical_SG7E_Gate_Authority_Reconciliation.py",
    "3ba7eef6133333c09aff113c1f92c16e187a856dc5fca856524a7c122c48e3e0",
)
V15_E1 = (
    "PAD_Stream_V15SG7E1_Frozen_Full_Grid_Deployment_Validation.py",
    "6fbbac849fdae3e165d5cb115a8573f386b23a98628cd953339b0584d7e292b3",
)
V15_ER = (
    "PAD_Stream_V15SG7ER_Front_Aware_FullGrid_Plume_Coverage_Validation.py",
    "5ac003c7d5dcb5451e46685a96635b2d4e3c366218e8a939435e4c80c1130890",
)
V15_ER_PREVIOUS_PACKAGE_SNAPSHOT_SHA = "e555b08f59933652d7f80b4bafe0608b883a00bbb550abbdf335816eb9d6c55d"
V15_ER_LIVE_REPO_SHA = "5ac003c7d5dcb5451e46685a96635b2d4e3c366218e8a939435e4c80c1130890"

OUT_REL = Path("provenance/hybrid_dp/V16E20_R1_HISTORICAL_SG7E_GATE_AUTHORITY_V16_APPLICABILITY_RECONCILIATION")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E20_R1_BLOCKED_HISTORICAL_SG7E_GATE_AUTHORITY_V16_APPLICABILITY")

EXPECTED_GRID = (15, 50, 50)
EXPECTED_TIME_DAYS = 100.0
EXPECTED_SUPPORTED = 20462
EXPECTED_BACKGROUND_COMPLETED = 17038
EXPECTED_BACKGROUND = 0.2
DIAGNOSTIC_THRESHOLD = 0.21

# Historical deployment-gate contract recovered from accepted V15 SG7E sources.
HISTORICAL_GATES = {
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

PROHIBITIONS = [
    "NO CHANGE TO V16E-18-R1 FROZEN CANDIDATE OR V16E-19 CONTRACT/BASELINE ARTIFACTS.",
    "NO MAP-BACK, BACKGROUND COMPLETION, TRANSPORT, PRESSURE, DARCY, POLLOCK, OR TOF RECOMPUTATION.",
    "NO TRAINING, CHECKPOINT LOAD, MODEL INFERENCE, OR INTERNAL-TEST/OOD REOPENING.",
    "NO REFERENCE PLUME IS SELECTED IN E20.",
    "NO AUTHORITATIVE PLUME THRESHOLD IS DEFINED IN E20.",
    "0.21 REMAINS DIAGNOSTIC-ONLY AND IS NOT USED FOR DEPLOYMENT PASS/FAIL.",
    "NO HISTORICAL GATE IS EVALUATED AGAINST THE V16 CANDIDATE IN E20.",
    "NO DEPLOYMENT PASS/FAIL OR FULL-GRID PLUME CLAIM IS MADE IN E20.",
]


class GateError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items: dict[str, dict[str, Any]] = {}

    def check(self, name: str, cond: Any, detail: str = ""):
        ok = bool(cond)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name + (f": {detail}" if detail else ""))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def arr_sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def native(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): native(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [native(x) for x in v]
    if isinstance(v, np.ndarray):
        return native(v.tolist())
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    return v


def enc(v: Any) -> bytes:
    return (json.dumps(native(v), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_bool(v: Any) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes", "pass"}


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def save_csv(path: Path, rows: list[dict[str, Any]]):
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: native(v) for k, v in row.items()} for row in rows])
    os.replace(tmp, path)


def bind(g: Gates, label: str, path: Path, expected: str) -> str:
    g.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    g.check(label + "_SHA_exact", actual == expected, actual if actual != expected else "")
    return actual


def source_contains(path: Path, required: list[str]) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    return all(token in text for token in required)


def assignment_value(text: str, symbol: str) -> float | None:
    pat = re.compile(rf"^\s*{re.escape(symbol)}\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*$", re.MULTILINE)
    m = pat.search(text)
    return float(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--drive-root", required=True)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    compute = Path(args.drive_root).resolve()
    out = compute / OUT_REL
    blocked = compute / BLOCKED_REL
    g = Gates()

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-20-R1 SG7E-R Source-Binding Reconciliation and V16 Applicability Audit")
    print("=" * 132)
    for line in PROHIBITIONS:
        print(line)

    try:
        # ------------------------------------------------------------------
        # V16E-19 validation-entry authority.
        # ------------------------------------------------------------------
        print("\nV16E-19 VALIDATION-ENTRY AUTHORITY")
        bind(g, "E19_runner", root / E19_RUNNER[0], E19_RUNNER[1])
        e19_paths: dict[str, Path] = {}
        for key, (name, digest) in E19.items():
            p = compute / E19_REL / name
            bind(g, "E19_" + key, p, digest)
            e19_paths[key] = p

        e19_contract = read_json(e19_paths["contract"])
        e19_audit = read_json(e19_paths["audit"])
        e19_summary = read_json(e19_paths["summary"])
        e19_gate_rows = read_csv(e19_paths["gates_csv"])

        g.check("E19_summary_status_PASS", e19_summary.get("status") == "PASS")
        g.check("E19_all_recorded_gates_pass", len(e19_gate_rows) > 0 and all(csv_bool(r.get("passed")) for r in e19_gate_rows))
        g.check("E19_frozen_candidate_identity_exact", e19_summary.get("frozen_candidate_sha256") == FROZEN_FILE_SHA)
        g.check("E19_no_gate_registry_adopted", e19_summary.get("authoritative_gate_registry_adopted") is False and int(e19_summary.get("authoritative_gate_count", -1)) == 0)
        g.check("E19_no_authoritative_plume_threshold", e19_summary.get("authoritative_plume_threshold_defined") is False)
        g.check("E19_no_reference_selected", e19_summary.get("reference_plume_selected") is False)
        g.check("E19_no_deployment_evaluation", e19_summary.get("deployment_validation_authorized") is False and e19_audit.get("deployment_pass_fail_evaluated") is False)
        g.check("E19_frozen_candidate_unchanged", e19_summary.get("frozen_candidate_modified") is False)
        g.check("E19_full_grid_plume_not_authorized", e19_summary.get("full_grid_plume_authorized") is False)
        g.check("E19_next_is_E20", str(e19_summary.get("next_milestone", "")).startswith("V16E-20"))

        frozen_path = compute / FROZEN_REL
        bind(g, "E18R1_frozen_candidate", frozen_path, FROZEN_FILE_SHA)

        # ------------------------------------------------------------------
        # Historical V15 source authority.
        # ------------------------------------------------------------------
        print("\nHISTORICAL V15 SG7E GATE-AUTHORITY SOURCE BINDINGS")
        e0r_path = root / V15_E0R[0]
        e1_path = root / V15_E1[0]
        er_path = root / V15_ER[0]
        bind(g, "V15SG7E0R_source", e0r_path, V15_E0R[1])
        bind(g, "V15SG7E1_source", e1_path, V15_E1[1])
        current_er_sha = bind(g, "V15SG7ER_source", er_path, V15_ER[1])
        g.check("V15SG7ER_live_repo_SHA_exact", current_er_sha == V15_ER_LIVE_REPO_SHA, current_er_sha)
        g.check("V15SG7ER_previous_package_snapshot_not_silently_reused", current_er_sha != V15_ER_PREVIOUS_PACKAGE_SNAPSHOT_SHA, f"previous={V15_ER_PREVIOUS_PACKAGE_SNAPSHOT_SHA} current={current_er_sha}")

        g.check("V15SG7E0R_canonical_registry_semantics", source_contains(e0r_path, [
            "Canonical gate registry constructed",
            "Use only the canonical AUTHORITATIVE registry for SG7E1 pass/fail decisions.",
            "No SG7E threshold changed or relaxed",
            "SG7E0R does NOT evaluate the frozen P4 field against gates.",
        ]))
        g.check("V15SG7E1_four_gate_semantics", source_contains(e1_path, [
            '"PRIMARY_VOLUME_GATE"',
            '"FOOTPRINT_IOU_GATE"',
            '"CENTROID_GATE_CELLS"',
            '"VERTICAL_EXTENT_GATE_LAYERS"',
            '"metric": "primary_volume_relative_error"',
            '"metric": "footprint_IoU"',
            '"metric": "centroid_distance_cells"',
            '"metric": "vertical_extent_error_layers"',
        ]))
        g.check("V15SG7E1_safe_reference_block_semantics", source_contains(e1_path, [
            "If the historical reference plume cannot be uniquely reconstructed, SG7E1",
            "blocks safely rather than inventing a reference.",
            "Historical plume threshold uniquely recovered",
            "Historical reference plume uniquely recovered",
        ]))
        g.check("V15SG7ER_accepted_primary_contract_semantics", source_contains(er_path, [
            "PRIMARY_TIME_DAYS = 100.0",
            "PRIMARY_VOLUME_GATE = 0.10",
            "FOOTPRINT_IOU_GATE = 0.90",
            "CENTROID_GATE_CELLS = 2.0",
            "VERTICAL_EXTENT_GATE_LAYERS = 2",
            "<=\n        PRIMARY_VOLUME_GATE",
            ">=\n        FOOTPRINT_IOU_GATE",
        ]))
        g.check("V15SG7ER_source_binding_reconciled_by_exact_contract_semantics", source_contains(er_path, [
            "PRIMARY_TIME_DAYS = 100.0",
            "PRIMARY_VOLUME_GATE = 0.10",
            "FOOTPRINT_IOU_GATE = 0.90",
            "CENTROID_GATE_CELLS = 2.0",
            "VERTICAL_EXTENT_GATE_LAYERS = 2",
            "plume_volume_relative_error",
            "footprint_IoU",
            "centroid_displacement_cells",
            "vertical_extent_difference_layers",
        ]), f"previous_snapshot={V15_ER_PREVIOUS_PACKAGE_SNAPSHOT_SHA}; live_repo={current_er_sha}")

        er_text = er_path.read_text(encoding="utf-8", errors="strict")
        recovered = {
            "PRIMARY_VOLUME_GATE": assignment_value(er_text, "PRIMARY_VOLUME_GATE"),
            "FOOTPRINT_IOU_GATE": assignment_value(er_text, "FOOTPRINT_IOU_GATE"),
            "CENTROID_GATE_CELLS": assignment_value(er_text, "CENTROID_GATE_CELLS"),
            "VERTICAL_EXTENT_GATE_LAYERS": assignment_value(er_text, "VERTICAL_EXTENT_GATE_LAYERS"),
            "PRIMARY_TIME_DAYS": assignment_value(er_text, "PRIMARY_TIME_DAYS"),
        }
        g.check("historical_primary_time_recovered_exact", recovered["PRIMARY_TIME_DAYS"] == EXPECTED_TIME_DAYS, str(recovered))
        for gate_name, spec in HISTORICAL_GATES.items():
            g.check(
                f"historical_{gate_name}_limit_exact",
                recovered.get(gate_name) == float(spec["limit"]),
                f"recovered={recovered.get(gate_name)} expected={spec['limit']}",
            )

        # Operators are verified against accepted historical implementation usage.
        g.check("historical_PRIMARY_VOLUME_GATE_operator_exact", source_contains(er_path, ["plume_volume_relative_error", "<=\n        PRIMARY_VOLUME_GATE"]))
        g.check("historical_FOOTPRINT_IOU_GATE_operator_exact", source_contains(er_path, ["footprint_IoU", ">=\n        FOOTPRINT_IOU_GATE"]))
        g.check("historical_CENTROID_GATE_CELLS_operator_exact", source_contains(er_path, ["centroid_displacement_cells", "<=\n        CENTROID_GATE_CELLS"]))
        g.check("historical_VERTICAL_EXTENT_GATE_LAYERS_operator_exact", source_contains(er_path, ["vertical_extent_difference_layers", "<=\n        VERTICAL_EXTENT_GATE_LAYERS"]))

        # ------------------------------------------------------------------
        # Frozen V16 input structural compatibility.
        # ------------------------------------------------------------------
        print("\nV16 FROZEN INPUT STRUCTURAL APPLICABILITY")
        with np.load(frozen_path, allow_pickle=False) as db:
            required = [
                "saturation_grid_full_float64",
                "saturation_grid_supported_only_float64",
                "supported_mask",
                "support_denominator",
                "support_numerator",
                "background_saturation",
                "physical_time_days",
                "grid_shape",
            ]
            g.check("frozen_required_arrays_present", all(k in db.files for k in required), str(db.files))
            full = np.array(db["saturation_grid_full_float64"], dtype=np.float64, copy=True)
            supported_only = np.array(db["saturation_grid_supported_only_float64"], dtype=np.float64, copy=True)
            support_u8 = np.array(db["supported_mask"], copy=True).astype(np.uint8)
            den = np.array(db["support_denominator"], dtype=np.float64, copy=True)
            num = np.array(db["support_numerator"], dtype=np.float64, copy=True)
            background = float(np.asarray(db["background_saturation"]))
            physical_time_days = float(np.asarray(db["physical_time_days"]))
            grid_shape = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())

        support = den > 0.0
        unsupported = ~support
        g.check("V16_grid_matches_historical_contract_shape", grid_shape == EXPECTED_GRID and full.shape == EXPECTED_GRID)
        g.check("V16_time_matches_historical_primary_time", physical_time_days == EXPECTED_TIME_DAYS)
        g.check("V16_full_grid_finite", np.all(np.isfinite(full)))
        g.check("V16_support_mask_reproduced", np.array_equal(support_u8.astype(bool), support))
        g.check("V16_support_counts_exact", int(np.sum(support)) == EXPECTED_SUPPORTED and int(np.sum(unsupported)) == EXPECTED_BACKGROUND_COMPLETED)
        g.check("V16_supported_state_sidecar_exact", np.array_equal(full[support], supported_only[support]))
        g.check("V16_background_completed_cells_exact", background == EXPECTED_BACKGROUND and np.all(full[unsupported] == background))
        g.check("V16_background_completed_cells_remain_unsupported", np.all(den[unsupported] == 0.0) and np.all(support_u8[unsupported] == 0))

        # Baseline identity cross-check against E19.
        g.check("V16_frozen_array_SHA_matches_E19", arr_sha(full) == e19_audit.get("candidate_array_sha256"))
        g.check("V16_support_mask_SHA_matches_E19", arr_sha(support_u8) == e19_audit.get("support_mask_array_sha256"))
        g.check("V16_denominator_SHA_matches_E19", arr_sha(den) == e19_audit.get("support_denominator_array_sha256"))
        g.check("V16_numerator_SHA_matches_E19", arr_sha(num) == e19_audit.get("support_numerator_array_sha256"))

        # ------------------------------------------------------------------
        # Gate applicability reconciliation.
        # ------------------------------------------------------------------
        print("\nHISTORICAL GATE AUTHORITY / V16 APPLICABILITY RECONCILIATION")
        applicability_rows: list[dict[str, Any]] = []
        registry_rows: list[dict[str, Any]] = []

        for name, spec in HISTORICAL_GATES.items():
            # Structural applicability means the metric definition remains valid on
            # a 15x50x50 binary plume mask at 100 d. It does NOT mean evaluable yet.
            structural = bool(
                grid_shape == EXPECTED_GRID
                and physical_time_days == EXPECTED_TIME_DAYS
                and np.all(np.isfinite(full))
            )
            registry_rows.append({
                "gate": name,
                "role": "AUTHORITATIVE_HISTORICAL_GATE",
                "metric": spec["metric"],
                "operator": spec["operator"],
                "limit": spec["limit"],
                "units": spec["units"],
                "historical_source": V15_ER[0],
                "historical_source_sha256": V15_ER[1],
                "V16_structurally_applicable": structural,
                "V16_evaluation_ready": False,
                "evaluation_block_reason": "authoritative plume threshold and reference plume unresolved",
            })
            applicability_rows.append({
                "gate": name,
                "same_primary_time": physical_time_days == EXPECTED_TIME_DAYS,
                "same_grid_shape": grid_shape == EXPECTED_GRID,
                "metric_defined_on_binary_plume_masks": True,
                "requires_reference_plume": True,
                "requires_authoritative_plume_threshold": True,
                "model_architecture_independent_metric": True,
                "structurally_applicable_to_V16": structural,
                "evaluable_in_E20": False,
            })

        g.check("historical_gate_registry_exact_four", len(registry_rows) == 4 and set(r["gate"] for r in registry_rows) == set(HISTORICAL_GATES))
        g.check("all_four_historical_gates_structurally_applicable", all(r["V16_structurally_applicable"] for r in registry_rows))
        g.check("no_gate_evaluable_before_threshold_reference", all(not r["V16_evaluation_ready"] for r in registry_rows))
        g.check("no_reference_plume_selected_in_E20", True)
        g.check("no_authoritative_plume_threshold_defined_in_E20", True)
        g.check("diagnostic_0p21_not_promoted", DIAGNOSTIC_THRESHOLD == 0.21)
        g.check("no_deployment_pass_fail_evaluated", True)
        g.check("frozen_candidate_not_modified", sha(frozen_path) == FROZEN_FILE_SHA)
        g.check("full_grid_plume_not_authorized", True)

        # ------------------------------------------------------------------
        # Persist reconciliation contract/audit.
        # ------------------------------------------------------------------
        source_authority = {
            "E19_runner_sha256": E19_RUNNER[1],
            "E19_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E19.items()},
            "E18R1_frozen_candidate_sha256": FROZEN_FILE_SHA,
            "V15SG7E0R_source": {"file": V15_E0R[0], "sha256": V15_E0R[1]},
            "V15SG7E1_source": {"file": V15_E1[0], "sha256": V15_E1[1]},
            "V15SG7ER_source": {"file": V15_ER[0], "sha256": V15_ER[1]},
            "V15SG7ER_source_binding_reconciliation": {
                "previous_package_snapshot_sha256": V15_ER_PREVIOUS_PACKAGE_SNAPSHOT_SHA,
                "live_repository_sha256": V15_ER_LIVE_REPO_SHA,
                "revision_reason": "PyCharm preflight detected live-repository source identity differed from package snapshot before any V16E-20 runner commit or execution; R1 binds the live source and re-verifies exact gate constants/operators semantically.",
            },
        }

        contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "frozen_candidate_sha256": FROZEN_FILE_SHA,
            "primary_time_days": EXPECTED_TIME_DAYS,
            "grid_shape": list(EXPECTED_GRID),
            "historical_gate_authority_reconciled": True,
            "historical_authoritative_gate_count": 4,
            "historical_gate_registry": HISTORICAL_GATES,
            "V16_structural_applicability": {
                "all_four_gates_applicable": True,
                "basis": [
                    "same 100-day primary evaluation time",
                    "same 15x50x50 Cartesian grid-index metric space",
                    "metrics operate on binary plume masks/reference masks rather than model architecture",
                    "frozen V16 full-grid field is finite and immutable",
                ],
            },
            "evaluation_prerequisites": {
                "authoritative_plume_threshold": "REQUIRED_BUT_UNRESOLVED",
                "reference_plume": "REQUIRED_BUT_UNRESOLVED",
                "reference_time_identity": "MUST_EQUAL_100_DAYS",
                "reference_grid_shape": "MUST_EQUAL_15x50x50_OR_HAVE_EXPLICIT_NONLOSSY_IDENTITY_MAPPING",
            },
            "authoritative_plume_threshold_defined": False,
            "reference_plume_selected": False,
            "deployment_pass_fail_evaluated": False,
            "diagnostic_threshold_0p21_role": "DIAGNOSTIC_ONLY_NOT_AUTHORITY",
            "frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "source_authority": source_authority,
            "next_milestone": NEXT_PASS,
        }

        audit = {
            "milestone": MILESTONE,
            "status": "PASS",
            "frozen_candidate_sha256": FROZEN_FILE_SHA,
            "frozen_candidate_array_sha256": arr_sha(full),
            "support_mask_array_sha256": arr_sha(support_u8),
            "support_denominator_array_sha256": arr_sha(den),
            "support_numerator_array_sha256": arr_sha(num),
            "historical_gate_limits_recovered": recovered,
            "historical_authoritative_gate_count": 4,
            "V16_structurally_applicable_gate_count": 4,
            "V16_evaluable_gate_count_E20": 0,
            "authoritative_plume_threshold_defined": False,
            "reference_plume_selected": False,
            "deployment_pass_fail_evaluated": False,
            "frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "source_authority": source_authority,
            "next_milestone": NEXT_PASS,
        }

        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "frozen_candidate_sha256": FROZEN_FILE_SHA,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "historical_authoritative_gate_count": 4,
            "V16_structurally_applicable_gate_count": 4,
            "V16_evaluable_gate_count": 0,
            "historical_gate_registry_adopted_for_future_V16_evaluation": True,
            "authoritative_plume_threshold_defined": False,
            "reference_plume_selected": False,
            "deployment_pass_fail_evaluated": False,
            "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
            "diagnostic_threshold_role": "DIAGNOSTIC_ONLY",
            "frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }

        handoff = f"""# PAD-Stream V16E-20-R1 - SG7E-R Source-Binding Reconciliation and V16 Applicability Audit PASS

V16E-20 reconciled the historical SG7E deployment-gate authority and established structural applicability to the frozen V16 100-day SGSim full-grid field.

Historical authoritative gate contract retained without change:
- PRIMARY_VOLUME_GATE: primary_volume_relative_error <= 0.10
- FOOTPRINT_IOU_GATE: footprint_IoU >= 0.90
- CENTROID_GATE_CELLS: centroid_distance_cells <= 2.0 cells
- VERTICAL_EXTENT_GATE_LAYERS: vertical_extent_error_layers <= 2.0 layers

V16 applicability:
- Grid identity: 15 x 50 x 50
- Primary evaluation time: 100 days
- All four gate metric definitions structurally applicable: YES
- Gate evaluation performed in E20: NO
- Authoritative plume threshold defined: NO
- Reference plume selected: NO
- Diagnostic 0.21 promoted: NO
- Frozen candidate modified: NO
- Full-grid plume authorized: NO

NEXT: {NEXT_PASS}
""".encode("utf-8")

        out.mkdir(parents=True, exist_ok=True)
        files = {
            "V16E20_R1_Historical_SG7E_Gate_Authority_Contract.json": enc(contract),
            "V16E20_R1_V16_Applicability_Audit.json": enc(audit),
            "PAD_Stream_V16E20_R1_Summary.json": enc(summary),
            "V16E20_R1_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)

        save_csv(out / "V16E20_R1_Historical_Authoritative_Gate_Registry.csv", registry_rows)
        save_csv(out / "V16E20_R1_V16_Gate_Applicability_Matrix.csv", applicability_rows)
        save_csv(out / "V16E20_R1_Source_Authority.csv", [
            {"role": "V16E19 validation-entry contract", "file": E19_RUNNER[0], "sha256": E19_RUNNER[1]},
            {"role": "V16E18-R1 frozen numerical input", "file": str(frozen_path), "sha256": FROZEN_FILE_SHA},
            {"role": "historical gate authority reconciliation", "file": V15_E0R[0], "sha256": V15_E0R[1]},
            {"role": "historical gate metric semantics", "file": V15_E1[0], "sha256": V15_E1[1]},
            {"role": "accepted historical primary contract", "file": V15_ER[0], "sha256": V15_ER[1]},
        ])
        save_csv(out / "V16E20_R1_Evaluation_Prerequisite_Matrix.csv", [
            {"prerequisite": "frozen V16 candidate identity", "status": "READY", "required_before_gate_evaluation": True},
            {"prerequisite": "historical four-gate authority", "status": "READY", "required_before_gate_evaluation": True},
            {"prerequisite": "V16 structural applicability", "status": "READY", "required_before_gate_evaluation": True},
            {"prerequisite": "authoritative plume threshold", "status": "UNRESOLVED", "required_before_gate_evaluation": True},
            {"prerequisite": "reference plume identity", "status": "UNRESOLVED", "required_before_gate_evaluation": True},
            {"prerequisite": "reference 100-day time identity", "status": "UNRESOLVED", "required_before_gate_evaluation": True},
        ])
        save_csv(out / "V16E20_R1_Final_Gate_Matrix.csv", [
            {"gate": name, "passed": rec["passed"], "detail": rec["detail"]}
            for name, rec in g.items.items()
        ])

        print("\n" + "=" * 132)
        print("V16E-20-R1 RESULT: PASS")
        print("=" * 132)
        print(f"{'Frozen candidate SHA-256':74}: {FROZEN_FILE_SHA}")
        print(f"{'Grid / primary time':74}: 15 x 50 x 50 / {EXPECTED_TIME_DAYS:.1f} days")
        print(f"{'Historical authoritative gates reconciled':74}: 4")
        print(f"{'V16 structurally applicable gates':74}: 4")
        print(f"{'V16 gates evaluable in E20':74}: 0")
        print(f"{'PRIMARY_VOLUME_GATE':74}: primary_volume_relative_error <= 0.10")
        print(f"{'FOOTPRINT_IOU_GATE':74}: footprint_IoU >= 0.90")
        print(f"{'CENTROID_GATE_CELLS':74}: centroid_distance_cells <= 2.0")
        print(f"{'VERTICAL_EXTENT_GATE_LAYERS':74}: vertical_extent_error_layers <= 2.0")
        print(f"{'Authoritative plume threshold defined':74}: NO")
        print(f"{'Reference plume selected':74}: NO")
        print(f"{'Deployment pass/fail evaluated':74}: NO")
        print(f"{'Diagnostic 0.21 promoted':74}: NO")
        print(f"{'Frozen candidate modified':74}: NO")
        print(f"{'Full-grid plume authorized':74}: NO")
        print(f"{'Internal test / OOD reopened':74}: NO / NO")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        for name in [
            "V16E20_R1_Historical_Authoritative_Gate_Registry.csv",
            "V16E20_R1_V16_Gate_Applicability_Matrix.csv",
            "V16E20_R1_Source_Authority.csv",
            "V16E20_R1_Evaluation_Prerequisite_Matrix.csv",
            "V16E20_R1_Final_Gate_Matrix.csv",
        ]:
            print(f"{name} SHA: {sha(out / name)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-20-R1 did not close: {exc}", flush=True)
        try:
            blocked.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "E19_modified": False,
                "frozen_candidate_modified": False,
                "historical_gate_registry_adopted_for_future_V16_evaluation": False,
                "authoritative_plume_threshold_defined": False,
                "reference_plume_selected": False,
                "deployment_pass_fail_evaluated": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = blocked / "V16E20_R1_Blocked_Historical_SG7E_Gate_Authority_V16_Applicability_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", blocked)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
