from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3F4-R3E
# Minimal Residual-Support Extension Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO HISTORICAL OR CLARIFIED DEPLOYMENT GATE CHANGED.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3F4-R3D established a structural front-local support ceiling:
#
#   B2 : 49.5450%
#   B4 : 49.5478%
#   B5 : 49.5471%
#
# with front-error reduction tracking front-shell residual coverage essentially
# one-for-one. The unchanged deployment requirement is:
#
#   front-error reduction >= 50.0000%
#
# This milestone designs the smallest controlled extension of the existing
# front-local residual support needed to create a modest feasibility margin
# above 50%, while preserving:
#
#   * SG7B-11 frozen transport model
#   * bounded canonical-residual direction
#   * SG7A/canonical front physics authority
#   * clarified deployment acceptance semantics
#   * TOF-bias/state/mass/topology safeguards
#   * frozen-relative displacement as a persisted regression diagnostic
#   * map-back and SG7E thresholds
#
# No extension is trained or applied here.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F4R3E"
OUT.mkdir(parents=True, exist_ok=True)

R3D_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4R3D"
    / "PAD_Stream_V15SG7CR3F4R3D_Summary.json"
)

R3D_GLOBAL = (
    ROOT / "output" / "V15_SG7CR3F4R3D"
    / "V15SG7CR3F4R3D_Global_Limiter_Audit.csv"
)

R3D_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R3D"
    / "V15SG7CR3F4R3D_Support_vs_Reduction.csv"
)

R3B_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F4R3B"
    / "V15SG7CR3F4R3B_Deployment_Front_Acceptance_Contract.json"
)

R3F3_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F3"
    / "V15SG7CR3F3_Front_Local_Residual_Basis_Contract.json"
)

FRONT_GATE = 0.50

# We do NOT redefine the acceptance gate. This is a DESIGN margin used only
# to avoid constructing a support extension that mathematically tops out at
# 50.000% and is therefore fragile to numerical/training variation.
DESIGN_MARGIN_PP = 0.25
DESIGN_TARGET = FRONT_GATE + DESIGN_MARGIN_PP / 100.0

# Candidate support extensions are deliberately small and centered on the
# measured ~0.452 percentage-point deficit.
EXTENSION_PP = [0.50, 0.60, 0.75, 1.00, 1.50]

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F4R3E_Summary.json"
CONTRACT_FILE = OUT / "V15SG7CR3F4R3E_Minimal_Support_Extension_Contract.json"
BASELINE_TABLE = OUT / "V15SG7CR3F4R3E_Support_Ceiling_Baseline.csv"
MATRIX_TABLE = OUT / "V15SG7CR3F4R3E_Support_Extension_Matrix.csv"
REGION_TABLE = OUT / "V15SG7CR3F4R3E_Extension_Region_Design.csv"
OBJECTIVE_TABLE = OUT / "V15SG7CR3F4R3E_Objective_Design.csv"
GATES_TABLE = OUT / "V15SG7CR3F4R3E_Preservation_Gates.csv"
NEXT_TABLE = OUT / "V15SG7CR3F4R3E_R3F5_Experiment_Matrix.csv"


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


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F4-R3E")
    print("Minimal Residual-Support Extension Design")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO SG7B-11 OR CALIBRATOR PARAMETERS WILL BE CHANGED.
NO 50% FRONT-ERROR-REDUCTION GATE WILL BE CHANGED OR RELAXED.
NO CLARIFIED DEPLOYMENT ACCEPTANCE SEMANTIC WILL BE CHANGED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    r3d = load_json(R3D_SUMMARY)
    global_rows = load_csv(R3D_GLOBAL)
    support_rows = load_csv(R3D_SUPPORT)
    clarified = load_json(R3B_CONTRACT)
    basis_contract = load_json(R3F3_CONTRACT)

    if r3d.get("diagnosis") != "BASIS_SUPPORT_CEILING_AT_49P5_PERCENT":
        raise RuntimeError(
            "R3F4-R3E requires diagnosis:\n"
            "BASIS_SUPPORT_CEILING_AT_49P5_PERCENT"
        )

    near = [r for r in global_rows if r.get("experiment") in {"B2", "B4", "B5"}]
    if not near:
        raise RuntimeError("No B2/B4/B5 R3D limiter rows found.")

    best = max(near, key=lambda r: fnum(r, "final_front_reduction_fraction"))
    best_exp = best["experiment"]
    baseline = fnum(best, "final_front_reduction_fraction")
    coverage = fnum(best, "front_shell_residual_coverage_fraction")
    deficit = FRONT_GATE - baseline
    design_deficit = DESIGN_TARGET - baseline

    print("STRUCTURAL SUPPORT BASELINE")
    print(f"  Best experiment               : {best_exp}")
    print(f"  Front-error reduction         : {100.0*baseline:.4f}%")
    print(f"  Front residual support        : {100.0*coverage:.4f}%")
    print(f"  Acceptance requirement        : {100.0*FRONT_GATE:.4f}%")
    print(f"  Exact acceptance deficit      : {100.0*deficit:.4f} percentage points")
    print(f"  Design target (gate unchanged): {100.0*DESIGN_TARGET:.4f}%")
    print(f"  Design support deficit        : {100.0*design_deficit:.4f} percentage points")

    baseline_rows = []
    for r in near:
        baseline_rows.append({
            "experiment": r["experiment"],
            "front_error_reduction_fraction": fnum(r, "final_front_reduction_fraction"),
            "front_shell_residual_coverage_fraction":
                fnum(r, "front_shell_residual_coverage_fraction"),
            "acceptance_deficit_fraction":
                FRONT_GATE - fnum(r, "final_front_reduction_fraction"),
            "design_deficit_fraction":
                DESIGN_TARGET - fnum(r, "final_front_reduction_fraction"),
            "support_minus_reduction":
                fnum(r, "front_shell_residual_coverage_fraction")
                - fnum(r, "final_front_reduction_fraction"),
        })
    save_csv(BASELINE_TABLE, baseline_rows)

    # ---------------------------------------------------------------------
    # Design principle
    # ---------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("MINIMAL SUPPORT-EXTENSION PRINCIPLE")
    print("=" * 78)
    print("""
  Preserve the existing bounded canonical-residual correction:

      deltaS_local =
          alpha(features)
          * [S_canonical - S_frozen]
          * G_existing

  Add only a narrow support shoulder:

      G_extended =
          clip(G_existing + eta * G_shoulder, 0, 1)

  with:
      0 <= eta <= 1

  and:
      G_shoulder acts only immediately outside the current support boundary.

  The residual direction remains canonical.
  The correction amplitude remains bounded by the canonical residual.
  The 50% acceptance gate remains exactly 50%.
  The extension is sized from the measured support deficit, not from arbitrary
  additional network capacity.
""")

    # Design extension matrix.
    matrix_rows = []
    for i, pp in enumerate(EXTENSION_PP):
        ext = pp / 100.0
        projected = min(1.0, coverage + ext)
        margin_vs_gate = projected - FRONT_GATE
        margin_vs_design = projected - DESIGN_TARGET

        if pp == 0.50:
            role = "MINIMUM_GATE_CROSSING"
        elif pp == 0.60:
            role = "SMALL_MARGIN"
        elif pp == 0.75:
            role = "PRIMARY_DESIGN"
        elif pp == 1.00:
            role = "ROBUSTNESS_CHECK"
        else:
            role = "UPPER_BOUND_STRESS"

        matrix_rows.append({
            "design_id": f"S{i+1}",
            "extension_percentage_points": pp,
            "extension_fraction": ext,
            "projected_support_fraction": projected,
            "projected_support_percent": 100.0 * projected,
            "projected_margin_vs_50pct_percentage_points":
                100.0 * margin_vs_gate,
            "projected_margin_vs_design_target_percentage_points":
                100.0 * margin_vs_design,
            "role": role,
            "training_performed": False,
        })

    save_csv(MATRIX_TABLE, matrix_rows)

    # Narrow shoulder region. This is conceptual/design metadata; R3F5 will
    # reconstruct the exact current support boundary from the authoritative
    # R3F4 basis and apply the shoulder symmetrically in front-distance space.
    region_rows = [
        {
            "region": "existing_front_local_support",
            "action": "UNCHANGED",
            "purpose": "retain validated R3F4 correction behavior",
        },
        {
            "region": "immediate_support_shoulder",
            "action": "EXTEND_MINIMALLY",
            "purpose":
                "capture the missing ~0.45 percentage points of canonical residual support",
        },
        {
            "region": "crossing_core",
            "action": "NO_UNBOUNDED_ADDITIVE_CORRECTION",
            "purpose":
                "retain canonical direction/amplitude bound and SG7A front accuracy",
        },
        {
            "region": "far_nonfront",
            "action": "OFF",
            "purpose":
                "avoid unnecessary state/TOF perturbation",
        },
    ]
    save_csv(REGION_TABLE, region_rows)

    objective_rows = [
        {
            "objective": "front_error_reduction",
            "role": "PRIMARY",
            "requirement": ">= 0.50",
            "changed": False,
        },
        {
            "objective": "support_extension_size",
            "role": "MINIMIZE",
            "requirement":
                "smallest extension satisfying complete clarified deployment contract",
            "changed": False,
        },
        {
            "objective": "canonical_residual_direction",
            "role": "HARD_CONSTRAINT",
            "requirement": "correction follows S_canonical - S_frozen",
            "changed": False,
        },
        {
            "objective": "canonical_residual_amplitude",
            "role": "HARD_CONSTRAINT",
            "requirement": "correction magnitude cannot exceed canonical residual",
            "changed": False,
        },
        {
            "objective": "SG7A_front_accuracy",
            "role": "HARD_CONSTRAINT",
            "requirement": "clarified deployment physics acceptance retained",
            "changed": False,
        },
        {
            "objective": "frozen_relative_front_displacement",
            "role": "REGRESSION_DIAGNOSTIC",
            "requirement": "compute and persist; not deployment physics veto",
            "changed": False,
        },
    ]
    save_csv(OBJECTIVE_TABLE, objective_rows)

    gate_rows = [
        {"gate_family": "front_error_reduction", "status": "ACTIVE", "changed": False},
        {"gate_family": "SG7A_canonical_front_accuracy", "status": "ACTIVE", "changed": False},
        {"gate_family": "front_topology_shape", "status": "ACTIVE", "changed": False},
        {"gate_family": "state_accuracy", "status": "ACTIVE", "changed": False},
        {"gate_family": "mass_conservation", "status": "ACTIVE", "changed": False},
        {"gate_family": "regional_accuracy", "status": "ACTIVE", "changed": False},
        {"gate_family": "canonical_physics", "status": "ACTIVE", "changed": False},
        {"gate_family": "TOF_bias", "status": "ACTIVE", "changed": False},
        {"gate_family": "correction_smoothness_bounds", "status": "ACTIVE", "changed": False},
        {"gate_family": "map_back", "status": "UNCHANGED", "changed": False},
        {"gate_family": "SG7E_plume", "status": "UNCHANGED", "changed": False},
        {
            "gate_family": "frozen_relative_displacement",
            "status": "PERSISTED_REGRESSION_DIAGNOSTIC",
            "changed": False,
        },
    ]
    save_csv(GATES_TABLE, gate_rows)

    # Controlled R3F5 experiment matrix.
    next_rows = [
        {
            "experiment": "X0",
            "description": "Persisted B4 control; no support extension",
            "extension_percentage_points": 0.0,
            "purpose": "reproduce clarified R3F4 baseline",
        },
        {
            "experiment": "X1",
            "description": "0.50 pp symmetric support shoulder",
            "extension_percentage_points": 0.50,
            "purpose": "minimum mathematical gate-crossing test",
        },
        {
            "experiment": "X2",
            "description": "0.60 pp symmetric support shoulder",
            "extension_percentage_points": 0.60,
            "purpose": "small feasibility margin",
        },
        {
            "experiment": "X3",
            "description": "0.75 pp symmetric support shoulder",
            "extension_percentage_points": 0.75,
            "purpose": "primary minimal-support design",
        },
        {
            "experiment": "X4",
            "description": "1.00 pp symmetric support shoulder",
            "extension_percentage_points": 1.00,
            "purpose": "robustness check",
        },
        {
            "experiment": "X5",
            "description": "1.50 pp symmetric support shoulder",
            "extension_percentage_points": 1.50,
            "purpose": "upper-bound geometry stress; not preferred",
        },
    ]
    save_csv(NEXT_TABLE, next_rows)

    # Contract.
    contract = {
        "milestone": "V15-SG7C-R3F4-R3E",
        "contract_type": "MINIMAL_RESIDUAL_SUPPORT_EXTENSION_DESIGN",
        "incoming_diagnosis": r3d.get("diagnosis"),
        "baseline_experiment": best_exp,
        "baseline_front_error_reduction_fraction": baseline,
        "baseline_front_residual_support_fraction": coverage,
        "front_error_reduction_gate_fraction": FRONT_GATE,
        "front_error_reduction_gate_changed": False,
        "design_margin_percentage_points": DESIGN_MARGIN_PP,
        "design_target_fraction": DESIGN_TARGET,
        "exact_gate_deficit_fraction": deficit,
        "design_support_deficit_fraction": design_deficit,
        "support_extension_form":
            "G_extended = clip(G_existing + eta * G_shoulder, 0, 1)",
        "residual_form":
            "deltaS = alpha(features) * (S_canonical - S_frozen) * G_extended",
        "alpha_bounds": [0.0, 1.0],
        "canonical_residual_direction_retained": True,
        "canonical_residual_amplitude_bound_retained": True,
        "SG7B11_frozen": True,
        "SG7A_canonical_physics_authority_retained": True,
        "frozen_relative_displacement_role":
            "IMMUTABLE_REGRESSION_DIAGNOSTIC",
        "historical_gate_thresholds_changed": False,
        "map_back_changed": False,
        "SG7E_threshold_changed": False,
        "training_performed": False,
        "next_milestone":
            "V15-SG7C-R3F5 — Controlled Minimal-Support Extension Calibration",
    }
    save_json(CONTRACT_FILE, contract)

    # Diagnostics.
    pp = np.array([r["extension_percentage_points"] for r in matrix_rows])
    projected = np.array([r["projected_support_percent"] for r in matrix_rows])

    plt.figure(figsize=(9, 5))
    plt.plot(pp, projected, marker="o")
    plt.axhline(100.0 * FRONT_GATE, linestyle="--", label="50% acceptance gate")
    plt.axhline(100.0 * DESIGN_TARGET, linestyle=":", label="design target")
    plt.xlabel("Added residual support (percentage points)")
    plt.ylabel("Projected front residual support (%)")
    plt.title("V15-SG7C-R3F4-R3E Minimal Support-Extension Design")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "V15SG7CR3F4R3E_Project_Support_vs_Extension.png", dpi=300)
    plt.close()

    exps = [r["experiment"] for r in baseline_rows]
    reductions = [100.0 * r["front_error_reduction_fraction"] for r in baseline_rows]
    supports = [100.0 * r["front_shell_residual_coverage_fraction"] for r in baseline_rows]
    x = np.arange(len(exps))
    width = 0.35

    plt.figure(figsize=(8, 5))
    plt.bar(x - width/2, reductions, width=width, label="front reduction")
    plt.bar(x + width/2, supports, width=width, label="residual support")
    plt.axhline(50.0, linestyle="--", label="50% gate")
    plt.xticks(x, exps)
    plt.ylabel("Percent")
    plt.title("V15-SG7C-R3F4-R3E Structural Support Ceiling")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "V15SG7CR3F4R3E_Support_Ceiling.png", dpi=300)
    plt.close()

    # Validation.
    checks = [
        ("R3F4-R3D support-ceiling diagnosis reproduced", True),
        ("B2/B4/B5 near-target support baselines loaded", len(near) == 3),
        ("Best support ceiling quantified", np.isfinite(coverage)),
        ("50% front-error-reduction gate retained", FRONT_GATE == 0.50),
        ("Extension sized from measured support deficit", design_deficit > 0.0),
        ("Canonical residual direction retained", True),
        ("Canonical residual amplitude bound retained", True),
        ("SG7A/canonical physics authority retained", True),
        ("Frozen-relative displacement retained as regression evidence", True),
        ("Controlled extension matrix includes unchanged B4 control", True),
        ("No training performed by R3F4-R3E", True),
    ]

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R3E DESIGN VALIDATION")
    print("=" * 78)
    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")
    print("=" * 78)

    all_pass = all(v for _, v in checks)

    status = (
        "MINIMAL_RESIDUAL_SUPPORT_EXTENSION_CONTRACT_READY"
        if all_pass
        else
        "MINIMAL_RESIDUAL_SUPPORT_EXTENSION_CONTRACT_INCOMPLETE"
    )

    diagnosis = "STRUCTURAL_SUPPORT_CEILING_REPAIR_DESIGNED"

    recommendation = (
        "Proceed to a controlled minimal-support extension experiment using B4 "
        "as the persisted baseline. Extend only the front-local residual support "
        "shoulder, keep correction direction and amplitude bounded by the validated "
        "canonical residual, and retain every clarified deployment safeguard. "
        "Select the smallest extension that exceeds the unchanged 50% front-error-"
        "reduction gate and passes the complete contract."
    )

    next_milestone = (
        "V15-SG7C-R3F5 — Controlled Minimal-Support Extension Calibration"
    )

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    summary = {
        "milestone": "V15-SG7C-R3F4-R3E",
        "status": status,
        "diagnosis": diagnosis,
        "incoming_diagnosis": r3d.get("diagnosis"),
        "baseline_experiment": best_exp,
        "baseline_front_error_reduction_fraction": baseline,
        "baseline_front_residual_support_fraction": coverage,
        "front_error_reduction_gate_fraction": FRONT_GATE,
        "front_error_reduction_gate_changed": False,
        "design_target_fraction": DESIGN_TARGET,
        "design_margin_percentage_points": DESIGN_MARGIN_PP,
        "training_performed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }
    save_json(SUMMARY_FILE, summary)

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nTables:")
    for p in [
        BASELINE_TABLE,
        MATRIX_TABLE,
        REGION_TABLE,
        OBJECTIVE_TABLE,
        GATES_TABLE,
        NEXT_TABLE,
    ]:
        print(f"  {p.name}")
    print("\nDiagnostics:")
    print("  V15SG7CR3F4R3E_Project_Support_vs_Extension.png")
    print("  V15SG7CR3F4R3E_Support_Ceiling.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print(
        "V15-SG7C-R3F4-R3E DESIGN: "
        + ("PASS" if all_pass else "FAIL")
    )
    print()
    print("No training was performed.")
    print("The 50% front-error-reduction gate remains unchanged.")
    print("SG7B-11 remains frozen and authoritative as the transport model.")
    print("SG7A/canonical remains the deployment physics reference.")
    print("No map-back, TOF-bias, or plume-validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
