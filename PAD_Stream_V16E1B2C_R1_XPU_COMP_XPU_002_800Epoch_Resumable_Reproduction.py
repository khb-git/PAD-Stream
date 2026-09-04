#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2C-XPU-R1
Resumable execution repair for V16E-BLREP-COMP-XPU-002.

Reason
------
The prospectively frozen 800-epoch COMP-XPU-002 run experienced an Intel
Level-Zero / Unified Runtime device-loss error during torch.xpu.synchronize()
after epoch 150:

    UR_RESULT_ERROR_DEVICE_LOST

The failed run had not yet written the final experiment checkpoint/history,
because the original runner only archives those after all 800 epochs.

This repair changes NO scientific training setting. It imports the exact frozen
V16E-1B2C runner and replaces only its execution loop with an epoch-boundary
recovery-checkpoint implementation.

Scientific settings remain unchanged:
  * same experiment: V16E-BLREP-COMP-XPU-002
  * fresh seed-1337 initialization for a new run
  * same frozen Godunov dataset
  * same 11-D conditioning
  * same 2 x LSTM(64)
  * same losses and weights
  * same Adam lr = 1e-3
  * same logical batch = 8192
  * same XPU microbatch = 2048
  * same deterministic epoch permutations
  * same 800-epoch target
  * no TOF
  * no OOD

Operational repair only:
  * recovery checkpoint every 25 completed epochs;
  * recovery checkpoint includes model state, Adam optimizer state, and history;
  * rerunning this same script automatically resumes from the latest valid
    recovery checkpoint;
  * checkpoints are written only at completed epoch boundaries;
  * device loss during an epoch never causes a partial epoch to be accepted.

This is continuation/resume of the same experiment, NOT warm-starting a new
experiment. A resumed run restores the optimizer state as well as the weights.
"""

from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import sys
import time

import numpy as np
import torch


R = Path(__file__).resolve().parent

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-002"
TARGET_EPOCHS = 800
CHECKPOINT_INTERVAL = 25
REQUIRED_MICROBATCH = 2048

OUT = (
    R
    / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)

RECOVERY_DIR = OUT / "recovery"
RECOVERY_DIR.mkdir(parents=True, exist_ok=True)

RECOVERY_LATEST = RECOVERY_DIR / "V16E_BLREP_COMP_XPU_002_RECOVERY_LATEST.json"

FROZEN_DATASET = (
    R
    / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
FROZEN_DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

FINAL_SUMMARY = OUT / "PAD_Stream_V16E1B2C_XPU_Summary.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def import_frozen_runner():
    if not BASE_RUNNER.exists():
        raise RuntimeError(f"Frozen B2C runner is missing: {BASE_RUNNER}")

    actual = sha256(BASE_RUNNER)
    if actual != BASE_RUNNER_SHA:
        raise RuntimeError(
            "Frozen B2C runner SHA mismatch.\n"
            f"Expected: {BASE_RUNNER_SHA}\n"
            f"Actual  : {actual}"
        )

    spec = importlib.util.spec_from_file_location(
        "v16e1b2c_frozen_runner",
        BASE_RUNNER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import frozen V16E-1B2C runner.")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cpu_clone(obj):
    """Recursively clone tensor state to CPU for durable recovery storage."""
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
    """Ensure restored Adam state tensors live with XPU parameters."""
    for state in optimizer.state.values():
        for key, value in list(state.items()):
            if torch.is_tensor(value):
                state[key] = value.to(device)


def checkpoint_path(epoch: int) -> Path:
    return RECOVERY_DIR / f"V16E_BLREP_COMP_XPU_002_RECOVERY_E{epoch:04d}.pt"


def atomic_torch_save(payload, destination: Path):
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, destination)


def atomic_json_write(payload, destination: Path):
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, destination)


def save_recovery_checkpoint(
    M,
    model,
    optimizer,
    history,
    completed_epoch,
    microbatch,
):
    # Epoch already completed and XPU synchronization already succeeded.
    path = checkpoint_path(completed_epoch)

    payload = {
        "recovery_schema": "V16E1B2C_XPU_R1_EPOCH_BOUNDARY_V1",
        "experiment_id": EXPERIMENT_ID,
        "base_runner_sha256": BASE_RUNNER_SHA,
        "Stage2_source_sha256": M.SOURCE_SHA,
        "dataset_sha256": FROZEN_DATASET_SHA,
        "target_epochs": TARGET_EPOCHS,
        "completed_epoch": int(completed_epoch),
        "seed": int(M.SEED),
        "logical_batch": int(M.LOGICAL_BATCH),
        "microbatch": int(microbatch),
        "learning_rate": float(M.LR),
        "model_state_dict": cpu_clone(model.state_dict()),
        "optimizer_state_dict": cpu_clone(optimizer.state_dict()),
        "history": copy.deepcopy(history),
        "training_semantics": {
            "epoch_boundary_only": True,
            "partial_epoch_accepted": False,
            "warm_start": False,
            "optimizer_state_restored_on_resume": True,
        },
    }

    atomic_torch_save(payload, path)
    ck_sha = sha256(path)

    latest = {
        "experiment_id": EXPERIMENT_ID,
        "completed_epoch": int(completed_epoch),
        "checkpoint_path": str(path),
        "checkpoint_sha256": ck_sha,
        "base_runner_sha256": BASE_RUNNER_SHA,
        "dataset_sha256": FROZEN_DATASET_SHA,
        "target_epochs": TARGET_EPOCHS,
        "microbatch": int(microbatch),
    }
    atomic_json_write(latest, RECOVERY_LATEST)

    # Keep only the latest recovery payload. The pointer JSON preserves identity.
    for old in RECOVERY_DIR.glob("V16E_BLREP_COMP_XPU_002_RECOVERY_E*.pt"):
        if old != path:
            try:
                old.unlink()
            except OSError:
                pass

    print(
        f"  [RECOVERY] epoch {completed_epoch:04d} checkpoint saved\n"
        f"             SHA-256: {ck_sha}"
    )


def load_latest_recovery(M, model, optimizer, device, microbatch):
    if not RECOVERY_LATEST.exists():
        return None

    latest = json.loads(RECOVERY_LATEST.read_text(encoding="utf-8"))

    required = {
        "experiment_id": EXPERIMENT_ID,
        "base_runner_sha256": BASE_RUNNER_SHA,
        "dataset_sha256": FROZEN_DATASET_SHA,
        "target_epochs": TARGET_EPOCHS,
        "microbatch": microbatch,
    }

    for key, expected in required.items():
        actual = latest.get(key)
        if actual != expected:
            raise RuntimeError(
                f"Recovery pointer mismatch for {key}: "
                f"expected {expected!r}, got {actual!r}"
            )

    path = Path(latest["checkpoint_path"])
    if not path.exists():
        raise RuntimeError(f"Recovery checkpoint does not exist: {path}")

    actual_sha = sha256(path)
    if actual_sha != latest["checkpoint_sha256"]:
        raise RuntimeError(
            "Recovery checkpoint SHA mismatch.\n"
            f"Expected: {latest['checkpoint_sha256']}\n"
            f"Actual  : {actual_sha}"
        )

    payload = torch.load(path, map_location="cpu", weights_only=False)

    checks = {
        "experiment_id": payload.get("experiment_id") == EXPERIMENT_ID,
        "base_runner_sha256": payload.get("base_runner_sha256") == BASE_RUNNER_SHA,
        "Stage2_source_sha256": payload.get("Stage2_source_sha256") == M.SOURCE_SHA,
        "dataset_sha256": payload.get("dataset_sha256") == FROZEN_DATASET_SHA,
        "target_epochs": payload.get("target_epochs") == TARGET_EPOCHS,
        "seed": payload.get("seed") == M.SEED,
        "logical_batch": payload.get("logical_batch") == M.LOGICAL_BATCH,
        "microbatch": payload.get("microbatch") == microbatch,
    }

    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        raise RuntimeError(
            "Recovery checkpoint scientific identity mismatch: "
            + ", ".join(failed)
        )

    completed = int(payload["completed_epoch"])
    history = payload["history"]

    if completed < 1 or completed > TARGET_EPOCHS:
        raise RuntimeError(f"Invalid recovery epoch: {completed}")

    if (
        not isinstance(history.get("epoch"), list)
        or len(history["epoch"]) != completed
        or history["epoch"][-1] != completed
    ):
        raise RuntimeError("Recovery history does not match completed epoch.")

    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.to(device)

    optimizer.load_state_dict(payload["optimizer_state_dict"])
    move_optimizer_state_to_device(optimizer, device)

    print("\nRECOVERY CHECKPOINT FOUND")
    print("  completed epoch :", completed)
    print("  checkpoint      :", path)
    print("  SHA-256         :", actual_sha)
    print("  optimizer state : RESTORED")
    print("  next epoch      :", completed + 1)

    return {
        "completed_epoch": completed,
        "history": history,
        "checkpoint_path": path,
        "checkpoint_sha256": actual_sha,
    }


def train_xpu_resumable(
    M,
    model,
    arrays,
    device,
    microbatch,
    epochs,
):
    if epochs != TARGET_EPOCHS:
        raise RuntimeError(
            f"R1 recovery runner requires epochs={TARGET_EPOCHS}; got {epochs}."
        )

    if microbatch != REQUIRED_MICROBATCH:
        raise RuntimeError(
            f"Frozen COMP-XPU-002 microbatch is {REQUIRED_MICROBATCH}; "
            f"got {microbatch}."
        )

    if not FROZEN_DATASET.exists() or sha256(FROZEN_DATASET) != FROZEN_DATASET_SHA:
        raise RuntimeError("Frozen Stage-2 dataset is missing or changed.")

    xi_all, Sw_all, p11_all, tD_all, ai_all, at_all = arrays
    N = len(xi_all)

    rng = np.random.default_rng(M.SEED)
    idx = np.arange(N)
    rng.shuffle(idx)

    n_train = int(0.8 * N)
    train_idx = idx[:n_train]
    holdout_idx = idx[n_train:]

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=M.LR,
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

    recovery = load_latest_recovery(
        M=M,
        model=model,
        optimizer=optimizer,
        device=device,
        microbatch=microbatch,
    )

    if recovery is None:
        start_epoch = 1
        print("\nRECOVERY")
        print("  no valid recovery checkpoint found")
        print("  starting a fresh seed-1337 COMP-XPU-002 run")
    else:
        history = recovery["history"]
        start_epoch = recovery["completed_epoch"] + 1

    print("\nXPU TRAINING — RESUMABLE")
    print("  device              :", device)
    print("  train profiles      :", len(train_idx))
    print("  holdout profiles    :", len(holdout_idx))
    print("  logical batch       :", M.LOGICAL_BATCH)
    print("  XPU microbatch      :", microbatch)
    print("  optimizer updates/ep:",
          int(np.ceil(len(train_idx) / M.LOGICAL_BATCH)))
    print("  target epochs       :", epochs)
    print("  starting epoch      :", start_epoch)
    print("  recovery interval   :", CHECKPOINT_INTERVAL)
    print("  mixed precision     : OFF")

    if start_epoch > epochs:
        print("  training already complete in recovery checkpoint.")
        return history, train_idx, holdout_idx

    session_t0 = time.time()

    for epoch in range(start_epoch, epochs + 1):
        t0 = time.time()

        # Exact same deterministic epoch permutation as the frozen B2C runner.
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

        for b0 in range(0, len(order), M.LOGICAL_BATCH):
            logical_idx = order[b0:b0 + M.LOGICAL_BATCH]
            logical_n = len(logical_idx)

            optimizer.zero_grad(set_to_none=True)

            for m0 in range(0, logical_n, microbatch):
                ids = logical_idx[m0:m0 + microbatch]
                m = len(ids)

                xi = torch.from_numpy(xi_all[ids]).to(device)
                Sw = torch.from_numpy(Sw_all[ids]).to(device)
                p11 = torch.from_numpy(p11_all[ids]).to(device)
                tD = torch.from_numpy(tD_all[ids]).to(device)
                ai = torch.from_numpy(ai_all[ids]).to(device)
                at = torch.from_numpy(at_all[ids]).to(device)

                _, parts = M.total_losses(
                    model,
                    xi,
                    Sw,
                    p11,
                    tD,
                    ai,
                    at,
                )

                scale = float(m) / float(logical_n)
                (parts["total"] * scale).backward()

                for k in sums:
                    sums[k] += float(parts[k].detach().cpu()) * m

                count += m
                del xi, Sw, p11, tD, ai, at, parts

            optimizer.step()

        # An epoch is accepted only if the XPU completes all queued work.
        M.sync_xpu()

        n = max(count, 1)
        sec = time.time() - t0

        history["epoch"].append(epoch)
        for k in sums:
            history[k].append(sums[k] / n)
        history["epoch_seconds"].append(sec)

        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(
                f"[XPU-COMP-R1] Epoch {epoch:04d}/{epochs} "
                f"| Data {history['data'][-1]:.3e} "
                f"| Phys {history['physics'][-1]:.3e} "
                f"| BC {history['bc_inj'][-1]:.3e} "
                f"| Tip {history['bc_tip'][-1]:.3e} "
                f"| Anchor {history['anchor'][-1]:.3e} "
                f"| Mono {history['mono'][-1]:.3e} "
                f"| {sec:.2f}s/epoch "
                f"| session {time.time()-session_t0:.1f}s"
            )

        if epoch % CHECKPOINT_INTERVAL == 0 or epoch == epochs:
            save_recovery_checkpoint(
                M=M,
                model=model,
                optimizer=optimizer,
                history=history,
                completed_epoch=epoch,
                microbatch=microbatch,
            )

    return history, train_idx, holdout_idx


def main():
    M = import_frozen_runner()

    # Bind only the operational execution repair. All scientific/evaluation/
    # archival logic remains the exact frozen B2C implementation.
    def patched_train_xpu(model, arrays, device, microbatch, epochs):
        return train_xpu_resumable(
            M=M,
            model=model,
            arrays=arrays,
            device=device,
            microbatch=microbatch,
            epochs=epochs,
        )

    M.train_xpu = patched_train_xpu

    try:
        M.main()
    except RuntimeError as exc:
        msg = str(exc)

        if (
            "UR_RESULT_ERROR_DEVICE_LOST" in msg
            or "DEVICE_LOST" in msg
            or "level_zero backend failed with error: 20" in msg
        ):
            print("\n" + "=" * 80)
            print("INTEL XPU DEVICE LOSS DETECTED")
            print("=" * 80)
            print(
                "No partial epoch has been accepted. After the Intel GPU is "
                "healthy again, rerun this SAME command. The runner will "
                "restore the latest completed-epoch model + Adam state."
            )

            if RECOVERY_LATEST.exists():
                latest = json.loads(
                    RECOVERY_LATEST.read_text(encoding="utf-8")
                )
                print("Latest safe epoch :", latest.get("completed_epoch"))
                print("Recovery SHA-256  :", latest.get("checkpoint_sha256"))
            else:
                print(
                    "No recovery checkpoint had yet been written; "
                    "the next run will restart from fresh seed-1337 initialization."
                )

            raise SystemExit(75)

        raise


if __name__ == "__main__":
    main()
