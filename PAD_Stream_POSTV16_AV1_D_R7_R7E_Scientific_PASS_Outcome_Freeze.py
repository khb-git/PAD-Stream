#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV1-D-R7-R7E-OUTCOME-FREEZE"
STATUS_PASS = (
    "AV1DR7R7E_FOUNDATION0001_SCIENTIFIC_PASS_OUTCOME_FROZEN_"
    "NO_SUBSEQUENT_MILESTONE_AUTHORIZED"
)
STATUS_BLOCKED = "AV1DR7R7E_OUTCOME_FREEZE_BLOCKED"
FREEZE_PROTOCOL_ID = (
    "POSTV16_AV1_D_R7_R7E_FOUNDATION0001_SCIENTIFIC_PASS_OUTCOME_FREEZE_V1"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R7E_COMMIT = "71b453db2f58e2aa0ee00ae6656f4db5cdf5b5e3"

R7R7E = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_"
    "Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
)
R7R7E_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"
R7R7D = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7D_"
    "Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
)
R7R7D_BLOB = "bd2873f7fb6b98d4e857c98864b78e2da6f202a4"
R7R7C = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7C_"
    "Support_Domain_Capacity_Failure_Closure.py"
)
R7R7C_BLOB = "a58f5910d2290ecb5a258af9ecf9a27afe6620ee"
R7R7B = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7B_"
    "Canonical_Solver_Native_Semantics_Execution.py"
)
R7R7B_BLOB = "c65fc15f630a097a81fbe6fe28dab87c7056ce65"
R7R7A = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7A_"
    "Canonical_Primary_Envelope_Arithmetic_Semantics_Freeze.py"
)
R7R7A_BLOB = "191792855ecbb2560475ca2066b307d6fef494d5"
R7R2 = (
    "PAD_Stream_POSTV16_AV1_D_R7_R2_"
    "Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
)
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"

SOURCE_BLOBS = {
    R7R7E: R7R7E_BLOB,
    R7R7D: R7R7D_BLOB,
    R7R7C: R7R7C_BLOB,
    R7R7B: R7R7B_BLOB,
    R7R7A: R7R7A_BLOB,
    R7R2: R7R2_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R7R7E_REL = BASE / (
    "POSTV16_AV1_D_R7_R7E_Frozen_Horizontal_Face_Halo_"
    "Occupancy_Domain_Execution"
)
R7R7E_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7E_Summary.json"
R7R7E_DECISION = "POSTV16_AV1_D_R7_R7E_Final_Decision.json"
R7R7E_TIME = "POSTV16_AV1_D_R7_R7E_Timewise_Strict_Certification_Audit.csv"
R7R7E_COMPONENT = "POSTV16_AV1_D_R7_R7E_Component_Strict_LP_Audit.csv"
R7R7E_GATES = "POSTV16_AV1_D_R7_R7E_Final_Gate_Matrix.csv"
R7R7E_MANIFEST = "POSTV16_AV1_D_R7_R7E_Artifact_Manifest.csv"
R7R7E_STATE = (
    "POSTV16_AV1_D_R7_R7E_Foundation0001_"
    "Frozen_Horizontal_Face_Halo_Occupancy_Integrated_State.npz"
)

OUT_REL = BASE / "POSTV16_AV1_D_R7_R7E_Scientific_PASS_Outcome_Freeze"
BLOCKED_REL = BASE / "POSTV16_AV1_D_R7_R7E_OUTCOME_FREEZE_BLOCKED"

R7R7E_STATUS = (
    "AV1DR7R7E_FROZEN_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_DOMAIN_"
    "EXECUTED_ALL_9_TIMES_END_TO_END_BOUNDED_CONSERVATIVE_INTEGRATION_PASS"
)
R7R7D_PROTOCOL_ID = (
    "POSTV16_AV1_D_R7_R7D_"
    "SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_EXTENSION_V1"
)
R7R7A_PROTOCOL_ID = (
    "POSTV16_AV1_D_R7_R7A_"
    "SOLVER_NATIVE_UNSCALED_PRIMARY_ENVELOPE_SEMANTICS_V1"
)
R7R2_PROTOCOL_ID = (
    "POSTV16_AV1_D_R7_R2_"
    "SUPPORT_GRAPH_MIN_COST_EXCESS_MASS_RECONCILIATION_V1"
)

FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"
WEIGHTS_SHA = "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"
NORM_SHA = "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"
INTEGRATED_STATE_SHA = "24e053237d8bd21bdfd0db72f97fd38ae2c2caa77b0ab812b6c36337020d5bd8"

CANONICAL_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]
EXPECTED_S0_CELLS = 20462
EXPECTED_H1_CELLS = 10952
EXPECTED_D1_CELLS = 31414
EXPECTED_S0_DIRECTED_ARCS = 56596
EXPECTED_H1_ENTRY_ARCS = 20919
EXPECTED_MAX_RAW_OVERLOADED_CELLS = 10625
EXPECTED_MAX_RAW_CAPACITY_EXCESS_KG = 100322.486235897
EXPECTED_MAX_POST_CAPACITY_EXCESS_KG = 4.547473508864641e-13
EXPECTED_MAX_MASS_REL_CLOSURE = 3.7838791414171293e-16
EXPECTED_MAX_EOS_REL_CLOSURE = 3.2128351280335353e-16
EXPECTED_MIN_SECONDARY_SLACK = 0.0
EXPECTED_MAX_H1_MASS_KG = 25976372.61373238
EXPECTED_MAX_H1_CAPACITY_FRACTION = 0.6293036641004597
EXPECTED_MAX_H1_OCCUPIED = 8091
EXPECTED_DAY365_D1_CAPACITY_KG = 118409399.20577468
EXPECTED_DAY365_S0_CAPACITY_KG = 77131437.39561492
EXPECTED_DAY365_H1_CAPACITY_KG = 41277961.81015976
EXPECTED_DAY365_S0_MASS_KG = 64845079.95249124
EXPECTED_DAY365_H1_MASS_KG = 13916215.728146736
EXPECTED_DAY365_H1_CAPACITY_FRACTION = 0.3371342749951751
EXPECTED_DAY365_H1_OCCUPIED = 5140
EXPECTED_DAY365_H1_TOTAL_FRACTION = 0.1766885068089069

AUTHORIZED_CLAIM = (
    "On frozen Foundation Case 0001, the single prospectively frozen R7-R7D "
    "one-cell lateral occupancy halo is sufficient for bounded conservative "
    "end-to-end integration across all nine canonical times while preserving "
    "the unchanged SG7D S0 transport skeleton, accepted transport model, B1 "
    "representation bridge, R7-R2 support-backbone costs, R7-R7A canonical "
    "solver arithmetic, saturation bounds, and R2 EOS."
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    manifest = {row["file"]: row["sha256"] for row in rows}
    if not manifest:
        raise GateError("R7R7E_manifest_empty")
    for filename, expected in manifest.items():
        path = directory / filename
        if not path.is_file():
            raise GateError(f"manifest_file_missing:{filename}")
        actual = sha256_file(path)
        if actual != expected:
            raise GateError(f"manifest_SHA_mismatch:{filename}:{actual}:{expected}")
    return manifest


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = out / name
        if path.exists() and path.read_bytes() != data:
            raise GateError(f"existing_output_differs:{name}")
        if not path.exists():
            path.write_bytes(data)


def near(actual: float, expected: float, *, rtol: float = 1.0e-13, atol: float = 1.0e-9) -> bool:
    a = float(actual)
    b = float(expected)
    return abs(a - b) <= max(atol, rtol * max(abs(b), 1.0))


def self_test() -> None:
    if len(CANONICAL_DAYS) != 9:
        raise RuntimeError("canonical_day_count")
    if CANONICAL_DAYS[5] != 365.0:
        raise RuntimeError("day365_index")
    if EXPECTED_S0_CELLS + EXPECTED_H1_CELLS != EXPECTED_D1_CELLS:
        raise RuntimeError("D1_partition")
    if not 0.0 < EXPECTED_DAY365_H1_CAPACITY_FRACTION < 1.0:
        raise RuntimeError("day365_H1_capacity_fraction")
    if not 0.0 < EXPECTED_MAX_H1_CAPACITY_FRACTION < 1.0:
        raise RuntimeError("max_H1_capacity_fraction")
    if EXPECTED_MAX_POST_CAPACITY_EXCESS_KG > 1.0e-10:
        raise RuntimeError("post_capacity_excess")
    if EXPECTED_MAX_MASS_REL_CLOSURE > 1.0e-12:
        raise RuntimeError("mass_closure")
    if EXPECTED_MAX_EOS_REL_CLOSURE > 1.0e-12:
        raise RuntimeError("EOS_closure")
    print("POSTV16-AV1-D-R7-R7E outcome-freeze self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("=" * 196)
    print("POSTV16-AV1-D-R7-R7E — SEALED SCIENTIFIC PASS OUTCOME FREEZE")
    print("=" * 196)
    print("FREEZE/CLOSURE ONLY. NO MODEL INFERENCE. NO LP EXECUTION. NO MAPBACK EXECUTION. NO RETUNING.")
    print("R7-R3, R7-R6, AND R7-R7B REMAIN IMMUTABLE FAILS. R7-R7E REMAINS A CASE-SPECIFIC SCIENTIFIC PASS.")
    print("THIS FREEZE DOES NOT NAME OR AUTHORIZE ANY SUBSEQUENT SCIENTIFIC MILESTONE.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R7R7E_commit", parent == PARENT_R7R7E_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for filename, expected_blob in SOURCE_BLOBS.items():
            path = root / filename
            actual = git_blob_sha(path, root) if path.is_file() else "missing"
            gate(f"{Path(filename).stem}_git_blob_exact", actual == expected_blob, actual)

        stage = "R7R7E_artifact_binding"
        r7e = drive / R7R7E_REL
        gate("R7R7E_output_present", r7e.is_dir(), str(r7e))
        manifest = verify_manifest(r7e, R7R7E_MANIFEST)
        gate("R7R7E_manifest_SHA_closure", True, len(manifest))
        gate("R7R7E_manifest_file_count_exact", len(manifest) == 6, len(manifest))

        required_manifested = {R7R7E_STATE, R7R7E_SUMMARY, R7R7E_DECISION, R7R7E_TIME, R7R7E_COMPONENT, R7R7E_GATES}
        gate("R7R7E_manifest_required_artifact_set_exact", set(manifest) == required_manifested, sorted(manifest))

        decision = load_json(r7e / R7R7E_DECISION)
        summary = load_json(r7e / R7R7E_SUMMARY)
        time_rows = read_csv(r7e / R7R7E_TIME)
        component_rows = read_csv(r7e / R7R7E_COMPONENT)
        gate_rows = read_csv(r7e / R7R7E_GATES)

        stage = "R7R7E_decision_binding"
        gate("R7R7E_status_exact", decision["status"] == R7R7E_STATUS, decision["status"])
        gate("R7R7E_scientific_execution_pass_true", decision["scientific_execution_pass"] is True)
        gate("R7R7E_all_9_canonical_times_completed", decision["all_9_canonical_times_completed"] is True)
        gate("R7R7E_candidate_count_one", int(decision["candidate_count"]) == 1)
        gate("R7R7E_authorized_claim_exact", decision["authorized_claim"] == AUTHORIZED_CLAIM)
        gate("R7R7D_occupancy_protocol_exact", decision["occupancy_domain_protocol_id"] == R7R7D_PROTOCOL_ID, decision["occupancy_domain_protocol_id"])
        gate("R7R7A_arithmetic_protocol_exact", decision["canonical_arithmetic_protocol_id"] == R7R7A_PROTOCOL_ID, decision["canonical_arithmetic_protocol_id"])
        gate("R7R2_physical_protocol_exact", decision["physical_protocol_id"] == R7R2_PROTOCOL_ID, decision["physical_protocol_id"])
        gate("foundation_SHA_exact", decision["foundation_case_sha256"] == FOUNDATION_SHA, decision["foundation_case_sha256"])
        gate("accepted_weights_SHA_exact", decision["accepted_weights_sha256"] == WEIGHTS_SHA, decision["accepted_weights_sha256"])
        gate("normalization_SHA_exact", decision["normalization_sha256"] == NORM_SHA, decision["normalization_sha256"])
        gate("integrated_state_SHA_exact", decision["integrated_state_sha256"] == INTEGRATED_STATE_SHA, decision["integrated_state_sha256"])
        state_sha = sha256_file(r7e / R7R7E_STATE)
        gate("integrated_state_file_SHA_exact", state_sha == INTEGRATED_STATE_SHA, state_sha)

        stage = "immutable_history_binding"
        gate("R7R3_immutable_FAIL", decision["R7R3_immutable_result"] == "FAIL")
        gate("R7R6_immutable_FAIL", decision["R7R6_immutable_result"] == "FAIL")
        gate("R7R7B_immutable_FAIL", decision["R7R7B_immutable_result"] == "FAIL")
        gate("R7R3_not_retested", decision["R7R3_retested"] is False)
        gate("R7R6_not_retested", decision["R7R6_retested"] is False)
        gate("R7R7B_not_retested", decision["R7R7B_retested"] is False)

        stage = "R7R7E_semantic_binding"
        gate("occupancy_domain_extended", decision["occupancy_domain_extended"] is True)
        gate("occupancy_domain_exact", decision["occupancy_domain"] == "D1 = exact SG7D support S0 union frozen single non-recursive same-layer x/y face halo H1")
        gate("H1_terminal_sink_role_exact", decision["H1_role"] == "terminal finite-volume occupancy sinks only")
        gate("halo_entry_cost_exact", float(decision["halo_entry_cost_units"]) == 5.0)
        gate("H1_reverse_arcs_false", decision["H1_reverse_arcs"] is False)
        gate("H1_to_H1_transit_false", decision["H1_to_H1_transit_arcs"] is False)
        gate("vertical_halo_false", decision["vertical_halo"] is False)
        gate("diagonal_halo_false", decision["diagonal_halo"] is False)
        gate("second_ring_halo_false", decision["second_ring_halo"] is False)
        gate("adaptive_domain_growth_false", decision["adaptive_domain_growth"] is False)
        gate("outside_D1_sinks_false", decision["cells_outside_D1_used_as_sinks"] is False)
        gate("raw_deposition_outside_S0_false", decision["raw_deposition_outside_S0"] is False)
        gate("accepted_checkpoint_unmodified", decision["accepted_checkpoint_modified"] is False)
        gate("B1_unmodified", decision["B1_modified"] is False)
        gate("S0_support_graph_unmodified", decision["S0_support_graph_modified"] is False)
        gate("S0_primary_cost_unmodified", decision["S0_primary_graph_cost_modified"] is False)
        gate("raw_SG7D_E37A_deposition_unmodified", decision["raw_SG7D_E37A_deposition_modified"] is False)
        gate("EOS_unmodified", decision["EOS_modified"] is False)
        gate("pressure_field_unmodified", decision["pressure_field_modified"] is False)
        gate("saturation_bounds_unmodified", decision["saturation_bounds_modified"] is False)
        gate("no_mass_clipping_or_discard", decision["mass_clipping_or_discarding_used"] is False)
        gate("no_global_saturation_rescaling", decision["global_saturation_rescaling_used"] is False)
        gate("no_geology0031", decision["geology0031_used"] is False)
        gate("no_acceptance_truth", decision["acceptance_truth_used"] is False)
        gate("no_alternate_candidate", decision["alternate_candidate_used"] is False)
        gate("no_retuning", decision["retuning_used"] is False)
        gate("no_plume_fidelity_claim", decision["plume_fidelity_claim"] is False)
        gate("no_generalization_claim", decision["generalization_claim"] is False)
        gate("no_calibrated_dispersion_model_claim", decision["calibrated_dispersion_model_claim"] is False)
        gate("no_new_accuracy_claim", decision["new_accuracy_claim"] is False)
        gate("next_object_present", isinstance(decision["next"], dict))
        gate("next_not_authorized", decision["next"]["authorized"] is False)
        gate("next_milestone_unnamed", decision["next"]["milestone"] is None)
        gate("next_name_unnamed", decision["next"]["name"] is None)

        stage = "R7R7E_summary_binding"
        exact_ints = {
            "S0_cell_count": EXPECTED_S0_CELLS,
            "H1_cell_count": EXPECTED_H1_CELLS,
            "D1_cell_count": EXPECTED_D1_CELLS,
            "S0_directed_arc_count": EXPECTED_S0_DIRECTED_ARCS,
            "H1_entry_arc_count": EXPECTED_H1_ENTRY_ARCS,
            "maximum_raw_overloaded_cells": EXPECTED_MAX_RAW_OVERLOADED_CELLS,
            "maximum_H1_occupied_cell_count": EXPECTED_MAX_H1_OCCUPIED,
            "day365_H1_occupied_cell_count": EXPECTED_DAY365_H1_OCCUPIED,
        }
        for key, expected in exact_ints.items():
            gate(f"summary_{key}_exact", int(summary[key]) == expected, summary[key])

        exact_floats = {
            "maximum_raw_capacity_excess_kg": EXPECTED_MAX_RAW_CAPACITY_EXCESS_KG,
            "maximum_post_reconciliation_capacity_excess_kg": EXPECTED_MAX_POST_CAPACITY_EXCESS_KG,
            "maximum_mass_relative_closure": EXPECTED_MAX_MASS_REL_CLOSURE,
            "maximum_EOS_mass_relative_closure": EXPECTED_MAX_EOS_REL_CLOSURE,
            "minimum_secondary_inequality_slack": EXPECTED_MIN_SECONDARY_SLACK,
            "maximum_H1_component_mass_kg": EXPECTED_MAX_H1_MASS_KG,
            "maximum_H1_capacity_fraction_used": EXPECTED_MAX_H1_CAPACITY_FRACTION,
            "day365_D1_capacity_kg": EXPECTED_DAY365_D1_CAPACITY_KG,
            "day365_S0_capacity_kg": EXPECTED_DAY365_S0_CAPACITY_KG,
            "day365_H1_capacity_kg": EXPECTED_DAY365_H1_CAPACITY_KG,
            "day365_S0_final_component_mass_kg": EXPECTED_DAY365_S0_MASS_KG,
            "day365_H1_final_component_mass_kg": EXPECTED_DAY365_H1_MASS_KG,
            "day365_H1_capacity_fraction_used": EXPECTED_DAY365_H1_CAPACITY_FRACTION,
            "day365_H1_fraction_of_total_component_mass": EXPECTED_DAY365_H1_TOTAL_FRACTION,
        }
        for key, expected in exact_floats.items():
            gate(f"summary_{key}_exact", near(float(summary[key]), expected), summary[key])
        gate("summary_integrated_state_SHA_exact", summary["integrated_state_sha256"] == INTEGRATED_STATE_SHA, summary["integrated_state_sha256"])

        stage = "R7R7E_timewise_binding"
        gate("timewise_row_count_9", len(time_rows) == 9, len(time_rows))
        days = [float(row["target_day"]) for row in time_rows]
        gate("timewise_days_exact", days == CANONICAL_DAYS, days)
        for row in time_rows:
            day = float(row["target_day"])
            gate(f"day{day:g}_post_capacity_excess_bounded", float(row["max_capacity_excess_after_reconciliation_kg"]) <= 1.0e-10, row["max_capacity_excess_after_reconciliation_kg"])
            gate(f"day{day:g}_mass_closure_bounded", float(row["total_component_mass_relative_closure"]) <= 1.0e-12, row["total_component_mass_relative_closure"])
            gate(f"day{day:g}_EOS_closure_bounded", float(row["EOS_mass_relative_closure"]) <= 1.0e-12, row["EOS_mass_relative_closure"])
            gate(f"day{day:g}_secondary_residual_canonical", float(row["minimum_secondary_inequality_slack"]) >= -1.0e-10, row["minimum_secondary_inequality_slack"])

        h1_mass = [float(row["H1_final_component_mass_kg"]) for row in time_rows]
        h1_fraction = [float(row["H1_capacity_fraction_used"]) for row in time_rows]
        h1_occupied = [int(float(row["H1_occupied_cell_count"])) for row in time_rows]
        gate("H1_mass_nondecreasing_over_canonical_times", all(b >= a for a, b in zip(h1_mass, h1_mass[1:])), h1_mass)
        gate("H1_capacity_fraction_nondecreasing_over_canonical_times", all(b >= a for a, b in zip(h1_fraction, h1_fraction[1:])), h1_fraction)
        gate("H1_occupied_count_nondecreasing_over_canonical_times", all(b >= a for a, b in zip(h1_occupied, h1_occupied[1:])), h1_occupied)

        day365 = next(row for row in time_rows if float(row["target_day"]) == 365.0)
        gate("day365_H1_mass_exact", near(float(day365["H1_final_component_mass_kg"]), EXPECTED_DAY365_H1_MASS_KG), day365["H1_final_component_mass_kg"])
        gate("day365_H1_capacity_fraction_exact", near(float(day365["H1_capacity_fraction_used"]), EXPECTED_DAY365_H1_CAPACITY_FRACTION), day365["H1_capacity_fraction_used"])
        gate("component_audit_nonempty", len(component_rows) > 0, len(component_rows))
        gate("gate_matrix_nonempty", len(gate_rows) > 0, len(gate_rows))

        stage = "freeze_outcome"
        claim_boundary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "freeze_protocol_id": FREEZE_PROTOCOL_ID,
            "authorized_claim": AUTHORIZED_CLAIM,
            "scope": {
                "foundation_case": "Foundation Case 0001 only",
                "canonical_times_days": CANONICAL_DAYS,
                "occupancy_domain": "D1 = exact SG7D support S0 union frozen single non-recursive same-layer x/y face halo H1",
                "H1_role": "terminal finite-volume occupancy sinks only",
                "halo_entry_cost_units": 5.0,
            },
            "what_pass_is_allowed_to_mean": {
                "one_ring_lateral_halo_sufficient_for_this_case": True,
                "bounded_conservative_end_to_end_integration_all_9_times": True,
                "prior_R7R7B_capacity_obstruction_removed_in_new_frozen_candidate": True,
            },
            "what_pass_is_not_allowed_to_mean": {
                "R7R7B_reclassified_or_retested": False,
                "plume_fidelity_validated": False,
                "generalization_validated": False,
                "calibrated_dispersion_model_validated": False,
                "new_accuracy_claim_validated": False,
                "alternate_candidate_validated": False,
                "adaptive_domain_growth_validated": False,
            },
            "immutable_history": {
                "R7R3": "FAIL",
                "R7R6": "FAIL",
                "R7R7B": "FAIL",
                "prior_results_relabelled": False,
                "prior_failed_executions_retested": False,
            },
            "unchanged_authorities": {
                "accepted_checkpoint": True,
                "B1_representation_bridge": True,
                "S0_support_graph": True,
                "S0_primary_graph_cost": True,
                "raw_SG7D_E37A_deposition": True,
                "R7R7A_canonical_solver_arithmetic": True,
                "R2_EOS": True,
                "pressure_field": True,
                "saturation_bounds": True,
            },
            "next": {
                "milestone": None,
                "name": None,
                "authorized": False,
                "reason": "This artifact freezes the R7-R7E outcome only. A subsequent scientific milestone requires a separate prospective design decision after this freeze.",
            },
        }

        frozen_outcome = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "freeze_protocol_id": FREEZE_PROTOCOL_ID,
            "R7R7E_status": R7R7E_STATUS,
            "R7R7E_scientific_execution_pass": True,
            "R7R7E_source_commit": PARENT_R7R7E_COMMIT,
            "R7R7E_source_blob": R7R7E_BLOB,
            "R7R7E_integrated_state_sha256": INTEGRATED_STATE_SHA,
            "R7R7E_manifest_entries": len(manifest),
            "R7R7E_all_9_times_completed": True,
            "R7R7E_candidate_count": 1,
            "R7R3_result": "FAIL",
            "R7R6_result": "FAIL",
            "R7R7B_result": "FAIL",
            "R7R7B_retested": False,
            "S0_cell_count": EXPECTED_S0_CELLS,
            "H1_cell_count": EXPECTED_H1_CELLS,
            "D1_cell_count": EXPECTED_D1_CELLS,
            "S0_directed_arc_count": EXPECTED_S0_DIRECTED_ARCS,
            "H1_entry_arc_count": EXPECTED_H1_ENTRY_ARCS,
            "day365_H1_component_mass_kg": EXPECTED_DAY365_H1_MASS_KG,
            "day365_H1_capacity_fraction_used": EXPECTED_DAY365_H1_CAPACITY_FRACTION,
            "day365_H1_occupied_cell_count": EXPECTED_DAY365_H1_OCCUPIED,
            "maximum_H1_component_mass_kg": EXPECTED_MAX_H1_MASS_KG,
            "maximum_H1_capacity_fraction_used": EXPECTED_MAX_H1_CAPACITY_FRACTION,
            "maximum_H1_occupied_cell_count": EXPECTED_MAX_H1_OCCUPIED,
            "maximum_post_reconciliation_capacity_excess_kg": EXPECTED_MAX_POST_CAPACITY_EXCESS_KG,
            "maximum_mass_relative_closure": EXPECTED_MAX_MASS_REL_CLOSURE,
            "maximum_EOS_mass_relative_closure": EXPECTED_MAX_EOS_REL_CLOSURE,
            "minimum_secondary_inequality_slack": EXPECTED_MIN_SECONDARY_SLACK,
            "plume_fidelity_claim": False,
            "generalization_claim": False,
            "calibrated_dispersion_model_claim": False,
            "new_accuracy_claim": False,
            "next_milestone_authorized": False,
        }

        diagnostic_snapshot = []
        for row in time_rows:
            diagnostic_snapshot.append({
                "target_day": float(row["target_day"]),
                "raw_overloaded_cell_count": int(float(row["raw_overloaded_cell_count"])),
                "raw_max_capacity_excess_kg": float(row["raw_max_capacity_excess_kg"]),
                "D1_capacity_kg": float(row["D1_capacity_kg"]),
                "S0_capacity_kg": float(row["S0_capacity_kg"]),
                "H1_capacity_kg": float(row["H1_capacity_kg"]),
                "S0_final_component_mass_kg": float(row["S0_final_component_mass_kg"]),
                "H1_final_component_mass_kg": float(row["H1_final_component_mass_kg"]),
                "H1_capacity_fraction_used": float(row["H1_capacity_fraction_used"]),
                "H1_occupied_cell_count": int(float(row["H1_occupied_cell_count"])),
                "H1_fraction_of_total_component_mass": float(row["H1_fraction_of_total_component_mass"]),
                "max_capacity_excess_after_reconciliation_kg": float(row["max_capacity_excess_after_reconciliation_kg"]),
                "total_component_mass_relative_closure": float(row["total_component_mass_relative_closure"]),
                "EOS_mass_relative_closure": float(row["EOS_mass_relative_closure"]),
                "minimum_secondary_inequality_slack": float(row["minimum_secondary_inequality_slack"]),
            })

        summary_freeze = {
            **frozen_outcome,
            "authorized_claim": AUTHORIZED_CLAIM,
            "source_output_directory": str(R7R7E_REL),
            "source_manifest_SHA_closure": True,
            "source_artifact_count": len(manifest),
            "model_inference_performed_in_freeze": False,
            "LP_execution_performed_in_freeze": False,
            "mapback_execution_performed_in_freeze": False,
            "R7R7E_outputs_modified": False,
            "freeze_only": True,
            "next": {"milestone": None, "name": None, "authorized": False},
        }

        immutable_publish(out, {
            "PAD_Stream_POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Summary.json": json_bytes(summary_freeze),
            "POSTV16_AV1_D_R7_R7E_Frozen_Outcome_Contract.json": json_bytes(frozen_outcome),
            "POSTV16_AV1_D_R7_R7E_Frozen_Claim_Boundary.json": json_bytes(claim_boundary),
            "POSTV16_AV1_D_R7_R7E_Frozen_Timewise_Diagnostic_Snapshot.csv": csv_bytes(diagnostic_snapshot),
            "POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Gate_Matrix.csv": csv_bytes([{"gate": key, **value} for key, value in gates.items()]),
        })

        freeze_manifest = []
        for path in sorted(out.iterdir()):
            if path.is_file() and path.name != "POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Artifact_Manifest.csv":
                freeze_manifest.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
        immutable_publish(out, {
            "POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Artifact_Manifest.csv": csv_bytes(freeze_manifest)
        })

        print("\n" + "=" * 196)
        print("POSTV16-AV1-D-R7-R7E OUTCOME FREEZE: PASS")
        print("=" * 196)
        print(f"{'Status':116}: {STATUS_PASS}")
        print(f"{'Freeze protocol':116}: {FREEZE_PROTOCOL_ID}")
        print(f"{'R7-R7E source commit':116}: {PARENT_R7R7E_COMMIT}")
        print(f"{'R7-R7E source blob':116}: {R7R7E_BLOB}")
        print(f"{'R7-R7E integrated state SHA256':116}: {INTEGRATED_STATE_SHA}")
        print(f"{'R7-R7E manifested artifacts verified':116}: {len(manifest)}")
        print(f"{'Scientific outcome':116}: PASS — Foundation Case 0001 only")
        print(f"{'Canonical times completed':116}: 9 / 9")
        print(f"{'S0 / H1 / D1 cell counts':116}: {EXPECTED_S0_CELLS} / {EXPECTED_H1_CELLS} / {EXPECTED_D1_CELLS}")
        print(f"{'Day365 H1 mass / capacity fraction / occupied cells':116}: {EXPECTED_DAY365_H1_MASS_KG:.12e} / {EXPECTED_DAY365_H1_CAPACITY_FRACTION:.12e} / {EXPECTED_DAY365_H1_OCCUPIED}")
        print(f"{'Maximum H1 mass / capacity fraction / occupied cells':116}: {EXPECTED_MAX_H1_MASS_KG:.12e} / {EXPECTED_MAX_H1_CAPACITY_FRACTION:.12e} / {EXPECTED_MAX_H1_OCCUPIED}")
        print(f"{'Max post-capacity excess / mass closure / EOS closure':116}: {EXPECTED_MAX_POST_CAPACITY_EXCESS_KG:.12e} / {EXPECTED_MAX_MASS_REL_CLOSURE:.12e} / {EXPECTED_MAX_EOS_REL_CLOSURE:.12e}")
        print(f"{'Immutable R7-R3 / R7-R6 / R7-R7B':116}: FAIL / FAIL / FAIL")
        print(f"{'R7-R7B retested':116}: False")
        print(f"{'Plume fidelity / generalization claim':116}: False / False")
        print(f"{'Model inference / LP / mapback in freeze':116}: False / False / False")
        print(f"{'Subsequent milestone named':116}: False")
        print(f"{'Subsequent milestone authorized':116}: False")
        print(f"{'NEXT':116}: Review frozen R7-R7E outcome; no subsequent milestone preauthorized")
        print("=" * 196)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "R7R7E_result_changed": False,
            "R7R3_result_changed": False,
            "R7R6_result_changed": False,
            "R7R7B_result_changed": False,
            "model_inference_performed": False,
            "LP_execution_performed": False,
            "mapback_execution_performed": False,
            "subsequent_milestone_named": False,
            "subsequent_milestone_authorized": False,
            "next_action": "Audit only the R7-R7E outcome-freeze binding. Do not reinterpret or rerun the R7-R7E scientific result.",
        }
        data = json_bytes(report)
        path = blocked / "POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Blocked_Report.json"
        if path.exists() and path.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            path = blocked / f"POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Blocked_Report_{suffix}.json"
        if not path.exists():
            path.write_bytes(data)

        print("\n" + "=" * 196)
        print("POSTV16-AV1-D-R7-R7E OUTCOME FREEZE: BLOCKED")
        print("=" * 196)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", path)
        print("No change to the sealed R7-R7E scientific PASS and no subsequent milestone is authorized from a blocked freeze.")
        return 2


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
