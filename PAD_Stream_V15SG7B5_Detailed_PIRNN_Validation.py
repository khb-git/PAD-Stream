from pathlib import Path
import json
import zipfile
import shutil

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-5
# Detailed PI-RNN Diagnostic Validation Against Frozen SG7A
#
# PURPOSE
# -------
# Compare the SG7B-4:
#
#   1. BEST-DATA checkpoint
#   2. FINAL / stronger-physics checkpoint
#
# without retraining.
#
#
# QUESTIONS
# ---------
# 1. Did validation-data checkpoint selection choose a model that fits
#    SG7A well but violates the conservative FV physics?
#
# 2. Does the later/final model trade some data accuracy for substantially
#    better physics consistency?
#
# 3. Where are the largest errors?
#
#       - injector region
#       - high-gradient/front region
#       - smooth interior
#       - outlet region
#
# 4. At what dimensionless times are the errors largest?
#
# 5. Is SG7B-4 limited primarily by:
#
#       A) checkpoint selection,
#       B) loss weighting/schedule,
#       C) boundary behavior,
#       D) front-location capability?
#
#
# IMPORTANT
# ---------
# NO TRAINING occurs in SG7B-5.
#
# SG7A, SG7B-2, SG7B-3, and the original SG7B-4 run remain untouched.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

DATASET_FILE = (
    ROOT
    / "output"
    / "V15_SG7B3"
    / "SG7B3_REFERENCE_DATASET.npz"
)

SG7B4_DIR = (
    ROOT
    / "output"
    / "V15_SG7B4"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B5"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# -----------------------------------------------------------------------------
# Best corrected SG7B-4 model
# -----------------------------------------------------------------------------

BEST_MODEL_FILE = (
    SG7B4_DIR
    / "V15SG7B4_Best_Model_Serializable.keras"
)


# -----------------------------------------------------------------------------
# Original final model from first SG7B-4 training run
#
# This still contains the old Lambda layer, so we recover its weights.
# -----------------------------------------------------------------------------

LEGACY_FINAL_MODEL_FILE = (
    SG7B4_DIR
    / "V15SG7B4_Final_Model.keras"
)

RECOVERED_FINAL_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B5_Final_Recovered.weights.h5"
)

FINAL_CORRECTED_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B5_Final_Model_Serializable.keras"
)


# -----------------------------------------------------------------------------
# SG7B-4 history
# -----------------------------------------------------------------------------

HISTORY_FILE = (
    SG7B4_DIR
    / "V15SG7B4_Training_History.npz"
)


# -----------------------------------------------------------------------------
# SG7B-5 outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B5_Summary.json"
)

METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B5_Checkpoint_Metrics.npz"
)


# =============================================================================
# FROZEN PHYSICS
# =============================================================================

SWC = 0.20
SOR = 0.20

S_INITIAL = SWC
S_INJECTED = (
    1.0
    - SOR
)

MOBILE_RANGE = (
    S_INJECTED
    - S_INITIAL
)

KR_DISP_MAX = 0.80
KR_RES_MAX = 0.80

N_DISP = 2.0
N_RES = 2.0

MU_DISP = 0.50
MU_RES = 5.00

POROSITY = 0.20

NC = 0.10
PE_C = 22.0
LAMBDA_BC = 2.0

EPS = 1.0e-8


# =============================================================================
# NETWORK
# =============================================================================

SEQUENCE_LENGTH = 201
INPUT_FEATURES = 2

HIDDEN_SIZE = 64
N_LSTM_LAYERS = 2

BATCH_SIZE = 32


# =============================================================================
# LOAD DATASET
# =============================================================================

def load_dataset():

    if not DATASET_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-3 dataset:\n"
            f"{DATASET_FILE}"
        )

    data = np.load(
        DATASET_FILE
    )

    required = [
        "X_test",
        "Y_test",
        "tD_test",
        "xi",
        "tD_scale",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"Dataset field missing: {key}"
            )

    return {
        key: data[key]
        for key in required
    }


# =============================================================================
# PHYSICS FUNCTIONS
# =============================================================================

@tf.function
def effective_saturation_tf(
    S,
):

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = (
        S
        - SWC
    ) / span

    return tf.clip_by_value(
        Se,
        0.0,
        1.0,
    )


@tf.function
def fractional_flow_tf(
    S,
):

    Se = effective_saturation_tf(
        S
    )

    kr_disp = (
        KR_DISP_MAX
        * tf.pow(
            Se,
            N_DISP,
        )
    )

    kr_res = (
        KR_RES_MAX
        * tf.pow(
            1.0 - Se,
            N_RES,
        )
    )

    lambda_disp = (
        kr_disp
        / MU_DISP
    )

    lambda_res = (
        kr_res
        / MU_RES
    )

    return (
        lambda_disp
        /
        (
            lambda_disp
            + lambda_res
            + EPS
        )
    )


@tf.function
def diffusion_shape_tf(
    S,
):

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = (
        S
        - SWC
    ) / span

    Se = tf.clip_by_value(
        Se,
        1.0e-6,
        1.0 - 1.0e-6,
    )

    kr_res = (
        KR_RES_MAX
        * tf.pow(
            1.0 - Se,
            N_RES,
        )
    )

    fw = fractional_flow_tf(
        S
    )

    exponent = (
        -1.0
        / LAMBDA_BC
        - 1.0
    )

    raw = (
        kr_res
        * fw
        * tf.pow(
            Se,
            exponent,
        )
    )

    # Frozen SG7A normalization at Se = 0.5
    Se_mid = 0.5

    kr_disp_mid = (
        KR_DISP_MAX
        * Se_mid ** N_DISP
    )

    kr_res_mid = (
        KR_RES_MAX
        * (
            1.0
            - Se_mid
        ) ** N_RES
    )

    lambda_disp_mid = (
        kr_disp_mid
        / MU_DISP
    )

    lambda_res_mid = (
        kr_res_mid
        / MU_RES
    )

    fw_mid = (
        lambda_disp_mid
        /
        (
            lambda_disp_mid
            + lambda_res_mid
        )
    )

    norm = (
        kr_res_mid
        * fw_mid
        * Se_mid ** exponent
    )

    return (
        raw
        / norm
    )


# =============================================================================
# CORRECT SERIALIZABLE ARCHITECTURE
# =============================================================================

def build_corrected_model():

    inputs = tf.keras.Input(
        shape=(
            SEQUENCE_LENGTH,
            INPUT_FEATURES,
        ),
        name="xi_tD_sequence",
    )

    x = inputs

    for layer_id in range(
        N_LSTM_LAYERS
    ):

        x = tf.keras.layers.LSTM(
            HIDDEN_SIZE,
            return_sequences=True,
            name=(
                f"lstm_{layer_id + 1}"
            ),
        )(x)

    raw = (
        tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(
                1
            ),
            name="raw_saturation",
        )(x)
    )

    sigmoid_output = (
        tf.keras.layers.Activation(
            "sigmoid",
            name="saturation_sigmoid",
        )(raw)
    )

    outputs = (
        tf.keras.layers.Rescaling(
            scale=MOBILE_RANGE,
            offset=S_INITIAL,
            name="physical_saturation",
        )(sigmoid_output)
    )

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name=(
            "PAD_Stream_"
            "V15SG7B5_ValidationModel"
        ),
    )


# =============================================================================
# LEGACY FINAL MODEL FOR WEIGHT RECOVERY
# =============================================================================

def build_legacy_model():

    inputs = tf.keras.Input(
        shape=(
            SEQUENCE_LENGTH,
            INPUT_FEATURES,
        ),
        name="xi_tD_sequence",
    )

    x = inputs

    for layer_id in range(
        N_LSTM_LAYERS
    ):

        x = tf.keras.layers.LSTM(
            HIDDEN_SIZE,
            return_sequences=True,
            name=(
                f"lstm_{layer_id + 1}"
            ),
        )(x)

    raw = (
        tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(
                1
            ),
            name="raw_saturation",
        )(x)
    )

    outputs = tf.keras.layers.Lambda(
        lambda z:
        (
            S_INITIAL
            +
            MOBILE_RANGE
            * tf.sigmoid(z)
        ),
        output_shape=(
            SEQUENCE_LENGTH,
            1,
        ),
        name="physical_saturation",
    )(raw)

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
    )


# =============================================================================
# RECOVER FINAL CHECKPOINT
# =============================================================================

def recover_final_checkpoint():

    if not LEGACY_FINAL_MODEL_FILE.exists():

        raise FileNotFoundError(
            "Legacy final SG7B-4 model not found:\n"
            f"{LEGACY_FINAL_MODEL_FILE}"
        )

    print(
        "\nRecovering SG7B-4 final checkpoint..."
    )

    with zipfile.ZipFile(
        LEGACY_FINAL_MODEL_FILE,
        "r",
    ) as archive:

        weight_name = None

        for name in archive.namelist():

            if name.endswith(
                "model.weights.h5"
            ):

                weight_name = name
                break

        if weight_name is None:

            raise RuntimeError(
                "Could not find model.weights.h5 "
                "inside final SG7B-4 archive."
            )

        with archive.open(
            weight_name
        ) as source:

            with open(
                RECOVERED_FINAL_WEIGHTS_FILE,
                "wb",
            ) as destination:

                shutil.copyfileobj(
                    source,
                    destination,
                )

    legacy_model = (
        build_legacy_model()
    )

    legacy_model.load_weights(
        RECOVERED_FINAL_WEIGHTS_FILE
    )

    corrected_model = (
        build_corrected_model()
    )

    for layer_name in [
        "lstm_1",
        "lstm_2",
        "raw_saturation",
    ]:

        corrected_model.get_layer(
            layer_name
        ).set_weights(
            legacy_model.get_layer(
                layer_name
            ).get_weights()
        )

    corrected_model.save(
        FINAL_CORRECTED_MODEL_FILE
    )

    print(
        "  Final checkpoint recovery : PASS"
    )

    print(
        f"  {FINAL_CORRECTED_MODEL_FILE}"
    )

    return corrected_model


# =============================================================================
# INPUT AT ARBITRARY TIME
# =============================================================================

def build_input_for_time(
    base_x,
    normalized_time,
):

    xi = (
        base_x[
            :,
            :,
            0:1
        ]
    )

    n_nodes = (
        tf.shape(
            xi
        )[1]
    )

    normalized_time = tf.reshape(
        normalized_time,
        (
            -1,
            1,
            1,
        ),
    )

    time_feature = tf.tile(
        normalized_time,
        (
            1,
            n_nodes,
            1,
        ),
    )

    return tf.concat(
        [
            xi,
            time_feature,
        ],
        axis=2,
    )


# =============================================================================
# DIFFERENTIABLE FV RESIDUAL
# =============================================================================

def finite_volume_residual(
    model,
    X,
    tD_scale,
):

    xi = (
        X[
            0,
            :,
            0
        ]
    )

    dxi = (
        xi[1]
        - xi[0]
    )

    t_norm = (
        X[
            :,
            0,
            1
        ]
    )

    t_actual = (
        t_norm
        * tD_scale
    )

    dt_reference = (
        tD_scale
        / 800.0
    )

    t_minus = tf.maximum(
        t_actual
        - dt_reference,
        0.0,
    )

    t_plus = tf.minimum(
        t_actual
        + dt_reference,
        tD_scale,
    )

    denominator = (
        t_plus
        - t_minus
        + EPS
    )

    X_minus = build_input_for_time(
        X,
        t_minus
        / tD_scale,
    )

    X_plus = build_input_for_time(
        X,
        t_plus
        / tD_scale,
    )

    S_minus = (
        model(
            X_minus,
            training=False,
        )[
            :,
            :,
            0
        ]
    )

    S_plus = (
        model(
            X_plus,
            training=False,
        )[
            :,
            :,
            0
        ]
    )

    S = (
        model(
            X,
            training=False,
        )[
            :,
            :,
            0
        ]
    )

    S_t = (
        S_plus
        - S_minus
    ) / tf.reshape(
        denominator,
        (
            -1,
            1,
        ),
    )

    batch_size = (
        tf.shape(
            S
        )[0]
    )

    # -------------------------------------------------------------------------
    # ADVECTIVE FLUX
    # -------------------------------------------------------------------------

    face_xi = tf.linspace(
        0.0,
        1.0,
        SEQUENCE_LENGTH + 1,
    )

    u_face = tf.exp(
        NC
        * face_xi
    )

    fw = fractional_flow_tf(
        S
    )

    f_injected = (
        fractional_flow_tf(
            tf.constant(
                S_INJECTED,
                dtype=tf.float32,
            )
        )
    )

    F_left = (
        tf.ones(
            (
                batch_size,
                1,
            ),
            dtype=tf.float32,
        )
        *
        u_face[0]
        *
        f_injected
    )

    F_internal = (
        fw[
            :,
            :-1
        ]
        *
        u_face[
            1:-1
        ][
            None,
            :
        ]
    )

    F_outlet = (
        fw[
            :,
            -1:
        ]
        *
        u_face[-1]
    )

    F_adv = tf.concat(
        [
            F_left,
            F_internal,
            F_outlet,
        ],
        axis=1,
    )

    div_adv = (
        F_adv[
            :,
            1:
        ]
        -
        F_adv[
            :,
            :-1
        ]
    ) / dxi

    # -------------------------------------------------------------------------
    # CAPILLARY FLUX
    # -------------------------------------------------------------------------

    D_cell = diffusion_shape_tf(
        S
    )

    D_internal = (
        0.5
        * (
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

    grad_internal = (
        S[
            :,
            1:
        ]
        -
        S[
            :,
            :-1
        ]
    ) / dxi

    G_internal = (
        POROSITY
        / PE_C
        *
        D_internal
        *
        grad_internal
    )

    D_injected = diffusion_shape_tf(
        tf.constant(
            S_INJECTED,
            dtype=tf.float32,
        )
    )

    D_left = (
        0.5
        * (
            D_injected
            +
            D_cell[
                :,
                0
            ]
        )
    )

    grad_left = (
        S[
            :,
            0
        ]
        -
        S_INJECTED
    ) / (
        0.5
        * dxi
    )

    G_left = (
        POROSITY
        / PE_C
        *
        D_left
        *
        grad_left
    )[
        :,
        None
    ]

    G_right = tf.zeros(
        (
            batch_size,
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

    residual = (
        S_t
        +
        div_adv
        -
        div_cap
    )

    scale = (
        tf.abs(
            S_t
        )
        +
        tf.abs(
            div_adv
        )
        +
        tf.abs(
            div_cap
        )
        +
        1.0e-4
    )

    relative = (
        residual
        / scale
    )

    return (
        residual,
        relative,
        S,
    )


# =============================================================================
# REGION MASKS
# =============================================================================

def build_region_masks(
    truth,
    xi,
):
    """
    Build masks profile-by-profile.

    Injector:
        first 5% of xi.

    Outlet:
        last 5%.

    High-gradient:
        top 10% of |dS/dxi| for each truth profile.

    Interior:
        all points that are neither injector, outlet,
        nor high-gradient.
    """

    n_profiles, n_nodes = (
        truth.shape
    )

    injector_mask = np.zeros(
        (
            n_profiles,
            n_nodes,
        ),
        dtype=bool,
    )

    outlet_mask = np.zeros_like(
        injector_mask
    )

    high_gradient_mask = np.zeros_like(
        injector_mask
    )

    n_boundary = max(
        3,
        int(
            0.05
            * n_nodes
        ),
    )

    injector_mask[
        :,
        :n_boundary
    ] = True

    outlet_mask[
        :,
        -n_boundary:
    ] = True

    for p in range(
        n_profiles
    ):

        gradient = np.abs(
            np.gradient(
                truth[p],
                xi,
                edge_order=2,
            )
        )

        threshold = np.quantile(
            gradient,
            0.90,
        )

        high_gradient_mask[
            p
        ] = (
            gradient
            >= threshold
        )

    interior_mask = ~(
        injector_mask
        |
        outlet_mask
        |
        high_gradient_mask
    )

    return {
        "injector":
            injector_mask,

        "outlet":
            outlet_mask,

        "high_gradient":
            high_gradient_mask,

        "interior":
            interior_mask,
    }


# =============================================================================
# CHECKPOINT EVALUATION
# =============================================================================

def evaluate_checkpoint(
    name,
    model,
    dataset,
):

    print(
        "\n"
        + "-" * 78
    )

    print(
        f"EVALUATING: {name}"
    )

    print(
        "-" * 78
    )

    X_test = (
        dataset[
            "X_test"
        ].astype(
            np.float32
        )
    )

    truth = (
        dataset[
            "Y_test"
        ][
            :,
            :,
            0
        ]
    )

    tD_test = (
        dataset[
            "tD_test"
        ]
    )

    xi = (
        dataset[
            "xi"
        ]
    )

    prediction = (
        model.predict(
            X_test,
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    )

    error = (
        prediction
        - truth
    )

    abs_error = np.abs(
        error
    )

    # -------------------------------------------------------------------------
    # Global profile errors
    # -------------------------------------------------------------------------

    L1 = float(
        np.mean(
            abs_error
        )
    )

    L2 = float(
        np.sqrt(
            np.mean(
                error ** 2
            )
        )
    )

    Linf = float(
        np.max(
            abs_error
        )
    )

    profile_L1 = np.mean(
        abs_error,
        axis=1,
    )

    # -------------------------------------------------------------------------
    # Locate global max error
    # -------------------------------------------------------------------------

    max_flat_index = int(
        np.argmax(
            abs_error
        )
    )

    max_profile_index, max_xi_index = (
        np.unravel_index(
            max_flat_index,
            abs_error.shape,
        )
    )

    max_error_tD = float(
        tD_test[
            max_profile_index
        ]
    )

    max_error_xi = float(
        xi[
            max_xi_index
        ]
    )

    max_truth_value = float(
        truth[
            max_profile_index,
            max_xi_index
        ]
    )

    max_prediction_value = float(
        prediction[
            max_profile_index,
            max_xi_index
        ]
    )

    # -------------------------------------------------------------------------
    # Regional errors
    # -------------------------------------------------------------------------

    masks = build_region_masks(
        truth,
        xi,
    )

    regional = {}

    for region_name, mask in (
        masks.items()
    ):

        region_error = (
            error[
                mask
            ]
        )

        regional[
            region_name
        ] = {
            "L1":
                float(
                    np.mean(
                        np.abs(
                            region_error
                        )
                    )
                ),

            "L2":
                float(
                    np.sqrt(
                        np.mean(
                            region_error ** 2
                        )
                    )
                ),

            "Linf":
                float(
                    np.max(
                        np.abs(
                            region_error
                        )
                    )
                ),
        }

    # -------------------------------------------------------------------------
    # FV physics
    # -------------------------------------------------------------------------

    X_tf = tf.constant(
        X_test,
        dtype=tf.float32,
    )

    tD_scale = tf.constant(
        float(
            dataset[
                "tD_scale"
            ][0]
        ),
        dtype=tf.float32,
    )

    (
        residual_tf,
        relative_tf,
        _,
    ) = finite_volume_residual(
        model,
        X_tf,
        tD_scale,
    )

    residual = (
        residual_tf.numpy()
    )

    relative = (
        relative_tf.numpy()
    )

    fv_RMS = float(
        np.sqrt(
            np.mean(
                residual ** 2
            )
        )
    )

    fv_relative_MAE = float(
        np.mean(
            np.abs(
                relative
            )
        )
    )

    fv_relative_RMS = float(
        np.sqrt(
            np.mean(
                relative ** 2
            )
        )
    )

    # -------------------------------------------------------------------------
    # Regional FV residual
    # -------------------------------------------------------------------------

    regional_fv = {}

    for region_name, mask in (
        masks.items()
    ):

        region_relative = (
            relative[
                mask
            ]
        )

        regional_fv[
            region_name
        ] = {
            "relative_MAE":
                float(
                    np.mean(
                        np.abs(
                            region_relative
                        )
                    )
                ),

            "relative_RMS":
                float(
                    np.sqrt(
                        np.mean(
                            region_relative ** 2
                        )
                    )
                ),
        }

    # -------------------------------------------------------------------------
    # Mass / storage
    # -------------------------------------------------------------------------

    true_mass = np.trapezoid(
        truth,
        xi,
        axis=1,
    )

    pred_mass = np.trapezoid(
        prediction,
        xi,
        axis=1,
    )

    mass_error = (
        pred_mass
        - true_mass
    )

    mass_relative = (
        np.abs(
            mass_error
        )
        /
        (
            np.abs(
                true_mass
            )
            + 1.0e-12
        )
    )

    mass_MAE = float(
        np.mean(
            np.abs(
                mass_error
            )
        )
    )

    mass_relative_MAE = float(
        np.mean(
            mass_relative
        )
    )

    mass_relative_max = float(
        np.max(
            mass_relative
        )
    )

    # -------------------------------------------------------------------------
    # Boundary endpoint statistics
    # -------------------------------------------------------------------------

    inlet_truth = (
        truth[
            :,
            0
        ]
    )

    inlet_prediction = (
        prediction[
            :,
            0
        ]
    )

    outlet_truth = (
        truth[
            :,
            -1
        ]
    )

    outlet_prediction = (
        prediction[
            :,
            -1
        ]
    )

    inlet_MAE = float(
        np.mean(
            np.abs(
                inlet_prediction
                - inlet_truth
            )
        )
    )

    outlet_MAE = float(
        np.mean(
            np.abs(
                outlet_prediction
                - outlet_truth
            )
        )
    )

    # -------------------------------------------------------------------------
    # Time-band diagnostics
    # -------------------------------------------------------------------------

    tD_min = float(
        np.min(
            tD_test
        )
    )

    tD_max = float(
        np.max(
            tD_test
        )
    )

    tD_span = (
        tD_max
        - tD_min
    )

    early_limit = (
        tD_min
        + tD_span
        / 3.0
    )

    late_start = (
        tD_min
        + 2.0
        * tD_span
        / 3.0
    )

    early_mask = (
        tD_test
        <= early_limit
    )

    middle_mask = (
        (
            tD_test
            > early_limit
        )
        &
        (
            tD_test
            < late_start
        )
    )

    late_mask = (
        tD_test
        >= late_start
    )

    time_bands = {}

    for band_name, band_mask in [
        (
            "early",
            early_mask,
        ),
        (
            "middle",
            middle_mask,
        ),
        (
            "late",
            late_mask,
        ),
    ]:

        if np.any(
            band_mask
        ):

            band_error = (
                error[
                    band_mask
                ]
            )

            time_bands[
                band_name
            ] = {
                "L1":
                    float(
                        np.mean(
                            np.abs(
                                band_error
                            )
                        )
                    ),

                "L2":
                    float(
                        np.sqrt(
                            np.mean(
                                band_error ** 2
                            )
                        )
                    ),
            }

    # -------------------------------------------------------------------------
    # Print
    # -------------------------------------------------------------------------

    print(
        f"  L1                      : "
        f"{L1:.6e}"
    )

    print(
        f"  L2                      : "
        f"{L2:.6e}"
    )

    print(
        f"  Linf                    : "
        f"{Linf:.6e}"
    )

    print(
        f"  Predicted saturation    : "
        f"{prediction.min():.6f} "
        f"-> "
        f"{prediction.max():.6f}"
    )

    print(
        "\n  FV PHYSICS"
    )

    print(
        f"    Relative MAE          : "
        f"{fv_relative_MAE:.6e}"
    )

    print(
        f"    Relative RMS          : "
        f"{fv_relative_RMS:.6e}"
    )

    print(
        "\n  MASS"
    )

    print(
        f"    Relative MAE          : "
        f"{mass_relative_MAE:.6e}"
    )

    print(
        f"    Maximum relative      : "
        f"{mass_relative_max:.6e}"
    )

    print(
        "\n  MAXIMUM POINTWISE ERROR"
    )

    print(
        f"    tD                    : "
        f"{max_error_tD:.6f}"
    )

    print(
        f"    xi                    : "
        f"{max_error_xi:.6f}"
    )

    print(
        f"    Truth                 : "
        f"{max_truth_value:.6f}"
    )

    print(
        f"    Prediction            : "
        f"{max_prediction_value:.6f}"
    )

    return {
        "name":
            name,

        "prediction":
            prediction,

        "truth":
            truth,

        "error":
            error,

        "profile_L1":
            profile_L1,

        "relative_residual":
            relative,

        "L1":
            L1,

        "L2":
            L2,

        "Linf":
            Linf,

        "min_prediction":
            float(
                prediction.min()
            ),

        "max_prediction":
            float(
                prediction.max()
            ),

        "fv_RMS":
            fv_RMS,

        "fv_relative_MAE":
            fv_relative_MAE,

        "fv_relative_RMS":
            fv_relative_RMS,

        "mass_MAE":
            mass_MAE,

        "mass_relative_MAE":
            mass_relative_MAE,

        "mass_relative_max":
            mass_relative_max,

        "inlet_MAE":
            inlet_MAE,

        "outlet_MAE":
            outlet_MAE,

        "regional":
            regional,

        "regional_fv":
            regional_fv,

        "time_bands":
            time_bands,

        "max_error_tD":
            max_error_tD,

        "max_error_xi":
            max_error_xi,

        "max_truth_value":
            max_truth_value,

        "max_prediction_value":
            max_prediction_value,
    }


# =============================================================================
# CHECKPOINT SCORE
# =============================================================================

def checkpoint_score(
    result,
):
    """
    Diagnostic score only.

    This is NOT yet a training loss.

    Purpose:
        compare data, physics, and mass simultaneously.

    Terms are normalized by practical scales so one raw quantity
    does not dominate merely because of units.
    """

    data_term = (
        result[
            "L1"
        ]
        / 0.02
    )

    physics_term = (
        result[
            "fv_relative_MAE"
        ]
        / 0.05
    )

    mass_term = (
        result[
            "mass_relative_MAE"
        ]
        / 0.02
    )

    score = (
        data_term
        +
        physics_term
        +
        mass_term
    )

    return float(
        score
    )


# =============================================================================
# DECISION LOGIC
# =============================================================================

def determine_diagnosis(
    best_result,
    final_result,
):

    best_score = (
        checkpoint_score(
            best_result
        )
    )

    final_score = (
        checkpoint_score(
            final_result
        )
    )

    physics_improvement = (
        best_result[
            "fv_relative_MAE"
        ]
        /
        max(
            final_result[
                "fv_relative_MAE"
            ],
            1.0e-12,
        )
    )

    data_degradation = (
        final_result[
            "L1"
        ]
        /
        max(
            best_result[
                "L1"
            ],
            1.0e-12,
        )
    )

    if (
        physics_improvement
        >= 2.0
        and
        data_degradation
        <= 1.5
    ):

        diagnosis = (
            "CHECKPOINT_SELECTION"
        )

        recommendation = (
            "The later checkpoint substantially improves "
            "FV consistency without an unacceptable data-error "
            "increase. Revise checkpoint selection to include "
            "physics and mass terms before changing architecture."
        )

    elif (
        best_result[
            "fv_relative_MAE"
        ] > 0.10
        and
        final_result[
            "fv_relative_MAE"
        ] > 0.10
    ):

        diagnosis = (
            "LOSS_WEIGHTING_OR_TRAINING"
        )

        recommendation = (
            "Both checkpoints remain too physics-inconsistent. "
            "Retain the plain-LSTM architecture initially, but "
            "revise physics weighting, warm-up, and checkpoint "
            "selection before testing more complex architecture."
        )

    else:

        diagnosis = (
            "MIXED"
        )

        recommendation = (
            "Checkpoint selection and training balance both "
            "contribute. Use the regional/time diagnostics before "
            "deciding whether an auxiliary front coordinate is needed."
        )

    return {
        "best_score":
            best_score,

        "final_score":
            final_score,

        "physics_improvement_factor":
            float(
                physics_improvement
            ),

        "data_error_ratio_final_over_best":
            float(
                data_degradation
            ),

        "diagnosis":
            diagnosis,

        "recommendation":
            recommendation,
    }


# =============================================================================
# PLOTS
# =============================================================================

def plot_checkpoint_profiles(
    dataset,
    best_result,
    final_result,
):

    xi = dataset[
        "xi"
    ]

    tD = dataset[
        "tD_test"
    ]

    truth = best_result[
        "truth"
    ]

    positions = np.linspace(
        0,
        len(tD) - 1,
        5,
        dtype=int,
    )

    fig, ax = plt.subplots(
        figsize=(
            10,
            7,
        )
    )

    for position in positions:

        ax.plot(
            xi,
            truth[
                position
            ],
            linewidth=2.0,
            label=(
                "Truth "
                f"tD={tD[position]:.2f}"
            ),
        )

        ax.plot(
            xi,
            best_result[
                "prediction"
            ][
                position
            ],
            linestyle="--",
            linewidth=1.3,
            label=(
                "Best-data "
                f"tD={tD[position]:.2f}"
            ),
        )

        ax.plot(
            xi,
            final_result[
                "prediction"
            ][
                position
            ],
            linestyle=":",
            linewidth=1.5,
            label=(
                "Final "
                f"tD={tD[position]:.2f}"
            ),
        )

    ax.set_xlabel(
        r"TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-5\n"
        "Best-Data vs Final PI-RNN Checkpoint"
    )

    ax.legend(
        fontsize=7,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B5_Checkpoint_Profiles.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_error_vs_time(
    dataset,
    best_result,
    final_result,
):

    tD = dataset[
        "tD_test"
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        tD,
        best_result[
            "profile_L1"
        ],
        label="Best-data checkpoint",
    )

    ax.plot(
        tD,
        final_result[
            "profile_L1"
        ],
        label="Final checkpoint",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile L1 error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-5\n"
        "Prediction Error vs Dimensionless Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B5_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_regional_error(
    best_result,
    final_result,
):

    regions = [
        "injector",
        "high_gradient",
        "interior",
        "outlet",
    ]

    best_values = np.array([
        best_result[
            "regional"
        ][
            region
        ][
            "L1"
        ]
        for region
        in regions
    ])

    final_values = np.array([
        final_result[
            "regional"
        ][
            region
        ][
            "L1"
        ]
        for region
        in regions
    ])

    x = np.arange(
        len(
            regions
        )
    )

    width = 0.35

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        x
        - width / 2,
        best_values,
        width,
        label="Best-data",
    )

    ax.bar(
        x
        + width / 2,
        final_values,
        width,
        label="Final",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        regions
    )

    ax.set_ylabel(
        "Regional saturation L1 error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-5\n"
        "Spatial Error Localization"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B5_Regional_Error.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_regional_physics(
    best_result,
    final_result,
):

    regions = [
        "injector",
        "high_gradient",
        "interior",
        "outlet",
    ]

    best_values = np.array([
        best_result[
            "regional_fv"
        ][
            region
        ][
            "relative_MAE"
        ]
        for region
        in regions
    ])

    final_values = np.array([
        final_result[
            "regional_fv"
        ][
            region
        ][
            "relative_MAE"
        ]
        for region
        in regions
    ])

    x = np.arange(
        len(
            regions
        )
    )

    width = 0.35

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        x
        - width / 2,
        best_values,
        width,
        label="Best-data",
    )

    ax.bar(
        x
        + width / 2,
        final_values,
        width,
        label="Final",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        regions
    )

    ax.set_ylabel(
        "Regional FV relative MAE"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-5\n"
        "Physics Residual Localization"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B5_Regional_FV_Residual.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_error_maps(
    dataset,
    best_result,
    final_result,
):

    xi = dataset[
        "xi"
    ]

    tD = dataset[
        "tD_test"
    ]

    # -------------------------------------------------------------------------
    # Best-data map
    # -------------------------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    im = ax.imshow(
        np.abs(
            best_result[
                "error"
            ]
        ),
        origin="lower",
        aspect="auto",
        extent=[
            xi[0],
            xi[-1],
            tD[0],
            tD[-1],
        ],
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "|S_PI-RNN - S_SG7A|"
    )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        r"$t_D$"
    )

    ax.set_title(
        "V15-SG7B-5 — Best-Data Checkpoint Error Map"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B5_Best_Error_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # -------------------------------------------------------------------------
    # Final map
    # -------------------------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    im = ax.imshow(
        np.abs(
            final_result[
                "error"
            ]
        ),
        origin="lower",
        aspect="auto",
        extent=[
            xi[0],
            xi[-1],
            tD[0],
            tD[-1],
        ],
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "|S_PI-RNN - S_SG7A|"
    )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        r"$t_D$"
    )

    ax.set_title(
        "V15-SG7B-5 — Final Checkpoint Error Map"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B5_Final_Error_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# SAVE NUMERICAL RESULTS
# =============================================================================

def save_metrics_npz(
    dataset,
    best_result,
    final_result,
):

    np.savez_compressed(
        METRICS_FILE,

        xi=
            dataset[
                "xi"
            ],

        tD_test=
            dataset[
                "tD_test"
            ],

        truth=
            best_result[
                "truth"
            ],

        best_prediction=
            best_result[
                "prediction"
            ],

        final_prediction=
            final_result[
                "prediction"
            ],

        best_error=
            best_result[
                "error"
            ],

        final_error=
            final_result[
                "error"
            ],

        best_profile_L1=
            best_result[
                "profile_L1"
            ],

        final_profile_L1=
            final_result[
                "profile_L1"
            ],

        best_relative_FV=
            best_result[
                "relative_residual"
            ],

        final_relative_FV=
            final_result[
                "relative_residual"
            ],
    )


# =============================================================================
# JSON HELPERS
# =============================================================================

def clean_result_for_json(
    result,
):

    return {
        "L1":
            result[
                "L1"
            ],

        "L2":
            result[
                "L2"
            ],

        "Linf":
            result[
                "Linf"
            ],

        "minimum_prediction":
            result[
                "min_prediction"
            ],

        "maximum_prediction":
            result[
                "max_prediction"
            ],

        "fv_RMS":
            result[
                "fv_RMS"
            ],

        "fv_relative_MAE":
            result[
                "fv_relative_MAE"
            ],

        "fv_relative_RMS":
            result[
                "fv_relative_RMS"
            ],

        "mass_MAE":
            result[
                "mass_MAE"
            ],

        "mass_relative_MAE":
            result[
                "mass_relative_MAE"
            ],

        "mass_relative_max":
            result[
                "mass_relative_max"
            ],

        "inlet_MAE":
            result[
                "inlet_MAE"
            ],

        "outlet_MAE":
            result[
                "outlet_MAE"
            ],

        "regional_error":
            result[
                "regional"
            ],

        "regional_FV":
            result[
                "regional_fv"
            ],

        "time_bands":
            result[
                "time_bands"
            ],

        "maximum_error_location": {
            "tD":
                result[
                    "max_error_tD"
                ],

            "xi":
                result[
                    "max_error_xi"
                ],

            "truth":
                result[
                    "max_truth_value"
                ],

            "prediction":
                result[
                    "max_prediction_value"
                ],
        },
    }


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    best_result,
    final_result,
    diagnosis,
    history_info,
):

    summary = {
        "milestone":
            "V15-SG7B-5",

        "description":
            (
                "Detailed diagnostic validation of "
                "SG7B-4 PI-RNN checkpoints against "
                "frozen SG7A truth"
            ),

        "status":
            "DIAGNOSTIC_COMPLETE",

        "no_retraining":
            True,

        "architecture": {
            "type":
                "plain stacked LSTM",

            "hidden_size":
                HIDDEN_SIZE,

            "layers":
                N_LSTM_LAYERS,

            "fourier_features":
                False,

            "film":
                False,

            "front_coordinate":
                False,
        },

        "best_data_checkpoint":
            clean_result_for_json(
                best_result
            ),

        "final_checkpoint":
            clean_result_for_json(
                final_result
            ),

        "training_history":
            history_info,

        "diagnosis":
            diagnosis,

        "reference_truth_FV_relative_MAE":
            2.002532e-03,

        "decision_rule":
            (
                "Do not change architecture until checkpoint "
                "selection and physics-loss balance have been "
                "diagnosed from existing training."
            ),

        "next_action":
            diagnosis[
                "recommendation"
            ],
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
# HISTORY DIAGNOSTICS
# =============================================================================

def analyze_history():

    if not HISTORY_FILE.exists():

        return {
            "available":
                False,
        }

    data = np.load(
        HISTORY_FILE
    )

    history = {
        key:
            np.asarray(
                data[
                    key
                ]
            )
        for key
        in data.files
    }

    val_data = (
        history[
            "val_data"
        ]
    )

    val_phys = (
        history[
            "val_phys"
        ]
    )

    val_mass = (
        history[
            "val_mass"
        ]
    )

    epoch = (
        history[
            "epoch"
        ]
    )

    lambda_phys = (
        history[
            "lambda_phys"
        ]
    )

    best_data_index = int(
        np.argmin(
            val_data
        )
    )

    best_physics_index = int(
        np.argmin(
            val_phys
        )
    )

    best_mass_index = int(
        np.argmin(
            val_mass
        )
    )

    return {
        "available":
            True,

        "epochs_completed":
            int(
                len(
                    epoch
                )
            ),

        "best_data_epoch":
            int(
                epoch[
                    best_data_index
                ]
            ),

        "best_data_MSE":
            float(
                val_data[
                    best_data_index
                ]
            ),

        "physics_weight_at_best_data":
            float(
                lambda_phys[
                    best_data_index
                ]
            ),

        "best_physics_epoch":
            int(
                epoch[
                    best_physics_index
                ]
            ),

        "best_validation_FV_loss":
            float(
                val_phys[
                    best_physics_index
                ]
            ),

        "data_MSE_at_best_physics":
            float(
                val_data[
                    best_physics_index
                ]
            ),

        "best_mass_epoch":
            int(
                epoch[
                    best_mass_index
                ]
            ),

        "best_validation_mass_loss":
            float(
                val_mass[
                    best_mass_index
                ]
            ),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7B-5"
    )

    print(
        "Detailed PI-RNN Diagnostic Validation"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    # -------------------------------------------------------------------------
    # LOAD DATA
    # -------------------------------------------------------------------------

    dataset = (
        load_dataset()
    )

    print(
        "\nTEST DATASET"
    )

    print(
        f"  Profiles                : "
        f"{len(dataset['X_test'])}"
    )

    print(
        f"  xi nodes                : "
        f"{len(dataset['xi'])}"
    )

    print(
        f"  tD range                : "
        f"{dataset['tD_test'].min():.6f} "
        f"-> "
        f"{dataset['tD_test'].max():.6f}"
    )

    # -------------------------------------------------------------------------
    # BEST-DATA MODEL
    # -------------------------------------------------------------------------

    if not BEST_MODEL_FILE.exists():

        raise FileNotFoundError(
            "Corrected SG7B-4 best model "
            "not found:\n"
            f"{BEST_MODEL_FILE}"
        )

    print(
        "\nLoading best-data checkpoint..."
    )

    best_model = (
        tf.keras.models.load_model(
            BEST_MODEL_FILE
        )
    )

    print(
        "  Best-data checkpoint load : PASS"
    )

    # -------------------------------------------------------------------------
    # FINAL MODEL
    # -------------------------------------------------------------------------

    final_model = (
        recover_final_checkpoint()
    )

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    history_info = (
        analyze_history()
    )

    if history_info[
        "available"
    ]:

        print(
            "\nTRAINING HISTORY DIAGNOSTICS"
        )

        print(
            f"  Epochs completed        : "
            f"{history_info['epochs_completed']}"
        )

        print(
            f"  Best data epoch         : "
            f"{history_info['best_data_epoch']}"
        )

        print(
            f"  Best physics epoch      : "
            f"{history_info['best_physics_epoch']}"
        )

        print(
            f"  Best mass epoch         : "
            f"{history_info['best_mass_epoch']}"
        )

    # -------------------------------------------------------------------------
    # EVALUATE
    # -------------------------------------------------------------------------

    best_result = (
        evaluate_checkpoint(
            "BEST-DATA CHECKPOINT",
            best_model,
            dataset,
        )
    )

    final_result = (
        evaluate_checkpoint(
            "FINAL CHECKPOINT",
            final_model,
            dataset,
        )
    )

    # -------------------------------------------------------------------------
    # DIAGNOSIS
    # -------------------------------------------------------------------------

    diagnosis = (
        determine_diagnosis(
            best_result,
            final_result,
        )
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "SG7B-5 DIAGNOSTIC DECISION"
    )

    print(
        "=" * 78
    )

    print(
        f"Best-data composite score : "
        f"{diagnosis['best_score']:.4f}"
    )

    print(
        f"Final composite score     : "
        f"{diagnosis['final_score']:.4f}"
    )

    print(
        f"Physics improvement factor: "
        f"{diagnosis['physics_improvement_factor']:.3f}"
    )

    print(
        f"Final/best data error ratio: "
        f"{diagnosis['data_error_ratio_final_over_best']:.3f}"
    )

    print(
        f"\nDiagnosis:"
    )

    print(
        f"  {diagnosis['diagnosis']}"
    )

    print(
        "\nRecommendation:"
    )

    print(
        f"  {diagnosis['recommendation']}"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # FIGURES
    # -------------------------------------------------------------------------

    plot_checkpoint_profiles(
        dataset,
        best_result,
        final_result,
    )

    plot_error_vs_time(
        dataset,
        best_result,
        final_result,
    )

    plot_regional_error(
        best_result,
        final_result,
    )

    plot_regional_physics(
        best_result,
        final_result,
    )

    plot_error_maps(
        dataset,
        best_result,
        final_result,
    )

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    save_metrics_npz(
        dataset,
        best_result,
        final_result,
    )

    save_summary(
        best_result,
        final_result,
        diagnosis,
        history_info,
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
        "\nRecovered final model:"
    )

    print(
        "  V15SG7B5_Final_Model_Serializable.keras"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B5_Checkpoint_Profiles.png"
    )

    print(
        "  V15SG7B5_Error_vs_tD.png"
    )

    print(
        "  V15SG7B5_Regional_Error.png"
    )

    print(
        "  V15SG7B5_Regional_FV_Residual.png"
    )

    print(
        "  V15SG7B5_Best_Error_Map.png"
    )

    print(
        "  V15SG7B5_Final_Error_Map.png"
    )

    print(
        "\nNumerical data:"
    )

    print(
        "  V15SG7B5_Checkpoint_Metrics.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B5_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-5 COMPLETED"
    )

    print(
        "NO SG7B PI-RNN HAS BEEN FROZEN YET."
    )

    print(
        "The next milestone will be selected "
        "from the diagnostic result above."
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()