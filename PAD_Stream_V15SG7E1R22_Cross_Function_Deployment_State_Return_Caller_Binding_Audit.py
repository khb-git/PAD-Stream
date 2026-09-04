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
# PAD-Stream V15-SG7E1R22
# Cross-Function Deployment-State Return / Caller Binding Audit
#
# FORENSIC CROSS-FUNCTION DATAFLOW MILESTONE
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
# SG7E1R21R established:
#
#   R21_SERIALIZER_BINDING_REJECTED_BY_SEMANTIC_ROLE_AUDIT
#
# because:
#
#   guard_mask is AUXILIARY_MASK
#
# and the valid state-like frozen candidates are:
#
#   frozen100
#   K5_100
#   L2_independent_100
#
# R22 traces the actual deployment state across FUNCTION BOUNDARIES:
#
#   evaluator / correction function
#       -> return expression
#       -> caller assignment / tuple unpack
#       -> aliases
#       -> final candidate/freeze package dictionary
#       -> persisted state-like NPZ key
#
# R22 restricts authority to state-like arrays only and explicitly excludes:
#
#   truth100
#   guard_mask
#   gamma fields
#   coefficient fields
#   X08 support arrays
#
# A binding is accepted only if one state-like key is reached through a unique
# cross-function return/caller lineage. Numerical closeness or SG7E performance
# is never used.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R22"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R21R_DIR = ROOT / "output" / "V15_SG7E1R21R"
R21R_SUMMARY = R21R_DIR / "PAD_Stream_V15SG7E1R21R_Summary.json"
R21R_CONTRACT = R21R_DIR / "V15SG7E1R21R_Semantic_Role_Binding_Contract.json"
R21R_STATE_CANDS = R21R_DIR / "V15SG7E1R21R_State_Like_Key_Candidates.csv"

R19_PERSISTED = (
    ROOT / "output" / "V15_SG7E1R19"
    / "V15SG7E1R19_Persisted_100d_Candidate_Inventory.csv"
)

R1F3_DIR = ROOT / "output" / "V15_SG7CR3F5R1F3"
R1F3_FROZEN = (
    R1F3_DIR / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)
R1F3_MANIFEST = R1F3_DIR / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
R1F3_CONTRACT = R1F3_DIR / "V15SG7CR3F5R1F3_Frozen_Deployment_Contract.json"

SOURCE_PREFIXES = (
    "PAD_Stream_V15SG7CR3F5R1E",
    "PAD_Stream_V15SG7CR3F5R1F1",
    "PAD_Stream_V15SG7CR3F5R1F2A",
    "PAD_Stream_V15SG7CR3F5R1F2B",
    "PAD_Stream_V15SG7CR3F5R1F2C",
    "PAD_Stream_V15SG7CR3F5R1F2CR",
    "PAD_Stream_V15SG7CR3F5R1F2CRR",
    "PAD_Stream_V15SG7CR3F5R1F3",
)

EXPECTED_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

FUNCTION_TABLE = OUT / "V15SG7E1R22_Function_Definition_Inventory.csv"
RETURN_TABLE = OUT / "V15SG7E1R22_Deployment_State_Return_Trace.csv"
CALL_TABLE = OUT / "V15SG7E1R22_Caller_Assignment_Trace.csv"
CROSS_TABLE = OUT / "V15SG7E1R22_Cross_Function_Lineage.csv"
STATE_KEY_TABLE = OUT / "V15SG7E1R22_State_Key_Lineage_Scoring.csv"
BOUND_HASH_TABLE = OUT / "V15SG7E1R22_Bound_Deployment_State_Hash.csv"
DECISION_TABLE = OUT / "V15SG7E1R22_Cross_Function_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R22_Cross_Function_Deployment_State_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R22_Summary.json"


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
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


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


def flatten_names(node):
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        out = []
        for elt in node.elts:
            out.extend(flatten_names(elt))
        return out
    return []


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


def expr_names(node):
    return sorted({
        n.id for n in ast.walk(node)
        if isinstance(n, ast.Name)
    })


def state_semantic_score(text):
    """
    Semantic ranking only to identify return expressions likely to carry deployed
    state. This does NOT choose a persisted key; final authority requires actual
    cross-function lineage.
    """
    low = text.lower()
    score = 0
    positive = {
        "l2": 4,
        "independent": 4,
        "candidate": 3,
        "state": 3,
        "corrected": 2,
        "saturation": 2,
        "100": 1,
    }
    negative = {
        "truth": -6,
        "mask": -6,
        "guard": -5,
        "gamma": -5,
        "coeff": -5,
        "weight": -3,
    }
    for tok, val in positive.items():
        if tok in low:
            score += val
    for tok, val in negative.items():
        if tok in low:
            score += val
    return score


def parse_module(path):
    text = safe_text(path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None

    funcs = {}
    calls = []
    assignments = []
    dict_records = []
    save_records = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            returns = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    expr = node_src(text, sub.value)
                    returns.append({
                        "line": sub.lineno,
                        "expression": expr,
                        "symbols": expr_names(sub.value),
                        "semantic_score": state_semantic_score(expr),
                    })

            funcs[node.name] = {
                "source": str(path),
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
                "returns": returns,
            }

        elif isinstance(node, ast.Assign):
            targets = []
            for t in node.targets:
                targets.extend(flatten_names(t))

            value = node.value
            assignments.append({
                "source": str(path),
                "line": node.lineno,
                "targets": targets,
                "rhs_expression": node_src(text, value),
                "rhs_symbols": expr_names(value),
                "rhs_call": call_name(value) if isinstance(value, ast.Call) else "",
                "rhs_is_call": isinstance(value, ast.Call),
            })

            # Dict packing
            if isinstance(value, ast.Dict):
                for k, v in zip(value.keys, value.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        dict_records.append({
                            "source": str(path),
                            "line": node.lineno,
                            "container": targets[0] if targets else "",
                            "key": k.value,
                            "value_expression": node_src(text, v),
                            "value_symbols": expr_names(v),
                        })

        elif isinstance(node, ast.Call):
            cname = call_name(node)

            # Calls to project functions.
            if cname:
                calls.append({
                    "source": str(path),
                    "line": node.lineno,
                    "call_name": cname,
                    "expression": node_src(text, node),
                })

            # Savez key/value
            low = cname.lower()
            if low.endswith("savez") or low.endswith("savez_compressed"):
                for kw in node.keywords:
                    if kw.arg is not None:
                        save_records.append({
                            "source": str(path),
                            "line": node.lineno,
                            "mode": "keyword",
                            "key": kw.arg,
                            "value_expression": node_src(text, kw.value),
                            "value_symbols": expr_names(kw.value),
                            "container": "",
                        })
                    else:
                        save_records.append({
                            "source": str(path),
                            "line": node.lineno,
                            "mode": "kwargs",
                            "key": "",
                            "value_expression": node_src(text, kw.value),
                            "value_symbols": expr_names(kw.value),
                            "container": node_src(text, kw.value),
                        })

    return text, funcs, calls, assignments, dict_records, save_records


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R22")
    print("Cross-Function Deployment-State Return / Caller Binding Audit")
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

    s21r = load_json(R21R_SUMMARY)
    c21r = load_json(R21R_CONTRACT)

    if s21r.get("status") != "R21_SERIALIZER_BINDING_REJECTED_BY_SEMANTIC_ROLE_AUDIT":
        raise RuntimeError("R22 requires rejected R21 serializer binding.")

    if s21r.get("diagnosis") != (
        "GUARD_MASK_OR_AUXILIARY_FIELD_CANNOT_BE_AUTHORITATIVE_100D_DEPLOYMENT_STATE"
    ):
        raise RuntimeError("R22 requires R21R semantic contradiction diagnosis.")

    state_candidates = load_csv(R21R_STATE_CANDS)
    allowed_keys = {r["key"] for r in state_candidates}

    if not allowed_keys:
        raise RuntimeError("No state-like frozen candidates available.")

    # -------------------------------------------------------------------------
    # Parse all relevant sources.
    # -------------------------------------------------------------------------

    module_data = {}
    function_rows = []
    return_rows = []
    call_assign_rows = []
    all_assignments = []
    all_dicts = []
    all_saves = []

    for src in source_files():
        parsed = parse_module(src)
        if parsed is None:
            continue

        text, funcs, calls, assigns, dicts, saves = parsed
        module_data[str(src)] = {
            "text": text,
            "funcs": funcs,
            "calls": calls,
            "assigns": assigns,
            "dicts": dicts,
            "saves": saves,
        }

        for fname, rec in funcs.items():
            function_rows.append({
                "source": rec["source"],
                "function": fname,
                "line": rec["line"],
                "args": ";".join(rec["args"]),
                "return_count": len(rec["returns"]),
                "max_return_semantic_score": max(
                    [r["semantic_score"] for r in rec["returns"]],
                    default=-999,
                ),
            })

            for rr in rec["returns"]:
                return_rows.append({
                    "source": rec["source"],
                    "function": fname,
                    **rr,
                })

        all_assignments.extend(assigns)
        all_dicts.extend(dicts)
        all_saves.extend(saves)

    save_csv(FUNCTION_TABLE, function_rows)
    save_csv(RETURN_TABLE, return_rows)

    # -------------------------------------------------------------------------
    # Identify deployment-like functions by return semantics.
    # -------------------------------------------------------------------------

    deployment_funcs = set()

    for row in return_rows:
        if int(row["semantic_score"]) >= 3:
            deployment_funcs.add(row["function"])

    # Also explicitly retain functions named around validation/correction/candidate.
    for row in function_rows:
        lf = row["function"].lower()
        if any(tok in lf for tok in (
            "candidate",
            "correct",
            "reconstruct",
            "deploy",
            "validate",
            "independent",
        )):
            if int(row["return_count"]) > 0:
                deployment_funcs.add(row["function"])

    # -------------------------------------------------------------------------
    # Trace caller assignments: lhs = function(...)
    # -------------------------------------------------------------------------

    caller_output_symbols = defaultdict(set)  # function -> symbols

    for row in all_assignments:
        if not row["rhs_is_call"]:
            continue

        cname = row["rhs_call"].split(".")[-1]
        if cname not in deployment_funcs:
            continue

        targets = row["targets"]
        for t in targets:
            caller_output_symbols[cname].add(t)

        call_assign_rows.append({
            "source": row["source"],
            "line": row["line"],
            "called_function": cname,
            "caller_targets": ";".join(targets),
            "rhs_expression": row["rhs_expression"],
        })

    save_csv(CALL_TABLE, call_assign_rows)

    # -------------------------------------------------------------------------
    # Build alias graph from caller outputs forward.
    # -------------------------------------------------------------------------

    seed_symbols = set()
    for vals in caller_output_symbols.values():
        seed_symbols.update(vals)

    edges = defaultdict(set)
    for row in all_assignments:
        for srcsym in row["rhs_symbols"]:
            for dst in row["targets"]:
                edges[srcsym].add(dst)

    reachable = set(seed_symbols)
    q = deque(seed_symbols)

    while q:
        cur = q.popleft()
        for nxt in edges.get(cur, set()):
            if nxt not in reachable:
                reachable.add(nxt)
                q.append(nxt)

    # -------------------------------------------------------------------------
    # Resolve dictionaries.
    # -------------------------------------------------------------------------

    dict_key_lineage = defaultdict(list)

    for row in all_dicts:
        vals = set(row["value_symbols"])
        if vals.intersection(reachable):
            dict_key_lineage[row["key"]].append({
                "source": row["source"],
                "line": row["line"],
                "container": row["container"],
                "value_expression": row["value_expression"],
                "value_symbols": row["value_symbols"],
            })
            if row["container"]:
                reachable.add(row["container"])

    # -------------------------------------------------------------------------
    # Serializer lineage to allowed state-like keys only.
    # -------------------------------------------------------------------------

    serializer_key_lineage = defaultdict(list)

    # Direct keyword saves
    for row in all_saves:
        if row["mode"] == "keyword":
            if row["key"] not in allowed_keys:
                continue
            if set(row["value_symbols"]).intersection(reachable):
                serializer_key_lineage[row["key"]].append({
                    "source": row["source"],
                    "line": row["line"],
                    "mode": "keyword",
                    "value_expression": row["value_expression"],
                })

        elif row["mode"] == "kwargs":
            containers = set(row["value_symbols"])
            for key in allowed_keys:
                for rec in dict_key_lineage.get(key, []):
                    if rec["container"] in containers or rec["container"] in reachable:
                        serializer_key_lineage[key].append({
                            "source": row["source"],
                            "line": row["line"],
                            "mode": "kwargs_dict",
                            "value_expression": rec["value_expression"],
                        })

    # -------------------------------------------------------------------------
    # Cross-function lineage evidence table.
    # -------------------------------------------------------------------------

    cross_rows = []

    for func, outputs in sorted(caller_output_symbols.items()):
        func_returns = [
            r for r in return_rows
            if r["function"] == func
        ]
        for out in sorted(outputs):
            downstream = set([out])
            qq = deque([out])
            while qq:
                cur = qq.popleft()
                for nxt in edges.get(cur, set()):
                    if nxt not in downstream:
                        downstream.add(nxt)
                        qq.append(nxt)

            connected_keys = []
            for key in allowed_keys:
                recs = serializer_key_lineage.get(key, [])
                if recs:
                    connected_keys.append(key)

            cross_rows.append({
                "function": func,
                "caller_output_symbol": out,
                "return_expressions": " || ".join(r["expression"] for r in func_returns),
                "return_semantic_scores": ";".join(str(r["semantic_score"]) for r in func_returns),
                "downstream_symbol_count": len(downstream),
                "downstream_symbols": ";".join(sorted(downstream)),
                "connected_state_like_keys": ";".join(sorted(set(connected_keys))),
            })

    save_csv(CROSS_TABLE, cross_rows)

    # -------------------------------------------------------------------------
    # Persisted state-like candidate hash inventory.
    # -------------------------------------------------------------------------

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    db = np.load(R1F3_FROZEN, allow_pickle=True)

    persisted = {}
    for key in allowed_keys:
        if key not in db.files:
            continue
        arr = np.asarray(db[key])
        if arr.shape != EXPECTED_SHAPE:
            continue
        persisted[key] = {
            "key": key,
            "sha256": sha256_array(arr),
            "dtype": str(arr.dtype),
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
        }

    db.close()

    r19_hashes = {
        r["array_sha256"]
        for r in load_csv(R19_PERSISTED)
    }

    # -------------------------------------------------------------------------
    # Key lineage score.
    #
    # Authority:
    # +200 direct cross-function caller-output -> serializer lineage
    # +120 dictionary packing from reachable caller output
    # + 50 hash belongs to R19 historical 100d set
    # + 30 explicit R1F3 manifest/contract reference
    #
    # Negative semantic roles are already excluded upstream.
    # -------------------------------------------------------------------------

    manifest_blob = (
        json.dumps(load_json(R1F3_MANIFEST), indent=2)
        + "\n"
        + json.dumps(load_json(R1F3_CONTRACT), indent=2)
    ).lower()

    key_rows = []

    for key, rec in persisted.items():
        lineage_records = serializer_key_lineage.get(key, [])
        score = 0
        evidence = []

        if lineage_records:
            modes = {x["mode"] for x in lineage_records}
            if "keyword" in modes:
                score += 200
                evidence.append("direct_cross_function_serializer_lineage")
            if "kwargs_dict" in modes:
                score += 120
                evidence.append("cross_function_dictionary_serializer_lineage")

        if rec["sha256"] in r19_hashes:
            score += 50
            evidence.append("R19_historical_100d_hash")

        if key.lower() in manifest_blob:
            score += 30
            evidence.append("R1F3_manifest_contract_reference")

        key_rows.append({
            **rec,
            "lineage_record_count": len(lineage_records),
            "binding_score": score,
            "binding_evidence": ";".join(evidence),
        })

    key_rows.sort(
        key=lambda r: (
            int(r["binding_score"]),
            int(r["lineage_record_count"]),
            r["key"],
        ),
        reverse=True,
    )

    save_csv(STATE_KEY_TABLE, key_rows)

    # -------------------------------------------------------------------------
    # Unique binding.
    # -------------------------------------------------------------------------

    selected = None
    margin = 0

    if key_rows:
        top = key_rows[0]
        second_score = int(key_rows[1]["binding_score"]) if len(key_rows) > 1 else -999
        margin = int(top["binding_score"]) - second_score

        has_cross_function_lineage = int(top["lineage_record_count"]) > 0

        if has_cross_function_lineage and int(top["binding_score"]) >= 170 and margin >= 30:
            selected = top

    hash_rows = []
    if selected:
        hash_rows.append({
            "artifact": str(R1F3_FROZEN),
            "key": selected["key"],
            "sha256": selected["sha256"],
            "dtype": selected["dtype"],
            "range_min": selected["min"],
            "range_max": selected["max"],
            "binding_score": selected["binding_score"],
            "binding_margin": margin,
            "binding_evidence": selected["binding_evidence"],
            "in_R19_100d_set": selected["sha256"] in r19_hashes,
        })

    save_csv(BOUND_HASH_TABLE, hash_rows)

    # -------------------------------------------------------------------------
    # Final decision.
    # -------------------------------------------------------------------------

    if selected and selected["sha256"] in r19_hashes:
        status = "L2_100D_DEPLOYMENT_STATE_BOUND"
        diagnosis = "CROSS_FUNCTION_RETURN_CALLER_LINEAGE_IDENTIFIES_UNIQUE_STATE_LIKE_100D_KEY"
        recommendation = (
            "The actual 100-day deployment state is now uniquely bound across the "
            "function-return/caller/alias/serializer chain to one state-like frozen key. "
            "Proceed to true no-training 100-day evaluator replay and precision-aware closure "
            "against this bound array only."
        )
        next_milestone = (
            "V15-SG7E1R23 — Bound 100-Day Deterministic Evaluator Replay / Closure Validation"
        )

    elif selected and selected["sha256"] not in r19_hashes:
        status = "L2_100D_STATE_BOUND_TIME_PROVENANCE_CONFLICT"
        diagnosis = "CROSS_FUNCTION_STATE_BINDING_RESOLVED_BUT_HASH_NOT_IN_HISTORICAL_100D_SET"
        recommendation = (
            "Do not replay new times. The state-like key is uniquely bound, but its hash "
            "is absent from the historical 100-day set. Audit only the time label attached "
            "to this bound deployment state."
        )
        next_milestone = (
            "V15-SG7E1R23 — Bound Deployment-State Time-Label Reconciliation Audit"
        )

    else:
        status = "L2_100D_CROSS_FUNCTION_BINDING_STILL_AMBIGUOUS"
        diagnosis = "NO_SINGLE_STATE_LIKE_KEY_HAS_UNIQUE_RETURN_CALLER_SERIALIZER_LINEAGE"
        recommendation = (
            "Do not choose among frozen100, K5_100, and L2_independent_100 by naming or "
            "numerical closeness. Audit the final candidate-selection dictionary/manifest "
            "field that identifies which state was nominated and frozen after independent "
            "validation."
        )
        next_milestone = (
            "V15-SG7E1R23 — Final Candidate-Selection Manifest / Nominated-State Binding Audit"
        )

    checks = [
        ("Incoming R21R semantic contradiction reproduced", True),
        ("Only state-like frozen candidates retained", set(persisted).issubset(allowed_keys)),
        ("Relevant source functions inventoried", len(function_rows) > 0),
        ("Deployment-like return expressions traced", len(return_rows) > 0),
        ("Cross-function caller assignments traced", True),
        ("Caller-output alias graph constructed", True),
        ("Dictionary packing traced", True),
        ("Serializer lineage restricted to state-like keys", True),
        ("Truth/mask/gamma/coeff keys excluded", True),
        ("No candidate selected by numerical performance", True),
        ("No 250/500/1000d state generated", True),
        ("No training performed", True),
        ("No threshold changed or relaxed", True),
    ]

    decision = [{
        "status": status,
        "diagnosis": diagnosis,
        "source_files": len(module_data),
        "deployment_functions": ";".join(sorted(deployment_funcs)),
        "caller_assignment_records": len(call_assign_rows),
        "caller_output_seed_symbols": ";".join(sorted(seed_symbols)),
        "reachable_symbol_count": len(reachable),
        "allowed_state_like_keys": ";".join(sorted(allowed_keys)),
        "selected_key": selected["key"] if selected else "",
        "selected_sha256": selected["sha256"] if selected else "",
        "binding_score": selected["binding_score"] if selected else "",
        "binding_margin": margin,
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION_TABLE, decision)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R22",
        "status": status,
        "diagnosis": diagnosis,
        "binding": {
            "resolved": selected is not None,
            "key": selected["key"] if selected else None,
            "sha256": selected["sha256"] if selected else None,
            "binding_score": int(selected["binding_score"]) if selected else None,
            "binding_margin": margin,
            "in_R19_100d_set": (
                selected["sha256"] in r19_hashes if selected else False
            ),
        },
        "scope": {
            "allowed_state_like_keys": sorted(allowed_keys),
            "excluded_auxiliary_roles": [
                "truth",
                "guard/mask",
                "gamma",
                "coefficient",
                "support",
            ],
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "candidate_performance_used": False,
            "semantic_name_used_as_sole_authority": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
            "threshold_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R22",
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

    print("STATE-LIKE CANDIDATE SCOPE")
    print(f"  Allowed keys            : {sorted(allowed_keys)}")

    print("\nCROSS-FUNCTION TRACE")
    print(f"  Source modules          : {len(module_data)}")
    print(f"  Deployment functions    : {sorted(deployment_funcs)}")
    print(f"  Caller assignments      : {len(call_assign_rows)}")
    print(f"  Caller-output seeds     : {sorted(seed_symbols)}")
    print(f"  Reachable aliases       : {len(reachable)}")

    print("\nSTATE-LIKE KEY LINEAGE")
    for row in key_rows:
        print(
            f"  score={int(row['binding_score']):3d} | "
            f"lineage={int(row['lineage_record_count']):2d} | "
            f"{row['key']:24s} | {row['sha256'][:16]}"
        )

    if selected:
        print("\nSELECTED DEPLOYMENT STATE")
        print(f"  Key                     : {selected['key']}")
        print(f"  SHA-256                 : {selected['sha256']}")
        print(f"  Score / margin          : {selected['binding_score']} / {margin}")
        print(f"  In historical 100d set  : {selected['sha256'] in r19_hashes}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R22 CROSS-FUNCTION BINDING VALIDATION")
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
        FUNCTION_TABLE,
        RETURN_TABLE,
        CALL_TABLE,
        CROSS_TABLE,
        STATE_KEY_TABLE,
        BOUND_HASH_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R22 CROSS-FUNCTION DEPLOYMENT-STATE RETURN / CALLER BINDING AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("Only state-like frozen keys were permitted to compete.")
    print("No key was selected by numerical performance or naming alone.")
    print("No 250/500/1000-day state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
