from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1A2R2
# Runtime Support-Transformation Audit
#
# DIAGNOSTIC / EXACT-TRANSFORMATION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R3F5-R1A2R recovered the actual runtime geometry:
#
#   required_shell      : (13633,)
#   coeff_shell         : (13633,)
#   supported_required  : (13633,)
#   shell               : (2662, 201)
#   coeff100            : (2662, 201)
#
# and established that:
#
#   sum(required_shell) = authoritative required residual sum exactly.
#
# The previous binary guess:
#
#   required_shell * (coeff_shell > 0.5)
#
# did NOT reproduce the authoritative supported residual sum.
#
# R1A2R2 therefore audits the exact historical transformation. It:
#
#   1. loads the persisted runtime arrays from R1A2R,
#   2. parses the authoritative R3F4-R source expression for:
#
#        supported_required
#        required_shell
#        residual_coverage_fraction
#
#   3. tests direct and deterministic transformations,
#   4. checks whether sum(supported_required) itself is the authoritative
#      supported residual sum,
#   5. identifies the exact relationship between supported_required,
#      required_shell, and coeff_shell,
#   6. serializes the exact 1-D front-shell arrays when closure is achieved.
#
# No scaling, anchoring, guessed support threshold, or retraining is allowed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1A2R2"
OUT.mkdir(parents=True, exist_ok=True)

R1A2R_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R"
    / "PAD_Stream_V15SG7CR3F5R1A2R_Summary.json"
)

R1A2R_RUNTIME = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R"
    / "V15SG7CR3F5R1A2R_Runtime_Variables.npz"
)

R1A2R_PATCH = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R"
    / "V15SG7CR3F5R1A2R_Runtime_Patch_Audit.csv"
)

R3F4R_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1A2R2_Summary.json"
SOURCE_TABLE = OUT / "V15SG7CR3F5R1A2R2_Source_Transformation_Trace.csv"
TRANSFORM_TABLE = OUT / "V15SG7CR3F5R1A2R2_Transformation_Candidates.csv"
RELATION_TABLE = OUT / "V15SG7CR3F5R1A2R2_Array_Relationship_Audit.csv"
CLOSURE_TABLE = OUT / "V15SG7CR3F5R1A2R2_Exact_Closure_Audit.csv"
EXACT_NPZ = OUT / "V15SG7CR3F5R1A2R2_Exact_Support_Arrays.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1A2R2_Runtime_Support_Transformation_Contract.json"

SUM_ABS_TOL = 1e-8
FRACTION_ABS_TOL = 1e-10
ARRAY_ABS_TOL = 1e-12


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
# SOURCE TRACE
# =============================================================================

TARGET_SYMBOLS = {
    "required_shell",
    "supported_required",
    "coeff_shell",
    "residual_coverage_fraction",
    "front_shell_required_residual_sum",
    "front_shell_supported_residual_sum",
    "front_shell_residual_coverage_fraction",
}


def authoritative_source():
    rows = load_csv(R1A2R_PATCH)
    if not rows:
        raise RuntimeError("R1A2R runtime patch audit is empty.")

    path = Path(rows[0]["original_source"])
    if not path.is_absolute():
        path = ROOT / path

    function_name = rows[0]["function"]

    if not path.exists():
        raise FileNotFoundError(f"Authoritative source not found:\n{path}")

    return path, function_name


def source_transform_trace(path: Path, function_name: str):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text, filename=str(path))

    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            fn = node
            break

    if fn is None:
        raise RuntimeError(f"Function '{function_name}' not found.")

    rows = []

    for node in ast.walk(fn):

        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if value is None:
                continue

            for target in targets:
                if isinstance(target, ast.Name) and target.id in TARGET_SYMBOLS:
                    rows.append({
                        "symbol": target.id,
                        "line_number": getattr(node, "lineno", -1),
                        "expression": ast.unparse(value),
                        "kind": "assignment",
                    })

                if isinstance(target, ast.Subscript):
                    sl = target.slice
                    if isinstance(sl, ast.Constant) and str(sl.value) in TARGET_SYMBOLS:
                        rows.append({
                            "symbol": str(sl.value),
                            "line_number": getattr(node, "lineno", -1),
                            "expression": ast.unparse(value),
                            "kind": "dict_assignment",
                        })

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and str(key.value) in TARGET_SYMBOLS:
                    rows.append({
                        "symbol": str(key.value),
                        "line_number": getattr(key, "lineno", getattr(node, "lineno", -1)),
                        "expression": ast.unparse(value),
                        "kind": "dict_literal",
                    })

    rows.sort(key=lambda r: (r["line_number"], r["symbol"]))
    return rows


# =============================================================================
# TRANSFORMATION AUDIT
# =============================================================================

def summarize_relation(name, candidate, reference):
    candidate = np.asarray(candidate, dtype=float)
    reference = np.asarray(reference, dtype=float)

    if candidate.shape != reference.shape:
        return {
            "relation": name,
            "shape_match": False,
            "L1": np.nan,
            "Linf": np.nan,
            "sum_candidate": np.nan,
            "sum_reference": float(np.sum(reference)),
        }

    delta = candidate - reference

    return {
        "relation": name,
        "shape_match": True,
        "L1": float(np.mean(np.abs(delta))),
        "Linf": float(np.max(np.abs(delta))) if delta.size else 0.0,
        "sum_candidate": float(np.sum(candidate)),
        "sum_reference": float(np.sum(reference)),
    }


def candidate_supported_fields(required, coeff):
    required = np.asarray(required, dtype=float)
    coeff = np.asarray(coeff, dtype=float)

    candidates = []

    # Continuous coefficient forms.
    candidates.append(("required_times_coeff", required * coeff))
    candidates.append(("required_times_clip01_coeff", required * np.clip(coeff, 0.0, 1.0)))
    candidates.append(("required_times_abs_coeff", required * np.abs(coeff)))

    # Binary support thresholds.
    for threshold in [
        0.0,
        1e-12,
        1e-8,
        1e-6,
        1e-4,
        1e-3,
        1e-2,
        0.05,
        0.10,
        0.20,
        0.25,
        0.30,
        0.40,
        0.45,
        0.49,
        0.50,
        0.51,
        0.55,
        0.60,
        0.70,
        0.75,
        0.80,
        0.90,
        0.95,
    ]:
        candidates.append((
            f"required_times_coeff_gt_{threshold:g}",
            required * (coeff > threshold),
        ))

    # Complement forms, included only as diagnostics.
    candidates.append(("required_times_one_minus_coeff", required * (1.0 - coeff)))
    candidates.append(("required_times_coeff_le_0_5", required * (coeff <= 0.5)))

    return candidates


def threshold_for_exact_sum(required, coeff, target_sum):
    """
    Audit whether any coefficient threshold exactly reproduces the authoritative
    supported sum.

    Because thresholded sums change only at observed coefficient values, test
    all unique coefficient breakpoints deterministically.
    """
    required = np.asarray(required, dtype=float)
    coeff = np.asarray(coeff, dtype=float)

    order = np.argsort(-coeff)
    coeff_sorted = coeff[order]
    req_sorted = required[order]
    cumulative = np.cumsum(req_sorted)

    best = None

    for i in range(len(coeff_sorted)):
        supported_sum = float(cumulative[i])
        error = abs(supported_sum - target_sum)

        # Threshold chosen between current and next value where possible.
        if i + 1 < len(coeff_sorted):
            threshold = 0.5 * (coeff_sorted[i] + coeff_sorted[i + 1])
        else:
            threshold = coeff_sorted[i] - np.finfo(float).eps

        row = {
            "rank": i + 1,
            "threshold": float(threshold),
            "supported_sum": supported_sum,
            "error": error,
            "included_fraction": float((i + 1) / len(coeff_sorted)),
        }

        if best is None or error < best["error"]:
            best = row

    return best


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1A2R2")
    print("Runtime Support-Transformation Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO GATE WILL BE CHANGED OR RELAXED.
NO SUPPORT SCALING OR ANCHORING WILL BE USED.
""")

    incoming = load_json(R1A2R_SUMMARY)

    if (
        incoming.get("diagnosis")
        !=
        "RUNTIME_SHAPES_RECOVERED_BUT_EXACT_SUPPORT_TRIPLET_NOT_YET_CLOSED"
    ):
        raise RuntimeError(
            "R3F5-R1A2R2 requires the R1A2R runtime-transformation diagnosis."
        )

    support_rows = load_csv(R3F4R_SUPPORT)

    b4 = next(
        row for row in support_rows
        if row.get("experiment") == "B4"
    )

    auth_required = fnum(
        b4,
        "front_shell_required_residual_sum",
    )

    auth_supported = fnum(
        b4,
        "front_shell_supported_residual_sum",
    )

    auth_fraction = fnum(
        b4,
        "front_shell_residual_coverage_fraction",
    )

    print("AUTHORITATIVE B4 CONTRACT")
    print(f"  Required residual sum   : {auth_required:.12e}")
    print(f"  Supported residual sum  : {auth_supported:.12e}")
    print(f"  Coverage fraction       : {auth_fraction:.12e}")

    if not R1A2R_RUNTIME.exists():
        raise FileNotFoundError(
            f"Missing R1A2R runtime database:\n{R1A2R_RUNTIME}"
        )

    db = np.load(
        R1A2R_RUNTIME,
        allow_pickle=True,
    )

    required_keys = [
        "required_shell",
        "supported_required",
        "coeff_shell",
    ]

    missing = [
        key for key in required_keys
        if key not in db.files
    ]

    if missing:
        raise RuntimeError(
            "R1A2R runtime database is missing required keys: "
            + ", ".join(missing)
        )

    required = np.asarray(
        db["required_shell"],
        dtype=float,
    )

    supported_required = np.asarray(
        db["supported_required"],
        dtype=float,
    )

    coeff = np.asarray(
        db["coeff_shell"],
        dtype=float,
    )

    if not (
        required.ndim == 1
        and supported_required.ndim == 1
        and coeff.ndim == 1
        and required.shape == supported_required.shape == coeff.shape
    ):
        raise RuntimeError(
            "required_shell, supported_required, and coeff_shell must be "
            "shape-compatible 1-D front-shell arrays."
        )

    print("\nRUNTIME FRONT-SHELL ARRAYS")
    print(f"  required_shell          : shape={required.shape}")
    print(f"  supported_required      : shape={supported_required.shape}")
    print(f"  coeff_shell             : shape={coeff.shape}")

    # -------------------------------------------------------------------------
    # Source transformation trace.
    # -------------------------------------------------------------------------

    source_path, function_name = authoritative_source()

    source_rows = source_transform_trace(
        source_path,
        function_name,
    )

    save_csv(
        SOURCE_TABLE,
        source_rows,
    )

    print("\nAUTHORITATIVE SOURCE TRANSFORMATION")

    for row in source_rows:
        print(
            f"  line {row['line_number']:>4} | "
            f"{row['symbol']} = {row['expression']}"
        )

    # -------------------------------------------------------------------------
    # Direct closure checks.
    # -------------------------------------------------------------------------

    direct_required_sum = float(
        np.sum(required)
    )

    direct_supported_sum = float(
        np.sum(supported_required)
    )

    direct_fraction = (
        direct_supported_sum
        /
        direct_required_sum
    )

    direct_req_error = abs(
        direct_required_sum
        -
        auth_required
    )

    direct_sup_error = abs(
        direct_supported_sum
        -
        auth_supported
    )

    direct_frac_error = abs(
        direct_fraction
        -
        auth_fraction
    )

    direct_closure = bool(
        direct_req_error <= SUM_ABS_TOL
        and
        direct_sup_error <= SUM_ABS_TOL
        and
        direct_frac_error <= FRACTION_ABS_TOL
    )

    print("\nDIRECT RUNTIME CLOSURE")
    print(f"  sum(required_shell)     : {direct_required_sum:.12e}")
    print(f"  sum(supported_required) : {direct_supported_sum:.12e}")
    print(f"  direct coverage         : {direct_fraction:.12e}")
    print(f"  Required error          : {direct_req_error:.6e}")
    print(f"  Supported error         : {direct_sup_error:.6e}")
    print(f"  Fraction error          : {direct_frac_error:.6e}")
    print(f"  Exact closure           : {'PASS' if direct_closure else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Relationship audit.
    # -------------------------------------------------------------------------

    relation_rows = []

    for name, candidate in candidate_supported_fields(
        required,
        coeff,
    ):
        relation_rows.append(
            summarize_relation(
                name,
                candidate,
                supported_required,
            )
        )

    relation_rows.sort(
        key=lambda row: (
            np.inf if not row["shape_match"] else row["Linf"],
            np.inf if not row["shape_match"] else row["L1"],
        )
    )

    save_csv(
        RELATION_TABLE,
        relation_rows,
    )

    print("\nCLOSEST ARRAY RELATIONSHIPS")

    for row in relation_rows[:10]:
        print(
            f"  {row['relation']:<42s} "
            f"L1={row['L1']:.6e} | "
            f"Linf={row['Linf']:.6e}"
        )

    # -------------------------------------------------------------------------
    # Supported-sum transformation candidates.
    # -------------------------------------------------------------------------

    transform_rows = []

    # Direct historical field is the highest-priority candidate.
    transform_rows.append({
        "transformation": "sum(supported_required)",
        "supported_sum": direct_supported_sum,
        "coverage_fraction": direct_fraction,
        "supported_error": direct_sup_error,
        "fraction_error": direct_frac_error,
        "source": "runtime_authoritative_array",
    })

    for name, candidate in candidate_supported_fields(
        required,
        coeff,
    ):
        supported_sum = float(
            np.sum(candidate)
        )

        fraction = (
            supported_sum
            /
            direct_required_sum
        )

        transform_rows.append({
            "transformation": f"sum({name})",
            "supported_sum": supported_sum,
            "coverage_fraction": fraction,
            "supported_error": abs(supported_sum - auth_supported),
            "fraction_error": abs(fraction - auth_fraction),
            "source": "deterministic_candidate",
        })

    exact_threshold = threshold_for_exact_sum(
        required,
        coeff,
        auth_supported,
    )

    if exact_threshold is not None:
        threshold = exact_threshold["threshold"]

        candidate = required * (coeff > threshold)

        supported_sum = float(
            np.sum(candidate)
        )

        fraction = (
            supported_sum
            /
            direct_required_sum
        )

        transform_rows.append({
            "transformation":
                f"sum(required_shell * (coeff_shell > {threshold:.17e}))",
            "supported_sum":
                supported_sum,
            "coverage_fraction":
                fraction,
            "supported_error":
                abs(
                    supported_sum
                    -
                    auth_supported
                ),
            "fraction_error":
                abs(
                    fraction
                    -
                    auth_fraction
                ),
            "source":
                "all_unique_coeff_thresholds",
        })

    transform_rows.sort(
        key=lambda row: (
            row["supported_error"],
            row["fraction_error"],
        )
    )

    save_csv(
        TRANSFORM_TABLE,
        transform_rows,
    )

    print("\nBEST SUPPORTED-SUM TRANSFORMATIONS")

    for row in transform_rows[:10]:
        print(
            f"  {row['transformation']:<62s} "
            f"sum={row['supported_sum']:.12e} | "
            f"err={row['supported_error']:.6e}"
        )

    # -------------------------------------------------------------------------
    # Exact transformation classification.
    # -------------------------------------------------------------------------

    exact_supported_array = bool(
        direct_sup_error <= SUM_ABS_TOL
    )

    best_relation = relation_rows[0] if relation_rows else None

    relation_exact = bool(
        best_relation is not None
        and
        best_relation["Linf"] <= ARRAY_ABS_TOL
    )

    if direct_closure:

        np.savez_compressed(
            EXACT_NPZ,
            required_shell=required.astype(np.float64),
            supported_required=supported_required.astype(np.float64),
            coeff_shell=coeff.astype(np.float64),
            authoritative_required_sum=np.asarray(auth_required, dtype=np.float64),
            authoritative_supported_sum=np.asarray(auth_supported, dtype=np.float64),
            authoritative_coverage_fraction=np.asarray(auth_fraction, dtype=np.float64),
        )

        status = "RUNTIME_SUPPORT_TRANSFORMATION_RECONCILED"

        if relation_exact:
            diagnosis = (
                "SUPPORTED_REQUIRED_EXACTLY_RECONSTRUCTED_FROM_COEFFICIENT_TRANSFORMATION"
            )
        else:
            diagnosis = (
                "SUPPORTED_REQUIRED_IS_AUTHORITATIVE_RUNTIME_SUPPORT_FIELD"
            )

        recommendation = (
            "The authoritative 1-D front-shell arrays close the B4 support contract "
            "exactly. Use required_shell and supported_required as the authoritative "
            "support populations in the next calibration branch. Keep coeff_shell as "
            "diagnostic unless its exact source relationship is required for extension "
            "construction. Do not return to guessed coefficient thresholds."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )

        exact_pass = True

    else:

        status = "RUNTIME_SUPPORT_TRANSFORMATION_NOT_YET_RECONCILED"
        diagnosis = "SUPPORTED_REQUIRED_DOES_NOT_CLOSE_AUTHORITATIVE_SUM"

        recommendation = (
            "The direct runtime supported_required field does not yet close the "
            "authoritative supported residual sum. Use the parsed source expression and "
            "best deterministic candidate table to reconstruct the exact transformation "
            "before any calibration."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A2R3 — Exact Supported-Residual Expression Reconstruction"
        )

        exact_pass = False

    save_csv(
        CLOSURE_TABLE,
        [{
            "required_sum": direct_required_sum,
            "supported_sum": direct_supported_sum,
            "coverage_fraction": direct_fraction,
            "authoritative_required_sum": auth_required,
            "authoritative_supported_sum": auth_supported,
            "authoritative_fraction": auth_fraction,
            "required_error": direct_req_error,
            "supported_error": direct_sup_error,
            "fraction_error": direct_frac_error,
            "exact_closure": direct_closure,
            "best_array_relation":
                (best_relation["relation"] if best_relation else ""),
            "best_relation_L1":
                (best_relation["L1"] if best_relation else np.nan),
            "best_relation_Linf":
                (best_relation["Linf"] if best_relation else np.nan),
        }]
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1A2R2",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_calibrated": False,
            "gate_changed": False,
            "authoritative_required_array": "required_shell",
            "authoritative_supported_array": "supported_required",
            "coefficient_array": "coeff_shell",
            "direct_runtime_closure": direct_closure,
            "best_array_relation":
                (best_relation["relation"] if best_relation else None),
            "best_array_relation_Linf":
                (best_relation["Linf"] if best_relation else None),
            "exact_arrays":
                (str(EXACT_NPZ) if exact_pass else None),
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        }
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1A2R2",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_calibrated": False,
            "gate_changed": False,
            "exact_closure": exact_pass,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        }
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R2 DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R1A2R diagnosis reproduced", True),
        ("required_shell loaded", True),
        ("supported_required loaded", True),
        ("coeff_shell loaded", True),
        ("Front-shell array shapes compatible", True),
        ("Authoritative source transformation parsed", bool(source_rows)),
        ("Required residual sum closes", direct_req_error <= SUM_ABS_TOL),
        ("Supported residual sum closes", direct_sup_error <= SUM_ABS_TOL),
        ("Support fraction closes", direct_frac_error <= FRACTION_ABS_TOL),
        ("Deterministic coefficient relationships audited", bool(relation_rows)),
        ("All unique coefficient thresholds audited", exact_threshold is not None),
        ("No support scaling or anchoring used", True),
        ("No support extension calibrated", True),
        ("No training performed", True),
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
    print(f"  {SOURCE_TABLE.name}")
    print(f"  {TRANSFORM_TABLE.name}")
    print(f"  {RELATION_TABLE.name}")
    print(f"  {CLOSURE_TABLE.name}")

    if exact_pass:
        print("\nRecovered exact arrays:")
        print(f"  {EXACT_NPZ.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R2 TRANSFORMATION AUDIT: COMPLETE")
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
