from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R3
# Remaining X100 Helper Input Binding / In-Place Feature Population Audit
#
# DIAGNOSTIC-ONLY FEATURE-BINDING MILESTONE
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
# R26I-R2 established the key construction pattern:
#
#     X100 = np.zeros((n_streamlines, n_nodes, 2), dtype=np.float32)
#
# but reconstruction remained blocked because:
#
#   - workspace was not yet bound,
#   - tD_scale was not yet bound,
#   - the prior audit traced the allocation of X100 but not subsequent in-place
#     population statements such as:
#
#         X100[..., 0] = ...
#         X100[..., 1] = ...
#
# R26I-R3 therefore audits ONLY the resolved SG7B10 helper:
#
#     load_deployment_database(workspace, tD_scale)
#
# and traces:
#
#   1. caller-side recursive binding of workspace and tD_scale,
#   2. np.load path construction from workspace,
#   3. exact NPZ key accesses,
#   4. n_streamlines / n_nodes source,
#   5. every X100 subscript write,
#   6. deterministic reconstruction of the fully populated (*,*,2) X100 tensor.
#
# No model inference is executed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR3"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
HELPER = "load_deployment_database"

PREV_DIR = ROOT / "output" / "V15_SG7E1R26IR2B"
PREV_SUMMARY = PREV_DIR / "PAD_Stream_V15SG7E1R26IR2B_Summary.json"

# Outputs
CALLER_BIND_TABLE = OUT / "V15SG7E1R26IR3_Helper_Caller_Argument_Binding.csv"
LOAD_PATH_TABLE = OUT / "V15SG7E1R26IR3_Workspace_Load_Path_Resolution.csv"
NPZ_KEY_TABLE = OUT / "V15SG7E1R26IR3_NPZ_Key_Binding.csv"
X100_WRITE_TABLE = OUT / "V15SG7E1R26IR3_X100_InPlace_Write_Trace.csv"
DIM_TABLE = OUT / "V15SG7E1R26IR3_X100_Dimension_Source_Trace.csv"
RECON_TABLE = OUT / "V15SG7E1R26IR3_X100_Full_Reconstruction_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR3_X100_Input_Binding_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR3_Reconstructed_Populated_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR3_Remaining_X100_Input_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR3_Summary.json"


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
                    "rhs_symbols": names_in(node.value),
                }
                amap[tgt.id] = rec
                rows.append(rec)
    return rows, amap


def resolve_simple_symbol(symbol, amap, env):
    """
    Conservative recursive evaluator for caller-side scalar/path values.
    Supports constants, variable aliases, Path joining, division operator on Path,
    and simple arithmetic.
    """
    visiting = set()

    def ev(node):
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            if node.id in visiting:
                raise ValueError("cycle")
            if node.id not in amap:
                raise KeyError(node.id)
            visiting.add(node.id)
            val = ev(amap[node.id]["rhs_node"])
            visiting.remove(node.id)
            env[node.id] = val
            return val

        if isinstance(node, ast.BinOp):
            a = ev(node.left)
            b = ev(node.right)
            if isinstance(node.op, ast.Div):
                # Path / "child" OR numeric division
                if isinstance(a, Path):
                    return a / str(b)
                return a / b
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Pow):
                return a ** b
            raise ValueError("unsupported binop")

        if isinstance(node, ast.Call):
            cname = call_name(node)
            args = [ev(a) for a in node.args]

            if cname in {"Path"}:
                return Path(*args)
            if cname in {"float"}:
                return float(*args)
            if cname in {"int"}:
                return int(*args)

            raise ValueError(f"unsupported caller call {cname}")

        if isinstance(node, ast.Attribute):
            base = ev(node.value)
            if node.attr == "resolve":
                return base.resolve
            raise ValueError(f"unsupported attr {node.attr}")

        raise ValueError(f"unsupported caller node {type(node).__name__}")

    if symbol in env:
        return env[symbol]
    if symbol not in amap:
        raise KeyError(symbol)
    return ev(amap[symbol]["rhs_node"])


def find_helper_call(tree, text):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and call_name(node) == HELPER:
            return node
    return None


def slice_to_python(node, ev):
    if isinstance(node, ast.Slice):
        lo = ev(node.lower) if node.lower else None
        hi = ev(node.upper) if node.upper else None
        st = ev(node.step) if node.step else None
        return slice(lo, hi, st)
    if isinstance(node, ast.Tuple):
        return tuple(slice_to_python(x, ev) for x in node.elts)
    return ev(node)


class HelperEvaluator:
    """
    Restricted evaluator for deterministic helper reconstruction.
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

        if isinstance(node, ast.List):
            return [self.eval(x) for x in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self.eval(x) for x in node.elts)

        if isinstance(node, ast.Dict):
            return {
                self.eval(k): self.eval(v)
                for k, v in zip(node.keys, node.values)
            }

        if isinstance(node, ast.Subscript):
            base = self.eval(node.value)
            idx = slice_to_python(node.slice, self.eval)
            return base[idx]

        if isinstance(node, ast.Attribute):
            base = self.eval(node.value)
            if node.attr in {"shape", "dtype", "T"}:
                return getattr(base, node.attr)
            if node.attr == "files":
                return base.files
            raise ValueError(f"unsupported attr {node.attr}")

        if isinstance(node, ast.Call):
            cname = call_name(node)
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
            }

            if cname in allowed:
                return allowed[cname](*args, **kwargs)

            if cname == "np.load":
                path = Path(args[0])
                db = np.load(path, allow_pickle=kwargs.get("allow_pickle", False))
                return db

            if isinstance(node.func, ast.Attribute):
                obj = self.eval(node.func.value)
                meth = node.func.attr
                if meth == "reshape": return obj.reshape(*args, **kwargs)
                if meth == "ravel": return obj.ravel()
                if meth == "flatten": return obj.flatten()
                if meth == "astype": return obj.astype(*args, **kwargs)

            raise ValueError(f"unsupported helper call {cname}")

        raise ValueError(f"unsupported node {type(node).__name__}")


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R3")
    print("Remaining X100 Helper Input Binding / In-Place Feature Population Audit")
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
    if prev.get("status") != "SG7B10_DEPLOYMENT_X100_NUMERIC_RECONSTRUCTION_BLOCKED":
        raise RuntimeError("R26I-R3 requires blocked R26I-R2 reconstruction status.")

    text = safe_text(SOURCE)
    tree = ast.parse(text)
    helper = find_function(tree, HELPER)
    if helper is None:
        raise RuntimeError(f"Missing helper {HELPER}")

    # -------------------------------------------------------------------------
    # Caller-side argument binding
    # -------------------------------------------------------------------------

    _, root_amap = ordinary_assignments(tree, text)
    helper_call = find_helper_call(tree, text)
    if helper_call is None:
        raise RuntimeError("Could not find helper call.")

    params = [a.arg for a in helper.args.args]
    caller_env = {
        "ROOT": ROOT,
        "__file__": str(SOURCE),
    }

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
            })
            continue

        arg = helper_call.args[i]
        expr = node_src(text, arg)

        try:
            if isinstance(arg, ast.Name):
                val = resolve_simple_symbol(arg.id, root_amap, caller_env)
            else:
                # small wrapper through synthetic assignment
                temp_map = {"__arg__": {
                    "rhs_node": arg,
                    "line": getattr(arg, "lineno", ""),
                    "rhs": expr,
                    "rhs_symbols": names_in(arg),
                }}
                merged = dict(root_amap)
                merged.update(temp_map)
                val = resolve_simple_symbol("__arg__", merged, caller_env)

            bound_args[param] = val
            resolved = True
        except Exception as exc:
            val = f"{type(exc).__name__}: {exc}"
            resolved = False

        caller_rows.append({
            "parameter": param,
            "expression": expr,
            "resolved": resolved,
            "value": str(val),
            "value_type": type(val).__name__ if resolved else "",
        })

    save_csv(CALLER_BIND_TABLE, caller_rows)

    # -------------------------------------------------------------------------
    # Trace helper assignments + X100 in-place writes
    # -------------------------------------------------------------------------

    helper_assignments = []
    x100_writes = []
    dim_rows = []

    for node in ast.walk(helper):
        if not isinstance(node, ast.Assign):
            continue

        rhs = node.value

        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                helper_assignments.append({
                    "line": node.lineno,
                    "target": tgt.id,
                    "rhs_node": rhs,
                    "rhs": node_src(text, rhs),
                })
                if tgt.id in {"n_streamlines", "n_nodes"}:
                    dim_rows.append({
                        "line": node.lineno,
                        "symbol": tgt.id,
                        "rhs": node_src(text, rhs),
                        "rhs_symbols": ";".join(names_in(rhs)),
                    })

            elif isinstance(tgt, ast.Subscript):
                base = tgt.value.id if isinstance(tgt.value, ast.Name) else ""
                if base == "X100":
                    x100_writes.append({
                        "line": node.lineno,
                        "target": node_src(text, tgt),
                        "slice": node_src(text, tgt.slice),
                        "rhs": node_src(text, rhs),
                        "rhs_symbols": ";".join(names_in(rhs)),
                        "target_node": tgt,
                        "rhs_node": rhs,
                    })

    save_csv(X100_WRITE_TABLE, [
        {k: v for k, v in r.items() if not k.endswith("_node")}
        for r in x100_writes
    ])
    save_csv(DIM_TABLE, dim_rows)

    # -------------------------------------------------------------------------
    # Execute helper assignment sequence conservatively in source-line order.
    # This catches np.load path construction and all X100 in-place writes.
    # -------------------------------------------------------------------------

    env = {"np": np, "Path": Path}
    env.update(bound_args)

    load_path_rows = []
    npz_key_rows = []
    reconstruction_rows = []

    # Need source-order traversal of top-level statements inside helper.
    statements = sorted(helper.body, key=lambda n: getattr(n, "lineno", 10**9))

    evaluator = HelperEvaluator(env)

    for stmt in statements:
        if not isinstance(stmt, ast.Assign):
            continue

        rhs = stmt.value

        # Ordinary name assignment
        simple_targets = [t for t in stmt.targets if isinstance(t, ast.Name)]
        sub_targets = [t for t in stmt.targets if isinstance(t, ast.Subscript)]

        if simple_targets:
            try:
                val = evaluator.eval(rhs)
                for tgt in simple_targets:
                    env[tgt.id] = val

                    reconstruction_rows.append({
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
                        path_val = None
                        try:
                            path_val = evaluator.eval(rhs.args[0])
                        except Exception:
                            pass
                        load_path_rows.append({
                            "line": stmt.lineno,
                            "handle": tgt.id,
                            "expression": node_src(text, rhs),
                            "resolved_path": str(path_val) if path_val is not None else "",
                            "exists": bool(Path(path_val).exists()) if path_val is not None else False,
                        })

            except Exception as exc:
                for tgt in simple_targets:
                    reconstruction_rows.append({
                        "line": stmt.lineno,
                        "operation": "NAME_ASSIGN",
                        "target": tgt.id,
                        "rhs": node_src(text, rhs),
                        "resolved": False,
                        "shape": "",
                        "dtype": "",
                        "failure": f"{type(exc).__name__}: {exc}",
                    })

        # X100 subscript write
        for tgt in sub_targets:
            base = tgt.value.id if isinstance(tgt.value, ast.Name) else ""
            if base != "X100":
                continue

            try:
                if "X100" not in env:
                    raise KeyError("X100 allocation not resolved")

                idx = slice_to_python(tgt.slice, evaluator.eval)
                val = evaluator.eval(rhs)
                env["X100"][idx] = val

                reconstruction_rows.append({
                    "line": stmt.lineno,
                    "operation": "X100_INPLACE_WRITE",
                    "target": node_src(text, tgt),
                    "rhs": node_src(text, rhs),
                    "resolved": True,
                    "shape": str(np.asarray(val).shape),
                    "dtype": str(np.asarray(val).dtype),
                    "failure": "",
                })

            except Exception as exc:
                reconstruction_rows.append({
                    "line": stmt.lineno,
                    "operation": "X100_INPLACE_WRITE",
                    "target": node_src(text, tgt),
                    "rhs": node_src(text, rhs),
                    "resolved": False,
                    "shape": "",
                    "dtype": "",
                    "failure": f"{type(exc).__name__}: {exc}",
                })

    # Audit NPZ accesses by source + resolved handle content
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

        key = ""
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value

        if key:
            npz_key_rows.append({
                "handle": handle,
                "key": key,
                "exists_in_loaded_npz": key in obj.files,
                "shape": str(np.asarray(obj[key]).shape) if key in obj.files else "",
                "dtype": str(np.asarray(obj[key]).dtype) if key in obj.files else "",
            })

    save_csv(LOAD_PATH_TABLE, load_path_rows)
    save_csv(NPZ_KEY_TABLE, npz_key_rows)
    save_csv(RECON_TABLE, reconstruction_rows)

    # -------------------------------------------------------------------------
    # Final X100 state
    # -------------------------------------------------------------------------

    x100 = env.get("X100")
    numeric = isinstance(x100, np.ndarray) and x100.dtype.kind in {"f", "i", "u", "b", "c"}
    finite = bool(np.all(np.isfinite(x100))) if numeric else False
    shape_ok = isinstance(x100, np.ndarray) and x100.ndim >= 2 and x100.shape[-1] == 2

    all_writes_resolved = all(
        r["resolved"]
        for r in reconstruction_rows
        if r["operation"] == "X100_INPLACE_WRITE"
    ) and len(x100_writes) > 0

    args_resolved = all(r["resolved"] for r in caller_rows)

    ready = (
        args_resolved
        and numeric
        and finite
        and shape_ok
        and all_writes_resolved
    )

    if ready:
        status = "SG7B10_DEPLOYMENT_X100_FULLY_RECONSTRUCTED"
        diagnosis = (
            "CALLER_ARGUMENTS_LOAD_PATHS_DIMENSIONS_AND_INPLACE_FEATURE_WRITES_REPRODUCE_X100"
        )
        recommendation = (
            "The authoritative SG7B10 deployment X100 tensor is now fully reconstructed, including "
            "its in-place feature-channel population. Persist this tensor as the only legal input "
            "for the repaired 100-day runtime control. Do not use heuristic artifact discovery."
        )
        next_milestone = (
            "V15-SG7E1R26I-R4 — Repaired Authoritative SG7B10 100-Day Runtime Control"
        )

        np.savez_compressed(NUMERICAL_FILE, X100=np.asarray(x100))

    else:
        status = "SG7B10_DEPLOYMENT_X100_FULL_RECONSTRUCTION_STILL_BLOCKED"
        diagnosis = (
            "ONE_OR_MORE_CALLER_LOAD_DIMENSION_OR_INPLACE_WRITE_BINDINGS_REMAIN_UNRESOLVED"
        )
        recommendation = (
            "Do not call model.predict. Audit only the failed caller/load/dimension/X100-write rows "
            "persisted by R26I-R3. Do not broaden evaluator authority or fabricate feature values."
        )
        next_milestone = (
            "V15-SG7E1R26I-R4 — Final Failed X100 Write / Load Binding Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "caller_args_resolved": args_resolved,
        "load_paths_resolved": sum(1 for r in load_path_rows if r["exists"]),
        "load_path_records": len(load_path_rows),
        "npz_key_records": len(npz_key_rows),
        "X100_write_count": len(x100_writes),
        "all_X100_writes_resolved": all_writes_resolved,
        "X100_present": isinstance(x100, np.ndarray),
        "X100_shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "X100_dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "X100_numeric": numeric,
        "X100_finite": finite,
        "model_feature_dim_ok": shape_ok,
        "ready": ready,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R3",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "helper": HELPER,
        "caller_binding": {
            "resolved": args_resolved,
            "arguments": caller_rows,
        },
        "X100": {
            "write_count": len(x100_writes),
            "all_writes_resolved": all_writes_resolved,
            "ready": ready,
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
        "milestone": "V15-SG7E1R26I-R3",
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

    print("CALLER ARGUMENT BINDING")
    for r in caller_rows:
        print(
            f"  {r['parameter']:<20s} | resolved={r['resolved']} | "
            f"{r['expression']} -> {r['value']}"
        )

    print("\nHELPER LOAD PATHS")
    for r in load_path_rows:
        print(
            f"  {r['handle']:<16s} | exists={r['exists']} | "
            f"{r['resolved_path']}"
        )

    print("\nX100 IN-PLACE WRITES")
    print(f"  Write count             : {len(x100_writes)}")
    for r in x100_writes:
        print(f"  line={r['line']} | {r['target']} <- {r['rhs']}")

    print("\nFINAL X100")
    if isinstance(x100, np.ndarray):
        print(f"  Shape                   : {x100.shape}")
        print(f"  Dtype                   : {x100.dtype}")
        print(f"  Numeric                 : {numeric}")
        print(f"  Finite                  : {finite}")
        print(f"  Feature dim = 2         : {shape_ok}")
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
        CALLER_BIND_TABLE,
        LOAD_PATH_TABLE,
        NPZ_KEY_TABLE,
        X100_WRITE_TABLE,
        DIM_TABLE,
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
    print("V15-SG7E1R26I-R3 REMAINING X100 HELPER INPUT BINDING AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No fabricated feature was used.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
