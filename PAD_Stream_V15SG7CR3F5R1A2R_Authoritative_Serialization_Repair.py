from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1A2R
# Authoritative Serialization Repair
#
# RUNTIME SHAPE / SEMANTIC AUDIT
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R3F5-R1A2 correctly located the authoritative R3F4-R source, but automatic
# semantic selection chose:
#
#   front shell         -> coverage_limited
#   required residual   -> required_shell
#   support/coefficient -> coeff100
#
# and the injected serializer failed with:
#
#   IndexError: too many indices for array: array is 1-dimensional,
#               but 2 were indexed
#
# This proves at least one selected runtime variable did not have the assumed
# 2-D front-shell geometry.
#
# R3F5-R1A2R therefore stops guessing by variable name.
#
# It instruments the authoritative R3F4-R runtime and records, for every
# candidate variable near the support calculation:
#
#   * Python type
#   * NumPy shape
#   * ndim
#   * dtype
#   * finite fraction
#   * min / max / mean
#   * boolean-like status
#   * whether shape matches required_shell
#   * whether it can reproduce:
#
#         front_shell_required_residual_sum
#         front_shell_supported_residual_sum
#
# The original R3F4-R source is never overwritten.
# A patched runtime copy is created solely for diagnostics.
#
# If the exact compatible array triplet is identified, R1A2R serializes it
# directly and routes to R3F5-R1B.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1A2R"
OUT.mkdir(parents=True, exist_ok=True)

R1A2_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1A2"
    / "PAD_Stream_V15SG7CR3F5R1A2_Summary.json"
)

R1A2_PATCH_AUDIT = (
    ROOT / "output" / "V15_SG7CR3F5R1A2"
    / "V15SG7CR3F5R1A2_Serialization_Patch_Audit.csv"
)

R1A2_VARIABLES = (
    ROOT / "output" / "V15_SG7CR3F5R1A2"
    / "V15SG7CR3F5R1A2_Runtime_Variable_Selection.csv"
)

R3F4R_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

PATCHED_RUNTIME = (
    ROOT / "PAD_Stream_V15SG7CR3F5R1A2R_Runtime_Shape_Audit.py"
)

RUNTIME_DUMP = OUT / "V15SG7CR3F5R1A2R_Runtime_Variables.npz"
EXACT_ARRAYS = OUT / "V15SG7CR3F5R1A2R_Exact_Support_Arrays.npz"

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1A2R_Summary.json"
RUNTIME_TABLE = OUT / "V15SG7CR3F5R1A2R_Runtime_Variable_Shapes.csv"
PAIR_TABLE = OUT / "V15SG7CR3F5R1A2R_Array_Compatibility_Audit.csv"
CLOSURE_TABLE = OUT / "V15SG7CR3F5R1A2R_Exact_Closure_Audit.csv"
PATCH_TABLE = OUT / "V15SG7CR3F5R1A2R_Runtime_Patch_Audit.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1A2R_Authoritative_Serialization_Repair_Contract.json"

TARGET_FIELDS = [
    "front_shell_required_residual_sum",
    "front_shell_supported_residual_sum",
    "front_shell_residual_coverage_fraction",
]

SUM_ABS_TOL = 1e-8
FRACTION_ABS_TOL = 1e-10


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


def select_original_source():
    rows = load_csv(R1A2_PATCH_AUDIT)
    if not rows:
        raise RuntimeError("R1A2 patch audit is empty.")

    source = Path(rows[0]["original_source"])
    function_name = rows[0]["function"]

    if not source.is_absolute():
        source = ROOT / source

    if not source.exists():
        raise FileNotFoundError(f"Authoritative source missing:\n{source}")

    return source, function_name


def parse_function(path: Path, function_name: str):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text, filename=str(path))
    lines = text.splitlines()

    fn = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            fn = node
            break

    if fn is None:
        raise RuntimeError(f"Function '{function_name}' not found in {path.name}")

    return text, lines, fn


def candidate_runtime_variables(path: Path, function_name: str):
    _, _, fn = parse_function(path, function_name)

    rows = []

    for node in ast.walk(fn):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        targets = node.targets if isinstance(node, ast.Assign) else [node.target]

        if node.value is None:
            continue

        for target in targets:
            if not isinstance(target, ast.Name):
                continue

            name = target.id
            expr = ast.unparse(node.value)
            low = (name + " " + expr).lower()

            score = 0

            for token, weight in [
                ("front", 2),
                ("shell", 4),
                ("residual", 4),
                ("support", 4),
                ("coeff", 3),
                ("mask", 3),
                ("coverage", 2),
                ("required", 2),
                ("supported", 2),
                ("canonical", 1),
                ("frozen", 1),
                ("truth", 1),
            ]:
                if token in low:
                    score += weight

            if score > 0:
                rows.append({
                    "variable": name,
                    "line_number": getattr(node, "lineno", -1),
                    "expression": expr,
                    "semantic_score": score,
                })

    # Guarantee the previously selected variables are included.
    prior_rows = load_csv(R1A2_VARIABLES)

    for prior in prior_rows:
        name = prior.get("variable")
        if not name:
            continue

        if not any(row["variable"] == name for row in rows):
            rows.append({
                "variable": name,
                "line_number": prior.get("line_number", ""),
                "expression": prior.get("expression", ""),
                "semantic_score": prior.get("semantic_score", 0),
            })

    # de-duplicate by name, keeping highest score
    best = {}

    for row in rows:
        name = row["variable"]
        score = float(row.get("semantic_score") or 0)

        if name not in best or score > float(best[name].get("semantic_score") or 0):
            best[name] = row

    out = list(best.values())
    out.sort(key=lambda r: (-float(r.get("semantic_score") or 0), str(r["variable"])))

    return out


def last_target_line(path: Path, function_name: str):
    _, lines, fn = parse_function(path, function_name)

    start = fn.lineno
    end = getattr(fn, "end_lineno", start)

    line_number = None

    for i in range(start - 1, end):
        if any(field in lines[i] for field in TARGET_FIELDS):
            line_number = i + 1

    if line_number is None:
        raise RuntimeError("Could not locate support metric calculation line.")

    return line_number


def indentation(line: str):
    return line[: len(line) - len(line.lstrip())]


def build_runtime_probe(indent: str, variable_names: list[str]):
    names_repr = repr(variable_names)

    raw = [
        "# --- V15-SG7C-R3F5-R1A2R RUNTIME PROBE BEGIN ---",
        "try:",
        f"    _r1a2r_names = {names_repr}",
        "    _r1a2r_payload = {}",
        "    _r1a2r_meta = []",
        "    for _r1a2r_name in _r1a2r_names:",
        "        if _r1a2r_name not in locals():",
        "            _r1a2r_meta.append((_r1a2r_name, 'MISSING', '', '', '', '', '', '', ''))",
        "            continue",
        "        _r1a2r_obj = locals()[_r1a2r_name]",
        "        try:",
        "            _r1a2r_arr = np.asarray(_r1a2r_obj)",
        "        except Exception:",
        "            _r1a2r_meta.append((_r1a2r_name, type(_r1a2r_obj).__name__, '', '', '', '', '', '', ''))",
        "            continue",
        "        _r1a2r_payload[_r1a2r_name] = _r1a2r_arr",
        "        try:",
        "            _r1a2r_numeric = np.issubdtype(_r1a2r_arr.dtype, np.number) or _r1a2r_arr.dtype == bool",
        "        except Exception:",
        "            _r1a2r_numeric = False",
        "        if _r1a2r_numeric and _r1a2r_arr.size:",
        "            try:",
        "                _r1a2r_finite = np.isfinite(_r1a2r_arr.astype(float))",
        "                _r1a2r_ff = float(np.mean(_r1a2r_finite))",
        "                if np.any(_r1a2r_finite):",
        "                    _r1a2r_vals = _r1a2r_arr.astype(float)[_r1a2r_finite]",
        "                    _r1a2r_min = float(np.min(_r1a2r_vals))",
        "                    _r1a2r_max = float(np.max(_r1a2r_vals))",
        "                    _r1a2r_mean = float(np.mean(_r1a2r_vals))",
        "                else:",
        "                    _r1a2r_min = _r1a2r_max = _r1a2r_mean = float('nan')",
        "            except Exception:",
        "                _r1a2r_ff = _r1a2r_min = _r1a2r_max = _r1a2r_mean = float('nan')",
        "        else:",
        "            _r1a2r_ff = _r1a2r_min = _r1a2r_max = _r1a2r_mean = float('nan')",
        "        _r1a2r_meta.append((",
        "            _r1a2r_name,",
        "            type(_r1a2r_obj).__name__,",
        "            str(tuple(_r1a2r_arr.shape)),",
        "            int(_r1a2r_arr.ndim),",
        "            str(_r1a2r_arr.dtype),",
        "            int(_r1a2r_arr.size),",
        "            _r1a2r_ff,",
        "            _r1a2r_min,",
        "            _r1a2r_max,",
        "            _r1a2r_mean,",
        "        ))",
        "    _r1a2r_out = Path(__file__).resolve().parent / 'output' / 'V15_SG7CR3F5R1A2R'",
        "    _r1a2r_out.mkdir(parents=True, exist_ok=True)",
        "    np.savez_compressed(",
        "        _r1a2r_out / 'V15SG7CR3F5R1A2R_Runtime_Variables.npz',",
        "        **_r1a2r_payload,",
        "    )",
        "    with open(_r1a2r_out / 'V15SG7CR3F5R1A2R_Runtime_Meta.json', 'w', encoding='utf-8') as _r1a2r_f:",
        "        json.dump(_r1a2r_meta, _r1a2r_f, indent=2)",
        "    print('\\n[R3F5-R1A2R] Runtime variable probe serialized.')",
        "except Exception as _r1a2r_exc:",
        "    print('[R3F5-R1A2R] Runtime probe failed: %r' % (_r1a2r_exc,))",
        "# --- V15-SG7C-R3F5-R1A2R RUNTIME PROBE END ---",
    ]

    return [indent + line if line else "" for line in raw]


def patch_runtime(source_path: Path, function_name: str, variable_names: list[str]):
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    inject_after = last_target_line(source_path, function_name)
    indent = indentation(lines[inject_after - 1])

    probe = build_runtime_probe(indent, variable_names)

    patched = lines[:inject_after] + probe + lines[inject_after:]

    # Required imports for the probe.
    first_100 = "\n".join(patched[:100])

    insert_at = 0

    if patched and patched[0].startswith("#!"):
        insert_at = 1

    if "from pathlib import Path" not in first_100:
        patched.insert(insert_at, "from pathlib import Path")
        insert_at += 1

    if "import json" not in first_100:
        patched.insert(insert_at, "import json")

    return "\n".join(patched) + "\n", inject_after


def describe_runtime(meta_rows):
    rows = []

    for item in meta_rows:
        # missing rows may be shorter
        padded = list(item) + [""] * (10 - len(item))

        rows.append({
            "variable": padded[0],
            "python_type": padded[1],
            "shape": padded[2],
            "ndim": padded[3],
            "dtype": padded[4],
            "size": padded[5],
            "finite_fraction": padded[6],
            "min": padded[7],
            "max": padded[8],
            "mean": padded[9],
        })

    return rows


def is_boolean_like(arr):
    a = np.asarray(arr)

    if a.dtype == bool:
        return True

    if a.size == 0 or not np.issubdtype(a.dtype, np.number):
        return False

    finite = np.isfinite(a.astype(float))

    if not np.any(finite):
        return False

    vals = np.unique(a.astype(float)[finite])

    return (
        vals.size <= 4
        and np.all(np.isclose(vals, np.round(vals)))
        and np.all((vals >= 0) & (vals <= 1))
    )


def mask_versions(name, arr):
    a = np.asarray(arr)

    out = []

    if is_boolean_like(a):
        out.append((name + "::bool", a.astype(bool)))

    if np.issubdtype(a.dtype, np.number):
        af = a.astype(float)

        for threshold in [0.0, 1e-12, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 0.05, 0.1, 0.5]:
            out.append((f"{name}::gt_{threshold:g}", af > threshold))

    return out


def residual_versions(name, arr):
    a = np.asarray(arr)

    if not np.issubdtype(a.dtype, np.number):
        return []

    af = a.astype(float)

    return [
        (name + "::abs", np.abs(af)),
        (name + "::raw", af),
    ]


def exact_compatibility_search(db, auth_required, auth_supported, auth_fraction):
    arrays = {
        key: np.asarray(db[key])
        for key in db.files
    }

    residuals = []
    masks = []

    for name, arr in arrays.items():
        if arr.ndim == 0:
            continue

        residuals.extend(residual_versions(name, arr))
        masks.extend(mask_versions(name, arr))

    rows = []
    best = None

    for res_name, res in residuals:
        for shell_name, shell in masks:
            if res.shape != shell.shape:
                continue

            required_sum = float(np.sum(res[shell]))

            req_err = abs(required_sum - auth_required)

            # prune wildly wrong candidates
            if req_err > max(10.0, 0.25 * abs(auth_required)):
                continue

            for support_name, support in masks:
                if support.shape != res.shape:
                    continue

                supported_sum = float(np.sum(res[shell & support]))

                sup_err = abs(supported_sum - auth_supported)

                fraction = supported_sum / required_sum if required_sum > 0 else np.nan

                frac_err = abs(fraction - auth_fraction)

                score = req_err + sup_err

                row = {
                    "residual": res_name,
                    "shell": shell_name,
                    "support": support_name,
                    "shape": str(res.shape),
                    "required_sum": required_sum,
                    "supported_sum": supported_sum,
                    "coverage_fraction": fraction,
                    "required_error": req_err,
                    "supported_error": sup_err,
                    "fraction_error": frac_err,
                    "score": score,
                }

                rows.append(row)

                if best is None or score < best["row"]["score"]:
                    best = {
                        "row": row,
                        "required_residual": res,
                        "shell_mask": shell,
                        "support_mask": support,
                    }

    rows.sort(key=lambda r: r["score"])

    return best, rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1A2R")
    print("Authoritative Serialization Repair")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO GATE WILL BE CHANGED OR RELAXED.
THIS MILESTONE AUDITS RUNTIME ARRAY SHAPES BEFORE SERIALIZATION.
""")

    incoming = load_json(R1A2_SUMMARY)

    if incoming.get("diagnosis") != "SERIALIZED_RUNTIME_ARRAYS_DO_NOT_YET_CLOSE_AUTHORITATIVE_CONTRACT":
        raise RuntimeError(
            "R3F5-R1A2R requires the R3F5-R1A2 serialization-repair diagnosis."
        )

    support_rows = load_csv(R3F4R_SUPPORT)
    b4 = next(row for row in support_rows if row.get("experiment") == "B4")

    auth_required = fnum(b4, "front_shell_required_residual_sum")
    auth_supported = fnum(b4, "front_shell_supported_residual_sum")
    auth_fraction = fnum(b4, "front_shell_residual_coverage_fraction")

    print("AUTHORITATIVE B4 CONTRACT")
    print(f"  Required residual sum   : {auth_required:.12e}")
    print(f"  Supported residual sum  : {auth_supported:.12e}")
    print(f"  Coverage fraction       : {auth_fraction:.12e}")

    source_path, function_name = select_original_source()

    variable_rows = candidate_runtime_variables(
        source_path,
        function_name,
    )

    variable_names = [row["variable"] for row in variable_rows]

    print("\nRUNTIME AUDIT PLAN")
    print(f"  Authoritative source    : {source_path.name}")
    print(f"  Function                : {function_name}")
    print(f"  Candidate variables     : {len(variable_names)}")

    patched_text, injection_line = patch_runtime(
        source_path,
        function_name,
        variable_names,
    )

    PATCHED_RUNTIME.write_text(
        patched_text,
        encoding="utf-8",
    )

    save_csv(PATCH_TABLE, [{
        "original_source": str(source_path),
        "patched_runtime_copy": str(PATCHED_RUNTIME),
        "function": function_name,
        "injection_after_line": injection_line,
        "candidate_variable_count": len(variable_names),
        "original_overwritten": False,
    }])

    namespace = {
        "__name__": "__main__",
        "__file__": str(PATCHED_RUNTIME),
    }

    runtime_error = None

    try:
        exec(
            compile(
                patched_text,
                str(PATCHED_RUNTIME),
                "exec",
            ),
            namespace,
            namespace,
        )
    except SystemExit as exc:
        if exc.code not in (None, 0):
            runtime_error = repr(exc)
    except Exception as exc:
        runtime_error = repr(exc)

    meta_path = OUT / "V15SG7CR3F5R1A2R_Runtime_Meta.json"

    runtime_dump_exists = RUNTIME_DUMP.exists()
    meta_exists = meta_path.exists()

    runtime_rows = []

    if meta_exists:
        meta = load_json(meta_path)
        runtime_rows = describe_runtime(meta)
        save_csv(RUNTIME_TABLE, runtime_rows)

    print("\nRUNTIME VARIABLE SHAPES")

    for row in runtime_rows[:30]:
        print(
            f"  {row['variable']:<28s} "
            f"shape={row['shape']:<18s} "
            f"ndim={row['ndim']} "
            f"dtype={row['dtype']}"
        )

    best = None
    compatibility_rows = []

    if runtime_dump_exists:
        db = np.load(RUNTIME_DUMP, allow_pickle=True)

        best, compatibility_rows = exact_compatibility_search(
            db,
            auth_required,
            auth_supported,
            auth_fraction,
        )

        save_csv(
            PAIR_TABLE,
            compatibility_rows[:500],
        )

    if best is None:
        req_error = np.inf
        sup_error = np.inf
        frac_error = np.inf
        exact_pass = False
    else:
        req_error = best["row"]["required_error"]
        sup_error = best["row"]["supported_error"]
        frac_error = best["row"]["fraction_error"]

        exact_pass = bool(
            req_error <= SUM_ABS_TOL
            and sup_error <= SUM_ABS_TOL
            and frac_error <= FRACTION_ABS_TOL
        )

    if best is not None:
        print("\nBEST RUNTIME ARRAY TRIPLET")
        print(f"  Residual                : {best['row']['residual']}")
        print(f"  Front shell             : {best['row']['shell']}")
        print(f"  Support                 : {best['row']['support']}")
        print(f"  Shape                   : {best['row']['shape']}")
        print(f"  Required sum            : {best['row']['required_sum']:.12e}")
        print(f"  Supported sum           : {best['row']['supported_sum']:.12e}")
        print(f"  Coverage                : {best['row']['coverage_fraction']:.12e}")
        print(f"  Required error          : {req_error:.6e}")
        print(f"  Supported error         : {sup_error:.6e}")
        print(f"  Fraction error          : {frac_error:.6e}")
        print(f"  Exact closure           : {'PASS' if exact_pass else 'FAIL'}")

    if exact_pass:
        np.savez_compressed(
            EXACT_ARRAYS,
            required_residual=np.asarray(best["required_residual"], dtype=np.float64),
            front_shell_mask=np.asarray(best["shell_mask"], dtype=np.uint8),
            support_mask=np.asarray(best["support_mask"], dtype=np.uint8),
            authoritative_required_sum=np.asarray(auth_required, dtype=np.float64),
            authoritative_supported_sum=np.asarray(auth_supported, dtype=np.float64),
            authoritative_coverage_fraction=np.asarray(auth_fraction, dtype=np.float64),
        )

        save_csv(CLOSURE_TABLE, [{
            **best["row"],
            "authoritative_required_sum": auth_required,
            "authoritative_supported_sum": auth_supported,
            "authoritative_fraction": auth_fraction,
            "exact_closure": True,
        }])

        status = "AUTHORITATIVE_SERIALIZATION_REPAIRED"
        diagnosis = "EXACT_RUNTIME_SUPPORT_ARRAY_TRIPLET_IDENTIFIED"
        recommendation = (
            "The exact runtime residual/front-shell/support array triplet has been "
            "identified by shape-compatible closure rather than variable-name guessing. "
            "Proceed to exact-array minimal-support extension calibration."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )
    else:
        status = "AUTHORITATIVE_SERIALIZATION_VARIABLES_STILL_AMBIGUOUS"
        diagnosis = "RUNTIME_SHAPES_RECOVERED_BUT_EXACT_SUPPORT_TRIPLET_NOT_YET_CLOSED"
        recommendation = (
            "Runtime variable shapes are now available, but no array triplet closes the "
            "authoritative B4 support contract exactly. Do not calibrate support. Inspect "
            "the top compatibility candidates and identify the deterministic transformation "
            "between the runtime residual/support variables and the reported sums."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1A2R2 — Runtime Support-Transformation Audit"
        )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7C-R3F5-R1A2R",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_calibrated": False,
        "runtime_dump_produced": runtime_dump_exists,
        "exact_closure": exact_pass,
        "exact_arrays": str(EXACT_ARRAYS) if exact_pass else None,
        "runtime_error": runtime_error,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7C-R3F5-R1A2R",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_calibrated": False,
        "gate_changed": False,
        "exact_closure": exact_pass,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R3F5-R1A2 diagnosis reproduced", True),
        ("Authoritative source loaded", source_path.exists()),
        ("Runtime probe copy generated", PATCHED_RUNTIME.exists()),
        ("Original source left unchanged", True),
        ("Runtime metadata produced", meta_exists),
        ("Runtime NPZ produced", runtime_dump_exists),
        ("Runtime variable shapes audited", bool(runtime_rows)),
        ("Compatible array triplets searched", runtime_dump_exists),
        ("Exact required sum closes", req_error <= SUM_ABS_TOL),
        ("Exact supported sum closes", sup_error <= SUM_ABS_TOL),
        ("Exact support fraction closes", frac_error <= FRACTION_ABS_TOL),
        ("No support extension calibrated", True),
        ("No training performed", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    print("=" * 78)

    if runtime_error:
        print("\nRUNTIME EXECUTION NOTE")
        print(f"  {runtime_error}")

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
    print(f"  {RUNTIME_TABLE.name}")
    print(f"  {PAIR_TABLE.name}")
    print(f"  {CLOSURE_TABLE.name}")
    print(f"  {PATCH_TABLE.name}")

    print("\nRuntime probe:")
    print(f"  {PATCHED_RUNTIME.name}")

    if runtime_dump_exists:
        print("\nRuntime numerical:")
        print(f"  {RUNTIME_DUMP.name}")

    if exact_pass:
        print("\nRecovered exact arrays:")
        print(f"  {EXACT_ARRAYS.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R REPAIR AUDIT: COMPLETE")
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
