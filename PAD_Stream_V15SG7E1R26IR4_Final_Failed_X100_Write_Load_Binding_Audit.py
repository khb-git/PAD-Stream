from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from types import SimpleNamespace

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R4
# Final Failed X100 Write / Load Binding Audit
#
# DIAGNOSTIC-ONLY FEATURE-BINDING REPAIR MILESTONE
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
# R26I-R3 narrowed the remaining failures to two caller-side bindings:
#
#   deployment_workspace
#       -> failed on Path.resolve()
#
#   tD_scale
#       -> failed on Subscript
#
# while also proving the exact X100 feature writes:
#
#   X100[:, :, 0] = xi[None, :]
#   X100[:, :, 1] = normalized_tD[:, None].astype(np.float32)
#
# R26I-R4 repairs ONLY those unresolved provenance bindings by adding support
# for:
#
#   - Path(...).resolve()
#   - object.method() calls on resolved Path values
#   - dictionary literal construction
#   - dictionary / list / tuple subscript expressions
#   - JSON-loaded configuration dictionaries
#   - simple namespace attributes
#   - recursive aliases feeding deployment_workspace / tD_scale
#
# Once those caller values are resolved, R26I-R4 executes the already-audited
# load_deployment_database assignment sequence, including the two in-place
# X100 writes, but DOES NOT call model.predict.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR4"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
HELPER_NAME = "load_deployment_database"

PREV_DIR = ROOT / "output" / "V15_SG7E1R26IR3"
PREV_SUMMARY = PREV_DIR / "PAD_Stream_V15SG7E1R26IR3_Summary.json"

# Outputs
CALLER_TABLE = OUT / "V15SG7E1R26IR4_Caller_Binding_Repair.csv"
CONFIG_TABLE = OUT / "V15SG7E1R26IR4_Config_Subscript_Provenance.csv"
LOAD_TABLE = OUT / "V15SG7E1R26IR4_Helper_Load_Path_and_Key_Audit.csv"
WRITE_TABLE = OUT / "V15SG7E1R26IR4_X100_Write_Replay.csv"
RECON_TABLE = OUT / "V15SG7E1R26IR4_X100_Reconstruction_Validation.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR4_Final_X100_Binding_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR4_Reconstructed_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR4_Final_X100_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR4_Summary.json"


# =============================================================================
# Generic helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


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


def names_in(node):
    return sorted({n.id for n in ast.walk(node) if isinstance(n, ast.Name)})


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def ordinary_assignments(scope, text):
    rows = []
    amap = {}

    for node in ast.walk(scope):
        if not isinstance(node, ast.Assign):
            continue

        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                rec = {
                    "line": node.lineno,
                    "target": tgt.id,
                    "rhs_node": node.value,
                    "rhs": node_src(text, node.value),
                    "rhs_symbols": names_in(node.value),
                }
                rows.append(rec)
                amap[tgt.id] = rec

    return rows, amap


def find_helper_call(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and call_name(node) == HELPER_NAME:
            return node
    return None


# =============================================================================
# Caller-side evaluator
# =============================================================================

class CallerEvaluator:
    """
    Conservative evaluator for source-defined caller configuration.
    """

    def __init__(self, assignments, env, text, config_trace):
        self.assignments = assignments
        self.env = env
        self.text = text
        self.config_trace = config_trace
        self.visiting = set()

    def resolve_symbol(self, symbol):
        if symbol in self.env:
            return self.env[symbol]

        if symbol in self.visiting:
            raise ValueError(f"recursive symbol cycle: {symbol}")

        if symbol not in self.assignments:
            raise KeyError(symbol)

        self.visiting.add(symbol)
        try:
            value = self.eval(self.assignments[symbol]["rhs_node"])
            self.env[symbol] = value
            return value
        finally:
            self.visiting.remove(symbol)

    def eval(self, node):
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return self.resolve_symbol(node.id)

        if isinstance(node, ast.Dict):
            return {
                self.eval(k): self.eval(v)
                for k, v in zip(node.keys, node.values)
            }

        if isinstance(node, ast.List):
            return [self.eval(x) for x in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self.eval(x) for x in node.elts)

        if isinstance(node, ast.UnaryOp):
            v = self.eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return +v
            raise ValueError("unsupported unary operator")

        if isinstance(node, ast.BinOp):
            a = self.eval(node.left)
            b = self.eval(node.right)

            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                if isinstance(a, Path):
                    return a / str(b)
                return a / b
            if isinstance(node.op, ast.Pow):
                return a ** b

            raise ValueError("unsupported binary operator")

        if isinstance(node, ast.Subscript):
            base = self.eval(node.value)
            idx = self._slice(node.slice)
            value = base[idx]

            self.config_trace.append({
                "line": getattr(node, "lineno", ""),
                "expression": node_src(self.text, node),
                "base_type": type(base).__name__,
                "index": repr(idx),
                "resolved": True,
                "value": repr(value),
            })

            return value

        if isinstance(node, ast.Attribute):
            base = self.eval(node.value)

            if node.attr in {"parent", "name", "stem", "suffix"} and isinstance(base, Path):
                return getattr(base, node.attr)

            if isinstance(base, (dict, SimpleNamespace)):
                if isinstance(base, dict) and node.attr in base:
                    return base[node.attr]
                if hasattr(base, node.attr):
                    return getattr(base, node.attr)

            raise ValueError(f"unsupported attribute: {node.attr}")

        if isinstance(node, ast.Call):
            cname = call_name(node)

            # Handle bound methods before recursively evaluating function as attr.
            if isinstance(node.func, ast.Attribute):
                obj = self.eval(node.func.value)
                meth = node.func.attr
                args = [self.eval(a) for a in node.args]
                kwargs = {kw.arg: self.eval(kw.value) for kw in node.keywords if kw.arg}

                if isinstance(obj, Path):
                    if meth == "resolve":
                        return obj.resolve()
                    if meth == "exists":
                        return obj.exists()
                    if meth == "is_file":
                        return obj.is_file()
                    if meth == "is_dir":
                        return obj.is_dir()

                if isinstance(obj, str):
                    if meth == "lower":
                        return obj.lower()
                    if meth == "strip":
                        return obj.strip()

                raise ValueError(f"unsupported bound method: {type(obj).__name__}.{meth}")

            args = [self.eval(a) for a in node.args]
            kwargs = {kw.arg: self.eval(kw.value) for kw in node.keywords if kw.arg}

            if cname == "Path":
                return Path(*args)
            if cname == "float":
                return float(*args)
            if cname == "int":
                return int(*args)
            if cname == "str":
                return str(*args)
            if cname == "dict":
                return dict(*args, **kwargs)
            if cname == "SimpleNamespace":
                return SimpleNamespace(*args, **kwargs)

            # Source-local JSON helpers are common in the PAD-Stream audit chain.
            if cname in {"load_json", "json.load"}:
                if cname == "load_json":
                    path = Path(args[0])
                    return json.loads(path.read_text(encoding="utf-8"))
                raise ValueError("json.load file-handle evaluation intentionally unsupported")

            raise ValueError(f"unsupported caller call: {cname}")

        raise ValueError(f"unsupported caller AST node: {type(node).__name__}")

    def _slice(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Slice):
            lo = self.eval(node.lower) if node.lower else None
            hi = self.eval(node.upper) if node.upper else None
            st = self.eval(node.step) if node.step else None
            return slice(lo, hi, st)
        if isinstance(node, ast.Tuple):
            return tuple(self._slice(x) for x in node.elts)
        return self.eval(node)


# =============================================================================
# Helper evaluator
# =============================================================================

class HelperEvaluator:
    def __init__(self, env, text):
        self.env = env
        self.text = text

    def eval(self, node):
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise KeyError(node.id)
            return self.env[node.id]

        if isinstance(node, ast.List):
            return [self.eval(x) for x in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self.eval(x) for x in node.elts)

        if isinstance(node, ast.Dict):
            return {
                self.eval(k): self.eval(v)
                for k, v in zip(node.keys, node.values)
            }

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
            if isinstance(node.op, ast.Div):
                if isinstance(a, Path):
                    return a / str(b)
                return a / b
            if isinstance(node.op, ast.Pow): return a ** b
            raise ValueError("unsupported binop")

        if isinstance(node, ast.Subscript):
            base = self.eval(node.value)
            idx = self._slice(node.slice)
            return base[idx]

        if isinstance(node, ast.Attribute):
            base = self.eval(node.value)
            if node.attr in {"shape", "dtype", "T", "files"}:
                return getattr(base, node.attr)
            if isinstance(base, Path) and node.attr in {"name", "stem", "suffix", "parent"}:
                return getattr(base, node.attr)
            raise ValueError(f"unsupported helper attribute {node.attr}")

        if isinstance(node, ast.Call):
            cname = call_name(node)

            if isinstance(node.func, ast.Attribute):
                obj = self.eval(node.func.value)
                meth = node.func.attr
                args = [self.eval(a) for a in node.args]
                kwargs = {kw.arg: self.eval(kw.value) for kw in node.keywords if kw.arg}

                if isinstance(obj, np.ndarray):
                    if meth == "reshape": return obj.reshape(*args, **kwargs)
                    if meth == "ravel": return obj.ravel()
                    if meth == "flatten": return obj.flatten()
                    if meth == "astype": return obj.astype(*args, **kwargs)

                if isinstance(obj, Path):
                    if meth == "resolve": return obj.resolve()
                    if meth == "exists": return obj.exists()

                raise ValueError(f"unsupported helper bound method {type(obj).__name__}.{meth}")

            args = [self.eval(a) for a in node.args]
            kwargs = {kw.arg: self.eval(kw.value) for kw in node.keywords if kw.arg}

            allowed = {
                "np.asarray": np.asarray,
                "np.array": np.array,
                "np.zeros": np.zeros,
                "np.zeros_like": np.zeros_like,
                "np.ones": np.ones,
                "np.ones_like": np.ones_like,
                "np.full": np.full,
                "np.full_like": np.full_like,
                "np.column_stack": np.column_stack,
                "np.stack": np.stack,
                "np.concatenate": np.concatenate,
                "np.reshape": np.reshape,
                "np.repeat": np.repeat,
                "np.tile": np.tile,
                "np.clip": np.clip,
                "np.log": np.log,
                "np.log1p": np.log1p,
                "np.sqrt": np.sqrt,
                "np.exp": np.exp,
                "np.float32": np.float32,
                "np.float64": np.float64,
                "float": float,
                "int": int,
                "len": len,
                "Path": Path,
            }

            if cname in allowed:
                return allowed[cname](*args, **kwargs)

            if cname == "np.load":
                path = Path(args[0])
                return np.load(path, allow_pickle=kwargs.get("allow_pickle", False))

            raise ValueError(f"unsupported helper call {cname}")

        raise ValueError(f"unsupported helper AST node {type(node).__name__}")

    def _slice(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Slice):
            lo = self.eval(node.lower) if node.lower else None
            hi = self.eval(node.upper) if node.upper else None
            st = self.eval(node.step) if node.step else None
            return slice(lo, hi, st)
        if isinstance(node, ast.Tuple):
            return tuple(self._slice(x) for x in node.elts)
        return self.eval(node)


# =============================================================================
# Main
# =============================================================================

def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R4")
    print("Final Failed X100 Write / Load Binding Audit")
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

    prev = load_json(PREV_SUMMARY)
    if prev.get("status") != "SG7B10_DEPLOYMENT_X100_FULL_RECONSTRUCTION_STILL_BLOCKED":
        raise RuntimeError("R26I-R4 requires blocked R26I-R3 reconstruction status.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = safe_text(SOURCE)
    tree = ast.parse(text)

    helper = find_function(tree, HELPER_NAME)
    if helper is None:
        raise RuntimeError(f"Missing helper {HELPER_NAME}")

    helper_call = find_helper_call(tree)
    if helper_call is None:
        raise RuntimeError("Missing load_deployment_database call.")

    # -------------------------------------------------------------------------
    # 1. Repair caller-side argument binding
    # -------------------------------------------------------------------------

    _, root_amap = ordinary_assignments(tree, text)

    config_trace = []
    caller_env = {
        "ROOT": ROOT,
        "__file__": str(SOURCE),
        "np": np,
        "Path": Path,
        "SimpleNamespace": SimpleNamespace,
    }

    evaluator = CallerEvaluator(root_amap, caller_env, text, config_trace)

    params = [a.arg for a in helper.args.args]
    caller_rows = []
    bound_args = {}

    for i, param in enumerate(params):
        if i >= len(helper_call.args):
            caller_rows.append({
                "parameter": param,
                "expression": "",
                "resolved": False,
                "value": "",
                "value_type": "",
                "failure": "missing positional argument",
            })
            continue

        arg_node = helper_call.args[i]
        expr = node_src(text, arg_node)

        try:
            val = evaluator.eval(arg_node)
            bound_args[param] = val
            caller_rows.append({
                "parameter": param,
                "expression": expr,
                "resolved": True,
                "value": str(val),
                "value_type": type(val).__name__,
                "failure": "",
            })
        except Exception as exc:
            caller_rows.append({
                "parameter": param,
                "expression": expr,
                "resolved": False,
                "value": "",
                "value_type": "",
                "failure": f"{type(exc).__name__}: {exc}",
            })

    save_csv(CALLER_TABLE, caller_rows)
    save_csv(CONFIG_TABLE, config_trace)

    args_resolved = all(r["resolved"] for r in caller_rows)

    # -------------------------------------------------------------------------
    # 2. Replay helper statements in exact source order
    # -------------------------------------------------------------------------

    env = {
        "np": np,
        "Path": Path,
    }
    env.update(bound_args)

    helper_eval = HelperEvaluator(env, text)

    helper_rows = []
    load_rows = []
    write_rows = []

    # We execute only top-level assignment statements. This is sufficient for
    # the already-observed helper construction path and avoids running unrelated
    # control flow.
    for stmt in sorted(helper.body, key=lambda n: getattr(n, "lineno", 10**9)):
        if not isinstance(stmt, ast.Assign):
            continue

        rhs = stmt.value

        # Ordinary name targets
        for tgt in [t for t in stmt.targets if isinstance(t, ast.Name)]:
            try:
                val = helper_eval.eval(rhs)
                env[tgt.id] = val

                helper_rows.append({
                    "line": stmt.lineno,
                    "operation": "NAME_ASSIGN",
                    "target": tgt.id,
                    "rhs": node_src(text, rhs),
                    "resolved": True,
                    "shape": str(val.shape) if isinstance(val, np.ndarray) else "",
                    "dtype": str(val.dtype) if isinstance(val, np.ndarray) else type(val).__name__,
                    "failure": "",
                })

                if isinstance(rhs, ast.Call) and call_name(rhs) == "np.load":
                    path_val = helper_eval.eval(rhs.args[0])
                    load_rows.append({
                        "line": stmt.lineno,
                        "handle": tgt.id,
                        "path_expression": node_src(text, rhs.args[0]),
                        "resolved_path": str(path_val),
                        "exists": Path(path_val).exists(),
                        "keys": ";".join(val.files) if hasattr(val, "files") else "",
                    })

            except Exception as exc:
                helper_rows.append({
                    "line": stmt.lineno,
                    "operation": "NAME_ASSIGN",
                    "target": tgt.id,
                    "rhs": node_src(text, rhs),
                    "resolved": False,
                    "shape": "",
                    "dtype": "",
                    "failure": f"{type(exc).__name__}: {exc}",
                })

        # In-place X100 targets
        for tgt in [t for t in stmt.targets if isinstance(t, ast.Subscript)]:
            base = tgt.value.id if isinstance(tgt.value, ast.Name) else ""
            if base != "X100":
                continue

            try:
                if "X100" not in env:
                    raise KeyError("X100 allocation not resolved")

                idx = helper_eval._slice(tgt.slice)
                val = helper_eval.eval(rhs)
                env["X100"][idx] = val

                write_rows.append({
                    "line": stmt.lineno,
                    "target": node_src(text, tgt),
                    "rhs": node_src(text, rhs),
                    "resolved": True,
                    "value_shape": str(np.asarray(val).shape),
                    "value_dtype": str(np.asarray(val).dtype),
                    "failure": "",
                })

            except Exception as exc:
                write_rows.append({
                    "line": stmt.lineno,
                    "target": node_src(text, tgt),
                    "rhs": node_src(text, rhs),
                    "resolved": False,
                    "value_shape": "",
                    "value_dtype": "",
                    "failure": f"{type(exc).__name__}: {exc}",
                })

    # Audit explicit NPZ key reads from resolved handles.
    for node in ast.walk(helper):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name):
            continue

        handle = node.value.id
        if handle not in env:
            continue

        obj = env[handle]
        if not hasattr(obj, "files"):
            continue

        key = None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value

        if key is not None:
            load_rows.append({
                "line": getattr(node, "lineno", ""),
                "handle": handle,
                "path_expression": "",
                "resolved_path": "",
                "exists": key in obj.files,
                "keys": key,
                "key_shape": str(np.asarray(obj[key]).shape) if key in obj.files else "",
                "key_dtype": str(np.asarray(obj[key]).dtype) if key in obj.files else "",
            })

    save_csv(LOAD_TABLE, load_rows)
    save_csv(WRITE_TABLE, write_rows)

    # -------------------------------------------------------------------------
    # 3. Final reconstruction validation
    # -------------------------------------------------------------------------

    x100 = env.get("X100")

    is_array = isinstance(x100, np.ndarray)
    numeric = is_array and x100.dtype.kind in {"f", "i", "u", "b", "c"}
    finite = bool(np.all(np.isfinite(x100))) if numeric else False
    feature_dim_ok = is_array and x100.ndim == 3 and x100.shape[-1] == 2
    all_writes_resolved = len(write_rows) == 2 and all(r["resolved"] for r in write_rows)

    # Feature channels must actually be populated; this is diagnostic only,
    # not a physics gate.
    channel0_nontrivial = False
    channel1_nontrivial = False

    if is_array and feature_dim_ok:
        channel0 = x100[..., 0]
        channel1 = x100[..., 1]
        channel0_nontrivial = bool(np.any(channel0 != 0.0))
        channel1_nontrivial = bool(np.any(channel1 != 0.0))

    ready = (
        args_resolved
        and numeric
        and finite
        and feature_dim_ok
        and all_writes_resolved
        and channel0_nontrivial
        and channel1_nontrivial
    )

    recon_row = {
        "caller_args_resolved": args_resolved,
        "X100_present": is_array,
        "X100_shape": str(x100.shape) if is_array else "",
        "X100_dtype": str(x100.dtype) if is_array else "",
        "numeric": numeric,
        "finite": finite,
        "feature_dim_2": feature_dim_ok,
        "write_count": len(write_rows),
        "all_writes_resolved": all_writes_resolved,
        "channel0_nontrivial": channel0_nontrivial,
        "channel1_nontrivial": channel1_nontrivial,
        "ready": ready,
    }
    save_csv(RECON_TABLE, [recon_row])

    if ready:
        status = "SG7B10_DEPLOYMENT_X100_FINAL_BINDING_REPAIRED"
        diagnosis = (
            "PATH_RESOLVE_CONFIG_SUBSCRIPT_LOAD_BINDINGS_AND_BOTH_X100_FEATURE_WRITES_CLOSE"
        )
        recommendation = (
            "The remaining X100 binding failures are repaired. deployment_workspace and tD_scale "
            "resolve from source provenance, helper load paths/keys resolve, and both SG7B10 "
            "feature channels are populated into a finite float tensor with trailing dimension 2. "
            "Persist this reconstructed X100 as the sole legal input to the repaired 100-day "
            "runtime control."
        )
        next_milestone = (
            "V15-SG7E1R26I-R5 — Repaired Authoritative SG7B10 100-Day Runtime Control"
        )

        np.savez_compressed(
            NUMERICAL_FILE,
            X100=np.asarray(x100),
        )
    else:
        status = "SG7B10_DEPLOYMENT_X100_FINAL_BINDING_STILL_BLOCKED"
        diagnosis = (
            "ONE_OR_MORE_SOURCE_DEFINED_CALLER_LOAD_OR_FEATURE_WRITE_COMPONENTS_REMAIN_UNRESOLVED"
        )
        recommendation = (
            "Do not call model.predict. Inspect only the failed caller, load-path, or X100-write "
            "rows emitted by R26I-R4. Do not broaden evaluator authority or fabricate any feature."
        )
        next_milestone = (
            "V15-SG7E1R26I-R5 — Residual X100 Binding Failure Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        **recon_row,
        "numerical_artifact": str(NUMERICAL_FILE) if ready else "",
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R4",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "helper": HELPER_NAME,
        "caller_binding": {
            "resolved": args_resolved,
            "records": caller_rows,
        },
        "X100": {
            "resolved": ready,
            "shape": list(x100.shape) if is_array else None,
            "dtype": str(x100.dtype) if is_array else None,
            "feature_writes": write_rows,
            "artifact": str(NUMERICAL_FILE) if ready else None,
            "key": "X100" if ready else None,
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
        "milestone": "V15-SG7E1R26I-R4",
        "status": status,
        "diagnosis": diagnosis,
        "X100_ready": ready,
        "X100_shape": list(x100.shape) if is_array else None,
        "X100_dtype": str(x100.dtype) if is_array else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("CALLER BINDING REPAIR")
    for r in caller_rows:
        print(
            f"  {r['parameter']:<20s} | resolved={r['resolved']} | "
            f"{r['expression']} -> {r['value'] if r['resolved'] else r['failure']}"
        )

    print("\nHELPER LOADS")
    if load_rows:
        for r in load_rows[:20]:
            print(
                f"  handle={r.get('handle','')} | exists={r.get('exists','')} | "
                f"path={r.get('resolved_path','')} | key={r.get('keys','')}"
            )
    else:
        print("  NONE RESOLVED")

    print("\nX100 WRITES")
    for r in write_rows:
        print(
            f"  line={r['line']} | resolved={r['resolved']} | "
            f"{r['target']} <- {r['rhs']}"
            + ("" if r["resolved"] else f" | {r['failure']}")
        )

    print("\nFINAL X100")
    if is_array:
        print(f"  Shape                   : {x100.shape}")
        print(f"  Dtype                   : {x100.dtype}")
        print(f"  Numeric                 : {numeric}")
        print(f"  Finite                  : {finite}")
        print(f"  Feature dim = 2         : {feature_dim_ok}")
        print(f"  Channel 0 populated     : {channel0_nontrivial}")
        print(f"  Channel 1 populated     : {channel1_nontrivial}")
        print(f"  All writes resolved     : {all_writes_resolved}")
    else:
        print("  NOT RECONSTRUCTED")

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
        CALLER_TABLE,
        CONFIG_TABLE,
        LOAD_TABLE,
        WRITE_TABLE,
        RECON_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    if ready:
        print("\nNumerical:")
        print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R4 FINAL FAILED X100 WRITE / LOAD BINDING AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No fabricated feature was used.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
