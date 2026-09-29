#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib.util
import json
import multiprocessing
import os
import sys
import time

import numpy as np


# =============================================================================
# PAD-Stream V16E-1B2CUDA8HRRRR
#
# Generate and Freeze New Source-Native DEV and Blind CERT Datasets
#
# PURPOSE
# -------
# Execute the CUDA8G data firewall using the exact frozen Stage-2
# source-native Godunov dataset generator.
#
# DEV:
#   seed = 20260918
#   480 selected case/Nc combinations
#   6 times per combination
#   2,880 profiles
#   inspectable during development
#
# BLIND CERT:
#   seed = 20260919
#   480 selected case/Nc combinations
#   6 times per combination
#   2,880 profiles
#   generated and hashed now
#   scientifically SEALED until the final COMP008 checkpoint is frozen
#
# NO MODEL TRAINING.
# NO CERTIFICATION METRICS.
# NO OOD.
# NO TOF.
# B3 REMAINS BLOCKED.
#
# IMPLEMENTATION/PROVENANCE REPAIR RELATIVE TO FAILED CUDA8H/CUDA8HR:
#   CUDA8H compared the historical scientific-source SHA to raw repository
#   bytes only.
#
#   CUDA8HR repaired that scientific-source authority check, but still required
#   the failed CUDA8H runner itself to match its historical SHA as raw bytes.
#
#   CUDA8HRR applies the same exact raw/LF/CRLF UTF-8 text-authority rule to:
#     1. the failed CUDA8H source,
#     2. the failed CUDA8HR source,
#     3. the Stage-2 scientific source.
#
#   Newline convention is the ONLY normalization allowed.
#   No whitespace, token, comment, or semantic normalization is permitted.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8HRR"

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


# =============================================================================
# Frozen authorities
# =============================================================================

CUDA8G_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8G_Stage2_Architecture_Redesign_and_New_Certification_Protocol_Freeze.py"
)

CUDA8H_FAILED_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8H_Generate_and_Freeze_New_DEV_and_Blind_CERT_Datasets.py"
)

CUDA8HR_FAILED_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8HR_CrossPlatform_Source_Authority_Repair_Generate_and_Freeze_New_DEV_and_Blind_CERT_Datasets.py"
)

CUDA8G_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8G_ARCHITECTURE_AND_CERTIFICATION_PROTOCOL_FREEZE"
)

CUDA8G_ARCHITECTURE = (
    CUDA8G_ROOT
    / "V16E1B2CUDA8G_COMP008_Bounded_Monotone_Architecture_Protocol.json"
)

CUDA8G_DATA_PROTOCOL = (
    CUDA8G_ROOT
    / "V16E1B2CUDA8G_New_SourceNative_Data_Protocol.json"
)

CUDA8G_CERTIFICATION = (
    CUDA8G_ROOT
    / "V16E1B2CUDA8G_Stage2_Certification_Protocol.json"
)

CUDA8G_SUMMARY = (
    CUDA8G_ROOT
    / "PAD_Stream_V16E1B2CUDA8G_Summary.json"
)

CUDA8G_HANDOFF = (
    CUDA8G_ROOT
    / "V16E1B2CUDA8G_Handoff.md"
)


# Exact frozen Stage-2 native-coordinate reproduction source that contains the
# generator used for the original Stage-2 dataset.
BASE_GENERATOR = (
    REPO
    / "PAD_Stream_V16E1B2_XPU_Final_Compressible_BL_PIRNN_Native_Coordinate_Reproduction.py"
)


EXPECTED = {
    "CUDA8G_SOURCE":
        "af7cbe21f216be173add5e59c954707931e433459d1bf817a0ec711bee1267b2",

    "CUDA8H_FAILED_SOURCE":
        "6c0836aa6b7b04d4a0ca58cf30b35764b78539faab3b7f8d88c02b0165e62b1",

    "CUDA8HR_FAILED_SOURCE":
        "fd55d1ae5f0e5043057b6f1d0a590b5c413b1fff9ad25f556c599cef8b0d04d1",

    "CUDA8G_ARCHITECTURE":
        "e5c61bf1cb3c7b64acd52584c9a076253ae36fd51b7cca3e5fdd9aa7a1b2d135",

    "CUDA8G_DATA_PROTOCOL":
        "9c309766cc23b776a3a8db5ebac2c5c8d2ff5ed5a1eb7d79c6e7ca954211514b",

    "CUDA8G_CERTIFICATION":
        "eda537ef04b83fc22ed61881ea204136e531bdf330bbced6f497eff40f6e8490",

    "CUDA8G_SUMMARY":
        "81fc61b9a0d1c25953618b52b1cc712d4d293fd6214da1289441be65a4a52ade",

    "CUDA8G_HANDOFF":
        "c84cc1c596a811a9a74523b80e111ce468b02f17c2c8f79cb02b20ab39f11261",

    # Exact local/repository authority for the frozen Stage-2 generator port.
    "BASE_GENERATOR":
        "bec3cb8366fa46b18f424f6434123438326e92896ff0dbac018a07cd7403c7ee",

    # Frozen scientific source behind the generator.
    "STAGE2_SCIENTIFIC_SOURCE":
        "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397",
}


# =============================================================================
# Frozen CUDA8G data contract
# =============================================================================

DEV_SEED = 20260918
CERT_SEED = 20260919

SELECTED_COMBOS = 480
TIMES_PER_COMBO = 6
EXPECTED_PROFILES = SELECTED_COMBOS * TIMES_PER_COMBO

N_FAN = 64
PARAM_DIM = 11

WORKERS = min(
    8,
    max(
        1,
        os.cpu_count() or 1,
    ),
)


# =============================================================================
# Output paths
# =============================================================================

DATA_ROOT = (
    DRIVE
    / "datasets"
    / "stage2_redesign"
)

DATA_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


DEV_DATASET = (
    DATA_ROOT
    / "V16E_STAGE2_DEV_GODUNOV_SEED20260918.npz"
)

DEV_META = (
    DATA_ROOT
    / "V16E_STAGE2_DEV_GODUNOV_SEED20260918.json"
)

DEV_SELECTION = (
    DATA_ROOT
    / "V16E_STAGE2_DEV_GODUNOV_SEED20260918_SELECTION.npy"
)


CERT_ROOT = (
    DATA_ROOT
    / "sealed_certification"
)

CERT_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

CERT_DATASET = (
    CERT_ROOT
    / "V16E_STAGE2_BLIND_CERT_GODUNOV_SEED20260919.npz"
)

CERT_META = (
    CERT_ROOT
    / "V16E_STAGE2_BLIND_CERT_GODUNOV_SEED20260919.json"
)

CERT_SELECTION = (
    CERT_ROOT
    / "V16E_STAGE2_BLIND_CERT_GODUNOV_SEED20260919_SELECTION.npy"
)

CERT_SEAL = (
    CERT_ROOT
    / "V16E_STAGE2_BLIND_CERT_SEALED.json"
)


PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8HRR_NEW_DEV_AND_BLIND_CERT_DATA_FREEZE"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8HRR_Data_Generation_Results.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8HRR_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8HRR_Handoff.md"
)


# =============================================================================
# Helpers
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()



def text_authority_hashes(path: Path):
    """
    Return raw/LF/CRLF SHA-256 values for a UTF-8 text authority.

    Scientific text is considered byte-equivalent across platforms only when
    the historical frozen SHA matches one of:
      - raw bytes,
      - universal-newline text encoded with LF,
      - the same text encoded with CRLF.

    No whitespace, token, comment, or semantic normalization is permitted.
    """
    raw = path.read_bytes()

    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Scientific source is not UTF-8 text: {path}"
        ) from exc

    # Canonicalize newline convention only.
    lf_text = decoded.replace("\r\n", "\n").replace("\r", "\n")
    lf_bytes = lf_text.encode("utf-8")
    crlf_bytes = lf_text.replace("\n", "\r\n").encode("utf-8")

    return {
        "raw": hashlib.sha256(raw).hexdigest(),
        "LF": hashlib.sha256(lf_bytes).hexdigest(),
        "CRLF": hashlib.sha256(crlf_bytes).hexdigest(),
    }


def verify_cross_platform_text_authority(
    path: Path,
    expected_sha: str,
):
    hashes = text_authority_hashes(
        path
    )

    matched_modes = [
        mode
        for mode, digest in hashes.items()
        if digest == expected_sha
    ]

    print(
        "  scientific source raw SHA :",
        hashes["raw"],
    )
    print(
        "  scientific source LF SHA  :",
        hashes["LF"],
    )
    print(
        "  scientific source CRLF SHA:",
        hashes["CRLF"],
    )
    print(
        "  frozen authority SHA      :",
        expected_sha,
    )

    if not matched_modes:
        return False, None, hashes

    # Prefer raw if the platform file is already byte-identical.
    mode = (
        "raw"
        if "raw" in matched_modes
        else matched_modes[0]
    )

    print(
        "  matched authority mode    :",
        mode,
    )

    return True, mode, hashes


def array_sha256(x) -> str:
    a = np.ascontiguousarray(
        np.asarray(
            x
        )
    )

    return hashlib.sha256(
        a.tobytes(order="C")
    ).hexdigest()


def gate(
    name,
    condition,
):
    ok = bool(
        condition
    )

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8HRR gate failed: {name}"
        )


def atomic_json(
    path: Path,
    obj,
):
    tmp = Path(
        str(path)
        +
        ".tmp"
    )

    with tmp.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            obj,
            f,
            indent=2,
            allow_nan=False,
        )

        f.write("\n")
        f.flush()
        os.fsync(
            f.fileno()
        )

    os.replace(
        tmp,
        path,
    )


def import_by_path(
    name,
    path,
):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


# =============================================================================
# Process worker
# =============================================================================

_WORKER_BASE = None


def _worker_initializer(
    generator_path,
):
    global _WORKER_BASE

    _WORKER_BASE = import_by_path(
        "cuda8hrr_worker_base_generator",
        Path(
            generator_path
        ),
    )


def _worker(
    task,
):
    if _WORKER_BASE is None:
        raise RuntimeError(
            "CUDA8H worker base generator was not initialized."
        )

    return _WORKER_BASE._godunov_combo_worker(
        task
    )


# =============================================================================
# Banner
# =============================================================================

print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8HRR")
print("Generate and Freeze New Source-Native DEV and Blind CERT Datasets")
print("=" * 110)

print()
print("NO MODEL TRAINING.")
print("NO CERTIFICATION METRICS.")
print("BLIND CERT SCIENTIFIC INSPECTION: FORBIDDEN.")
print("NO OOD.")
print("NO TOF.")
print("B3 REMAINS BLOCKED.")
print()


# =============================================================================
# Authority gates
# =============================================================================

AUTHORITY = {
    "CUDA8G_SOURCE":
        CUDA8G_SOURCE,

    "CUDA8G_ARCHITECTURE":
        CUDA8G_ARCHITECTURE,

    "CUDA8G_DATA_PROTOCOL":
        CUDA8G_DATA_PROTOCOL,

    "CUDA8G_CERTIFICATION":
        CUDA8G_CERTIFICATION,

    "CUDA8G_SUMMARY":
        CUDA8G_SUMMARY,

    "CUDA8G_HANDOFF":
        CUDA8G_HANDOFF,

    "BASE_GENERATOR":
        BASE_GENERATOR,
}


TEXT_AUTHORITY = {
    "CUDA8H_FAILED_SOURCE":
        CUDA8H_FAILED_SOURCE,

    "CUDA8HR_FAILED_SOURCE":
        CUDA8HR_FAILED_SOURCE,
}



print("FROZEN AUTHORITY GATES")

for name, path in AUTHORITY.items():
    gate(
        f"{name}_exists",
        path.exists(),
    )

    gate(
        f"{name}_SHA_exact",
        sha256(
            path
        )
        ==
        EXPECTED[
            name
        ],
    )


for name, path in TEXT_AUTHORITY.items():
    gate(
        f"{name}_exists",
        path.exists(),
    )

    ok, mode, hashes = verify_cross_platform_text_authority(
        path,
        EXPECTED[
            name
        ],
    )

    gate(
        f"{name}_cross_platform_authority_exact",
        ok,
    )

    print(
        f"  {name} authority mode:",
        mode,
    )


BASE = import_by_path(
    "cuda8hrr_base_generator",
    BASE_GENERATOR,
)


gate(
    "Stage2_scientific_source_exists",
    Path(
        BASE.SOURCE
    ).exists(),
)

source_authority_ok, source_authority_mode, source_authority_hashes = (
    verify_cross_platform_text_authority(
        Path(
            BASE.SOURCE
        ),
        EXPECTED[
            "STAGE2_SCIENTIFIC_SOURCE"
        ],
    )
)

gate(
    "Stage2_scientific_source_cross_platform_authority_exact",
    source_authority_ok,
)

gate(
    "NX_TRAIN_exact_1601",
    int(
        BASE.NX_TRAIN
    )
    ==
    1601,
)

gate(
    "NC_grid_exact",
    np.array_equal(
        np.asarray(
            BASE.NC_VALS,
            dtype=np.float32,
        ),
        np.asarray(
            [
                0.00,
                0.05,
                0.10,
                0.20,
                0.30,
            ],
            dtype=np.float32,
        ),
    ),
)


cuda8g_data = json.loads(
    CUDA8G_DATA_PROTOCOL.read_text(
        encoding="utf-8"
    )
)


print()
print("CUDA8G DATA-PROTOCOL GATES")

gate(
    "DEV_seed_exact",
    int(
        cuda8g_data[
            "new_development_set"
        ][
            "seed"
        ]
    )
    ==
    DEV_SEED,
)

gate(
    "DEV_profiles_exact_2880",
    int(
        cuda8g_data[
            "new_development_set"
        ][
            "profiles"
        ]
    )
    ==
    EXPECTED_PROFILES,
)

gate(
    "CERT_seed_exact",
    int(
        cuda8g_data[
            "new_blind_certification_set"
        ][
            "seed"
        ]
    )
    ==
    CERT_SEED,
)

gate(
    "CERT_profiles_exact_2880",
    int(
        cuda8g_data[
            "new_blind_certification_set"
        ][
            "profiles"
        ]
    )
    ==
    EXPECTED_PROFILES,
)

gate(
    "CERT_must_be_hashed_before_COMP008",
    cuda8g_data[
        "new_blind_certification_set"
    ][
        "must_be_generated_and_hashed_before_COMP008_training"
    ]
    is True,
)

gate(
    "CERT_must_remain_sealed",
    cuda8g_data[
        "new_blind_certification_set"
    ][
        "must_remain_sealed_until_final_COMP008_checkpoint_is_frozen"
    ]
    is True,
)


# =============================================================================
# Exact source-native selection logic
# =============================================================================

param_list = BASE.generate_param_grid()

all_combos = [
    (
        p,
        float(
            nc
        ),
    )
    for p in param_list
    for nc in BASE.NC_VALS
]


print()
print("SOURCE-NATIVE GENERATOR STRUCTURE")

print(
    "  parameter cases          :",
    len(
        param_list
    ),
)

print(
    "  full case/Nc combinations:",
    len(
        all_combos
    ),
)

print(
    "  frozen DEV selections    :",
    SELECTED_COMBOS,
)

print(
    "  frozen CERT selections   :",
    SELECTED_COMBOS,
)

print(
    "  times per selection      :",
    TIMES_PER_COMBO,
)

print(
    "  fan nodes                :",
    N_FAN,
)


gate(
    "full_combo_count_exact_129600",
    len(
        all_combos
    )
    ==
    129600,
)


def selected_indices(
    seed,
):
    rng = np.random.default_rng(
        seed
    )

    return rng.choice(
        len(
            all_combos
        ),
        size=SELECTED_COMBOS,
        replace=False,
    ).astype(
        np.int64
    )


dev_indices = selected_indices(
    DEV_SEED
)

cert_indices = selected_indices(
    CERT_SEED
)


gate(
    "DEV_selection_unique_480",
    np.unique(
        dev_indices
    ).size
    ==
    SELECTED_COMBOS,
)

gate(
    "CERT_selection_unique_480",
    np.unique(
        cert_indices
    ).size
    ==
    SELECTED_COMBOS,
)


# The datasets are independent draws. Overlap is permitted by IID sampling,
# but selection identity is forbidden.
gate(
    "DEV_CERT_selection_not_identical",
    not np.array_equal(
        dev_indices,
        cert_indices,
    ),
)


RUNNER_SHA = sha256(
    Path(
        __file__
    )
)


# =============================================================================
# Build/cache helper
# =============================================================================

def validate_saved_dataset(
    dataset_path,
    meta_path,
    selection_path,
    role,
    seed,
    selected,
):
    if not (
        dataset_path.exists()
        and
        meta_path.exists()
        and
        selection_path.exists()
    ):
        return None


    meta = json.loads(
        meta_path.read_text(
            encoding="utf-8"
        )
    )


    checks = [
        meta.get(
            "milestone"
        )
        ==
        MILESTONE,

        meta.get(
            "role"
        )
        ==
        role,

        int(
            meta.get(
                "seed",
                -1,
            )
        )
        ==
        seed,

        int(
            meta.get(
                "selected_case_Nc_combinations",
                -1,
            )
        )
        ==
        SELECTED_COMBOS,

        int(
            meta.get(
                "profile_count",
                -1,
            )
        )
        ==
        EXPECTED_PROFILES,

        meta.get(
            "generator_runner_sha256"
        )
        ==
        EXPECTED[
            "BASE_GENERATOR"
        ],

        meta.get(
            "stage2_scientific_source_sha256"
        )
        ==
        EXPECTED[
            "STAGE2_SCIENTIFIC_SOURCE"
        ],

        meta.get(
            "cuda8hrr_runner_sha256"
        )
        ==
        RUNNER_SHA,

        meta.get(
            "dataset_sha256"
        )
        ==
        sha256(
            dataset_path
        ),
    ]


    saved_selection = np.load(
        selection_path,
        allow_pickle=False,
    )


    checks.extend(
        [
            np.array_equal(
                saved_selection,
                selected,
            ),

            meta.get(
                "selection_sha256"
            )
            ==
            array_sha256(
                selected
            ),
        ]
    )


    if not all(
        checks
    ):
        raise RuntimeError(
            f"Existing {role} dataset failed exact cache/provenance validation. "
            "Failing closed; no overwrite permitted."
        )


    with np.load(
        dataset_path,
        allow_pickle=False,
    ) as d:
        required = {
            "xi",
            "Sw",
            "p11",
            "tD",
            "ai",
            "at",
        }

        if (
            set(
                d.files
            )
            !=
            required
        ):
            raise RuntimeError(
                f"Existing {role} dataset schema mismatch."
            )

        shapes = {
            key:
                list(
                    d[
                        key
                    ].shape
                )
            for key in required
        }


    expected_shapes = {
        "xi":
            [
                EXPECTED_PROFILES,
                N_FAN,
                1,
            ],

        "Sw":
            [
                EXPECTED_PROFILES,
                N_FAN,
                1,
            ],

        "p11":
            [
                EXPECTED_PROFILES,
                PARAM_DIM,
            ],

        "tD":
            [
                EXPECTED_PROFILES,
            ],

        "ai":
            [
                EXPECTED_PROFILES,
                4,
            ],

        "at":
            [
                EXPECTED_PROFILES,
                4,
            ],
    }


    if shapes != expected_shapes:
        raise RuntimeError(
            f"Existing {role} dataset shapes mismatch."
        )


    print(
        f"[PASS] {role}_cached_dataset_exact"
    )

    print(
        f"  {role} dataset SHA:",
        sha256(
            dataset_path
        ),
    )


    return meta


def build_dataset(
    dataset_path,
    meta_path,
    selection_path,
    role,
    seed,
    selected,
    sealed,
):
    cached = validate_saved_dataset(
        dataset_path,
        meta_path,
        selection_path,
        role,
        seed,
        selected,
    )

    if cached is not None:
        return cached


    # Fail closed on incomplete prior writes.
    incomplete = [
        p
        for p in (
            dataset_path,
            meta_path,
            selection_path,
        )
        if p.exists()
    ]

    if incomplete:
        raise RuntimeError(
            f"Incomplete existing {role} artifact set detected: "
            f"{[str(p) for p in incomplete]}. "
            "Delete only after explicit scientific/provenance review."
        )


    print()
    print("-" * 110)
    print(
        f"GENERATING {role}"
    )
    print("-" * 110)

    print(
        "  seed                  :",
        seed,
    )

    print(
        "  selections            :",
        SELECTED_COMBOS,
    )

    print(
        "  expected profiles     :",
        EXPECTED_PROFILES,
    )

    print(
        "  workers               :",
        WORKERS,
    )

    if sealed:
        print(
            "  scientific inspection : SEALED / FORBIDDEN"
        )


    combos = [
        all_combos[
            int(
                idx
            )
        ]
        for idx in selected
    ]


    tasks = [
        (
            i,
            p,
            nc,
        )
        for i, (
            p,
            nc,
        )
        in enumerate(
            combos
        )
    ]


    t0 = time.time()


    if WORKERS <= 1:
        results = [
            BASE._godunov_combo_worker(
                task
            )
            for task in tasks
        ]

    else:
        results = []

        with ProcessPoolExecutor(
            max_workers=WORKERS,
            mp_context=multiprocessing.get_context("fork"),
            initializer=_worker_initializer,
            initargs=(
                str(
                    BASE_GENERATOR
                ),
            ),
        ) as ex:
            for n, result in enumerate(
                ex.map(
                    _worker,
                    tasks,
                    chunksize=1,
                ),
                start=1,
            ):
                results.append(
                    result
                )

                if (
                    n % 50 == 0
                    or
                    n
                    ==
                    len(
                        tasks
                    )
                ):
                    print(
                        f"  progress: {n:>3}/{len(tasks)} "
                        f"| elapsed={time.time()-t0:.1f}s"
                    )


    order_ok = all(
        result[
            0
        ]
        ==
        i
        for i, result in enumerate(
            results
        )
    )


    if not order_ok:
        raise RuntimeError(
            f"{role}: parallel result ordering changed."
        )


    combo_profile_counts = [
        len(
            combo_rows
        )
        for _,
        combo_rows
        in results
    ]


    if not all(
        count
        ==
        TIMES_PER_COMBO
        for count in combo_profile_counts
    ):
        raise RuntimeError(
            f"{role}: at least one selected combination did not produce "
            f"exactly {TIMES_PER_COMBO} profiles."
        )


    rows = []

    for _, combo_rows in results:
        rows.extend(
            combo_rows
        )


    if len(
        rows
    ) != EXPECTED_PROFILES:
        raise RuntimeError(
            f"{role}: profile count {len(rows)} != {EXPECTED_PROFILES}."
        )


    xi = np.stack(
        [
            r[
                0
            ].reshape(
                -1,
                1,
            )
            for r in rows
        ],
        axis=0,
    ).astype(
        np.float32
    )

    Sw = np.stack(
        [
            r[
                1
            ].reshape(
                -1,
                1,
            )
            for r in rows
        ],
        axis=0,
    ).astype(
        np.float32
    )

    p11 = np.stack(
        [
            r[
                2
            ]
            for r in rows
        ],
        axis=0,
    ).astype(
        np.float32
    )

    tD = np.asarray(
        [
            r[
                3
            ]
            for r in rows
        ],
        dtype=np.float32,
    )

    ai = np.stack(
        [
            r[
                4
            ]
            for r in rows
        ],
        axis=0,
    ).astype(
        np.int32
    )

    at = np.stack(
        [
            r[
                5
            ]
            for r in rows
        ],
        axis=0,
    ).astype(
        np.float32
    )


    # Structural validation only.
    expected_shapes = {
        "xi":
            (
                EXPECTED_PROFILES,
                N_FAN,
                1,
            ),

        "Sw":
            (
                EXPECTED_PROFILES,
                N_FAN,
                1,
            ),

        "p11":
            (
                EXPECTED_PROFILES,
                PARAM_DIM,
            ),

        "tD":
            (
                EXPECTED_PROFILES,
            ),

        "ai":
            (
                EXPECTED_PROFILES,
                4,
            ),

        "at":
            (
                EXPECTED_PROFILES,
                4,
            ),
    }


    arrays = {
        "xi":
            xi,

        "Sw":
            Sw,

        "p11":
            p11,

        "tD":
            tD,

        "ai":
            ai,

        "at":
            at,
    }


    for key, expected_shape in expected_shapes.items():
        if arrays[
            key
        ].shape != expected_shape:
            raise RuntimeError(
                f"{role}: {key} shape "
                f"{arrays[key].shape} != {expected_shape}."
            )

        if not np.isfinite(
            arrays[
                key
            ]
        ).all():
            raise RuntimeError(
                f"{role}: {key} contains nonfinite values."
            )


    native_nc = np.asarray(
        p11[
            :,
            10
        ],
        dtype=np.float32,
    )

    expected_nc = np.asarray(
        BASE.NC_VALS,
        dtype=np.float32,
    )


    # Structural integrity only; do not expose CERT distribution counts.
    if set(
        np.unique(
            native_nc
        ).tolist()
    ) != set(
        expected_nc.tolist()
    ):
        raise RuntimeError(
            f"{role}: all five frozen Nc strata are not represented."
        )


    tmp_dataset = Path(
        str(
            dataset_path
        )
        +
        ".tmp.npz"
    )

    np.savez_compressed(
        tmp_dataset,
        xi=xi,
        Sw=Sw,
        p11=p11,
        tD=tD,
        ai=ai,
        at=at,
    )

    os.replace(
        tmp_dataset,
        dataset_path,
    )


    tmp_selection = Path(
        str(
            selection_path
        )
        +
        ".tmp.npy"
    )

    np.save(
        tmp_selection,
        selected,
        allow_pickle=False,
    )

    os.replace(
        tmp_selection,
        selection_path,
    )


    dataset_sha = sha256(
        dataset_path
    )

    selection_sha = array_sha256(
        selected
    )


    meta = {
        "milestone":
            MILESTONE,

        "role":
            role,

        "scientifically_sealed":
            bool(
                sealed
            ),

        "seed":
            seed,

        "generator_runner_path":
            str(
                BASE_GENERATOR
            ),

        "generator_runner_sha256":
            EXPECTED[
                "BASE_GENERATOR"
            ],

        "stage2_scientific_source_path":
            str(
                BASE.SOURCE
            ),

        "stage2_scientific_source_sha256":
            EXPECTED[
                "STAGE2_SCIENTIFIC_SOURCE"
            ],

        "stage2_scientific_source_authority_mode":
            source_authority_mode,

        "stage2_scientific_source_raw_sha256":
            source_authority_hashes[
                "raw"
            ],

        "stage2_scientific_source_LF_sha256":
            source_authority_hashes[
                "LF"
            ],

        "stage2_scientific_source_CRLF_sha256":
            source_authority_hashes[
                "CRLF"
            ],

        "cuda8hrr_runner_sha256":
            RUNNER_SHA,

        "selection_method":
            (
                "np.random.default_rng(seed).choice("
                "129600,size=480,replace=False)"
            ),

        "selected_case_Nc_combinations":
            SELECTED_COMBOS,

        "selection_sha256":
            selection_sha,

        "times_per_selected_combination":
            TIMES_PER_COMBO,

        "profile_count":
            EXPECTED_PROFILES,

        "NX_TRAIN":
            1601,

        "n_fan":
            N_FAN,

        "parameter_dim":
            PARAM_DIM,

        "Nc_values":
            [
                0.00,
                0.05,
                0.10,
                0.20,
                0.30,
            ],

        "t_min_days":
            100.0,

        "horizon":
            "0.95*t_BT",

        "parallel_workers_used":
            WORKERS,

        "parallel_output_order_preserved":
            True,

        "all_selected_combinations_produced_six_profiles":
            True,

        "all_five_Nc_strata_present":
            True,

        "xi_shape":
            list(
                xi.shape
            ),

        "Sw_shape":
            list(
                Sw.shape
            ),

        "p11_shape":
            list(
                p11.shape
            ),

        "tD_shape":
            list(
                tD.shape
            ),

        "ai_shape":
            list(
                ai.shape
            ),

        "at_shape":
            list(
                at.shape
            ),

        "dataset_sha256":
            dataset_sha,

        "build_seconds":
            float(
                time.time()
                -
                t0
            ),

        "scientific_metrics_computed":
            False,

        "model_evaluated":
            False,

        "OOD":
            False,

        "TOF":
            False,
    }


    atomic_json(
        meta_path,
        meta,
    )


    print(
        f"[PASS] {role}_generation_complete"
    )

    print(
        f"  dataset SHA:",
        dataset_sha,
    )

    print(
        f"  selection SHA:",
        selection_sha,
    )

    print(
        f"  profiles:",
        EXPECTED_PROFILES,
    )

    if sealed:
        print(
            "  certification science: SEALED"
        )


    return meta


# =============================================================================
# Generate/freeze DEV first
# =============================================================================

dev_meta = build_dataset(
    DEV_DATASET,
    DEV_META,
    DEV_SELECTION,
    role="DEV",
    seed=DEV_SEED,
    selected=dev_indices,
    sealed=False,
)


# =============================================================================
# Generate/freeze blind CERT second
# =============================================================================

cert_meta = build_dataset(
    CERT_DATASET,
    CERT_META,
    CERT_SELECTION,
    role="BLIND_CERT",
    seed=CERT_SEED,
    selected=cert_indices,
    sealed=True,
)


# =============================================================================
# Seal artifact
# =============================================================================

seal = {
    "milestone":
        MILESTONE,

    "role":
        "BLIND_STAGE2_CERTIFICATION",

    "status":
        "GENERATED_HASHED_AND_SCIENTIFICALLY_SEALED",

    "dataset_path":
        str(
            CERT_DATASET
        ),

    "dataset_sha256":
        cert_meta[
            "dataset_sha256"
        ],

    "selection_sha256":
        cert_meta[
            "selection_sha256"
        ],

    "seed":
        CERT_SEED,

    "profile_count":
        EXPECTED_PROFILES,

    "may_be_used_for_development":
        False,

    "may_be_used_for_model_selection":
        False,

    "may_be_used_for_threshold_tuning":
        False,

    "may_be_used_for_optimizer_selection":
        False,

    "may_be_used_for_architecture_selection":
        False,

    "authorized_open_condition":
        (
            "Only after COMP008 architecture, optimization contract, training "
            "horizon, and final checkpoint are frozen without CERT results."
        ),

    "if_final_certification_fails":
        (
            "Record the failure. Do not tune COMP008 against this same blind set."
        ),

    "OOD":
        False,

    "TOF":
        False,
}


atomic_json(
    CERT_SEAL,
    seal,
)

CERT_SEAL_SHA = sha256(
    CERT_SEAL
)


# =============================================================================
# Final provenance
# =============================================================================

results = {
    "milestone":
        MILESTONE,

    "runner_sha256":
        RUNNER_SHA,

    "generator_runner_sha256":
        EXPECTED[
            "BASE_GENERATOR"
        ],

    "stage2_scientific_source_sha256":
        EXPECTED[
            "STAGE2_SCIENTIFIC_SOURCE"
        ],

    "DEV": {
        "seed":
            DEV_SEED,

        "profiles":
            EXPECTED_PROFILES,

        "dataset_path":
            str(
                DEV_DATASET
            ),

        "dataset_sha256":
            dev_meta[
                "dataset_sha256"
            ],

        "selection_sha256":
            dev_meta[
                "selection_sha256"
            ],

        "scientifically_sealed":
            False,
    },

    "BLIND_CERT": {
        "seed":
            CERT_SEED,

        "profiles":
            EXPECTED_PROFILES,

        "dataset_path":
            str(
                CERT_DATASET
            ),

        "dataset_sha256":
            cert_meta[
                "dataset_sha256"
            ],

        "selection_sha256":
            cert_meta[
                "selection_sha256"
            ],

        "seal_path":
            str(
                CERT_SEAL
            ),

        "seal_sha256":
            CERT_SEAL_SHA,

        "scientifically_sealed":
            True,
    },

    "original_holdout_retired_from_future_certification":
        True,

    "COMP008_implementation_preflight_authorized":
        True,

    "COMP008_training_authorized":
        False,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "OOD_used":
        False,

    "TOF_used":
        False,

    "next_milestone":
        (
            "V16E-1B2CUDA8I — COMP008 bounded-monotone architecture "
            "implementation and DEV-only preflight"
        ),
}


atomic_json(
    RESULTS_PATH,
    results,
)

RESULTS_SHA = sha256(
    RESULTS_PATH
)


summary = {
    "milestone":
        MILESTONE,

    "runner_sha256":
        RUNNER_SHA,

    "results_sha256":
        RESULTS_SHA,

    "DEV_dataset_sha256":
        dev_meta[
            "dataset_sha256"
        ],

    "BLIND_CERT_dataset_sha256":
        cert_meta[
            "dataset_sha256"
        ],

    "BLIND_CERT_seal_sha256":
        CERT_SEAL_SHA,

    "DEV_profiles":
        EXPECTED_PROFILES,

    "BLIND_CERT_profiles":
        EXPECTED_PROFILES,

    "BLIND_CERT_scientifically_sealed":
        True,

    "COMP008_implementation_preflight_authorized":
        True,

    "COMP008_training_authorized":
        False,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "next_milestone":
        results[
            "next_milestone"
        ],
}


atomic_json(
    SUMMARY_PATH,
    summary,
)

SUMMARY_SHA = sha256(
    SUMMARY_PATH
)


handoff = f"""# PAD-Stream V16E-1B2CUDA8HRRRR

## Status

New IID/source-native Stage-2 DEV and blind certification datasets have been
generated and frozen with the exact Stage-2 Godunov generator.

No model training occurred.

## DEV dataset

Seed: `{DEV_SEED}`

Profiles: `{EXPECTED_PROFILES}`

Dataset SHA-256:

`{dev_meta["dataset_sha256"]}`

Selection SHA-256:

`{dev_meta["selection_sha256"]}`

Role:

Development diagnostics, bounded-monotone architecture preflight, optimizer/loss
development, and independent Nc=0 injector-derivative investigation.

## Blind certification dataset

Seed: `{CERT_SEED}`

Profiles: `{EXPECTED_PROFILES}`

Dataset SHA-256:

`{cert_meta["dataset_sha256"]}`

Selection SHA-256:

`{cert_meta["selection_sha256"]}`

Seal SHA-256:

`{CERT_SEAL_SHA}`

Status:

`GENERATED_HASHED_AND_SCIENTIFICALLY_SEALED`

The blind certification dataset may not be used for architecture selection,
optimizer selection, loss tuning, threshold tuning, or development metrics.

## Original holdout

The original 2,880-profile Stage-2 holdout remains retired from future
certification. It remains retrospective CUDA8E/CUDA8F evidence only.

## Authorization

COMP008 architecture implementation/preflight: AUTHORIZED.

COMP008 training: NOT AUTHORIZED.

Stage 2 certified: NO.

B3 authorized: NO.

## Hashes

CUDA8HRR runner SHA-256:

`{RUNNER_SHA}`

Results SHA-256:

`{RESULTS_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`

## Next

`V16E-1B2CUDA8I — COMP008 bounded-monotone architecture implementation and DEV-only preflight`
"""


HANDOFF_PATH.write_text(
    handoff,
    encoding="utf-8",
)

HANDOFF_SHA = sha256(
    HANDOFF_PATH
)


print()
print("=" * 110)
print("CUDA8HRR RESULT")
print("=" * 110)

print(
    "DEV dataset SHA       :",
    dev_meta[
        "dataset_sha256"
    ],
)

print(
    "DEV selection SHA     :",
    dev_meta[
        "selection_sha256"
    ],
)

print(
    "BLIND CERT dataset SHA:",
    cert_meta[
        "dataset_sha256"
    ],
)

print(
    "BLIND CERT selection SHA:",
    cert_meta[
        "selection_sha256"
    ],
)

print(
    "BLIND CERT seal SHA   :",
    CERT_SEAL_SHA,
)

print(
    "Results SHA           :",
    RESULTS_SHA,
)

print(
    "Summary SHA           :",
    SUMMARY_SHA,
)

print(
    "Handoff SHA           :",
    HANDOFF_SHA,
)

print(
    "Runner SHA            :",
    RUNNER_SHA,
)

print()
print("DEV GENERATED/FROZEN: YES")
print("BLIND CERT GENERATED/FROZEN: YES")
print("BLIND CERT SCIENTIFICALLY SEALED: YES")
print("COMP008 IMPLEMENTATION PREFLIGHT AUTHORIZED: YES")
print("COMP008 TRAINING AUTHORIZED: NO")
print("STAGE 2 CERTIFIED: NO")
print("B3 AUTHORIZED: NO")

print()
print(
    "NEXT: V16E-1B2CUDA8I — COMP008 bounded-monotone architecture "
    "implementation and DEV-only preflight"
)
