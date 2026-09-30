#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F

MILESTONE = "V16E-1B2CUDA8L"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-008"

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")

CUDA6 = REPO / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"

CUDA8G_SOURCE = REPO / "PAD_Stream_V16E1B2CUDA8G_Stage2_Architecture_Redesign_and_New_Certification_Protocol_Freeze.py"
CUDA8G_ROOT = DRIVE / "provenance" / "stage2_redesign" / "V16E1B2CUDA8G_ARCHITECTURE_AND_CERTIFICATION_PROTOCOL_FREEZE"
CUDA8G_CERTIFICATION = CUDA8G_ROOT / "V16E1B2CUDA8G_Stage2_Certification_Protocol.json"

CUDA8J_SOURCE = REPO / "PAD_Stream_V16E1B2CUDA8J_Final_Stage2_Development_Decision_and_COMP008_Training_Contract_Freeze.py"
CUDA8J_ROOT = DRIVE / "provenance" / "stage2_redesign" / "V16E1B2CUDA8J_FINAL_STAGE2_DEVELOPMENT_CONTRACT_FREEZE"
CUDA8J_ARCHITECTURE = CUDA8J_ROOT / "V16E1B2CUDA8J_COMP008_Architecture_Contract.json"
CUDA8J_LOSS = CUDA8J_ROOT / "V16E1B2CUDA8J_COMP008_Loss_and_Physics_Contract.json"
CUDA8J_TRAINING = CUDA8J_ROOT / "V16E1B2CUDA8J_COMP008_Production_Training_Contract.json"
CUDA8J_CERTIFICATION = CUDA8J_ROOT / "V16E1B2CUDA8J_Stage2_Blind_Certification_Contract.json"
CUDA8J_DECISION = CUDA8J_ROOT / "V16E1B2CUDA8J_Final_Development_Decision.json"
CUDA8J_SUMMARY = CUDA8J_ROOT / "PAD_Stream_V16E1B2CUDA8J_Summary.json"
CUDA8J_HANDOFF = CUDA8J_ROOT / "V16E1B2CUDA8J_Handoff.md"

CUDA8K_SOURCE = REPO / "PAD_Stream_V16E1B2CUDA8K_COMP008_Authorized_Production_Training_Runner.py"
RUN008 = DRIVE / "runs" / EXPERIMENT
HISTORY008 = RUN008 / "V16E_BLREP_COMP_CUDA_008_HISTORY.json"
COMP008 = RUN008 / "V16E_BLREP_COMP_CUDA_008.pt"
RECOVERY008_E0800 = RUN008 / "recovery" / "V16E_BLREP_COMP_CUDA_008_RECOVERY_E0800.pt"
MANIFEST008 = RUN008 / "V16E_BLREP_COMP_CUDA_008_MANIFEST.json"
SUMMARY008 = RUN008 / "PAD_Stream_V16E1B2CUDA8K_Summary.json"
HANDOFF008 = RUN008 / "V16E1B2CUDA8K_Handoff.md"

COMP004 = DRIVE / "provenance" / "xpu_reference" / "V16E_BLREP_COMP_XPU_004.pt"
COMP005 = DRIVE / "runs" / "V16E-BLREP-COMP-CUDA-005" / "V16E_BLREP_COMP_CUDA_005.pt"
COMP007 = DRIVE / "runs" / "V16E-BLREP-COMP-CUDA-007" / "V16E_BLREP_COMP_CUDA_007.pt"

BLIND_CERT = DRIVE / "datasets" / "stage2_redesign" / "sealed_certification" / "V16E_STAGE2_BLIND_CERT_GODUNOV_SEED20260919.npz"
BLIND_CERT_SEAL = DRIVE / "datasets" / "stage2_redesign" / "sealed_certification" / "V16E_STAGE2_BLIND_CERT_SEALED.json"

PROVENANCE_ROOT = DRIVE / "provenance" / "stage2_redesign" / "V16E1B2CUDA8L_COMP008_BLIND_STAGE2_CERTIFICATION"
PROVENANCE_ROOT.mkdir(parents=True, exist_ok=True)

OPEN_EVENT_PATH = PROVENANCE_ROOT / "V16E1B2CUDA8L_Blind_CERT_Opened_Event.json"
PARTIAL_PATH = PROVENANCE_ROOT / "V16E1B2CUDA8L_Partial_Blind_Metrics.json"
RESULTS_PATH = PROVENANCE_ROOT / "V16E1B2CUDA8L_Blind_Stage2_Certification_Results.json"
DISPOSITION_PATH = PROVENANCE_ROOT / "V16E1B2CUDA8L_Stage2_Final_Disposition.json"
SUMMARY_PATH = PROVENANCE_ROOT / "PAD_Stream_V16E1B2CUDA8L_Summary.json"
HANDOFF_PATH = PROVENANCE_ROOT / "V16E1B2CUDA8L_Handoff.md"

EXPECTED = {
    "CUDA6": "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",
    "CUDA8G_SOURCE": "af7cbe21f216be173add5e59c954707931e433459d1bf817a0ec711bee1267b2",
    "CUDA8G_CERTIFICATION": "eda537ef04b83fc22ed61881ea204136e531bdf330bbced6f497eff40f6e8490",
    "CUDA8J_SOURCE": "cccf266b6b1e84047e233823da8100d14d61ce400931b169dc365fa680c11187",
    "CUDA8J_ARCHITECTURE": "4cae0a004c445f589aae040c340f026ddf285eff07ac67ac42e9710ba2034ab5",
    "CUDA8J_LOSS": "b5745fa551c25c0713051adc90125382485df0d907301d2db99577bf5763d931",
    "CUDA8J_TRAINING": "9a195b03f303eca78471c9b9d5df653468e48fa90758158da604bfb149229a6e",
    "CUDA8J_CERTIFICATION": "71abcc4a28dac85798d7673d3a16825303d327f7d85ae2473e17f658b354534d",
    "CUDA8J_DECISION": "b1f31f32591dc75950ddad9c2aed24b0fd92f9d5828075fa59649a1d86c71fc0",
    "CUDA8J_SUMMARY": "57465a49d5e24f206f14f36e4f583e948ab8588b6b4cb0435603fb26ace23332",
    "CUDA8J_HANDOFF": "290369361c985a47a7e221dd8a7e5c1742f89b636adcc2e90a4b7b0bdcbc6d0b",
    "CUDA8K_SOURCE": "75b5cb3cca6d84de542c9d2b8e025b40dc0c5925d3bdf0bc653e5e376aacda6f",
    "HISTORY008": "290163d44835a48c0cce18eb8814d991ee8336328a684c60895229ea26fe9f14",
    "COMP008": "3ee18d9a2afe4eb8e00fb65b1c7497c57d7be8c8fd6c75a229368403ab4e7014",
    "COMP008_STATE": "4c779ab08fead493566bfb8c5edd3d7a1e7103e4e69ab89f956f2e255e66c375",
    "RECOVERY008_E0800": "ca9bb1b3fd9b88b7500d444a2412f7679a2c6cf5fb32cb381b6604191e0b703d",
    "MANIFEST008": "d32361f3f5fc711337f382073ccf9f8469e2ff566210b3690bf0936514758e3d",
    "SUMMARY008": "d8f75551b2823b2c01446b2399a57ce39d6637228dc91f175f671d34eab6a4fd",
    "HANDOFF008": "b1977fdecb0a518058c2fd11fc9c1d79e1dc6514d4b247784ae8241025e941a7",
    "COMP004": "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69",
    "COMP005": "aaca2ae60d7a789bf6d3d2a177d1b3b5188181809597b1be6901ed7473e0906f",
    "COMP007": "98521407ab803b4899a75988c65f303f94e9447dd25e159e7cc3ffdb7e9c042d",
    "BLIND_CERT": "0eaf3fc1a6be77b2b804baf54e03837346754a411b92e5b1b19f83f3d8ddf265",
    "BLIND_CERT_SEAL": "7dd0bdd24c05e8d0265f77030247da3739b00eeca41af8c9495c22eaddc1c1ae",
    "B2S": "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea",
    "BASE_M": "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18",
    "ETA_J": "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c",
    "CUDA3": "1065788f8f82d7f58aba873b8396cf70a17906571421315151640a0c879df886",
}

N_CERT = 2880
EVAL_MICROBATCH = 256
ADOPTED_CHUNK = 64
REL_COMPARE_TOL = 1.0e-6
ABS_COMPARE_TOL = 1.0e-12
BOUND_TOL = 1.0e-6
ENDPOINT_TOL = 1.0e-6

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def state_tensor_hash(state) -> str:
    h = hashlib.sha256()
    for name in sorted(state.keys()):
        t = state[name].detach().cpu().contiguous()
        h.update(name.encode("utf-8"))
        h.update(str(t.dtype).encode("utf-8"))
        h.update(str(tuple(t.shape)).encode("utf-8"))
        h.update(t.numpy().tobytes())
    return h.hexdigest()

def gate(name, condition):
    ok = bool(condition)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        raise RuntimeError(f"CUDA8L certification gate failed: {name}")

def atomic_json(path: Path, obj):
    tmp = Path(str(path) + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def finite_tensor(x):
    return bool(torch.isfinite(x).all().item())

def native_nc_mask_np(values, nc):
    target = np.asarray(nc, dtype=values.dtype)
    return values == target

def compare_le(candidate, reference):
    return float(candidate) <= float(reference) * (1.0 + REL_COMPARE_TOL) + ABS_COMPARE_TOL

def extract_model_state(payload):
    if not isinstance(payload, dict):
        raise RuntimeError("Checkpoint payload is not a dictionary.")
    for key in ("model_state_dict", "model_state", "state_dict"):
        if key in payload and isinstance(payload[key], dict):
            return payload[key]
    if payload and all(torch.is_tensor(v) for v in payload.values()):
        return payload
    raise RuntimeError("No supported model state found in checkpoint.")

def load_strict(model, path):
    payload = torch.load(path, map_location="cpu", weights_only=False)
    state = extract_model_state(payload)
    result = model.load_state_dict(state, strict=True)
    if result.missing_keys or result.unexpected_keys:
        raise RuntimeError(f"Strict load failed for {path.name}.")
    return payload

def error_metrics(pred, truth):
    e = pred - truth
    mse = float(np.mean(e ** 2))
    return {
        "mse": mse,
        "rmse": math.sqrt(mse),
        "mae": float(np.mean(np.abs(e))),
        "max_abs": float(np.max(np.abs(e))),
    }

def import_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8L")
print("ONE-TIME BLIND STAGE-2 CERTIFICATION — COMP008 vs COMP004 / COMP005 / COMP007")
print("=" * 110)
print()
print("NO TRAINING. NO OPTIMIZER. NO DEV. NO ORIGINAL HOLDOUT.")
print("NO MODEL SELECTION. NO THRESHOLD TUNING. NO HYPERPARAMETER CHANGES.")
print("NO OOD. NO TOF.")
print()

AUTHORITY = {
    "CUDA6": CUDA6,
    "CUDA8G_SOURCE": CUDA8G_SOURCE,
    "CUDA8G_CERTIFICATION": CUDA8G_CERTIFICATION,
    "CUDA8J_SOURCE": CUDA8J_SOURCE,
    "CUDA8J_ARCHITECTURE": CUDA8J_ARCHITECTURE,
    "CUDA8J_LOSS": CUDA8J_LOSS,
    "CUDA8J_TRAINING": CUDA8J_TRAINING,
    "CUDA8J_CERTIFICATION": CUDA8J_CERTIFICATION,
    "CUDA8J_DECISION": CUDA8J_DECISION,
    "CUDA8J_SUMMARY": CUDA8J_SUMMARY,
    "CUDA8J_HANDOFF": CUDA8J_HANDOFF,
    "CUDA8K_SOURCE": CUDA8K_SOURCE,
    "HISTORY008": HISTORY008,
    "COMP008": COMP008,
    "RECOVERY008_E0800": RECOVERY008_E0800,
    "MANIFEST008": MANIFEST008,
    "SUMMARY008": SUMMARY008,
    "HANDOFF008": HANDOFF008,
    "COMP004": COMP004,
    "COMP005": COMP005,
    "COMP007": COMP007,
    "BLIND_CERT": BLIND_CERT,
    "BLIND_CERT_SEAL": BLIND_CERT_SEAL,
}

print("FROZEN AUTHORITY GATES — BEFORE CERT OPEN")
for name, path in AUTHORITY.items():
    gate(f"{name}_exists", path.exists())
    gate(f"{name}_SHA_exact", sha256(path) == EXPECTED[name])

cert_contract = json.loads(CUDA8J_CERTIFICATION.read_text(encoding="utf-8"))
decision_j = json.loads(CUDA8J_DECISION.read_text(encoding="utf-8"))
summary_k = json.loads(SUMMARY008.read_text(encoding="utf-8"))
ckpt008_payload = torch.load(COMP008, map_location="cpu", weights_only=False)

print()
print("CUDA8J / CUDA8K CONTRACT GATES")

gate("CUDA8J_development_cycle_closed", decision_j["development_cycle_closed"] is True)
gate("CUDA8J_no_further_adjustments", decision_j["further_current_cycle_architecture_loss_hyperparameter_adjustment_authorized"] is False)
gate("CUDA8J_Stage2_not_predeclared_certified", decision_j["Stage2_certified"] is False)
gate("CUDA8J_B3_not_predeclared_authorized", decision_j["B3_authorized"] is False)
gate("CUDA8J_CERT_single_use", cert_contract["blind_dataset"]["single_use"] is True)
gate("CUDA8J_CERT_dataset_SHA_exact", cert_contract["blind_dataset"]["sha256"] == EXPECTED["BLIND_CERT"])

gate("CUDA8K_completed_800_epochs", int(summary_k["completed_epochs"]) == 800)
gate("CUDA8K_completed_1600_steps", int(summary_k["optimizer_steps_completed"]) == 1600)
gate("CUDA8K_final_checkpoint_SHA_exact", summary_k["checkpoint_sha256"] == EXPECTED["COMP008"])
gate("CUDA8K_final_model_state_SHA_exact", summary_k["model_state_tensor_sha256"] == EXPECTED["COMP008_STATE"])
gate("CUDA8K_original_holdout_not_evaluated", summary_k["original_holdout_evaluated"] is False)
gate("CUDA8K_DEV_not_loaded", summary_k["DEV_loaded"] is False)
gate("CUDA8K_blind_CERT_not_loaded", summary_k["blind_CERT_loaded"] is False)
gate("CUDA8K_Stage2_not_predeclared_certified", summary_k["Stage2_certified"] is False)
gate("CUDA8K_B3_not_predeclared_authorized", summary_k["B3_authorized"] is False)

gate("COMP008_experiment_exact", ckpt008_payload["experiment"] == EXPERIMENT)
gate("COMP008_completed_epoch_800", int(ckpt008_payload["completed_epoch"]) == 800)
gate("COMP008_optimizer_steps_1600", int(ckpt008_payload["optimizer_steps_completed"]) == 1600)
gate("COMP008_runner_SHA_exact", ckpt008_payload["runner_sha256"] == EXPECTED["CUDA8K_SOURCE"])
gate("COMP008_model_state_declared_SHA_exact", ckpt008_payload["model_state_tensor_sha256"] == EXPECTED["COMP008_STATE"])
gate("COMP008_model_state_recomputed_SHA_exact", state_tensor_hash(ckpt008_payload["model_state_dict"]) == EXPECTED["COMP008_STATE"])
gate("COMP008_original_holdout_not_evaluated", ckpt008_payload["original_holdout_evaluated"] is False)
gate("COMP008_DEV_not_loaded", ckpt008_payload["DEV_loaded"] is False)
gate("COMP008_blind_CERT_not_loaded", ckpt008_payload["blind_CERT_loaded"] is False)
gate("COMP008_Stage2_not_predeclared_certified", ckpt008_payload["Stage2_certified"] is False)
gate("COMP008_B3_not_predeclared_authorized", ckpt008_payload["B3_authorized"] is False)

gate("CUDA_available", torch.cuda.is_available())
device = torch.device("cuda")
gpu_name = torch.cuda.get_device_name(0)
gpu_total_gib = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3

print()
print("RUNTIME")
print("  PyTorch :", torch.__version__)
print("  GPU     :", gpu_name)
print("  Memory  :", f"{gpu_total_gib:.3f} GiB")

gate("A100_runtime", "A100" in gpu_name)
gate("A100_memory_at_least_70GiB", gpu_total_gib >= 70.0)
gate("PyTorch_2_11_0_cu128", str(torch.__version__) == "2.11.0+cu128")

torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

C = import_by_path("cuda8l_cuda6", CUDA6)
B2S = C.import_module(C.B2S_SOURCE, "cuda8l_B2S")
M = C.import_module(B2S.BASE_RUNNER, "cuda8l_M")
J = C.import_module(B2S.B2J_SOURCE, "cuda8l_J")
CUDA3 = C.import_module(C.CUDA3_SOURCE, "cuda8l_CUDA3")

print()
print("SCIENTIFIC SOURCE GATES")
gate("B2S_SHA_exact", sha256(Path(B2S.__file__)) == EXPECTED["B2S"])
gate("BASE_M_SHA_exact", sha256(Path(M.__file__)) == EXPECTED["BASE_M"])
gate("ETA_J_SHA_exact", sha256(Path(J.__file__)) == EXPECTED["ETA_J"])
gate("CUDA3_SHA_exact", sha256(Path(CUDA3.__file__)) == EXPECTED["CUDA3"])

RUNNER_SHA = sha256(Path(__file__))

event_object = {
    "milestone": MILESTONE,
    "experiment": EXPERIMENT,
    "runner_sha256": RUNNER_SHA,
    "blind_CERT_sha256": EXPECTED["BLIND_CERT"],
    "COMP004_sha256": EXPECTED["COMP004"],
    "COMP005_sha256": EXPECTED["COMP005"],
    "COMP007_sha256": EXPECTED["COMP007"],
    "COMP008_sha256": EXPECTED["COMP008"],
    "COMP008_model_state_sha256": EXPECTED["COMP008_STATE"],
    "scientific_event": "SINGLE_FROZEN_STAGE2_BLIND_CERTIFICATION",
    "restart_policy": "same runner/hash may resume same certification event after technical interruption; no tuning or contract change allowed",
    "blind_CERT_opened": True,
}

if OPEN_EVENT_PATH.exists():
    existing_event = json.loads(OPEN_EVENT_PATH.read_text(encoding="utf-8"))
    gate("existing_CERT_event_exact", existing_event == event_object)
    print()
    print("RESUMING SAME FROZEN BLIND-CERTIFICATION EVENT.")
else:
    atomic_json(OPEN_EVENT_PATH, event_object)
    print()
    print("BLIND CERTIFICATION EVENT OPENED FOR THE FIRST TIME.")

OPEN_EVENT_SHA = sha256(OPEN_EVENT_PATH)

print()
print("=" * 110)
print("OPENING SEALED BLIND CERT DATASET")
print("=" * 110)

with np.load(BLIND_CERT, allow_pickle=False) as d:
    keys = set(d.files)
    gate("blind_CERT_required_schema", {"xi", "Sw", "p11", "tD", "ai", "at"}.issubset(keys))
    xi_c = np.array(d["xi"], copy=True)
    Sw_c = np.array(d["Sw"], copy=True)
    p11_c = np.array(d["p11"], copy=True)

gate("blind_CERT_profiles_2880", xi_c.shape[0] == N_CERT)
gate("blind_CERT_fan_nodes_64", xi_c.shape[1] == 64)
gate("blind_CERT_arrays_finite", np.isfinite(xi_c).all() and np.isfinite(Sw_c).all() and np.isfinite(p11_c).all())

nc_c = p11_c[:, 10]
nc0_mask = native_nc_mask_np(nc_c, 0.0)
ncpos_mask = ~nc0_mask

gate("blind_CERT_contains_Nc0", int(np.sum(nc0_mask)) > 0)
gate("blind_CERT_contains_Nc_positive", int(np.sum(ncpos_mask)) > 0)

teacher_tip_max_abs = float(np.max(np.abs(Sw_c[:, -1, 0] - p11_c[:, 9])))
gate("blind_CERT_teacher_RH_tip_contract", teacher_tip_max_abs <= ENDPOINT_TOL)

BaseEtaModel = J.build_eta_model_class(M)

class COMP007LiftedModel(BaseEtaModel):
    def forward(self, xi_seq, p11_phys):
        S_raw = super().forward(xi_seq, p11_phys)
        sor = p11_phys[:, 3:4].unsqueeze(1)
        Sw_star = p11_phys[:, 9:10].unsqueeze(1)
        S_inj = 1.0 - sor
        S0 = S_raw[:, 0:1, :]
        S1 = S_raw[:, -1:, :]
        return S_raw + (1.0 - xi_seq) * (S_inj - S0) + xi_seq * (Sw_star - S1)

class COMP008BoundedMonotoneModel(BaseEtaModel):
    EPSILON = 1.0e-8

    def forward(self, xi_seq, p11_phys):
        z = super().forward(xi_seq, p11_phys)
        interval_logits = 0.5 * (z[:, :-1, :] + z[:, 1:, :])
        q = F.softplus(interval_logits) + self.EPSILON
        w = q / q.sum(dim=1, keepdim=True)
        cumulative = torch.cumsum(w, dim=1)
        zero = torch.zeros_like(z[:, :1, :])
        one = torch.ones_like(z[:, :1, :])
        Ccoord = torch.cat([zero, cumulative[:, :-1, :], one], dim=1)
        sor = p11_phys[:, 3:4].unsqueeze(1)
        Sw_star = p11_phys[:, 9:10].unsqueeze(1)
        S_inj = 1.0 - sor
        return S_inj - (S_inj - Sw_star) * Ccoord

MODEL_SPECS = {
    "COMP004": {"checkpoint": COMP004, "kind": "base"},
    "COMP005": {"checkpoint": COMP005, "kind": "base"},
    "COMP007": {"checkpoint": COMP007, "kind": "lifted"},
    "COMP008": {"checkpoint": COMP008, "kind": "bounded"},
}

def make_model(label, spec):
    if spec["kind"] == "base":
        model = BaseEtaModel().to(device)
    elif spec["kind"] == "lifted":
        model = COMP007LiftedModel().to(device)
    elif spec["kind"] == "bounded":
        model = COMP008BoundedMonotoneModel().to(device)
    else:
        raise RuntimeError(f"Unknown model kind for {label}.")
    load_strict(model, spec["checkpoint"])
    model.eval()
    print(f"[PASS] {label}_strict_checkpoint_load")
    return model

engine = CUDA3.make_cuda3_chunked_batched_engine(ADOPTED_CHUNK)
original_engine = B2S.local_recurrent_derivatives_create_graph

def evaluate_model(label, spec):
    print()
    print("-" * 110)
    print(f"EVALUATING {label} ON BLIND CERT")
    print("-" * 110)

    model = make_model(label, spec)
    prediction_chunks = []

    with torch.no_grad():
        for m0 in range(0, N_CERT, EVAL_MICROBATCH):
            m1 = min(m0 + EVAL_MICROBATCH, N_CERT)
            xi = torch.from_numpy(xi_c[m0:m1]).to(device)
            p11 = torch.from_numpy(p11_c[m0:m1]).to(device)
            with torch.backends.cudnn.flags(enabled=False):
                pred = model(xi, p11)
            if not finite_tensor(pred):
                raise RuntimeError(f"{label}: nonfinite blind prediction.")
            prediction_chunks.append(pred.detach().cpu().numpy())
            del xi, p11, pred

    pred = np.concatenate(prediction_chunks, axis=0)

    source_global = error_metrics(pred, Sw_c)
    source_nc0 = error_metrics(pred[nc0_mask], Sw_c[nc0_mask])
    source_ncpos = error_metrics(pred[ncpos_mask], Sw_c[ncpos_mask])

    swc = p11_c[:, 2][:, None, None]
    sor = p11_c[:, 3][:, None, None]
    upper = 1.0 - sor

    lower_violation = float(np.max(np.maximum(swc - pred, 0.0)))
    upper_violation = float(np.max(np.maximum(pred - upper, 0.0)))

    inj_target = 1.0 - p11_c[:, 3]
    tip_target = p11_c[:, 9]
    inj_error = pred[:, 0, 0] - inj_target
    tip_error = pred[:, -1, 0] - tip_target

    injector_rmse = math.sqrt(float(np.mean(inj_error ** 2)))
    injector_max_abs = float(np.max(np.abs(inj_error)))
    tip_rmse = math.sqrt(float(np.mean(tip_error ** 2)))
    tip_max_abs = float(np.max(np.abs(tip_error)))

    dS = pred[:, 1:, 0] - pred[:, :-1, 0]
    mono_violation_fraction = float(np.mean(dS > 0.0))
    positive_slope_max = float(np.max(np.maximum(dS, 0.0)))

    residual_chunks = []
    B2S.local_recurrent_derivatives_create_graph = engine

    try:
        for m0 in range(0, N_CERT, EVAL_MICROBATCH):
            m1 = min(m0 + EVAL_MICROBATCH, N_CERT)
            xi = torch.from_numpy(xi_c[m0:m1]).to(device).detach().clone().requires_grad_(True)
            p11 = torch.from_numpy(p11_c[m0:m1]).to(device).detach().clone().requires_grad_(True)

            with torch.backends.cudnn.flags(enabled=False):
                S_pred, _unused_global, residual = B2S.corrected_physics_loss_training_graph(
                    M, model, xi, p11
                )

            if not finite_tensor(S_pred):
                raise RuntimeError(f"{label}: nonfinite corrected-physics prediction.")
            if not finite_tensor(residual):
                raise RuntimeError(f"{label}: nonfinite corrected residual.")

            residual_chunks.append(residual.detach().cpu().numpy())
            del xi, p11, S_pred, _unused_global, residual
            torch.cuda.empty_cache()

    finally:
        B2S.local_recurrent_derivatives_create_graph = original_engine

    residual_np = np.concatenate(residual_chunks, axis=0)

    def residual_metrics(mask):
        r = residual_np[mask]
        mse = float(np.mean(r ** 2))
        return {
            "mse": mse,
            "rmse": math.sqrt(mse),
            "mae": float(np.mean(np.abs(r))),
            "max_abs": float(np.max(np.abs(r))),
        }

    physics_global = residual_metrics(np.ones(N_CERT, dtype=bool))
    physics_nc0 = residual_metrics(nc0_mask)
    physics_ncpos = residual_metrics(ncpos_mask)

    metrics = {
        "source_native": {
            "global": source_global,
            "Nc0": source_nc0,
            "Nc_positive": source_ncpos,
        },
        "corrected_residual": {
            "global": physics_global,
            "Nc0": physics_nc0,
            "Nc_positive": physics_ncpos,
        },
        "physical": {
            "prediction_finite": bool(np.isfinite(pred).all()),
            "residual_finite": bool(np.isfinite(residual_np).all()),
            "lower_bound_max_violation": lower_violation,
            "upper_bound_max_violation": upper_violation,
            "injector_rmse": injector_rmse,
            "injector_max_abs": injector_max_abs,
            "tip_rmse": tip_rmse,
            "RH_tip_state_max_abs": tip_max_abs,
            "mono_violation_fraction": mono_violation_fraction,
            "positive_slope_max": positive_slope_max,
        },
    }

    print("Source global RMSE       :", f"{source_global['rmse']:.12e}")
    print("Source Nc=0 RMSE         :", f"{source_nc0['rmse']:.12e}")
    print("Source Nc>0 RMSE         :", f"{source_ncpos['rmse']:.12e}")
    print("Corrected global RMSE    :", f"{physics_global['rmse']:.12e}")
    print("Corrected Nc=0 RMSE      :", f"{physics_nc0['rmse']:.12e}")
    print("Corrected Nc>0 RMSE      :", f"{physics_ncpos['rmse']:.12e}")
    print("Tip RMSE                 :", f"{tip_rmse:.12e}")
    print("Mono violation fraction  :", f"{mono_violation_fraction:.12e}")
    print("Upper-bound max violation:", f"{upper_violation:.12e}")

    del model
    torch.cuda.empty_cache()
    return metrics

if PARTIAL_PATH.exists():
    partial = json.loads(PARTIAL_PATH.read_text(encoding="utf-8"))
    gate("partial_runner_SHA_exact", partial["runner_sha256"] == RUNNER_SHA)
    gate("partial_blind_CERT_SHA_exact", partial["blind_CERT_sha256"] == EXPECTED["BLIND_CERT"])
    metrics_all = partial["models"]
else:
    metrics_all = {}

for label in ("COMP004", "COMP005", "COMP007", "COMP008"):
    if label in metrics_all:
        print()
        print(f"[PASS] {label}_blind_metrics_already_frozen_in_same_event")
        continue

    metrics_all[label] = evaluate_model(label, MODEL_SPECS[label])

    atomic_json(
        PARTIAL_PATH,
        {
            "milestone": MILESTONE,
            "experiment": EXPERIMENT,
            "runner_sha256": RUNNER_SHA,
            "blind_CERT_sha256": EXPECTED["BLIND_CERT"],
            "open_event_sha256": OPEN_EVENT_SHA,
            "models": metrics_all,
        },
    )

gate(
    "all_four_model_metrics_present",
    set(metrics_all.keys()) == {"COMP004", "COMP005", "COMP007", "COMP008"},
)

metrics004 = metrics_all["COMP004"]
metrics005 = metrics_all["COMP005"]
metrics007 = metrics_all["COMP007"]
metrics008 = metrics_all["COMP008"]

print()
print("=" * 110)
print("FINAL FROZEN STAGE-2 BLIND ACCEPTANCE GATES")
print("=" * 110)

acceptance = {
    "preserve_COMP005_global_source_RMSE":
        compare_le(
            metrics008["source_native"]["global"]["rmse"],
            metrics005["source_native"]["global"]["rmse"],
        ),

    "preserve_COMP005_Nc_positive_source_RMSE":
        compare_le(
            metrics008["source_native"]["Nc_positive"]["rmse"],
            metrics005["source_native"]["Nc_positive"]["rmse"],
        ),

    "preserve_COMP005_global_corrected_RMSE":
        compare_le(
            metrics008["corrected_residual"]["global"]["rmse"],
            metrics005["corrected_residual"]["global"]["rmse"],
        ),

    "preserve_COMP005_Nc_positive_corrected_RMSE":
        compare_le(
            metrics008["corrected_residual"]["Nc_positive"]["rmse"],
            metrics005["corrected_residual"]["Nc_positive"]["rmse"],
        ),

    "restore_COMP004_Nc0_source_RMSE":
        compare_le(
            metrics008["source_native"]["Nc0"]["rmse"],
            metrics004["source_native"]["Nc0"]["rmse"],
        ),

    "restore_COMP004_Nc0_corrected_RMSE":
        compare_le(
            metrics008["corrected_residual"]["Nc0"]["rmse"],
            metrics004["corrected_residual"]["Nc0"]["rmse"],
        ),

    "restore_COMP004_tip_RMSE":
        compare_le(
            metrics008["physical"]["tip_rmse"],
            metrics004["physical"]["tip_rmse"],
        ),

    "restore_COMP004_mono_violation_fraction":
        compare_le(
            metrics008["physical"]["mono_violation_fraction"],
            metrics004["physical"]["mono_violation_fraction"],
        ),

    "predictions_finite":
        metrics008["physical"]["prediction_finite"] is True,

    "corrected_residual_finite":
        metrics008["physical"]["residual_finite"] is True,

    "lower_bound_PASS":
        metrics008["physical"]["lower_bound_max_violation"] <= BOUND_TOL,

    "upper_bound_PASS":
        metrics008["physical"]["upper_bound_max_violation"] <= BOUND_TOL,

    "injector_endpoint_PASS":
        metrics008["physical"]["injector_max_abs"] <= ENDPOINT_TOL,

    "RH_tip_state_PASS":
        metrics008["physical"]["RH_tip_state_max_abs"] <= ENDPOINT_TOL,
}

for name, ok in acceptance.items():
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")

all_acceptance_pass = all(acceptance.values())

if all_acceptance_pass:
    STAGE2_CERTIFIED = True
    B3_AUTHORIZED = True
    disposition = (
        "STAGE2_COMPRESSIBLE_CERTIFIED_"
        "COMP008_ALL_FROZEN_SINGLE_USE_BLIND_ACCEPTANCE_GATES_PASS_"
        "B3_CAPILLARY_STAGE3_AUTHORIZED"
    )
    next_milestone = (
        "V16E-1B3 — Stage-3 Capillary BL PI-RNN "
        "reproduction/development under the frozen four-phase BL roadmap"
    )
else:
    STAGE2_CERTIFIED = False
    B3_AUTHORIZED = False
    disposition = (
        "STAGE2_COMPRESSIBLE_RECORDED_UNRESOLVED_"
        "ONE_OR_MORE_FROZEN_SINGLE_USE_BLIND_ACCEPTANCE_GATES_FAIL_"
        "NO_CERT_DRIVEN_TUNING_AUTHORIZED_B3_REMAINS_BLOCKED"
    )
    next_milestone = (
        "Document the frozen Stage-2 limitation. "
        "Do not tune against this blind CERT set and do not begin B3 "
        "under the current certification rule."
    )

results = {
    "milestone": MILESTONE,
    "experiment": EXPERIMENT,
    "runner_sha256": RUNNER_SHA,
    "blind_CERT_opened": True,
    "blind_CERT_sha256": EXPECTED["BLIND_CERT"],
    "blind_CERT_profiles": N_CERT,
    "open_event_sha256": OPEN_EVENT_SHA,
    "restart_safe_same_event": True,
    "evaluation_geometry": {
        "microbatch": EVAL_MICROBATCH,
        "CUDA3_VJP_chunk": ADOPTED_CHUNK,
    },
    "comparison_tolerances": {
        "relative": REL_COMPARE_TOL,
        "absolute": ABS_COMPARE_TOL,
        "bound": BOUND_TOL,
        "endpoint": ENDPOINT_TOL,
    },
    "COMP004": metrics004,
    "COMP005": metrics005,
    "COMP007": metrics007,
    "COMP008": metrics008,
    "acceptance_gates": acceptance,
    "all_acceptance_gates_PASS": all_acceptance_pass,
    "Stage2_certified": STAGE2_CERTIFIED,
    "B3_authorized": B3_AUTHORIZED,
    "disposition": disposition,
    "next_milestone": next_milestone,
    "training_performed": False,
    "DEV_used": False,
    "original_holdout_used": False,
    "OOD_used": False,
    "TOF_used": False,
    "cert_driven_tuning_authorized": False,
}

atomic_json(RESULTS_PATH, results)
RESULTS_SHA = sha256(RESULTS_PATH)

disposition_artifact = {
    "milestone": MILESTONE,
    "experiment": EXPERIMENT,
    "runner_sha256": RUNNER_SHA,
    "results_sha256": RESULTS_SHA,
    "all_acceptance_gates_PASS": all_acceptance_pass,
    "Stage2_certified": STAGE2_CERTIFIED,
    "B3_authorized": B3_AUTHORIZED,
    "disposition": disposition,
    "blind_CERT_reuse_for_tuning": False,
    "further_current_cycle_repair_authorized": False,
    "next_milestone": next_milestone,
}

atomic_json(DISPOSITION_PATH, disposition_artifact)
DISPOSITION_SHA = sha256(DISPOSITION_PATH)

summary = {
    "milestone": MILESTONE,
    "experiment": EXPERIMENT,
    "runner_sha256": RUNNER_SHA,
    "open_event_sha256": OPEN_EVENT_SHA,
    "results_sha256": RESULTS_SHA,
    "disposition_sha256": DISPOSITION_SHA,
    "Stage2_certified": STAGE2_CERTIFIED,
    "B3_authorized": B3_AUTHORIZED,
    "disposition": disposition,
    "next_milestone": next_milestone,
    "blind_CERT_evaluated": True,
    "training_performed": False,
    "DEV_used": False,
    "original_holdout_used": False,
    "OOD_used": False,
    "TOF_used": False,
}

atomic_json(SUMMARY_PATH, summary)
SUMMARY_SHA = sha256(SUMMARY_PATH)

handoff = f"""# PAD-Stream V16E-1B2CUDA8L

## Role

Single frozen blind Stage-2 certification event for COMP008.

No training, optimizer steps, model selection, threshold tuning, DEV use,
original-holdout use, OOD, or TOF work occurred.

A technical runtime restart may resume this same event using the same exact
runner and already-frozen per-model metrics. It is not a second scientific
trial and cannot change the frozen contract.

## Models

- COMP004
- COMP005
- COMP007
- COMP008

All four were evaluated on the exact same 2,880-profile blind CERT set.

## COMP008 headline blind metrics

Source-native global RMSE:

`{metrics008["source_native"]["global"]["rmse"]:.12e}`

Source-native Nc=0 RMSE:

`{metrics008["source_native"]["Nc0"]["rmse"]:.12e}`

Source-native Nc>0 RMSE:

`{metrics008["source_native"]["Nc_positive"]["rmse"]:.12e}`

Corrected-residual global RMSE:

`{metrics008["corrected_residual"]["global"]["rmse"]:.12e}`

Corrected-residual Nc=0 RMSE:

`{metrics008["corrected_residual"]["Nc0"]["rmse"]:.12e}`

Corrected-residual Nc>0 RMSE:

`{metrics008["corrected_residual"]["Nc_positive"]["rmse"]:.12e}`

Tip RMSE:

`{metrics008["physical"]["tip_rmse"]:.12e}`

Monotonicity violation fraction:

`{metrics008["physical"]["mono_violation_fraction"]:.12e}`

Upper-bound max violation:

`{metrics008["physical"]["upper_bound_max_violation"]:.12e}`

Injector max endpoint error:

`{metrics008["physical"]["injector_max_abs"]:.12e}`

RH tip max endpoint error:

`{metrics008["physical"]["RH_tip_state_max_abs"]:.12e}`

## Final Stage-2 disposition

All frozen blind acceptance gates pass:

`{all_acceptance_pass}`

Stage 2 certified:

`{STAGE2_CERTIFIED}`

B3 authorized:

`{B3_AUTHORIZED}`

Disposition:

`{disposition}`

## Policy after blind certification

The blind CERT set may not be used for tuning.

No further current-cycle Stage-2 repair is authorized from these blind results.

## Hashes

Runner SHA-256:

`{RUNNER_SHA}`

Blind-open event SHA-256:

`{OPEN_EVENT_SHA}`

Results SHA-256:

`{RESULTS_SHA}`

Disposition SHA-256:

`{DISPOSITION_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`

## Next

{next_milestone}
"""

HANDOFF_PATH.write_text(handoff, encoding="utf-8")
HANDOFF_SHA = sha256(HANDOFF_PATH)

print()
print("=" * 110)
print("CUDA8L FINAL BLIND STAGE-2 CERTIFICATION RESULT")
print("=" * 110)

print()
print("COMP008 HEADLINE BLIND METRICS")
print("  Source global RMSE    :", f"{metrics008['source_native']['global']['rmse']:.12e}")
print("  Source Nc=0 RMSE      :", f"{metrics008['source_native']['Nc0']['rmse']:.12e}")
print("  Source Nc>0 RMSE      :", f"{metrics008['source_native']['Nc_positive']['rmse']:.12e}")
print("  Corrected global RMSE :", f"{metrics008['corrected_residual']['global']['rmse']:.12e}")
print("  Corrected Nc=0 RMSE   :", f"{metrics008['corrected_residual']['Nc0']['rmse']:.12e}")
print("  Corrected Nc>0 RMSE   :", f"{metrics008['corrected_residual']['Nc_positive']['rmse']:.12e}")
print("  Tip RMSE              :", f"{metrics008['physical']['tip_rmse']:.12e}")
print("  Mono violation frac   :", f"{metrics008['physical']['mono_violation_fraction']:.12e}")
print("  Upper bound max viol. :", f"{metrics008['physical']['upper_bound_max_violation']:.12e}")

print()
print("ALL ACCEPTANCE GATES PASS:", all_acceptance_pass)
print("STAGE 2 CERTIFIED:", STAGE2_CERTIFIED)
print("B3 AUTHORIZED:", B3_AUTHORIZED)
print("DISPOSITION:", disposition)
print("NEXT:", next_milestone)

print()
print("Runner SHA      :", RUNNER_SHA)
print("Open-event SHA  :", OPEN_EVENT_SHA)
print("Results SHA     :", RESULTS_SHA)
print("Disposition SHA :", DISPOSITION_SHA)
print("Summary SHA     :", SUMMARY_SHA)
print("Handoff SHA     :", HANDOFF_SHA)
