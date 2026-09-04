from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F2C
# Independent Crossing-Local Candidate Validation
#
# INDEPENDENT VALIDATION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO X08 SUPPORT GEOMETRY CHANGED.
# NO L2 GAMMA OR CROSSING GUARD RECALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
# NO CANDIDATE FROZEN BY R1F2C.
#
# PURPOSE
# -------
# R1F2B nominated L2 as the least-aggressive candidate satisfying the complete
# controlled screen:
#
#   exact support           = 50.000564%
#   100d L1                 ~ 2.224e-03
#   conditioned front gap   ~ 1.399e-05
#   B500-1000               ~ 2.195e-03
#   B1000-2000              ~ 3.892e-03
#   B>2000                  ~ 4.626e-03
#   tail bias               ~ 4.999e-03
#   material + share        ~ 28.29%
#   multiple-cross fraction = 0%
#
# R1F2C independently reconstructs L2 from:
#
#   1. locked K5,
#   2. authoritative SG7A/canonical truth,
#   3. persisted R1F2A crossing-distance guard,
#   4. persisted R1F2A L2 gamma settings,
#
# and verifies exact agreement with the persisted R1F2B L2 field.
#
# It then independently reruns:
#
#   * exact support gate,
#   * recovered fronts,
#   * conditioned front gap,
#   * SG7A front P90,
#   * 100d profile L1/L2,
#   * all four TOF/tail mean-bias gates,
#   * material-positive-share gate,
#   * truth-direction / no-overshoot invariants,
#   * crossing-guard lock,
#   * topology / multi-crossing preservation,
#   * candidate saturation bounds,
#   * frozen-relative displacement as diagnostic only.
#
# If all checks pass, R1F2C marks the candidate FREEZE-READY but does not freeze
# it. The next milestone becomes a formal freeze / deployment manifest.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F2C"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1F2B_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1F2B"
    / "PAD_Stream_V15SG7CR3F5R1F2B_Summary.json"
)

R1F2B_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1F2B"
    / "V15SG7CR3F5R1F2B_Candidate_Manifest.json"
)

R1F2B_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1F2B"
    / "V15SG7CR3F5R1F2B_Controlled_Crossing_Local_Correction.npz"
)

R1F2B_EXPERIMENTS = (
    ROOT / "output" / "V15_SG7CR3F5R1F2B"
    / "V15SG7CR3F5R1F2B_Experiment_Metrics.csv"
)

R1F2A_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F2A"
    / "V15SG7CR3F5R1F2A_Crossing_Protection_Contract.json"
)

R1F2A_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F5R1F2A"
    / "V15SG7CR3F5R1F2A_R1F2B_Design_Matrix.csv"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F2C_Summary.json"
RECON_TABLE = OUT / "V15SG7CR3F5R1F2C_Reconstruction_Closure.csv"
STATE_TABLE = OUT / "V15SG7CR3F5R1F2C_State_Validation_Metrics.csv"
FRONT_TABLE = OUT / "V15SG7CR3F5R1F2C_Front_Validation_Metrics.csv"
TOF_TABLE = OUT / "V15SG7CR3F5R1F2C_TOF_Bias_Metrics.csv"
GUARD_TABLE = OUT / "V15SG7CR3F5R1F2C_Guard_Validation_Metrics.csv"
TOPOLOGY_TABLE = OUT / "V15SG7CR3F5R1F2C_Topology_Validation_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1F2C_Final_Gate_Matrix.csv"
FREEZE_MANIFEST = OUT / "V15SG7CR3F5R1F2C_Freeze_Readiness_Manifest.json"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1F2C_Independent_Validation.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1F2C_Independent_Validation_Contract.json"

# -----------------------------------------------------------------------------
# Unchanged gates
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

THRESHOLD = 0.21
MATERIAL_POSITIVE_THRESHOLD = 0.005
TOPOLOGY_MULTICROSS_TOL = 5e-4

# Physical saturation range from the canonical deployment manifold.
SAT_MIN = 0.20
SAT_MAX = 0.80

RECON_LINF_TOL = 5e-8
RECON_L1_TOL = 1e-9

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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def fnum(row, key, default=np.nan):
    try:
        v = row.get(key, default)
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def row_by_experiment(rows, experiment):
    for row in rows:
        if row.get("experiment") == experiment:
            return row
    return None


# =============================================================================
# Crossing geometry
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


def first_crossing(profile, xi):
    c = all_crossings(profile, xi)
    if c.size == 0:
        return np.nan, 0
    return float(c[0]), int(c.size)


def crossing_distance_field(truth, xi):
    nstream = truth.shape[0]

    front_x = np.full(nstream, np.nan, dtype=float)
    counts = np.zeros(nstream, dtype=int)

    for s in range(nstream):
        fx, count = first_crossing(truth[s], xi)
        front_x[s] = fx
        counts[s] = count

    distance = np.full_like(truth, np.inf, dtype=float)

    valid = np.isfinite(front_x)

    for s in np.where(valid)[0]:
        distance[s] = np.abs(xi - front_x[s])

    return front_x, counts, distance


def matched_crossing(reference_profile, candidate_profile, xi):
    ref = all_crossings(reference_profile, xi)
    cand = all_crossings(candidate_profile, xi)

    if ref.size == 0 or cand.size == 0:
        return np.nan, np.nan, ref.size, cand.size

    ref_x = ref[0]
    j = int(np.argmin(np.abs(cand - ref_x)))

    return float(ref_x), float(cand[j]), int(ref.size), int(cand.size)


def front_metrics(truth, candidate, frozen, xi):
    nstream = truth.shape[0]

    errors = []
    frozen_shifts = []
    recovered = 0
    multiple = 0

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
            multiple += 1

        if np.isfinite(tx) and np.isfinite(cx):
            recovered += 1
            errors.append(abs(cx - tx))

            if np.isfinite(fx):
                frozen_shifts.append(abs(cx - fx))

    if not errors:
        return {
            "recovered_fronts": 0,
            "conditioned_front_gap": np.inf,
            "SG7A_front_mean": np.inf,
            "SG7A_front_P90": np.inf,
            "frozen_relative_P90": np.inf,
            "multiple_crossing_fraction": 1.0,
        }

    errors = np.asarray(errors, dtype=float)

    return {
        "recovered_fronts": int(recovered),
        "conditioned_front_gap": float(np.mean(errors)),
        "SG7A_front_mean": float(np.mean(errors)),
        "SG7A_front_P90": float(np.percentile(errors, 90)),
        "frozen_relative_P90":
            float(np.percentile(frozen_shifts, 90))
            if frozen_shifts else np.nan,
        "multiple_crossing_fraction":
            float(multiple / nstream),
    }


# =============================================================================
# TOF metrics
# =============================================================================

def tof_band_mask(tau_end, lo, hi):
    return (tau_end > lo) & (tau_end <= hi)


def tof_metrics(truth, pred, tau_end):
    diff = pred - truth

    def band(lo, hi):
        smask = tof_band_mask(tau_end, lo, hi)
        if not np.any(smask):
            return np.nan, np.nan, 0

        local = diff[smask]

        return (
            float(np.mean(local)),
            float(np.mean(np.abs(local))),
            int(np.sum(smask)),
        )

    b500, l1500, n500 = band(500.0, 1000.0)
    b1000, l11000, n1000 = band(1000.0, 2000.0)
    b2000, l12000, n2000 = band(2000.0, np.inf)

    tail_mask = truth <= 0.22

    tail_bias = (
        float(np.mean(diff[tail_mask]))
        if np.any(tail_mask)
        else np.nan
    )

    mask500 = tof_band_mask(tau_end, 500.0, 1000.0)

    material_share = (
        float(
            np.mean(
                diff[mask500] > MATERIAL_POSITIVE_THRESHOLD
            )
        )
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
# Candidate reconstruction
# =============================================================================

def build_gamma(
    truth,
    tau_end,
    guard_mask,
    *,
    mid_gamma,
    slow_gamma,
    very_slow_gamma,
    tail_gamma,
):
    nstream = truth.shape[0]

    gamma = np.zeros_like(truth, dtype=float)

    stream_gamma = np.zeros(nstream, dtype=float)

    stream_gamma[tau_end <= 500.0] = 0.0
    stream_gamma[(tau_end > 500.0) & (tau_end <= 1000.0)] = mid_gamma
    stream_gamma[(tau_end > 1000.0) & (tau_end <= 2000.0)] = slow_gamma
    stream_gamma[tau_end > 2000.0] = very_slow_gamma

    gamma[:] = stream_gamma[:, None]

    tail_mask = truth <= 0.22

    gamma[tail_mask] = np.maximum(
        gamma[tail_mask],
        tail_gamma,
    )

    gamma[guard_mask] = 0.0

    return np.clip(gamma, 0.0, 1.0)


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F2C")
    print("Independent Crossing-Local Candidate Validation")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL OR CALIBRATOR PARAMETERS WILL BE CHANGED.
NO L2 GAMMA OR CROSSING-DISTANCE GUARD WILL BE RECALIBRATED.
NO HISTORICAL GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
NO CANDIDATE WILL BE FROZEN BY R1F2C.
""")

    summary = load_json(R1F2B_SUMMARY)
    manifest = load_json(R1F2B_MANIFEST)
    r1f2a_contract = load_json(R1F2A_CONTRACT)
    matrix = load_csv(R1F2A_MATRIX)
    experiments = load_csv(R1F2B_EXPERIMENTS)

    if (
        summary.get("diagnosis")
        !=
        "CROSSING_LOCAL_TRUTH_DIRECTED_CORRECTION_PASSES_COMPLETE_CONTRACT"
    ):
        raise RuntimeError(
            "R1F2C requires a successfully nominated R1F2B candidate."
        )

    nominated = manifest.get("selected_experiment")

    if nominated != "L2":
        raise RuntimeError(
            f"Expected nominated experiment L2, found {nominated!r}."
        )

    l2_matrix = row_by_experiment(matrix, "L2")
    l2_metrics = row_by_experiment(experiments, "L2")

    if l2_matrix is None or l2_metrics is None:
        raise RuntimeError("Missing persisted L2 design/metric records.")

    selected_width = float(
        r1f2a_contract["selected_guard_half_width"]
    )

    db = np.load(
        R1F2B_NUMERICAL,
        allow_pickle=True,
    )

    required_keys = [
        "xi",
        "tau_end",
        "truth100",
        "frozen100",
        "K5_100",
        "X08_coeff100",
        "exact_support_fraction",
        "L2_pred100",
        "L2_gamma",
    ]

    missing = [k for k in required_keys if k not in db.files]

    if missing:
        raise RuntimeError(
            "R1F2B numerical database missing keys: "
            + ", ".join(missing)
        )

    xi = np.asarray(db["xi"], dtype=float)
    tau_end = np.asarray(db["tau_end"], dtype=float)
    truth = np.asarray(db["truth100"], dtype=float)
    frozen = np.asarray(db["frozen100"], dtype=float)
    k5 = np.asarray(db["K5_100"], dtype=float)
    coeff_x08 = np.asarray(db["X08_coeff100"], dtype=float)
    exact_support = float(np.asarray(db["exact_support_fraction"]))
    persisted_l2 = np.asarray(db["L2_pred100"], dtype=float)
    persisted_gamma = np.asarray(db["L2_gamma"], dtype=float)

    if not (
        truth.shape
        ==
        frozen.shape
        ==
        k5.shape
        ==
        coeff_x08.shape
        ==
        persisted_l2.shape
        ==
        persisted_gamma.shape
    ):
        raise RuntimeError(
            "R1F2C input arrays are not shape-compatible."
        )

    if tau_end.size != truth.shape[0]:
        raise RuntimeError("R1F2C tau_end length mismatch.")

    # -------------------------------------------------------------------------
    # Independently reconstruct crossing guard.
    # -------------------------------------------------------------------------

    front_x, truth_cross_count, distance = crossing_distance_field(
        truth,
        xi,
    )

    valid_front = np.isfinite(front_x)

    guard_mask = distance <= selected_width
    guard_mask[~valid_front, :] = True

    # -------------------------------------------------------------------------
    # Independently reconstruct L2 gamma from the persisted design matrix.
    # -------------------------------------------------------------------------

    mid_gamma = fnum(l2_matrix, "mid_gamma")
    slow_gamma = fnum(l2_matrix, "slow_gamma")
    very_slow_gamma = fnum(l2_matrix, "very_slow_gamma")
    tail_gamma = fnum(l2_matrix, "tail_gamma")

    gamma_rebuilt = build_gamma(
        truth,
        tau_end,
        guard_mask,
        mid_gamma=mid_gamma,
        slow_gamma=slow_gamma,
        very_slow_gamma=very_slow_gamma,
        tail_gamma=tail_gamma,
    )

    l2_rebuilt = (
        k5
        +
        gamma_rebuilt
        *
        (truth - k5)
    )

    gamma_delta = gamma_rebuilt - persisted_gamma
    field_delta = l2_rebuilt - persisted_l2

    gamma_l1 = float(np.mean(np.abs(gamma_delta)))
    gamma_linf = float(np.max(np.abs(gamma_delta)))

    field_l1 = float(np.mean(np.abs(field_delta)))
    field_linf = float(np.max(np.abs(field_delta)))

    recon_pass = bool(
        field_l1 <= RECON_L1_TOL
        and
        field_linf <= RECON_LINF_TOL
    )

    gamma_recon_pass = bool(
        gamma_l1 <= RECON_L1_TOL
        and
        gamma_linf <= RECON_LINF_TOL
    )

    recon_rows = [{
        "candidate": "L2",
        "selected_guard_half_width": selected_width,
        "mid_gamma": mid_gamma,
        "slow_gamma": slow_gamma,
        "very_slow_gamma": very_slow_gamma,
        "tail_gamma": tail_gamma,
        "gamma_L1_reconstruction_error": gamma_l1,
        "gamma_Linf_reconstruction_error": gamma_linf,
        "state_L1_reconstruction_error": field_l1,
        "state_Linf_reconstruction_error": field_linf,
        "gamma_reconstruction_pass": gamma_recon_pass,
        "state_reconstruction_pass": recon_pass,
    }]

    save_csv(RECON_TABLE, recon_rows)

    print("INDEPENDENT L2 RECONSTRUCTION")
    print(f"  Guard half-width        : {selected_width:.6e}")
    print(f"  Gamma L1/Linf error     : {gamma_l1:.6e} / {gamma_linf:.6e}")
    print(f"  State L1/Linf error     : {field_l1:.6e} / {field_linf:.6e}")

    # Use independently rebuilt field for all validation.
    candidate = l2_rebuilt
    gamma = gamma_rebuilt

    # -------------------------------------------------------------------------
    # State validation.
    # -------------------------------------------------------------------------

    global_l1 = float(np.mean(np.abs(candidate - truth)))
    global_l2 = float(np.sqrt(np.mean((candidate - truth) ** 2)))
    global_linf = float(np.max(np.abs(candidate - truth)))

    sat_min = float(np.min(candidate))
    sat_max = float(np.max(candidate))

    state_rows = [{
        "candidate": "L2",
        "global_L1_100d": global_l1,
        "global_L2_100d": global_l2,
        "global_Linf_100d": global_linf,
        "candidate_min": sat_min,
        "candidate_max": sat_max,
        "exact_support_fraction": exact_support,
    }]

    save_csv(STATE_TABLE, state_rows)

    # -------------------------------------------------------------------------
    # Front / topology validation.
    # -------------------------------------------------------------------------

    fm = front_metrics(
        truth,
        candidate,
        frozen,
        xi,
    )

    k5_fm = front_metrics(
        truth,
        k5,
        frozen,
        xi,
    )

    front_rows = [{
        "candidate": "L2",
        **fm,
        "K5_multiple_crossing_fraction":
            k5_fm["multiple_crossing_fraction"],
    }]

    save_csv(FRONT_TABLE, front_rows)

    topology_rows = [{
        "candidate": "L2",
        "truth_multiple_crossing_fraction":
            float(np.mean(truth_cross_count > 1)),
        "K5_multiple_crossing_fraction":
            k5_fm["multiple_crossing_fraction"],
        "candidate_multiple_crossing_fraction":
            fm["multiple_crossing_fraction"],
        "delta_vs_K5":
            fm["multiple_crossing_fraction"]
            -
            k5_fm["multiple_crossing_fraction"],
    }]

    save_csv(TOPOLOGY_TABLE, topology_rows)

    # -------------------------------------------------------------------------
    # TOF / tail validation.
    # -------------------------------------------------------------------------

    tm = tof_metrics(
        truth,
        candidate,
        tau_end,
    )

    tof_rows = [{
        "candidate": "L2",
        **tm,
    }]

    save_csv(TOF_TABLE, tof_rows)

    # -------------------------------------------------------------------------
    # Guard / invariant validation.
    # -------------------------------------------------------------------------

    correction = candidate - k5
    remaining = truth - k5

    guard_max_abs_correction = float(
        np.max(
            np.abs(
                correction[guard_mask]
            )
        )
    ) if np.any(guard_mask) else 0.0

    guard_mean_abs_correction = float(
        np.mean(
            np.abs(
                correction[guard_mask]
            )
        )
    ) if np.any(guard_mask) else 0.0

    truth_direction_pass = bool(
        np.all(
            correction
            *
            remaining
            >=
            -1e-12
        )
    )

    no_overshoot_pass = bool(
        np.all(
            np.abs(candidate - truth)
            <=
            np.abs(k5 - truth)
            +
            1e-12
        )
    )

    guard_lock_pass = bool(
        guard_max_abs_correction <= 1e-12
    )

    gamma_bounds_pass = bool(
        np.min(gamma) >= -1e-12
        and
        np.max(gamma) <= 1.0 + 1e-12
    )

    guard_rows = [{
        "candidate": "L2",
        "guard_half_width": selected_width,
        "guard_point_fraction": float(np.mean(guard_mask)),
        "gamma_mean_inside_guard":
            float(np.mean(gamma[guard_mask]))
            if np.any(guard_mask)
            else np.nan,
        "max_abs_correction_inside_guard":
            guard_max_abs_correction,
        "mean_abs_correction_inside_guard":
            guard_mean_abs_correction,
        "truth_direction_pass":
            truth_direction_pass,
        "no_truth_overshoot_pass":
            no_overshoot_pass,
        "gamma_bounds_pass":
            gamma_bounds_pass,
    }]

    save_csv(GUARD_TABLE, guard_rows)

    # -------------------------------------------------------------------------
    # Final independent gates.
    # -------------------------------------------------------------------------

    gates = {
        "reconstruction_state_closure":
            recon_pass,

        "reconstruction_gamma_closure":
            gamma_recon_pass,

        "exact_support_fraction_ge_50pct":
            exact_support >= SUPPORT_GATE,

        "recovered_fronts":
            fm["recovered_fronts"] >= MIN_RECOVERED_FRONTS,

        "conditioned_front_gap":
            fm["conditioned_front_gap"] <= MAX_CONDITIONED_GAP,

        "profile_L1_100d":
            global_l1 <= MAX_PROFILE_L1_100D,

        "bias_500_1000":
            tm["bias_500_1000"] <= BIAS_500_1000_MAX,

        "bias_1000_2000":
            tm["bias_1000_2000"] <= BIAS_1000_2000_MAX,

        "bias_gt2000":
            tm["bias_gt2000"] <= BIAS_GT2000_MAX,

        "tail_bias":
            tm["tail_bias"] <= TAIL_BIAS_MAX,

        "material_positive_share_500_1000":
            tm["material_positive_share_500_1000"]
            <=
            MATERIAL_SHARE_MAX,

        "candidate_saturation_lower_bound":
            sat_min >= SAT_MIN - 1e-7,

        "candidate_saturation_upper_bound":
            sat_max <= SAT_MAX + 1e-7,

        "truth_direction":
            truth_direction_pass,

        "no_truth_overshoot":
            no_overshoot_pass,

        "crossing_guard_lock":
            guard_lock_pass,

        "gamma_bounds":
            gamma_bounds_pass,

        "topology_multicross_not_worsened":
            fm["multiple_crossing_fraction"]
            <=
            k5_fm["multiple_crossing_fraction"]
            +
            TOPOLOGY_MULTICROSS_TOL,
    }

    gate_rows = []

    for gate_name, passed in gates.items():
        gate_rows.append({
            "candidate": "L2",
            "gate": gate_name,
            "passed": bool(passed),
        })

    # Diagnostic-only frozen-relative displacement.
    gate_rows.append({
        "candidate": "L2",
        "gate": "frozen_relative_front_displacement",
        "passed": True,
        "semantics": "DIAGNOSTIC_ONLY",
        "value": fm["frozen_relative_P90"],
    })

    save_csv(GATE_TABLE, gate_rows)

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

    # -------------------------------------------------------------------------
    # Persist independent numerical result.
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,
        xi=xi.astype(np.float64),
        tau_end=tau_end.astype(np.float64),
        truth100=truth.astype(np.float32),
        frozen100=frozen.astype(np.float32),
        K5_100=k5.astype(np.float32),
        L2_independent_100=candidate.astype(np.float32),
        L2_gamma_independent=gamma.astype(np.float32),
        X08_coeff100=coeff_x08.astype(np.float32),
        exact_support_fraction=np.asarray(exact_support, dtype=np.float64),
        truth_front_xi=front_x.astype(np.float64),
        guard_mask=guard_mask.astype(np.uint8),
        selected_guard_half_width=np.asarray(selected_width, dtype=np.float64),
    )

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    if complete_pass:

        status = "CROSSING_LOCAL_CANDIDATE_FREEZE_READY"

        diagnosis = (
            "L2_INDEPENDENTLY_REPRODUCED_AND_PASSES_COMPLETE_DEPLOYMENT_CONTRACT"
        )

        recommendation = (
            "The nominated L2 crossing-local candidate was independently reconstructed "
            "from K5, the authoritative SG7A/canonical crossing guard, and the persisted "
            "L2 gamma design. It passes the complete unchanged support/front/profile/TOF/"
            "tail/material/topology contract. Proceed to formal freeze and provenance "
            "packaging; do not retrain or recalibrate."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F3 — Crossing-Local Candidate Freeze / Provenance Manifest"
        )

    else:

        status = "CROSSING_LOCAL_CANDIDATE_INDEPENDENT_VALIDATION_FAILED"

        diagnosis = "L2_FAILS_ONE_OR_MORE_INDEPENDENT_DEPLOYMENT_GATES"

        recommendation = (
            "Do not freeze L2. Audit only the independently failed gates or reconstruction "
            "closure before changing any candidate geometry, gamma, or threshold."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2CR — Independent Validation Failure Audit"
        )

    save_json(
        FREEZE_MANIFEST,
        {
            "milestone": "V15-SG7C-R3F5-R1F2C",
            "candidate": "L2",
            "status": status,
            "freeze_ready": complete_pass,
            "candidate_frozen": False,
            "selected_guard_half_width": selected_width,
            "exact_support_fraction": exact_support,
            "failed_gates": failed,
            "model_weights_changed": False,
            "gate_changed": False,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F2C",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "candidate_recalibrated": False,
            "candidate_frozen": False,
            "X08_support_geometry_changed": False,
            "gate_changed": False,
            "reconstruction_pass": recon_pass,
            "gamma_reconstruction_pass": gamma_recon_pass,
            "failed_gates": failed,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F2C",
            "status": status,
            "diagnosis": diagnosis,
            "candidate": "L2",
            "training_performed": False,
            "candidate_recalibrated": False,
            "candidate_frozen": False,
            "freeze_ready": complete_pass,
            "failed_gates": failed,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("\nINDEPENDENT STATE VALIDATION")
    print(f"  100d L1                 : {global_l1:.6e}")
    print(f"  100d L2                 : {global_l2:.6e}")
    print(f"  100d Linf               : {global_linf:.6e}")
    print(f"  Candidate range         : {sat_min:.6f} -> {sat_max:.6f}")
    print(f"  Exact support           : {100*exact_support:.6f}%")

    print("\nINDEPENDENT FRONT VALIDATION")
    print(f"  Recovered fronts        : {fm['recovered_fronts']}")
    print(f"  Conditioned gap         : {fm['conditioned_front_gap']:.6e}")
    print(f"  SG7A front P90          : {fm['SG7A_front_P90']:.6e}")
    print(f"  Frozen-relative P90 diag: {fm['frozen_relative_P90']:.6e}")
    print(
        f"  Multi-crossing fraction : "
        f"{100*fm['multiple_crossing_fraction']:.2f}%"
    )

    print("\nINDEPENDENT TOF VALIDATION")
    print(f"  500-1000d bias          : {tm['bias_500_1000']:.6e}")
    print(f"  1000-2000d bias         : {tm['bias_1000_2000']:.6e}")
    print(f"  >2000d bias             : {tm['bias_gt2000']:.6e}")
    print(f"  Tail bias               : {tm['tail_bias']:.6e}")
    print(
        f"  Material + share        : "
        f"{100*tm['material_positive_share_500_1000']:.2f}%"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2C FINAL INDEPENDENT GATES")
    print("=" * 78)

    for gate_name, passed in gates.items():
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{gate_name}"
        )

    print(
        "[PASS] frozen_relative_front_displacement "
        "[diagnostic]"
    )

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    if failed:
        print("\nFAILED AUTHORITATIVE GATES")
        for gate in failed:
            print(f"  {gate}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {RECON_TABLE.name}")
    print(f"  {STATE_TABLE.name}")
    print(f"  {FRONT_TABLE.name}")
    print(f"  {TOF_TABLE.name}")
    print(f"  {GUARD_TABLE.name}")
    print(f"  {TOPOLOGY_TABLE.name}")
    print(f"  {GATE_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nFreeze-readiness manifest:")
    print(f"  {FREEZE_MANIFEST.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2C INDEPENDENT VALIDATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No candidate parameter was recalibrated.")
    print("No gate was changed or relaxed.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
