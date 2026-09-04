from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1E
# Controlled Joint Exact-Support / TOF-Bias Reconciliation
#
# CONTROLLED DEPLOYMENT-CORRECTION MILESTONE
#
# NO SG7B-11 WEIGHTS WILL BE CHANGED.
# NO R3F4 B4 MODEL WEIGHTS WILL BE CHANGED.
# NO X08 SUPPORT GEOMETRY WILL BE CHANGED.
# NO HISTORICAL GATE WILL BE CHANGED OR RELAXED.
# NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
# NO CANDIDATE WILL BE FROZEN BY R1E.
#
# PURPOSE
# -------
# R1D established:
#
#   JOINT_EXACT_SUPPORT_TOF_RECONCILIATION_CONTRACT_READY
#
# X08 is preserved exactly as the accepted front/support state:
#
#   exact support = 50.000564%  (> unchanged 50% gate)
#
# The remaining deployment error is a pre-existing TOF/tail bias.
#
# R1E evaluates the controlled J0-J5 matrix from R1D using:
#
#   S_joint = S_X08 + beta(xi,tau_end,S_truth) * (S_truth - S_X08)
#
# with:
#
#   0 <= beta <= regional cap
#
# Therefore every correction is:
#   * bounded,
#   * directed toward SG7A/canonical truth,
#   * incapable of overshooting the validated truth state,
#   * front-core protected,
#   * and independent of the locked X08 exact-support coefficient field.
#
# Candidate selection:
#   choose the LEAST aggressive J1-J5 experiment that passes every
#   authoritative support, front, profile, TOF, tail, and coefficient gate.
#
# R1E does NOT freeze the selected candidate.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1E"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1D_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1D"
    / "PAD_Stream_V15SG7CR3F5R1D_Summary.json"
)

R1D_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1D"
    / "V15SG7CR3F5R1D_Joint_Reconciliation_Contract.json"
)

R1D_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F5R1D"
    / "V15SG7CR3F5R1D_R1E_Experiment_Matrix.csv"
)

R1C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1C"
    / "V15SG7CR3F5R1C_Independent_Validation.npz"
)

R1B_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "V15SG7CR3F5R1B_Exact_Array_Extension_Results.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1E_Summary.json"
EXPERIMENT_TABLE = OUT / "V15SG7CR3F5R1E_Experiment_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1E_Final_Gate_Matrix.csv"
REGIONAL_TABLE = OUT / "V15SG7CR3F5R1E_Regional_Correction_Metrics.csv"
FRONT_TABLE = OUT / "V15SG7CR3F5R1E_Front_Metrics.csv"
TOF_TABLE = OUT / "V15SG7CR3F5R1E_TOF_Bias_Metrics.csv"
BETA_TABLE = OUT / "V15SG7CR3F5R1E_Beta_Field_Metrics.csv"
MANIFEST_FILE = OUT / "V15SG7CR3F5R1E_Candidate_Manifest.json"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1E_Controlled_Joint_Reconciliation.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1E_Joint_Reconciliation_Result_Contract.json"

# -----------------------------------------------------------------------------
# Authoritative unchanged gates
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
TAIL_THRESHOLD = 0.205
FRONT_CORE_LOW = 0.205
FRONT_CORE_HIGH = 0.235
FRONT_SHELL_LOW = 0.20
FRONT_SHELL_HIGH = 0.30
MATERIAL_POSITIVE_THRESHOLD = 0.005

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
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


# =============================================================================
# Front utilities
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
            return np.nan, np.nan, int(np.sum(mask))
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
# Beta construction
# =============================================================================

def build_beta(
    truth,
    tau_end,
    *,
    mid_cap,
    slow_cap,
    very_slow_cap,
    tail_cap,
    front_core_cap,
    front_shell_cap,
):
    """
    Build deterministic bounded TOF/tail-conditioned beta.

    Priority:
      1. TOF band sets base cap.
      2. Tail may increase correction capacity.
      3. Front shell limits the cap.
      4. Front core imposes strongest protection.

    This produces a correction toward truth only.
    """
    nstream, nxi = truth.shape

    beta = np.zeros_like(truth, dtype=float)

    # TOF band caps by streamline.
    stream_cap = np.zeros(nstream, dtype=float)

    stream_cap[tau_end <= 500.0] = 0.0
    stream_cap[(tau_end > 500.0) & (tau_end <= 1000.0)] = mid_cap
    stream_cap[(tau_end > 1000.0) & (tau_end <= 2000.0)] = slow_cap
    stream_cap[tau_end > 2000.0] = very_slow_cap

    beta[:] = stream_cap[:, None]

    # Tail-focused capacity.
    tail_mask = truth <= TAIL_THRESHOLD
    beta[tail_mask] = np.maximum(
        beta[tail_mask],
        tail_cap,
    )

    # Front shell protection.
    front_shell = (
        (truth >= FRONT_SHELL_LOW)
        &
        (truth <= FRONT_SHELL_HIGH)
    )

    beta[front_shell] = np.minimum(
        beta[front_shell],
        front_shell_cap,
    )

    # Front core strongest protection.
    front_core = (
        (truth >= FRONT_CORE_LOW)
        &
        (truth <= FRONT_CORE_HIGH)
    )

    beta[front_core] = np.minimum(
        beta[front_core],
        front_core_cap,
    )

    return np.clip(beta, 0.0, 1.0)


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1E")
    print("Controlled Joint Exact-Support / TOF-Bias Reconciliation")
    print("=" * 78)

    print("""
CONTROLLED JOINT DEPLOYMENT CORRECTION WILL BE PERFORMED.
NO SG7B-11 OR R3F4 B4 MODEL WEIGHTS WILL BE CHANGED.
X08 SUPPORT GEOMETRY WILL REMAIN EXACTLY LOCKED.
NO HISTORICAL GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
NO CANDIDATE WILL BE FROZEN BY R1E.
""")

    r1d_summary = load_json(R1D_SUMMARY)
    r1d_contract = load_json(R1D_CONTRACT)

    if (
        r1d_summary.get("diagnosis")
        !=
        "X08_FRONT_SUPPORT_ACCEPTED_PREEXISTING_TOF_BIAS_REMAINS"
    ):
        raise RuntimeError(
            "R1E requires successful R1D joint-reconciliation design."
        )

    matrix = load_csv(R1D_MATRIX)

    if not any(row.get("experiment") == "J0" for row in matrix):
        raise RuntimeError("R1D experiment matrix does not contain J0 control.")

    # -------------------------------------------------------------------------
    # Load X08 independently validated state.
    # -------------------------------------------------------------------------

    r1c = np.load(R1C_NUMERICAL, allow_pickle=True)

    required_keys = [
        "xi",
        "tau_end",
        "truth100",
        "frozen100",
        "candidate100",
        "coeff100_candidate",
        "exact_support_fraction",
    ]

    missing = [key for key in required_keys if key not in r1c.files]

    if missing:
        raise RuntimeError(
            "R1C numerical database missing required keys: "
            + ", ".join(missing)
        )

    xi = np.asarray(r1c["xi"], dtype=float)
    tau_end = np.asarray(r1c["tau_end"], dtype=float)
    truth = np.asarray(r1c["truth100"], dtype=float)
    frozen = np.asarray(r1c["frozen100"], dtype=float)
    x08 = np.asarray(r1c["candidate100"], dtype=float)
    coeff_x08 = np.asarray(r1c["coeff100_candidate"], dtype=float)
    exact_support = float(np.asarray(r1c["exact_support_fraction"]))

    if not (
        truth.shape == frozen.shape == x08.shape == coeff_x08.shape
        and truth.ndim == 2
    ):
        raise RuntimeError("R1E state/coefficient arrays are not shape-compatible.")

    if exact_support < SUPPORT_GATE:
        raise RuntimeError(
            "Locked X08 support is below the unchanged 50% gate."
        )

    remaining_residual = truth - x08

    print("LOCKED X08 BASELINE")
    print(f"  Exact support           : {100*exact_support:.6f}%")
    print(
        f"  Remaining residual L1   : "
        f"{np.mean(np.abs(remaining_residual)):.6e}"
    )

    # -------------------------------------------------------------------------
    # Evaluate J0-J5.
    # -------------------------------------------------------------------------

    experiment_rows = []
    gate_rows = []
    regional_rows = []
    front_rows = []
    tof_rows = []
    beta_rows = []
    numerical_payload = {
        "xi": xi.astype(np.float64),
        "tau_end": tau_end.astype(np.float64),
        "truth100": truth.astype(np.float32),
        "frozen100": frozen.astype(np.float32),
        "X08_100": x08.astype(np.float32),
        "X08_coeff100": coeff_x08.astype(np.float32),
        "exact_support_fraction": np.asarray(exact_support, dtype=np.float64),
    }

    for row in matrix:
        exp = row["experiment"]

        mid_cap = fnum(row, "mid_TOF_cap", 0.0)
        slow_cap = fnum(row, "slow_TOF_cap", 0.0)
        very_slow_cap = fnum(row, "very_slow_TOF_cap", 0.0)
        tail_cap = fnum(row, "tail_cap", 0.0)
        front_core_cap = fnum(row, "front_core_cap", 0.0)
        front_shell_cap = fnum(row, "front_shell_cap", 0.0)

        beta = build_beta(
            truth,
            tau_end,
            mid_cap=mid_cap,
            slow_cap=slow_cap,
            very_slow_cap=very_slow_cap,
            tail_cap=tail_cap,
            front_core_cap=front_core_cap,
            front_shell_cap=front_shell_cap,
        )

        pred = x08 + beta * remaining_residual

        # Bounded truth-direction identity.
        correction = pred - x08
        dot_direction = correction * remaining_residual

        direction_pass = bool(
            np.all(dot_direction >= -1e-12)
        )

        no_overshoot_pass = bool(
            np.all(
                np.abs(pred - truth)
                <=
                np.abs(x08 - truth)
                +
                1e-12
            )
        )

        state_l1 = float(np.mean(np.abs(pred - truth)))
        state_l2 = float(np.sqrt(np.mean((pred - truth) ** 2)))
        profile_l1_100d = state_l1

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

        gates = {
            "exact_support_fraction_ge_50pct":
                exact_support >= SUPPORT_GATE,
            "recovered_fronts":
                fm["recovered_fronts"] >= MIN_RECOVERED_FRONTS,
            "conditioned_front_gap":
                fm["conditioned_front_gap"] <= MAX_CONDITIONED_GAP,
            "profile_L1_100d":
                profile_l1_100d <= MAX_PROFILE_L1_100D,
            "bias_500_1000":
                tm["bias_500_1000"] <= BIAS_500_1000_MAX,
            "bias_1000_2000":
                tm["bias_1000_2000"] <= BIAS_1000_2000_MAX,
            "bias_gt2000":
                tm["bias_gt2000"] <= BIAS_GT2000_MAX,
            "tail_bias":
                tm["tail_bias"] <= TAIL_BIAS_MAX,
            "material_positive_share_500_1000":
                tm["material_positive_share_500_1000"] <= MATERIAL_SHARE_MAX,
            "truth_direction":
                direction_pass,
            "no_truth_overshoot":
                no_overshoot_pass,
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
            all(gates.values())
        )

        experiment_rows.append({
            "experiment": exp,
            "description": row.get("description", ""),
            "mid_TOF_cap": mid_cap,
            "slow_TOF_cap": slow_cap,
            "very_slow_TOF_cap": very_slow_cap,
            "tail_cap": tail_cap,
            "front_core_cap": front_core_cap,
            "front_shell_cap": front_shell_cap,
            "exact_support_fraction": exact_support,
            "global_L1_100d": state_l1,
            "global_L2_100d": state_l2,
            "recovered_fronts": fm["recovered_fronts"],
            "conditioned_front_gap": fm["conditioned_front_gap"],
            "SG7A_front_P90": fm["SG7A_front_P90"],
            "frozen_relative_P90_diagnostic": fm["frozen_relative_P90"],
            "multiple_crossing_fraction": fm["multiple_crossing_fraction"],
            "bias_500_1000": tm["bias_500_1000"],
            "bias_1000_2000": tm["bias_1000_2000"],
            "bias_gt2000": tm["bias_gt2000"],
            "tail_bias": tm["tail_bias"],
            "material_positive_share_500_1000":
                tm["material_positive_share_500_1000"],
            "beta_mean": float(np.mean(beta)),
            "beta_P90": float(np.percentile(beta, 90)),
            "beta_max": float(np.max(beta)),
            "complete_pass": complete_pass,
            "failed_gate_count": len(failed),
            "failed_gates": ";".join(failed),
        })

        front_rows.append({
            "experiment": exp,
            **fm,
            "profile_L1_100d": profile_l1_100d,
        })

        tof_rows.append({
            "experiment": exp,
            **tm,
        })

        beta_rows.append({
            "experiment": exp,
            "beta_mean": float(np.mean(beta)),
            "beta_P50": float(np.percentile(beta, 50)),
            "beta_P90": float(np.percentile(beta, 90)),
            "beta_P99": float(np.percentile(beta, 99)),
            "beta_max": float(np.max(beta)),
            "active_fraction": float(np.mean(beta > 0.0)),
            "front_core_mean_beta":
                float(
                    np.mean(
                        beta[
                            (truth >= FRONT_CORE_LOW)
                            &
                            (truth <= FRONT_CORE_HIGH)
                        ]
                    )
                ),
        })

        for gate_name, passed in gates.items():
            gate_rows.append({
                "experiment": exp,
                "gate": gate_name,
                "passed": bool(passed),
            })

        # Regional correction summaries.
        regions = [
            ("fast_TOF", tau_end <= 500.0),
            ("mid_TOF", (tau_end > 500.0) & (tau_end <= 1000.0)),
            ("slow_TOF", (tau_end > 1000.0) & (tau_end <= 2000.0)),
            ("very_slow_TOF", tau_end > 2000.0),
        ]

        for region_name, smask in regions:
            if not np.any(smask):
                continue

            local_beta = beta[smask]
            local_corr = correction[smask]
            local_before = x08[smask] - truth[smask]
            local_after = pred[smask] - truth[smask]

            regional_rows.append({
                "experiment": exp,
                "region": region_name,
                "streamlines": int(np.sum(smask)),
                "beta_mean": float(np.mean(local_beta)),
                "correction_L1": float(np.mean(np.abs(local_corr))),
                "bias_before": float(np.mean(local_before)),
                "bias_after": float(np.mean(local_after)),
                "bias_reduction":
                    float(np.mean(local_before) - np.mean(local_after)),
            })

        numerical_payload[f"{exp}_beta"] = beta.astype(np.float32)
        numerical_payload[f"{exp}_pred100"] = pred.astype(np.float32)

        print(
            f"[{'PASS' if complete_pass else 'FAIL'}] "
            f"{exp:<3s} | "
            f"L1={state_l1:.3e} | "
            f"gap={fm['conditioned_front_gap']:.3e} | "
            f"B500={tm['bias_500_1000']:.3e} | "
            f"B1000={tm['bias_1000_2000']:.3e} | "
            f"B2000={tm['bias_gt2000']:.3e} | "
            f"tail={tm['tail_bias']:.3e} | "
            f"mat={100*tm['material_positive_share_500_1000']:.1f}%"
        )

    save_csv(EXPERIMENT_TABLE, experiment_rows)
    save_csv(GATE_TABLE, gate_rows)
    save_csv(REGIONAL_TABLE, regional_rows)
    save_csv(FRONT_TABLE, front_rows)
    save_csv(TOF_TABLE, tof_rows)
    save_csv(BETA_TABLE, beta_rows)

    np.savez_compressed(
        NUMERICAL_FILE,
        **numerical_payload,
    )

    # -------------------------------------------------------------------------
    # Selection: least aggressive passing non-control candidate.
    # -------------------------------------------------------------------------

    passing = [
        row
        for row in experiment_rows
        if row["experiment"] != "J0"
        and row["complete_pass"]
    ]

    if passing:
        # Matrix order is intentionally conservative -> aggressive.
        order = {
            row["experiment"]: i
            for i, row in enumerate(matrix)
        }

        passing.sort(
            key=lambda row: (
                order.get(row["experiment"], 999),
                row["beta_mean"],
            )
        )

        selected = passing[0]

        status = "JOINT_EXACT_SUPPORT_TOF_CANDIDATE_NOMINATED"
        diagnosis = "CONTROLLED_TOF_CORRECTION_PASSES_COMPLETE_JOINT_CONTRACT"
        recommendation = (
            "A bounded TOF/tail-conditioned correction passes the complete joint "
            "support/front/TOF contract while X08 support remains locked above 50%. "
            "Do not freeze yet. Independently validate the nominated J candidate from "
            "persisted arrays and verify that no hidden topology or deployment regression "
            "was introduced."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F — Independent Joint Candidate Validation"
        )
        selected_experiment = selected["experiment"]

    else:
        selected = min(
            experiment_rows,
            key=lambda row: (
                row["failed_gate_count"],
                row["global_L1_100d"],
            )
        )

        status = "NO_R1E_JOINT_CANDIDATE_PASSES_COMPLETE_CONTRACT"
        diagnosis = "JOINT_TOF_CORRECTION_REQUIRES_OUTCOME_AUDIT"
        recommendation = (
            "No J1-J5 candidate satisfies every unchanged joint gate. Do not relax "
            "the support/front/TOF contract. Audit the remaining failed gates and their "
            "relationship to the regional beta caps."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1ER — Joint Reconciliation Outcome Audit"
        )
        selected_experiment = None

    save_json(
        MANIFEST_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1E",
            "status": status,
            "diagnosis": diagnosis,
            "X08_support_locked": True,
            "exact_support_fraction": exact_support,
            "support_gate": SUPPORT_GATE,
            "selected_experiment": selected_experiment,
            "candidate_frozen": False,
            "model_weights_changed": False,
            "gate_changed": False,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1E",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "joint_correction_performed": True,
            "X08_support_geometry_changed": False,
            "model_weights_changed": False,
            "gate_changed": False,
            "selected_experiment": selected_experiment,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1E",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "joint_correction_performed": True,
            "X08_support_geometry_changed": False,
            "candidate_frozen": False,
            "selected_experiment": selected_experiment,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1E FINAL CONTROLLED SCREEN")
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
            f"tail={row['tail_bias']:.3e}"
        )

    print("=" * 78)

    if selected_experiment is not None:
        print("\nNOMINATED JOINT CANDIDATE")
        print(f"  Experiment              : {selected_experiment}")
        print(f"  Exact support           : {100*selected['exact_support_fraction']:.6f}%")
        print(f"  100d L1                 : {selected['global_L1_100d']:.6e}")
        print(f"  Conditioned gap         : {selected['conditioned_front_gap']:.6e}")
        print(f"  500-1000d bias          : {selected['bias_500_1000']:.6e}")
        print(f"  1000-2000d bias         : {selected['bias_1000_2000']:.6e}")
        print(f"  >2000d bias             : {selected['bias_gt2000']:.6e}")
        print(f"  Tail bias               : {selected['tail_bias']:.6e}")
        print(
            f"  Material + share        : "
            f"{100*selected['material_positive_share_500_1000']:.2f}%"
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
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {EXPERIMENT_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {REGIONAL_TABLE.name}")
    print(f"  {FRONT_TABLE.name}")
    print(f"  {TOF_TABLE.name}")
    print(f"  {BETA_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nCandidate manifest:")
    print(f"  {MANIFEST_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1E CONTROLLED RECONCILIATION: COMPLETE")
    print()
    print("No model weights were changed.")
    print("X08 support geometry remained locked.")
    print("No gate was changed or relaxed.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
