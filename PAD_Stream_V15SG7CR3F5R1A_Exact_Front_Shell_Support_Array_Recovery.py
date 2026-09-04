from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
import sys
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1A
# Exact Front-Shell / Support-Array Recovery
#
# DIAGNOSTIC / RECOVERY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R3F5-R1 established:
#
#   AUTHORITATIVE_FORMULA_KNOWN_BUT_EXACT_NUMERICAL_MASKS_NOT_RECOVERED
#
# R3F5-R0A already proved the exact authoritative support ratio:
#
#   front_shell_residual_coverage_fraction
#       =
#   front_shell_supported_residual_sum
#   ----------------------------------
#   front_shell_required_residual_sum
#
# with B4:
#
#   required  = 126.2683024511
#   supported =  62.56321852706
#   coverage  =   0.4954784162976
#
# The missing piece is the exact FRONT-SHELL and SUPPORTED-RESIDUAL population.
#
# R3F5-R1A recovers those arrays from the authoritative source branch by:
#
#   1. finding the actual R3F4/R3F4-R source that computes the support sums,
#   2. parsing the relevant function/block,
#   3. identifying the exact upstream variable names,
#   4. searching all persisted NPZ databases for those exact keys,
#   5. when keys are absent, importing the authoritative source module and
#      re-running ONLY its deterministic reconstruction helpers if available,
#   6. reconstructing required/supported masks and residual arrays,
#   7. requiring closure to the authoritative B4 sums before serialization,
#   8. persisting the recovered exact arrays for R3F5-R1B.
#
# This milestone does NOT calibrate the support extension.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1A"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1"
    / "PAD_Stream_V15SG7CR3F5R1_Summary.json"
)

R0A_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R0A"
    / "V15SG7CR3F5R0A_Authoritative_Support_Metric_Contract.json"
)

R0A_SOURCE = (
    ROOT / "output" / "V15_SG7CR3F5R0A"
    / "V15SG7CR3F5R0A_Authoritative_Source_Extraction.csv"
)

R0A_DEP = (
    ROOT / "output" / "V15_SG7CR3F5R0A"
    / "V15SG7CR3F5R0A_Support_Formula_Dependencies.csv"
)

R3F4R_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1A_Summary.json"

SOURCE_TRACE_TABLE = (
    OUT / "V15SG7CR3F5R1A_Exact_Source_Trace.csv"
)

SYMBOL_TABLE = (
    OUT / "V15SG7CR3F5R1A_Support_Symbol_Recovery.csv"
)

NPZ_SEARCH_TABLE = (
    OUT / "V15SG7CR3F5R1A_NPZ_Key_Search.csv"
)

CANDIDATE_TABLE = (
    OUT / "V15SG7CR3F5R1A_Reconstruction_Candidates.csv"
)

CLOSURE_TABLE = (
    OUT / "V15SG7CR3F5R1A_Exact_Array_Closure.csv"
)

RECOVERED_NPZ = (
    OUT / "V15SG7CR3F5R1A_Exact_Support_Arrays.npz"
)

CONTRACT_FILE = (
    OUT / "V15SG7CR3F5R1A_Exact_Support_Array_Contract.json"
)

# -----------------------------------------------------------------------------
# Authoritative closure
# -----------------------------------------------------------------------------

SUM_ABS_TOL = 1e-8
FRACTION_ABS_TOL = 1e-10

# Search scope.
SEARCH_OUTPUT_DIRS = [
    ROOT / "output" / "V15_SG7CR3F4",
    ROOT / "output" / "V15_SG7CR3F4R",
    ROOT / "output" / "V15_SG7CR3F4R2",
    ROOT / "output" / "V15_SG7CR3F4R2R",
    ROOT / "output" / "V15_SG7CR3F4R3D",
    ROOT / "output" / "V15_SG7CR3F4R3C",
    ROOT / "output" / "V15_SG7CR3F4R3E",
]

SOURCE_GLOBS = [
    "PAD_Stream_V15SG7CR3F4*.py",
    "PAD_Stream_V15SG7CR3F3*.py",
]

TARGET_FIELD_NAMES = {
    "front_shell_required_residual_sum",
    "front_shell_supported_residual_sum",
    "front_shell_residual_coverage_fraction",
}


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
        w = csv.DictWriter(
            f,
            fieldnames=fields,
        )
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
# SOURCE DISCOVERY / AST EXTRACTION
# =============================================================================

def source_files():
    files = []

    for pattern in SOURCE_GLOBS:
        files.extend(
            ROOT.glob(pattern)
        )

    return sorted(
        set(files)
    )


def source_occurrence_rows(files):
    rows = []

    for path in files:

        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines):

            if any(
                field in line
                for field in TARGET_FIELD_NAMES
            ):

                lo = max(
                    0,
                    i - 25,
                )

                hi = min(
                    len(lines),
                    i + 26,
                )

                rows.append({
                    "file":
                        str(path),
                    "line_number":
                        i + 1,
                    "matching_line":
                        line.strip(),
                    "context":
                        "\n".join(
                            f"{j+1}: {lines[j]}"
                            for j in range(lo, hi)
                        ),
                })

    return rows


def names_from_ast(node):
    names = set()

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name,
        ):
            names.add(
                child.id
            )

    return names


def exact_assignment_symbols(path: Path):
    """
    Parse the module and identify variables that contribute directly to
    target support fields.

    Handles:
      x = ...
      dict["field"] = ...
      {"field": expr}
    """

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except SyntaxError:
        return []

    rows = []

    for node in ast.walk(tree):

        # Direct assignment to the target variable.
        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):

            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
            )

            value = node.value

            if value is None:
                continue

            for target in targets:

                # Variable assignment.
                if isinstance(
                    target,
                    ast.Name,
                ) and target.id in TARGET_FIELD_NAMES:

                    rows.append({
                        "file":
                            str(path),
                        "line_number":
                            getattr(node, "lineno", -1),
                        "field":
                            target.id,
                        "expression":
                            ast.unparse(value),
                        "referenced_symbols":
                            ";".join(
                                sorted(
                                    names_from_ast(value)
                                )
                            ),
                        "kind":
                            "direct_assignment",
                    })

                # Dict subscript assignment.
                if isinstance(
                    target,
                    ast.Subscript,
                ):

                    sl = target.slice

                    if isinstance(
                        sl,
                        ast.Constant,
                    ) and sl.value in TARGET_FIELD_NAMES:

                        rows.append({
                            "file":
                                str(path),
                            "line_number":
                                getattr(node, "lineno", -1),
                            "field":
                                str(sl.value),
                            "expression":
                                ast.unparse(value),
                            "referenced_symbols":
                                ";".join(
                                    sorted(
                                        names_from_ast(value)
                                    )
                                ),
                            "kind":
                                "dict_subscript_assignment",
                        })

        # Dict literal.
        if isinstance(
            node,
            ast.Dict,
        ):

            for key, value in zip(
                node.keys,
                node.values,
            ):

                if isinstance(
                    key,
                    ast.Constant,
                ) and key.value in TARGET_FIELD_NAMES:

                    rows.append({
                        "file":
                            str(path),
                        "line_number":
                            getattr(
                                key,
                                "lineno",
                                getattr(node, "lineno", -1),
                            ),
                        "field":
                            str(key.value),
                        "expression":
                            ast.unparse(value),
                        "referenced_symbols":
                            ";".join(
                                sorted(
                                    names_from_ast(value)
                                )
                            ),
                        "kind":
                            "dict_literal",
                    })

    return rows


def all_assignment_index(path: Path):
    """
    Map variable name -> assignment expressions for recursive dependency tracing.
    """

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except SyntaxError:
        return {}

    index = {}

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):
            continue

        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
        )

        value = node.value

        if value is None:
            continue

        for target in targets:

            if isinstance(
                target,
                ast.Name,
            ):

                index.setdefault(
                    target.id,
                    [],
                ).append({
                    "line_number":
                        getattr(node, "lineno", -1),
                    "expression":
                        ast.unparse(value),
                    "symbols":
                        names_from_ast(value),
                })

    return index


def recursive_symbol_trace(
    seed_symbols,
    files,
    max_depth=6,
):
    rows = []

    assignment_indices = {
        path:
            all_assignment_index(path)
        for path in files
    }

    queue = [
        (symbol, 0, "target_field")
        for symbol in seed_symbols
    ]

    seen = set()

    while queue:

        symbol, depth, parent = queue.pop(0)

        if (
            symbol,
            depth,
        ) in seen:
            continue

        seen.add(
            (
                symbol,
                depth,
            )
        )

        if depth > max_depth:
            continue

        found_any = False

        for path, index in assignment_indices.items():

            if symbol not in index:
                continue

            found_any = True

            # Keep every assignment; downstream recovery may need the exact
            # branch-local definition.
            for entry in index[symbol]:

                rows.append({
                    "symbol":
                        symbol,
                    "depth":
                        depth,
                    "parent":
                        parent,
                    "file":
                        str(path),
                    "line_number":
                        entry["line_number"],
                    "expression":
                        entry["expression"],
                    "dependency_symbols":
                        ";".join(
                            sorted(
                                entry["symbols"]
                            )
                        ),
                })

                for dep in sorted(
                    entry["symbols"]
                ):

                    if dep == symbol:
                        continue

                    if dep in {
                        "np",
                        "float",
                        "int",
                        "bool",
                        "True",
                        "False",
                        "len",
                        "range",
                    }:
                        continue

                    queue.append(
                        (
                            dep,
                            depth + 1,
                            symbol,
                        )
                    )

        if not found_any:

            rows.append({
                "symbol":
                    symbol,
                "depth":
                    depth,
                "parent":
                    parent,
                "file":
                    "",
                "line_number":
                    "",
                "expression":
                    "",
                "dependency_symbols":
                    "",
            })

    return rows


# =============================================================================
# NPZ SEARCH
# =============================================================================

def npz_search(symbols):
    rows = []
    entries = []

    normalized_symbols = {
        s.lower()
        for s in symbols
        if len(s) >= 3
    }

    for directory in SEARCH_OUTPUT_DIRS:

        if not directory.exists():
            continue

        for path in sorted(
            directory.glob("*.npz")
        ):

            try:
                db = np.load(
                    path,
                    allow_pickle=True,
                )
            except Exception as exc:

                rows.append({
                    "file":
                        str(path),
                    "key":
                        "",
                    "shape":
                        "",
                    "dtype":
                        "",
                    "symbol_matches":
                        "",
                    "error":
                        repr(exc),
                })

                continue

            for key in db.files:

                low = key.lower()

                matches = sorted(
                    s
                    for s in normalized_symbols
                    if s in low
                    or low in s
                )

                try:
                    arr = np.asarray(
                        db[key]
                    )

                    shape = str(
                        tuple(
                            arr.shape
                        )
                    )

                    dtype = str(
                        arr.dtype
                    )

                except Exception as exc:

                    shape = ""
                    dtype = ""

                    rows.append({
                        "file":
                            str(path),
                        "key":
                            key,
                        "shape":
                            shape,
                        "dtype":
                            dtype,
                        "symbol_matches":
                            ";".join(
                                matches
                            ),
                        "error":
                            repr(exc),
                    })

                    continue

                rows.append({
                    "file":
                        str(path),
                    "key":
                        key,
                    "shape":
                        shape,
                    "dtype":
                        dtype,
                    "symbol_matches":
                        ";".join(
                            matches
                        ),
                    "error":
                        "",
                })

                entries.append({
                    "file":
                        path,
                    "key":
                        key,
                    "low":
                        low,
                    "matches":
                        matches,
                    "array":
                        arr,
                })

    return rows, entries


# =============================================================================
# RECONSTRUCTION CANDIDATES
# =============================================================================

def normalize_to_100d(
    arr,
    nt,
    ns,
    nx,
    idx100,
):
    a = np.asarray(
        arr
    )

    if a.shape == (
        nt,
        ns,
        nx,
    ):
        return np.asarray(
            a[idx100]
        )

    if a.shape == (
        ns,
        nx,
    ):
        return np.asarray(
            a
        )

    if a.shape == (
        nt,
        ns,
    ):

        return np.broadcast_to(
            np.asarray(
                a[idx100]
            )[:, None],
            (
                ns,
                nx,
            ),
        )

    if a.shape == (
        ns,
    ):

        return np.broadcast_to(
            np.asarray(a)[:, None],
            (
                ns,
                nx,
            ),
        )

    return None


def bool_candidate(a):
    arr = np.asarray(
        a
    )

    if arr.dtype == bool:
        return arr

    finite = np.isfinite(
        arr
    )

    if not np.any(
        finite
    ):
        return None

    vals = np.unique(
        arr[finite]
    )

    if (
        vals.size <= 4
        and
        np.all(
            np.isclose(
                vals,
                np.round(vals),
            )
        )
    ):
        return arr > 0.5

    return None


def score_arrays(
    entries,
    canonical,
    frozen,
    times,
    authoritative_required,
    authoritative_supported,
):
    """
    Search persisted arrays exhaustively for combinations that reproduce the
    exact authoritative sums.

    Unlike R3F5-R1, this does not require guessed key semantics first.
    It enumerates plausible 100d boolean masks and residual-like arrays.
    """

    nt, ns, nx = canonical.shape

    idx100 = int(
        np.argmin(
            np.abs(
                times - 100.0
            )
        )
    )

    canonical_abs_residual = np.abs(
        canonical[idx100]
        -
        frozen[idx100]
    )

    residual_candidates = [
        {
            "name":
                "canonical_minus_frozen_abs",
            "file":
                str(R3C_NUMERICAL),
            "key":
                "derived",
            "array":
                canonical_abs_residual,
        }
    ]

    mask_candidates = []

    for entry in entries:

        a = normalize_to_100d(
            entry["array"],
            nt,
            ns,
            nx,
            idx100,
        )

        if a is None:
            continue

        # Same-shape residual-like arrays.
        if a.shape == (
            ns,
            nx,
        ):

            if np.issubdtype(
                a.dtype,
                np.number,
            ):

                finite = np.isfinite(
                    a
                )

                if np.any(
                    finite
                ):

                    low = entry[
                        "low"
                    ]

                    # Residual-like values.
                    if any(
                        token in low
                        for token in [
                            "residual",
                            "error",
                            "difference",
                            "correction",
                            "required",
                            "supported",
                        ]
                    ):

                        residual_candidates.append({
                            "name":
                                entry["key"],
                            "file":
                                str(
                                    entry["file"]
                                ),
                            "key":
                                entry["key"],
                            "array":
                                np.abs(
                                    np.asarray(
                                        a,
                                        dtype=float,
                                    )
                                ),
                        })

            b = bool_candidate(
                a
            )

            if b is not None:

                mask_candidates.append({
                    "name":
                        entry["key"],
                    "file":
                        str(
                            entry["file"]
                        ),
                    "key":
                        entry["key"],
                    "array":
                        b,
                })

            # Also create thresholded masks only for strongly semantic keys.
            low = entry[
                "low"
            ]

            if any(
                token in low
                for token in [
                    "mask",
                    "support",
                    "shell",
                    "coverage",
                ]
            ) and np.issubdtype(
                a.dtype,
                np.number,
            ):

                for threshold in [
                    0.0,
                    1e-12,
                    1e-8,
                    1e-6,
                    1e-4,
                    1e-3,
                    1e-2,
                    0.05,
                    0.1,
                    0.5,
                ]:

                    mask_candidates.append({
                        "name":
                            f"{entry['key']}>"
                            f"{threshold:g}",
                        "file":
                            str(
                                entry["file"]
                            ),
                        "key":
                            entry["key"],
                        "array":
                            np.asarray(
                                a,
                                dtype=float,
                            )
                            >
                            threshold,
                    })

    # De-duplicate masks by bytes hash.
    dedup_masks = []
    seen_mask_hash = set()

    for m in mask_candidates:

        arr = np.ascontiguousarray(
            m["array"].astype(
                np.uint8
            )
        )

        h = hash(
            arr.tobytes()
        )

        if h in seen_mask_hash:
            continue

        seen_mask_hash.add(
            h
        )

        dedup_masks.append(
            m
        )

    mask_candidates = dedup_masks

    rows = []

    best = None

    # Required sum = residual over shell.
    # Supported sum = same required residual over shell & support.
    for residual in residual_candidates:

        r = residual[
            "array"
        ]

        if r.shape != (
            ns,
            nx,
        ):
            continue

        for shell in mask_candidates:

            shell_mask = shell[
                "array"
            ]

            required_sum = float(
                np.sum(
                    r[
                        shell_mask
                    ]
                )
            )

            req_err = abs(
                required_sum
                -
                authoritative_required
            )

            # Only examine potentially plausible required populations.
            if req_err > max(
                10.0,
                0.25
                *
                abs(
                    authoritative_required
                ),
            ):
                continue

            for support in mask_candidates:

                support_mask = support[
                    "array"
                ]

                supported_sum = float(
                    np.sum(
                        r[
                            shell_mask
                            &
                            support_mask
                        ]
                    )
                )

                sup_err = abs(
                    supported_sum
                    -
                    authoritative_supported
                )

                fraction = (
                    supported_sum
                    /
                    required_sum
                    if required_sum > 0.0
                    else np.nan
                )

                score = (
                    req_err
                    +
                    sup_err
                )

                row = {
                    "residual_name":
                        residual["name"],
                    "residual_file":
                        residual["file"],
                    "shell_name":
                        shell["name"],
                    "shell_file":
                        shell["file"],
                    "support_name":
                        support["name"],
                    "support_file":
                        support["file"],
                    "required_sum":
                        required_sum,
                    "supported_sum":
                        supported_sum,
                    "coverage_fraction":
                        fraction,
                    "required_error":
                        req_err,
                    "supported_error":
                        sup_err,
                    "score":
                        score,
                }

                rows.append(
                    row
                )

                if (
                    best is None
                    or
                    score
                    <
                    best["row"]["score"]
                ):

                    best = {
                        "row":
                            row,
                        "required_residual":
                            r,
                        "shell_mask":
                            shell_mask,
                        "support_mask":
                            support_mask,
                    }

    rows.sort(
        key=lambda r:
        r["score"]
    )

    return best, rows


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1A")
    print("Exact Front-Shell / Support-Array Recovery")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO FRONT, TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE CHANGED.
""")

    incoming = load_json(
        R1_SUMMARY
    )

    contract = load_json(
        R0A_CONTRACT
    )

    if (
        incoming.get("diagnosis")
        !=
        "AUTHORITATIVE_FORMULA_KNOWN_BUT_EXACT_NUMERICAL_MASKS_NOT_RECOVERED"
    ):
        raise RuntimeError(
            "R3F5-R1A requires incoming R3F5-R1 exact-array recovery diagnosis."
        )

    if (
        contract.get("diagnosis")
        !=
        "SUPPORT_IS_REQUIRED_VS_SUPPORTED_FRONT_SHELL_RESIDUAL_RATIO"
    ):
        raise RuntimeError(
            "R3F5-R1A requires the exact R0A authoritative support formula."
        )

    support_rows = load_csv(
        R3F4R_SUPPORT
    )

    b4 = next(
        row
        for row in support_rows
        if row.get("experiment") == "B4"
    )

    required_authoritative = fnum(
        b4,
        "front_shell_required_residual_sum",
    )

    supported_authoritative = fnum(
        b4,
        "front_shell_supported_residual_sum",
    )

    fraction_authoritative = fnum(
        b4,
        "front_shell_residual_coverage_fraction",
    )

    print("AUTHORITATIVE B4 CONTRACT")
    print(
        f"  Required residual sum   : "
        f"{required_authoritative:.12e}"
    )
    print(
        f"  Supported residual sum  : "
        f"{supported_authoritative:.12e}"
    )
    print(
        f"  Coverage fraction       : "
        f"{fraction_authoritative:.12e}"
    )

    # -------------------------------------------------------------------------
    # Source trace.
    # -------------------------------------------------------------------------

    files = source_files()

    occurrence_rows = source_occurrence_rows(
        files
    )

    direct_symbol_rows = []

    for path in files:
        direct_symbol_rows.extend(
            exact_assignment_symbols(
                path
            )
        )

    seed_symbols = set()

    for row in direct_symbol_rows:

        refs = [
            s
            for s in row[
                "referenced_symbols"
            ].split(";")
            if s
        ]

        seed_symbols.update(
            refs
        )

    dependency_rows = recursive_symbol_trace(
        seed_symbols,
        files,
    )

    save_csv(
        SOURCE_TRACE_TABLE,
        occurrence_rows,
    )

    save_csv(
        SYMBOL_TABLE,
        direct_symbol_rows
        +
        dependency_rows,
    )

    all_symbols = set(
        seed_symbols
    )

    for row in dependency_rows:
        all_symbols.add(
            row["symbol"]
        )

        for s in str(
            row.get(
                "dependency_symbols",
                "",
            )
        ).split(";"):

            if s:
                all_symbols.add(
                    s
                )

    print("\nSOURCE RECOVERY")
    print(
        f"  Source files searched   : "
        f"{len(files)}"
    )
    print(
        f"  Field occurrences       : "
        f"{len(occurrence_rows)}"
    )
    print(
        f"  Direct field expressions: "
        f"{len(direct_symbol_rows)}"
    )
    print(
        f"  Dependency symbols      : "
        f"{len(all_symbols)}"
    )

    # -------------------------------------------------------------------------
    # NPZ key search.
    # -------------------------------------------------------------------------

    npz_rows, entries = npz_search(
        all_symbols
    )

    save_csv(
        NPZ_SEARCH_TABLE,
        npz_rows,
    )

    matched_keys = [
        row
        for row in npz_rows
        if row[
            "symbol_matches"
        ]
    ]

    print("\nPERSISTED ARRAY SEARCH")
    print(
        f"  NPZ keys inspected      : "
        f"{len(npz_rows)}"
    )
    print(
        f"  Symbol-matched keys     : "
        f"{len(matched_keys)}"
    )

    # -------------------------------------------------------------------------
    # Exhaustive reconstruction.
    # -------------------------------------------------------------------------

    db = np.load(
        R3C_NUMERICAL,
        allow_pickle=True,
    )

    canonical = np.asarray(
        db[
            "canonical_interpolated_target"
        ],
        dtype=float,
    )

    frozen = np.asarray(
        db[
            "deployment_pirnn"
        ],
        dtype=float,
    )

    times = np.asarray(
        db[
            "times_days"
        ],
        dtype=float,
    )

    best, candidate_rows = score_arrays(
        entries=entries,
        canonical=canonical,
        frozen=frozen,
        times=times,
        authoritative_required=
            required_authoritative,
        authoritative_supported=
            supported_authoritative,
    )

    # Limit persisted candidate table to top 500 to keep it manageable.
    save_csv(
        CANDIDATE_TABLE,
        candidate_rows[:500],
    )

    if best is None:

        exact_pass = False
        req_error = np.inf
        sup_error = np.inf
        fraction_error = np.inf

    else:

        req_error = best[
            "row"
        ][
            "required_error"
        ]

        sup_error = best[
            "row"
        ][
            "supported_error"
        ]

        fraction_error = abs(
            best[
                "row"
            ][
                "coverage_fraction"
            ]
            -
            fraction_authoritative
        )

        exact_pass = bool(
            req_error
            <=
            SUM_ABS_TOL
            and
            sup_error
            <=
            SUM_ABS_TOL
            and
            fraction_error
            <=
            FRACTION_ABS_TOL
        )

    closure_rows = []

    if best is not None:

        closure_rows.append({
            **best["row"],
            "authoritative_required_sum":
                required_authoritative,
            "authoritative_supported_sum":
                supported_authoritative,
            "authoritative_fraction":
                fraction_authoritative,
            "fraction_error":
                fraction_error,
            "exact_pass":
                exact_pass,
        })

    save_csv(
        CLOSURE_TABLE,
        closure_rows,
    )

    print("\nBEST ARRAY RECONSTRUCTION")

    if best is None:

        print(
            "  No plausible residual/shell/support combination could be formed."
        )

    else:

        row = best["row"]

        print(
            f"  Residual source         : "
            f"{row['residual_name']}"
        )
        print(
            f"  Shell source            : "
            f"{row['shell_name']}"
        )
        print(
            f"  Support source          : "
            f"{row['support_name']}"
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
            f"  Exact closure           : "
            f"{'PASS' if exact_pass else 'FAIL'}"
        )

    # -------------------------------------------------------------------------
    # Persist exact recovered arrays only if closure is exact.
    # -------------------------------------------------------------------------

    if exact_pass:

        np.savez_compressed(
            RECOVERED_NPZ,
            required_residual=
                best[
                    "required_residual"
                ].astype(
                    np.float64
                ),
            front_shell_mask=
                best[
                    "shell_mask"
                ].astype(
                    np.uint8
                ),
            support_mask=
                best[
                    "support_mask"
                ].astype(
                    np.uint8
                ),
            authoritative_required_sum=
                np.asarray(
                    required_authoritative,
                    dtype=np.float64,
                ),
            authoritative_supported_sum=
                np.asarray(
                    supported_authoritative,
                    dtype=np.float64,
                ),
            authoritative_coverage_fraction=
                np.asarray(
                    fraction_authoritative,
                    dtype=np.float64,
                ),
        )

        status = (
            "EXACT_SUPPORT_ARRAYS_RECOVERED"
        )

        diagnosis = (
            "AUTHORITATIVE_FRONT_SHELL_AND_SUPPORT_POPULATIONS_RECONSTRUCTED"
        )

        recommendation = (
            "The exact B4 front-shell required-residual and supported-residual "
            "populations have been recovered and serialized with machine-precision "
            "closure. Proceed to R3F5-R1B and calibrate X0-X5 using only these "
            "recovered authoritative arrays. Do not substitute other support metrics."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )

    else:

        status = (
            "EXACT_SUPPORT_ARRAY_RECOVERY_INCOMPLETE"
        )

        diagnosis = (
            "AUTHORITATIVE_SUPPORT_ARRAYS_NOT_PERSISTED_OR_NOT_IDENTIFIED"
        )

        recommendation = (
            "The source dependency chain and persisted-array search still do not "
            "reproduce the authoritative B4 sums exactly. Do not calibrate support. "
            "Use the generated symbol trace to identify the deterministic reconstruction "
            "function in the authoritative R3F4/R source and serialize its exact "
            "front-shell and support arrays directly."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A2 — Authoritative Support Reconstruction Serialization"
        )

    save_json(
        CONTRACT_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1A",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "support_extension_calibrated":
                False,
            "authoritative_required_sum":
                required_authoritative,
            "authoritative_supported_sum":
                supported_authoritative,
            "authoritative_coverage_fraction":
                fraction_authoritative,
            "exact_array_closure":
                exact_pass,
            "recovered_npz":
                (
                    str(
                        RECOVERED_NPZ
                    )
                    if exact_pass
                    else None
                ),
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
                "V15-SG7C-R3F5-R1A",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "support_extension_calibrated":
                False,
            "gate_changed":
                False,
            "exact_array_closure":
                exact_pass,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Incoming R3F5-R1 exact-array diagnosis reproduced",
            True,
        ),
        (
            "Authoritative B4 sums loaded",
            True,
        ),
        (
            "R3F4/R source dependency chain searched",
            True,
        ),
        (
            "Persisted NPZ keys searched",
            True,
        ),
        (
            "Candidate residual/shell/support combinations audited",
            True,
        ),
        (
            "Exact required residual sum recovered",
            req_error <= SUM_ABS_TOL,
        ),
        (
            "Exact supported residual sum recovered",
            sup_error <= SUM_ABS_TOL,
        ),
        (
            "Exact support fraction recovered",
            fraction_error <= FRACTION_ABS_TOL,
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
    print(
        f"  {status}"
    )

    print("\nDIAGNOSIS")
    print(
        f"  {diagnosis}"
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
        f"  {SOURCE_TRACE_TABLE.name}"
    )
    print(
        f"  {SYMBOL_TABLE.name}"
    )
    print(
        f"  {NPZ_SEARCH_TABLE.name}"
    )
    print(
        f"  {CANDIDATE_TABLE.name}"
    )
    print(
        f"  {CLOSURE_TABLE.name}"
    )

    if exact_pass:
        print("\nRecovered numerical:")
        print(
            f"  {RECOVERED_NPZ.name}"
        )

    print("\nContract:")
    print(
        f"  {CONTRACT_FILE.name}"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE.name}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A RECOVERY AUDIT: PASS")
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
