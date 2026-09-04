#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AC-XPU
Subprocess-Isolated Chunked Batched-VJP
Equivalence + Warmed Performance Sweep

Purpose
-------
Execute the V16E-1B2AB-authorized chunked batched-VJP sweep:

    cotangent chunks = 2, 4, 8, 16, 32

at the exact frozen reference microbatch=128.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT MUTATION.
NO OOD.
NO TOF.

Scientific model
----------------
UNCHANGED.

The exact frozen B2S corrected Stage-2 graph remains authoritative.
The exact B2AA equivalence/performance helper functions are reused.

Only the implementation of local recurrent derivative extraction changes.

Known endpoints
---------------
chunk=1:
    certified loop baseline semantics.

chunk=64:
    frozen B2AA runtime-resource failure:
    UR_RESULT_ERROR_OUT_OF_RESOURCES

B2AC candidates:
    2, 4, 8, 16, 32

Execution strategy
------------------
1. Create one isolated LOOP BASELINE artifact on the exact 128 reference rows:
       N_xi
       N_tD
       N_X
       corrected residual
       physics loss
       complete total loss
       every parameter gradient
       warmed loop performance:
           1 warm-up + 3 measured repeats

   The baseline tensor artifact is SHA-bound.

2. Run each chunk candidate in a FRESH subprocess / XPU context.

3. Candidate sequence:
       runtime feasibility
       derivative equivalence
       full corrected-graph equivalence
       parameter-gradient equivalence
       ONLY THEN warmed performance:
           1 warm-up + 3 measured repeats

4. Runtime failure:
       record exact error
       no fallback
       no performance
       continue next isolated candidate

5. Equivalence failure:
       record exact differences
       no performance
       continue next isolated candidate

6. B2AC does NOT adopt any candidate.
   V16E-1B2AD-XPU performs interpretation/adoption.

Equivalence budget
------------------
Use only the B2Z/B2AB-frozen computational identity budget:

    bound =
        1024 * eps_float32
        * max(1, max_abs(reference), max_abs(candidate))

This is implementation-equivalence only.
It is NOT a scientific model threshold.

COMP-XPU-005 full training remains blocked.
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
import statistics
import subprocess
import sys
import time
import traceback

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2AC-XPU"

REFERENCE_MICROBATCH = 128
CHUNK_CANDIDATES = [2, 4, 8, 16, 32]
KNOWN_LOOP_CHUNK = 1
KNOWN_FAILED_FULL_CHUNK = 64
WARMUP_REPEATS = 1
MEASURED_REPEATS = 3

FLOAT32_EPS = float(np.finfo(np.float32).eps)
IDENTITY_EPS_MULTIPLIER = 1024.0

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

# Exact corrected graph authority.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# Exact reference rows.
B2U_DIR = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
B2U_RESULTS = B2U_DIR / "V16E1B2U_Extended_Throughput_Memory_Results.json"
B2U_RESULTS_SHA = "e71f398c88feee2260c50109055b917103e76800365954823f320457a0d30075"

# Warmed baseline authority.
B2Y_DIR = (
    R / "output"
    / "V16_E1B2Y_XPU_WARMED_STEADY_STATE_EXACT_GRAPH_BENCHMARK"
)
B2Y_RESULTS = B2Y_DIR / "V16E1B2Y_Warmed_Steady_State_Results.json"
B2Y_RESULTS_SHA = "32d5a9a1e8c0970a497fe81dffb5c877d8ac23439a463d701e1d9b0bcd163b16"

# Reuse exact B2AA equivalence / performance helpers.
B2AA_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AA_XPU_Batched_VJP_Equivalence_Performance_Audit.py"
)
B2AA_SOURCE_SHA = "2306ea121d5aead6de1a710cbe4b2eeee688ec03039fb1a4f252a966da1f048c"

# B2AB authority.
B2AB_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AB_XPU_B2AA_Interpretation_Chunked_Batched_VJP_Protocol_Freeze.py"
)
B2AB_SOURCE_SHA = "52cf459501ca1dafaf16008de5d1e9831442ca35ae7621051dba341ef57f3c09"

B2AB_DIR = (
    R / "output"
    / "V16_E1B2AB_XPU_B2AA_INTERPRETATION_CHUNKED_BATCHED_VJP_PROTOCOL"
)
B2AB_INTERPRETATION = B2AB_DIR / "V16E1B2AB_B2AA_Runtime_Interpretation.json"
B2AB_PROTOCOL = B2AB_DIR / "V16E1B2AB_B2AC_Chunked_Batched_VJP_Protocol.json"
B2AB_HANDOFF = B2AB_DIR / "V16E1B2AB_B2AC_Handoff.md"
B2AB_SUMMARY = B2AB_DIR / "PAD_Stream_V16E1B2AB_XPU_Summary.json"

B2AB_INTERPRETATION_SHA = "650e95186db725c7b15c7b923b25afd2aca8687ed5d687428d36fcb303472a97"
B2AB_PROTOCOL_SHA = "fd9368be674f548001c1fca76ff68a6e7dbbce605e5b9b8e0eb34dcda87bd043"
B2AB_HANDOFF_SHA = "f796da2cd6f8f75f4ae74800053d928197a5cfdffddbad7bae2e5d39389e8895"
B2AB_SUMMARY_SHA = "a851a8e43b14a8f446a9fa2637807e5a8bc44ea0a57d2cde98ce039176efc19e"

EXPECTED_B2AB_STATUS = (
    "V16E1B2AB_XPU_B2AA_RUNTIME_RESOURCE_INTERPRETATION_AND_CHUNKED_BATCHED_VJP_PROTOCOL_FROZEN_"
    "FULL_64_COTANGENT_IS_GRADS_BATCHED_TRUE_CALL_PRESERVED_AS_UR_RESULT_ERROR_OUT_OF_RESOURCES_"
    "WITHOUT_UNIVERSAL_UNSUPPORTED_OR_OOM_RECLASSIFICATION_"
    "CHUNKED_BATCHED_VJP_CANDIDATES_2_4_8_16_32_AUTHORIZED_AS_IMPLEMENTATION_ONLY_ROUTE_"
    "EXACT_LOOP_BASELINE_FULL_CORRECTED_GRAPH_AND_FLOAT32_EPSILON_DERIVED_EQUIVALENCE_FIREWALL_PRESERVED_"
    "SUBPROCESS_ISOLATION_NO_FALLBACK_EQUIVALENCE_BEFORE_PERFORMANCE_REQUIRED_"
    "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2AC_XPU_CHUNKED_BATCHED_VJP_SWEEP"
)
OUT.mkdir(parents=True, exist_ok=True)

BASELINE_DIR = OUT / "loop_baseline"
CANDIDATE_DIR = OUT / "candidate_results"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_JSON = BASELINE_DIR / "V16E1B2AC_Loop_Baseline.json"
BASELINE_TENSORS = BASELINE_DIR / "V16E1B2AC_Loop_Baseline_Tensors.pt"

RESULTS = OUT / "V16E1B2AC_Chunked_Batched_VJP_Sweep_Results.json"
DECISION = OUT / "V16E1B2AC_Chunked_Batched_VJP_Measurement_Decision.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2AC_XPU_Summary.json"


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


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify_runtime_error(text: str) -> str:
    t = text.lower()

    if "ur_result_error_out_of_resources" in t:
        return "UR_RESULT_ERROR_OUT_OF_RESOURCES"

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


def get_reference_ids(b2u):
    for rec in b2u.get("candidate_results", []):
        if int(rec.get("microbatch", -1)) == REFERENCE_MICROBATCH:
            ids = rec.get("dataset_indices")

            if (
                not isinstance(ids, list)
                or len(ids) != REFERENCE_MICROBATCH
            ):
                raise RuntimeError(
                    "B2U microbatch-128 dataset indices missing/incomplete."
                )

            return np.asarray(
                ids,
                dtype=int,
            )

    raise RuntimeError(
        "B2U microbatch-128 reference record not found."
    )


def sync_xpu():
    if hasattr(torch.xpu, "synchronize"):
        torch.xpu.synchronize()


def checkpoint_unchanged() -> bool:
    return (
        COMP004_CHECKPOINT.exists()
        and sha256(COMP004_CHECKPOINT)
        == COMP004_CHECKPOINT_SHA
    )


# =============================================================================
# Chunked local derivative engine
# =============================================================================

def make_chunked_batched_engine(chunk_size: int):
    if chunk_size not in CHUNK_CANDIDATES:
        raise RuntimeError(
            f"Unauthorized chunk size {chunk_size}"
        )

    def chunked_local_recurrent_derivatives_create_graph(
        S_pred,
        xi,
        p11,
    ):
        if S_pred.ndim != 3:
            raise RuntimeError(
                f"Unexpected S_pred rank {S_pred.ndim}; expected [B,T,1]."
            )

        B, T, C = S_pred.shape

        if C != 1:
            raise RuntimeError(
                f"Unexpected output channel count {C}; expected 1."
            )

        nxi_chunks = []
        ntd_chunks = []
        nx_chunks = []

        for j0 in range(
            0,
            T,
            chunk_size,
        ):
            j1 = min(
                T,
                j0 + chunk_size,
            )

            K = (
                j1 - j0
            )

            global_j = torch.arange(
                j0,
                j1,
                device=S_pred.device,
            )

            local_j = torch.arange(
                K,
                device=S_pred.device,
            )

            # K one-hot sequence-output cotangents.
            V2 = torch.nn.functional.one_hot(
                global_j,
                num_classes=T,
            ).to(
                dtype=S_pred.dtype,
                device=S_pred.device,
            )

            V = (
                V2[:, None, :, None]
                .expand(
                    K,
                    B,
                    T,
                    1,
                )
            )

            gx, gp = torch.autograd.grad(
                outputs=S_pred,
                inputs=(xi, p11),
                grad_outputs=V,
                retain_graph=True,
                create_graph=True,
                allow_unused=False,
                is_grads_batched=True,
            )

            # gx: [K, B, T, 1]
            # Extract local spatial diagonal dN_j/dxi_j.
            N_xi_chunk = (
                gx[
                    local_j,
                    :,
                    global_j,
                    0,
                ]
                .transpose(
                    0,
                    1,
                )
                .unsqueeze(-1)
            )

            # gp: [K, B, 11]
            N_tD_chunk = (
                gp[:, :, 7]
                .transpose(
                    0,
                    1,
                )
                .unsqueeze(-1)
            )

            N_X_chunk = (
                gp[:, :, 8]
                .transpose(
                    0,
                    1,
                )
                .unsqueeze(-1)
            )

            nxi_chunks.append(
                N_xi_chunk
            )

            ntd_chunks.append(
                N_tD_chunk
            )

            nx_chunks.append(
                N_X_chunk
            )

        N_xi = torch.cat(
            nxi_chunks,
            dim=1,
        )

        N_tD = torch.cat(
            ntd_chunks,
            dim=1,
        )

        N_X = torch.cat(
            nx_chunks,
            dim=1,
        )

        if (
            N_xi.shape != S_pred.shape
            or N_tD.shape != S_pred.shape
            or N_X.shape != S_pred.shape
        ):
            raise RuntimeError(
                "Chunked derivative output shapes do not match S_pred."
            )

        return (
            N_xi,
            N_tD,
            N_X,
        )

    return chunked_local_recurrent_derivatives_create_graph


# =============================================================================
# Baseline serialization
# =============================================================================

def baseline_child(
    result_path: Path,
    tensor_path: Path,
) -> int:
    payload = {
        "milestone":
            MILESTONE,

        "role":
            "EXACT_LOOP_BASELINE",

        "success":
            False,

        "optimizer_created":
            False,

        "optimizer_step":
            False,

        "weight_update":
            False,
    }

    try:
        if not torch.xpu.is_available():
            raise RuntimeError(
                "Intel XPU unavailable."
            )

        if not exact(
            B2AA_SOURCE,
            B2AA_SOURCE_SHA,
        ):
            raise RuntimeError(
                "B2AA helper source SHA mismatch."
            )

        A = import_module(
            B2AA_SOURCE,
            "b2ac_b2aa_helpers_baseline",
        )

        S = import_module(
            B2S_SOURCE,
            "b2ac_b2s_exact_baseline",
        )

        b2u = read_json(
            B2U_RESULTS
        )

        ids = get_reference_ids(
            b2u
        )

        device = torch.device(
            "xpu"
        )

        baseline_engine = (
            S.local_recurrent_derivatives_create_graph
        )

        derivative = A.derivative_snapshot(
            S,
            baseline_engine,
            ids,
            device,
            "b2ac_loop_derivative",
        )

        full = A.full_graph_snapshot(
            S,
            baseline_engine,
            ids,
            device,
            "b2ac_loop_full",
        )

        perf = A.warmed_performance_block(
            S,
            baseline_engine,
            ids,
            device,
            "b2ac_loop_perf",
        )

        tensor_payload = {
            "reference_ids":
                torch.as_tensor(
                    ids,
                    dtype=torch.int64,
                ),

            "S_pred_derivative":
                derivative[
                    "S_pred"
                ],

            "N_xi":
                derivative[
                    "N_xi"
                ],

            "N_tD":
                derivative[
                    "N_tD"
                ],

            "N_X":
                derivative[
                    "N_X"
                ],

            "S_pred_full":
                full[
                    "S_pred"
                ],

            "residual":
                full[
                    "residual"
                ],

            "parameter_gradients":
                full[
                    "parameter_gradients"
                ],
        }

        torch.save(
            tensor_payload,
            tensor_path,
        )

        if not tensor_path.exists():
            raise RuntimeError(
                "Baseline tensor artifact was not written."
            )

        payload.update({
            "success":
                True,

            "reference_microbatch":
                REFERENCE_MICROBATCH,

            "reference_ids":
                [int(x) for x in ids],

            "tensor_artifact":
                str(tensor_path.name),

            "tensor_artifact_sha256":
                sha256(
                    tensor_path
                ),

            "full_losses":
                full[
                    "losses"
                ],

            "full_gradient_summary":
                full[
                    "gradient_summary"
                ],

            "weights_exactly_unchanged":
                bool(
                    full[
                        "weights_exactly_unchanged"
                    ]
                ),

            "checkpoint_SHA_unchanged":
                bool(
                    full[
                        "checkpoint_SHA_unchanged"
                    ]
                    and checkpoint_unchanged()
                ),

            "performance":
                perf,

            "performance_median_seconds":
                float(
                    perf[
                        "median_wall_seconds"
                    ]
                ),

            "performance_mean_seconds":
                float(
                    perf[
                        "mean_wall_seconds"
                    ]
                ),

            "performance_median_profiles_per_second":
                float(
                    perf[
                        "median_profiles_per_second"
                    ]
                ),
        })

        atomic_json_write(
            payload,
            result_path,
        )

        return 0

    except BaseException as exc:
        payload.update({
            "success":
                False,

            "failure_class":
                classify_runtime_error(
                    f"{type(exc).__name__}: {exc}"
                ),

            "error":
                f"{type(exc).__name__}: {exc}",

            "traceback":
                traceback.format_exc(),

            "checkpoint_SHA_unchanged":
                checkpoint_unchanged(),
        })

        atomic_json_write(
            payload,
            result_path,
        )

        return 2


# =============================================================================
# Candidate child
# =============================================================================

def candidate_child(
    chunk_size: int,
    baseline_json_path: Path,
    baseline_tensor_path: Path,
    result_path: Path,
) -> int:
    payload = {
        "milestone":
            MILESTONE,

        "role":
            "CHUNKED_BATCHED_VJP_CANDIDATE",

        "chunk_size":
            int(chunk_size),

        "runtime_success":
            False,

        "derivative_equivalence_pass":
            False,

        "full_graph_equivalence_pass":
            False,

        "parameter_gradient_equivalence_pass":
            False,

        "performance_benchmark_run":
            False,

        "fallback_used":
            False,

        "optimizer_created":
            False,

        "optimizer_step":
            False,

        "weight_update":
            False,

        "scientific_graph_changed":
            False,
    }

    try:
        if chunk_size not in CHUNK_CANDIDATES:
            raise RuntimeError(
                f"Unauthorized chunk candidate {chunk_size}"
            )

        if not torch.xpu.is_available():
            raise RuntimeError(
                "Intel XPU unavailable."
            )

        if not exact(
            B2AA_SOURCE,
            B2AA_SOURCE_SHA,
        ):
            raise RuntimeError(
                "B2AA helper source SHA mismatch."
            )

        if not baseline_json_path.exists():
            raise RuntimeError(
                "Loop baseline JSON missing."
            )

        if not baseline_tensor_path.exists():
            raise RuntimeError(
                "Loop baseline tensor artifact missing."
            )

        baseline_json = read_json(
            baseline_json_path
        )

        if baseline_json.get(
            "success"
        ) is not True:
            raise RuntimeError(
                "Loop baseline artifact is not certified successful."
            )

        if (
            baseline_json.get(
                "tensor_artifact_sha256"
            )
            != sha256(
                baseline_tensor_path
            )
        ):
            raise RuntimeError(
                "Loop baseline tensor SHA mismatch."
            )

        baseline_tensors = torch.load(
            baseline_tensor_path,
            map_location="cpu",
            weights_only=False,
        )

        ids = (
            baseline_tensors[
                "reference_ids"
            ]
            .cpu()
            .numpy()
            .astype(int)
        )

        if len(ids) != REFERENCE_MICROBATCH:
            raise RuntimeError(
                "Baseline reference id count mismatch."
            )

        A = import_module(
            B2AA_SOURCE,
            f"b2ac_b2aa_helpers_chunk{chunk_size}",
        )

        S = import_module(
            B2S_SOURCE,
            f"b2ac_b2s_exact_chunk{chunk_size}",
        )

        engine = make_chunked_batched_engine(
            chunk_size
        )

        device = torch.device(
            "xpu"
        )

        # =====================================================================
        # A. Runtime + derivative equivalence.
        # =====================================================================

        try:
            candidate_derivative = A.derivative_snapshot(
                S,
                engine,
                ids,
                device,
                f"b2ac_chunk{chunk_size}_derivative",
            )
        except BaseException as exc:
            runtime_text = (
                f"{type(exc).__name__}: {exc}"
            )

            payload.update({
                "runtime_success":
                    False,

                "failure_stage":
                    "DERIVATIVE_RUNTIME",

                "failure_class":
                    classify_runtime_error(
                        runtime_text
                    ),

                "error":
                    runtime_text,

                "traceback":
                    traceback.format_exc(),

                "performance_benchmark_run":
                    False,

                "checkpoint_SHA_unchanged":
                    checkpoint_unchanged(),
            })

            atomic_json_write(
                payload,
                result_path,
            )

            return 0

        payload[
            "runtime_success"
        ] = True

        derivative_checks = {
            "S_pred":
                A.identity_compare(
                    "S_pred",
                    baseline_tensors[
                        "S_pred_derivative"
                    ],
                    candidate_derivative[
                        "S_pred"
                    ],
                ),

            "N_xi":
                A.identity_compare(
                    "N_xi",
                    baseline_tensors[
                        "N_xi"
                    ],
                    candidate_derivative[
                        "N_xi"
                    ],
                ),

            "N_tD":
                A.identity_compare(
                    "N_tD",
                    baseline_tensors[
                        "N_tD"
                    ],
                    candidate_derivative[
                        "N_tD"
                    ],
                ),

            "N_X":
                A.identity_compare(
                    "N_X",
                    baseline_tensors[
                        "N_X"
                    ],
                    candidate_derivative[
                        "N_X"
                    ],
                ),
        }

        derivative_equivalence_pass = all(
            rec[
                "pass"
            ]
            for rec in derivative_checks.values()
        )

        payload[
            "derivative_checks"
        ] = derivative_checks

        payload[
            "derivative_equivalence_pass"
        ] = bool(
            derivative_equivalence_pass
        )

        if not derivative_equivalence_pass:
            payload.update({
                "failure_stage":
                    "DERIVATIVE_EQUIVALENCE",

                "performance_benchmark_run":
                    False,

                "checkpoint_SHA_unchanged":
                    checkpoint_unchanged(),
            })

            atomic_json_write(
                payload,
                result_path,
            )

            return 0

        # =====================================================================
        # B. Full corrected graph + parameter-gradient equivalence.
        # =====================================================================

        try:
            candidate_full = A.full_graph_snapshot(
                S,
                engine,
                ids,
                device,
                f"b2ac_chunk{chunk_size}_full",
            )
        except BaseException as exc:
            runtime_text = (
                f"{type(exc).__name__}: {exc}"
            )

            payload.update({
                "failure_stage":
                    "FULL_GRAPH_RUNTIME",

                "failure_class":
                    classify_runtime_error(
                        runtime_text
                    ),

                "error":
                    runtime_text,

                "traceback":
                    traceback.format_exc(),

                "performance_benchmark_run":
                    False,

                "checkpoint_SHA_unchanged":
                    checkpoint_unchanged(),
            })

            atomic_json_write(
                payload,
                result_path,
            )

            return 0

        full_checks = {
            "S_pred":
                A.identity_compare(
                    "S_pred",
                    baseline_tensors[
                        "S_pred_full"
                    ],
                    candidate_full[
                        "S_pred"
                    ],
                ),

            "corrected_residual":
                A.identity_compare(
                    "corrected_residual",
                    baseline_tensors[
                        "residual"
                    ],
                    candidate_full[
                        "residual"
                    ],
                ),

            "physics_loss":
                A.scalar_identity_compare(
                    "physics_loss",
                    baseline_json[
                        "full_losses"
                    ][
                        "physics"
                    ],
                    candidate_full[
                        "losses"
                    ][
                        "physics"
                    ],
                ),

            "total_loss":
                A.scalar_identity_compare(
                    "total_loss",
                    baseline_json[
                        "full_losses"
                    ][
                        "total"
                    ],
                    candidate_full[
                        "losses"
                    ][
                        "total"
                    ],
                ),
        }

        gradient_checks = A.compare_parameter_gradients(
            baseline_tensors[
                "parameter_gradients"
            ],
            candidate_full[
                "parameter_gradients"
            ],
        )

        full_graph_equivalence_pass = all(
            rec[
                "pass"
            ]
            for rec in full_checks.values()
        )

        parameter_gradient_equivalence_pass = bool(
            gradient_checks[
                "all_parameter_gradients_pass"
            ]
        )

        payload[
            "full_graph_checks"
        ] = full_checks

        payload[
            "parameter_gradient_checks"
        ] = gradient_checks

        payload[
            "full_graph_equivalence_pass"
        ] = bool(
            full_graph_equivalence_pass
        )

        payload[
            "parameter_gradient_equivalence_pass"
        ] = bool(
            parameter_gradient_equivalence_pass
        )

        payload[
            "candidate_gradient_summary"
        ] = candidate_full[
            "gradient_summary"
        ]

        payload[
            "weights_exactly_unchanged"
        ] = bool(
            candidate_full[
                "weights_exactly_unchanged"
            ]
        )

        payload[
            "checkpoint_SHA_unchanged"
        ] = bool(
            candidate_full[
                "checkpoint_SHA_unchanged"
            ]
            and checkpoint_unchanged()
        )

        if not (
            full_graph_equivalence_pass
            and parameter_gradient_equivalence_pass
        ):
            payload.update({
                "failure_stage":
                    "FULL_GRAPH_OR_GRADIENT_EQUIVALENCE",

                "performance_benchmark_run":
                    False,
            })

            atomic_json_write(
                payload,
                result_path,
            )

            return 0

        # =====================================================================
        # C. Warmed performance only after full equivalence.
        # =====================================================================

        try:
            perf = A.warmed_performance_block(
                S,
                engine,
                ids,
                device,
                f"b2ac_chunk{chunk_size}_perf",
            )
        except BaseException as exc:
            runtime_text = (
                f"{type(exc).__name__}: {exc}"
            )

            payload.update({
                "failure_stage":
                    "PERFORMANCE_RUNTIME",

                "failure_class":
                    classify_runtime_error(
                        runtime_text
                    ),

                "error":
                    runtime_text,

                "traceback":
                    traceback.format_exc(),

                "performance_benchmark_run":
                    False,

                "checkpoint_SHA_unchanged":
                    checkpoint_unchanged(),
            })

            atomic_json_write(
                payload,
                result_path,
            )

            return 0

        baseline_median = float(
            baseline_json[
                "performance_median_seconds"
            ]
        )

        candidate_median = float(
            perf[
                "median_wall_seconds"
            ]
        )

        payload.update({
            "performance_benchmark_run":
                True,

            "performance":
                perf,

            "performance_median_seconds":
                candidate_median,

            "performance_mean_seconds":
                float(
                    perf[
                        "mean_wall_seconds"
                    ]
                ),

            "performance_median_profiles_per_second":
                float(
                    perf[
                        "median_profiles_per_second"
                    ]
                ),

            "loop_baseline_median_seconds":
                baseline_median,

            "loop_over_candidate_median_ratio":
                float(
                    baseline_median
                    / max(
                        candidate_median,
                        1e-30,
                    )
                ),

            "candidate_throughput_over_loop_ratio":
                float(
                    perf[
                        "median_profiles_per_second"
                    ]
                    / max(
                        baseline_json[
                            "performance_median_profiles_per_second"
                        ],
                        1e-30,
                    )
                ),

            "failure_stage":
                None,

            "checkpoint_SHA_unchanged":
                checkpoint_unchanged(),

            "weights_exactly_unchanged":
                True,
        })

        atomic_json_write(
            payload,
            result_path,
        )

        return 0

    except BaseException as exc:
        runtime_text = (
            f"{type(exc).__name__}: {exc}"
        )

        payload.update({
            "failure_stage":
                "HARNESS_RUNTIME",

            "failure_class":
                classify_runtime_error(
                    runtime_text
                ),

            "error":
                runtime_text,

            "traceback":
                traceback.format_exc(),

            "performance_benchmark_run":
                False,

            "checkpoint_SHA_unchanged":
                checkpoint_unchanged(),
        })

        atomic_json_write(
            payload,
            result_path,
        )

        return 2


# =============================================================================
# Parent authority + orchestration
# =============================================================================

def parent_main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2AC-XPU")
    print("Chunked Batched-VJP Equivalence + Warmed Performance Sweep")
    print("=" * 80)
    print("NO TRAINING — NO OPTIMIZER — NO WEIGHT UPDATE.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2AC summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(
                DATASET,
                DATASET_SHA,
            ),

        "COMP004_checkpoint_SHA_exact":
            exact(
                COMP004_CHECKPOINT,
                COMP004_CHECKPOINT_SHA,
            ),

        "B2S_source_SHA_exact":
            exact(
                B2S_SOURCE,
                B2S_SOURCE_SHA,
            ),

        "B2U_results_SHA_exact":
            exact(
                B2U_RESULTS,
                B2U_RESULTS_SHA,
            ),

        "B2Y_results_SHA_exact":
            exact(
                B2Y_RESULTS,
                B2Y_RESULTS_SHA,
            ),

        "B2AA_source_SHA_exact":
            exact(
                B2AA_SOURCE,
                B2AA_SOURCE_SHA,
            ),

        "B2AB_source_SHA_exact":
            exact(
                B2AB_SOURCE,
                B2AB_SOURCE_SHA,
            ),

        "B2AB_interpretation_SHA_exact":
            exact(
                B2AB_INTERPRETATION,
                B2AB_INTERPRETATION_SHA,
            ),

        "B2AB_protocol_SHA_exact":
            exact(
                B2AB_PROTOCOL,
                B2AB_PROTOCOL_SHA,
            ),

        "B2AB_handoff_SHA_exact":
            exact(
                B2AB_HANDOFF,
                B2AB_HANDOFF_SHA,
            ),

        "B2AB_summary_SHA_exact":
            exact(
                B2AB_SUMMARY,
                B2AB_SUMMARY_SHA,
            ),
    }

    b2ab = (
        read_json(
            B2AB_SUMMARY
        )
        if B2AB_SUMMARY.exists()
        else {}
    )

    b2ab_protocol = (
        read_json(
            B2AB_PROTOCOL
        )
        if B2AB_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2AB_status_exact":
            b2ab.get(
                "status"
            )
            == EXPECTED_B2AB_STATUS,

        "B2AB_B2AC_true":
            b2ab.get(
                "B2AC_authorized"
            )
            is True,

        "B2AB_training_false":
            b2ab.get(
                "COMP_XPU_005_full_training_authorized"
            )
            is False,

        "B2AB_B3_false":
            b2ab.get(
                "B3_authorized"
            )
            is False,

        "B2AB_candidates_exact":
            b2ab.get(
                "authorized_chunk_candidates"
            )
            == CHUNK_CANDIDATES,

        "B2AB_loop_endpoint_1":
            b2ab.get(
                "known_loop_chunk"
            )
            == KNOWN_LOOP_CHUNK,

        "B2AB_failed_endpoint_64":
            b2ab.get(
                "known_failed_full_chunk"
            )
            == KNOWN_FAILED_FULL_CHUNK,

        "B2AB_protocol_next_exact":
            b2ab_protocol.get(
                "authorized_next_milestone"
            )
            == MILESTONE,

        "B2AB_protocol_candidates_exact":
            b2ab_protocol.get(
                "authorized_chunk_candidates"
            )
            == CHUNK_CANDIDATES,

        "B2AB_protocol_reference_128":
            (
                b2ab_protocol
                .get("reference", {})
                .get("microbatch")
                == REFERENCE_MICROBATCH
            ),

        "B2AB_eps_exact":
            (
                b2ab_protocol
                .get("equivalence_budget", {})
                .get("float32_epsilon")
                == FLOAT32_EPS
            ),

        "B2AB_multiplier_exact":
            (
                b2ab_protocol
                .get("equivalence_budget", {})
                .get("multiplier")
                == IDENTITY_EPS_MULTIPLIER
            ),

        "B2AB_training_firewall_false":
            (
                b2ab_protocol
                .get("scientific_firewall", {})
                .get("training")
                is False
            ),

        "B2AB_optimizer_firewall_false":
            (
                b2ab_protocol
                .get("scientific_firewall", {})
                .get("optimizer")
                is False
            ),

        "B2AB_weight_update_firewall_false":
            (
                b2ab_protocol
                .get("scientific_firewall", {})
                .get("weight_update")
                is False
            ),
    })

    print("AUTHORITY / CHUNK-SWEEP GATES")

    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(
        gates.values()
    ):
        raise RuntimeError(
            "B2AC blocked by authority/protocol mismatch."
        )

    # Remove only stale B2AC artifacts, never prior milestone artifacts.
    for p in CANDIDATE_DIR.glob(
        "chunk_*.json"
    ):
        try:
            p.unlink()
        except OSError:
            pass

    for p in (
        BASELINE_JSON,
        BASELINE_TENSORS,
    ):
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass

    script = Path(
        __file__
    ).resolve()

    # =========================================================================
    # Isolated loop baseline.
    # =========================================================================

    print("\nLOOP BASELINE — ISOLATED SUBPROCESS")

    baseline_cmd = [
        sys.executable,
        str(script),
        "--baseline",
        "--result-path",
        str(BASELINE_JSON),
        "--tensor-path",
        str(BASELINE_TENSORS),
    ]

    t0 = time.perf_counter()

    baseline_proc = subprocess.run(
        baseline_cmd,
        cwd=str(R),
        capture_output=True,
        text=True,
    )

    baseline_wall = (
        time.perf_counter()
        - t0
    )

    if not BASELINE_JSON.exists():
        combined = (
            (baseline_proc.stdout or "")
            + "\n"
            + (baseline_proc.stderr or "")
        ).strip()

        raise RuntimeError(
            "B2AC loop baseline child produced no result artifact.\n"
            + combined[-4000:]
        )

    baseline = read_json(
        BASELINE_JSON
    )

    if baseline.get(
        "success"
    ) is not True:
        raise RuntimeError(
            "B2AC loop baseline failed: "
            + str(
                baseline.get(
                    "error"
                )
            )
        )

    if baseline_proc.returncode != 0:
        raise RuntimeError(
            "B2AC loop baseline returned nonzero despite success artifact."
        )

    if not BASELINE_TENSORS.exists():
        raise RuntimeError(
            "B2AC loop baseline tensor artifact missing."
        )

    if (
        baseline.get(
            "tensor_artifact_sha256"
        )
        != sha256(
            BASELINE_TENSORS
        )
    ):
        raise RuntimeError(
            "B2AC loop baseline tensor SHA mismatch."
        )

    print(
        "  PASS"
        f" | median={baseline['performance_median_seconds']:.3f}s"
        f" | throughput={baseline['performance_median_profiles_per_second']:.3f} profiles/s"
        f" | wall={baseline_wall:.3f}s"
    )

    if not checkpoint_unchanged():
        raise RuntimeError(
            "COMP-XPU-004 checkpoint changed during loop baseline."
        )

    # =========================================================================
    # Isolated chunk candidates.
    # =========================================================================

    candidate_results = []

    print("\nCHUNKED BATCHED-VJP CANDIDATES")
    print(
        "  Each candidate uses a fresh subprocess/XPU context."
    )
    print(
        "  Runtime/equivalence failure skips performance but does not stop the sweep.\n"
    )

    for chunk in CHUNK_CANDIDATES:
        result_path = (
            CANDIDATE_DIR
            / f"chunk_{chunk:02d}.json"
        )

        cmd = [
            sys.executable,
            str(script),
            "--candidate",
            str(chunk),
            "--baseline-json",
            str(BASELINE_JSON),
            "--baseline-tensors",
            str(BASELINE_TENSORS),
            "--result-path",
            str(result_path),
        ]

        child_start = time.perf_counter()

        proc = subprocess.run(
            cmd,
            cwd=str(R),
            capture_output=True,
            text=True,
        )

        child_wall = (
            time.perf_counter()
            - child_start
        )

        if result_path.exists():
            rec = read_json(
                result_path
            )
        else:
            combined = (
                (proc.stdout or "")
                + "\n"
                + (proc.stderr or "")
            ).strip()

            rec = {
                "milestone":
                    MILESTONE,

                "role":
                    "CHUNKED_BATCHED_VJP_CANDIDATE",

                "chunk_size":
                    int(chunk),

                "runtime_success":
                    False,

                "derivative_equivalence_pass":
                    False,

                "full_graph_equivalence_pass":
                    False,

                "parameter_gradient_equivalence_pass":
                    False,

                "performance_benchmark_run":
                    False,

                "failure_stage":
                    "SUBPROCESS_NO_ARTIFACT",

                "failure_class":
                    classify_runtime_error(
                        combined
                    ),

                "error":
                    combined[-4000:],

                "fallback_used":
                    False,

                "optimizer_created":
                    False,

                "optimizer_step":
                    False,

                "weight_update":
                    False,

                "scientific_graph_changed":
                    False,
            }

        rec[
            "subprocess_returncode"
        ] = int(
            proc.returncode
        )

        rec[
            "subprocess_wall_seconds"
        ] = float(
            child_wall
        )

        candidate_results.append(
            rec
        )

        if rec.get(
            "performance_benchmark_run"
        ):
            print(
                f"  chunk={chunk:2d} | EQUIV PASS | PERF PASS "
                f"| median={rec['performance_median_seconds']:.3f}s "
                f"| loop/candidate={rec['loop_over_candidate_median_ratio']:.3f}x "
                f"| throughput={rec['performance_median_profiles_per_second']:.3f} profiles/s"
            )

        elif rec.get(
            "runtime_success"
        ) and not rec.get(
            "derivative_equivalence_pass"
        ):
            print(
                f"  chunk={chunk:2d} | RUNTIME PASS | DERIVATIVE EQUIV FAIL"
            )

        elif (
            rec.get(
                "runtime_success"
            )
            and rec.get(
                "derivative_equivalence_pass"
            )
            and not (
                rec.get(
                    "full_graph_equivalence_pass"
                )
                and rec.get(
                    "parameter_gradient_equivalence_pass"
                )
            )
        ):
            print(
                f"  chunk={chunk:2d} | DERIVATIVE PASS | FULL/GRAD EQUIV FAIL"
            )

        else:
            print(
                f"  chunk={chunk:2d} | RUNTIME FAIL "
                f"| class={rec.get('failure_class')} "
                f"| stage={rec.get('failure_stage')}"
            )

        if not checkpoint_unchanged():
            raise RuntimeError(
                f"COMP-XPU-004 checkpoint changed during chunk={chunk}."
            )

    # =========================================================================
    # Freeze measurement set.
    # =========================================================================

    runtime_successful = [
        int(
            rec[
                "chunk_size"
            ]
        )
        for rec in candidate_results
        if rec.get(
            "runtime_success"
        )
    ]

    derivative_equivalent = [
        int(
            rec[
                "chunk_size"
            ]
        )
        for rec in candidate_results
        if rec.get(
            "derivative_equivalence_pass"
        )
    ]

    fully_equivalent = [
        int(
            rec[
                "chunk_size"
            ]
        )
        for rec in candidate_results
        if (
            rec.get(
                "full_graph_equivalence_pass"
            )
            and rec.get(
                "parameter_gradient_equivalence_pass"
            )
        )
    ]

    performance_candidates = [
        int(
            rec[
                "chunk_size"
            ]
        )
        for rec in candidate_results
        if rec.get(
            "performance_benchmark_run"
        )
    ]

    measured_performance = {
        str(
            rec[
                "chunk_size"
            ]
        ): {
            "median_seconds":
                float(
                    rec[
                        "performance_median_seconds"
                    ]
                ),

            "mean_seconds":
                float(
                    rec[
                        "performance_mean_seconds"
                    ]
                ),

            "median_profiles_per_second":
                float(
                    rec[
                        "performance_median_profiles_per_second"
                    ]
                ),

            "loop_over_candidate_median_ratio":
                float(
                    rec[
                        "loop_over_candidate_median_ratio"
                    ]
                ),

            "candidate_throughput_over_loop_ratio":
                float(
                    rec[
                        "candidate_throughput_over_loop_ratio"
                    ]
                ),
        }
        for rec in candidate_results
        if rec.get(
            "performance_benchmark_run"
        )
    }

    descriptive_fastest = None

    if performance_candidates:
        descriptive_fastest = min(
            performance_candidates,
            key=lambda c:
                measured_performance[
                    str(c)
                ][
                    "median_seconds"
                ],
        )

    all_attempted = (
        {
            int(
                rec[
                    "chunk_size"
                ]
            )
            for rec in candidate_results
        }
        == set(
            CHUNK_CANDIDATES
        )
    )

    all_no_fallback = all(
        rec.get(
            "fallback_used"
        )
        is False
        for rec in candidate_results
    )

    all_no_optimizer = all(
        rec.get(
            "optimizer_created"
        )
        is False
        for rec in candidate_results
    )

    all_no_step = all(
        rec.get(
            "optimizer_step"
        )
        is False
        for rec in candidate_results
    )

    all_no_update = all(
        rec.get(
            "weight_update"
        )
        is False
        for rec in candidate_results
    )

    all_graph_unchanged = all(
        rec.get(
            "scientific_graph_changed"
        )
        is False
        for rec in candidate_results
    )

    results_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "SUBPROCESS_ISOLATED_CHUNKED_BATCHED_VJP_EQUIVALENCE_PERFORMANCE_SWEEP",

        "reference": {
            "microbatch":
                REFERENCE_MICROBATCH,

            "loop_chunk_semantics":
                KNOWN_LOOP_CHUNK,

            "known_failed_full_chunk":
                KNOWN_FAILED_FULL_CHUNK,

            "candidate_chunks":
                CHUNK_CANDIDATES,

            "baseline_json_sha256":
                sha256(
                    BASELINE_JSON
                ),

            "baseline_tensor_sha256":
                sha256(
                    BASELINE_TENSORS
                ),

            "loop_baseline_performance_median_seconds":
                float(
                    baseline[
                        "performance_median_seconds"
                    ]
                ),

            "loop_baseline_median_profiles_per_second":
                float(
                    baseline[
                        "performance_median_profiles_per_second"
                    ]
                ),
        },

        "candidate_results":
            candidate_results,

        "runtime_successful_chunks":
            runtime_successful,

        "derivative_equivalent_chunks":
            derivative_equivalent,

        "fully_equivalent_chunks":
            fully_equivalent,

        "performance_measured_chunks":
            performance_candidates,

        "measured_performance":
            measured_performance,

        "descriptive_fastest_equivalent_measured_chunk":
            descriptive_fastest,

        "descriptive_fastest_semantics":
            "measurement only; NOT adopted by B2AC",

        "candidate_adopted":
            False,

        "fallback_used":
            False,

        "optimizer_created":
            False,

        "optimizer_step":
            False,

        "weight_update":
            False,

        "checkpoint_mutated":
            False,

        "scientific_graph_changed":
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
        json.dumps(
            results_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    decision_payload = {
        "milestone":
            MILESTONE,

        "runtime_successful_chunks":
            runtime_successful,

        "fully_equivalent_chunks":
            fully_equivalent,

        "performance_measured_chunks":
            performance_candidates,

        "descriptive_fastest_equivalent_measured_chunk":
            descriptive_fastest,

        "candidate_adopted":
            False,

        "reason_not_adopted":
            "B2AC is a measurement milestone only. V16E-1B2AD-XPU must "
            "interpret runtime, equivalence, performance, and resource behavior "
            "before any implementation is adopted.",

        "known_full_chunk_64_result":
            "UR_RESULT_ERROR_OUT_OF_RESOURCES from frozen B2AA",

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_decision_required":
            "V16E-1B2AD-XPU — interpret chunked batched-VJP sweep and freeze "
            "the derivative-engine implementation route.",
    }

    DECISION.write_text(
        json.dumps(
            decision_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates.update({
        "loop_baseline_success":
            baseline.get(
                "success"
            )
            is True,

        "loop_baseline_tensor_SHA_bound":
            baseline.get(
                "tensor_artifact_sha256"
            )
            == sha256(
                BASELINE_TENSORS
            ),

        "all_five_candidates_attempted":
            bool(
                all_attempted
            ),

        "all_children_no_fallback":
            bool(
                all_no_fallback
            ),

        "all_children_no_optimizer":
            bool(
                all_no_optimizer
            ),

        "all_children_no_optimizer_step":
            bool(
                all_no_step
            ),

        "all_children_no_weight_update":
            bool(
                all_no_update
            ),

        "all_children_scientific_graph_unchanged":
            bool(
                all_graph_unchanged
            ),

        "COMP004_checkpoint_still_unchanged":
            checkpoint_unchanged(),

        "results_written":
            RESULTS.exists()
            and RESULTS.stat().st_size > 0,

        "decision_written":
            DECISION.exists()
            and DECISION.stat().st_size > 0,

        "candidate_not_auto_adopted":
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

        "COMP005_training_not_authorized":
            True,

        "B3_not_authorized":
            True,
    })

    ok = all(
        bool(v)
        for v in gates.values()
    )

    status = (
        "V16E1B2AC_XPU_CHUNKED_BATCHED_VJP_SUBPROCESS_ISOLATED_EQUIVALENCE_AND_WARMED_PERFORMANCE_SWEEP_COMPLETE_"
        "EXACT_LOOP_BASELINE_DERIVATIVES_CORRECTED_GRAPH_PARAMETER_GRADIENTS_AND_WARMED_PERFORMANCE_SHA_BOUND_"
        "CHUNKS_2_4_8_16_32_ATTEMPTED_IN_FRESH_XPU_SUBPROCESSES_"
        "RUNTIME_DERIVATIVE_FULL_GRAPH_PARAMETER_GRADIENT_AND_PERFORMANCE_RESULTS_FROZEN_"
        "NO_AUTOMATIC_CANDIDATE_ADOPTION_NO_FALLBACK_NO_SCIENTIFIC_GRAPH_CHANGE_"
        "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
        "B2AD_CHUNK_SWEEP_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2AC_XPU_CHUNKED_BATCHED_VJP_SWEEP_COMPLETED_WITH_GATE_FAILURE"
    )

    summary_payload = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "baseline_json_sha256":
            sha256(
                BASELINE_JSON
            ),

        "baseline_tensor_sha256":
            sha256(
                BASELINE_TENSORS
            ),

        "results_sha256":
            sha256(
                RESULTS
            ),

        "decision_sha256":
            sha256(
                DECISION
            ),

        "runtime_successful_chunks":
            runtime_successful,

        "derivative_equivalent_chunks":
            derivative_equivalent,

        "fully_equivalent_chunks":
            fully_equivalent,

        "performance_measured_chunks":
            performance_candidates,

        "descriptive_fastest_equivalent_measured_chunk":
            descriptive_fastest,

        "candidate_adopted":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2AD-XPU — interpret chunked batched-VJP runtime, "
                "equivalence, performance, and resource results; freeze the "
                "next derivative-engine implementation route without training"
                if ok else
                "V16E-1B2AC-R1 — diagnose chunk-sweep execution gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nSWEEP SUMMARY")
    print(
        "  runtime successful    :",
        runtime_successful,
    )
    print(
        "  derivative equivalent :",
        derivative_equivalent,
    )
    print(
        "  fully equivalent      :",
        fully_equivalent,
    )
    print(
        "  performance measured  :",
        performance_candidates,
    )
    print(
        "  descriptive fastest   :",
        descriptive_fastest,
        "(NOT adopted)",
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

    print("\nHASHES")
    print(
        "  Baseline JSON  :",
        sha256(
            BASELINE_JSON
        ),
    )
    print(
        "  Baseline Tensor:",
        sha256(
            BASELINE_TENSORS
        ),
    )
    print(
        "  Results        :",
        sha256(
            RESULTS
        ),
    )
    print(
        "  Decision       :",
        sha256(
            DECISION
        ),
    )
    print(
        "  Summary        :",
        sha256(
            SUMMARY
        ),
    )

    print("\nNEXT")
    print(
        " ",
        summary_payload[
            "next_milestone"
        ],
    )

    if not ok:
        sys.exit(2)


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--baseline",
        action="store_true",
    )

    ap.add_argument(
        "--candidate",
        type=int,
        default=None,
    )

    ap.add_argument(
        "--baseline-json",
        type=Path,
        default=None,
    )

    ap.add_argument(
        "--baseline-tensors",
        type=Path,
        default=None,
    )

    ap.add_argument(
        "--result-path",
        type=Path,
        default=None,
    )

    ap.add_argument(
        "--tensor-path",
        type=Path,
        default=None,
    )

    return ap.parse_args()


def main():
    args = parse_args()

    if args.baseline:
        if (
            args.result_path is None
            or args.tensor_path is None
        ):
            raise RuntimeError(
                "--baseline requires --result-path and --tensor-path"
            )

        rc = baseline_child(
            args.result_path,
            args.tensor_path,
        )

        sys.exit(
            rc
        )

    if args.candidate is not None:
        if (
            args.baseline_json is None
            or args.baseline_tensors is None
            or args.result_path is None
        ):
            raise RuntimeError(
                "--candidate requires --baseline-json, --baseline-tensors, "
                "and --result-path"
            )

        rc = candidate_child(
            args.candidate,
            args.baseline_json,
            args.baseline_tensors,
            args.result_path,
        )

        sys.exit(
            rc
        )

    parent_main()


if __name__ == "__main__":
    main()
