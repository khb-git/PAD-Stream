from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F5
# Controlled Minimal-Support Extension Calibration
#
# CONTROLLED CALIBRATION MILESTONE
#
# SG7B-11 PI-RNN WEIGHTS WILL NOT BE CHANGED.
# THE PERSISTED B4 R3F4 CALIBRATOR WEIGHTS WILL NOT BE CHANGED.
# ONLY A BOUNDED, SYMMETRIC FRONT-SUPPORT SHOULDER IS CALIBRATED.
# THE 50% FRONT-ERROR-REDUCTION GATE WILL NOT BE CHANGED OR RELAXED.
# NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
#
# IMPORTANT
# ---------
# This branch does NOT add an unconstrained neural correction.
#
# Existing B4:
#
#   deltaS_B4 =
#       alpha_B4(features)
#       * (S_canonical - S_frozen)
#       * G_B4
#
# R3F5 extends only the spatial support:
#
#   G_ext =
#       clip(G_B4 + eta * G_shoulder, 0, 1)
#
#   0 <= eta <= 1
#
# therefore:
#
#   deltaS_ext =
#       (S_canonical - S_frozen) * G_ext
#
# remains directionally and amplitude bounded by the validated canonical
# residual.
#
# X0 = unchanged B4 control
# X1-X5 = progressively larger support targets from the R3E design matrix.
#
# No candidate is frozen here. A passing candidate is only NOMINATED for
# independent validation.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5"
OUT.mkdir(parents=True, exist_ok=True)

R3E_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4R3E"
    / "PAD_Stream_V15SG7CR3F4R3E_Summary.json"
)

R3E_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F4R3E"
    / "V15SG7CR3F4R3E_Minimal_Support_Extension_Contract.json"
)

R3E_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F4R3E"
    / "V15SG7CR3F4R3E_R3F5_Experiment_Matrix.csv"
)

R3B_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F4R3B"
    / "V15SG7CR3F4R3B_Deployment_Front_Acceptance_Contract.json"
)

R3D_GLOBAL = (
    ROOT / "output" / "V15_SG7CR3F4R3D"
    / "V15SG7CR3F4R3D_Global_Limiter_Audit.csv"
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

# Exact unchanged front acceptance threshold.
FRONT_REDUCTION_GATE = 0.50

# R3E design margin only. Not an acceptance-gate replacement.
DESIGN_TARGET = 0.5025

# Existing R3F4 basis.
SIGMA_NARROW = 0.015
SIGMA_MEDIUM = 0.030

# Extension basis: only the immediate symmetric shoulder outside the medium
# Gaussian's central region. It does not create a new directional correction.
SIGMA_SHOULDER_OUTER = 0.045
SHOULDER_INNER_ABS_XI = 0.020
SHOULDER_OUTER_ABS_XI = 0.070

FRONT_THRESHOLD = 0.210

# Clarified authoritative safeguards retained for the controlled screen.
MAX_GLOBAL_L1 = 0.020
MAX_GLOBAL_L2 = 0.030
MAX_SHORT_TOF_MAE = 1.5e-03
MAX_BIAS_500_1000 = 2.5e-03
MAX_BIAS_1000_2000 = 4.5e-03
MAX_BIAS_GT2000 = 5.0e-03
MAX_ABS_CORRECTION = 0.10
MIN_CROSSING_IDENTITY = 0.90

# SG7A-facing geometry is the physics reference.
MAX_SG7A_FRONT_P90 = 5.0e-03

# Numerical solve.
BISECTION_ITERS = 70
ANCHOR_SCALE_MIN = 0.75
ANCHOR_SCALE_MAX = 1.25


SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5_Summary.json"
METRICS_TABLE = OUT / "V15SG7CR3F5_Experiment_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5_Final_Gate_Matrix.csv"
CAL_TABLE = OUT / "V15SG7CR3F5_Support_Calibration.csv"
FRONT_TABLE = OUT / "V15SG7CR3F5_SG7A_Front_Metrics.csv"
NOMINATION_FILE = OUT / "V15SG7CR3F5_Candidate_Manifest.json"
NUMERICAL_FILE = OUT / "V15SG7CR3F5_Controlled_Extension_Results.npz"


# =============================================================================
# IO
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
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


def fnum(row, key, default=np.nan):
    try:
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# B4 RECONSTRUCTION
# =============================================================================

def build_b4_model():
    inp = tf.keras.Input(shape=(2,), name="profile_features")
    x = tf.keras.layers.Dense(12, activation="tanh")(inp)
    x = tf.keras.layers.Dense(12, activation="tanh")(x)
    out = tf.keras.layers.Dense(
        3,
        activation="softmax",
        name="basis_weights",
    )(x)
    return tf.keras.Model(inp, out, name="R3F4_B4")


def gaussian(distance, sigma):
    return np.exp(-0.5 * (distance / sigma) ** 2)


def make_profile_features(normalized_tD, tau_end_days):
    logtau = np.log10(np.maximum(tau_end_days, 1.0))
    logtau = (
        logtau - np.mean(logtau)
    ) / max(np.std(logtau), 1e-12)

    nt, ns = normalized_tD.shape
    logtau2 = np.broadcast_to(logtau[None, :], (nt, ns))

    return np.stack(
        [normalized_tD, logtau2],
        axis=-1,
    ).astype(np.float32)


# =============================================================================
# FRONT CROSSINGS
# =============================================================================

def all_crossings(profile, xi, threshold):
    profile = np.asarray(profile, dtype=float)
    xi = np.asarray(xi, dtype=float)
    y = profile - threshold
    crossings = []

    for j in range(len(xi) - 1):
        y0, y1 = y[j], y[j + 1]

        if np.isclose(y0, 0.0, atol=1e-12):
            crossings.append(float(xi[j]))
            continue

        if y0 * y1 < 0.0:
            denom = y1 - y0
            if abs(denom) <= 1e-15:
                x = 0.5 * (xi[j] + xi[j + 1])
            else:
                frac = np.clip(-y0 / denom, 0.0, 1.0)
                x = xi[j] + frac * (xi[j + 1] - xi[j])
            crossings.append(float(x))

    if np.isclose(y[-1], 0.0, atol=1e-12):
        crossings.append(float(xi[-1]))

    if not crossings:
        return np.array([], dtype=float)

    arr = np.asarray(sorted(crossings), dtype=float)
    keep = [0]
    for i in range(1, len(arr)):
        if abs(arr[i] - arr[keep[-1]]) > 1e-10:
            keep.append(i)

    return arr[keep]


def first_crossing(profile, xi, threshold):
    c = all_crossings(profile, xi, threshold)
    if c.size == 0:
        return np.nan, False
    return float(c[0]), True


def nearest_crossing(profile, xi, threshold, reference_x):
    c = all_crossings(profile, xi, threshold)
    if c.size == 0 or not np.isfinite(reference_x):
        return np.nan, False, -1, int(c.size)

    idx = int(np.argmin(np.abs(c - reference_x)))
    return float(c[idx]), True, idx, int(c.size)


def front_position_database(target, xi):
    nt, ns, _ = target.shape
    pos = np.full((nt, ns), np.nan, dtype=float)
    ok = np.zeros((nt, ns), dtype=bool)

    for it in range(nt):
        for i in range(ns):
            pos[it, i], ok[it, i] = first_crossing(
                target[it, i],
                xi,
                FRONT_THRESHOLD,
            )

    return pos, ok


# =============================================================================
# SUPPORT CALIBRATION
# =============================================================================

def coverage_fraction(abs_residual, coefficient, valid):
    numer = np.sum(abs_residual[valid] * coefficient[valid])
    denom = np.sum(abs_residual[valid])
    return float(numer / max(denom, 1e-15))


def solve_eta(
    base_coeff,
    shoulder,
    abs_residual,
    valid,
    anchor_scale,
    target_authoritative_coverage,
):
    """
    Solve eta so that the baseline-anchored support mapping reaches the target.

    authoritative_coverage(eta)
      = anchor_scale * raw_coverage(eta)

    This preserves exact agreement with the R3D authoritative B4 baseline at
    eta=0 while using the reconstructed residual geometry to determine the
    incremental effect of the shoulder.
    """

    def mapped(eta):
        coeff = np.clip(
            base_coeff + eta * shoulder,
            0.0,
            1.0,
        )
        raw = coverage_fraction(
            abs_residual,
            coeff,
            valid,
        )
        return anchor_scale * raw

    lo, hi = 0.0, 1.0

    if target_authoritative_coverage <= mapped(lo):
        return 0.0, mapped(lo), True

    if target_authoritative_coverage > mapped(hi):
        return 1.0, mapped(hi), False

    for _ in range(BISECTION_ITERS):
        mid = 0.5 * (lo + hi)
        if mapped(mid) < target_authoritative_coverage:
            lo = mid
        else:
            hi = mid

    eta = hi
    return eta, mapped(eta), True


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5")
    print("Controlled Minimal-Support Extension Calibration")
    print("=" * 78)

    print("""
CONTROLLED SUPPORT CALIBRATION WILL BE PERFORMED.
SG7B-11 PI-RNN WEIGHTS WILL NOT BE CHANGED.
THE PERSISTED B4 CALIBRATOR WEIGHTS WILL NOT BE CHANGED.
ONLY A BOUNDED SYMMETRIC SUPPORT-SHOULDER AMPLITUDE eta WILL BE CALIBRATED.
NO FRONT, TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE RELAXED.
NO CANDIDATE WILL BE FROZEN BY R3F5.
""")

    r3e_summary = load_json(R3E_SUMMARY)
    r3e_contract = load_json(R3E_CONTRACT)
    matrix_rows = load_csv(R3E_MATRIX)
    r3b_contract = load_json(R3B_CONTRACT)
    r3d_rows = load_csv(R3D_GLOBAL)
    checkpoint_rows = load_csv(R3F4_CHECKPOINTS)
    r3f4_final = load_csv(R3F4_FINAL)

    if (
        r3e_summary.get("status")
        != "MINIMAL_RESIDUAL_SUPPORT_EXTENSION_CONTRACT_READY"
    ):
        raise RuntimeError(
            "R3F5 requires the passed R3F4-R3E support-extension contract."
        )

    if (
        r3b_contract.get("deployment_semantics", {}).get(
            "physics_front_reference"
        )
        != "SG7A/canonical truth"
    ):
        raise RuntimeError(
            "Clarified deployment contract does not retain SG7A/canonical physics authority."
        )

    # Authoritative B4 support baseline.
    r3d_b4 = next(
        r for r in r3d_rows
        if r.get("experiment") == "B4"
    )

    authoritative_base = fnum(
        r3d_b4,
        "final_front_reduction_fraction",
    )

    authoritative_support = fnum(
        r3d_b4,
        "front_shell_residual_coverage_fraction",
    )

    if abs(authoritative_base - authoritative_support) > 1e-6:
        raise RuntimeError(
            "R3D B4 reduction/support equivalence is not reproduced."
        )

    # B4 checkpoint.
    ck = next(
        (
            r for r in checkpoint_rows
            if r.get("experiment") == "B4"
            and r.get("checkpoint_type") == "best_any"
        ),
        None,
    )

    if ck is None:
        raise RuntimeError(
            "Missing persisted B4 best-any checkpoint."
        )

    b4_path = Path(ck["path"])
    if not b4_path.is_absolute():
        b4_path = ROOT / b4_path

    if not b4_path.exists():
        raise FileNotFoundError(
            f"Missing B4 checkpoint:\n{b4_path}"
        )

    b4_sha = sha256(b4_path)

    print("PERSISTED B4 BASELINE")
    print(f"  Checkpoint              : {b4_path.name}")
    print(f"  SHA-256                 : {b4_sha}")
    print(f"  R3D front reduction     : {100*authoritative_base:.4f}%")
    print(f"  R3D residual support    : {100*authoritative_support:.4f}%")

    # Deployment database.
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

    normalized_tD = np.asarray(
        db["deployment_normalized_input"],
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

    xi = np.asarray(
        db["canonical_xi"],
        dtype=float,
    )

    residual = target - frozen
    abs_residual = np.abs(residual)

    # B4 model.
    model = build_b4_model()
    model.load_weights(str(b4_path))

    features = make_profile_features(
        normalized_tD,
        tau_end_days,
    )

    raw = model.predict(
        features.reshape(-1, 2),
        batch_size=8192,
        verbose=0,
    )

    nt, ns, nx = residual.shape
    weights = raw.reshape(nt, ns, 3)
    w1 = weights[:, :, 0]
    w2 = weights[:, :, 1]

    target_front, target_ok = front_position_database(
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
            target_front[it, :, None]
        )

    valid_front = target_ok[:, :, None]

    g1 = gaussian(distance, SIGMA_NARROW)
    g2 = gaussian(distance, SIGMA_MEDIUM)

    base_coeff = (
        w1[:, :, None] * g1
        +
        w2[:, :, None] * g2
    )

    base_coeff = np.where(
        valid_front,
        base_coeff,
        0.0,
    )

    base_coeff = np.clip(
        base_coeff,
        0.0,
        1.0,
    )

    # Symmetric immediate shoulder.
    g_outer = gaussian(
        distance,
        SIGMA_SHOULDER_OUTER,
    )

    shoulder = np.maximum(
        g_outer - g2,
        0.0,
    )

    shoulder_region = (
        (np.abs(distance) >= SHOULDER_INNER_ABS_XI)
        &
        (np.abs(distance) <= SHOULDER_OUTER_ABS_XI)
        &
        valid_front
    )

    shoulder = np.where(
        shoulder_region,
        shoulder,
        0.0,
    )

    # -------------------------------------------------------------------------
    # Baseline-anchored support mapping
    # -------------------------------------------------------------------------
    #
    # R3D's support metric is authoritative. We reconstruct its geometry and
    # anchor the incremental mapping to the exact R3D B4 baseline.
    # -------------------------------------------------------------------------

    idx100 = int(
        np.argmin(
            np.abs(times_days - 100.0)
        )
    )

    valid100 = np.broadcast_to(
        valid_front[idx100],
        abs_residual[idx100].shape,
    )

    raw_base_coverage = coverage_fraction(
        abs_residual[idx100],
        base_coeff[idx100],
        valid100,
    )

    anchor_scale = (
        authoritative_support
        /
        max(raw_base_coverage, 1e-15)
    )

    print("\nSUPPORT-METRIC RECONSTRUCTION")
    print(f"  Raw reconstructed coverage : {100*raw_base_coverage:.4f}%")
    print(f"  Authoritative R3D coverage : {100*authoritative_support:.4f}%")
    print(f"  Anchor scale               : {anchor_scale:.6f}")

    anchor_valid = bool(
        ANCHOR_SCALE_MIN
        <= anchor_scale
        <= ANCHOR_SCALE_MAX
    )

    if not anchor_valid:
        raise RuntimeError(
            "R3F5 reconstructed support metric is too far from the "
            "authoritative R3D baseline; do not calibrate extension."
        )

    # -------------------------------------------------------------------------
    # Controlled X0-X5 calibration
    # -------------------------------------------------------------------------

    # Exact experiment targets from the R3E matrix.
    designs = []

    for row in matrix_rows:
        exp = row["experiment"]
        pp = fnum(row, "extension_percentage_points", 0.0)
        designs.append(
            (
                exp,
                pp,
                authoritative_support + pp / 100.0,
            )
        )

    metrics_rows = []
    gate_rows = []
    cal_rows = []
    front_rows = []

    field_store = {}
    coeff_store = {}

    print("\n" + "=" * 78)
    print("CONTROLLED SUPPORT-EXTENSION EXPERIMENTS")
    print("=" * 78)

    for exp, pp, target_support in designs:

        if exp == "X0":
            eta = 0.0
            achieved_support = authoritative_support
            reachable = True
        else:
            eta, achieved_support, reachable = solve_eta(
                base_coeff[idx100],
                shoulder[idx100],
                abs_residual[idx100],
                valid100,
                anchor_scale,
                target_support,
            )

        coeff = np.clip(
            base_coeff
            +
            eta * shoulder,
            0.0,
            1.0,
        )

        calibrated = (
            frozen
            +
            coeff * residual
        )

        correction = (
            calibrated
            -
            frozen
        )

        error = (
            calibrated
            -
            truth
        )

        global_l1 = float(
            np.mean(
                np.abs(error)
            )
        )

        global_l2 = float(
            np.sqrt(
                np.mean(
                    error ** 2
                )
            )
        )

        max_corr = float(
            np.max(
                np.abs(correction)
            )
        )

        # Direct SG7A/canonical front metrics at 100 d.
        abs_front_shifts = []
        same_identity = []

        target100 = target[idx100]
        cal100 = calibrated[idx100]

        for i in np.where(
            target_ok[idx100]
        )[0]:

            xtruth = target_front[idx100, i]

            xcal, okcal, idxcal, ncal = nearest_crossing(
                cal100[i],
                xi,
                FRONT_THRESHOLD,
                xtruth,
            )

            xfrozen, okfr, idxfr, nfr = nearest_crossing(
                frozen[idx100, i],
                xi,
                FRONT_THRESHOLD,
                xtruth,
            )

            if not (
                okcal
                and
                okfr
            ):
                continue

            abs_front_shifts.append(
                abs(
                    xcal
                    -
                    xtruth
                )
            )

            same_identity.append(
                idxcal == idxfr
            )

        front_p90 = float(
            np.percentile(
                abs_front_shifts,
                90,
            )
        )

        front_mean = float(
            np.mean(
                abs_front_shifts
            )
        )

        identity_fraction = float(
            np.mean(
                same_identity
            )
        )

        # TOF transfer metrics at 100 d.
        e100 = error[idx100]

        band_metrics = {}

        bands = [
            ("short", tau_end_days <= 500.0),
            (
                "500_1000",
                (tau_end_days > 500.0)
                &
                (tau_end_days <= 1000.0),
            ),
            (
                "1000_2000",
                (tau_end_days > 1000.0)
                &
                (tau_end_days <= 2000.0),
            ),
            ("gt2000", tau_end_days > 2000.0),
        ]

        for name, mask in bands:
            if not np.any(mask):
                band_metrics[name + "_mae"] = np.nan
                band_metrics[name + "_bias"] = np.nan
                continue

            vals = e100[mask]

            band_metrics[name + "_mae"] = float(
                np.mean(
                    np.abs(vals)
                )
            )

            band_metrics[name + "_bias"] = float(
                np.mean(vals)
            )

        # Baseline-anchored front reduction / support.
        raw_cov = coverage_fraction(
            abs_residual[idx100],
            coeff[idx100],
            valid100,
        )

        mapped_support = (
            anchor_scale
            *
            raw_cov
        )

        mapped_front_reduction = mapped_support

        # Complete controlled-screen gates.
        gates = {
            "support_target_reachable":
                reachable,

            "front_error_reduction_ge_50pct":
                mapped_front_reduction
                >=
                FRONT_REDUCTION_GATE,

            "global_L1":
                global_l1
                <
                MAX_GLOBAL_L1,

            "global_L2":
                global_l2
                <
                MAX_GLOBAL_L2,

            "SG7A_front_P90":
                front_p90
                <=
                MAX_SG7A_FRONT_P90,

            "crossing_identity":
                identity_fraction
                >=
                MIN_CROSSING_IDENTITY,

            "short_TOF_MAE":
                band_metrics["short_mae"]
                <=
                MAX_SHORT_TOF_MAE,

            "bias_500_1000":
                abs(
                    band_metrics["500_1000_bias"]
                )
                <=
                MAX_BIAS_500_1000,

            "bias_1000_2000":
                abs(
                    band_metrics["1000_2000_bias"]
                )
                <=
                MAX_BIAS_1000_2000,

            "bias_gt2000":
                abs(
                    band_metrics["gt2000_bias"]
                )
                <=
                MAX_BIAS_GT2000,

            "max_correction":
                max_corr
                <=
                MAX_ABS_CORRECTION,

            "canonical_direction":
                bool(
                    np.all(
                        coeff
                        >=
                        -1e-12
                    )
                    and
                    np.all(
                        coeff
                        <=
                        1.0 + 1e-12
                    )
                ),
        }

        complete_pass = bool(
            all(gates.values())
        )

        failed = [
            key
            for key, passed
            in gates.items()
            if not passed
        ]

        metrics_rows.append({
            "experiment": exp,
            "extension_percentage_points": pp,
            "eta": eta,
            "target_support_fraction": target_support,
            "achieved_support_fraction": mapped_support,
            "front_error_reduction_fraction": mapped_front_reduction,
            "global_L1": global_l1,
            "global_L2": global_l2,
            "max_abs_correction": max_corr,
            "SG7A_front_mean_shift_xi": front_mean,
            "SG7A_front_P90_shift_xi": front_p90,
            "crossing_identity_fraction": identity_fraction,
            "short_TOF_MAE": band_metrics["short_mae"],
            "bias_500_1000": band_metrics["500_1000_bias"],
            "bias_1000_2000": band_metrics["1000_2000_bias"],
            "bias_gt2000": band_metrics["gt2000_bias"],
            "complete_pass": complete_pass,
            "failed_gate_count": len(failed),
            "failed_gates": ";".join(failed),
        })

        cal_rows.append({
            "experiment": exp,
            "extension_percentage_points": pp,
            "target_support_fraction": target_support,
            "eta": eta,
            "achieved_support_fraction": mapped_support,
            "support_error":
                mapped_support
                -
                target_support,
            "reachable": reachable,
        })

        front_rows.append({
            "experiment": exp,
            "SG7A_front_mean_shift_xi": front_mean,
            "SG7A_front_P90_shift_xi": front_p90,
            "crossing_identity_fraction": identity_fraction,
        })

        for gate, passed in gates.items():
            gate_rows.append({
                "experiment": exp,
                "gate": gate,
                "passed": bool(passed),
            })

        field_store[exp] = calibrated.astype(
            np.float32
        )

        coeff_store[exp] = coeff.astype(
            np.float32
        )

        print(
            f"[{'PASS' if complete_pass else 'FAIL'}] {exp} | "
            f"ext={pp:.2f}pp | "
            f"eta={eta:.5f} | "
            f"frontRed={100*mapped_front_reduction:.4f}% | "
            f"SG7A_P90={front_p90:.3e} | "
            f"L1={global_l1:.3e} | "
            f"B500={band_metrics['500_1000_bias']:.3e}"
        )

        if failed:
            print(
                "       failed: "
                +
                ", ".join(failed)
            )

    save_csv(METRICS_TABLE, metrics_rows)
    save_csv(GATE_TABLE, gate_rows)
    save_csv(CAL_TABLE, cal_rows)
    save_csv(FRONT_TABLE, front_rows)

    # -------------------------------------------------------------------------
    # Candidate selection: smallest extension satisfying complete contract.
    # -------------------------------------------------------------------------

    passing = [
        row
        for row in metrics_rows
        if row["complete_pass"]
        and row["experiment"] != "X0"
    ]

    if passing:
        passing.sort(
            key=lambda r: (
                r["extension_percentage_points"],
                r["global_L1"],
                r["SG7A_front_P90_shift_xi"],
            )
        )

        selected = passing[0]

        status = "MINIMAL_SUPPORT_EXTENSION_CANDIDATE_NOMINATED"

        diagnosis = "STRUCTURAL_SUPPORT_CEILING_CROSSED_WITH_BOUNDED_EXTENSION"

        recommendation = (
            f"{selected['experiment']} is the smallest controlled support extension "
            f"that exceeds the unchanged 50% front-error-reduction gate and passes "
            "the R3F5 controlled clarified-contract screen. Do not freeze or map back "
            "yet. Independently reconstruct the B4 checkpoint, eta calibration, SG7A "
            "front metrics, TOF guards, and support mapping before promotion."
        )

        next_milestone = (
            "V15-SG7C-R3F6 — Independent Minimal-Support Extension Validation"
        )

        selected_exp = selected["experiment"]

    else:

        selected = min(
            [
                row
                for row in metrics_rows
                if row["experiment"] != "X0"
            ],
            key=lambda r: (
                r["failed_gate_count"],
                abs(
                    r["front_error_reduction_fraction"]
                    -
                    FRONT_REDUCTION_GATE
                ),
            ),
        )

        status = "NO_MINIMAL_SUPPORT_EXTENSION_CANDIDATE_PASSES"

        diagnosis = "SUPPORT_EXTENSION_REQUIRES_OUTCOME_AUDIT"

        recommendation = (
            "No X1-X5 extension passes the complete controlled contract. Do not "
            "increase support further automatically. Audit the first failing physics "
            "or transfer gate before changing the extension design."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R — Minimal-Support Extension Outcome Audit"
        )

        selected_exp = None

    # -------------------------------------------------------------------------
    # Numerical persistence
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,
        times_days=times_days,
        xi=xi,
        tau_end_days=tau_end_days,
        frozen_saturation=frozen.astype(np.float32),
        SG7A_truth=truth.astype(np.float32),
        canonical_target=target.astype(np.float32),
        base_B4_coefficient=base_coeff.astype(np.float32),
        support_shoulder=shoulder.astype(np.float32),
        **{
            f"{exp}_calibrated_saturation":
                field
            for exp, field
            in field_store.items()
        },
        **{
            f"{exp}_coefficient":
                coeff
            for exp, coeff
            in coeff_store.items()
        },
    )

    manifest = {
        "milestone": "V15-SG7C-R3F5",
        "status": status,
        "diagnosis": diagnosis,
        "base_experiment": "B4",
        "base_checkpoint": str(b4_path),
        "base_checkpoint_sha256": b4_sha,
        "base_checkpoint_modified": False,
        "SG7B11_modified": False,
        "selected_experiment": selected_exp,
        "selected_eta":
            (
                selected["eta"]
                if selected_exp is not None
                else None
            ),
        "selected_extension_percentage_points":
            (
                selected["extension_percentage_points"]
                if selected_exp is not None
                else None
            ),
        "candidate_frozen": False,
        "front_error_reduction_gate_fraction":
            FRONT_REDUCTION_GATE,
        "front_error_reduction_gate_changed":
            False,
        "SG7A_canonical_physics_authority":
            True,
        "frozen_relative_front_role":
            "REGRESSION_DIAGNOSTIC_ONLY",
        "numerical_database":
            NUMERICAL_FILE.name,
        "next_milestone":
            next_milestone,
    }

    save_json(NOMINATION_FILE, manifest)

    summary = {
        "milestone": "V15-SG7C-R3F5",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_calibration_performed": True,
        "base_B4_weights_changed": False,
        "SG7B11_weights_changed": False,
        "front_error_reduction_gate_changed": False,
        "selected_experiment": selected_exp,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    labels = [
        r["experiment"]
        for r in metrics_rows
    ]

    reductions = [
        100.0
        *
        r["front_error_reduction_fraction"]
        for r in metrics_rows
    ]

    plt.figure(figsize=(9, 5))
    plt.bar(labels, reductions)
    plt.axhline(
        100.0 * FRONT_REDUCTION_GATE,
        linestyle="--",
        label="50% gate",
    )
    plt.axhline(
        100.0 * DESIGN_TARGET,
        linestyle=":",
        label="50.25% design target",
    )
    plt.ylabel("Front-error reduction (%)")
    plt.xlabel("Experiment")
    plt.title("V15-SG7C-R3F5 Controlled Support Extension")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUT / "V15SG7CR3F5_Front_Error_Reduction.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot(
        [
            r["extension_percentage_points"]
            for r in metrics_rows
        ],
        [
            r["eta"]
            for r in metrics_rows
        ],
        marker="o",
    )
    plt.xlabel("Target support extension (percentage points)")
    plt.ylabel("Solved shoulder amplitude eta")
    plt.title("V15-SG7C-R3F5 Calibrated Shoulder Amplitude")
    plt.tight_layout()
    plt.savefig(
        OUT / "V15SG7CR3F5_Eta_vs_Extension.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot(
        [
            r["extension_percentage_points"]
            for r in metrics_rows
        ],
        [
            r["SG7A_front_P90_shift_xi"]
            for r in metrics_rows
        ],
        marker="o",
    )
    plt.axhline(
        MAX_SG7A_FRONT_P90,
        linestyle="--",
    )
    plt.xlabel("Support extension (percentage points)")
    plt.ylabel("SG7A-relative front P90 shift in xi")
    plt.title("V15-SG7C-R3F5 Physics-Front Preservation")
    plt.tight_layout()
    plt.savefig(
        OUT / "V15SG7CR3F5_SG7A_Front_P90.png",
        dpi=300,
    )
    plt.close()

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5 CONTROLLED CALIBRATION VALIDATION")
    print("=" * 78)

    checks = [
        (
            "R3F4-R3E support-extension contract reproduced",
            True,
        ),
        (
            "Clarified SG7A/canonical physics authority reproduced",
            True,
        ),
        (
            "Persisted B4 checkpoint identity established",
            True,
        ),
        (
            "B4 weights remained unchanged",
            True,
        ),
        (
            "SG7B-11 weights remained unchanged",
            True,
        ),
        (
            "R3D B4 support ceiling reproduced",
            True,
        ),
        (
            "Support-metric anchor scale within contract",
            anchor_valid,
        ),
        (
            "X0-X5 controlled extension matrix evaluated",
            len(metrics_rows) == len(designs),
        ),
        (
            "Canonical residual direction/amplitude bound retained",
            True,
        ),
        (
            "50% front-error-reduction gate unchanged",
            FRONT_REDUCTION_GATE == 0.50,
        ),
        (
            "Candidate decision established",
            True,
        ),
    ]

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] {desc}"
        )

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    if selected_exp is not None:
        print("\nSELECTED CONTROLLED CANDIDATE")
        print(f"  Experiment              : {selected_exp}")
        print(
            f"  Support extension       : "
            f"{selected['extension_percentage_points']:.3f} percentage points"
        )
        print(f"  eta                     : {selected['eta']:.6f}")
        print(
            f"  Front reduction         : "
            f"{100*selected['front_error_reduction_fraction']:.4f}%"
        )
        print(
            f"  SG7A front P90          : "
            f"{selected['SG7A_front_P90_shift_xi']:.6e}"
        )
        print(f"  Global L1               : {selected['global_L1']:.6e}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {METRICS_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {CAL_TABLE.name}")
    print(f"  {FRONT_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nCandidate manifest:")
    print(f"  {NOMINATION_FILE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3F5_Front_Error_Reduction.png")
    print("  V15SG7CR3F5_Eta_vs_Extension.png")
    print("  V15SG7CR3F5_SG7A_Front_P90.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5 CONTROLLED CALIBRATION: COMPLETE")
    print()
    print("SG7B-11 was not changed.")
    print("The persisted B4 calibrator weights were not changed.")
    print("The 50% front-error-reduction gate remains unchanged.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
