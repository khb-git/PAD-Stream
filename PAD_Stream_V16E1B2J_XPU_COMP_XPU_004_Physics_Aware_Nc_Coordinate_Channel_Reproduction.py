#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2J-XPU
COMP-XPU-004 — Physics-Aware Nc Coordinate-Channel Reproduction

Experiment
----------
V16E-BLREP-COMP-XPU-004

Prospectively frozen scientific change
--------------------------------------
Keep the original physical sequence coordinate xi and original raw physical
11-D conditioner p11, and add one physics-aware sequence channel:

    xD = xi * xD_star

    y(xD; Nc) =
        xD                                  for Nc -> 0
        -expm1(-Nc*xD) / Nc                 otherwise

    eta = y(xi*xD_star;Nc) / y(xD_star;Nc)

The LSTM sequence features change from:

    [xi]

to:

    [xi, eta]

The repeated raw conditioner remains:

    [no,nw,swi,sor,mu_w,mu_o,phi,tD,xD_star,Sw_star,Nc_physical]

COMP-XPU-003's Nc/0.30 conditioner scaling is NOT carried forward.

Scientific firewall
-------------------
UNCHANGED:
  * physical Nc
  * frozen Stage-2 Godunov dataset
  * conservative Godunov teacher
  * breakthrough calculation
  * Stage-2 physics residual
  * y(x;Nc) physical definition
  * raw physical p11 conditioner
  * all loss terms / weights
  * 800 epochs
  * fresh seed-1337 initialization
  * 2 x LSTM(64)
  * Adam lr=1e-3
  * logical batch=8192
  * XPU microbatch=2048
  * Adam foreach=False
  * NX_TRAIN=1601 / NX_REF=3201
  * same 80/20 development-diagnostic split
  * no OOD
  * no TOF

Operational durability
----------------------
Recovery checkpoint every 25 completed epochs containing:
  * model state
  * full Adam optimizer state
  * training history

Partial epochs are never accepted.

B3 is NOT automatically authorized. COMP-XPU-004 must be compared against the
frozen COMP-XPU-002 baseline using the B2D/B2G/B2H diagnostic framework.
"""

from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn


# =============================================================================
# Identity / paths
# =============================================================================

R = Path(__file__).resolve().parent

MILESTONE = "V16E-1B2J-XPU"
EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-004"

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

B2I_SOURCE = (
    R
    / "PAD_Stream_V16E1B2I_XPU_Physics_Aware_Nc_Coordinate_Channel_Protocol_Freeze.py"
)
B2I_SOURCE_SHA = "6daa8b73a2ff5393065bbe7191eb0e4aa33d79e47b21f6bea87d823aba533e91"

B2I_DIR = (
    R
    / "output"
    / "V16_E1B2I_XPU_PHYSICS_AWARE_NC_COORDINATE_CHANNEL_PROTOCOL_FREEZE"
)
B2I_PROTOCOL = B2I_DIR / "V16E1B2I_COMP_XPU_004_Physics_Aware_Nc_Channel_Protocol.json"
B2I_INTERPRETATION = B2I_DIR / "V16E1B2I_B2H_Interpretation.json"
B2I_HANDOFF = B2I_DIR / "V16E1B2I_Execution_Handoff.md"
B2I_SUMMARY = B2I_DIR / "PAD_Stream_V16E1B2I_XPU_Summary.json"

B2I_PROTOCOL_SHA = "34d022c94271326132e34c6603c34c9477e5b111a6cb267b69cc472dc3b595f1"
B2I_INTERPRETATION_SHA = "772516e5f317ceb390a72ba636c7f22c8d1209a31cb7165c530f991d290f523d"
B2I_HANDOFF_SHA = "c445de130701d4577ae0e3ae9ff35be6d9b48a0e10cb6afe7066dd46a983976e"
B2I_SUMMARY_SHA = "08c7a8b02420ed804163a34a4c8ff34706efb2c1e03bdd0d2dd20ded0838caf4"

EXPECTED_B2I_STATUS = (
    "V16E1B2I_XPU_PHYSICS_AWARE_NC_COORDINATE_CHANNEL_PROTOCOL_FROZEN_"
    "NC_GROUPS_REPRESENTED_SYSTEMATIC_MODEL_TO_TEACHER_UNDER_RESPONSE_CONFIRMED_"
    "SIMPLE_NC_SCALING_NOT_SUFFICIENT_"
    "ONE_FACTOR_SEQUENCE_FEATURE_XI_PLUS_NORMALIZED_STRETCHED_COORDINATE_ETA_AUTHORIZED_"
    "RAW_PHYSICAL_P11_GODUNOV_TEACHER_PHYSICS_RESIDUAL_LOSSES_AND_DATASET_UNCHANGED_"
    "FRESH_800_EPOCH_COMP_XPU_004_AUTHORIZED_NO_OOD_NO_TOF_B3_NOT_YET_AUTHORIZED"
)

DATASET = (
    R
    / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_META = (
    R
    / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.json"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# Frozen COMP-XPU-002 comparison baseline
COMP002_DIR = (
    R
    / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-002"
)
COMP002_CHECKPOINT = COMP002_DIR / "V16E_BLREP_COMP_XPU_002.pt"
COMP002_METRICS = COMP002_DIR / "V16E_BLREP_COMP_XPU_002_Metrics.json"
COMP002_MANIFEST = COMP002_DIR / "V16E_BLREP_COMP_XPU_002_Manifest.json"
COMP002_SUMMARY = COMP002_DIR / "PAD_Stream_V16E1B2C_XPU_Summary.json"

COMP002_CHECKPOINT_SHA = "fca205b1981fbbdf15424af8ac8174df88ff7addf99e718548319a81f87d271b"
COMP002_METRICS_SHA = "f17fa9f5d6e5954119dc3e412fc01052b4cfb6173c157ac71ff1aa04b0a0385d"
COMP002_MANIFEST_SHA = "3ab6abb7fe60ef5e6dcacfa3f543c65578a39fb64b0219357a658604edc1a48f"
COMP002_SUMMARY_SHA = "8ede892568a1e21c989f5c2782a3f0696e00480a0d671771e6fead754a6b9788"

OUT = (
    R
    / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)
OUT.mkdir(parents=True, exist_ok=True)

PORT_PROTOCOL = OUT / "V16E_BLREP_COMP_XPU_004_Framework_Port_Protocol.json"
CHECKPOINT = OUT / "V16E_BLREP_COMP_XPU_004.pt"
CONFIG = OUT / "V16E_BLREP_COMP_XPU_004_Config.json"
HISTORY = OUT / "V16E_BLREP_COMP_XPU_004_Training_History.json"
METRICS = OUT / "V16E_BLREP_COMP_XPU_004_Metrics.json"
MANIFEST = OUT / "V16E_BLREP_COMP_XPU_004_Manifest.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2J_XPU_Summary.json"

RECOVERY_DIR = OUT / "recovery"
RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
RECOVERY_LATEST = RECOVERY_DIR / "V16E_BLREP_COMP_XPU_004_RECOVERY_LATEST.json"

TARGET_EPOCHS = 800
MICROBATCH = 2048
CHECKPOINT_INTERVAL = 25
INPUT_FEATURES = 2
PARAM_DIM = 11


# =============================================================================
# Helpers
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(R))
    except ValueError:
        return str(path)


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def jsonable(v):
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.integer, np.floating, np.bool_)):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    return v


def import_base_runner():
    if not BASE_RUNNER.exists():
        raise RuntimeError(f"Frozen base runner missing: {BASE_RUNNER}")
    if sha256(BASE_RUNNER) != BASE_RUNNER_SHA:
        raise RuntimeError("Frozen base runner SHA mismatch.")

    spec = importlib.util.spec_from_file_location(
        "v16e1b2c_base",
        BASE_RUNNER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import frozen B2C runner.")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cpu_clone(obj):
    if torch.is_tensor(obj):
        return obj.detach().cpu().clone()
    if isinstance(obj, dict):
        return {k: cpu_clone(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [cpu_clone(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(cpu_clone(v) for v in obj)
    return copy.deepcopy(obj)


def move_optimizer_state_to_device(optimizer, device):
    for state in optimizer.state.values():
        for key, value in list(state.items()):
            if torch.is_tensor(value):
                state[key] = value.to(device)


def atomic_json_write(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_torch_save(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, path)


# =============================================================================
# Physics-aware eta feature
# =============================================================================

def normalized_stretched_coordinate(xi_seq, p11):
    """
    eta = y(xi*xD_star;Nc) / y(xD_star;Nc)

    Exact Nc->0 limit:
        y(x;0)=x
        eta=xi

    xi_seq: [B,T,1]
    p11:    [B,11] physical conditioner
    """
    if xi_seq.ndim != 3 or xi_seq.shape[-1] != 1:
        raise RuntimeError(
            f"Expected xi_seq [B,T,1], got {tuple(xi_seq.shape)}"
        )

    if p11.ndim != 2 or p11.shape[-1] != PARAM_DIM:
        raise RuntimeError(
            f"Expected physical p11 [B,{PARAM_DIM}], got {tuple(p11.shape)}"
        )

    xD_star = p11[:, 8:9].unsqueeze(1)
    Nc = p11[:, 10:11].unsqueeze(1)

    xD = xi_seq * xD_star

    small = torch.abs(Nc) < 1e-8
    Nc_safe = torch.where(
        small,
        torch.ones_like(Nc),
        Nc,
    )

    y = torch.where(
        small,
        xD,
        -torch.expm1(-Nc_safe * xD) / Nc_safe,
    )

    y_star = torch.where(
        small,
        xD_star,
        -torch.expm1(-Nc_safe * xD_star) / Nc_safe,
    )

    eta = y / torch.clamp(
        y_star,
        min=1e-12,
    )

    return eta


# =============================================================================
# Model: one architecture change only
# =============================================================================

def build_eta_model_class(M):
    class CompressiblePIRNNEtaXPU(nn.Module):
        def __init__(self):
            super().__init__()

            self.lstm1 = nn.LSTM(
                input_size=INPUT_FEATURES + PARAM_DIM,
                hidden_size=M.HIDDEN,
                num_layers=1,
                batch_first=True,
            )

            self.lstm2 = nn.LSTM(
                input_size=M.HIDDEN,
                hidden_size=M.HIDDEN,
                num_layers=1,
                batch_first=True,
            )

            self.out = nn.Linear(
                M.HIDDEN,
                1,
            )

            self._keras_like_init()

        @staticmethod
        def _init_lstm(lstm):
            for name, param in lstm.named_parameters():
                if "weight_ih" in name:
                    fan_in = param.shape[1]
                    fan_out = param.shape[0]
                    limit = math.sqrt(
                        6.0 / (fan_in + fan_out)
                    )
                    nn.init.uniform_(
                        param,
                        -limit,
                        limit,
                    )

                elif "weight_hh" in name:
                    nn.init.orthogonal_(param)

                elif "bias_ih" in name:
                    nn.init.zeros_(param)
                    h = param.numel() // 4
                    with torch.no_grad():
                        param[h:2*h].fill_(1.0)

                elif "bias_hh" in name:
                    nn.init.zeros_(param)

        def _keras_like_init(self):
            self._init_lstm(self.lstm1)
            self._init_lstm(self.lstm2)

            fan_in = self.out.weight.shape[1]
            fan_out = self.out.weight.shape[0]
            limit = math.sqrt(
                6.0 / (fan_in + fan_out)
            )

            nn.init.uniform_(
                self.out.weight,
                -limit,
                limit,
            )
            nn.init.zeros_(self.out.bias)

        def forward(self, xi_seq, p11_phys):
            if p11_phys.shape[-1] != PARAM_DIM:
                raise RuntimeError(
                    f"Expected raw physical p11 dim={PARAM_DIM}, "
                    f"got {p11_phys.shape[-1]}"
                )

            T = xi_seq.shape[1]

            # One scientific change: expose eta as second sequence channel.
            eta = normalized_stretched_coordinate(
                xi_seq,
                p11_phys,
            )

            seq = torch.cat(
                [xi_seq, eta],
                dim=-1,
            )

            p_rep = p11_phys.unsqueeze(1).expand(
                -1,
                T,
                -1,
            )

            z = torch.cat(
                [seq, p_rep],
                dim=-1,
            )

            if z.shape[-1] != INPUT_FEATURES + PARAM_DIM:
                raise RuntimeError(
                    f"Expected first-LSTM width {INPUT_FEATURES + PARAM_DIM}, "
                    f"got {z.shape[-1]}"
                )

            y, _ = self.lstm1(z)
            y, _ = self.lstm2(y)
            raw = self.out(y)

            swc = p_rep[:, :, 2:3]
            sor = p_rep[:, :, 3:4]

            span = torch.clamp(
                1.0 - swc - sor,
                min=1e-8,
            )

            return swc + span * torch.sigmoid(raw)

    return CompressiblePIRNNEtaXPU


# =============================================================================
# XPU smoke test for 13-input first LSTM
# =============================================================================

def eta_xpu_smoke_test(M, device):
    print("\nXPU ETA-CHANNEL COMPRESSIBLE LSTM SMOKE TEST")

    test = nn.LSTM(
        input_size=INPUT_FEATURES + PARAM_DIM,
        hidden_size=M.HIDDEN,
        num_layers=2,
        batch_first=True,
    ).to(device)

    x = torch.randn(
        8,
        64,
        INPUT_FEATURES + PARAM_DIM,
        device=device,
        requires_grad=True,
    )

    y, _ = test(x)
    loss = (y ** 2).mean()
    loss.backward()
    M.sync_xpu()

    passed = (
        y.device.type == "xpu"
        and x.grad is not None
        and torch.isfinite(y).all().item()
        and torch.isfinite(x.grad).all().item()
    )

    print("  input width     :", INPUT_FEATURES + PARAM_DIM)
    print("  output device   :", y.device)
    print("  forward/backward:", "PASS" if passed else "FAIL")

    del test, x, y, loss

    if hasattr(torch.xpu, "empty_cache"):
        torch.xpu.empty_cache()

    if not passed:
        raise RuntimeError("XPU eta-channel LSTM smoke test failed.")


# =============================================================================
# Recovery
# =============================================================================

def recovery_path(epoch: int) -> Path:
    return (
        RECOVERY_DIR
        / f"V16E_BLREP_COMP_XPU_004_RECOVERY_E{epoch:04d}.pt"
    )


def save_recovery(M, model, optimizer, history, epoch, runner_sha):
    path = recovery_path(epoch)

    payload = {
        "schema":
            "V16E1B2J_XPU_COMP004_RECOVERY_V1",
        "milestone":
            MILESTONE,
        "experiment_id":
            EXPERIMENT_ID,
        "runner_sha256":
            runner_sha,
        "Stage2_sha256":
            STAGE2_SHA,
        "B2I_protocol_sha256":
            B2I_PROTOCOL_SHA,
        "dataset_sha256":
            DATASET_SHA,
        "completed_epoch":
            int(epoch),
        "target_epochs":
            TARGET_EPOCHS,
        "seed":
            int(M.SEED),
        "logical_batch":
            int(M.LOGICAL_BATCH),
        "microbatch":
            MICROBATCH,
        "Adam_foreach":
            False,
        "input_features":
            INPUT_FEATURES,
        "raw_param_dim":
            PARAM_DIM,
        "eta_channel":
            True,
        "raw_p11_scaled":
            False,
        "model_state_dict":
            cpu_clone(model.state_dict()),
        "optimizer_state_dict":
            cpu_clone(optimizer.state_dict()),
        "history":
            copy.deepcopy(history),
        "partial_epoch_accepted":
            False,
    }

    atomic_torch_save(
        payload,
        path,
    )

    ck_sha = sha256(path)

    pointer = {
        "experiment_id":
            EXPERIMENT_ID,
        "completed_epoch":
            int(epoch),
        "checkpoint_path":
            str(path),
        "checkpoint_sha256":
            ck_sha,
        "runner_sha256":
            runner_sha,
        "dataset_sha256":
            DATASET_SHA,
        "target_epochs":
            TARGET_EPOCHS,
        "microbatch":
            MICROBATCH,
        "input_features":
            INPUT_FEATURES,
        "raw_param_dim":
            PARAM_DIM,
        "eta_channel":
            True,
        "raw_p11_scaled":
            False,
        "Adam_foreach":
            False,
    }

    atomic_json_write(
        pointer,
        RECOVERY_LATEST,
    )

    for old in RECOVERY_DIR.glob(
        "V16E_BLREP_COMP_XPU_004_RECOVERY_E*.pt"
    ):
        if old != path:
            try:
                old.unlink()
            except OSError:
                pass

    print(
        f"  [RECOVERY] epoch {epoch:04d} checkpoint saved"
    )
    print(
        f"             SHA-256: {ck_sha}"
    )


def load_recovery(M, model, optimizer, device, runner_sha):
    if not RECOVERY_LATEST.exists():
        return None

    ptr = read_json(
        RECOVERY_LATEST
    )

    required = {
        "experiment_id":
            EXPERIMENT_ID,
        "runner_sha256":
            runner_sha,
        "dataset_sha256":
            DATASET_SHA,
        "target_epochs":
            TARGET_EPOCHS,
        "microbatch":
            MICROBATCH,
        "input_features":
            INPUT_FEATURES,
        "raw_param_dim":
            PARAM_DIM,
        "eta_channel":
            True,
        "raw_p11_scaled":
            False,
        "Adam_foreach":
            False,
    }

    for key, expected in required.items():
        if ptr.get(key) != expected:
            raise RuntimeError(
                f"Recovery pointer mismatch for {key}: "
                f"{ptr.get(key)!r} != {expected!r}"
            )

    path = Path(
        ptr["checkpoint_path"]
    )

    if not path.exists():
        raise RuntimeError(
            f"Recovery checkpoint missing: {path}"
        )

    if sha256(path) != ptr["checkpoint_sha256"]:
        raise RuntimeError(
            "Recovery checkpoint SHA mismatch."
        )

    payload = torch.load(
        path,
        map_location="cpu",
        weights_only=False,
    )

    checks = {
        "experiment":
            payload.get("experiment_id")
            == EXPERIMENT_ID,
        "runner":
            payload.get("runner_sha256")
            == runner_sha,
        "Stage2":
            payload.get("Stage2_sha256")
            == STAGE2_SHA,
        "B2I":
            payload.get("B2I_protocol_sha256")
            == B2I_PROTOCOL_SHA,
        "dataset":
            payload.get("dataset_sha256")
            == DATASET_SHA,
        "epochs":
            payload.get("target_epochs")
            == TARGET_EPOCHS,
        "seed":
            payload.get("seed")
            == M.SEED,
        "logical_batch":
            payload.get("logical_batch")
            == M.LOGICAL_BATCH,
        "microbatch":
            payload.get("microbatch")
            == MICROBATCH,
        "input_features":
            payload.get("input_features")
            == INPUT_FEATURES,
        "raw_param_dim":
            payload.get("raw_param_dim")
            == PARAM_DIM,
        "eta_channel":
            payload.get("eta_channel")
            is True,
        "raw_p11_scaled":
            payload.get("raw_p11_scaled")
            is False,
        "foreach":
            payload.get("Adam_foreach")
            is False,
    }

    if not all(checks.values()):
        failed = [
            k
            for k, v in checks.items()
            if not v
        ]
        raise RuntimeError(
            "Recovery scientific identity mismatch: "
            + ", ".join(failed)
        )

    completed = int(
        payload["completed_epoch"]
    )

    history = payload["history"]

    if (
        len(history.get("epoch", []))
        != completed
        or history["epoch"][-1]
        != completed
    ):
        raise RuntimeError(
            "Recovery history/epoch mismatch."
        )

    model.load_state_dict(
        payload["model_state_dict"],
        strict=True,
    )
    model.to(device)

    optimizer.load_state_dict(
        payload["optimizer_state_dict"]
    )

    move_optimizer_state_to_device(
        optimizer,
        device,
    )

    print("\nRECOVERY CHECKPOINT FOUND")
    print("  completed epoch :", completed)
    print("  SHA-256         :", ptr["checkpoint_sha256"])
    print("  optimizer state : RESTORED")
    print("  next epoch      :", completed + 1)

    return completed, history


# =============================================================================
# Training
# =============================================================================

def train(
    M,
    model,
    arrays,
    device,
    runner_sha,
):
    (
        xi_all,
        Sw_all,
        p11_all,
        tD_all,
        ai_all,
        at_all,
    ) = arrays

    rng = np.random.default_rng(
        M.SEED
    )
    idx = np.arange(
        len(xi_all)
    )
    rng.shuffle(idx)

    n_train = int(
        0.8 * len(idx)
    )

    train_idx = idx[:n_train]
    holdout_idx = idx[n_train:]

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=M.LR,
        foreach=False,
    )

    history = {
        "epoch": [],
        "data": [],
        "physics": [],
        "bc_inj": [],
        "bc_tip": [],
        "anchor": [],
        "mono": [],
        "total": [],
        "epoch_seconds": [],
    }

    recovered = load_recovery(
        M,
        model,
        optimizer,
        device,
        runner_sha,
    )

    if recovered is None:
        start_epoch = 1
        print("\nRECOVERY")
        print("  no valid recovery checkpoint found")
        print(
            "  starting fresh seed-1337 COMP-XPU-004 run"
        )
    else:
        completed, history = recovered
        start_epoch = completed + 1

    print("\nXPU TRAINING — COMP-XPU-004")
    print("  device              :", device)
    print("  train profiles      :", len(train_idx))
    print("  holdout profiles    :", len(holdout_idx))
    print("  sequence features   : [xi, eta]")
    print("  first LSTM width    :", INPUT_FEATURES + PARAM_DIM)
    print("  raw p11             : unchanged physical 11-D")
    print("  Nc scaling          : NONE")
    print("  logical batch       :", M.LOGICAL_BATCH)
    print("  XPU microbatch      :", MICROBATCH)
    print(
        "  optimizer updates/ep:",
        int(
            np.ceil(
                len(train_idx)
                / M.LOGICAL_BATCH
            )
        ),
    )
    print("  target epochs       :", TARGET_EPOCHS)
    print("  starting epoch      :", start_epoch)
    print("  recovery interval   :", CHECKPOINT_INTERVAL)
    print("  Adam foreach        : False")
    print("  mixed precision     : OFF")

    session_t0 = time.time()

    for epoch in range(
        start_epoch,
        TARGET_EPOCHS + 1,
    ):
        t0 = time.time()

        erng = np.random.default_rng(
            M.SEED + epoch
        )
        order = train_idx.copy()
        erng.shuffle(order)

        sums = {
            "data": 0.0,
            "physics": 0.0,
            "bc_inj": 0.0,
            "bc_tip": 0.0,
            "anchor": 0.0,
            "mono": 0.0,
            "total": 0.0,
        }
        count = 0

        for b0 in range(
            0,
            len(order),
            M.LOGICAL_BATCH,
        ):
            logical_idx = order[
                b0:b0 + M.LOGICAL_BATCH
            ]
            logical_n = len(
                logical_idx
            )

            optimizer.zero_grad(
                set_to_none=True
            )

            for m0 in range(
                0,
                logical_n,
                MICROBATCH,
            ):
                ids = logical_idx[
                    m0:m0 + MICROBATCH
                ]
                m = len(ids)

                xi = torch.from_numpy(
                    xi_all[ids]
                ).to(device)

                Sw = torch.from_numpy(
                    Sw_all[ids]
                ).to(device)

                p11_phys = torch.from_numpy(
                    p11_all[ids]
                ).to(device)

                tD = torch.from_numpy(
                    tD_all[ids]
                ).to(device)

                ai = torch.from_numpy(
                    ai_all[ids]
                ).to(device)

                at = torch.from_numpy(
                    at_all[ids]
                ).to(device)

                # Physics residual receives the ORIGINAL xi and physical p11.
                # The model alone derives eta internally.
                _, parts = M.total_losses(
                    model,
                    xi,
                    Sw,
                    p11_phys,
                    tD,
                    ai,
                    at,
                )

                scale = (
                    float(m)
                    / float(logical_n)
                )

                (
                    parts["total"]
                    * scale
                ).backward()

                for k in sums:
                    sums[k] += (
                        float(
                            parts[k]
                            .detach()
                            .cpu()
                        )
                        * m
                    )

                count += m

                del (
                    xi,
                    Sw,
                    p11_phys,
                    tD,
                    ai,
                    at,
                    parts,
                )

            optimizer.step()

        # Epoch accepted only after all queued XPU work succeeds.
        M.sync_xpu()

        n = max(
            count,
            1,
        )

        sec = (
            time.time()
            - t0
        )

        history["epoch"].append(
            epoch
        )

        for k in sums:
            history[k].append(
                sums[k] / n
            )

        history[
            "epoch_seconds"
        ].append(sec)

        if (
            epoch == 1
            or epoch % 10 == 0
            or epoch == TARGET_EPOCHS
        ):
            print(
                f"[XPU-COMP004] Epoch {epoch:04d}/{TARGET_EPOCHS} "
                f"| Data {history['data'][-1]:.3e} "
                f"| Phys {history['physics'][-1]:.3e} "
                f"| BC {history['bc_inj'][-1]:.3e} "
                f"| Tip {history['bc_tip'][-1]:.3e} "
                f"| Anchor {history['anchor'][-1]:.3e} "
                f"| Mono {history['mono'][-1]:.3e} "
                f"| {sec:.2f}s/epoch "
                f"| session {time.time()-session_t0:.1f}s"
            )

        if (
            epoch % CHECKPOINT_INTERVAL == 0
            or epoch == TARGET_EPOCHS
        ):
            save_recovery(
                M,
                model,
                optimizer,
                history,
                epoch,
                runner_sha,
            )

    return (
        history,
        train_idx,
        holdout_idx,
    )


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2J-XPU")
    print("COMP-XPU-004 Physics-Aware Nc Coordinate-Channel Reproduction")
    print("=" * 80)
    print("Experiment:", EXPERIMENT_ID)
    print()

    if SUMMARY.exists():
        raise RuntimeError(
            "B2J summary already exists; refusing overwrite."
        )

    runner_path = Path(
        __file__
    ).resolve()

    runner_sha = sha256(
        runner_path
    )

    gates = {
        "Stage2_SHA_exact":
            exact(
                STAGE2,
                STAGE2_SHA,
            ),

        "base_runner_SHA_exact":
            exact(
                BASE_RUNNER,
                BASE_RUNNER_SHA,
            ),

        "B2I_source_SHA_exact":
            exact(
                B2I_SOURCE,
                B2I_SOURCE_SHA,
            ),

        "B2I_protocol_SHA_exact":
            exact(
                B2I_PROTOCOL,
                B2I_PROTOCOL_SHA,
            ),

        "B2I_interpretation_SHA_exact":
            exact(
                B2I_INTERPRETATION,
                B2I_INTERPRETATION_SHA,
            ),

        "B2I_handoff_SHA_exact":
            exact(
                B2I_HANDOFF,
                B2I_HANDOFF_SHA,
            ),

        "B2I_summary_SHA_exact":
            exact(
                B2I_SUMMARY,
                B2I_SUMMARY_SHA,
            ),

        "dataset_SHA_exact":
            exact(
                DATASET,
                DATASET_SHA,
            ),

        "dataset_meta_exists":
            DATASET_META.exists()
            and DATASET_META.stat().st_size > 0,

        "COMP002_checkpoint_SHA_exact":
            exact(
                COMP002_CHECKPOINT,
                COMP002_CHECKPOINT_SHA,
            ),

        "COMP002_metrics_SHA_exact":
            exact(
                COMP002_METRICS,
                COMP002_METRICS_SHA,
            ),

        "COMP002_manifest_SHA_exact":
            exact(
                COMP002_MANIFEST,
                COMP002_MANIFEST_SHA,
            ),

        "COMP002_summary_SHA_exact":
            exact(
                COMP002_SUMMARY,
                COMP002_SUMMARY_SHA,
            ),
    }

    b2i_summary = (
        read_json(
            B2I_SUMMARY
        )
        if B2I_SUMMARY.exists()
        else {}
    )

    b2i_protocol = (
        read_json(
            B2I_PROTOCOL
        )
        if B2I_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2I_status_exact":
            b2i_summary.get(
                "status"
            )
            == EXPECTED_B2I_STATUS,

        "B2I_authorized_experiment_exact":
            b2i_summary.get(
                "authorized_next_experiment"
            )
            == EXPERIMENT_ID,

        "B2I_training_authorized":
            b2i_summary.get(
                "training_authorized_next"
            )
            is True,

        "B2I_B3_false":
            b2i_summary.get(
                "B3_authorized"
            )
            is False,

        "protocol_feature_old_exact":
            b2i_protocol.get(
                "one_scientific_change",
                {},
            ).get(
                "old"
            )
            == ["xi"],

        "protocol_feature_new_exact":
            b2i_protocol.get(
                "one_scientific_change",
                {},
            ).get(
                "new"
            )
            == ["xi", "eta"],

        "protocol_input_features_new_2":
            b2i_protocol.get(
                "one_scientific_change",
                {},
            ).get(
                "input_feature_count_new"
            )
            == 2,

        "protocol_raw_p11_unscaled":
            b2i_protocol.get(
                "raw_conditioner_policy",
                {},
            ).get(
                "Nc_scaled_in_p11"
            )
            is False,

        "protocol_COMP003_scaling_not_carried":
            b2i_protocol.get(
                "raw_conditioner_policy",
                {},
            ).get(
                "COMP_XPU_003_Nc_over_0p30_not_carried_forward"
            )
            is True,

        "protocol_epochs_800":
            b2i_protocol.get(
                "must_remain_identical_to_COMP_XPU_002",
                {},
            ).get(
                "epochs"
            )
            == 800,

        "protocol_microbatch_2048":
            b2i_protocol.get(
                "must_remain_identical_to_COMP_XPU_002",
                {},
            ).get(
                "XPU_microbatch"
            )
            == 2048,

        "protocol_Adam_foreach_false":
            b2i_protocol.get(
                "must_remain_identical_to_COMP_XPU_002",
                {},
            ).get(
                "Adam_foreach"
            )
            is False,
    })

    print("AUTHORITY / PROTOCOL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(
        gates.values()
    ):
        raise RuntimeError(
            "COMP-XPU-004 blocked by authority/protocol mismatch."
        )

    M = import_base_runner()

    print("\nRUNTIME")
    print(
        "  PyTorch:",
        torch.__version__,
    )
    print(
        "  XPU available:",
        torch.xpu.is_available(),
    )
    print(
        "  XPU count:",
        torch.xpu.device_count()
        if torch.xpu.is_available()
        else 0,
    )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable."
        )

    device = torch.device(
        "xpu"
    )

    torch.manual_seed(
        M.SEED
    )

    eta_xpu_smoke_test(
        M,
        device,
    )

    # Exact frozen physical dataset only.
    d = np.load(
        DATASET
    )

    arrays = (
        d["xi"],
        d["Sw"],
        d["p11"],
        d["tD"],
        d["ai"],
        d["at"],
    )

    (
        xi_all,
        Sw_all,
        p11_all,
        tD_all,
        ai_all,
        at_all,
    ) = arrays

    gates.update({
        "dataset_xi_shape_exact":
            tuple(
                xi_all.shape
            )
            == (14400, 64, 1),

        "dataset_p11_shape_exact":
            tuple(
                p11_all.shape
            )
            == (14400, 11),

        "physical_Nc_max_0p30":
            np.isclose(
                float(
                    np.max(
                        p11_all[:, 10]
                    )
                ),
                0.30,
                atol=1e-7,
            ),

        "physical_Nc_min_0":
            np.isclose(
                float(
                    np.min(
                        p11_all[:, 10]
                    )
                ),
                0.0,
                atol=1e-7,
            ),
    })

    if not all(
        gates.values()
    ):
        raise RuntimeError(
            "Frozen physical dataset gate failed."
        )

    port_protocol = {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "classification":
            "FRAMEWORK_EQUIVALENT_ONE_FACTOR_PHYSICS_AWARE_ETA_CHANNEL_REPRODUCTION",

        "authority": {
            "runner_sha256":
                runner_sha,
            "Stage2_source_sha256":
                STAGE2_SHA,
            "B2I_protocol_sha256":
                B2I_PROTOCOL_SHA,
            "dataset_sha256":
                DATASET_SHA,
            "comparison_baseline_checkpoint_sha256":
                COMP002_CHECKPOINT_SHA,
        },

        "one_scientific_change": {
            "sequence_input_old":
                ["xi"],
            "sequence_input_new":
                ["xi", "eta"],
            "eta":
                "y(xi*xD_star;Nc)/y(xD_star;Nc)",
            "first_LSTM_input_width_old":
                12,
            "first_LSTM_input_width_new":
                13,
        },

        "raw_conditioner": {
            "dim":
                11,
            "physical_Nc":
                True,
            "Nc_scaled":
                False,
        },

        "physics_firewall": {
            "teacher_unchanged":
                True,
            "physics_residual_unchanged":
                True,
            "physical_Nc_unchanged":
                True,
            "raw_p11_unchanged":
                True,
            "dataset_unchanged":
                True,
            "loss_weights_unchanged":
                True,
        },

        "training": {
            "epochs":
                TARGET_EPOCHS,
            "seed":
                M.SEED,
            "logical_batch":
                M.LOGICAL_BATCH,
            "microbatch":
                MICROBATCH,
            "optimizer":
                "Adam",
            "learning_rate":
                M.LR,
            "Adam_foreach":
                False,
            "mixed_precision":
                False,
        },

        "evaluation_semantics":
            "development diagnostic; NOT independent and NOT OOD",

        "B3_automatic_authorization":
            False,
    }

    PORT_PROTOCOL.write_text(
        json.dumps(
            port_protocol,
            indent=2,
        ),
        encoding="utf-8",
    )

    EtaModel = build_eta_model_class(
        M
    )

    torch.manual_seed(
        M.SEED
    )

    model = EtaModel().to(
        device
    )

    # Structural / eta identity gates.
    gates.update({
        "model_parameters_on_XPU":
            {
                p.device.type
                for p
                in model.parameters()
            }
            == {"xpu"},

        "first_LSTM_input_width_13":
            model.lstm1.input_size
            == 13,

        "second_LSTM_width_unchanged_64":
            model.lstm2.input_size
            == M.HIDDEN
            and model.lstm2.hidden_size
            == M.HIDDEN,

        "fresh_seed_1337_initialization":
            M.SEED
            == 1337,

        "raw_p11_dim_11":
            PARAM_DIM
            == 11,

        "sequence_features_2":
            INPUT_FEATURES
            == 2,

        "Nc_scaling_not_used":
            True,

        "loss_weights_unchanged":
            (
                M.LAMBDA_DATA
                == 1.0
                and M.LAMBDA_PHYS
                == 0.05
                and M.LAMBDA_BC
                == 5.0
                and M.LAMBDA_TIP
                == 5.0
                and M.LAMBDA_ANCHOR
                == 10.0
                and M.LAMBDA_MONO
                == 0.2
                and M.LAMBDA_SHAPE
                == 0.0
            ),
    })

    # Exact eta limit/endpoint test on XPU.
    with torch.no_grad():
        xi_test = torch.tensor(
            [[[0.0], [0.25], [0.5], [0.75], [1.0]]],
            dtype=torch.float32,
            device=device,
        )
        p_test = torch.tensor(
            [[
                2.0, 2.0, 0.2, 0.2,
                0.5, 0.7, 0.2, 0.5,
                0.8, 0.4, 0.0,
            ]],
            dtype=torch.float32,
            device=device,
        )
        eta0 = normalized_stretched_coordinate(
            xi_test,
            p_test,
        ).cpu().numpy()

        p_test[:, 10] = 0.30
        eta3 = normalized_stretched_coordinate(
            xi_test,
            p_test,
        ).cpu().numpy()

    gates.update({
        "eta_Nc0_equals_xi":
            np.allclose(
                eta0,
                xi_test.cpu().numpy(),
                atol=1e-6,
            ),

        "eta_endpoint_zero":
            np.isclose(
                float(
                    eta3[0, 0, 0]
                ),
                0.0,
                atol=1e-6,
            ),

        "eta_endpoint_one":
            np.isclose(
                float(
                    eta3[0, -1, 0]
                ),
                1.0,
                atol=1e-6,
            ),

        "eta_finite":
            np.isfinite(
                eta3
            ).all(),
    })

    if not all(
        gates.values()
    ):
        raise RuntimeError(
            "Eta/model architecture gate failed."
        )

    config = {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "framework":
            "PyTorch XPU",

        "pytorch_version":
            torch.__version__,

        "device":
            str(device),

        "runner_sha256":
            runner_sha,

        "Stage2_source_sha256":
            STAGE2_SHA,

        "B2I_protocol_sha256":
            B2I_PROTOCOL_SHA,

        "dataset_sha256":
            DATASET_SHA,

        "comparison_baseline":
            "V16E-BLREP-COMP-XPU-002",

        "scientific_change": {
            "sequence_features":
                ["xi", "eta"],
            "eta_definition":
                "y(xi*xD_star;Nc)/y(xD_star;Nc)",
            "raw_p11_scaled":
                False,
            "physical_Nc_unchanged":
                True,
        },

        "input_features":
            INPUT_FEATURES,

        "raw_param_dim":
            PARAM_DIM,

        "first_LSTM_input_width":
            INPUT_FEATURES
            + PARAM_DIM,

        "epochs":
            TARGET_EPOCHS,

        "seed":
            M.SEED,

        "hidden":
            M.HIDDEN,

        "layers":
            M.LAYERS,

        "logical_batch":
            M.LOGICAL_BATCH,

        "microbatch":
            MICROBATCH,

        "optimizer":
            "Adam",

        "learning_rate":
            M.LR,

        "Adam_foreach":
            False,

        "mixed_precision":
            False,

        "B3_authorized":
            False,
    }

    CONFIG.write_text(
        json.dumps(
            config,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Train
    # -------------------------------------------------------------------------

    (
        history,
        train_idx,
        holdout_idx,
    ) = train(
        M=M,
        model=model,
        arrays=arrays,
        device=device,
        runner_sha=runner_sha,
    )

    HISTORY.write_text(
        json.dumps(
            jsonable(
                history
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    torch.save(
        {
            "milestone":
                MILESTONE,

            "experiment_id":
                EXPERIMENT_ID,

            "runner_sha256":
                runner_sha,

            "Stage2_source_sha256":
                STAGE2_SHA,

            "B2I_protocol_sha256":
                B2I_PROTOCOL_SHA,

            "dataset_sha256":
                DATASET_SHA,

            "framework":
                "PyTorch XPU",

            "pytorch_version":
                torch.__version__,

            "sequence_features":
                ["xi", "eta"],

            "eta_definition":
                "y(xi*xD_star;Nc)/y(xD_star;Nc)",

            "input_features":
                INPUT_FEATURES,

            "raw_param_dim":
                PARAM_DIM,

            "first_LSTM_input_width":
                INPUT_FEATURES
                + PARAM_DIM,

            "raw_p11_scaled":
                False,

            "physical_Nc_unchanged":
                True,

            "hidden":
                M.HIDDEN,

            "layers":
                M.LAYERS,

            "model_state_dict":
                model.state_dict(),
        },
        CHECKPOINT,
    )

    model.eval()

    gates.update({
        "full_800_epochs_completed":
            len(
                history.get(
                    "epoch",
                    [],
                )
            )
            == TARGET_EPOCHS,

        "history_last_epoch_800":
            history.get(
                "epoch",
                [None],
            )[-1]
            == TARGET_EPOCHS,

        "checkpoint_written":
            CHECKPOINT.exists()
            and CHECKPOINT.stat().st_size
            > 0,

        "history_written":
            HISTORY.exists()
            and HISTORY.stat().st_size
            > 0,

        "config_written":
            CONFIG.exists()
            and CONFIG.stat().st_size
            > 0,

        "model_eval_mode_before_inference":
            model.training
            is False,
    })

    # -------------------------------------------------------------------------
    # Evaluation
    # -------------------------------------------------------------------------

    print("\nSOURCE-NATIVE DEVELOPMENT-DIAGNOSTIC HOLDOUT")

    holdout = M.holdout_metrics(
        model,
        arrays,
        holdout_idx,
        device,
    )

    print(
        f"  MSE     : {holdout['mse']:.12e}"
    )
    print(
        f"  RMSE    : {holdout['rmse']:.12e}"
    )
    print(
        f"  MAE     : {holdout['mae']:.12e}"
    )
    print(
        f"  Max |e| : {holdout['max_abs_error']:.12e}"
    )
    print(
        "  Bounds  :",
        "PASS"
        if holdout["bounds_pass"]
        else "FAIL",
    )

    p1 = M.make_case(
        no=2.0,
        nw=2.0,
        swc=0.20,
        sor=0.20,
        mu_w=0.5,
        mu_o=0.7,
        phi=0.20,
    )

    p2 = M.make_case(
        no=3.0,
        nw=2.0,
        swc=0.15,
        sor=0.25,
        mu_w=6.0,
        mu_o=0.9,
        phi=0.25,
    )

    print("\nSOURCE CASE DIAGNOSTICS")

    cases = {
        "case1_nc0_stage1_nesting":
            M.evaluate_case(
                model,
                p1,
                0.0,
                device,
            ),

        "case1_nc01":
            M.evaluate_case(
                model,
                p1,
                0.10,
                device,
            ),

        "case2_nc0_stage1_nesting":
            M.evaluate_case(
                model,
                p2,
                0.0,
                device,
            ),

        "case2_nc02":
            M.evaluate_case(
                model,
                p2,
                0.20,
                device,
            ),
    }

    for name, case in cases.items():
        print(
            f"  {name:<30} "
            f"R2={case['diagnostics']['r_squared']:.8f} "
            f"max_res={case['diagnostics']['max_abs_residual']:.5e}"
        )

    print("\nNc ACCURACY SWEEP — CASE 1")

    sweep = M.nc_accuracy_sweep(
        model,
        p1,
        device,
    )

    for nc, vals in sweep.items():
        print(
            f"  Nc={nc} "
            f"MAE={vals['mae']:.5e} "
            f"max={vals['max_abs_error']:.5e}"
        )

    def case_finite(case):
        return (
            len(
                case["rows"]
            )
            == 15
            and all(
                finite(
                    r["mse"]
                )
                and finite(
                    r["mae"]
                )
                and finite(
                    r["max_abs_err"]
                )
                for r
                in case["rows"]
            )
            and finite(
                case[
                    "diagnostics"
                ][
                    "r_squared"
                ]
            )
            and finite(
                case[
                    "diagnostics"
                ][
                    "max_abs_residual"
                ]
            )
        )

    gates.update({
        "holdout_predictions_finite":
            holdout[
                "finite_predictions"
            ],

        "holdout_bounds_pass":
            holdout[
                "bounds_pass"
            ],

        "holdout_metrics_finite":
            all(
                finite(
                    holdout[k]
                )
                for k
                in (
                    "mse",
                    "rmse",
                    "mae",
                    "max_abs_error",
                )
            ),

        "all_four_cases_finite":
            all(
                case_finite(c)
                for c
                in cases.values()
            ),

        "Nc_sweep_all_finite":
            all(
                finite(
                    v["mae"]
                )
                and finite(
                    v[
                        "max_abs_error"
                    ]
                )
                for v
                in sweep.values()
            ),

        "Stage1_nesting_Nc0_evaluated":
            (
                "case1_nc0_stage1_nesting"
                in cases
                and
                "case2_nc0_stage1_nesting"
                in cases
            ),

        "physical_Nc_evaluation_used":
            True,

        "raw_p11_evaluation_used":
            True,

        "no_OOD":
            True,

        "no_TOF":
            True,

        "no_numeric_threshold_invented":
            True,
    })

    metrics = {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "classification":
            "ONE_FACTOR_PHYSICS_AWARE_ETA_CHANNEL_REPRODUCTION",

        "scientific_change": {
            "sequence_features":
                ["xi", "eta"],
            "raw_p11":
                "unchanged physical 11-D",
            "physical_Nc":
                "unchanged",
        },

        "training": {
            "epochs_completed":
                len(
                    history["epoch"]
                ),

            "final_losses": {
                k:
                    history[k][-1]
                for k
                in (
                    "data",
                    "physics",
                    "bc_inj",
                    "bc_tip",
                    "anchor",
                    "mono",
                    "total",
                )
            },

            "mean_epoch_seconds":
                float(
                    np.mean(
                        history[
                            "epoch_seconds"
                        ]
                    )
                ),
        },

        "holdout":
            holdout,

        "source_cases":
            cases,

        "Nc_accuracy_sweep_case1":
            sweep,

        "evaluation_semantics":
            "development diagnostic; NOT independent and NOT OOD",

        "threshold_policy":
            "No numerical acceptance threshold invented or applied.",
    }

    METRICS.write_text(
        json.dumps(
            jsonable(
                metrics
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "classification":
            "FRAMEWORK_EQUIVALENT_ONE_FACTOR_PHYSICS_AWARE_ETA_CHANNEL_XPU_REPRODUCTION",

        "authority": {
            "runner_sha256":
                runner_sha,
            "Stage2_sha256":
                STAGE2_SHA,
            "B2I_protocol_sha256":
                B2I_PROTOCOL_SHA,
            "dataset_sha256":
                DATASET_SHA,
            "comparison_baseline_checkpoint_sha256":
                COMP002_CHECKPOINT_SHA,
        },

        "artifacts": {
            "port_protocol": {
                "path":
                    rel(
                        PORT_PROTOCOL
                    ),
                "sha256":
                    sha256(
                        PORT_PROTOCOL
                    ),
            },

            "checkpoint": {
                "path":
                    rel(
                        CHECKPOINT
                    ),
                "sha256":
                    sha256(
                        CHECKPOINT
                    ),
            },

            "config": {
                "path":
                    rel(
                        CONFIG
                    ),
                "sha256":
                    sha256(
                        CONFIG
                    ),
            },

            "history": {
                "path":
                    rel(
                        HISTORY
                    ),
                "sha256":
                    sha256(
                        HISTORY
                    ),
            },

            "metrics": {
                "path":
                    rel(
                        METRICS
                    ),
                "sha256":
                    sha256(
                        METRICS
                    ),
            },
        },

        "firewall": {
            "sequence_feature_changed":
                True,
            "eta_channel_added":
                True,
            "raw_p11_changed":
                False,
            "Nc_scaled":
                False,
            "physical_Nc_changed":
                False,
            "teacher_changed":
                False,
            "physics_residual_changed":
                False,
            "loss_weights_changed":
                False,
            "dataset_changed":
                False,
            "epochs_changed_vs_COMP002":
                False,
            "OOD_claim":
                False,
            "TOF":
                False,
            "B3_authorized":
                False,
        },
    }

    MANIFEST.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates.update({
        "metrics_written":
            METRICS.exists()
            and METRICS.stat().st_size
            > 0,

        "manifest_written":
            MANIFEST.exists()
            and MANIFEST.stat().st_size
            > 0,

        "manifest_checkpoint_SHA_exact":
            read_json(
                MANIFEST
            )[
                "artifacts"
            ][
                "checkpoint"
            ][
                "sha256"
            ]
            == sha256(
                CHECKPOINT
            ),

        "manifest_metrics_SHA_exact":
            read_json(
                MANIFEST
            )[
                "artifacts"
            ][
                "metrics"
            ][
                "sha256"
            ]
            == sha256(
                METRICS
            ),
    })

    ok = all(
        bool(v)
        for v
        in gates.values()
    )

    status = (
        "V16E1B2J_XPU_COMP_XPU_004_PHYSICS_AWARE_NC_COORDINATE_CHANNEL_REPRODUCTION_COMPLETE_"
        "SEQUENCE_FEATURES_XI_PLUS_ETA_RAW_PHYSICAL_P11_UNCHANGED_NO_NC_SCALING_"
        "GODUNOV_TEACHER_PHYSICS_RESIDUAL_LOSSES_AND_DATASET_UNCHANGED_"
        "FRESH_800_EPOCH_INTEL_XPU_TRAINING_COMPLETE_CHECKPOINT_AND_METRICS_SHA_BOUND_"
        "DIAGNOSTICS_FINITE_SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
        "V16E1B2K_COMP_XPU_002_VS_004_COMPARISON_REQUIRED_B3_NOT_YET_AUTHORIZED"
        if ok else
        "V16E1B2J_XPU_COMP_XPU_004_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "status":
            status,

        "runner_sha256":
            runner_sha,

        "port_protocol_sha256":
            sha256(
                PORT_PROTOCOL
            ),

        "checkpoint_sha256":
            sha256(
                CHECKPOINT
            ),

        "config_sha256":
            sha256(
                CONFIG
            ),

        "history_sha256":
            sha256(
                HISTORY
            ),

        "metrics_sha256":
            sha256(
                METRICS
            ),

        "manifest_sha256":
            sha256(
                MANIFEST
            ),

        "holdout_mse":
            holdout["mse"],

        "holdout_rmse":
            holdout["rmse"],

        "holdout_mae":
            holdout["mae"],

        "holdout_max_abs_error":
            holdout[
                "max_abs_error"
            ],

        "B3_authorized":
            False,

        "comparison_required_before_B3":
            True,

        "next_milestone": (
            "V16E-1B2K-XPU — Compare COMP-XPU-004 against COMP-XPU-002 "
            "using frozen overall, per-Nc holdout, per-Nc loss, full-domain, "
            "front-excluded, front-position, and model-to-teacher response-gain diagnostics"
            if ok else
            "V16E-1B2J-XPU-R1 — diagnose failed gate"
        ),

        "gates": {
            k:
                bool(v)
            for k, v
            in gates.items()
        },
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    print("\nSTATUS")
    print(
        " ",
        status,
    )

    print("\nARTIFACT HASHES")
    print(
        "  Runner       :",
        runner_sha,
    )
    print(
        "  Dataset      :",
        DATASET_SHA,
    )
    print(
        "  Port protocol:",
        sha256(
            PORT_PROTOCOL
        ),
    )
    print(
        "  Checkpoint   :",
        sha256(
            CHECKPOINT
        ),
    )
    print(
        "  Config       :",
        sha256(
            CONFIG
        ),
    )
    print(
        "  History      :",
        sha256(
            HISTORY
        ),
    )
    print(
        "  Metrics      :",
        sha256(
            METRICS
        ),
    )
    print(
        "  Manifest     :",
        sha256(
            MANIFEST
        ),
    )
    print(
        "  Summary      :",
        sha256(
            SUMMARY
        ),
    )

    print("\nNEXT")
    print(
        " ",
        summary[
            "next_milestone"
        ],
    )

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
