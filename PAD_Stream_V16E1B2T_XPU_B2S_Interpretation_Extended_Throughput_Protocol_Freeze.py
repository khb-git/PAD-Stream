#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2T-XPU
B2S Feasibility Interpretation + Extended Throughput Protocol Freeze

Purpose
-------
Freeze the correct operational interpretation of V16E-1B2S before any
COMP-XPU-005 training runner is authorized.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

B2S proved
----------
* Exact corrected-residual create_graph=True backward is executable on Intel XPU.
* Candidate microbatches 1, 2, 4, 8, 16 all passed.
* Parameter gradients were finite.
* No optimizer object or optimizer step was used.
* Frozen COMP-XPU-004 weights/checkpoint remained unchanged.

But B2S did NOT establish the practical microbatch ceiling:
* every tested candidate passed;
* the largest tested candidate (16) therefore represents a protocol boundary,
  not a hardware/graph failure boundary;
* throughput improved strongly as candidate size increased;
* candidate 16 used only the measured B2S peak-memory amount recorded in the
  frozen results artifact;
* a naive full-run projection from the single B2S candidate-16 timing is
  operationally large.

Therefore B2T does NOT freeze microbatch=16 as the final COMP-XPU-005 training
microbatch and does NOT authorize the 800-epoch run.

Instead B2T authorizes one further NO-OPTIMIZER / NO-WEIGHT-UPDATE operational
benchmark:

    V16E-1B2U-XPU

with continuation candidates:

    32, 64, 128, 256

These are an operational power-of-two continuation of the already frozen
1,2,4,8,16 sequence. They introduce no scientific change.

Each candidate must run in its own subprocess / XPU context. OOM/device-loss
is an allowed operational result and must not mutate prior artifacts.

B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2T-XPU"

# =============================================================================
# Frozen authorities
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

# B2R
B2R_SOURCE = (
    R
    / "PAD_Stream_V16E1B2R_XPU_B2Q_Interpretation_Corrected_Stage2_Feasibility_Protocol_Freeze.py"
)
B2R_SOURCE_SHA = "a80f0be6d98ebfaf29b609b04cfaef96ff42c68786ab9a057c1ebb7822403269"

B2R_DIR = (
    R / "output"
    / "V16_E1B2R_XPU_B2Q_INTERPRETATION_CORRECTED_STAGE2_PROTOCOL"
)
B2R_PROSPECTIVE = B2R_DIR / "V16E1B2R_COMP_XPU_005_Prospective_Scientific_Protocol.json"
B2R_FEASIBILITY = B2R_DIR / "V16E1B2R_B2S_Autograd_Backward_Feasibility_Protocol.json"
B2R_SUMMARY = B2R_DIR / "PAD_Stream_V16E1B2R_XPU_Summary.json"

B2R_PROSPECTIVE_SHA = "7dfdc867086a2229832965be1496cdd8bc4415d239e5bef371f8a472fda8988b"
B2R_FEASIBILITY_SHA = "24cb9c45e9416160a827fb14f4a1408a4e6c0bd3d4f9aad1af30bae2f93ac8c9"
B2R_SUMMARY_SHA = "8e16e592c832a71ec14c85ae5eb9a31201ce99f31e8a99b8e8af5510600de4db"

# B2S
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

EXPECTED_B2S_STATUS = (
    "V16E1B2S_XPU_CORRECTED_CONSERVATIVE_STAGE2_RESIDUAL_BACKWARD_FEASIBILITY_COMPLETE_"
    "CREATE_GRAPH_TRUE_LOCAL_RECURRENT_XI_TD_XDSTAR_DERIVATIVES_COMPLETE_FROZEN_TOTAL_LOSS_BACKWARD_"
    "INTEL_XPU_CANDIDATES_1_2_4_8_16_ATTEMPTED_LARGEST_SUCCESSFUL_TESTED_MICROBATCH_BOUND_"
    "FINITE_PARAMETER_GRADIENTS_CONFIRMED_NO_OPTIMIZER_NO_OPTIMIZER_STEP_NO_WEIGHT_CHANGE_"
    "COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
    "B2T_OPERATIONAL_TRAINING_PROTOCOL_FREEZE_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2T_XPU_B2S_INTERPRETATION_EXTENDED_THROUGHPUT_PROTOCOL"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2T_B2S_Operational_Interpretation.json"
PROTOCOL = OUT / "V16E1B2T_B2U_Extended_Throughput_Protocol.json"
HANDOFF = OUT / "V16E1B2T_B2U_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2T_XPU_Summary.json"

TESTED = [1, 2, 4, 8, 16]
EXTENDED = [32, 64, 128, 256]
LOGICAL_BATCH = 8192
TARGET_EPOCHS = 800


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


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def microbatches_per_epoch(n_train: int, logical_batch: int, microbatch: int) -> int:
    total = 0
    for b0 in range(0, n_train, logical_batch):
        chunk = min(logical_batch, n_train - b0)
        total += int(math.ceil(chunk / microbatch))
    return total


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2T-XPU")
    print("B2S Feasibility Interpretation + Extended Throughput Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2T summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),

        "B2R_source_SHA_exact":
            exact(B2R_SOURCE, B2R_SOURCE_SHA),

        "B2R_prospective_SHA_exact":
            exact(B2R_PROSPECTIVE, B2R_PROSPECTIVE_SHA),

        "B2R_feasibility_SHA_exact":
            exact(B2R_FEASIBILITY, B2R_FEASIBILITY_SHA),

        "B2R_summary_SHA_exact":
            exact(B2R_SUMMARY, B2R_SUMMARY_SHA),

        "B2S_source_SHA_exact":
            exact(B2S_SOURCE, B2S_SOURCE_SHA),

        "B2S_results_SHA_exact":
            exact(B2S_RESULTS, B2S_RESULTS_SHA),

        "B2S_summary_SHA_exact":
            exact(B2S_SUMMARY, B2S_SUMMARY_SHA),
    }

    b2s = read_json(B2S_RESULTS) if B2S_RESULTS.exists() else {}
    b2s_summary = read_json(B2S_SUMMARY) if B2S_SUMMARY.exists() else {}
    b2r_prospective = (
        read_json(B2R_PROSPECTIVE)
        if B2R_PROSPECTIVE.exists()
        else {}
    )

    gates.update({
        "B2S_status_exact":
            b2s_summary.get("status") == EXPECTED_B2S_STATUS,

        "B2S_COMP005_training_false":
            b2s_summary.get("COMP_XPU_005_full_training_authorized") is False,

        "B2S_B3_false":
            b2s_summary.get("B3_authorized") is False,

        "B2S_tested_candidates_exact":
            b2s.get("candidate_microbatches") == TESTED,

        "B2S_all_candidates_successful":
            b2s.get("successful_microbatches") == TESTED,

        "B2S_largest_successful_16":
            b2s.get("largest_successful_tested_microbatch") == 16,

        "B2S_optimizer_false":
            b2s.get("optimizer_created") is False,

        "B2S_optimizer_step_false":
            b2s.get("optimizer_step") is False,

        "B2S_weight_update_false":
            b2s.get("weight_update") is False,

        "B2S_checkpoint_mutated_false":
            b2s.get("checkpoint_mutated") is False,

        "B2R_epochs_800":
            (
                b2r_prospective
                .get("must_remain_identical_to_COMP_XPU_004", {})
                .get("epochs")
                == TARGET_EPOCHS
            ),

        "B2R_logical_batch_8192":
            (
                b2r_prospective
                .get("must_remain_identical_to_COMP_XPU_004", {})
                .get("logical_batch")
                == LOGICAL_BATCH
            ),
    })

    candidate_rows = b2s.get("candidate_results", [])

    by_mb = {
        int(rec["microbatch"]): rec
        for rec in candidate_rows
        if "microbatch" in rec
    }

    gates.update({
        "all_candidate_records_present":
            set(by_mb.keys()) == set(TESTED),

        "all_candidate_times_finite":
            all(
                finite(by_mb[m].get("forward_residual_backward_seconds"))
                for m in TESTED
            ),

        "all_candidate_gradients_finite":
            all(
                by_mb[m].get("parameter_gradients_finite") is True
                for m in TESTED
            ),

        "all_candidate_weights_unchanged":
            all(
                by_mb[m].get("weights_exactly_unchanged") is True
                for m in TESTED
            ),

        "all_candidate_checkpoint_SHA_unchanged":
            all(
                by_mb[m].get("checkpoint_SHA_unchanged") is True
                for m in TESTED
            ),
    })

    print("AUTHORITY / B2S INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2T blocked by authority or B2S interpretation mismatch."
        )

    d = np.load(DATASET)
    n_profiles = int(len(d["p11"]))
    n_train = int(0.8 * n_profiles)

    mb16 = by_mb[16]
    t16 = float(mb16["forward_residual_backward_seconds"])
    peak16 = mb16.get("peak_xpu_memory_bytes")

    mb_per_epoch_16 = microbatches_per_epoch(
        n_train=n_train,
        logical_batch=LOGICAL_BATCH,
        microbatch=16,
    )

    projected_epoch_seconds_16 = (
        mb_per_epoch_16 * t16
    )

    projected_800_seconds_16 = (
        projected_epoch_seconds_16
        * TARGET_EPOCHS
    )

    throughput_rows = []

    for mb in TESTED:
        rec = by_mb[mb]
        sec = float(rec["forward_residual_backward_seconds"])

        throughput_rows.append({
            "microbatch":
                mb,

            "measured_backward_path_seconds":
                sec,

            "measured_profiles_per_second":
                float(mb / sec),

            "peak_xpu_memory_bytes":
                rec.get("peak_xpu_memory_bytes"),

            "success":
                bool(rec.get("success")),
        })

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2S_MEMORY_FEASIBILITY_VS_FULL_RUN_PRACTICALITY_INTERPRETATION",

        "B2S_certified_result":
            {
                "all_tested_microbatches_passed":
                    TESTED,

                "largest_successful_tested_microbatch":
                    16,

                "meaning":
                    "16 is the largest value permitted by the B2R/B2S candidate set; "
                    "it is not an observed XPU or graph failure boundary.",
            },

        "measured_throughput":
            throughput_rows,

        "candidate_16_projection": {
            "dataset_profiles":
                n_profiles,

            "frozen_train_profiles":
                n_train,

            "logical_batch":
                LOGICAL_BATCH,

            "microbatch":
                16,

            "measured_single_candidate_seconds":
                t16,

            "microbatches_per_epoch":
                mb_per_epoch_16,

            "projected_seconds_per_epoch_from_single_B2S_measurement":
                projected_epoch_seconds_16,

            "projected_hours_per_epoch_from_single_B2S_measurement":
                float(projected_epoch_seconds_16 / 3600.0),

            "projected_days_for_800_epochs_from_single_B2S_measurement":
                float(projected_800_seconds_16 / 86400.0),

            "peak_xpu_memory_bytes_observed_in_B2S":
                peak16,

            "interpretation":
                "Projection is an operational diagnostic, not a runtime promise. "
                "It excludes optimizer/checkpoint overhead and is used only to show "
                "that memory feasibility at microbatch 16 is not sufficient evidence "
                "for a practical 800-epoch execution contract.",
        },

        "decision":
            "DO_NOT_FREEZE_MICROBATCH_16_AS_FINAL_TRAINING_MICROBATCH",

        "reason":
            "B2S found no memory/graph ceiling through 16 and measured throughput "
            "continued to improve strongly with candidate size. A larger no-update "
            "benchmark is warranted before locking the operational training contract.",

        "scientific_protocol_changed":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    INTERPRETATION.write_text(
        json.dumps(interpretation, indent=2),
        encoding="utf-8",
    )

    protocol = {
        "milestone":
            MILESTONE,

        "authorized_next_milestone":
            "V16E-1B2U-XPU",

        "classification":
            "EXTENDED_NO_OPTIMIZER_CORRECTED_RESIDUAL_THROUGHPUT_AND_MEMORY_BENCHMARK",

        "scientific_model":
            "unchanged prospective V16E-BLREP-COMP-XPU-005",

        "baseline_checkpoint":
            {
                "experiment":
                    "V16E-BLREP-COMP-XPU-004",
                "sha256":
                    COMP004_CHECKPOINT_SHA,
            },

        "exact_graph":
            "same corrected conservative Stage-2 forward + create_graph=True "
            "local recurrent derivatives + complete total loss backward as B2S",

        "candidate_microbatches":
            EXTENDED,

        "candidate_rationale":
            "power-of-two continuation of the already tested 1,2,4,8,16 sequence; "
            "operational only, no scientific parameter change",

        "execution_isolation":
            "each candidate in a fresh subprocess/XPU context",

        "allowed_candidate_outcomes":
            [
                "PASS",
                "OOM",
                "DEVICE_LOST",
                "RUNTIME_ERROR",
            ],

        "selection_rule":
            "Select the largest tested candidate that completes finite forward, "
            "corrected residual, complete backward, XPU synchronization, finite "
            "parameter gradients, exact no-weight-change, and checkpoint-SHA gates. "
            "Do not infer viability above the largest tested success.",

        "benchmark_requirements":
            [
                "wall time",
                "profiles per second",
                "peak XPU memory if available",
                "finite corrected residual",
                "finite total loss",
                "finite parameter gradients",
                "nonzero parameter gradients",
                "weights unchanged",
                "checkpoint SHA unchanged",
                "no optimizer object",
                "no optimizer step",
            ],

        "scientific_firewall":
            {
                "training":
                    False,
                "optimizer":
                    False,
                "optimizer_step":
                    False,
                "weight_update":
                    False,
                "scientific_settings_changed":
                    False,
                "OOD":
                    False,
                "TOF":
                    False,
                "B3_authorized":
                    False,
            },

        "full_COMP_XPU_005_training_authorized":
            False,
    }

    PROTOCOL.write_text(
        json.dumps(protocol, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2T-XPU — B2U Extended Throughput Handoff\n\n"
        "## Certified B2S result\n\n"
        "Microbatches 1, 2, 4, 8, and 16 all execute the exact corrected-residual "
        "create_graph=True backward on Intel XPU without weight mutation.\n\n"
        "## Why microbatch 16 is not frozen as the final training value\n\n"
        "No tested candidate failed, so B2S did not find the operational ceiling. "
        "The candidate-16 timing projected through the frozen 11,520-profile training "
        "split and logical batch 8192 is operationally large for an 800-epoch run. "
        "That projection is diagnostic only, not a runtime promise.\n\n"
        "## B2U\n\n"
        "Benchmark 32, 64, 128, and 256 with the exact B2S graph. Each candidate "
        "must run in an isolated subprocess. OOM/device loss is an acceptable "
        "measurement outcome. No optimizer and no weight update are permitted.\n\n"
        "After B2U, freeze the largest actually tested successful value and then "
        "decide whether a full COMP-XPU-005 execution contract is practical.\n\n"
        "B3 remains blocked.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,

        "extended_protocol_written":
            PROTOCOL.exists()
            and PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "microbatch16_not_falsely_promoted_to_hardware_ceiling":
            True,

        "extended_candidates_bound":
            EXTENDED == [32, 64, 128, 256],

        "COMP005_training_not_authorized":
            True,

        "B2U_authorized":
            True,

        "B3_not_authorized":
            True,

        "no_training":
            True,

        "no_optimizer":
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
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2T_XPU_B2S_FEASIBILITY_INTERPRETATION_AND_EXTENDED_THROUGHPUT_PROTOCOL_FROZEN_"
        "CORRECTED_RESIDUAL_BACKWARD_CONFIRMED_FOR_MICROBATCHES_1_2_4_8_16_"
        "MICROBATCH_16_CLASSIFIED_AS_LARGEST_PROTOCOL_TEST_NOT_HARDWARE_CEILING_"
        "NAIVE_FULL_RUN_TIMING_PROJECTION_BOUND_AS_OPERATIONAL_DIAGNOSTIC_ONLY_"
        "COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_"
        "B2U_EXTENDED_MICROBATCHES_32_64_128_256_NO_UPDATE_BENCHMARK_AUTHORIZED_"
        "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2T_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "interpretation_sha256":
            sha256(INTERPRETATION),

        "protocol_sha256":
            sha256(PROTOCOL),

        "handoff_sha256":
            sha256(HANDOFF),

        "B2S_largest_successful_tested_microbatch":
            16,

        "B2S_microbatch16_projected_hours_per_epoch":
            float(projected_epoch_seconds_16 / 3600.0),

        "B2S_microbatch16_projected_days_for_800_epochs":
            float(projected_800_seconds_16 / 86400.0),

        "authorized_extended_candidates":
            EXTENDED,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B2U_authorized":
            bool(ok),

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2U-XPU — subprocess-isolated corrected-residual backward "
                "throughput/memory benchmark for microbatches 32,64,128,256; "
                "no optimizer and no weight update"
                if ok else
                "V16E-1B2T-R1 — diagnose B2S interpretation/protocol gate failure"
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

    print("\nB2S OPERATIONAL INTERPRETATION")
    print("  frozen train profiles           :", n_train)
    print("  logical batch                   :", LOGICAL_BATCH)
    print("  B2S candidate-16 measured time  :", f"{t16:.3f} s")
    print("  microbatches/epoch at mb=16     :", mb_per_epoch_16)
    print(
        "  projected hours/epoch at mb=16 :",
        f"{projected_epoch_seconds_16 / 3600.0:.3f}",
    )
    print(
        "  projected days/800 epochs       :",
        f"{projected_800_seconds_16 / 86400.0:.3f}",
    )
    print("  NOTE: projection is diagnostic, not a runtime promise.")

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Interpretation:", sha256(INTERPRETATION))
    print("  Protocol      :", sha256(PROTOCOL))
    print("  Handoff       :", sha256(HANDOFF))
    print("  Summary       :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
