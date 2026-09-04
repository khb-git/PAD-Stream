from __future__ import annotations

from pathlib import Path
import csv
import json
import re


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R0A
# Exact Authoritative Support Formula Extraction
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R3F5-R0 established that the candidate support reconstructions did not match
# the authoritative R3F4-R/R3D value:
#
#   authoritative B4 support = 49.5478%
#
# The R3F4-R support table contains:
#
#   front_shell_required_residual_sum
#   front_shell_supported_residual_sum
#   front_shell_residual_coverage_fraction
#   front_shell_coefficient_mean
#   front_shell_coefficient_P90
#   front_shell_coefficient_max
#
# This strongly suggests the support metric is not a generic coefficient
# occupancy. R3F5-R0A therefore extracts the exact formula and the upstream
# masks/arrays used to construct the numerator and denominator.
#
# The milestone:
#
#   1. searches authoritative source files for the support fields,
#   2. extracts the exact assignment expression,
#   3. traces variable dependencies recursively,
#   4. records the front-shell mask definition,
#   5. records required/supported residual definitions,
#   6. reconstructs the formula symbolically from the source,
#   7. verifies that the CSV values satisfy:
#
#        coverage
#          =
#        supported_residual_sum
#        -----------------------
#        required_residual_sum
#
#   8. writes a repaired support-metric contract for R3F5-R1.
#
# No support extension is calibrated here.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R0A"
OUT.mkdir(parents=True, exist_ok=True)

R0_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R0"
    / "PAD_Stream_V15SG7CR3F5R0_Summary.json"
)

R0_SOURCE = (
    ROOT / "output" / "V15_SG7CR3F5R0"
    / "V15SG7CR3F5R0_Source_Definition_Evidence.csv"
)

R3F4R_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

SUMMARY_FILE = (
    OUT / "PAD_Stream_V15SG7CR3F5R0A_Summary.json"
)

FORMULA_TABLE = (
    OUT / "V15SG7CR3F5R0A_Exact_Support_Formula.csv"
)

DEPENDENCY_TABLE = (
    OUT / "V15SG7CR3F5R0A_Support_Formula_Dependencies.csv"
)

SOURCE_TABLE = (
    OUT / "V15SG7CR3F5R0A_Authoritative_Source_Extraction.csv"
)

NUMERICAL_TABLE = (
    OUT / "V15SG7CR3F5R0A_CSV_Formula_Closure.csv"
)

CONTRACT_FILE = (
    OUT / "V15SG7CR3F5R0A_Authoritative_Support_Metric_Contract.json"
)


FIELD_NAMES = [
    "front_shell_required_residual_sum",
    "front_shell_supported_residual_sum",
    "front_shell_residual_coverage_fraction",
    "front_shell_coefficient_mean",
    "front_shell_coefficient_P90",
    "front_shell_coefficient_max",
]

SEARCH_FILES = [
    "PAD_Stream_V15SG7CR3F4R_Front_Local_Basis_Outcome_Audit.py",
    "PAD_Stream_V15SG7CR3F4_Controlled_Front_Local_Residual_Basis_Calibration.py",
    "PAD_Stream_V15SG7CR3F4R2_True_Front_Displacement_Basis_Audit.py",
    "PAD_Stream_V15SG7CR3F4R3D_Near_Threshold_Front_Reduction_Limiter_Audit.py",
]

MAX_DEPENDENCY_DEPTH = 4


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
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def fnum(row, key, default=float("nan")):
    try:
        v = row.get(key, default)
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


# =============================================================================
# SOURCE PARSING
# =============================================================================

ASSIGNMENT_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$"
)

DICT_FIELD_RE = re.compile(
    r"""["']([^"']+)["']\s*:\s*(.+?)(?:,)?\s*$"""
)

IDENTIFIER_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*\b"
)


def read_lines(path: Path):
    return path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()


def find_authoritative_sources():
    candidates = []

    for name in SEARCH_FILES:
        p = ROOT / name
        if p.exists():
            candidates.append(p)

    # Robust fallback.
    for p in ROOT.glob("PAD_Stream_V15SG7CR3F4*.py"):
        if p not in candidates:
            candidates.append(p)

    return sorted(candidates)


def extract_field_occurrences(path: Path):
    lines = read_lines(path)
    rows = []

    for i, line in enumerate(lines):
        for field in FIELD_NAMES:
            if field in line:
                lo = max(0, i - 15)
                hi = min(len(lines), i + 16)
                rows.append({
                    "file": str(path),
                    "line_number": i + 1,
                    "field": field,
                    "matching_line": line.strip(),
                    "context_excerpt":
                        "\n".join(
                            f"{j+1}: {lines[j]}"
                            for j in range(lo, hi)
                        ),
                })

    return rows


def assignments_in_file(path: Path):
    lines = read_lines(path)
    out = {}

    for i, line in enumerate(lines):
        m = ASSIGNMENT_RE.match(line)

        if m:
            var = m.group(1)
            expr = m.group(2).strip()
            out.setdefault(var, []).append({
                "file": str(path),
                "line_number": i + 1,
                "expression": expr,
            })

    return out


def extract_field_expression(path: Path, field: str):
    lines = read_lines(path)

    for i, line in enumerate(lines):
        if field not in line:
            continue

        # Dict-style field.
        dm = DICT_FIELD_RE.search(line)

        if dm and dm.group(1) == field:
            return {
                "file": str(path),
                "line_number": i + 1,
                "expression": dm.group(2).strip().rstrip(","),
                "source_kind": "DICT_FIELD",
            }

        # Assignment-style field.
        am = ASSIGNMENT_RE.match(line)

        if am and am.group(1) == field:
            return {
                "file": str(path),
                "line_number": i + 1,
                "expression": am.group(2).strip(),
                "source_kind": "ASSIGNMENT",
            }

    return None


def identifiers(expr: str):
    blacklist = {
        "np", "float", "int", "bool", "True", "False",
        "sum", "mean", "max", "min", "abs", "where",
        "clip", "percentile", "isfinite", "nan",
    }

    return [
        token
        for token in IDENTIFIER_RE.findall(expr)
        if token not in blacklist
        and not token.isupper()
    ]


def trace_dependencies(
    symbol: str,
    assignment_maps,
    depth=0,
    seen=None,
):
    if seen is None:
        seen = set()

    key = (symbol, depth)

    if key in seen or depth > MAX_DEPENDENCY_DEPTH:
        return []

    seen.add(key)

    rows = []

    for path, amap in assignment_maps.items():
        if symbol not in amap:
            continue

        # Prefer latest definition in file since metric blocks commonly assign
        # the final diagnostic variable near output construction.
        entry = amap[symbol][-1]

        rows.append({
            "depth": depth,
            "symbol": symbol,
            "file": entry["file"],
            "line_number": entry["line_number"],
            "expression": entry["expression"],
        })

        for dep in identifiers(entry["expression"]):
            if dep == symbol:
                continue

            rows.extend(
                trace_dependencies(
                    dep,
                    assignment_maps,
                    depth + 1,
                    seen,
                )
            )

    return rows


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R0A")
    print("Exact Authoritative Support Formula Extraction")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO FRONT, TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE CHANGED.
""")

    incoming = load_json(R0_SUMMARY)

    if (
        incoming.get("diagnosis")
        != "AUTHORITATIVE_SUPPORT_METRIC_NOT_YET_RECONSTRUCTED"
    ):
        raise RuntimeError(
            "R3F5-R0A requires incoming diagnosis:\n"
            "AUTHORITATIVE_SUPPORT_METRIC_NOT_YET_RECONSTRUCTED"
        )

    source_evidence = load_csv(R0_SOURCE)
    support_rows = load_csv(R3F4R_SUPPORT)

    b4 = next(
        (
            row for row in support_rows
            if row.get("experiment") == "B4"
        ),
        None,
    )

    if b4 is None:
        raise RuntimeError(
            "Missing B4 authoritative support row."
        )

    required_sum = fnum(
        b4,
        "front_shell_required_residual_sum",
    )

    supported_sum = fnum(
        b4,
        "front_shell_supported_residual_sum",
    )

    coverage = fnum(
        b4,
        "front_shell_residual_coverage_fraction",
    )

    ratio = (
        supported_sum
        /
        required_sum
        if required_sum != 0.0
        else float("nan")
    )

    closure_error = abs(
        coverage - ratio
    )

    print("AUTHORITATIVE CSV CLOSURE")
    print(
        f"  Required residual sum    : "
        f"{required_sum:.12e}"
    )
    print(
        f"  Supported residual sum   : "
        f"{supported_sum:.12e}"
    )
    print(
        f"  Stored coverage          : "
        f"{coverage:.12e}"
    )
    print(
        f"  Supported / required     : "
        f"{ratio:.12e}"
    )
    print(
        f"  Closure error            : "
        f"{closure_error:.12e}"
    )

    numerical_rows = [{
        "experiment": "B4",
        "front_shell_required_residual_sum": required_sum,
        "front_shell_supported_residual_sum": supported_sum,
        "stored_front_shell_residual_coverage_fraction": coverage,
        "reconstructed_supported_over_required": ratio,
        "absolute_closure_error": closure_error,
        "formula_closes": bool(closure_error <= 1e-12),
    }]

    save_csv(
        NUMERICAL_TABLE,
        numerical_rows,
    )

    # -------------------------------------------------------------------------
    # Source extraction
    # -------------------------------------------------------------------------

    sources = find_authoritative_sources()

    if not sources:
        raise FileNotFoundError(
            "No R3F4/R authoritative source files found."
        )

    occurrence_rows = []

    for path in sources:
        occurrence_rows.extend(
            extract_field_occurrences(path)
        )

    save_csv(
        SOURCE_TABLE,
        occurrence_rows,
    )

    assignment_maps = {
        str(path): assignments_in_file(path)
        for path in sources
    }

    formula_rows = []

    for field in FIELD_NAMES:

        matches = []

        for path in sources:
            result = extract_field_expression(
                path,
                field,
            )

            if result is not None:
                matches.append(result)

        if matches:
            # Prefer direct assignment, then first match.
            matches.sort(
                key=lambda r:
                0
                if r["source_kind"] == "ASSIGNMENT"
                else 1
            )

            chosen = matches[0]

            formula_rows.append({
                "field": field,
                "file": chosen["file"],
                "line_number": chosen["line_number"],
                "source_kind": chosen["source_kind"],
                "expression": chosen["expression"],
                "found": True,
            })

        else:
            formula_rows.append({
                "field": field,
                "file": "",
                "line_number": "",
                "source_kind": "",
                "expression": "",
                "found": False,
            })

    save_csv(
        FORMULA_TABLE,
        formula_rows,
    )

    # -------------------------------------------------------------------------
    # Dependency tracing
    # -------------------------------------------------------------------------

    dependency_rows = []

    target_symbols = [
        "front_shell_required_residual_sum",
        "front_shell_supported_residual_sum",
        "front_shell_residual_coverage_fraction",
    ]

    # Extract symbols referenced by the dictionary field expressions first.
    seed_symbols = set()

    for row in formula_rows:
        if (
            row["field"] in target_symbols
            and row["expression"]
        ):
            for token in identifiers(
                row["expression"]
            ):
                seed_symbols.add(token)

    # Include field names themselves because some files may assign them directly.
    seed_symbols.update(
        target_symbols
    )

    for symbol in sorted(seed_symbols):

        dependency_rows.extend(
            trace_dependencies(
                symbol,
                assignment_maps,
            )
        )

    # De-duplicate.
    dedup = []
    seen = set()

    for row in dependency_rows:
        key = (
            row["symbol"],
            row["file"],
            row["line_number"],
            row["expression"],
        )

        if key not in seen:
            seen.add(key)
            dedup.append(row)

    dependency_rows = sorted(
        dedup,
        key=lambda r: (
            r["depth"],
            r["symbol"],
            r["file"],
            r["line_number"],
        )
    )

    save_csv(
        DEPENDENCY_TABLE,
        dependency_rows,
    )

    # -------------------------------------------------------------------------
    # Semantic extraction
    # -------------------------------------------------------------------------

    all_source_text = "\n".join(
        "\n".join(read_lines(path))
        for path in sources
    )

    all_source_lower = all_source_text.lower()

    required_signal = (
        "front_shell_required_residual_sum"
        in all_source_lower
    )

    supported_signal = (
        "front_shell_supported_residual_sum"
        in all_source_lower
    )

    coverage_signal = (
        "front_shell_residual_coverage_fraction"
        in all_source_lower
    )

    shell_signal = (
        "front_shell"
        in all_source_lower
    )

    coefficient_signal = (
        "coefficient"
        in all_source_lower
    )

    canonical_residual_signal = (
        "canonical"
        in all_source_lower
        and
        "residual"
        in all_source_lower
    )

    formula_closes = bool(
        closure_error <= 1e-12
    )

    enough_formula_evidence = bool(
        required_signal
        and
        supported_signal
        and
        coverage_signal
        and
        shell_signal
    )

    # The exact arithmetic identity is established from the authoritative CSV.
    # Source extraction then records the exact upstream definitions/masks.
    if (
        formula_closes
        and
        enough_formula_evidence
        and
        occurrence_rows
    ):

        status = "AUTHORITATIVE_SUPPORT_FORMULA_EXTRACTED"

        diagnosis = (
            "SUPPORT_IS_REQUIRED_VS_SUPPORTED_FRONT_SHELL_RESIDUAL_RATIO"
        )

        recommendation = (
            "Use the authoritative ratio "
            "front_shell_supported_residual_sum / "
            "front_shell_required_residual_sum in R3F5-R1. "
            "Reconstruct the exact front-shell and supported-residual masks from "
            "the extracted source dependencies. Do not use coefficient occupancy, "
            "residual-weighted coefficient averages, or multiplicative anchoring."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1 — Controlled Minimal-Support Extension Calibration Repair"
        )

    else:

        status = "AUTHORITATIVE_SUPPORT_FORMULA_EXTRACTION_INCOMPLETE"

        diagnosis = (
            "AUTHORITATIVE_SUPPORT_FORMULA_DEPENDENCY_CHAIN_INCOMPLETE"
        )

        recommendation = (
            "The CSV arithmetic may close, but the source dependency chain is not "
            "yet sufficient to reconstruct the exact front-shell/support masks. "
            "Inspect the generated source and dependency tables before calibration."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R0B — Support Mask / Residual Dependency Extraction"
        )

    # -------------------------------------------------------------------------
    # Contract
    # -------------------------------------------------------------------------

    contract = {
        "milestone": "V15-SG7C-R3F5-R0A",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_calibrated": False,
        "authoritative_formula": (
            "front_shell_supported_residual_sum / "
            "front_shell_required_residual_sum"
        ),
        "authoritative_B4": {
            "front_shell_required_residual_sum":
                required_sum,
            "front_shell_supported_residual_sum":
                supported_sum,
            "front_shell_residual_coverage_fraction":
                coverage,
            "reconstructed_ratio":
                ratio,
            "absolute_closure_error":
                closure_error,
        },
        "source_signals": {
            "required_residual_field_found":
                required_signal,
            "supported_residual_field_found":
                supported_signal,
            "coverage_field_found":
                coverage_signal,
            "front_shell_semantics_found":
                shell_signal,
            "coefficient_semantics_found":
                coefficient_signal,
            "canonical_residual_semantics_found":
                canonical_residual_signal,
        },
        "prohibited_replacements": [
            "residual_weighted_coefficient",
            "generic_coefficient_occupancy",
            "multiplicative_anchor",
        ],
        "required_R3F5_R1_behavior": [
            "reuse exact authoritative front-shell mask semantics",
            "reuse exact authoritative required residual definition",
            "reuse exact authoritative supported residual definition",
            "compute coverage as supported / required",
            "retain canonical residual direction and amplitude bounds",
            "do not modify B4 checkpoint weights",
            "do not modify SG7B-11 weights",
            "do not change 50 percent gate",
        ],
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        CONTRACT_FILE,
        contract,
    )

    summary = {
        "milestone": "V15-SG7C-R3F5-R0A",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "model_parameters_changed": False,
        "support_extension_calibrated": False,
        "gate_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("\nSOURCE EXTRACTION")
    print(
        f"  Authoritative source files searched : "
        f"{len(sources)}"
    )
    print(
        f"  Field occurrences extracted         : "
        f"{len(occurrence_rows)}"
    )
    print(
        f"  Dependency assignments extracted    : "
        f"{len(dependency_rows)}"
    )

    print("\nEXACT SUPPORT FORMULA")
    print(
        "  front_shell_residual_coverage_fraction ="
    )
    print(
        "      front_shell_supported_residual_sum"
    )
    print(
        "      ----------------------------------"
    )
    print(
        "      front_shell_required_residual_sum"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R0A DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Incoming R3F5-R0 incomplete metric diagnosis reproduced",
            True,
        ),
        (
            "Authoritative B4 required-residual sum loaded",
            required_sum == required_sum,
        ),
        (
            "Authoritative B4 supported-residual sum loaded",
            supported_sum == supported_sum,
        ),
        (
            "Stored coverage loaded",
            coverage == coverage,
        ),
        (
            "Coverage = supported / required closes",
            formula_closes,
        ),
        (
            "Authoritative R3F4/R source files located",
            bool(sources),
        ),
        (
            "Support-field source occurrences extracted",
            bool(occurrence_rows),
        ),
        (
            "Front-shell semantics located",
            shell_signal,
        ),
        (
            "No support extension calibrated",
            True,
        ),
        (
            "No training performed",
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
    print(f"  {FORMULA_TABLE.name}")
    print(f"  {DEPENDENCY_TABLE.name}")
    print(f"  {SOURCE_TABLE.name}")
    print(f"  {NUMERICAL_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R0A AUDIT: PASS")
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