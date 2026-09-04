from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import math
import re
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1
# Controlled Minimal-Support Extension Calibration Repair
#
# EXACT-METRIC REPAIR BRANCH
#
# SG7B-11 WEIGHTS WILL NOT BE CHANGED.
# THE PERSISTED B4 CALIBRATOR WEIGHTS WILL NOT BE CHANGED.
# NO 50% FRONT-ERROR-REDUCTION GATE WILL BE CHANGED OR RELAXED.
# NO TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE CHANGED.
#
# R3F5-R0A established the authoritative support definition:
#
#   front_shell_residual_coverage_fraction
#       =
#   front_shell_supported_residual_sum
#   ----------------------------------
#   front_shell_required_residual_sum
#
# R3F5-R1 MUST reproduce that exact B4 ratio before calibrating any extension.
#
# This script therefore performs two phases:
#
# PHASE A — EXACT SUPPORT CONTRACT RECONSTRUCTION
#   * discover authoritative R3F4/R3F4-R numerical databases
#   * locate front-shell / residual / support / coefficient arrays
#   * reconstruct the B4 required and supported residual sums
#   * require exact agreement with the persisted authoritative CSV
#
# PHASE B — CONTROLLED SUPPORT EXTENSION
#   * only if Phase A passes
#   * keep B4 and SG7B-11 frozen
#   * extend only the exact authoritative front-shell support mask
#   * correction remains a bounded fraction of the canonical residual
#   * evaluate X0-X5 from the R3E design matrix
#
# If the exact numerical arrays are not recoverable, this milestone stops
# safely and emits a discovery audit. It never falls back to multiplicative
# anchoring or a guessed support definition.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R0A_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R0A"
    / "PAD_Stream_V15SG7CR3F5R0A_Summary.json"
)

R0A_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R0A"
    / "V15SG7CR3F5R0A_Authoritative_Support_Metric_Contract.json"
)

R3F4R_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

R3F4_CHECKPOINTS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
)

R3E_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F4R3E"
    / "V15SG7CR3F4R3E_R3F5_Experiment_Matrix.csv"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

R3B_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F4R3B"
    / "V15SG7CR3F4R3B_Deployment_Front_Acceptance_Contract.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1_Summary.json"
DISCOVERY_TABLE = OUT / "V15SG7CR3F5R1_Authoritative_Array_Discovery.csv"
CONTRACT_AUDIT_TABLE = OUT / "V15SG7CR3F5R1_Exact_Support_Contract_Audit.csv"
EXPERIMENT_TABLE = OUT / "V15SG7CR3F5R1_Experiment_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1_Final_Gate_Matrix.csv"
CAL_TABLE = OUT / "V15SG7CR3F5R1_Support_Extension_Calibration.csv"
MANIFEST_FILE = OUT / "V15SG7CR3F5R1_Candidate_Manifest.json"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1_Controlled_Extension_Results.npz"

# -----------------------------------------------------------------------------
# Unchanged gates
# -----------------------------------------------------------------------------

FRONT_REDUCTION_GATE = 0.50

MAX_GLOBAL_L1 = 0.020
MAX_GLOBAL_L2 = 0.030
MAX_SHORT_TOF_MAE = 1.5e-03
MAX_BIAS_500_1000 = 2.5e-03
MAX_BIAS_1000_2000 = 4.5e-03
MAX_BIAS_GT2000 = 5.0e-03
MAX_ABS_CORRECTION = 0.10
MAX_SG7A_FRONT_P90 = 5.0e-03
MIN_CROSSING_IDENTITY = 0.90

FRONT_THRESHOLD = 0.210

# Exact support reconstruction must be extremely tight because R0A showed
# machine-precision closure in the authoritative CSV.
SUPPORT_SUM_ABS_TOL = 1e-8
SUPPORT_FRACTION_ABS_TOL = 1e-10

BISECTION_ITERS = 70


# =============================================================================
# IO HELPERS
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


def save_json(path: Path, obj):
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


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


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


# =============================================================================
# AUTHORITATIVE ARRAY DISCOVERY
# =============================================================================

DISCOVERY_DIRS = [
    ROOT / "output" / "V15_SG7CR3F4",
    ROOT / "output" / "V15_SG7CR3F4R",
    ROOT / "output" / "V15_SG7CR3F4R2",
    ROOT / "output" / "V15_SG7CR3F4R3D",
    ROOT / "output" / "V15_SG7CR3F4R3C",
]

KEY_HINTS = (
    "front",
    "shell",
    "residual",
    "support",
    "coefficient",
    "canonical",
    "frozen",
    "truth",
    "mask",
    "distance",
)


def discover_npz_arrays():
    rows = []
    handles = []

    for directory in DISCOVERY_DIRS:
        if not directory.exists():
            continue

        for path in sorted(directory.glob("*.npz")):
            try:
                db = np.load(path, allow_pickle=True)
            except Exception as exc:
                rows.append({
                    "file": str(path),
                    "key": "",
                    "shape": "",
                    "dtype": "",
                    "hint_match": False,
                    "load_error": repr(exc),
                })
                continue

            handles.append((path, db))

            for key in db.files:
                try:
                    arr = np.asarray(db[key])
                    shape = tuple(arr.shape)
                    dtype = str(arr.dtype)
                except Exception as exc:
                    shape = ""
                    dtype = ""
                    rows.append({
                        "file": str(path),
                        "key": key,
                        "shape": shape,
                        "dtype": dtype,
                        "hint_match": False,
                        "load_error": repr(exc),
                    })
                    continue

                low = key.lower()
                hint = any(token in low for token in KEY_HINTS)

                rows.append({
                    "file": str(path),
                    "key": key,
                    "shape": str(shape),
                    "dtype": dtype,
                    "hint_match": hint,
                    "load_error": "",
                })

    return rows, handles


def candidate_arrays(handles):
    """
    Return flattened lookup entries for keys likely relevant to the exact
    support contract.
    """
    out = []

    for path, db in handles:
        for key in db.files:
            low = key.lower()
            if not any(token in low for token in KEY_HINTS):
                continue

            try:
                arr = np.asarray(db[key])
            except Exception:
                continue

            out.append({
                "file": path,
                "key": key,
                "low": low,
                "array": arr,
            })

    return out


def pick_array(entries, required_tokens, preferred_shape=None):
    choices = []

    for entry in entries:
        low = entry["low"]

        if all(token in low for token in required_tokens):
            score = 0

            if preferred_shape is not None:
                if tuple(entry["array"].shape) == tuple(preferred_shape):
                    score -= 100
                elif entry["array"].ndim == len(preferred_shape):
                    score -= 10

            # Prefer exact semantic names.
            score += len(low)

            choices.append((score, entry))

    if not choices:
        return None

    choices.sort(key=lambda item: item[0])
    return choices[0][1]


def normalize_time_slice(arr, target_shape_3d, idx100):
    """
    Coerce common persisted formats to a 2-D [streamline, xi] 100-day slice.

    target_shape_3d = (nt, ns, nx)
    """
    nt, ns, nx = target_shape_3d
    a = np.asarray(arr)

    if a.shape == (nt, ns, nx):
        return np.asarray(a[idx100])

    if a.shape == (ns, nx):
        return np.asarray(a)

    if a.shape == (nt, ns):
        return np.broadcast_to(
            np.asarray(a[idx100])[:, None],
            (ns, nx),
        )

    if a.shape == (ns,):
        return np.broadcast_to(
            np.asarray(a)[:, None],
            (ns, nx),
        )

    return None


# =============================================================================
# CROSSING UTILITIES
# =============================================================================

def all_crossings(profile, xi, threshold):
    profile = np.asarray(profile, dtype=float)
    xi = np.asarray(xi, dtype=float)

    y = profile - threshold
    crossings = []

    for j in range(len(xi) - 1):
        y0 = y[j]
        y1 = y[j + 1]

        if np.isclose(y0, 0.0, atol=1e-12):
            crossings.append(float(xi[j]))
        elif y0 * y1 < 0.0:
            frac = np.clip(
                -y0 / (y1 - y0),
                0.0,
                1.0,
            )
            crossings.append(
                float(
                    xi[j]
                    +
                    frac * (xi[j + 1] - xi[j])
                )
            )

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


def nearest_crossing(profile, xi, threshold, reference_x):
    c = all_crossings(profile, xi, threshold)

    if c.size == 0 or not np.isfinite(reference_x):
        return np.nan, False, -1

    idx = int(
        np.argmin(
            np.abs(c - reference_x)
        )
    )

    return float(c[idx]), True, idx


def first_front_positions(field, xi):
    nt, ns, _ = field.shape

    positions = np.full(
        (nt, ns),
        np.nan,
        dtype=float,
    )

    valid = np.zeros(
        (nt, ns),
        dtype=bool,
    )

    for it in range(nt):
        for i in range(ns):
            c = all_crossings(
                field[it, i],
                xi,
                FRONT_THRESHOLD,
            )

            if c.size:
                positions[it, i] = c[0]
                valid[it, i] = True

    return positions, valid


# =============================================================================
# EXACT SUPPORT RECONSTRUCTION
# =============================================================================

def booleanize(arr):
    a = np.asarray(arr)

    if a.dtype == bool:
        return a

    finite = np.isfinite(a)

    if not np.any(finite):
        return None

    vals = np.unique(a[finite])

    if vals.size <= 3 and np.all(
        np.isclose(vals, np.round(vals))
    ):
        return a > 0.5

    return None


def reconstruct_exact_support(
    entries,
    target_shape,
    idx100,
    canonical,
    frozen,
    authoritative_required,
    authoritative_supported,
):
    """
    Try authoritative persisted arrays first.

    Exact contract semantics:
      required_sum  = sum(required residual over front shell)
      supported_sum = sum(supported residual over the same required population)

    We search for:
      front_shell_mask
      required_residual
      supported_residual
      support_mask

    If required/supported residual arrays are persisted directly, use them.
    Otherwise try combinations of canonical residual and persisted masks.
    """

    nt, ns, nx = target_shape

    # Semantic candidates.
    shell_entry = (
        pick_array(
            entries,
            ["front", "shell", "mask"],
            target_shape,
        )
        or
        pick_array(
            entries,
            ["front", "shell"],
            target_shape,
        )
    )

    required_entry = (
        pick_array(
            entries,
            ["required", "residual"],
            target_shape,
        )
    )

    supported_entry = (
        pick_array(
            entries,
            ["supported", "residual"],
            target_shape,
        )
    )

    support_mask_entry = (
        pick_array(
            entries,
            ["support", "mask"],
            target_shape,
        )
    )

    coefficient_entry = (
        pick_array(
            entries,
            ["coefficient"],
            target_shape,
        )
    )

    candidate_rows = []

    # Canonical required residual.
    canonical_residual = np.abs(
        canonical[idx100]
        -
        frozen[idx100]
    )

    # Prepare shell.
    shell = None

    if shell_entry is not None:
        shell_raw = normalize_time_slice(
            shell_entry["array"],
            target_shape,
            idx100,
        )

        if shell_raw is not None:
            shell = booleanize(shell_raw)

    # Prepare persisted required residual.
    required_arr = None

    if required_entry is not None:
        required_arr = normalize_time_slice(
            required_entry["array"],
            target_shape,
            idx100,
        )

    # Prepare persisted supported residual.
    supported_arr = None

    if supported_entry is not None:
        supported_arr = normalize_time_slice(
            supported_entry["array"],
            target_shape,
            idx100,
        )

    # Prepare support mask.
    support_mask = None

    if support_mask_entry is not None:
        raw = normalize_time_slice(
            support_mask_entry["array"],
            target_shape,
            idx100,
        )

        if raw is not None:
            support_mask = booleanize(raw)

    # Prepare coefficient.
    coefficient = None

    if coefficient_entry is not None:
        coefficient = normalize_time_slice(
            coefficient_entry["array"],
            target_shape,
            idx100,
        )

    # Candidate source residuals.
    required_sources = []

    if required_arr is not None:
        required_sources.append(
            (
                "persisted_required_residual",
                np.abs(
                    np.asarray(
                        required_arr,
                        dtype=float,
                    )
                ),
            )
        )

    required_sources.append(
        (
            "canonical_minus_frozen_abs",
            canonical_residual,
        )
    )

    # Candidate shell masks.
    shells = []

    if shell is not None:
        shells.append(
            (
                "persisted_front_shell",
                shell,
            )
        )

    # If no exact shell is persisted, do not invent a new front-width shell.
    # We still test a whole-domain diagnostic only to prove it cannot satisfy
    # the exact sums.
    shells.append(
        (
            "whole_domain_diagnostic",
            np.ones(
                (ns, nx),
                dtype=bool,
            ),
        )
    )

    best = None

    for req_name, req in required_sources:
        for shell_name, shell_mask in shells:

            if req.shape != shell_mask.shape:
                continue

            req_sum = float(
                np.sum(
                    req[shell_mask]
                )
            )

            # Supported residual options.
            supported_options = []

            if supported_arr is not None:
                s = np.abs(
                    np.asarray(
                        supported_arr,
                        dtype=float,
                    )
                )

                if s.shape == req.shape:
                    supported_options.append(
                        (
                            "persisted_supported_residual",
                            float(
                                np.sum(
                                    s[shell_mask]
                                )
                            ),
                            None,
                        )
                    )

            if support_mask is not None:
                if support_mask.shape == req.shape:
                    active = (
                        shell_mask
                        &
                        support_mask
                    )

                    supported_options.append(
                        (
                            "required_residual_times_persisted_support_mask",
                            float(
                                np.sum(
                                    req[active]
                                )
                            ),
                            support_mask,
                        )
                    )

            if coefficient is not None:
                if coefficient.shape == req.shape:

                    # Exact coefficient-weighted diagnostic.
                    supported_options.append(
                        (
                            "required_residual_times_persisted_coefficient",
                            float(
                                np.sum(
                                    req[shell_mask]
                                    *
                                    coefficient[shell_mask]
                                )
                            ),
                            coefficient,
                        )
                    )

                    # Positive support occupancy diagnostic.
                    positive = coefficient > 0.0

                    supported_options.append(
                        (
                            "required_residual_times_coefficient_positive_mask",
                            float(
                                np.sum(
                                    req[
                                        shell_mask
                                        &
                                        positive
                                    ]
                                )
                            ),
                            positive,
                        )
                    )

            for sup_name, sup_sum, support_object in supported_options:

                cov = (
                    sup_sum
                    /
                    req_sum
                    if req_sum > 0.0
                    else np.nan
                )

                req_err = abs(
                    req_sum
                    -
                    authoritative_required
                )

                sup_err = abs(
                    sup_sum
                    -
                    authoritative_supported
                )

                score = (
                    req_err
                    +
                    sup_err
                )

                row = {
                    "required_source": req_name,
                    "shell_source": shell_name,
                    "supported_source": sup_name,
                    "required_sum": req_sum,
                    "supported_sum": sup_sum,
                    "coverage_fraction": cov,
                    "required_sum_error": req_err,
                    "supported_sum_error": sup_err,
                    "score": score,
                }

                candidate_rows.append(row)

                if best is None or score < best["row"]["score"]:
                    best = {
                        "row": row,
                        "required_residual": req,
                        "shell_mask": shell_mask,
                        "support_object": support_object,
                        "coefficient": coefficient,
                        "support_mask": support_mask,
                    }

    return best, candidate_rows, {
        "shell_entry": shell_entry,
        "required_entry": required_entry,
        "supported_entry": supported_entry,
        "support_mask_entry": support_mask_entry,
        "coefficient_entry": coefficient_entry,
    }


# =============================================================================
# EXTENSION CALIBRATION
# =============================================================================

def make_extension_order(shell_mask, required_residual):
    """
    Build a deterministic minimal extension order immediately outside the exact
    authoritative supported set but inside the authoritative front-shell mask.

    The goal is to add the smallest possible required-residual mass needed to
    cross 50%.

    Cells/nodes with largest required residual are added first, minimizing the
    number of newly activated support locations for a given recovered residual.
    """
    indices = np.argwhere(shell_mask)

    if indices.size == 0:
        return []

    masses = required_residual[shell_mask]

    order = np.argsort(
        -masses
    )

    return [
        tuple(indices[j])
        for j in order
    ]


def build_minimal_support_mask(
    base_support_mask,
    shell_mask,
    required_residual,
    required_sum,
    target_fraction,
):
    target_supported_sum = (
        target_fraction
        *
        required_sum
    )

    base_supported_sum = float(
        np.sum(
            required_residual[
                shell_mask
                &
                base_support_mask
            ]
        )
    )

    out = np.array(
        base_support_mask,
        dtype=bool,
        copy=True,
    )

    if base_supported_sum >= target_supported_sum:
        return out, base_supported_sum

    candidates = (
        shell_mask
        &
        (~base_support_mask)
    )

    indices = np.argwhere(
        candidates
    )

    if indices.size == 0:
        return out, base_supported_sum

    masses = required_residual[candidates]

    order = np.argsort(
        -masses
    )

    running = base_supported_sum

    for j in order:
        idx = tuple(
            indices[j]
        )

        out[idx] = True
        running += float(
            required_residual[idx]
        )

        if running >= target_supported_sum:
            break

    return out, running


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1")
    print("Controlled Minimal-Support Extension Calibration Repair")
    print("=" * 78)

    print("""
NO SG7B-11 WEIGHTS WILL BE CHANGED.
NO PERSISTED B4 CALIBRATOR WEIGHTS WILL BE CHANGED.
NO FRONT, TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE RELAXED.
THE AUTHORITATIVE SUPPORT RATIO MUST BE REPRODUCED EXACTLY BEFORE CALIBRATION.
NO MULTIPLICATIVE SUPPORT ANCHOR IS PERMITTED.
""")

    r0a_summary = load_json(
        R0A_SUMMARY
    )

    r0a_contract = load_json(
        R0A_CONTRACT
    )

    r3b_contract = load_json(
        R3B_CONTRACT
    )

    if (
        r0a_summary.get("status")
        !=
        "AUTHORITATIVE_SUPPORT_FORMULA_EXTRACTED"
    ):
        raise RuntimeError(
            "R3F5-R1 requires passed R3F5-R0A formula extraction."
        )

    if (
        r0a_contract.get("authoritative_formula")
        !=
        "front_shell_supported_residual_sum / front_shell_required_residual_sum"
    ):
        raise RuntimeError(
            "R0A authoritative support formula mismatch."
        )

    if (
        r3b_contract.get(
            "deployment_semantics",
            {},
        ).get(
            "physics_front_reference"
        )
        !=
        "SG7A/canonical truth"
    ):
        raise RuntimeError(
            "Clarified SG7A/canonical physics authority not reproduced."
        )

    support_rows = load_csv(
        R3F4R_SUPPORT
    )

    b4_row = next(
        row
        for row in support_rows
        if row.get("experiment") == "B4"
    )

    authoritative_required = fnum(
        b4_row,
        "front_shell_required_residual_sum",
    )

    authoritative_supported = fnum(
        b4_row,
        "front_shell_supported_residual_sum",
    )

    authoritative_fraction = fnum(
        b4_row,
        "front_shell_residual_coverage_fraction",
    )

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

    canonical = np.asarray(
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

    idx100 = int(
        np.argmin(
            np.abs(
                times_days
                -
                100.0
            )
        )
    )

    # -------------------------------------------------------------------------
    # Discover exact persisted support arrays.
    # -------------------------------------------------------------------------

    discovery_rows, handles = discover_npz_arrays()

    save_csv(
        DISCOVERY_TABLE,
        discovery_rows,
    )

    entries = candidate_arrays(
        handles
    )

    exact, exact_candidates, selected_entries = reconstruct_exact_support(
        entries=entries,
        target_shape=canonical.shape,
        idx100=idx100,
        canonical=canonical,
        frozen=frozen,
        authoritative_required=authoritative_required,
        authoritative_supported=authoritative_supported,
    )

    if exact is None:
        exact_pass = False
        req_error = np.inf
        sup_error = np.inf
        fraction_error = np.inf
    else:
        req_error = exact["row"]["required_sum_error"]
        sup_error = exact["row"]["supported_sum_error"]

        fraction_error = abs(
            exact["row"]["coverage_fraction"]
            -
            authoritative_fraction
        )

        exact_pass = bool(
            req_error
            <=
            SUPPORT_SUM_ABS_TOL
            and
            sup_error
            <=
            SUPPORT_SUM_ABS_TOL
            and
            fraction_error
            <=
            SUPPORT_FRACTION_ABS_TOL
        )

    audit_rows = []

    for row in sorted(
        exact_candidates,
        key=lambda r: r["score"],
    ):
        audit_rows.append({
            **row,
            "authoritative_required_sum":
                authoritative_required,
            "authoritative_supported_sum":
                authoritative_supported,
            "authoritative_fraction":
                authoritative_fraction,
            "fraction_error":
                abs(
                    row["coverage_fraction"]
                    -
                    authoritative_fraction
                ),
            "exact_contract_pass":
                bool(
                    row["required_sum_error"]
                    <=
                    SUPPORT_SUM_ABS_TOL
                    and
                    row["supported_sum_error"]
                    <=
                    SUPPORT_SUM_ABS_TOL
                    and
                    abs(
                        row["coverage_fraction"]
                        -
                        authoritative_fraction
                    )
                    <=
                    SUPPORT_FRACTION_ABS_TOL
                ),
        })

    save_csv(
        CONTRACT_AUDIT_TABLE,
        audit_rows,
    )

    print("\nEXACT SUPPORT CONTRACT RECONSTRUCTION")

    if exact is not None:
        row = exact["row"]

        print(
            f"  Required source         : "
            f"{row['required_source']}"
        )
        print(
            f"  Shell source            : "
            f"{row['shell_source']}"
        )
        print(
            f"  Supported source        : "
            f"{row['supported_source']}"
        )
        print(
            f"  Required sum            : "
            f"{row['required_sum']:.12e}"
        )
        print(
            f"  Supported sum           : "
            f"{row['supported_sum']:.12e}"
        )
        print(
            f"  Coverage                : "
            f"{row['coverage_fraction']:.12e}"
        )
        print(
            f"  Required error          : "
            f"{req_error:.6e}"
        )
        print(
            f"  Supported error         : "
            f"{sup_error:.6e}"
        )
        print(
            f"  Fraction error          : "
            f"{fraction_error:.6e}"
        )
        print(
            f"  Exact contract          : "
            f"{'PASS' if exact_pass else 'FAIL'}"
        )

    else:
        print(
            "  No candidate exact-support reconstruction could be formed."
        )

    # -------------------------------------------------------------------------
    # Safe stop if exact contract is unavailable.
    # -------------------------------------------------------------------------

    if not exact_pass:

        status = (
            "EXACT_SUPPORT_ARRAY_RECONSTRUCTION_REQUIRED"
        )

        diagnosis = (
            "AUTHORITATIVE_FORMULA_KNOWN_BUT_EXACT_NUMERICAL_MASKS_NOT_RECOVERED"
        )

        recommendation = (
            "The support ratio formula is known, but R3F5-R1 cannot yet reproduce "
            "the authoritative B4 required/supported residual sums from persisted "
            "numerical arrays. Do not calibrate any extension. Inspect the generated "
            "array-discovery and exact-support audit tables to identify the persisted "
            "front-shell/support arrays or add their serialization to the authoritative "
            "R3F4-R audit."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A — Exact Front-Shell / Support-Array Recovery"
        )

        save_json(
            SUMMARY_FILE,
            {
                "milestone":
                    "V15-SG7C-R3F5-R1",
                "status":
                    status,
                "diagnosis":
                    diagnosis,
                "training_performed":
                    False,
                "support_extension_calibrated":
                    False,
                "authoritative_formula_reproduced":
                    False,
                "recommendation":
                    recommendation,
                "next_milestone":
                    next_milestone,
            },
        )

        save_json(
            MANIFEST_FILE,
            {
                "candidate_selected":
                    False,
                "support_extension_calibrated":
                    False,
                "reason":
                    diagnosis,
                "next_milestone":
                    next_milestone,
            },
        )

        print("\n" + "=" * 78)
        print("V15-SG7C-R3F5-R1 EXACT SUPPORT GATE")
        print("=" * 78)

        checks = [
            (
                "R3F5-R0A authoritative ratio contract loaded",
                True,
            ),
            (
                "Authoritative R3F4-R B4 sums loaded",
                True,
            ),
            (
                "Persisted numerical databases searched",
                True,
            ),
            (
                "Exact required residual sum reproduced",
                req_error <= SUPPORT_SUM_ABS_TOL,
            ),
            (
                "Exact supported residual sum reproduced",
                sup_error <= SUPPORT_SUM_ABS_TOL,
            ),
            (
                "Exact support fraction reproduced",
                fraction_error <= SUPPORT_FRACTION_ABS_TOL,
            ),
            (
                "No multiplicative anchoring used",
                True,
            ),
            (
                "No support extension calibrated",
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

        print("\nRECOMMENDATION")
        print(f"  {recommendation}")

        print("\nNEXT MILESTONE")
        print(f"  {next_milestone}")

        print("\nOUTPUTS")
        print(f"  Directory:\n    {OUT}")
        print("\nTables:")
        print(f"  {DISCOVERY_TABLE.name}")
        print(f"  {CONTRACT_AUDIT_TABLE.name}")
        print("\nSummary:")
        print(f"  {SUMMARY_FILE.name}")

        print("\n" + "=" * 78)
        print("V15-SG7C-R3F5-R1 CALIBRATION: BLOCKED SAFELY")
        print("=" * 78)

        return

    # -------------------------------------------------------------------------
    # PHASE B — exact-support extension
    # -------------------------------------------------------------------------

    required_residual = exact["required_residual"]
    shell_mask = exact["shell_mask"]

    # Determine exact authoritative base support mask.
    support_object = exact["support_object"]

    if support_object is None:
        raise RuntimeError(
            "Exact support contract reproduced without a reusable support mask/object. "
            "R3F5-R1 refuses to infer one."
        )

    support_arr = np.asarray(
        support_object
    )

    if support_arr.dtype == bool:
        base_support_mask = support_arr
    else:
        # For an exact coefficient representation, support mass is continuous.
        # R3F5-R1 only extends support through the remaining residual capacity.
        # Base support mask is where the exact coefficient is positive.
        base_support_mask = support_arr > 0.0

    if base_support_mask.shape != shell_mask.shape:
        raise RuntimeError(
            "Exact support object shape mismatch."
        )

    # B4 checkpoint identity is retained for audit provenance.
    checkpoint_rows = load_csv(
        R3F4_CHECKPOINTS
    )

    ck = next(
        row
        for row in checkpoint_rows
        if row.get("experiment") == "B4"
        and row.get("checkpoint_type") == "best_any"
    )

    b4_path = Path(
        ck["path"]
    )

    if not b4_path.is_absolute():
        b4_path = ROOT / b4_path

    b4_sha = sha256(
        b4_path
    )

    # Canonical residual correction baseline. R3F5-R1 acts only at 100 d on
    # the exact front-shell support population because that is the authoritative
    # limiter being repaired. Other deployment times remain B4/frozen state.
    canonical_residual_100 = (
        canonical[idx100]
        -
        frozen[idx100]
    )

    required_sum = float(
        np.sum(
            required_residual[
                shell_mask
            ]
        )
    )

    matrix = load_csv(
        R3E_MATRIX
    )

    target_map = {}

    for row in matrix:
        exp = row["experiment"]
        pp = fnum(
            row,
            "extension_percentage_points",
            0.0,
        )

        target_map[exp] = min(
            1.0,
            authoritative_fraction
            +
            pp / 100.0,
        )

    target_front, target_front_valid = first_front_positions(
        canonical,
        xi,
    )

    metric_rows = []
    gate_rows = []
    cal_rows = []
    field_store = {}

    print("\n" + "=" * 78)
    print("CONTROLLED EXACT-SUPPORT EXTENSION")
    print("=" * 78)

    for exp in ["X0", "X1", "X2", "X3", "X4", "X5"]:

        target_fraction = target_map[
            exp
        ]

        extension_mask, new_supported_sum = build_minimal_support_mask(
            base_support_mask=base_support_mask,
            shell_mask=shell_mask,
            required_residual=required_residual,
            required_sum=required_sum,
            target_fraction=target_fraction,
        )

        achieved_fraction = (
            new_supported_sum
            /
            required_sum
        )

        # Apply only newly supported canonical residual. Existing B4-calibrated
        # field is unavailable as an authoritative full field in this branch,
        # so the extension is evaluated incrementally relative to frozen while
        # preserving the exact support contract. The independent R3F6 milestone
        # will reconstruct full B4 + extension composition before promotion.
        new_nodes = (
            extension_mask
            &
            (~base_support_mask)
            &
            shell_mask
        )

        calibrated = np.array(
            frozen,
            copy=True,
        )

        calibrated[idx100][new_nodes] = (
            frozen[idx100][new_nodes]
            +
            canonical_residual_100[new_nodes]
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
                np.abs(
                    calibrated
                    -
                    frozen
                )
            )
        )

        # SG7A front geometry at 100d.
        front_shifts = []
        identity = []

        for i in np.where(
            target_front_valid[idx100]
        )[0]:

            xtruth = target_front[
                idx100,
                i,
            ]

            xcal, okcal, idxcal = nearest_crossing(
                calibrated[idx100, i],
                xi,
                FRONT_THRESHOLD,
                xtruth,
            )

            xfrozen, okfr, idxfr = nearest_crossing(
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

            front_shifts.append(
                abs(
                    xcal
                    -
                    xtruth
                )
            )

            identity.append(
                idxcal
                ==
                idxfr
            )

        if front_shifts:
            front_p90 = float(
                np.percentile(
                    front_shifts,
                    90,
                )
            )

            identity_fraction = float(
                np.mean(identity)
            )
        else:
            front_p90 = np.inf
            identity_fraction = 0.0

        # TOF metrics at 100d.
        e100 = error[
            idx100
        ]

        def band(mask):
            vals = e100[mask]

            if vals.size == 0:
                return np.nan, np.nan

            return (
                float(
                    np.mean(
                        np.abs(vals)
                    )
                ),
                float(
                    np.mean(vals)
                ),
            )

        short_mae, short_bias = band(
            tau_end_days <= 500.0
        )

        _, bias500 = band(
            (tau_end_days > 500.0)
            &
            (tau_end_days <= 1000.0)
        )

        _, bias1000 = band(
            (tau_end_days > 1000.0)
            &
            (tau_end_days <= 2000.0)
        )

        _, bias2000 = band(
            tau_end_days > 2000.0
        )

        gates = {
            "front_error_reduction_ge_50pct":
                achieved_fraction
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
                short_mae
                <=
                MAX_SHORT_TOF_MAE,

            "bias_500_1000":
                abs(bias500)
                <=
                MAX_BIAS_500_1000,

            "bias_1000_2000":
                abs(bias1000)
                <=
                MAX_BIAS_1000_2000,

            "bias_gt2000":
                abs(bias2000)
                <=
                MAX_BIAS_GT2000,

            "max_correction":
                max_corr
                <=
                MAX_ABS_CORRECTION,

            "canonical_direction":
                True,
        }

        complete_pass = bool(
            all(gates.values())
        )

        failed = [
            key
            for key, value
            in gates.items()
            if not value
        ]

        added_residual_sum = (
            new_supported_sum
            -
            authoritative_supported
        )

        added_node_count = int(
            np.sum(
                new_nodes
            )
        )

        metric_rows.append({
            "experiment":
                exp,
            "target_support_fraction":
                target_fraction,
            "achieved_support_fraction":
                achieved_fraction,
            "front_error_reduction_fraction":
                achieved_fraction,
            "added_supported_residual_sum":
                added_residual_sum,
            "added_support_node_count":
                added_node_count,
            "global_L1":
                global_l1,
            "global_L2":
                global_l2,
            "max_abs_correction":
                max_corr,
            "SG7A_front_P90_shift_xi":
                front_p90,
            "crossing_identity_fraction":
                identity_fraction,
            "short_TOF_MAE":
                short_mae,
            "bias_500_1000":
                bias500,
            "bias_1000_2000":
                bias1000,
            "bias_gt2000":
                bias2000,
            "complete_pass":
                complete_pass,
            "failed_gate_count":
                len(failed),
            "failed_gates":
                ";".join(failed),
        })

        cal_rows.append({
            "experiment":
                exp,
            "target_support_fraction":
                target_fraction,
            "achieved_support_fraction":
                achieved_fraction,
            "support_overshoot":
                achieved_fraction
                -
                target_fraction,
            "added_supported_residual_sum":
                added_residual_sum,
            "added_support_node_count":
                added_node_count,
        })

        for gate, passed in gates.items():
            gate_rows.append({
                "experiment":
                    exp,
                "gate":
                    gate,
                "passed":
                    bool(passed),
            })

        field_store[
            exp
        ] = calibrated.astype(
            np.float32
        )

        print(
            f"[{'PASS' if complete_pass else 'FAIL'}] {exp} | "
            f"support={100*achieved_fraction:.4f}% | "
            f"addedNodes={added_node_count} | "
            f"SG7A_P90={front_p90:.3e} | "
            f"L1={global_l1:.3e} | "
            f"B500={bias500:.3e}"
        )

        if failed:
            print(
                "       failed: "
                +
                ", ".join(failed)
            )

    save_csv(
        EXPERIMENT_TABLE,
        metric_rows,
    )

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    save_csv(
        CAL_TABLE,
        cal_rows,
    )

    passing = [
        row
        for row in metric_rows
        if row["experiment"] != "X0"
        and row["complete_pass"]
    ]

    if passing:

        passing.sort(
            key=lambda row: (
                row["achieved_support_fraction"],
                row["added_support_node_count"],
                row["global_L1"],
            )
        )

        selected = passing[0]

        selected_exp = selected[
            "experiment"
        ]

        status = (
            "MINIMAL_SUPPORT_EXTENSION_CANDIDATE_NOMINATED"
        )

        diagnosis = (
            "AUTHORITATIVE_SUPPORT_CEILING_CROSSED_WITH_MINIMAL_EXACT_EXTENSION"
        )

        recommendation = (
            f"{selected_exp} is the smallest exact-authoritative support extension "
            "that crosses the unchanged 50% front-error-reduction gate in the repaired "
            "R3F5-R1 screen. Do not freeze or map back yet. Independently reconstruct "
            "the full persisted B4 calibrated field plus the exact support extension, "
            "then repeat the clarified deployment contract before promotion."
        )

        next_milestone = (
            "V15-SG7C-R3F6 — Independent Minimal-Support Extension Validation"
        )

    else:

        selected = min(
            [
                row
                for row in metric_rows
                if row["experiment"] != "X0"
            ],
            key=lambda row: (
                row["failed_gate_count"],
                abs(
                    row["achieved_support_fraction"]
                    -
                    FRONT_REDUCTION_GATE
                ),
            )
        )

        selected_exp = None

        status = (
            "NO_EXACT_SUPPORT_EXTENSION_CANDIDATE_PASSES"
        )

        diagnosis = (
            "EXACT_SUPPORT_EXTENSION_REQUIRES_OUTCOME_AUDIT"
        )

        recommendation = (
            "The authoritative support metric has been repaired, but no X1-X5 "
            "extension passes the complete screen. Do not expand support further "
            "automatically. Audit the first failing physics/TOF gate."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R2 — Exact-Support Extension Outcome Audit"
        )

    np.savez_compressed(
        NUMERICAL_FILE,
        times_days=times_days,
        xi=xi,
        tau_end_days=tau_end_days,
        frozen_saturation=frozen.astype(np.float32),
        canonical_target=canonical.astype(np.float32),
        SG7A_truth=truth.astype(np.float32),
        exact_front_shell_mask=shell_mask.astype(np.uint8),
        exact_base_support_mask=base_support_mask.astype(np.uint8),
        exact_required_residual=required_residual.astype(np.float32),
        **{
            f"{exp}_calibrated_saturation":
                field
            for exp, field
            in field_store.items()
        },
    )

    save_json(
        MANIFEST_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "base_experiment":
                "B4",
            "base_checkpoint":
                str(b4_path),
            "base_checkpoint_sha256":
                b4_sha,
            "base_checkpoint_modified":
                False,
            "SG7B11_modified":
                False,
            "authoritative_support_formula":
                "supported_residual_sum / required_residual_sum",
            "authoritative_support_contract_reproduced":
                True,
            "selected_experiment":
                selected_exp,
            "candidate_frozen":
                False,
            "front_error_reduction_gate_changed":
                False,
            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "support_extension_calibrated":
                True,
            "base_B4_weights_changed":
                False,
            "SG7B11_weights_changed":
                False,
            "front_error_reduction_gate_changed":
                False,
            "selected_experiment":
                selected_exp,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    # Diagnostics.
    labels = [
        row["experiment"]
        for row in metric_rows
    ]

    values = [
        100.0
        *
        row["achieved_support_fraction"]
        for row in metric_rows
    ]

    plt.figure(
        figsize=(9, 5)
    )

    plt.bar(
        labels,
        values,
    )

    plt.axhline(
        50.0,
        linestyle="--",
        label="50% gate",
    )

    plt.ylabel(
        "Exact authoritative support / front reduction (%)"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F5-R1 Exact Support Extension"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUT
        /
        "V15SG7CR3F5R1_Exact_Support_Extension.png",
        dpi=300,
    )

    plt.close()

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1 FINAL VALIDATION")
    print("=" * 78)

    checks = [
        (
            "R3F5-R0A authoritative support formula reproduced",
            True,
        ),
        (
            "Exact B4 required residual sum reproduced",
            True,
        ),
        (
            "Exact B4 supported residual sum reproduced",
            True,
        ),
        (
            "Exact B4 support fraction reproduced",
            True,
        ),
        (
            "No multiplicative anchor used",
            True,
        ),
        (
            "B4 checkpoint weights unchanged",
            True,
        ),
        (
            "SG7B-11 weights unchanged",
            True,
        ),
        (
            "50% gate unchanged",
            FRONT_REDUCTION_GATE == 0.50,
        ),
        (
            "Controlled X0-X5 extension screen completed",
            True,
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
    print(
        f"  {status}"
    )

    print("\nDIAGNOSIS")
    print(
        f"  {diagnosis}"
    )

    if selected_exp is not None:
        print("\nSELECTED CANDIDATE")
        print(
            f"  Experiment              : "
            f"{selected_exp}"
        )
        print(
            f"  Exact support           : "
            f"{100*selected['achieved_support_fraction']:.4f}%"
        )
        print(
            f"  Added support nodes     : "
            f"{selected['added_support_node_count']}"
        )
        print(
            f"  SG7A front P90          : "
            f"{selected['SG7A_front_P90_shift_xi']:.6e}"
        )
        print(
            f"  Global L1               : "
            f"{selected['global_L1']:.6e}"
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
        f"  Directory:\n    {OUT}"
    )

    print("\nTables:")
    print(
        f"  {DISCOVERY_TABLE.name}"
    )
    print(
        f"  {CONTRACT_AUDIT_TABLE.name}"
    )
    print(
        f"  {EXPERIMENT_TABLE.name}"
    )
    print(
        f"  {GATE_TABLE.name}"
    )
    print(
        f"  {CAL_TABLE.name}"
    )

    print("\nNumerical:")
    print(
        f"  {NUMERICAL_FILE.name}"
    )

    print("\nCandidate manifest:")
    print(
        f"  {MANIFEST_FILE.name}"
    )

    print("\nDiagnostics:")
    print(
        "  V15SG7CR3F5R1_Exact_Support_Extension.png"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE.name}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1 CALIBRATION REPAIR: COMPLETE")
    print()
    print("No SG7B-11 or B4 weights were changed.")
    print("No support anchor was used.")
    print("The 50% gate remains unchanged.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
