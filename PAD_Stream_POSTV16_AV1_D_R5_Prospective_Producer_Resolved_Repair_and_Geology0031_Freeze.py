#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
from typing import Any

MILESTONE = "POSTV16-AV1-D-R5"
STATUS_PASS = (
    "AV1DR5_PRODUCER_RESOLVED_REPAIR_AND_GEOLOGY0031_INDEPENDENT_"
    "ACCEPTANCE_PROTOCOL_PROSPECTIVELY_FROZEN"
)
STATUS_BLOCKED = "AV1DR5_PROSPECTIVE_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R4_COMMIT = "3d87d1b397305e01e380e7f1fca3ad1b09da4ac1"

R4 = "PAD_Stream_POSTV16_AV1_D_R4_R3C_Failure_Closure_and_Producer_Localization.py"
R4_BLOB = "c49bb74157654042cb1a0f654ebaf3f2ef2877b0"

R3B = "PAD_Stream_POSTV16_AV1_D_R3B_Frozen_TrainValidation_Outlet_Response_Repair_Execution.py"
R3B_BLOB = "787fe69e6631a1d294c17e791ab82aa4ab963c10"

R3C = "PAD_Stream_POSTV16_AV1_D_R3C_One_Touch_Final_Geology0030_Acceptance.py"
R3C_BLOB = "578accd65e5abd6f40e8c898c9bd79b43008d7d9"

R7E = "PAD_Stream_V16AR7E_Producer_Identity_Scope_Limitation_Foundation_Case_Freeze_Decision.py"
R7E_BLOB = "ae6eb91e6c8a1ae867cd2007f058c49b3c076826"

D11A = "PAD_Stream_V16D11A_Explicit_Versioned_Spectral_Ensemble_Recipe_1p1_Provenance_Repair_and_Binding_Audit.py"
D11A_BLOB = "a26dabfd89407cd60ccbdc9e5ed80a07cc3f9c67"

D22 = "PAD_Stream_V16D22_Versioned_InjectionRate_ProducerBHP_ControlSpace_Design_and_New_FoundationCase_Registry_Contract.py"
D22_BLOB = "d1c4a9e737ce59ed4450dbbb61859247986ceada"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

C25 = "PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
C25_BLOB = "0a4740b95c2b5e5d15db3137414e663e1e9b6282"

C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

SOURCE_BLOBS = {
    R4: R4_BLOB,
    R3B: R3B_BLOB,
    R3C: R3C_BLOB,
    R7E: R7E_BLOB,
    D11A: D11A_BLOB,
    D22: D22_BLOB,
    R2: R2_BLOB,
    C25: C25_BLOB,
    C26: C26_BLOB,
}

R7E_CONTRACT = (
    Path("output")
    / "V16_A_R7E_PRODUCER_SCOPE_FREEZE_DECISION"
    / "V16AR7E_Producer_Identity_Scope_Contract.json"
)
R7E_CONTRACT_BLOB = "526293491f8553b93141aad9f131e1e39d4cc640"

D11A_CONTRACT = (
    Path("output")
    / "V16_D11A_SPECTRAL_ENSEMBLE_RECIPE_1P1_PROVENANCE_REPAIR"
    / "V16D11A_Spectral_Ensemble_Recipe_1p1_Contract.json"
)
D11A_CONTRACT_BLOB = "b3acf7ddad07cabaed2999a0d4b6046055db15a3"

R4_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R4_R3C_Failure_Closure_and_Producer_Localization"
)
R4_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R4_Summary.json"
R4_CLOSURE = "POSTV16_AV1_D_R4_R3C_Scientific_Failure_Closure.json"
R4_MANIFEST = "POSTV16_AV1_D_R4_Artifact_Manifest.csv"
R4_STATUS = (
    "AV1DR4_R3C_FINAL_FAIL_CLOSED_PROD_SW_DAY30_PRODUCER_EVENT_MISMATCH_"
    "LOCALIZED_GEOLOGY0030_CONSUMED_NO_RETEST_AUTHORIZED"
)

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R5_BLOCKED"
)

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

C18R_NAME = "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA = "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
C19_NAME = "V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA = "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"

STARTING_CHECKPOINT = "R3B_RESPONSE"
STARTING_WEIGHTS_SHA = "8207f17f35c354a3396525ed3ba8de88c923f7b55351f7cc58a9000268a26364"

THRESHOLD = 1.0e-4
NEW_GEOLOGY_ID = "0031"
NEW_GEOLOGY_SEED = 390051
RECIPE = "V16D_SPECTRAL_ENSEMBLE_RECIPE_1.1"
INJECTION_TPD = 500.0
PRODUCER_BHP_PSI = 2000.0

PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}

TARGET_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]


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
    m = {r["file"]: r["sha256"] for r in rows}
    for fn, expected in m.items():
        p = directory / fn
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{fn}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA_mismatch:{fn}:{actual}:{expected}")
    return m


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


def self_test() -> None:
    calc = 160400 + (31 - 2) * 7919
    if calc != NEW_GEOLOGY_SEED:
        raise RuntimeError("geology0031_seed")
    if sorted(PRODUCERS) != ["PROD_NE", "PROD_NW", "PROD_SE", "PROD_SW"]:
        raise RuntimeError("producer_set")
    if len(TARGET_DAYS) != 9 or TARGET_DAYS[0] != 30.0 or TARGET_DAYS[-1] != 1000.0:
        raise RuntimeError("target_days")
    print("POSTV16-AV1-D-R5 self-test: PASS")


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
    print("POSTV16-AV1-D-R5 — PROSPECTIVE PRODUCER-RESOLVED REPAIR + GEOLOGY0031 ACCEPTANCE FREEZE")
    print("=" * 168)
    print("NO TRAINING. NO MODEL INFERENCE. NO GEOLOGY0031 GENERATION. NO TARGET GENERATION.")
    print("NO GEOLOGY0030 REUSE FOR TRAINING/SELECTION/ACCEPTANCE.")
    print("FREEZES A NEW DERIVED-V16 PRODUCER CONNECTIVITY RULE, ONE REPAIR OBJECTIVE,")
    print("AND THE NEXT UNTOUCHED INDEPENDENT ACCEPTANCE CASE BEFORE ANY NEW LEARNING.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_R4_commit", parent == PARENT_R4_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, blob in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == blob, actual)

        for p, blob, label in (
            (root / R7E_CONTRACT, R7E_CONTRACT_BLOB, "R7E_contract"),
            (root / D11A_CONTRACT, D11A_CONTRACT_BLOB, "D11A_contract"),
        ):
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{label}_git_blob_exact", actual == blob, actual)

        stage = "R4_binding"

        r4 = drive / R4_REL
        gate("R4_output_present", r4.is_dir(), str(r4))
        m4 = verify_manifest(r4, R4_MANIFEST)
        gate("R4_manifest_SHA_closure", True, len(m4))

        r4s = load_json(r4 / R4_SUMMARY)
        r4c = load_json(r4 / R4_CLOSURE)

        gate("R4_status_exact", r4s["status"] == R4_STATUS, r4s["status"])
        gate("R4_geology0030_consumed", r4s["geology0030_consumed"] is True)
        gate("R4_new_inference_false", r4s["new_inference"] is False)
        gate("R4_target_reopened_false", r4s["target_reopened"] is False)
        gate("R4_retraining_false", r4s["retraining"] is False)
        gate("R4_single_producer_day_mismatch", int(r4s["producer_day_mismatch_count"]) == 1)
        gate("R4_localization_exact", r4s["localization"] == "PROD_SW / day 30 only", r4s["localization"])
        gate("R4_causal_mechanism_not_established", r4c["causal_claim"].startswith("NOT ESTABLISHED"))
        gate("R4_no_posthoc_tolerance", r4c["posthoc_tolerance_created"] is False)
        gate("R4_geology0030_retest_false", r4c["geology0030_retest_authorized"] is False)

        stage = "producer_connectivity_scope_binding"

        r7e = load_json(root / R7E_CONTRACT)
        fs = r7e["foundation_scope"]
        gate("historical_producer_id_unavailable", fs["producer_id_status"] == "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE")
        gate("future_connectivity_branch_allowed", fs["future_connectivity_branch_allowed"] is True)
        gate("future_connectivity_must_be_derived_V16", fs["future_connectivity_branch_must_be_labeled_derived_V16"] is True)

        # Freeze a NEW post-freeze V16 connectivity rule. This is not claimed
        # to reproduce historical V15 producer metadata.
        connectivity = {
            "milestone": MILESTONE,
            "rule_id": "POSTV16_DERIVED_V16_TERMINAL_XY_NEAREST_PRODUCER_COLUMN_V1",
            "authority_class": "NEW_POST_FREEZE_DERIVED_V16_CONNECTIVITY_METADATA",
            "historical_V15_producer_id_claim": False,
            "source_endpoint_artifact": {
                "name": FOUNDATION_NAME,
                "sha256": FOUNDATION_SHA,
                "required_array": "streamline_xyz",
                "expected_shape": [1078, 201, 3],
                "endpoint": "streamline_xyz[:, -1, :]",
                "Pollock_retrace": False,
            },
            "grid_mapping": {
                "dx_m": 6.096,
                "dy_m": 6.096,
                "origin_cell_center_m": [0.0, 0.0],
                "terminal_continuous_cell_coordinates": [
                    "i_terminal = x_terminal_m / 6.096",
                    "j_terminal = y_terminal_m / 6.096",
                ],
            },
            "producer_columns_ij": PRODUCERS,
            "classification_rule": (
                "Assign each frozen terminal endpoint to the producer column "
                "with minimum squared horizontal cell-index distance "
                "(i_terminal-i_prod)^2 + (j_terminal-j_prod)^2."
            ),
            "tie_policy": "PROHIBITED; any exact minimum-distance tie blocks label certification",
            "z_coordinate_role": "ignored because producer identity is a vertical well-column connectivity label",
            "no_distance_acceptance_threshold": True,
            "training_role": "grouping/weighting metadata only; NOT a predictor input feature",
            "required_certification_before_training": {
                "all_1078_labels_assigned": True,
                "all_four_producers_present": True,
                "no_ties": True,
                "labels_deterministic_from_frozen_endpoint_geometry": True,
                "no_Pollock_retrace": True,
                "no_geology0030_information_used": True,
            },
        }

        stage = "repair_protocol_freeze"

        repair = {
            "milestone": MILESTONE,
            "repair_id": "POSTV16_AV1_D_R5_PRODUCER_BALANCED_RESPONSE_REPAIR_V1",
            "motivation": (
                "R3C aggregate event behavior passed while exactly one producer-day "
                "classification failed. R4 localized that failure but established no "
                "causal mechanism. The repair is therefore generic producer balancing, "
                "not PROD_SW-specific tuning."
            ),
            "starting_checkpoint": {
                "candidate_id": STARTING_CHECKPOINT,
                "weights_sha256": STARTING_WEIGHTS_SHA,
            },
            "architecture": "UNCHANGED exact C26 2xLSTM64 + TimeDistributed Dense + sigmoid/rescale",
            "predictor_features": "UNCHANGED exact C26 201x9 input",
            "training_data": {
                "C18R_name": C18R_NAME,
                "C18R_sha256": C18R_SHA,
                "C19_name": C19_NAME,
                "C19_sha256": C19_SHA,
                "gradient_partition": "C19 TRAIN only",
                "selection_partition": "C19 VALIDATION only",
                "retired_C19_TEST_role": "PROHIBITED for training, checkpoint selection, or final acceptance",
                "geology0030_role": "diagnostic historical evidence only; arrays and metrics prohibited in objective/selection",
            },
            "producer_labels": {
                "authority": connectivity["rule_id"],
                "role": "loss grouping and validation grouping only",
                "not_model_input": True,
            },
            "base_objective": {
                "L_profile": "exact R3B/C26 uniform profile MSE",
                "L_phys": "exact C25 physics residual",
                "lambda_phys": 0.01,
                "L_global_response": (
                    "exact R3B flow-weighted terminal fractional-flow MSE "
                    "using frozen streamline weights"
                ),
                "lambda_global_response": 1.0,
            },
            "new_repair_term": {
                "name": "L_producer_balanced_response",
                "definition": (
                    "For each producer p, compute the flow-weighted mean squared "
                    "terminal fractional-flow error over TRAIN samples assigned to p; "
                    "then average the four producer losses with equal 1/4 weight."
                ),
                "formula": (
                    "L_prod = (1/4) * sum_p [ "
                    "sum_{s in p} q_s (fw_pred_s-fw_true_s)^2 / sum_{s in p} q_s ]"
                ),
                "lambda_producer_balanced_response": 1.0,
                "acceptance_threshold_used": False,
                "PROD_SW_specific_weighting": False,
            },
            "total_training_objective": (
                "L_total = L_profile + 0.01*L_phys "
                "+ 1.0*L_global_response + 1.0*L_producer_balanced_response"
            ),
            "optimizer_training_schedule": {
                "optimizer": "Adam",
                "initial_lr": 1.0e-3,
                "batch_size": 64,
                "max_epochs": 300,
                "patience": 30,
                "min_delta": 1.0e-6,
                "lr_patience": 10,
                "min_lr": 1.0e-6,
                "rng_seed": 16021,
            },
            "single_candidate_policy": {
                "candidate_count": 1,
                "no_posthoc_lambda_search": True,
                "no_architecture_search": True,
                "no_feature_search": True,
                "no_threshold_in_training": True,
            },
            "validation_checkpoint_selection": {
                "primary": "lowest worst-producer flow-weighted outlet fractional-flow RMSE",
                "secondary": "lowest equal-producer mean flow-weighted outlet fractional-flow RMSE",
                "tertiary": "lowest global flow-weighted outlet fractional-flow RMSE",
                "quaternary": "lowest terminal saturation RMSE",
                "fifth": "lowest full-profile RMSE",
                "sixth": "lowest frozen base total objective",
                "breakthrough_threshold_used": False,
                "geology0030_used": False,
                "retired_C19_TEST_used": False,
            },
            "post_selection": {
                "selected_checkpoint_frozen_before_geology0031_target_opening": True,
                "no_adaptation_after_geology0031_opening": True,
            },
        }

        stage = "new_acceptance_freeze"

        seed_rule_value = 160400 + (31 - 2) * 7919
        gate("geology0031_seed_formula_exact", seed_rule_value == NEW_GEOLOGY_SEED, seed_rule_value)

        d11a = load_json(root / D11A_CONTRACT)
        gate("Recipe1p1_exact", d11a["recipe_1p1"]["recipe_id"] == RECIPE)
        gate("Recipe1p1_not_SGS", "NOT sequential Gaussian simulation" in d11a["recipe_1p1"]["algorithm"])

        acceptance = {
            "milestone": MILESTONE,
            "acceptance_id": "POSTV16_AV1_D_R5_GEOLOGY0031_REFERENCE_CONTROL_ONE_TOUCH_ACCEPTANCE_V1",
            "prospectively_frozen_before_generation": True,
            "geology_id": NEW_GEOLOGY_ID,
            "seed": NEW_GEOLOGY_SEED,
            "seed_rule": "160400 + (geology_case_id - 2)*7919",
            "geology_recipe": RECIPE,
            "geology_algorithm_claim": "spectral GRF; NOT SGSim/SGS",
            "controls": {
                "CO2_injection_tonnes_per_day": INJECTION_TPD,
                "producer_BHP_psi": PRODUCER_BHP_PSI,
            },
            "grid": "50x50x15, 20x20x4 ft",
            "porosity": 0.20,
            "Kz_over_Kh": 0.10,
            "well_geometry": "frozen V15 five-spot",
            "target_days": TARGET_DAYS,
            "generation_order": {
                "freeze_this_R5_contract_first": True,
                "generate_and_certify_geology0031_next": True,
                "generate_flow_Pollock_metric_Stage4_truth": True,
                "seal_target_before_R5_repair_training": True,
                "target_may_not_be_opened_for_training_or_selection": True,
            },
            "one_touch_final_evaluation": {
                "all_1078_streamlines": True,
                "all_9_target_days": True,
                "no_case_time_streamline_or_node_suppression": True,
                "no_adaptation_after_opening": True,
                "no_threshold_tuning_after_opening": True,
                "no_alternate_candidate_after_opening": True,
                "no_replacement_geology_or_seed_after_opening": True,
            },
            "structural_hard_gates": [
                "finite predictions",
                "saturation within [0.2,0.8]",
                "exact E37A component-mass 201->200 projection closure",
                "no saturation averaging",
            ],
            "primary_event_hard_gates": {
                "aggregate_CO2_cut_threshold": THRESHOLD,
                "aggregate_classification_match_all_9_times": True,
                "aggregate_first_breakthrough_target_day_match": True,
                "each_producer_classification_match_all_9_times": True,
            },
            "descriptive_only_not_acceptance_gates": [
                "profile RMSE/MAE/max error",
                "outlet saturation RMSE/MAE",
                "aggregate cut MAE/max absolute error",
                "producer cut absolute errors",
                "component-mass error",
            ],
            "claim_limit": (
                "A PASS supports repaired producer-resolved outlet/breakthrough "
                "event behavior on one prospectively frozen independent Recipe1.1 "
                "geology at the reference controls. It does not establish universal "
                "geology generalization or Cartesian plume-field equivalence."
            ),
            "geology0030_role": "consumed diagnostic/development evidence only; not an independent test",
        }

        gate("acceptance_threshold_unchanged", acceptance["primary_event_hard_gates"]["aggregate_CO2_cut_threshold"] == THRESHOLD)
        gate("geology0030_not_reused", acceptance["geology0030_role"].startswith("consumed"))
        gate("new_case_is_0031", acceptance["geology_id"] == "0031")
        gate("new_case_reference_controls", acceptance["controls"]["CO2_injection_tonnes_per_day"] == 500.0 and acceptance["controls"]["producer_BHP_psi"] == 2000.0)

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "repository_head": head,
            "repository_parent": parent,
            "producer_connectivity_rule_id": connectivity["rule_id"],
            "repair_id": repair["repair_id"],
            "starting_checkpoint": STARTING_CHECKPOINT,
            "starting_weights_sha256": STARTING_WEIGHTS_SHA,
            "new_acceptance_geology_id": NEW_GEOLOGY_ID,
            "new_acceptance_seed": NEW_GEOLOGY_SEED,
            "geology_recipe": RECIPE,
            "training_performed": False,
            "model_inference_performed": False,
            "geology0031_generated": False,
            "geology0031_target_generated": False,
            "geology0030_reused_for_acceptance": False,
            "next": (
                "POSTV16-AV1-D-R5A — derive/certify the post-freeze V16 producer "
                "connectivity labels and generate/seal geology0031 acceptance authority "
                "before any R5 repair training."
            ),
        }

        files = {
            "PAD_Stream_POSTV16_AV1_D_R5_Summary.json": json_bytes(summary),
            "POSTV16_AV1_D_R5_Derived_V16_Producer_Connectivity_Contract.json": json_bytes(connectivity),
            "POSTV16_AV1_D_R5_Producer_Resolved_Repair_Protocol.json": json_bytes(repair),
            "POSTV16_AV1_D_R5_Geology0031_Independent_Acceptance_Authority.json": json_bytes(acceptance),
            "POSTV16_AV1_D_R5_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV1_D_R5_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(
            out,
            {"POSTV16_AV1_D_R5_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R5: PASS")
        print("=" * 168)
        print(f"{'Status':88}: {STATUS_PASS}")
        print(f"{'R3C/R4 result':88}: final FAIL preserved; geology0030 consumed")
        print(f"{'New producer label authority':88}: derived V16 terminal-XY nearest producer column")
        print(f"{'Historical V15 producer-id claim':88}: False")
        print(f"{'Starting checkpoint':88}: {STARTING_CHECKPOINT}")
        print(f"{'Starting weights SHA256':88}: {STARTING_WEIGHTS_SHA}")
        print(f"{'New repair':88}: global response + equal-producer response; threshold-free")
        print(f"{'New independent geology':88}: 0031")
        print(f"{'Geology0031 seed':88}: {NEW_GEOLOGY_SEED}")
        print(f"{'Geology recipe':88}: {RECIPE} (spectral GRF, not SGS)")
        print(f"{'Controls':88}: 500 t/day, 2000 psi")
        print(f"{'Acceptance threshold':88}: {THRESHOLD:.1e} unchanged")
        print(f"{'Training / inference':88}: False / False")
        print(f"{'Geology0031 generated / target generated':88}: False / False")
        print(f"{'NEXT':88}: R5A — certify labels + generate/seal geology0031 before training")
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
            "training_performed": False,
            "model_inference_performed": False,
            "geology0031_generated": False,
            "geology0031_target_generated": False,
            "geology0030_retest_authorized": False,
            "next_action": (
                "Audit only the failed R5 prospective-freeze gate. "
                "Do not train, generate geology0031, or reopen geology0030."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R5_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R5_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R5: BLOCKED")
        print("=" * 168)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("No training, inference, or geology0031 generation occurred.")
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
