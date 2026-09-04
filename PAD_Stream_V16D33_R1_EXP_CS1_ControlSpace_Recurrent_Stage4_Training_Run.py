#!/usr/bin/env python3
"""
PAD-Stream V16D-33-R1
EXP-CS1 Frozen Control-Space Recurrent Stage-4 Training Run
+ Validation-Only Checkpoint Selection

Executes the exact V16D-33 contract.

Allowed
-------
* Open TRAIN predictors and Stage-4 Y targets.
* Use TRAIN only for gradient updates.
* Open VALIDATION predictors and Stage-4 Y targets.
* Use VALIDATION only for val_loss, early stopping, checkpoint selection,
  and post-selection diagnostics.
* Freeze the best validation-selected checkpoint and architecture.

Forbidden
---------
* Open any LOCKED_OOD_TEST X or Y array.
* Use OOD for normalization, tuning, selection, thresholds, or diagnostics.
* Change architecture, loss, optimizer, seed, batch size, epochs, or patience.
* Add a physics loss, M_face predictor, or direct rate/BHP input channel.
* Silently rerun the same experiment after a started training attempt.

The future OOD opening remains controlled by V16D-31D.
"""

from pathlib import Path
import csv
import hashlib
import json
import math
import os
import platform
import random
import sys
import time

import numpy as np


# =============================================================================
# ROOT / FROZEN AUTHORITIES
# =============================================================================

R = Path(__file__).resolve().parent

D33 = (
    R
    / "output"
    / "V16_D33_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_TRAINING_PROTOCOL_FREEZE"
)

D33_SUMMARY = D33 / "PAD_Stream_V16D33_Summary.json"
D33_PROTOCOL = (
    D33 / "V16D33_EXP_CS1_ControlSpace_Executable_Training_Protocol_1.0.json"
)

D33_SUMMARY_SHA = (
    "b347b5aa8e3583ce4f35201840e47bf4cfb2e65d4589f0cbe981cad897dd760b"
)
D33_PROTOCOL_SHA = (
    "e12219bdfe85fdbc2de30e348df609ff9bc91a652500a65f053dc6b64b4f9f4a"
)

D32 = (
    R
    / "output"
    / "V16_D32_CONTROLSPACE_36CASE_STAGE4_LEARNING_DATASET_TRAIN_ONLY_NORMALIZATION"
)
D32_REGISTRY = D32 / "V16D32_Frozen_36Case_Learning_Dataset_Registry.json"
D32_REGISTRY_SHA = (
    "9429b239626fbfc8fe8569a2214a79a7abd5e40fbc38ac9112ba236e547fb90d"
)
D32_NORMALIZATION = D32 / "V16D32_TRAIN_Only_Normalization_Statistics.json"
D32_NORMALIZATION_SHA = (
    "dcda1cf01fa30bd1cd947a500de73295037d6ca2b492725edd050c0ff7c3bfd9"
)

D31D = (
    R
    / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)
D31D_CONTRACT = D31D / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_CONTRACT_SHA = (
    "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
)


# =============================================================================
# OUTPUT / RUN IDENTITY
# =============================================================================

O = (
    R
    / "output"
    / "V16_D33_R1_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_TRAINING_RUN"
)
O.mkdir(parents=True, exist_ok=True)

RUN_LOCK = O / "TRAINING_STARTED.lock"

CHECKPOINT = O / "V16D33R1_EXP_CS1_Best.weights.h5"
TRAINING_HISTORY = O / "V16D33R1_EXP_CS1_Training_History.csv"
ARCHITECTURE_JSON = O / "V16D33R1_EXP_CS1_Model_Architecture.json"
VALIDATION_DIAGNOSTICS = O / "V16D33R1_EXP_CS1_Validation_Diagnostics.json"
CASE_BINDING_MANIFEST = O / "V16D33R1_TRAIN_VALIDATION_Artifact_Bindings.json"
SUMMARY = O / "PAD_Stream_V16D33R1_Summary.json"


# =============================================================================
# FROZEN EXPERIMENT CONSTANTS
# =============================================================================

EXPERIMENT = "EXP-CS1"
SEED = 161501

N_TIMES = 9
N_STREAMLINES = 1078
N_NODES = 201
N_CHANNELS = 9

X_CASE_SHAPE = (9, 1078, 201, 9)
Y_CASE_SHAPE = (9, 1078, 201)

SEQUENCE_X_SHAPE = (201, 9)
SEQUENCE_Y_SHAPE = (201, 1)

EXPECTED_TRAIN_CASES = 18
EXPECTED_VALIDATION_CASES = 9
EXPECTED_OOD_CASES = 9

EXPECTED_TRAIN_SAMPLES = 174636
EXPECTED_VALIDATION_SAMPLES = 87318

BATCH_SIZE = 64
MAX_EPOCHS = 300
EARLY_STOP_PATIENCE = 25
LEARNING_RATE = 1.0e-3

SW_MIN = 0.2
SW_MAX = 0.8

FEATURES = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
    "target_time_hat",
    "target_eta_sequence",
]


# =============================================================================
# HELPERS
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text())


def resolve_path(value: str) -> Path:
    p = Path(value)
    if not p.is_absolute():
        p = R / p
    return p


def require_regular_file(path: Path, label: str):
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"{label} missing: {path}")


def verify_entry_artifacts(entry: dict):
    """
    Hash-verify a TRAIN or VALIDATION entry before any np.load.

    LOCKED_OOD_TEST is explicitly rejected.
    """
    partition = entry.get("partition")
    cid = entry.get("case_id", "<unknown>")

    if partition == "LOCKED_OOD_TEST":
        raise RuntimeError(
            f"OOD FIREWALL: D33-R1 must never resolve/open locked OOD entry {cid}."
        )

    if partition not in ("TRAIN", "VALIDATION"):
        raise RuntimeError(
            f"{cid}: invalid training-run partition {partition!r}"
        )

    x_info = entry.get("X_normalized", {})
    y_info = entry.get("Y_stage4", {})

    x_path = resolve_path(x_info.get("path", ""))
    y_path = resolve_path(y_info.get("path", ""))

    require_regular_file(x_path, f"{cid} X")
    require_regular_file(y_path, f"{cid} Y")

    x_sha = sha256(x_path)
    y_sha = sha256(y_path)

    if x_sha != x_info.get("sha256"):
        raise RuntimeError(
            f"{cid}: normalized X SHA mismatch."
        )

    if y_sha != y_info.get("sha256"):
        raise RuntimeError(
            f"{cid}: Stage-4 Y SHA mismatch."
        )

    if x_info.get("shape") != list(X_CASE_SHAPE):
        raise RuntimeError(
            f"{cid}: registry X shape authority mismatch."
        )

    if y_info.get("shape_authority") != list(Y_CASE_SHAPE):
        raise RuntimeError(
            f"{cid}: registry Y shape authority mismatch."
        )

    return {
        "case_id": cid,
        "partition": partition,
        "geology": entry.get("geology"),
        "injection_rate_tpd": entry.get("injection_rate_tpd"),
        "producer_bhp_psi": entry.get("producer_bhp_psi"),
        "X_path": str(x_path.relative_to(R)),
        "X_sha256": x_sha,
        "Y_path": str(y_path.relative_to(R)),
        "Y_sha256": y_sha,
    }


def x_from_entry(entry: dict) -> np.ndarray:
    if entry.get("partition") == "LOCKED_OOD_TEST":
        raise RuntimeError("OOD FIREWALL: attempted OOD predictor load.")

    p = resolve_path(entry["X_normalized"]["path"])

    with np.load(p, allow_pickle=False) as z:
        if "X" not in z.files:
            raise RuntimeError(
                f"{entry['case_id']}: normalized predictor key X absent."
            )

        a = np.asarray(z["X"])

        if a.shape != X_CASE_SHAPE:
            raise RuntimeError(
                f"{entry['case_id']}: X shape {a.shape} != {X_CASE_SHAPE}"
            )

        if not np.issubdtype(a.dtype, np.number):
            raise RuntimeError(
                f"{entry['case_id']}: X dtype is nonnumeric {a.dtype}"
            )

        a = np.asarray(a, dtype=np.float32)

    if not np.isfinite(a).all():
        raise RuntimeError(
            f"{entry['case_id']}: X contains nonfinite values."
        )

    return a


def y_from_entry(entry: dict) -> np.ndarray:
    if entry.get("partition") == "LOCKED_OOD_TEST":
        raise RuntimeError("OOD FIREWALL: attempted OOD target load.")

    p = resolve_path(entry["Y_stage4"]["path"])

    with np.load(p, allow_pickle=False) as z:
        if "Y_transport" not in z.files:
            raise RuntimeError(
                f"{entry['case_id']}: exact Y_transport key absent; "
                f"available={list(z.files)}"
            )

        a = np.asarray(z["Y_transport"])

        if a.shape != Y_CASE_SHAPE:
            raise RuntimeError(
                f"{entry['case_id']}: Y shape {a.shape} != {Y_CASE_SHAPE}"
            )

        if not np.issubdtype(a.dtype, np.number):
            raise RuntimeError(
                f"{entry['case_id']}: Y dtype is nonnumeric {a.dtype}"
            )

        a = np.asarray(a, dtype=np.float32)

    if not np.isfinite(a).all():
        raise RuntimeError(
            f"{entry['case_id']}: Y contains nonfinite values."
        )

    return a


def make_sequence_generator(entries, shuffle: bool, seed: int):
    """
    Reiterable per-case generator.

    The frozen EXP-CS1 protocol specifies deterministic TRAIN shuffle from the
    seed and no VALIDATION shuffle. Each generator invocation starts from the
    same frozen RNG seed, matching the earlier EXP-MC1 baseline behavior.
    """
    def generator():
        if any(e.get("partition") == "LOCKED_OOD_TEST" for e in entries):
            raise RuntimeError(
                "OOD FIREWALL: OOD entry supplied to dataset generator."
            )

        order = np.arange(len(entries))
        rng = np.random.default_rng(seed)

        if shuffle:
            rng.shuffle(order)

        for ii in order:
            e = entries[int(ii)]

            X = x_from_entry(e)
            Y = y_from_entry(e)

            X = X.reshape(-1, N_NODES, N_CHANNELS)
            Y = Y.reshape(-1, N_NODES, 1)

            if X.shape[0] != N_TIMES * N_STREAMLINES:
                raise RuntimeError(
                    f"{e['case_id']}: sequence count mismatch in X."
                )

            if Y.shape[0] != N_TIMES * N_STREAMLINES:
                raise RuntimeError(
                    f"{e['case_id']}: sequence count mismatch in Y."
                )

            indices = np.arange(N_TIMES * N_STREAMLINES)

            if shuffle:
                rng.shuffle(indices)

            for q in indices:
                yield X[q], Y[q]

    return generator


def validation_diagnostics(model, dataset):
    """
    Evaluate the frozen best checkpoint on VALIDATION only.

    Accumulate in float64 so the frozen validation MSE/RMSE/MAE can later serve
    as the denominator authority for the D31D OOD generalization-gap report.
    """
    n = 0
    sum_sq = 0.0
    sum_abs = 0.0
    sum_signed = 0.0
    pred_min = math.inf
    pred_max = -math.inf
    target_min = math.inf
    target_max = -math.inf

    for xb, yb in dataset:
        pred = model(xb, training=False)

        p = np.asarray(pred.numpy(), dtype=np.float64)
        y = np.asarray(yb.numpy(), dtype=np.float64)

        if p.shape != y.shape:
            raise RuntimeError(
                f"Validation prediction/target shape mismatch: {p.shape} vs {y.shape}"
            )

        if not np.isfinite(p).all() or not np.isfinite(y).all():
            raise RuntimeError(
                "Nonfinite prediction/target encountered in validation diagnostics."
            )

        d = p - y

        n += int(d.size)
        sum_sq += float(np.square(d).sum(dtype=np.float64))
        sum_abs += float(np.abs(d).sum(dtype=np.float64))
        sum_signed += float(d.sum(dtype=np.float64))

        pred_min = min(pred_min, float(p.min()))
        pred_max = max(pred_max, float(p.max()))
        target_min = min(target_min, float(y.min()))
        target_max = max(target_max, float(y.max()))

    if n <= 0:
        raise RuntimeError("Validation diagnostics saw zero values.")

    mse = sum_sq / n
    rmse = math.sqrt(mse)
    mae = sum_abs / n
    mean_signed_error = sum_signed / n

    return {
        "values_evaluated": n,
        "MSE_float64_accumulation": mse,
        "RMSE_float64_accumulation": rmse,
        "MAE_float64_accumulation": mae,
        "mean_signed_error_float64_accumulation": mean_signed_error,
        "prediction_min": pred_min,
        "prediction_max": pred_max,
        "target_min": target_min,
        "target_max": target_max,
        "all_predictions_finite": True,
        "all_targets_finite": True,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-33-R1")
    print(
        "EXP-CS1 Frozen Control-Space Recurrent Stage-4 Training Run "
        "+ Validation-Only Checkpoint Selection"
    )
    print("=" * 78)

    # -------------------------------------------------------------------------
    # 1. Frozen authority pre-gates
    # -------------------------------------------------------------------------

    gates = {
        "D33_summary_SHA_exact":
            exact_sha(D33_SUMMARY, D33_SUMMARY_SHA),

        "D33_protocol_SHA_exact":
            exact_sha(D33_PROTOCOL, D33_PROTOCOL_SHA),

        "D32_dataset_registry_SHA_exact":
            exact_sha(D32_REGISTRY, D32_REGISTRY_SHA),

        "D32_normalization_SHA_exact":
            exact_sha(D32_NORMALIZATION, D32_NORMALIZATION_SHA),

        "D31D_contract_SHA_exact":
            exact_sha(D31D_CONTRACT, D31D_CONTRACT_SHA),
    }

    if not all(gates.values()):
        print("\nPRE-GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError(
            "D33-R1 blocked: exact frozen authority SHA mismatch."
        )

    protocol = read_json(D33_PROTOCOL)
    d33_summary = read_json(D33_SUMMARY)
    registry = read_json(D32_REGISTRY)

    gates.update(
        {
            "D33_status_authorizes_training": (
                d33_summary.get("status")
                == "V16D_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_"
                   "TRAINING_PROTOCOL_FROZEN_OOD_REMAINS_SEALED_FIRST_"
                   "TRAINING_RUN_AUTHORIZED"
            ),

            "protocol_experiment_EXP_CS1":
                protocol.get("experiment") == EXPERIMENT,

            "protocol_seed_exact":
                protocol.get("seed") == SEED,

            "protocol_input_shape_exact":
                protocol.get("model", {}).get("input_shape") == [201, 9],

            "protocol_output_shape_exact":
                protocol.get("model", {}).get("output_shape") == [201, 1],

            "protocol_MSE_exact":
                protocol.get("objective", {}).get("training_loss") == "MSE",

            "protocol_no_physics_loss":
                protocol.get("objective", {}).get("physics_loss") == "NONE",

            "protocol_Adam_lr_exact": (
                protocol.get("optimizer", {}).get("name") == "Adam"
                and protocol.get("optimizer", {}).get("learning_rate")
                == LEARNING_RATE
            ),

            "protocol_batch64_exact":
                protocol.get("sampling", {}).get("batch_size") == BATCH_SIZE,

            "protocol_train_samples_exact":
                protocol.get("sampling", {}).get("TRAIN_samples")
                == EXPECTED_TRAIN_SAMPLES,

            "protocol_validation_samples_exact":
                protocol.get("sampling", {}).get("VALIDATION_samples")
                == EXPECTED_VALIDATION_SAMPLES,

            "protocol_max_epochs_exact":
                protocol.get("epochs", {}).get("max") == MAX_EPOCHS,

            "protocol_patience25_exact":
                protocol.get("epochs", {})
                .get("early_stopping", {})
                .get("patience")
                == EARLY_STOP_PATIENCE,

            "protocol_checkpoint_validation_MSE_only": (
                protocol.get("checkpoint", {}).get("selection_authority")
                == "minimum raw VALIDATION MSE"
            ),

            "registry_feature_order_exact":
                registry.get("feature_order") == FEATURES,

            "registry_normalization_SHA_exact":
                registry.get("normalization", {}).get("statistics_sha256")
                == D32_NORMALIZATION_SHA,

            "registry_OOD_not_opened":
                registry.get("locked_OOD", {}).get("opened") is False,

            "registry_OOD_not_evaluated":
                registry.get("locked_OOD", {}).get("evaluated") is False,
        }
    )

    print("\nPRE-GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError(
            "D33-R1 blocked: frozen protocol/registry semantic mismatch."
        )

    # -------------------------------------------------------------------------
    # 2. Partition registry without opening OOD arrays
    # -------------------------------------------------------------------------

    cases = registry.get("cases", [])

    train = [e for e in cases if e.get("partition") == "TRAIN"]
    validation = [
        e for e in cases if e.get("partition") == "VALIDATION"
    ]
    ood = [
        e for e in cases if e.get("partition") == "LOCKED_OOD_TEST"
    ]

    gates["exact_18_TRAIN_cases"] = len(train) == EXPECTED_TRAIN_CASES
    gates["exact_9_VALIDATION_cases"] = (
        len(validation) == EXPECTED_VALIDATION_CASES
    )
    gates["exact_9_LOCKED_OOD_registry_entries"] = (
        len(ood) == EXPECTED_OOD_CASES
    )
    gates["registry_exact_36_cases"] = len(cases) == 36

    if not all(
        gates[k]
        for k in (
            "exact_18_TRAIN_cases",
            "exact_9_VALIDATION_cases",
            "exact_9_LOCKED_OOD_registry_entries",
            "registry_exact_36_cases",
        )
    ):
        raise RuntimeError("D33-R1 case partition count mismatch.")

    print(
        "\nREGISTRY"
        f"\n  TRAIN      : {len(train)}"
        f"\n  VALIDATION : {len(validation)}"
        f"\n  LOCKED OOD : {len(ood)} (registry metadata only; arrays remain unopened)"
    )

    # -------------------------------------------------------------------------
    # 3. Hash-verify TRAIN + VALIDATION only, before np.load
    # -------------------------------------------------------------------------

    bindings = []

    print("\nTRAIN / VALIDATION ARTIFACT SHA PREFLIGHT")

    for idx, entry in enumerate(train + validation, 1):
        b = verify_entry_artifacts(entry)
        bindings.append(b)

        print(
            f"[{idx:02d}/27] {b['case_id']} "
            f"{b['partition']} X/Y SHA PASS"
        )

    CASE_BINDING_MANIFEST.write_text(
        json.dumps(
            {
                "milestone": "V16D-33-R1",
                "experiment": EXPERIMENT,
                "TRAIN_and_VALIDATION_only": True,
                "LOCKED_OOD_entries_resolved_or_hashed": False,
                "bindings": bindings,
            },
            indent=2,
        )
    )

    gates["27_TRAIN_VALIDATION_XY_bindings_SHA_verified"] = (
        len(bindings) == 27
    )
    gates["OOD_artifacts_not_resolved_or_hashed"] = True

    if not all(gates.values()):
        raise RuntimeError("D33-R1 artifact preflight failed.")

    # -------------------------------------------------------------------------
    # 4. Single-attempt execution lock
    # -------------------------------------------------------------------------

    if RUN_LOCK.exists():
        raise RuntimeError(
            "\nD33-R1 TRAINING ATTEMPT ALREADY STARTED.\n"
            f"Lock file exists: {RUN_LOCK}\n"
            "The frozen D33 interruption policy prohibits a silent rerun under "
            "the same experiment identity. Diagnose the prior attempt and freeze "
            "a restart/recovery milestone if needed."
        )

    RUN_LOCK.write_text(
        json.dumps(
            {
                "milestone": "V16D-33-R1",
                "experiment": EXPERIMENT,
                "D33_protocol_sha256": D33_PROTOCOL_SHA,
                "D32_dataset_registry_sha256": D32_REGISTRY_SHA,
                "created_unix_time": time.time(),
                "meaning":
                    "Training attempt consumed. Do not silently rerun EXP-CS1 "
                    "under the same identity after interruption/failure.",
            },
            indent=2,
        )
    )

    print("\nTRAINING ATTEMPT LOCK CREATED")
    print(" ", RUN_LOCK.relative_to(R))

    # -------------------------------------------------------------------------
    # 5. Determinism
    # -------------------------------------------------------------------------

    os.environ["PYTHONHASHSEED"] = str(SEED)
    random.seed(SEED)
    np.random.seed(SEED)

    import tensorflow as tf

    tf.keras.utils.set_random_seed(SEED)

    determinism_requested = True
    determinism_enabled = False
    determinism_error = None

    try:
        tf.config.experimental.enable_op_determinism()
        determinism_enabled = True
    except Exception as exc:
        determinism_error = repr(exc)

    print("\nRUNTIME")
    print("  Python     :", sys.version.replace("\n", " "))
    print("  Platform   :", platform.platform())
    print("  TensorFlow :", tf.__version__)
    print("  GPUs       :", tf.config.list_physical_devices("GPU"))
    print("  Determinism requested:", determinism_requested)
    print("  Determinism enabled  :", determinism_enabled)
    if determinism_error:
        print("  Determinism note     :", determinism_error)

    # -------------------------------------------------------------------------
    # 6. Deterministic streaming datasets
    # -------------------------------------------------------------------------

    output_signature = (
        tf.TensorSpec(SEQUENCE_X_SHAPE, tf.float32),
        tf.TensorSpec(SEQUENCE_Y_SHAPE, tf.float32),
    )

    train_ds = (
        tf.data.Dataset.from_generator(
            make_sequence_generator(train, True, SEED),
            output_signature=output_signature,
        )
        .batch(BATCH_SIZE, drop_remainder=False)
        .prefetch(tf.data.AUTOTUNE)
    )

    validation_ds = (
        tf.data.Dataset.from_generator(
            make_sequence_generator(validation, False, SEED),
            output_signature=output_signature,
        )
        .batch(BATCH_SIZE, drop_remainder=False)
        .prefetch(tf.data.AUTOTUNE)
    )

    # -------------------------------------------------------------------------
    # 7. Exact frozen EXP-CS1 model
    # -------------------------------------------------------------------------

    inp = tf.keras.Input(
        shape=(N_NODES, N_CHANNELS),
        name="C20_predictors",
    )

    x = tf.keras.layers.LSTM(
        64,
        return_sequences=True,
        name="lstm_1",
    )(inp)

    x = tf.keras.layers.LSTM(
        64,
        return_sequences=True,
        name="lstm_2",
    )(x)

    raw = tf.keras.layers.TimeDistributed(
        tf.keras.layers.Dense(
            1,
            activation="sigmoid",
        ),
        name="td_sigmoid",
    )(x)

    out = tf.keras.layers.Rescaling(
        scale=SW_MAX - SW_MIN,
        offset=SW_MIN,
        name="bounded_Sw_0p2_0p8",
    )(raw)

    model = tf.keras.Model(
        inp,
        out,
        name="V16D_EXP_CS1",
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=LEARNING_RATE,
        ),
        loss="mse",
        metrics=["mae"],
    )

    # Force build and verify exact I/O.
    probe = model(
        tf.zeros(
            (1, N_NODES, N_CHANNELS),
            dtype=tf.float32,
        ),
        training=False,
    )

    if tuple(probe.shape) != (1, N_NODES, 1):
        raise RuntimeError(
            f"Built model output shape mismatch: {tuple(probe.shape)}"
        )

    layer_signature = [
        (layer.name, layer.__class__.__name__)
        for layer in model.layers
    ]

    required_layer_signature = [
        ("C20_predictors", "InputLayer"),
        ("lstm_1", "LSTM"),
        ("lstm_2", "LSTM"),
        ("td_sigmoid", "TimeDistributed"),
        ("bounded_Sw_0p2_0p8", "Rescaling"),
    ]

    if layer_signature != required_layer_signature:
        raise RuntimeError(
            "Built model layer signature drift:\n"
            f"got={layer_signature}\n"
            f"expected={required_layer_signature}"
        )

    architecture_text = model.to_json()
    ARCHITECTURE_JSON.write_text(architecture_text)
    architecture_sha = sha256(ARCHITECTURE_JSON)

    print("\nMODEL")
    model.summary()
    print("Architecture SHA-256:", architecture_sha)

    # -------------------------------------------------------------------------
    # 8. Frozen callbacks / training
    # -------------------------------------------------------------------------

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(CHECKPOINT),
            monitor="val_loss",
            mode="min",
            save_best_only=True,
            save_weights_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            mode="min",
            patience=EARLY_STOP_PATIENCE,
            min_delta=0.0,
            restore_best_weights=False,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            str(TRAINING_HISTORY)
        ),
    ]

    print("\nTRAINING")
    print("  EXP-CS1 begins.")
    print("  TRAIN gradients only.")
    print("  VALIDATION selects the checkpoint.")
    print("  LOCKED OOD remains sealed.")

    t0 = time.time()

    history = model.fit(
        train_ds,
        validation_data=validation_ds,
        epochs=MAX_EPOCHS,
        callbacks=callbacks,
        verbose=2,
    )

    runtime_seconds = time.time() - t0

    if not CHECKPOINT.exists():
        raise RuntimeError(
            "Training completed without the frozen best-checkpoint artifact."
        )

    if not TRAINING_HISTORY.exists():
        raise RuntimeError(
            "Training history CSV missing after model.fit."
        )

    # -------------------------------------------------------------------------
    # 9. Validation-only best-checkpoint selection/freeze
    # -------------------------------------------------------------------------

    val_loss_history = np.asarray(
        history.history.get("val_loss", []),
        dtype=np.float64,
    )

    train_loss_history = np.asarray(
        history.history.get("loss", []),
        dtype=np.float64,
    )

    if (
        val_loss_history.size == 0
        or train_loss_history.size == 0
        or not np.isfinite(val_loss_history).all()
        or not np.isfinite(train_loss_history).all()
    ):
        raise RuntimeError(
            "Training history missing/nonfinite loss values."
        )

    best_epoch = int(np.argmin(val_loss_history) + 1)
    best_raw_val_mse = float(np.min(val_loss_history))
    epochs_executed = int(len(val_loss_history))

    # The checkpoint already corresponds to minimum val_loss by frozen callback.
    model.load_weights(CHECKPOINT)

    # Keras validation report after exact best-checkpoint reload.
    validation_return_dict = model.evaluate(
        validation_ds,
        verbose=1,
        return_dict=True,
    )

    validation_return_dict = {
        str(k): float(v)
        for k, v in validation_return_dict.items()
    }

    # Independent float64 aggregate diagnostics on the exact frozen checkpoint.
    diag = validation_diagnostics(
        model,
        validation_ds,
    )

    diag.update(
        {
            "milestone": "V16D-33-R1",
            "experiment": EXPERIMENT,
            "selection_partition": "VALIDATION",
            "checkpoint_selection_rule":
                "minimum raw VALIDATION MSE / val_loss",
            "best_epoch": best_epoch,
            "best_raw_val_MSE_from_training_history":
                best_raw_val_mse,
            "keras_reloaded_checkpoint_evaluation":
                validation_return_dict,
            "checkpoint_sha256":
                sha256(CHECKPOINT),
            "architecture_sha256":
                architecture_sha,
            "LOCKED_OOD_opened":
                False,
            "LOCKED_OOD_evaluated":
                False,
        }
    )

    VALIDATION_DIAGNOSTICS.write_text(
        json.dumps(diag, indent=2)
    )

    # -------------------------------------------------------------------------
    # 10. Final certification gates
    # -------------------------------------------------------------------------

    checkpoint_sha = sha256(CHECKPOINT)
    history_sha = sha256(TRAINING_HISTORY)
    validation_diag_sha = sha256(VALIDATION_DIAGNOSTICS)
    binding_sha = sha256(CASE_BINDING_MANIFEST)

    final_gates = dict(gates)

    final_gates.update(
        {
            "training_attempt_lock_exists":
                RUN_LOCK.exists(),

            "checkpoint_exists":
                CHECKPOINT.exists(),

            "checkpoint_SHA_frozen":
                len(checkpoint_sha) == 64,

            "architecture_JSON_exists":
                ARCHITECTURE_JSON.exists(),

            "architecture_SHA_frozen":
                len(architecture_sha) == 64,

            "history_exists":
                TRAINING_HISTORY.exists(),

            "history_finite":
                bool(
                    np.isfinite(train_loss_history).all()
                    and np.isfinite(val_loss_history).all()
                ),

            "epochs_within_frozen_max":
                1 <= epochs_executed <= MAX_EPOCHS,

            "best_epoch_valid":
                1 <= best_epoch <= epochs_executed,

            "best_validation_MSE_finite":
                np.isfinite(best_raw_val_mse),

            "reloaded_validation_loss_finite":
                all(
                    np.isfinite(v)
                    for v in validation_return_dict.values()
                ),

            "float64_validation_MSE_finite":
                np.isfinite(
                    diag["MSE_float64_accumulation"]
                ),

            "float64_validation_RMSE_finite":
                np.isfinite(
                    diag["RMSE_float64_accumulation"]
                ),

            "float64_validation_MAE_finite":
                np.isfinite(
                    diag["MAE_float64_accumulation"]
                ),

            "validation_value_count_exact":
                diag["values_evaluated"]
                == EXPECTED_VALIDATION_SAMPLES * N_NODES,

            "prediction_bounds_architecturally_enforced":
                (
                    diag["prediction_min"] >= SW_MIN - 1.0e-6
                    and diag["prediction_max"] <= SW_MAX + 1.0e-6
                ),

            "checkpoint_selected_by_validation_only":
                True,

            "TRAIN_only_gradient_updates":
                True,

            "no_OOD_X_loaded":
                True,

            "no_OOD_Y_loaded":
                True,

            "no_OOD_metric_computed":
                True,

            "no_OOD_informed_decision":
                True,

            "no_architecture_change":
                True,

            "no_loss_change":
                True,

            "no_optimizer_change":
                True,

            "no_seed_change":
                True,

            "no_batch_change":
                True,

            "no_physics_loss":
                True,

            "no_M_face_predictor":
                True,

            "no_direct_control_channels":
                True,
        }
    )

    ok = bool(all(final_gates.values()))

    status = (
        "V16D_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_TRAINED_"
        "BEST_VALIDATION_CHECKPOINT_FROZEN_OOD_REMAINS_SEALED_"
        "FINAL_ONE_TOUCH_EVALUATOR_BINDING_CONTRACT_AUTHORIZED"
        if ok
        else "V16D_D33_R1_EXP_CS1_TRAINING_CERTIFICATION_BLOCKED"
    )

    next_milestone = (
        "V16D-34 — Freeze EXP-CS1 selected architecture/checkpoint/"
        "validation metrics into the final one-touch locked-OOD evaluator "
        "binding contract"
        if ok
        else "Diagnose D33-R1 without opening OOD; do not tune or rerun silently."
    )

    summary = {
        "milestone": "V16D-33-R1",
        "experiment": EXPERIMENT,
        "status": status,

        "frozen_authorities": {
            "D33_summary_sha256":
                D33_SUMMARY_SHA,
            "D33_protocol_sha256":
                D33_PROTOCOL_SHA,
            "D32_dataset_registry_sha256":
                D32_REGISTRY_SHA,
            "D32_normalization_sha256":
                D32_NORMALIZATION_SHA,
            "D31D_contract_sha256":
                D31D_CONTRACT_SHA,
        },

        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "tensorflow": tf.__version__,
            "GPU_devices": [
                str(x)
                for x in tf.config.list_physical_devices("GPU")
            ],
            "op_determinism_requested":
                determinism_requested,
            "op_determinism_enabled":
                determinism_enabled,
            "op_determinism_error":
                determinism_error,
            "runtime_seconds":
                runtime_seconds,
        },

        "training": {
            "seed":
                SEED,
            "TRAIN_cases":
                len(train),
            "VALIDATION_cases":
                len(validation),
            "LOCKED_OOD_registry_cases":
                len(ood),
            "TRAIN_samples":
                EXPECTED_TRAIN_SAMPLES,
            "VALIDATION_samples":
                EXPECTED_VALIDATION_SAMPLES,
            "batch_size":
                BATCH_SIZE,
            "max_epochs":
                MAX_EPOCHS,
            "epochs_executed":
                epochs_executed,
            "best_epoch":
                best_epoch,
            "best_raw_validation_MSE":
                best_raw_val_mse,
            "early_stopping_patience":
                EARLY_STOP_PATIENCE,
        },

        "selected_model": {
            "architecture":
                "LSTM64 -> LSTM64 -> TD Dense sigmoid -> Rescaling[0.2,0.8]",
            "architecture_path":
                str(ARCHITECTURE_JSON.relative_to(R)),
            "architecture_sha256":
                architecture_sha,
            "checkpoint_path":
                str(CHECKPOINT.relative_to(R)),
            "checkpoint_sha256":
                checkpoint_sha,
            "selection_authority":
                "minimum raw VALIDATION MSE",
        },

        "frozen_validation_metrics": {
            "MSE":
                diag["MSE_float64_accumulation"],
            "RMSE":
                diag["RMSE_float64_accumulation"],
            "MAE":
                diag["MAE_float64_accumulation"],
            "mean_signed_error":
                diag["mean_signed_error_float64_accumulation"],
            "prediction_min":
                diag["prediction_min"],
            "prediction_max":
                diag["prediction_max"],
            "values_evaluated":
                diag["values_evaluated"],
            "diagnostics_path":
                str(VALIDATION_DIAGNOSTICS.relative_to(R)),
            "diagnostics_sha256":
                validation_diag_sha,
        },

        "artifact_hashes": {
            "training_history_sha256":
                history_sha,
            "TRAIN_VALIDATION_binding_manifest_sha256":
                binding_sha,
            "run_lock_sha256":
                sha256(RUN_LOCK),
        },

        "LOCKED_OOD": {
            "geology": "0029",
            "registry_entries": len(ood),
            "X_opened": False,
            "Y_opened": False,
            "evaluated": False,
            "used_for_selection": False,
            "one_touch_contract":
                str(D31D_CONTRACT.relative_to(R)),
            "one_touch_contract_sha256":
                D31D_CONTRACT_SHA,
        },

        "gates": final_gates,
        "next_milestone": next_milestone,
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2)
    )

    print("\n" + "=" * 78)
    print("V16D-33-R1 TRAINING RESULT")
    print("=" * 78)

    print("  epochs executed      :", epochs_executed)
    print("  best epoch           :", best_epoch)
    print(
        "  best raw val MSE     :",
        f"{best_raw_val_mse:.12e}",
    )
    print(
        "  frozen val RMSE      :",
        f"{diag['RMSE_float64_accumulation']:.12e}",
    )
    print(
        "  frozen val MAE       :",
        f"{diag['MAE_float64_accumulation']:.12e}",
    )
    print(
        "  validation pred range:",
        f"[{diag['prediction_min']:.9f}, {diag['prediction_max']:.9f}]",
    )
    print(
        "  checkpoint SHA-256   :",
        checkpoint_sha,
    )
    print(
        "  architecture SHA-256 :",
        architecture_sha,
    )

    print("\nFINAL GATES")
    for name, passed in final_gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nLOCKED-OOD STATUS")
    print(
        "  SEALED — geology0029 X/Y arrays were never loaded or evaluated."
    )

    print("\nNEXT")
    print(" ", next_milestone)

    print("\nValidation diagnostics SHA-256:", validation_diag_sha)
    print("Training history SHA-256      :", history_sha)
    print("Summary SHA-256               :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
