from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R2
# Exact X100 Component Array Binding / Reconstruction
#
# DIAGNOSTIC-ONLY FEATURE-RECONSTRUCTION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R26I-R1 resolved:
#
#   deployment = load_deployment_database(deployment_workspace, tD_scale)
#
# and:
#
#   load_deployment_database(...) returns {"X100": X100, ...}
#
# R26I-R2 now traces the LOCAL X100 VARIABLE itself inside
# load_deployment_database:
#
#   persisted file/key/scalar inputs
#       -> intermediate assignments
#       -> X100 assignment
#       -> exact numeric reconstruction
#
# It does NOT search for another evaluator and it does NOT call model.predict.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR2B"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
HELPER_NAME = "load_deployment_database"

R26IR1_DIR = ROOT / "output" / "V15_SG7E1R26IR1"
R26IR1_SUMMARY = R26IR1_DIR / "PAD_Stream_V15SG7E1R26IR1_Summary.json"

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

# Outputs
HELPER_TABLE = OUT / "V15SG7E1R26IR2B_Helper_X100_Assignment.csv"
DEPENDENCY_TABLE = OUT / "V15SG7E1R26IR2B_X100_Assignment_Dependency_Trace.csv"
LOAD_TABLE = OUT / "V15SG7E1R26IR2B_Persisted_Load_Key_Trace.csv"
ARG_TABLE = OUT / "V15SG7E1R26IR2B_Helper_Argument_Binding.csv"
RECON_TABLE = OUT / "V15SG7E1R26IR2B_X100_Reconstruction_Validation.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR2B_X100_Reconstruction_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR2B_Reconstructed_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR2B_Exact_X100_Component_Reconstruction_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR2B_Summary.json"


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def safe_text(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def node_src(text, node):
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""


def names_in(node):
    return sorted({n.id for n in ast.walk(node) if isinstance(n, ast.Name)})


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def ordinary_assignments(func_node, text):
    rows = []
    amap = {}

    for node in ast.walk(func_node):
        if not isinstance(node, ast.Assign):
            continue

        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                rec = {
                    "line": node.lineno,
                    "target": tgt.id,
                    "rhs": node_src(text, node.value),
                    "rhs_node": node.value,
                    "rhs_symbols": names_in(node.value),
                }
                rows.append(rec)
                amap[tgt.id] = rec

    return rows, amap


def recursive_trace(seed, amap):
    rows = []
    seen = set()
    frontier = [seed]

    while frontier:
        sym = frontier.pop()
        if sym in seen:
            continue
        seen.add(sym)

        if sym not in amap:
            continue

        rec = amap[sym]
        rows.append({
            "symbol": sym,
            "assignment_line": rec["line"],
            "rhs": rec["rhs"],
            "rhs_symbols": ";".join(rec["rhs_symbols"]),
        })

        for dep in rec["rhs_symbols"]:
            if dep not in seen:
                frontier.append(dep)

    return rows


def call_name(node):
    if not isinstance(node, ast.Call):
        return ""
    cur = node.func
    parts = []
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def find_main_helper_call(tree, text):
    """
    Resolve actual argument expressions passed into:
        load_deployment_database(deployment_workspace, tD_scale)
    """
    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if call_name(node) != HELPER_NAME:
            continue

        for i, arg in enumerate(node.args):
            rows.append({
                "arg_index": i,
                "expression": node_src(text, arg),
                "symbols": ";".join(names_in(arg)),
            })

    return rows


def project_npz_files():
    output_root = ROOT / "output"
    if not output_root.exists():
        return []
    return sorted(output_root.rglob("*.npz"))


def source_literal_paths(func_node, text):
    """
    Extract .npz filenames or paths literally referenced in the helper.
    """
    refs = set()

    for node in ast.walk(func_node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            if ".npz" in s.lower():
                refs.add(s)

    return sorted(refs)


def candidate_artifacts_from_literals(literals):
    paths = []

    for lit in literals:
        name = Path(lit).name.lower()

        for p in project_npz_files():
            if p.name.lower() == name:
                paths.append(p.resolve())

    return sorted(set(paths))


def find_npz_key_accesses(func_node, text):
    """
    Record:
      np.load(...)
      handle["key"]
    and ordinary assignment targets.
    """
    load_handles = {}
    rows = []

    # identify: db = np.load(...)
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Assign):
            continue

        if not isinstance(node.value, ast.Call):
            continue

        if call_name(node.value) != "np.load":
            continue

        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                load_handles[tgt.id] = node.value

                rows.append({
                    "kind": "NP_LOAD",
                    "line": node.lineno,
                    "target": tgt.id,
                    "key": "",
                    "expression": node_src(text, node.value),
                })

    # identify: x = db["key"] / db["key"][...]
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Assign):
            continue

        for sub in ast.walk(node.value):
            if not isinstance(sub, ast.Subscript):
                continue

            if not isinstance(sub.value, ast.Name):
                continue

            handle = sub.value.id
            if handle not in load_handles:
                continue

            key = ""
            if isinstance(sub.slice, ast.Constant) and isinstance(sub.slice.value, str):
                key = sub.slice.value

            targets = [
                tgt.id for tgt in node.targets
                if isinstance(tgt, ast.Name)
            ]

            rows.append({
                "kind": "NPZ_KEY_ACCESS",
                "line": node.lineno,
                "target": ";".join(targets),
                "key": key,
                "expression": node_src(text, node.value),
                "handle": handle,
            })

    return rows, load_handles


class EvalContext:
    """
    Restricted evaluator for the exact helper assignment chain.
    Supports array/scalar operations only.
    """

    def __init__(self, env):
        self.env = env

    def eval(self, node):
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise KeyError(node.id)
            return self.env[node.id]

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.UnaryOp):
            v = self.eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return +v
            raise ValueError("unsupported unary")

        if isinstance(node, ast.BinOp):
            a = self.eval(node.left)
            b = self.eval(node.right)

            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div): return a / b
            if isinstance(node.op, ast.Pow): return a ** b

            raise ValueError("unsupported binop")

        if isinstance(node, ast.List):
            return [self.eval(x) for x in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self.eval(x) for x in node.elts)

        if isinstance(node, ast.Subscript):
            base = self.eval(node.value)

            if isinstance(node.slice, ast.Constant):
                idx = node.slice.value
            elif isinstance(node.slice, ast.Tuple):
                idx = tuple(self._slice(x) for x in node.slice.elts)
            else:
                idx = self._slice(node.slice)

            return base[idx]

        if isinstance(node, ast.Attribute):
            base = self.eval(node.value)
            if node.attr in {"shape", "dtype", "T"}:
                return getattr(base, node.attr)
            raise ValueError(f"unsupported attr {node.attr}")

        if isinstance(node, ast.Call):
            name = call_name(node)
            args = [self.eval(a) for a in node.args]
            kwargs = {
                kw.arg: self.eval(kw.value)
                for kw in node.keywords if kw.arg is not None
            }

            allowed = {
                "np.asarray": np.asarray,
                "np.array": np.array,
                "np.column_stack": np.column_stack,
                "np.stack": np.stack,
                "np.concatenate": np.concatenate,
                "np.reshape": np.reshape,
                "np.ravel": np.ravel,
                "np.full": np.full,
                "np.full_like": np.full_like,
                "np.zeros": np.zeros,
                "np.zeros_like": np.zeros_like,
                "np.ones": np.ones,
                "np.ones_like": np.ones_like,
                "np.repeat": np.repeat,
                "np.tile": np.tile,
                "np.clip": np.clip,
                "np.log": np.log,
                "np.log1p": np.log1p,
                "np.sqrt": np.sqrt,
                "np.exp": np.exp,
                "np.float32": np.float32,
                "np.float64": np.float64,
            }

            if name in allowed:
                return allowed[name](*args, **kwargs)

            if isinstance(node.func, ast.Attribute):
                obj = self.eval(node.func.value)
                method = node.func.attr

                if method == "reshape":
                    return obj.reshape(*args, **kwargs)
                if method == "ravel":
                    return obj.ravel()
                if method == "flatten":
                    return obj.flatten()
                if method == "astype":
                    return obj.astype(*args, **kwargs)

            raise ValueError(f"unsupported call {name}")

        raise ValueError(f"unsupported AST node {type(node).__name__}")

    def _slice(self, node):
        if isinstance(node, ast.Slice):
            lo = self.eval(node.lower) if node.lower else None
            hi = self.eval(node.upper) if node.upper else None
            st = self.eval(node.step) if node.step else None
            return slice(lo, hi, st)
        return self.eval(node)


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R2")
    print("Exact X100 Component Array Binding / Reconstruction")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
SG7B10 REMAINS THE AUTHORITATIVE EVALUATOR SOURCE.
""")

    prev = load_json(R26IR1_SUMMARY)

    if prev.get("status") != "SG7B10_DEPLOYMENT_X100_CONSTRUCTOR_EXPRESSION_RESOLVED":
        raise RuntimeError("R26I-R2 requires resolved R26I-R1 constructor expression.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = safe_text(SOURCE)
    tree = ast.parse(text)
    helper = find_function(tree, HELPER_NAME)

    if helper is None:
        raise RuntimeError(f"Missing helper {HELPER_NAME}")

    assign_rows, amap = ordinary_assignments(helper, text)

    x100_assignments = [
        r for r in assign_rows
        if r["target"] == "X100"
    ]

    save_csv(HELPER_TABLE, [{
        "source": str(SOURCE),
        "helper": HELPER_NAME,
        "X100_assignment_count": len(x100_assignments),
        "line": r["line"],
        "rhs": r["rhs"],
        "rhs_symbols": ";".join(r["rhs_symbols"]),
    } for r in x100_assignments])

    dependency_rows = recursive_trace("X100", amap)
    save_csv(DEPENDENCY_TABLE, dependency_rows)

    # -------------------------------------------------------------------------
    # Load/key trace within helper
    # -------------------------------------------------------------------------

    load_rows, load_handles = find_npz_key_accesses(helper, text)
    save_csv(LOAD_TABLE, load_rows)

    # -------------------------------------------------------------------------
    # Bind helper call arguments from main-level ordinary assignments.
    # -------------------------------------------------------------------------

    main_assign_rows, main_amap = ordinary_assignments(tree, text)
    call_args = find_main_helper_call(tree, text)

    helper_params = [a.arg for a in helper.args.args]
    arg_rows = []
    arg_env = {}

    # Resolve simple scalar/path main assignments conservatively.
    scalar_env = {
        "np": np,
        "ROOT": ROOT,
    }

    # Iteratively evaluate only constants/simple Path arithmetic is not needed
    # for X100 numeric construction except tD_scale scalar.
    changed = True
    unresolved_main = dict(main_amap)

    while changed:
        changed = False

        for sym in list(unresolved_main):
            rec = unresolved_main[sym]
            node = rec["rhs_node"]

            try:
                if isinstance(node, ast.Constant):
                    val = node.value
                elif isinstance(node, ast.UnaryOp) and isinstance(node.operand, ast.Constant):
                    base = node.operand.value
                    val = -base if isinstance(node.op, ast.USub) else base
                else:
                    continue
            except Exception:
                continue

            scalar_env[sym] = val
            del unresolved_main[sym]
            changed = True

    for i, param in enumerate(helper_params):
        expr = call_args[i]["expression"] if i < len(call_args) else ""
        syms = call_args[i]["symbols"].split(";") if i < len(call_args) else []

        value = None
        resolved = False

        if len(syms) == 1 and syms[0] in scalar_env:
            value = scalar_env[syms[0]]
            resolved = True
        elif not syms:
            try:
                node = ast.parse(expr, mode="eval").body
                if isinstance(node, ast.Constant):
                    value = node.value
                    resolved = True
            except Exception:
                pass

        arg_rows.append({
            "parameter": param,
            "call_expression": expr,
            "symbols": ";".join(syms),
            "resolved_scalar": resolved,
            "value": repr(value) if resolved else "",
        })

        if resolved:
            arg_env[param] = value

    save_csv(ARG_TABLE, arg_rows)

    # -------------------------------------------------------------------------
    # Resolve np.load artifact(s) from helper source/path semantics.
    # -------------------------------------------------------------------------

    literal_npz = source_literal_paths(helper, text)
    literal_artifacts = candidate_artifacts_from_literals(literal_npz)

    # Also allow exact filenames embedded in load expressions.
    load_expr_text = "\n".join(r["expression"] for r in load_rows)
    for p in project_npz_files():
        if p.name in load_expr_text and p.resolve() not in literal_artifacts:
            literal_artifacts.append(p.resolve())

    # Build NPZ handle environments where exact artifact identity is unique.
    env = {"np": np}
    env.update(arg_env)

    binding_rows = []

    # For each np.load handle, identify candidate artifact by filename mention.
    for handle, load_call in load_handles.items():
        expr = node_src(text, load_call)
        matches = [
            p for p in literal_artifacts
            if p.name in expr
        ]

        if len(matches) == 1:
            db = np.load(matches[0], allow_pickle=True)
            env[handle] = {k: np.array(db[k], copy=True) for k in db.files}
            db.close()

            binding_rows.append({
                "symbol": handle,
                "binding_kind": "NPZ_HANDLE",
                "artifact": str(matches[0]),
                "key": "",
                "resolved": True,
            })
        else:
            binding_rows.append({
                "symbol": handle,
                "binding_kind": "NPZ_HANDLE",
                "artifact": ";".join(str(p) for p in matches),
                "key": "",
                "resolved": False,
            })

    # Evaluate helper ordinary assignments iteratively, with special support
    # for dict-backed np.load handles.
    unresolved = dict(amap)
    reconstruction_log = []
    progress = True

    while progress:
        progress = False

        for sym in list(unresolved):
            rec = unresolved[sym]
            rhs_node = rec["rhs_node"]

            try:
                val = EvalContext(env).eval(rhs_node)
            except Exception:
                # Special case: handle["key"] where handle is dict-backed.
                try:
                    if isinstance(rhs_node, ast.Subscript) and isinstance(rhs_node.value, ast.Name):
                        h = rhs_node.value.id
                        if h in env and isinstance(env[h], dict):
                            if isinstance(rhs_node.slice, ast.Constant):
                                key = rhs_node.slice.value
                                val = env[h][key]
                            else:
                                continue
                        else:
                            continue
                    else:
                        continue
                except Exception:
                    continue

            if isinstance(val, np.ndarray):
                if val.dtype.kind not in {"f", "i", "u", "b", "c"}:
                    del unresolved[sym]
                    continue

            env[sym] = val
            del unresolved[sym]
            progress = True

            reconstruction_log.append({
                "symbol": sym,
                "line": rec["line"],
                "rhs": rec["rhs"],
                "resolved": True,
                "shape": str(np.asarray(val).shape) if isinstance(val, np.ndarray) else "",
                "dtype": str(np.asarray(val).dtype) if isinstance(val, np.ndarray) else type(val).__name__,
            })

    # Add explicit load/key binding rows
    for row in load_rows:
        if row["kind"] != "NPZ_KEY_ACCESS":
            continue

        target_syms = [s for s in row["target"].split(";") if s]
        for sym in target_syms:
            resolved = sym in env
            arr = env.get(sym)

            binding_rows.append({
                "symbol": sym,
                "binding_kind": "NPZ_KEY_ACCESS",
                "artifact": "",
                "key": row["key"],
                "resolved": resolved,
                "shape": str(arr.shape) if resolved and isinstance(arr, np.ndarray) else "",
                "dtype": str(arr.dtype) if resolved and isinstance(arr, np.ndarray) else "",
            })

    save_csv(LOAD_TABLE, load_rows + binding_rows)

    # -------------------------------------------------------------------------
    # Final X100 reconstruction validation
    # -------------------------------------------------------------------------

    recon_rows = []

    x100 = env.get("X100")
    resolved = isinstance(x100, np.ndarray)

    if resolved:
        numeric = x100.dtype.kind in {"f", "i", "u", "b", "c"}
        finite = bool(np.all(np.isfinite(x100))) if numeric else False
        shape_ok = (
            x100.ndim == 2
            and x100.shape[1] == 2
        )

        resolved = numeric and finite and shape_ok

        recon_rows.append({
            "symbol": "X100",
            "resolved": resolved,
            "shape": str(x100.shape),
            "dtype": str(x100.dtype),
            "numeric": numeric,
            "finite": finite,
            "model_input_shape_compatible": shape_ok,
        })
    else:
        recon_rows.append({
            "symbol": "X100",
            "resolved": False,
            "shape": "",
            "dtype": "",
            "numeric": False,
            "finite": False,
            "model_input_shape_compatible": False,
        })

    save_csv(RECON_TABLE, reconstruction_log + recon_rows)

    if resolved:
        status = "SG7B10_DEPLOYMENT_X100_NUMERIC_RECONSTRUCTION_READY"
        diagnosis = (
            "EXACT_HELPER_ASSIGNMENT_CHAIN_RECONSTRUCTS_FINITE_NUMERIC_TWO_COLUMN_X100"
        )
        recommendation = (
            "The authoritative SG7B10 deployment X100 tensor is now reconstructed from the exact "
            "load_deployment_database assignment chain and persisted inputs. Persist this X100 "
            "artifact as the only legal 100-day model input and proceed to the repaired SG7B10 "
            "100-day runtime control. Do not use heuristic X100 discovery."
        )
        next_milestone = (
            "V15-SG7E1R26I-R3 — Repaired Authoritative SG7B10 100-Day Runtime Control"
        )

        np.savez_compressed(
            NUMERICAL_FILE,
            X100=np.asarray(x100),
        )
    else:
        status = "SG7B10_DEPLOYMENT_X100_NUMERIC_RECONSTRUCTION_BLOCKED"
        diagnosis = (
            "ONE_OR_MORE_HELPER_LOAD_SCALAR_OR_ARRAY_BINDINGS_PREVENT_EXACT_X100_RECONSTRUCTION"
        )
        recommendation = (
            "Do not call model.predict. Audit only the unresolved assignments inside "
            "load_deployment_database shown in the R26I-R2 dependency/reconstruction tables. "
            "Do not broaden evaluator authority and do not fabricate feature components."
        )
        next_milestone = (
            "V15-SG7E1R26I-R3 — Remaining X100 Helper Input Binding Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "X100_assignment_count": len(x100_assignments),
        "dependency_record_count": len(dependency_rows),
        "np_load_record_count": sum(1 for r in load_rows if r["kind"] == "NP_LOAD"),
        "npz_key_access_count": sum(1 for r in load_rows if r["kind"] == "NPZ_KEY_ACCESS"),
        "helper_argument_count": len(helper_params),
        "resolved_helper_arguments": sum(1 for r in arg_rows if r["resolved_scalar"]),
        "resolved_intermediate_assignments": len(reconstruction_log),
        "X100_resolved": resolved,
        "X100_shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "X100_dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R2",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "helper": HELPER_NAME,
        "X100_assignment": {
            "count": len(x100_assignments),
            "expressions": [r["rhs"] for r in x100_assignments],
        },
        "reconstruction": {
            "resolved": resolved,
            "shape": list(x100.shape) if isinstance(x100, np.ndarray) else None,
            "dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else None,
            "artifact": str(NUMERICAL_FILE) if resolved else None,
            "key": "X100" if resolved else None,
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "model_predict_executed": False,
            "fabricated_feature_used": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R2",
        "status": status,
        "diagnosis": diagnosis,
        "X100_resolved": resolved,
        "X100_shape": list(x100.shape) if isinstance(x100, np.ndarray) else None,
        "X100_dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("HELPER X100 ASSIGNMENT")
    print(f"  Assignment count        : {len(x100_assignments)}")
    for r in x100_assignments:
        print(f"  line={r['line']} | X100 <- {r['rhs']}")

    print("\nDEPENDENCY TRACE")
    print(f"  Records                 : {len(dependency_rows)}")

    print("\nHELPER LOAD CONTRACT")
    print(f"  Literal NPZ refs        : {len(literal_npz)}")
    print(f"  Matched artifacts       : {len(literal_artifacts)}")
    print(f"  np.load handles         : {len(load_handles)}")

    print("\nHELPER ARGUMENTS")
    for r in arg_rows:
        print(
            f"  {r['parameter']:<24s} | "
            f"resolved={r['resolved_scalar']} | "
            f"{r['call_expression']}"
        )

    print("\nRECONSTRUCTION")
    print(f"  Intermediates resolved  : {len(reconstruction_log)}")

    if isinstance(x100, np.ndarray):
        print(f"  X100 shape              : {x100.shape}")
        print(f"  X100 dtype              : {x100.dtype}")
        print(f"  X100 finite             : {bool(np.all(np.isfinite(x100))) if x100.dtype.kind in {'f','i','u','b','c'} else False}")
        print(f"  X100 model-shape ready  : {resolved}")
    else:
        print("  X100                    : NOT RECONSTRUCTED")

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
    for p in (
        HELPER_TABLE,
        DEPENDENCY_TABLE,
        LOAD_TABLE,
        ARG_TABLE,
        RECON_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    if resolved:
        print("\nNumerical:")
        print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R2 EXACT X100 COMPONENT ARRAY BINDING / RECONSTRUCTION: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No fabricated feature was used.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
