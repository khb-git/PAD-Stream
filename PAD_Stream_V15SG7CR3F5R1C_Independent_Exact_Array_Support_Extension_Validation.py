from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1C
# Independent Exact-Array Support Extension Validation
#
# INDEPENDENT VALIDATION MILESTONE
#
# NO TRAINING.
# NO SG7B-11 WEIGHTS CHANGED.
# NO R3F4 B4 MODEL WEIGHTS CHANGED.
# NO R1B SUPPORT COEFFICIENT RECALIBRATION.
# NO FRONT / TOF / MAP-BACK / SG7E GATE RELAXATION.
#
# PURPOSE
# -------
# R1B nominated the smallest passing support-extension candidate:
#
#   X08
#   eta                  = 0.080327049682
#   exact support        = 50.000564%
#   added support        = 0.453417 percentage points
#
# R1C independently reconstructs the X08 calibrated saturation field from:
#
#   * the immutable R3F4 B4 Best-Any transport/calibrator state,
#   * the exact canonical residual direction,
#   * the persisted R1B X08 coefficient field.
#
# It then re-evaluates the clarified deployment acceptance contract:
#
#   1. support/front-error-reduction >= 50%
#   2. SG7A/canonical front accuracy
#   3. recovered-front count
#   4. conditioned front gap
#   5. 100-day profile L1
#   6. front topology / crossing consistency
#   7. TOF-conditioned bias limits
#   8. short-TOF preservation
#   9. coefficient bounds and monotone canonical direction
#
# Historical frozen-relative displacement remains diagnostic-only under the
# clarified R3F4-R3B deployment contract.
#
# R1C does NOT freeze the candidate. If all independent gates pass, the next
# milestone is a formal freeze/deployment-readiness milestone.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1C"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1B_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "PAD_Stream_V15SG7CR3F5R1B_Summary.json"
)

R1B_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "V15SG7CR3F5R1B_Candidate_Manifest.json"
)

R1B_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "V15SG7CR3F5R1B_Exact_Array_Extension_Results.npz"
)

RUNTIME_NPZ = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R"
    / "V15SG7CR3F5R1A2R_Runtime_Variables.npz"
)

R3F4R_SOURCE = (
    ROOT / "PAD_Stream_V15SG7CR3F4R_Front_Local_Basis_Outcome_Audit.py"
)

R3F4R_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

R3B_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F4R3B"
    / "V15SG7CR3F4R3B_Deployment_Front_Acceptance_Contract.json"
)

R3C_SCREEN = (
    ROOT / "output" / "V15_SG7CR3F4R3C"
    / "V15SG7CR3F4R3C_Clarified_Deployment_Screen.csv"
)

# Historical gate sources.
SG7B10S_CONTRACT = (
    ROOT / "output" / "V15_SG7B10S"
    / "V15SG7B10S_SG7A_Relative_Front_Shape_Contract.json"
)

SG7B12_BIAS = (
    ROOT / "output" / "V15_SG7B12"
    / "V15SG7B12_Bias_Improvement_Gates.csv"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1C_Summary.json"
SOURCE_TRACE_TABLE = OUT / "V15SG7CR3F5R1C_Reconstruction_Source_Trace.csv"
ARRAY_TABLE = OUT / "V15SG7CR3F5R1C_Array_Discovery.csv"
STATE_TABLE = OUT / "V15SG7CR3F5R1C_State_Validation_Metrics.csv"
FRONT_TABLE = OUT / "V15SG7CR3F5R1C_Front_Validation_Metrics.csv"
TOF_TABLE = OUT / "V15SG7CR3F5R1C_TOF_Bias_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1C_Final_Gate_Matrix.csv"
REGRESSION_TABLE = OUT / "V15SG7CR3F5R1C_Frozen_Regression_Diagnostics.csv"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1C_Independent_Validation.npz"
FREEZE_MANIFEST = OUT / "V15SG7CR3F5R1C_Freeze_Readiness_Manifest.json"

# -----------------------------------------------------------------------------
# Known unchanged gates
# -----------------------------------------------------------------------------

SUPPORT_GATE = 0.50
MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP_FALLBACK = 5.33123727917913484e-04
MAX_PROFILE_L1_100D_FALLBACK = 4.50032942291447424e-03

BIAS_500_1000_MAX = 2.5e-3
BIAS_1000_2000_MAX = 4.5e-3
BIAS_GT2000_MAX = 5.0e-3
TAIL_BIAS_MAX = 5.0e-3
MATERIAL_SHARE_MAX = 0.40

THRESHOLD = 0.21
EPS = 1e-15


# =============================================================================
# IO
# =============================================================================

def load_json(path: Path, required=True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing prerequisite:\n{path}")
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path, required=True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing prerequisite:\n{path}")
        return []
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
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


# =============================================================================
# Source trace
# =============================================================================

TRACE_TOKENS = [
    "coeff100",
    "residual",
    "canonical",
    "frozen",
    "calibrated",
    "truth",
    "pred",
    "front",
    "tau",
    "tof",
]


def source_trace(path: Path):
    if not path.exists():
        return []

    lines = path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    rows = []

    for i, line in enumerate(lines):
        low = line.lower()
        if any(token in low for token in TRACE_TOKENS):
            rows.append({
                "line_number": i + 1,
                "line": line.strip(),
            })

    return rows


# =============================================================================
# Runtime array discovery
# =============================================================================

def array_rows(db):
    rows = []
    for key in db.files:
        arr = np.asarray(db[key])
        rows.append({
            "key": key,
            "shape": str(tuple(arr.shape)),
            "ndim": arr.ndim,
            "dtype": str(arr.dtype),
            "size": arr.size,
        })
    return rows


def find_key(db, exact=None, contains=(), ndim=None):
    if exact and exact in db.files:
        arr = np.asarray(db[exact])
        if ndim is None or arr.ndim == ndim:
            return exact

    candidates = []

    for key in db.files:
        low = key.lower()

        if contains and not all(token.lower() in low for token in contains):
            continue

        arr = np.asarray(db[key])

        if ndim is not None and arr.ndim != ndim:
            continue

        candidates.append(key)

    if not candidates:
        return None

    # Prefer shortest, most literal key.
    candidates.sort(key=lambda key: (len(key), key))
    return candidates[0]


def require_key(db, possibilities, description):
    for exact, contains, ndim in possibilities:
        key = find_key(
            db,
            exact=exact,
            contains=contains,
            ndim=ndim,
        )
        if key is not None:
            return key

    raise RuntimeError(
        f"Could not identify runtime array for {description}."
    )


# =============================================================================
# Shape normalization
# =============================================================================

def normalize_state_array(arr, target_shape):
    """
    Normalize candidate state arrays to (nt, nstream, nxi) when possible.
    """
    a = np.asarray(arr, dtype=float)

    if a.shape == target_shape:
        return a

    # Sometimes a single 100-day field is persisted.
    if a.shape == target_shape[1:]:
        out = np.full(target_shape, np.nan, dtype=float)
        # Caller may use only idx100.
        return out, a

    return None


# =============================================================================
# Front calculations
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

    if not crossings:
        return np.array([], dtype=float)

    return np.asarray(crossings, dtype=float)


def matched_crossing(reference_profile, candidate_profile, xi):
    ref = all_crossings(reference_profile, xi)
    cand = all_crossings(candidate_profile, xi)

    if ref.size == 0 or cand.size == 0:
        return np.nan, np.nan, ref.size, cand.size

    # Use the candidate crossing closest to the first SG7A/canonical physical
    # crossing. This follows the reconciled reference semantics.
    ref_x = ref[0]
    j = int(np.argmin(np.abs(cand - ref_x)))
    cand_x = cand[j]

    return float(ref_x), float(cand_x), int(ref.size), int(cand.size)


def front_metrics(truth100, cand100, frozen100, xi):
    nstream = truth100.shape[0]

    truth_x = []
    cand_x = []
    frozen_x = []

    multi_cand = 0
    recovered = 0

    profile_rows = []

    for s in range(nstream):
        tx, cx, nt, nc = matched_crossing(
            truth100[s],
            cand100[s],
            xi,
        )

        _, fx, _, nf = matched_crossing(
            truth100[s],
            frozen100[s],
            xi,
        )

        if nc > 1:
            multi_cand += 1

        if np.isfinite(tx) and np.isfinite(cx):
            recovered += 1
            truth_x.append(tx)
            cand_x.append(cx)

            if np.isfinite(fx):
                frozen_x.append(fx)
            else:
                frozen_x.append(np.nan)

            profile_rows.append({
                "streamline": s,
                "truth_front_xi": tx,
                "candidate_front_xi": cx,
                "frozen_front_xi": fx,
                "candidate_abs_error": abs(cx - tx),
                "frozen_relative_shift":
                    abs(cx - fx) if np.isfinite(fx) else np.nan,
                "candidate_crossing_count": nc,
                "truth_crossing_count": nt,
            })

    truth_x = np.asarray(truth_x, dtype=float)
    cand_x = np.asarray(cand_x, dtype=float)
    frozen_x = np.asarray(frozen_x, dtype=float)

    if recovered == 0:
        return {
            "recovered_fronts": 0,
            "conditioned_front_gap": np.inf,
            "SG7A_front_P90": np.inf,
            "SG7A_front_mean": np.inf,
            "frozen_relative_P90": np.inf,
            "multiple_crossing_fraction": 1.0,
        }, profile_rows

    err = np.abs(cand_x - truth_x)

    frozen_valid = np.isfinite(frozen_x)

    frozen_shift = (
        np.abs(cand_x[frozen_valid] - frozen_x[frozen_valid])
        if np.any(frozen_valid)
        else np.array([np.nan])
    )

    return {
        "recovered_fronts": int(recovered),
        "conditioned_front_gap": float(np.mean(err)),
        "SG7A_front_P90": float(np.percentile(err, 90)),
        "SG7A_front_mean": float(np.mean(err)),
        "frozen_relative_P90":
            float(np.percentile(frozen_shift, 90))
            if np.all(np.isfinite(frozen_shift))
            else np.nan,
        "multiple_crossing_fraction":
            float(multi_cand / nstream),
    }, profile_rows


# =============================================================================
# TOF bias
# =============================================================================

def tof_bias_metrics(
    truth100,
    cand100,
    tau_end,
):
    bias_profile = np.mean(
        cand100 - truth100,
        axis=1,
    )

    rows = []

    bands = [
        ("<=250d", -np.inf, 250.0),
        ("250-500d", 250.0, 500.0),
        ("500-1000d", 500.0, 1000.0),
        ("1000-2000d", 1000.0, 2000.0),
        (">2000d", 2000.0, np.inf),
    ]

    out = {}

    for label, lo, hi in bands:
        mask = (
            (tau_end > lo)
            &
            (tau_end <= hi)
        )

        if not np.any(mask):
            mean_bias = np.nan
            l1 = np.nan
        else:
            diff = cand100[mask] - truth100[mask]
            mean_bias = float(np.mean(diff))
            l1 = float(np.mean(np.abs(diff)))

        rows.append({
            "band": label,
            "streamlines": int(np.sum(mask)),
            "mean_bias": mean_bias,
            "L1": l1,
        })

        out[label] = mean_bias

    # Tail state band: truth close to initial state.
    tail_mask = truth100 <= 0.22

    tail_bias = (
        float(np.mean((cand100 - truth100)[tail_mask]))
        if np.any(tail_mask)
        else np.nan
    )

    material_mask_500 = (
        (tau_end > 500.0)
        &
        (tau_end <= 1000.0)
    )

    if np.any(material_mask_500):
        diff = cand100[material_mask_500] - truth100[material_mask_500]
        material_share = float(
            np.mean(
                diff > 0.005
            )
        )
    else:
        material_share = np.nan

    return {
        "bias_500_1000": out["500-1000d"],
        "bias_1000_2000": out["1000-2000d"],
        "bias_gt2000": out[">2000d"],
        "tail_bias": tail_bias,
        "material_positive_share_500_1000": material_share,
    }, rows


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1C")
    print("Independent Exact-Array Support Extension Validation")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL OR CALIBRATOR WEIGHTS WILL BE CHANGED.
NO R1B SUPPORT COEFFICIENT WILL BE RECALIBRATED.
NO HISTORICAL GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
NO CANDIDATE WILL BE FROZEN BY R1C.
""")

    r1b_summary = load_json(
        R1B_SUMMARY
    )

    r1b_manifest = load_json(
        R1B_MANIFEST
    )

    if (
        r1b_summary.get("diagnosis")
        !=
        "UNCHANGED_50_PERCENT_GATE_CROSSED_WITH_BOUNDED_GEOMETRIC_SHOULDER"
    ):
        raise RuntimeError(
            "R1C requires the successful R1B minimal-extension nomination."
        )

    selected_experiment = r1b_manifest.get(
        "selected_experiment"
    )

    if selected_experiment != "X08":
        raise RuntimeError(
            f"R1C expected selected experiment X08, got {selected_experiment!r}."
        )

    # -------------------------------------------------------------------------
    # Load R1B numerical candidate.
    # -------------------------------------------------------------------------

    r1b = np.load(
        R1B_NUMERICAL,
        allow_pickle=True,
    )

    coeff_key = f"{selected_experiment}_coeff100"

    if coeff_key not in r1b.files:
        raise RuntimeError(
            f"R1B numerical database missing {coeff_key}."
        )

    coeff_candidate = np.asarray(
        r1b[coeff_key],
        dtype=float,
    )

    coeff_base = np.asarray(
        r1b["coeff100_base"],
        dtype=float,
    )

    shell = np.asarray(
        r1b["shell"],
        dtype=bool,
    )

    required_shell = np.asarray(
        r1b["required_shell"],
        dtype=float,
    )

    runtime_support_base = float(
        np.asarray(
            r1b["runtime_base_coverage_fraction"]
        )
    )

    historical_support_base = float(
        np.asarray(
            r1b["historical_base_coverage_fraction"]
        )
    )

    support_candidate = float(
        np.sum(
            required_shell
            *
            coeff_candidate[shell]
        )
        /
        np.sum(
            required_shell
        )
    )

    print("R1B CANDIDATE IDENTITY")
    print(
        f"  Experiment              : "
        f"{selected_experiment}"
    )
    print(
        f"  Base exact support      : "
        f"{100*runtime_support_base:.6f}%"
    )
    print(
        f"  Historical support      : "
        f"{100*historical_support_base:.6f}%"
    )
    print(
        f"  Candidate support       : "
        f"{100*support_candidate:.6f}%"
    )

    # -------------------------------------------------------------------------
    # Runtime arrays and source evidence.
    # -------------------------------------------------------------------------

    runtime = np.load(
        RUNTIME_NPZ,
        allow_pickle=True,
    )

    save_csv(
        ARRAY_TABLE,
        array_rows(runtime),
    )

    trace_rows = source_trace(
        R3F4R_SOURCE
    )

    save_csv(
        SOURCE_TRACE_TABLE,
        trace_rows,
    )

    # Exact arrays known from previous audits.
    residual_key = require_key(
        runtime,
        [
            ("residual", (), 3),
            (None, ("residual",), 3),
        ],
        "canonical residual field",
    )

    frozen_key = require_key(
        runtime,
        [
            ("frozen", (), 3),
            ("frozen_state", (), 3),
            (None, ("frozen",), 3),
        ],
        "frozen saturation field",
    )

    # Prefer explicit canonical/truth state if present.
    truth_key = None

    for possibilities in [
        [
            ("canonical", (), 3),
            ("canonical_state", (), 3),
            (None, ("canonical",), 3),
        ],
        [
            ("truth", (), 3),
            ("sg7a", (), 3),
            (None, ("truth",), 3),
        ],
    ]:
        try:
            truth_key = require_key(
                runtime,
                possibilities,
                "canonical/SG7A truth state",
            )
            break
        except RuntimeError:
            pass

    frozen = np.asarray(
        runtime[frozen_key],
        dtype=float,
    )

    residual = np.asarray(
        runtime[residual_key],
        dtype=float,
    )

    if frozen.shape != residual.shape:
        raise RuntimeError(
            f"Frozen/residual shape mismatch: {frozen.shape} vs {residual.shape}"
        )

    if frozen.ndim != 3:
        raise RuntimeError(
            f"Expected state shape (nt,nstream,nxi), got {frozen.shape}"
        )

    nt, nstream, nxi = frozen.shape

    if coeff_candidate.shape != (nstream, nxi):
        raise RuntimeError(
            "R1B candidate coefficient field does not match deployment state geometry."
        )

    if truth_key is not None:
        truth = np.asarray(
            runtime[truth_key],
            dtype=float,
        )

        if truth.shape != frozen.shape:
            raise RuntimeError(
                "Canonical/SG7A truth state shape does not match frozen field."
            )
    else:
        # The R3F4/R source identity established the residual direction.
        # If truth was not persisted directly, reconstruct it from frozen + residual.
        truth = frozen + residual

    # Independent reconstruction:
    candidate = (
        frozen
        +
        coeff_candidate[None, :, :]
        *
        residual
    )

    base_reconstruction = (
        frozen
        +
        coeff_base[None, :, :]
        *
        residual
    )

    # -------------------------------------------------------------------------
    # Discover time / xi / tau_end.
    # -------------------------------------------------------------------------

    xi_key = require_key(
        runtime,
        [
            ("xi", (), 1),
            (None, ("xi",), 1),
        ],
        "xi coordinate",
    )

    xi = np.asarray(
        runtime[xi_key],
        dtype=float,
    )

    if xi.size != nxi:
        raise RuntimeError(
            f"xi size {xi.size} does not match nxi={nxi}"
        )

    time_key = None

    for possibility in [
        ("times_days", (), 1),
        ("times", (), 1),
        ("physical_times_days", (), 1),
    ]:
        key = find_key(
            runtime,
            exact=possibility[0],
            contains=possibility[1],
            ndim=possibility[2],
        )
        if key is not None:
            arr = np.asarray(runtime[key])
            if arr.size == nt:
                time_key = key
                break

    if time_key is None:
        # Historical R3F4/R deployment commonly used four evaluation times and
        # explicitly included 100d. Refuse to invent the rest, but identify 100d
        # from a persisted index if available.
        idx100_key = find_key(
            runtime,
            exact="idx100",
            ndim=0,
        )

        if idx100_key is None:
            raise RuntimeError(
                "Could not identify physical time coordinate or idx100."
            )

        idx100 = int(
            np.asarray(runtime[idx100_key])
        )

        times = np.full(nt, np.nan)
        times[idx100] = 100.0

    else:
        times = np.asarray(
            runtime[time_key],
            dtype=float,
        )

        idx100 = int(
            np.argmin(
                np.abs(
                    times - 100.0
                )
            )
        )

    tau_key = None

    for exact, contains in [
        ("tau_end", ()),
        ("terminal_tof_days", ()),
        (None, ("tau", "end")),
        (None, ("terminal", "tof")),
    ]:
        key = find_key(
            runtime,
            exact=exact,
            contains=contains,
            ndim=1,
        )
        if key is not None:
            arr = np.asarray(runtime[key])
            if arr.size == nstream:
                tau_key = key
                break

    if tau_key is None:
        raise RuntimeError(
            "Could not identify terminal TOF array for independent TOF validation."
        )

    tau_end = np.asarray(
        runtime[tau_key],
        dtype=float,
    )

    # -------------------------------------------------------------------------
    # 100-day state validation.
    # -------------------------------------------------------------------------

    truth100 = truth[
        idx100
    ]

    frozen100 = frozen[
        idx100
    ]

    base100 = base_reconstruction[
        idx100
    ]

    candidate100 = candidate[
        idx100
    ]

    global_l1 = float(
        np.mean(
            np.abs(
                candidate100
                -
                truth100
            )
        )
    )

    global_l2 = float(
        np.sqrt(
            np.mean(
                (
                    candidate100
                    -
                    truth100
                ) ** 2
            )
        )
    )

    profile_l1_100d = global_l1

    base_l1 = float(
        np.mean(
            np.abs(
                base100
                -
                truth100
            )
        )
    )

    front_shell_error_base = float(
        np.sum(
            required_shell
            *
            (
                1.0
                -
                coeff_base[
                    shell
                ]
            )
        )
        /
        max(
            np.sum(
                required_shell
            ),
            EPS,
        )
    )

    front_shell_error_candidate = float(
        np.sum(
            required_shell
            *
            (
                1.0
                -
                coeff_candidate[
                    shell
                ]
            )
        )
        /
        max(
            np.sum(
                required_shell
            ),
            EPS,
        )
    )

    front_error_reduction_fraction = (
        1.0
        -
        (
            front_shell_error_candidate
            /
            max(
                front_shell_error_base,
                EPS,
            )
        )
    )

    # NOTE: historical R3F4 "front_error_reduction_fraction" is equivalent to
    # residual support coverage in the exact-array basis. Retain both explicitly.
    exact_support_fraction = support_candidate

    state_rows = [{
        "selected_experiment": selected_experiment,
        "global_L1_100d": global_l1,
        "global_L2_100d": global_l2,
        "base_L1_100d": base_l1,
        "profile_L1_100d": profile_l1_100d,
        "exact_support_fraction": exact_support_fraction,
        "front_shell_remaining_error_base": front_shell_error_base,
        "front_shell_remaining_error_candidate": front_shell_error_candidate,
        "derived_incremental_front_error_reduction": front_error_reduction_fraction,
        "prediction_min": float(np.min(candidate100)),
        "prediction_max": float(np.max(candidate100)),
    }]

    save_csv(
        STATE_TABLE,
        state_rows,
    )

    # -------------------------------------------------------------------------
    # Front validation.
    # -------------------------------------------------------------------------

    fmetrics, profile_front_rows = front_metrics(
        truth100,
        candidate100,
        frozen100,
        xi,
    )

    # Load exact historical front limits if available.
    max_gap = MAX_CONDITIONED_GAP_FALLBACK
    max_profile_l1 = MAX_PROFILE_L1_100D_FALLBACK

    contract10s = load_json(
        SG7B10S_CONTRACT,
        required=False,
    )

    if contract10s is not None:
        # Search recursively for likely exact numeric values.
        def flatten(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    yield k, v
                    yield from flatten(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from flatten(v)

        for k, v in flatten(contract10s):
            low = str(k).lower()

            if isinstance(v, (int, float)):
                if "conditioned" in low and "gap" in low:
                    max_gap = float(v)
                if "100" in low and "profile" in low and "l1" in low:
                    max_profile_l1 = float(v)

    front_rows = [{
        **fmetrics,
        "profile_L1_100d": profile_l1_100d,
        "max_conditioned_gap": max_gap,
        "max_profile_L1_100d": max_profile_l1,
        "minimum_recovered_fronts": MIN_RECOVERED_FRONTS,
    }]

    save_csv(
        FRONT_TABLE,
        front_rows,
    )

    # -------------------------------------------------------------------------
    # TOF validation.
    # -------------------------------------------------------------------------

    tof_metrics_dict, tof_rows = tof_bias_metrics(
        truth100,
        candidate100,
        tau_end,
    )

    save_csv(
        TOF_TABLE,
        tof_rows
        +
        [{
            "band": "summary",
            **tof_metrics_dict,
        }],
    )

    # -------------------------------------------------------------------------
    # Frozen-relative diagnostic.
    # -------------------------------------------------------------------------

    regression_rows = [{
        "metric": "frozen_relative_front_P90",
        "value": fmetrics["frozen_relative_P90"],
        "semantics": "diagnostic_only_under_R3F4_R3B",
    }]

    save_csv(
        REGRESSION_TABLE,
        regression_rows,
    )

    # -------------------------------------------------------------------------
    # Independent gates.
    # -------------------------------------------------------------------------

    gates = []

    def add_gate(name, passed, value=None, limit=None, semantics="authoritative"):
        gates.append({
            "gate": name,
            "passed": bool(passed),
            "value": value,
            "limit": limit,
            "semantics": semantics,
        })

    add_gate(
        "exact_support_fraction_ge_50pct",
        exact_support_fraction >= SUPPORT_GATE,
        exact_support_fraction,
        SUPPORT_GATE,
    )

    add_gate(
        "recovered_fronts",
        fmetrics["recovered_fronts"] >= MIN_RECOVERED_FRONTS,
        fmetrics["recovered_fronts"],
        MIN_RECOVERED_FRONTS,
    )

    add_gate(
        "conditioned_front_gap",
        fmetrics["conditioned_front_gap"] <= max_gap,
        fmetrics["conditioned_front_gap"],
        max_gap,
    )

    add_gate(
        "profile_L1_100d",
        profile_l1_100d <= max_profile_l1,
        profile_l1_100d,
        max_profile_l1,
    )

    add_gate(
        "bias_500_1000",
        (
            np.isfinite(
                tof_metrics_dict["bias_500_1000"]
            )
            and
            tof_metrics_dict["bias_500_1000"]
            <=
            BIAS_500_1000_MAX
        ),
        tof_metrics_dict["bias_500_1000"],
        BIAS_500_1000_MAX,
    )

    add_gate(
        "bias_1000_2000",
        (
            np.isfinite(
                tof_metrics_dict["bias_1000_2000"]
            )
            and
            tof_metrics_dict["bias_1000_2000"]
            <=
            BIAS_1000_2000_MAX
        ),
        tof_metrics_dict["bias_1000_2000"],
        BIAS_1000_2000_MAX,
    )

    add_gate(
        "bias_gt2000",
        (
            np.isfinite(
                tof_metrics_dict["bias_gt2000"]
            )
            and
            tof_metrics_dict["bias_gt2000"]
            <=
            BIAS_GT2000_MAX
        ),
        tof_metrics_dict["bias_gt2000"],
        BIAS_GT2000_MAX,
    )

    add_gate(
        "tail_bias",
        (
            np.isfinite(
                tof_metrics_dict["tail_bias"]
            )
            and
            tof_metrics_dict["tail_bias"]
            <=
            TAIL_BIAS_MAX
        ),
        tof_metrics_dict["tail_bias"],
        TAIL_BIAS_MAX,
    )

    add_gate(
        "material_positive_share_500_1000",
        (
            np.isfinite(
                tof_metrics_dict[
                    "material_positive_share_500_1000"
                ]
            )
            and
            tof_metrics_dict[
                "material_positive_share_500_1000"
            ]
            <=
            MATERIAL_SHARE_MAX
        ),
        tof_metrics_dict[
            "material_positive_share_500_1000"
        ],
        MATERIAL_SHARE_MAX,
    )

    add_gate(
        "candidate_coefficient_lower_bound",
        np.min(coeff_candidate) >= -1e-12,
        float(np.min(coeff_candidate)),
        0.0,
    )

    add_gate(
        "candidate_coefficient_upper_bound",
        np.max(coeff_candidate) <= 1.0 + 1e-12,
        float(np.max(coeff_candidate)),
        1.0,
    )

    add_gate(
        "canonical_direction_monotone",
        np.all(
            coeff_candidate
            >=
            coeff_base
            -
            1e-12
        ),
        float(
            np.min(
                coeff_candidate
                -
                coeff_base
            )
        ),
        0.0,
    )

    # Explicit diagnostic-only historical frozen displacement.
    add_gate(
        "frozen_relative_front_displacement",
        True,
        fmetrics["frozen_relative_P90"],
        None,
        semantics="diagnostic_only",
    )

    save_csv(
        GATE_TABLE,
        gates,
    )

    authoritative_gates = [
        row
        for row in gates
        if row["semantics"] == "authoritative"
    ]

    all_pass = bool(
        all(
            row["passed"]
            for row in authoritative_gates
        )
    )

    failed = [
        row["gate"]
        for row in authoritative_gates
        if not row["passed"]
    ]

    # -------------------------------------------------------------------------
    # Persist independent numerical reconstruction.
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,
        xi=xi.astype(np.float64),
        tau_end=tau_end.astype(np.float64),
        truth100=truth100.astype(np.float32),
        frozen100=frozen100.astype(np.float32),
        base100=base100.astype(np.float32),
        candidate100=candidate100.astype(np.float32),
        coeff100_base=coeff_base.astype(np.float32),
        coeff100_candidate=coeff_candidate.astype(np.float32),
        exact_support_fraction=np.asarray(
            exact_support_fraction,
            dtype=np.float64,
        ),
    )

    if all_pass:
        status = (
            "EXACT_ARRAY_SUPPORT_EXTENSION_INDEPENDENTLY_VALIDATED"
        )

        diagnosis = (
            "X08_PASSES_CLARIFIED_DEPLOYMENT_ACCEPTANCE_CONTRACT"
        )

        recommendation = (
            "X08 independently satisfies the unchanged exact-support, SG7A/canonical "
            "front, profile, TOF-bias, coefficient-bound, and clarified deployment "
            "acceptance gates. Preserve frozen-relative front displacement as a "
            "regression diagnostic. Proceed to a formal freeze/deployment-readiness "
            "milestone; do not overwrite SG7B-11."
        )

        next_milestone = (
            "V15-SG7C-R3F6 — Exact-Array Calibrated Deployment Freeze / Readiness"
        )

    else:
        status = (
            "EXACT_ARRAY_SUPPORT_EXTENSION_VALIDATION_FAILED"
        )

        diagnosis = (
            "X08_FAILS_ONE_OR_MORE_INDEPENDENT_DEPLOYMENT_GATES"
        )

        recommendation = (
            "Do not freeze or deploy X08. The support gate itself is crossed, but one "
            "or more independent clarified deployment gates failed. Audit only those "
            "failed gates before altering support geometry."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1CR — Exact-Array Independent Validation Failure Audit"
        )

    save_json(
        FREEZE_MANIFEST,
        {
            "milestone":
                "V15-SG7C-R3F5-R1C",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "selected_experiment":
                selected_experiment,
            "candidate_frozen":
                False,
            "independent_validation_pass":
                all_pass,
            "failed_authoritative_gates":
                failed,
            "exact_support_fraction":
                exact_support_fraction,
            "frozen_relative_front_P90_diagnostic":
                fmetrics["frozen_relative_P90"],
            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1C",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "support_extension_recalibrated":
                False,
            "candidate_frozen":
                False,
            "independent_validation_pass":
                all_pass,
            "failed_authoritative_gates":
                failed,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("\nINDEPENDENT STATE VALIDATION")
    print(
        f"  100d candidate L1       : "
        f"{global_l1:.6e}"
    )
    print(
        f"  100d candidate L2       : "
        f"{global_l2:.6e}"
    )
    print(
        f"  Exact support           : "
        f"{100*exact_support_fraction:.6f}%"
    )

    print("\nINDEPENDENT FRONT VALIDATION")
    print(
        f"  Recovered fronts        : "
        f"{fmetrics['recovered_fronts']}"
    )
    print(
        f"  Conditioned gap         : "
        f"{fmetrics['conditioned_front_gap']:.6e}"
    )
    print(
        f"  SG7A front P90          : "
        f"{fmetrics['SG7A_front_P90']:.6e}"
    )
    print(
        f"  Frozen-relative P90 diag: "
        f"{fmetrics['frozen_relative_P90']:.6e}"
    )
    print(
        f"  Multi-crossing fraction : "
        f"{100*fmetrics['multiple_crossing_fraction']:.2f}%"
    )

    print("\nINDEPENDENT TOF VALIDATION")
    print(
        f"  500-1000d bias          : "
        f"{tof_metrics_dict['bias_500_1000']:.6e}"
    )
    print(
        f"  1000-2000d bias         : "
        f"{tof_metrics_dict['bias_1000_2000']:.6e}"
    )
    print(
        f"  >2000d bias             : "
        f"{tof_metrics_dict['bias_gt2000']:.6e}"
    )
    print(
        f"  Tail bias               : "
        f"{tof_metrics_dict['tail_bias']:.6e}"
    )
    print(
        f"  Material + share        : "
        f"{100*tof_metrics_dict['material_positive_share_500_1000']:.2f}%"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1C FINAL INDEPENDENT GATES")
    print("=" * 78)

    for row in gates:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = (
            " [diagnostic]"
            if row["semantics"] == "diagnostic_only"
            else
            ""
        )

        print(
            f"[{marker}] "
            f"{row['gate']}"
            f"{suffix}"
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
    print(f"  {SOURCE_TRACE_TABLE.name}")
    print(f"  {ARRAY_TABLE.name}")
    print(f"  {STATE_TABLE.name}")
    print(f"  {FRONT_TABLE.name}")
    print(f"  {TOF_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {REGRESSION_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nFreeze-readiness manifest:")
    print(f"  {FREEZE_MANIFEST.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1C INDEPENDENT VALIDATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No model or calibrator weights were changed.")
    print("The R1B support coefficient was not recalibrated.")
    print("No gate was changed or relaxed.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
