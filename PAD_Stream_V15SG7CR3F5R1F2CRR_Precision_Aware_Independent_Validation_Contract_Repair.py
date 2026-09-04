from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F2C-R
# Precision-Aware Independent Validation Contract Repair
#
# CONTRACT-REPAIR / INDEPENDENT-RERUN MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO L2 GAMMA OR CROSSING GUARD RECALIBRATED.
# NO PHYSICS / FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
# NO CANDIDATE FROZEN.
#
# PURPOSE
# -------
# R1F2CR established:
#
#   FLOAT32_PERSISTENCE_PRECISION_EXPLAINS_CLOSURE_FAILURE
#
# with:
#
#   persisted L2 gamma dtype = float32
#   persisted L2 state dtype = float32
#
#   observed gamma Linf = 1.363601e-08
#   derived gamma envelope = 2.980232e-08
#
#   observed state Linf = 2.979928e-08
#   derived state envelope = 1.192093e-07
#
# Therefore the only R1F2C failures were caused by a fixed decimal closure
# tolerance that was stricter than the actual persistence representation.
#
# R1F2C-R repairs ONLY the reconstruction-closure contract:
#
#   gamma closure:
#       L_inf <= precision-aware gamma envelope
#
#   state closure:
#       L_inf <= precision-aware state envelope
#
# The envelopes are loaded directly from the R1F2CR provenance audit.
# They are NOT manually chosen in this script.
#
# R1F2C-R then independently reconstructs L2 again and reruns the complete
# deployment validation contract.
#
# If every gate passes, L2 becomes freeze-ready.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1F2CR_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CR"
    / "PAD_Stream_V15SG7CR3F5R1F2CR_Summary.json"
)

R1F2CR_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CR"
    / "V15SG7CR3F5R1F2CR_Precision_Aware_Closure_Contract.json"
)

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

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F2CRR_Summary.json"
RECON_TABLE = OUT / "V15SG7CR3F5R1F2CRR_Precision_Aware_Reconstruction_Closure.csv"
STATE_TABLE = OUT / "V15SG7CR3F5R1F2CRR_State_Validation_Metrics.csv"
FRONT_TABLE = OUT / "V15SG7CR3F5R1F2CRR_Front_Validation_Metrics.csv"
TOF_TABLE = OUT / "V15SG7CR3F5R1F2CRR_TOF_Bias_Metrics.csv"
GUARD_TABLE = OUT / "V15SG7CR3F5R1F2CRR_Guard_Validation_Metrics.csv"
TOPOLOGY_TABLE = OUT / "V15SG7CR3F5R1F2CRR_Topology_Validation_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1F2CRR_Final_Gate_Matrix.csv"
FREEZE_MANIFEST = OUT / "V15SG7CR3F5R1F2CRR_Freeze_Readiness_Manifest.json"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1F2CRR_Independent_Validation.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1F2CRR_Repaired_Independent_Validation_Contract.json"

# -----------------------------------------------------------------------------
# Unchanged authoritative deployment gates
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

SAT_MIN = 0.20
SAT_MAX = 0.80

EPS = 1e-15


# =============================================================================
# IO helpers
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


def row_by_experiment(rows, exp):
    for row in rows:
        if row.get("experiment") == exp:
            return row
    return None


# =============================================================================
# Crossing geometry
# =============================================================================

def all_crossings(profile, xi, threshold=THRESHOLD):
    p = np.asarray(profile, dtype=float)
    x = np.asarray(xi, dtype=float)
    y = p - threshold

    out = []

    for i in range(len(y) - 1):
        y0 = y[i]
        y1 = y[i + 1]

        if not np.isfinite(y0) or not np.isfinite(y1):
            continue

        if y0 == 0.0:
            out.append(float(x[i]))
            continue

        if y0 * y1 < 0.0 or y1 == 0.0:
            denom = y1 - y0

            if abs(denom) <= EPS:
                xc = 0.5 * (x[i] + x[i + 1])
            else:
                frac = -y0 / denom
                xc = x[i] + frac * (x[i + 1] - x[i])

            out.append(float(xc))

    return np.asarray(out, dtype=float)


def crossing_distance_field(truth, xi):
    nstream = truth.shape[0]

    front_x = np.full(nstream, np.nan, dtype=float)
    count = np.zeros(nstream, dtype=int)

    for s in range(nstream):
        crossings = all_crossings(truth[s], xi)

        if crossings.size:
            front_x[s] = crossings[0]
            count[s] = int(crossings.size)

    distance = np.full_like(truth, np.inf, dtype=float)

    valid = np.isfinite(front_x)

    for s in np.where(valid)[0]:
        distance[s] = np.abs(
            xi - front_x[s]
        )

    return front_x, count, distance, valid


def matched_crossing(reference_profile, candidate_profile, xi):
    ref = all_crossings(reference_profile, xi)
    cand = all_crossings(candidate_profile, xi)

    if ref.size == 0 or cand.size == 0:
        return np.nan, np.nan, ref.size, cand.size

    ref_x = ref[0]

    j = int(
        np.argmin(
            np.abs(
                cand - ref_x
            )
        )
    )

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

        "conditioned_front_gap":
            float(np.mean(errors)),

        "SG7A_front_mean":
            float(np.mean(errors)),

        "SG7A_front_P90":
            float(np.percentile(errors, 90)),

        "frozen_relative_P90":
            float(np.percentile(frozen_shifts, 90))
            if frozen_shifts
            else np.nan,

        "multiple_crossing_fraction":
            float(multiple / nstream),
    }


# =============================================================================
# TOF metrics
# =============================================================================

def tof_band_mask(tau_end, lo, hi):
    return (
        (tau_end > lo)
        &
        (tau_end <= hi)
    )


def tof_metrics(truth, pred, tau_end):
    diff = pred - truth

    def band(lo, hi):
        smask = tof_band_mask(
            tau_end,
            lo,
            hi,
        )

        if not np.any(smask):
            return np.nan, np.nan, 0

        local = diff[smask]

        return (
            float(np.mean(local)),
            float(np.mean(np.abs(local))),
            int(np.sum(smask)),
        )

    b500, l1500, n500 = band(
        500.0,
        1000.0,
    )

    b1000, l11000, n1000 = band(
        1000.0,
        2000.0,
    )

    b2000, l12000, n2000 = band(
        2000.0,
        np.inf,
    )

    tail_mask = truth <= 0.22

    tail_bias = (
        float(
            np.mean(
                diff[tail_mask]
            )
        )
        if np.any(tail_mask)
        else np.nan
    )

    mask500 = tof_band_mask(
        tau_end,
        500.0,
        1000.0,
    )

    material_share = (
        float(
            np.mean(
                diff[mask500]
                >
                MATERIAL_POSITIVE_THRESHOLD
            )
        )
        if np.any(mask500)
        else np.nan
    )

    return {
        "bias_500_1000":
            b500,

        "L1_500_1000":
            l1500,

        "streamlines_500_1000":
            n500,

        "bias_1000_2000":
            b1000,

        "L1_1000_2000":
            l11000,

        "streamlines_1000_2000":
            n1000,

        "bias_gt2000":
            b2000,

        "L1_gt2000":
            l12000,

        "streamlines_gt2000":
            n2000,

        "tail_bias":
            tail_bias,

        "material_positive_share_500_1000":
            material_share,
    }


# =============================================================================
# L2 gamma reconstruction
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
    """
    Rebuild in float64 for independent validation.
    Precision-aware closure is judged against the persisted float32 envelope
    established by R1F2CR.
    """
    truth64 = np.asarray(truth, dtype=np.float64)
    tau64 = np.asarray(tau_end, dtype=np.float64)

    nstream = truth64.shape[0]

    gamma = np.zeros_like(
        truth64,
        dtype=np.float64,
    )

    stream_gamma = np.zeros(
        nstream,
        dtype=np.float64,
    )

    stream_gamma[
        tau64 <= 500.0
    ] = 0.0

    stream_gamma[
        (tau64 > 500.0)
        &
        (tau64 <= 1000.0)
    ] = float(mid_gamma)

    stream_gamma[
        (tau64 > 1000.0)
        &
        (tau64 <= 2000.0)
    ] = float(slow_gamma)

    stream_gamma[
        tau64 > 2000.0
    ] = float(very_slow_gamma)

    gamma[:] = stream_gamma[:, None]

    tail_mask = truth64 <= 0.22

    gamma[tail_mask] = np.maximum(
        gamma[tail_mask],
        float(tail_gamma),
    )

    gamma[guard_mask] = 0.0

    return np.clip(
        gamma,
        0.0,
        1.0,
    )


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F2C-R")
    print("Precision-Aware Independent Validation Contract Repair")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL OR CALIBRATOR PARAMETERS WILL BE CHANGED.
NO L2 GAMMA OR CROSSING-DISTANCE GUARD WILL BE RECALIBRATED.
NO PHYSICS / FRONT / TOF / MAP-BACK / SG7E GATE WILL BE CHANGED OR RELAXED.
ONLY THE RECONSTRUCTION-CLOSURE NUMERICAL CONTRACT IS REPAIRED.
NO CANDIDATE WILL BE FROZEN BY R1F2C-R.
""")

    cr_summary = load_json(
        R1F2CR_SUMMARY
    )

    cr_contract = load_json(
        R1F2CR_CONTRACT
    )

    b_summary = load_json(
        R1F2B_SUMMARY
    )

    b_manifest = load_json(
        R1F2B_MANIFEST
    )

    a_contract = load_json(
        R1F2A_CONTRACT
    )

    if (
        cr_summary.get("diagnosis")
        !=
        "FLOAT32_PERSISTENCE_PRECISION_EXPLAINS_CLOSURE_FAILURE"
    ):
        raise RuntimeError(
            "R1F2C-R requires R1F2CR precision provenance resolution."
        )

    if not bool(
        cr_contract.get(
            "quantization_consistent",
            False,
        )
    ):
        raise RuntimeError(
            "R1F2CR did not establish quantization-consistent closure."
        )

    if (
        b_summary.get("diagnosis")
        !=
        "CROSSING_LOCAL_TRUTH_DIRECTED_CORRECTION_PASSES_COMPLETE_CONTRACT"
    ):
        raise RuntimeError(
            "R1F2C-R requires a successful R1F2B candidate nomination."
        )

    if (
        b_manifest.get("selected_experiment")
        !=
        "L2"
    ):
        raise RuntimeError(
            "R1F2C-R expects L2 as the nominated R1F2B candidate."
        )

    # Precision-aware closure envelope from R1F2CR.
    gamma_envelope = float(
        cr_contract[
            "gamma_precision_aware_envelope"
        ]
    )

    state_envelope = float(
        cr_contract[
            "state_precision_aware_envelope"
        ]
    )

    selected_width = float(
        a_contract[
            "selected_guard_half_width"
        ]
    )

    matrix = load_csv(
        R1F2A_MATRIX
    )

    l2 = row_by_experiment(
        matrix,
        "L2",
    )

    if l2 is None:
        raise RuntimeError(
            "Missing L2 design matrix record."
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

    missing = [
        k
        for k in required_keys
        if k not in db.files
    ]

    if missing:
        raise RuntimeError(
            "R1F2B numerical database missing required arrays: "
            +
            ", ".join(missing)
        )

    xi = np.asarray(
        db["xi"],
        dtype=np.float64,
    )

    tau_end = np.asarray(
        db["tau_end"],
        dtype=np.float64,
    )

    truth = np.asarray(
        db["truth100"],
        dtype=np.float64,
    )

    frozen = np.asarray(
        db["frozen100"],
        dtype=np.float64,
    )

    k5 = np.asarray(
        db["K5_100"],
        dtype=np.float64,
    )

    coeff_x08 = np.asarray(
        db["X08_coeff100"],
        dtype=np.float64,
    )

    persisted_l2 = np.asarray(
        db["L2_pred100"],
        dtype=np.float64,
    )

    persisted_gamma = np.asarray(
        db["L2_gamma"],
        dtype=np.float64,
    )

    exact_support = float(
        np.asarray(
            db[
                "exact_support_fraction"
            ]
        )
    )

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
            "R1F2C-R state/coefficient arrays are not shape-compatible."
        )

    if tau_end.size != truth.shape[0]:
        raise RuntimeError(
            "R1F2C-R tau_end length mismatch."
        )

    # -------------------------------------------------------------------------
    # Independent guard reconstruction.
    # -------------------------------------------------------------------------

    front_x, truth_cross_count, distance, valid_front = (
        crossing_distance_field(
            truth,
            xi,
        )
    )

    guard_mask = (
        distance
        <=
        selected_width
    )

    guard_mask[
        ~valid_front,
        :
    ] = True

    # -------------------------------------------------------------------------
    # Independent L2 reconstruction.
    # -------------------------------------------------------------------------

    mid_gamma = fnum(
        l2,
        "mid_gamma",
    )

    slow_gamma = fnum(
        l2,
        "slow_gamma",
    )

    very_slow_gamma = fnum(
        l2,
        "very_slow_gamma",
    )

    tail_gamma = fnum(
        l2,
        "tail_gamma",
    )

    gamma = build_gamma(
        truth,
        tau_end,
        guard_mask,
        mid_gamma=mid_gamma,
        slow_gamma=slow_gamma,
        very_slow_gamma=very_slow_gamma,
        tail_gamma=tail_gamma,
    )

    candidate = (
        k5
        +
        gamma
        *
        (
            truth
            -
            k5
        )
    )

    gamma_delta = (
        gamma
        -
        persisted_gamma
    )

    state_delta = (
        candidate
        -
        persisted_l2
    )

    gamma_l1 = float(
        np.mean(
            np.abs(
                gamma_delta
            )
        )
    )

    gamma_linf = float(
        np.max(
            np.abs(
                gamma_delta
            )
        )
    )

    state_l1 = float(
        np.mean(
            np.abs(
                state_delta
            )
        )
    )

    state_linf = float(
        np.max(
            np.abs(
                state_delta
            )
        )
    )

    gamma_closure_pass = bool(
        gamma_linf
        <=
        gamma_envelope
        +
        EPS
    )

    state_closure_pass = bool(
        state_linf
        <=
        state_envelope
        +
        EPS
    )

    recon_rows = [{
        "candidate":
            "L2",

        "persisted_gamma_dtype":
            cr_contract[
                "persisted_gamma_dtype"
            ],

        "persisted_state_dtype":
            cr_contract[
                "persisted_state_dtype"
            ],

        "gamma_L1_error":
            gamma_l1,

        "gamma_Linf_error":
            gamma_linf,

        "gamma_precision_aware_envelope":
            gamma_envelope,

        "gamma_closure_pass":
            gamma_closure_pass,

        "state_L1_error":
            state_l1,

        "state_Linf_error":
            state_linf,

        "state_precision_aware_envelope":
            state_envelope,

        "state_closure_pass":
            state_closure_pass,

        "closure_basis":
            "R1F2CR persisted-dtype ULP provenance",
    }]

    save_csv(
        RECON_TABLE,
        recon_rows,
    )

    print("PRECISION-AWARE L2 RECONSTRUCTION")
    print(
        f"  Gamma L1 / Linf        : "
        f"{gamma_l1:.6e} / {gamma_linf:.6e}"
    )
    print(
        f"  Gamma envelope         : "
        f"{gamma_envelope:.6e}"
    )
    print(
        f"  State L1 / Linf        : "
        f"{state_l1:.6e} / {state_linf:.6e}"
    )
    print(
        f"  State envelope         : "
        f"{state_envelope:.6e}"
    )

    # -------------------------------------------------------------------------
    # State validation.
    # -------------------------------------------------------------------------

    global_l1 = float(
        np.mean(
            np.abs(
                candidate
                -
                truth
            )
        )
    )

    global_l2 = float(
        np.sqrt(
            np.mean(
                (
                    candidate
                    -
                    truth
                ) ** 2
            )
        )
    )

    global_linf = float(
        np.max(
            np.abs(
                candidate
                -
                truth
            )
        )
    )

    sat_min = float(
        np.min(
            candidate
        )
    )

    sat_max = float(
        np.max(
            candidate
        )
    )

    save_csv(
        STATE_TABLE,
        [{
            "candidate":
                "L2",
            "global_L1_100d":
                global_l1,
            "global_L2_100d":
                global_l2,
            "global_Linf_100d":
                global_linf,
            "candidate_min":
                sat_min,
            "candidate_max":
                sat_max,
            "exact_support_fraction":
                exact_support,
        }],
    )

    # -------------------------------------------------------------------------
    # Front / topology.
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

    save_csv(
        FRONT_TABLE,
        [{
            "candidate":
                "L2",
            **fm,
            "K5_multiple_crossing_fraction":
                k5_fm[
                    "multiple_crossing_fraction"
                ],
        }],
    )

    save_csv(
        TOPOLOGY_TABLE,
        [{
            "candidate":
                "L2",

            "truth_multiple_crossing_fraction":
                float(
                    np.mean(
                        truth_cross_count
                        >
                        1
                    )
                ),

            "K5_multiple_crossing_fraction":
                k5_fm[
                    "multiple_crossing_fraction"
                ],

            "candidate_multiple_crossing_fraction":
                fm[
                    "multiple_crossing_fraction"
                ],

            "delta_vs_K5":
                fm[
                    "multiple_crossing_fraction"
                ]
                -
                k5_fm[
                    "multiple_crossing_fraction"
                ],
        }],
    )

    # -------------------------------------------------------------------------
    # TOF metrics.
    # -------------------------------------------------------------------------

    tm = tof_metrics(
        truth,
        candidate,
        tau_end,
    )

    save_csv(
        TOF_TABLE,
        [{
            "candidate":
                "L2",
            **tm,
        }],
    )

    # -------------------------------------------------------------------------
    # Guard / invariants.
    # -------------------------------------------------------------------------

    correction = (
        candidate
        -
        k5
    )

    remaining = (
        truth
        -
        k5
    )

    guard_max_abs_correction = (
        float(
            np.max(
                np.abs(
                    correction[
                        guard_mask
                    ]
                )
            )
        )
        if np.any(
            guard_mask
        )
        else
        0.0
    )

    guard_lock_pass = bool(
        guard_max_abs_correction
        <=
        1e-12
    )

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
            np.abs(
                candidate
                -
                truth
            )
            <=
            np.abs(
                k5
                -
                truth
            )
            +
            1e-12
        )
    )

    gamma_bounds_pass = bool(
        np.min(
            gamma
        )
        >=
        -1e-12
        and
        np.max(
            gamma
        )
        <=
        1.0
        +
        1e-12
    )

    save_csv(
        GUARD_TABLE,
        [{
            "candidate":
                "L2",

            "guard_half_width":
                selected_width,

            "guard_point_fraction":
                float(
                    np.mean(
                        guard_mask
                    )
                ),

            "gamma_mean_inside_guard":
                float(
                    np.mean(
                        gamma[
                            guard_mask
                        ]
                    )
                )
                if np.any(
                    guard_mask
                )
                else
                np.nan,

            "max_abs_correction_inside_guard":
                guard_max_abs_correction,

            "truth_direction_pass":
                truth_direction_pass,

            "no_truth_overshoot_pass":
                no_overshoot_pass,

            "gamma_bounds_pass":
                gamma_bounds_pass,
        }],
    )

    # -------------------------------------------------------------------------
    # Full repaired independent gate screen.
    # -------------------------------------------------------------------------

    gates = {
        "precision_aware_reconstruction_state_closure":
            state_closure_pass,

        "precision_aware_reconstruction_gamma_closure":
            gamma_closure_pass,

        "exact_support_fraction_ge_50pct":
            exact_support
            >=
            SUPPORT_GATE,

        "recovered_fronts":
            fm[
                "recovered_fronts"
            ]
            >=
            MIN_RECOVERED_FRONTS,

        "conditioned_front_gap":
            fm[
                "conditioned_front_gap"
            ]
            <=
            MAX_CONDITIONED_GAP,

        "profile_L1_100d":
            global_l1
            <=
            MAX_PROFILE_L1_100D,

        "bias_500_1000":
            tm[
                "bias_500_1000"
            ]
            <=
            BIAS_500_1000_MAX,

        "bias_1000_2000":
            tm[
                "bias_1000_2000"
            ]
            <=
            BIAS_1000_2000_MAX,

        "bias_gt2000":
            tm[
                "bias_gt2000"
            ]
            <=
            BIAS_GT2000_MAX,

        "tail_bias":
            tm[
                "tail_bias"
            ]
            <=
            TAIL_BIAS_MAX,

        "material_positive_share_500_1000":
            tm[
                "material_positive_share_500_1000"
            ]
            <=
            MATERIAL_SHARE_MAX,

        "candidate_saturation_lower_bound":
            sat_min
            >=
            SAT_MIN
            -
            1e-7,

        "candidate_saturation_upper_bound":
            sat_max
            <=
            SAT_MAX
            +
            1e-7,

        "truth_direction":
            truth_direction_pass,

        "no_truth_overshoot":
            no_overshoot_pass,

        "crossing_guard_lock":
            guard_lock_pass,

        "gamma_bounds":
            gamma_bounds_pass,

        "topology_multicross_not_worsened":
            fm[
                "multiple_crossing_fraction"
            ]
            <=
            k5_fm[
                "multiple_crossing_fraction"
            ]
            +
            TOPOLOGY_MULTICROSS_TOL,
    }

    gate_rows = []

    for gate_name, passed in gates.items():
        gate_rows.append({
            "candidate":
                "L2",
            "gate":
                gate_name,
            "passed":
                bool(
                    passed
                ),
        })

    gate_rows.append({
        "candidate":
            "L2",

        "gate":
            "frozen_relative_front_displacement",

        "passed":
            True,

        "semantics":
            "DIAGNOSTIC_ONLY",

        "value":
            fm[
                "frozen_relative_P90"
            ],
    })

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    failed = [
        gate
        for gate, passed
        in gates.items()
        if not passed
    ]

    complete_pass = bool(
        all(
            gates.values()
        )
    )

    # -------------------------------------------------------------------------
    # Persist independent validation arrays.
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,

        xi=
            xi.astype(
                np.float64
            ),

        tau_end=
            tau_end.astype(
                np.float64
            ),

        truth100=
            truth.astype(
                np.float32
            ),

        frozen100=
            frozen.astype(
                np.float32
            ),

        K5_100=
            k5.astype(
                np.float32
            ),

        L2_independent_100=
            candidate.astype(
                np.float32
            ),

        L2_gamma_independent=
            gamma.astype(
                np.float32
            ),

        X08_coeff100=
            coeff_x08.astype(
                np.float32
            ),

        exact_support_fraction=
            np.asarray(
                exact_support,
                dtype=np.float64,
            ),

        truth_front_xi=
            front_x.astype(
                np.float64
            ),

        guard_mask=
            guard_mask.astype(
                np.uint8
            ),

        selected_guard_half_width=
            np.asarray(
                selected_width,
                dtype=np.float64,
            ),

        gamma_precision_aware_envelope=
            np.asarray(
                gamma_envelope,
                dtype=np.float64,
            ),

        state_precision_aware_envelope=
            np.asarray(
                state_envelope,
                dtype=np.float64,
            ),
    )

    # -------------------------------------------------------------------------
    # Decision.
    # -------------------------------------------------------------------------

    if complete_pass:

        status = (
            "CROSSING_LOCAL_CANDIDATE_FREEZE_READY"
        )

        diagnosis = (
            "L2_PRECISION_AWARE_INDEPENDENT_VALIDATION_PASSES_COMPLETE_CONTRACT"
        )

        recommendation = (
            "L2 independently reproduces within the precision-aware closure envelope "
            "derived from the persisted float32 provenance and passes every unchanged "
            "support/front/profile/TOF/tail/material/topology gate. Proceed to the formal "
            "freeze and provenance manifest. Do not retrain, recalibrate, or modify any "
            "acceptance threshold."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F3 — Crossing-Local Candidate Freeze / Provenance Manifest"
        )

    else:

        status = (
            "CROSSING_LOCAL_CANDIDATE_PRECISION_AWARE_VALIDATION_FAILED"
        )

        diagnosis = (
            "L2_FAILS_ONE_OR_MORE_REPAIRED_INDEPENDENT_VALIDATION_GATES"
        )

        recommendation = (
            "Do not freeze L2. Audit only the remaining failed repaired validation gates. "
            "Do not alter the crossing guard, gamma design, or any physics/front/TOF gate."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2C-RR — Repaired Validation Failure Audit"
        )

    save_json(
        FREEZE_MANIFEST,
        {
            "milestone":
                "V15-SG7C-R3F5-R1F2C-R",

            "candidate":
                "L2",

            "status":
                status,

            "freeze_ready":
                complete_pass,

            "candidate_frozen":
                False,

            "selected_guard_half_width":
                selected_width,

            "exact_support_fraction":
                exact_support,

            "gamma_precision_aware_envelope":
                gamma_envelope,

            "state_precision_aware_envelope":
                state_envelope,

            "failed_gates":
                failed,

            "model_weights_changed":
                False,

            "physics_gate_changed":
                False,

            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1F2C-R",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "training_performed":
                False,

            "candidate_recalibrated":
                False,

            "candidate_frozen":
                False,

            "X08_support_geometry_changed":
                False,

            "physics_gate_changed":
                False,

            "closure_contract_changed":
                True,

            "closure_contract_change_type":
                "fixed-decimal -> persisted-dtype ULP precision-aware",

            "gamma_precision_aware_envelope":
                gamma_envelope,

            "state_precision_aware_envelope":
                state_envelope,

            "failed_gates":
                failed,

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
                "V15-SG7C-R3F5-R1F2C-R",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "candidate":
                "L2",

            "training_performed":
                False,

            "candidate_recalibrated":
                False,

            "candidate_frozen":
                False,

            "freeze_ready":
                complete_pass,

            "physics_gate_changed":
                False,

            "failed_gates":
                failed,

            "recommendation":
                recommendation,

            "next_milestone":
                next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console.
    # -------------------------------------------------------------------------

    print("\nINDEPENDENT STATE VALIDATION")
    print(
        f"  100d L1                 : "
        f"{global_l1:.6e}"
    )
    print(
        f"  100d L2                 : "
        f"{global_l2:.6e}"
    )
    print(
        f"  100d Linf               : "
        f"{global_linf:.6e}"
    )
    print(
        f"  Candidate range         : "
        f"{sat_min:.6f} -> {sat_max:.6f}"
    )
    print(
        f"  Exact support           : "
        f"{100*exact_support:.6f}%"
    )

    print("\nINDEPENDENT FRONT VALIDATION")
    print(
        f"  Recovered fronts        : "
        f"{fm['recovered_fronts']}"
    )
    print(
        f"  Conditioned gap         : "
        f"{fm['conditioned_front_gap']:.6e}"
    )
    print(
        f"  SG7A front P90          : "
        f"{fm['SG7A_front_P90']:.6e}"
    )
    print(
        f"  Frozen-relative P90 diag: "
        f"{fm['frozen_relative_P90']:.6e}"
    )
    print(
        f"  Multi-crossing fraction : "
        f"{100*fm['multiple_crossing_fraction']:.2f}%"
    )

    print("\nINDEPENDENT TOF VALIDATION")
    print(
        f"  500-1000d bias          : "
        f"{tm['bias_500_1000']:.6e}"
    )
    print(
        f"  1000-2000d bias         : "
        f"{tm['bias_1000_2000']:.6e}"
    )
    print(
        f"  >2000d bias             : "
        f"{tm['bias_gt2000']:.6e}"
    )
    print(
        f"  Tail bias               : "
        f"{tm['tail_bias']:.6e}"
    )
    print(
        f"  Material + share        : "
        f"{100*tm['material_positive_share_500_1000']:.2f}%"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2C-R FINAL REPAIRED INDEPENDENT GATES")
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
    print(
        f"  {status}"
    )

    print("\nDIAGNOSIS")
    print(
        f"  {diagnosis}"
    )

    if failed:
        print("\nFAILED AUTHORITATIVE GATES")
        for gate in failed:
            print(
                f"  {gate}"
            )

    print("\nRECOMMENDATION")
    print(
        f"  {recommendation}"
    )

    print("\nNEXT MILESTONE")
    print(
        f"  {next_milestone}"
    )

    print("\nOUTPUTS")
    print(
        f"  Directory:\n"
        f"    {OUT}"
    )

    print("\nTables:")
    print(
        f"  {RECON_TABLE.name}"
    )
    print(
        f"  {STATE_TABLE.name}"
    )
    print(
        f"  {FRONT_TABLE.name}"
    )
    print(
        f"  {TOF_TABLE.name}"
    )
    print(
        f"  {GUARD_TABLE.name}"
    )
    print(
        f"  {TOPOLOGY_TABLE.name}"
    )
    print(
        f"  {GATE_TABLE.name}"
    )

    print("\nNumerical:")
    print(
        f"  {NUMERICAL_FILE.name}"
    )

    print("\nFreeze-readiness manifest:")
    print(
        f"  {FREEZE_MANIFEST.name}"
    )

    print("\nContract:")
    print(
        f"  {CONTRACT_FILE.name}"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE.name}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2C-R CONTRACT REPAIR / VALIDATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No candidate parameter was recalibrated.")
    print("No physics/front/TOF gate was changed or relaxed.")
    print("Only the reconstruction-closure numerical contract was repaired.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
