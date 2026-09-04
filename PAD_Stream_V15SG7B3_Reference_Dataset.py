from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-3
# Reference-Case PI-RNN Dataset and Training Design
#
# PURPOSE
# -------
# Build a validated sequence-learning dataset from the frozen SG7A master
# transport solution.
#
# REFERENCE PHYSICS
# -----------------
#
# Nc        = 0.10
# Pe_c      = 22
# lambda_BC = 2
#
#
# LEARNING PROBLEM
# ----------------
#
# Input:
#
#       xi sequence
#       +
#       global dimensionless time tD
#
# Output:
#
#       full saturation sequence
#
#       S(xi_0), ..., S(xi_200)
#
#
# IMPORTANT
# ---------
# No neural network is trained in SG7B-3.
#
# This milestone only:
#
#   - loads frozen SG7A truth
#   - creates deterministic time-based train/validation/test splits
#   - builds model-ready arrays
#   - validates the splits
#   - saves the dataset contract for SG7B-4
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7A_FILE = (
    ROOT
    / "output"
    / "V15_SG7A"
    / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B3"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATASET_FILE = (
    OUTPUT_DIR
    / "SG7B3_REFERENCE_DATASET.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B3_Summary.json"
)

SPLIT_CSV = (
    OUTPUT_DIR
    / "V15SG7B3_TimeSplit.csv"
)


# =============================================================================
# FROZEN REFERENCE PHYSICS
# =============================================================================

NC = 0.10
PE_C = 22.0
LAMBDA_BC = 2.0

SWC = 0.20
SOR = 0.20

S_INITIAL = SWC
S_INJECTED = 1.0 - SOR

POROSITY = 0.20


# =============================================================================
# SPLIT DESIGN
# =============================================================================

# The split is performed using repeating groups of 20 consecutive snapshots:
#
#     14 train
#      3 validation
#      3 test
#
# This gives approximately:
#
#     70 / 15 / 15 %
#
# and ensures validation/test occur as withheld contiguous time intervals.

BLOCK_SIZE = 20

TRAIN_PER_BLOCK = 14
VAL_PER_BLOCK = 3
TEST_PER_BLOCK = 3

assert (
    TRAIN_PER_BLOCK
    + VAL_PER_BLOCK
    + TEST_PER_BLOCK
    == BLOCK_SIZE
)


# =============================================================================
# LOAD SG7A
# =============================================================================

def load_sg7a():

    if not SG7A_FILE.exists():

        raise FileNotFoundError(
            f"Frozen SG7A file not found:\n"
            f"{SG7A_FILE}"
        )

    data = np.load(
        SG7A_FILE
    )

    required = [
        "xi",
        "master_tD",
        "master_saturation",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"Missing SG7A dataset field: {key}"
            )

    xi = np.asarray(
        data["xi"],
        dtype=np.float64,
    )

    tD = np.asarray(
        data["master_tD"],
        dtype=np.float64,
    )

    saturation = np.asarray(
        data["master_saturation"],
        dtype=np.float64,
    )

    expected_shape = (
        len(tD),
        len(xi),
    )

    if saturation.shape != expected_shape:

        raise ValueError(
            "Unexpected master saturation shape.\n"
            f"Expected: {expected_shape}\n"
            f"Found   : {saturation.shape}"
        )

    return (
        xi,
        tD,
        saturation,
    )


# =============================================================================
# TIME SPLIT
# =============================================================================

def make_split_indices(
    n_snapshots,
):

    train = []
    val = []
    test = []

    split_label = np.empty(
        n_snapshots,
        dtype="U8",
    )

    for idx in range(
        n_snapshots
    ):

        position = (
            idx
            % BLOCK_SIZE
        )

        if position < TRAIN_PER_BLOCK:

            train.append(
                idx
            )

            split_label[idx] = (
                "train"
            )

        elif position < (
            TRAIN_PER_BLOCK
            + VAL_PER_BLOCK
        ):

            val.append(
                idx
            )

            split_label[idx] = (
                "val"
            )

        else:

            test.append(
                idx
            )

            split_label[idx] = (
                "test"
            )

    return (
        np.array(
            train,
            dtype=int,
        ),
        np.array(
            val,
            dtype=int,
        ),
        np.array(
            test,
            dtype=int,
        ),
        split_label,
    )


# =============================================================================
# BUILD SEQUENCE INPUTS
# =============================================================================

def build_sequence_inputs(
    xi,
    tD_values,
):
    """
    Build plain-LSTM sequence input.

    For every profile:

        feature 0 = xi
        feature 1 = tD

    Shape:

        [N_samples, N_xi, 2]
    """

    n_samples = len(
        tD_values
    )

    n_xi = len(
        xi
    )

    X = np.zeros(
        (
            n_samples,
            n_xi,
            2,
        ),
        dtype=np.float32,
    )

    for n, time_value in enumerate(
        tD_values
    ):

        X[
            n,
            :,
            0
        ] = xi

        X[
            n,
            :,
            1
        ] = time_value

    return X


# =============================================================================
# TIME NORMALIZATION
# =============================================================================

def normalize_time(
    tD,
):
    """
    Reference-case normalization.

    xi already lies in [0,1].

    Map:

        tD -> tD / max(tD)

    so both model inputs remain approximately O(1).
    """

    tD_max = float(
        np.max(
            tD
        )
    )

    if tD_max <= 0.0:

        raise ValueError(
            "Invalid tD maximum."
        )

    normalized = (
        tD
        / tD_max
    )

    return (
        normalized,
        tD_max,
    )


# =============================================================================
# DATASET ASSEMBLY
# =============================================================================

def build_dataset(
    xi,
    tD,
    saturation,
    train_idx,
    val_idx,
    test_idx,
):

    tD_normalized, tD_scale = (
        normalize_time(
            tD
        )
    )

    X_all = (
        build_sequence_inputs(
            xi,
            tD_normalized,
        )
    )

    # Output shape expected by sequence model:
    #
    #     [samples, sequence, 1]

    Y_all = saturation[
        :,
        :,
        None,
    ].astype(
        np.float32
    )

    dataset = {
        "X_train":
            X_all[
                train_idx
            ],

        "Y_train":
            Y_all[
                train_idx
            ],

        "tD_train":
            tD[
                train_idx
            ],

        "index_train":
            train_idx,

        "X_val":
            X_all[
                val_idx
            ],

        "Y_val":
            Y_all[
                val_idx
            ],

        "tD_val":
            tD[
                val_idx
            ],

        "index_val":
            val_idx,

        "X_test":
            X_all[
                test_idx
            ],

        "Y_test":
            Y_all[
                test_idx
            ],

        "tD_test":
            tD[
                test_idx
            ],

        "index_test":
            test_idx,

        "xi":
            xi.astype(
                np.float32
            ),

        "tD_all":
            tD.astype(
                np.float64
            ),

        "tD_scale":
            np.array(
                [
                    tD_scale
                ],
                dtype=np.float64,
            ),

        "Nc":
            np.array(
                [
                    NC
                ],
                dtype=np.float64,
            ),

        "Pe_c":
            np.array(
                [
                    PE_C
                ],
                dtype=np.float64,
            ),

        "lambda_BC":
            np.array(
                [
                    LAMBDA_BC
                ],
                dtype=np.float64,
            ),
    }

    return dataset


# =============================================================================
# SPLIT CSV
# =============================================================================

def write_split_csv(
    tD,
    labels,
):

    with open(
        SPLIT_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(
            f
        )

        writer.writerow(
            [
                "snapshot",
                "tD",
                "split",
            ]
        )

        for idx in range(
            len(tD)
        ):

            writer.writerow(
                [
                    idx,
                    float(
                        tD[idx]
                    ),
                    labels[idx],
                ]
            )


# =============================================================================
# VALIDATION
# =============================================================================

def validate_dataset(
    xi,
    tD,
    saturation,
    train_idx,
    val_idx,
    test_idx,
    dataset,
):

    train_set = set(
        train_idx.tolist()
    )

    val_set = set(
        val_idx.tolist()
    )

    test_set = set(
        test_idx.tolist()
    )

    checks = []

    # -------------------------------------------------------------------------
    # ORIGINAL DATA
    # -------------------------------------------------------------------------

    checks.append(
        (
            "201 xi nodes",
            len(
                xi
            ) == 201,
        )
    )

    checks.append(
        (
            "801 SG7A snapshots",
            len(
                tD
            ) == 801,
        )
    )

    checks.append(
        (
            "Master saturation shape correct",
            saturation.shape
            ==
            (
                801,
                201,
            ),
        )
    )

    # -------------------------------------------------------------------------
    # SPLIT DISJOINTNESS
    # -------------------------------------------------------------------------

    checks.append(
        (
            "Train/validation indices disjoint",
            len(
                train_set
                &
                val_set
            ) == 0,
        )
    )

    checks.append(
        (
            "Train/test indices disjoint",
            len(
                train_set
                &
                test_set
            ) == 0,
        )
    )

    checks.append(
        (
            "Validation/test indices disjoint",
            len(
                val_set
                &
                test_set
            ) == 0,
        )
    )

    # -------------------------------------------------------------------------
    # COMPLETE COVERAGE
    # -------------------------------------------------------------------------

    union = (
        train_set
        |
        val_set
        |
        test_set
    )

    checks.append(
        (
            "All snapshots assigned exactly once",
            len(
                union
            ) == len(
                tD
            ),
        )
    )

    # -------------------------------------------------------------------------
    # FINITENESS
    # -------------------------------------------------------------------------

    checks.append(
        (
            "Training input finite",
            np.all(
                np.isfinite(
                    dataset[
                        "X_train"
                    ]
                )
            ),
        )
    )

    checks.append(
        (
            "Training targets finite",
            np.all(
                np.isfinite(
                    dataset[
                        "Y_train"
                    ]
                )
            ),
        )
    )

    checks.append(
        (
            "Validation targets finite",
            np.all(
                np.isfinite(
                    dataset[
                        "Y_val"
                    ]
                )
            ),
        )
    )

    checks.append(
        (
            "Test targets finite",
            np.all(
                np.isfinite(
                    dataset[
                        "Y_test"
                    ]
                )
            ),
        )
    )

    # -------------------------------------------------------------------------
    # SATURATION BOUNDS
    # -------------------------------------------------------------------------

    checks.append(
        (
            "Saturation lower bound respected",
            np.min(
                saturation
            )
            >= S_INITIAL
            - 1.0e-7,
        )
    )

    checks.append(
        (
            "Saturation upper bound respected",
            np.max(
                saturation
            )
            <= S_INJECTED
            + 1.0e-7,
        )
    )

    # -------------------------------------------------------------------------
    # SEQUENCE SHAPE
    # -------------------------------------------------------------------------

    checks.append(
        (
            "Training sequence has 201 nodes",
            dataset[
                "X_train"
            ].shape[1]
            == 201,
        )
    )

    checks.append(
        (
            "Input contains xi and tD only",
            dataset[
                "X_train"
            ].shape[2]
            == 2,
        )
    )

    checks.append(
        (
            "Output has one saturation channel",
            dataset[
                "Y_train"
            ].shape[2]
            == 1,
        )
    )

    # -------------------------------------------------------------------------
    # NORMALIZATION
    # -------------------------------------------------------------------------

    checks.append(
        (
            "Normalized xi lies in [0,1]",
            (
                np.min(
                    dataset[
                        "X_train"
                    ][
                        :,
                        :,
                        0
                    ]
                )
                >= 0.0
                and
                np.max(
                    dataset[
                        "X_train"
                    ][
                        :,
                        :,
                        0
                    ]
                )
                <= 1.0
            ),
        )
    )

    checks.append(
        (
            "Normalized tD lies in [0,1]",
            (
                np.min(
                    dataset[
                        "X_train"
                    ][
                        :,
                        :,
                        1
                    ]
                )
                >= 0.0
                and
                np.max(
                    dataset[
                        "X_train"
                    ][
                        :,
                        :,
                        1
                    ]
                )
                <= 1.0
            ),
        )
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-3 DATASET VALIDATION"
    )

    print(
        "=" * 78
    )

    all_passed = True

    for description, passed in checks:

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"[{status:4s}] "
            f"{description}"
        )

        if not passed:

            all_passed = False

    print(
        "=" * 78
    )

    if not all_passed:

        raise RuntimeError(
            "V15-SG7B-3 dataset validation failed. "
            "Do not begin PI-RNN training."
        )

    print(
        "V15-SG7B-3 REFERENCE DATASET VALIDATION: PASS"
    )


# =============================================================================
# PLOTS
# =============================================================================

def plot_time_split(
    tD,
    labels,
):

    fig, ax = plt.subplots(
        figsize=(
            11,
            4,
        )
    )

    mapping = {
        "train": 0,
        "val": 1,
        "test": 2,
    }

    y = np.array([
        mapping[
            item
        ]
        for item in labels
    ])

    ax.scatter(
        tD,
        y,
        s=12,
    )

    ax.set_yticks(
        [
            0,
            1,
            2,
        ]
    )

    ax.set_yticklabels(
        [
            "Train",
            "Validation",
            "Test",
        ]
    )

    ax.set_xlabel(
        r"Dimensionless time $t_D$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-3\n"
        "Reference PI-RNN Time-Split Design"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B3_TimeSplit.png",
        dpi=300,
    )

    plt.close(fig)


def plot_representative_profiles(
    xi,
    tD,
    saturation,
    train_idx,
    val_idx,
    test_idx,
):

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(
            9,
            11,
        ),
        sharex=True,
    )

    split_info = [
        (
            "Training",
            train_idx,
        ),
        (
            "Validation",
            val_idx,
        ),
        (
            "Test",
            test_idx,
        ),
    ]

    for ax, (
        name,
        indices,
    ) in zip(
        axes,
        split_info,
    ):

        if len(
            indices
        ) <= 5:

            selected = indices

        else:

            selected_positions = np.linspace(
                0,
                len(
                    indices
                ) - 1,
                5,
                dtype=int,
            )

            selected = indices[
                selected_positions
            ]

        for idx in selected:

            ax.plot(
                xi,
                saturation[
                    idx
                ],
                label=(
                    rf"$t_D={tD[idx]:.2f}$"
                ),
            )

        ax.set_ylabel(
            "Saturation"
        )

        ax.set_title(
            name
        )

        ax.legend()

    axes[-1].set_xlabel(
        r"TOF coordinate $\xi$"
    )

    fig.suptitle(
        "PAD-Stream V15-SG7B-3\n"
        "Representative Frozen SG7A Targets",
        fontsize=14,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B3_Representative_Targets.png",
        dpi=300,
    )

    plt.close(fig)


def plot_dataset_coverage(
    tD,
    saturation,
    train_idx,
    val_idx,
    test_idx,
):

    mean_sat = np.mean(
        saturation,
        axis=1,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.scatter(
        tD[
            train_idx
        ],
        mean_sat[
            train_idx
        ],
        s=12,
        label="Train",
    )

    ax.scatter(
        tD[
            val_idx
        ],
        mean_sat[
            val_idx
        ],
        s=18,
        label="Validation",
    )

    ax.scatter(
        tD[
            test_idx
        ],
        mean_sat[
            test_idx
        ],
        s=18,
        label="Test",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Mean profile saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-3\n"
        "Train / Validation / Test Physics Coverage"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B3_Dataset_Coverage.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# SAVE DATASET
# =============================================================================

def save_dataset(
    dataset,
):

    np.savez_compressed(
        DATASET_FILE,
        **dataset,
    )


# =============================================================================
# SAVE SUMMARY
# =============================================================================

def save_summary(
    xi,
    tD,
    saturation,
    train_idx,
    val_idx,
    test_idx,
    dataset,
):

    n_total = len(
        tD
    )

    summary = {
        "milestone":
            "V15-SG7B-3",

        "description":
            (
                "Reference-case PI-RNN dataset "
                "and training design"
            ),

        "status":
            "PASS",

        "source":
            "Frozen V15-SG7A master solution",

        "reference_physics": {
            "Nc":
                NC,

            "Pe_c":
                PE_C,

            "lambda_bc":
                LAMBDA_BC,

            "phi":
                POROSITY,
        },

        "learning_contract": {
            "input":
                "[xi, normalized tD]",

            "output":
                "S(xi,tD)",

            "sequence_nodes":
                int(
                    len(
                        xi
                    )
                ),

            "input_features":
                2,

            "output_features":
                1,

            "front_location_input":
                False,

            "shock_saturation_input":
                False,

            "fourier_features":
                False,

            "film":
                False,

            "architecture_family":
                "plain stacked LSTM",
        },

        "dataset": {
            "total_profiles":
                int(
                    n_total
                ),

            "profile_length":
                int(
                    len(
                        xi
                    )
                ),

            "total_saturation_values":
                int(
                    saturation.size
                ),

            "tD_min":
                float(
                    tD.min()
                ),

            "tD_max":
                float(
                    tD.max()
                ),

            "tD_normalization_scale":
                float(
                    dataset[
                        "tD_scale"
                    ][0]
                ),
        },

        "split": {
            "strategy":
                (
                    "deterministic repeating contiguous "
                    "time-block holdout"
                ),

            "block_size":
                BLOCK_SIZE,

            "train_per_block":
                TRAIN_PER_BLOCK,

            "validation_per_block":
                VAL_PER_BLOCK,

            "test_per_block":
                TEST_PER_BLOCK,

            "train_profiles":
                int(
                    len(
                        train_idx
                    )
                ),

            "validation_profiles":
                int(
                    len(
                        val_idx
                    )
                ),

            "test_profiles":
                int(
                    len(
                        test_idx
                    )
                ),

            "train_fraction":
                float(
                    len(
                        train_idx
                    )
                    / n_total
                ),

            "validation_fraction":
                float(
                    len(
                        val_idx
                    )
                    / n_total
                ),

            "test_fraction":
                float(
                    len(
                        test_idx
                    )
                    / n_total
                ),
        },

        "approved_physics_loss":
            (
                "V15-SG7B-2 conservative "
                "finite-volume residual"
            ),

        "initial_training_loss_design": {
            "data":
                True,

            "finite_volume_physics":
                True,

            "boundary":
                True,

            "global_mass_balance":
                True,

            "front_anchor":
                False,

            "shock_anchor":
                False,

            "curvature_penalty":
                False,

            "monotonicity":
                False,
        },

        "next_milestone":
            (
                "V15-SG7B-4 - reference-case "
                "plain-LSTM PI-RNN training"
            ),
    }

    with open(
        SUMMARY_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7B-3"
    )

    print(
        "Reference-Case PI-RNN Dataset and Training Design"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    (
        xi,
        tD,
        saturation,
    ) = load_sg7a()

    print(
        "\nFROZEN SG7A MASTER DATABASE"
    )

    print(
        f"  Profiles                : "
        f"{len(tD):,}"
    )

    print(
        f"  xi nodes                : "
        f"{len(xi)}"
    )

    print(
        f"  Saturation values       : "
        f"{saturation.size:,}"
    )

    print(
        f"  tD range                : "
        f"{tD.min():.6f} -> "
        f"{tD.max():.6f}"
    )

    # -------------------------------------------------------------------------
    # SPLIT
    # -------------------------------------------------------------------------

    (
        train_idx,
        val_idx,
        test_idx,
        labels,
    ) = make_split_indices(
        len(
            tD
        )
    )

    print(
        "\nDATASET SPLIT"
    )

    print(
        f"  Training profiles       : "
        f"{len(train_idx):,} "
        f"({100.0 * len(train_idx) / len(tD):.2f}%)"
    )

    print(
        f"  Validation profiles     : "
        f"{len(val_idx):,} "
        f"({100.0 * len(val_idx) / len(tD):.2f}%)"
    )

    print(
        f"  Test profiles           : "
        f"{len(test_idx):,} "
        f"({100.0 * len(test_idx) / len(tD):.2f}%)"
    )

    # -------------------------------------------------------------------------
    # BUILD
    # -------------------------------------------------------------------------

    dataset = build_dataset(
        xi,
        tD,
        saturation,
        train_idx,
        val_idx,
        test_idx,
    )

    print(
        "\nMODEL-READY ARRAYS"
    )

    print(
        f"  X_train                 : "
        f"{dataset['X_train'].shape}"
    )

    print(
        f"  Y_train                 : "
        f"{dataset['Y_train'].shape}"
    )

    print(
        f"  X_val                   : "
        f"{dataset['X_val'].shape}"
    )

    print(
        f"  Y_val                   : "
        f"{dataset['Y_val'].shape}"
    )

    print(
        f"  X_test                  : "
        f"{dataset['X_test'].shape}"
    )

    print(
        f"  Y_test                  : "
        f"{dataset['Y_test'].shape}"
    )

    print(
        f"  tD normalization scale  : "
        f"{dataset['tD_scale'][0]:.6f}"
    )

    # -------------------------------------------------------------------------
    # VALIDATE
    # -------------------------------------------------------------------------

    validate_dataset(
        xi,
        tD,
        saturation,
        train_idx,
        val_idx,
        test_idx,
        dataset,
    )

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    save_dataset(
        dataset
    )

    write_split_csv(
        tD,
        labels,
    )

    plot_time_split(
        tD,
        labels,
    )

    plot_representative_profiles(
        xi,
        tD,
        saturation,
        train_idx,
        val_idx,
        test_idx,
    )

    plot_dataset_coverage(
        tD,
        saturation,
        train_idx,
        val_idx,
        test_idx,
    )

    save_summary(
        xi,
        tD,
        saturation,
        train_idx,
        val_idx,
        test_idx,
        dataset,
    )

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nDataset:"
    )

    print(
        "  SG7B3_REFERENCE_DATASET.npz"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B3_TimeSplit.csv"
    )

    print(
        "  V15SG7B3_TimeSplit.png"
    )

    print(
        "  V15SG7B3_Representative_Targets.png"
    )

    print(
        "  V15SG7B3_Dataset_Coverage.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B3_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-3 COMPLETED SUCCESSFULLY"
    )

    print(
        "Reference PI-RNN training contract:"
    )

    print(
        "  Input  : [xi, normalized tD]"
    )

    print(
        "  Output : S(xi, tD)"
    )

    print(
        "  Model  : plain stacked LSTM"
    )

    print(
        "  Physics: conservative FV residual"
    )

    print(
        "\nNext milestone:"
    )

    print(
        "V15-SG7B-4 — Reference-Case "
        "Plain-LSTM PI-RNN Training"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()