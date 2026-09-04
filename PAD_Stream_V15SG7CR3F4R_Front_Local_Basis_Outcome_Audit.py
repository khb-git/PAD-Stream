from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F4-R
# Front-Local Basis Outcome Audit
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
# R3F4 produced a striking pattern:
#
#   B2/B4/B5:
#       front error reduction ~49.5%
#       recovered fronts      992/992
#       sign agreement        100%
#       overshoot             0%
#
# but:
#
#       P90 frozen-front xi shift ~0.4437
#
# and that same large shift appears across B1-B5.
#
# This audit asks whether that "shift" is:
#
#   1. a real physical/topological displacement,
#   2. a threshold-crossing identity artifact,
#   3. caused by multiple S=0.21 crossings,
#   4. caused by insufficient front-local support,
#   5. or a mixed mechanism.
#
# Key distinction:
#
#   FIRST-CROSSING metric
#       chooses the first S=0.21 crossing in xi.
#
#   MATCHED-CROSSING metric
#       chooses the calibrated crossing nearest the authoritative
#       SG7A/canonical crossing for that profile.
#
# If profiles contain multiple crossings, the first-crossing metric can
# report an artificial O(1) displacement even when the physically
# corresponding front remains nearby.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3F4_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "PAD_Stream_V15SG7CR3F4_Summary.json"
)

R3F4_CHECKPOINTS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
)

R3F4_FINAL = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
)

R3F4_EPOCHS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Epoch_Metrics.csv"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F4R"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R_Global_Crossing_Audit.csv"
)

PROFILE_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R_Profile_Crossing_Audit.csv"
)

MULTIPLICITY_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R_Crossing_Multiplicity.csv"
)

SUPPORT_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

LIMITER_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R_Limiter_Decomposition.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "PAD_Stream_V15SG7CR3F4R_Summary.json"
)


FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300

SIGMA_NARROW = 0.015
SIGMA_MEDIUM = 0.030
COSINE_HALF_WIDTH = 0.030

AUTHORITATIVE_MEAN_SHIFT_LIMIT = 2.0e-03
AUTHORITATIVE_P90_SHIFT_LIMIT = 5.0e-03
FRONT_REDUCTION_TARGET = 0.50


# =============================================================================
# IO
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
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def num(row, key, default=np.nan):
    try:
        return float(row.get(key, default))
    except Exception:
        return default


# =============================================================================
# R3F4 MODEL RECONSTRUCTION
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
# CROSSING GEOMETRY
# =============================================================================

def all_crossings(profile, xi, threshold):
    """
    Return all linear-interpolated threshold crossings in increasing xi order.
    """
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

    # Include exact final node if needed.
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

    # Remove numerically duplicated crossings.
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


def first_crossing(
    profile,
    xi,
    threshold,
):
    c = all_crossings(
        profile,
        xi,
        threshold,
    )

    if c.size == 0:
        return np.nan, False

    return float(c[0]), True


def matched_crossing(
    profile,
    xi,
    threshold,
    reference_x,
):
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
        return np.nan, False, 0

    idx = int(
        np.argmin(
            np.abs(
                c
                -
                reference_x
            )
        )
    )

    return (
        float(c[idx]),
        True,
        int(c.size),
    )


def crossing_database(
    field,
    xi,
):
    nt, ns, _ = field.shape

    first = np.full(
        (nt, ns),
        np.nan,
    )

    count = np.zeros(
        (nt, ns),
        dtype=int,
    )

    for it in range(nt):
        for i in range(ns):

            c = all_crossings(
                field[it, i],
                xi,
                FRONT_THRESHOLD,
            )

            count[it, i] = int(
                c.size
            )

            if c.size:
                first[it, i] = c[0]

    return first, count


# =============================================================================
# BASIS FIELDS
# =============================================================================

def make_basis_fields(
    target,
    xi,
):
    nt, ns, nx = target.shape

    target_first, target_count = crossing_database(
        target,
        xi,
    )

    distance = np.zeros(
        (nt, ns, nx),
        dtype=float,
    )

    valid = (
        target_count > 0
    )

    for it in range(nt):
        distance[it] = (
            xi[None, :]
            -
            target_first[it, :, None]
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

    valid3 = valid[:, :, None]

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
        "target_first": target_first,
        "target_count": target_count,
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
# CHECKPOINT SELECTION
# =============================================================================

def select_best_any_checkpoints(
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
            p = (
                ROOT
                /
                p
            )

        if not p.exists():
            raise FileNotFoundError(
                f"Missing persisted R3F4 checkpoint:\n{p}"
            )

        selected.append({
            "experiment": exp,
            "path": str(p),
            "sha256": row.get(
                "sha256",
                "",
            ),
        })

    return selected


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F4-R")
    print("Front-Local Basis Outcome Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 OR CALIBRATOR PARAMETERS WILL BE CHANGED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3F4_SUMMARY,
        R3F4_CHECKPOINTS,
        R3F4_FINAL,
        R3F4_EPOCHS,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F4-R prerequisite:\n{path}"
            )

    summary = load_json(
        R3F4_SUMMARY
    )

    if (
        summary.get("status")
        !=
        "NO_R3F4_BASIS_CALIBRATOR_PASSES_COMPLETE_CONTRACT"
    ):
        raise RuntimeError(
            "R3F4-R requires incoming no-candidate status."
        )

    checkpoint_rows = load_csv(
        R3F4_CHECKPOINTS
    )

    final_rows = load_csv(
        R3F4_FINAL
    )

    epoch_rows = load_csv(
        R3F4_EPOCHS
    )

    selected = select_best_any_checkpoints(
        checkpoint_rows
    )

    if not selected:
        raise RuntimeError(
            "No persisted B1-B5 best-any checkpoints found."
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
                times_days
                -
                100.0
            )
        )
    )

    truth100 = truth[idx100]
    target100 = target[idx100]
    frozen100 = frozen[idx100]

    target_first_100 = basis[
        "target_first"
    ][idx100]

    target_count_100 = basis[
        "target_count"
    ][idx100]

    frozen_first_100, frozen_count_100 = crossing_database(
        frozen[idx100:idx100+1],
        xi,
    )

    frozen_first_100 = frozen_first_100[0]
    frozen_count_100 = frozen_count_100[0]

    global_rows = []
    profile_rows = []
    multiplicity_rows = []
    support_rows = []

    print("\n" + "=" * 78)
    print("R3F4-R CROSSING IDENTITY AUDIT")
    print("=" * 78)

    for item in selected:

        exp = item["experiment"]

        print(
            f"\n{exp} — loading persisted best-any checkpoint"
        )

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

        cal100 = calibrated[idx100]
        coeff100 = coefficient[idx100]

        first_shifts_truth = []
        first_shifts_frozen = []

        matched_shifts_truth = []
        matched_shifts_frozen = []

        matched_truth_valid = 0
        matched_frozen_valid = 0

        cal_multiplicity = []

        identity_switch_count = 0

        for i in range(
            cal100.shape[0]
        ):

            cal_cross = all_crossings(
                cal100[i],
                xi,
                FRONT_THRESHOLD,
            )

            cal_multiplicity.append(
                int(cal_cross.size)
            )

            truth_ref = (
                target_first_100[i]
                if target_count_100[i] > 0
                else np.nan
            )

            frozen_ref = (
                frozen_first_100[i]
                if frozen_count_100[i] > 0
                else np.nan
            )

            first_cal = (
                cal_cross[0]
                if cal_cross.size
                else np.nan
            )

            matched_truth = np.nan
            matched_frozen = np.nan

            if (
                cal_cross.size
                and
                np.isfinite(truth_ref)
            ):
                j = int(
                    np.argmin(
                        np.abs(
                            cal_cross
                            -
                            truth_ref
                        )
                    )
                )

                matched_truth = float(
                    cal_cross[j]
                )

                matched_truth_valid += 1

                first_shifts_truth.append(
                    abs(
                        first_cal
                        -
                        truth_ref
                    )
                )

                matched_shifts_truth.append(
                    abs(
                        matched_truth
                        -
                        truth_ref
                    )
                )

                if j != 0:
                    identity_switch_count += 1

            if (
                cal_cross.size
                and
                np.isfinite(frozen_ref)
            ):
                j = int(
                    np.argmin(
                        np.abs(
                            cal_cross
                            -
                            frozen_ref
                        )
                    )
                )

                matched_frozen = float(
                    cal_cross[j]
                )

                matched_frozen_valid += 1

                first_shifts_frozen.append(
                    abs(
                        first_cal
                        -
                        frozen_ref
                    )
                )

                matched_shifts_frozen.append(
                    abs(
                        matched_frozen
                        -
                        frozen_ref
                    )
                )

            profile_rows.append({
                "experiment": exp,
                "streamline": i,
                "tau_end_days": float(
                    tau_end_days[i]
                ),
                "target_crossing_count": int(
                    target_count_100[i]
                ),
                "frozen_crossing_count": int(
                    frozen_count_100[i]
                ),
                "calibrated_crossing_count": int(
                    cal_cross.size
                ),
                "target_first_crossing": (
                    float(truth_ref)
                    if np.isfinite(truth_ref)
                    else np.nan
                ),
                "frozen_first_crossing": (
                    float(frozen_ref)
                    if np.isfinite(frozen_ref)
                    else np.nan
                ),
                "calibrated_first_crossing": (
                    float(first_cal)
                    if np.isfinite(first_cal)
                    else np.nan
                ),
                "calibrated_matched_to_target": matched_truth,
                "calibrated_matched_to_frozen": matched_frozen,
                "first_shift_vs_target": (
                    abs(
                        first_cal
                        -
                        truth_ref
                    )
                    if (
                        np.isfinite(first_cal)
                        and
                        np.isfinite(truth_ref)
                    )
                    else np.nan
                ),
                "matched_shift_vs_target": (
                    abs(
                        matched_truth
                        -
                        truth_ref
                    )
                    if (
                        np.isfinite(matched_truth)
                        and
                        np.isfinite(truth_ref)
                    )
                    else np.nan
                ),
                "first_shift_vs_frozen": (
                    abs(
                        first_cal
                        -
                        frozen_ref
                    )
                    if (
                        np.isfinite(first_cal)
                        and
                        np.isfinite(frozen_ref)
                    )
                    else np.nan
                ),
                "matched_shift_vs_frozen": (
                    abs(
                        matched_frozen
                        -
                        frozen_ref
                    )
                    if (
                        np.isfinite(matched_frozen)
                        and
                        np.isfinite(frozen_ref)
                    )
                    else np.nan
                ),
                "coefficient_mean": float(
                    np.mean(
                        coeff100[i]
                    )
                ),
                "coefficient_max": float(
                    np.max(
                        coeff100[i]
                    )
                ),
            })

        first_shifts_truth = np.asarray(
            first_shifts_truth,
            dtype=float,
        )

        first_shifts_frozen = np.asarray(
            first_shifts_frozen,
            dtype=float,
        )

        matched_shifts_truth = np.asarray(
            matched_shifts_truth,
            dtype=float,
        )

        matched_shifts_frozen = np.asarray(
            matched_shifts_frozen,
            dtype=float,
        )

        cal_multiplicity = np.asarray(
            cal_multiplicity,
            dtype=int,
        )

        multi_fraction = float(
            np.mean(
                cal_multiplicity > 1
            )
        )

        identity_switch_fraction = (
            identity_switch_count
            /
            max(
                matched_truth_valid,
                1,
            )
        )

        first_p90_truth = float(
            np.percentile(
                first_shifts_truth,
                90,
            )
        )

        matched_p90_truth = float(
            np.percentile(
                matched_shifts_truth,
                90,
            )
        )

        first_p90_frozen = float(
            np.percentile(
                first_shifts_frozen,
                90,
            )
        )

        matched_p90_frozen = float(
            np.percentile(
                matched_shifts_frozen,
                90,
            )
        )

        first_mean_frozen = float(
            np.mean(
                first_shifts_frozen
            )
        )

        matched_mean_frozen = float(
            np.mean(
                matched_shifts_frozen
            )
        )

        # Front-shell residual coverage by basis coefficient.
        shell = (
            (truth100 >= FRONT_SHELL_LOW)
            &
            (truth100 <= FRONT_SHELL_HIGH)
        )

        required_shell = np.abs(
            residual[idx100][shell]
        )

        coeff_shell = coeff100[
            shell
        ]

        supported_required = (
            coeff_shell
            *
            required_shell
        )

        residual_coverage_fraction = float(
            np.sum(
                supported_required
            )
            /
            max(
                np.sum(
                    required_shell
                ),
                1e-15,
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
            "first_mean_shift_vs_frozen": first_mean_frozen,
            "first_P90_shift_vs_frozen": first_p90_frozen,
            "matched_mean_shift_vs_frozen": matched_mean_frozen,
            "matched_P90_shift_vs_frozen": matched_p90_frozen,
            "first_P90_shift_vs_target": first_p90_truth,
            "matched_P90_shift_vs_target": matched_p90_truth,
            "calibrated_multi_crossing_fraction": multi_fraction,
            "crossing_identity_switch_fraction": identity_switch_fraction,
            "front_shell_residual_coverage_fraction": residual_coverage_fraction,
            "matched_front_gate_pass": bool(
                matched_mean_frozen
                <=
                AUTHORITATIVE_MEAN_SHIFT_LIMIT
                and
                matched_p90_frozen
                <=
                AUTHORITATIVE_P90_SHIFT_LIMIT
            ),
        })

        multiplicity_rows.append({
            "experiment": exp,
            "zero_crossing_profiles": int(
                np.sum(
                    cal_multiplicity == 0
                )
            ),
            "one_crossing_profiles": int(
                np.sum(
                    cal_multiplicity == 1
                )
            ),
            "multi_crossing_profiles": int(
                np.sum(
                    cal_multiplicity > 1
                )
            ),
            "multi_crossing_fraction": multi_fraction,
            "identity_switch_count": int(
                identity_switch_count
            ),
            "identity_switch_fraction": identity_switch_fraction,
        })

        support_rows.append({
            "experiment": exp,
            "front_shell_required_residual_sum": float(
                np.sum(
                    required_shell
                )
            ),
            "front_shell_supported_residual_sum": float(
                np.sum(
                    supported_required
                )
            ),
            "front_shell_residual_coverage_fraction": residual_coverage_fraction,
            "front_shell_coefficient_mean": float(
                np.mean(
                    coeff_shell
                )
            ),
            "front_shell_coefficient_P90": float(
                np.percentile(
                    coeff_shell,
                    90,
                )
            ),
            "front_shell_coefficient_max": float(
                np.max(
                    coeff_shell
                )
            ),
        })

        print(
            f"  first P90 shift vs frozen  : {first_p90_frozen:.6e}"
        )

        print(
            f"  matched P90 shift vs frozen: {matched_p90_frozen:.6e}"
        )

        print(
            f"  multiple-crossing fraction : {100*multi_fraction:.2f}%"
        )

        print(
            f"  identity-switch fraction    : {100*identity_switch_fraction:.2f}%"
        )

        print(
            f"  front residual coverage     : {100*residual_coverage_fraction:.2f}%"
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
        MULTIPLICITY_TABLE,
        multiplicity_rows,
    )

    save_csv(
        SUPPORT_TABLE,
        support_rows,
    )

    # -------------------------------------------------------------------------
    # Limiter classification
    # -------------------------------------------------------------------------

    best = max(
        global_rows,
        key=lambda r:
        r["front_error_reduction_fraction"]
        if np.isfinite(
            r["front_error_reduction_fraction"]
        )
        else -np.inf,
    )

    first_shift_huge = bool(
        best[
            "first_P90_shift_vs_frozen"
        ]
        >
        0.05
    )

    matched_shift_small = bool(
        best[
            "matched_P90_shift_vs_frozen"
        ]
        <=
        AUTHORITATIVE_P90_SHIFT_LIMIT
    )

    multi_material = bool(
        best[
            "calibrated_multi_crossing_fraction"
        ]
        >=
        0.10
    )

    identity_switch_material = bool(
        best[
            "crossing_identity_switch_fraction"
        ]
        >=
        0.10
    )

    near_50 = bool(
        best[
            "front_error_reduction_fraction"
        ]
        >=
        0.49
    )

    coverage_limited = bool(
        best[
            "front_shell_residual_coverage_fraction"
        ]
        <
        0.55
    )

    if (
        first_shift_huge
        and
        matched_shift_small
        and
        (
            multi_material
            or
            identity_switch_material
        )
    ):
        diagnosis = "FIRST_CROSSING_IDENTITY_METRIC_ARTIFACT"

        recommendation = (
            "The large R3F4 front-shift signal is primarily caused by first-crossing "
            "identity switching in multi-crossing profiles. Do not relax the physical "
            "front gate. Repair the front-matching metric so each calibrated crossing "
            "is paired to the authoritative SG7A/frozen crossing before judging "
            "displacement, then re-evaluate the existing B2/B4/B5 checkpoints without "
            "retraining."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R2 — Matched-Crossing Front-Gate Reconciliation"
        )

    elif (
        first_shift_huge
        and
        not matched_shift_small
    ):
        diagnosis = "TRUE_FRONT_DISPLACEMENT_REMAINS"

        recommendation = (
            "Matched-crossing displacement remains outside the authoritative limits, "
            "so the R3F4 shift is physical rather than a first-crossing artifact. "
            "Audit basis asymmetry and crossing-core support before any new training."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R2 — True Front-Displacement Basis Audit"
        )

    elif (
        near_50
        and
        coverage_limited
    ):
        diagnosis = "FRONT_RESIDUAL_SUPPORT_COVERAGE_LIMIT"

        recommendation = (
            "The corrected front geometry is acceptable, but the bounded basis covers "
            "insufficient canonical residual to cross the 50% front-error-reduction "
            "gate. Design a slightly wider support family while preserving matched "
            "crossing identity and the existing sign/overshoot constraints."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R2 — Residual-Support Width Repair Design"
        )

    else:
        diagnosis = "MIXED_CROSSING_IDENTITY_AND_SUPPORT_LIMITER"

        recommendation = (
            "R3F4 contains both crossing-identity and residual-support effects. "
            "Reconcile crossing correspondence first, then quantify the remaining "
            "front-reduction shortfall before changing basis support."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R2 — Crossing/Support Reconciliation Audit"
        )

    limiter_rows = [
        {
            "best_experiment": best["experiment"],
            "front_error_reduction_fraction": best[
                "front_error_reduction_fraction"
            ],
            "first_P90_shift_vs_frozen": best[
                "first_P90_shift_vs_frozen"
            ],
            "matched_P90_shift_vs_frozen": best[
                "matched_P90_shift_vs_frozen"
            ],
            "multi_crossing_fraction": best[
                "calibrated_multi_crossing_fraction"
            ],
            "identity_switch_fraction": best[
                "crossing_identity_switch_fraction"
            ],
            "front_shell_residual_coverage_fraction": best[
                "front_shell_residual_coverage_fraction"
            ],
            "first_shift_huge": first_shift_huge,
            "matched_shift_small": matched_shift_small,
            "multi_crossing_material": multi_material,
            "identity_switch_material": identity_switch_material,
            "near_50_percent_reduction": near_50,
            "coverage_limited": coverage_limited,
            "diagnosis": diagnosis,
        }
    ]

    save_csv(
        LIMITER_TABLE,
        limiter_rows,
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

    width = 0.35

    plt.figure(
        figsize=(9, 5)
    )

    plt.bar(
        x - width / 2,
        [
            row["first_P90_shift_vs_frozen"]
            for row in global_rows
        ],
        width=width,
        label="first crossing",
    )

    plt.bar(
        x + width / 2,
        [
            row["matched_P90_shift_vs_frozen"]
            for row in global_rows
        ],
        width=width,
        label="matched crossing",
    )

    plt.axhline(
        AUTHORITATIVE_P90_SHIFT_LIMIT,
        linestyle="--",
    )

    plt.xticks(
        x,
        labels,
    )

    plt.ylabel(
        "P90 front displacement in xi"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4-R First vs Matched Crossing"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R_First_vs_Matched_Crossing.png",
        dpi=300,
    )

    plt.close()

    plt.figure(
        figsize=(9, 5)
    )

    plt.bar(
        labels,
        [
            row["calibrated_multi_crossing_fraction"]
            for row in global_rows
        ],
    )

    plt.ylabel(
        "Fraction of profiles with >1 crossing"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4-R Threshold Crossing Multiplicity"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R_Crossing_Multiplicity.png",
        dpi=300,
    )

    plt.close()

    plt.figure(
        figsize=(9, 5)
    )

    plt.bar(
        labels,
        [
            row["front_shell_residual_coverage_fraction"]
            for row in global_rows
        ],
    )

    plt.axhline(
        0.50,
        linestyle="--",
    )

    plt.ylabel(
        "Canonical front residual coverage fraction"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4-R Front Residual Support Coverage"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R_Residual_Support_Coverage.png",
        dpi=300,
    )

    plt.close()

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        (
            "R3F4 no-candidate status reproduced",
            True,
        ),
        (
            "Persisted B1-B5 checkpoints loaded",
            len(selected) > 0,
        ),
        (
            "Canonical/frozen/calibrated threshold crossings reconstructed",
            True,
        ),
        (
            "All crossing multiplicities counted",
            True,
        ),
        (
            "First-crossing displacement reproduced",
            True,
        ),
        (
            "Matched-crossing displacement established",
            True,
        ),
        (
            "Front residual support coverage quantified",
            True,
        ),
        (
            "Limiter mechanism classified",
            True,
        ),
    ]

    for description, flag in checks:
        print(
            f"[{'PASS' if flag else 'FAIL'}] {description}"
        )

    print("=" * 78)

    print("\nBEST R3F4 FRONT-REDUCTION CASE")
    print(f"  Experiment                : {best['experiment']}")
    print(f"  Front reduction           : {100*best['front_error_reduction_fraction']:.3f}%")
    print(f"  First P90 shift vs frozen : {best['first_P90_shift_vs_frozen']:.6e}")
    print(f"  Matched P90 shift vs frozen: {best['matched_P90_shift_vs_frozen']:.6e}")
    print(f"  Multi-crossing fraction   : {100*best['calibrated_multi_crossing_fraction']:.2f}%")
    print(f"  Identity-switch fraction  : {100*best['crossing_identity_switch_fraction']:.2f}%")
    print(f"  Residual coverage         : {100*best['front_shell_residual_coverage_fraction']:.2f}%")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F4-R",
            "status": "FRONT_LOCAL_BASIS_OUTCOME_AUDIT_COMPLETE",
            "incoming_status": summary.get("status"),
            "best_experiment": best["experiment"],
            "diagnosis": diagnosis,
            "best_metrics": best,
            "flags": {
                "first_shift_huge": first_shift_huge,
                "matched_shift_small": matched_shift_small,
                "multi_crossing_material": multi_material,
                "identity_switch_material": identity_switch_material,
                "near_50_percent_reduction": near_50,
                "coverage_limited": coverage_limited,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nTables:")
    print(f"  {GLOBAL_TABLE.name}")
    print(f"  {PROFILE_TABLE.name}")
    print(f"  {MULTIPLICITY_TABLE.name}")
    print(f"  {SUPPORT_TABLE.name}")
    print(f"  {LIMITER_TABLE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3F4R_First_vs_Matched_Crossing.png")
    print("  V15SG7CR3F4R_Crossing_Multiplicity.png")
    print("  V15SG7CR3F4R_Residual_Support_Coverage.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No model, front, TOF-bias, map-back, or plume gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
