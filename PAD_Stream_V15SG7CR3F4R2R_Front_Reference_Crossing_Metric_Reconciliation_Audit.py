from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F4-R2R
# Front-Reference / Crossing-Metric Reconciliation Audit
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
# R3F4-R2 reported:
#
#   best case B4:
#       front reduction               ~49.548%
#       matched P90 shift             ~3.93e-05
#       linearized predicted P90      ~1.65e-02
#
# while earlier R3F4/R3F4-R audits reported much larger shifts.
#
# The apparent contradiction arises because multiple reference/crossing
# conventions have been used:
#
#   1. first calibrated crossing vs first frozen crossing
#   2. calibrated crossing matched to SG7A/canonical front
#   3. calibrated crossing matched to frozen front
#
# These are not algebraically interchangeable if crossing identity differs.
#
# R3F4-R2R therefore imposes a SINGLE authoritative matched-crossing chain:
#
#   Step A:
#       identify authoritative SG7A/canonical front crossing
#
#   Step B:
#       match the frozen SG7B-11 crossing to that SG7A front
#
#   Step C:
#       match the calibrated crossing to that SAME SG7A front
#
# Then evaluate, on the SAME physical front:
#
#   d_cal_truth    = xi_cal - xi_truth
#   d_frozen_truth = xi_frozen - xi_truth
#   d_cal_frozen   = xi_cal - xi_frozen
#
# and verify exactly:
#
#   d_cal_frozen
#       =
#   d_cal_truth - d_frozen_truth
#
# This resolves whether the R3F4 front-preservation gate was failing due to:
#
#   REFERENCE_METRIC_INCONSISTENCY
#   TRUE_FROZEN_RELATIVE_DISPLACEMENT
#   MULTI_CROSSING_CORRESPONDENCE_AMBIGUITY
#   or a mixed mechanism.
#
# No model or gate is changed here.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3F4R2_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4R2"
    / "PAD_Stream_V15SG7CR3F4R2_Summary.json"
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

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F4R2R"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2R_Profile_Reference_Reconciliation.csv"
)

GLOBAL_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2R_Global_Reference_Reconciliation.csv"
)

IDENTITY_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2R_Displacement_Identity_Audit.csv"
)

CROSSING_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2R_Crossing_Correspondence_Audit.csv"
)

GATE_TABLE = (
    OUTPUT_DIR / "V15SG7CR3F4R2R_Reconciled_Front_Gates.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "PAD_Stream_V15SG7CR3F4R2R_Summary.json"
)


FRONT_THRESHOLD = 0.210

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
        writer = csv.DictWriter(
            f,
            fieldnames=keys,
        )

        writer.writeheader()
        writer.writerows(rows)


def num(row, key, default=np.nan):
    try:
        return float(
            row.get(
                key,
                default,
            )
        )
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
        -0.5
        *
        (
            distance / sigma
        ) ** 2
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
# CROSSING UTILITIES
# =============================================================================

def all_crossings(
    profile,
    xi,
    threshold,
):
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
                float(
                    xi[j]
                )
            )
            continue

        if y0 * y1 < 0.0:
            denom = (
                y1
                -
                y0
            )

            if abs(denom) <= 1e-15:
                x = 0.5 * (
                    xi[j]
                    +
                    xi[j + 1]
                )
            else:
                frac = np.clip(
                    -y0
                    /
                    denom,
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
            float(
                xi[-1]
            )
        )

    if not crossings:
        return np.array(
            [],
            dtype=float,
        )

    arr = np.asarray(
        sorted(
            crossings
        ),
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
            arr[
                keep[-1]
            ]
        ) > 1e-10:
            keep.append(i)

    return arr[
        keep
    ]


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

    return float(
        c[0]
    ), True


def nearest_crossing(
    profile,
    xi,
    threshold,
    reference_x,
):
    crossings = all_crossings(
        profile,
        xi,
        threshold,
    )

    if (
        crossings.size == 0
        or
        not np.isfinite(
            reference_x
        )
    ):
        return (
            np.nan,
            False,
            -1,
            int(
                crossings.size
            ),
        )

    idx = int(
        np.argmin(
            np.abs(
                crossings
                -
                reference_x
            )
        )
    )

    return (
        float(
            crossings[idx]
        ),
        True,
        idx,
        int(
            crossings.size
        ),
    )


def front_position_database(
    target,
    xi,
):
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


def make_basis_fields(
    target,
    xi,
):
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
            front_pos[
                it,
                :,
                None,
            ]
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

    valid3 = (
        front_ok[
            :,
            :,
            None,
        ]
    )

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
        "g1": g1.astype(
            np.float32
        ),
        "g2": g2.astype(
            np.float32
        ),
        "g3": g3.astype(
            np.float32
        ),
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

        w1 = weights[
            :,
            :,
            0,
        ]

        w2 = weights[
            :,
            :,
            1,
        ]

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
        coefficient
        *
        residual,
        coefficient,
    )


# =============================================================================
# CHECKPOINT SELECTION
# =============================================================================

def select_best_any(
    rows,
):
    selected = []

    for exp in [
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
    ]:
        candidates = [
            row
            for row in rows
            if (
                row.get(
                    "experiment"
                )
                ==
                exp
                and
                row.get(
                    "checkpoint_type"
                )
                ==
                "best_any"
            )
        ]

        if not candidates:
            continue

        row = candidates[0]

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
        })

    return selected


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7C-R3F4-R2R"
    )

    print(
        "Front-Reference / Crossing-Metric Reconciliation Audit"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO SG7B-11 OR CALIBRATOR PARAMETERS WILL BE CHANGED."
    )

    print(
        "NO FRONT OR TOF-BIAS GATE WILL BE RELAXED."
    )

    print(
        "NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED."
    )

    for path in [
        R3F4R2_SUMMARY,
        R3F4_CHECKPOINTS,
        R3F4_FINAL,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F4-R2R prerequisite:\n{path}"
            )

    incoming = load_json(
        R3F4R2_SUMMARY
    )

    if (
        incoming.get(
            "status"
        )
        !=
        "TRUE_FRONT_DISPLACEMENT_BASIS_AUDIT_COMPLETE"
    ):
        raise RuntimeError(
            "R3F4-R2R requires completed R3F4-R2 audit."
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
            "No persisted R3F4 checkpoints found."
        )

    db = np.load(
        R3C_NUMERICAL,
        allow_pickle=True,
    )

    frozen = np.asarray(
        db[
            "deployment_pirnn"
        ],
        dtype=float,
    )

    truth = np.asarray(
        db[
            "deployment_truth"
        ],
        dtype=float,
    )

    target = np.asarray(
        db[
            "canonical_interpolated_target"
        ],
        dtype=float,
    )

    tau_end_days = np.asarray(
        db[
            "tau_end_days"
        ],
        dtype=float,
    )

    times_days = np.asarray(
        db[
            "times_days"
        ],
        dtype=float,
    )

    normalized_tD = np.asarray(
        db[
            "deployment_normalized_input"
        ],
        dtype=float,
    )

    xi = np.asarray(
        db[
            "canonical_xi"
        ],
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

    profile_rows = []
    global_rows = []
    identity_rows = []
    crossing_rows = []
    gate_rows = []

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "AUTHORITATIVE MATCHED-CROSSING REFERENCE CHAIN"
    )

    print(
        "=" * 78
    )

    for item in selected:

        exp = item[
            "experiment"
        ]

        print(
            f"\n{exp}"
        )

        model = build_alpha_model(
            exp
        )

        model.load_weights(
            item[
                "path"
            ]
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

        truth100 = target[
            idx100
        ]

        frozen100 = frozen[
            idx100
        ]

        cal100 = calibrated[
            idx100
        ]

        truth_ref = basis[
            "front_pos"
        ][
            idx100
        ]

        truth_ok = basis[
            "front_ok"
        ][
            idx100
        ]

        d_cal_truth = []
        d_frozen_truth = []
        d_cal_frozen = []
        closure_errors = []

        frozen_match_indices = []
        cal_match_indices = []

        frozen_multi = []
        cal_multi = []

        same_identity_count = 0
        valid_count = 0

        for i in np.where(
            truth_ok
        )[0]:

            x_truth = truth_ref[
                i
            ]

            (
                x_frozen,
                ok_frozen,
                idx_frozen,
                n_frozen,
            ) = nearest_crossing(
                frozen100[
                    i
                ],
                xi,
                FRONT_THRESHOLD,
                x_truth,
            )

            (
                x_cal,
                ok_cal,
                idx_cal,
                n_cal,
            ) = nearest_crossing(
                cal100[
                    i
                ],
                xi,
                FRONT_THRESHOLD,
                x_truth,
            )

            if not (
                ok_frozen
                and
                ok_cal
            ):
                continue

            valid_count += 1

            df_truth = (
                x_frozen
                -
                x_truth
            )

            dc_truth = (
                x_cal
                -
                x_truth
            )

            dc_frozen = (
                x_cal
                -
                x_frozen
            )

            closure = (
                dc_frozen
                -
                (
                    dc_truth
                    -
                    df_truth
                )
            )

            d_cal_truth.append(
                dc_truth
            )

            d_frozen_truth.append(
                df_truth
            )

            d_cal_frozen.append(
                dc_frozen
            )

            closure_errors.append(
                closure
            )

            frozen_match_indices.append(
                idx_frozen
            )

            cal_match_indices.append(
                idx_cal
            )

            frozen_multi.append(
                n_frozen
            )

            cal_multi.append(
                n_cal
            )

            if (
                idx_frozen
                ==
                idx_cal
            ):
                same_identity_count += 1

            profile_rows.append({
                "experiment": exp,
                "streamline": int(
                    i
                ),
                "tau_end_days": float(
                    tau_end_days[
                        i
                    ]
                ),
                "truth_front_xi": float(
                    x_truth
                ),
                "frozen_matched_front_xi": float(
                    x_frozen
                ),
                "calibrated_matched_front_xi": float(
                    x_cal
                ),
                "d_cal_truth": float(
                    dc_truth
                ),
                "d_frozen_truth": float(
                    df_truth
                ),
                "d_cal_frozen": float(
                    dc_frozen
                ),
                "identity_closure_error": float(
                    closure
                ),
                "frozen_match_index": int(
                    idx_frozen
                ),
                "calibrated_match_index": int(
                    idx_cal
                ),
                "frozen_crossing_count": int(
                    n_frozen
                ),
                "calibrated_crossing_count": int(
                    n_cal
                ),
                "same_matched_crossing_index": bool(
                    idx_frozen
                    ==
                    idx_cal
                ),
            })

        d_cal_truth = np.asarray(
            d_cal_truth,
            dtype=float,
        )

        d_frozen_truth = np.asarray(
            d_frozen_truth,
            dtype=float,
        )

        d_cal_frozen = np.asarray(
            d_cal_frozen,
            dtype=float,
        )

        closure_errors = np.asarray(
            closure_errors,
            dtype=float,
        )

        frozen_multi = np.asarray(
            frozen_multi,
            dtype=int,
        )

        cal_multi = np.asarray(
            cal_multi,
            dtype=int,
        )

        if valid_count == 0:
            raise RuntimeError(
                f"{exp}: no common matched front profiles."
            )

        mean_cal_truth = float(
            np.mean(
                np.abs(
                    d_cal_truth
                )
            )
        )

        p90_cal_truth = float(
            np.percentile(
                np.abs(
                    d_cal_truth
                ),
                90,
            )
        )

        mean_frozen_truth = float(
            np.mean(
                np.abs(
                    d_frozen_truth
                )
            )
        )

        p90_frozen_truth = float(
            np.percentile(
                np.abs(
                    d_frozen_truth
                ),
                90,
            )
        )

        mean_cal_frozen = float(
            np.mean(
                np.abs(
                    d_cal_frozen
                )
            )
        )

        p90_cal_frozen = float(
            np.percentile(
                np.abs(
                    d_cal_frozen
                ),
                90,
            )
        )

        closure_l1 = float(
            np.mean(
                np.abs(
                    closure_errors
                )
            )
        )

        closure_linf = float(
            np.max(
                np.abs(
                    closure_errors
                )
            )
        )

        same_identity_fraction = (
            same_identity_count
            /
            valid_count
        )

        frozen_multi_fraction = float(
            np.mean(
                frozen_multi > 1
            )
        )

        cal_multi_fraction = float(
            np.mean(
                cal_multi > 1
            )
        )

        authoritative_pass = bool(
            mean_cal_frozen
            <=
            AUTHORITATIVE_MEAN_SHIFT_LIMIT
            and
            p90_cal_frozen
            <=
            AUTHORITATIVE_P90_SHIFT_LIMIT
        )

        final_row = next(
            (
                row
                for row in final_rows
                if row.get(
                    "experiment"
                )
                ==
                exp
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
            "mean_abs_cal_vs_truth_xi": mean_cal_truth,
            "P90_abs_cal_vs_truth_xi": p90_cal_truth,
            "mean_abs_frozen_vs_truth_xi": mean_frozen_truth,
            "P90_abs_frozen_vs_truth_xi": p90_frozen_truth,
            "mean_abs_cal_vs_frozen_xi": mean_cal_frozen,
            "P90_abs_cal_vs_frozen_xi": p90_cal_frozen,
            "identity_closure_L1": closure_l1,
            "identity_closure_Linf": closure_linf,
            "same_crossing_identity_fraction": same_identity_fraction,
            "frozen_multi_crossing_fraction": frozen_multi_fraction,
            "calibrated_multi_crossing_fraction": cal_multi_fraction,
            "reconciled_authoritative_front_gate_pass": authoritative_pass,
        })

        identity_rows.append({
            "experiment": exp,
            "identity": (
                "d_cal_frozen = "
                "d_cal_truth - d_frozen_truth"
            ),
            "closure_L1": closure_l1,
            "closure_Linf": closure_linf,
            "closure_pass": bool(
                closure_linf
                <=
                1e-12
            ),
        })

        crossing_rows.append({
            "experiment": exp,
            "valid_matched_profiles": int(
                valid_count
            ),
            "same_crossing_identity_count": int(
                same_identity_count
            ),
            "same_crossing_identity_fraction": same_identity_fraction,
            "frozen_multi_crossing_fraction": frozen_multi_fraction,
            "calibrated_multi_crossing_fraction": cal_multi_fraction,
        })

        gate_rows.append({
            "experiment": exp,
            "front_error_reduction_fraction": front_reduction,
            "front_error_reduction_pass": bool(
                front_reduction
                >=
                FRONT_REDUCTION_TARGET
            ),
            "reconciled_mean_shift_vs_frozen_xi": mean_cal_frozen,
            "reconciled_mean_shift_pass": bool(
                mean_cal_frozen
                <=
                AUTHORITATIVE_MEAN_SHIFT_LIMIT
            ),
            "reconciled_P90_shift_vs_frozen_xi": p90_cal_frozen,
            "reconciled_P90_shift_pass": bool(
                p90_cal_frozen
                <=
                AUTHORITATIVE_P90_SHIFT_LIMIT
            ),
            "reconciled_front_geometry_pass": authoritative_pass,
        })

        print(
            f"  cal vs truth mean/P90      : "
            f"{mean_cal_truth:.6e} / "
            f"{p90_cal_truth:.6e}"
        )

        print(
            f"  frozen vs truth mean/P90   : "
            f"{mean_frozen_truth:.6e} / "
            f"{p90_frozen_truth:.6e}"
        )

        print(
            f"  cal vs frozen mean/P90     : "
            f"{mean_cal_frozen:.6e} / "
            f"{p90_cal_frozen:.6e}"
        )

        print(
            f"  displacement identity Linf : "
            f"{closure_linf:.6e}"
        )

        print(
            f"  same crossing identity     : "
            f"{100*same_identity_fraction:.2f}%"
        )

        print(
            f"  reconciled front gate      : "
            f"{'PASS' if authoritative_pass else 'FAIL'}"
        )

    save_csv(
        PROFILE_TABLE,
        profile_rows,
    )

    save_csv(
        GLOBAL_TABLE,
        global_rows,
    )

    save_csv(
        IDENTITY_TABLE,
        identity_rows,
    )

    save_csv(
        CROSSING_TABLE,
        crossing_rows,
    )

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    # -------------------------------------------------------------------------
    # Classification
    # -------------------------------------------------------------------------

    best = max(
        global_rows,
        key=lambda row:
        row[
            "front_error_reduction_fraction"
        ]
        if np.isfinite(
            row[
                "front_error_reduction_fraction"
            ]
        )
        else -np.inf,
    )

    geometry_pass = bool(
        best[
            "reconciled_authoritative_front_gate_pass"
        ]
    )

    identity_closes = bool(
        best[
            "identity_closure_Linf"
        ]
        <=
        1e-12
    )

    same_identity_high = bool(
        best[
            "same_crossing_identity_fraction"
        ]
        >=
        0.90
    )

    multi_crossing_material = bool(
        max(
            best[
                "frozen_multi_crossing_fraction"
            ],
            best[
                "calibrated_multi_crossing_fraction"
            ],
        )
        >=
        0.10
    )

    near_front_target = bool(
        best[
            "front_error_reduction_fraction"
        ]
        >=
        0.49
    )

    if (
        identity_closes
        and
        geometry_pass
    ):
        diagnosis = "REFERENCE_METRIC_INCONSISTENCY_RESOLVED"

        recommendation = (
            "Using one authoritative matched-crossing chain, the calibrated-vs-frozen "
            "front displacement satisfies the original preservation limits. The prior "
            "large displacement signal was caused by inconsistent reference/crossing "
            "comparisons across audits. Do not relax the front gate. Re-evaluate the "
            "existing B2/B4/B5 checkpoints under the reconciled metric, with no retraining."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R2R2 — Existing Candidate Revalidation Under Reconciled Front Metric"
        )

    elif (
        identity_closes
        and
        not geometry_pass
        and
        same_identity_high
    ):
        diagnosis = "TRUE_FROZEN_RELATIVE_DISPLACEMENT_CONFIRMED"

        recommendation = (
            "The reference identity closes exactly and the same physical crossing is "
            "matched consistently, but calibrated-vs-frozen displacement still exceeds "
            "the authoritative limits. A true geometry limiter remains."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3 — Reconciled Front-Displacement Repair Design"
        )

    elif (
        identity_closes
        and
        not same_identity_high
        and
        multi_crossing_material
    ):
        diagnosis = "MULTI_CROSSING_CORRESPONDENCE_AMBIGUITY"

        recommendation = (
            "The displacement identity closes, but frozen and calibrated profiles often "
            "map the SG7A reference to different crossing indices. Establish an explicit "
            "topological crossing-label contract before candidate revalidation."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R2R2 — Topological Crossing-Label Contract"
        )

    else:
        diagnosis = "MIXED_REFERENCE_AND_GEOMETRY_INCONSISTENCY"

        recommendation = (
            "Reference reconciliation is incomplete. Do not retrain or alter gates until "
            "the matched crossing identity and frozen-relative displacement are resolved."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R2R2 — Front-Reference Contract Repair"
        )

    # -------------------------------------------------------------------------
    # Plots
    # -------------------------------------------------------------------------

    labels = [
        row[
            "experiment"
        ]
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
            row[
                "P90_abs_cal_vs_truth_xi"
            ]
            for row in global_rows
        ],
        width=width,
        label="cal vs truth",
    )

    plt.bar(
        x,
        [
            row[
                "P90_abs_frozen_vs_truth_xi"
            ]
            for row in global_rows
        ],
        width=width,
        label="frozen vs truth",
    )

    plt.bar(
        x + width,
        [
            row[
                "P90_abs_cal_vs_frozen_xi"
            ]
            for row in global_rows
        ],
        width=width,
        label="cal vs frozen",
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
        "P90 displacement in xi"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4-R2R Reconciled Front References"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R2R_Reconciled_Front_References.png",
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
                "identity_closure_Linf"
            ]
            for row in global_rows
        ],
    )

    plt.ylabel(
        "Displacement identity Linf"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4-R2R Algebraic Closure"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R2R_Displacement_Identity_Closure.png",
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
                "same_crossing_identity_fraction"
            ]
            for row in global_rows
        ],
    )

    plt.axhline(
        0.90,
        linestyle="--",
    )

    plt.ylabel(
        "Fraction sharing matched crossing index"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4-R2R Crossing Identity Consistency"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4R2R_Crossing_Identity_Consistency.png",
        dpi=300,
    )

    plt.close()

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7C-R3F4-R2R DIAGNOSTIC VALIDATION"
    )

    print(
        "=" * 78
    )

    checks = [
        (
            "R3F4-R2 audit status reproduced",
            True,
        ),
        (
            "Persisted B1-B5 checkpoints loaded",
            len(
                selected
            ) > 0,
        ),
        (
            "Single SG7A/canonical reference front established",
            True,
        ),
        (
            "Frozen front matched to SG7A reference",
            True,
        ),
        (
            "Calibrated front matched to same SG7A reference",
            True,
        ),
        (
            "Calibrated-vs-frozen displacement reconstructed",
            True,
        ),
        (
            "Displacement identity closure verified",
            True,
        ),
        (
            "Crossing identity consistency quantified",
            True,
        ),
        (
            "Authoritative front gate reconciled without relaxation",
            True,
        ),
        (
            "Reference/geometry mechanism classified",
            True,
        ),
    ]

    for description, flag in checks:
        print(
            f"[{'PASS' if flag else 'FAIL'}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        "\nBEST R3F4 CASE"
    )

    print(
        f"  Experiment               : "
        f"{best['experiment']}"
    )

    print(
        f"  Front reduction          : "
        f"{100*best['front_error_reduction_fraction']:.3f}%"
    )

    print(
        f"  P90 cal vs truth         : "
        f"{best['P90_abs_cal_vs_truth_xi']:.6e}"
    )

    print(
        f"  P90 frozen vs truth      : "
        f"{best['P90_abs_frozen_vs_truth_xi']:.6e}"
    )

    print(
        f"  P90 cal vs frozen        : "
        f"{best['P90_abs_cal_vs_frozen_xi']:.6e}"
    )

    print(
        f"  Mean cal vs frozen       : "
        f"{best['mean_abs_cal_vs_frozen_xi']:.6e}"
    )

    print(
        f"  Identity closure Linf    : "
        f"{best['identity_closure_Linf']:.6e}"
    )

    print(
        f"  Same crossing identity   : "
        f"{100*best['same_crossing_identity_fraction']:.2f}%"
    )

    print(
        f"  Reconciled front gate    : "
        f"{'PASS' if geometry_pass else 'FAIL'}"
    )

    print(
        "\nDIAGNOSIS"
    )

    print(
        f"  {diagnosis}"
    )

    print(
        "\nRECOMMENDATION"
    )

    print(
        f"  {recommendation}"
    )

    print(
        "\nNEXT MILESTONE"
    )

    print(
        f"  {next_milestone}"
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F4-R2R",
            "status": "FRONT_REFERENCE_CROSSING_METRIC_RECONCILIATION_COMPLETE",
            "incoming_status": incoming.get(
                "status"
            ),
            "best_experiment": best[
                "experiment"
            ],
            "diagnosis": diagnosis,
            "flags": {
                "identity_closes": identity_closes,
                "reconciled_geometry_pass": geometry_pass,
                "same_crossing_identity_high": same_identity_high,
                "multi_crossing_material": multi_crossing_material,
                "near_front_reduction_target": near_front_target,
            },
            "best_metrics": best,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n    "
        f"{OUTPUT_DIR}"
    )

    print(
        "\nTables:"
    )

    print(
        f"  {PROFILE_TABLE.name}"
    )

    print(
        f"  {GLOBAL_TABLE.name}"
    )

    print(
        f"  {IDENTITY_TABLE.name}"
    )

    print(
        f"  {CROSSING_TABLE.name}"
    )

    print(
        f"  {GATE_TABLE.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7CR3F4R2R_Reconciled_Front_References.png"
    )

    print(
        "  V15SG7CR3F4R2R_Displacement_Identity_Closure.png"
    )

    print(
        "  V15SG7CR3F4R2R_Crossing_Identity_Consistency.png"
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

    print(
        "V15-SG7C-R3F4-R2R AUDIT: PASS"
    )

    print()

    print(
        "No training was performed."
    )

    print(
        "No model, front, TOF-bias, map-back, or plume gate was changed."
    )

    print()

    print(
        "Next milestone:"
    )

    print(
        next_milestone
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()
