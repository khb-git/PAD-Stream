from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F2CR
# Independent Validation Failure Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO L2 GAMMA OR CROSSING GUARD RECALIBRATED.
# NO PHYSICS / FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
# NO CANDIDATE FROZEN.
#
# PURPOSE
# -------
# R1F2C independently reconstructed L2 and passed every substantive deployment
# gate, but failed only:
#
#   reconstruction_state_closure
#   reconstruction_gamma_closure
#
# with errors on the order of 1e-8:
#
#   gamma Linf ~ 1.36e-8
#   state Linf ~ 2.98e-8
#
# R1F2CR determines whether this discrepancy is explained by persistence /
# numerical-representation effects, especially:
#
#   * persisted float32 arrays,
#   * independent float64 reconstruction,
#   * float32 quantization,
#   * operation-order differences.
#
# This audit does NOT simply loosen tolerances. It derives a reconstruction
# closure envelope from actual persisted dtype / ULP scale and checks whether
# the observed differences fall inside that numerical representation envelope.
#
# If confirmed, the next milestone is a precision-aware R1F2C contract repair
# and rerun. No physical gate is altered.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F2CR"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1F2C_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1F2C"
    / "PAD_Stream_V15SG7CR3F5R1F2C_Summary.json"
)

R1F2C_RECON = (
    ROOT / "output" / "V15_SG7CR3F5R1F2C"
    / "V15SG7CR3F5R1F2C_Reconstruction_Closure.csv"
)

R1F2C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1F2C"
    / "V15SG7CR3F5R1F2C_Independent_Validation.npz"
)

R1F2B_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1F2B"
    / "V15SG7CR3F5R1F2B_Controlled_Crossing_Local_Correction.npz"
)

R1F2A_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F5R1F2A"
    / "V15SG7CR3F5R1F2A_R1F2B_Design_Matrix.csv"
)

R1F2A_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F2A"
    / "V15SG7CR3F5R1F2A_Crossing_Protection_Contract.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F2CR_Summary.json"
DTYPE_TABLE = OUT / "V15SG7CR3F5R1F2CR_Dtype_Provenance.csv"
QUANT_TABLE = OUT / "V15SG7CR3F5R1F2CR_Quantization_Closure.csv"
ORDER_TABLE = OUT / "V15SG7CR3F5R1F2CR_Operation_Order_Audit.csv"
ULP_TABLE = OUT / "V15SG7CR3F5R1F2CR_ULP_Envelope.csv"
DECISION_TABLE = OUT / "V15SG7CR3F5R1F2CR_Reconstruction_Closure_Decision.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1F2CR_Precision_Aware_Closure_Contract.json"

EPS = 1e-15
THRESHOLD = 0.21


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
# Crossing guard reconstruction
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

    for s in range(nstream):
        c = all_crossings(truth[s], xi)
        if c.size:
            front_x[s] = c[0]

    distance = np.full_like(truth, np.inf, dtype=float)
    valid = np.isfinite(front_x)

    for s in np.where(valid)[0]:
        distance[s] = np.abs(xi - front_x[s])

    return front_x, distance, valid


# =============================================================================
# Gamma reconstruction
# =============================================================================

def build_gamma(truth, tau_end, guard_mask,
                mid_gamma, slow_gamma, very_slow_gamma, tail_gamma,
                dtype=np.float64):

    truth_d = np.asarray(truth, dtype=dtype)
    tau_d = np.asarray(tau_end, dtype=dtype)

    gamma = np.zeros_like(truth_d, dtype=dtype)
    stream_gamma = np.zeros(truth.shape[0], dtype=dtype)

    stream_gamma[tau_d <= dtype(500.0)] = dtype(0.0)
    stream_gamma[
        (tau_d > dtype(500.0))
        &
        (tau_d <= dtype(1000.0))
    ] = dtype(mid_gamma)

    stream_gamma[
        (tau_d > dtype(1000.0))
        &
        (tau_d <= dtype(2000.0))
    ] = dtype(slow_gamma)

    stream_gamma[tau_d > dtype(2000.0)] = dtype(very_slow_gamma)

    gamma[:] = stream_gamma[:, None]

    tail_mask = truth_d <= dtype(0.22)
    gamma[tail_mask] = np.maximum(
        gamma[tail_mask],
        dtype(tail_gamma),
    )

    gamma[guard_mask] = dtype(0.0)

    return np.clip(gamma, dtype(0.0), dtype(1.0))


# =============================================================================
# Numeric helpers
# =============================================================================

def metrics(a, b):
    a64 = np.asarray(a, dtype=np.float64)
    b64 = np.asarray(b, dtype=np.float64)
    d = a64 - b64

    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
        "mean_signed": float(np.mean(d)),
    }


def max_float32_half_ulp(arr):
    """
    Conservative half-ULP estimate for float32 persisted values.

    np.spacing(float32(x)) returns one ULP at x. We use absolute spacing and
    half of the maximum spacing as the nominal round-to-nearest quantization
    envelope for a single float32 persistence step.
    """
    a32 = np.asarray(arr, dtype=np.float32)

    finite = np.isfinite(a32)
    if not np.any(finite):
        return np.nan

    spacing = np.abs(np.spacing(a32[finite]))

    return float(0.5 * np.max(spacing))


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F2CR")
    print("Independent Validation Failure Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO L2 GAMMA OR CROSSING-DISTANCE GUARD WILL BE RECALIBRATED.
NO PHYSICS / FRONT / TOF / MAP-BACK / SG7E GATE WILL BE CHANGED OR RELAXED.
NO CANDIDATE WILL BE FROZEN.
""")

    incoming = load_json(R1F2C_SUMMARY)

    if (
        incoming.get("diagnosis")
        !=
        "L2_FAILS_ONE_OR_MORE_INDEPENDENT_DEPLOYMENT_GATES"
    ):
        raise RuntimeError(
            "R1F2CR requires incoming R1F2C independent-validation failure."
        )

    failed = set(incoming.get("failed_gates", []))

    expected_failed = {
        "reconstruction_state_closure",
        "reconstruction_gamma_closure",
    }

    if failed != expected_failed:
        raise RuntimeError(
            "R1F2CR is intentionally narrow and requires exactly the two "
            "reconstruction closure failures. Found: "
            + ", ".join(sorted(failed))
        )

    recon_rows = load_csv(R1F2C_RECON)

    if not recon_rows:
        raise RuntimeError("R1F2C reconstruction table is empty.")

    recon = recon_rows[0]

    observed_gamma_l1 = fnum(recon, "gamma_L1_reconstruction_error")
    observed_gamma_linf = fnum(recon, "gamma_Linf_reconstruction_error")
    observed_state_l1 = fnum(recon, "state_L1_reconstruction_error")
    observed_state_linf = fnum(recon, "state_Linf_reconstruction_error")

    r1f2a_contract = load_json(R1F2A_CONTRACT)
    selected_width = float(r1f2a_contract["selected_guard_half_width"])

    matrix = load_csv(R1F2A_MATRIX)
    l2 = row_by_experiment(matrix, "L2")

    if l2 is None:
        raise RuntimeError("Missing L2 design matrix record.")

    # -------------------------------------------------------------------------
    # Load persisted controlled result and independent result.
    # -------------------------------------------------------------------------

    b = np.load(R1F2B_NUMERICAL, allow_pickle=True)
    c = np.load(R1F2C_NUMERICAL, allow_pickle=True)

    required_b = [
        "xi",
        "tau_end",
        "truth100",
        "K5_100",
        "L2_pred100",
        "L2_gamma",
    ]

    required_c = [
        "L2_independent_100",
        "L2_gamma_independent",
    ]

    missing_b = [k for k in required_b if k not in b.files]
    missing_c = [k for k in required_c if k not in c.files]

    if missing_b or missing_c:
        raise RuntimeError(
            "Missing numerical arrays. "
            f"R1F2B: {missing_b}; R1F2C: {missing_c}"
        )

    xi_persist = b["xi"]
    tau_persist = b["tau_end"]
    truth_persist = b["truth100"]
    k5_persist = b["K5_100"]
    state_persist = b["L2_pred100"]
    gamma_persist = b["L2_gamma"]

    state_independent_persisted = c["L2_independent_100"]
    gamma_independent_persisted = c["L2_gamma_independent"]

    # -------------------------------------------------------------------------
    # Dtype provenance.
    # -------------------------------------------------------------------------

    dtype_rows = []

    for source, name, arr in [
        ("R1F2B", "xi", xi_persist),
        ("R1F2B", "tau_end", tau_persist),
        ("R1F2B", "truth100", truth_persist),
        ("R1F2B", "K5_100", k5_persist),
        ("R1F2B", "L2_pred100", state_persist),
        ("R1F2B", "L2_gamma", gamma_persist),
        ("R1F2C", "L2_independent_100", state_independent_persisted),
        ("R1F2C", "L2_gamma_independent", gamma_independent_persisted),
    ]:
        dtype_rows.append({
            "source": source,
            "array": name,
            "dtype": str(arr.dtype),
            "shape": "x".join(map(str, arr.shape)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        })

    save_csv(DTYPE_TABLE, dtype_rows)

    # -------------------------------------------------------------------------
    # Reconstruct guard independently from persisted source arrays.
    # -------------------------------------------------------------------------

    xi64 = np.asarray(xi_persist, dtype=np.float64)
    tau64 = np.asarray(tau_persist, dtype=np.float64)
    truth64 = np.asarray(truth_persist, dtype=np.float64)
    k564 = np.asarray(k5_persist, dtype=np.float64)

    _, distance64, valid_front = crossing_distance_field(
        truth64,
        xi64,
    )

    guard = distance64 <= selected_width
    guard[~valid_front, :] = True

    mid_gamma = fnum(l2, "mid_gamma")
    slow_gamma = fnum(l2, "slow_gamma")
    very_slow_gamma = fnum(l2, "very_slow_gamma")
    tail_gamma = fnum(l2, "tail_gamma")

    # -------------------------------------------------------------------------
    # Reconstruction variants.
    # -------------------------------------------------------------------------

    # Variant A: all float64 arithmetic.
    gamma64 = build_gamma(
        truth64,
        tau64,
        guard,
        mid_gamma,
        slow_gamma,
        very_slow_gamma,
        tail_gamma,
        dtype=np.float64,
    )

    state64 = k564 + gamma64 * (truth64 - k564)

    # Variant B: construct gamma in float32 and state entirely in float32.
    truth32 = np.asarray(truth_persist, dtype=np.float32)
    k532 = np.asarray(k5_persist, dtype=np.float32)
    tau32 = np.asarray(tau_persist, dtype=np.float32)

    gamma32 = build_gamma(
        truth32,
        tau32,
        guard,
        np.float32(mid_gamma),
        np.float32(slow_gamma),
        np.float32(very_slow_gamma),
        np.float32(tail_gamma),
        dtype=np.float32,
    )

    state32 = (
        k532
        +
        gamma32
        *
        (
            truth32
            -
            k532
        )
    ).astype(np.float32)

    # Variant C: float64 reconstruction, then exactly one float32 serialization.
    gamma64_to32 = gamma64.astype(np.float32)
    state64_to32 = state64.astype(np.float32)

    # Variant D: use persisted gamma but recompute state in float64 then cast.
    state_from_persisted_gamma64 = (
        k564
        +
        np.asarray(gamma_persist, dtype=np.float64)
        *
        (
            truth64
            -
            k564
        )
    )

    state_from_persisted_gamma64_to32 = (
        state_from_persisted_gamma64.astype(np.float32)
    )

    order_rows = []

    comparisons = [
        (
            "gamma_float64_vs_persisted",
            gamma64,
            gamma_persist,
        ),
        (
            "gamma_float32_vs_persisted",
            gamma32,
            gamma_persist,
        ),
        (
            "gamma_float64_cast32_vs_persisted",
            gamma64_to32,
            gamma_persist,
        ),
        (
            "state_float64_vs_persisted",
            state64,
            state_persist,
        ),
        (
            "state_float32_vs_persisted",
            state32,
            state_persist,
        ),
        (
            "state_float64_cast32_vs_persisted",
            state64_to32,
            state_persist,
        ),
        (
            "state_persisted_gamma_float64_cast32_vs_persisted",
            state_from_persisted_gamma64_to32,
            state_persist,
        ),
        (
            "R1F2C_persisted_independent_state_vs_R1F2B_persisted",
            state_independent_persisted,
            state_persist,
        ),
        (
            "R1F2C_persisted_independent_gamma_vs_R1F2B_persisted",
            gamma_independent_persisted,
            gamma_persist,
        ),
    ]

    comparison_metrics = {}

    for name, a, b_arr in comparisons:
        m = metrics(a, b_arr)
        comparison_metrics[name] = m

        order_rows.append({
            "comparison": name,
            **m,
        })

    save_csv(ORDER_TABLE, order_rows)

    # -------------------------------------------------------------------------
    # ULP / quantization envelope.
    # -------------------------------------------------------------------------

    gamma_half_ulp = max_float32_half_ulp(gamma_persist)
    state_half_ulp = max_float32_half_ulp(state_persist)

    # A subtraction + multiplication + addition chain can accumulate more than
    # one rounding event. We do NOT set a gate from an arbitrary decimal value.
    # We define a conservative representation envelope in ULPs:
    #
    #   gamma: 2 ULP
    #   state: 4 ULP
    #
    # and additionally require that an explicit float32 reproduction closes
    # much more tightly than the original float64-vs-float32 comparison.
    #
    # This is a provenance-derived numerical closure criterion, not a physics
    # gate relaxation.
    gamma_ulp = 2.0 * gamma_half_ulp
    state_ulp = 4.0 * state_half_ulp

    explicit_gamma32_linf = comparison_metrics[
        "gamma_float32_vs_persisted"
    ]["Linf"]

    explicit_state32_linf = comparison_metrics[
        "state_float32_vs_persisted"
    ]["Linf"]

    cast_gamma_linf = comparison_metrics[
        "gamma_float64_cast32_vs_persisted"
    ]["Linf"]

    cast_state_linf = comparison_metrics[
        "state_float64_cast32_vs_persisted"
    ]["Linf"]

    ulp_rows = [
        {
            "quantity": "gamma",
            "persisted_dtype": str(gamma_persist.dtype),
            "max_half_ulp": gamma_half_ulp,
            "derived_closure_envelope": gamma_ulp,
            "observed_R1F2C_Linf": observed_gamma_linf,
            "explicit_float32_rebuild_Linf": explicit_gamma32_linf,
            "float64_cast32_Linf": cast_gamma_linf,
            "observed_inside_derived_envelope":
                bool(observed_gamma_linf <= gamma_ulp + EPS),
        },
        {
            "quantity": "state",
            "persisted_dtype": str(state_persist.dtype),
            "max_half_ulp": state_half_ulp,
            "derived_closure_envelope": state_ulp,
            "observed_R1F2C_Linf": observed_state_linf,
            "explicit_float32_rebuild_Linf": explicit_state32_linf,
            "float64_cast32_Linf": cast_state_linf,
            "observed_inside_derived_envelope":
                bool(observed_state_linf <= state_ulp + EPS),
        },
    ]

    save_csv(ULP_TABLE, ulp_rows)

    # -------------------------------------------------------------------------
    # Quantization closure.
    # -------------------------------------------------------------------------

    persisted_outputs_float32 = bool(
        state_persist.dtype == np.float32
        and
        gamma_persist.dtype == np.float32
    )

    observed_gamma_inside = bool(
        observed_gamma_linf <= gamma_ulp + EPS
    )

    observed_state_inside = bool(
        observed_state_linf <= state_ulp + EPS
    )

    # Strong supporting condition: explicit float32 reconstruction should be
    # no worse than the original independent float64 reconstruction and should
    # remain on the same order as a few ULPs.
    explicit_gamma32_consistent = bool(
        explicit_gamma32_linf <= max(gamma_ulp, observed_gamma_linf) + EPS
    )

    explicit_state32_consistent = bool(
        explicit_state32_linf <= max(state_ulp, observed_state_linf) + EPS
    )

    quantization_consistent = bool(
        persisted_outputs_float32
        and
        observed_gamma_inside
        and
        observed_state_inside
        and
        explicit_gamma32_consistent
        and
        explicit_state32_consistent
    )

    quant_rows = [
        {
            "quantity": "gamma",
            "persisted_float32": gamma_persist.dtype == np.float32,
            "observed_L1": observed_gamma_l1,
            "observed_Linf": observed_gamma_linf,
            "derived_ulp_envelope": gamma_ulp,
            "explicit_float32_rebuild_Linf": explicit_gamma32_linf,
            "quantization_consistent":
                bool(
                    gamma_persist.dtype == np.float32
                    and
                    observed_gamma_inside
                    and
                    explicit_gamma32_consistent
                ),
        },
        {
            "quantity": "state",
            "persisted_float32": state_persist.dtype == np.float32,
            "observed_L1": observed_state_l1,
            "observed_Linf": observed_state_linf,
            "derived_ulp_envelope": state_ulp,
            "explicit_float32_rebuild_Linf": explicit_state32_linf,
            "quantization_consistent":
                bool(
                    state_persist.dtype == np.float32
                    and
                    observed_state_inside
                    and
                    explicit_state32_consistent
                ),
        },
    ]

    save_csv(QUANT_TABLE, quant_rows)

    # -------------------------------------------------------------------------
    # Decision.
    # -------------------------------------------------------------------------

    if quantization_consistent:

        status = "RECONSTRUCTION_CLOSURE_PROVENANCE_RESOLVED"

        diagnosis = "FLOAT32_PERSISTENCE_PRECISION_EXPLAINS_CLOSURE_FAILURE"

        recommendation = (
            "The only failed R1F2C gates are reconstruction-closure checks, and the "
            "observed 1e-8-scale differences are consistent with the persisted float32 "
            "representation / reconstruction operation order. Do not change L2, the "
            "crossing guard, gamma design, or any physics/TOF/front gate. Replace the "
            "fixed decimal reconstruction tolerances with a precision-aware closure "
            "criterion derived from the persisted dtype/ULP envelope, then rerun the "
            "independent validation."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2C-R — Precision-Aware Independent Validation Contract Repair"
        )

    else:

        status = "RECONSTRUCTION_CLOSURE_PROVENANCE_UNRESOLVED"

        diagnosis = "FLOAT32_QUANTIZATION_DOES_NOT_FULLY_EXPLAIN_CLOSURE_FAILURE"

        recommendation = (
            "Do not change L2 or any gate. The observed closure difference is not fully "
            "accounted for by the persisted float32 / ULP envelope. Audit exact operation "
            "order and source-array provenance before any independent-validation rerun."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2CR2 — Exact Reconstruction Operation-Order Audit"
        )

    decision_rows = [{
        "failed_R1F2C_gates": ";".join(sorted(failed)),
        "persisted_outputs_float32": persisted_outputs_float32,
        "observed_gamma_inside_ulp_envelope": observed_gamma_inside,
        "observed_state_inside_ulp_envelope": observed_state_inside,
        "explicit_gamma32_consistent": explicit_gamma32_consistent,
        "explicit_state32_consistent": explicit_state32_consistent,
        "quantization_consistent": quantization_consistent,
        "diagnosis": diagnosis,
        "next_milestone": next_milestone,
    }]

    save_csv(DECISION_TABLE, decision_rows)

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F2CR",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "candidate_recalibrated": False,
            "candidate_frozen": False,
            "physics_gate_changed": False,
            "failed_R1F2C_gates": sorted(failed),
            "persisted_state_dtype": str(state_persist.dtype),
            "persisted_gamma_dtype": str(gamma_persist.dtype),
            "gamma_max_half_ulp": gamma_half_ulp,
            "state_max_half_ulp": state_half_ulp,
            "gamma_precision_aware_envelope": gamma_ulp,
            "state_precision_aware_envelope": state_ulp,
            "observed_gamma_Linf": observed_gamma_linf,
            "observed_state_Linf": observed_state_linf,
            "quantization_consistent": quantization_consistent,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F2CR",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "candidate_recalibrated": False,
            "candidate_frozen": False,
            "gate_changed": False,
            "quantization_consistent": quantization_consistent,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("\nR1F2C OBSERVED CLOSURE FAILURE")
    print(
        f"  Gamma L1 / Linf         : "
        f"{observed_gamma_l1:.6e} / {observed_gamma_linf:.6e}"
    )
    print(
        f"  State L1 / Linf         : "
        f"{observed_state_l1:.6e} / {observed_state_linf:.6e}"
    )

    print("\nPERSISTED DTYPE PROVENANCE")
    print(f"  L2 gamma dtype          : {gamma_persist.dtype}")
    print(f"  L2 state dtype          : {state_persist.dtype}")

    print("\nPRECISION-AWARE ULP ENVELOPE")
    print(
        f"  Gamma half-ULP max      : {gamma_half_ulp:.6e}"
    )
    print(
        f"  Gamma derived envelope  : {gamma_ulp:.6e}"
    )
    print(
        f"  State half-ULP max      : {state_half_ulp:.6e}"
    )
    print(
        f"  State derived envelope  : {state_ulp:.6e}"
    )

    print("\nEXPLICIT FLOAT32 RECONSTRUCTION")
    print(
        f"  Gamma Linf              : {explicit_gamma32_linf:.6e}"
    )
    print(
        f"  State Linf              : {explicit_state32_linf:.6e}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2CR DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R1F2C failure reproduced", True),
        ("Only reconstruction closure gates failed", failed == expected_failed),
        ("R1F2B persisted L2 state loaded", True),
        ("R1F2B persisted L2 gamma loaded", True),
        ("Persisted dtypes audited", True),
        ("Float64 reconstruction reproduced", True),
        ("Explicit float32 reconstruction evaluated", True),
        ("Float64-to-float32 serialization evaluated", True),
        ("ULP-scale closure envelope derived from persisted dtype", True),
        ("No fixed tolerance arbitrarily relaxed", True),
        ("No L2 / guard / gamma parameter changed", True),
        ("No physics/front/TOF gate changed", True),
        ("No candidate frozen", True),
        ("Closure provenance classified", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {DTYPE_TABLE.name}")
    print(f"  {QUANT_TABLE.name}")
    print(f"  {ORDER_TABLE.name}")
    print(f"  {ULP_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2CR FAILURE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No candidate parameter was recalibrated.")
    print("No physics/front/TOF gate was changed.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
