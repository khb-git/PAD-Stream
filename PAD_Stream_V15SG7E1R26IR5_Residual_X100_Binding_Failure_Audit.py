from __future__ import annotations

from pathlib import Path
import ast
import argparse
import csv
import importlib.util
import json
import sys
from types import SimpleNamespace

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R5
# Residual X100 Binding Failure Audit
#
# DIAGNOSTIC-ONLY CALLER / BASE-MODULE BINDING MILESTONE
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
# R26I-R4 reduced the remaining failure to exactly:
#
#   workspace  -> KeyError: 'argparse'
#   tD_scale   -> unsupported caller call: load_base_module
#
# R26I-R5 repairs ONLY these two caller-side provenance bindings.
#
# It audits:
#   1. argparse parser definitions / defaults used to construct deployment_workspace,
#   2. args.<field> consumption in the deployment_workspace assignment chain,
#   3. the source-defined load_base_module() helper,
#   4. the returned base-module object and exact tD_scale assignment,
#   5. replays load_deployment_database(workspace, tD_scale) directly,
#   6. validates the returned deployment["X100"] numeric tensor,
#   7. DOES NOT call model.predict.
#
# SG7B10 REMAINS THE AUTHORITATIVE EVALUATOR.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR5"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"

PREV_DIR = ROOT / "output" / "V15_SG7E1R26IR4"
PREV_SUMMARY = PREV_DIR / "PAD_Stream_V15SG7E1R26IR4_Summary.json"

# Outputs
ARGPARSE_TABLE = OUT / "V15SG7E1R26IR5_Argparse_Default_Contract.csv"
WORKSPACE_TABLE = OUT / "V15SG7E1R26IR5_Deployment_Workspace_Binding.csv"
BASE_TABLE = OUT / "V15SG7E1R26IR5_Base_Module_Binding.csv"
TDSCALE_TABLE = OUT / "V15SG7E1R26IR5_tD_Scale_Binding.csv"
HELPER_TABLE = OUT / "V15SG7E1R26IR5_Load_Deployment_Database_Runtime_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR5_Residual_Binding_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR5_Reconstructed_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR5_Residual_X100_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR5_Summary.json"


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


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def ordinary_assignments(scope, text):
    amap = {}
    rows = []

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
                }
                amap[tgt.id] = rec
                rows.append(rec)

    return rows, amap


def extract_argparse_defaults(tree, text):
    """
    Extract parser.add_argument(...) calls and source-defined defaults only.
    No CLI value is invented.
    """
    rows = []
    defaults = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node)
        if not cname.endswith(".add_argument"):
            continue

        flags = []
        for a in node.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                flags.append(a.value)

        dest = None
        default_present = False
        default_value = None

        for kw in node.keywords:
            if kw.arg == "dest":
                if isinstance(kw.value, ast.Constant):
                    dest = kw.value.value
            elif kw.arg == "default":
                default_present = True
                try:
                    default_value = ast.literal_eval(kw.value)
                except Exception:
                    default_value = node_src(text, kw.value)

        if not dest and flags:
            long_flags = [f for f in flags if f.startswith("--")]
            base = (long_flags[-1] if long_flags else flags[-1]).lstrip("-")
            dest = base.replace("-", "_")

        rows.append({
            "line": getattr(node, "lineno", ""),
            "flags": ";".join(flags),
            "dest": dest or "",
            "default_present": default_present,
            "default_value": repr(default_value) if default_present else "",
            "expression": node_src(text, node),
        })

        if dest and default_present:
            defaults[dest] = default_value

    return rows, defaults


class SourceEvaluator:
    """
    Restricted evaluator for main()-local source configuration.
    Supports source-defined defaults, namespace attributes, paths, dictionaries,
    subscripts, getattr, and already-bound runtime objects.
    """

    def __init__(self, amap, env):
        self.amap = amap
        self.env = env
        self.visiting = set()

    def resolve(self, symbol):
        if symbol in self.env:
            return self.env[symbol]
        if symbol in self.visiting:
            raise ValueError(f"cycle at {symbol}")
        if symbol not in self.amap:
            raise KeyError(symbol)

        self.visiting.add(symbol)
        try:
            value = self.eval(self.amap[symbol]["rhs_node"])
            self.env[symbol] = value
            return value
        finally:
            self.visiting.remove(symbol)

    def eval(self, node):
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return self.resolve(node.id)

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
            if isinstance(node.op, ast.USub): return -v
            if isinstance(node.op, ast.UAdd): return +v
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
            if isinstance(node.slice, ast.Constant):
                idx = node.slice.value
            else:
                idx = self.eval(node.slice)
            return base[idx]

        if isinstance(node, ast.Attribute):
            base = self.eval(node.value)
            if isinstance(base, (argparse.Namespace, SimpleNamespace)):
                return getattr(base, node.attr)
            if isinstance(base, dict) and node.attr in base:
                return base[node.attr]
            if isinstance(base, Path) and node.attr in {"parent", "name", "stem", "suffix"}:
                return getattr(base, node.attr)
            if hasattr(base, node.attr) and not node.attr.startswith("__"):
                return getattr(base, node.attr)
            raise ValueError(f"unsupported attribute {node.attr}")

        if isinstance(node, ast.Call):
            cname = call_name(node)

            if isinstance(node.func, ast.Attribute):
                obj = self.eval(node.func.value)
                meth = node.func.attr
                args = [self.eval(a) for a in node.args]
                kwargs = {kw.arg: self.eval(kw.value) for kw in node.keywords if kw.arg}

                if isinstance(obj, Path):
                    if meth == "resolve": return obj.resolve()
                    if meth == "exists": return obj.exists()
                if isinstance(obj, str):
                    if meth == "strip": return obj.strip()
                    if meth == "lower": return obj.lower()

                raise ValueError(f"unsupported bound method {type(obj).__name__}.{meth}")

            args = [self.eval(a) for a in node.args]
            kwargs = {kw.arg: self.eval(kw.value) for kw in node.keywords if kw.arg}

            if cname == "Path": return Path(*args)
            if cname == "float": return float(*args)
            if cname == "int": return int(*args)
            if cname == "str": return str(*args)
            if cname == "getattr": return getattr(*args)
            if cname == "dict": return dict(*args, **kwargs)

            raise ValueError(f"unsupported source call {cname}")

        raise ValueError(f"unsupported node {type(node).__name__}")


def import_source_module():
    """
    Import SG7B10 without running main(). Python's __name__ guard protects the
    executable workflow. This gives us its actual helper functions.
    """
    name = "_pad_stream_sg7b10_r26ir5"
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create import spec.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def locate_main_function(tree):
    return find_function(tree, "main")


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R5")
    print("Residual X100 Binding Failure Audit")
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
    if prev.get("status") != "SG7B10_DEPLOYMENT_X100_FINAL_BINDING_STILL_BLOCKED":
        raise RuntimeError("R26I-R5 requires blocked R26I-R4 status.")

    text = safe_text(SOURCE)
    tree = ast.parse(text)
    main_fn = locate_main_function(tree)

    if main_fn is None:
        raise RuntimeError("Could not locate SG7B10 main().")

    # -------------------------------------------------------------------------
    # 1. Resolve argparse defaults into a source-faithful Namespace
    # -------------------------------------------------------------------------

    argparse_rows, defaults = extract_argparse_defaults(tree, text)
    save_csv(ARGPARSE_TABLE, argparse_rows)

    args_namespace = argparse.Namespace(**defaults)

    # -------------------------------------------------------------------------
    # 2. Import authoritative source and execute load_base_module() only
    # -------------------------------------------------------------------------

    module_imported = False
    base_module = None
    base_error = ""

    try:
        sg7b10 = import_source_module()
        module_imported = True

        if not hasattr(sg7b10, "load_base_module"):
            raise AttributeError("load_base_module not found after import.")

        base_module = sg7b10.load_base_module()
    except Exception as exc:
        base_error = f"{type(exc).__name__}: {exc}"

    base_rows = [{
        "source_imported": module_imported,
        "load_base_module_available": bool(module_imported and hasattr(sg7b10, "load_base_module")) if module_imported else False,
        "base_module_resolved": base_module is not None,
        "base_module_type": type(base_module).__name__ if base_module is not None else "",
        "base_module_name": getattr(base_module, "__name__", "") if base_module is not None else "",
        "failure": base_error,
    }]
    save_csv(BASE_TABLE, base_rows)

    # -------------------------------------------------------------------------
    # 3. Resolve main-local deployment_workspace and tD_scale
    # -------------------------------------------------------------------------

    _, main_amap = ordinary_assignments(main_fn, text)

    env = {
        "ROOT": ROOT,
        "Path": Path,
        "args": args_namespace,
        "argparse": argparse,
    }

    # Bind source-defined base-module variable aliases by identifying the
    # assignment that calls load_base_module().
    for sym, rec in main_amap.items():
        if isinstance(rec["rhs_node"], ast.Call) and call_name(rec["rhs_node"]) == "load_base_module":
            if base_module is not None:
                env[sym] = base_module

    evaluator = SourceEvaluator(main_amap, env)

    workspace = None
    workspace_error = ""
    try:
        workspace = evaluator.resolve("deployment_workspace")
    except Exception as exc:
        workspace_error = f"{type(exc).__name__}: {exc}"

    td_scale = None
    td_error = ""
    try:
        td_scale = evaluator.resolve("tD_scale")
    except Exception as exc:
        td_error = f"{type(exc).__name__}: {exc}"

    workspace_rows = [{
        "symbol": "deployment_workspace",
        "resolved": workspace is not None,
        "value": str(workspace) if workspace is not None else "",
        "value_type": type(workspace).__name__ if workspace is not None else "",
        "exists": Path(workspace).exists() if workspace is not None else False,
        "failure": workspace_error,
        "source_expression": main_amap.get("deployment_workspace", {}).get("rhs", ""),
    }]
    save_csv(WORKSPACE_TABLE, workspace_rows)

    td_rows = [{
        "symbol": "tD_scale",
        "resolved": td_scale is not None,
        "value": repr(td_scale) if td_scale is not None else "",
        "value_type": type(td_scale).__name__ if td_scale is not None else "",
        "finite": bool(np.isfinite(float(td_scale))) if td_scale is not None else False,
        "positive": bool(float(td_scale) > 0.0) if td_scale is not None else False,
        "failure": td_error,
        "source_expression": main_amap.get("tD_scale", {}).get("rhs", ""),
    }]
    save_csv(TDSCALE_TABLE, td_rows)

    # -------------------------------------------------------------------------
    # 4. Execute ONLY load_deployment_database(workspace, tD_scale)
    # -------------------------------------------------------------------------

    deployment = None
    helper_error = ""

    if module_imported and workspace is not None and td_scale is not None:
        try:
            if not hasattr(sg7b10, "load_deployment_database"):
                raise AttributeError("load_deployment_database not found.")

            deployment = sg7b10.load_deployment_database(
                workspace,
                td_scale,
            )
        except Exception as exc:
            helper_error = f"{type(exc).__name__}: {exc}"

    x100 = None
    if isinstance(deployment, dict) and "X100" in deployment:
        x100 = np.asarray(deployment["X100"])

    numeric = isinstance(x100, np.ndarray) and x100.dtype.kind in {"f", "i", "u", "b", "c"}
    finite = bool(np.all(np.isfinite(x100))) if numeric else False
    shape_ok = isinstance(x100, np.ndarray) and x100.ndim == 3 and x100.shape[-1] == 2
    channel0_populated = bool(np.any(x100[..., 0] != 0.0)) if shape_ok else False
    channel1_populated = bool(np.any(x100[..., 1] != 0.0)) if shape_ok else False

    helper_rows = [{
        "workspace_resolved": workspace is not None,
        "workspace_exists": Path(workspace).exists() if workspace is not None else False,
        "tD_scale_resolved": td_scale is not None,
        "helper_called": bool(module_imported and workspace is not None and td_scale is not None),
        "deployment_return_type": type(deployment).__name__ if deployment is not None else "",
        "deployment_keys": ";".join(sorted(deployment.keys())) if isinstance(deployment, dict) else "",
        "X100_present": isinstance(x100, np.ndarray),
        "X100_shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "X100_dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "X100_numeric": numeric,
        "X100_finite": finite,
        "feature_dim_2": shape_ok,
        "channel0_populated": channel0_populated,
        "channel1_populated": channel1_populated,
        "failure": helper_error,
    }]
    save_csv(HELPER_TABLE, helper_rows)

    ready = (
        base_module is not None
        and workspace is not None
        and Path(workspace).exists()
        and td_scale is not None
        and np.isfinite(float(td_scale))
        and float(td_scale) > 0.0
        and isinstance(x100, np.ndarray)
        and numeric
        and finite
        and shape_ok
        and channel0_populated
        and channel1_populated
    )

    if ready:
        status = "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_VALIDATED"
        diagnosis = (
            "ARGPARSE_DEFAULTS_BASE_MODULE_TDSCALE_AND_DEPLOYMENT_WORKSPACE_REPRODUCE_POPULATED_X100"
        )
        recommendation = (
            "The residual X100 binding failure is resolved using the actual SG7B10 source-defined "
            "argparse defaults, load_base_module(), and load_deployment_database() helper. The "
            "returned deployment['X100'] tensor is finite, numeric, populated in both feature "
            "channels, and has trailing dimension 2. Persist this X100 as the sole legal input "
            "for the repaired 100-day runtime control."
        )
        next_milestone = (
            "V15-SG7E1R26I-R6 — Repaired Authoritative SG7B10 100-Day Runtime Control"
        )

        np.savez_compressed(
            NUMERICAL_FILE,
            X100=x100,
            tD_scale=np.asarray([float(td_scale)], dtype=np.float64),
            deployment_workspace=np.asarray([str(workspace)]),
        )
    else:
        status = "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_STILL_BLOCKED"
        diagnosis = (
            "ARGPARSE_DEFAULT_BASE_MODULE_OR_DEPLOYMENT_DATABASE_RUNTIME_BINDING_REMAINS_UNRESOLVED"
        )
        recommendation = (
            "Do not call model.predict. Inspect only the failed argparse/default, base-module, "
            "workspace, tD_scale, or load_deployment_database row emitted by R26I-R5. Do not "
            "broaden evaluator authority or fabricate feature inputs."
        )
        next_milestone = (
            "V15-SG7E1R26I-R6 — Final Runtime Constructor Binding Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "argparse_default_count": len(defaults),
        "base_module_resolved": base_module is not None,
        "workspace_resolved": workspace is not None,
        "workspace_exists": Path(workspace).exists() if workspace is not None else False,
        "tD_scale_resolved": td_scale is not None,
        "X100_ready": ready,
        "X100_shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "X100_dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R5",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "argparse_defaults": defaults,
        "base_module": {
            "resolved": base_module is not None,
            "module_name": getattr(base_module, "__name__", None) if base_module is not None else None,
        },
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
        "milestone": "V15-SG7E1R26I-R5",
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

    print("ARGPARSE DEFAULT CONTRACT")
    print(f"  Defaults recovered      : {len(defaults)}")
    for key in sorted(defaults):
        print(f"  {key:<24s} = {defaults[key]!r}")

    print("\nBASE MODULE")
    print(f"  Source imported         : {module_imported}")
    print(f"  Base module resolved    : {base_module is not None}")
    if base_module is not None:
        print(f"  Module name             : {getattr(base_module, '__name__', '')}")
    elif base_error:
        print(f"  Failure                 : {base_error}")

    print("\nCALLER BINDINGS")
    print(f"  deployment_workspace    : {workspace if workspace is not None else 'UNRESOLVED'}")
    if workspace is not None:
        print(f"  workspace exists        : {Path(workspace).exists()}")
    elif workspace_error:
        print(f"  workspace failure       : {workspace_error}")

    print(f"  tD_scale                : {td_scale if td_scale is not None else 'UNRESOLVED'}")
    if td_scale is None and td_error:
        print(f"  tD_scale failure        : {td_error}")

    print("\nDEPLOYMENT DATABASE RUNTIME")
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
        print(f"  Channel 0 populated     : {channel0_populated}")
        print(f"  Channel 1 populated     : {channel1_populated}")
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
        ARGPARSE_TABLE,
        WORKSPACE_TABLE,
        BASE_TABLE,
        TDSCALE_TABLE,
        HELPER_TABLE,
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
    print("V15-SG7E1R26I-R5 RESIDUAL X100 BINDING FAILURE AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No fabricated feature was used.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
