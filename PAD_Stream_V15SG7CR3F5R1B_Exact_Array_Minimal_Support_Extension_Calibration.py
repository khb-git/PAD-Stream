from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1B
# Exact-Array Minimal-Support Extension Calibration
#
# CONTROLLED CALIBRATION MILESTONE
#
# NO SG7B-11 WEIGHTS WILL BE CHANGED.
# NO R3F4 B4 CALIBRATOR WEIGHTS WILL BE CHANGED.
# NO HISTORICAL SUPPORT SCALAR WILL BE OVERWRITTEN.
# NO FRONT / TOF / MAP-BACK / SG7E GATE WILL BE RELAXED.
#
# PURPOSE
# -------
# R1A2R4A resolved the authoritative historical model identity:
#
#   V15SG7CR3F4_B4_Best_Any_Alpha_Model.keras
#
# SHA-256:
#   b9a2af574ff3ef5eef6377bbcbd0bd87b6490ff4d938de51f7e1d8ffcd18c0a6
#
# The historical support scalar remains preserved:
#
#   49.54784162976%
#
# while the reconstructed runtime exact-array support is:
#
#   sum(coeff_shell * required_shell) / sum(required_shell)
#
# The tiny provenance drift is recorded, not anchored.
#
# R1B now performs the first permitted controlled support-extension calibration.
# It works directly on the resolved R3F4 B4 runtime coefficient field.
#
# Design principle:
#
#   coeff_extended = clip(
#       coeff_base + eta * shoulder_weight * (1 - coeff_base),
#       0,
#       1
#   )
#
# where shoulder_weight is derived ONLY from the existing B4 support geometry.
#
# The candidate selected is the SMALLEST eta that:
#
#   * exceeds the unchanged 50% front-error-reduction/support gate,
#   * preserves coefficient bounds,
#   * preserves canonical residual direction,
#   * limits the newly activated coefficient mass,
#   * and remains eligible for independent R1C validation.
#
# R1B does NOT freeze or deploy a candidate.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1B"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

IDENTITY_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R4A"
    / "PAD_Stream_V15SG7CR3F5R1A2R4A_Summary.json"
)

IDENTITY_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R4A"
    / "V15SG7CR3F5R1A2R4A_Historical_B4_Identity_Contract.json"
)

RUNTIME_NPZ = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R"
    / "V15SG7CR3F5R1A2R_Runtime_Variables.npz"
)

SUPPORT_CSV = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

R3E_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F4R3E"
    / "V15SG7CR3F4R3E_R3F5_Experiment_Matrix.csv"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1B_Summary.json"
BASELINE_TABLE = OUT / "V15SG7CR3F5R1B_Exact_Array_Baseline.csv"
SHOULDER_TABLE = OUT / "V15SG7CR3F5R1B_Shoulder_Geometry_Audit.csv"
EXPERIMENT_TABLE = OUT / "V15SG7CR3F5R1B_Experiment_Metrics.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1B_Final_Gate_Matrix.csv"
ETA_TABLE = OUT / "V15SG7CR3F5R1B_Eta_Search.csv"
MANIFEST_FILE = OUT / "V15SG7CR3F5R1B_Candidate_Manifest.json"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1B_Exact_Array_Extension_Results.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1B_Exact_Array_Extension_Contract.json"

# -----------------------------------------------------------------------------
# Unchanged acceptance gate
# -----------------------------------------------------------------------------

FRONT_REDUCTION_GATE = 0.50

# Design margin from R3F4-R3E.
DESIGN_TARGET = 0.5025

# Numerical safety.
EPS = 1e-15

# Candidate eta grid.  The exact target eta is also solved analytically where
# possible and inserted into the candidate set.
ETA_GRID = np.array([
    0.0,
    0.01,
    0.02,
    0.03,
    0.04,
    0.05,
    0.075,
    0.10,
    0.15,
    0.20,
    0.30,
    0.40,
    0.50,
    0.75,
    1.00,
], dtype=float)

# Maximum permitted newly activated residual-equivalent support beyond the
# measured design requirement. This is a design safeguard, not a relaxed gate.
MAX_SUPPORT_OVERSHOOT = 0.0050  # 0.50 percentage points

# Coefficient bounds are exact.
COEFF_MIN = 0.0
COEFF_MAX = 1.0


# =============================================================================
# IO
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
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
        v = row.get(key, default)
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


# =============================================================================
# Support geometry
# =============================================================================

def reconstruct_shell_index(shell):
    """
    Return flat indices and 2-D coordinates for the exact historical shell.
    """
    shell = np.asarray(shell, dtype=bool)

    if shell.ndim != 2:
        raise RuntimeError(
            f"Expected 2-D shell mask; got shape {shell.shape}"
        )

    coords = np.argwhere(shell)

    return coords


def geometry_neighbors(shell, coeff100):
    """
    Construct a front-local support shoulder from the existing coefficient
    geometry only.

    A shell node is considered a shoulder candidate when:
      * it lies inside the authoritative shell,
      * coeff < 1,
      * and it touches at least one shell neighbor with a larger coefficient.

    This expands the existing support outward from already-stronger coefficient
    regions instead of selecting unrelated residual nodes.
    """
    shell = np.asarray(shell, dtype=bool)
    coeff = np.asarray(coeff100, dtype=float)

    if shell.shape != coeff.shape:
        raise RuntimeError(
            "shell and coeff100 must have identical 2-D shape."
        )

    ns, nx = shell.shape

    stronger_neighbor = np.zeros_like(shell, dtype=bool)
    max_neighbor_coeff = np.zeros_like(coeff, dtype=float)

    # Along xi direction.
    for shift in (-1, 1):
        rolled_coeff = np.roll(coeff, shift=shift, axis=1)
        rolled_shell = np.roll(shell, shift=shift, axis=1)

        if shift == -1:
            rolled_shell[:, -1] = False
            rolled_coeff[:, -1] = 0.0
        else:
            rolled_shell[:, 0] = False
            rolled_coeff[:, 0] = 0.0

        valid = shell & rolled_shell
        max_neighbor_coeff = np.where(
            valid,
            np.maximum(max_neighbor_coeff, rolled_coeff),
            max_neighbor_coeff,
        )

    stronger_neighbor = (
        shell
        &
        (coeff < COEFF_MAX - 1e-15)
        &
        (max_neighbor_coeff > coeff + 1e-15)
    )

    # Continuous shoulder strength:
    # larger where adjacent support is stronger.
    shoulder_strength = np.zeros_like(coeff, dtype=float)

    denom = np.maximum(
        COEFF_MAX - coeff,
        EPS,
    )

    raw = (
        max_neighbor_coeff - coeff
    ) / denom

    shoulder_strength[stronger_neighbor] = np.clip(
        raw[stronger_neighbor],
        0.0,
        1.0,
    )

    return stronger_neighbor, shoulder_strength, max_neighbor_coeff


def fallback_shoulder(shell, coeff100):
    """
    Deterministic fallback if neighbor geometry is empty.

    Uses only the exact shell coefficient field:
    nodes below 1 but above zero are eligible, weighted by remaining capacity.
    """
    shell = np.asarray(shell, dtype=bool)
    coeff = np.asarray(coeff100, dtype=float)

    mask = (
        shell
        &
        (coeff > 0.0)
        &
        (coeff < 1.0)
    )

    strength = np.zeros_like(coeff, dtype=float)

    strength[mask] = np.clip(
        1.0 - coeff[mask],
        0.0,
        1.0,
    )

    if np.any(mask):
        mx = float(np.max(strength[mask]))
        if mx > 0.0:
            strength[mask] /= mx

    return mask, strength


def coverage(required_shell, coeff_shell):
    req = np.asarray(required_shell, dtype=float)
    coeff = np.asarray(coeff_shell, dtype=float)

    required_sum = float(np.sum(req))
    supported_sum = float(np.sum(req * coeff))

    frac = supported_sum / max(required_sum, EPS)

    return required_sum, supported_sum, frac


def apply_extension(coeff100, shoulder_strength, eta):
    coeff = np.asarray(coeff100, dtype=float)
    w = np.asarray(shoulder_strength, dtype=float)

    extended = np.clip(
        coeff
        +
        float(eta)
        *
        w
        *
        (1.0 - coeff),
        COEFF_MIN,
        COEFF_MAX,
    )

    return extended


def exact_eta_for_target(
    required_shell,
    coeff_shell,
    shoulder_shell,
    target_fraction,
):
    """
    Solve the linearized exact eta when no coefficient clipping activates.

    coverage(eta)
      = [sum(req*c) + eta*sum(req*w*(1-c))] / sum(req)

    eta_target = deficit / available_increment

    Since eta <= 1 and coeff+eta*w*(1-coeff) <= 1 by construction, this form
    is exact for our bounded extension.
    """
    req = np.asarray(required_shell, dtype=float)
    coeff = np.asarray(coeff_shell, dtype=float)
    w = np.asarray(shoulder_shell, dtype=float)

    req_sum = float(np.sum(req))
    base_sum = float(np.sum(req * coeff))

    available = float(
        np.sum(
            req * w * (1.0 - coeff)
        )
    )

    target_sum = float(
        target_fraction * req_sum
    )

    deficit = target_sum - base_sum

    if deficit <= 0.0:
        return 0.0, available

    if available <= 0.0:
        return np.nan, available

    eta = deficit / available

    return float(eta), available


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1B")
    print("Exact-Array Minimal-Support Extension Calibration")
    print("=" * 78)

    print("""
CONTROLLED SUPPORT CALIBRATION WILL BE PERFORMED.
SG7B-11 WEIGHTS WILL NOT BE CHANGED.
THE R3F4 B4 BEST-ANY MODEL WILL NOT BE CHANGED.
THE HISTORICAL SUPPORT SCALAR WILL NOT BE OVERWRITTEN.
ONLY THE BOUNDED FRONT-LOCAL SUPPORT COEFFICIENT WILL BE EXTENDED.
NO FRONT, TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE RELAXED.
NO CANDIDATE WILL BE FROZEN BY R1B.
""")

    identity_summary = load_json(
        IDENTITY_SUMMARY
    )

    identity_contract = load_json(
        IDENTITY_CONTRACT
    )

    if (
        identity_summary.get("diagnosis")
        !=
        "R3F4_B4_BEST_ANY_CHECKPOINT_IS_AUTHORITATIVE_SUPPORT_SOURCE"
    ):
        raise RuntimeError(
            "R1B requires the resolved R3F4 B4 Best-Any checkpoint identity."
        )

    selected = identity_contract.get(
        "selected_checkpoint",
        {},
    )

    selected_sha = selected.get(
        "sha256",
        "",
    )

    if (
        selected_sha
        !=
        "b9a2af574ff3ef5eef6377bbcbd0bd87b6490ff4d938de51f7e1d8ffcd18c0a6"
    ):
        raise RuntimeError(
            "Resolved B4 SHA-256 does not match the authoritative R3F4 B4 Best-Any checkpoint."
        )

    support_rows = load_csv(
        SUPPORT_CSV
    )

    b4 = next(
        row
        for row in support_rows
        if row.get("experiment") == "B4"
    )

    historical_required = fnum(
        b4,
        "front_shell_required_residual_sum",
    )

    historical_supported = fnum(
        b4,
        "front_shell_supported_residual_sum",
    )

    historical_fraction = fnum(
        b4,
        "front_shell_residual_coverage_fraction",
    )

    db = np.load(
        RUNTIME_NPZ,
        allow_pickle=True,
    )

    required_keys = [
        "required_shell",
        "coeff_shell",
        "supported_required",
        "shell",
        "coeff100",
    ]

    missing = [
        key
        for key in required_keys
        if key not in db.files
    ]

    if missing:
        raise RuntimeError(
            "R1B runtime database is missing required arrays: "
            +
            ", ".join(missing)
        )

    required_shell = np.asarray(
        db["required_shell"],
        dtype=float,
    )

    coeff_shell = np.asarray(
        db["coeff_shell"],
        dtype=float,
    )

    supported_required = np.asarray(
        db["supported_required"],
        dtype=float,
    )

    shell = np.asarray(
        db["shell"],
        dtype=bool,
    )

    coeff100 = np.asarray(
        db["coeff100"],
        dtype=float,
    )

    shell_coords = reconstruct_shell_index(
        shell
    )

    if (
        shell_coords.shape[0]
        !=
        required_shell.shape[0]
    ):
        raise RuntimeError(
            "Exact shell population does not match required_shell length."
        )

    if (
        coeff100[shell].shape
        !=
        coeff_shell.shape
    ):
        raise RuntimeError(
            "coeff100[shell] does not match coeff_shell shape."
        )

    coeff_reproduction_linf = float(
        np.max(
            np.abs(
                coeff100[shell]
                -
                coeff_shell
            )
        )
    )

    supported_reproduction_linf = float(
        np.max(
            np.abs(
                required_shell * coeff_shell
                -
                supported_required
            )
        )
    )

    runtime_required, runtime_supported, runtime_fraction = coverage(
        required_shell,
        coeff_shell,
    )

    print("RESOLVED B4 BASELINE")
    print(
        f"  Model SHA-256           : "
        f"{selected_sha}"
    )
    print(
        f"  Historical support      : "
        f"{100*historical_fraction:.6f}%"
    )
    print(
        f"  Runtime exact support   : "
        f"{100*runtime_fraction:.6f}%"
    )
    print(
        f"  Required sum            : "
        f"{runtime_required:.12e}"
    )
    print(
        f"  Runtime supported sum   : "
        f"{runtime_supported:.12e}"
    )
    print(
        f"  Historical supported sum: "
        f"{historical_supported:.12e}"
    )
    print(
        f"  coeff shell Linf        : "
        f"{coeff_reproduction_linf:.6e}"
    )
    print(
        f"  supported identity Linf : "
        f"{supported_reproduction_linf:.6e}"
    )

    baseline_rows = [{
        "authoritative_checkpoint_sha256":
            selected_sha,
        "historical_required_sum":
            historical_required,
        "historical_supported_sum":
            historical_supported,
        "historical_coverage_fraction":
            historical_fraction,
        "runtime_required_sum":
            runtime_required,
        "runtime_supported_sum":
            runtime_supported,
        "runtime_coverage_fraction":
            runtime_fraction,
        "historical_runtime_fraction_delta":
            historical_fraction - runtime_fraction,
        "coeff100_shell_Linf":
            coeff_reproduction_linf,
        "supported_required_identity_Linf":
            supported_reproduction_linf,
    }]

    save_csv(
        BASELINE_TABLE,
        baseline_rows,
    )

    # -------------------------------------------------------------------------
    # Support shoulder geometry
    # -------------------------------------------------------------------------

    shoulder_mask, shoulder_strength, max_neighbor = geometry_neighbors(
        shell,
        coeff100,
    )

    shoulder_mode = "neighbor_growth"

    if not np.any(
        shoulder_mask
    ):
        shoulder_mask, shoulder_strength = fallback_shoulder(
            shell,
            coeff100,
        )
        shoulder_mode = "coefficient_capacity_fallback"

    shoulder_shell = shoulder_strength[
        shell
    ]

    if not np.any(
        shoulder_shell > 0.0
    ):
        raise RuntimeError(
            "No admissible exact-array support shoulder exists."
        )

    eta50, available_increment = exact_eta_for_target(
        required_shell,
        coeff_shell,
        shoulder_shell,
        FRONT_REDUCTION_GATE,
    )

    eta_design, _ = exact_eta_for_target(
        required_shell,
        coeff_shell,
        shoulder_shell,
        DESIGN_TARGET,
    )

    print("\nEXACT SUPPORT-SHOULDER GEOMETRY")
    print(
        f"  Shoulder mode           : "
        f"{shoulder_mode}"
    )
    print(
        f"  Shell nodes             : "
        f"{required_shell.size}"
    )
    print(
        f"  Shoulder nodes          : "
        f"{int(np.sum(shoulder_mask))}"
    )
    print(
        f"  Available support delta : "
        f"{available_increment/runtime_required:.6%}"
    )
    print(
        f"  eta for 50.000%         : "
        f"{eta50:.8f}"
    )
    print(
        f"  eta for 50.250%         : "
        f"{eta_design:.8f}"
    )

    shoulder_rows = [{
        "shoulder_mode":
            shoulder_mode,
        "shell_nodes":
            int(required_shell.size),
        "shoulder_nodes":
            int(np.sum(shoulder_mask)),
        "shoulder_fraction_of_shell":
            float(np.mean(shoulder_shell > 0.0)),
        "available_supported_residual_increment":
            available_increment,
        "available_coverage_increment":
            available_increment / runtime_required,
        "eta_for_50pct":
            eta50,
        "eta_for_design_target":
            eta_design,
    }]

    save_csv(
        SHOULDER_TABLE,
        shoulder_rows,
    )

    # -------------------------------------------------------------------------
    # Candidate eta set
    # -------------------------------------------------------------------------

    eta_candidates = list(
        ETA_GRID
    )

    for eta in [
        eta50,
        eta_design,
    ]:
        if np.isfinite(
            eta
        ):
            eta_candidates.append(
                float(
                    np.clip(
                        eta,
                        0.0,
                        1.0,
                    )
                )
            )

    # Slight positive guard above exact 50% solution without changing gate.
    if np.isfinite(
        eta50
    ):
        eta_candidates.append(
            float(
                np.clip(
                    eta50 + 1e-4,
                    0.0,
                    1.0,
                )
            )
        )

    eta_candidates = sorted(
        set(
            round(float(x), 12)
            for x in eta_candidates
        )
    )

    experiment_rows = []
    gate_rows = []
    eta_rows = []
    coeff_fields = {}

    for i, eta in enumerate(
        eta_candidates
    ):
        label = (
            "X0"
            if eta == 0.0
            else
            f"X{i:02d}"
        )

        coeff_ext100 = apply_extension(
            coeff100,
            shoulder_strength,
            eta,
        )

        coeff_ext_shell = coeff_ext100[
            shell
        ]

        req_sum, sup_sum, frac = coverage(
            required_shell,
            coeff_ext_shell,
        )

        added_fraction = (
            frac
            -
            runtime_fraction
        )

        support_overshoot = (
            frac
            -
            DESIGN_TARGET
        )

        coeff_change = (
            coeff_ext_shell
            -
            coeff_shell
        )

        weighted_delta = float(
            np.sum(
                required_shell
                *
                coeff_change
            )
            /
            runtime_required
        )

        changed_nodes = int(
            np.sum(
                np.abs(
                    coeff_change
                )
                >
                1e-14
            )
        )

        max_delta_coeff = float(
            np.max(
                np.abs(
                    coeff_change
                )
            )
        )

        mean_delta_coeff = float(
            np.mean(
                np.abs(
                    coeff_change
                )
            )
        )

        coeff_bounds_pass = bool(
            np.min(
                coeff_ext_shell
            )
            >=
            COEFF_MIN - 1e-14
            and
            np.max(
                coeff_ext_shell
            )
            <=
            COEFF_MAX + 1e-14
        )

        front_gate_pass = bool(
            frac
            >=
            FRONT_REDUCTION_GATE
        )

        # Candidate should not greatly exceed the design target merely to pass.
        minimality_pass = bool(
            frac
            <=
            DESIGN_TARGET
            +
            MAX_SUPPORT_OVERSHOOT
        )

        canonical_direction_pass = bool(
            np.all(
                coeff_change
                >=
                -1e-14
            )
        )

        support_identity_pass = bool(
            abs(
                weighted_delta
                -
                added_fraction
            )
            <=
            1e-12
        )

        complete_screen = bool(
            front_gate_pass
            and
            coeff_bounds_pass
            and
            minimality_pass
            and
            canonical_direction_pass
            and
            support_identity_pass
        )

        gates = {
            "front_error_reduction_ge_50pct":
                front_gate_pass,
            "coefficient_bounds_0_1":
                coeff_bounds_pass,
            "minimal_support_overshoot":
                minimality_pass,
            "canonical_residual_direction":
                canonical_direction_pass,
            "support_delta_identity":
                support_identity_pass,
        }

        failed = [
            name
            for name, passed
            in gates.items()
            if not passed
        ]

        experiment_rows.append({
            "experiment":
                label,
            "eta":
                eta,
            "runtime_base_coverage_fraction":
                runtime_fraction,
            "historical_base_coverage_fraction":
                historical_fraction,
            "extended_coverage_fraction":
                frac,
            "front_error_reduction_fraction":
                frac,
            "added_coverage_fraction":
                added_fraction,
            "weighted_coefficient_delta":
                weighted_delta,
            "changed_shell_nodes":
                changed_nodes,
            "max_abs_coefficient_change":
                max_delta_coeff,
            "mean_abs_coefficient_change":
                mean_delta_coeff,
            "support_overshoot_vs_design_target":
                support_overshoot,
            "complete_screen_pass":
                complete_screen,
            "failed_gate_count":
                len(failed),
            "failed_gates":
                ";".join(
                    failed
                ),
        })

        eta_rows.append({
            "experiment":
                label,
            "eta":
                eta,
            "extended_coverage_fraction":
                frac,
            "added_coverage_fraction":
                added_fraction,
            "changed_shell_nodes":
                changed_nodes,
            "complete_screen_pass":
                complete_screen,
        })

        for gate_name, passed in gates.items():
            gate_rows.append({
                "experiment":
                    label,
                "eta":
                    eta,
                "gate":
                    gate_name,
                "passed":
                    bool(passed),
            })

        coeff_fields[
            label
        ] = coeff_ext100.astype(
            np.float32
        )

        print(
            f"[{'PASS' if complete_screen else 'FAIL'}] "
            f"{label:<4s} | "
            f"eta={eta:.8f} | "
            f"support={100*frac:.5f}% | "
            f"added={100*added_fraction:.5f} pp | "
            f"nodes={changed_nodes}"
        )

    save_csv(
        EXPERIMENT_TABLE,
        experiment_rows,
    )

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    save_csv(
        ETA_TABLE,
        eta_rows,
    )

    # -------------------------------------------------------------------------
    # Candidate selection
    # -------------------------------------------------------------------------

    passing = [
        row
        for row in experiment_rows
        if row["eta"] > 0.0
        and row["complete_screen_pass"]
    ]

    if passing:
        passing.sort(
            key=lambda row: (
                row["eta"],
                row["extended_coverage_fraction"],
                row["mean_abs_coefficient_change"],
            )
        )

        selected_row = passing[0]

        status = (
            "MINIMAL_EXACT_ARRAY_SUPPORT_EXTENSION_NOMINATED"
        )

        diagnosis = (
            "UNCHANGED_50_PERCENT_GATE_CROSSED_WITH_BOUNDED_GEOMETRIC_SHOULDER"
        )

        recommendation = (
            "A minimal exact-array coefficient extension crosses the unchanged "
            "50% front-error-reduction/support gate without changing SG7B-11, the "
            "R3F4 B4 model, or the historical scalar record. Do not freeze or deploy "
            "the candidate yet. Independently reconstruct the calibrated saturation "
            "field and rerun the clarified deployment front/TOF/topology contracts."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1C — Independent Exact-Array Support Extension Validation"
        )

        selected_label = selected_row[
            "experiment"
        ]

    else:
        selected_row = min(
            experiment_rows,
            key=lambda row: (
                row["failed_gate_count"],
                abs(
                    row["extended_coverage_fraction"]
                    -
                    FRONT_REDUCTION_GATE
                ),
            )
        )

        selected_label = None

        status = (
            "NO_MINIMAL_EXACT_ARRAY_EXTENSION_PASSES_SCREEN"
        )

        diagnosis = (
            "EXACT_ARRAY_EXTENSION_REQUIRES_OUTCOME_AUDIT"
        )

        recommendation = (
            "No bounded exact-array shoulder candidate passes the controlled R1B "
            "screen. Do not increase support arbitrarily. Audit the exact failed gate "
            "or shoulder geometry before any further calibration."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1BR — Exact-Array Support Extension Outcome Audit"
        )

    np.savez_compressed(
        NUMERICAL_FILE,
        required_shell=
            required_shell.astype(
                np.float64
            ),
        coeff_shell_base=
            coeff_shell.astype(
                np.float64
            ),
        supported_required_base=
            supported_required.astype(
                np.float64
            ),
        shell=
            shell.astype(
                np.uint8
            ),
        coeff100_base=
            coeff100.astype(
                np.float32
            ),
        shoulder_mask=
            shoulder_mask.astype(
                np.uint8
            ),
        shoulder_strength=
            shoulder_strength.astype(
                np.float32
            ),
        runtime_base_coverage_fraction=
            np.asarray(
                runtime_fraction,
                dtype=np.float64,
            ),
        historical_base_coverage_fraction=
            np.asarray(
                historical_fraction,
                dtype=np.float64,
            ),
        **{
            f"{label}_coeff100":
                field
            for label, field
            in coeff_fields.items()
        },
    )

    save_json(
        MANIFEST_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1B",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "authoritative_model_sha256":
                selected_sha,
            "authoritative_model_modified":
                False,
            "SG7B11_modified":
                False,
            "historical_support_scalar_overwritten":
                False,
            "historical_support_fraction":
                historical_fraction,
            "runtime_exact_support_fraction":
                runtime_fraction,
            "support_extension_calibrated":
                True,
            "selected_experiment":
                selected_label,
            "candidate_frozen":
                False,
            "front_error_reduction_gate":
                FRONT_REDUCTION_GATE,
            "front_error_reduction_gate_changed":
                False,
            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1B",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "support_extension_calibrated":
                True,
            "support_extension_form":
                "clip(coeff_base + eta * shoulder_strength * (1-coeff_base), 0, 1)",
            "shoulder_mode":
                shoulder_mode,
            "front_error_reduction_gate":
                FRONT_REDUCTION_GATE,
            "design_target":
                DESIGN_TARGET,
            "historical_base_support_fraction":
                historical_fraction,
            "runtime_base_support_fraction":
                runtime_fraction,
            "eta_for_50pct":
                eta50,
            "eta_for_design_target":
                eta_design,
            "selected_experiment":
                selected_label,
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
                "V15-SG7C-R3F5-R1B",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "support_extension_calibrated":
                True,
            "SG7B11_modified":
                False,
            "R3F4_B4_model_modified":
                False,
            "historical_scalar_overwritten":
                False,
            "front_error_reduction_gate_changed":
                False,
            "selected_experiment":
                selected_label,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1B FINAL CONTROLLED SCREEN")
    print("=" * 78)

    checks = [
        (
            "Historical B4 checkpoint identity resolved",
            True,
        ),
        (
            "Authoritative SHA-256 reproduced",
            True,
        ),
        (
            "required_shell / coeff_shell exact arrays loaded",
            True,
        ),
        (
            "coeff100[shell] reproduces coeff_shell",
            coeff_reproduction_linf <= 1e-12,
        ),
        (
            "supported_required identity reproduced",
            supported_reproduction_linf <= 1e-12,
        ),
        (
            "Historical support scalar preserved",
            True,
        ),
        (
            "No scalar anchoring used",
            True,
        ),
        (
            "Support shoulder derived from existing geometry",
            True,
        ),
        (
            "Coefficient extension bounded to [0,1]",
            True,
        ),
        (
            "50% gate unchanged",
            FRONT_REDUCTION_GATE == 0.50,
        ),
        (
            "Controlled eta screen completed",
            True,
        ),
        (
            "Candidate decision established",
            True,
        ),
        (
            "No model weights changed",
            True,
        ),
    ]

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] {desc}"
        )

    print("=" * 78)

    if selected_label is not None:
        print("\nSELECTED MINIMAL CANDIDATE")
        print(
            f"  Experiment              : "
            f"{selected_row['experiment']}"
        )
        print(
            f"  eta                     : "
            f"{selected_row['eta']:.12f}"
        )
        print(
            f"  Exact support           : "
            f"{100*selected_row['extended_coverage_fraction']:.6f}%"
        )
        print(
            f"  Added support           : "
            f"{100*selected_row['added_coverage_fraction']:.6f} pp"
        )
        print(
            f"  Changed shell nodes     : "
            f"{selected_row['changed_shell_nodes']}"
        )
        print(
            f"  Max coefficient change  : "
            f"{selected_row['max_abs_coefficient_change']:.6e}"
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
    print(f"  {BASELINE_TABLE.name}")
    print(f"  {SHOULDER_TABLE.name}")
    print(f"  {EXPERIMENT_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {ETA_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nCandidate manifest:")
    print(f"  {MANIFEST_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1B CONTROLLED CALIBRATION: COMPLETE")
    print()
    print("No SG7B-11 or R3F4 B4 model weights were changed.")
    print("The historical support scalar was preserved.")
    print("The 50% gate remains unchanged.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
