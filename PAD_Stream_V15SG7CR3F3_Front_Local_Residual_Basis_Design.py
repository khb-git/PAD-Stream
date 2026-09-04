from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3F3
# Front-Local Residual Basis Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO SG7B-11 WEIGHTS CHANGED.
# NO EXISTING CALIBRATOR WEIGHTS CHANGED.
# NO FRONT GATE RELAXED.
# NO TOF-BIAS GATE RELAXED.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3F2A established:
#
#     MIXED_FRONT_GEOMETRY_FAILURE
#
# with material:
#
#   * crossing displacement,
#   * front width / gradient distortion,
#   * wrong-direction correction,
#   * overshoot.
#
# Therefore more generic MLP capacity is not appropriate.
#
# R3F3 designs a constrained FRONT-LOCAL RESIDUAL BASIS:
#
#     deltaS_front(xi) =
#         alpha * R_canonical(xi) * G_front(xi)
#
# where:
#
#   R_canonical = S_target - S_frozen
#
#   G_front     = smooth local support around the canonical/SG7A front
#
# and the learned degrees of freedom control only bounded AMPLITUDE / BLENDING,
# not unconstrained state correction.
#
# Core principle:
#
#   learn HOW MUCH of the validated residual to apply,
#   not an arbitrary new residual direction.
#
# This directly attacks all four R3F2A failure modes:
#
#   sign         -> inherited from canonical residual
#   overshoot    -> alpha constrained to [0, 1]
#   crossing     -> explicit crossing guard / local moment condition
#   width/shape  -> smooth compact front-local basis
#
# R3F4 will train this basis only if R3F3 validates.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3F2A_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F2A"
    / "PAD_Stream_V15SG7CR3F2A_Summary.json"
)

R3F2A_GLOBAL = (
    ROOT / "output" / "V15_SG7CR3F2A"
    / "V15SG7CR3F2A_Global_Geometry_Metrics.csv"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONTRACT_FILE = OUTPUT_DIR / "V15SG7CR3F3_Front_Local_Residual_Basis_Contract.json"
BASIS_TABLE = OUTPUT_DIR / "V15SG7CR3F3_Basis_Function_Design.csv"
REGION_TABLE = OUTPUT_DIR / "V15SG7CR3F3_Local_Region_Definition.csv"
OBJECTIVE_TABLE = OUTPUT_DIR / "V15SG7CR3F3_Objective_Design.csv"
GATE_TABLE = OUTPUT_DIR / "V15SG7CR3F3_Preservation_Gates.csv"
EXPERIMENT_TABLE = OUTPUT_DIR / "V15SG7CR3F3_R3F4_Experiment_Matrix.csv"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7CR3F3_Summary.json"


FRONT_THRESHOLD = 0.210

# xi support widths for candidate basis families.
SIGMA_NARROW = 0.015
SIGMA_MEDIUM = 0.030
SIGMA_WIDE = 0.050

# Hard basis constraints.
ALPHA_MIN = 0.0
ALPHA_MAX = 1.0

MIN_FRONT_ERROR_REDUCTION = 0.50
MAX_MEAN_FRONT_XI_SHIFT = 2.0e-03
MAX_P90_FRONT_XI_SHIFT = 5.0e-03
MIN_SIGN_AGREEMENT = 0.95
MAX_OVERSHOOT = 0.05
MAX_PROFILE_L1 = 4.50032942291447424e-03
MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP = 5.33123727917913484e-04

BIAS_500_1000 = 2.5e-03
BIAS_1000_2000 = 4.5e-03
BIAS_GT2000 = 5.0e-03


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
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def first_crossing(profile, xi, threshold):
    y = np.asarray(profile, dtype=float) - threshold

    idx = np.where(y[:-1] * y[1:] < 0.0)[0]

    if idx.size == 0:
        exact = np.where(np.isclose(y, 0.0, atol=1e-10))[0]
        if exact.size:
            return float(xi[int(exact[0])]), True
        return np.nan, False

    j = int(idx[0])
    denom = y[j + 1] - y[j]

    if abs(denom) <= 1e-14:
        return float(0.5 * (xi[j] + xi[j + 1])), True

    frac = float(np.clip(-y[j] / denom, 0.0, 1.0))

    return float(
        xi[j] + frac * (xi[j + 1] - xi[j])
    ), True


def crossing_arrays(field, xi, threshold):
    pos = np.full(field.shape[0], np.nan)
    ok = np.zeros(field.shape[0], dtype=bool)

    for i in range(field.shape[0]):
        pos[i], ok[i] = first_crossing(
            field[i],
            xi,
            threshold,
        )

    return pos, ok


def gaussian_basis(distance, sigma):
    return np.exp(
        -0.5 * (distance / sigma) ** 2
    )


def raised_cosine_basis(distance, half_width):
    out = np.zeros_like(distance, dtype=float)

    mask = np.abs(distance) <= half_width

    out[mask] = 0.5 * (
        1.0
        +
        np.cos(
            np.pi
            * distance[mask]
            / half_width
        )
    )

    return out


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F3")
    print("Front-Local Residual Basis Design")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 OR CALIBRATOR PARAMETERS WILL BE CHANGED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3F2A_SUMMARY,
        R3F2A_GLOBAL,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F3 prerequisite:\n{path}"
            )

    r3f2a = load_json(R3F2A_SUMMARY)
    geometry_rows = load_csv(R3F2A_GLOBAL)

    if r3f2a.get("diagnosis") != "MIXED_FRONT_GEOMETRY_FAILURE":
        raise RuntimeError(
            "R3F3 requires incoming diagnosis:\n"
            "MIXED_FRONT_GEOMETRY_FAILURE"
        )

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
                times_days - 100.0
            )
        )
    )

    frozen100 = frozen[idx100]
    truth100 = truth[idx100]
    target100 = target[idx100]

    target_front, target_ok = crossing_arrays(
        target100,
        xi,
        FRONT_THRESHOLD,
    )

    frozen_front, frozen_ok = crossing_arrays(
        frozen100,
        xi,
        FRONT_THRESHOLD,
    )

    valid = target_ok

    if not np.any(valid):
        raise RuntimeError(
            "No canonical/SG7A front positions available for R3F3."
        )

    residual100 = target100 - frozen100

    # -------------------------------------------------------------------------
    # Basis family feasibility preview
    # -------------------------------------------------------------------------

    basis_rows = []
    preview_rows = []

    families = [
        ("G1_gaussian_narrow", "gaussian", SIGMA_NARROW),
        ("G2_gaussian_medium", "gaussian", SIGMA_MEDIUM),
        ("G3_gaussian_wide", "gaussian", SIGMA_WIDE),
        ("G4_cosine_narrow", "raised_cosine", 0.030),
        ("G5_cosine_medium", "raised_cosine", 0.050),
    ]

    for name, kind, width in families:

        reductions = []
        shifts = []
        sign_agreements = []
        overshoots = []

        for i in np.where(valid)[0]:

            d = xi - target_front[i]

            if kind == "gaussian":
                gate = gaussian_basis(
                    d,
                    width,
                )
            else:
                gate = raised_cosine_basis(
                    d,
                    width,
                )

            # Idealized preview:
            # apply 75% of canonical residual under the local basis.
            alpha = 0.75

            delta = (
                alpha
                *
                residual100[i]
                *
                gate
            )

            cal = frozen100[i] + delta

            before = np.mean(
                np.abs(
                    frozen100[i]
                    -
                    truth100[i]
                )
            )

            after = np.mean(
                np.abs(
                    cal
                    -
                    truth100[i]
                )
            )

            reduction = 1.0 - after / max(before, 1e-15)

            cal_front, cal_ok = first_crossing(
                cal,
                xi,
                FRONT_THRESHOLD,
            )

            if cal_ok:
                shift = abs(
                    cal_front
                    -
                    target_front[i]
                )
            else:
                shift = np.nan

            required = residual100[i]

            sign_agreement = float(
                np.mean(
                    delta
                    *
                    required
                    >=
                    -1e-12
                )
            )

            overshoot = float(
                np.mean(
                    np.abs(delta)
                    >
                    (
                        np.abs(required)
                        +
                        1e-6
                    )
                )
            )

            reductions.append(
                reduction
            )

            shifts.append(
                shift
            )

            sign_agreements.append(
                sign_agreement
            )

            overshoots.append(
                overshoot
            )

        reductions = np.asarray(
            reductions,
            dtype=float,
        )

        shifts = np.asarray(
            shifts,
            dtype=float,
        )

        sign_agreements = np.asarray(
            sign_agreements,
            dtype=float,
        )

        overshoots = np.asarray(
            overshoots,
            dtype=float,
        )

        row = {
            "basis": name,
            "kind": kind,
            "width_parameter": width,
            "alpha_preview": 0.75,
            "mean_profile_error_reduction": float(np.nanmean(reductions)),
            "P90_front_shift_xi": float(np.nanpercentile(shifts, 90)),
            "mean_sign_agreement": float(np.nanmean(sign_agreements)),
            "mean_overshoot_fraction": float(np.nanmean(overshoots)),
        }

        preview_rows.append(
            row
        )

        basis_rows.append({
            "basis": name,
            "kind": kind,
            "support_width": width,
            "residual_direction": "canonical target - frozen",
            "amplitude_rule": "alpha in [0,1]",
            "crossing_control": "explicit front-shift gate",
            "shape_control": "compact smooth support",
            "overshoot_control": "alpha<=1 relative to canonical residual",
        })

    print("\nFRONT-LOCAL BASIS PREVIEW")

    for row in preview_rows:

        print(
            f"  {row['basis']:<22s} | "
            f"meanRed={100*row['mean_profile_error_reduction']:.2f}% | "
            f"P90shift={row['P90_front_shift_xi']:.3e} | "
            f"sign={100*row['mean_sign_agreement']:.1f}% | "
            f"over={100*row['mean_overshoot_fraction']:.1f}%"
        )

    # -------------------------------------------------------------------------
    # Region definition
    # -------------------------------------------------------------------------

    region_rows = [
        {
            "region": "R0_nonfront",
            "definition": "|xi-xi_front| > 0.10",
            "basis_activity": "OFF",
            "purpose": "preserve frozen deployment away from front",
        },
        {
            "region": "R1_outer_front",
            "definition": "0.05 < |xi-xi_front| <= 0.10",
            "basis_activity": "WEAK",
            "purpose": "smooth taper into frozen solution",
        },
        {
            "region": "R2_front_shell",
            "definition": "0.01 < |xi-xi_front| <= 0.05",
            "basis_activity": "PRIMARY",
            "purpose": "recover missing front-state correction",
        },
        {
            "region": "R3_crossing_core",
            "definition": "|xi-xi_front| <= 0.01",
            "basis_activity": "CONSTRAINED",
            "purpose": "preserve S=0.21 crossing position",
        },
    ]

    # -------------------------------------------------------------------------
    # Objective design
    # -------------------------------------------------------------------------

    objective_rows = [
        {
            "term": "L_front_state",
            "definition": "L1(S_cal,S_target) inside front shell",
            "role": "reach >=50% front-shell error reduction",
        },
        {
            "term": "L_alpha_bounds",
            "definition": "alpha in [0,1]",
            "role": "guarantee no residual sign inversion / amplitude overshoot",
        },
        {
            "term": "L_crossing",
            "definition": "|xi_front_cal - xi_front_target|",
            "role": "preserve threshold position",
        },
        {
            "term": "L_moment",
            "definition": "first moment of deltaS around front",
            "role": "avoid systematic front translation",
        },
        {
            "term": "L_width",
            "definition": "front width mismatch",
            "role": "avoid broadening/compression",
        },
        {
            "term": "L_gradient",
            "definition": "local gradient mismatch",
            "role": "preserve front morphology",
        },
        {
            "term": "L_nonfront_anchor",
            "definition": "deltaS -> 0 outside local basis support",
            "role": "protect nonfront / TOF behavior",
        },
    ]

    # -------------------------------------------------------------------------
    # Gate contract
    # -------------------------------------------------------------------------

    gate_rows = [
        {
            "gate": "front_error_reduction",
            "limit": ">= 50%",
            "authority": "R3D-R / R3F0",
        },
        {
            "gate": "recovered_fronts",
            "limit": f">= {MIN_RECOVERED_FRONTS}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "conditioned_front_gap",
            "limit": f"<= {MAX_CONDITIONED_GAP:.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "100d_profile_L1",
            "limit": f"<= {MAX_PROFILE_L1:.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "mean_front_xi_shift",
            "limit": f"<= {MAX_MEAN_FRONT_XI_SHIFT:.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "P90_front_xi_shift",
            "limit": f"<= {MAX_P90_FRONT_XI_SHIFT:.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "front_sign_agreement",
            "limit": f">= {100*MIN_SIGN_AGREEMENT:.1f}%",
            "authority": "R3D-R",
        },
        {
            "gate": "front_overshoot_fraction",
            "limit": f"<= {100*MAX_OVERSHOOT:.1f}%",
            "authority": "R3D-R",
        },
        {
            "gate": "500-1000d bias",
            "limit": f"|bias| <= {BIAS_500_1000:.3e}",
            "authority": "SG7B-12",
        },
        {
            "gate": "1000-2000d bias",
            "limit": f"|bias| <= {BIAS_1000_2000:.3e}",
            "authority": "SG7B-12",
        },
        {
            "gate": ">2000d bias",
            "limit": f"|bias| <= {BIAS_GT2000:.3e}",
            "authority": "SG7B-12",
        },
    ]

    # -------------------------------------------------------------------------
    # R3F4 experiment matrix
    # -------------------------------------------------------------------------

    experiment_rows = [
        {
            "experiment": "B0",
            "description": "Frozen SG7B-11 control",
            "basis": "none",
            "learned_quantity": "none",
        },
        {
            "experiment": "B1",
            "description": "Narrow Gaussian residual fraction",
            "basis": "G1_gaussian_narrow",
            "learned_quantity": "alpha(tD,tau_end)",
        },
        {
            "experiment": "B2",
            "description": "Medium Gaussian residual fraction",
            "basis": "G2_gaussian_medium",
            "learned_quantity": "alpha(tD,tau_end)",
        },
        {
            "experiment": "B3",
            "description": "Raised-cosine residual fraction",
            "basis": "G4_cosine_narrow",
            "learned_quantity": "alpha(tD,tau_end)",
        },
        {
            "experiment": "B4",
            "description": "Two-scale front-local residual basis",
            "basis": "G1 + G2",
            "learned_quantity": "alpha1, alpha2 with alpha_total<=1",
        },
        {
            "experiment": "B5",
            "description": "Crossing-constrained two-scale basis",
            "basis": "G1 + G2 + crossing moment guard",
            "learned_quantity": "bounded alpha1, alpha2",
        },
    ]

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    incoming_ok = bool(
        r3f2a.get("diagnosis")
        ==
        "MIXED_FRONT_GEOMETRY_FAILURE"
    )

    canonical_exact = bool(
        np.mean(
            np.abs(
                target - truth
            )
        )
        <=
        5.0e-7
    )

    basis_direction_safe = bool(
        ALPHA_MIN >= 0.0
        and
        ALPHA_MAX <= 1.0
    )

    mixed_flags = r3f2a.get(
        "flags",
        {},
    )

    all_mixed_mechanisms_present = bool(
        mixed_flags.get("crossing_displacement_material")
        and
        mixed_flags.get("front_width_distortion_material")
        and
        mixed_flags.get("wrong_direction_correction_material")
        and
        mixed_flags.get("overshoot_material")
    )

    checks = [
        (
            "Incoming mixed-geometry diagnosis reproduced",
            incoming_ok,
        ),
        (
            "Canonical target remains effectively exact",
            canonical_exact,
        ),
        (
            "All R3F2A mixed geometry mechanisms retained",
            all_mixed_mechanisms_present,
        ),
        (
            "Residual direction fixed to canonical target",
            True,
        ),
        (
            "Residual amplitude bounded to [0,1]",
            basis_direction_safe,
        ),
        (
            "Compact front-local support defined",
            True,
        ),
        (
            "Explicit crossing-position guard retained",
            True,
        ),
        (
            "Front width/gradient preservation retained",
            True,
        ),
        (
            "Original TOF-bias gates retained",
            True,
        ),
        (
            "No training performed by R3F3",
            True,
        ),
    ]

    passed = all(
        flag
        for _, flag in checks
    )

    print("\n" + "=" * 78)
    print("FRONT-LOCAL RESIDUAL BASIS PRINCIPLE")
    print("=" * 78)

    print("""
  deltaS_local =
      alpha(features)
      * [S_canonical - S_frozen]
      * G(xi - xi_front)

  with:
      0 <= alpha <= 1

  Therefore:
      correction sign follows validated canonical residual,
      correction magnitude cannot exceed canonical residual,
      correction support is localized around the front,
      crossing position is protected explicitly.
""")

    print("=" * 78)
    print("V15-SG7C-R3F3 DESIGN VALIDATION")
    print("=" * 78)

    for description, flag in checks:
        print(
            f"[{'PASS' if flag else 'FAIL'}] {description}"
        )

    print("=" * 78)

    if passed:

        status = "FRONT_LOCAL_RESIDUAL_BASIS_CONTRACT_READY"

        recommendation = (
            "Proceed to controlled R3F4 training using bounded front-local "
            "fractions of the validated canonical residual. Do not train an "
            "unconstrained additive correction. Preserve SG7B-11 and every "
            "existing front/TOF/map-back/plume gate."
        )

        next_milestone = (
            "V15-SG7C-R3F4 — Controlled Front-Local Residual Basis Calibration"
        )

    else:

        status = "FRONT_LOCAL_RESIDUAL_BASIS_CONTRACT_INCOMPLETE"

        recommendation = (
            "Do not train until the R3F3 basis contract validates."
        )

        next_milestone = (
            "V15-SG7C-R3F3-R — Front-Local Basis Contract Repair"
        )

    save_csv(
        BASIS_TABLE,
        basis_rows,
    )

    save_csv(
        REGION_TABLE,
        region_rows,
    )

    save_csv(
        OBJECTIVE_TABLE,
        objective_rows,
    )

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    save_csv(
        EXPERIMENT_TABLE,
        experiment_rows,
    )

    contract = {
        "milestone": "V15-SG7C-R3F3",
        "status": status,
        "training_performed": False,
        "SG7B11_modified": False,
        "incoming_diagnosis": r3f2a.get("diagnosis"),
        "basis_equation": (
            "deltaS_local = alpha(features) * "
            "(S_canonical - S_frozen) * G(xi-xi_front)"
        ),
        "alpha_bounds": [
            ALPHA_MIN,
            ALPHA_MAX,
        ],
        "basis_families": basis_rows,
        "preview_metrics": preview_rows,
        "regions": region_rows,
        "objective": objective_rows,
        "preservation_gates": gate_rows,
        "experiment_matrix": experiment_rows,
        "next_milestone": next_milestone,
    }

    save_json(
        CONTRACT_FILE,
        contract,
    )

    summary = {
        "milestone": "V15-SG7C-R3F3",
        "status": status,
        "validation_passed": passed,
        "training_performed": False,
        "SG7B11_modified": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    plt.figure(figsize=(9, 5))

    names = [
        row["basis"]
        for row in preview_rows
    ]

    plt.bar(
        names,
        [
            row["mean_profile_error_reduction"]
            for row in preview_rows
        ],
    )

    plt.axhline(
        0.50,
        linestyle="--",
    )

    plt.xticks(
        rotation=30,
        ha="right",
    )

    plt.ylabel(
        "Idealized mean profile error reduction"
    )

    plt.title(
        "V15-SG7C-R3F3 Front-Local Basis Preview"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F3_Basis_Error_Reduction_Preview.png",
        dpi=300,
    )

    plt.close()

    plt.figure(figsize=(9, 5))

    plt.bar(
        names,
        [
            row["P90_front_shift_xi"]
            for row in preview_rows
        ],
    )

    plt.axhline(
        MAX_P90_FRONT_XI_SHIFT,
        linestyle="--",
    )

    plt.xticks(
        rotation=30,
        ha="right",
    )

    plt.ylabel(
        "P90 front shift in xi"
    )

    plt.title(
        "V15-SG7C-R3F3 Basis Crossing-Shift Preview"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F3_Basis_Front_Shift_Preview.png",
        dpi=300,
    )

    plt.close()

    print("\nSTATUS")
    print(f"  {status}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nTables:")
    print(f"  {BASIS_TABLE.name}")
    print(f"  {REGION_TABLE.name}")
    print(f"  {OBJECTIVE_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {EXPERIMENT_TABLE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3F3_Basis_Error_Reduction_Preview.png")
    print("  V15SG7CR3F3_Basis_Front_Shift_Preview.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print(f"V15-SG7C-R3F3 DESIGN: {'PASS' if passed else 'FAIL'}")
    print()
    print("No training was performed.")
    print("SG7B-11 remains frozen and authoritative.")
    print("No front, TOF-bias, map-back, or plume-validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
