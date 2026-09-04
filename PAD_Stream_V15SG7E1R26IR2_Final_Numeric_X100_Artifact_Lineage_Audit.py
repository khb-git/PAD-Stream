from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R
# Final Numeric X100 Artifact Lineage Audit
#
# DIAGNOSTIC-ONLY X100-CONSTRUCTION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
#
# PURPOSE
# -------
# R26IR proved that no persisted NPZ array currently discovered is directly
# executable as deployment["X100"] for the authoritative model input shape:
#
#     (None, 2)
#
# This means SG7B10 deployment["X100"] is almost certainly CONSTRUCTED IN
# MEMORY rather than persisted as one ready-made tensor.
#
# Earlier audits missed this because they traced ordinary Name assignments but
# not dictionary/subscript assignments such as:
#
#     deployment["X100"] = ...
#
# or dictionary literals such as:
#
#     deployment = {"X100": ..., ...}
#
# R26I-R therefore traces the exact SG7B10 construction chain:
#
#     persisted component arrays
#       -> normalization / reshaping
#       -> X100 two-column feature construction
#       -> deployment["X100"]
#
# The audit:
#
#   1. finds every assignment to deployment and deployment["X100"],
#   2. traces dictionary-literal X100 entries,
#   3. recursively traces the component symbols used by X100,
#   4. resolves those component symbols to persisted NPZ keys where possible,
#   5. reconstructs X100 ONLY if the source expression can be evaluated from
#      persisted numeric components with no fabricated values,
#   6. verifies the reconstructed tensor is numeric, finite, and shape (*,2),
#   7. DOES NOT call model.predict.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR2"
OUT.mkdir(parents=True, exist_ok=True)

AUTHORITATIVE_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

R26IR_DIR = ROOT / "output" / "V15_SG7E1R26IR"
R26IR_SUMMARY = R26IR_DIR / "PAD_Stream_V15SG7E1R26IR_Summary.json"

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

# Outputs
ASSIGN_TABLE = OUT / "V15SG7E1R26IR2_Deployment_Subscript_Assignment_Trace.csv"
DICT_TABLE = OUT / "V15SG7E1R26IR2_Deployment_Dictionary_X100_Trace.csv"
DEPENDENCY_TABLE = OUT / "V15SG7E1R26IR2_X100_Component_Dependency_Trace.csv"
PERSISTED_TABLE = OUT / "V15SG7E1R26IR2_Component_to_Persisted_Array_Binding.csv"
RECON_TABLE = OUT / "V15SG7E1R26IR2_X100_Reconstruction_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR2_X100_Lineage_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR2_Reconstructed_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR2_X100_Lineage_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR2_Summary.json"


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


def literal_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def subscript_identity(node):
    """
    Return (base_name, key_string) for Name["literal"] subscripts.
    """
    if not isinstance(node, ast.Subscript):
        return None, None

    base = node.value.id if isinstance(node.value, ast.Name) else None

    sl = node.slice
    if isinstance(sl, ast.Constant):
        key = sl.value if isinstance(sl.value, str) else None
    else:
        key = None

    return base, key


def ordinary_assignment_map(tree, text):
    out = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                out[tgt.id] = {
                    "line": node.lineno,
                    "rhs_node": node.value,
                    "rhs": node_src(text, node.value),
                    "rhs_symbols": names_in(node.value),
                }

    return out


def recursive_dependencies(seed_symbols, amap):
    rows = []
    seen = set()
    frontier = list(seed_symbols)

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


def candidate_npz_files():
    output_root = ROOT / "output"
    if not output_root.exists():
        return []

    out = []

    for p in output_root.rglob("*.npz"):
        low = str(p).lower()

        # Tight lineage around B9/B10 and the later CR3 transfer chain.
        if any(tok in low for tok in (
            "v15_sg7b9",
            "v15sg7b9",
            "v15_sg7b10",
            "v15sg7b10",
            "v15_sg7b11",
            "v15sg7b11",
            "sg7cr",
        )):
            out.append(p.resolve())

    return sorted(set(out))


def persisted_key_inventory():
    records = []

    for path in candidate_npz_files():
        try:
            db = np.load(path, allow_pickle=True)
        except Exception:
            continue

        for key in db.files:
            try:
                arr = np.asarray(db[key])
            except Exception:
                continue

            records.append({
                "path": path,
                "key": key,
                "shape": arr.shape,
                "dtype": str(arr.dtype),
                "kind": arr.dtype.kind,
                "arr": np.array(arr, copy=True),
            })

        db.close()

    return records


def score_component_binding(symbol: str, rec):
    """
    Score persisted-array bindings from symbol/key semantics and shape only.
    No candidate performance is used.
    """
    s = symbol.lower()
    k = rec["key"].lower()
    p = str(rec["path"]).lower()

    score = 0
    reasons = []

    if k == s:
        score += 1000
        reasons.append("exact_symbol_key")

    if s in k or k in s:
        score += 400
        reasons.append("symbol_key_overlap")

    aliases = {
        "xi": ["xi", "xcoord", "normalized_xi"],
        "tau": ["tau", "tof"],
        "tof": ["tof", "tau"],
        "time": ["time", "days", "t100"],
        "t100": ["t100", "time100", "100d", "100_day"],
        "x100": ["x100"],
    }

    for root, toks in aliases.items():
        if root in s:
            for tok in toks:
                if tok in k:
                    score += 250
                    reasons.append(f"semantic_{root}_{tok}")

    if "sg7b10" in p:
        score += 150
        reasons.append("B10_artifact")
    elif "sg7b9" in p or "sg7b11" in p:
        score += 100
        reasons.append("adjacent_B_milestone")
    elif "sg7cr" in p:
        score += 50
        reasons.append("CR_lineage")

    if rec["kind"] in {"f", "i", "u", "b"}:
        score += 50
        reasons.append("numeric")

    return score, reasons


def bind_component_symbols(symbols, inventory):
    rows = []
    bindings = {}

    for sym in sorted(set(symbols)):
        candidates = []

        for rec in inventory:
            score, reasons = score_component_binding(sym, rec)
            if score <= 0:
                continue

            candidates.append((
                score,
                rec,
                reasons,
            ))

        candidates.sort(key=lambda x: x[0], reverse=True)

        selected = None
        margin = 0

        if candidates:
            top = candidates[0]
            second_score = candidates[1][0] if len(candidates) > 1 else -999999
            margin = top[0] - second_score

            strong = (
                top[1]["key"].lower() == sym.lower()
                or top[0] >= 1000
            )

            if len(candidates) == 1 or strong or margin >= 400:
                selected = top

        for rank, (score, rec, reasons) in enumerate(candidates[:10], start=1):
            rows.append({
                "symbol": sym,
                "rank": rank,
                "artifact": str(rec["path"]),
                "key": rec["key"],
                "shape": str(rec["shape"]),
                "dtype": rec["dtype"],
                "score": score,
                "reasons": ";".join(reasons),
                "selected": bool(selected and rec["path"] == selected[1]["path"] and rec["key"] == selected[1]["key"]),
                "selection_margin": margin if rank == 1 else "",
            })

        if selected:
            bindings[sym] = selected[1]["arr"]

    return rows, bindings


class SafeEvaluator:
    """
    Restricted AST evaluator for NumPy feature-construction expressions.
    Only operations needed for deterministic array construction are permitted.
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
            val = self.eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -val
            if isinstance(node.op, ast.UAdd):
                return +val
            raise ValueError("unsupported unary op")

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
                return a / b
            if isinstance(node.op, ast.Pow):
                return a ** b

            raise ValueError("unsupported binary op")

        if isinstance(node, ast.Subscript):
            base = self.eval(node.value)

            sl = node.slice
            if isinstance(sl, ast.Constant):
                idx = sl.value
            elif isinstance(sl, ast.Tuple):
                idx = tuple(self._slice_part(x) for x in sl.elts)
            else:
                idx = self._slice_part(sl)

            return base[idx]

        if isinstance(node, ast.Attribute):
            base = self.eval(node.value)

            # Shape/dtype attributes only.
            if node.attr in {"shape", "dtype"}:
                return getattr(base, node.attr)

            raise ValueError(f"unsupported attribute: {node.attr}")

        if isinstance(node, ast.List):
            return [self.eval(x) for x in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self.eval(x) for x in node.elts)

        if isinstance(node, ast.Call):
            name = self._call_name(node)

            args = [self.eval(a) for a in node.args]
            kwargs = {
                kw.arg: self.eval(kw.value)
                for kw in node.keywords
                if kw.arg is not None
            }

            allowed = {
                "np.column_stack": np.column_stack,
                "np.stack": np.stack,
                "np.concatenate": np.concatenate,
                "np.asarray": np.asarray,
                "np.array": np.array,
                "np.full": np.full,
                "np.full_like": np.full_like,
                "np.zeros": np.zeros,
                "np.zeros_like": np.zeros_like,
                "np.ones": np.ones,
                "np.ones_like": np.ones_like,
                "np.reshape": np.reshape,
                "np.ravel": np.ravel,
                "np.repeat": np.repeat,
                "np.tile": np.tile,
                "np.clip": np.clip,
                "np.log1p": np.log1p,
                "np.log": np.log,
                "np.exp": np.exp,
                "np.sqrt": np.sqrt,
                "np.float32": np.float32,
                "np.float64": np.float64,
            }

            if name in allowed:
                return allowed[name](*args, **kwargs)

            # ndarray methods
            if isinstance(node.func, ast.Attribute):
                obj = self.eval(node.func.value)
                method = node.func.attr

                if method == "reshape":
                    return obj.reshape(*args, **kwargs)
                if method == "ravel":
                    return obj.ravel()
                if method == "astype":
                    return obj.astype(*args, **kwargs)
                if method == "flatten":
                    return obj.flatten()

            raise ValueError(f"unsupported call: {name}")

        raise ValueError(f"unsupported AST node: {type(node).__name__}")

    def _slice_part(self, node):
        if isinstance(node, ast.Slice):
            lower = self.eval(node.lower) if node.lower else None
            upper = self.eval(node.upper) if node.upper else None
            step = self.eval(node.step) if node.step else None
            return slice(lower, upper, step)
        return self.eval(node)

    def _call_name(self, node):
        cur = node.func
        parts = []
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R")
    print("Final Numeric X100 Artifact Lineage Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
""")

    sir = load_json(R26IR_SUMMARY)

    if sir.get("status") != "SG7B10_DEPLOYMENT_X100_EXECUTABLE_TENSOR_NOT_YET_UNIQUE":
        raise RuntimeError("R26I-R requires unresolved R26IR X100 binding.")

    if not AUTHORITATIVE_SOURCE.exists():
        raise FileNotFoundError(AUTHORITATIVE_SOURCE)

    text = safe_text(AUTHORITATIVE_SOURCE)
    tree = ast.parse(text)

    ordinary_map = ordinary_assignment_map(tree, text)

    # -------------------------------------------------------------------------
    # 1. Trace deployment["X100"] subscript assignments.
    # -------------------------------------------------------------------------

    subscript_rows = []
    x100_expr_nodes = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        for tgt in node.targets:
            base, key = subscript_identity(tgt)

            if base == "deployment":
                subscript_rows.append({
                    "line": node.lineno,
                    "base": base,
                    "key": key or "",
                    "rhs": node_src(text, node.value),
                    "rhs_symbols": ";".join(names_in(node.value)),
                    "is_X100": key == "X100",
                })

                if key == "X100":
                    x100_expr_nodes.append(node.value)

    save_csv(ASSIGN_TABLE, subscript_rows)

    # -------------------------------------------------------------------------
    # 2. Trace dictionary literal construction of deployment.
    # -------------------------------------------------------------------------

    dict_rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        assigns_deployment = any(
            isinstance(t, ast.Name) and t.id == "deployment"
            for t in node.targets
        )

        if not assigns_deployment or not isinstance(node.value, ast.Dict):
            continue

        for k_node, v_node in zip(node.value.keys, node.value.values):
            key = literal_string(k_node)

            dict_rows.append({
                "line": node.lineno,
                "key": key or "",
                "value_expression": node_src(text, v_node),
                "value_symbols": ";".join(names_in(v_node)),
                "is_X100": key == "X100",
            })

            if key == "X100":
                x100_expr_nodes.append(v_node)

    save_csv(DICT_TABLE, dict_rows)

    # -------------------------------------------------------------------------
    # 3. Exact X100 source expressions + recursive dependencies.
    # -------------------------------------------------------------------------

    # Deduplicate by source expression
    unique_exprs = []
    seen_expr = set()

    for node in x100_expr_nodes:
        src = node_src(text, node)

        if src and src not in seen_expr:
            seen_expr.add(src)
            unique_exprs.append(node)

    dependency_rows = []
    x100_seed_symbols = set()

    for idx, node in enumerate(unique_exprs):
        seeds = names_in(node)
        x100_seed_symbols.update(seeds)

        deps = recursive_dependencies(seeds, ordinary_map)

        dependency_rows.append({
            "expression_index": idx,
            "symbol": "<X100_EXPRESSION>",
            "assignment_line": getattr(node, "lineno", ""),
            "rhs": node_src(text, node),
            "rhs_symbols": ";".join(seeds),
        })

        for r in deps:
            dependency_rows.append({
                "expression_index": idx,
                **r,
            })

    save_csv(DEPENDENCY_TABLE, dependency_rows)

    # Symbols actually requiring persisted binding are leaves that do not have
    # an ordinary source assignment, plus semantically important array symbols.
    all_dependency_symbols = set()

    for row in dependency_rows:
        if row["symbol"] != "<X100_EXPRESSION>":
            all_dependency_symbols.add(row["symbol"])

        for s in filter(None, str(row["rhs_symbols"]).split(";")):
            all_dependency_symbols.add(s)

    leaf_symbols = {
        s for s in all_dependency_symbols
        if s not in ordinary_map
        and s not in {
            "np", "float", "int", "bool", "len", "range", "enumerate",
            "Path", "ROOT", "BATCH_SIZE",
        }
    }

    # -------------------------------------------------------------------------
    # 4. Bind leaf symbols to persisted numeric arrays.
    # -------------------------------------------------------------------------

    inventory = persisted_key_inventory()
    persisted_rows, bindings = bind_component_symbols(
        leaf_symbols,
        inventory,
    )

    save_csv(PERSISTED_TABLE, persisted_rows)

    # -------------------------------------------------------------------------
    # 5. Attempt deterministic reconstruction of X100 from source expression.
    # -------------------------------------------------------------------------

    reconstruction_rows = []
    successful = []

    # Environment starts with persisted leaf bindings.
    env = dict(bindings)
    env["np"] = np

    # Iteratively evaluate ordinary assignments when their dependencies resolve.
    unresolved = dict(ordinary_map)
    progress = True

    while progress:
        progress = False

        for sym in list(unresolved):
            rec = unresolved[sym]

            try:
                val = SafeEvaluator(env).eval(rec["rhs_node"])
            except Exception:
                continue

            # Only retain scalar or numeric ndarray values.
            if isinstance(val, np.ndarray):
                if val.dtype.kind not in {"f", "i", "u", "b", "c"}:
                    del unresolved[sym]
                    continue
            elif not np.isscalar(val):
                del unresolved[sym]
                continue

            env[sym] = val
            del unresolved[sym]
            progress = True

    for idx, node in enumerate(unique_exprs):
        expr = node_src(text, node)

        try:
            arr = SafeEvaluator(env).eval(node)
            arr = np.asarray(arr)

            numeric = arr.dtype.kind in {"f", "i", "u", "b", "c"}
            finite = bool(np.all(np.isfinite(arr))) if numeric else False
            shape_ok = (
                arr.ndim == 2
                and arr.shape[1] == 2
            )

            executable = numeric and finite and shape_ok

            reconstruction_rows.append({
                "expression_index": idx,
                "expression": expr,
                "success": True,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "numeric": numeric,
                "finite": finite,
                "model_input_shape_compatible": shape_ok,
                "executable_X100": executable,
                "failure": "",
            })

            if executable:
                successful.append((idx, expr, np.array(arr, copy=True)))

        except Exception as exc:
            reconstruction_rows.append({
                "expression_index": idx,
                "expression": expr,
                "success": False,
                "shape": "",
                "dtype": "",
                "numeric": False,
                "finite": False,
                "model_input_shape_compatible": False,
                "executable_X100": False,
                "failure": f"{type(exc).__name__}: {exc}",
            })

    save_csv(RECON_TABLE, reconstruction_rows)

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    resolved = len(successful) == 1

    if resolved:
        idx, expr, x100 = successful[0]

        status = "SG7B10_DEPLOYMENT_X100_CONSTRUCTION_CONTRACT_RESOLVED"
        diagnosis = (
            "SOURCE_LEVEL_DEPLOYMENT_X100_RECONSTRUCTS_FROM_PERSISTED_NUMERIC_COMPONENTS"
        )
        recommendation = (
            "The SG7B10 deployment['X100'] tensor is now reconstructed from its exact source "
            "expression and persisted numeric component bindings. The resulting tensor is finite, "
            "numeric, and compatible with the authoritative model input shape (*,2). Freeze this "
            "X100 artifact/key contract for the repaired 100-day runtime control. Do not permit "
            "heuristic X100 discovery or nonnumeric fallbacks."
        )
        next_milestone = (
            "V15-SG7E1R26I-R1 — Repaired Authoritative SG7B10 100-Day Runtime Control"
        )

        np.savez_compressed(
            NUMERICAL_FILE,
            X100=x100,
            expression_index=np.asarray([idx], dtype=np.int64),
            expression=np.asarray([expr]),
        )

    else:
        status = "SG7B10_DEPLOYMENT_X100_CONSTRUCTION_CONTRACT_STILL_INCOMPLETE"
        diagnosis = (
            "SOURCE_X100_EXPRESSION_OR_REQUIRED_PERSISTED_COMPONENT_BINDINGS_REMAIN_UNRESOLVED"
        )
        recommendation = (
            "Do not call model.predict. Audit only the unresolved X100 source-expression leaf "
            "symbols shown by R26I-R and bind them to their exact SG7B9/B10 persisted arrays. "
            "Do not broaden source authority or fabricate feature values."
        )
        next_milestone = (
            "V15-SG7E1R26I-R1 — Missing X100 Component Binding Audit"
        )

    selected_shape = list(successful[0][2].shape) if resolved else None
    selected_dtype = str(successful[0][2].dtype) if resolved else None

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "X100_source_expression_count": len(unique_exprs),
        "dependency_record_count": len(dependency_rows),
        "leaf_symbol_count": len(leaf_symbols),
        "persisted_binding_count": len(bindings),
        "successful_reconstruction_count": len(successful),
        "resolved": resolved,
        "selected_shape": str(selected_shape) if selected_shape else "",
        "selected_dtype": selected_dtype or "",
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(AUTHORITATIVE_SOURCE),
        "X100_source": {
            "expression_count": len(unique_exprs),
            "expressions": [node_src(text, n) for n in unique_exprs],
            "leaf_symbols": sorted(leaf_symbols),
            "persisted_bindings": sorted(bindings),
        },
        "reconstruction": {
            "resolved": resolved,
            "successful_count": len(successful),
            "shape": selected_shape,
            "dtype": selected_dtype,
            "numerical_artifact": str(NUMERICAL_FILE) if resolved else None,
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
        "milestone": "V15-SG7E1R26I-R",
        "status": status,
        "diagnosis": diagnosis,
        "X100_resolved": resolved,
        "X100_shape": selected_shape,
        "X100_dtype": selected_dtype,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("SG7B10 X100 SOURCE TRACE")
    print(f"  Subscript assignments   : {sum(1 for r in subscript_rows if r['is_X100'])}")
    print(f"  Dictionary X100 entries : {sum(1 for r in dict_rows if r['is_X100'])}")
    print(f"  Unique X100 expressions : {len(unique_exprs)}")
    print(f"  Dependency records      : {len(dependency_rows)}")
    print(f"  Leaf symbols            : {len(leaf_symbols)}")
    print(f"  Persisted bindings      : {len(bindings)}")

    print("\nX100 EXPRESSIONS")
    for idx, node in enumerate(unique_exprs):
        print(f"  [{idx}] {node_src(text, node)}")

    print("\nRECONSTRUCTION")
    for row in reconstruction_rows:
        print(
            f"  expr={row['expression_index']} | "
            f"success={row['success']} | "
            f"shape={row['shape']} | "
            f"dtype={row['dtype']} | "
            f"exec={row['executable_X100']} | "
            f"{row['failure']}"
        )

    if resolved:
        print("\nRESOLVED X100")
        print(f"  Shape                   : {successful[0][2].shape}")
        print(f"  Dtype                   : {successful[0][2].dtype}")
        print(f"  Numerical artifact      : {NUMERICAL_FILE}")

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
        ASSIGN_TABLE,
        DICT_TABLE,
        DEPENDENCY_TABLE,
        PERSISTED_TABLE,
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
    print("V15-SG7E1R26I-R FINAL NUMERIC X100 ARTIFACT LINEAGE AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No fabricated feature was used.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
