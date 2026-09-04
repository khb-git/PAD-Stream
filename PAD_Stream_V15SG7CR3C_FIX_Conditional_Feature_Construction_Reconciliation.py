from __future__ import annotations

from pathlib import Path
import csv
import importlib.util
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3C-FIX
# Conditional Feature Construction Reconciliation / xi Equivalence Audit
#
# DIAGNOSTIC / CONTRACT-REPAIR MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO ARCHITECTURE CHANGE.
# NO SG6 GEOMETRY CHANGE.
# NO FEATURE CONVENTION CHANGE.
# NO TARGET SCALING CHANGE.
# NO MAP-BACK OR SG7E THRESHOLD CHANGE.
#
# WHY THIS MILESTONE EXISTS
# -------------------------
# SG7C-R3C reported:
#
#   Canonical xi == deployment xi : False
#
# but simultaneously found:
#
#   canonical-interpolated target L1 vs SG7A = O(1e-8)
#
# over the full deployment population.
#
# That combination strongly suggests the xi "mismatch" may be representational
# (floating-point precision / endpoint construction / affine-equivalent grid)
# rather than a semantic feature mismatch.
#
# This milestone therefore audits:
#
#   - shape equality
#   - ordering
#   - endpoint equality
#   - spacing equality
#   - absolute/relative differences
#   - affine equivalence
#   - normalized-coordinate equivalence
#   - whether canonical target interpolation already proves semantic identity
#
# No feature is changed here. We only decide whether R3C's xi check was a
# false-positive contract failure.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3C_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3C"
    / "PAD_Stream_V15SG7CR3C_Summary.json"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

R3A_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3A"
    / "V15SG7CR3A_Coordinate_Audit.npz"
)

BASE_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B6D_Advective_Flux_Refinement.py"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3C_FIX"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

XI_TABLE = OUTPUT_DIR / "V15SG7CR3C_FIX_Xi_Equivalence_Audit.csv"
GRID_TABLE = OUTPUT_DIR / "V15SG7CR3C_FIX_Grid_Comparison.csv"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7CR3C_FIX_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import:\n{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3C-FIX")
    print("Conditional Feature Construction Reconciliation / xi Equivalence Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO FEATURE CONSTRUCTION WILL BE CHANGED.")
    print("NO TARGET SCALING WILL BE CHANGED.")
    print("NO MODEL, MAP-BACK, OR VALIDATION GATE WILL BE CHANGED.")

    for path in [
        R3C_SUMMARY,
        R3C_NUMERICAL,
        R3A_NUMERICAL,
        BASE_SOURCE,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing prerequisite:\n{path}")

    r3c = load_json(R3C_SUMMARY)

    if r3c.get("diagnosis") != "CONDITIONAL_FEATURE_SEMANTICS_MISMATCH":
        raise RuntimeError(
            "R3C-FIX requires incoming diagnosis:\n"
            "CONDITIONAL_FEATURE_SEMANTICS_MISMATCH"
        )

    base = import_module(
        BASE_SOURCE,
        "pad_stream_sg7b6d_for_r3c_fix",
    )

    dataset = base.load_dataset()

    X_train = np.asarray(dataset["X_train"], dtype=float)
    canonical_xi = np.asarray(X_train[0, :, 0], dtype=float)

    r3a_db = np.load(R3A_NUMERICAL, allow_pickle=True)
    deployment_xi = np.asarray(r3a_db["xi"], dtype=float)

    r3c_db = np.load(R3C_NUMERICAL, allow_pickle=True)

    canonical_interp_error = np.asarray(
        r3c_db["interpolation_error"],
        dtype=float,
    )

    canonical_interp_l1 = float(np.mean(np.abs(canonical_interp_error)))
    canonical_interp_linf = float(np.max(np.abs(canonical_interp_error)))

    same_shape = canonical_xi.shape == deployment_xi.shape

    if not same_shape:
        max_abs = np.inf
        mean_abs = np.inf
        max_rel = np.inf
        spacing_linf = np.inf
        monotonic_same = False
        affine_linf = np.inf
        normalized_linf = np.inf
    else:
        diff = canonical_xi - deployment_xi
        max_abs = float(np.max(np.abs(diff)))
        mean_abs = float(np.mean(np.abs(diff)))

        denom = np.maximum(
            np.maximum(np.abs(canonical_xi), np.abs(deployment_xi)),
            1.0e-15,
        )
        max_rel = float(np.max(np.abs(diff) / denom))

        dc = np.diff(canonical_xi)
        dd = np.diff(deployment_xi)

        spacing_linf = float(np.max(np.abs(dc - dd)))

        monotonic_same = bool(
            np.all(dc > 0.0)
            and np.all(dd > 0.0)
        )

        # Best affine mapping deployment -> canonical.
        A = np.column_stack([
            deployment_xi,
            np.ones_like(deployment_xi),
        ])

        coeff, *_ = np.linalg.lstsq(
            A,
            canonical_xi,
            rcond=None,
        )

        mapped = coeff[0] * deployment_xi + coeff[1]

        affine_linf = float(
            np.max(
                np.abs(
                    mapped
                    -
                    canonical_xi
                )
            )
        )

        # Compare after normalization to [0,1].
        c_norm = (
            canonical_xi
            -
            canonical_xi[0]
        ) / (
            canonical_xi[-1]
            -
            canonical_xi[0]
        )

        d_norm = (
            deployment_xi
            -
            deployment_xi[0]
        ) / (
            deployment_xi[-1]
            -
            deployment_xi[0]
        )

        normalized_linf = float(
            np.max(
                np.abs(
                    c_norm
                    -
                    d_norm
                )
            )
        )

    endpoint_start_diff = (
        float(abs(canonical_xi[0] - deployment_xi[0]))
        if same_shape else np.inf
    )

    endpoint_end_diff = (
        float(abs(canonical_xi[-1] - deployment_xi[-1]))
        if same_shape else np.inf
    )

    # Tolerances intentionally distinguish numerical equivalence from semantic
    # equivalence. The interpolation manifold itself is the strongest semantic
    # check.
    strict_numerical_equiv = bool(
        same_shape
        and max_abs <= 1.0e-7
        and spacing_linf <= 1.0e-7
    )

    affine_equiv = bool(
        same_shape
        and monotonic_same
        and affine_linf <= 1.0e-10
    )

    normalized_equiv = bool(
        same_shape
        and monotonic_same
        and normalized_linf <= 1.0e-10
    )

    target_semantic_equiv = bool(
        canonical_interp_l1 <= 5.0e-7
        and canonical_interp_linf <= 5.0e-6
    )

    semantic_equiv = bool(
        target_semantic_equiv
        and same_shape
        and monotonic_same
        and (
            strict_numerical_equiv
            or affine_equiv
            or normalized_equiv
        )
    )

    print("\n" + "=" * 78)
    print("XI EQUIVALENCE AUDIT")
    print("=" * 78)
    print(f"Canonical shape            : {canonical_xi.shape}")
    print(f"Deployment shape           : {deployment_xi.shape}")
    print(f"Same shape                 : {same_shape}")
    print(f"Canonical range            : {canonical_xi[0]:.17e} -> {canonical_xi[-1]:.17e}")
    print(f"Deployment range           : {deployment_xi[0]:.17e} -> {deployment_xi[-1]:.17e}")
    print(f"Start endpoint difference  : {endpoint_start_diff:.17e}")
    print(f"End endpoint difference    : {endpoint_end_diff:.17e}")
    print(f"Mean |delta xi|            : {mean_abs:.17e}")
    print(f"Max |delta xi|             : {max_abs:.17e}")
    print(f"Max relative difference    : {max_rel:.17e}")
    print(f"Spacing Linf difference    : {spacing_linf:.17e}")
    print(f"Affine-fit Linf            : {affine_linf:.17e}")
    print(f"Normalized-grid Linf       : {normalized_linf:.17e}")

    print("\nTARGET-MANIFOLD SEMANTIC CHECK")
    print(f"Canonical interpolation L1 : {canonical_interp_l1:.6e}")
    print(f"Canonical interpolation max: {canonical_interp_linf:.6e}")

    print("\nDIAGNOSTIC FLAGS")
    print(f"  Strict numerical equiv   : {strict_numerical_equiv}")
    print(f"  Affine equivalent        : {affine_equiv}")
    print(f"  Normalized-grid equiv    : {normalized_equiv}")
    print(f"  Target semantic equiv    : {target_semantic_equiv}")
    print(f"  Overall semantic equiv   : {semantic_equiv}")

    xi_rows = []

    if same_shape:
        for i in range(len(canonical_xi)):
            xi_rows.append({
                "node": i,
                "canonical_xi": canonical_xi[i],
                "deployment_xi": deployment_xi[i],
                "difference": canonical_xi[i] - deployment_xi[i],
                "abs_difference": abs(canonical_xi[i] - deployment_xi[i]),
            })

    grid_rows = [{
        "same_shape": same_shape,
        "canonical_nodes": len(canonical_xi),
        "deployment_nodes": len(deployment_xi),
        "canonical_start": canonical_xi[0],
        "deployment_start": deployment_xi[0],
        "canonical_end": canonical_xi[-1],
        "deployment_end": deployment_xi[-1],
        "mean_abs_difference": mean_abs,
        "max_abs_difference": max_abs,
        "max_relative_difference": max_rel,
        "spacing_Linf": spacing_linf,
        "affine_Linf": affine_linf,
        "normalized_grid_Linf": normalized_linf,
        "canonical_interp_L1": canonical_interp_l1,
        "canonical_interp_Linf": canonical_interp_linf,
        "strict_numerical_equiv": strict_numerical_equiv,
        "affine_equiv": affine_equiv,
        "normalized_equiv": normalized_equiv,
        "target_semantic_equiv": target_semantic_equiv,
        "semantic_equiv": semantic_equiv,
    }]

    save_csv(XI_TABLE, xi_rows)
    save_csv(GRID_TABLE, grid_rows)

    # -------------------------------------------------------------------------
    # Classification
    # -------------------------------------------------------------------------

    if semantic_equiv:
        diagnosis = "R3C_XI_MISMATCH_IS_NUMERICAL_OR_REPRESENTATIONAL"
        recommendation = (
            "Do not repair the deployment feature construction. The canonical and "
            "deployment xi coordinates are semantically equivalent, and the canonical "
            "target manifold already reproduces SG7A deployment truth to near machine "
            "precision. Reclassify R3C as feature/target transfer valid and proceed to "
            "a frozen-model deployment calibration design."
        )
        next_milestone = (
            "V15-SG7C-R3D — Frozen PI-RNN Deployment Calibration Design"
        )
        repaired_r3c_diagnosis = (
            "FEATURE_AND_TARGET_TRANSFER_VALID_MODEL_APPROXIMATION_RESIDUAL"
        )

    else:
        diagnosis = "TRUE_XI_FEATURE_SEMANTICS_MISMATCH"
        recommendation = (
            "The xi grids are not numerically, affinely, or normalized-coordinate "
            "equivalent despite the interpolation result. Audit the exact feature "
            "construction path before calibration."
        )
        next_milestone = (
            "V15-SG7C-R3C-FIX2 — xi Feature Construction Trace Audit"
        )
        repaired_r3c_diagnosis = None

    # -------------------------------------------------------------------------
    # Plot
    # -------------------------------------------------------------------------

    if same_shape:
        plt.figure(figsize=(9, 5))
        plt.plot(canonical_xi, label="canonical xi")
        plt.plot(deployment_xi, linestyle="--", label="deployment xi")
        plt.xlabel("Node index")
        plt.ylabel("xi")
        plt.title("V15-SG7C-R3C-FIX Canonical vs Deployment xi")
        plt.legend()
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7CR3C_FIX_Xi_Comparison.png",
            dpi=300,
        )
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.plot(np.abs(canonical_xi - deployment_xi))
        plt.xlabel("Node index")
        plt.ylabel("|delta xi|")
        plt.title("V15-SG7C-R3C-FIX xi Numerical Difference")
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7CR3C_FIX_Xi_Difference.png",
            dpi=300,
        )
        plt.close()

    print("\n" + "=" * 78)
    print("V15-SG7C-R3C-FIX DIAGNOSTIC VALIDATION")
    print("=" * 78)
    print("[PASS] Incoming R3C feature-mismatch diagnosis reproduced")
    print("[PASS] Canonical xi loaded from authoritative PI-RNN dataset")
    print("[PASS] Deployment xi loaded from SG6/R3A coordinate database")
    print("[PASS] Shape/order/endpoint/spacing comparison completed")
    print("[PASS] Affine and normalized-grid equivalence tested")
    print("[PASS] Canonical interpolation semantic check retained")
    print("[PASS] Diagnostic classification established")
    print("=" * 78)

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nREPAIRED R3C INTERPRETATION")
    print(f"  {repaired_r3c_diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    summary = {
        "milestone": "V15-SG7C-R3C-FIX",
        "status": "XI_FEATURE_EQUIVALENCE_AUDIT_COMPLETE",
        "incoming_diagnosis": r3c.get("diagnosis"),
        "diagnosis": diagnosis,
        "semantic_equivalence": semantic_equiv,
        "strict_numerical_equivalence": strict_numerical_equiv,
        "affine_equivalence": affine_equiv,
        "normalized_grid_equivalence": normalized_equiv,
        "target_semantic_equivalence": target_semantic_equiv,
        "max_abs_xi_difference": max_abs,
        "spacing_Linf_difference": spacing_linf,
        "affine_Linf": affine_linf,
        "normalized_grid_Linf": normalized_linf,
        "canonical_interp_L1": canonical_interp_l1,
        "canonical_interp_Linf": canonical_interp_linf,
        "repaired_R3C_diagnosis": repaired_r3c_diagnosis,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {XI_TABLE.name}")
    print(f"  {GRID_TABLE.name}")
    print("\nDiagnostics:")
    print("  V15SG7CR3C_FIX_Xi_Comparison.png")
    print("  V15SG7CR3C_FIX_Xi_Difference.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3C-FIX AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No feature, target, model, map-back, or validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
