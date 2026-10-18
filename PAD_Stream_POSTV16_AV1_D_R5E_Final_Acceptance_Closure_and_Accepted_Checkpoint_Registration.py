#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


MILESTONE = "POSTV16-AV1-D-R5E"
STATUS_PASS = (
    "AV1DR5E_R5_FINAL_ACCEPTANCE_CLOSED_ACCEPTED_POSTV16_"
    "TRANSPORT_CHECKPOINT_REGISTERED_R6_DEPLOYMENT_AUTHORIZED"
)
STATUS_BLOCKED = "AV1DR5E_FINAL_ACCEPTANCE_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R5D_COMMIT = "cd4c4be55c3d74713337315463d7408964238d62"

R5D = "PAD_Stream_POSTV16_AV1_D_R5D_One_Touch_Final_Geology0031_Acceptance.py"
R5D_BLOB = "b5d2b67a38e5c7bcaff748a018145c151bd6950f"
R5CR1 = "PAD_Stream_POSTV16_AV1_D_R5C_R1_TimeMajor_Order_Dtype_Repair.py"
R5CR1_BLOB = "f2340b3a258a435833ced5c137fa2215f02dda3d"
R5BR1 = "PAD_Stream_POSTV16_AV1_D_R5B_R1_C7_Metric_Binding_ControlFlow_Repair.py"
R5BR1_BLOB = "773defe3d960cade441ce8dd098b31791747ca80"
R5A = "PAD_Stream_POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority.py"
R5A_BLOB = "740c4862e934c2b05b2eaa63c4136110c01866e9"
R5 = "PAD_Stream_POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze.py"
R5_BLOB = "c5d2f64f124153b4e352f302302e0558a31c5c58"
C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

SOURCE_BLOBS = {
    R5D: R5D_BLOB,
    R5CR1: R5CR1_BLOB,
    R5BR1: R5BR1_BLOB,
    R5A: R5A_BLOB,
    R5: R5_BLOB,
    C26: C26_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R5_REL = BASE / "POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze"
R5_ACCEPT = "POSTV16_AV1_D_R5_Geology0031_Independent_Acceptance_Authority.json"
R5_MANIFEST = "POSTV16_AV1_D_R5_Artifact_Manifest.csv"

R5A_REL = BASE / "POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority"
R5A_AUTHORITY = "POSTV16_AV1_D_R5A_Sealed_Acceptance_Authority.json"
R5A_MANIFEST = "POSTV16_AV1_D_R5A_Artifact_Manifest.csv"
R5A_TARGET = "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_SEALED_Stage4_Target.npz"

R5BR1_REL = BASE / "POSTV16_AV1_D_R5B_R1_Producer_Balanced_TrainValidation_Repair_Execution"
R5BR1_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R5B_R1_Summary.json"
R5BR1_SELECTED = "POSTV16_AV1_D_R5B_R1_Selected_Checkpoint_Contract.json"
R5BR1_MANIFEST = "POSTV16_AV1_D_R5B_R1_Artifact_Manifest.csv"
R5BR1_WEIGHTS = "POSTV16_AV1_D_R5B_R1_SELECTED_FROZEN.weights.h5"

R5CR1_REL = BASE / "POSTV16_AV1_D_R5C_R1_Geology0031_Deployment_Conditioning_Authority"
R5CR1_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R5C_R1_Summary.json"
R5CR1_AUTHORITY = "POSTV16_AV1_D_R5C_R1_Deployment_Conditioning_Authority.json"
R5CR1_MANIFEST = "POSTV16_AV1_D_R5C_R1_Artifact_Manifest.csv"
R5CR1_CONDITIONING = "POSTV16_AV1_D_R5C_R1_Geology0031_C26_Deployment_Conditioning.npz"

R5D_REL = BASE / "POSTV16_AV1_D_R5D_One_Touch_Final_Geology0031_Acceptance"
R5D_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R5D_Summary.json"
R5D_DECISION = "POSTV16_AV1_D_R5D_Final_Decision.json"
R5D_AGG = "POSTV16_AV1_D_R5D_Aggregate_Event_Audit.csv"
R5D_PROD = "POSTV16_AV1_D_R5D_Producer_Event_Audit.csv"
R5D_GATES = "POSTV16_AV1_D_R5D_Final_Gate_Matrix.csv"
R5D_MANIFEST = "POSTV16_AV1_D_R5D_Artifact_Manifest.csv"

OUT_REL = BASE / "POSTV16_AV1_D_R5E_Final_Acceptance_Closure_and_Accepted_Checkpoint_Registration"
BLOCKED_REL = BASE / "POSTV16_AV1_D_R5E_BLOCKED"

SELECTED_ID = "R5B_PRODUCER_BALANCED_RESPONSE"
SELECTED_SHA = "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"
CONDITIONING_SHA = "c1a6225f14bc90698b45d96ed848add8ec2a5820d0c67f4a1f6f55fc52690f13"
TARGET_SHA = "cef2647c394909fb268b621a5e6074b49c3aa41a285c75082d7d976f48e62afc"
C3_SHA = "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"
THRESHOLD = 1.0e-4

R5D_STATUS = (
    "AV1DR5D_ONE_TOUCH_GEOLOGY0031_FINAL_EVENT_ACCEPTANCE_PASS_"
    "PRODUCER_BALANCED_REPAIR_ACCEPTED_ON_FROZEN_INDEPENDENT_CASE"
)
R5BR1_STATUS = (
    "AV1DR5BR1_C7_METRIC_BINDING_CONTROLFLOW_REPAIRED_SINGLE_"
    "PRODUCER_BALANCED_TRAIN_VALIDATION_REPAIR_EXECUTED_"
    "SELECTED_CHECKPOINT_FROZEN_GEOLOGY0031_REMAINS_SEALED"
)
R5CR1_STATUS = (
    "AV1DR5CR1_TIME_MAJOR_ORDER_DTYPE_REPAIRED_"
    "GEOLOGY0031_C26_DEPLOYMENT_CONDITIONING_"
    "AUTHORITY_GENERATED_CERTIFIED_AND_SHA_SEALED"
)

ACCEPTED_WEIGHT_NAME = "POSTV16_AV1_D_R5E_ACCEPTED_POSTV16_TRANSPORT_FROZEN.weights.h5"


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


def bool_csv(v: str) -> bool:
    return str(v).strip().lower() == "true"


def self_test() -> None:
    if len(SELECTED_SHA) != 64 or len(CONDITIONING_SHA) != 64 or len(TARGET_SHA) != 64:
        raise RuntimeError("sha_lengths")
    if THRESHOLD != 1.0e-4:
        raise RuntimeError("threshold")
    if SELECTED_ID != "R5B_PRODUCER_BALANCED_RESPONSE":
        raise RuntimeError("selected_id")
    print("POSTV16-AV1-D-R5E self-test: PASS")


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

    print("=" * 178)
    print("POSTV16-AV1-D-R5E — FINAL R5 ACCEPTANCE CLOSURE + ACCEPTED CHECKPOINT REGISTRATION")
    print("=" * 178)
    print("NO TRAINING. NO MODEL INFERENCE. NO TARGET ARRAY OPENING. NO NEW GEOLOGY.")
    print("THIS MILESTONE CLOSES R5, REGISTERS THE ACCEPTED CHECKPOINT,")
    print("MARKS GEOLOGY0031 AS CONSUMED FINAL ACCEPTANCE EVIDENCE, AND AUTHORIZES R6 DEPLOYMENT INTEGRATION.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_R5D_commit", parent == PARENT_R5D_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, blob in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == blob, actual)

        stage = "R5_lineage_binding"

        r5 = drive / R5_REL
        r5a = drive / R5A_REL
        r5b = drive / R5BR1_REL
        r5c = drive / R5CR1_REL
        r5d = drive / R5D_REL

        for label, d in (
            ("R5", r5),
            ("R5A", r5a),
            ("R5BR1", r5b),
            ("R5CR1", r5c),
            ("R5D", r5d),
        ):
            gate(f"{label}_output_present", d.is_dir(), str(d))

        m5 = verify_manifest(r5, R5_MANIFEST)
        m5a = verify_manifest(r5a, R5A_MANIFEST)
        m5b = verify_manifest(r5b, R5BR1_MANIFEST)
        m5c = verify_manifest(r5c, R5CR1_MANIFEST)
        m5d = verify_manifest(r5d, R5D_MANIFEST)

        gate("R5_manifest_SHA_closure", True, len(m5))
        gate("R5A_manifest_SHA_closure", True, len(m5a))
        gate("R5BR1_manifest_SHA_closure", True, len(m5b))
        gate("R5CR1_manifest_SHA_closure", True, len(m5c))
        gate("R5D_manifest_SHA_closure", True, len(m5d))

        accept = load_json(r5 / R5_ACCEPT)
        r5a_auth = load_json(r5a / R5A_AUTHORITY)
        r5b_sum = load_json(r5b / R5BR1_SUMMARY)
        r5b_sel = load_json(r5b / R5BR1_SELECTED)
        r5c_sum = load_json(r5c / R5CR1_SUMMARY)
        r5c_auth = load_json(r5c / R5CR1_AUTHORITY)
        r5d_sum = load_json(r5d / R5D_SUMMARY)
        r5d_dec = load_json(r5d / R5D_DECISION)

        gate("R5_geology0031_exact", accept["geology_id"] == "0031", accept["geology_id"])
        gate("R5_seed390051_exact", int(accept["seed"]) == 390051, accept["seed"])
        gate(
            "R5_threshold_exact",
            float(accept["primary_event_hard_gates"]["aggregate_CO2_cut_threshold"]) == THRESHOLD,
            accept["primary_event_hard_gates"]["aggregate_CO2_cut_threshold"],
        )
        gate("R5_geology0030_role_consumed", accept["geology0030_role"].startswith("consumed"))

        one = accept["one_touch_final_evaluation"]
        gate("R5_one_touch_all_1078", one["all_1078_streamlines"] is True)
        gate("R5_one_touch_all_9_days", one["all_9_target_days"] is True)
        gate("R5_no_adaptation_after_opening", one["no_adaptation_after_opening"] is True)
        gate("R5_no_threshold_tuning_after_opening", one["no_threshold_tuning_after_opening"] is True)
        gate("R5_no_alternate_candidate_after_opening", one["no_alternate_candidate_after_opening"] is True)
        gate("R5_no_replacement_geology_after_opening", one["no_replacement_geology_or_seed_after_opening"] is True)

        gate("R5A_geology0031_exact", r5a_auth["acceptance_authority"]["geology"]["id"] == "0031")
        gate(
            "R5A_target_SHA_exact",
            r5a_auth["acceptance_authority"]["sealed_target_sha256"] == TARGET_SHA,
            r5a_auth["acceptance_authority"]["sealed_target_sha256"],
        )

        gate("R5BR1_status_exact", r5b_sum["status"] == R5BR1_STATUS, r5b_sum["status"])
        gate("R5BR1_candidate_exact", r5b_sum["candidate_id"] == SELECTED_ID, r5b_sum["candidate_id"])
        gate(
            "R5BR1_selected_SHA_exact",
            r5b_sum["selected_frozen_weights_sha256"] == SELECTED_SHA,
            r5b_sum["selected_frozen_weights_sha256"],
        )
        gate("R5BR1_geology0031_unopened_at_selection", r5b_sel["geology0031_target_opened"] is False)
        gate("R5BR1_geology0031_inference_false", r5b_sel["geology0031_model_inference"] is False)

        source_weights = r5b / R5BR1_WEIGHTS
        gate("accepted_source_weights_present", source_weights.is_file(), str(source_weights))
        gate(
            "accepted_source_weights_SHA_exact",
            source_weights.is_file() and sha256_file(source_weights) == SELECTED_SHA,
            sha256_file(source_weights) if source_weights.is_file() else "missing",
        )

        gate("R5CR1_status_exact", r5c_sum["status"] == R5CR1_STATUS, r5c_sum["status"])
        gate(
            "R5CR1_conditioning_SHA_exact",
            r5c_sum["conditioning_artifact_sha256"] == CONDITIONING_SHA,
            r5c_sum["conditioning_artifact_sha256"],
        )
        gate("R5CR1_target_unopened", r5c_sum["sealed_target_opened"] is False)
        gate("R5CR1_inference_false", r5c_sum["model_inference_performed"] is False)
        gate(
            "R5CR1_C3_normalization_SHA_exact",
            r5c_auth["conditioning"]["normalization_authority_sha256"] == C3_SHA,
            r5c_auth["conditioning"]["normalization_authority_sha256"],
        )

        conditioning_path = r5c / R5CR1_CONDITIONING
        gate(
            "acceptance_conditioning_file_SHA_exact",
            conditioning_path.is_file() and sha256_file(conditioning_path) == CONDITIONING_SHA,
            sha256_file(conditioning_path) if conditioning_path.is_file() else "missing",
        )

        target_path = r5a / R5A_TARGET
        gate(
            "consumed_acceptance_target_file_SHA_exact_without_array_open",
            target_path.is_file() and sha256_file(target_path) == TARGET_SHA,
            sha256_file(target_path) if target_path.is_file() else "missing",
        )

        stage = "R5D_final_decision_binding"

        gate("R5D_status_exact", r5d_dec["status"] == R5D_STATUS, r5d_dec["status"])
        gate("R5D_final_acceptance_PASS", r5d_dec["final_acceptance_pass"] is True)
        gate("R5D_structural_acceptance_PASS", r5d_dec["structural_acceptance_pass"] is True)
        gate("R5D_primary_event_acceptance_PASS", r5d_dec["primary_event_acceptance_pass"] is True)
        gate("R5D_selected_candidate_exact", r5d_dec["selected_candidate"] == SELECTED_ID)
        gate("R5D_selected_SHA_exact", r5d_dec["selected_weights_sha256"] == SELECTED_SHA)
        gate("R5D_conditioning_SHA_exact", r5d_dec["conditioning_sha256"] == CONDITIONING_SHA)
        gate("R5D_truth_SHA_exact", r5d_dec["sealed_target_sha256"] == TARGET_SHA)
        gate("R5D_threshold_unchanged", float(r5d_dec["breakthrough_threshold"]) == THRESHOLD)
        gate(
            "R5D_first_breakthrough_60_60",
            float(r5d_dec["truth_first_breakthrough_target_day"]) == 60.0
            and float(r5d_dec["prediction_first_breakthrough_target_day"]) == 60.0,
            [
                r5d_dec["truth_first_breakthrough_target_day"],
                r5d_dec["prediction_first_breakthrough_target_day"],
            ],
        )
        gate("R5D_zero_aggregate_mismatches", int(r5d_dec["aggregate_mismatch_count"]) == 0)
        gate("R5D_zero_producer_day_mismatches", int(r5d_dec["producer_day_mismatch_count"]) == 0)
        gate("R5D_producer_mismatch_list_empty", r5d_dec["producer_day_mismatches"] == [])
        gate("R5D_all_1078_used", r5d_dec["all_1078_streamlines_used"] is True)
        gate("R5D_all_9_days_used", r5d_dec["all_9_target_days_used"] is True)
        gate("R5D_no_adaptation", r5d_dec["adaptation_after_opening"] is False)
        gate("R5D_no_threshold_tuning", r5d_dec["threshold_tuning_after_opening"] is False)
        gate("R5D_no_alternate_candidate", r5d_dec["alternate_candidate_evaluated"] is False)
        gate("R5D_no_replacement_geology", r5d_dec["replacement_geology_or_seed_used"] is False)
        gate("R5D_second_test_not_authorized", r5d_dec["second_test_attempt_authorized"] is False)
        gate("R5D_geology0030_not_reused", r5d_dec["geology0030_reused"] is False)
        gate("R5D_summary_target_opened_true", r5d_sum["target_opened"] is True)
        gate("R5D_summary_inference_performed_true", r5d_sum["model_inference_performed"] is True)

        claim_limit = accept["claim_limit"]
        gate("R5D_claim_limit_identity", r5d_dec["claim_limit"] == claim_limit)

        agg_rows = read_csv(r5d / R5D_AGG)
        prod_rows = read_csv(r5d / R5D_PROD)
        gate("R5D_aggregate_audit_9_rows", len(agg_rows) == 9, len(agg_rows))
        gate("R5D_producer_audit_36_rows", len(prod_rows) == 36, len(prod_rows))
        gate("R5D_aggregate_audit_all_matches", all(bool_csv(r["classification_match"]) for r in agg_rows))
        gate("R5D_producer_audit_all_matches", all(bool_csv(r["classification_match"]) for r in prod_rows))

        gate_rows = read_csv(r5d / R5D_GATES)
        gate_map = {r["gate"]: r for r in gate_rows}
        hard_gate_names = [
            "finite_predictions",
            "saturation_bounds_0p2_0p8",
            "E37A_201_to_200_mass_projection_closure",
            "no_saturation_averaging",
            "aggregate_classification_match_all_9_times",
            "aggregate_first_breakthrough_target_day_match",
            "each_producer_classification_match_all_9_times",
        ]
        for name in hard_gate_names:
            gate(f"R5D_hard_gate_{name}_PASS", name in gate_map and bool_csv(gate_map[name]["passed"]))

        stage = "accepted_checkpoint_registration"

        out.mkdir(parents=True, exist_ok=True)
        accepted_weights = out / ACCEPTED_WEIGHT_NAME
        if accepted_weights.exists():
            gate(
                "existing_registered_weights_SHA_exact",
                sha256_file(accepted_weights) == SELECTED_SHA,
                sha256_file(accepted_weights),
            )
        else:
            shutil.copyfile(source_weights, accepted_weights)

        gate(
            "registered_accepted_weights_SHA_exact",
            sha256_file(accepted_weights) == SELECTED_SHA,
            sha256_file(accepted_weights),
        )

        registry = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "registry_id": "POSTV16_AV1_D_R5E_ACCEPTED_TRANSPORT_DEPLOYMENT_CHECKPOINT_V1",
            "transport_checkpoint": {
                "role": "ACCEPTED_POSTV16_TRANSPORT_DEPLOYMENT_CHECKPOINT",
                "candidate_id": SELECTED_ID,
                "artifact": ACCEPTED_WEIGHT_NAME,
                "sha256": SELECTED_SHA,
                "immutable": True,
                "architecture_authority": {
                    "source": C26,
                    "git_blob": C26_BLOB,
                    "input_shape": [201, 9],
                    "parameter_count": 52033,
                },
                "conditioning_semantics": {
                    "required_sequence_channels": [
                        "xi",
                        "pollock_tau_hat",
                        "adv_tau_hat",
                        "log10_Kh",
                        "log10_Kz_over_Kh",
                        "porosity",
                        "pressure_z",
                    ],
                    "time_channels": ["target_time_hat", "target_eta"],
                    "normalization_authority_sha256": C3_SHA,
                    "sample_order": "time-major then streamline",
                },
                "modification_authorized": False,
                "retraining_under_R5_authorized": False,
            },
            "acceptance_evidence": {
                "geology_id": "0031",
                "seed": 390051,
                "geology_recipe": accept["geology_recipe"],
                "controls": accept["controls"],
                "conditioning_sha256": CONDITIONING_SHA,
                "truth_sha256": TARGET_SHA,
                "threshold": THRESHOLD,
                "R5D_final_status": R5D_STATUS,
                "structural_acceptance_pass": True,
                "primary_event_acceptance_pass": True,
                "aggregate_mismatch_count": 0,
                "producer_day_mismatch_count": 0,
                "truth_first_breakthrough_target_day": 60.0,
                "prediction_first_breakthrough_target_day": 60.0,
                "role": "CONSUMED_FINAL_ACCEPTANCE_EVIDENCE",
                "future_untouched_independent_test_role": False,
                "retest_under_R5_authorized": False,
            },
            "claim_boundary": {
                "accepted_claim": claim_limit,
                "does_not_establish": [
                    "universal geology generalization",
                    "Cartesian plume-field equivalence",
                    "generalization across injection-rate / producer-BHP control space",
                ],
            },
            "next_lineage": {
                "R5_repair_branch_closed": True,
                "R5_reopening_for_tuning_authorized": False,
                "R6_deployment_integration_authorized": True,
                "R6_may_load_accepted_checkpoint": True,
                "R6_may_modify_accepted_checkpoint_weights": False,
                "R6_may_change_C26_architecture_under_this_registration": False,
                "R6_may_refit_C3_normalization_under_this_registration": False,
                "R6_goal": (
                    "integrate the accepted transport checkpoint into the canonical "
                    "PAD-Stream runtime with exact source/normalization/feature/"
                    "conservative-mapback bindings; no new scientific acceptance claim"
                ),
            },
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "R5_branch_state": "CLOSED_AFTER_VALID_ONE_TOUCH_PASS",
            "R5D_commit": PARENT_R5D_COMMIT,
            "R5D_runner_blob": R5D_BLOB,
            "accepted_checkpoint_sha256": SELECTED_SHA,
            "acceptance_conditioning_sha256": CONDITIONING_SHA,
            "acceptance_truth_sha256": TARGET_SHA,
            "geology0031_consumed_final_acceptance_evidence": True,
            "geology0031_future_independent_test_role": False,
            "geology0030_consumed_diagnostic_evidence": True,
            "new_training_performed": False,
            "new_model_inference_performed": False,
            "target_array_opened_in_R5E": False,
            "new_geology_generated": False,
            "threshold_changed": False,
            "accepted_checkpoint_modified": False,
            "R6_deployment_integration_authorized": True,
            "claim_limit": claim_limit,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "repository_head": head,
            "repository_parent": parent,
            "accepted_checkpoint": ACCEPTED_WEIGHT_NAME,
            "accepted_checkpoint_sha256": SELECTED_SHA,
            "R5D_final_acceptance_pass": True,
            "R5_branch_closed": True,
            "geology0031_consumed_final_acceptance_evidence": True,
            "new_training_performed": False,
            "new_model_inference_performed": False,
            "target_array_opened": False,
            "R6_deployment_integration_authorized": True,
            "next": (
                "POSTV16-AV1-D-R6 — accepted PI-RNN deployment promotion and "
                "canonical PAD-Stream runtime binding."
            ),
        }

        files = {
            "PAD_Stream_POSTV16_AV1_D_R5E_Summary.json": json_bytes(summary),
            "POSTV16_AV1_D_R5E_Accepted_Deployment_Checkpoint_Registry.json": json_bytes(registry),
            "POSTV16_AV1_D_R5E_R5_Final_Closure_Contract.json": json_bytes(closure),
            "POSTV16_AV1_D_R5E_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV1_D_R5E_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {"POSTV16_AV1_D_R5E_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print("\n" + "=" * 178)
        print("POSTV16-AV1-D-R5E: PASS")
        print("=" * 178)
        print(f"{'Status':96}: {STATUS_PASS}")
        print(f"{'R5 branch state':96}: CLOSED_AFTER_VALID_ONE_TOUCH_PASS")
        print(f"{'Accepted deployment candidate':96}: {SELECTED_ID}")
        print(f"{'Accepted deployment weights SHA256':96}: {SELECTED_SHA}")
        print(f"{'Canonical registered weights artifact':96}: {ACCEPTED_WEIGHT_NAME}")
        print(f"{'Acceptance evidence conditioning SHA256':96}: {CONDITIONING_SHA}")
        print(f"{'Acceptance evidence truth SHA256':96}: {TARGET_SHA}")
        print(f"{'Geology0031 consumed final evidence':96}: True")
        print(f"{'Geology0031 future untouched-test role':96}: False")
        print(f"{'New training / inference in R5E':96}: False / False")
        print(f"{'Target array opened in R5E':96}: False")
        print(f"{'R6 deployment integration authorized':96}: True")
        print(f"{'NEXT':96}: POSTV16-AV1-D-R6 — accepted PI-RNN deployment promotion")
        print("=" * 178)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "new_training_performed": False,
            "new_model_inference_performed": False,
            "target_array_opened": False,
            "new_geology_generated": False,
            "R5_branch_closed": False,
            "R6_deployment_integration_authorized": False,
            "next_action": (
                "Audit only the failed R5E provenance/closure/registration gate. "
                "Do not retrain, rerun R5D, reopen geology0031, change the threshold, "
                "or alter the accepted checkpoint."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R5E_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R5E_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 178)
        print("POSTV16-AV1-D-R5E: BLOCKED")
        print("=" * 178)
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
