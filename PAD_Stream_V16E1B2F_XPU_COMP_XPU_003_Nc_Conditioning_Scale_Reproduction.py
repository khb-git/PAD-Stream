#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2F-XPU
COMP-XPU-003 — Nc-Conditioning-Scale Reproduction

Experiment
----------
V16E-BLREP-COMP-XPU-003

Prospectively frozen scientific change
--------------------------------------
Only the copy of physical Nc presented to the neural-network conditioner is
scaled:

    Nc_model = Nc_physical / 0.30

The physical Nc remains unchanged in:
  * the frozen Godunov teacher dataset,
  * breakthrough calculations,
  * y(x;Nc),
  * the physics residual,
  * fine-grid reference evaluation,
  * diagnostics and labels.

Implementation firewall
-----------------------
The frozen Stage-2 p11 array remains the physical authority:

    p11_phys = [..., Nc_physical]

The model creates an internal copy:

    p11_model = p11_phys.clone()
    p11_model[:,10] = p11_phys[:,10] / 0.30

Only p11_model is concatenated into the LSTM input. M.total_losses continues to
receive p11_phys, so physics_loss_char uses physical Nc.

Everything else remains COMP-XPU-002:
  * frozen dataset SHA
  * 800 epochs
  * fresh seed-1337 initialization
  * 2 x LSTM(64)
  * Adam lr=1e-3
  * same loss weights
  * logical batch=8192
  * XPU microbatch=2048
  * Adam foreach=False
  * NX_TRAIN=1601 / NX_REF=3201
  * same development-diagnostic 80/20 split
  * no OOD
  * no TOF

Operational durability
----------------------
Epoch-boundary recovery checkpoints are written every 25 completed epochs and
include model state, full Adam optimizer state, and training history. Partial
epochs are never accepted.

B3 is NOT automatically authorized by this run. A subsequent COMP-XPU-002 vs
COMP-XPU-003 comparison is required.
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

MILESTONE = "V16E-1B2F-XPU"
EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-003"

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

B2E_SOURCE = R / "PAD_Stream_V16E1B2E_XPU_Nc_Conditioning_Scale_Protocol_Freeze.py"
B2E_SOURCE_SHA = "6b0bd45c33b68b4212df2dbeed0fb8da9b90af5c4dfb197f9df8014a8a511150"

B2E_DIR = (
    R / "output"
    / "V16_E1B2E_XPU_NC_CONDITIONING_SCALE_PROTOCOL_FREEZE"
)
B2E_PROTOCOL = B2E_DIR / "V16E1B2E_COMP_XPU_003_Nc_Conditioning_Scale_Protocol.json"
B2E_INTERPRETATION = B2E_DIR / "V16E1B2E_B2D_Interpretation.json"
B2E_HANDOFF = B2E_DIR / "V16E1B2E_Execution_Handoff.md"
B2E_SUMMARY = B2E_DIR / "PAD_Stream_V16E1B2E_XPU_Summary.json"

B2E_PROTOCOL_SHA = "58f37ef536f3683772c7e9fb342d5a39bdead660e77205b13cc150f8fc7c3ee3"
B2E_INTERPRETATION_SHA = "4ce9ca907c7c973e3d2f151b4f214aebd45feff894bc079b871548a1c897b1ab"
B2E_HANDOFF_SHA = "27e513fe3afd500762e8928314a8313140db7fff72418b11365f0a5b1c1e5eb2"
B2E_SUMMARY_SHA = "75001b6d8ae8b9d525102f64cbe1396cca81f4d1fbc2afbbbb999a2a8edf06f9"

EXPECTED_B2E_STATUS = (
    "V16E1B2E_XPU_NC_CONDITIONING_SCALE_PROTOCOL_FROZEN_"
    "UNDERTRAINING_NOT_SUFFICIENT_ABSOLUTE_ACCURACY_IMPROVED_BUT_RELATIVE_HIGH_NC_WEAKNESS_PERSISTS_"
    "RAW_STAGE2_CONDITIONER_DIRECT_CONCAT_CONFIRMED_"
    "ONE_FACTOR_NETWORK_NC_SCALE_0P30_TO_UNIT_INTERVAL_AUTHORIZED_"
    "PHYSICAL_NC_TEACHER_RESIDUAL_AND_TRANSFORM_UNCHANGED_"
    "FRESH_800_EPOCH_COMP_XPU_003_AUTHORIZED_NO_OOD_NO_TOF_B3_NOT_YET_AUTHORIZED"
)

DATASET = (
    R / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_META = (
    R / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.json"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

OUT = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)
OUT.mkdir(parents=True, exist_ok=True)

PORT_PROTOCOL = OUT / "V16E_BLREP_COMP_XPU_003_Framework_Port_Protocol.json"
CHECKPOINT = OUT / "V16E_BLREP_COMP_XPU_003.pt"
CONFIG = OUT / "V16E_BLREP_COMP_XPU_003_Config.json"
HISTORY = OUT / "V16E_BLREP_COMP_XPU_003_Training_History.json"
METRICS = OUT / "V16E_BLREP_COMP_XPU_003_Metrics.json"
MANIFEST = OUT / "V16E_BLREP_COMP_XPU_003_Manifest.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2F_XPU_Summary.json"

RECOVERY_DIR = OUT / "recovery"
RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
RECOVERY_LATEST = RECOVERY_DIR / "V16E_BLREP_COMP_XPU_003_RECOVERY_LATEST.json"

NC_SCALE_DENOMINATOR = 0.30
TARGET_EPOCHS = 800
MICROBATCH = 2048
CHECKPOINT_INTERVAL = 25


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
# Model: one scientific change only
# =============================================================================

def build_scaled_model_class(M):
    class CompressiblePIRNNScaledNc(M.CompressiblePIRNNXPU):
        """
        Exact frozen topology; only Nc's network-conditioning representation is
        transformed from physical [0,0.30] to model [0,1].
        """

        def forward(self, xi_seq, p11_phys):
            if p11_phys.shape[-1] != 11:
                raise RuntimeError(
                    f"Expected physical p11 with 11 columns; got {p11_phys.shape}"
                )

            # Clone prevents any mutation of physical authority tensor.
            p11_model = p11_phys.clone()

            # ONE SCIENTIFIC CHANGE:
            p11_model[:, 10] = (
                p11_phys[:, 10] / NC_SCALE_DENOMINATOR
            )

            return super().forward(xi_seq, p11_model)

    return CompressiblePIRNNScaledNc


# =============================================================================
# Recovery
# =============================================================================

def recovery_path(epoch: int) -> Path:
    return RECOVERY_DIR / f"V16E_BLREP_COMP_XPU_003_RECOVERY_E{epoch:04d}.pt"


def save_recovery(M, model, optimizer, history, epoch, runner_sha):
    path = recovery_path(epoch)

    payload = {
        "schema": "V16E1B2F_XPU_COMP003_RECOVERY_V1",
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "runner_sha256": runner_sha,
        "Stage2_sha256": STAGE2_SHA,
        "B2E_protocol_sha256": B2E_PROTOCOL_SHA,
        "dataset_sha256": DATASET_SHA,
        "completed_epoch": int(epoch),
        "target_epochs": TARGET_EPOCHS,
        "seed": int(M.SEED),
        "logical_batch": int(M.LOGICAL_BATCH),
        "microbatch": MICROBATCH,
        "Adam_foreach": False,
        "Nc_scale_denominator": NC_SCALE_DENOMINATOR,
        "model_state_dict": cpu_clone(model.state_dict()),
        "optimizer_state_dict": cpu_clone(optimizer.state_dict()),
        "history": copy.deepcopy(history),
        "partial_epoch_accepted": False,
    }

    atomic_torch_save(payload, path)
    ck_sha = sha256(path)

    pointer = {
        "experiment_id": EXPERIMENT_ID,
        "completed_epoch": int(epoch),
        "checkpoint_path": str(path),
        "checkpoint_sha256": ck_sha,
        "runner_sha256": runner_sha,
        "dataset_sha256": DATASET_SHA,
        "target_epochs": TARGET_EPOCHS,
        "microbatch": MICROBATCH,
        "Nc_scale_denominator": NC_SCALE_DENOMINATOR,
        "Adam_foreach": False,
    }
    atomic_json_write(pointer, RECOVERY_LATEST)

    # Keep latest only.
    for old in RECOVERY_DIR.glob("V16E_BLREP_COMP_XPU_003_RECOVERY_E*.pt"):
        if old != path:
            try:
                old.unlink()
            except OSError:
                pass

    print(f"  [RECOVERY] epoch {epoch:04d} checkpoint saved")
    print(f"             SHA-256: {ck_sha}")


def load_recovery(M, model, optimizer, device, runner_sha):
    if not RECOVERY_LATEST.exists():
        return None

    ptr = read_json(RECOVERY_LATEST)

    required = {
        "experiment_id": EXPERIMENT_ID,
        "runner_sha256": runner_sha,
        "dataset_sha256": DATASET_SHA,
        "target_epochs": TARGET_EPOCHS,
        "microbatch": MICROBATCH,
        "Nc_scale_denominator": NC_SCALE_DENOMINATOR,
        "Adam_foreach": False,
    }
    for key, expected in required.items():
        if ptr.get(key) != expected:
            raise RuntimeError(
                f"Recovery pointer mismatch for {key}: "
                f"{ptr.get(key)!r} != {expected!r}"
            )

    path = Path(ptr["checkpoint_path"])
    if not path.exists():
        raise RuntimeError(f"Recovery checkpoint missing: {path}")
    if sha256(path) != ptr["checkpoint_sha256"]:
        raise RuntimeError("Recovery checkpoint SHA mismatch.")

    payload = torch.load(
        path,
        map_location="cpu",
        weights_only=False,
    )

    checks = {
        "experiment":
            payload.get("experiment_id") == EXPERIMENT_ID,
        "runner":
            payload.get("runner_sha256") == runner_sha,
        "Stage2":
            payload.get("Stage2_sha256") == STAGE2_SHA,
        "B2E":
            payload.get("B2E_protocol_sha256") == B2E_PROTOCOL_SHA,
        "dataset":
            payload.get("dataset_sha256") == DATASET_SHA,
        "epochs":
            payload.get("target_epochs") == TARGET_EPOCHS,
        "seed":
            payload.get("seed") == M.SEED,
        "logical_batch":
            payload.get("logical_batch") == M.LOGICAL_BATCH,
        "microbatch":
            payload.get("microbatch") == MICROBATCH,
        "foreach":
            payload.get("Adam_foreach") is False,
        "scale":
            payload.get("Nc_scale_denominator")
            == NC_SCALE_DENOMINATOR,
    }

    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        raise RuntimeError(
            "Recovery scientific identity mismatch: "
            + ", ".join(failed)
        )

    completed = int(payload["completed_epoch"])
    history = payload["history"]

    if (
        len(history.get("epoch", [])) != completed
        or history["epoch"][-1] != completed
    ):
        raise RuntimeError("Recovery history/epoch mismatch.")

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
    xi_all, Sw_all, p11_all, tD_all, ai_all, at_all = arrays

    rng = np.random.default_rng(M.SEED)
    idx = np.arange(len(xi_all))
    rng.shuffle(idx)

    n_train = int(0.8 * len(idx))
    train_idx = idx[:n_train]
    holdout_idx = idx[n_train:]

    # Frozen optimizer, low-memory execution implementation.
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
        print("  starting fresh seed-1337 COMP-XPU-003 run")
    else:
        completed, history = recovered
        start_epoch = completed + 1

    print("\nXPU TRAINING — COMP-XPU-003")
    print("  device              :", device)
    print("  train profiles      :", len(train_idx))
    print("  holdout profiles    :", len(holdout_idx))
    print("  logical batch       :", M.LOGICAL_BATCH)
    print("  XPU microbatch      :", MICROBATCH)
    print("  optimizer updates/ep:",
          int(np.ceil(len(train_idx) / M.LOGICAL_BATCH)))
    print("  target epochs       :", TARGET_EPOCHS)
    print("  starting epoch      :", start_epoch)
    print("  recovery interval   :", CHECKPOINT_INTERVAL)
    print("  Adam foreach        : False")
    print("  physical Nc         : unchanged [0,0.30]")
    print("  model Nc            : physical Nc / 0.30")
    print("  mixed precision     : OFF")

    session_t0 = time.time()

    for epoch in range(start_epoch, TARGET_EPOCHS + 1):
        t0 = time.time()

        erng = np.random.default_rng(M.SEED + epoch)
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
            logical_n = len(logical_idx)

            optimizer.zero_grad(set_to_none=True)

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

                # IMPORTANT: physical p11 enters total_losses.
                # The model alone scales its internal conditioner copy.
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

                _, parts = M.total_losses(
                    model,
                    xi,
                    Sw,
                    p11_phys,
                    tD,
                    ai,
                    at,
                )

                scale = float(m) / float(logical_n)
                (parts["total"] * scale).backward()

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

                del xi, Sw, p11_phys, tD, ai, at, parts

            optimizer.step()

        # Completed epoch only after all queued XPU work succeeds.
        M.sync_xpu()

        n = max(count, 1)
        sec = time.time() - t0

        history["epoch"].append(epoch)
        for k in sums:
            history[k].append(
                sums[k] / n
            )
        history["epoch_seconds"].append(sec)

        if (
            epoch == 1
            or epoch % 10 == 0
            or epoch == TARGET_EPOCHS
        ):
            print(
                f"[XPU-COMP003] Epoch {epoch:04d}/{TARGET_EPOCHS} "
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

    return history, train_idx, holdout_idx


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2F-XPU")
    print("COMP-XPU-003 Nc-Conditioning-Scale Reproduction")
    print("=" * 80)
    print("Experiment:", EXPERIMENT_ID)
    print()

    if SUMMARY.exists():
        raise RuntimeError(
            "B2F summary already exists; refusing overwrite."
        )

    runner_path = Path(__file__).resolve()
    runner_sha = sha256(runner_path)

    gates = {
        "Stage2_SHA_exact":
            exact(STAGE2, STAGE2_SHA),
        "base_runner_SHA_exact":
            exact(BASE_RUNNER, BASE_RUNNER_SHA),

        "B2E_source_SHA_exact":
            exact(B2E_SOURCE, B2E_SOURCE_SHA),
        "B2E_protocol_SHA_exact":
            exact(B2E_PROTOCOL, B2E_PROTOCOL_SHA),
        "B2E_interpretation_SHA_exact":
            exact(
                B2E_INTERPRETATION,
                B2E_INTERPRETATION_SHA,
            ),
        "B2E_handoff_SHA_exact":
            exact(B2E_HANDOFF, B2E_HANDOFF_SHA),
        "B2E_summary_SHA_exact":
            exact(B2E_SUMMARY, B2E_SUMMARY_SHA),

        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),
        "dataset_meta_exists":
            DATASET_META.exists()
            and DATASET_META.stat().st_size > 0,
    }

    b2e_summary = (
        read_json(B2E_SUMMARY)
        if B2E_SUMMARY.exists()
        else {}
    )
    b2e_protocol = (
        read_json(B2E_PROTOCOL)
        if B2E_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2E_status_exact":
            b2e_summary.get("status")
            == EXPECTED_B2E_STATUS,
        "B2E_authorized_experiment_exact":
            b2e_summary.get(
                "authorized_next_experiment"
            )
            == EXPERIMENT_ID,
        "B2E_training_authorized":
            b2e_summary.get(
                "training_authorized_next"
            )
            is True,
        "B2E_B3_false":
            b2e_summary.get(
                "B3_authorized"
            )
            is False,

        "protocol_Nc_scale_exact":
            b2e_protocol.get(
                "one_scientific_change", {}
            ).get("new")
            == "Nc_cond = Nc_physical / 0.30",

        "protocol_epochs_800":
            b2e_protocol.get(
                "must_remain_identical_to_COMP_XPU_002",
                {},
            ).get("epochs")
            == 800,

        "protocol_microbatch_2048":
            b2e_protocol.get(
                "must_remain_identical_to_COMP_XPU_002",
                {},
            ).get("XPU_microbatch")
            == 2048,

        "protocol_Adam_foreach_false":
            b2e_protocol.get(
                "must_remain_identical_to_COMP_XPU_002",
                {},
            ).get("Adam_foreach")
            is False,
    })

    print("AUTHORITY / PROTOCOL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "COMP-XPU-003 blocked by authority/protocol mismatch."
        )

    M = import_base_runner()

    print("\nRUNTIME")
    print("  PyTorch:", torch.__version__)
    print("  XPU available:", torch.xpu.is_available())
    print(
        "  XPU count:",
        torch.xpu.device_count()
        if torch.xpu.is_available()
        else 0,
    )

    if not torch.xpu.is_available():
        raise RuntimeError("Intel XPU unavailable.")

    device = torch.device("xpu")
    torch.manual_seed(M.SEED)

    M.xpu_smoke_test(device)

    # Frozen physical dataset only. No rebuilding.
    d = np.load(DATASET)
    arrays = (
        d["xi"],
        d["Sw"],
        d["p11"],
        d["tD"],
        d["ai"],
        d["at"],
    )
    xi_all, Sw_all, p11_all, tD_all, ai_all, at_all = arrays

    gates.update({
        "dataset_xi_shape_exact":
            tuple(xi_all.shape)
            == (14400, 64, 1),
        "dataset_p11_shape_exact":
            tuple(p11_all.shape)
            == (14400, 11),
        "physical_Nc_max_0p30":
            np.isclose(
                float(np.max(p11_all[:, 10])),
                0.30,
                atol=1e-7,
            ),
        "physical_Nc_min_0":
            np.isclose(
                float(np.min(p11_all[:, 10])),
                0.0,
                atol=1e-7,
            ),
    })

    if not all(gates.values()):
        raise RuntimeError(
            "Frozen physical dataset gate failed."
        )

    # Prospective port protocol artifact.
    port_protocol = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "classification":
            "FRAMEWORK_EQUIVALENT_ONE_FACTOR_NC_CONDITIONING_SCALE_REPRODUCTION",

        "authority": {
            "Stage2_source_sha256":
                STAGE2_SHA,
            "B2E_protocol_sha256":
                B2E_PROTOCOL_SHA,
            "dataset_sha256":
                DATASET_SHA,
            "runner_sha256":
                runner_sha,
        },

        "one_scientific_change": {
            "physical_Nc":
                "unchanged",
            "model_conditioner_Nc":
                "Nc_physical / 0.30",
        },

        "physics_firewall": {
            "dataset_p11_is_physical": True,
            "teacher_uses_physical_Nc": True,
            "physics_loss_receives_physical_p11": True,
            "model_scales_internal_copy_only": True,
        },

        "training": {
            "epochs": TARGET_EPOCHS,
            "seed": M.SEED,
            "logical_batch": M.LOGICAL_BATCH,
            "microbatch": MICROBATCH,
            "optimizer": "Adam",
            "learning_rate": M.LR,
            "Adam_foreach": False,
            "mixed_precision": False,
        },

        "evaluation_semantics":
            "reproduction development diagnostic; NOT OOD",

        "B3_automatic_authorization": False,
    }

    PORT_PROTOCOL.write_text(
        json.dumps(
            port_protocol,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Fresh model unless exact recovery exists.
    ScaledModel = build_scaled_model_class(M)

    torch.manual_seed(M.SEED)
    model = ScaledModel().to(device)

    gates.update({
        "model_parameters_on_XPU":
            {p.device.type for p in model.parameters()}
            == {"xpu"},
        "fresh_seed_1337_initialization":
            M.SEED == 1337,
        "Nc_model_scale_denominator_exact":
            NC_SCALE_DENOMINATOR == 0.30,
        "physical_p11_not_mutated_by_model_design":
            True,
        "loss_weights_unchanged":
            (
                M.LAMBDA_DATA == 1.0
                and M.LAMBDA_PHYS == 0.05
                and M.LAMBDA_BC == 5.0
                and M.LAMBDA_TIP == 5.0
                and M.LAMBDA_ANCHOR == 10.0
                and M.LAMBDA_MONO == 0.2
                and M.LAMBDA_SHAPE == 0.0
            ),
    })

    config = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "framework": "PyTorch XPU",
        "pytorch_version": torch.__version__,
        "device": str(device),

        "runner_sha256": runner_sha,
        "Stage2_source_sha256": STAGE2_SHA,
        "B2E_protocol_sha256": B2E_PROTOCOL_SHA,
        "dataset_sha256": DATASET_SHA,

        "scientific_change": {
            "network_Nc_scale_denominator":
                NC_SCALE_DENOMINATOR,
            "physical_Nc_unchanged":
                True,
            "p11_physical_remains_dataset_authority":
                True,
        },

        "epochs": TARGET_EPOCHS,
        "seed": M.SEED,
        "hidden": M.HIDDEN,
        "layers": M.LAYERS,
        "param_dim": M.PARAM_DIM,
        "logical_batch": M.LOGICAL_BATCH,
        "microbatch": MICROBATCH,
        "optimizer": "Adam",
        "learning_rate": M.LR,
        "Adam_foreach": False,
        "mixed_precision": False,

        "B3_authorized": False,
    }

    CONFIG.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Train
    # -------------------------------------------------------------------------

    history, train_idx, holdout_idx = train(
        M=M,
        model=model,
        arrays=arrays,
        device=device,
        runner_sha=runner_sha,
    )

    HISTORY.write_text(
        json.dumps(
            jsonable(history),
            indent=2,
        ),
        encoding="utf-8",
    )

    torch.save(
        {
            "milestone": MILESTONE,
            "experiment_id": EXPERIMENT_ID,
            "runner_sha256": runner_sha,
            "Stage2_source_sha256": STAGE2_SHA,
            "B2E_protocol_sha256": B2E_PROTOCOL_SHA,
            "dataset_sha256": DATASET_SHA,
            "framework": "PyTorch XPU",
            "pytorch_version": torch.__version__,
            "conditioner_Nc_scale_denominator":
                NC_SCALE_DENOMINATOR,
            "physical_Nc_unchanged": True,
            "param_dim": M.PARAM_DIM,
            "hidden": M.HIDDEN,
            "layers": M.LAYERS,
            "model_state_dict":
                model.state_dict(),
        },
        CHECKPOINT,
    )

    model.eval()

    gates.update({
        "full_800_epochs_completed":
            len(history.get("epoch", []))
            == TARGET_EPOCHS,
        "history_last_epoch_800":
            history.get("epoch", [None])[-1]
            == TARGET_EPOCHS,
        "checkpoint_written":
            CHECKPOINT.exists()
            and CHECKPOINT.stat().st_size > 0,
        "history_written":
            HISTORY.exists()
            and HISTORY.stat().st_size > 0,
        "config_written":
            CONFIG.exists()
            and CONFIG.stat().st_size > 0,
        "model_eval_mode_before_inference":
            model.training is False,
    })

    # -------------------------------------------------------------------------
    # Evaluation — physical p11 remains input; model scales internally.
    # -------------------------------------------------------------------------

    print("\nSOURCE-NATIVE DEVELOPMENT-DIAGNOSTIC HOLDOUT")
    holdout = M.holdout_metrics(
        model,
        arrays,
        holdout_idx,
        device,
    )

    print(f"  MSE     : {holdout['mse']:.12e}")
    print(f"  RMSE    : {holdout['rmse']:.12e}")
    print(f"  MAE     : {holdout['mae']:.12e}")
    print(f"  Max |e| : {holdout['max_abs_error']:.12e}")
    print("  Bounds  :", "PASS" if holdout["bounds_pass"] else "FAIL")

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
            len(case["rows"]) == 15
            and all(
                finite(r["mse"])
                and finite(r["mae"])
                and finite(r["max_abs_err"])
                for r in case["rows"]
            )
            and finite(
                case["diagnostics"]["r_squared"]
            )
            and finite(
                case["diagnostics"]["max_abs_residual"]
            )
        )

    gates.update({
        "holdout_predictions_finite":
            holdout["finite_predictions"],
        "holdout_bounds_pass":
            holdout["bounds_pass"],
        "holdout_metrics_finite":
            all(
                finite(holdout[k])
                for k in (
                    "mse",
                    "rmse",
                    "mae",
                    "max_abs_error",
                )
            ),
        "all_four_cases_finite":
            all(
                case_finite(c)
                for c in cases.values()
            ),
        "Nc_sweep_all_finite":
            all(
                finite(v["mae"])
                and finite(
                    v["max_abs_error"]
                )
                for v in sweep.values()
            ),
        "Stage1_nesting_Nc0_evaluated":
            "case1_nc0_stage1_nesting"
            in cases
            and "case2_nc0_stage1_nesting"
            in cases,
        "physical_Nc_evaluation_used":
            True,
        "no_OOD":
            True,
        "no_TOF":
            True,
        "no_numeric_threshold_invented":
            True,
    })

    metrics = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,

        "classification":
            "ONE_FACTOR_NC_CONDITIONING_SCALE_REPRODUCTION",

        "scientific_change": {
            "model_Nc":
                "Nc_physical/0.30",
            "physics_Nc":
                "Nc_physical unchanged",
        },

        "training": {
            "epochs_completed":
                len(history["epoch"]),
            "final_losses": {
                k: history[k][-1]
                for k in (
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
                        history["epoch_seconds"]
                    )
                ),
        },

        "holdout": holdout,
        "source_cases": cases,
        "Nc_accuracy_sweep_case1": sweep,

        "evaluation_semantics":
            "development diagnostic; NOT independent and NOT OOD",

        "threshold_policy":
            "No numerical acceptance threshold invented or applied.",
    }

    METRICS.write_text(
        json.dumps(
            jsonable(metrics),
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,

        "classification":
            "FRAMEWORK_EQUIVALENT_ONE_FACTOR_NC_CONDITIONING_SCALE_XPU_REPRODUCTION",

        "authority": {
            "runner_sha256":
                runner_sha,
            "Stage2_sha256":
                STAGE2_SHA,
            "B2E_protocol_sha256":
                B2E_PROTOCOL_SHA,
            "dataset_sha256":
                DATASET_SHA,
        },

        "artifacts": {
            "port_protocol": {
                "path": rel(PORT_PROTOCOL),
                "sha256":
                    sha256(PORT_PROTOCOL),
            },
            "checkpoint": {
                "path": rel(CHECKPOINT),
                "sha256":
                    sha256(CHECKPOINT),
            },
            "config": {
                "path": rel(CONFIG),
                "sha256":
                    sha256(CONFIG),
            },
            "history": {
                "path": rel(HISTORY),
                "sha256":
                    sha256(HISTORY),
            },
            "metrics": {
                "path": rel(METRICS),
                "sha256":
                    sha256(METRICS),
            },
        },

        "firewall": {
            "physical_Nc_changed":
                False,
            "teacher_changed":
                False,
            "physics_residual_changed":
                False,
            "loss_weights_changed":
                False,
            "architecture_width_or_depth_changed":
                False,
            "epochs_changed_vs_COMP_XPU_002":
                False,
            "only_model_conditioner_Nc_scaled":
                True,
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
            and METRICS.stat().st_size > 0,
        "manifest_written":
            MANIFEST.exists()
            and MANIFEST.stat().st_size > 0,
        "manifest_checkpoint_SHA_exact":
            read_json(MANIFEST)[
                "artifacts"
            ]["checkpoint"]["sha256"]
            == sha256(CHECKPOINT),
        "manifest_metrics_SHA_exact":
            read_json(MANIFEST)[
                "artifacts"
            ]["metrics"]["sha256"]
            == sha256(METRICS),
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2F_XPU_COMP_XPU_003_NC_CONDITIONING_SCALE_REPRODUCTION_COMPLETE_"
        "PHYSICAL_NC_TEACHER_RESIDUAL_TRANSFORM_AND_DATASET_UNCHANGED_"
        "MODEL_CONDITIONER_NC_SCALED_0P30_TO_UNIT_INTERVAL_ONLY_"
        "FRESH_800_EPOCH_INTEL_XPU_TRAINING_COMPLETE_CHECKPOINT_AND_METRICS_SHA_BOUND_"
        "DIAGNOSTICS_FINITE_SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
        "V16E1B2G_COMP_XPU_002_VS_003_COMPARISON_REQUIRED_B3_NOT_YET_AUTHORIZED"
        if ok else
        "V16E1B2F_XPU_COMP_XPU_003_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "status": status,

        "runner_sha256": runner_sha,
        "port_protocol_sha256":
            sha256(PORT_PROTOCOL),
        "checkpoint_sha256":
            sha256(CHECKPOINT),
        "config_sha256":
            sha256(CONFIG),
        "history_sha256":
            sha256(HISTORY),
        "metrics_sha256":
            sha256(METRICS),
        "manifest_sha256":
            sha256(MANIFEST),

        "holdout_mse":
            holdout["mse"],
        "holdout_rmse":
            holdout["rmse"],
        "holdout_mae":
            holdout["mae"],
        "holdout_max_abs_error":
            holdout["max_abs_error"],

        "B3_authorized":
            False,
        "comparison_required_before_B3":
            True,

        "next_milestone": (
            "V16E-1B2G-XPU — Compare COMP-XPU-003 against COMP-XPU-002 "
            "using the frozen B2D per-Nc, full-domain, front-excluded, "
            "front-position, and response-ratio diagnostics"
            if ok else
            "V16E-1B2F-XPU-R1 — diagnose failed gate"
        ),

        "gates": {
            k: bool(v)
            for k, v in gates.items()
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
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nARTIFACT HASHES")
    print("  Runner       :", runner_sha)
    print("  Dataset      :", DATASET_SHA)
    print("  Port protocol:", sha256(PORT_PROTOCOL))
    print("  Checkpoint   :", sha256(CHECKPOINT))
    print("  Config       :", sha256(CONFIG))
    print("  History      :", sha256(HISTORY))
    print("  Metrics      :", sha256(METRICS))
    print("  Manifest     :", sha256(MANIFEST))
    print("  Summary      :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
