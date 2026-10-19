#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path
from typing import Any


MILESTONE = "POSTV16-AV1-E"
STATUS_PASS = (
    "AV1E_EXTERNAL_FULL_PHYSICS_DEPLOYMENT_ACCEPTANCE_CONTRACT_"
    "PROSPECTIVELY_FROZEN_NO_BENCHMARK_EXECUTION"
)
STATUS_BLOCKED = "AV1E_ACCEPTANCE_CONTRACT_FREEZE_BLOCKED"
PROTOCOL_ID = (
    "POSTV16_AV1_E_FOUNDATION0001_EXTERNAL_FULL_PHYSICS_"
    "DEPLOYMENT_ACCEPTANCE_CONTRACT_V1"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

# The R7-R7E scientific PASS outcome-freeze commit is the exact parent.
PARENT_R7R7E_OUTCOME_FREEZE_COMMIT = (
    "d8102e6e0badc0b6745de2f2e3dc4770dc2696d0"
)

R7R7E_FREEZE = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_"
    "Scientific_PASS_Outcome_Freeze.py"
)
R7R7E_FREEZE_BLOB = "9b6c73e07622baa6e4d0f4d8e2b60710aabcae90"

R7R7E_EXEC = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_"
    "Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
)
R7R7E_EXEC_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"

R7R7D = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7D_"
    "Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
)
R7R7D_BLOB = "bd2873f7fb6b98d4e857c98864b78e2da6f202a4"

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

AV1D = "PAD_Stream_POSTV16_AV1_D_Physical_Impact_Deployment_Audit.py"
AV1D_BLOB = "PLACEHOLDER_AV1D_BLOB"

SOURCE_BLOBS = {
    R7R7E_FREEZE: R7R7E_FREEZE_BLOB,
    R7R7E_EXEC: R7R7E_EXEC_BLOB,
    R7R7D: R7R7D_BLOB,
    R7R7A: R7R7A_BLOB,
    R7R2: R7R2_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R7E_FREEZE_REL = (
    BASE /
    "POSTV16_AV1_D_R7_R7E_Scientific_PASS_Outcome_Freeze"
)
R7R7E_FREEZE_SUMMARY = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Summary.json"
)
R7R7E_FROZEN_OUTCOME = (
    "POSTV16_AV1_D_R7_R7E_Frozen_Outcome_Contract.json"
)
R7R7E_CLAIM = (
    "POSTV16_AV1_D_R7_R7E_Frozen_Claim_Boundary.json"
)
R7R7E_TIME = (
    "POSTV16_AV1_D_R7_R7E_Frozen_Timewise_Diagnostic_Snapshot.csv"
)
R7R7E_FREEZE_GATES = (
    "POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Gate_Matrix.csv"
)
R7R7E_FREEZE_MANIFEST = (
    "POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Artifact_Manifest.csv"
)

R7R7E_FREEZE_STATUS = (
    "AV1DR7R7E_FOUNDATION0001_SCIENTIFIC_PASS_OUTCOME_FROZEN_"
    "NO_SUBSEQUENT_MILESTONE_AUTHORIZED"
)
R7R7E_FREEZE_PROTOCOL = (
    "POSTV16_AV1_D_R7_R7E_FOUNDATION0001_SCIENTIFIC_PASS_OUTCOME_FREEZE_V1"
)
R7R7E_EXEC_STATUS = (
    "AV1DR7R7E_FROZEN_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_DOMAIN_"
    "EXECUTED_ALL_9_TIMES_END_TO_END_BOUNDED_CONSERVATIVE_INTEGRATION_PASS"
)

FOUNDATION_SHA = (
    "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"
)
WEIGHTS_SHA = (
    "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"
)
NORM_SHA = (
    "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"
)
INTEGRATED_STATE_SHA = (
    "24e053237d8bd21bdfd0db72f97fd38ae2c2caa77b0ab812b6c36337020d5bd8"
)

CANONICAL_DAYS = [
    30.0, 60.0, 100.0, 150.0, 250.0,
    365.0, 500.0, 750.0, 1000.0,
]

GRID = [15, 50, 50]
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
BACKGROUND_TOTAL_SATURATION = 0.20
MAX_TOTAL_SATURATION = 0.80
VISIBLE_INCREMENTAL_CO2_THRESHOLD = 1.0e-4
BREAKTHROUGH_CO2_CUT = 1.0e-4

# ----------------------------------------------------------------------
# PROSPECTIVE PROJECT-SPECIFIC DEPLOYMENT ACCEPTANCE GATES
#
# These are frozen BEFORE exposure to the external/full-physics benchmark
# outputs. They are engineering acceptance criteria for this Foundation
# Case deployment study, not universal reservoir-simulation standards.
# ----------------------------------------------------------------------

MAX_GRID_SATURATION_RMSE = 0.05
MAX_STORED_CO2_MASS_ABS_RELATIVE = 0.02
MIN_VISIBLE_PLUME_JACCARD = 0.70

# One horizontal-cell diagonal = sqrt(20^2 + 20^2) ft.
MAX_PLUME_CENTROID_DISTANCE_M = (
    math.sqrt(DX_FT * DX_FT + DY_FT * DY_FT) * 0.3048
)

MAX_AGGREGATE_CO2_CUT_ABS_ERROR = 0.02

# Existing numerical conservation / physical-bound authorities are not
# relaxed by AV1-E.
MAX_INTERNAL_MASS_RELATIVE_CLOSURE = 1.0e-10
MAX_INTERNAL_EOS_RELATIVE_CLOSURE = 1.0e-10
MAX_POST_RECONCILIATION_CAPACITY_EXCESS_KG = 1.0e-7

OUT_REL = (
    BASE /
    "POSTV16_AV1_E_Prospective_External_Full_Physics_"
    "Deployment_Acceptance_Contract_Freeze"
)
BLOCKED_REL = BASE / "POSTV16_AV1_E_BLOCKED"


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


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(
        s,
        fieldnames=fields,
        lineterminator="\n",
    )
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError(
                f"existing_output_differs:{name}"
            )
        if not p.exists():
            p.write_bytes(data)


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    manifest = {
        row["file"]: row["sha256"]
        for row in rows
    }
    if not manifest:
        raise GateError("manifest_empty")
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError(
                f"manifest_file_missing:{fn}"
            )
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(
                f"manifest_SHA_mismatch:{fn}:{actual}:{expected}"
            )
    return manifest


def near(
    a: float,
    b: float,
    rtol: float = 1.0e-13,
    atol: float = 1.0e-12,
) -> bool:
    return abs(float(a) - float(b)) <= max(
        atol,
        rtol * max(abs(float(b)), 1.0),
    )


def self_test() -> None:
    expected = math.sqrt(800.0) * 0.3048
    if not near(
        MAX_PLUME_CENTROID_DISTANCE_M,
        expected,
        rtol=1.0e-15,
        atol=1.0e-15,
    ):
        raise RuntimeError(
            "centroid_resolution_threshold_mismatch"
        )

    if not (
        0.0 < MAX_GRID_SATURATION_RMSE < 0.60
    ):
        raise RuntimeError(
            "grid_RMSE_threshold_invalid"
        )

    if not (
        0.0
        < MAX_STORED_CO2_MASS_ABS_RELATIVE
        < 1.0
    ):
        raise RuntimeError(
            "mass_threshold_invalid"
        )

    if not (
        0.0
        < MIN_VISIBLE_PLUME_JACCARD
        <= 1.0
    ):
        raise RuntimeError(
            "jaccard_threshold_invalid"
        )

    if not (
        0.0
        < MAX_AGGREGATE_CO2_CUT_ABS_ERROR
        < 1.0
    ):
        raise RuntimeError(
            "producer_cut_threshold_invalid"
        )

    print(
        "POSTV16-AV1-E acceptance-contract self-test: PASS"
    )


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
        }
        suffix = (
            f" — {value}"
            if value is not None
            else ""
        )
        print(
            f"[{'PASS' if ok else 'FAIL'}] "
            f"{name}{suffix}"
        )
        if not ok:
            raise GateError(name)

    print("=" * 196)
    print(
        "POSTV16-AV1-E — PROSPECTIVE EXTERNAL/FULL-PHYSICS "
        "DEPLOYMENT ACCEPTANCE CONTRACT FREEZE"
    )
    print("=" * 196)
    print(
        "DESIGN/FREEZE ONLY. NO EXTERNAL BENCHMARK OUTPUT IS READ. "
        "NO MODEL INFERENCE. NO LP EXECUTION. NO MAPBACK EXECUTION."
    )
    print(
        "NO RETRAINING OR RETUNING. ACCEPTANCE GATES ARE FROZEN "
        "BEFORE BENCHMARK EXPOSURE."
    )
    print(
        "R7-R7E REMAINS A FOUNDATION CASE 0001 CASE-SPECIFIC PASS. "
        "THIS MILESTONE DOES NOT UPGRADE IT TO A PLUME-FIDELITY OR "
        "GENERALIZATION CLAIM.\n"
    )

    try:
        root = root.resolve()
        drive = drive.resolve()

        parent = git_text(
            root,
            "rev-parse",
            "HEAD^",
        )
        status = git_text(
            root,
            "status",
            "--porcelain",
        )

        gate(
            "repository_parent_is_R7R7E_outcome_freeze_commit",
            parent
            ==
            PARENT_R7R7E_OUTCOME_FREEZE_COMMIT,
            parent,
        )
        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        for fn, expected_blob in SOURCE_BLOBS.items():
            p = root / fn
            actual = (
                git_blob_sha(p, root)
                if p.is_file()
                else "missing"
            )
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected_blob,
                actual,
            )

        # ==============================================================
        # Bind the already-frozen R7-R7E PASS outcome.
        # ==============================================================

        stage = "R7R7E_outcome_freeze_binding"

        src = drive / R7R7E_FREEZE_REL

        gate(
            "R7R7E_outcome_freeze_output_present",
            src.is_dir(),
            str(src),
        )

        manifest = verify_manifest(
            src,
            R7R7E_FREEZE_MANIFEST,
        )

        gate(
            "R7R7E_outcome_freeze_manifest_SHA_closure",
            True,
            len(manifest),
        )

        required = {
            R7R7E_FREEZE_SUMMARY,
            R7R7E_FROZEN_OUTCOME,
            R7R7E_CLAIM,
            R7R7E_TIME,
            R7R7E_FREEZE_GATES,
        }

        gate(
            "R7R7E_outcome_freeze_required_artifacts_present",
            required.issubset(
                set(manifest)
            ),
            sorted(
                required.intersection(
                    set(manifest)
                )
            ),
        )

        summary = load_json(
            src / R7R7E_FREEZE_SUMMARY
        )
        frozen = load_json(
            src / R7R7E_FROZEN_OUTCOME
        )
        claim = load_json(
            src / R7R7E_CLAIM
        )

        gate(
            "R7R7E_freeze_status_exact",
            summary["status"]
            ==
            R7R7E_FREEZE_STATUS,
            summary["status"],
        )

        gate(
            "R7R7E_freeze_protocol_exact",
            summary["freeze_protocol_id"]
            ==
            R7R7E_FREEZE_PROTOCOL,
            summary["freeze_protocol_id"],
        )

        gate(
            "R7R7E_scientific_PASS_bound",
            summary[
                "R7R7E_scientific_execution_pass"
            ]
            is True,
        )

        gate(
            "R7R7E_execution_status_exact",
            summary["R7R7E_status"]
            ==
            R7R7E_EXEC_STATUS,
            summary["R7R7E_status"],
        )

        gate(
            "R7R7E_all_9_times_completed",
            summary[
                "R7R7E_all_9_times_completed"
            ]
            is True,
        )

        gate(
            "R7R7E_candidate_count_one",
            int(
                summary[
                    "R7R7E_candidate_count"
                ]
            )
            == 1,
        )

        gate(
            "foundation_SHA_exact",
            frozen[
                "R7R7E_integrated_state_sha256"
            ]
            ==
            INTEGRATED_STATE_SHA,
            frozen[
                "R7R7E_integrated_state_sha256"
            ],
        )

        gate(
            "R7R3_immutable_FAIL",
            summary["R7R3_result"]
            == "FAIL",
        )
        gate(
            "R7R6_immutable_FAIL",
            summary["R7R6_result"]
            == "FAIL",
        )
        gate(
            "R7R7B_immutable_FAIL",
            summary["R7R7B_result"]
            == "FAIL",
        )
        gate(
            "R7R7B_not_retested",
            summary["R7R7B_retested"]
            is False,
        )

        gate(
            "R7R7E_no_plume_fidelity_claim",
            summary["plume_fidelity_claim"]
            is False,
        )
        gate(
            "R7R7E_no_generalization_claim",
            summary["generalization_claim"]
            is False,
        )
        gate(
            "R7R7E_no_new_accuracy_claim",
            summary["new_accuracy_claim"]
            is False,
        )
        gate(
            "R7R7E_next_previously_unauthorized",
            summary["next"]["authorized"]
            is False,
        )

        gate(
            "R7R7E_outputs_not_modified",
            summary["R7R7E_outputs_modified"]
            is False,
        )

        # Internal numerical quality remains authoritative and is not
        # replaced by the external/full-physics fidelity contract.
        gate(
            "R7R7E_internal_mass_closure_within_future_floor",
            float(
                summary[
                    "maximum_mass_relative_closure"
                ]
            )
            <=
            MAX_INTERNAL_MASS_RELATIVE_CLOSURE,
            summary[
                "maximum_mass_relative_closure"
            ],
        )

        gate(
            "R7R7E_internal_EOS_closure_within_future_floor",
            float(
                summary[
                    "maximum_EOS_mass_relative_closure"
                ]
            )
            <=
            MAX_INTERNAL_EOS_RELATIVE_CLOSURE,
            summary[
                "maximum_EOS_mass_relative_closure"
            ],
        )

        gate(
            "R7R7E_post_capacity_excess_within_future_floor",
            float(
                summary[
                    "maximum_post_reconciliation_capacity_excess_kg"
                ]
            )
            <=
            MAX_POST_RECONCILIATION_CAPACITY_EXCESS_KG,
            summary[
                "maximum_post_reconciliation_capacity_excess_kg"
            ],
        )

        # ==============================================================
        # Freeze benchmark input/output authority requirements.
        # ==============================================================

        stage = "freeze_external_benchmark_acceptance_contract"

        benchmark_schema = {
            "protocol_id": PROTOCOL_ID,
            "benchmark_role": (
                "Independent external/full-physics reference for "
                "Foundation Case 0001 deployment validation."
            ),
            "benchmark_engine": {
                "required": True,
                "specific_engine_not_selected_by_AV1E": True,
                "recommended_if_available": (
                    "CMG full-physics reservoir simulation"
                ),
                "engine_name_required_in_future_manifest": True,
                "engine_version_required_in_future_manifest": True,
                "input_deck_SHA256_required": True,
                "output_bundle_SHA256_required": True,
                "run_log_SHA256_required": True,
            },
            "independence": {
                "must_not_use_C26_or_PAD_Stream_predictions_as_truth": True,
                "must_not_tune_benchmark_to_match_PAD_Stream": True,
                "must_not_retune_C26_after_benchmark_exposure": True,
                "must_not_change_R7R7E_mapback_after_benchmark_exposure": True,
                "benchmark_generated_from_same_physical_case": True,
            },
            "foundation_case_binding": {
                "source_foundation_SHA256": FOUNDATION_SHA,
                "grid_kji": GRID,
                "cell_dimensions_ft_xyz": [
                    DX_FT,
                    DY_FT,
                    DZ_FT,
                ],
                "target_days": CANONICAL_DAYS,
                "same_geology_required": True,
                "same_porosity_required": True,
                "same_well_locations_required": True,
                "same_well_controls_required": True,
                "same_gravity_setting_required": True,
                "same_relative_permeability_required": True,
                "same_capillary_pressure_model_required": True,
                "same_fluid_EOS_required_or_translation_documented": True,
                "same_initial_state_required": True,
            },
            "required_future_outputs": {
                "grid_total_saturation": {
                    "shape": [
                        9,
                        15,
                        50,
                        50,
                    ],
                    "dtype": (
                        "float32 or float64"
                    ),
                    "units": "fraction",
                },
                "stored_CO2_mass_kg": {
                    "shape": [9],
                    "units": "kg",
                },
                "aggregate_CO2_cut": {
                    "shape": [9],
                    "units": "fraction",
                },
                "producer_resolved_CO2_cut": {
                    "required": True,
                    "target_days": CANONICAL_DAYS,
                    "units": "fraction",
                },
                "producer_resolved_CO2_mass_rate_kg_day": {
                    "required": True,
                    "target_days": CANONICAL_DAYS,
                    "units": "kg/day",
                },
                "benchmark_mass_balance_diagnostics": {
                    "required": True,
                },
            },
            "comparison_frame": {
                "same_grid_required": True,
                "same_cell_ordering_required_or_exact_mapping_supplied": True,
                "same_target_days_required": True,
                "incremental_CO2_saturation_definition": (
                    "Sg_incremental = total_saturation - 0.20 "
                    "for PAD-Stream comparison when the benchmark "
                    "reports the same total-saturation convention."
                ),
                "visible_plume_threshold_incremental_CO2": (
                    VISIBLE_INCREMENTAL_CO2_THRESHOLD
                ),
                "breakthrough_CO2_cut_threshold": (
                    BREAKTHROUGH_CO2_CUT
                ),
            },
        }

        acceptance = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "prospective": True,
            "benchmark_results_seen_during_freeze": False,
            "benchmark_execution_performed": False,
            "PAD_Stream_model_inference_performed": False,
            "LP_execution_performed": False,
            "mapback_execution_performed": False,
            "training_or_retuning_performed": False,
            "R7R7E_outputs_modified": False,
            "R7R7E_scientific_result_changed": False,
            "scope": (
                "Foundation Case 0001 deployment fidelity against "
                "one independently generated external/full-physics benchmark."
            ),
            "hard_acceptance_gates": {
                "every_canonical_time_required": True,
                "grid_saturation_RMSE_max": (
                    MAX_GRID_SATURATION_RMSE
                ),
                "stored_CO2_mass_abs_relative_max": (
                    MAX_STORED_CO2_MASS_ABS_RELATIVE
                ),
                "visible_plume_Jaccard_min": (
                    MIN_VISIBLE_PLUME_JACCARD
                ),
                "plume_centroid_distance_m_max": (
                    MAX_PLUME_CENTROID_DISTANCE_M
                ),
                "aggregate_CO2_cut_abs_error_max": (
                    MAX_AGGREGATE_CO2_CUT_ABS_ERROR
                ),
                "breakthrough_classification_matches_at_all_canonical_times": True,
                "first_breakthrough_canonical_target_day_matches": True,
                "PAD_Stream_internal_mass_relative_closure_max": (
                    MAX_INTERNAL_MASS_RELATIVE_CLOSURE
                ),
                "PAD_Stream_internal_EOS_relative_closure_max": (
                    MAX_INTERNAL_EOS_RELATIVE_CLOSURE
                ),
                "PAD_Stream_post_reconciliation_capacity_excess_kg_max": (
                    MAX_POST_RECONCILIATION_CAPACITY_EXCESS_KG
                ),
                "grid_total_saturation_lower_bound": (
                    BACKGROUND_TOTAL_SATURATION
                ),
                "grid_total_saturation_upper_bound": (
                    MAX_TOTAL_SATURATION
                ),
            },
            "pass_semantics": {
                "all_hard_gates_must_pass": True,
                "averaging_across_days_cannot_rescue_a_failed_day": True,
                "producer_resolved_metrics_are_required_diagnostics": True,
                "no_post_hoc_threshold_change": True,
                "no_new_candidate_after_results": True,
            },
            "threshold_basis": {
                "grid_RMSE": (
                    "Absolute saturation tolerance fixed before external "
                    "benchmark exposure."
                ),
                "stored_mass": (
                    "Two-percent Foundation Case deployment tolerance fixed "
                    "before external benchmark exposure."
                ),
                "visible_plume_Jaccard": (
                    "Prospective plume-overlap requirement fixed before "
                    "external benchmark exposure."
                ),
                "centroid_distance": (
                    "One horizontal Cartesian-cell diagonal: "
                    f"{MAX_PLUME_CENTROID_DISTANCE_M:.12f} m."
                ),
                "aggregate_CO2_cut": (
                    "Two percentage-point absolute producer-response "
                    "tolerance fixed before external benchmark exposure."
                ),
                "breakthrough": (
                    "Inherited E36 event threshold of 1e-4 aggregate CO2 cut; "
                    "not newly selected in AV1-E."
                ),
                "universal_standard_claim": False,
                "project_specific_engineering_acceptance_contract": True,
            },
            "immutable_authorities": {
                "foundation_case_SHA256": FOUNDATION_SHA,
                "accepted_weights_SHA256": WEIGHTS_SHA,
                "normalization_SHA256": NORM_SHA,
                "R7R7E_integrated_state_SHA256": INTEGRATED_STATE_SHA,
                "R7R7E_outcome_freeze_protocol": R7R7E_FREEZE_PROTOCOL,
                "R7R3_result": "FAIL",
                "R7R6_result": "FAIL",
                "R7R7B_result": "FAIL",
                "R7R7B_retested": False,
            },
            "claims_not_yet_authorized": {
                "external_full_physics_fidelity": False,
                "final_deployment_acceptance": False,
                "generalization": False,
                "field_validation": False,
                "calibrated_dispersion_model": False,
            },
            "next": {
                "milestone": "POSTV16-AV1-F",
                "name": (
                    "One-Touch External Full-Physics Deployment "
                    "Acceptance Execution"
                ),
                "authorized": True,
                "condition": (
                    "Proceed only after one benchmark bundle satisfying "
                    "the frozen AV1-E benchmark schema is available and "
                    "its engine/version/input/output provenance is sealed "
                    "before comparison."
                ),
                "retuning_before_execution_authorized": False,
                "alternate_thresholds_authorized": False,
            },
        }

        claim_boundary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "authorized_claim": (
                "The external/full-physics deployment acceptance protocol "
                "for Foundation Case 0001 has been prospectively frozen "
                "before exposure to the benchmark result."
            ),
            "R7R7E_case_specific_PASS_preserved": True,
            "R7R7E_upgraded_to_plume_fidelity_PASS": False,
            "external_benchmark_result_available_in_AV1E": False,
            "final_deployment_accepted_in_AV1E": False,
            "generalization_claim": False,
            "field_scale_validation_claim": False,
            "benchmark_engine_selected_in_AV1E": False,
            "CMG_required": False,
            "CMG_recommended_if_available": True,
            "acceptance_thresholds_are_project_specific": True,
            "thresholds_are_universal_standards": False,
        }

        threshold_rows = [
            {
                "metric": "grid_saturation_RMSE",
                "operator": "<=",
                "threshold": MAX_GRID_SATURATION_RMSE,
                "units": "absolute saturation fraction",
                "hard_gate": True,
                "applies": "each of 9 canonical times",
            },
            {
                "metric": "stored_CO2_mass_abs_relative",
                "operator": "<=",
                "threshold": MAX_STORED_CO2_MASS_ABS_RELATIVE,
                "units": "fraction",
                "hard_gate": True,
                "applies": "each of 9 canonical times",
            },
            {
                "metric": "visible_plume_Jaccard",
                "operator": ">=",
                "threshold": MIN_VISIBLE_PLUME_JACCARD,
                "units": "dimensionless",
                "hard_gate": True,
                "applies": "each of 9 canonical times",
            },
            {
                "metric": "plume_centroid_distance",
                "operator": "<=",
                "threshold": MAX_PLUME_CENTROID_DISTANCE_M,
                "units": "m",
                "hard_gate": True,
                "applies": "each of 9 canonical times",
            },
            {
                "metric": "aggregate_CO2_cut_abs_error",
                "operator": "<=",
                "threshold": MAX_AGGREGATE_CO2_CUT_ABS_ERROR,
                "units": "fraction",
                "hard_gate": True,
                "applies": "each of 9 canonical times",
            },
            {
                "metric": "breakthrough_classification_match",
                "operator": "==",
                "threshold": True,
                "units": "boolean",
                "hard_gate": True,
                "applies": "each of 9 canonical times",
            },
            {
                "metric": "first_breakthrough_canonical_target_day_match",
                "operator": "==",
                "threshold": True,
                "units": "boolean",
                "hard_gate": True,
                "applies": "Foundation Case 0001",
            },
        ]

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "R7R7E_outcome_freeze_bound": True,
            "R7R7E_scientific_PASS_preserved": True,
            "R7R7E_plume_fidelity_claim_remains_false": True,
            "external_benchmark_results_read": False,
            "external_benchmark_execution_performed": False,
            "model_inference_performed": False,
            "LP_execution_performed": False,
            "mapback_execution_performed": False,
            "training_or_retuning_performed": False,
            "thresholds_frozen_before_benchmark_exposure": True,
            "benchmark_engine_specific_identity_deferred_to_future_sealed_manifest": True,
            "hard_gate_count": len(threshold_rows),
            "target_days": CANONICAL_DAYS,
            "grid": GRID,
            "foundation_SHA256": FOUNDATION_SHA,
            "next": acceptance["next"],
        }

        immutable_publish(
            out,
            {
                "PAD_Stream_POSTV16_AV1_E_Summary.json":
                    json_bytes(summary_out),
                "POSTV16_AV1_E_Frozen_External_Full_Physics_Acceptance_Contract.json":
                    json_bytes(acceptance),
                "POSTV16_AV1_E_Frozen_Benchmark_Authority_Schema.json":
                    json_bytes(benchmark_schema),
                "POSTV16_AV1_E_Frozen_Claim_Boundary.json":
                    json_bytes(claim_boundary),
                "POSTV16_AV1_E_Frozen_Acceptance_Thresholds.csv":
                    csv_bytes(threshold_rows),
                "POSTV16_AV1_E_Final_Gate_Matrix.csv":
                    csv_bytes(
                        [
                            {
                                "gate": key,
                                **value,
                            }
                            for key, value
                            in gates.items()
                        ]
                    ),
            },
        )

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name
                !=
                "POSTV16_AV1_E_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV1_E_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print("\n" + "=" * 196)
        print("POSTV16-AV1-E: PASS")
        print("=" * 196)
        print(
            f"{'Status':112}: "
            f"{STATUS_PASS}"
        )
        print(
            f"{'Protocol':112}: "
            f"{PROTOCOL_ID}"
        )
        print(
            f"{'R7-R7E outcome freeze bound':112}: True"
        )
        print(
            f"{'External benchmark outputs read':112}: False"
        )
        print(
            f"{'Benchmark execution in AV1-E':112}: False"
        )
        print(
            f"{'Model inference / LP / mapback in AV1-E':112}: "
            "False / False / False"
        )
        print(
            f"{'Training / retuning in AV1-E':112}: False"
        )
        print(
            f"{'Grid saturation RMSE max':112}: "
            f"{MAX_GRID_SATURATION_RMSE}"
        )
        print(
            f"{'Stored CO2 mass abs-relative max':112}: "
            f"{MAX_STORED_CO2_MASS_ABS_RELATIVE}"
        )
        print(
            f"{'Visible plume Jaccard min':112}: "
            f"{MIN_VISIBLE_PLUME_JACCARD}"
        )
        print(
            f"{'Plume centroid distance max [m]':112}: "
            f"{MAX_PLUME_CENTROID_DISTANCE_M:.12f}"
        )
        print(
            f"{'Aggregate CO2-cut abs error max':112}: "
            f"{MAX_AGGREGATE_CO2_CUT_ABS_ERROR}"
        )
        print(
            f"{'Breakthrough event threshold inherited':112}: "
            f"{BREAKTHROUGH_CO2_CUT}"
        )
        print(
            f"{'R7-R7E upgraded to plume-fidelity PASS':112}: False"
        )
        print(
            f"{'Final deployment accepted in AV1-E':112}: False"
        )
        print(
            f"{'Next milestone authorized':112}: True"
        )
        print(
            f"{'NEXT':112}: POSTV16-AV1-F — one-touch external/full-physics deployment acceptance execution"
        )
        print("=" * 196)

        return 0

    except Exception as exc:
        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "benchmark_results_read": False,
            "benchmark_execution_performed": False,
            "model_inference_performed": False,
            "LP_execution_performed": False,
            "mapback_execution_performed": False,
            "training_or_retuning_performed": False,
            "R7R7E_scientific_result_changed": False,
            "next_milestone_authorized": False,
            "next_action": (
                "Audit only the AV1-E prospective contract freeze. "
                "Do not inspect a benchmark result under an unfrozen or "
                "partially frozen acceptance contract."
            ),
        }

        data = json_bytes(report)

        p = (
            blocked /
            "POSTV16_AV1_E_Blocked_Report.json"
        )

        if (
            p.exists()
            and p.read_bytes() != data
        ):
            suffix = hashlib.sha256(
                data
            ).hexdigest()[:12]
            p = (
                blocked /
                f"POSTV16_AV1_E_Blocked_Report_{suffix}.json"
            )

        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 196)
        print("POSTV16-AV1-E: BLOCKED")
        print("=" * 196)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", p)
        print(
            "No benchmark result was read and no subsequent "
            "acceptance execution is authorized from a blocked freeze."
        )

        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )
    p.add_argument(
        "--self-test",
        action="store_true",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
