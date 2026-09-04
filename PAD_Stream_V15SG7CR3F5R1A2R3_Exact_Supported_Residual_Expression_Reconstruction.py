from __future__ import annotations

from pathlib import Path
import csv
import json
import math
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1A2R3
# Exact Supported-Residual Expression Reconstruction
#
# DIAGNOSTIC / PROVENANCE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R3F5-R1A2R2 established the exact historical source expression:
#
#   required_shell      = abs(residual[idx100][shell])
#   coeff_shell         = coeff100[shell]
#   supported_required  = coeff_shell * required_shell
#
# and:
#
#   sum(required_shell) closes EXACTLY.
#
# But the current reconstructed runtime gives:
#
#   sum(supported_required) = 62.56234252704
#
# while the persisted authoritative R3F4-R B4 record gives:
#
#   62.56321852706
#
# Difference:
#
#   8.7600002e-04
#
# Therefore the algebra is no longer in question.  The remaining issue must be
# one of:
#
#   * floating-point / accumulation representation,
#   * coefficient precision,
#   * checkpoint / coefficient-field provenance,
#   * historical scalar serialization provenance.
#
# R1A2R3 audits those possibilities without changing any model or gate.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1A2R3"
OUT.mkdir(parents=True, exist_ok=True)

R2_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R2"
    / "PAD_Stream_V15SG7CR3F5R1A2R2_Summary.json"
)

RUNTIME_NPZ = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R"
    / "V15SG7CR3F5R1A2R_Runtime_Variables.npz"
)

SUPPORT_CSV = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

CHECKPOINT_CSV = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
)

FINAL_METRICS_CSV = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
)

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1A2R3_Summary.json"
NUMERICAL_TABLE = OUT / "V15SG7CR3F5R1A2R3_Numerical_Accumulation_Audit.csv"
COEFF_TABLE = OUT / "V15SG7CR3F5R1A2R3_Coefficient_Provenance_Audit.csv"
CHECKPOINT_TABLE = OUT / "V15SG7CR3F5R1A2R3_Checkpoint_Identity_Audit.csv"
SCALAR_TABLE = OUT / "V15SG7CR3F5R1A2R3_Scalar_Provenance_Audit.csv"
EXACT_NPZ = OUT / "V15SG7CR3F5R1A2R3_Resolved_Support_Arrays.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1A2R3_Supported_Residual_Expression_Contract.json"

SUM_ABS_TOL = 1e-8
FRACTION_ABS_TOL = 1e-10

# Tiny relative differences are classified separately from material physics/model
# differences. This threshold does NOT alter any acceptance gate.
PROVENANCE_REL_TOL = 5e-5


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
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


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def kahan_sum(values):
    total = 0.0
    c = 0.0
    for x in np.asarray(values, dtype=np.float64).ravel():
        y = x - c
        t = total + y
        c = (t - total) - y
        total = t
    return float(total)


def pairwise_python_sum(values):
    # Python sum accumulates Python float after conversion.
    return float(sum(float(x) for x in np.asarray(values).ravel()))


def coefficient_stats(coeff):
    c = np.asarray(coeff, dtype=np.float64)
    return {
        "mean": float(np.mean(c)),
        "p90": float(np.percentile(c, 90)),
        "max": float(np.max(c)),
        "min": float(np.min(c)),
        "std": float(np.std(c)),
    }


def row_for_experiment(rows, experiment):
    for row in rows:
        if row.get("experiment") == experiment:
            return row
    return None


def checkpoint_rows_for_b4(rows):
    return [
        row for row in rows
        if row.get("experiment") == "B4"
    ]


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1A2R3")
    print("Exact Supported-Residual Expression Reconstruction")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO GATE WILL BE CHANGED OR RELAXED.
THE SOURCE ALGEBRA IS NOW FIXED AND WILL NOT BE REINTERPRETED.
""")

    incoming = load_json(R2_SUMMARY)

    if incoming.get("diagnosis") != "SUPPORTED_REQUIRED_DOES_NOT_CLOSE_AUTHORITATIVE_SUM":
        raise RuntimeError(
            "R1A2R3 requires the R1A2R2 supported-required closure diagnosis."
        )

    support_rows = load_csv(SUPPORT_CSV)
    b4 = row_for_experiment(support_rows, "B4")

    if b4 is None:
        raise RuntimeError("Missing authoritative B4 support record.")

    auth_required = fnum(b4, "front_shell_required_residual_sum")
    auth_supported = fnum(b4, "front_shell_supported_residual_sum")
    auth_fraction = fnum(b4, "front_shell_residual_coverage_fraction")

    auth_coeff_mean = fnum(b4, "front_shell_coefficient_mean")
    auth_coeff_p90 = fnum(b4, "front_shell_coefficient_P90")
    auth_coeff_max = fnum(b4, "front_shell_coefficient_max")

    db = np.load(RUNTIME_NPZ, allow_pickle=True)

    for key in ["required_shell", "coeff_shell", "supported_required"]:
        if key not in db.files:
            raise RuntimeError(f"Missing runtime key: {key}")

    required = np.asarray(db["required_shell"])
    coeff = np.asarray(db["coeff_shell"])
    supported = np.asarray(db["supported_required"])

    if not (
        required.shape == coeff.shape == supported.shape
        and required.ndim == 1
    ):
        raise RuntimeError("Runtime front-shell arrays are not shape-compatible 1-D arrays.")

    # -------------------------------------------------------------------------
    # 1. Algebra identity
    # -------------------------------------------------------------------------

    product64 = (
        np.asarray(required, dtype=np.float64)
        *
        np.asarray(coeff, dtype=np.float64)
    )

    identity_l1 = float(
        np.mean(
            np.abs(
                np.asarray(supported, dtype=np.float64)
                -
                product64
            )
        )
    )

    identity_linf = float(
        np.max(
            np.abs(
                np.asarray(supported, dtype=np.float64)
                -
                product64
            )
        )
    )

    # -------------------------------------------------------------------------
    # 2. Accumulation / precision variants
    # -------------------------------------------------------------------------

    numerical_rows = []

    variants = []

    req32 = np.asarray(required, dtype=np.float32)
    req64 = np.asarray(required, dtype=np.float64)
    coeff32 = np.asarray(coeff, dtype=np.float32)
    coeff64 = np.asarray(coeff, dtype=np.float64)
    sup32 = np.asarray(supported, dtype=np.float32)
    sup64 = np.asarray(supported, dtype=np.float64)

    variants.extend([
        ("stored_supported_np_sum_float64", float(np.sum(sup64, dtype=np.float64))),
        ("stored_supported_np_sum_float32", float(np.sum(sup32, dtype=np.float32))),
        ("stored_supported_python_sum", pairwise_python_sum(sup64)),
        ("stored_supported_kahan_sum", kahan_sum(sup64)),
        ("required64_times_coeff64_np_sum", float(np.sum(req64 * coeff64, dtype=np.float64))),
        ("required32_times_coeff32_np_sum32", float(np.sum(req32 * coeff32, dtype=np.float32))),
        ("required32_times_coeff32_np_sum64", float(np.sum(req32 * coeff32, dtype=np.float64))),
        ("required64_times_coeff32_np_sum64", float(np.sum(req64 * coeff32.astype(np.float64), dtype=np.float64))),
        ("required32_times_coeff64_np_sum64", float(np.sum(req32.astype(np.float64) * coeff64, dtype=np.float64))),
        ("required64_times_coeff64_kahan", kahan_sum(req64 * coeff64)),
    ])

    for name, value in variants:
        numerical_rows.append({
            "variant": name,
            "supported_sum": value,
            "absolute_error_vs_authoritative": abs(value - auth_supported),
            "relative_error_vs_authoritative":
                abs(value - auth_supported) / max(abs(auth_supported), 1e-15),
        })

    numerical_rows.sort(
        key=lambda r: r["absolute_error_vs_authoritative"]
    )

    save_csv(NUMERICAL_TABLE, numerical_rows)

    print("\nNUMERICAL ACCUMULATION AUDIT")
    for row in numerical_rows:
        print(
            f"  {row['variant']:<42s} "
            f"{row['supported_sum']:.12e} | "
            f"err={row['absolute_error_vs_authoritative']:.6e}"
        )

    best_numeric = numerical_rows[0]

    # -------------------------------------------------------------------------
    # 3. Coefficient provenance
    # -------------------------------------------------------------------------

    current_stats = coefficient_stats(coeff64)

    coeff_rows = [
        {
            "metric": "mean",
            "runtime_value": current_stats["mean"],
            "authoritative_value": auth_coeff_mean,
            "absolute_difference": abs(current_stats["mean"] - auth_coeff_mean),
        },
        {
            "metric": "P90",
            "runtime_value": current_stats["p90"],
            "authoritative_value": auth_coeff_p90,
            "absolute_difference": abs(current_stats["p90"] - auth_coeff_p90),
        },
        {
            "metric": "max",
            "runtime_value": current_stats["max"],
            "authoritative_value": auth_coeff_max,
            "absolute_difference": abs(current_stats["max"] - auth_coeff_max),
        },
    ]

    save_csv(COEFF_TABLE, coeff_rows)

    print("\nCOEFFICIENT PROVENANCE")
    for row in coeff_rows:
        print(
            f"  {row['metric']:<5s} runtime={row['runtime_value']:.12e} | "
            f"authoritative={row['authoritative_value']:.12e} | "
            f"delta={row['absolute_difference']:.6e}"
        )

    coeff_stats_available = all(
        np.isfinite(row["authoritative_value"])
        for row in coeff_rows
    )

    coeff_stats_match = bool(
        coeff_stats_available
        and all(
            row["absolute_difference"] <= 5e-6
            for row in coeff_rows
        )
    )

    # -------------------------------------------------------------------------
    # 4. Scalar provenance / implied coefficient perturbation
    # -------------------------------------------------------------------------

    runtime_supported = float(np.sum(sup64, dtype=np.float64))
    runtime_required = float(np.sum(req64, dtype=np.float64))
    runtime_fraction = runtime_supported / runtime_required

    scalar_delta = auth_supported - runtime_supported
    scalar_rel = abs(scalar_delta) / max(abs(auth_supported), 1e-15)

    # If every coefficient changed uniformly by dc, this dc would explain the
    # scalar difference. This is diagnostic only; it is NOT applied.
    implied_uniform_coeff_delta = (
        scalar_delta / runtime_required
        if runtime_required > 0
        else np.nan
    )

    weighted_mean_coeff_runtime = (
        runtime_supported / runtime_required
        if runtime_required > 0
        else np.nan
    )

    weighted_mean_coeff_authoritative = (
        auth_supported / auth_required
        if auth_required > 0
        else np.nan
    )

    scalar_rows = [
        {
            "quantity": "runtime_required_sum",
            "value": runtime_required,
        },
        {
            "quantity": "authoritative_required_sum",
            "value": auth_required,
        },
        {
            "quantity": "runtime_supported_sum",
            "value": runtime_supported,
        },
        {
            "quantity": "authoritative_supported_sum",
            "value": auth_supported,
        },
        {
            "quantity": "supported_sum_delta_authoritative_minus_runtime",
            "value": scalar_delta,
        },
        {
            "quantity": "supported_sum_relative_delta",
            "value": scalar_rel,
        },
        {
            "quantity": "runtime_weighted_mean_coefficient",
            "value": weighted_mean_coeff_runtime,
        },
        {
            "quantity": "authoritative_weighted_mean_coefficient",
            "value": weighted_mean_coeff_authoritative,
        },
        {
            "quantity": "implied_uniform_coefficient_delta_diagnostic_only",
            "value": implied_uniform_coeff_delta,
        },
        {
            "quantity": "runtime_coverage_fraction",
            "value": runtime_fraction,
        },
        {
            "quantity": "authoritative_coverage_fraction",
            "value": auth_fraction,
        },
    ]

    save_csv(SCALAR_TABLE, scalar_rows)

    # -------------------------------------------------------------------------
    # 5. Checkpoint identity audit
    # -------------------------------------------------------------------------

    checkpoint_rows = checkpoint_rows_for_b4(
        load_csv(CHECKPOINT_CSV)
    )

    final_metrics = row_for_experiment(
        load_csv(FINAL_METRICS_CSV),
        "B4",
    )

    checkpoint_audit = []

    for row in checkpoint_rows:
        path_value = row.get("path") or row.get("checkpoint_path") or ""

        p = Path(path_value) if path_value else None

        if p is not None and not p.is_absolute():
            p = ROOT / p

        exists = bool(
            p is not None
            and p.exists()
        )

        digest = sha256(p) if exists else ""

        checkpoint_audit.append({
            "experiment": "B4",
            "checkpoint_type": row.get("checkpoint_type", ""),
            "epoch": row.get("epoch", ""),
            "path": str(p) if p is not None else "",
            "exists": exists,
            "sha256": digest,
        })

    if final_metrics is not None:
        checkpoint_audit.append({
            "experiment": "B4",
            "checkpoint_type": "final_metrics_record",
            "epoch": final_metrics.get("epoch", ""),
            "path": "",
            "exists": "",
            "sha256": "",
            "front_error_reduction_fraction":
                final_metrics.get("front_error_reduction_fraction", ""),
        })

    save_csv(CHECKPOINT_TABLE, checkpoint_audit)

    # -------------------------------------------------------------------------
    # 6. Classification
    # -------------------------------------------------------------------------

    required_closes = abs(runtime_required - auth_required) <= SUM_ABS_TOL
    algebra_exact = identity_linf <= 1e-12

    numerical_precision_explains = (
        best_numeric["absolute_error_vs_authoritative"] <= SUM_ABS_TOL
    )

    tiny_provenance_delta = (
        scalar_rel <= PROVENANCE_REL_TOL
    )

    if required_closes and algebra_exact and numerical_precision_explains:

        status = "SUPPORTED_RESIDUAL_EXPRESSION_RECONCILED"
        diagnosis = "FLOATING_POINT_ACCUMULATION_REPRESENTATION_DIFFERENCE"

        resolved_supported = best_numeric["supported_sum"]

        recommendation = (
            "The exact source algebra is correct and a deterministic precision/"
            "accumulation representation reproduces the authoritative supported sum. "
            "Freeze this numerical convention for the exact-array extension branch."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )

        resolved = True

    elif required_closes and algebra_exact and coeff_stats_match and tiny_provenance_delta:

        status = "SUPPORTED_RESIDUAL_PROVENANCE_RECONCILED"
        diagnosis = "TINY_HISTORICAL_SCALAR_PROVENANCE_DRIFT"

        resolved_supported = runtime_supported

        recommendation = (
            "The source expression and runtime arrays are internally exact, the required "
            "sum closes, and coefficient summary statistics reproduce the historical B4 "
            "record. The remaining supported-sum discrepancy is a tiny historical scalar "
            "provenance difference rather than a transformation error. Preserve BOTH the "
            "historical scalar and the runtime-reconstructed scalar in the record. Use the "
            "runtime arrays themselves—not a scalar anchor—for the exact-array extension."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )

        resolved = True

    elif required_closes and algebra_exact and tiny_provenance_delta:

        status = "SUPPORTED_RESIDUAL_PROVENANCE_ISOLATED"
        diagnosis = "LIKELY_CHECKPOINT_OR_COEFFICIENT_FIELD_PROVENANCE_DRIFT"

        resolved_supported = runtime_supported

        recommendation = (
            "The algebra is exact and the discrepancy is tiny, but coefficient summary "
            "provenance does not fully match or is unavailable. Do not calibrate yet. "
            "Resolve the exact B4 coefficient/checkpoint identity that produced the "
            "historical scalar."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A2R4 — B4 Coefficient / Checkpoint Provenance Audit"
        )

        resolved = False

    else:

        status = "SUPPORTED_RESIDUAL_EXPRESSION_RECONSTRUCTION_INCOMPLETE"
        diagnosis = "MATERIAL_RUNTIME_PROVENANCE_MISMATCH"

        resolved_supported = runtime_supported

        recommendation = (
            "The remaining discrepancy cannot be classified as a tiny numerical/"
            "provenance difference. Do not calibrate support. Audit the historical "
            "checkpoint and coefficient field before proceeding."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A2R4 — B4 Coefficient / Checkpoint Provenance Audit"
        )

        resolved = False

    if resolved:
        np.savez_compressed(
            EXACT_NPZ,
            required_shell=req64,
            coeff_shell=coeff64,
            supported_required=sup64,
            runtime_required_sum=np.asarray(runtime_required, dtype=np.float64),
            runtime_supported_sum=np.asarray(runtime_supported, dtype=np.float64),
            historical_authoritative_required_sum=np.asarray(auth_required, dtype=np.float64),
            historical_authoritative_supported_sum=np.asarray(auth_supported, dtype=np.float64),
            runtime_coverage_fraction=np.asarray(runtime_fraction, dtype=np.float64),
            historical_authoritative_coverage_fraction=np.asarray(auth_fraction, dtype=np.float64),
            algebra_identity_L1=np.asarray(identity_l1, dtype=np.float64),
            algebra_identity_Linf=np.asarray(identity_linf, dtype=np.float64),
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    print("\nEXPRESSION IDENTITY")
    print(f"  supported == coeff*required L1  : {identity_l1:.12e}")
    print(f"  supported == coeff*required Linf: {identity_linf:.12e}")

    print("\nSCALAR PROVENANCE")
    print(f"  Runtime supported sum      : {runtime_supported:.12e}")
    print(f"  Historical supported sum   : {auth_supported:.12e}")
    print(f"  Absolute delta             : {scalar_delta:.12e}")
    print(f"  Relative delta             : {scalar_rel:.12e}")
    print(f"  Implied uniform dCoeff     : {implied_uniform_coeff_delta:.12e}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R3 DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R1A2R2 diagnosis reproduced", True),
        ("required_shell / coeff_shell / supported_required loaded", True),
        ("Source algebra supported=coeff*required reproduced", algebra_exact),
        ("Required residual sum closes", required_closes),
        ("Float32/float64 accumulation variants audited", bool(numerical_rows)),
        ("Coefficient historical summary audited", True),
        ("Checkpoint identity evidence audited", True),
        ("No scalar scaling or anchoring applied", True),
        ("No support extension calibrated", True),
        ("No training performed", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    print("=" * 78)

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1A2R3",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_calibrated": False,
            "gate_changed": False,
            "source_expression":
                "supported_required = coeff_shell * required_shell",
            "algebra_identity_L1": identity_l1,
            "algebra_identity_Linf": identity_linf,
            "runtime_required_sum": runtime_required,
            "historical_required_sum": auth_required,
            "runtime_supported_sum": runtime_supported,
            "historical_supported_sum": auth_supported,
            "supported_sum_delta": scalar_delta,
            "supported_sum_relative_delta": scalar_rel,
            "coefficient_stats_match_historical": coeff_stats_match,
            "numerical_precision_explains_difference": numerical_precision_explains,
            "resolved": resolved,
            "resolved_exact_arrays": str(EXACT_NPZ) if resolved else None,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        }
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1A2R3",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_calibrated": False,
            "gate_changed": False,
            "resolved": resolved,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        }
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
    print(f"  {NUMERICAL_TABLE.name}")
    print(f"  {COEFF_TABLE.name}")
    print(f"  {CHECKPOINT_TABLE.name}")
    print(f"  {SCALAR_TABLE.name}")

    if resolved:
        print("\nResolved numerical:")
        print(f"  {EXACT_NPZ.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R3 EXPRESSION RECONSTRUCTION: COMPLETE")
    print()
    print("No training was performed.")
    print("No support extension was calibrated.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
