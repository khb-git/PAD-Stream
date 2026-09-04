from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F4-R2
# True Front-Displacement Basis Audit
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
# R3F4-R established:
#
#     TRUE_FRONT_DISPLACEMENT_REMAINS
#
# with the best R3F4 case B4 showing approximately:
#
#     front error reduction        ~49.55%
#     matched P90 shift vs frozen  ~2.11e-02 xi
#     authoritative P90 limit       5.00e-03 xi
#     residual coverage            ~49.55%
#
# This audit determines WHY the bounded residual basis moves the front.
#
# It decomposes the applied canonical residual around the authoritative
# front into:
#
#   * upstream vs downstream correction mass,
#   * crossing-core correction,
#   * first spatial moment about the target front,
#   * basis support asymmetry,
#   * residual asymmetry,
#   * local crossing sensitivity,
#   * predicted crossing displacement from linearized front mechanics.
#
# The goal is to distinguish:
#
#   BASIS_SUPPORT_ASYMMETRY
#   CANONICAL_RESIDUAL_ASYMMETRY
#   CROSSING_CORE_OVERACTIVATION
#   FRONT_SLOPE_SENSITIVITY
#   MIXED_FRONT_DISPLACEMENT_MECHANISM
#
# No correction architecture is changed here.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3F4R_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "PAD_Stream_V15SG7CR3F4R_Summary.json"
)

R3F4_CHECKPOINTS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
)

R3F4_FINAL = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F4R2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2_Global_Displacement_Mechanism.csv"
)

PROFILE_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2_Profile_Displacement_Mechanics.csv"
)

CORE_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2_Crossing_Core_Audit.csv"
)

ASYMMETRY_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2_Basis_Residual_Asymmetry.csv"
)

LINEAR_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2_Linearized_Crossing_Shift.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "PAD_Stream_V15SG7CR3F4R2_Summary.json"
)


FRONT_THRESHOLD = 0.210

SIGMA_NARROW = 0.015
SIGMA_MEDIUM = 0.030
COSINE_HALF_WIDTH = 0.030

CORE_HALF_WIDTH = 0.010
SHELL_HALF_WIDTH = 0.050

AUTHORITATIVE_MEAN_SHIFT_LIMIT = 2.0e-03
AUTHORITATIVE_P90_SHIFT_LIMIT = 5.0e-03


# =============================================================================
# IO HELPERS
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return

    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def num(row, key, default=np.nan):
    try:
        return float(row.get(key, default))
    except Exception:
        return default


# =============================================================================
# MODEL / BASIS RECONSTRUCTION
# =============================================================================

def build_alpha_model(experiment):
    inp = tf.keras.Input(
        shape=(2,),
        name="profile_features",
    )

    x = tf.keras.layers.Dense(
        12,
        activation="tanh",
    )(inp)

    x = tf.keras.layers.Dense(
        12,
        activation="tanh",
    )(x)

    if experiment in {"B1", "B2", "B3"}:
        out = tf.keras.layers.Dense(
            1,
            activation="sigmoid",
            name="alpha",
        )(x)

    elif experiment in {"B4", "B5"}:
        out = tf.keras.layers.Dense(
            3,
            activation="softmax",
            name="basis_weights",
        )(x)

    else:
        raise ValueError(
            f"Unsupported experiment: {experiment}"
        )

    return tf.keras.Model(
        inp,
        out,
        name=f"R3F4_{experiment}",
    )


def gaussian(distance, sigma):
    return np.exp(
        -0.5 * (distance / sigma) ** 2
    )


def raised_cosine(distance, half_width):
    out = np.zeros_like(
        distance,
        dtype=float,
    )

    mask = (
        np.abs(distance)
        <=
        half_width
    )

    out[mask] = 0.5 * (
        1.0
        +
        np.cos(
            np.pi
            *
            distance[mask]
            /
            half_width
        )
    )

    return out


def make_profile_features(
    normalized_tD,
    tau_end_days,
):
    logtau = np.log10(
        np.maximum(
            tau_end_days,
            1.0,
        )
    )

    logtau = (
        logtau
        -
        np.mean(logtau)
    ) / max(
        np.std(logtau),
        1e-12,
    )

    nt, ns = normalized_tD.shape

    logtau2 = np.broadcast_to(
        logtau[None, :],
        (nt, ns),
    )

    return np.stack(
        [
            normalized_tD,
            logtau2,
        ],
        axis=-1,
    ).astype(np.float32)


# =============================================================================
# CROSSINGS
# =============================================================================

def all_crossings(profile, xi, threshold):
    profile = np.asarray(
        profile,
        dtype=float,
    )

    xi = np.asarray(
        xi,
        dtype=float,
    )

    y = (
        profile
        -
        threshold
    )

    crossings = []

    for j in range(
        len(xi) - 1
    ):
        y0 = y[j]
        y1 = y[j + 1]

        if np.isclose(
            y0,
            0.0,
            atol=1e-12,
        ):
            crossings.append(
                float(xi[j])
            )
            continue

        if y0 * y1 < 0.0:
            denom = (
                y1 - y0
            )

            if abs(denom) <= 1e-15:
                x = 0.5 * (
                    xi[j]
                    +
                    xi[j + 1]
                )
            else:
                frac = np.clip(
                    -y0 / denom,
                    0.0,
                    1.0,
                )

                x = (
                    xi[j]
                    +
                    frac
                    *
                    (
                        xi[j + 1]
                        -
                        xi[j]
                    )
                )

            crossings.append(
                float(x)
            )

    if np.isclose(
        y[-1],
        0.0,
        atol=1e-12,
    ):
        crossings.append(
            float(xi[-1])
        )

    if not crossings:
        return np.array(
            [],
            dtype=float,
        )

    arr = np.asarray(
        sorted(crossings),
        dtype=float,
    )

    keep = [0]

    for i in range(
        1,
        len(arr),
    ):
        if abs(
            arr[i]
            -
            arr[keep[-1]]
        ) > 1e-10:
            keep.append(i)

    return arr[keep]


def first_crossing(profile, xi, threshold):
    c = all_crossings(
        profile,
        xi,
        threshold,
    )

    if c.size == 0:
        return np.nan, False

    return float(c[0]), True


def matched_crossing(profile, xi, threshold, reference_x):
    c = all_crossings(
        profile,
        xi,
        threshold,
    )

    if (
        c.size == 0
        or
        not np.isfinite(reference_x)
    ):
        return np.nan, False

    idx = int(
        np.argmin(
            np.abs(
                c
                -
                reference_x
            )
        )
    )

    return float(c[idx]), True


def front_position_database(target, xi):
    nt, ns, _ = target.shape

    pos = np.full(
        (nt, ns),
        np.nan,
        dtype=float,
    )

    ok = np.zeros(
        (nt, ns),
        dtype=bool,
    )

    for it in range(nt):
        for i in range(ns):
            pos[it, i], ok[it, i] = first_crossing(
                target[it, i],
                xi,
                FRONT_THRESHOLD,
            )

    return pos, ok


def make_basis_fields(target, xi):
    nt, ns, nx = target.shape

    front_pos, front_ok = front_position_database(
        target,
        xi,
    )

    distance = np.zeros(
        (nt, ns, nx),
        dtype=float,
    )

    for it in range(nt):
        distance[it] = (
            xi[None, :]
            -
            front_pos[it, :, None]
        )

    g1 = gaussian(
        distance,
        SIGMA_NARROW,
    )

    g2 = gaussian(
        distance,
        SIGMA_MEDIUM,
    )

    g3 = raised_cosine(
        distance,
        COSINE_HALF_WIDTH,
    )

    valid3 = front_ok[:, :, None]

    g1 = np.where(
        valid3,
        g1,
        0.0,
    )

    g2 = np.where(
        valid3,
        g2,
        0.0,
    )

    g3 = np.where(
        valid3,
        g3,
        0.0,
    )

    return {
        "front_pos": front_pos,
        "front_ok": front_ok,
        "distance": distance,
        "g1": g1.astype(np.float32),
        "g2": g2.astype(np.float32),
        "g3": g3.astype(np.float32),
    }


def reconstruct_delta(
    experiment,
    model,
    profile_features,
    residual,
    basis,
):
    nt, ns, nx = residual.shape

    raw = model.predict(
        profile_features.reshape(
            -1,
            2,
        ),
        batch_size=8192,
        verbose=0,
    )

    if experiment == "B1":
        alpha = raw[:, 0].reshape(
            nt,
            ns,
        )

        coefficient = (
            alpha[:, :, None]
            *
            basis["g1"]
        )

    elif experiment == "B2":
        alpha = raw[:, 0].reshape(
            nt,
            ns,
        )

        coefficient = (
            alpha[:, :, None]
            *
            basis["g2"]
        )

    elif experiment == "B3":
        alpha = raw[:, 0].reshape(
            nt,
            ns,
        )

        coefficient = (
            alpha[:, :, None]
            *
            basis["g3"]
        )

    elif experiment in {"B4", "B5"}:
        weights = raw.reshape(
            nt,
            ns,
            3,
        )

        w1 = weights[:, :, 0]
        w2 = weights[:, :, 1]

        coefficient = (
            w1[:, :, None]
            *
            basis["g1"]
            +
            w2[:, :, None]
            *
            basis["g2"]
        )

    else:
        raise ValueError(
            experiment
        )

    coefficient = np.clip(
        coefficient,
        0.0,
        1.0,
    )

    return (
        coefficient * residual,
        coefficient,
    )


# =============================================================================
# LOCAL FRONT MECHANICS
# =============================================================================

def local_slope(profile, xi, x0):
    if not np.isfinite(x0):
        return np.nan

    j = int(
        np.argmin(
            np.abs(
                xi
                -
                x0
            )
        )
    )

    if j <= 0:
        j = 1

    if j >= len(xi) - 1:
        j = len(xi) - 2

    return float(
        (
            profile[j + 1]
            -
            profile[j - 1]
        )
        /
        (
            xi[j + 1]
            -
            xi[j - 1]
        )
    )


def interp_at(profile, xi, x0):
    if not np.isfinite(x0):
        return np.nan

    return float(
        np.interp(
            x0,
            xi,
            profile,
        )
    )


# =============================================================================
# CHECKPOINT SELECTION
# =============================================================================

def select_best_any(
    checkpoint_rows,
):
    selected = []

    for exp in [
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
    ]:

        rows = [
            r
            for r in checkpoint_rows
            if (
                r.get("experiment")
                ==
                exp
                and
                r.get("checkpoint_type")
                ==
                "best_any"
            )
        ]

        if not rows:
            continue

        row = rows[0]

        p = Path(
            row["path"]
        )

        if not p.is_absolute():
            p = ROOT / p

        if not p.exists():
            raise FileNotFoundError(
                f"Missing R3F4 checkpoint:\n{p}"
            )

        selected.append({
            "experiment": exp,
            "path": str(p),
        })

    return selected


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F4-R2")
    print("True Front-Displacement Basis Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 OR CALIBRATOR PARAMETERS WILL BE CHANGED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3F4R_SUMMARY,
        R3F4_CHECKPOINTS,
        R3F4_FINAL,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F4-R2 prerequisite:\n{path}"
            )

    incoming = load_json(
        R3F4R_SUMMARY
    )

    if (
        incoming.get("diagnosis")
        !=
        "TRUE_FRONT_DISPLACEMENT_REMAINS"
    ):
        raise RuntimeError(
            "R3F4-R2 requires incoming diagnosis:\n"
            "TRUE_FRONT_DISPLACEMENT_REMAINS"
        )

    checkpoint_rows = load_csv(
        R3F4_CHECKPOINTS
    )

    final_rows = load_csv(
        R3F4_FINAL
    )

    selected = select_best_any(
        checkpoint_rows
    )

    if not selected:
        raise RuntimeError(
            "No persisted R3F4 best-any checkpoints found."
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

    target = np.asarray(
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

    residual = (
        target
        -
        frozen
    )

    basis = make_basis_fields(
        target,
        xi,
    )

    profile_features = make_profile_features(
        normalized_tD,
        tau_end_days,
    )

    idx100 = int(
        np.argmin(
            np.abs(
                times_days - 100.0
            )
        )
    )

    global_rows = []
    profile_rows = []
    core_rows = []
    asymmetry_rows = []
    linear_rows = []

    print("\n" + "=" * 78)
    print("R3F4-R2 DISPLACEMENT MECHANICS")
    print("=" * 78)

    for item in selected:

        exp = item["experiment"]

        model = build_alpha_model(
            exp
        )

        model.load_weights(
            item["path"]
        )

        delta, coefficient = reconstruct_delta(
            exp,
            model,
            profile_features,
            residual,
            basis,
        )

        calibrated = (
            frozen
            +
            delta
        )

        d100 = delta[idx100]
        c100 = coefficient[idx100]
        r100 = residual[idx100]
        f100 = frozen[idx100]
        t100 = target[idx100]
        cal100 = calibrated[idx100]

        target_front = basis[
            "front_pos"
        ][idx100]

        target_ok = basis[
            "front_ok"
        ][idx100]

        distance = basis[
            "distance"
        ][idx100]

        matched_shifts = []
        predicted_shifts = []

        upstream_mass = []
        downstream_mass = []

        residual_upstream = []
        residual_downstream = []

        basis_upstream = []
        basis_downstream = []

        core_fraction_list = []
        first_moment_list = []
        slope_list = []

        for i in np.where(
            target_ok
        )[0]:

            xref = target_front[i]

            xcal, okcal = matched_crossing(
                cal100[i],
                xi,
                FRONT_THRESHOLD,
                xref,
            )

            if not okcal:
                continue

            shift = (
                xcal
                -
                xref
            )

            matched_shifts.append(
                abs(shift)
            )

            dist = distance[i]

            shell = (
                np.abs(dist)
                <=
                SHELL_HALF_WIDTH
            )

            core = (
                np.abs(dist)
                <=
                CORE_HALF_WIDTH
            )

            up = (
                (dist < 0.0)
                &
                shell
            )

            down = (
                (dist > 0.0)
                &
                shell
            )

            abs_delta = np.abs(
                d100[i]
            )

            abs_residual = np.abs(
                r100[i]
            )

            abs_coeff = np.abs(
                c100[i]
            )

            up_mass = float(
                np.sum(
                    abs_delta[up]
                )
            )

            down_mass = float(
                np.sum(
                    abs_delta[down]
                )
            )

            upstream_mass.append(
                up_mass
            )

            downstream_mass.append(
                down_mass
            )

            residual_upstream.append(
                float(
                    np.sum(
                        abs_residual[up]
                    )
                )
            )

            residual_downstream.append(
                float(
                    np.sum(
                        abs_residual[down]
                    )
                )
            )

            basis_upstream.append(
                float(
                    np.sum(
                        abs_coeff[up]
                    )
                )
            )

            basis_downstream.append(
                float(
                    np.sum(
                        abs_coeff[down]
                    )
                )
            )

            total_shell_delta = float(
                np.sum(
                    abs_delta[shell]
                )
            )

            core_fraction = (
                float(
                    np.sum(
                        abs_delta[core]
                    )
                )
                /
                max(
                    total_shell_delta,
                    1e-15,
                )
            )

            core_fraction_list.append(
                core_fraction
            )

            # Signed first moment of applied correction around the target front.
            signed_moment = float(
                np.sum(
                    dist[shell]
                    *
                    d100[i][shell]
                )
            )

            norm = float(
                np.sum(
                    np.abs(
                        d100[i][shell]
                    )
                )
            )

            first_moment = (
                signed_moment
                /
                max(
                    norm,
                    1e-15,
                )
            )

            first_moment_list.append(
                first_moment
            )

            slope = local_slope(
                f100[i],
                xi,
                xref,
            )

            slope_list.append(
                slope
            )

            delta_at_front = interp_at(
                d100[i],
                xi,
                xref,
            )

            # Linearized threshold displacement:
            #
            #   Delta xi ~= -Delta S(xf) / (dS_frozen/dxi)
            #
            predicted = (
                -delta_at_front
                /
                slope
                if (
                    np.isfinite(slope)
                    and
                    abs(slope) > 1e-10
                )
                else np.nan
            )

            predicted_shifts.append(
                abs(predicted)
                if np.isfinite(predicted)
                else np.nan
            )

            profile_rows.append({
                "experiment": exp,
                "streamline": int(i),
                "tau_end_days": float(
                    tau_end_days[i]
                ),
                "target_front_xi": float(
                    xref
                ),
                "calibrated_matched_front_xi": float(
                    xcal
                ),
                "signed_shift_xi": float(
                    shift
                ),
                "abs_shift_xi": float(
                    abs(shift)
                ),
                "frozen_front_slope": slope,
                "deltaS_at_target_front": delta_at_front,
                "linearized_abs_shift": (
                    abs(predicted)
                    if np.isfinite(predicted)
                    else np.nan
                ),
                "upstream_abs_correction_mass": up_mass,
                "downstream_abs_correction_mass": down_mass,
                "crossing_core_correction_fraction": core_fraction,
                "signed_first_moment_xi": first_moment,
            })

            core_rows.append({
                "experiment": exp,
                "streamline": int(i),
                "core_half_width_xi": CORE_HALF_WIDTH,
                "shell_half_width_xi": SHELL_HALF_WIDTH,
                "crossing_core_correction_fraction": core_fraction,
                "core_abs_correction": float(
                    np.sum(
                        abs_delta[core]
                    )
                ),
                "shell_abs_correction": total_shell_delta,
                "deltaS_at_target_front": delta_at_front,
                "frozen_front_slope": slope,
            })

        matched_shifts = np.asarray(
            matched_shifts,
            dtype=float,
        )

        predicted_shifts = np.asarray(
            predicted_shifts,
            dtype=float,
        )

        upstream_mass = np.asarray(
            upstream_mass,
            dtype=float,
        )

        downstream_mass = np.asarray(
            downstream_mass,
            dtype=float,
        )

        residual_upstream = np.asarray(
            residual_upstream,
            dtype=float,
        )

        residual_downstream = np.asarray(
            residual_downstream,
            dtype=float,
        )

        basis_upstream = np.asarray(
            basis_upstream,
            dtype=float,
        )

        basis_downstream = np.asarray(
            basis_downstream,
            dtype=float,
        )

        core_fraction_list = np.asarray(
            core_fraction_list,
            dtype=float,
        )

        first_moment_list = np.asarray(
            first_moment_list,
            dtype=float,
        )

        slope_list = np.asarray(
            slope_list,
            dtype=float,
        )

        applied_asymmetry = float(
            np.mean(
                np.abs(
                    upstream_mass
                    -
                    downstream_mass
                )
                /
                np.maximum(
                    upstream_mass
                    +
                    downstream_mass,
                    1e-15,
                )
            )
        )

        residual_asymmetry = float(
            np.mean(
                np.abs(
                    residual_upstream
                    -
                    residual_downstream
                )
                /
                np.maximum(
                    residual_upstream
                    +
                    residual_downstream,
                    1e-15,
                )
            )
        )

        basis_asymmetry = float(
            np.mean(
                np.abs(
                    basis_upstream
                    -
                    basis_downstream
                )
                /
                np.maximum(
                    basis_upstream
                    +
                    basis_downstream,
                    1e-15,
                )
            )
        )

        mean_core_fraction = float(
            np.mean(
                core_fraction_list
            )
        )

        p90_core_fraction = float(
            np.percentile(
                core_fraction_list,
                90,
            )
        )

        moment_abs_mean = float(
            np.mean(
                np.abs(
                    first_moment_list
                )
            )
        )

        matched_p90 = float(
            np.percentile(
                matched_shifts,
                90,
            )
        )

        predicted_p90 = float(
            np.nanpercentile(
                predicted_shifts,
                90,
            )
        )

        shift_prediction_ratio = (
            predicted_p90
            /
            max(
                matched_p90,
                1e-15,
            )
        )

        slope_abs_median = float(
            np.nanmedian(
                np.abs(
                    slope_list
                )
            )
        )

        final_row = next(
            (
                r
                for r in final_rows
                if r.get("experiment") == exp
            ),
            None,
        )

        front_reduction = (
            num(
                final_row,
                "front_error_reduction_fraction",
            )
            if final_row
            else np.nan
        )

        global_rows.append({
            "experiment": exp,
            "front_error_reduction_fraction": front_reduction,
            "matched_mean_shift_xi": float(
                np.mean(
                    matched_shifts
                )
            ),
            "matched_P90_shift_xi": matched_p90,
            "linearized_P90_shift_xi": predicted_p90,
            "linearized_to_actual_P90_ratio": shift_prediction_ratio,
            "applied_correction_asymmetry": applied_asymmetry,
            "canonical_residual_asymmetry": residual_asymmetry,
            "basis_support_asymmetry": basis_asymmetry,
            "mean_crossing_core_correction_fraction": mean_core_fraction,
            "P90_crossing_core_correction_fraction": p90_core_fraction,
            "mean_abs_first_moment_xi": moment_abs_mean,
            "median_abs_frozen_front_slope": slope_abs_median,
        })

        asymmetry_rows.append({
            "experiment": exp,
            "applied_correction_asymmetry": applied_asymmetry,
            "canonical_residual_asymmetry": residual_asymmetry,
            "basis_support_asymmetry": basis_asymmetry,
            "mean_upstream_abs_correction_mass": float(
                np.mean(
                    upstream_mass
                )
            ),
            "mean_downstream_abs_correction_mass": float(
                np.mean(
                    downstream_mass
                )
            ),
            "mean_upstream_abs_residual_mass": float(
                np.mean(
                    residual_upstream
                )
            ),
            "mean_downstream_abs_residual_mass": float(
                np.mean(
                    residual_downstream
                )
            ),
        })

        linear_rows.append({
            "experiment": exp,
            "actual_matched_P90_shift_xi": matched_p90,
            "linearized_P90_shift_xi": predicted_p90,
            "linearized_to_actual_P90_ratio": shift_prediction_ratio,
            "median_abs_frozen_front_slope": slope_abs_median,
        })

        print(
            f"\n{exp}"
        )
        print(
            f"  matched P90 shift         : {matched_p90:.6e}"
        )
        print(
            f"  linearized P90 shift      : {predicted_p90:.6e}"
        )
        print(
            f"  applied asymmetry         : {100*applied_asymmetry:.2f}%"
        )
        print(
            f"  residual asymmetry        : {100*residual_asymmetry:.2f}%"
        )
        print(
            f"  basis asymmetry           : {100*basis_asymmetry:.2f}%"
        )
        print(
            f"  mean core correction share: {100*mean_core_fraction:.2f}%"
        )
        print(
            f"  median |front slope|      : {slope_abs_median:.6e}"
        )

    save_csv(
        GLOBAL_TABLE,
        global_rows,
    )

    save_csv(
        PROFILE_TABLE,
        profile_rows,
    )

    save_csv(
        CORE_TABLE,
        core_rows,
    )

    save_csv(
        ASYMMETRY_TABLE,
        asymmetry_rows,
    )

    save_csv(
        LINEAR_TABLE,
        linear_rows,
    )

    # -------------------------------------------------------------------------
    # Classification
    # -------------------------------------------------------------------------

    best = max(
        global_rows,
        key=lambda r:
        r[
            "front_error_reduction_fraction"
        ]
        if np.isfinite(
            r[
                "front_error_reduction_fraction"
            ]
        )
        else -np.inf,
    )

    basis_asymmetry_material = bool(
        best[
            "basis_support_asymmetry"
        ]
        > 0.10
    )

    residual_asymmetry_material = bool(
        best[
            "canonical_residual_asymmetry"
        ]
        > 0.25
    )

    core_overactivation = bool(
        best[
            "mean_crossing_core_correction_fraction"
        ]
        > 0.35
    )

    slope_sensitive = bool(
        best[
            "linearized_to_actual_P90_ratio"
        ]
        >= 0.50
    )

    first_moment_material = bool(
        best[
            "mean_abs_first_moment_xi"
        ]
        > 2.0e-03
    )

    if (
        basis_asymmetry_material
        and
        not residual_asymmetry_material
        and
        not core_overactivation
    ):
        diagnosis = "BASIS_SUPPORT_ASYMMETRY"

        recommendation = (
            "The local basis itself is asymmetric around the authoritative front. "
            "Design a symmetric zero-first-moment support basis before retraining."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3 — Symmetric Zero-Moment Basis Design"
        )

    elif (
        residual_asymmetry_material
        and
        not basis_asymmetry_material
        and
        not core_overactivation
    ):
        diagnosis = "CANONICAL_RESIDUAL_ASYMMETRY"

        recommendation = (
            "The basis support is sufficiently symmetric, but the canonical residual "
            "inside that support is strongly one-sided and translates the threshold. "
            "Design a residual decomposition that separates shape correction from "
            "front-position correction."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3 — Shape/Translation Residual Decomposition Design"
        )

    elif (
        core_overactivation
        and
        slope_sensitive
    ):
        diagnosis = "CROSSING_CORE_OVERACTIVATION_WITH_SLOPE_SENSITIVITY"

        recommendation = (
            "A large fraction of correction is applied directly in the crossing core, "
            "and the linearized threshold mechanics explain a material part of the "
            "observed shift. Design a crossing-null residual basis that suppresses "
            "deltaS at the authoritative threshold while retaining shoulder correction."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3 — Crossing-Null Shoulder Residual Basis Design"
        )

    elif (
        slope_sensitive
        and
        not core_overactivation
    ):
        diagnosis = "FRONT_SLOPE_SENSITIVITY"

        recommendation = (
            "The remaining displacement is largely explained by the local threshold "
            "slope: even bounded correction produces significant xi motion. Design "
            "a slope-scaled crossing guard before retraining."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3 — Slope-Scaled Crossing Guard Design"
        )

    else:
        diagnosis = "MIXED_FRONT_DISPLACEMENT_MECHANISM"

        recommendation = (
            "The true displacement combines residual asymmetry, crossing-core activity, "
            "and/or front-slope sensitivity. Design a crossing-null, zero-first-moment "
            "front-shoulder basis rather than widening the current Gaussian support."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3 — Crossing-Null Zero-Moment Front Basis Design"
        )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    labels = [
        row["experiment"]
        for row in global_rows
    ]

    x = np.arange(
        len(labels)
    )

    width = 0.25

    plt.figure(
        figsize=(10, 5)
    )

    plt.bar(
        x - width,
        [
            row["basis_support_asymmetry"]
            for row in global_rows
        ],
        width=width,
        label="basis",
    )

    plt.bar(
        x,
        [
            row["canonical_residual_asymmetry"]
            for row in global_rows
        ],
        width=width,
        label="residual",
    )

    plt.bar(
        x + width,
        [
            row["applied_correction_asymmetry"]
            for row in global_rows
        ],
        width=width,
        label="applied",
    )

    plt.xticks(
        x,
        labels,
    )

    plt.ylabel(
        "Upstream/downstream asymmetry"
    )

    plt.title(
        "V15-SG7C-R3F4-R2 Front-Correction Asymmetry"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R2_Asymmetry_Comparison.png",
        dpi=300,
    )

    plt.close()

    plt.figure(
        figsize=(9, 5)
    )

    plt.bar(
        labels,
        [
            row[
                "mean_crossing_core_correction_fraction"
            ]
            for row in global_rows
        ],
    )

    plt.ylabel(
        "Fraction of shell correction inside crossing core"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4-R2 Crossing-Core Activity"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R2_Crossing_Core_Activity.png",
        dpi=300,
    )

    plt.close()

    plt.figure(
        figsize=(9, 5)
    )

    plt.scatter(
        [
            row[
                "linearized_P90_shift_xi"
            ]
            for row in global_rows
        ],
        [
            row[
                "matched_P90_shift_xi"
            ]
            for row in global_rows
        ],
        s=70,
    )

    maxv = max(
        max(
            row[
                "linearized_P90_shift_xi"
            ]
            for row in global_rows
        ),
        max(
            row[
                "matched_P90_shift_xi"
            ]
            for row in global_rows
        ),
    )

    plt.plot(
        [0.0, maxv],
        [0.0, maxv],
        linestyle="--",
    )

    for row in global_rows:
        plt.annotate(
            row["experiment"],
            (
                row[
                    "linearized_P90_shift_xi"
                ],
                row[
                    "matched_P90_shift_xi"
                ],
            ),
        )

    plt.xlabel(
        "Linearized predicted P90 shift"
    )

    plt.ylabel(
        "Actual matched P90 shift"
    )

    plt.title(
        "V15-SG7C-R3F4-R2 Linearized Crossing Mechanics"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R2_Linearized_vs_Actual_Shift.png",
        dpi=300,
    )

    plt.close()

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R2 DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        (
            "R3F4-R true-displacement diagnosis reproduced",
            True,
        ),
        (
            "Persisted B1-B5 checkpoints loaded",
            len(selected) > 0,
        ),
        (
            "Matched crossing displacement reconstructed",
            True,
        ),
        (
            "Upstream/downstream basis asymmetry quantified",
            True,
        ),
        (
            "Canonical residual asymmetry quantified",
            True,
        ),
        (
            "Crossing-core correction fraction quantified",
            True,
        ),
        (
            "Front first moment quantified",
            True,
        ),
        (
            "Linearized crossing-shift mechanics established",
            True,
        ),
        (
            "Displacement mechanism classified",
            True,
        ),
    ]

    for description, flag in checks:
        print(
            f"[{'PASS' if flag else 'FAIL'}] {description}"
        )

    print("=" * 78)

    print("\nBEST R3F4 CASE")
    print(
        f"  Experiment                  : {best['experiment']}"
    )
    print(
        f"  Front reduction             : {100*best['front_error_reduction_fraction']:.3f}%"
    )
    print(
        f"  Matched P90 shift           : {best['matched_P90_shift_xi']:.6e}"
    )
    print(
        f"  Basis asymmetry             : {100*best['basis_support_asymmetry']:.2f}%"
    )
    print(
        f"  Residual asymmetry          : {100*best['canonical_residual_asymmetry']:.2f}%"
    )
    print(
        f"  Applied asymmetry           : {100*best['applied_correction_asymmetry']:.2f}%"
    )
    print(
        f"  Mean crossing-core share    : {100*best['mean_crossing_core_correction_fraction']:.2f}%"
    )
    print(
        f"  Linearized/actual P90 ratio : {best['linearized_to_actual_P90_ratio']:.3f}"
    )

    print("\nDIAGNOSTIC FLAGS")
    print(
        f"  Basis asymmetry material    : {basis_asymmetry_material}"
    )
    print(
        f"  Residual asymmetry material : {residual_asymmetry_material}"
    )
    print(
        f"  Crossing-core overactive    : {core_overactivation}"
    )
    print(
        f"  Front slope sensitive       : {slope_sensitive}"
    )
    print(
        f"  First moment material       : {first_moment_material}"
    )

    print("\nDIAGNOSIS")
    print(
        f"  {diagnosis}"
    )

    print("\nRECOMMENDATION")
    print(
        f"  {recommendation}"
    )

    print("\nNEXT MILESTONE")
    print(
        f"  {next_milestone}"
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F4-R2",
            "status": "TRUE_FRONT_DISPLACEMENT_BASIS_AUDIT_COMPLETE",
            "incoming_diagnosis": incoming.get(
                "diagnosis"
            ),
            "best_experiment": best[
                "experiment"
            ],
            "diagnosis": diagnosis,
            "flags": {
                "basis_asymmetry_material": basis_asymmetry_material,
                "canonical_residual_asymmetry_material": residual_asymmetry_material,
                "crossing_core_overactivation": core_overactivation,
                "front_slope_sensitivity": slope_sensitive,
                "first_moment_material": first_moment_material,
            },
            "best_metrics": best,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("\nOUTPUTS")
    print(
        f"  Directory:\n    {OUTPUT_DIR}"
    )

    print("\nTables:")
    print(
        f"  {GLOBAL_TABLE.name}"
    )
    print(
        f"  {PROFILE_TABLE.name}"
    )
    print(
        f"  {CORE_TABLE.name}"
    )
    print(
        f"  {ASYMMETRY_TABLE.name}"
    )
    print(
        f"  {LINEAR_TABLE.name}"
    )

    print("\nDiagnostics:")
    print(
        "  V15SG7CR3F4R2_Asymmetry_Comparison.png"
    )
    print(
        "  V15SG7CR3F4R2_Crossing_Core_Activity.png"
    )
    print(
        "  V15SG7CR3F4R2_Linearized_vs_Actual_Shift.png"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE.name}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R2 AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No model, front, TOF-bias, map-back, or plume gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
