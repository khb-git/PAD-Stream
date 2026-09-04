from __future__ import annotations

from pathlib import Path
import ast
import argparse
import csv
import importlib.util
import json
import sys
from types import ModuleType, SimpleNamespace

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R6
# Final Runtime Constructor Binding Audit
#
# DIAGNOSTIC-ONLY CALLER / BASE-DATASET BINDING REPAIR
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
# R26I-R5 reduced the remaining failures to two precise evaluator limitations:
#
#   1. argparse default:
#        default=str(DEFAULT_DEPLOYMENT_WORKSPACE)
#      was preserved as the literal text "str(DEFAULT_DEPLOYMENT_WORKSPACE)"
#      instead of being evaluated from the imported SG7B10 module globals.
#
#   2. tD_scale:
#      its source chain reaches the authoritative base module's
#      module.load_dataset(...) method, which R26I-R5 did not permit.
#
# R26I-R6 repairs ONLY those two runtime-constructor bindings.
#
# Strategy
# --------
#   - Import SG7B10 without executing main().
#   - Evaluate argparse default AST expressions against the imported SG7B10
#     module namespace, so DEFAULT_DEPLOYMENT_WORKSPACE is source-authentic.
#   - Resolve load_base_module() from SG7B10.
#   - Trace and evaluate the exact main()-local tD_scale assignment while
#     allowing read-only calls into the already-authoritative base module,
#     including base.load_dataset(...).
#   - Call only load_deployment_database(workspace, tD_scale).
#   - Validate deployment["X100"].
#   - DO NOT call model.predict.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR6"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"

PREV = (
    ROOT / "output" / "V15_SG7E1R26IR5"
    / "PAD_Stream_V15SG7E1R26IR5_Summary.json"
)

ARGPARSE_TABLE = OUT / "V15SG7E1R26IR6_Argparse_Runtime_Default_Binding.csv"
BASE_TABLE = OUT / "V15SG7E1R26IR6_Base_Module_Runtime_Binding.csv"
DATASET_TABLE = OUT / "V15SG7E1R26IR6_Base_Dataset_Call_Trace.csv"
WORKSPACE_TABLE = OUT / "V15SG7E1R26IR6_Deployment_Workspace_Runtime_Binding.csv"
TDSCALE_TABLE = OUT / "V15SG7E1R26IR6_tD_Scale_Runtime_Binding.csv"
HELPER_TABLE = OUT / "V15SG7E1R26IR6_Deployment_Database_Runtime_Validation.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR6_Final_Runtime_Constructor_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR6_Reconstructed_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR6_Final_Runtime_Constructor_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR6_Summary.json"


# =============================================================================
# Basic helpers
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
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


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


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def ordinary_assignments(scope, text):
    amap = {}
    for node in ast.walk(scope):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                amap[target.id] = {
                    "line": node.lineno,
                    "rhs_node": node.value,
                    "rhs": node_src(text, node.value),
                }
    return amap


def import_sg7b10():
    name = "_pad_stream_sg7b10_r26ir6"
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create SG7B10 import specification.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# =============================================================================
# Source-authentic expression evaluator
# =============================================================================

class RuntimeExpressionEvaluator:
    """
    Restricted evaluator for SG7B10 configuration / data-loading expressions.

    Allowed effects are read-only configuration and dataset loading from the
    already-authoritative imported SG7B10/base modules. No training calls,
    model.fit, optimizer operations, or model.predict are allowed.
    """

    FORBIDDEN_METHODS = {
        "fit", "train_on_batch", "compile", "predict", "predict_on_batch",
        "save", "save_weights", "set_weights",
    }

    def __init__(self, assignments, env, call_trace):
        self.assignments = assignments
        self.env = env
        self.call_trace = call_trace
        self.visiting = set()

    def resolve(self, symbol):
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
            return self.resolve(node.id)

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
            value = self.eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return +value
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
            if isinstance(node.slice, ast.Constant):
                idx = node.slice.value
            elif isinstance(node.slice, ast.Slice):
                lo = self.eval(node.slice.lower) if node.slice.lower else None
                hi = self.eval(node.slice.upper) if node.slice.upper else None
                st = self.eval(node.slice.step) if node.slice.step else None
                idx = slice(lo, hi, st)
            else:
                idx = self.eval(node.slice)
            return base[idx]

        if isinstance(node, ast.Attribute):
            base = self.eval(node.value)

            if isinstance(base, (argparse.Namespace, SimpleNamespace)):
                return getattr(base, node.attr)

            if isinstance(base, dict) and node.attr in base:
                return base[node.attr]

            if isinstance(base, Path) and node.attr in {
                "parent", "name", "stem", "suffix",
            }:
                return getattr(base, node.attr)

            if hasattr(base, node.attr) and not node.attr.startswith("__"):
                return getattr(base, node.attr)

            raise ValueError(f"unsupported attribute {node.attr}")

        if isinstance(node, ast.Call):
            # Bound method/function call.
            if isinstance(node.func, ast.Attribute):
                obj = self.eval(node.func.value)
                method = node.func.attr

                if method in self.FORBIDDEN_METHODS:
                    raise RuntimeError(f"forbidden runtime method: {method}")

                args = [self.eval(a) for a in node.args]
                kwargs = {
                    kw.arg: self.eval(kw.value)
                    for kw in node.keywords
                    if kw.arg is not None
                }

                # Safe Path/string methods
                if isinstance(obj, Path):
                    if method == "resolve":
                        return obj.resolve()
                    if method == "exists":
                        return obj.exists()
                    if method == "is_file":
                        return obj.is_file()
                    if method == "is_dir":
                        return obj.is_dir()

                if isinstance(obj, str):
                    if method == "strip":
                        return obj.strip()
                    if method == "lower":
                        return obj.lower()

                # Read-only authoritative module calls.
                if isinstance(obj, ModuleType):
                    if method.startswith("load_") or method.startswith("build_"):
                        fn = getattr(obj, method)
                        self.call_trace.append({
                            "object": getattr(obj, "__name__", type(obj).__name__),
                            "method": method,
                            "args": repr(args),
                            "kwargs": repr(kwargs),
                            "allowed": True,
                        })
                        return fn(*args, **kwargs)

                # Ordinary object accessors with load_* semantics.
                if method.startswith("load_") and hasattr(obj, method):
                    fn = getattr(obj, method)
                    self.call_trace.append({
                        "object": type(obj).__name__,
                        "method": method,
                        "args": repr(args),
                        "kwargs": repr(kwargs),
                        "allowed": True,
                    })
                    return fn(*args, **kwargs)

                raise ValueError(
                    f"unsupported bound method {type(obj).__name__}.{method}"
                )

            # Plain function call
            cname = call_name(node)
            args = [self.eval(a) for a in node.args]
            kwargs = {
                kw.arg: self.eval(kw.value)
                for kw in node.keywords
                if kw.arg is not None
            }

            if cname == "Path":
                return Path(*args)
            if cname == "str":
                return str(*args)
            if cname == "float":
                return float(*args)
            if cname == "int":
                return int(*args)
            if cname == "len":
                return len(*args)
            if cname == "getattr":
                return getattr(*args)
            if cname == "dict":
                return dict(*args, **kwargs)
            if cname == "np.asarray":
                return np.asarray(*args, **kwargs)
            if cname == "np.array":
                return np.array(*args, **kwargs)

            # Source helper may be bound into env.
            if cname in self.env and callable(self.env[cname]):
                if cname.startswith("load_") or cname.startswith("build_"):
                    self.call_trace.append({
                        "object": "<env>",
                        "method": cname,
                        "args": repr(args),
                        "kwargs": repr(kwargs),
                        "allowed": True,
                    })
                    return self.env[cname](*args, **kwargs)

            raise ValueError(f"unsupported runtime call: {cname}")

        raise ValueError(f"unsupported AST node: {type(node).__name__}")


def extract_argparse_defaults(tree, text, module_globals):
    """
    Evaluate argparse default expressions against imported SG7B10 globals.

    This specifically fixes:
        default=str(DEFAULT_DEPLOYMENT_WORKSPACE)
    """
    rows = []
    defaults = {}

    # Tiny evaluator using module globals only.
    module_env = {
        key: value
        for key, value in module_globals.items()
        if not key.startswith("__")
    }

    evaluator = RuntimeExpressionEvaluator({}, module_env, [])

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not call_name(node).endswith(".add_argument"):
            continue

        flags = [
            a.value for a in node.args
            if isinstance(a, ast.Constant) and isinstance(a.value, str)
        ]

        dest = None
        default_node = None

        for kw in node.keywords:
            if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                dest = kw.value.value
            elif kw.arg == "default":
                default_node = kw.value

        if dest is None and flags:
            long_flags = [f for f in flags if f.startswith("--")]
            chosen = (long_flags[-1] if long_flags else flags[-1]).lstrip("-")
            dest = chosen.replace("-", "_")

        resolved = False
        value = None
        failure = ""

        if default_node is not None:
            try:
                value = evaluator.eval(default_node)
                resolved = True
            except Exception as exc:
                failure = f"{type(exc).__name__}: {exc}"

        rows.append({
            "line": getattr(node, "lineno", ""),
            "flags": ";".join(flags),
            "dest": dest or "",
            "default_expression": node_src(text, default_node) if default_node else "",
            "resolved": resolved,
            "value": repr(value) if resolved else "",
            "failure": failure,
        })

        if dest and resolved:
            defaults[dest] = value

    return rows, defaults


# =============================================================================
# Main
# =============================================================================

def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R6")
    print("Final Runtime Constructor Binding Audit")
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

    prev = load_json(PREV)
    if prev.get("status") != "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_STILL_BLOCKED":
        raise RuntimeError("R26I-R6 requires blocked R26I-R5 status.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = safe_text(SOURCE)
    tree = ast.parse(text)
    main_fn = find_function(tree, "main")
    if main_fn is None:
        raise RuntimeError("Could not locate SG7B10 main().")

    # -------------------------------------------------------------------------
    # Import SG7B10 and resolve source-authentic argparse defaults.
    # -------------------------------------------------------------------------

    sg7b10 = import_sg7b10()

    argparse_rows, defaults = extract_argparse_defaults(
        tree,
        text,
        vars(sg7b10),
    )
    save_csv(ARGPARSE_TABLE, argparse_rows)

    args_ns = argparse.Namespace(**defaults)

    # -------------------------------------------------------------------------
    # Authoritative base module.
    # -------------------------------------------------------------------------

    base_module = sg7b10.load_base_module()

    save_csv(BASE_TABLE, [{
        "resolved": base_module is not None,
        "module_name": getattr(base_module, "__name__", ""),
        "module_file": str(getattr(base_module, "__file__", "")),
        "has_load_dataset": hasattr(base_module, "load_dataset"),
    }])

    # -------------------------------------------------------------------------
    # Resolve main-local variables from actual source semantics.
    # -------------------------------------------------------------------------

    main_amap = ordinary_assignments(main_fn, text)

    env = {
        "ROOT": ROOT,
        "Path": Path,
        "np": np,
        "args": args_ns,
        "argparse": argparse,
        "sg7b10": sg7b10,
        "base": base_module,
        "base_module": base_module,
        "load_base_module": sg7b10.load_base_module,
        "load_deployment_database": sg7b10.load_deployment_database,
    }

    # Bind whichever local variable receives load_base_module().
    for symbol, rec in main_amap.items():
        rhs = rec["rhs_node"]
        if isinstance(rhs, ast.Call) and call_name(rhs) == "load_base_module":
            env[symbol] = base_module

    call_trace = []
    evaluator = RuntimeExpressionEvaluator(main_amap, env, call_trace)

    # deployment_workspace
    workspace = None
    workspace_error = ""
    try:
        workspace = evaluator.resolve("deployment_workspace")
    except Exception as exc:
        workspace_error = f"{type(exc).__name__}: {exc}"

    save_csv(WORKSPACE_TABLE, [{
        "expression": main_amap.get("deployment_workspace", {}).get("rhs", ""),
        "resolved": workspace is not None,
        "value": str(workspace) if workspace is not None else "",
        "exists": Path(workspace).exists() if workspace is not None else False,
        "failure": workspace_error,
    }])

    # tD_scale
    td_scale = None
    td_error = ""
    try:
        td_scale = evaluator.resolve("tD_scale")
    except Exception as exc:
        td_error = f"{type(exc).__name__}: {exc}"

    save_csv(TDSCALE_TABLE, [{
        "expression": main_amap.get("tD_scale", {}).get("rhs", ""),
        "resolved": td_scale is not None,
        "value": repr(td_scale) if td_scale is not None else "",
        "finite": bool(np.isfinite(float(td_scale))) if td_scale is not None else False,
        "positive": bool(float(td_scale) > 0.0) if td_scale is not None else False,
        "failure": td_error,
    }])

    save_csv(DATASET_TABLE, call_trace)

    # -------------------------------------------------------------------------
    # Call ONLY load_deployment_database(...)
    # -------------------------------------------------------------------------

    deployment = None
    helper_error = ""

    if workspace is not None and td_scale is not None:
        try:
            deployment = sg7b10.load_deployment_database(
                workspace,
                td_scale,
            )
        except Exception as exc:
            helper_error = f"{type(exc).__name__}: {exc}"

    x100 = None
    if isinstance(deployment, dict) and "X100" in deployment:
        x100 = np.asarray(deployment["X100"])

    numeric = (
        isinstance(x100, np.ndarray)
        and x100.dtype.kind in {"f", "i", "u", "b", "c"}
    )
    finite = bool(np.all(np.isfinite(x100))) if numeric else False
    shape_ok = (
        isinstance(x100, np.ndarray)
        and x100.ndim == 3
        and x100.shape[-1] == 2
    )

    ch0 = bool(np.any(x100[..., 0] != 0.0)) if shape_ok else False
    ch1 = bool(np.any(x100[..., 1] != 0.0)) if shape_ok else False

    save_csv(HELPER_TABLE, [{
        "helper_called": workspace is not None and td_scale is not None,
        "helper_success": deployment is not None,
        "failure": helper_error,
        "deployment_type": type(deployment).__name__ if deployment is not None else "",
        "deployment_keys": ";".join(sorted(deployment.keys())) if isinstance(deployment, dict) else "",
        "X100_present": isinstance(x100, np.ndarray),
        "X100_shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "X100_dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "X100_numeric": numeric,
        "X100_finite": finite,
        "feature_dim_2": shape_ok,
        "channel0_populated": ch0,
        "channel1_populated": ch1,
    }])

    ready = (
        workspace is not None
        and Path(workspace).exists()
        and td_scale is not None
        and np.isfinite(float(td_scale))
        and float(td_scale) > 0.0
        and isinstance(x100, np.ndarray)
        and numeric
        and finite
        and shape_ok
        and ch0
        and ch1
    )

    if ready:
        status = "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_FULLY_RESOLVED"
        diagnosis = (
            "SOURCE_AUTHENTIC_ARGPARSE_DEFAULT_AND_BASE_DATASET_CALL_CLOSE_FINAL_X100_BINDINGS"
        )
        recommendation = (
            "The final runtime-constructor bindings are resolved. The source-authentic argparse "
            "default resolves deployment_workspace, the authoritative base-module dataset call "
            "resolves tD_scale, and load_deployment_database returns a finite populated X100 tensor. "
            "Persist this X100 and proceed to the repaired authoritative SG7B10 100-day runtime "
            "control. No heuristic X100 discovery is permitted."
        )
        next_milestone = (
            "V15-SG7E1R26I-R7 — Repaired Authoritative SG7B10 100-Day Runtime Control"
        )

        np.savez_compressed(
            NUMERICAL_FILE,
            X100=x100,
            tD_scale=np.asarray([float(td_scale)], dtype=np.float64),
            deployment_workspace=np.asarray([str(workspace)]),
        )
    else:
        status = "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_NOT_YET_CLOSED"
        diagnosis = (
            "ONE_SOURCE_AUTHENTIC_RUNTIME_BINDING_OR_DEPLOYMENT_HELPER_INPUT_REMAINS_UNRESOLVED"
        )
        recommendation = (
            "Do not call model.predict. Inspect only the failed R26I-R6 workspace, tD_scale, "
            "base-dataset call, or deployment-helper row. Do not reopen evaluator authority."
        )
        next_milestone = (
            "V15-SG7E1R26I-R7 — Residual Runtime Constructor Closure Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "workspace_resolved": workspace is not None,
        "workspace_exists": Path(workspace).exists() if workspace is not None else False,
        "tD_scale_resolved": td_scale is not None,
        "base_dataset_calls": len(call_trace),
        "X100_ready": ready,
        "X100_shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "X100_dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R6",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "deployment_workspace": {
            "resolved": workspace is not None,
            "value": str(workspace) if workspace is not None else None,
            "exists": Path(workspace).exists() if workspace is not None else False,
        },
        "tD_scale": {
            "resolved": td_scale is not None,
            "value": float(td_scale) if td_scale is not None else None,
        },
        "X100": {
            "resolved": ready,
            "shape": list(x100.shape) if isinstance(x100, np.ndarray) else None,
            "dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else None,
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
        "milestone": "V15-SG7E1R26I-R6",
        "status": status,
        "diagnosis": diagnosis,
        "X100_ready": ready,
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

    print("SOURCE-AUTHENTIC ARGPARSE DEFAULTS")
    for row in argparse_rows:
        if row["default_expression"]:
            print(
                f"  {row['dest']:<24s} | resolved={row['resolved']} | "
                f"{row['default_expression']} -> "
                f"{row['value'] if row['resolved'] else row['failure']}"
            )

    print("\nAUTHORITATIVE BASE MODULE")
    print(f"  Module                  : {getattr(base_module, '__name__', '')}")
    print(f"  File                    : {getattr(base_module, '__file__', '')}")
    print(f"  load_dataset available  : {hasattr(base_module, 'load_dataset')}")

    print("\nFINAL CALLER BINDINGS")
    print(f"  deployment_workspace    : {workspace if workspace is not None else 'UNRESOLVED'}")
    if workspace is not None:
        print(f"  workspace exists        : {Path(workspace).exists()}")
    elif workspace_error:
        print(f"  workspace failure       : {workspace_error}")

    print(f"  tD_scale                : {td_scale if td_scale is not None else 'UNRESOLVED'}")
    if td_scale is None and td_error:
        print(f"  tD_scale failure        : {td_error}")

    print("\nBASE DATASET CALL TRACE")
    print(f"  Calls                   : {len(call_trace)}")
    for row in call_trace:
        print(
            f"  {row['object']}::{row['method']} "
            f"args={row['args']} kwargs={row['kwargs']}"
        )

    print("\nDEPLOYMENT DATABASE")
    print(f"  Helper success          : {deployment is not None}")
    if helper_error:
        print(f"  Helper failure          : {helper_error}")

    print("\nFINAL X100")
    if isinstance(x100, np.ndarray):
        print(f"  Shape                   : {x100.shape}")
        print(f"  Dtype                   : {x100.dtype}")
        print(f"  Numeric                 : {numeric}")
        print(f"  Finite                  : {finite}")
        print(f"  Feature dim = 2         : {shape_ok}")
        print(f"  Channel 0 populated     : {ch0}")
        print(f"  Channel 1 populated     : {ch1}")
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
    for path in (
        ARGPARSE_TABLE,
        BASE_TABLE,
        DATASET_TABLE,
        WORKSPACE_TABLE,
        TDSCALE_TABLE,
        HELPER_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {path.name}")

    if ready:
        print("\nNumerical:")
        print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R6 FINAL RUNTIME CONSTRUCTOR BINDING AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No fabricated feature was used.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
