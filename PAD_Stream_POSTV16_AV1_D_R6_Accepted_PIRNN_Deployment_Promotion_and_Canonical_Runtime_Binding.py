#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import io
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV1-D-R6"
STATUS_PASS = (
    "AV1DR6_ACCEPTED_PIRNN_DEPLOYMENT_PROMOTED_"
    "CANONICAL_PAD_STREAM_RUNTIME_BOUND_NO_MODEL_CHANGE"
)
STATUS_BLOCKED = "AV1DR6_CANONICAL_RUNTIME_BINDING_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R5E_COMMIT = "9d141fb5974686ca3ff116cb93ebe2b4d4fe9dcf"

R5E = "PAD_Stream_POSTV16_AV1_D_R5E_Final_Acceptance_Closure_and_Accepted_Checkpoint_Registration.py"
R5E_BLOB = "3e6874c4f503ce4f65229ebce97aac07fdf69cf6"
C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"
C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"
B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SOURCE_BLOBS = {
    R5E: R5E_BLOB,
    C26: C26_BLOB,
    C2: C2_BLOB,
    B1: B1_BLOB,
    E37A: E37A_BLOB,
}

C2_CONTRACT_REL = Path("output")/"V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"/"V16C2_Multi_Coordinate_Transport_Database_Contract.json"
C2_CONTRACT_BLOB = "88bc5ad068f0f24e78230318c5eab69b80f3dfc2"
C3_CONTRACT_REL = Path("output")/"V16_C3_PIRNN_TRANSPORT_CONDITIONING_CONTRACT"/"V16C3_PIRNN_Transport_Conditioning_Contract.json"
C3_CONTRACT_BLOB = "220ea7dcf59ef32cc850af065abca0b0c699029e"

C3_NORMALIZATION_NAME = "V16C3_Conditioning_Normalization_Parameters.npz"
C3_NORMALIZATION_SHA = "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R5E_REL = BASE / "POSTV16_AV1_D_R5E_Final_Acceptance_Closure_and_Accepted_Checkpoint_Registration"
R5E_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R5E_Summary.json"
R5E_REGISTRY = "POSTV16_AV1_D_R5E_Accepted_Deployment_Checkpoint_Registry.json"
R5E_CLOSURE = "POSTV16_AV1_D_R5E_R5_Final_Closure_Contract.json"
R5E_MANIFEST = "POSTV16_AV1_D_R5E_Artifact_Manifest.csv"
R5E_ACCEPTED_WEIGHTS = "POSTV16_AV1_D_R5E_ACCEPTED_POSTV16_TRANSPORT_FROZEN.weights.h5"
R5E_STATUS = (
    "AV1DR5E_R5_FINAL_ACCEPTANCE_CLOSED_ACCEPTED_POSTV16_"
    "TRANSPORT_CHECKPOINT_REGISTERED_R6_DEPLOYMENT_AUTHORIZED"
)

OUT_REL = BASE / "POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding"
BLOCKED_REL = BASE / "POSTV16_AV1_D_R6_BLOCKED"

SELECTED_ID = "R5B_PRODUCER_BALANCED_RESPONSE"
SELECTED_SHA = "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"
ACCEPTANCE_CONDITIONING_SHA = "c1a6225f14bc90698b45d96ed848add8ec2a5820d0c67f4a1f6f55fc52690f13"
ACCEPTANCE_TARGET_SHA = "cef2647c394909fb268b621a5e6074b49c3aa41a285c75082d7d976f48e62afc"

RUNTIME_WEIGHTS = "POSTV16_AV1_D_R6_ACCEPTED_TRANSPORT_FROZEN.weights.h5"
RUNTIME_NORMALIZATION = "POSTV16_AV1_D_R6_C3_Conditioning_Normalization_Parameters.npz"
RUNTIME_C2_CONTRACT = "POSTV16_AV1_D_R6_C2_Sampling_Authority_Contract.json"
RUNTIME_C3_CONTRACT = "POSTV16_AV1_D_R6_C3_Conditioning_Authority_Contract.json"

EXPECTED_REQUIRED_SEQUENCE = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
]
EXPECTED_TIME_CHANNELS = ["target_time_hat", "target_eta"]
EXPECTED_C26_CHANNELS = EXPECTED_REQUIRED_SEQUENCE + EXPECTED_TIME_CHANNELS
EXPECTED_STATIC = ["log_streamline_weight_z"]


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
        check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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


def find_named_exact(roots: list[Path], name: str, expected_sha: str) -> Path:
    hits: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p) == expected_sha:
                    hits.append(p.resolve())
            except OSError:
                pass
    if not hits:
        raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    return sorted(set(hits), key=lambda p: (len(str(p)), str(p)))[0]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def self_test() -> None:
    if EXPECTED_C26_CHANNELS != [
        "xi","pollock_tau_hat","adv_tau_hat","log10_Kh",
        "log10_Kz_over_Kh","porosity","pressure_z",
        "target_time_hat","target_eta",
    ]:
        raise RuntimeError("channel_order")
    if len(SELECTED_SHA) != 64 or len(C3_NORMALIZATION_SHA) != 64:
        raise RuntimeError("sha_lengths")
    print("POSTV16-AV1-D-R6 self-test: PASS")


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

    print("=" * 180)
    print("POSTV16-AV1-D-R6 — ACCEPTED PI-RNN DEPLOYMENT PROMOTION + CANONICAL PAD-STREAM RUNTIME BINDING")
    print("=" * 180)
    print("NO TRAINING. NO MODEL INFERENCE. NO ACCEPTANCE-TARGET OPENING. NO NEW GEOLOGY.")
    print("THE ACCEPTED R5E CHECKPOINT IS PROMOTED BYTE-FOR-BYTE INTO A GENERIC DEPLOYMENT RUNTIME.")
    print("R5 ACCEPTANCE EVIDENCE IS NOT COPIED FORWARD AS RUNTIME INPUT.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_R5E_commit", parent == PARENT_R5E_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, blob in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == blob, actual)

        for p, blob, label in (
            (root / C2_CONTRACT_REL, C2_CONTRACT_BLOB, "C2_contract"),
            (root / C3_CONTRACT_REL, C3_CONTRACT_BLOB, "C3_contract"),
        ):
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{label}_git_blob_exact", actual == blob, actual)

        stage = "R5E_binding"

        r5e = drive / R5E_REL
        gate("R5E_output_present", r5e.is_dir(), str(r5e))
        m5e = verify_manifest(r5e, R5E_MANIFEST)
        gate("R5E_manifest_SHA_closure", True, len(m5e))

        summary = load_json(r5e / R5E_SUMMARY)
        registry = load_json(r5e / R5E_REGISTRY)
        closure = load_json(r5e / R5E_CLOSURE)

        gate("R5E_status_exact", summary["status"] == R5E_STATUS, summary["status"])
        gate("R5E_branch_closed", summary["R5_branch_closed"] is True)
        gate("R5E_R6_authorized", summary["R6_deployment_integration_authorized"] is True)
        gate("R5E_no_new_training", summary["new_training_performed"] is False)
        gate("R5E_no_new_inference", summary["new_model_inference_performed"] is False)
        gate("R5E_no_target_opening", summary["target_array_opened"] is False)

        tc = registry["transport_checkpoint"]
        gate("R5E_registry_role_exact", tc["role"] == "ACCEPTED_POSTV16_TRANSPORT_DEPLOYMENT_CHECKPOINT")
        gate("R5E_registry_candidate_exact", tc["candidate_id"] == SELECTED_ID, tc["candidate_id"])
        gate("R5E_registry_weights_SHA_exact", tc["sha256"] == SELECTED_SHA, tc["sha256"])
        gate("R5E_registry_immutable", tc["immutable"] is True)
        gate("R5E_registry_modification_forbidden", tc["modification_authorized"] is False)
        gate("R5E_registry_retraining_forbidden", tc["retraining_under_R5_authorized"] is False)
        gate("R5E_registry_architecture_blob_exact", tc["architecture_authority"]["git_blob"] == C26_BLOB)
        gate("R5E_registry_input_shape_exact", tc["architecture_authority"]["input_shape"] == [201,9])
        gate("R5E_registry_param_count_exact", int(tc["architecture_authority"]["parameter_count"]) == 52033)

        sem = tc["conditioning_semantics"]
        gate("R5E_required_sequence_channels_exact", sem["required_sequence_channels"] == EXPECTED_REQUIRED_SEQUENCE, sem["required_sequence_channels"])
        gate("R5E_time_channels_exact", sem["time_channels"] == EXPECTED_TIME_CHANNELS, sem["time_channels"])
        gate("R5E_normalization_SHA_exact", sem["normalization_authority_sha256"] == C3_NORMALIZATION_SHA, sem["normalization_authority_sha256"])
        gate("R5E_sample_order_exact", sem["sample_order"] == "time-major then streamline")

        ev = registry["acceptance_evidence"]
        gate("R5E_geology0031_consumed_evidence", ev["role"] == "CONSUMED_FINAL_ACCEPTANCE_EVIDENCE")
        gate("R5E_geology0031_no_future_untouched_role", ev["future_untouched_independent_test_role"] is False)
        gate("R5E_acceptance_conditioning_SHA_exact", ev["conditioning_sha256"] == ACCEPTANCE_CONDITIONING_SHA)
        gate("R5E_acceptance_truth_SHA_exact", ev["truth_sha256"] == ACCEPTANCE_TARGET_SHA)

        nl = registry["next_lineage"]
        gate("R5E_next_R6_authorized", nl["R6_deployment_integration_authorized"] is True)
        gate("R5E_R6_checkpoint_load_allowed", nl["R6_may_load_accepted_checkpoint"] is True)
        gate("R5E_R6_weight_change_forbidden", nl["R6_may_modify_accepted_checkpoint_weights"] is False)
        gate("R5E_R6_architecture_change_forbidden", nl["R6_may_change_C26_architecture_under_this_registration"] is False)
        gate("R5E_R6_normalization_refit_forbidden", nl["R6_may_refit_C3_normalization_under_this_registration"] is False)

        gate("R5E_closure_branch_state_exact", closure["R5_branch_state"] == "CLOSED_AFTER_VALID_ONE_TOUCH_PASS")
        gate("R5E_closure_checkpoint_unmodified", closure["accepted_checkpoint_modified"] is False)
        gate("R5E_closure_R6_authorized", closure["R6_deployment_integration_authorized"] is True)

        source_weights = r5e / R5E_ACCEPTED_WEIGHTS
        gate("R5E_accepted_weights_present", source_weights.is_file(), str(source_weights))
        gate(
            "R5E_accepted_weights_SHA_exact",
            source_weights.is_file() and sha256_file(source_weights) == SELECTED_SHA,
            sha256_file(source_weights) if source_weights.is_file() else "missing",
        )

        stage = "frozen_conditioning_authority_binding"

        c2_contract = load_json(root / C2_CONTRACT_REL)
        c3_contract = load_json(root / C3_CONTRACT_REL)

        gate("C2_authoritative_coordinate_pollock", c2_contract["authoritative_coordinate"] == "pollock_tof_s")
        gate("C2_shape_1078x201", c2_contract["database_shape"] == {"streamlines":1078,"nodes_per_streamline":201})
        gate("C2_sampling_method_exact", c2_contract["sampling"]["method"] == "trilinear cell-centered")
        gate("C2_origin_exact", c2_contract["sampling"]["origin_center_m"] == [0.0,0.0,0.0])
        gate("C2_spacing_exact", c2_contract["sampling"]["grid_spacing_m"] == [6.096,6.096,1.2192])
        gate("C2_raw_normalization_not_performed", c2_contract["normalization"]["performed"] is False)

        gate("C3_transport_coordinate_exact", c3_contract["transport_coordinate"]["authoritative_raw"] == "pollock_tof_s")
        gate("C3_required_sequence_exact", c3_contract["required_sequence_channels"] == EXPECTED_REQUIRED_SEQUENCE)
        gate("C3_required_static_exact", c3_contract["required_static_channels"] == EXPECTED_STATIC)
        gate("C3_normalization_artifact_SHA_exact", c3_contract["normalization_parameters"]["sha256"] == C3_NORMALIZATION_SHA)

        c3_npz = find_named_exact([root, drive], C3_NORMALIZATION_NAME, C3_NORMALIZATION_SHA)
        gate("C3_normalization_binary_exact", sha256_file(c3_npz) == C3_NORMALIZATION_SHA, str(c3_npz))

        with np.load(c3_npz, allow_pickle=False) as z:
            required_keys = {"pressure_mean_psi","pressure_std_psi","ln_weight_mean","ln_weight_std"}
            gate("C3_normalization_required_keys_present", required_keys.issubset(set(z.files)), sorted(z.files))
            pmean = float(np.asarray(z["pressure_mean_psi"]).reshape(-1)[0])
            pstd = float(np.asarray(z["pressure_std_psi"]).reshape(-1)[0])
            lwmean = float(np.asarray(z["ln_weight_mean"]).reshape(-1)[0])
            lwstd = float(np.asarray(z["ln_weight_std"]).reshape(-1)[0])

        gate("C3_pressure_stats_finite", np.isfinite(pmean) and np.isfinite(pstd) and pstd > 0, [pmean,pstd])
        gate("C3_logweight_stats_finite", np.isfinite(lwmean) and np.isfinite(lwstd) and lwstd > 0, [lwmean,lwstd])

        stage = "accepted_model_architecture_binding"

        c26 = load_module(root / C26, "postv16_r6_c26")
        import tensorflow as tf
        try:
            tf.config.experimental.enable_op_determinism()
        except Exception:
            pass
        tf.keras.utils.set_random_seed(16021)

        model = c26.model()
        gate("C26_parameter_count_52033", model.count_params() == 52033, model.count_params())
        gate("C26_input_shape_exact", tuple(model.input_shape) == (None,201,9), model.input_shape)
        gate("C26_output_shape_exact", tuple(model.output_shape) == (None,201), model.output_shape)

        # Load only to prove byte-compatible architecture binding. NO inference.
        model.load_weights(source_weights)
        gate("accepted_weights_load_into_exact_C26_architecture", True)

        stage = "canonical_runtime_promotion"

        out.mkdir(parents=True, exist_ok=True)

        runtime_weights = out / RUNTIME_WEIGHTS
        if runtime_weights.exists():
            gate("existing_runtime_weights_SHA_exact", sha256_file(runtime_weights) == SELECTED_SHA, sha256_file(runtime_weights))
        else:
            shutil.copyfile(source_weights, runtime_weights)
        gate("runtime_weights_byte_identity_exact", sha256_file(runtime_weights) == SELECTED_SHA, sha256_file(runtime_weights))

        runtime_norm = out / RUNTIME_NORMALIZATION
        if runtime_norm.exists():
            gate("existing_runtime_normalization_SHA_exact", sha256_file(runtime_norm) == C3_NORMALIZATION_SHA, sha256_file(runtime_norm))
        else:
            shutil.copyfile(c3_npz, runtime_norm)
        gate("runtime_normalization_byte_identity_exact", sha256_file(runtime_norm) == C3_NORMALIZATION_SHA, sha256_file(runtime_norm))

        c2_copy = out / RUNTIME_C2_CONTRACT
        c3_copy = out / RUNTIME_C3_CONTRACT
        c2_bytes = (root / C2_CONTRACT_REL).read_bytes()
        c3_bytes = (root / C3_CONTRACT_REL).read_bytes()
        if c2_copy.exists() and c2_copy.read_bytes() != c2_bytes:
            raise GateError("existing_C2_runtime_contract_differs")
        if c3_copy.exists() and c3_copy.read_bytes() != c3_bytes:
            raise GateError("existing_C3_runtime_contract_differs")
        if not c2_copy.exists():
            c2_copy.write_bytes(c2_bytes)
        if not c3_copy.exists():
            c3_copy.write_bytes(c3_bytes)

        gate("runtime_C2_contract_git_blob_identity", git_text(root,"hash-object",str(c2_copy)) == C2_CONTRACT_BLOB)
        gate("runtime_C3_contract_git_blob_identity", git_text(root,"hash-object",str(c3_copy)) == C3_CONTRACT_BLOB)

        runtime_schema = {
            "milestone": MILESTONE,
            "schema_id": "POSTV16_AV1_D_R6_CANONICAL_ACCEPTED_TRANSPORT_RUNTIME_SCHEMA_V1",
            "model": {
                "candidate_id": SELECTED_ID,
                "weights_artifact": RUNTIME_WEIGHTS,
                "weights_sha256": SELECTED_SHA,
                "architecture_source": C26,
                "architecture_git_blob": C26_BLOB,
                "input_shape_per_sample": [201,9],
                "output_shape_per_sample": [201],
                "parameter_count": 52033,
                "weights_mutable": False,
                "architecture_mutable": False,
            },
            "predictor_channel_order": EXPECTED_C26_CHANNELS,
            "channel_construction": {
                "xi": "frozen common 201-node transport coordinate",
                "pollock_tau_hat": "pollock_tau_s / terminal_pollock_tau_s per streamline",
                "adv_tau_hat": "C2-sampled directional ADV travel time / terminal_pollock_tau_s",
                "log10_Kh": "log10(sqrt(Kx_mD * Ky_mD)) after frozen C2 sampling",
                "log10_Kz_over_Kh": "log10(Kz_mD / Kh_mD) after frozen C2 sampling",
                "porosity": "raw sampled porosity",
                "pressure_z": "(pressure_psi - frozen_C3_pressure_mean_psi) / frozen_C3_pressure_std_psi",
                "target_time_hat": "target_time_days / 1000.0",
                "target_eta": "target_time_days * 86400 / terminal_pollock_tau_s",
            },
            "normalization": {
                "artifact": RUNTIME_NORMALIZATION,
                "sha256": C3_NORMALIZATION_SHA,
                "refit_allowed": False,
                "pressure_mean_psi": pmean,
                "pressure_std_psi": pstd,
                "ln_weight_mean": lwmean,
                "ln_weight_std": lwstd,
            },
            "static_sidecar": {
                "C3_required_static_channel": "log_streamline_weight_z",
                "formula": "(ln(streamline_weight_m3_s) - frozen_ln_weight_mean) / frozen_ln_weight_std",
                "concatenated_to_C26_predictor": False,
                "reason": "exact accepted C26 architecture is fixed at 201x9",
                "raw_streamline_weight_m3_s_preserved": True,
            },
            "sample_axis": {
                "generic_runtime_sample_count": "N",
                "multi_time_case_order": "time-major then streamline",
                "hardcoded_geology0031_sample_count": False,
            },
            "output_representation": {
                "model_output": "201-node saturation sequence",
                "direct_saturation_averaging_to_200_CVs": "PROHIBITED",
                "required_bridge": "C26 saturation -> component mass -> exact B1 half-overlap projection -> E37A 200-CV inversion",
                "B1_source": B1,
                "B1_git_blob": B1_BLOB,
                "E37A_source": E37A,
                "E37A_git_blob": E37A_BLOB,
            },
            "runtime_scope": {
                "accepted_checkpoint_is_generic_runtime_component": True,
                "geology0031_conditioning_is_runtime_input": False,
                "geology0031_truth_is_runtime_input": False,
                "acceptance_evidence_reused_for_runtime_prediction": False,
                "R5_accuracy_claim_extended_by_R6": False,
            },
        }

        deployment_registry = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "registry_id": "POSTV16_AV1_D_R6_CANONICAL_PAD_STREAM_ACCEPTED_TRANSPORT_RUNTIME_V1",
            "parent_acceptance_closure": {
                "R5E_commit": PARENT_R5E_COMMIT,
                "R5E_runner_blob": R5E_BLOB,
                "R5_branch_closed": True,
            },
            "runtime_artifacts": {
                "weights": {
                    "file": RUNTIME_WEIGHTS,
                    "sha256": SELECTED_SHA,
                },
                "C3_normalization": {
                    "file": RUNTIME_NORMALIZATION,
                    "sha256": C3_NORMALIZATION_SHA,
                },
                "C2_sampling_contract": {
                    "file": RUNTIME_C2_CONTRACT,
                    "git_blob": C2_CONTRACT_BLOB,
                },
                "C3_conditioning_contract": {
                    "file": RUNTIME_C3_CONTRACT,
                    "git_blob": C3_CONTRACT_BLOB,
                },
            },
            "scientific_firewall": {
                "new_training_performed": False,
                "model_inference_performed": False,
                "acceptance_target_opened": False,
                "new_geology_generated": False,
                "weights_modified": False,
                "architecture_modified": False,
                "normalization_refit": False,
                "acceptance_conditioning_copied_into_runtime": False,
                "acceptance_truth_copied_into_runtime": False,
                "new_accuracy_or_generalization_claim_created": False,
            },
            "next": {
                "milestone": "POSTV16-AV1-D-R7",
                "name": "Full End-to-End PAD-Stream Integration with Accepted Transport Runtime",
                "authorized": True,
                "goal": (
                    "connect geology -> pressure -> conservative Darcy fluxes -> Pollock -> "
                    "runtime conditioning -> accepted C26 transport -> conservative B1/E37A "
                    "representation bridge/mapback under one canonical execution path"
                ),
            },
        }

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "repository_head": head,
            "repository_parent": parent,
            "accepted_candidate": SELECTED_ID,
            "accepted_weights_sha256": SELECTED_SHA,
            "runtime_input_shape_per_sample": [201,9],
            "runtime_output_shape_per_sample": [201],
            "C3_normalization_sha256": C3_NORMALIZATION_SHA,
            "new_training_performed": False,
            "model_inference_performed": False,
            "acceptance_target_opened": False,
            "weights_modified": False,
            "architecture_modified": False,
            "normalization_refit": False,
            "R7_end_to_end_integration_authorized": True,
        }

        immutable_publish(
            out,
            {
                "PAD_Stream_POSTV16_AV1_D_R6_Summary.json": json_bytes(summary_out),
                "POSTV16_AV1_D_R6_Canonical_Transport_Runtime_Schema.json": json_bytes(runtime_schema),
                "POSTV16_AV1_D_R6_Canonical_Deployment_Registry.json": json_bytes(deployment_registry),
                "POSTV16_AV1_D_R6_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            },
        )

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV1_D_R6_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(
            out,
            {"POSTV16_AV1_D_R6_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print("\n" + "=" * 180)
        print("POSTV16-AV1-D-R6: PASS")
        print("=" * 180)
        print(f"{'Status':98}: {STATUS_PASS}")
        print(f"{'Accepted candidate':98}: {SELECTED_ID}")
        print(f"{'Runtime weights SHA256':98}: {SELECTED_SHA}")
        print(f"{'Runtime C3 normalization SHA256':98}: {C3_NORMALIZATION_SHA}")
        print(f"{'C26 input / output per sample':98}: (201, 9) / (201,)")
        print(f"{'C26 parameter count':98}: 52033")
        print(f"{'C3 static sidecar concatenated to predictor':98}: False")
        print(f"{'Required conservative output bridge':98}: B1 component-mass projection -> E37A 200-CV inversion")
        print(f"{'Acceptance conditioning copied into runtime':98}: False")
        print(f"{'Acceptance truth copied into runtime':98}: False")
        print(f"{'Training / inference in R6':98}: False / False")
        print(f"{'Weights / architecture / normalization changed':98}: False / False / False")
        print(f"{'R7 end-to-end integration authorized':98}: True")
        print(f"{'NEXT':98}: POSTV16-AV1-D-R7 — full end-to-end PAD-Stream integration")
        print("=" * 180)
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
            "model_inference_performed": False,
            "acceptance_target_opened": False,
            "new_geology_generated": False,
            "weights_modified": False,
            "R7_end_to_end_integration_authorized": False,
            "next_action": (
                "Audit only this R6 deployment/provenance/schema binding failure. "
                "Do not retrain, modify the accepted checkpoint, refit normalization, "
                "or reuse R5 acceptance evidence as runtime input."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R6_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R6_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 180)
        print("POSTV16-AV1-D-R6: BLOCKED")
        print("=" * 180)
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
