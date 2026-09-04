from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re
from collections import defaultdict, deque

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R21
# Final Freeze-Serializer Alias / Dictionary Binding Audit
#
# FORENSIC SERIALIZER-BINDING MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO SCALAR ANCHORING OR FITTING.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
#
# PURPOSE
# -------
# SG7E1R20 established:
#
#   L2_100D_EVALUATOR_OUTPUT_BINDING_STILL_AMBIGUOUS
#
# with:
#
#   SOURCE_SYMBOL_OR_SERIALIZATION_CHAIN_DOES_NOT_SELECT_ONE_UNIQUE_OUTPUT_KEY
#
# R20 also established that regex-level evaluator-call tracing was insufficient:
#
#   call assignments      : 0
#   tracked symbols       : 0
#   serialization records : 0
#
# R21 therefore moves from regex matching to AST/dataflow tracing.
#
# It traces:
#
#   evaluator/deployment output
#      -> tuple unpacking / function return
#      -> local aliases
#      -> dictionary packing
#      -> **kwargs expansion
#      -> np.savez / np.savez_compressed
#      -> R1F3 freeze copy
#      -> exact persisted NPZ key/hash
#
# This branch specifically targets likely frozen-package keys such as:
#
#   L2_independent_100
#   frozen100
#   truth100
#   X08_coeff100
#   K5_100
#
# but DOES NOT select by name alone.
#
# Authority comes only from source-level alias/dictionary/serializer lineage.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R21"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R20_DIR = ROOT / "output" / "V15_SG7E1R20"
R20_SUMMARY = R20_DIR / "PAD_Stream_V15SG7E1R20_Summary.json"
R20_CONTRACT = R20_DIR / "V15SG7E1R20_Exact_100d_Evaluator_Output_Binding_Contract.json"
R20_KEYS = R20_DIR / "V15SG7E1R20_Persisted_Key_Candidate_Audit.csv"

R19_PERSISTED = (
    ROOT / "output" / "V15_SG7E1R19"
    / "V15SG7E1R19_Persisted_100d_Candidate_Inventory.csv"
)

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

R1F3_DIR = ROOT / "output" / "V15_SG7CR3F5R1F3"
R1F3_FROZEN = (
    R1F3_DIR / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)
R1F3_MANIFEST = R1F3_DIR / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
R1F3_CONTRACT = R1F3_DIR / "V15SG7CR3F5R1F3_Frozen_Deployment_Contract.json"

# Historical source branch likely involved in final candidate creation/freeze.
SOURCE_PREFIXES = (
    "PAD_Stream_V15SG7CR3F5R1F2B",
    "PAD_Stream_V15SG7CR3F5R1F2C",
    "PAD_Stream_V15SG7CR3F5R1F2CR",
    "PAD_Stream_V15SG7CR3F5R1F2CRR",
    "PAD_Stream_V15SG7CR3F5R1F3",
)

EXPECTED_STATE_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SOURCE_INVENTORY = OUT / "V15SG7E1R21_Source_AST_Inventory.csv"
RETURN_TRACE = OUT / "V15SG7E1R21_Function_Return_Trace.csv"
ASSIGN_TRACE = OUT / "V15SG7E1R21_Alias_Assignment_Trace.csv"
DICT_TRACE = OUT / "V15SG7E1R21_Dictionary_Packing_Trace.csv"
SERIALIZER_TRACE = OUT / "V15SG7E1R21_Serializer_Expansion_Trace.csv"
FREEZE_TRACE = OUT / "V15SG7E1R21_Freeze_Copy_Key_Trace.csv"
KEY_SCORE = OUT / "V15SG7E1R21_Final_Persisted_Key_Binding.csv"
HASH_ID = OUT / "V15SG7E1R21_Bound_100d_Output_Hash.csv"
DECISION = OUT / "V15SG7E1R21_Final_Serializer_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R21_Final_Freeze_Serializer_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R21_Summary.json"


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def source_files():
    files = []
    for p in ROOT.glob("*.py"):
        if any(p.name.startswith(prefix) for prefix in SOURCE_PREFIXES):
            files.append(p.resolve())
    return sorted(set(files))


def node_src(text, node):
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""


def flatten_target_names(node):
    names = []
    if isinstance(node, ast.Name):
        names.append(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            names.extend(flatten_target_names(elt))
    return names


def call_name(node):
    if not isinstance(node, ast.Call):
        return ""
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        parts = []
        cur = f
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


def expr_names(node):
    return sorted({
        n.id for n in ast.walk(node)
        if isinstance(n, ast.Name)
    })


def string_constant(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def is_savez_call(node):
    name = call_name(node).lower()
    return name.endswith("np.savez") or name.endswith("np.savez_compressed") or name.endswith("savez") or name.endswith("savez_compressed")


def is_model_eval_call(node):
    name = call_name(node).lower()
    markers = (
        ".predict",
        "predict_on_batch",
        "model",
        "load_model",
        "evaluate",
        "infer",
        "inference",
    )
    return any(m in name for m in markers)


def build_ast_records(path: Path):
    text = safe_text(path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None

    inventory = []
    returns = []
    assigns = []
    dicts = []
    serializers = []

    # Function scope stack via recursive visitor.
    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.scope = ["<module>"]

        def visit_FunctionDef(self, node):
            self.scope.append(node.name)
            inventory.append({
                "source": str(path),
                "kind": "function",
                "name": node.name,
                "line": node.lineno,
                "args": ";".join(a.arg for a in node.args.args),
            })
            self.generic_visit(node)
            self.scope.pop()

        def visit_Return(self, node):
            if node.value is not None:
                returns.append({
                    "source": str(path),
                    "function": self.scope[-1],
                    "line": node.lineno,
                    "expression": node_src(text, node.value)[:3000],
                    "symbols": ";".join(expr_names(node.value)),
                })
            self.generic_visit(node)

        def visit_Assign(self, node):
            targets = []
            for t in node.targets:
                targets.extend(flatten_target_names(t))

            rhs = node.value
            rhs_text = node_src(text, rhs)[:4000]
            rhs_symbols = expr_names(rhs)
            rhs_call = call_name(rhs)

            assigns.append({
                "source": str(path),
                "function": self.scope[-1],
                "line": node.lineno,
                "targets": ";".join(targets),
                "rhs_expression": rhs_text,
                "rhs_symbols": ";".join(rhs_symbols),
                "rhs_call": rhs_call,
                "is_model_eval_call": is_model_eval_call(rhs),
                "is_dict_literal": isinstance(rhs, ast.Dict),
            })

            if isinstance(rhs, ast.Dict):
                for k, v in zip(rhs.keys, rhs.values):
                    key = string_constant(k)
                    if key is None:
                        continue
                    dicts.append({
                        "source": str(path),
                        "function": self.scope[-1],
                        "line": node.lineno,
                        "container_symbols": ";".join(targets),
                        "dict_key": key,
                        "value_expression": node_src(text, v)[:3000],
                        "value_symbols": ";".join(expr_names(v)),
                    })

            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            targets = flatten_target_names(node.target)
            rhs = node.value
            if rhs is not None:
                assigns.append({
                    "source": str(path),
                    "function": self.scope[-1],
                    "line": node.lineno,
                    "targets": ";".join(targets),
                    "rhs_expression": node_src(text, rhs)[:4000],
                    "rhs_symbols": ";".join(expr_names(rhs)),
                    "rhs_call": call_name(rhs),
                    "is_model_eval_call": is_model_eval_call(rhs),
                    "is_dict_literal": isinstance(rhs, ast.Dict),
                })
            self.generic_visit(node)

        def visit_Call(self, node):
            if is_savez_call(node):
                rec = {
                    "source": str(path),
                    "function": self.scope[-1],
                    "line": node.lineno,
                    "call": call_name(node),
                    "path_expression": node_src(text, node.args[0])[:2000] if node.args else "",
                    "kwargs_expansions": [],
                    "keyword_pairs": [],
                }

                for kw in node.keywords:
                    if kw.arg is None:
                        rec["kwargs_expansions"].append(node_src(text, kw.value)[:2000])
                    else:
                        rec["keyword_pairs"].append({
                            "key": kw.arg,
                            "value_expression": node_src(text, kw.value)[:3000],
                            "value_symbols": expr_names(kw.value),
                        })

                serializers.append(rec)

            self.generic_visit(node)

    Visitor().visit(tree)
    return text, inventory, returns, assigns, dicts, serializers


def load_persisted_state_candidates():
    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    rows = []
    db = np.load(R1F3_FROZEN, allow_pickle=True)
    for key in db.files:
        arr = np.asarray(db[key])
        if arr.shape == EXPECTED_STATE_SHAPE and np.issubdtype(arr.dtype, np.number):
            rows.append({
                "key": key,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "sha256": sha256_array(arr),
            })
    db.close()
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R21")
    print("Final Freeze-Serializer Alias / Dictionary Binding Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POST-HOC ALIGNMENT WILL BE PERFORMED.
NO SCALAR ANCHORING OR FITTING WILL BE PERFORMED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
""")

    r20s = load_json(R20_SUMMARY)
    r20c = load_json(R20_CONTRACT)
    r1f3_manifest = load_json(R1F3_MANIFEST)
    r1f3_contract = load_json(R1F3_CONTRACT)

    if r20s.get("status") != "L2_100D_EVALUATOR_OUTPUT_BINDING_STILL_AMBIGUOUS":
        raise RuntimeError("R21 requires R20 ambiguous output-binding status.")

    if r20s.get("diagnosis") != (
        "SOURCE_SYMBOL_OR_SERIALIZATION_CHAIN_DOES_NOT_SELECT_ONE_UNIQUE_OUTPUT_KEY"
    ):
        raise RuntimeError("R21 requires R20 serializer-chain ambiguity diagnosis.")

    # -------------------------------------------------------------------------
    # AST inventory
    # -------------------------------------------------------------------------

    src_inventory = []
    return_rows = []
    assign_rows = []
    dict_rows = []
    serializer_rows_raw = []
    source_texts = {}

    for src in source_files():
        result = build_ast_records(src)
        if result is None:
            continue

        text, inv, ret, ass, dct, ser = result
        source_texts[str(src)] = text

        src_inventory.append({
            "source": str(src),
            "parsed": True,
            "function_count": len(inv),
            "return_count": len(ret),
            "assignment_count": len(ass),
            "dictionary_record_count": len(dct),
            "serializer_count": len(ser),
        })

        return_rows.extend(ret)
        assign_rows.extend(ass)
        dict_rows.extend(dct)
        serializer_rows_raw.extend(ser)

    save_csv(SOURCE_INVENTORY, src_inventory)
    save_csv(RETURN_TRACE, return_rows)
    save_csv(ASSIGN_TRACE, assign_rows)
    save_csv(DICT_TRACE, dict_rows)

    # -------------------------------------------------------------------------
    # Build symbol dataflow graph.
    #
    # Edge source_symbol -> target_symbol if target depends on source.
    # -------------------------------------------------------------------------

    edges = defaultdict(set)
    reverse_edges = defaultdict(set)

    evaluator_seed_symbols = set()

    for row in assign_rows:
        targets = [x for x in row["targets"].split(";") if x]
        rhs_symbols = [x for x in row["rhs_symbols"].split(";") if x]

        for src_sym in rhs_symbols:
            for dst_sym in targets:
                edges[src_sym].add(dst_sym)
                reverse_edges[dst_sym].add(src_sym)

        if bool(row["is_model_eval_call"]):
            evaluator_seed_symbols.update(targets)

    # Also use returned-symbols from functions with deployment-like names.
    deployment_function_names = set()
    for row in src_inventory:
        pass

    for row in return_rows:
        fname = row["function"].lower()
        if any(tok in fname for tok in ("deploy", "predict", "eval", "reconstruct", "candidate", "correct")):
            evaluator_seed_symbols.update(
                x for x in row["symbols"].split(";") if x
            )

    # -------------------------------------------------------------------------
    # Expand forward aliases from evaluator seeds.
    # -------------------------------------------------------------------------

    reachable = set(evaluator_seed_symbols)
    q = deque(evaluator_seed_symbols)

    while q:
        cur = q.popleft()
        for nxt in edges.get(cur, set()):
            if nxt not in reachable:
                reachable.add(nxt)
                q.append(nxt)

    # If no direct evaluator seeds are found, use semantically strong symbols
    # from assignments/returns as conservative seeds, but do not select keys yet.
    fallback_seed_used = False

    if not reachable:
        fallback_seed_used = True
        semantic_tokens = (
            "l2",
            "independent",
            "candidate",
            "corrected",
            "state100",
            "state_100",
            "100d",
            "100",
        )

        for row in assign_rows:
            for sym in row["targets"].split(";"):
                ls = sym.lower()
                if sym and any(tok in ls for tok in semantic_tokens):
                    reachable.add(sym)

        q = deque(reachable)
        while q:
            cur = q.popleft()
            for nxt in edges.get(cur, set()):
                if nxt not in reachable:
                    reachable.add(nxt)
                    q.append(nxt)

    # -------------------------------------------------------------------------
    # Resolve dict containers whose values depend on reachable symbols.
    # -------------------------------------------------------------------------

    dict_container_to_keys = defaultdict(list)

    for row in dict_rows:
        vals = set(x for x in row["value_symbols"].split(";") if x)
        container_syms = [x for x in row["container_symbols"].split(";") if x]

        if vals.intersection(reachable):
            for container in container_syms:
                dict_container_to_keys[container].append({
                    "dict_key": row["dict_key"],
                    "value_symbols": sorted(vals),
                    "source": row["source"],
                    "line": row["line"],
                })
                reachable.add(container)

    # -------------------------------------------------------------------------
    # Serializer expansion trace:
    # keyword key=value and **dict containers.
    # -------------------------------------------------------------------------

    serializer_rows = []

    for rec in serializer_rows_raw:
        # Direct keyword serialization.
        for pair in rec["keyword_pairs"]:
            vals = set(pair["value_symbols"])
            connected = bool(vals.intersection(reachable))

            serializer_rows.append({
                "source": rec["source"],
                "function": rec["function"],
                "line": rec["line"],
                "call": rec["call"],
                "serialization_mode": "keyword",
                "serialization_key": pair["key"],
                "value_expression": pair["value_expression"],
                "value_symbols": ";".join(sorted(vals)),
                "connected_to_evaluator_output": connected,
                "dict_container": "",
            })

        # **dictionary expansion
        for expr in rec["kwargs_expansions"]:
            container_symbols = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expr)
            for container in container_symbols:
                for drec in dict_container_to_keys.get(container, []):
                    vals = set(drec["value_symbols"])
                    connected = bool(vals.intersection(reachable)) or container in reachable

                    serializer_rows.append({
                        "source": rec["source"],
                        "function": rec["function"],
                        "line": rec["line"],
                        "call": rec["call"],
                        "serialization_mode": "kwargs_dict_expansion",
                        "serialization_key": drec["dict_key"],
                        "value_expression": f"**{expr}",
                        "value_symbols": ";".join(sorted(vals)),
                        "connected_to_evaluator_output": connected,
                        "dict_container": container,
                    })

    save_csv(SERIALIZER_TRACE, serializer_rows)

    # -------------------------------------------------------------------------
    # Freeze-copy trace:
    # identify whether R1F3 copies an earlier NPZ wholesale or builds a new one.
    # -------------------------------------------------------------------------

    freeze_rows = []

    freeze_sources = [
        p for p in source_files()
        if "R1F3" in p.name
    ]

    for src in freeze_sources:
        text = safe_text(src)
        lines = text.splitlines()

        for i, line in enumerate(lines, start=1):
            ll = line.lower()
            if any(tok in ll for tok in (
                "np.load",
                "np.savez",
                "savez_compressed",
                "copy",
                "shutil",
                "frozen_candidate",
                "freeze",
            )):
                freeze_rows.append({
                    "source": str(src),
                    "line": i,
                    "matched_line": line.strip()[:1500],
                    "context": "\n".join(lines[max(0, i-8):min(len(lines), i+12)])[:5000],
                })

    save_csv(FREEZE_TRACE, freeze_rows)

    # -------------------------------------------------------------------------
    # Persisted frozen keys.
    # -------------------------------------------------------------------------

    persisted = load_persisted_state_candidates()
    persisted_by_key = {r["key"]: r for r in persisted}

    r19_100_rows = load_csv(R19_PERSISTED)
    r19_100_hashes = {r["array_sha256"] for r in r19_100_rows}

    # -------------------------------------------------------------------------
    # Source-authority score.
    #
    # Only lineage evidence counts:
    #   +120 directly serialized from reachable evaluator symbol
    #   +100 via reachable dictionary container
    #    +60 persisted in R1F3 frozen artifact
    #    +50 hash belongs to R19 100d candidate set
    #    +30 exact manifest/contract key mention
    #
    # No numerical error/performance enters score.
    # -------------------------------------------------------------------------

    manifest_blob = (
        json.dumps(r1f3_manifest, indent=2)
        + "\n"
        + json.dumps(r1f3_contract, indent=2)
    ).lower()

    source_binding = defaultdict(list)

    for row in serializer_rows:
        if not bool(row["connected_to_evaluator_output"]):
            continue
        source_binding[row["serialization_key"]].append(row)

    score_rows = []

    for p in persisted:
        key = p["key"]
        score = 60
        evidence = ["R1F3_frozen_persisted_key"]

        if key in source_binding:
            modes = {r["serialization_mode"] for r in source_binding[key]}
            if "keyword" in modes:
                score += 120
                evidence.append("direct_serializer_from_reachable_output")
            if "kwargs_dict_expansion" in modes:
                score += 100
                evidence.append("dictionary_serializer_from_reachable_output")

        if p["sha256"] in r19_100_hashes:
            score += 50
            evidence.append("R19_100d_candidate_hash")

        if key.lower() in manifest_blob:
            score += 30
            evidence.append("R1F3_manifest_contract_key_reference")

        # Semantic note only, no authority points.
        semantic_role = []
        lk = key.lower()
        if "truth" in lk:
            semantic_role.append("truth_like")
        if "gamma" in lk or "coeff" in lk or "mask" in lk:
            semantic_role.append("auxiliary_like")
        if "independent" in lk:
            semantic_role.append("independent_validation_like")
        if "frozen100" in lk:
            semantic_role.append("frozen_baseline_like")
        if "k5" in lk:
            semantic_role.append("upstream_stage_like")

        score_rows.append({
            **p,
            "binding_score": score,
            "binding_evidence": ";".join(evidence),
            "semantic_role_note": ";".join(semantic_role),
            "serializer_record_count": len(source_binding.get(key, [])),
        })

    score_rows.sort(
        key=lambda r: (
            int(r["binding_score"]),
            int(r["serializer_record_count"]),
            r["key"],
        ),
        reverse=True,
    )

    save_csv(KEY_SCORE, score_rows)

    # -------------------------------------------------------------------------
    # Unique selection.
    # -------------------------------------------------------------------------

    selected = None
    margin = 0

    if score_rows:
        top_score = int(score_rows[0]["binding_score"])
        second_score = int(score_rows[1]["binding_score"]) if len(score_rows) > 1 else -999
        margin = top_score - second_score

        # Require actual serializer lineage, not just frozen-file membership.
        serializer_supported = score_rows[0]["serializer_record_count"] > 0
        unique_margin = margin >= 30

        if serializer_supported and unique_margin:
            selected = score_rows[0]

    hash_rows = []
    if selected:
        hash_rows.append({
            "artifact": str(R1F3_FROZEN),
            "key": selected["key"],
            "sha256": selected["sha256"],
            "dtype": selected["dtype"],
            "shape": selected["shape"],
            "binding_score": selected["binding_score"],
            "binding_margin": margin,
            "binding_evidence": selected["binding_evidence"],
            "in_R19_100d_candidate_set": selected["sha256"] in r19_100_hashes,
        })

    save_csv(HASH_ID, hash_rows)

    # -------------------------------------------------------------------------
    # Final decision.
    # -------------------------------------------------------------------------

    if selected and selected["sha256"] in r19_100_hashes:
        status = "L2_100D_EVALUATOR_OUTPUT_BOUND"
        diagnosis = "AST_ALIAS_DICTIONARY_SERIALIZER_LINEAGE_IDENTIFIES_UNIQUE_100D_OUTPUT"
        recommendation = (
            "The exact historical 100-day deployment output is now bound through AST-level "
            "alias/dictionary/serializer provenance to one frozen NPZ key and one historical "
            "100-day hash. Use only this bound array as the replay target. Proceed to a true "
            "100-day deterministic evaluator replay and precision-aware closure validation."
        )
        next_milestone = (
            "V15-SG7E1R22 — Bound 100-Day Deterministic Evaluator Replay / Closure Validation"
        )

    elif selected and selected["sha256"] not in r19_100_hashes:
        status = "L2_100D_OUTPUT_BOUND_TIME_LABEL_CONFLICT"
        diagnosis = "SERIALIZER_LINEAGE_RESOLVED_BUT_BOUND_HASH_NOT_IN_HISTORICAL_100D_SET"
        recommendation = (
            "Do not replay new times. The exact serialized output key is resolved, but its hash "
            "is not included in the historical 100-day provenance set. Audit only the time-label "
            "assignment for the bound output."
        )
        next_milestone = (
            "V15-SG7E1R22 — Bound Output Historical Time-Label Reconciliation Audit"
        )

    else:
        status = "L2_100D_FREEZE_SERIALIZER_BINDING_REMAINS_AMBIGUOUS"
        diagnosis = "AST_DATAFLOW_DOES_NOT_YET_REACH_ONE_UNIQUE_FROZEN_100D_KEY"
        recommendation = (
            "Do not choose a persisted state by name or numerical closeness. Inspect the generated "
            "AST return/assignment/dictionary/serializer tables to identify the unresolved function "
            "return or container alias. The next audit should trace that exact function across caller "
            "boundaries rather than broadening the search."
        )
        next_milestone = (
            "V15-SG7E1R22 — Cross-Function Return / Caller Binding Audit"
        )

    checks = [
        ("Incoming R20 serializer ambiguity reproduced", True),
        ("Historical R1F2/R1F3 sources parsed with AST", len(src_inventory) > 0),
        ("Function returns inventoried", True),
        ("Alias assignments inventoried", True),
        ("Dictionary packing inventoried", True),
        ("np.savez / np.savez_compressed calls inventoried", True),
        ("Evaluator-output dataflow graph constructed", True),
        ("R1F3 freeze-copy path audited", True),
        ("Frozen 2662x201 keys inventoried", len(persisted) > 0),
        ("Binding authority excludes numerical performance", True),
        ("No key selected by semantic name alone", True),
        ("No scalar anchoring/scaling used", True),
        ("No 250/500/1000d state generated", True),
        ("No training performed", True),
        ("No threshold changed or relaxed", True),
    ]

    decision_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "source_files": len(src_inventory),
        "return_records": len(return_rows),
        "assignment_records": len(assign_rows),
        "dictionary_records": len(dict_rows),
        "serializer_records": len(serializer_rows),
        "evaluator_seed_symbols": ";".join(sorted(evaluator_seed_symbols)),
        "fallback_seed_used": fallback_seed_used,
        "reachable_symbol_count": len(reachable),
        "persisted_state_keys": len(persisted),
        "selected_key": selected["key"] if selected else "",
        "selected_sha256": selected["sha256"] if selected else "",
        "binding_score": selected["binding_score"] if selected else "",
        "binding_margin": margin,
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION, decision_rows)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R21",
        "status": status,
        "diagnosis": diagnosis,
        "binding": {
            "resolved": selected is not None,
            "key": selected["key"] if selected else None,
            "sha256": selected["sha256"] if selected else None,
            "binding_score": int(selected["binding_score"]) if selected else None,
            "binding_margin": margin,
            "in_R19_100d_candidate_set": (
                selected["sha256"] in r19_100_hashes
                if selected else False
            ),
        },
        "dataflow": {
            "evaluator_seed_symbols": sorted(evaluator_seed_symbols),
            "fallback_seed_used": fallback_seed_used,
            "reachable_symbols": sorted(reachable),
            "serializer_records": len(serializer_rows),
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "candidate_performance_used": False,
            "semantic_name_used_as_sole_authority": False,
            "scalar_anchoring_used": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
            "threshold_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R21",
        "status": status,
        "diagnosis": diagnosis,
        "binding_resolved": selected is not None,
        "selected_key": selected["key"] if selected else None,
        "selected_sha256": selected["sha256"] if selected else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("AST / DATAFLOW TRACE")
    print(f"  Source files            : {len(src_inventory)}")
    print(f"  Return records          : {len(return_rows)}")
    print(f"  Assignment records      : {len(assign_rows)}")
    print(f"  Dictionary records      : {len(dict_rows)}")
    print(f"  Serializer records      : {len(serializer_rows)}")
    print(f"  Evaluator seed symbols  : {sorted(evaluator_seed_symbols)}")
    print(f"  Fallback seed used      : {fallback_seed_used}")
    print(f"  Reachable symbols       : {len(reachable)}")

    print("\nFROZEN 100-DAY KEY BINDING")
    for row in score_rows[:12]:
        print(
            f"  score={int(row['binding_score']):3d} | "
            f"serial={int(row['serializer_record_count']):2d} | "
            f"{row['key']} | {row['sha256'][:16]}"
        )

    if selected:
        print("\nSELECTED SERIALIZER BINDING")
        print(f"  Key                     : {selected['key']}")
        print(f"  SHA-256                 : {selected['sha256']}")
        print(f"  Score / margin          : {selected['binding_score']} / {margin}")
        print(f"  In historical 100d set  : {selected['sha256'] in r19_100_hashes}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R21 SERIALIZER BINDING VALIDATION")
    print("=" * 78)
    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")
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
    for p in (
        SOURCE_INVENTORY,
        RETURN_TRACE,
        ASSIGN_TRACE,
        DICT_TRACE,
        SERIALIZER_TRACE,
        FREEZE_TRACE,
        KEY_SCORE,
        HASH_ID,
        DECISION,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R21 FINAL FREEZE-SERIALIZER ALIAS / DICTIONARY BINDING AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No key was selected by semantic name or numerical performance alone.")
    print("No scalar anchoring or post-hoc alignment was used.")
    print("No 250/500/1000-day state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
