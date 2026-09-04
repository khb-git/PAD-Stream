from __future__ import annotations

from pathlib import Path
import csv
import json
import math

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F2A
# Front-Correction Geometry / Topology Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO SG7B-11 WEIGHTS CHANGED.
# NO CALIBRATOR WEIGHTS CHANGED.
# NO FRONT GATE RELAXED.
# NO TOF-BIAS GATE RELAXED.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3F1-R diagnosed:
#
#     FRONT_CAPACITY_TOPOLOGY_TRADEOFF_CONFIRMED
#
# The strongest persisted front-state checkpoints achieved approximately
# 35-37% front-shell error reduction, but simultaneously violated one or more
# front-preservation gates:
#
#   * mean frozen-front xi shift,
#   * P90 frozen-front xi shift,
#   * front sign agreement,
#   * front overshoot,
#   * and occasionally TOF-bias preservation.
#
# R3F2A therefore reconstructs selected persisted R3F1 calibrator checkpoints
# and audits the geometry of:
#
#     deltaS = S_calibrated - S_frozen
#
# relative to:
#
#     the SG7A/canonical front position,
#     the frozen SG7B-11 front position,
#     local front-normal coordinate d_xi = xi - xi_front,
#     correction direction,
#     correction overshoot,
#     local gradient,
#     front width,
#     and front-crossing displacement.
#
# The objective is to classify the topology damage as one of:
#
#   CROSSING_DISPLACEMENT_DOMINANT
#   FRONT_BROADENING_OR_COMPRESSION_DOMINANT
#   WRONG_DIRECTION_CORRECTION_DOMINANT
#   OVERSHOOT_DOMINANT
#   MIXED_FRONT_GEOMETRY_FAILURE
#
# No model is altered by this script.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3F1R_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F1R"
    / "PAD_Stream_V15SG7CR3F1R_Summary.json"
)

R3F1_CHECKPOINTS = (
    ROOT / "output" / "V15_SG7CR3F1"
    / "V15SG7CR3F1_Best_Checkpoint_By_Experiment.csv"
)

R3F1_EPOCHS = (
    ROOT / "output" / "V15_SG7CR3F1"
    / "V15SG7CR3F1_Epoch_Metrics.csv"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F2A"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F2A_Selected_Checkpoints.csv"
)

GLOBAL_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F2A_Global_Geometry_Metrics.csv"
)

PROFILE_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F2A_Profile_Geometry_Metrics.csv"
)

DISTANCE_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F2A_Correction_By_Front_Distance.csv"
)

TOF_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F2A_Correction_By_TOF.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "PAD_Stream_V15SG7CR3F2A_Summary.json"
)


FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300

# Front width measured over a wider transition envelope.
WIDTH_LOW = 0.210
WIDTH_HIGH = 0.500

# Front-distance bins in xi.
FRONT_DISTANCE_BINS = np.array(
    [-1.0, -0.10, -0.05, -0.025, -0.010, 0.0,
      0.010, 0.025, 0.050, 0.10, 1.0],
    dtype=float,
)

TOF_BANDS = [
    ("<=250d", -np.inf, 250.0),
    ("250-500d", 250.0, 500.0),
    ("500-1000d", 500.0, 1000.0),
    ("1000-2000d", 1000.0, 2000.0),
    (">2000d", 2000.0, np.inf),
]


# =============================================================================
# IO HELPERS
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def num(row, key, default=np.nan):
    try:
        return float(row.get(key, default))
    except Exception:
        return default


# =============================================================================
# FEATURE RECONSTRUCTION
# =============================================================================

def make_features(xi, normalized_tD, tau_end_days, frozen):
    nt, ns, nx = frozen.shape

    xi3 = np.broadcast_to(
        xi[None, None, :],
        (nt, ns, nx),
    )

    tnorm3 = np.broadcast_to(
        normalized_tD[:, :, None],
        (nt, ns, nx),
    )

    logtau = np.log10(np.maximum(tau_end_days, 1.0))
    logtau = (logtau - np.mean(logtau)) / max(np.std(logtau), 1e-12)

    logtau3 = np.broadcast_to(
        logtau[None, :, None],
        (nt, ns, nx),
    )

    front_distance = np.abs(frozen - FRONT_THRESHOLD)

    features = np.stack(
        [
            xi3,
            tnorm3,
            logtau3,
            frozen,
            front_distance,
        ],
        axis=-1,
    )

    return features.astype(np.float32)


# =============================================================================
# FRONT GEOMETRY HELPERS
# =============================================================================

def first_crossing(profile, xi, threshold):
    y = np.asarray(profile, dtype=float) - threshold

    idx = np.where(y[:-1] * y[1:] < 0.0)[0]

    if idx.size == 0:
        exact = np.where(np.isclose(y, 0.0, atol=1e-10))[0]
        if exact.size:
            return float(xi[int(exact[0])]), True
        return np.nan, False

    j = int(idx[0])
    denom = y[j + 1] - y[j]

    if abs(denom) <= 1e-14:
        return float(0.5 * (xi[j] + xi[j + 1])), True

    frac = float(np.clip(-y[j] / denom, 0.0, 1.0))

    return float(
        xi[j] + frac * (xi[j + 1] - xi[j])
    ), True


def crossing_arrays(field, xi, threshold):
    pos = np.full(field.shape[0], np.nan)
    ok = np.zeros(field.shape[0], dtype=bool)

    for i in range(field.shape[0]):
        pos[i], ok[i] = first_crossing(
            field[i],
            xi,
            threshold,
        )

    return pos, ok


def front_width(profile, xi, low=WIDTH_LOW, high=WIDTH_HIGH):
    """
    Width between high and low saturation crossings.

    For a decreasing saturation profile in xi, high S is upstream and low S
    is downstream. Width is absolute xi distance.
    """
    x_low, ok_low = first_crossing(profile, xi, low)
    x_high, ok_high = first_crossing(profile, xi, high)

    if not (ok_low and ok_high):
        return np.nan

    return abs(x_low - x_high)


def local_gradient_at(profile, xi, x_front):
    if not np.isfinite(x_front):
        return np.nan

    j = int(np.argmin(np.abs(xi - x_front)))

    if j == 0:
        return float(
            (profile[1] - profile[0])
            /
            (xi[1] - xi[0])
        )

    if j == len(xi) - 1:
        return float(
            (profile[-1] - profile[-2])
            /
            (xi[-1] - xi[-2])
        )

    return float(
        (profile[j + 1] - profile[j - 1])
        /
        (xi[j + 1] - xi[j - 1])
    )


# =============================================================================
# CHECKPOINT SELECTION
# =============================================================================

def select_checkpoints(checkpoint_rows, epoch_rows):
    """
    Select the best-any persisted checkpoints for F2/F3/F4, plus F1 if present.

    R3F1-R showed F2/F3/F4 are the most informative front-state cases.
    """
    selected_experiments = ["F1", "F2", "F3", "F4"]

    selected = []

    for exp in selected_experiments:

        candidates = [
            row
            for row in checkpoint_rows
            if row.get("experiment") == exp
            and row.get("checkpoint_type") == "best_any"
        ]

        if not candidates:
            continue

        row = candidates[0]

        checkpoint_path = Path(row["path"])

        if not checkpoint_path.is_absolute():
            checkpoint_path = ROOT / checkpoint_path

        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"Persisted checkpoint does not exist:\n{checkpoint_path}"
            )

        # Pull best front-reduction epoch from persisted epoch table for context.
        exp_epochs = [
            r
            for r in epoch_rows
            if r.get("experiment") == exp
        ]

        best_front_epoch = None
        best_front_red = np.nan

        if exp_epochs:
            valid = [
                r for r in exp_epochs
                if np.isfinite(
                    num(r, "front_error_reduction_fraction")
                )
            ]

            if valid:
                best_row = max(
                    valid,
                    key=lambda r:
                    num(r, "front_error_reduction_fraction"),
                )

                best_front_epoch = int(
                    num(best_row, "epoch")
                )

                best_front_red = num(
                    best_row,
                    "front_error_reduction_fraction",
                )

        selected.append({
            "experiment": exp,
            "checkpoint_type": row.get("checkpoint_type"),
            "checkpoint_epoch": int(num(row, "epoch")),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": row.get("sha256", ""),
            "best_front_epoch": best_front_epoch,
            "best_front_reduction_fraction": best_front_red,
        })

    return selected



# =============================================================================
# TRUSTED R3F1 CALIBRATOR RECONSTRUCTION
# =============================================================================

def build_r3f1_calibrator_for_experiment(experiment: str):
    """
    Rebuild the exact R3F1 calibrator architecture and load weights only.

    Why this is needed
    ------------------
    The R3F1 .keras files contain Lambda layers created by the local PAD-Stream
    training script. Keras 3 can deserialize the trusted Python lambdas with
    safe_mode=False, but it can still fail when reconstructing the Lambda
    output shape from the serialized config.

    We therefore avoid full model deserialization entirely:
      1. rebuild the known architecture in code,
      2. create the same bounded-delta Lambda with an explicit output_shape,
      3. load ONLY the persisted weights from the trusted local .keras file.

    This does not alter or retrain any parameter.
    """

    experiment = str(experiment).upper()

    architecture_map = {
        "F0": "mlp16",
        "F1": "mlp24",
        "F2": "mlp32",
        "F3": "dual24",
        "F4": "dual24",
    }

    if experiment not in architecture_map:
        raise ValueError(
            f"Unsupported R3F1 experiment for reconstruction: {experiment}"
        )

    architecture = architecture_map[experiment]

    inp = tf.keras.Input(
        shape=(5,),
        name="features",
    )

    # For the simple MLPs, do not hard-code generic Dense names such as
    # "dense_2". Keras' global layer-name counter advances as F1, F2, F3, F4
    # are reconstructed in the same process, and a hard-coded generic name can
    # collide with an automatically generated Dense name. Weight loading from
    # the trusted .keras checkpoint follows the reconstructed layer topology.
    if architecture == "mlp16":

        x = tf.keras.layers.Dense(
            16,
            activation="tanh",
        )(inp)

        x = tf.keras.layers.Dense(
            16,
            activation="tanh",
        )(x)

        raw = tf.keras.layers.Dense(
            1,
            activation=None,
        )(x)

    elif architecture == "mlp24":

        x = tf.keras.layers.Dense(
            24,
            activation="tanh",
        )(inp)

        x = tf.keras.layers.Dense(
            24,
            activation="tanh",
        )(x)

        raw = tf.keras.layers.Dense(
            1,
            activation=None,
        )(x)

    elif architecture == "mlp32":

        x = tf.keras.layers.Dense(
            32,
            activation="tanh",
        )(inp)

        x = tf.keras.layers.Dense(
            32,
            activation="tanh",
        )(x)

        raw = tf.keras.layers.Dense(
            1,
            activation=None,
        )(x)

    elif architecture == "dual24":

        shared = tf.keras.layers.Dense(
            24,
            activation="tanh",
        )(inp)

        shared = tf.keras.layers.Dense(
            24,
            activation="tanh",
        )(shared)

        global_head = tf.keras.layers.Dense(
            1,
            activation=None,
            name="global_head",
        )(shared)

        front_head = tf.keras.layers.Dense(
            16,
            activation="tanh",
        )(shared)

        front_head = tf.keras.layers.Dense(
            1,
            activation=None,
            name="front_head",
        )(front_head)

        front_distance = inp[:, 4:5]

        gate = tf.keras.layers.Lambda(
            lambda z: tf.exp(-tf.square(z / 0.06)),
            output_shape=(1,),
            name="front_gate",
        )(front_distance)

        raw = global_head + gate * front_head

    else:
        raise RuntimeError(
            f"Unhandled architecture: {architecture}"
        )

    out = tf.keras.layers.Lambda(
        lambda z: 0.10 * tf.tanh(z / 0.10),
        output_shape=(1,),
        name="bounded_deltaS",
    )(raw)

    model = tf.keras.Model(
        inp,
        out,
        name=experiment,
    )

    # Force variable creation before loading weights.
    _ = model(
        tf.zeros(
            (1, 5),
            dtype=tf.float32,
        ),
        training=False,
    )

    return model


def load_r3f1_calibrator_weights(experiment: str, checkpoint_path: str):
    """
    Rebuild trusted R3F1 architecture and load weights from the .keras artifact.

    Uses Keras' weight-loading pathway rather than serialized model-config
    deserialization, avoiding Lambda output-shape reconstruction errors.
    """

    model = build_r3f1_calibrator_for_experiment(
        experiment
    )

    checkpoint_path = Path(
        checkpoint_path
    )

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"R3F1 checkpoint not found:\n{checkpoint_path}"
        )

    try:
        model.load_weights(
            checkpoint_path,
        )

    except Exception as exc:
        raise RuntimeError(
            "Could not load R3F1 calibrator weights into the reconstructed "
            f"{experiment} architecture.\nCheckpoint:\n{checkpoint_path}\n\n"
            "This indicates an architecture/name mismatch rather than a physics "
            f"or validation failure.\nOriginal error: {exc}"
        ) from exc

    return model


# =============================================================================
# MAIN AUDIT
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F2A")
    print("Front-Correction Geometry / Topology Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 OR CALIBRATOR PARAMETERS WILL BE CHANGED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3F1R_SUMMARY,
        R3F1_CHECKPOINTS,
        R3F1_EPOCHS,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F2A prerequisite:\n{path}"
            )

    r3f1r = load_json(R3F1R_SUMMARY)

    if r3f1r.get("diagnosis") != "FRONT_CAPACITY_TOPOLOGY_TRADEOFF_CONFIRMED":
        raise RuntimeError(
            "R3F2A requires incoming diagnosis:\n"
            "FRONT_CAPACITY_TOPOLOGY_TRADEOFF_CONFIRMED"
        )

    checkpoint_rows = load_csv(R3F1_CHECKPOINTS)
    epoch_rows = load_csv(R3F1_EPOCHS)

    selected = select_checkpoints(
        checkpoint_rows,
        epoch_rows,
    )

    if not selected:
        raise RuntimeError(
            "No persisted R3F1 calibrator checkpoints were selected."
        )

    save_csv(
        CHECKPOINT_TABLE,
        selected,
    )

    db = np.load(
        R3C_NUMERICAL,
        allow_pickle=True,
    )

    frozen = np.asarray(
        db["deployment_pirnn"],
        dtype=float,
    )

    truth = np.asarray(
        db["deployment_truth"],
        dtype=float,
    )

    canonical = np.asarray(
        db["canonical_interpolated_target"],
        dtype=float,
    )

    tau_end_days = np.asarray(
        db["tau_end_days"],
        dtype=float,
    )

    times_days = np.asarray(
        db["times_days"],
        dtype=float,
    )

    normalized_tD = np.asarray(
        db["deployment_normalized_input"],
        dtype=float,
    )

    xi = np.asarray(
        db["canonical_xi"],
        dtype=float,
    )

    features = make_features(
        xi,
        normalized_tD,
        tau_end_days,
        frozen,
    )

    X = features.reshape(-1, 5)

    idx100 = int(
        np.argmin(
            np.abs(
                times_days - 100.0
            )
        )
    )

    truth100 = truth[idx100]
    frozen100 = frozen[idx100]
    canonical100 = canonical[idx100]

    truth_front_pos, truth_front_ok = crossing_arrays(
        truth100,
        xi,
        FRONT_THRESHOLD,
    )

    frozen_front_pos, frozen_front_ok = crossing_arrays(
        frozen100,
        xi,
        FRONT_THRESHOLD,
    )

    valid_truth = truth_front_ok

    print("\nSELECTED PERSISTED CHECKPOINTS")

    for row in selected:
        print(
            f"  {row['experiment']} | "
            f"checkpoint epoch={row['checkpoint_epoch']} | "
            f"best front epoch={row['best_front_epoch']} | "
            f"best frontRed={100*row['best_front_reduction_fraction']:.2f}%"
        )

    global_rows = []
    profile_rows = []
    distance_rows = []
    tof_rows = []

    experiment_fields = {}

    # -------------------------------------------------------------------------
    # Reconstruct each persisted checkpoint
    # -------------------------------------------------------------------------

    for selected_row in selected:

        exp = selected_row["experiment"]

        print("\n" + "=" * 78)
        print(f"GEOMETRY AUDIT — {exp}")
        print("=" * 78)

        # Rebuild the known R3F1 architecture and load only its weights.
        # This bypasses Keras 3 Lambda-config deserialization entirely.
        model = load_r3f1_calibrator_weights(
            exp,
            selected_row["checkpoint_path"],
        )

        delta = model.predict(
            X,
            batch_size=8192,
            verbose=0,
        ).reshape(frozen.shape)

        calibrated = frozen + delta

        experiment_fields[exp] = {
            "delta": delta,
            "calibrated": calibrated,
        }

        delta100 = delta[idx100]
        cal100 = calibrated[idx100]

        cal_front_pos, cal_front_ok = crossing_arrays(
            cal100,
            xi,
            FRONT_THRESHOLD,
        )

        common_truth = valid_truth & cal_front_ok

        common_frozen = (
            valid_truth
            &
            frozen_front_ok
            &
            cal_front_ok
        )

        if np.any(common_truth):
            truth_shift = np.abs(
                cal_front_pos[common_truth]
                -
                truth_front_pos[common_truth]
            )
        else:
            truth_shift = np.array([np.nan])

        if np.any(common_frozen):
            frozen_shift = np.abs(
                cal_front_pos[common_frozen]
                -
                frozen_front_pos[common_frozen]
            )
        else:
            frozen_shift = np.array([np.nan])

        shell = (
            (truth100 >= FRONT_SHELL_LOW)
            &
            (truth100 <= FRONT_SHELL_HIGH)
        )

        required100 = canonical100 - frozen100

        applied_shell = delta100[shell]
        required_shell = required100[shell]

        sign_agreement = float(
            np.mean(
                applied_shell * required_shell >= -1e-12
            )
        )

        overshoot = np.abs(applied_shell) > (
            np.abs(required_shell) + 1e-6
        )

        overshoot_fraction = float(
            np.mean(overshoot)
        )

        wrong_direction_fraction = float(
            1.0 - sign_agreement
        )

        # Front widths and gradients.
        width_truth = []
        width_frozen = []
        width_cal = []

        grad_truth = []
        grad_frozen = []
        grad_cal = []

        for i in np.where(valid_truth)[0]:

            wt = front_width(
                truth100[i],
                xi,
            )

            wf = front_width(
                frozen100[i],
                xi,
            )

            wc = front_width(
                cal100[i],
                xi,
            )

            gt = local_gradient_at(
                truth100[i],
                xi,
                truth_front_pos[i],
            )

            gf = local_gradient_at(
                frozen100[i],
                xi,
                frozen_front_pos[i]
                if frozen_front_ok[i]
                else np.nan,
            )

            gc = local_gradient_at(
                cal100[i],
                xi,
                cal_front_pos[i]
                if cal_front_ok[i]
                else np.nan,
            )

            width_truth.append(wt)
            width_frozen.append(wf)
            width_cal.append(wc)

            grad_truth.append(gt)
            grad_frozen.append(gf)
            grad_cal.append(gc)

            profile_rows.append({
                "experiment": exp,
                "streamline": int(i),
                "tau_end_days": float(tau_end_days[i]),
                "truth_front_xi": truth_front_pos[i],
                "frozen_front_xi": (
                    frozen_front_pos[i]
                    if frozen_front_ok[i]
                    else np.nan
                ),
                "calibrated_front_xi": (
                    cal_front_pos[i]
                    if cal_front_ok[i]
                    else np.nan
                ),
                "truth_front_width": wt,
                "frozen_front_width": wf,
                "calibrated_front_width": wc,
                "truth_front_gradient": gt,
                "frozen_front_gradient": gf,
                "calibrated_front_gradient": gc,
            })

        width_truth = np.asarray(width_truth, dtype=float)
        width_frozen = np.asarray(width_frozen, dtype=float)
        width_cal = np.asarray(width_cal, dtype=float)

        grad_truth = np.asarray(grad_truth, dtype=float)
        grad_frozen = np.asarray(grad_frozen, dtype=float)
        grad_cal = np.asarray(grad_cal, dtype=float)

        valid_width = (
            np.isfinite(width_truth)
            &
            np.isfinite(width_cal)
        )

        valid_grad = (
            np.isfinite(grad_truth)
            &
            np.isfinite(grad_cal)
        )

        if np.any(valid_width):
            width_abs_error = np.abs(
                width_cal[valid_width]
                -
                width_truth[valid_width]
            )

            width_ratio = width_cal[valid_width] / np.maximum(
                width_truth[valid_width],
                1e-12,
            )

            width_mae = float(
                np.mean(width_abs_error)
            )

            width_ratio_median = float(
                np.median(width_ratio)
            )

            width_ratio_p90 = float(
                np.percentile(
                    np.abs(width_ratio - 1.0),
                    90,
                )
            )
        else:
            width_mae = np.nan
            width_ratio_median = np.nan
            width_ratio_p90 = np.nan

        if np.any(valid_grad):

            grad_abs_error = np.abs(
                grad_cal[valid_grad]
                -
                grad_truth[valid_grad]
            )

            grad_mae = float(
                np.mean(grad_abs_error)
            )

            grad_ratio = np.abs(
                grad_cal[valid_grad]
            ) / np.maximum(
                np.abs(
                    grad_truth[valid_grad]
                ),
                1e-12,
            )

            grad_ratio_median = float(
                np.median(grad_ratio)
            )

        else:

            grad_mae = np.nan
            grad_ratio_median = np.nan

        mean_truth_shift = float(
            np.nanmean(truth_shift)
        )

        p90_truth_shift = float(
            np.nanpercentile(
                truth_shift,
                90,
            )
        )

        mean_frozen_shift = float(
            np.nanmean(frozen_shift)
        )

        p90_frozen_shift = float(
            np.nanpercentile(
                frozen_shift,
                90,
            )
        )

        global_rows.append({
            "experiment": exp,
            "recovered_fronts": int(np.sum(common_truth)),
            "truth_front_count": int(np.sum(valid_truth)),
            "mean_shift_vs_truth_xi": mean_truth_shift,
            "P90_shift_vs_truth_xi": p90_truth_shift,
            "mean_shift_vs_frozen_xi": mean_frozen_shift,
            "P90_shift_vs_frozen_xi": p90_frozen_shift,
            "front_wrong_direction_fraction": wrong_direction_fraction,
            "front_sign_agreement": sign_agreement,
            "front_overshoot_fraction": overshoot_fraction,
            "front_width_MAE_xi": width_mae,
            "front_width_ratio_median": width_ratio_median,
            "front_width_ratio_abs_error_P90": width_ratio_p90,
            "front_gradient_MAE": grad_mae,
            "front_gradient_ratio_median": grad_ratio_median,
        })

        print(f"  Recovered fronts           : {int(np.sum(common_truth))} / {int(np.sum(valid_truth))}")
        print(f"  Mean xi shift vs truth     : {mean_truth_shift:.6e}")
        print(f"  P90 xi shift vs truth      : {p90_truth_shift:.6e}")
        print(f"  Mean xi shift vs frozen    : {mean_frozen_shift:.6e}")
        print(f"  P90 xi shift vs frozen     : {p90_frozen_shift:.6e}")
        print(f"  Wrong-direction fraction   : {100*wrong_direction_fraction:.2f}%")
        print(f"  Overshoot fraction         : {100*overshoot_fraction:.2f}%")
        print(f"  Front-width MAE            : {width_mae:.6e}")
        print(f"  Median width ratio         : {width_ratio_median:.6f}")
        print(f"  Gradient MAE               : {grad_mae:.6e}")

        # ---------------------------------------------------------------------
        # Correction versus front-relative distance.
        # ---------------------------------------------------------------------

        for i in np.where(valid_truth)[0]:

            dxi = xi - truth_front_pos[i]

            abs_delta = np.abs(
                delta100[i]
            )

            required_i = required100[i]

            for b in range(
                len(FRONT_DISTANCE_BINS) - 1
            ):

                lo = FRONT_DISTANCE_BINS[b]
                hi = FRONT_DISTANCE_BINS[b + 1]

                mask = (
                    (dxi >= lo)
                    &
                    (dxi < hi)
                )

                if not np.any(mask):
                    continue

                applied = delta100[i][mask]
                required_local = required_i[mask]

                local_sign = float(
                    np.mean(
                        applied
                        *
                        required_local
                        >=
                        -1e-12
                    )
                )

                local_overshoot = float(
                    np.mean(
                        np.abs(applied)
                        >
                        (
                            np.abs(required_local)
                            +
                            1e-6
                        )
                    )
                )

                distance_rows.append({
                    "experiment": exp,
                    "streamline": int(i),
                    "distance_bin_low": float(lo),
                    "distance_bin_high": float(hi),
                    "node_count": int(np.sum(mask)),
                    "mean_abs_correction": float(np.mean(np.abs(applied))),
                    "mean_signed_correction": float(np.mean(applied)),
                    "mean_abs_required": float(np.mean(np.abs(required_local))),
                    "sign_agreement": local_sign,
                    "overshoot_fraction": local_overshoot,
                })

        # ---------------------------------------------------------------------
        # Correction by terminal TOF.
        # ---------------------------------------------------------------------

        for label, lo, hi in TOF_BANDS:

            sl = (
                (tau_end_days > lo)
                &
                (tau_end_days <= hi)
            )

            if not np.any(sl):
                continue

            vals = delta100[sl]
            req = required100[sl]

            tof_rows.append({
                "experiment": exp,
                "TOF_band": label,
                "streamlines": int(np.sum(sl)),
                "mean_abs_correction": float(np.mean(np.abs(vals))),
                "mean_signed_correction": float(np.mean(vals)),
                "mean_abs_required": float(np.mean(np.abs(req))),
                "sign_agreement": float(
                    np.mean(
                        vals * req >= -1e-12
                    )
                ),
                "overshoot_fraction": float(
                    np.mean(
                        np.abs(vals)
                        >
                        (
                            np.abs(req) + 1e-6
                        )
                    )
                ),
            })

    # -------------------------------------------------------------------------
    # Save tables
    # -------------------------------------------------------------------------

    save_csv(
        GLOBAL_TABLE,
        global_rows,
    )

    save_csv(
        PROFILE_TABLE,
        profile_rows,
    )

    save_csv(
        DISTANCE_TABLE,
        distance_rows,
    )

    save_csv(
        TOF_TABLE,
        tof_rows,
    )

    # -------------------------------------------------------------------------
    # Classification
    # -------------------------------------------------------------------------

    global_map = {
        row["experiment"]: row
        for row in global_rows
    }

    # Use F3 as the primary high-capacity reference where available.
    primary_exp = (
        "F3"
        if "F3" in global_map
        else max(
            global_rows,
            key=lambda r:
            r["front_wrong_direction_fraction"]
            +
            r["front_overshoot_fraction"],
        )["experiment"]
    )

    primary = global_map[primary_exp]

    displacement_material = bool(
        primary["P90_shift_vs_truth_xi"] > 5.0e-03
        or
        primary["P90_shift_vs_frozen_xi"] > 5.0e-03
    )

    wrong_direction_material = bool(
        primary["front_wrong_direction_fraction"] > 0.05
    )

    overshoot_material = bool(
        primary["front_overshoot_fraction"] > 0.05
    )

    width_material = bool(
        np.isfinite(primary["front_width_ratio_abs_error_P90"])
        and
        primary["front_width_ratio_abs_error_P90"] > 0.25
    )

    if (
        displacement_material
        and not width_material
        and not wrong_direction_material
        and not overshoot_material
    ):
        diagnosis = "CROSSING_DISPLACEMENT_DOMINANT"

        recommendation = (
            "The topology failure is dominated by front-position displacement. "
            "Design a correction parameterization that is explicitly zero-integral "
            "around the front and constrained to preserve the S=0.21 crossing."
        )

        next_milestone = (
            "V15-SG7C-R3F2B — Crossing-Preserving Front Correction Design"
        )

    elif (
        width_material
        and not wrong_direction_material
        and not overshoot_material
    ):
        diagnosis = "FRONT_BROADENING_OR_COMPRESSION_DOMINANT"

        recommendation = (
            "The main topology damage is front-width/gradient distortion. "
            "Design a shape-preserving local correction basis rather than increasing "
            "global residual capacity."
        )

        next_milestone = (
            "V15-SG7C-R3F2B — Shape-Preserving Front Correction Design"
        )

    elif (
        wrong_direction_material
        and not overshoot_material
    ):
        diagnosis = "WRONG_DIRECTION_CORRECTION_DOMINANT"

        recommendation = (
            "A material share of front-local calibration moves opposite the validated "
            "canonical residual direction. Design a sign-constrained front residual "
            "basis before further training."
        )

        next_milestone = (
            "V15-SG7C-R3F2B — Direction-Constrained Front Correction Design"
        )

    elif (
        overshoot_material
        and not wrong_direction_material
    ):
        diagnosis = "OVERSHOOT_DOMINANT"

        recommendation = (
            "Front-local correction generally points in the correct direction but "
            "frequently exceeds the validated canonical residual. Design a bounded "
            "fractional-residual correction rather than an unconstrained additive head."
        )

        next_milestone = (
            "V15-SG7C-R3F2B — Fractional-Residual Front Correction Design"
        )

    else:
        diagnosis = "MIXED_FRONT_GEOMETRY_FAILURE"

        recommendation = (
            "The topology tradeoff combines displacement, directionality, overshoot, "
            "and/or width distortion. Do not add more generic capacity. Design a "
            "front-local residual basis whose amplitude, sign, and crossing effect are "
            "explicitly controlled."
        )

        next_milestone = (
            "V15-SG7C-R3F3 — Front-Local Residual Basis Design"
        )

    # -------------------------------------------------------------------------
    # Diagnostic plots
    # -------------------------------------------------------------------------

    plt.figure(figsize=(9, 5))

    labels = [
        row["experiment"]
        for row in global_rows
    ]

    plt.bar(
        labels,
        [
            row["P90_shift_vs_truth_xi"]
            for row in global_rows
        ],
    )

    plt.axhline(
        5.0e-03,
        linestyle="--",
    )

    plt.ylabel(
        "P90 calibrated-front shift vs SG7A xi"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F2A Front Crossing Displacement"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F2A_Front_Crossing_Displacement.png",
        dpi=300,
    )

    plt.close()

    plt.figure(figsize=(9, 5))

    x = np.arange(
        len(global_rows)
    )

    width = 0.35

    plt.bar(
        x - width / 2,
        [
            row["front_wrong_direction_fraction"]
            for row in global_rows
        ],
        width=width,
        label="wrong direction",
    )

    plt.bar(
        x + width / 2,
        [
            row["front_overshoot_fraction"]
            for row in global_rows
        ],
        width=width,
        label="overshoot",
    )

    plt.axhline(
        0.05,
        linestyle="--",
    )

    plt.xticks(
        x,
        labels,
    )

    plt.ylabel(
        "Fraction of front-shell samples"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F2A Directionality / Overshoot"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F2A_Directionality_Overshoot.png",
        dpi=300,
    )

    plt.close()

    # Aggregate front-distance behavior by experiment.
    if distance_rows:

        plt.figure(figsize=(9, 5))

        for exp in sorted(
            set(
                row["experiment"]
                for row in distance_rows
            )
        ):

            rows = [
                row
                for row in distance_rows
                if row["experiment"] == exp
            ]

            centers = sorted(
                set(
                    0.5 * (
                        row["distance_bin_low"]
                        +
                        row["distance_bin_high"]
                    )
                    for row in rows
                )
            )

            ys = []

            for center in centers:

                vals = [
                    row["mean_abs_correction"]
                    for row in rows
                    if np.isclose(
                        0.5 * (
                            row["distance_bin_low"]
                            +
                            row["distance_bin_high"]
                        ),
                        center,
                    )
                ]

                ys.append(
                    float(
                        np.mean(vals)
                    )
                )

            plt.plot(
                centers,
                ys,
                marker="o",
                label=exp,
            )

        plt.axvline(
            0.0,
            linestyle="--",
        )

        plt.xlabel(
            "xi - SG7A front xi"
        )

        plt.ylabel(
            "Mean |deltaS|"
        )

        plt.title(
            "V15-SG7C-R3F2A Correction vs Front Distance"
        )

        plt.legend()

        plt.tight_layout()

        plt.savefig(
            OUTPUT_DIR
            /
            "V15SG7CR3F2A_Correction_vs_Front_Distance.png",
            dpi=300,
        )

        plt.close()

    # -------------------------------------------------------------------------
    # Validation and summary
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F2A DIAGNOSTIC VALIDATION")
    print("=" * 78)
    print("[PASS] R3F1-R topology-tradeoff diagnosis reproduced")
    print("[PASS] Persisted calibrator checkpoints loaded")
    print("[PASS] SG7A / frozen / canonical deployment fields reconstructed")
    print("[PASS] Calibrated front positions reconstructed")
    print("[PASS] Front-width and gradient diagnostics established")
    print("[PASS] Directionality and overshoot diagnostics established")
    print("[PASS] Front-distance correction structure established")
    print("[PASS] Terminal-TOF correction structure established")
    print("[PASS] Geometry/topology mechanism classified")
    print("=" * 78)

    print("\nPRIMARY HIGH-CAPACITY REFERENCE")
    print(f"  Experiment               : {primary_exp}")
    print(f"  P90 shift vs truth       : {primary['P90_shift_vs_truth_xi']:.6e}")
    print(f"  P90 shift vs frozen      : {primary['P90_shift_vs_frozen_xi']:.6e}")
    print(f"  Wrong-direction fraction : {100*primary['front_wrong_direction_fraction']:.2f}%")
    print(f"  Overshoot fraction       : {100*primary['front_overshoot_fraction']:.2f}%")
    print(f"  Width error P90          : {primary['front_width_ratio_abs_error_P90']:.6e}")

    print("\nDIAGNOSTIC FLAGS")
    print(f"  Crossing displacement material : {displacement_material}")
    print(f"  Width/gradient distortion      : {width_material}")
    print(f"  Wrong-direction material       : {wrong_direction_material}")
    print(f"  Overshoot material             : {overshoot_material}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    summary = {
        "milestone": "V15-SG7C-R3F2A",
        "status": "FRONT_CORRECTION_GEOMETRY_TOPOLOGY_AUDIT_COMPLETE",
        "incoming_diagnosis": r3f1r.get("diagnosis"),
        "primary_reference_experiment": primary_exp,
        "diagnosis": diagnosis,
        "flags": {
            "crossing_displacement_material": displacement_material,
            "front_width_distortion_material": width_material,
            "wrong_direction_correction_material": wrong_direction_material,
            "overshoot_material": overshoot_material,
        },
        "primary_metrics": primary,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nTables:")
    print(f"  {CHECKPOINT_TABLE.name}")
    print(f"  {GLOBAL_TABLE.name}")
    print(f"  {PROFILE_TABLE.name}")
    print(f"  {DISTANCE_TABLE.name}")
    print(f"  {TOF_TABLE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3F2A_Front_Crossing_Displacement.png")
    print("  V15SG7CR3F2A_Directionality_Overshoot.png")
    print("  V15SG7CR3F2A_Correction_vs_Front_Distance.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F2A AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No SG7B-11, calibrator, front, TOF-bias, map-back, or plume gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()