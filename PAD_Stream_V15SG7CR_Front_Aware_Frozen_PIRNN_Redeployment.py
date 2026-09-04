from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R
# Front-Aware Frozen PI-RNN Redeployment on SGSim Streamlines
#
# NO TRAINING.
# NO MODEL PARAMETER CHANGE.
# NO SG6 GEOMETRY CHANGE.
# NO TRANSPORT-PHYSICS CHANGE.
# NO MAP-BACK.
#
# PURPOSE
# -------
# Deploy the independently frozen front-aware SG7B PI-RNN from SG7B-11 on
# the accepted 11x11 SGSim streamline / TOF database.
#
# This milestone is deliberately an A/B redeployment:
#
#     Original frozen SG7B  -> accepted SG7C database
#     Front-aware SG7B      -> SG7C-R database
#
# The same:
#   - SG6 streamline geometry,
#   - TOF coordinates,
#   - flow weights,
#   - deployment times,
#   - tD normalization,
#   - SG7A deployment truth
#
# are retained.
#
# SG7C-R answers:
#   1. Does the front-aware frozen model preserve global deployment accuracy?
#   2. Does it recover the early SG7A threshold fronts in actual SGSim
#      streamline space?
#   3. Is the front improvement achieved without changing geometry or physics?
#
# No grid map-back is performed here. That remains SG7D-R.
# =============================================================================


# =============================================================================
# ROOT / INPUTS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7B10_SOURCE = (
    ROOT
    / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

SG7B11_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7B11"
    / "PAD_Stream_V15SG7B11_Summary.json"
)

SG7B11_MANIFEST = (
    ROOT
    / "output"
    / "V15_SG7B11"
    / "V15SG7B11_Front_Aware_Freeze_Manifest.json"
)

FRONT_AWARE_MODEL = (
    ROOT
    / "output"
    / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

DEFAULT_WORKSPACE = (
    ROOT.parent
    / f"{ROOT.name}_SG5C_seed_11x11"
)

SG6_RELATIVE = (
    Path("output")
    / "V15_SG6"
    / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)

ORIGINAL_SG7C_RELATIVE = (
    Path("output")
    / "V15_SG7C"
    / "SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)


# =============================================================================
# OUTPUTS
# =============================================================================

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7CR"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DEPLOYMENT_FILE = (
    OUTPUT_DIR
    / "SG7CR_FRONT_AWARE_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)

METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7CR_Deployment_Metrics.csv"
)

FRONT_FILE = (
    OUTPUT_DIR
    / "V15SG7CR_Front_Metrics.csv"
)

PRODUCER_FILE = (
    OUTPUT_DIR
    / "V15SG7CR_Producer_Response.csv"
)

COMPARISON_FILE = (
    OUTPUT_DIR
    / "V15SG7CR_Original_vs_FrontAware.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7CR_Summary.json"
)


# =============================================================================
# DEPLOYMENT CONTRACT
# =============================================================================

DEPLOYMENT_TIMES_DAYS = np.asarray(
    [
        100.0,
        250.0,
        500.0,
        1000.0,
    ],
    dtype=np.float64,
)

MAX_GLOBAL_L1 = 0.020
MAX_GLOBAL_L2 = 0.030
MAX_SNAPSHOT_L1 = 0.020
MAX_WEIGHTED_SNAPSHOT_L1 = 0.020

# Retained front-aware contract established by SG7B-10S / SG7B-11.
FRONT_THRESHOLD = 0.210
MIN_100D_RECOVERED_FRONTS = 744

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
            f"Could not import module:\n{path}"
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

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                chunk_size
            )

            if not chunk:

                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def find_npz_key(
    database,
    aliases,
    description,
):

    for key in aliases:

        if key in database:

            return key

    raise KeyError(
        f"Could not identify {description}.\n"
        f"Accepted aliases: {aliases}\n"
        f"Available keys: {list(database.keys())}"
    )


def flow_weighted_mean(
    values,
    weights,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    weights = np.asarray(
        weights,
        dtype=np.float64,
    )

    return float(
        np.sum(
            values
            *
            weights
        )
        /
        (
            np.sum(
                weights
            )
            +
            EPS
        )
    )


def profile_has_crossing(
    saturation,
    threshold=FRONT_THRESHOLD,
):

    shifted = (
        np.asarray(
            saturation,
            dtype=np.float64,
        )
        -
        float(
            threshold
        )
    )

    return np.any(
        shifted[
            :,
            :-1
        ]
        *
        shifted[
            :,
            1:
        ]
        <
        0.0,
        axis=1,
    )


# =============================================================================
# LOAD SG6 GEOMETRY
# =============================================================================

def load_sg6(
    workspace: Path,
):

    path = (
        workspace
        /
        SG6_RELATIVE
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing SG6 database:\n{path}"
        )

    db = np.load(
        path,
        allow_pickle=True,
    )

    xi_key = find_npz_key(
        db,
        [
            "xi",
            "transport_xi",
        ],
        "SG6 xi",
    )

    xyz_key = find_npz_key(
        db,
        [
            "xyz_m",
            "transport_xyz",
            "xyz",
            "streamline_xyz",
            "XYZ",
        ],
        "SG6 streamline XYZ",
    )

    tau_key = find_npz_key(
        db,
        [
            "tau_s",
            "tof_s",
            "tau",
            "transport_tau_s",
        ],
        "SG6 streamline TOF",
    )

    tau_end_key = find_npz_key(
        db,
        [
            "tau_end_s",
            "terminal_tau_s",
            "terminal_tof_s",
        ],
        "SG6 terminal TOF",
    )

    weight_key = find_npz_key(
        db,
        [
            "weights_m3_s",
            "weights",
            "flow_weights_m3_s",
        ],
        "SG6 flow weights",
    )

    producer_key = find_npz_key(
        db,
        [
            "producer",
            "producer_id",
            "producer_index",
        ],
        "SG6 producer identity",
    )

    streamline_id_key = find_npz_key(
        db,
        [
            "streamline_id",
            "id",
        ],
        "SG6 streamline ID",
    )

    path_length_key = None

    for key in [
        "path_length_m",
        "streamline_path_length_m",
    ]:

        if key in db:

            path_length_key = key

            break

    return {
        "path":
            path,

        "xi":
            np.asarray(
                db[
                    xi_key
                ],
                dtype=np.float32,
            ),

        "xyz_m":
            np.asarray(
                db[
                    xyz_key
                ],
                dtype=np.float64,
            ),

        "tau_s":
            np.asarray(
                db[
                    tau_key
                ],
                dtype=np.float64,
            ),

        "tau_end_s":
            np.asarray(
                db[
                    tau_end_key
                ],
                dtype=np.float64,
            ),

        "weights_m3_s":
            np.asarray(
                db[
                    weight_key
                ],
                dtype=np.float64,
            ),

        "producer":
            np.asarray(
                db[
                    producer_key
                ]
            ),

        "streamline_id":
            np.asarray(
                db[
                    streamline_id_key
                ]
            ),

        "path_length_m":
            (
                np.asarray(
                    db[
                        path_length_key
                    ],
                    dtype=np.float64,
                )
                if path_length_key
                is not None
                else None
            ),
    }


# =============================================================================
# LOAD ACCEPTED ORIGINAL SG7C DATABASE
#
# This is the immutable A/B reference and supplies the already accepted SG7A
# truth at the exact four physical deployment times.
# =============================================================================

def load_original_sg7c(
    workspace: Path,
):

    path = (
        workspace
        /
        ORIGINAL_SG7C_RELATIVE
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing original SG7C deployment database:\n{path}"
        )

    db = np.load(
        path,
        allow_pickle=True,
    )

    time_key = find_npz_key(
        db,
        [
            "times_days",
            "physical_times_days",
            "deployment_times_days",
        ],
        "SG7C deployment times",
    )

    truth_key = find_npz_key(
        db,
        [
            "SG7A_saturation",
            "truth_saturation",
            "reference_saturation",
            "S_truth",
        ],
        "SG7C SG7A truth",
    )

    prediction_key = find_npz_key(
        db,
        [
            "PI_RNN_saturation",
            "pirnn_saturation",
            "predicted_saturation",
            "S_pirnn",
        ],
        "SG7C frozen PI-RNN prediction",
    )

    return {
        "path":
            path,

        "times_days":
            np.asarray(
                db[
                    time_key
                ],
                dtype=np.float64,
            ),

        "truth":
            np.asarray(
                db[
                    truth_key
                ],
                dtype=np.float32,
            ),

        "prediction":
            np.asarray(
                db[
                    prediction_key
                ],
                dtype=np.float32,
            ),
    }


# =============================================================================
# INPUT CONSTRUCTION
# =============================================================================

def build_inputs(
    xi,
    terminal_days,
    physical_time_days,
    tD_scale,
):

    tD = (
        float(
            physical_time_days
        )
        /
        terminal_days
    )

    normalized = (
        tD
        /
        float(
            tD_scale
        )
    )

    if (
        np.any(
            normalized
            <
            -1.0e-8
        )
        or
        np.any(
            normalized
            >
            1.0
            +
            1.0e-6
        )
    ):

        raise RuntimeError(
            f"Deployment at {physical_time_days:.1f} days leaves "
            "the frozen PI-RNN training domain."
        )

    X = np.zeros(
        (
            len(
                terminal_days
            ),
            len(
                xi
            ),
            2,
        ),
        dtype=np.float32,
    )

    X[
        :,
        :,
        0
    ] = xi[
        None,
        :
    ]

    X[
        :,
        :,
        1
    ] = normalized[
        :,
        None
    ].astype(
        np.float32
    )

    return (
        X,
        tD,
        normalized,
    )


# =============================================================================
# FRONT METRICS
# =============================================================================

def front_metrics(
    prediction,
    truth,
):

    prediction = np.asarray(
        prediction,
        dtype=np.float64,
    )

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    truth_front = profile_has_crossing(
        truth
    )

    pred_front = profile_has_crossing(
        prediction
    )

    recovered = (
        truth_front
        &
        pred_front
    )

    per_profile_gap = np.min(
        np.abs(
            prediction
            -
            FRONT_THRESHOLD
        ),
        axis=1,
    )

    if np.any(
        truth_front
    ):

        conditioned_gap = float(
            np.mean(
                per_profile_gap[
                    truth_front
                ]
            )
        )

    else:

        conditioned_gap = np.nan

    return {
        "truth_front_count":
            int(
                np.sum(
                    truth_front
                )
            ),

        "pred_front_count":
            int(
                np.sum(
                    pred_front
                )
            ),

        "recovered_front_count":
            int(
                np.sum(
                    recovered
                )
            ),

        "conditioned_gap_mean":
            conditioned_gap,

        "global_gap_mean":
            float(
                np.mean(
                    per_profile_gap
                )
            ),
    }


# =============================================================================
# PRODUCER RESPONSE
# =============================================================================

def producer_response_rows(
    times_days,
    saturation,
    truth,
    producer,
    weights,
):

    rows = []

    unique_producers = np.unique(
        producer
    )

    for it, time_days in enumerate(
        times_days
    ):

        # The producer-end saturation is the terminal xi node.
        pred_terminal = saturation[
            it,
            :,
            -1
        ]

        truth_terminal = truth[
            it,
            :,
            -1
        ]

        for prod in unique_producers:

            mask = (
                producer
                ==
                prod
            )

            if not np.any(
                mask
            ):

                continue

            w = weights[
                mask
            ]

            rows.append(
                {
                    "time_days":
                        float(
                            time_days
                        ),

                    "producer":
                        str(
                            prod
                        ),

                    "streamlines":
                        int(
                            np.sum(
                                mask
                            )
                        ),

                    "flow_weight_m3_s":
                        float(
                            np.sum(
                                w
                            )
                        ),

                    "PI_RNN_terminal_saturation":
                        flow_weighted_mean(
                            pred_terminal[
                                mask
                            ],
                            w,
                        ),

                    "SG7A_terminal_saturation":
                        flow_weighted_mean(
                            truth_terminal[
                                mask
                            ],
                            w,
                        ),

                    "terminal_absolute_error":
                        flow_weighted_mean(
                            np.abs(
                                pred_terminal[
                                    mask
                                ]
                                -
                                truth_terminal[
                                    mask
                                ]
                            ),
                            w,
                        ),
                }
            )

    return rows


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7C-R front-aware frozen "
            "PI-RNN SGSim streamline redeployment."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_WORKSPACE
        ),
        help=(
            "Accepted 11x11 SG5C workspace containing SG6 and original SG7C."
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
        "PAD-Stream Version 15-SG7C-R"
    )

    print(
        "Front-Aware Frozen PI-RNN Redeployment on SGSim Streamlines"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO MODEL PARAMETERS WILL BE CHANGED."
    )

    print(
        "NO SG6 STREAMLINE GEOMETRY WILL BE CHANGED."
    )

    print(
        "NO TRANSPORT PHYSICS WILL BE CHANGED."
    )

    print(
        "NO GRID MAP-BACK WILL BE PERFORMED."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        SG7B10_SOURCE,
        SG7B11_SUMMARY,
        SG7B11_MANIFEST,
        FRONT_AWARE_MODEL,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7C-R prerequisite:\n{path}"
            )

    sg7b11_summary = load_json(
        SG7B11_SUMMARY
    )

    if (
        sg7b11_summary.get(
            "status"
        )
        !=
        "FRONT_AWARE_PI_RNN_FROZEN"
    ):

        raise RuntimeError(
            "SG7C-R requires SG7B-11 status:\n"
            "FRONT_AWARE_PI_RNN_FROZEN"
        )

    manifest = load_json(
        SG7B11_MANIFEST
    )

    expected_hash = manifest.get(
        "front_aware_frozen_sha256"
    )

    actual_hash = sha256_file(
        FRONT_AWARE_MODEL
    )

    if (
        expected_hash
        is None
        or
        actual_hash
        !=
        expected_hash
    ):

        raise RuntimeError(
            "Front-aware frozen model identity mismatch."
        )

    print(
        "\nFRONT-AWARE FROZEN MODEL"
    )

    print(
        f"  Model                   : "
        f"{FRONT_AWARE_MODEL.name}"
    )

    print(
        f"  SHA-256                 : "
        f"{actual_hash}"
    )

    print(
        "  Identity                : PASS"
    )

    # =========================================================================
    # AUTHORITATIVE INPUTS
    # =========================================================================

    sg10 = load_module(
        SG7B10_SOURCE,
        "pad_stream_sg7b10_for_sg7cr",
    )

    base = sg10.load_base_module()

    tf = sg10.tf

    dataset = base.load_dataset()

    tD_scale = float(
        dataset[
            "tD_scale"
        ][
            0
        ]
    )

    sg6 = load_sg6(
        workspace
    )

    original = load_original_sg7c(
        workspace
    )

    times_days = np.asarray(
        original[
            "times_days"
        ],
        dtype=np.float64,
    )

    if (
        times_days.shape
        !=
        DEPLOYMENT_TIMES_DAYS.shape
        or
        not np.allclose(
            times_days,
            DEPLOYMENT_TIMES_DAYS,
        )
    ):

        raise RuntimeError(
            "Original SG7C deployment times do not match the "
            "front-aware redeployment contract."
        )

    xi = sg6[
        "xi"
    ]

    xyz_m = sg6[
        "xyz_m"
    ]

    tau_s = sg6[
        "tau_s"
    ]

    tau_end_s = sg6[
        "tau_end_s"
    ]

    weights = sg6[
        "weights_m3_s"
    ]

    producer = sg6[
        "producer"
    ]

    streamline_id = sg6[
        "streamline_id"
    ]

    terminal_days = (
        tau_end_s
        /
        86400.0
    )

    truth = original[
        "truth"
    ]

    original_prediction = original[
        "prediction"
    ]

    n_streamlines = len(
        tau_end_s
    )

    n_nodes = len(
        xi
    )

    expected_shape = (
        len(
            times_days
        ),
        n_streamlines,
        n_nodes,
    )

    if truth.shape != expected_shape:

        raise RuntimeError(
            f"Unexpected original truth shape {truth.shape}; "
            f"expected {expected_shape}."
        )

    if original_prediction.shape != expected_shape:

        raise RuntimeError(
            f"Unexpected original prediction shape {original_prediction.shape}; "
            f"expected {expected_shape}."
        )

    if xyz_m.shape != (
        n_streamlines,
        n_nodes,
        3,
    ):

        raise RuntimeError(
            "SG6 XYZ shape is inconsistent."
        )

    if tau_s.shape != (
        n_streamlines,
        n_nodes,
    ):

        raise RuntimeError(
            "SG6 TOF shape is inconsistent."
        )

    print(
        "\nSG6 / ORIGINAL SG7C CONTRACT"
    )

    print(
        f"  Workspace               : "
        f"{workspace}"
    )

    print(
        f"  Streamlines             : "
        f"{n_streamlines:,}"
    )

    print(
        f"  xi nodes                : "
        f"{n_nodes}"
    )

    print(
        f"  Deployment times        : "
        f"{times_days.tolist()}"
    )

    print(
        f"  Minimum terminal TOF    : "
        f"{np.min(terminal_days):.3f} days"
    )

    print(
        f"  Median terminal TOF     : "
        f"{np.median(terminal_days):.3f} days"
    )

    print(
        f"  Maximum terminal TOF    : "
        f"{np.max(terminal_days):.3f} days"
    )

    print(
        f"  Total flow weight       : "
        f"{np.sum(weights) * 86400.0:.6f} m3/day"
    )

    print(
        f"  PI-RNN tD scale         : "
        f"{tD_scale:.6f}"
    )

    # =========================================================================
    # MODEL
    # =========================================================================

    model = tf.keras.models.load_model(
        FRONT_AWARE_MODEL
    )

    print(
        "\nDEPLOYING FRONT-AWARE FROZEN PI-RNN..."
    )

    predictions = []

    tD_all = []

    normalized_all = []

    metric_rows = []

    front_rows = []

    comparison_rows = []

    for it, time_days in enumerate(
        times_days
    ):

        X, tD, normalized = build_inputs(
            xi,
            terminal_days,
            time_days,
            tD_scale,
        )

        prediction = model.predict(
            X,
            batch_size=sg10.BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]

        predictions.append(
            prediction.astype(
                np.float32
            )
        )

        tD_all.append(
            tD.astype(
                np.float64
            )
        )

        normalized_all.append(
            normalized.astype(
                np.float64
            )
        )

        error = (
            prediction
            -
            truth[
                it
            ]
        )

        abs_error = np.abs(
            error
        )

        l1 = float(
            np.mean(
                abs_error
            )
        )

        l2 = float(
            np.sqrt(
                np.mean(
                    error ** 2
                )
            )
        )

        linf = float(
            np.max(
                abs_error
            )
        )

        profile_l1 = np.mean(
            abs_error,
            axis=1,
        )

        weighted_l1 = flow_weighted_mean(
            profile_l1,
            weights,
        )

        original_error = (
            original_prediction[
                it
            ]
            -
            truth[
                it
            ]
        )

        original_l1 = float(
            np.mean(
                np.abs(
                    original_error
                )
            )
        )

        original_weighted_l1 = flow_weighted_mean(
            np.mean(
                np.abs(
                    original_error
                ),
                axis=1,
            ),
            weights,
        )

        fnew = front_metrics(
            prediction,
            truth[
                it
            ],
        )

        fold = front_metrics(
            original_prediction[
                it
            ],
            truth[
                it
            ],
        )

        metric_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "L1":
                    l1,

                "L2":
                    l2,

                "Linf":
                    linf,

                "flow_weighted_L1":
                    weighted_l1,

                "tD_min":
                    float(
                        np.min(
                            tD
                        )
                    ),

                "tD_max":
                    float(
                        np.max(
                            tD
                        )
                    ),
            }
        )

        front_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                **fnew,
            }
        )

        comparison_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "original_L1":
                    original_l1,

                "front_aware_L1":
                    l1,

                "L1_change":
                    l1
                    -
                    original_l1,

                "original_weighted_L1":
                    original_weighted_l1,

                "front_aware_weighted_L1":
                    weighted_l1,

                "original_recovered_fronts":
                    fold[
                        "recovered_front_count"
                    ],

                "front_aware_recovered_fronts":
                    fnew[
                        "recovered_front_count"
                    ],

                "truth_fronts":
                    fnew[
                        "truth_front_count"
                    ],

                "original_conditioned_gap":
                    fold[
                        "conditioned_gap_mean"
                    ],

                "front_aware_conditioned_gap":
                    fnew[
                        "conditioned_gap_mean"
                    ],
            }
        )

        print(
            f"\n  Physical time = {time_days:.1f} days"
        )

        print(
            f"    tD range               : "
            f"{np.min(tD):.6f} -> {np.max(tD):.6f}"
        )

        print(
            f"    L1                     : "
            f"{l1:.6e}"
        )

        print(
            f"    L2                     : "
            f"{l2:.6e}"
        )

        print(
            f"    Linf                   : "
            f"{linf:.6e}"
        )

        print(
            f"    Flow-weighted L1       : "
            f"{weighted_l1:.6e}"
        )

        print(
            f"    Recovered fronts       : "
            f"{fnew['recovered_front_count']:,} / "
            f"{fnew['truth_front_count']:,}"
        )

        print(
            f"    Original fronts        : "
            f"{fold['recovered_front_count']:,} / "
            f"{fold['truth_front_count']:,}"
        )

        print(
            f"    Conditioned gap        : "
            f"{fnew['conditioned_gap_mean']:.6e}"
        )

    predictions = np.asarray(
        predictions,
        dtype=np.float32,
    )

    tD_all = np.asarray(
        tD_all,
        dtype=np.float64,
    )

    normalized_all = np.asarray(
        normalized_all,
        dtype=np.float64,
    )

    # =========================================================================
    # GLOBAL METRICS
    # =========================================================================

    global_error = (
        predictions.astype(
            np.float64
        )
        -
        truth.astype(
            np.float64
        )
    )

    global_l1 = float(
        np.mean(
            np.abs(
                global_error
            )
        )
    )

    global_l2 = float(
        np.sqrt(
            np.mean(
                global_error ** 2
            )
        )
    )

    global_linf = float(
        np.max(
            np.abs(
                global_error
            )
        )
    )

    max_snapshot_l1 = float(
        max(
            row[
                "L1"
            ]
            for row
            in metric_rows
        )
    )

    max_weighted_l1 = float(
        max(
            row[
                "flow_weighted_L1"
            ]
            for row
            in metric_rows
        )
    )

    max_tD = float(
        np.max(
            tD_all
        )
    )

    # =========================================================================
    # 100-DAY FRONT CONTRACT
    # =========================================================================

    idx100 = int(
        np.argmin(
            np.abs(
                times_days
                -
                100.0
            )
        )
    )

    front100 = front_rows[
        idx100
    ]

    original100 = comparison_rows[
        idx100
    ]

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "SG7B-11 front-aware freeze status verified",
            (
                sg7b11_summary.get(
                    "status"
                )
                ==
                "FRONT_AWARE_PI_RNN_FROZEN"
            ),
        ),

        (
            "Front-aware frozen model identity verified",
            (
                actual_hash
                ==
                expected_hash
            ),
        ),

        (
            "SG6 streamline count = 2662",
            n_streamlines
            ==
            2662,
        ),

        (
            "SG6 xi nodes = 201",
            n_nodes
            ==
            201,
        ),

        (
            "SG6 XYZ shape consistent",
            xyz_m.shape
            ==
            (
                n_streamlines,
                n_nodes,
                3,
            ),
        ),

        (
            "SG6 TOF shape consistent",
            tau_s.shape
            ==
            (
                n_streamlines,
                n_nodes,
            ),
        ),

        (
            "All terminal TOFs positive and finite",
            bool(
                np.all(
                    np.isfinite(
                        tau_end_s
                    )
                )
                and
                np.all(
                    tau_end_s
                    >
                    0.0
                )
            ),
        ),

        (
            "All streamline weights positive and finite",
            bool(
                np.all(
                    np.isfinite(
                        weights
                    )
                )
                and
                np.all(
                    weights
                    >
                    0.0
                )
            ),
        ),

        (
            "Streamline flow weights close injection rate",
            bool(
                np.isclose(
                    np.sum(
                        weights
                    )
                    *
                    86400.0,
                    714.285714,
                    rtol=5.0e-3,
                    atol=0.1,
                )
            ),
        ),

        (
            "All deployed tD values inside frozen domain",
            bool(
                max_tD
                <=
                tD_scale
                +
                1.0e-8
            ),
        ),

        (
            "PI-RNN predictions finite",
            bool(
                np.all(
                    np.isfinite(
                        predictions
                    )
                )
            ),
        ),

        (
            "SG7A deployment truth finite",
            bool(
                np.all(
                    np.isfinite(
                        truth
                    )
                )
            ),
        ),

        (
            "PI-RNN saturation lower bound respected",
            bool(
                np.min(
                    predictions
                )
                >=
                base.S_INITIAL
                -
                1.0e-7
            ),
        ),

        (
            "PI-RNN saturation upper bound respected",
            bool(
                np.max(
                    predictions
                )
                <=
                base.S_INJECTED
                +
                1.0e-7
            ),
        ),

        (
            "Global deployment L1 < 0.020",
            global_l1
            <
            MAX_GLOBAL_L1,
        ),

        (
            "Global deployment L2 < 0.030",
            global_l2
            <
            MAX_GLOBAL_L2,
        ),

        (
            "Every snapshot L1 < 0.020",
            all(
                row[
                    "L1"
                ]
                <
                MAX_SNAPSHOT_L1
                for row
                in metric_rows
            ),
        ),

        (
            "Every flow-weighted snapshot L1 < 0.020",
            all(
                row[
                    "flow_weighted_L1"
                ]
                <
                MAX_WEIGHTED_SNAPSHOT_L1
                for row
                in metric_rows
            ),
        ),

        (
            "100-day recovered fronts >= 744",
            front100[
                "recovered_front_count"
            ]
            >=
            MIN_100D_RECOVERED_FRONTS,
        ),

        (
            "100-day front recovery improves over original frozen deployment",
            front100[
                "recovered_front_count"
            ]
            >
            original100[
                "original_recovered_fronts"
            ],
        ),
    ]

    passed = all(
        flag
        for (
            _,
            flag,
        )
        in checks
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7C-R REDEPLOYMENT VALIDATION"
    )

    print(
        "=" * 78
    )

    for description, flag in checks:

        print(
            f"[{'PASS' if flag else 'FAIL'}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        f"Global L1                : "
        f"{global_l1:.6e}"
    )

    print(
        f"Global L2                : "
        f"{global_l2:.6e}"
    )

    print(
        f"Global Linf              : "
        f"{global_linf:.6e}"
    )

    print(
        f"Maximum snapshot L1      : "
        f"{max_snapshot_l1:.6e}"
    )

    print(
        f"Maximum weighted L1      : "
        f"{max_weighted_l1:.6e}"
    )

    print(
        f"Maximum deployed tD      : "
        f"{max_tD:.6f}"
    )

    print(
        f"Frozen PI-RNN tD limit   : "
        f"{tD_scale:.6f}"
    )

    print(
        "\n100-DAY A/B FRONT RESULT"
    )

    print(
        f"  SG7A fronts             : "
        f"{front100['truth_front_count']:,}"
    )

    print(
        f"  Original recovered      : "
        f"{original100['original_recovered_fronts']:,}"
    )

    print(
        f"  Front-aware recovered   : "
        f"{front100['recovered_front_count']:,}"
    )

    print(
        f"  Original gap            : "
        f"{original100['original_conditioned_gap']:.6e}"
    )

    print(
        f"  Front-aware gap         : "
        f"{front100['conditioned_gap_mean']:.6e}"
    )

    # =========================================================================
    # SAVE DATABASE
    #
    # Keep canonical SG7C-style aliases so SG7D-R can consume this directly.
    # =========================================================================

    save_payload = {
        "times_days":
            times_days.astype(
                np.float64
            ),

        "physical_times_days":
            times_days.astype(
                np.float64
            ),

        "PI_RNN_saturation":
            predictions.astype(
                np.float32
            ),

        "pirnn_saturation":
            predictions.astype(
                np.float32
            ),

        "SG7A_saturation":
            truth.astype(
                np.float32
            ),

        "truth_saturation":
            truth.astype(
                np.float32
            ),

        "original_frozen_PI_RNN_saturation":
            original_prediction.astype(
                np.float32
            ),

        "xi":
            xi.astype(
                np.float32
            ),

        "xyz_m":
            xyz_m.astype(
                np.float64
            ),

        "tau_s":
            tau_s.astype(
                np.float64
            ),

        "tau_end_s":
            tau_end_s.astype(
                np.float64
            ),

        "weights_m3_s":
            weights.astype(
                np.float64
            ),

        "producer":
            producer,

        "streamline_id":
            streamline_id,

        "tD":
            tD_all.astype(
                np.float64
            ),

        "normalized_tD":
            normalized_all.astype(
                np.float64
            ),

        "model_sha256":
            np.asarray(
                [
                    actual_hash
                ]
            ),

        "source_workspace":
            np.asarray(
                [
                    str(
                        workspace
                    )
                ]
            ),
    }

    if (
        sg6[
            "path_length_m"
        ]
        is not None
    ):

        save_payload[
            "path_length_m"
        ] = sg6[
            "path_length_m"
        ]

    np.savez_compressed(
        DEPLOYMENT_FILE,
        **save_payload,
    )

    # =========================================================================
    # TABLES
    # =========================================================================

    save_csv(
        METRICS_FILE,
        metric_rows,
    )

    save_csv(
        FRONT_FILE,
        front_rows,
    )

    save_csv(
        COMPARISON_FILE,
        comparison_rows,
    )

    producer_rows = producer_response_rows(
        times_days,
        predictions,
        truth,
        producer,
        weights,
    )

    save_csv(
        PRODUCER_FILE,
        producer_rows,
    )

    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times_days,
        [
            row[
                "original_L1"
            ]
            for row
            in comparison_rows
        ],
        marker="o",
        label="Original frozen",
    )

    ax.plot(
        times_days,
        [
            row[
                "front_aware_L1"
            ]
            for row
            in comparison_rows
        ],
        marker="s",
        label="Front-aware frozen",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "Deployment L1"
    )

    ax.set_title(
        "PAD-Stream V15-SG7C-R\n"
        "Original vs Front-Aware Deployment Error"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7CR_Error_vs_Time.png",
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

    ax.plot(
        times_days,
        [
            row[
                "original_recovered_fronts"
            ]
            for row
            in comparison_rows
        ],
        marker="o",
        label="Original frozen",
    )

    ax.plot(
        times_days,
        [
            row[
                "front_aware_recovered_fronts"
            ]
            for row
            in comparison_rows
        ],
        marker="s",
        label="Front-aware frozen",
    )

    ax.plot(
        times_days,
        [
            row[
                "truth_fronts"
            ]
            for row
            in comparison_rows
        ],
        linestyle="--",
        label="SG7A fronts",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "Resolved threshold fronts"
    )

    ax.set_title(
        "PAD-Stream V15-SG7C-R\n"
        "Front Recovery vs Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7CR_Front_Recovery_vs_Time.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # Representative 100-day profiles: select terminal-TOF quantiles.
    quantiles = [
        0.10,
        0.35,
        0.65,
        0.90,
    ]

    indices = []

    for q in quantiles:

        target = np.quantile(
            terminal_days,
            q,
        )

        idx = int(
            np.argmin(
                np.abs(
                    terminal_days
                    -
                    target
                )
            )
        )

        if idx not in indices:

            indices.append(
                idx
            )

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(
            12,
            9,
        )
    )

    axes = axes.ravel()

    for ax, idx in zip(
        axes,
        indices,
    ):

        ax.plot(
            xi,
            truth[
                idx100,
                idx
            ],
            label="SG7A",
        )

        ax.plot(
            xi,
            original_prediction[
                idx100,
                idx
            ],
            label="Original frozen",
        )

        ax.plot(
            xi,
            predictions[
                idx100,
                idx
            ],
            label="Front-aware frozen",
        )

        ax.axhline(
            FRONT_THRESHOLD,
            linestyle="--",
            label="S=0.21",
        )

        ax.set_title(
            f"Streamline {idx} | "
            f"TOF={terminal_days[idx]:.1f} d"
        )

        ax.set_xlabel(
            "xi"
        )

        ax.set_ylabel(
            "Saturation"
        )

        ax.legend()

    fig.suptitle(
        "PAD-Stream V15-SG7C-R\n"
        "Representative 100-Day Streamline Profiles"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7CR_Representative_Profiles_100d.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    if passed:

        status = (
            "FRONT_AWARE_FROZEN_PI_RNN_SUCCESSFULLY_REDEPLOYED"
        )

        recommendation = (
            "The independently frozen front-aware SG7B PI-RNN preserves "
            "SG7C streamline deployment accuracy while materially recovering "
            "the diagnosed early threshold fronts on the unchanged 11x11 SGSim "
            "streamline geometry. Proceed to conservative streamline-to-grid "
            "map-back using the SG7C-R deployment database."
        )

        next_milestone = (
            "V15-SG7D-R — Front-Aware Conservative "
            "Streamline-to-Grid Map-Back"
        )

    else:

        status = (
            "FRONT_AWARE_REDEPLOYMENT_VALIDATION_FAILED"
        )

        recommendation = (
            "Do not proceed to grid map-back. Diagnose the failed SG7C-R "
            "deployment gate while retaining both frozen model artifacts."
        )

        next_milestone = (
            "V15-SG7C-R1 — Front-Aware Redeployment Regression Audit"
        )

    summary = {
        "milestone":
            "V15-SG7C-R",

        "description":
            (
                "Front-aware frozen PI-RNN redeployment on accepted "
                "11x11 SGSim streamlines"
            ),

        "training_performed":
            False,

        "model_parameters_changed":
            False,

        "SG6_geometry_changed":
            False,

        "transport_physics_changed":
            False,

        "grid_mapback_performed":
            False,

        "workspace":
            str(
                workspace
            ),

        "model":
            str(
                FRONT_AWARE_MODEL
            ),

        "model_sha256":
            actual_hash,

        "streamlines":
            n_streamlines,

        "xi_nodes":
            n_nodes,

        "times_days":
            times_days.tolist(),

        "global_metrics": {
            "L1":
                global_l1,

            "L2":
                global_l2,

            "Linf":
                global_linf,

            "maximum_snapshot_L1":
                max_snapshot_l1,

            "maximum_weighted_L1":
                max_weighted_l1,

            "maximum_deployed_tD":
                max_tD,

            "tD_scale":
                tD_scale,
        },

        "100_day_front": {
            "truth_fronts":
                int(
                    front100[
                        "truth_front_count"
                    ]
                ),

            "original_recovered_fronts":
                int(
                    original100[
                        "original_recovered_fronts"
                    ]
                ),

            "front_aware_recovered_fronts":
                int(
                    front100[
                        "recovered_front_count"
                    ]
                ),

            "original_conditioned_gap":
                float(
                    original100[
                        "original_conditioned_gap"
                    ]
                ),

            "front_aware_conditioned_gap":
                float(
                    front100[
                        "conditioned_gap_mean"
                    ]
                ),
        },

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
    # OUTPUT LIST
    # =========================================================================

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nDeployment database:"
    )

    print(
        f"  {DEPLOYMENT_FILE.name}"
    )

    print(
        "\nTables:"
    )

    print(
        f"  {METRICS_FILE.name}"
    )

    print(
        f"  {FRONT_FILE.name}"
    )

    print(
        f"  {PRODUCER_FILE.name}"
    )

    print(
        f"  {COMPARISON_FILE.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7CR_Error_vs_Time.png"
    )

    print(
        "  V15SG7CR_Front_Recovery_vs_Time.png"
    )

    print(
        "  V15SG7CR_Representative_Profiles_100d.png"
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
            "V15-SG7C-R REDEPLOYMENT VALIDATION: PASS"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "FRONT-AWARE FROZEN SG7B PI-RNN SUCCESSFULLY "
            "REDEPLOYED ON SGSIM STREAMLINES"
        )

        print()

        print(
            "The SG6 streamline geometry and SG7A truth were unchanged."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7D-R — Front-Aware Conservative "
            "Streamline-to-Grid Map-Back"
        )

    else:

        print(
            "V15-SG7C-R REDEPLOYMENT VALIDATION: FAIL"
        )

        print()

        print(
            f"Next milestone:\n  {next_milestone}"
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
