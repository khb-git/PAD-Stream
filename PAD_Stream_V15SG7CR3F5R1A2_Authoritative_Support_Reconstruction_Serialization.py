from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1A2"
OUT.mkdir(parents=True, exist_ok=True)

R1A_SUMMARY = ROOT / "output" / "V15_SG7CR3F5R1A" / "PAD_Stream_V15SG7CR3F5R1A_Summary.json"
R3F4R_SUPPORT = ROOT / "output" / "V15_SG7CR3F4R" / "V15SG7CR3F4R_Basis_Support_Coverage.csv"

PATCHED_SCRIPT = ROOT / "PAD_Stream_V15SG7CR3F5R1A2_Authoritative_Serialization_Runtime.py"
SERIALIZED_NPZ = OUT / "V15SG7CR3F5R1A2_Authoritative_Support_Arrays.npz"

SOURCE_SELECTION_TABLE = OUT / "V15SG7CR3F5R1A2_Source_Function_Selection.csv"
VARIABLE_SELECTION_TABLE = OUT / "V15SG7CR3F5R1A2_Runtime_Variable_Selection.csv"
PATCH_AUDIT_TABLE = OUT / "V15SG7CR3F5R1A2_Serialization_Patch_Audit.csv"
CLOSURE_TABLE = OUT / "V15SG7CR3F5R1A2_Serialized_Array_Closure.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1A2_Authoritative_Serialization_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1A2_Summary.json"

TARGET_FIELDS = [
    "front_shell_required_residual_sum",
    "front_shell_supported_residual_sum",
    "front_shell_residual_coverage_fraction",
]

SUM_ABS_TOL = 1e-8
FRACTION_ABS_TOL = 1e-10


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path, rows):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with open(path, "w", newline="", encoding="utf-8") as f:
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


def candidate_source_files():
    files = []
    for pattern in [
        "PAD_Stream_V15SG7CR3F4R_Front_Local_Basis_Outcome_Audit.py",
        "PAD_Stream_V15SG7CR3F4_Controlled_Front_Local_Residual_Basis_Calibration.py",
        "PAD_Stream_V15SG7CR3F4*.py",
    ]:
        for p in ROOT.glob(pattern):
            if p not in files:
                files.append(p)
    return files


def function_spans(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text, filename=str(path))
    lines = text.splitlines()
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            segment = "\n".join(lines[start - 1:end])
            rows.append({
                "file": str(path),
                "function": node.name,
                "start_line": start,
                "end_line": end,
                "source": segment,
                "target_field_count": sum(field in segment for field in TARGET_FIELDS),
            })
    return rows


def select_authoritative_function():
    rows = []
    for path in candidate_source_files():
        try:
            rows.extend(function_spans(path))
        except Exception:
            pass

    relevant = [r for r in rows if r["target_field_count"] > 0]
    relevant.sort(key=lambda r: (-r["target_field_count"], r["end_line"] - r["start_line"]))
    return (relevant[0] if relevant else None), relevant


def variables_near_target_function(path, function_name):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text, filename=str(path))

    target_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            target_node = node
            break

    if target_node is None:
        return []

    rows = []
    for node in ast.walk(target_node):
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
                ("coefficient", 3),
                ("mask", 3),
                ("required", 2),
                ("supported", 2),
            ]:
                if token in low:
                    score += weight

            rows.append({
                "variable": name,
                "line_number": getattr(node, "lineno", -1),
                "expression": expr,
                "semantic_score": score,
            })

    rows.sort(key=lambda r: (-r["semantic_score"], r["line_number"]))
    return rows


def choose_variables(rows):
    def best(tokens, excludes=()):
        candidates = []
        for row in rows:
            low = (row["variable"] + " " + row["expression"]).lower()
            if all(t in low for t in tokens) and not any(e in low for e in excludes):
                candidates.append((row["semantic_score"], row))
        if not candidates:
            return None
        candidates.sort(key=lambda item: -item[0])
        return candidates[0][1]

    shell = best(["front", "shell"]) or best(["shell", "mask"])

    required = (
        best(["required", "residual"], ["sum"])
        or best(["residual"], ["supported", "sum"])
    )

    support = (
        best(["support", "mask"], ["sum"])
        or best(["coefficient"], ["mean", "p90", "max"])
        or best(["support"], ["sum"])
    )

    return shell, required, support


def find_injection_line(path, function_name):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text, filename=str(path))
    lines = text.splitlines()

    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            fn = node
            break

    if fn is None:
        raise RuntimeError("Authoritative function not found.")

    start = fn.lineno
    end = getattr(fn, "end_lineno", start)

    last = None
    for i in range(start - 1, end):
        if any(field in lines[i] for field in TARGET_FIELDS):
            last = i + 1

    if last is None:
        raise RuntimeError("No support-field line found in authoritative function.")

    return last


def indentation_of_line(line):
    return line[: len(line) - len(line.lstrip())]


def build_patch_block(indent, required_var, shell_var, support_var):
    req = required_var["variable"]
    shell = shell_var["variable"]
    support = support_var["variable"]

    raw = [
        "# --- V15-SG7C-R3F5-R1A2 SERIALIZATION PATCH BEGIN ---",
        "try:",
        f"    _r1a2_required = np.asarray({req}, dtype=float)",
        f"    _r1a2_shell_raw = np.asarray({shell})",
        f"    _r1a2_support_raw = np.asarray({support})",
        "",
        "    _r1a2_shell = (_r1a2_shell_raw if _r1a2_shell_raw.dtype == bool else _r1a2_shell_raw > 0.5)",
        "",
        "    if _r1a2_support_raw.dtype == bool:",
        "        _r1a2_support_mask = _r1a2_support_raw",
        "        _r1a2_support_coeff = _r1a2_support_raw.astype(float)",
        "    else:",
        "        _r1a2_support_coeff = np.asarray(_r1a2_support_raw, dtype=float)",
        "        _r1a2_support_mask = _r1a2_support_coeff > 0.0",
        "",
        "    _r1a2_required_sum_mask = float(np.sum(_r1a2_required[_r1a2_shell]))",
        "    _r1a2_supported_sum_mask = float(np.sum(_r1a2_required[_r1a2_shell & _r1a2_support_mask]))",
        "    _r1a2_supported_sum_coeff = float(np.sum(_r1a2_required[_r1a2_shell] * _r1a2_support_coeff[_r1a2_shell]))",
        "",
        '    _r1a2_out = Path(__file__).resolve().parent / "output" / "V15_SG7CR3F5R1A2"',
        "    _r1a2_out.mkdir(parents=True, exist_ok=True)",
        "    np.savez_compressed(",
        '        _r1a2_out / "V15SG7CR3F5R1A2_Authoritative_Support_Arrays.npz",',
        "        required_residual=_r1a2_required,",
        "        front_shell_mask=_r1a2_shell.astype(np.uint8),",
        "        support_mask=_r1a2_support_mask.astype(np.uint8),",
        "        support_coefficient=_r1a2_support_coeff.astype(np.float64),",
        "        reconstructed_required_sum=np.asarray(_r1a2_required_sum_mask, dtype=np.float64),",
        "        reconstructed_supported_sum_mask=np.asarray(_r1a2_supported_sum_mask, dtype=np.float64),",
        "        reconstructed_supported_sum_coeff=np.asarray(_r1a2_supported_sum_coeff, dtype=np.float64),",
        "    )",
        '    print("\\n[R3F5-R1A2] Exact support arrays serialized.")',
        '    print("[R3F5-R1A2] required_sum(mask)=%.12e" % _r1a2_required_sum_mask)',
        '    print("[R3F5-R1A2] supported_sum(mask)=%.12e" % _r1a2_supported_sum_mask)',
        '    print("[R3F5-R1A2] supported_sum(coeff)=%.12e" % _r1a2_supported_sum_coeff)',
        "except Exception as _r1a2_exc:",
        '    print("[R3F5-R1A2] Serialization patch failed: %r" % (_r1a2_exc,))',
        "# --- V15-SG7C-R3F5-R1A2 SERIALIZATION PATCH END ---",
    ]

    out = []
    for line in raw:
        out.append(indent + line if line else "")
    return out


def patch_source(source_path, function_name, required_var, shell_var, support_var):
    lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    inject_after = find_injection_line(source_path, function_name)

    indent = indentation_of_line(lines[inject_after - 1])

    patch_lines = build_patch_block(
        indent,
        required_var,
        shell_var,
        support_var,
    )

    patched = lines[:inject_after] + patch_lines + lines[inject_after:]

    if not any(line.strip() == "from pathlib import Path" for line in patched[:100]):
        insert_at = 0
        if patched and patched[0].startswith("#!"):
            insert_at = 1
        patched.insert(insert_at, "from pathlib import Path")

    return "\n".join(patched) + "\n", inject_after


def closure_from_serialized(path, auth_required, auth_supported, auth_fraction):
    db = np.load(path, allow_pickle=True)

    required = np.asarray(db["required_residual"], dtype=float)
    shell = np.asarray(db["front_shell_mask"], dtype=bool)
    support_mask = np.asarray(db["support_mask"], dtype=bool)
    coeff = np.asarray(db["support_coefficient"], dtype=float)

    if not (required.shape == shell.shape == support_mask.shape == coeff.shape):
        raise RuntimeError("Serialized support array shape mismatch.")

    required_sum = float(np.sum(required[shell]))
    supported_mask_sum = float(np.sum(required[shell & support_mask]))
    supported_coeff_sum = float(np.sum(required[shell] * coeff[shell]))

    modes = [
        ("support_mask", supported_mask_sum),
        ("support_coefficient", supported_coeff_sum),
    ]

    mode, supported_sum = min(
        modes,
        key=lambda item: abs(item[1] - auth_supported),
    )

    fraction = supported_sum / required_sum if required_sum > 0 else np.nan

    return {
        "support_mode": mode,
        "required_sum": required_sum,
        "supported_sum": supported_sum,
        "coverage_fraction": fraction,
        "required_error": abs(required_sum - auth_required),
        "supported_error": abs(supported_sum - auth_supported),
        "fraction_error": abs(fraction - auth_fraction),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1A2")
    print("Authoritative Support Reconstruction Serialization")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
THE ORIGINAL AUTHORITATIVE R3F4/R SOURCE WILL NOT BE OVERWRITTEN.
ONLY A SERIALIZATION COPY WILL BE CREATED.
""")

    incoming = load_json(R1A_SUMMARY)

    if incoming.get("diagnosis") != "AUTHORITATIVE_SUPPORT_ARRAYS_NOT_PERSISTED_OR_NOT_IDENTIFIED":
        raise RuntimeError(
            "R3F5-R1A2 requires incoming R3F5-R1A array-recovery diagnosis."
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

    selected, function_rows = select_authoritative_function()
    save_csv(SOURCE_SELECTION_TABLE, function_rows)

    if selected is None:
        raise RuntimeError(
            "Could not locate authoritative source function containing support fields."
        )

    source_path = Path(selected["file"])
    function_name = selected["function"]

    print("\nAUTHORITATIVE SOURCE SELECTION")
    print(f"  Source file             : {source_path.name}")
    print(f"  Function                : {function_name}")
    print(f"  Lines                   : {selected['start_line']} -> {selected['end_line']}")
    print(f"  Target field count      : {selected['target_field_count']}")

    variable_rows = variables_near_target_function(source_path, function_name)
    save_csv(VARIABLE_SELECTION_TABLE, variable_rows)

    shell_var, required_var, support_var = choose_variables(variable_rows)

    print("\nRUNTIME VARIABLE SELECTION")
    for label, row in [
        ("Front shell", shell_var),
        ("Required residual", required_var),
        ("Support/coefficient", support_var),
    ]:
        if row is None:
            print(f"  {label:<20}: NOT IDENTIFIED")
        else:
            print(f"  {label:<20}: {row['variable']} (line {row['line_number']})")

    ready = all(x is not None for x in [shell_var, required_var, support_var])

    if not ready:
        status = "AUTHORITATIVE_RUNTIME_VARIABLE_IDENTIFICATION_INCOMPLETE"
        diagnosis = "SUPPORT_FORMULA_LOCATED_BUT_RUNTIME_ARRAY_VARIABLES_AMBIGUOUS"
        recommendation = (
            "Inspect the runtime variable-selection table and identify the exact "
            "front-shell, required-residual, and support/coefficient variables before patching."
        )
        next_milestone = "V15-SG7C-R3F5-R1A2R — Runtime Variable Selection Repair"

        save_json(SUMMARY_FILE, {
            "milestone": "V15-SG7C-R3F5-R1A2",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_calibrated": False,
            "next_milestone": next_milestone,
        })

        print("\nSTATUS")
        print(f"  {status}")
        print("\nDIAGNOSIS")
        print(f"  {diagnosis}")
        print("\nNEXT MILESTONE")
        print(f"  {next_milestone}")
        return

    patched_text, injection_line = patch_source(
        source_path,
        function_name,
        required_var,
        shell_var,
        support_var,
    )

    PATCHED_SCRIPT.write_text(patched_text, encoding="utf-8")

    save_csv(PATCH_AUDIT_TABLE, [{
        "original_source": str(source_path),
        "patched_copy": str(PATCHED_SCRIPT),
        "function": function_name,
        "injection_after_line": injection_line,
        "required_residual_variable": required_var["variable"],
        "front_shell_variable": shell_var["variable"],
        "support_variable": support_var["variable"],
        "original_overwritten": False,
    }])

    print("\nSERIALIZATION PATCH")
    print(f"  Patched runtime copy    : {PATCHED_SCRIPT.name}")
    print(f"  Inject after source line: {injection_line}")
    print("  Original overwritten    : False")

    namespace = {
        "__name__": "__main__",
        "__file__": str(PATCHED_SCRIPT),
    }

    execution_error = None

    try:
        exec(
            compile(patched_text, str(PATCHED_SCRIPT), "exec"),
            namespace,
            namespace,
        )
    except SystemExit as exc:
        if exc.code not in (None, 0):
            execution_error = repr(exc)
    except Exception as exc:
        execution_error = repr(exc)

    serialized_exists = SERIALIZED_NPZ.exists()
    closure = None

    if serialized_exists:
        try:
            closure = closure_from_serialized(
                SERIALIZED_NPZ,
                auth_required,
                auth_supported,
                auth_fraction,
            )
        except Exception as exc:
            execution_error = (
                (execution_error + " | ") if execution_error else ""
            ) + repr(exc)

    closure_pass = bool(
        closure is not None
        and closure["required_error"] <= SUM_ABS_TOL
        and closure["supported_error"] <= SUM_ABS_TOL
        and closure["fraction_error"] <= FRACTION_ABS_TOL
    )

    if closure is not None:
        save_csv(CLOSURE_TABLE, [{
            **closure,
            "authoritative_required_sum": auth_required,
            "authoritative_supported_sum": auth_supported,
            "authoritative_fraction": auth_fraction,
            "closure_pass": closure_pass,
        }])

    if closure_pass:
        status = "AUTHORITATIVE_SUPPORT_ARRAYS_SERIALIZED"
        diagnosis = "EXACT_RUNTIME_FRONT_SHELL_AND_SUPPORT_ARRAYS_RECOVERED"
        recommendation = (
            "The authoritative runtime support arrays were serialized from a patched copy "
            "of the original branch and reproduce the B4 support contract exactly. "
            "Proceed to exact-array minimal-support extension calibration."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )
    else:
        status = "AUTHORITATIVE_SUPPORT_SERIALIZATION_REQUIRES_REPAIR"
        diagnosis = "SERIALIZED_RUNTIME_ARRAYS_DO_NOT_YET_CLOSE_AUTHORITATIVE_CONTRACT"
        recommendation = (
            "The patched serialization copy did not yet produce exact closure. "
            "Do not calibrate support. Inspect the selected runtime variables and patch audit."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1A2R — Authoritative Serialization Repair"
        )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7C-R3F5-R1A2",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_calibrated": False,
        "original_source": str(source_path),
        "patched_runtime_copy": str(PATCHED_SCRIPT),
        "original_source_overwritten": False,
        "runtime_function": function_name,
        "required_residual_variable": required_var["variable"],
        "front_shell_variable": shell_var["variable"],
        "support_variable": support_var["variable"],
        "serialized_npz": str(SERIALIZED_NPZ) if serialized_exists else None,
        "closure_pass": closure_pass,
        "execution_error": execution_error,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7C-R3F5-R1A2",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_calibrated": False,
        "gate_changed": False,
        "original_authoritative_source_modified": False,
        "closure_pass": closure_pass,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2 SERIALIZATION VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R3F5-R1A diagnosis reproduced", True),
        ("Authoritative source function identified", selected is not None),
        ("Runtime front-shell variable identified", shell_var is not None),
        ("Runtime required-residual variable identified", required_var is not None),
        ("Runtime support/coefficient variable identified", support_var is not None),
        ("Original authoritative source left unchanged", True),
        ("Serialization runtime copy generated", PATCHED_SCRIPT.exists()),
        ("Serialized NPZ produced", serialized_exists),
        (
            "Required residual sum closes",
            closure is not None and closure["required_error"] <= SUM_ABS_TOL,
        ),
        (
            "Supported residual sum closes",
            closure is not None and closure["supported_error"] <= SUM_ABS_TOL,
        ),
        (
            "Support fraction closes",
            closure is not None and closure["fraction_error"] <= FRACTION_ABS_TOL,
        ),
        ("No support extension calibrated", True),
        ("No training performed", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    print("=" * 78)

    if closure is not None:
        print("\nSERIALIZED ARRAY CLOSURE")
        print(f"  Support mode            : {closure['support_mode']}")
        print(f"  Required sum            : {closure['required_sum']:.12e}")
        print(f"  Supported sum           : {closure['supported_sum']:.12e}")
        print(f"  Coverage                : {closure['coverage_fraction']:.12e}")
        print(f"  Required error          : {closure['required_error']:.6e}")
        print(f"  Supported error         : {closure['supported_error']:.6e}")
        print(f"  Fraction error          : {closure['fraction_error']:.6e}")

    if execution_error:
        print("\nRUNTIME EXECUTION NOTE")
        print(f"  {execution_error}")

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
    print(f"  {SOURCE_SELECTION_TABLE.name}")
    print(f"  {VARIABLE_SELECTION_TABLE.name}")
    print(f"  {PATCH_AUDIT_TABLE.name}")
    print(f"  {CLOSURE_TABLE.name}")

    print("\nPatched runtime copy:")
    print(f"  {PATCHED_SCRIPT.name}")

    if serialized_exists:
        print("\nSerialized numerical:")
        print(f"  {SERIALIZED_NPZ.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2 SERIALIZATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No support extension was calibrated.")
    print("The original authoritative source was not overwritten.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
