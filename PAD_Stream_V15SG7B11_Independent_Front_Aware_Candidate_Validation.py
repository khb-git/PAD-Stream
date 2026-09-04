from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import shutil

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-11
# Independent Front-Aware Candidate Validation
#
# NO TRAINING.
# NO ARCHITECTURE CHANGE.
# NO THRESHOLD CHANGE.
# NO ORIGINAL SG7B-7R GATE RELAXATION.
#
# PURPOSE
# -------
# Independently evaluate the E2 front-aware candidate nominated by the
# SG7B-10 / 10R / 10S branch against:
#
#   A. Original SG7B-7R freeze contract
#      - state L1 / L2
#      - saturation bounds
#      - mass
#      - injector region
#      - front region
#      - early / late time
#      - canonical SG7A-activity-scaled physics
#
#   B. Front-aware improvement contract
#      - recovered early fronts
#      - front-conditioned threshold gap
#      - 100-day profile L1
#
#   C. SG7A/E0-relative front-shape preservation contract from SG7B-10S
#
# The canonical physics metric is recomputed independently here from:
#
#       |R_candidate - R_SG7A|
#   ---------------------------------
#   |T_SG7A| + |A_SG7A| + |C_SG7A| + 1e-4
#
# using the frozen SG7A master solution, the accepted positive-flow
# Godunov/upwind advective operator, the accepted capillary operator, and the
# exact same finite-volume temporal step used by the SG7B physics operator.
#
# Before candidate acceptance, the independent canonical implementation must
# reproduce the already frozen SG7B-7R baseline canonical metrics.
#
# If every gate passes, E2 is copied into a NEW front-aware frozen artifact.
# The original V15SG7B_FROZEN_Model.keras is never overwritten.
# =============================================================================


# =============================================================================
# ROOT / INPUTS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7B10_SOURCE = (
    ROOT
    / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

SG7B10S_CONTRACT_FILE = (
    ROOT
    / "output"
    / "V15_SG7B10S"
    / "V15SG7B10S_SG7A_Relative_Front_Shape_Contract.json"
)

SG7B10S_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7B10S"
    / "PAD_Stream_V15SG7B10S_Summary.json"
)

ORIGINAL_FROZEN_MODEL = (
    ROOT
    / "output"
    / "V15_SG7B7R"
    / "V15SG7B_FROZEN_Model.keras"
)

CANDIDATE_MODEL = (
    ROOT
    / "output"
    / "V15_SG7B10"
    / "experiments"
    / "E2"
    / "V15SG7B10_E2_Best_Model.keras"
)

DEFAULT_DEPLOYMENT_WORKSPACE = (
    ROOT.parent
    / f"{ROOT.name}_SG5C_seed_11x11"
)


# =============================================================================
# OUTPUTS
# =============================================================================

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B11"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FROZEN_FRONT_AWARE_MODEL = (
    OUTPUT_DIR
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

FREEZE_MANIFEST = (
    OUTPUT_DIR
    / "V15SG7B11_Front_Aware_Freeze_Manifest.json"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B11_Summary.json"
)

GATE_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B11_Final_Gates.csv"
)

PHYSICS_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B11_Canonical_Physics_Metrics.csv"
)

REGIONAL_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B11_State_Regional_Metrics.csv"
)

NUMERICAL_FILE = (
    OUTPUT_DIR
    / "V15SG7B11_Final_Validation.npz"
)


# =============================================================================
# ORIGINAL SG7B-7R FREEZE GATES
# =============================================================================

MAX_L1 = 0.020
MAX_L2 = 0.030
MAX_MASS_RELATIVE_MAE = 0.030

MAX_CANONICAL_MEAN = 0.500
MAX_CANONICAL_P90 = 1.000
MAX_CANONICAL_FRAC_GT1 = 0.10

MAX_INJECTOR_L1 = 0.015
MAX_FRONT_L1 = 0.030
MAX_EARLY_L1 = 0.020
MAX_LATE_L1 = 0.025


# =============================================================================
# FROZEN SG7B-7R CANONICAL REFERENCE
#
# These values are used ONLY as an independent implementation precheck.
# They do not define the candidate gates.
# =============================================================================

REFERENCE_E0_CANONICAL_MEAN = 3.413518e-01
REFERENCE_E0_CANONICAL_P90 = 8.684101e-01
REFERENCE_E0_CANONICAL_FRAC_GT1 = 8.051e-02

CANONICAL_PRECHECK_REL_TOL = 0.05
CANONICAL_PRECHECK_ABS_TOL_FRAC = 0.01


# =============================================================================
# NUMERICAL
# =============================================================================

EPS = 1.0e-12


# =============================================================================
# HELPERS
# =============================================================================

def load_module(
    path: Path,
    name: str,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing source module:\n{path}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:

        raise RuntimeError(
            f"Could not import source module:\n{path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def load_json(
    path: Path,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing JSON:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(
            handle
        )


def save_csv(
    path: Path,
    rows: list[dict],
):

    if not rows:

        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
):

    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                chunk_size
            )

            if not chunk:

                break

            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def relative_close(
    value,
    reference,
    rel_tol,
):

    value = float(
        value
    )

    reference = float(
        reference
    )

    return bool(
        abs(
            value
            -
            reference
        )
        <=
        rel_tol
        *
        max(
            abs(
                reference
            ),
            EPS,
        )
    )


# =============================================================================
# SG7A MASTER INTERPOLATION
# =============================================================================

def interpolate_master(
    master_t,
    master_s,
    query_t,
):

    master_t = np.asarray(
        master_t,
        dtype=np.float64,
    )

    master_s = np.asarray(
        master_s,
        dtype=np.float64,
    )

    query_t = np.asarray(
        query_t,
        dtype=np.float64,
    )

    if (
        master_s.ndim
        !=
        2
    ):

        raise RuntimeError(
            "SG7A master_saturation must be 2-D."
        )

    if (
        master_s.shape[
            0
        ]
        !=
        master_t.size
    ):

        raise RuntimeError(
            "SG7A master time/saturation length mismatch."
        )

    query_t = np.clip(
        query_t,
        master_t[
            0
        ],
        master_t[
            -1
        ],
    )

    right = np.searchsorted(
        master_t,
        query_t,
        side="left",
    )

    right = np.clip(
        right,
        0,
        master_t.size - 1,
    )

    left = np.maximum(
        right - 1,
        0,
    )

    exact = np.isclose(
        master_t[
            right
        ],
        query_t,
        rtol=0.0,
        atol=1.0e-12,
    )

    left[
        exact
    ] = right[
        exact
    ]

    t0 = master_t[
        left
    ]

    t1 = master_t[
        right
    ]

    denom = (
        t1
        -
        t0
    )

    alpha = np.zeros_like(
        query_t,
        dtype=np.float64,
    )

    valid = (
        np.abs(
            denom
        )
        >
        EPS
    )

    alpha[
        valid
    ] = (
        query_t[
            valid
        ]
        -
        t0[
            valid
        ]
    ) / denom[
        valid
    ]

    s0 = master_s[
        left
    ]

    s1 = master_s[
        right
    ]

    return (
        s0
        +
        alpha[
            :,
            None
        ]
        *
        (
            s1
            -
            s0
        )
    )


# =============================================================================
# CAPILLARY DIVERGENCE
#
# Mirrors the accepted SG7B finite-volume capillary operator.
# =============================================================================

def capillary_divergence(
    base,
    tf,
    saturation,
    dxi,
):

    S = tf.convert_to_tensor(
        saturation,
        dtype=tf.float32,
    )

    D_cell = base.diffusion_shape_tf(
        S
    )

    D_internal = (
        0.5
        *
        (
            D_cell[
                :,
                :-1
            ]
            +
            D_cell[
                :,
                1:
            ]
        )
    )

    G_internal = (
        base.POROSITY
        /
        base.PE_C
        *
        D_internal
        *
        (
            S[
                :,
                1:
            ]
            -
            S[
                :,
                :-1
            ]
        )
        /
        dxi
    )

    D_injected = base.diffusion_shape_tf(
        tf.constant(
            base.S_INJECTED,
            dtype=tf.float32,
        )
    )

    D_left = (
        0.5
        *
        (
            D_injected
            +
            D_cell[
                :,
                0
            ]
        )
    )

    G_left = (
        base.POROSITY
        /
        base.PE_C
        *
        D_left
        *
        (
            S[
                :,
                0
            ]
            -
            base.S_INJECTED
        )
        /
        (
            0.5
            *
            dxi
        )
    )[
        :,
        None
    ]

    G_right = tf.zeros(
        (
            tf.shape(
                S
            )[
                0
            ],
            1,
        ),
        dtype=tf.float32,
    )

    G_cap = tf.concat(
        [
            G_left,
            G_internal,
            G_right,
        ],
        axis=1,
    )

    div_cap = (
        G_cap[
            :,
            1:
        ]
        -
        G_cap[
            :,
            :-1
        ]
    ) / dxi

    return np.asarray(
        div_cap.numpy(),
        dtype=np.float64,
    )


# =============================================================================
# INDEPENDENT SG7A CANONICAL REFERENCE
# =============================================================================

def build_sg7a_canonical_reference(
    base,
    tf,
    dataset,
    sg7a,
):

    X = np.asarray(
        dataset[
            "X_test"
        ],
        dtype=np.float64,
    )

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][
            0
        ]
    )

    master_t = np.asarray(
        sg7a[
            "master_tD"
        ],
        dtype=np.float64,
    )

    master_s = np.asarray(
        sg7a[
            "master_saturation"
        ],
        dtype=np.float64,
    )

    t_actual = (
        X[
            :,
            0,
            1
        ]
        *
        tD_scale
    )

    dt_reference = (
        tD_scale
        /
        800.0
    )

    t_minus = np.maximum(
        t_actual
        -
        dt_reference,
        0.0,
    )

    t_plus = np.minimum(
        t_actual
        +
        dt_reference,
        tD_scale,
    )

    dt_effective = (
        t_plus
        -
        t_minus
        +
        float(
            base.EPS
        )
    )

    S = interpolate_master(
        master_t,
        master_s,
        t_actual,
    )

    S_minus = interpolate_master(
        master_t,
        master_s,
        t_minus,
    )

    S_plus = interpolate_master(
        master_t,
        master_s,
        t_plus,
    )

    S_t = (
        S_plus
        -
        S_minus
    ) / dt_effective[
        :,
        None
    ]

    S_tf = tf.convert_to_tensor(
        S.astype(
            np.float32
        ),
        dtype=tf.float32,
    )

    _, div_adv_tf = base.predicted_advective_flux(
        S_tf
    )

    div_adv = np.asarray(
        div_adv_tf.numpy(),
        dtype=np.float64,
    )

    dxi = float(
        xi[
            1
        ]
        -
        xi[
            0
        ]
    )

    div_cap = capillary_divergence(
        base,
        tf,
        S,
        dxi,
    )

    residual = (
        S_t
        +
        div_adv
        -
        div_cap
    )

    activity = (
        np.abs(
            S_t
        )
        +
        np.abs(
            div_adv
        )
        +
        np.abs(
            div_cap
        )
        +
        1.0e-4
    )

    # Dataset truth should agree with the SG7A master at the selected times.
    dataset_truth = np.asarray(
        dataset[
            "Y_test"
        ][
            :,
            :,
            0
        ],
        dtype=np.float64,
    )

    truth_alignment_linf = float(
        np.max(
            np.abs(
                dataset_truth
                -
                S
            )
        )
    )

    return {
        "S":
            S,

        "temporal":
            S_t,

        "advective":
            div_adv,

        "capillary":
            div_cap,

        "residual":
            residual,

        "activity":
            activity,

        "truth_alignment_linf":
            truth_alignment_linf,
    }


# =============================================================================
# CANDIDATE CANONICAL METRICS
# =============================================================================

def canonical_metrics(
    base,
    tf,
    model,
    dataset,
    sg7a_reference,
):

    X = np.asarray(
        dataset[
            "X_test"
        ],
        dtype=np.float32,
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][
            0
        ]
    )

    residual_tf, _, prediction_tf, _ = (
        base.finite_volume_residual(
            model,
            tf.constant(
                X,
                dtype=tf.float32,
            ),
            tf.constant(
                tD_scale,
                dtype=tf.float32,
            ),
            training=False,
        )
    )

    residual = np.asarray(
        residual_tf.numpy(),
        dtype=np.float64,
    )

    prediction = np.asarray(
        prediction_tf.numpy(),
        dtype=np.float64,
    )

    deltaR = (
        residual
        -
        sg7a_reference[
            "residual"
        ]
    )

    scaled = (
        np.abs(
            deltaR
        )
        /
        sg7a_reference[
            "activity"
        ]
    )

    flat = scaled.ravel()

    return {
        "prediction":
            prediction,

        "residual":
            residual,

        "deltaR":
            deltaR,

        "scaled":
            scaled,

        "absolute_deltaR_MAE":
            float(
                np.mean(
                    np.abs(
                        deltaR
                    )
                )
            ),

        "canonical_mean":
            float(
                np.mean(
                    flat
                )
            ),

        "canonical_RMS":
            float(
                np.sqrt(
                    np.mean(
                        flat ** 2
                    )
                )
            ),

        "canonical_P50":
            float(
                np.percentile(
                    flat,
                    50,
                )
            ),

        "canonical_P90":
            float(
                np.percentile(
                    flat,
                    90,
                )
            ),

        "canonical_P95":
            float(
                np.percentile(
                    flat,
                    95,
                )
            ),

        "canonical_P99":
            float(
                np.percentile(
                    flat,
                    99,
                )
            ),

        "fraction_gt_1":
            float(
                np.mean(
                    flat
                    >
                    1.0
                )
            ),
    }


# =============================================================================
# FRONT-SHAPE METRICS — independent reimplementation of 10S definitions
# =============================================================================

def front_pair_mask(
    truth,
    front_high,
    crossing_low,
):

    left = (
        truth[
            :,
            :-1
        ]
    )

    right = (
        truth[
            :,
            1:
        ]
    )

    return (
        (
            np.minimum(
                left,
                right,
            )
            <=
            float(
                front_high
            )
        )
        &
        (
            np.maximum(
                left,
                right,
            )
            >=
            float(
                crossing_low
            )
        )
    )


def local_shape_metrics(
    field,
    truth,
    xi,
    mask,
    monotonic_tol,
):

    field = np.asarray(
        field,
        dtype=np.float64,
    )

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    xi = np.asarray(
        xi,
        dtype=np.float64,
    )

    d_field = (
        field[
            :,
            1:
        ]
        -
        field[
            :,
            :-1
        ]
    )

    d_truth = (
        truth[
            :,
            1:
        ]
        -
        truth[
            :,
            :-1
        ]
    )

    dxi = (
        xi[
            1:
        ]
        -
        xi[
            :-1
        ]
    )

    grad_field = (
        d_field
        /
        dxi[
            None,
            :
        ]
    )

    grad_truth = (
        d_truth
        /
        dxi[
            None,
            :
        ]
    )

    local_d = d_field[
        mask
    ]

    local_grad = grad_field[
        mask
    ]

    local_truth_grad = grad_truth[
        mask
    ]

    positive = local_d[
        local_d
        >
        monotonic_tol
    ]

    node_mask = np.zeros_like(
        field,
        dtype=bool,
    )

    node_mask[
        :,
        :-1
    ] |= mask

    node_mask[
        :,
        1:
    ] |= mask

    tv_field = np.sum(
        np.abs(
            d_field
        )
        *
        mask,
        axis=1,
    )

    tv_truth = np.sum(
        np.abs(
            d_truth
        )
        *
        mask,
        axis=1,
    )

    return {
        "violation_fraction":
            float(
                np.mean(
                    local_d
                    >
                    monotonic_tol
                )
            ),

        "positive_dS_P99":
            (
                float(
                    np.percentile(
                        positive,
                        99,
                    )
                )
                if positive.size
                else 0.0
            ),

        "positive_dS_MAX":
            (
                float(
                    np.max(
                        positive
                    )
                )
                if positive.size
                else 0.0
            ),

        "gradient_MAE_vs_SG7A":
            float(
                np.mean(
                    np.abs(
                        local_grad
                        -
                        local_truth_grad
                    )
                )
            ),

        "front_state_L1_vs_SG7A":
            float(
                np.mean(
                    np.abs(
                        field[
                            node_mask
                        ]
                        -
                        truth[
                            node_mask
                        ]
                    )
                )
            ),

        "front_TV_MAE_vs_SG7A":
            float(
                np.mean(
                    np.abs(
                        tv_field
                        -
                        tv_truth
                    )
                )
            ),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7B-11 independent "
            "front-aware candidate validation."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_DEPLOYMENT_WORKSPACE
        ),
        help=(
            "Accepted 11x11 SG5C deployment workspace."
        ),
    )

    args = parser.parse_args()

    workspace = Path(
        args.workspace
    ).resolve()

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7B-11"
    )

    print(
        "Independent Front-Aware Candidate Validation"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO ARCHITECTURE CHANGE WILL BE MADE."
    )

    print(
        "NO ORIGINAL SG7B-7R GATE WILL BE RELAXED."
    )

    print(
        "NO FRONT THRESHOLD WILL BE CHANGED."
    )

    print(
        "THE ORIGINAL SG7B FROZEN MODEL WILL NOT BE OVERWRITTEN."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    required = [
        SG7B10_SOURCE,
        SG7B10S_CONTRACT_FILE,
        SG7B10S_SUMMARY_FILE,
        ORIGINAL_FROZEN_MODEL,
        CANDIDATE_MODEL,
    ]

    for path in required:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7B-11 prerequisite:\n{path}"
            )

    sg10s_summary = load_json(
        SG7B10S_SUMMARY_FILE
    )

    if (
        sg10s_summary.get(
            "status"
        )
        !=
        "E2_PASSES_RELATIVE_FRONT_SHAPE_SCREEN"
    ):

        raise RuntimeError(
            "SG7B-11 requires SG7B-10S status:\n"
            "E2_PASSES_RELATIVE_FRONT_SHAPE_SCREEN"
        )

    sg10s_contract = load_json(
        SG7B10S_CONTRACT_FILE
    )

    sg10 = load_module(
        SG7B10_SOURCE,
        "pad_stream_sg7b10_for_sg7b11",
    )

    base = sg10.load_base_module()

    tf = sg10.tf

    # =========================================================================
    # MODEL IDENTITY
    # =========================================================================

    frozen_hash = sha256_file(
        ORIGINAL_FROZEN_MODEL
    )

    candidate_hash = sha256_file(
        CANDIDATE_MODEL
    )

    print(
        "\nMODEL IDENTITY"
    )

    print(
        f"  Original frozen model   : "
        f"{ORIGINAL_FROZEN_MODEL.name}"
    )

    print(
        f"  Original SHA-256        : "
        f"{frozen_hash}"
    )

    print(
        f"  Candidate model         : "
        f"{CANDIDATE_MODEL.name}"
    )

    print(
        f"  Candidate SHA-256       : "
        f"{candidate_hash}"
    )

    # =========================================================================
    # AUTHORITATIVE DATA
    # =========================================================================

    dataset = base.load_dataset()

    sg7a = base.load_sg7a()

    targets = base.build_advective_targets(
        dataset,
        sg7a,
    )

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][
            0
        ]
    )

    deployment = sg10.load_deployment_database(
        workspace,
        tD_scale,
    )

    frozen_model = tf.keras.models.load_model(
        ORIGINAL_FROZEN_MODEL
    )

    candidate_model = tf.keras.models.load_model(
        CANDIDATE_MODEL
    )

    print(
        "\nAUTHORITATIVE DATABASE"
    )

    print(
        f"  Held-out profiles       : "
        f"{len(dataset['X_test']):,}"
    )

    print(
        f"  xi nodes                : "
        f"{len(xi)}"
    )

    print(
        f"  Deployment streamlines  : "
        f"{len(deployment['X100']):,}"
    )

    # =========================================================================
    # STATE / REGIONAL PRESERVATION
    # =========================================================================

    candidate_test = base.evaluate_split(
        candidate_model,
        dataset[
            "X_test"
        ],
        dataset[
            "Y_test"
        ],
        targets[
            "face_test"
        ],
        targets[
            "div_test"
        ],
        xi,
        tD_scale,
    )

    candidate_extra = sg10.additional_preservation_metrics(
        dataset[
            "X_test"
        ],
        candidate_test[
            "truth"
        ],
        candidate_test[
            "prediction"
        ],
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "HELD-OUT STATE / REGIONAL ACCURACY"
    )

    print(
        "=" * 78
    )

    print(
        f"L1                       : "
        f"{candidate_test['L1']:.6e}"
    )

    print(
        f"L2                       : "
        f"{candidate_test['L2']:.6e}"
    )

    print(
        f"Linf                     : "
        f"{candidate_test['Linf']:.6e}"
    )

    print(
        f"Prediction range         : "
        f"{candidate_test['minimum_prediction']:.6f} -> "
        f"{candidate_test['maximum_prediction']:.6f}"
    )

    print(
        f"Mass relative MAE        : "
        f"{candidate_test['mass_relative_MAE']:.6e}"
    )

    print(
        f"Injector L1              : "
        f"{candidate_test['injector_L1']:.6e}"
    )

    print(
        f"Front L1                 : "
        f"{candidate_extra['front_L1']:.6e}"
    )

    print(
        f"Early L1                 : "
        f"{candidate_extra['early_L1']:.6e}"
    )

    print(
        f"Late L1                  : "
        f"{candidate_extra['late_L1_recomputed']:.6e}"
    )

    # =========================================================================
    # INDEPENDENT CANONICAL PHYSICS
    # =========================================================================

    print(
        "\nBuilding independent SG7A canonical physics reference..."
    )

    canonical_truth = build_sg7a_canonical_reference(
        base,
        tf,
        dataset,
        sg7a,
    )

    frozen_canonical = canonical_metrics(
        base,
        tf,
        frozen_model,
        dataset,
        canonical_truth,
    )

    candidate_canonical = canonical_metrics(
        base,
        tf,
        candidate_model,
        dataset,
        canonical_truth,
    )

    precheck_mean = relative_close(
        frozen_canonical[
            "canonical_mean"
        ],
        REFERENCE_E0_CANONICAL_MEAN,
        CANONICAL_PRECHECK_REL_TOL,
    )

    precheck_p90 = relative_close(
        frozen_canonical[
            "canonical_P90"
        ],
        REFERENCE_E0_CANONICAL_P90,
        CANONICAL_PRECHECK_REL_TOL,
    )

    precheck_frac = bool(
        abs(
            frozen_canonical[
                "fraction_gt_1"
            ]
            -
            REFERENCE_E0_CANONICAL_FRAC_GT1
        )
        <=
        CANONICAL_PRECHECK_ABS_TOL_FRAC
    )

    canonical_precheck_pass = bool(
        precheck_mean
        and
        precheck_p90
        and
        precheck_frac
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "INDEPENDENT CANONICAL-PHYSICS PRECHECK"
    )

    print(
        "=" * 78
    )

    print(
        f"SG7A/dataset saturation Linf : "
        f"{canonical_truth['truth_alignment_linf']:.6e}"
    )

    print(
        f"E0 canonical mean            : "
        f"{frozen_canonical['canonical_mean']:.6e} "
        f"(reference {REFERENCE_E0_CANONICAL_MEAN:.6e})"
    )

    print(
        f"E0 canonical P90             : "
        f"{frozen_canonical['canonical_P90']:.6e} "
        f"(reference {REFERENCE_E0_CANONICAL_P90:.6e})"
    )

    print(
        f"E0 fraction > 1              : "
        f"{100.0 * frozen_canonical['fraction_gt_1']:.3f}% "
        f"(reference {100.0 * REFERENCE_E0_CANONICAL_FRAC_GT1:.3f}%)"
    )

    print(
        f"Independent reproduction     : "
        f"{'PASS' if canonical_precheck_pass else 'FAIL'}"
    )

    if not canonical_precheck_pass:

        raise RuntimeError(
            "Independent SG7B-11 canonical implementation did not reproduce "
            "the accepted SG7B-7R baseline within tolerance.\n"
            "Candidate freeze validation cannot proceed."
        )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "CANDIDATE CANONICAL PHYSICS"
    )

    print(
        "=" * 78
    )

    print(
        f"Absolute deltaR MAE      : "
        f"{candidate_canonical['absolute_deltaR_MAE']:.6e}"
    )

    print(
        f"Canonical mean           : "
        f"{candidate_canonical['canonical_mean']:.6e}"
    )

    print(
        f"Canonical RMS            : "
        f"{candidate_canonical['canonical_RMS']:.6e}"
    )

    print(
        f"Canonical P50            : "
        f"{candidate_canonical['canonical_P50']:.6e}"
    )

    print(
        f"Canonical P90            : "
        f"{candidate_canonical['canonical_P90']:.6e}"
    )

    print(
        f"Canonical P95            : "
        f"{candidate_canonical['canonical_P95']:.6e}"
    )

    print(
        f"Canonical P99            : "
        f"{candidate_canonical['canonical_P99']:.6e}"
    )

    print(
        f"Fraction > 1             : "
        f"{100.0 * candidate_canonical['fraction_gt_1']:.3f}%"
    )

    # =========================================================================
    # FRONT-AWARE DEPLOYMENT
    # =========================================================================

    deployment_prediction = candidate_model.predict(
        deployment[
            "X100"
        ],
        batch_size=sg10.BATCH_SIZE,
        verbose=0,
    )[
        :,
        :,
        0
    ]

    front = sg10.front_metrics_np(
        deployment_prediction,
        deployment[
            "truth100"
        ],
    )

    front_contract = (
        sg10s_contract[
            "front_improvement_contract"
        ]
    )

    min_fronts = int(
        front_contract[
            "minimum_recovered_fronts"
        ]
    )

    max_gap = float(
        front_contract[
            "maximum_conditioned_threshold_gap"
        ]
    )

    max_profile_l1 = float(
        front_contract[
            "maximum_100d_profile_L1"
        ]
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "FRONT-AWARE IMPROVEMENT"
    )

    print(
        "=" * 78
    )

    print(
        f"Recovered fronts        : "
        f"{front['recovered_front_count']:,} / "
        f"{front['truth_front_count']:,}"
    )

    print(
        f"Conditioned gap         : "
        f"{front['conditioned_threshold_gap_mean']:.6e}"
    )

    print(
        f"100d profile L1         : "
        f"{front['profile_L1_mean']:.6e}"
    )

    # =========================================================================
    # INDEPENDENT SG7B-10S SHAPE SCREEN
    # =========================================================================

    local_mask = front_pair_mask(
        deployment[
            "truth100"
        ],
        sg10.FRONT_HIGH,
        sg10.CROSSING_LOW,
    )

    candidate_shape = local_shape_metrics(
        deployment_prediction,
        deployment[
            "truth100"
        ],
        deployment[
            "xi"
        ],
        local_mask,
        sg10.MONOTONIC_TOL,
    )

    shape_gates = (
        sg10s_contract[
            "shape_preservation_gates"
        ]
    )

    shape_gate_results = []

    for gate in shape_gates:

        key = str(
            gate[
                "gate"
            ]
        )

        value = float(
            candidate_shape[
                key
            ]
        )

        limit = float(
            gate[
                "candidate_limit"
            ]
        )

        shape_gate_results.append(
            {
                "gate":
                    key,

                "value":
                    value,

                "limit":
                    limit,

                "passed":
                    bool(
                        value
                        <=
                        limit
                    ),
            }
        )

    shape_pass = all(
        row[
            "passed"
        ]
        for row
        in shape_gate_results
    )

    # =========================================================================
    # FINAL GATES
    # =========================================================================

    gates = [
        (
            "Model loads successfully",
            True,
            "load",
            1.0,
            1.0,
        ),

        (
            "Predictions finite",
            bool(
                np.all(
                    np.isfinite(
                        candidate_test[
                            "prediction"
                        ]
                    )
                )
                and
                np.all(
                    np.isfinite(
                        deployment_prediction
                    )
                )
            ),
            "finite",
            1.0,
            1.0,
        ),

        (
            "Saturation lower bound respected",
            bool(
                candidate_test[
                    "minimum_prediction"
                ]
                >=
                base.S_INITIAL
                -
                1.0e-7
            ),
            ">=",
            candidate_test[
                "minimum_prediction"
            ],
            base.S_INITIAL,
        ),

        (
            "Saturation upper bound respected",
            bool(
                candidate_test[
                    "maximum_prediction"
                ]
                <=
                base.S_INJECTED
                +
                1.0e-7
            ),
            "<=",
            candidate_test[
                "maximum_prediction"
            ],
            base.S_INJECTED,
        ),

        (
            "Held-out L1 < 0.020",
            candidate_test[
                "L1"
            ]
            <
            MAX_L1,
            "<",
            candidate_test[
                "L1"
            ],
            MAX_L1,
        ),

        (
            "Held-out L2 < 0.030",
            candidate_test[
                "L2"
            ]
            <
            MAX_L2,
            "<",
            candidate_test[
                "L2"
            ],
            MAX_L2,
        ),

        (
            "Mass relative MAE < 0.030",
            candidate_test[
                "mass_relative_MAE"
            ]
            <
            MAX_MASS_RELATIVE_MAE,
            "<",
            candidate_test[
                "mass_relative_MAE"
            ],
            MAX_MASS_RELATIVE_MAE,
        ),

        (
            "Canonical mean < 0.500",
            candidate_canonical[
                "canonical_mean"
            ]
            <
            MAX_CANONICAL_MEAN,
            "<",
            candidate_canonical[
                "canonical_mean"
            ],
            MAX_CANONICAL_MEAN,
        ),

        (
            "Canonical P90 < 1.000",
            candidate_canonical[
                "canonical_P90"
            ]
            <
            MAX_CANONICAL_P90,
            "<",
            candidate_canonical[
                "canonical_P90"
            ],
            MAX_CANONICAL_P90,
        ),

        (
            "Canonical fraction > 1 < 10%",
            candidate_canonical[
                "fraction_gt_1"
            ]
            <
            MAX_CANONICAL_FRAC_GT1,
            "<",
            candidate_canonical[
                "fraction_gt_1"
            ],
            MAX_CANONICAL_FRAC_GT1,
        ),

        (
            "Injector-region L1 < 0.015",
            candidate_test[
                "injector_L1"
            ]
            <
            MAX_INJECTOR_L1,
            "<",
            candidate_test[
                "injector_L1"
            ],
            MAX_INJECTOR_L1,
        ),

        (
            "High-gradient/front L1 < 0.030",
            candidate_extra[
                "front_L1"
            ]
            <
            MAX_FRONT_L1,
            "<",
            candidate_extra[
                "front_L1"
            ],
            MAX_FRONT_L1,
        ),

        (
            "Early-time L1 < 0.020",
            candidate_extra[
                "early_L1"
            ]
            <
            MAX_EARLY_L1,
            "<",
            candidate_extra[
                "early_L1"
            ],
            MAX_EARLY_L1,
        ),

        (
            "Late-time L1 < 0.025",
            candidate_extra[
                "late_L1_recomputed"
            ]
            <
            MAX_LATE_L1,
            "<",
            candidate_extra[
                "late_L1_recomputed"
            ],
            MAX_LATE_L1,
        ),

        (
            f"Recovered fronts >= {min_fronts}",
            front[
                "recovered_front_count"
            ]
            >=
            min_fronts,
            ">=",
            front[
                "recovered_front_count"
            ],
            min_fronts,
        ),

        (
            "Conditioned front gap within contract",
            front[
                "conditioned_threshold_gap_mean"
            ]
            <=
            max_gap,
            "<=",
            front[
                "conditioned_threshold_gap_mean"
            ],
            max_gap,
        ),

        (
            "100d profile L1 within contract",
            front[
                "profile_L1_mean"
            ]
            <=
            max_profile_l1,
            "<=",
            front[
                "profile_L1_mean"
            ],
            max_profile_l1,
        ),

        (
            "SG7A/E0-relative front shape preserved",
            shape_pass,
            "all",
            float(
                sum(
                    row[
                        "passed"
                    ]
                    for row
                    in shape_gate_results
                )
            ),
            float(
                len(
                    shape_gate_results
                )
            ),
        ),
    ]

    passed = all(
        flag
        for (
            _,
            flag,
            _,
            _,
            _,
        )
        in gates
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7B-11 FINAL INDEPENDENT GATES"
    )

    print(
        "=" * 78
    )

    for (
        description,
        flag,
        _,
        _,
        _,
    ) in gates:

        print(
            f"[{'PASS' if flag else 'FAIL'}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    # =========================================================================
    # DIAGNOSIS / PROMOTION
    # =========================================================================

    canonical_pass = bool(
        candidate_canonical[
            "canonical_mean"
        ]
        <
        MAX_CANONICAL_MEAN
        and
        candidate_canonical[
            "canonical_P90"
        ]
        <
        MAX_CANONICAL_P90
        and
        candidate_canonical[
            "fraction_gt_1"
        ]
        <
        MAX_CANONICAL_FRAC_GT1
    )

    state_pass = bool(
        candidate_test[
            "L1"
        ]
        <
        MAX_L1
        and
        candidate_test[
            "L2"
        ]
        <
        MAX_L2
        and
        candidate_test[
            "mass_relative_MAE"
        ]
        <
        MAX_MASS_RELATIVE_MAE
        and
        candidate_test[
            "injector_L1"
        ]
        <
        MAX_INJECTOR_L1
        and
        candidate_extra[
            "front_L1"
        ]
        <
        MAX_FRONT_L1
        and
        candidate_extra[
            "early_L1"
        ]
        <
        MAX_EARLY_L1
        and
        candidate_extra[
            "late_L1_recomputed"
        ]
        <
        MAX_LATE_L1
    )

    front_pass = bool(
        front[
            "recovered_front_count"
        ]
        >=
        min_fronts
        and
        front[
            "conditioned_threshold_gap_mean"
        ]
        <=
        max_gap
        and
        front[
            "profile_L1_mean"
        ]
        <=
        max_profile_l1
        and
        shape_pass
    )

    promoted_hash = None

    if passed:

        shutil.copy2(
            CANDIDATE_MODEL,
            FROZEN_FRONT_AWARE_MODEL,
        )

        promoted_hash = sha256_file(
            FROZEN_FRONT_AWARE_MODEL
        )

        status = (
            "FRONT_AWARE_PI_RNN_FROZEN"
        )

        recommendation = (
            "The E2 front-aware candidate independently satisfies the full "
            "original SG7B-7R state, mass, regional, and canonical-physics "
            "contract together with the SG7B-10S front-aware preservation "
            "contract. The new front-aware frozen model may now be redeployed "
            "through the SGSim streamline/grid pathway. The original frozen "
            "SG7B model remains archived and unchanged."
        )

        next_milestone = (
            "V15-SG7C-R — Front-Aware Frozen PI-RNN Redeployment "
            "on SGSim Streamlines"
        )

    elif (
        state_pass
        and
        front_pass
        and
        not canonical_pass
    ):

        status = (
            "CANDIDATE_CANONICAL_PHYSICS_REGRESSION"
        )

        recommendation = (
            "E2 preserves state accuracy and solves the diagnosed front defect "
            "but does not satisfy the frozen canonical-physics contract. Do not "
            "freeze E2. Audit the canonical residual regression before any "
            "additional training."
        )

        next_milestone = (
            "V15-SG7B-11R — Canonical Physics Regression Audit"
        )

    elif (
        state_pass
        and
        canonical_pass
        and
        not front_pass
    ):

        status = (
            "CANDIDATE_FRONT_SHAPE_REGRESSION"
        )

        recommendation = (
            "E2 preserves the original SG7B-7R contract but does not retain "
            "the complete front-aware improvement/preservation contract under "
            "independent validation. Resume shape-regularized refinement."
        )

        next_milestone = (
            "V15-SG7B-10B — Shape-Regularized Front-Aware Refinement"
        )

    else:

        status = (
            "CANDIDATE_PRESERVATION_REGRESSION"
        )

        recommendation = (
            "E2 does not independently preserve the complete frozen-model "
            "acceptance contract. Keep the original SG7B frozen model "
            "authoritative and diagnose the failed preservation gates."
        )

        next_milestone = (
            "V15-SG7B-11R — Candidate Preservation Regression Audit"
        )

    # =========================================================================
    # SAVE TABLES
    # =========================================================================

    gate_rows = []

    for (
        description,
        flag,
        operator,
        value,
        threshold,
    ) in gates:

        gate_rows.append(
            {
                "gate":
                    description,

                "passed":
                    bool(
                        flag
                    ),

                "operator":
                    operator,

                "value":
                    float(
                        value
                    ),

                "threshold":
                    float(
                        threshold
                    ),
            }
        )

    save_csv(
        GATE_TABLE_FILE,
        gate_rows,
    )

    physics_rows = []

    for label, result in [
        (
            "E0_frozen_precheck",
            frozen_canonical,
        ),

        (
            "E2_candidate",
            candidate_canonical,
        ),
    ]:

        physics_rows.append(
            {
                "model":
                    label,

                "absolute_deltaR_MAE":
                    result[
                        "absolute_deltaR_MAE"
                    ],

                "canonical_mean":
                    result[
                        "canonical_mean"
                    ],

                "canonical_RMS":
                    result[
                        "canonical_RMS"
                    ],

                "canonical_P50":
                    result[
                        "canonical_P50"
                    ],

                "canonical_P90":
                    result[
                        "canonical_P90"
                    ],

                "canonical_P95":
                    result[
                        "canonical_P95"
                    ],

                "canonical_P99":
                    result[
                        "canonical_P99"
                    ],

                "fraction_gt_1":
                    result[
                        "fraction_gt_1"
                    ],
            }
        )

    save_csv(
        PHYSICS_TABLE_FILE,
        physics_rows,
    )

    regional_rows = [
        {
            "L1":
                candidate_test[
                    "L1"
                ],

            "L2":
                candidate_test[
                    "L2"
                ],

            "Linf":
                candidate_test[
                    "Linf"
                ],

            "mass_relative_MAE":
                candidate_test[
                    "mass_relative_MAE"
                ],

            "injector_L1":
                candidate_test[
                    "injector_L1"
                ],

            "front_L1":
                candidate_extra[
                    "front_L1"
                ],

            "early_L1":
                candidate_extra[
                    "early_L1"
                ],

            "late_L1":
                candidate_extra[
                    "late_L1_recomputed"
                ],

            "prediction_min":
                candidate_test[
                    "minimum_prediction"
                ],

            "prediction_max":
                candidate_test[
                    "maximum_prediction"
                ],

            "recovered_fronts":
                front[
                    "recovered_front_count"
                ],

            "conditioned_gap":
                front[
                    "conditioned_threshold_gap_mean"
                ],

            "profile_L1_100d":
                front[
                    "profile_L1_mean"
                ],
        }
    ]

    save_csv(
        REGIONAL_TABLE_FILE,
        regional_rows,
    )

    # =========================================================================
    # NUMERICAL
    # =========================================================================

    np.savez_compressed(
        NUMERICAL_FILE,

        truth_test=
            candidate_test[
                "truth"
            ].astype(
                np.float32
            ),

        candidate_prediction_test=
            candidate_test[
                "prediction"
            ].astype(
                np.float32
            ),

        candidate_canonical_scaled=
            candidate_canonical[
                "scaled"
            ].astype(
                np.float32
            ),

        e0_canonical_scaled=
            frozen_canonical[
                "scaled"
            ].astype(
                np.float32
            ),

        deployment_truth100=
            deployment[
                "truth100"
            ].astype(
                np.float32
            ),

        deployment_candidate100=
            deployment_prediction.astype(
                np.float32
            ),

        xi=
            xi.astype(
                np.float32
            ),
    )

    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================

    fig, ax = plt.subplots(
        figsize=(
            8,
            6,
        )
    )

    labels = [
        "E0 frozen",
        "E2 candidate",
        "Gate",
    ]

    values = [
        frozen_canonical[
            "canonical_mean"
        ],
        candidate_canonical[
            "canonical_mean"
        ],
        MAX_CANONICAL_MEAN,
    ]

    ax.bar(
        labels,
        values,
    )

    ax.set_ylabel(
        "Canonical mean"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-11\n"
        "Independent Canonical Physics"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B11_Canonical_Physics.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.hist(
        candidate_canonical[
            "scaled"
        ].ravel(),
        bins=80,
        alpha=0.8,
    )

    ax.axvline(
        1.0,
        linestyle="--",
        label="Canonical = 1",
    )

    ax.set_xlabel(
        "SG7A-activity-scaled residual discrepancy"
    )

    ax.set_ylabel(
        "Samples"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-11\n"
        "Candidate Canonical-Physics Distribution"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B11_Canonical_Distribution.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    profile_error = np.mean(
        np.abs(
            candidate_test[
                "prediction"
            ]
            -
            candidate_test[
                "truth"
            ]
        ),
        axis=1,
    )

    t_norm = (
        dataset[
            "X_test"
        ][
            :,
            0,
            1
        ]
    )

    ax.scatter(
        t_norm,
        profile_error,
        s=18,
        alpha=0.7,
    )

    ax.set_xlabel(
        "Normalized tD"
    )

    ax.set_ylabel(
        "Profile L1"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-11\n"
        "Held-Out Candidate Error vs Time"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B11_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # =========================================================================
    # MANIFEST / SUMMARY
    # =========================================================================

    manifest = {
        "milestone":
            "V15-SG7B-11",

        "candidate_source":
            str(
                CANDIDATE_MODEL
            ),

        "candidate_sha256":
            candidate_hash,

        "original_frozen_model":
            str(
                ORIGINAL_FROZEN_MODEL
            ),

        "original_frozen_sha256":
            frozen_hash,

        "original_frozen_overwritten":
            False,

        "validation_passed":
            bool(
                passed
            ),

        "status":
            status,

        "front_aware_frozen_model":
            (
                str(
                    FROZEN_FRONT_AWARE_MODEL
                )
                if passed
                else None
            ),

        "front_aware_frozen_sha256":
            promoted_hash,

        "canonical_contract": {
            "mean_max":
                MAX_CANONICAL_MEAN,

            "P90_max":
                MAX_CANONICAL_P90,

            "fraction_gt_1_max":
                MAX_CANONICAL_FRAC_GT1,
        },

        "next_milestone":
            next_milestone,
    }

    with FREEZE_MANIFEST.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            manifest,
            handle,
            indent=2,
        )

    summary = {
        "milestone":
            "V15-SG7B-11",

        "description":
            "Independent front-aware candidate validation",

        "training_performed":
            False,

        "architecture_changed":
            False,

        "original_SG7B7R_gates_relaxed":
            False,

        "canonical_precheck_passed":
            bool(
                canonical_precheck_pass
            ),

        "state_preservation_passed":
            state_pass,

        "canonical_physics_passed":
            canonical_pass,

        "front_aware_contract_passed":
            front_pass,

        "validation_passed":
            bool(
                passed
            ),

        "status":
            status,

        "recommendation":
            recommendation,

        "next_milestone":
            next_milestone,
    }

    with SUMMARY_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            summary,
            handle,
            indent=2,
        )

    # =========================================================================
    # FINAL
    # =========================================================================

    print(
        "\nSTATUS"
    )

    print(
        f"  {status}"
    )

    print(
        "\nRECOMMENDATION"
    )

    print(
        f"  {recommendation}"
    )

    if passed:

        print(
            "\nNEW FRONT-AWARE FROZEN MODEL"
        )

        print(
            f"  {FROZEN_FRONT_AWARE_MODEL.name}"
        )

        print(
            "\nSHA-256"
        )

        print(
            f"  {promoted_hash}"
        )

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nTables:"
    )

    print(
        f"  {GATE_TABLE_FILE.name}"
    )

    print(
        f"  {PHYSICS_TABLE_FILE.name}"
    )

    print(
        f"  {REGIONAL_TABLE_FILE.name}"
    )

    print(
        "\nNumerical:"
    )

    print(
        f"  {NUMERICAL_FILE.name}"
    )

    print(
        "\nFreeze manifest:"
    )

    print(
        f"  {FREEZE_MANIFEST.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B11_Canonical_Physics.png"
    )

    print(
        "  V15SG7B11_Canonical_Distribution.png"
    )

    print(
        "  V15SG7B11_Error_vs_tD.png"
    )

    print(
        "\nSummary:"
    )

    print(
        f"  {SUMMARY_FILE.name}"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    if passed:

        print(
            "V15-SG7B-11 FINAL VALIDATION: PASS"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "FRONT-AWARE SG7B PI-RNN FROZEN"
        )

        print()

        print(
            "The original SG7B frozen model remains archived and unchanged."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7C-R — Front-Aware Frozen PI-RNN Redeployment "
            "on SGSim Streamlines"
        )

    else:

        print(
            "V15-SG7B-11 FINAL VALIDATION: FAIL"
        )

        print()

        print(
            "The original SG7B frozen model remains authoritative."
        )

        print()

        print(
            f"Next milestone:\n{next_milestone}"
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
