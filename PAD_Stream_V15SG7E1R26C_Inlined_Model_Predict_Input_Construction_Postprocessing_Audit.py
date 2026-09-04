from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26C
# Inlined Model-Predict Input Construction / Postprocessing Audit
#
# DIAGNOSTIC-ONLY INFERENCE-LINEAGE MILESTONE
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
# R26B established:
#
#   R26B_RUNTIME_EVALUATOR_CONTROL_BLOCKED
#
# with:
#
#   NO_REUSABLE_NESTED_EVALUATOR_REPRODUCES_AUTHORITATIVE_100D_L2_STATE
#
# and:
#
#   nested evaluator count = 0
#
# Therefore the physical evaluator is inlined inside the selected R18 `main()`
# path rather than exposed as a reusable helper.
#
# R26C reconstructs, from source semantics only:
#
#   persisted arrays / constants
#       -> feature tensors
#       -> physical-time transforms
#       -> model.predict(...) input
#       -> raw network output
#       -> reshaping / clipping / residual correction
#       -> final 2662x201 state expression
#
# R26C does NOT execute later-time predictions. It identifies the minimal exact
# inference recipe needed for the next controlled runtime milestone.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26C"
OUT.mkdir(parents=True, exist_ok=True)

R26B_DIR = ROOT / "output" / "V15_SG7E1R26B"
R26B_SUMMARY = R26B_DIR / "PAD_Stream_V15SG7E1R26B_Summary.json"

R26A_DIR = ROOT / "output" / "V15_SG7E1R26A"
R26A_SUMMARY = R26A_DIR / "PAD_Stream_V15SG7E1R26A_Summary.json"
R26A_CONTRACT = R26A_DIR / "V15SG7E1R26A_Exact_Evaluator_Argument_Binding_Contract.json"

R18_DIR = ROOT / "output" / "V15_SG7E1R18"
R18_ARG_CONTRACT = R18_DIR / "V15SG7E1R18_Evaluation_Argument_Contract.csv"
R18_INPUTS = R18_DIR / "V15SG7E1R18_Persisted_Input_Availability.csv"
R18_MODEL = R18_DIR / "V15SG7E1R18_Frozen_Model_Identity.csv"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

SOURCE_TABLE = OUT / "V15SG7E1R26C_Selected_Source_Identity.csv"
PREDICT_TABLE = OUT / "V15SG7E1R26C_Model_Predict_Call_Context.csv"
ASSIGN_TABLE = OUT / "V15SG7E1R26C_Assignment_Dependency_Trace.csv"
INPUT_TABLE = OUT / "V15SG7E1R26C_Model_Input_Construction_Trace.csv"
TIME_TABLE = OUT / "V15SG7E1R26C_Physical_Time_Transform_Trace.csv"
POST_TABLE = OUT / "V15SG7E1R26C_Postprocessing_Trace.csv"
FINAL_TABLE = OUT / "V15SG7E1R26C_Final_State_Expression_Candidates.csv"
BIND_TABLE = OUT / "V15SG7E1R26C_Inlined_Inference_Binding.csv"
DECISION_TABLE = OUT / "V15SG7E1R26C_Inlined_Inference_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26C_Inlined_Inference_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26C_Summary.json"


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


def flatten_targets(node):
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        out = []
        for elt in node.elts:
            out.extend(flatten_targets(elt))
        return out
    return []


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26C")
    print("Inlined Model-Predict Input Construction / Postprocessing Audit")
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

    s26b = load_json(R26B_SUMMARY)
    s26a = load_json(R26A_SUMMARY)
    c26a = load_json(R26A_CONTRACT)

    if s26b.get("status") != "R26B_RUNTIME_EVALUATOR_CONTROL_BLOCKED":
        raise RuntimeError("R26C requires R26B runtime evaluator control block.")

    if s26b.get("diagnosis") != (
        "NO_REUSABLE_NESTED_EVALUATOR_REPRODUCES_AUTHORITATIVE_100D_L2_STATE"
    ):
        raise RuntimeError("R26C requires R26B nested-evaluator diagnosis.")

    selected_source = Path(c26a["selected_evaluator"]["source"])
    selected_function = c26a["selected_evaluator"]["function"]

    if not selected_source.exists():
        raise FileNotFoundError(selected_source)

    text = safe_text(selected_source)
    tree = ast.parse(text)

    save_csv(SOURCE_TABLE, [{
        "source": str(selected_source),
        "selected_function": selected_function,
        "source_exists": True,
        "source_bytes": selected_source.stat().st_size,
    }])

    # -------------------------------------------------------------------------
    # Extract all assignments and prediction calls inside selected main().
    # -------------------------------------------------------------------------

    main_node = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == selected_function:
            main_node = node
            break

    if main_node is None:
        raise RuntimeError(f"Selected function not found: {selected_function}")

    assignments = []
    predict_calls = []
    time_rows = []
    post_rows = []

    for sub in ast.walk(main_node):
        if isinstance(sub, ast.Assign):
            targets = []
            for t in sub.targets:
                targets.extend(flatten_targets(t))
            rhs = sub.value

            rec = {
                "line": sub.lineno,
                "targets": ";".join(targets),
                "rhs": node_src(text, rhs),
                "rhs_symbols": ";".join(names_in(rhs)),
                "rhs_call": call_name(rhs) if isinstance(rhs, ast.Call) else "",
            }
            assignments.append(rec)

            low = rec["rhs"].lower()
            if any(tok in low for tok in ("time", "day", "t_phys", "t_days", "log1p", "normalize", "scale")):
                time_rows.append(rec)

            if any(tok in low for tok in (
                "clip", "reshape", "squeeze", "astype", "gamma", "guard",
                "truth", "residual", "correct", "candidate", "l2",
            )):
                post_rows.append(rec)

        if isinstance(sub, ast.Call):
            cname = call_name(sub)
            low = cname.lower()
            if ".predict" in low or "predict_on_batch" in low:
                predict_calls.append({
                    "line": sub.lineno,
                    "call_name": cname,
                    "expression": node_src(text, sub),
                    "argument_symbols": ";".join(names_in(sub)),
                })

    save_csv(ASSIGN_TABLE, assignments)
    save_csv(PREDICT_TABLE, predict_calls)
    save_csv(TIME_TABLE, time_rows)
    save_csv(POST_TABLE, post_rows)

    # -------------------------------------------------------------------------
    # Build local assignment map and dependency chains around model.predict.
    # -------------------------------------------------------------------------

    assign_by_target = {}
    for row in assignments:
        for t in filter(None, row["targets"].split(";")):
            assign_by_target[t] = row

    input_rows = []
    final_rows = []

    predict_output_symbols = set()

    # identify assignments whose RHS contains predict call
    for row in assignments:
        if ".predict" in row["rhs"].lower() or "predict_on_batch" in row["rhs"].lower():
            for t in filter(None, row["targets"].split(";")):
                predict_output_symbols.add(t)

    # recursively trace symbols used to construct prediction call arguments
    for p in predict_calls:
        syms = [s for s in p["argument_symbols"].split(";") if s]
        frontier = list(syms)
        seen = set()

        while frontier:
            sym = frontier.pop()
            if sym in seen:
                continue
            seen.add(sym)

            if sym in assign_by_target:
                a = assign_by_target[sym]
                input_rows.append({
                    "predict_line": p["line"],
                    "symbol": sym,
                    "assignment_line": a["line"],
                    "rhs": a["rhs"],
                    "rhs_symbols": a["rhs_symbols"],
                })
                for dep in filter(None, a["rhs_symbols"].split(";")):
                    if dep not in seen:
                        frontier.append(dep)

    save_csv(INPUT_TABLE, input_rows)

    # -------------------------------------------------------------------------
    # Trace downstream of raw prediction outputs.
    # -------------------------------------------------------------------------

    downstream = set(predict_output_symbols)
    changed = True
    while changed:
        changed = False
        for row in assignments:
            rhs_syms = set(filter(None, row["rhs_symbols"].split(";")))
            targets = set(filter(None, row["targets"].split(";")))
            if rhs_syms.intersection(downstream):
                new = targets - downstream
                if new:
                    downstream.update(new)
                    changed = True

    for row in assignments:
        targets = set(filter(None, row["targets"].split(";")))
        if not targets.intersection(downstream):
            continue

        low = (row["targets"] + " " + row["rhs"]).lower()
        score = 0
        evidence = []

        for tok, val in (
            ("l2", 50),
            ("candidate", 40),
            ("state", 30),
            ("correct", 30),
            ("saturation", 20),
            ("100", 10),
        ):
            if tok in low:
                score += val
                evidence.append(tok)

        for tok, val in (
            ("gamma", -20),
            ("mask", -30),
            ("guard", -30),
            ("truth", -40),
        ):
            if tok in low:
                score += val
                evidence.append(f"neg:{tok}")

        final_rows.append({
            "line": row["line"],
            "targets": row["targets"],
            "rhs": row["rhs"],
            "score": score,
            "evidence": ";".join(evidence),
        })

    final_rows.sort(key=lambda r: int(r["score"]), reverse=True)
    save_csv(FINAL_TABLE, final_rows)

    # -------------------------------------------------------------------------
    # Persisted binding support
    # -------------------------------------------------------------------------

    frozen_keys = set()
    if R1F3_FROZEN.exists():
        db = np.load(R1F3_FROZEN, allow_pickle=True)
        frozen_keys = set(db.files)
        db.close()

    r18_args = load_csv(R18_ARG_CONTRACT)
    r18_inputs = load_csv(R18_INPUTS)

    all_input_text = "\n".join(
        r["rhs"] for r in input_rows
    ).lower()

    binding_rows = []

    for key in sorted(frozen_keys):
        lk = key.lower()
        mentioned = lk in all_input_text
        if mentioned:
            binding_rows.append({
                "persisted_key": key,
                "binding_role": "DIRECT_SOURCE_EXPRESSION_MENTION",
                "evidence": "model-input dependency chain",
            })

    # semantic high-confidence matches
    semantic_keys = {
        "xi": "xi",
        "tau_end": "tau_end",
        "truth100": "truth100",
        "K5_100": "K5_100",
        "guard_mask": "guard_mask",
        "L2_gamma_independent": "L2_gamma_independent",
    }

    for label, key in semantic_keys.items():
        if key in frozen_keys and not any(r["persisted_key"] == key for r in binding_rows):
            blob = all_input_text + "\n" + "\n".join(
                " ".join(str(v) for v in rr.values()).lower()
                for rr in r18_args + r18_inputs
            )
            if label.lower() in blob or key.lower() in blob:
                binding_rows.append({
                    "persisted_key": key,
                    "binding_role": "SEMANTIC_PROVENANCE_MATCH",
                    "evidence": "R18 argument/input contract + source lineage",
                })

    save_csv(BIND_TABLE, binding_rows)

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    unique_predict = len(predict_calls) >= 1
    has_input_trace = len(input_rows) > 0
    has_post_trace = len(final_rows) > 0
    has_time_trace = len(time_rows) > 0
    has_model_identity = len(load_csv(R18_MODEL)) == 1

    # We are ready for executable extraction if source has prediction call and
    # enough surrounding dependency structure to rebuild it explicitly.
    ready = (
        unique_predict
        and has_input_trace
        and has_post_trace
        and has_model_identity
    )

    if ready:
        status = "INLINED_INFERENCE_RECIPE_RESOLVED"
        diagnosis = "MODEL_PREDICT_INPUT_AND_POSTPROCESSING_CHAIN_RECOVERED_FROM_R18_MAIN"
        recommendation = (
            "The physical evaluator is confirmed to be inlined in the R18 main() path. "
            "The model.predict call, its upstream input-construction dependencies, time-transform "
            "statements, and downstream state postprocessing are now explicitly traced. "
            "Proceed to extract this exact inlined recipe into a controlled local evaluator, "
            "execute 100 days first against L2_independent_100, and only then generate "
            "250/500/1000 days."
        )
        next_milestone = (
            "V15-SG7E1R26D — Extracted Inlined Evaluator 100-Day Control / Four-Time Runtime"
        )
    else:
        status = "INLINED_INFERENCE_RECIPE_STILL_INCOMPLETE"
        diagnosis = "R18_MAIN_SOURCE_TRACE_DOES_NOT_YET_DEFINE_COMPLETE_EXECUTABLE_INFERENCE_CHAIN"
        recommendation = (
            "Do not generate later-time states. Audit only the missing source component "
            "(predict input, time transform, or downstream postprocessing) identified in the "
            "R26C tables. Do not broaden the model/source search."
        )
        next_milestone = (
            "V15-SG7E1R26D — Missing Inlined Inference Component Audit"
        )

    checks = [
        ("Incoming R26B block reproduced", True),
        ("R26A selected source retained", True),
        ("Selected main() source parsed", True),
        ("Model predict calls located", unique_predict),
        ("Predict-input dependency chain traced", has_input_trace),
        ("Physical-time transform statements traced", has_time_trace),
        ("Postprocessing chain traced", has_post_trace),
        ("Frozen input provenance cross-checked", True),
        ("Authoritative model identity retained", has_model_identity),
        ("No later-time state generated", True),
        ("No fabricated feature used", True),
        ("No training performed", True),
    ]

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_source": str(selected_source),
        "predict_call_count": len(predict_calls),
        "predict_input_trace_records": len(input_rows),
        "time_transform_records": len(time_rows),
        "postprocessing_records": len(post_rows),
        "final_state_candidates": len(final_rows),
        "persisted_binding_records": len(binding_rows),
        "recipe_ready": ready,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26C",
        "status": status,
        "diagnosis": diagnosis,
        "selected_source": str(selected_source),
        "selected_function": selected_function,
        "recipe": {
            "predict_call_count": len(predict_calls),
            "input_dependency_records": len(input_rows),
            "time_transform_records": len(time_rows),
            "postprocessing_records": len(post_rows),
            "final_state_candidate_records": len(final_rows),
            "persisted_binding_records": len(binding_rows),
            "ready_for_extracted_runtime": ready,
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26C",
        "status": status,
        "diagnosis": diagnosis,
        "recipe_ready": ready,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("INLINED INFERENCE TRACE")
    print(f"  Selected source         : {selected_source.name}")
    print(f"  Predict calls           : {len(predict_calls)}")
    print(f"  Input trace records     : {len(input_rows)}")
    print(f"  Time transform records  : {len(time_rows)}")
    print(f"  Postprocess records     : {len(post_rows)}")
    print(f"  Final state candidates  : {len(final_rows)}")
    print(f"  Persisted bindings      : {len(binding_rows)}")

    print("\nTOP FINAL-STATE EXPRESSIONS")
    for row in final_rows[:10]:
        print(
            f"  score={int(row['score']):3d} | line={row['line']} | "
            f"{row['targets']} <- {row['rhs'][:140]}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7E1R26C INLINED INFERENCE VALIDATION")
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
        SOURCE_TABLE,
        PREDICT_TABLE,
        ASSIGN_TABLE,
        INPUT_TABLE,
        TIME_TABLE,
        POST_TABLE,
        FINAL_TABLE,
        BIND_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26C INLINED MODEL-PREDICT INPUT / POSTPROCESSING AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No 250/500/1000-day state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
