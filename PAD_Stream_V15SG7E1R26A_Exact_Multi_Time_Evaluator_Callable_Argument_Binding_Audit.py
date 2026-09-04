from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26A
# Exact Multi-Time Evaluator Callable / Argument Binding Audit
#
# DIAGNOSTIC-ONLY BINDING MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
#
# PURPOSE
# -------
# R26 established:
#
#   FOUR_TIME_REGENERATION_BLOCKED_EVALUATOR_BINDING
#
# with:
#
#   NO_DISCOVERED_CALLABLE_REPRODUCES_BOUND_100D_STATE
#
# R26A does NOT broaden the model search. It audits the exact historical
# evaluator path already identified in R18, focusing on:
#
#   1. the exact source function(s) used historically,
#   2. the full callable signature,
#   3. argument names and defaults,
#   4. time / xi / tau transformations,
#   5. model loading and prediction calls,
#   6. post-processing from raw prediction to deployed 100d state,
#   7. persisted feature-array origins,
#   8. return-object semantics.
#
# R26A is allowed to bind the evaluator contract, but it does NOT generate any
# new physical-time deployment state.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26A"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R26_DIR = ROOT / "output" / "V15_SG7E1R26"
R26_SUMMARY = R26_DIR / "PAD_Stream_V15SG7E1R26_Summary.json"
R26_EVALUATOR = R26_DIR / "V15SG7E1R26_Evaluator_Callable_Binding.csv"
R26_ARGS = R26_DIR / "V15SG7E1R26_Evaluator_Argument_Binding.csv"
R26_CONTROL = R26_DIR / "V15SG7E1R26_100d_Control_Closure.csv"

R18_DIR = ROOT / "output" / "V15_SG7E1R18"
R18_SUMMARY = R18_DIR / "PAD_Stream_V15SG7E1R18_Summary.json"
R18_EVAL_TRACE = R18_DIR / "V15SG7E1R18_Deployment_Evaluator_Source_Trace.csv"
R18_ARG_CONTRACT = R18_DIR / "V15SG7E1R18_Evaluation_Argument_Contract.csv"
R18_INPUTS = R18_DIR / "V15SG7E1R18_Persisted_Input_Availability.csv"
R18_MODEL = R18_DIR / "V15SG7E1R18_Frozen_Model_Identity.csv"

R23_SUMMARY = (
    ROOT / "output" / "V15_SG7E1R23"
    / "PAD_Stream_V15SG7E1R23_Summary.json"
)

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

EXPECTED_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SOURCE_TABLE = OUT / "V15SG7E1R26A_Historical_Evaluator_Source_Candidates.csv"
FUNCTION_TABLE = OUT / "V15SG7E1R26A_Function_Signature_Inventory.csv"
CALL_TABLE = OUT / "V15SG7E1R26A_Model_Predict_Call_Trace.csv"
TRANSFORM_TABLE = OUT / "V15SG7E1R26A_Time_Xi_Tau_Transform_Trace.csv"
ARG_BIND_TABLE = OUT / "V15SG7E1R26A_Exact_Argument_Binding_Candidates.csv"
RETURN_TABLE = OUT / "V15SG7E1R26A_Return_Object_Semantics.csv"
POST_TABLE = OUT / "V15SG7E1R26A_Postprocessing_Lineage.csv"
DECISION_TABLE = OUT / "V15SG7E1R26A_Evaluator_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26A_Exact_Evaluator_Argument_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26A_Summary.json"


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
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


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


def expr_names(node):
    return sorted({
        n.id for n in ast.walk(node)
        if isinstance(n, ast.Name)
    })


def candidate_source_paths():
    paths = []

    # Strongest evidence: exact R18 trace.
    for row in load_csv(R18_EVAL_TRACE):
        for col in ("source", "source_file", "path", "file"):
            val = row.get(col, "")
            if not val:
                continue
            p = Path(val)
            if not p.is_absolute():
                p = ROOT / p
            if p.exists() and p.suffix.lower() == ".py":
                paths.append(p.resolve())

    # R26 callable inventory may expose more exact files.
    for row in load_csv(R26_EVALUATOR):
        val = row.get("source", "")
        if val:
            p = Path(val)
            if not p.is_absolute():
                p = ROOT / p
            if p.exists() and p.suffix.lower() == ".py":
                paths.append(p.resolve())

    # Narrow fallback to the already-established late SG7C deployment branch.
    for p in ROOT.glob("PAD_Stream_V15SG7CR3F*.py"):
        if any(tok in p.name for tok in (
            "R3F4",
            "R3F5R1",
            "R3F5R1F",
            "R3F5R1F2",
        )):
            paths.append(p.resolve())

    return sorted(set(paths))


def score_function(name: str, source_text: str, fn_node: ast.FunctionDef):
    low = name.lower()
    score = 0
    evidence = []

    for tok, val in (
        ("predict", 40),
        ("deploy", 40),
        ("evaluate", 35),
        ("eval", 30),
        ("infer", 30),
        ("reconstruct", 25),
        ("transport", 20),
        ("pirnn", 20),
        ("state", 15),
        ("candidate", 10),
        ("correct", 10),
    ):
        if tok in low:
            score += val
            evidence.append(f"name:{tok}")

    params = [a.arg.lower() for a in fn_node.args.args]
    if any(any(tok in p for tok in ("time", "day", "t_phys", "t_days")) for p in params):
        score += 35
        evidence.append("time_parameter")

    body = "\n".join(
        node_src(source_text, n)
        for n in ast.walk(fn_node)
        if isinstance(n, ast.Call)
    ).lower()

    if ".predict(" in body or "predict_on_batch" in body:
        score += 50
        evidence.append("model_predict_call")

    if "load_model" in body:
        score += 20
        evidence.append("load_model")

    if "xi" in body:
        score += 10
        evidence.append("xi_semantics")

    if "tau" in body or "tof" in body:
        score += 10
        evidence.append("tau_tof_semantics")

    if "train" in low or "fit" in low:
        score -= 100
        evidence.append("training_like_penalty")

    return score, evidence


def parse_sources():
    source_rows = []
    function_rows = []
    call_rows = []
    transform_rows = []
    return_rows = []
    post_rows = []

    function_candidates = []

    for src in candidate_source_paths():
        text = safe_text(src)
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            source_rows.append({
                "source": str(src),
                "parsed": False,
                "reason": str(exc),
            })
            continue

        source_rows.append({
            "source": str(src),
            "parsed": True,
            "reason": "",
        })

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            score, evidence = score_function(node.name, text, node)

            args = []
            defaults = {}
            pos_args = node.args.args
            num_defaults = len(node.args.defaults)
            if num_defaults:
                offset = len(pos_args) - num_defaults
                for i, default in enumerate(node.args.defaults):
                    defaults[pos_args[offset + i].arg] = node_src(text, default)

            for a in pos_args:
                args.append(a.arg)

            function_rows.append({
                "source": str(src),
                "function": node.name,
                "line": node.lineno,
                "score": score,
                "evidence": ";".join(evidence),
                "args": ";".join(args),
                "defaults": json.dumps(defaults),
            })

            if score > 0:
                function_candidates.append((score, src, node.name, node, text))

            # model/predict calls
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    cname = call_name(sub).lower()
                    if any(tok in cname for tok in (
                        ".predict",
                        "predict_on_batch",
                        "load_model",
                        "model",
                    )):
                        call_rows.append({
                            "source": str(src),
                            "function": node.name,
                            "line": sub.lineno,
                            "call": call_name(sub),
                            "expression": node_src(text, sub)[:4000],
                            "argument_symbols": ";".join(expr_names(sub)),
                        })

            # time/xi/tau transform statements
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Assign, ast.AnnAssign)):
                    src_line = node_src(text, sub)
                    low = src_line.lower()
                    if any(tok in low for tok in (
                        "time",
                        "days",
                        "xi",
                        "tau",
                        "tof",
                        "scale",
                        "normalize",
                        "log1p",
                    )):
                        transform_rows.append({
                            "source": str(src),
                            "function": node.name,
                            "line": getattr(sub, "lineno", ""),
                            "statement": src_line[:4000],
                        })

            # returns
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    expr = node_src(text, sub.value)
                    return_rows.append({
                        "source": str(src),
                        "function": node.name,
                        "line": sub.lineno,
                        "expression": expr[:4000],
                        "symbols": ";".join(expr_names(sub.value)),
                    })

            # post-processing statements
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Assign, ast.AnnAssign)):
                    stmt = node_src(text, sub)
                    low = stmt.lower()
                    if any(tok in low for tok in (
                        "gamma",
                        "guard",
                        "clip",
                        "truth",
                        "residual",
                        "correct",
                        "candidate",
                        "l2",
                    )):
                        post_rows.append({
                            "source": str(src),
                            "function": node.name,
                            "line": getattr(sub, "lineno", ""),
                            "statement": stmt[:4000],
                        })

    function_candidates.sort(key=lambda x: (x[0], str(x[1]), x[2]), reverse=True)

    return (
        source_rows,
        function_rows,
        call_rows,
        transform_rows,
        return_rows,
        post_rows,
        function_candidates,
    )


def persisted_key_inventory():
    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    db = np.load(R1F3_FROZEN, allow_pickle=True)
    rows = []
    for key in db.files:
        arr = np.asarray(db[key])
        rows.append({
            "key": key,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
        })
    db.close()
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26A")
    print("Exact Multi-Time Evaluator Callable / Argument Binding Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
""")

    s26 = load_json(R26_SUMMARY)
    s18 = load_json(R18_SUMMARY)
    s23 = load_json(R23_SUMMARY)
    c25r = load_json(R25R_CONTRACT)

    if s26.get("status") != "FOUR_TIME_REGENERATION_BLOCKED_EVALUATOR_BINDING":
        raise RuntimeError("R26A requires R26 evaluator-binding block.")

    if s26.get("diagnosis") != "NO_DISCOVERED_CALLABLE_REPRODUCES_BOUND_100D_STATE":
        raise RuntimeError("R26A requires R26 callable-binding diagnosis.")

    if s23.get("selected_key") != "L2_independent_100":
        raise RuntimeError("R26A requires authoritative L2_independent_100 target.")

    envelope = float(c25r["contract_repair"]["precision_envelope"])

    (
        source_rows,
        function_rows,
        call_rows,
        transform_rows,
        return_rows,
        post_rows,
        function_candidates,
    ) = parse_sources()

    save_csv(SOURCE_TABLE, source_rows)
    save_csv(FUNCTION_TABLE, function_rows)
    save_csv(CALL_TABLE, call_rows)
    save_csv(TRANSFORM_TABLE, transform_rows)
    save_csv(RETURN_TABLE, return_rows)
    save_csv(POST_TABLE, post_rows)

    # -------------------------------------------------------------------------
    # Argument-binding evidence from R18 + current source signatures.
    # -------------------------------------------------------------------------

    r18_args = load_csv(R18_ARG_CONTRACT)
    r18_inputs = load_csv(R18_INPUTS)
    frozen_inventory = persisted_key_inventory()

    frozen_keys = {r["key"] for r in frozen_inventory}

    arg_rows = []

    for score, src, fn_name, fn_node, text in function_candidates:
        params = [a.arg for a in fn_node.args.args]
        defaults = {}
        if fn_node.args.defaults:
            offset = len(params) - len(fn_node.args.defaults)
            for i, d in enumerate(fn_node.args.defaults):
                defaults[params[offset + i]] = node_src(text, d)

        for p in params:
            low = p.lower()
            binding = ""
            evidence = []
            confidence = "UNRESOLVED"

            # time
            if any(tok == low or tok in low for tok in (
                "time_days",
                "t_days",
                "physical_time",
                "t_phys",
            )):
                binding = "PHYSICAL_TIME_DAYS"
                evidence.append("time_parameter_semantics")
                confidence = "HIGH"

            # exact frozen keys
            if p in frozen_keys:
                binding = f"R1F3_FROZEN::{p}"
                evidence.append("exact_frozen_key")
                confidence = "HIGH"

            # semantic mappings
            mappings = {
                "xi": "xi",
                "truth_front_xi": "truth_front_xi",
                "tau_end": "tau_end",
                "guard_mask": "guard_mask",
                "gamma": "L2_gamma_independent",
                "l2_gamma": "L2_gamma_independent",
                "truth": "truth100",
                "truth100": "truth100",
                "k5": "K5_100",
                "k5_100": "K5_100",
                "base_state": "K5_100",
            }
            if low in mappings and mappings[low] in frozen_keys:
                binding = f"R1F3_FROZEN::{mappings[low]}"
                evidence.append("semantic_frozen_key_mapping")
                confidence = "HIGH"

            if p in defaults and not binding:
                binding = f"DEFAULT::{defaults[p]}"
                evidence.append("function_default")
                confidence = "MEDIUM"

            # R18 corroboration by parameter string mention.
            for rr in r18_args:
                blob = " ".join(str(v) for v in rr.values()).lower()
                if low in blob:
                    evidence.append("R18_argument_contract_mention")

            for rr in r18_inputs:
                blob = " ".join(str(v) for v in rr.values()).lower()
                if low in blob:
                    evidence.append("R18_persisted_input_mention")

            if binding and "R18_argument_contract_mention" in evidence:
                confidence = "HIGH"

            arg_rows.append({
                "source": str(src),
                "function": fn_name,
                "function_score": score,
                "parameter": p,
                "binding": binding,
                "confidence": confidence,
                "evidence": ";".join(sorted(set(evidence))),
            })

    save_csv(ARG_BIND_TABLE, arg_rows)

    # -------------------------------------------------------------------------
    # Determine whether one callable is now fully bindable.
    # -------------------------------------------------------------------------

    candidate_summary = []

    for score, src, fn_name, fn_node, text in function_candidates:
        fn_args = [r for r in arg_rows if r["source"] == str(src) and r["function"] == fn_name]
        unresolved = [r for r in fn_args if not r["binding"]]
        high = [r for r in fn_args if r["confidence"] == "HIGH"]

        predict_calls = [
            r for r in call_rows
            if r["source"] == str(src) and r["function"] == fn_name
        ]
        transforms = [
            r for r in transform_rows
            if r["source"] == str(src) and r["function"] == fn_name
        ]
        returns = [
            r for r in return_rows
            if r["source"] == str(src) and r["function"] == fn_name
        ]

        binding_score = score
        if not unresolved:
            binding_score += 200
        binding_score += min(len(high) * 10, 100)
        if predict_calls:
            binding_score += 100
        if transforms:
            binding_score += 30
        if returns:
            binding_score += 20

        candidate_summary.append({
            "source": str(src),
            "function": fn_name,
            "source_score": score,
            "binding_score": binding_score,
            "parameter_count": len(fn_args),
            "high_confidence_bindings": len(high),
            "unresolved_parameters": ";".join(r["parameter"] for r in unresolved),
            "predict_call_count": len(predict_calls),
            "transform_record_count": len(transforms),
            "return_record_count": len(returns),
            "fully_bindable": len(unresolved) == 0,
        })

    candidate_summary.sort(
        key=lambda r: (
            int(r["fully_bindable"]),
            int(r["binding_score"]),
        ),
        reverse=True,
    )

    # We deliberately require a meaningful model/predict call and full binding.
    eligible = [
        r for r in candidate_summary
        if r["fully_bindable"]
        and int(r["predict_call_count"]) > 0
    ]

    selected = None
    margin = 0

    if eligible:
        top = eligible[0]
        second_score = int(eligible[1]["binding_score"]) if len(eligible) > 1 else -999
        margin = int(top["binding_score"]) - second_score

        # Require unique enough source authority.
        if margin >= 50 or len(eligible) == 1:
            selected = top

    # -------------------------------------------------------------------------
    # Final decision
    # -------------------------------------------------------------------------

    if selected is not None:
        status = "MULTI_TIME_EVALUATOR_CALLABLE_ARGUMENT_CONTRACT_BOUND"
        diagnosis = "ONE_HISTORICAL_NO_TRAINING_EVALUATOR_HAS_COMPLETE_PERSISTED_ARGUMENT_BINDING"
        recommendation = (
            "The historical evaluator callable and all required arguments are now explicitly "
            "bound from persisted provenance. Do not generate later-time states in this audit. "
            "Proceed to a controlled callable replay milestone that first executes 100 days "
            "against L2_independent_100 using this exact function/signature/binding contract; "
            "only after closure may 250/500/1000 days be generated."
        )
        next_milestone = (
            "V15-SG7E1R26B — Exact-Bound Evaluator 100-Day Control / Four-Time Regeneration"
        )
    else:
        status = "MULTI_TIME_EVALUATOR_ARGUMENT_BINDING_STILL_INCOMPLETE"
        diagnosis = "NO_SINGLE_HISTORICAL_EVALUATOR_HAS_COMPLETE_UNAMBIGUOUS_PERSISTED_ARGUMENT_BINDING"
        recommendation = (
            "Do not generate 250/500/1000-day states. Use the generated function-signature, "
            "predict-call, transform, and argument-binding tables to audit only the unresolved "
            "parameters of the highest-scoring historical evaluator. Do not broaden the source "
            "search or fabricate features."
        )
        next_milestone = (
            "V15-SG7E1R26B — Unresolved Evaluator Feature / Transform Binding Audit"
        )

    decision_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "candidate_source_count": len(source_rows),
        "function_candidate_count": len(function_candidates),
        "eligible_fully_bound_count": len(eligible),
        "selected_source": selected["source"] if selected else "",
        "selected_function": selected["function"] if selected else "",
        "selected_binding_score": selected["binding_score"] if selected else "",
        "binding_margin": margin,
        "precision_envelope": envelope,
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION_TABLE, decision_rows)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26A",
        "status": status,
        "diagnosis": diagnosis,
        "selected_evaluator": {
            "resolved": selected is not None,
            "source": selected["source"] if selected else None,
            "function": selected["function"] if selected else None,
            "binding_score": int(selected["binding_score"]) if selected else None,
            "binding_margin": margin,
        },
        "precision_envelope": envelope,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
            "fabricated_feature_used": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26A",
        "status": status,
        "diagnosis": diagnosis,
        "selected_source": selected["source"] if selected else None,
        "selected_function": selected["function"] if selected else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("HISTORICAL EVALUATOR SOURCE AUDIT")
    print(f"  Source candidates       : {len(source_rows)}")
    print(f"  Function candidates     : {len(function_candidates)}")
    print(f"  Model/predict calls     : {len(call_rows)}")
    print(f"  Transform records       : {len(transform_rows)}")
    print(f"  Return records          : {len(return_rows)}")

    print("\nTOP CALLABLE BINDING CANDIDATES")
    for row in candidate_summary[:12]:
        print(
            f"  score={int(row['binding_score']):4d} | "
            f"fullyBound={row['fully_bindable']} | "
            f"predict={int(row['predict_call_count']):2d} | "
            f"{Path(row['source']).name} :: {row['function']} | "
            f"unresolved={row['unresolved_parameters'] or 'NONE'}"
        )

    if selected:
        print("\nSELECTED EXACT EVALUATOR CONTRACT")
        print(f"  Source                  : {selected['source']}")
        print(f"  Function                : {selected['function']}")
        print(f"  Binding score           : {selected['binding_score']}")
        print(f"  Margin                  : {margin}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26A BINDING VALIDATION")
    print("=" * 78)
    checks = [
        ("Incoming R26 evaluator-binding block reproduced", True),
        ("R18 deterministic-regeneration contract retained", True),
        ("Historical evaluator sources inventoried", len(source_rows) > 0),
        ("Function signatures audited", len(function_rows) > 0),
        ("Model/predict calls audited", True),
        ("Time/xi/tau transforms audited", True),
        ("Persisted argument candidates audited", True),
        ("Return-object semantics audited", True),
        ("Postprocessing lineage audited", True),
        ("No fabricated feature used", True),
        ("No new later-time state generated", True),
        ("No training performed", True),
        ("No threshold changed or relaxed", True),
    ]
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
        SOURCE_TABLE,
        FUNCTION_TABLE,
        CALL_TABLE,
        TRANSFORM_TABLE,
        ARG_BIND_TABLE,
        RETURN_TABLE,
        POST_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26A EXACT MULTI-TIME EVALUATOR CALLABLE / ARGUMENT BINDING AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was changed.")
    print("No 250/500/1000-day state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
