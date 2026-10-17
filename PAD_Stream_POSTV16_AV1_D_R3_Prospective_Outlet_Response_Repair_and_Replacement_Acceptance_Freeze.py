#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

MILESTONE = "POSTV16-AV1-D-R3"
STATUS_PASS = (
    "AV1DR3_PROSPECTIVE_OUTLET_RESPONSE_REPAIR_AND_"
    "NEW_GEOLOGY0030_ACCEPTANCE_AUTHORITY_FROZEN"
)
STATUS_BLOCKED = "AV1DR3_REPAIR_ACCEPTANCE_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_R2_COMMIT = "5c63dcaf75074c6f215dec34a9062c46c0034b07"

R2_RUNNER = (
    "PAD_Stream_POSTV16_AV1_D_R2_"
    "Breakthrough_False_Positive_Localization_and_Test_Retirement_Audit.py"
)
R2_RUNNER_BLOB = "24cbe2e2ee7d5b71dc580e8cebadd5fdd7e45f30"

C25_RUNNER = (
    "PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_"
    "Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
)
C25_BLOB = "0a4740b95c2b5e5d15db3137414e663e1e9b6282"

C26_RUNNER = (
    "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_"
    "Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
)
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

D11A_RUNNER = (
    "PAD_Stream_V16D11A_Explicit_Versioned_Spectral_Ensemble_"
    "Recipe_1p1_Provenance_Repair_and_Binding_Audit.py"
)
D11A_BLOB = "a26dabfd89407cd60ccbdc9e5ed80a07cc3f9c67"

D22_RUNNER = (
    "PAD_Stream_V16D22_Versioned_InjectionRate_ProducerBHP_"
    "ControlSpace_Design_and_New_FoundationCase_Registry_Contract.py"
)
D22_BLOB = "d1c4a9e737ce59ed4450dbbb61859247986ceada"

D23_RUNNER = (
    "PAD_Stream_V16D23_Generate_and_Certify_Fresh_"
    "Recipe1p1_Geologies_0026_0029.py"
)
D23_BLOB = "e4c9fa6988040b6a2034717b12ea1831eb345e95"

D36R1_RUNNER = (
    "PAD_Stream_V16D36_R1_EXP_CS1_Post_OOD_Scientific_"
    "Interpretation_and_Closure_Recovery.py"
)
D36R1_BLOB = "063830607a9b57face17666530f274a4deaedc69"

SOURCE_BLOBS = {
    R2_RUNNER: R2_RUNNER_BLOB,
    C25_RUNNER: C25_BLOB,
    C26_RUNNER: C26_BLOB,
    D11A_RUNNER: D11A_BLOB,
    D22_RUNNER: D22_BLOB,
    D23_RUNNER: D23_BLOB,
    D36R1_RUNNER: D36R1_BLOB,
}

R2_OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R2_Breakthrough_False_Positive_Localization"
)
R2_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R2_Summary.json"
R2_DECISION = "POSTV16_AV1_D_R2_Decision_Contract.json"
R2_LOCALIZATION = "POSTV16_AV1_D_R2_Day30_Localization.json"
R2_RANKING = "POSTV16_AV1_D_R2_Day30_Test_Streamline_Contribution_Ranking.csv"
R2_MANIFEST = "POSTV16_AV1_D_R2_Artifact_Manifest.csv"
R2_STATUS = (
    "AV1DR2_BREAKTHROUGH_FALSE_POSITIVE_LOCALIZED_"
    "ORIGINAL_LOCKED_TEST_RETIRED_FROM_FINAL_ACCEPTANCE"
)

D11A_CONTRACT = (
    Path("output")
    / "V16_D11A_SPECTRAL_ENSEMBLE_RECIPE_1P1_PROVENANCE_REPAIR"
    / "V16D11A_Spectral_Ensemble_Recipe_1p1_Contract.json"
)
D11A_CONTRACT_BLOB = "b3acf7ddad07cabaed2999a0d4b6046055db15a3"

D22_CONTRACT = (
    Path("output")
    / "V16_D22_CONTROL_SPACE_DESIGN_FOUNDATION_CASE_REGISTRY"
    / "V16D22_Control_Space_Recipe_1.0_and_Foundation_Case_Registry.json"
)
D22_CONTRACT_BLOB = "c4abc55e042e0a46d870e63b467e8745e5ac981a"

D36R1_INTERPRETATION = (
    Path("output")
    / "V16_D36_R1_EXP_CS1_POST_OOD_SCIENTIFIC_INTERPRETATION_AND_CLOSURE_RECOVERY"
    / "V16D36R1_EXP_CS1_Post_OOD_Interpretation.json"
)
D36R1_INTERPRETATION_BLOB = "9f7fab64d167c9018d70573c14a011305ce2c923"

C18R_NAME = "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA = "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"

C19_NAME = "V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA = "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"

C26_WEIGHTS_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_A3R3R_C26_Weight_State_Compatibility_Reconstruction"
    / "V16C26_EXP2_Exact_Embedded.weights.h5"
)
C26_WEIGHTS_SHA = "4bf0bde8a68d400a7eee33735ca85b4524b70d14be367f278f7276533443f8f9"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R3_Prospective_Repair_and_Replacement_Acceptance_Freeze"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R3_BLOCKED"
)

BREAKTHROUGH_GAS_CUT = 1.0e-4

REPLACEMENT_GEOLOGY_ID = "0030"
REPLACEMENT_GEOLOGY_NUM = 30
SEED_BASE = 160400
SEED_STRIDE = 7919
REPLACEMENT_SEED = SEED_BASE + (REPLACEMENT_GEOLOGY_NUM - 2) * SEED_STRIDE
EXPECTED_REPLACEMENT_SEED = 382132

REPLACEMENT_INJECTION_TPD = 500.0
REPLACEMENT_PRODUCER_BHP_PSI = 2000.0
TARGET_DAYS = [30, 60, 100, 150, 250, 365, 500, 750, 1000]

REPAIR_CANDIDATES = [
    {
        "candidate_id": "R3A_TERMINAL",
        "lambda_terminal": 1.0,
        "lambda_outlet_response": 0.0,
    },
    {
        "candidate_id": "R3B_RESPONSE",
        "lambda_terminal": 0.0,
        "lambda_outlet_response": 1.0,
    },
    {
        "candidate_id": "R3C_TERMINAL_PLUS_RESPONSE",
        "lambda_terminal": 1.0,
        "lambda_outlet_response": 1.0,
    },
]


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
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    import io
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def find_by_name_and_sha(
    roots: list[Path],
    name: str,
    expected_sha: str,
) -> Path:
    hits: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p) == expected_sha:
                    hits.append(p)
            except OSError:
                pass
    if not hits:
        raise GateError(f"artifact_not_found_with_exact_sha:{name}:{expected_sha}")
    return sorted(set(hits), key=lambda p: (len(str(p)), str(p)))[0]


def verify_manifest(directory: Path, manifest_name: str) -> dict[str, str]:
    rows = read_csv(directory / manifest_name)
    manifest = {r["file"]: r["sha256"] for r in rows}
    for name, expected in manifest.items():
        p = directory / name
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{name}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(
                f"manifest_SHA_mismatch:{name}:{actual}:{expected}"
            )
    return manifest


def specific_case0030_artifacts(root: Path) -> list[str]:
    patterns = [
        "*Geology*0030*",
        "*Foundation*0030*",
        "*Case_0030*",
        "*case_0030*",
    ]
    hits: set[str] = set()
    for pattern in patterns:
        for p in root.rglob(pattern):
            if p.is_file():
                hits.add(str(p))
    return sorted(hits)


def self_test() -> None:
    seed = SEED_BASE + (30 - 2) * SEED_STRIDE
    if seed != EXPECTED_REPLACEMENT_SEED:
        raise RuntimeError("replacement_seed_formula")
    if len(REPAIR_CANDIDATES) != 3:
        raise RuntimeError("repair_candidate_count")
    ids = [x["candidate_id"] for x in REPAIR_CANDIDATES]
    if len(set(ids)) != len(ids):
        raise RuntimeError("repair_candidate_ids_not_unique")
    print("POSTV16-AV1-D-R3 self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    print("=" * 168)
    print("POSTV16-AV1-D-R3 — PROSPECTIVE OUTLET-RESPONSE REPAIR + REPLACEMENT ACCEPTANCE FREEZE")
    print("=" * 168)
    print("CONTRACT ONLY. NO TRAINING. NO RETUNING. NO NEW MODEL CHECKPOINT.")
    print("NO GEOLOGY0030 GENERATION. NO GEOLOGY0030 TARGET GENERATION OR OPENING.")
    print("THE RETIRED C19 TEST MAY BE USED ONLY FOR DIAGNOSTIC/REGRESSION REPORTING.")
    print("ALL REPAIR MODEL SELECTION IS TRAIN/VALIDATION ONLY.")
    print("FINAL EVENT ACCEPTANCE IS RESERVED FOR NEW GEOLOGY0030 AFTER THE MODEL IS FROZEN.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_AV1D_R2_commit",
            parent == PARENT_R2_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fname, blob in SOURCE_BLOBS.items():
            p = root / fname
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fname).stem}_git_blob_exact",
                actual == blob,
                actual,
            )

        for p, expected_blob, label in (
            (root / D11A_CONTRACT, D11A_CONTRACT_BLOB, "D11A_contract"),
            (root / D22_CONTRACT, D22_CONTRACT_BLOB, "D22_contract"),
            (
                root / D36R1_INTERPRETATION,
                D36R1_INTERPRETATION_BLOB,
                "D36R1_interpretation",
            ),
        ):
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{label}_git_blob_exact", actual == expected_blob, actual)

        stage = "R2_binding"

        r2_out = drive / R2_OUT_REL
        gate("R2_output_directory_present", r2_out.is_dir(), str(r2_out))
        r2_manifest = verify_manifest(r2_out, R2_MANIFEST)
        gate("R2_manifest_internal_SHA_closure", True, len(r2_manifest))

        r2_summary = load_json(r2_out / R2_SUMMARY)
        r2_decision = load_json(r2_out / R2_DECISION)
        r2_local = load_json(r2_out / R2_LOCALIZATION)
        r2_rank = read_csv(r2_out / R2_RANKING)

        gate(
            "R2_status_exact",
            r2_summary.get("status") == R2_STATUS,
            r2_summary.get("status"),
        )
        gate(
            "R2_false_positive_confirmed",
            r2_decision.get("breakthrough_false_positive_confirmed") is True,
        )
        gate(
            "R2_critical_day_30",
            float(r2_decision.get("critical_day")) == 30.0,
            r2_decision.get("critical_day"),
        )
        gate(
            "R2_existing_threshold_unchanged",
            float(r2_decision.get("existing_breakthrough_threshold"))
            == BREAKTHROUGH_GAS_CUT,
            r2_decision.get("existing_breakthrough_threshold"),
        )
        gate(
            "R2_original_test_retired",
            "RETIRED_FROM_FINAL_INDEPENDENT_ACCEPTANCE"
            in str(r2_decision.get("original_locked_test_status_after_diagnosis", "")),
            r2_decision.get("original_locked_test_status_after_diagnosis"),
        )
        gate(
            "R2_replacement_acceptance_required",
            r2_decision.get("replacement_final_acceptance_required") is True,
        )
        gate(
            "R2_training_not_performed",
            r2_summary.get("training_or_retuning_performed") is False,
        )
        gate(
            "R2_day30_one_streamline_sufficient",
            int(
                r2_local[
                    "minimum_largest_positive_contributors_needed_to_cross_threshold"
                ]
            ) == 1,
            r2_local[
                "minimum_largest_positive_contributors_needed_to_cross_threshold"
            ],
        )
        gate(
            "R2_day30_rank_rows_161",
            len(r2_rank) == 161,
            len(r2_rank),
        )

        stage = "training_authority_binding"

        c18r = find_by_name_and_sha(
            [root, drive], C18R_NAME, C18R_SHA
        )
        c19 = find_by_name_and_sha(
            [root, drive], C19_NAME, C19_SHA
        )
        gate("C18R_exact_SHA", sha256_file(c18r) == C18R_SHA, str(c18r))
        gate("C19_exact_SHA", sha256_file(c19) == C19_SHA, str(c19))

        weights = drive / C26_WEIGHTS_REL
        gate("C26_exact_initial_weights_present", weights.is_file(), str(weights))
        actual_weight_sha = sha256_file(weights) if weights.is_file() else "missing"
        gate(
            "C26_exact_initial_weights_SHA",
            actual_weight_sha == C26_WEIGHTS_SHA,
            actual_weight_sha,
        )

        c25_text = (root / C25_RUNNER).read_text(encoding="utf-8")
        gate(
            "C25_original_lambda_phys_0p01_bound",
            '"lambda_phys":0.01' in c25_text,
        )
        gate(
            "C25_terminal_node_excluded_from_PDE_bound",
            '"interior_mask":"j=1..199"' in c25_text
            and '"boundary_nodes_in_PDE_loss":False' in c25_text,
        )
        gate(
            "C25_supervised_profile_MSE_bound",
            '"data":"mean squared Sw error on supervised profiles"' in c25_text,
        )

        stage = "replacement_authority_provenance"

        d11a = load_json(root / D11A_CONTRACT)
        d22 = load_json(root / D22_CONTRACT)
        d36 = load_json(root / D36R1_INTERPRETATION)

        gate(
            "D11A_recipe_id_exact",
            d11a["recipe_1p1"]["recipe_id"]
            == "V16D_SPECTRAL_ENSEMBLE_RECIPE_1.1",
            d11a["recipe_1p1"]["recipe_id"],
        )
        gate(
            "D11A_algorithm_spectral_not_SGSim",
            "spectral Gaussian random-field" in d11a["recipe_1p1"]["algorithm"],
            d11a["recipe_1p1"]["algorithm"],
        )
        gate(
            "D22_seed_rule_exact",
            d22["geology"]["seed_rule"]
            == "160400 + (geology_case_id - 2)*7919",
            d22["geology"]["seed_rule"],
        )
        gate(
            "D22_reference_control_exact",
            float(d22["reference_control"]["CO2_injection_tonnes_per_day"])
            == REPLACEMENT_INJECTION_TPD
            and float(d22["reference_control"]["producer_BHP_psi"])
            == REPLACEMENT_PRODUCER_BHP_PSI,
            d22["reference_control"],
        )
        gate(
            "D36_geology0029_consumed",
            d36["experiment_closure"]["geology0029_consumed"] is True,
        )
        gate(
            "D36_geology0029_not_reusable_as_unseen",
            d36["experiment_closure"][
                "geology0029_may_not_be_reused_as_unseen_test"
            ] is True,
        )
        gate(
            "D36_future_learning_requires_new_locked_test",
            d36["experiment_closure"][
                "future_new_learning_experiment_requires_new_locked_test"
            ] is True,
        )

        computed_seed = (
            SEED_BASE
            + (REPLACEMENT_GEOLOGY_NUM - 2) * SEED_STRIDE
        )
        gate(
            "replacement_geology0030_seed_exact",
            computed_seed == EXPECTED_REPLACEMENT_SEED,
            computed_seed,
        )

        case0030_hits = specific_case0030_artifacts(root)
        gate(
            "no_preexisting_geology0030_artifact_in_repository",
            len(case0030_hits) == 0,
            case0030_hits,
        )

        stage = "contract_freeze"

        repair_contract = {
            "experiment_id": "POSTV16_AV1_OUTLET_RESPONSE_REPAIR_1",
            "purpose": (
                "Repair the diagnosed early-time outlet/producer-response tail "
                "without altering the already-accepted 201->200 representation."
            ),
            "initialization": {
                "architecture": "EXACT_C26_ARCHITECTURE_UNCHANGED",
                "initial_weights_sha256": C26_WEIGHTS_SHA,
                "parameter_count": 52033,
            },
            "data_firewall": {
                "training_partition": "C19 sample_partition_code == 0 ONLY",
                "validation_partition": "C19 sample_partition_code == 1 ONLY",
                "retired_test_partition": (
                    "C19 sample_partition_code == 2; DIAGNOSTIC/REGRESSION ONLY; "
                    "NO GRADIENT, LOSS-WEIGHT SELECTION, CHECKPOINT SELECTION, "
                    "EARLY STOPPING, THRESHOLD TUNING, OR FINAL ACCEPTANCE"
                ),
                "replacement_final_acceptance": (
                    "V16D Recipe1.1 geology0030 reference-control case; sealed "
                    "until the repaired model/checkpoint is frozen"
                ),
            },
            "base_objective": {
                "L_profile": "mean squared saturation error over all 201 nodes",
                "lambda_profile": 1.0,
                "L_phys": "exact frozen C25 adjacent-time interior PDE residual",
                "lambda_phys": 0.01,
                "PDE_nodes": "j=1..199; unchanged from C25",
            },
            "repair_terms": {
                "L_terminal": (
                    "mean((S_pred[:,-1]-S_true[:,-1])^2) on TRAIN only"
                ),
                "L_outlet_response": (
                    "flow-weighted mean((fw(S_pred[:,-1])-fw(S_true[:,-1]))^2) "
                    "using frozen streamline flow weights, normalized by mean "
                    "training-streamline weight; TRAIN only"
                ),
                "fractional_flow_constitutive_law": (
                    "same frozen Corey/fractional-flow law used by SG7A/E37A"
                ),
                "new_breakthrough_threshold_in_training_loss": False,
            },
            "candidate_family": REPAIR_CANDIDATES,
            "candidate_policy": {
                "all_candidates_start_from_exact_same_C26_weights": True,
                "all_candidates_same_optimizer_and_epoch_budget": (
                    "Use C26 optimizer/epoch/early-stopping mechanics unchanged "
                    "except validation selection metric below."
                ),
                "no_architecture_change": True,
                "no_predictor_feature_change": True,
                "no_C25_physics_weight_change": True,
                "no_candidate_added_after_validation_results": True,
            },
            "validation_selection": {
                "uses_validation_partition_only": True,
                "lexicographic_order": [
                    (
                        "minimum validation flow-weighted outlet fractional-flow RMSE"
                    ),
                    "minimum validation terminal saturation RMSE",
                    "minimum validation full-profile RMSE",
                    "minimum validation frozen total objective",
                ],
                "retired_test_used": False,
                "breakthrough_threshold_used_for_candidate_selection": False,
            },
            "post_selection": {
                "selected_checkpoint_frozen_before_any_replacement_test_opening": True,
                "retired_test_may_be_run_after_freeze": (
                    "YES, but only as labelled regression/diagnostic evidence"
                ),
                "retired_test_cannot_accept_or_reject_final_model": True,
            },
        }

        replacement_contract = {
            "authority_id": "POSTV16_AV1_REPLACEMENT_LOCKED_ACCEPTANCE_GEOLOGY0030",
            "geology_id": REPLACEMENT_GEOLOGY_ID,
            "seed": EXPECTED_REPLACEMENT_SEED,
            "seed_derivation": (
                "160400 + (30 - 2)*7919 = 382132"
            ),
            "geology_recipe": "V16D_SPECTRAL_ENSEMBLE_RECIPE_1.1",
            "geology_recipe_semantics": (
                "deterministic periodic spectral Gaussian random-field sampler; "
                "NOT SGS/SGSim"
            ),
            "controls": {
                "CO2_injection_tonnes_per_day": REPLACEMENT_INJECTION_TPD,
                "producer_BHP_psi": REPLACEMENT_PRODUCER_BHP_PSI,
                "well_geometry": "FROZEN_V15_FIVE_SPOT",
            },
            "transport": {
                "source_authentic_stage4": True,
                "nodes": 201,
                "target_days": TARGET_DAYS,
                "Pollock_primary": True,
                "same_C17_constitutive_parameters": True,
            },
            "generation_firewall": {
                "case_generation_may_begin_only_after_R3_freeze": True,
                "technical_generation_failure": (
                    "BLOCK; do not substitute geology0031 or any other seed"
                ),
                "visual_or_statistical_rejection": "PROHIBITED",
                "target_values_may_be_generated_and_SHA_sealed_before_training": True,
                "target_arrays_or_performance_metrics_may_be_opened_before_checkpoint_freeze": False,
                "model_inference_on_geology0030_before_checkpoint_freeze": False,
            },
            "one_touch_final_evaluation": {
                "model_checkpoint_must_be_frozen_first": True,
                "all_1078_streamlines": True,
                "all_9_target_days": True,
                "no_case_time_streamline_or_node_suppression": True,
                "no_adaptation_after_opening": True,
                "no_threshold_tuning_after_opening": True,
            },
            "primary_event_acceptance": {
                "threshold_source": "EXISTING_E36_BREAKTHROUGH_GAS_CUT",
                "aggregate_CO2_cut_threshold": BREAKTHROUGH_GAS_CUT,
                "require_aggregate_classification_match_at_all_9_times": True,
                "require_aggregate_first_breakthrough_target_day_match": True,
                "require_each_producer_classification_match_at_all_9_times": True,
            },
            "structural_acceptance": {
                "finite_predictions": True,
                "saturation_bounds_0p2_0p8": True,
                "E37A_201_to_200_mass_projection_closure": True,
                "no_saturation_averaging": True,
            },
            "descriptive_not_gate": [
                "profile RMSE",
                "profile MAE",
                "max absolute saturation error",
                "component-mass error",
                "outlet saturation error",
                "producer CO2-cut absolute error",
            ],
            "claim_limit": (
                "Passing geology0030 accepts the repaired outlet/breakthrough "
                "event behavior for this prospectively frozen independent case. "
                "It does NOT by itself authorize the unresolved Cartesian "
                "grid-saturation plume claim."
            ),
        }

        experiment_decision = {
            "R2_diagnosis_accepted": True,
            "representation_repair_required": False,
            "outlet_response_repair_authorized": True,
            "training_authorized_in_R3": False,
            "new_checkpoint_created_in_R3": False,
            "geology0030_generated_in_R3": False,
            "geology0030_opened_in_R3": False,
            "retired_test_final_acceptance_authorized": False,
            "replacement_acceptance_authority_frozen": True,
            "replacement_geology": REPLACEMENT_GEOLOGY_ID,
            "replacement_seed": EXPECTED_REPLACEMENT_SEED,
            "next": (
                "POSTV16-AV1-D-R3A — generate/certify geology0030 reference-control "
                "physics + source-authentic Stage4 targets and seal them without "
                "model inference or target inspection; then R3B may execute the "
                "frozen train/validation-only repair."
            ),
        }

        gate("repair_candidate_count_exact_3", len(REPAIR_CANDIDATES) == 3)
        gate(
            "repair_all_candidates_architecture_unchanged",
            repair_contract["candidate_policy"]["no_architecture_change"] is True,
        )
        gate(
            "repair_retired_test_excluded_from_selection",
            repair_contract["validation_selection"]["retired_test_used"] is False,
        )
        gate(
            "repair_no_new_breakthrough_threshold_in_loss",
            repair_contract["repair_terms"][
                "new_breakthrough_threshold_in_training_loss"
            ] is False,
        )
        gate(
            "replacement_case_exact_0030",
            replacement_contract["geology_id"] == "0030",
            replacement_contract["geology_id"],
        )
        gate(
            "replacement_case_seed_exact_382132",
            replacement_contract["seed"] == 382132,
            replacement_contract["seed"],
        )
        gate(
            "replacement_case_reference_control_only",
            replacement_contract["controls"]["CO2_injection_tonnes_per_day"]
            == 500.0
            and replacement_contract["controls"]["producer_BHP_psi"] == 2000.0,
            replacement_contract["controls"],
        )
        gate(
            "replacement_test_sealed_until_checkpoint_freeze",
            replacement_contract["generation_firewall"][
                "model_inference_on_geology0030_before_checkpoint_freeze"
            ] is False
            and replacement_contract["generation_firewall"][
                "target_arrays_or_performance_metrics_may_be_opened_before_checkpoint_freeze"
            ] is False,
        )
        gate(
            "replacement_test_no_seed_substitution",
            "BLOCK" in replacement_contract["generation_firewall"][
                "technical_generation_failure"
            ],
        )
        gate("no_training_in_R3", True)
        gate("no_model_inference_in_R3", True)
        gate("no_geology_generation_in_R3", True)
        gate("no_threshold_change_in_R3", True)

        files = {
            "PAD_Stream_POSTV16_AV1_D_R3_Summary.json": json_bytes({
                "milestone": MILESTONE,
                "status": STATUS_PASS,
                "repository_head": head,
                "repository_parent": parent,
                "R2_day30_truth_cut": r2_local["truth_aggregate_CO2_cut"],
                "R2_day30_heldout_cut": r2_local["heldout_aggregate_CO2_cut"],
                "R2_minimum_contributors_to_cross_threshold": r2_local[
                    "minimum_largest_positive_contributors_needed_to_cross_threshold"
                ],
                "repair_contract": repair_contract,
                "replacement_acceptance_contract": replacement_contract,
                "decision": experiment_decision,
            }),
            "POSTV16_AV1_D_R3_Repair_Protocol.json": json_bytes(
                repair_contract
            ),
            "POSTV16_AV1_D_R3_Replacement_Acceptance_Authority.json": json_bytes(
                replacement_contract
            ),
            "POSTV16_AV1_D_R3_Experiment_Decision.json": json_bytes(
                experiment_decision
            ),
            "POSTV16_AV1_D_R3_Repair_Candidate_Registry.csv": csv_bytes(
                REPAIR_CANDIDATES
            ),
            "POSTV16_AV1_D_R3_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV1_D_R3_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(
            out,
            {
                "POSTV16_AV1_D_R3_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R3: PASS")
        print("=" * 168)
        print(f"{'Status':86}: {STATUS_PASS}")
        print(f"{'Repair architecture':86}: EXACT C26, unchanged")
        print(f"{'Repair initialization':86}: exact C26 embedded weights")
        print(
            f"{'Repair candidates':86}: "
            f"{[x['candidate_id'] for x in REPAIR_CANDIDATES]}"
        )
        print(
            f"{'Training / validation use':86}: "
            "C19 TRAIN / VALIDATION only"
        )
        print(
            f"{'Original C19 test role':86}: "
            "RETIRED — diagnostics/regression only"
        )
        print(
            f"{'Replacement final geology / seed':86}: "
            f"0030 / {EXPECTED_REPLACEMENT_SEED}"
        )
        print(
            f"{'Replacement controls':86}: "
            f"{REPLACEMENT_INJECTION_TPD:.0f} t/day / "
            f"{REPLACEMENT_PRODUCER_BHP_PSI:.0f} psi"
        )
        print(
            f"{'Final event threshold':86}: "
            f"{BREAKTHROUGH_GAS_CUT:.1e} (existing E36; unchanged)"
        )
        print(f"{'Training performed':86}: False")
        print(f"{'Geology0030 generated/opened':86}: False / False")
        print(
            f"{'NEXT':86}: POSTV16-AV1-D-R3A — generate and seal geology0030 authority"
        )
        print("=" * 168)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "training_or_retuning": False,
            "geology0030_generated": False,
            "next_action": (
                "Audit only the failed R3 gate(s). Do not train and do not "
                "generate/open the replacement acceptance case."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R3_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R3_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R3: BLOCKED")
        print("=" * 168)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", p)
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
