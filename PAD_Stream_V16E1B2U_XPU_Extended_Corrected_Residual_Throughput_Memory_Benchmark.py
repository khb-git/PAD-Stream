#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2U-XPU
Extended Corrected-Residual Backward Throughput / Memory Benchmark

Purpose
-------
Continue the B2S Intel-XPU feasibility benchmark beyond the original
protocol boundary of microbatch 16.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT MUTATION.
NO OOD.
NO TOF.

Authority
---------
V16E-1B2T explicitly authorizes the operational continuation candidates:

    32, 64, 128, 256

Scientific model / graph
------------------------
UNCHANGED from the certified B2S benchmark:
    * frozen COMP-XPU-004 checkpoint
    * [xi, eta] architecture
    * raw physical 11-D p11
    * corrected conservative moving-fan residual
    * create_graph=True local recurrent derivatives
    * complete frozen Stage-2 total loss
    * total.backward()
    * gradients inspected then discarded
    * NO optimizer object and NO weight update

Implementation provenance
-------------------------
To avoid silently re-implementing the corrected derivative graph, every B2U
child imports the exact frozen B2S source SHA and calls its already-certified
run_candidate_child() function after changing ONLY the operational candidate
list from [1,2,4,8,16] to [32,64,128,256].

Each candidate runs in a separate Python subprocess / XPU context.
OOM or device loss is an allowed operational result.

Selection
---------
Bind the largest ACTUALLY TESTED successful candidate. Do not infer feasibility
above the largest tested success.

B2U does NOT authorize the COMP-XPU-005 800-epoch run.
A later V16E-1B2V operational execution-contract freeze is required.

B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time

import numpy as np


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2U-XPU"

ORIGINAL_B2S_CANDIDATES = [1, 2, 4, 8, 16]
CANDIDATES = [32, 64, 128, 256]
LOGICAL_BATCH = 8192
TARGET_EPOCHS = 800
SEED = 1337

# =============================================================================
# Frozen authority
# =============================================================================

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

COMP004_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-004"
)
COMP004_CHECKPOINT = COMP004_DIR / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"

# Certified B2S implementation / results.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

B2S_DIR = (
    R / "output"
    / "V16_E1B2S_XPU_CORRECTED_RESIDUAL_BACKWARD_FEASIBILITY"
)
B2S_RESULTS = B2S_DIR / "V16E1B2S_Corrected_Residual_Backward_Feasibility.json"
B2S_SUMMARY = B2S_DIR / "PAD_Stream_V16E1B2S_XPU_Summary.json"

B2S_RESULTS_SHA = "f133af4135ff10b68d2e300b72002e1008c99ef0df0804275b35aacd2d52f94d"
B2S_SUMMARY_SHA = "e861db86a39d2aa96020935837675f4a9b5dc04efe6a687cbf7196e5af18d7c1"

# B2T authority.
B2T_SOURCE = (
    R
    / "PAD_Stream_V16E1B2T_XPU_B2S_Interpretation_Extended_Throughput_Protocol_Freeze.py"
)
B2T_SOURCE_SHA = "319bbdf2a10d0434bef8063787d2cdcec6eaa4c47b6aa0f536af02059345a981"

B2T_DIR = (
    R / "output"
    / "V16_E1B2T_XPU_B2S_INTERPRETATION_EXTENDED_THROUGHPUT_PROTOCOL"
)
B2T_INTERPRETATION = B2T_DIR / "V16E1B2T_B2S_Operational_Interpretation.json"
B2T_PROTOCOL = B2T_DIR / "V16E1B2T_B2U_Extended_Throughput_Protocol.json"
B2T_HANDOFF = B2T_DIR / "V16E1B2T_B2U_Handoff.md"
B2T_SUMMARY = B2T_DIR / "PAD_Stream_V16E1B2T_XPU_Summary.json"

B2T_INTERPRETATION_SHA = "62452257efc0694a6c128c19dd78859fbf752434acebfb53c46919c9d5d7300b"
B2T_PROTOCOL_SHA = "0858cbf9934b95ca29d07f20f3157c20660a2e4684d432ced0e19e7659ed7598"
B2T_HANDOFF_SHA = "37d1a88a8c9573447e1482caa0757293aefa150271c377361e795e00a682080f"
B2T_SUMMARY_SHA = "9a54f2c7bb56160ec705153ec5f33b66070c8ae432aea157340c40548f516187"

EXPECTED_B2T_STATUS = (
    "V16E1B2T_XPU_B2S_FEASIBILITY_INTERPRETATION_AND_EXTENDED_THROUGHPUT_PROTOCOL_FROZEN_"
    "CORRECTED_RESIDUAL_BACKWARD_CONFIRMED_FOR_MICROBATCHES_1_2_4_8_16_"
    "MICROBATCH_16_CLASSIFIED_AS_LARGEST_PROTOCOL_TEST_NOT_HARDWARE_CEILING_"
    "NAIVE_FULL_RUN_TIMING_PROJECTION_BOUND_AS_OPERATIONAL_DIAGNOSTIC_ONLY_"
    "COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_"
    "B2U_EXTENDED_MICROBATCHES_32_64_128_256_NO_UPDATE_BENCHMARK_AUTHORIZED_"
    "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = OUT / "V16E1B2U_Extended_Throughput_Memory_Results.json"
DECISION = OUT / "V16E1B2U_Operational_Microbatch_Decision.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2U_XPU_Summary.json"
CHILD_DIR = OUT / "candidate_results"
CHILD_DIR.mkdir(parents=True, exist_ok=True)


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


def atomic_json_write(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify_runtime_error(text: str) -> str:
    t = text.lower()
    if (
        "out of memory" in t
        or "oom" in t
        or "ze_result_error_out_of_device_memory" in t
    ):
        return "OOM"
    if (
        "device lost" in t
        or "ur_result_error_device_lost" in t
        or "ze_result_error_device_lost" in t
    ):
        return "DEVICE_LOST"
    return "RUNTIME_ERROR"


def microbatches_per_epoch(
    n_train: int,
    logical_batch: int,
    microbatch: int,
) -> int:
    total = 0
    for b0 in range(0, n_train, logical_batch):
        chunk = min(logical_batch, n_train - b0)
        total += int(math.ceil(chunk / microbatch))
    return total


# =============================================================================
# Child: exact B2S graph, operational candidate list only
# =============================================================================

def child_main(microbatch: int, result_path: Path) -> int:
    """
    Import the exact frozen B2S source and reuse its certified child benchmark.

    ONLY operational mutation:
        B2S.CANDIDATES = [32,64,128,256]

    This changes no model, loss, derivative, dataset, optimizer, or scientific
    setting.
    """
    if microbatch not in CANDIDATES:
        payload = {
            "microbatch": int(microbatch),
            "success": False,
            "failure_class": "UNAUTHORIZED_CANDIDATE",
            "error": f"Unauthorized B2U candidate {microbatch}",
            "optimizer_created": False,
            "weight_update": False,
        }
        atomic_json_write(payload, result_path)
        return 2

    if not exact(B2S_SOURCE, B2S_SOURCE_SHA):
        payload = {
            "microbatch": int(microbatch),
            "success": False,
            "failure_class": "B2S_SOURCE_SHA_MISMATCH",
            "error": "Frozen B2S source SHA mismatch in child.",
            "optimizer_created": False,
            "weight_update": False,
        }
        atomic_json_write(payload, result_path)
        return 2

    B2S = import_module(
        B2S_SOURCE,
        f"v16e1b2s_reuse_mb{microbatch}",
    )

    # Operational candidate continuation only.
    B2S.CANDIDATES = list(CANDIDATES)

    rc = B2S.run_candidate_child(
        microbatch,
        result_path,
    )

    # Add B2U provenance fields without changing the underlying B2S result.
    if result_path.exists():
        rec = read_json(result_path)
        rec["B2U_milestone"] = MILESTONE
        rec["exact_B2S_source_sha256"] = B2S_SOURCE_SHA
        rec["B2U_operational_candidates"] = list(CANDIDATES)
        rec["scientific_graph_changed_from_B2S"] = False
        atomic_json_write(rec, result_path)

    return int(rc)


# =============================================================================
# Parent
# =============================================================================

def parent_main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2U-XPU")
    print("Extended Corrected-Residual Backward Throughput / Memory Benchmark")
    print("=" * 80)
    print("NO TRAINING — NO OPTIMIZER — NO WEIGHT UPDATE.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2U summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),

        "B2S_source_SHA_exact":
            exact(B2S_SOURCE, B2S_SOURCE_SHA),

        "B2S_results_SHA_exact":
            exact(B2S_RESULTS, B2S_RESULTS_SHA),

        "B2S_summary_SHA_exact":
            exact(B2S_SUMMARY, B2S_SUMMARY_SHA),

        "B2T_source_SHA_exact":
            exact(B2T_SOURCE, B2T_SOURCE_SHA),

        "B2T_interpretation_SHA_exact":
            exact(B2T_INTERPRETATION, B2T_INTERPRETATION_SHA),

        "B2T_protocol_SHA_exact":
            exact(B2T_PROTOCOL, B2T_PROTOCOL_SHA),

        "B2T_handoff_SHA_exact":
            exact(B2T_HANDOFF, B2T_HANDOFF_SHA),

        "B2T_summary_SHA_exact":
            exact(B2T_SUMMARY, B2T_SUMMARY_SHA),
    }

    b2s = read_json(B2S_RESULTS) if B2S_RESULTS.exists() else {}
    b2t = read_json(B2T_SUMMARY) if B2T_SUMMARY.exists() else {}
    b2t_protocol = (
        read_json(B2T_PROTOCOL)
        if B2T_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2S_original_candidates_exact":
            b2s.get("candidate_microbatches")
            == ORIGINAL_B2S_CANDIDATES,

        "B2S_original_all_successful":
            b2s.get("successful_microbatches")
            == ORIGINAL_B2S_CANDIDATES,

        "B2T_status_exact":
            b2t.get("status")
            == EXPECTED_B2T_STATUS,

        "B2T_COMP005_training_false":
            b2t.get("COMP_XPU_005_full_training_authorized")
            is False,

        "B2T_B2U_true":
            b2t.get("B2U_authorized")
            is True,

        "B2T_B3_false":
            b2t.get("B3_authorized")
            is False,

        "B2T_extended_candidates_exact":
            b2t.get("authorized_extended_candidates")
            == CANDIDATES,

        "B2T_protocol_next_exact":
            b2t_protocol.get("authorized_next_milestone")
            == MILESTONE,

        "B2T_protocol_candidates_exact":
            b2t_protocol.get("candidate_microbatches")
            == CANDIDATES,

        "B2T_protocol_training_false":
            (
                b2t_protocol
                .get("scientific_firewall", {})
                .get("training")
                is False
            ),

        "B2T_protocol_optimizer_false":
            (
                b2t_protocol
                .get("scientific_firewall", {})
                .get("optimizer")
                is False
            ),

        "B2T_protocol_weight_update_false":
            (
                b2t_protocol
                .get("scientific_firewall", {})
                .get("weight_update")
                is False
            ),
    })

    print("AUTHORITY / EXTENDED-BENCHMARK GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2U blocked by authority/protocol mismatch."
        )

    # Stale B2U child outputs may be safely replaced. No scientific artifact or
    # checkpoint is touched.
    for p in CHILD_DIR.glob("candidate_mb*.json"):
        try:
            p.unlink()
        except OSError:
            pass

    script = Path(__file__).resolve()
    candidate_results = []

    print("\nEXTENDED CANDIDATE BENCHMARKS")
    print("  Exact frozen B2S child graph reused.")
    print("  Each candidate runs in an isolated subprocess.")
    print("  OOM/device-loss is an allowed operational result.\n")

    for mb in CANDIDATES:
        result_path = (
            CHILD_DIR
            / f"candidate_mb{mb:03d}.json"
        )

        cmd = [
            sys.executable,
            str(script),
            "--candidate",
            str(mb),
            "--result-path",
            str(result_path),
        ]

        t0 = time.perf_counter()

        proc = subprocess.run(
            cmd,
            cwd=str(R),
            capture_output=True,
            text=True,
        )

        wall = time.perf_counter() - t0

        if result_path.exists():
            rec = read_json(result_path)
        else:
            combined = (
                (proc.stdout or "")
                + "\n"
                + (proc.stderr or "")
            ).strip()

            rec = {
                "microbatch": int(mb),
                "success": False,
                "failure_class": classify_runtime_error(combined),
                "error": combined[-4000:],
                "optimizer_created": False,
                "weight_update": False,
                "scientific_graph_changed_from_B2S": False,
            }

        rec["subprocess_returncode"] = int(proc.returncode)
        rec["subprocess_wall_seconds"] = float(wall)

        if rec.get("success"):
            sec = float(
                rec["forward_residual_backward_seconds"]
            )
            rec["profiles_per_second"] = float(
                mb / sec
            )

            mem = rec.get("peak_xpu_memory_bytes")
            mem_text = (
                f"{mem / (1024**3):.3f} GiB"
                if isinstance(mem, int)
                and mem >= 0
                else "n/a"
            )

            print(
                f"  microbatch={mb:3d} | PASS "
                f"| total={sec:.3f}s "
                f"| throughput={rec['profiles_per_second']:.3f} profiles/s "
                f"| peak={mem_text}"
            )
        else:
            print(
                f"  microbatch={mb:3d} | FAIL "
                f"| class={rec.get('failure_class')} "
                f"| returncode={proc.returncode}"
            )

        candidate_results.append(rec)

        if sha256(COMP004_CHECKPOINT) != COMP004_CHECKPOINT_SHA:
            raise RuntimeError(
                "COMP-XPU-004 checkpoint changed during B2U."
            )

    successful = [
        int(rec["microbatch"])
        for rec in candidate_results
        if rec.get("success")
    ]

    selected = max(successful) if successful else None

    # Frozen dataset size and training split.
    d = np.load(DATASET)
    n_profiles = int(len(d["p11"]))
    n_train = int(0.8 * n_profiles)

    projections = {}

    for rec in candidate_results:
        mb = int(rec["microbatch"])

        if not rec.get("success"):
            continue

        sec = float(
            rec["forward_residual_backward_seconds"]
        )

        n_micro = microbatches_per_epoch(
            n_train=n_train,
            logical_batch=LOGICAL_BATCH,
            microbatch=mb,
        )

        epoch_sec = float(
            n_micro * sec
        )

        projections[str(mb)] = {
            "microbatch":
                mb,

            "measured_single_candidate_seconds":
                sec,

            "measured_profiles_per_second":
                float(mb / sec),

            "microbatches_per_epoch":
                int(n_micro),

            "projected_seconds_per_epoch":
                epoch_sec,

            "projected_hours_per_epoch":
                float(epoch_sec / 3600.0),

            "projected_days_for_800_epochs":
                float(
                    epoch_sec
                    * TARGET_EPOCHS
                    / 86400.0
                ),

            "projection_semantics":
                "diagnostic only; not a runtime promise; excludes optimizer, "
                "checkpoint, data-loading, and full-epoch scheduling effects",
        }

    all_no_optimizer = all(
        rec.get("optimizer_created") is False
        for rec in candidate_results
    )

    all_no_update = all(
        rec.get("weight_update") is False
        for rec in candidate_results
    )

    all_reuse_exact_graph = all(
        rec.get("scientific_graph_changed_from_B2S") is False
        for rec in candidate_results
    )

    successful_finite_gradients = all(
        rec.get("parameter_gradients_finite") is True
        for rec in candidate_results
        if rec.get("success")
    )

    successful_weights_unchanged = all(
        rec.get("weights_exactly_unchanged") is True
        for rec in candidate_results
        if rec.get("success")
    )

    successful_checkpoint_unchanged = all(
        rec.get("checkpoint_SHA_unchanged") is True
        for rec in candidate_results
        if rec.get("success")
    )

    results_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "EXTENDED_NO_UPDATE_CORRECTED_RESIDUAL_THROUGHPUT_MEMORY_BENCHMARK",

        "exact_reused_implementation": {
            "B2S_source_sha256":
                B2S_SOURCE_SHA,

            "mutation":
                "operational candidate list only",

            "scientific_graph_changed":
                False,
        },

        "candidate_microbatches":
            CANDIDATES,

        "candidate_results":
            candidate_results,

        "successful_microbatches":
            successful,

        "largest_successful_tested_microbatch":
            selected,

        "training_split": {
            "dataset_profiles":
                n_profiles,
            "train_profiles":
                n_train,
            "logical_batch":
                LOGICAL_BATCH,
            "target_epochs":
                TARGET_EPOCHS,
        },

        "diagnostic_full_run_projections":
            projections,

        "selection_rule":
            "largest actually tested candidate completing finite forward, "
            "corrected residual, complete backward, XPU synchronization, finite "
            "parameter gradients, exact no-weight-change and checkpoint-SHA gates",

        "do_not_infer_above_largest_tested_success":
            True,

        "optimizer_created":
            False,

        "optimizer_step":
            False,

        "weight_update":
            False,

        "checkpoint_mutated":
            False,

        "scientific_settings_changed":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    RESULTS.write_text(
        json.dumps(results_payload, indent=2),
        encoding="utf-8",
    )

    decision = {
        "milestone":
            MILESTONE,

        "largest_successful_tested_microbatch":
            selected,

        "successful_microbatches":
            successful,

        "failed_candidates":
            [
                {
                    "microbatch": int(rec["microbatch"]),
                    "failure_class": rec.get("failure_class"),
                    "error": rec.get("error"),
                }
                for rec in candidate_results
                if not rec.get("success")
            ],

        "diagnostic_projections":
            projections,

        "operational_microbatch_finalized_for_training":
            False,

        "reason_not_finalized":
            "B2U binds the extended measured behavior. A separate B2V execution-"
            "contract freeze must interpret throughput/memory results and explicitly "
            "select the COMP-XPU-005 operational microbatch.",

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    DECISION.write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )

    gates.update({
        "all_four_extended_candidates_attempted":
            len(candidate_results)
            == len(CANDIDATES),

        "all_extended_candidates_recorded":
            {
                int(rec["microbatch"])
                for rec in candidate_results
            }
            == set(CANDIDATES),

        "at_least_one_extended_candidate_success":
            selected is not None,

        "all_children_report_no_optimizer":
            bool(all_no_optimizer),

        "all_children_report_no_weight_update":
            bool(all_no_update),

        "all_children_reuse_exact_B2S_graph":
            bool(all_reuse_exact_graph),

        "successful_gradients_finite":
            bool(successful_finite_gradients),

        "successful_weights_unchanged":
            bool(successful_weights_unchanged),

        "successful_checkpoint_SHA_unchanged":
            bool(successful_checkpoint_unchanged),

        "COMP004_checkpoint_still_unchanged":
            sha256(COMP004_CHECKPOINT)
            == COMP004_CHECKPOINT_SHA,

        "results_written":
            RESULTS.exists()
            and RESULTS.stat().st_size > 0,

        "decision_written":
            DECISION.exists()
            and DECISION.stat().st_size > 0,

        "parent_no_optimizer":
            True,

        "no_optimizer_step":
            True,

        "no_weight_update":
            True,

        "no_OOD":
            True,

        "no_TOF":
            True,

        "no_scientific_numeric_threshold":
            True,

        "COMP005_training_not_authorized":
            True,

        "B3_not_authorized":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_BACKWARD_THROUGHPUT_MEMORY_BENCHMARK_COMPLETE_"
        "EXACT_CERTIFIED_B2S_CREATE_GRAPH_TRUE_RECURRENT_DERIVATIVE_AND_TOTAL_LOSS_GRAPH_REUSED_"
        "EXTENDED_MICROBATCHES_32_64_128_256_ATTEMPTED_SUBPROCESS_ISOLATED_"
        "LARGEST_ACTUALLY_SUCCESSFUL_TESTED_MICROBATCH_AND_DIAGNOSTIC_FULL_RUN_PROJECTIONS_BOUND_"
        "FINITE_GRADIENTS_AND_NO_WEIGHT_CHANGE_CONFIRMED_FOR_SUCCESSFUL_CANDIDATES_"
        "NO_OPTIMIZER_NO_OPTIMIZER_STEP_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
        "B2V_EXECUTION_CONTRACT_FREEZE_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2U_XPU_EXTENDED_BENCHMARK_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "results_sha256":
            sha256(RESULTS),

        "decision_sha256":
            sha256(DECISION),

        "successful_microbatches":
            successful,

        "largest_successful_tested_microbatch":
            selected,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2V-XPU — interpret B2U throughput/memory measurements, "
                "freeze the final operational microbatch and corrected COMP-XPU-005 "
                "execution contract before fresh training"
                if ok else
                "V16E-1B2U-R1 — diagnose extended-throughput benchmark gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nEXTENDED SELECTION")
    print("  successful candidates:", successful)
    print("  largest successful tested microbatch:", selected)

    if projections:
        print("\nDIAGNOSTIC FULL-RUN PROJECTIONS")
        for mb in sorted(
            (int(k) for k in projections.keys())
        ):
            rec = projections[str(mb)]
            print(
                f"  mb={mb:3d} "
                f"| throughput={rec['measured_profiles_per_second']:.3f} profiles/s "
                f"| proj={rec['projected_hours_per_epoch']:.3f} h/epoch "
                f"| {rec['projected_days_for_800_epochs']:.3f} d/800ep"
            )
        print("  NOTE: projections are diagnostic, not runtime promises.")

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Results :", sha256(RESULTS))
    print("  Decision:", sha256(DECISION))
    print("  Summary :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--candidate",
        type=int,
        default=None,
    )

    ap.add_argument(
        "--result-path",
        type=Path,
        default=None,
    )

    return ap.parse_args()


def main():
    args = parse_args()

    if args.candidate is not None:
        if args.result_path is None:
            raise RuntimeError(
                "--result-path is required with --candidate"
            )

        rc = child_main(
            args.candidate,
            args.result_path,
        )
        sys.exit(rc)

    parent_main()


if __name__ == "__main__":
    main()
