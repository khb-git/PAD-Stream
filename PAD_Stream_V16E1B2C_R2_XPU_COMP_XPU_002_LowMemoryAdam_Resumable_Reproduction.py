#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2C-XPU-R2
Low-Memory Adam Execution Repair for V16E-BLREP-COMP-XPU-002

Observed failure:
  UR_RESULT_ERROR_OUT_OF_DEVICE_MEMORY
  at torch.optim.adam._multi_tensor_adam -> torch._foreach_sqrt

Operational repair only:
  force torch.optim.Adam(..., foreach=False)

Scientific settings remain unchanged:
  * same experiment V16E-BLREP-COMP-XPU-002
  * same frozen Godunov dataset
  * same fresh seed-1337 initialization
  * same 11-D conditioning
  * same 2 x LSTM(64)
  * same Adam algorithm and lr=1e-3
  * same loss terms / weights
  * same logical batch=8192
  * same XPU microbatch=2048
  * same deterministic epoch order
  * same 800-epoch target
  * same R1 recovery every 25 completed epochs
  * no TOF
  * no OOD

This R2 runner imports the exact R1 resumable runner and changes only the Adam
execution implementation from runtime-default foreach selection to foreach=False.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import os
import time

import torch


R = Path(__file__).resolve().parent

R1 = R / "PAD_Stream_V16E1B2C_R1_XPU_COMP_XPU_002_800Epoch_Resumable_Reproduction.py"
R1_SHA = "3a29b62b1d005c535cbc3f8f5b97215ee55b81326c3a6bfff752e88aea08440c"

EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-002"

OUT = (
    R
    / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)
OUT.mkdir(parents=True, exist_ok=True)

AMENDMENT = OUT / "V16E_BLREP_COMP_XPU_002_R2_LowMemory_Adam_Execution_Amendment.json"
COMPLETION = OUT / "V16E_BLREP_COMP_XPU_002_R2_Execution_Record.json"
FINAL_SUMMARY = OUT / "PAD_Stream_V16E1B2C_XPU_Summary.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def import_r1():
    if not R1.exists():
        raise RuntimeError(f"R1 runner is missing: {R1}")

    actual = sha256(R1)
    if actual != R1_SHA:
        raise RuntimeError(
            "R1 runner SHA mismatch.\n"
            f"Expected: {R1_SHA}\n"
            f"Actual  : {actual}"
        )

    spec = importlib.util.spec_from_file_location(
        "v16e1b2c_r1_resumable",
        R1,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import exact R1 resumable runner.")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def atomic_json_write(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2C-XPU-R2")
    print("Low-Memory Adam Resumable Execution Repair")
    print("=" * 80)
    print("Experiment:", EXPERIMENT_ID)
    print("Scientific hyperparameters unchanged.")
    print("Operational amendment: Adam foreach=False\n")

    R1MOD = import_r1()

    amendment = {
        "milestone": "V16E-1B2C-XPU-R2",
        "experiment_id": EXPERIMENT_ID,
        "classification": "OPERATIONAL_MEMORY_EXECUTION_REPAIR",
        "parent_R1_source_sha256": R1_SHA,
        "observed_failure": {
            "runtime_error": "UR_RESULT_ERROR_OUT_OF_DEVICE_MEMORY",
            "location":
                "torch.optim.adam._multi_tensor_adam -> torch._foreach_sqrt",
            "timing": "first optimizer step of fresh COMP-XPU-002 R1 attempt",
            "recovery_checkpoint_created_before_failure": False,
        },
        "single_operational_change": {
            "component": "torch.optim.Adam implementation",
            "old": "foreach=None/default runtime selection",
            "new": "foreach=False",
            "reason":
                "reduce peak optimizer-step memory by avoiding foreach "
                "tensor-list intermediates",
        },
        "scientific_settings_unchanged": {
            "experiment_id": EXPERIMENT_ID,
            "optimizer_algorithm": "Adam",
            "learning_rate": 1e-3,
            "logical_batch": 8192,
            "XPU_microbatch": 2048,
            "epochs": 800,
            "seed": 1337,
            "fresh_initialization": True,
            "dataset_changed": False,
            "architecture_changed": False,
            "conditioning_changed": False,
            "loss_weights_changed": False,
            "Nc_transform_changed": False,
            "TOF": False,
            "OOD": False,
        },
        "recovery_semantics":
            "R1 epoch-boundary model + Adam-state recovery remains active. "
            "R2 recovery checkpoints must be resumed with this R2 runner.",
        "provenance_policy":
            "Final COMP-XPU-002 evidence must bind this sidecar amendment "
            "because the base B2C config records Adam but not foreach=False.",
    }

    atomic_json_write(amendment, AMENDMENT)
    amendment_sha = sha256(AMENDMENT)

    print("EXECUTION AMENDMENT")
    print("  file    :", AMENDMENT)
    print("  SHA-256 :", amendment_sha)

    OriginalAdam = torch.optim.Adam

    def LowMemoryAdam(*args, **kwargs):
        if "foreach" in kwargs and kwargs["foreach"] not in (None, False):
            raise RuntimeError(
                "R2 execution firewall: foreach=True is prohibited."
            )
        kwargs["foreach"] = False
        return OriginalAdam(*args, **kwargs)

    torch.optim.Adam = LowMemoryAdam

    try:
        R1MOD.main()

    except SystemExit as exc:
        record = {
            "milestone": "V16E-1B2C-XPU-R2",
            "experiment_id": EXPERIMENT_ID,
            "amendment_sha256": amendment_sha,
            "status": "INTERRUPTED_OR_DEVICE_LOSS",
            "system_exit_code": exc.code,
            "final_summary_exists": FINAL_SUMMARY.exists(),
            "timestamp_unix": time.time(),
        }
        atomic_json_write(record, COMPLETION)
        raise

    except BaseException as exc:
        record = {
            "milestone": "V16E-1B2C-XPU-R2",
            "experiment_id": EXPERIMENT_ID,
            "amendment_sha256": amendment_sha,
            "status": "FAILED_EXCEPTION",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "final_summary_exists": FINAL_SUMMARY.exists(),
            "timestamp_unix": time.time(),
        }
        atomic_json_write(record, COMPLETION)
        raise

    finally:
        torch.optim.Adam = OriginalAdam

    record = {
        "milestone": "V16E-1B2C-XPU-R2",
        "experiment_id": EXPERIMENT_ID,
        "amendment_sha256": amendment_sha,
        "status": "NORMAL_COMPLETION",
        "Adam_foreach": False,
        "final_summary_exists": FINAL_SUMMARY.exists(),
        "final_summary_sha256":
            sha256(FINAL_SUMMARY) if FINAL_SUMMARY.exists() else None,
        "timestamp_unix": time.time(),
    }
    atomic_json_write(record, COMPLETION)

    print("\nR2 EXECUTION RECORD")
    print("  SHA-256:", sha256(COMPLETION))


if __name__ == "__main__":
    main()
