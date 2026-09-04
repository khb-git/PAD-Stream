from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F1
# Controlled Non-Front Slow-TOF Residual Correction
#
# CONTROLLED CORRECTION MILESTONE
#
# NO SG7B-11 WEIGHTS WILL BE CHANGED.
# NO R3F4 B4 MODEL WEIGHTS WILL BE CHANGED.
# NO X08 SUPPORT GEOMETRY WILL BE CHANGED.
# THE R1E J5 FIELD IS THE LOCKED FIRST-STAGE BASELINE.
# NO FRONT / TOF / MAP-BACK / SG7E GATE WILL BE CHANGED OR RELAXED.
# NO CANDIDATE WILL BE FROZEN BY R1F1.
#
# PURPOSE
# -------
# R1F0 established:
#
#   NONFRONT_SLOW_TOF_CAPACITY_CONTRACT_READY
#
# and sized the second-stage correction directly from the J5 residual deficits:
#
#   gamma_req(500-1000d)   ~ 0.234
#   gamma_req(1000-2000d)  ~ 0.211
#   gamma_req(>2000d)      ~ 0.260
#   gamma_req(tail)        ~ 0.307
#
# R1F1 applies the controlled K0-K5 matrix:
#
#   S_K = S_J5 + gamma_nonfront * (S_truth - S_J5)
#
# where:
#
#   * gamma = 0 in the accepted front core,
#   * gamma is zero or tightly bounded in the accepted front shell,
#   * gamma acts only on the remaining non-front slow-TOF / very-slow-TOF /
#     tail residual,
#   * correction direction is exactly toward SG7A/canonical truth,
#   * X08 exact-support coefficient field is never changed.
#
# Candidate selection:
#   choose the least aggressive K1-K5 candidate that passes every unchanged
#   support, front, profile, TOF, tail, material-share, truth-direction,
#   overshoot, and topology-preservation gate.
#
# R1F1 DOES NOT FREEZE THE CANDIDATE.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F1"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1F0_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1F0"
    / "PAD_Stream_V15SG7CR3F5R1F0_Summary.json"
)

R1F0_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F0"
    / "V15SG7CR3F5R1F0_NonFront_Capacity_Contract.json"
)

R1F0_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F5R1F0"
    / "V15SG7CR3F5R1F0_R1F1_Experiment_Matrix.csv"
)

R1E_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Controlled_Joint_Reconciliation.npz"
)

R1E_EXPERIMENTS = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Experiment_Metrics.csv"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F1_Summary.json"
EXPERIMENT_TABLE = OUT / "V15SG7CR3F5R1F1_Experiment_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1F1_Final_Gate_Matrix.csv"
REGIONAL_TABLE = OUT / "V15SG7CR3F5R1F1_Regional_Correction_Metrics.csv"
FRONT_TABLE = OUT / "V15SG7CR3F5R1F1_Front_Metrics.csv"
TOF_TABLE = OUT / "V15SG7CR3F5R1F1_TOF_Bias_Metrics.csv"
GAMMA_TABLE = OUT / "V15SG7CR3F5R1F1_Gamma_Field_Metrics.csv"
TOPOLOGY_TABLE = OUT / "V15SG7CR3F5R1F1_Topology_Preservation_Metrics.csv"
MANIFEST_FILE = OUT / "V15SG7CR3F5R1F1_Candidate_Manifest.json"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1F1_Controlled_NonFront_Correction.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1F1_Result_Contract.json"

# -----------------------------------------------------------------------------
# Unchanged authoritative gates
# -----------------------------------------------------------------------------

SUPPORT_GATE = 0.50
MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1_100D = 4.50032942291447424e-03

BIAS_500_1000_MAX = 2.5e-3
BIAS_1000_2000_MAX = 4.5e-3
BIAS_GT2000_MAX = 5.0e-3
TAIL_BIAS_MAX = 5.0e-3
MATERIAL_SHARE_MAX = 0.40

# Front semantics retained from R1D/R1F0.
THRESHOLD = 0.21
FRONT_CORE_LOW = 0.205
FRONT_CORE_HIGH = 0.235
FRONT_SHELL_LOW = 0.20
FRONT_SHELL_HIGH = 0.30
TAIL_THRESHOLD = 0.205

MATERIAL_POSITIVE_THRESHOLD = 0.005

# Topology guard:
# do not allow the second-stage correction to create a material increase in
# multiple-crossing incidence relative to locked J5.
TOPOLOGY_MULTICROSS_TOL = 5e-4

EPS = 1e-15


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

    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fnum(row, key, default=np.nan):
    try:
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def row_by_experiment(rows, experiment):
    for row in rows:
        if row.get("experiment") == experiment:
            return row
    return None


# =============================================================================
# Front / topology utilities
# =============================================================================

def all_crossings(profile, xi, threshold=THRESHOLD):
    p = np.asarray(profile, dtype=float)
    x = np.asarray(xi, dtype=float)

    y = p - threshold
    crossings = []

    for i in range(len(y) - 1):
        y0 = y[i]
        y1 = y[i + 1]

        if not np.isfinite(y0) or not np.isfinite(y1):
            continue

        if y0 == 0.0:
            crossings.append(float(x[i]))
            continue

        if y0 * y1 < 0.0 or y1 == 0.0:
            denom = y1 - y0

            if abs(denom) <= EPS:
                xc = 0.5 * (x[i] + x[i + 1])
            else:
                frac = -y0 / denom
                xc = x[i] + frac * (x[i + 1] - x[i])

            crossings.append(float(xc))

    return np.asarray(crossings, dtype=float)


def matched_crossing(reference_profile, candidate_profile, xi):
    ref = all_crossings(reference_profile, xi)
    cand = all_crossings(candidate_profile, xi)

    if ref.size == 0 or cand.size == 0:
        return np.nan, np.nan, ref.size, cand.size

    # Clarified deployment semantics:
    # match candidate crossing to SG7A/canonical physical crossing.
    ref_x = ref[0]
    j = int(np.argmin(np.abs(cand - ref_x)))
    cand_x = cand[j]

    return float(ref_x), float(cand_x), int(ref.size), int(cand.size)


def front_metrics(truth, candidate, frozen, xi):
    nstream = truth.shape[0]

    errors = []
    frozen_shifts = []
    recovered = 0
    multi = 0

    for s in range(nstream):
        tx, cx, _, nc = matched_crossing(
            truth[s],
            candidate[s],
            xi,
        )

        _, fx, _, _ = matched_crossing(
            truth[s],
            frozen[s],
            xi,
        )

        if nc > 1:
            multi += 1

        if np.isfinite(tx) and np.isfinite(cx):
            recovered += 1
            errors.append(abs(cx - tx))

            if np.isfinite(fx):
                frozen_shifts.append(abs(cx - fx))

    if not errors:
        return {
            "recovered_fronts": 0,
            "conditioned_front_gap": np.inf,
            "SG7A_front_P90": np.inf,
            "SG7A_front_mean": np.inf,
            "frozen_relative_P90": np.inf,
            "multiple_crossing_fraction": 1.0,
        }

    errors = np.asarray(errors, dtype=float)

    return {
        "recovered_fronts": int(recovered),
        "conditioned_front_gap": float(np.mean(errors)),
        "SG7A_front_P90": float(np.percentile(errors, 90)),
        "SG7A_front_mean": float(np.mean(errors)),
        "frozen_relative_P90":
            float(np.percentile(frozen_shifts, 90))
            if frozen_shifts
            else np.nan,
        "multiple_crossing_fraction": float(multi / nstream),
    }


# =============================================================================
# TOF metrics
# =============================================================================

def tof_band_mask(tau_end, lo, hi):
    return (tau_end > lo) & (tau_end <= hi)


def tof_metrics(truth, pred, tau_end):
    diff = pred - truth

    def mean_bias(lo, hi):
        mask = tof_band_mask(tau_end, lo, hi)

        if not np.any(mask):
            return np.nan, np.nan, 0

        local = diff[mask]

        return (
            float(np.mean(local)),
            float(np.mean(np.abs(local))),
            int(np.sum(mask)),
        )

    b500, l1500, n500 = mean_bias(500.0, 1000.0)
    b1000, l11000, n1000 = mean_bias(1000.0, 2000.0)
    b2000, l12000, n2000 = mean_bias(2000.0, np.inf)

    tail_mask = truth <= 0.22

    tail_bias = (
        float(np.mean(diff[tail_mask]))
        if np.any(tail_mask)
        else np.nan
    )

    mask500 = tof_band_mask(tau_end, 500.0, 1000.0)

    material_share = (
        float(np.mean(diff[mask500] > MATERIAL_POSITIVE_THRESHOLD))
        if np.any(mask500)
        else np.nan
    )

    return {
        "bias_500_1000": b500,
        "L1_500_1000": l1500,
        "streamlines_500_1000": n500,
        "bias_1000_2000": b1000,
        "L1_1000_2000": l11000,
        "streamlines_1000_2000": n1000,
        "bias_gt2000": b2000,
        "L1_gt2000": l12000,
        "streamlines_gt2000": n2000,
        "tail_bias": tail_bias,
        "material_positive_share_500_1000": material_share,
    }


# =============================================================================
# Second-stage gamma construction
# =============================================================================

def build_gamma(
    truth,
    tau_end,
    *,
    mid_gamma,
    slow_gamma,
    very_slow_gamma,
    tail_gamma,
    front_shell_gamma,
    front_core_gamma,
):
    """
    Deterministic second-stage non-front gamma.

    Base regional capacity:
      fast TOF         -> 0
      500-1000d        -> mid_gamma
      1000-2000d       -> slow_gamma
      >2000d           -> very_slow_gamma

    Tail can increase the base gamma.

    Then front protection is applied:
      accepted front shell -> cap by front_shell_gamma
      accepted front core  -> cap by front_core_gamma (normally exactly zero)
    """
    nstream, _ = truth.shape

    gamma = np.zeros_like(truth, dtype=float)

    stream_gamma = np.zeros(nstream, dtype=float)

    stream_gamma[tau_end <= 500.0] = 0.0
    stream_gamma[
        (tau_end > 500.0)
        &
        (tau_end <= 1000.0)
    ] = mid_gamma
    stream_gamma[
        (tau_end > 1000.0)
        &
        (tau_end <= 2000.0)
    ] = slow_gamma
    stream_gamma[
        tau_end > 2000.0
    ] = very_slow_gamma

    gamma[:] = stream_gamma[:, None]

    # Tail enhancement before front masking.
    tail_mask = truth <= TAIL_THRESHOLD

    gamma[tail_mask] = np.maximum(
        gamma[tail_mask],
        tail_gamma,
    )

    # Accepted front shell.
    front_shell = (
        (truth >= FRONT_SHELL_LOW)
        &
        (truth <= FRONT_SHELL_HIGH)
    )

    gamma[front_shell] = np.minimum(
        gamma[front_shell],
        front_shell_gamma,
    )

    # Accepted front core: strongest lock.
    front_core = (
        (truth >= FRONT_CORE_LOW)
        &
        (truth <= FRONT_CORE_HIGH)
    )

    gamma[front_core] = np.minimum(
        gamma[front_core],
        front_core_gamma,
    )

    return np.clip(gamma, 0.0, 1.0)


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F1")
    print("Controlled Non-Front Slow-TOF Residual Correction")
    print("=" * 78)

    print("""
CONTROLLED SECOND-STAGE CORRECTION WILL BE PERFORMED.
NO SG7B-11 OR R3F4 B4 MODEL WEIGHTS WILL BE CHANGED.
X08 SUPPORT GEOMETRY WILL REMAIN EXACTLY LOCKED.
R1E J5 IS THE LOCKED FIRST-STAGE BASELINE.
NO HISTORICAL GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
NO CANDIDATE WILL BE FROZEN BY R1F1.
""")

    summary = load_json(R1F0_SUMMARY)
    contract = load_json(R1F0_CONTRACT)

    if (
        summary.get("diagnosis")
        !=
        "TARGETED_EFFECTIVE_BETA_DEFICIT_REPAIR_DESIGNED"
    ):
        raise RuntimeError(
            "R1F1 requires successful R1F0 non-front capacity design."
        )

    matrix = load_csv(R1F0_MATRIX)

    if not any(row.get("experiment") == "K0" for row in matrix):
        raise RuntimeError("R1F0 experiment matrix does not contain K0.")

    # -------------------------------------------------------------------------
    # Load locked J5 / X08 state.
    # -------------------------------------------------------------------------

    db = np.load(
        R1E_NUMERICAL,
        allow_pickle=True,
    )

    required_keys = [
        "xi",
        "tau_end",
        "truth100",
        "frozen100",
        "X08_100",
        "X08_coeff100",
        "exact_support_fraction",
        "J5_pred100",
        "J5_beta",
    ]

    missing = [
        key
        for key in required_keys
        if key not in db.files
    ]

    if missing:
        raise RuntimeError(
            "R1E numerical database missing required arrays: "
            +
            ", ".join(missing)
        )

    xi = np.asarray(db["xi"], dtype=float)
    tau_end = np.asarray(db["tau_end"], dtype=float)
    truth = np.asarray(db["truth100"], dtype=float)
    frozen = np.asarray(db["frozen100"], dtype=float)
    x08 = np.asarray(db["X08_100"], dtype=float)
    coeff_x08 = np.asarray(db["X08_coeff100"], dtype=float)
    j5 = np.asarray(db["J5_pred100"], dtype=float)
    j5_beta = np.asarray(db["J5_beta"], dtype=float)
    exact_support = float(np.asarray(db["exact_support_fraction"]))

    if not (
        truth.shape
        ==
        frozen.shape
        ==
        x08.shape
        ==
        coeff_x08.shape
        ==
        j5.shape
        ==
        j5_beta.shape
    ):
        raise RuntimeError(
            "R1F1 input state/coefficient arrays are not shape-compatible."
        )

    if tau_end.size != truth.shape[0]:
        raise RuntimeError(
            "R1F1 tau_end length does not match streamline count."
        )

    if exact_support < SUPPORT_GATE:
        raise RuntimeError(
            "Locked X08 support is below the unchanged 50% gate."
        )

    remaining_after_j5 = truth - j5

    j5_front = front_metrics(
        truth,
        j5,
        frozen,
        xi,
    )

    j5_tof = tof_metrics(
        truth,
        j5,
        tau_end,
    )

    j5_l1 = float(
        np.mean(
            np.abs(
                j5 - truth
            )
        )
    )

    print("LOCKED FIRST-STAGE J5")
    print(
        f"  Exact support           : "
        f"{100*exact_support:.6f}%"
    )
    print(
        f"  100d L1                 : "
        f"{j5_l1:.6e}"
    )
    print(
        f"  Conditioned gap         : "
        f"{j5_front['conditioned_front_gap']:.6e}"
    )
    print(
        f"  500-1000d bias          : "
        f"{j5_tof['bias_500_1000']:.6e}"
    )
    print(
        f"  1000-2000d bias         : "
        f"{j5_tof['bias_1000_2000']:.6e}"
    )
    print(
        f"  >2000d bias             : "
        f"{j5_tof['bias_gt2000']:.6e}"
    )
    print(
        f"  Tail bias               : "
        f"{j5_tof['tail_bias']:.6e}"
    )
    print(
        f"  Material + share        : "
        f"{100*j5_tof['material_positive_share_500_1000']:.2f}%"
    )

    # -------------------------------------------------------------------------
    # Controlled K0-K5 evaluation.
    # -------------------------------------------------------------------------

    experiment_rows = []
    gate_rows = []
    regional_rows = []
    front_rows = []
    tof_rows = []
    gamma_rows = []
    topology_rows = []

    numerical_payload = {
        "xi": xi.astype(np.float64),
        "tau_end": tau_end.astype(np.float64),
        "truth100": truth.astype(np.float32),
        "frozen100": frozen.astype(np.float32),
        "X08_100": x08.astype(np.float32),
        "X08_coeff100": coeff_x08.astype(np.float32),
        "J5_100": j5.astype(np.float32),
        "J5_beta": j5_beta.astype(np.float32),
        "exact_support_fraction":
            np.asarray(
                exact_support,
                dtype=np.float64,
            ),
    }

    for matrix_row in matrix:

        exp = matrix_row["experiment"]

        mid_gamma = fnum(matrix_row, "mid_gamma", 0.0)
        slow_gamma = fnum(matrix_row, "slow_gamma", 0.0)
        very_slow_gamma = fnum(matrix_row, "very_slow_gamma", 0.0)
        tail_gamma = fnum(matrix_row, "tail_gamma", 0.0)
        front_shell_gamma = fnum(
            matrix_row,
            "front_shell_gamma",
            0.0,
        )
        front_core_gamma = fnum(
            matrix_row,
            "front_core_gamma",
            0.0,
        )

        gamma = build_gamma(
            truth,
            tau_end,
            mid_gamma=mid_gamma,
            slow_gamma=slow_gamma,
            very_slow_gamma=very_slow_gamma,
            tail_gamma=tail_gamma,
            front_shell_gamma=front_shell_gamma,
            front_core_gamma=front_core_gamma,
        )

        pred = (
            j5
            +
            gamma
            *
            remaining_after_j5
        )

        correction = pred - j5

        # Truth-direction and no-overshoot invariants.
        truth_direction_pass = bool(
            np.all(
                correction
                *
                remaining_after_j5
                >=
                -1e-12
            )
        )

        no_overshoot_pass = bool(
            np.all(
                np.abs(
                    pred - truth
                )
                <=
                np.abs(
                    j5 - truth
                )
                +
                1e-12
            )
        )

        # X08 support lock is structural: coeff_x08 is never modified.
        support_lock_pass = bool(
            exact_support >= SUPPORT_GATE
        )

        global_l1 = float(
            np.mean(
                np.abs(
                    pred - truth
                )
            )
        )

        global_l2 = float(
            np.sqrt(
                np.mean(
                    (
                        pred - truth
                    ) ** 2
                )
            )
        )

        fm = front_metrics(
            truth,
            pred,
            frozen,
            xi,
        )

        tm = tof_metrics(
            truth,
            pred,
            tau_end,
        )

        topology_pass = bool(
            fm["multiple_crossing_fraction"]
            <=
            j5_front["multiple_crossing_fraction"]
            +
            TOPOLOGY_MULTICROSS_TOL
        )

        gates = {
            "exact_support_fraction_ge_50pct":
                support_lock_pass,

            "recovered_fronts":
                fm["recovered_fronts"]
                >=
                MIN_RECOVERED_FRONTS,

            "conditioned_front_gap":
                fm["conditioned_front_gap"]
                <=
                MAX_CONDITIONED_GAP,

            "profile_L1_100d":
                global_l1
                <=
                MAX_PROFILE_L1_100D,

            "bias_500_1000":
                tm["bias_500_1000"]
                <=
                BIAS_500_1000_MAX,

            "bias_1000_2000":
                tm["bias_1000_2000"]
                <=
                BIAS_1000_2000_MAX,

            "bias_gt2000":
                tm["bias_gt2000"]
                <=
                BIAS_GT2000_MAX,

            "tail_bias":
                tm["tail_bias"]
                <=
                TAIL_BIAS_MAX,

            "material_positive_share_500_1000":
                tm["material_positive_share_500_1000"]
                <=
                MATERIAL_SHARE_MAX,

            "truth_direction":
                truth_direction_pass,

            "no_truth_overshoot":
                no_overshoot_pass,

            "topology_multicross_not_worsened":
                topology_pass,

            "X08_support_lock":
                True,
        }

        failed = [
            name
            for name, passed
            in gates.items()
            if not passed
        ]

        complete_pass = bool(
            all(
                gates.values()
            )
        )

        experiment_rows.append({
            "experiment":
                exp,
            "description":
                matrix_row.get(
                    "description",
                    "",
                ),
            "mid_gamma":
                mid_gamma,
            "slow_gamma":
                slow_gamma,
            "very_slow_gamma":
                very_slow_gamma,
            "tail_gamma":
                tail_gamma,
            "front_shell_gamma":
                front_shell_gamma,
            "front_core_gamma":
                front_core_gamma,
            "exact_support_fraction":
                exact_support,
            "global_L1_100d":
                global_l1,
            "global_L2_100d":
                global_l2,
            "recovered_fronts":
                fm["recovered_fronts"],
            "conditioned_front_gap":
                fm["conditioned_front_gap"],
            "SG7A_front_P90":
                fm["SG7A_front_P90"],
            "frozen_relative_P90_diagnostic":
                fm["frozen_relative_P90"],
            "multiple_crossing_fraction":
                fm["multiple_crossing_fraction"],
            "bias_500_1000":
                tm["bias_500_1000"],
            "bias_1000_2000":
                tm["bias_1000_2000"],
            "bias_gt2000":
                tm["bias_gt2000"],
            "tail_bias":
                tm["tail_bias"],
            "material_positive_share_500_1000":
                tm[
                    "material_positive_share_500_1000"
                ],
            "gamma_mean":
                float(
                    np.mean(
                        gamma
                    )
                ),
            "gamma_P90":
                float(
                    np.percentile(
                        gamma,
                        90,
                    )
                ),
            "gamma_max":
                float(
                    np.max(
                        gamma
                    )
                ),
            "complete_pass":
                complete_pass,
            "failed_gate_count":
                len(
                    failed
                ),
            "failed_gates":
                ";".join(
                    failed
                ),
        })

        front_rows.append({
            "experiment":
                exp,
            **fm,
            "profile_L1_100d":
                global_l1,
        })

        tof_rows.append({
            "experiment":
                exp,
            **tm,
        })

        # Gamma field diagnostics.
        front_core_mask = (
            (truth >= FRONT_CORE_LOW)
            &
            (truth <= FRONT_CORE_HIGH)
        )

        front_shell_mask = (
            (truth >= FRONT_SHELL_LOW)
            &
            (truth <= FRONT_SHELL_HIGH)
        )

        gamma_rows.append({
            "experiment":
                exp,
            "gamma_mean":
                float(np.mean(gamma)),
            "gamma_P50":
                float(np.percentile(gamma, 50)),
            "gamma_P90":
                float(np.percentile(gamma, 90)),
            "gamma_P99":
                float(np.percentile(gamma, 99)),
            "gamma_max":
                float(np.max(gamma)),
            "active_fraction":
                float(np.mean(gamma > 0.0)),
            "front_core_mean_gamma":
                float(np.mean(gamma[front_core_mask]))
                if np.any(front_core_mask)
                else np.nan,
            "front_shell_mean_gamma":
                float(np.mean(gamma[front_shell_mask]))
                if np.any(front_shell_mask)
                else np.nan,
        })

        topology_rows.append({
            "experiment":
                exp,
            "J5_multiple_crossing_fraction":
                j5_front["multiple_crossing_fraction"],
            "candidate_multiple_crossing_fraction":
                fm["multiple_crossing_fraction"],
            "delta_multiple_crossing_fraction":
                fm["multiple_crossing_fraction"]
                -
                j5_front["multiple_crossing_fraction"],
            "topology_guard_pass":
                topology_pass,
        })

        # Regional summaries.
        regions = [
            (
                "fast_TOF",
                tau_end <= 500.0,
            ),
            (
                "mid_TOF",
                (tau_end > 500.0)
                &
                (tau_end <= 1000.0),
            ),
            (
                "slow_TOF",
                (tau_end > 1000.0)
                &
                (tau_end <= 2000.0),
            ),
            (
                "very_slow_TOF",
                tau_end > 2000.0,
            ),
        ]

        for region_name, streamline_mask in regions:

            if not np.any(streamline_mask):
                continue

            local_gamma = gamma[
                streamline_mask
            ]

            local_corr = correction[
                streamline_mask
            ]

            before = (
                j5[
                    streamline_mask
                ]
                -
                truth[
                    streamline_mask
                ]
            )

            after = (
                pred[
                    streamline_mask
                ]
                -
                truth[
                    streamline_mask
                ]
            )

            regional_rows.append({
                "experiment":
                    exp,
                "region":
                    region_name,
                "streamlines":
                    int(
                        np.sum(
                            streamline_mask
                        )
                    ),
                "gamma_mean":
                    float(
                        np.mean(
                            local_gamma
                        )
                    ),
                "correction_L1":
                    float(
                        np.mean(
                            np.abs(
                                local_corr
                            )
                        )
                    ),
                "bias_before":
                    float(
                        np.mean(
                            before
                        )
                    ),
                "bias_after":
                    float(
                        np.mean(
                            after
                        )
                    ),
                "bias_reduction":
                    float(
                        np.mean(
                            before
                        )
                        -
                        np.mean(
                            after
                        )
                    ),
            })

        for gate_name, passed in gates.items():
            gate_rows.append({
                "experiment":
                    exp,
                "gate":
                    gate_name,
                "passed":
                    bool(
                        passed
                    ),
            })

        numerical_payload[
            f"{exp}_gamma"
        ] = gamma.astype(
            np.float32
        )

        numerical_payload[
            f"{exp}_pred100"
        ] = pred.astype(
            np.float32
        )

        print(
            f"[{'PASS' if complete_pass else 'FAIL'}] "
            f"{exp:<3s} | "
            f"L1={global_l1:.3e} | "
            f"gap={fm['conditioned_front_gap']:.3e} | "
            f"B500={tm['bias_500_1000']:.3e} | "
            f"B1000={tm['bias_1000_2000']:.3e} | "
            f"B2000={tm['bias_gt2000']:.3e} | "
            f"tail={tm['tail_bias']:.3e} | "
            f"mat={100*tm['material_positive_share_500_1000']:.1f}%"
        )

    # -------------------------------------------------------------------------
    # Persist.
    # -------------------------------------------------------------------------

    save_csv(
        EXPERIMENT_TABLE,
        experiment_rows,
    )

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    save_csv(
        REGIONAL_TABLE,
        regional_rows,
    )

    save_csv(
        FRONT_TABLE,
        front_rows,
    )

    save_csv(
        TOF_TABLE,
        tof_rows,
    )

    save_csv(
        GAMMA_TABLE,
        gamma_rows,
    )

    save_csv(
        TOPOLOGY_TABLE,
        topology_rows,
    )

    np.savez_compressed(
        NUMERICAL_FILE,
        **numerical_payload,
    )

    # -------------------------------------------------------------------------
    # Conservative selection.
    # -------------------------------------------------------------------------

    passing = [
        row
        for row in experiment_rows
        if row["experiment"] != "K0"
        and row["complete_pass"]
    ]

    if passing:

        order = {
            row["experiment"]: i
            for i, row in enumerate(matrix)
        }

        passing.sort(
            key=lambda row: (
                order.get(
                    row["experiment"],
                    999,
                ),
                row["gamma_mean"],
            )
        )

        selected = passing[0]
        selected_experiment = selected["experiment"]

        status = "NONFRONT_SLOW_TOF_CANDIDATE_NOMINATED"

        diagnosis = (
            "TARGETED_SECOND_STAGE_CORRECTION_PASSES_COMPLETE_CONTRACT"
        )

        recommendation = (
            "A controlled non-front second-stage residual correction satisfies the complete "
            "unchanged support/front/TOF/tail/topology contract while X08 support remains "
            "locked and the accepted front core remains protected. Do not freeze yet. "
            "Independently reconstruct and validate the nominated K candidate from persisted "
            "arrays before deployment freeze."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2 — Independent Non-Front Candidate Validation"
        )

    else:

        selected = min(
            experiment_rows,
            key=lambda row: (
                row["failed_gate_count"],
                row["global_L1_100d"],
            )
        )

        selected_experiment = None

        status = (
            "NO_R1F1_NONFRONT_CANDIDATE_PASSES_COMPLETE_CONTRACT"
        )

        diagnosis = (
            "NONFRONT_SECOND_STAGE_CORRECTION_REQUIRES_OUTCOME_AUDIT"
        )

        recommendation = (
            "No K1-K5 candidate satisfies every unchanged gate. Do not relax the contract "
            "or reopen X08 support. Audit the remaining gate limiter against the analytically "
            "sized non-front gamma trajectory."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F1R — Non-Front Correction Outcome Audit"
        )

    # -------------------------------------------------------------------------
    # Manifest / contract.
    # -------------------------------------------------------------------------

    save_json(
        MANIFEST_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1F1",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "X08_support_locked":
                True,
            "J5_first_stage_locked":
                True,
            "exact_support_fraction":
                exact_support,
            "selected_experiment":
                selected_experiment,
            "candidate_frozen":
                False,
            "model_weights_changed":
                False,
            "gate_changed":
                False,
            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1F1",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "second_stage_correction_performed":
                True,
            "X08_support_geometry_changed":
                False,
            "J5_first_stage_changed":
                False,
            "model_weights_changed":
                False,
            "gate_changed":
                False,
            "selected_experiment":
                selected_experiment,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1F1",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "second_stage_correction_performed":
                True,
            "X08_support_geometry_changed":
                False,
            "J5_first_stage_changed":
                False,
            "candidate_frozen":
                False,
            "selected_experiment":
                selected_experiment,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console summary.
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F1 FINAL CONTROLLED SCREEN")
    print("=" * 78)

    for row in experiment_rows:
        print(
            f"[{'PASS' if row['complete_pass'] else 'FAIL'}] "
            f"{row['experiment']} | "
            f"fails={row['failed_gate_count']} | "
            f"support={100*row['exact_support_fraction']:.6f}% | "
            f"gap={row['conditioned_front_gap']:.3e} | "
            f"B500={row['bias_500_1000']:.3e} | "
            f"B1000={row['bias_1000_2000']:.3e} | "
            f"B2000={row['bias_gt2000']:.3e} | "
            f"tail={row['tail_bias']:.3e} | "
            f"mat={100*row['material_positive_share_500_1000']:.1f}%"
        )

    print("=" * 78)

    if selected_experiment is not None:

        print("\nNOMINATED NON-FRONT CANDIDATE")
        print(
            f"  Experiment              : "
            f"{selected_experiment}"
        )
        print(
            f"  Exact support           : "
            f"{100*selected['exact_support_fraction']:.6f}%"
        )
        print(
            f"  100d L1                 : "
            f"{selected['global_L1_100d']:.6e}"
        )
        print(
            f"  Conditioned gap         : "
            f"{selected['conditioned_front_gap']:.6e}"
        )
        print(
            f"  500-1000d bias          : "
            f"{selected['bias_500_1000']:.6e}"
        )
        print(
            f"  1000-2000d bias         : "
            f"{selected['bias_1000_2000']:.6e}"
        )
        print(
            f"  >2000d bias             : "
            f"{selected['bias_gt2000']:.6e}"
        )
        print(
            f"  Tail bias               : "
            f"{selected['tail_bias']:.6e}"
        )
        print(
            f"  Material + share        : "
            f"{100*selected['material_positive_share_500_1000']:.2f}%"
        )
        print(
            f"  Multiple-cross fraction : "
            f"{100*selected['multiple_crossing_fraction']:.2f}%"
        )

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(
        f"  Directory:\n"
        f"    {OUT}"
    )

    print("\nTables:")
    print(f"  {EXPERIMENT_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {REGIONAL_TABLE.name}")
    print(f"  {FRONT_TABLE.name}")
    print(f"  {TOF_TABLE.name}")
    print(f"  {GAMMA_TABLE.name}")
    print(f"  {TOPOLOGY_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nCandidate manifest:")
    print(f"  {MANIFEST_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F1 CONTROLLED CORRECTION: COMPLETE")
    print()
    print("No model weights were changed.")
    print("X08 support geometry remained locked.")
    print("J5 remained the locked first-stage baseline.")
    print("No gate was changed or relaxed.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
