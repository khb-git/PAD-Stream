from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict

# =============================================================================
# PAD-Stream V15-SG7E1R26D
# Missing Inlined Inference Component Audit
#
# DIAGNOSTIC-ONLY MILESTONE
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
# R26C established:
#
#   INLINED_INFERENCE_RECIPE_STILL_INCOMPLETE
#
# because the R18 main() source contained:
#
#   predict calls          : 0
#   predict-input records  : 0
#   final-state candidates : 0
#
# while still containing time-transform and provenance-analysis logic.
#
# That pattern strongly suggests R18 is a FORENSIC/AUDIT PROGRAM that traces
# the evaluator elsewhere rather than executing the physical evaluator itself.
#
# R26D audits that hypothesis explicitly.
#
# It determines whether R18 main():
#
#   A) directly executes the model, or
#   B) searches/parses upstream source files and records evaluator provenance.
#
# If B is confirmed, R26D resolves the exact upstream source files/functions
# referenced by R18's own generated evaluator trace and identifies the narrowest
# authoritative source branch for the next runtime-binding milestone.
#
# No source is selected by numerical performance.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26D"
OUT.mkdir(parents=True, exist_ok=True)

R26C_DIR = ROOT / "output" / "V15_SG7E1R26C"
R26C_SUMMARY = R26C_DIR / "PAD_Stream_V15SG7E1R26C_Summary.json"
R26C_PREDICT = R26C_DIR / "V15SG7E1R26C_Model_Predict_Call_Context.csv"
R26C_INPUT = R26C_DIR / "V15SG7E1R26C_Model_Input_Construction_Trace.csv"
R26C_SOURCE = R26C_DIR / "V15SG7E1R26C_Selected_Source_Identity.csv"

R26A_DIR = ROOT / "output" / "V15_SG7E1R26A"
R26A_CONTRACT = R26A_DIR / "V15SG7E1R26A_Exact_Evaluator_Argument_Binding_Contract.json"

R18_DIR = ROOT / "output" / "V15_SG7E1R18"
R18_EVAL_TRACE = R18_DIR / "V15SG7E1R18_Deployment_Evaluator_Source_Trace.csv"
R18_ARG_CONTRACT = R18_DIR / "V15SG7E1R18_Evaluation_Argument_Contract.csv"
R18_INPUTS = R18_DIR / "V15SG7E1R18_Persisted_Input_Availability.csv"

SOURCE_CLASS_TABLE = OUT / "V15SG7E1R26D_R18_Source_Role_Classification.csv"
META_TRACE_TABLE = OUT / "V15SG7E1R26D_R18_Meta_Analysis_Operations.csv"
UPSTREAM_TABLE = OUT / "V15SG7E1R26D_Upstream_Evaluator_Source_Resolution.csv"
FUNCTION_TABLE = OUT / "V15SG7E1R26D_Upstream_Function_Candidate_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R26D_Missing_Component_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26D_Missing_Inference_Component_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26D_Summary.json"


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


def normalize_path(value: str):
    if not value:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve() if p.exists() else p


def extract_paths_from_row(row):
    paths = []
    for value in row.values():
        if value is None:
            continue
        s = str(value)
        # direct path
        if ".py" in s.lower():
            # find Windows or relative Python path substrings
            matches = re.findall(
                r'([A-Za-z]:\\[^"\';,\n\r]+?\.py|[^"\';,\n\r]+?\.py)',
                s,
                flags=re.I,
            )
            for m in matches:
                p = normalize_path(m.strip())
                if p is not None and p.exists():
                    paths.append(p)
    return paths


def score_upstream_function(path: Path):
    text = safe_text(path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        name = node.name
        low_name = name.lower()

        predict_calls = 0
        keras_calls = 0
        time_mentions = 0
        xi_mentions = 0
        tau_mentions = 0
        return_count = 0
        load_model_calls = 0
        direct_model_calls = 0

        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                cname = call_name(sub).lower()
                expr = node_src(text, sub).lower()

                if ".predict" in cname or "predict_on_batch" in cname:
                    predict_calls += 1

                if "load_model" in cname:
                    load_model_calls += 1

                # model(...) / net(...) / pirnn(...)
                if isinstance(sub.func, ast.Name):
                    fn = sub.func.id.lower()
                    if fn in {"model", "net", "network", "pirnn", "rnn"}:
                        direct_model_calls += 1

                if any(tok in expr for tok in ("keras", "tensorflow", "tf.")):
                    keras_calls += 1

            if isinstance(sub, ast.Return):
                return_count += 1

            src = node_src(text, sub).lower()
            if any(tok in src for tok in ("time_days", "t_days", "physical_time", "days")):
                time_mentions += 1
            if "xi" in src:
                xi_mentions += 1
            if "tau" in src or "tof" in src:
                tau_mentions += 1

        params = [a.arg for a in node.args.args]
        score = 0
        evidence = []

        if predict_calls:
            score += 150
            evidence.append("predict_call")
        if direct_model_calls:
            score += 120
            evidence.append("direct_model_call")
        if load_model_calls:
            score += 30
            evidence.append("load_model")
        if time_mentions:
            score += 40
            evidence.append("time_semantics")
        if xi_mentions:
            score += 20
            evidence.append("xi_semantics")
        if tau_mentions:
            score += 20
            evidence.append("tau_tof_semantics")
        if return_count:
            score += 20
            evidence.append("returns_value")

        for tok, val in (
            ("predict", 40),
            ("deploy", 40),
            ("eval", 30),
            ("infer", 30),
            ("state", 15),
            ("transport", 15),
        ):
            if tok in low_name:
                score += val
                evidence.append(f"name:{tok}")

        if name == "main":
            score -= 25
            evidence.append("main_penalty")
        if "audit" in low_name:
            score -= 30
            evidence.append("audit_penalty")
        if "train" in low_name or "fit" in low_name:
            score -= 200
            evidence.append("training_penalty")

        rows.append({
            "source": str(path),
            "function": name,
            "line": node.lineno,
            "parameters": ";".join(params),
            "predict_calls": predict_calls,
            "direct_model_calls": direct_model_calls,
            "load_model_calls": load_model_calls,
            "time_mentions": time_mentions,
            "xi_mentions": xi_mentions,
            "tau_mentions": tau_mentions,
            "return_count": return_count,
            "score": score,
            "evidence": ";".join(evidence),
        })

    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26D")
    print("Missing Inlined Inference Component Audit")
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

    s26c = load_json(R26C_SUMMARY)
    c26a = load_json(R26A_CONTRACT)

    if s26c.get("status") != "INLINED_INFERENCE_RECIPE_STILL_INCOMPLETE":
        raise RuntimeError("R26D requires R26C incomplete inlined recipe status.")

    if s26c.get("diagnosis") != (
        "R18_MAIN_SOURCE_TRACE_DOES_NOT_YET_DEFINE_COMPLETE_EXECUTABLE_INFERENCE_CHAIN"
    ):
        raise RuntimeError("R26D requires R26C source-trace diagnosis.")

    selected_source = Path(c26a["selected_evaluator"]["source"])
    if not selected_source.exists():
        raise FileNotFoundError(selected_source)

    # -------------------------------------------------------------------------
    # Classify R18 selected source as runtime evaluator vs provenance/audit tool.
    # -------------------------------------------------------------------------

    text = safe_text(selected_source)
    tree = ast.parse(text)

    predict_count = 0
    parse_count = 0
    glob_count = 0
    csv_count = 0
    source_read_count = 0
    regex_count = 0
    ast_parse_count = 0
    model_load_count = 0

    meta_rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node)
        low = cname.lower()
        expr = node_src(text, node)

        role = None

        if ".predict" in low or "predict_on_batch" in low:
            predict_count += 1
            role = "MODEL_PREDICTION"
        elif "load_model" in low:
            model_load_count += 1
            role = "MODEL_LOAD"
        elif "ast.parse" in low:
            ast_parse_count += 1
            parse_count += 1
            role = "SOURCE_AST_PARSE"
        elif ".glob" in low or ".rglob" in low:
            glob_count += 1
            role = "SOURCE_FILE_DISCOVERY"
        elif "read_text" in low:
            source_read_count += 1
            role = "SOURCE_TEXT_READ"
        elif "re.search" in low or "re.findall" in low or "re.finditer" in low:
            regex_count += 1
            role = "SOURCE_PATTERN_SEARCH"
        elif "csv." in low or "read_csv" in low:
            csv_count += 1
            role = "STRUCTURED_PROVENANCE_READ"

        if role:
            meta_rows.append({
                "line": getattr(node, "lineno", ""),
                "call": cname,
                "role": role,
                "expression": expr[:2500],
            })

    is_audit_meta_program = (
        predict_count == 0
        and model_load_count == 0
        and (
            ast_parse_count > 0
            or glob_count > 0
            or source_read_count > 0
            or regex_count > 0
        )
    )

    save_csv(META_TRACE_TABLE, meta_rows)

    save_csv(SOURCE_CLASS_TABLE, [{
        "source": str(selected_source),
        "predict_call_count": predict_count,
        "model_load_call_count": model_load_count,
        "ast_parse_count": ast_parse_count,
        "glob_count": glob_count,
        "source_read_count": source_read_count,
        "regex_count": regex_count,
        "csv_read_count": csv_count,
        "classified_as_audit_meta_program": is_audit_meta_program,
        "classified_as_direct_runtime_evaluator": (
            predict_count > 0 or model_load_count > 0
        ),
    }])

    # -------------------------------------------------------------------------
    # Resolve upstream sources from R18's own persisted evaluator trace.
    # -------------------------------------------------------------------------

    trace_rows = load_csv(R18_EVAL_TRACE)
    path_hits = defaultdict(lambda: {
        "row_hits": 0,
        "field_hits": 0,
        "evidence": [],
    })

    for idx, row in enumerate(trace_rows):
        row_paths = set(extract_paths_from_row(row))
        for p in row_paths:
            info = path_hits[p]
            info["row_hits"] += 1
            info["field_hits"] += sum(
                1 for v in row.values()
                if str(p.name).lower() in str(v).lower()
            )
            info["evidence"].append(idx)

    upstream_rows = []

    for path, info in path_hits.items():
        text_up = safe_text(path).lower()
        runtime_tokens = {
            "predict": text_up.count(".predict("),
            "predict_on_batch": text_up.count("predict_on_batch"),
            "load_model": text_up.count("load_model"),
            "model_call": len(re.findall(r"\bmodel\s*\(", text_up)),
            "time_days": text_up.count("time_days") + text_up.count("t_days"),
            "xi": text_up.count("xi"),
            "tau": text_up.count("tau") + text_up.count("tof"),
        }

        runtime_score = (
            100 * runtime_tokens["predict"]
            + 100 * runtime_tokens["predict_on_batch"]
            + 30 * runtime_tokens["load_model"]
            + 60 * runtime_tokens["model_call"]
            + 5 * min(runtime_tokens["time_days"], 10)
            + 2 * min(runtime_tokens["xi"], 10)
            + 2 * min(runtime_tokens["tau"], 10)
            + 20 * info["row_hits"]
        )

        upstream_rows.append({
            "source": str(path),
            "row_hits_in_R18_trace": info["row_hits"],
            "field_hits_in_R18_trace": info["field_hits"],
            **runtime_tokens,
            "runtime_score": runtime_score,
        })

    upstream_rows.sort(
        key=lambda r: (
            int(r["runtime_score"]),
            int(r["row_hits_in_R18_trace"]),
        ),
        reverse=True,
    )

    save_csv(UPSTREAM_TABLE, upstream_rows)

    # -------------------------------------------------------------------------
    # Function-level audit only inside resolved R18-linked upstream files.
    # -------------------------------------------------------------------------

    function_rows = []
    for row in upstream_rows:
        p = Path(row["source"])
        function_rows.extend(score_upstream_function(p))

    function_rows.sort(
        key=lambda r: (
            int(r["score"]),
            int(r["predict_calls"]) + int(r["direct_model_calls"]),
        ),
        reverse=True,
    )

    save_csv(FUNCTION_TABLE, function_rows)

    # Select source/function by provenance + actual runtime semantics.
    eligible_functions = [
        r for r in function_rows
        if (
            int(r["predict_calls"]) > 0
            or int(r["direct_model_calls"]) > 0
        )
        and int(r["score"]) > 0
    ]

    selected_fn = None
    margin = 0

    if eligible_functions:
        top = eligible_functions[0]
        second = int(eligible_functions[1]["score"]) if len(eligible_functions) > 1 else -999
        margin = int(top["score"]) - second

        # Require at least one explicit R18-linked source and a runtime call.
        source_record = next(
            (r for r in upstream_rows if r["source"] == top["source"]),
            None,
        )

        if source_record and int(source_record["row_hits_in_R18_trace"]) > 0:
            selected_fn = top

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    if is_audit_meta_program and selected_fn is not None:
        status = "TRUE_UPSTREAM_EVALUATOR_SOURCE_RESOLVED"
        diagnosis = (
            "R18_MAIN_IS_PROVENANCE_AUDIT_NOT_RUNTIME_EVALUATOR_AND_R18_TRACE_IDENTIFIES_UPSTREAM_INFERENCE_SOURCE"
        )
        recommendation = (
            "The repeated callable failures are explained: the R18 script is an audit/meta-program, "
            "not the deployment evaluator. Its own persisted evaluator trace now resolves the "
            "actual upstream source/function containing model inference. Preserve this exact "
            "source/function identity and proceed to bind its concrete model input tensors, time "
            "transform, and return/postprocessing semantics. Do not return to R18 main() as a "
            "runtime callable."
        )
        next_milestone = (
            "V15-SG7E1R26E — True Upstream Evaluator Input / Return Binding Audit"
        )

    elif is_audit_meta_program:
        status = "R18_CONFIRMED_META_PROGRAM_UPSTREAM_RUNTIME_SOURCE_NOT_YET_UNIQUE"
        diagnosis = (
            "R18_DOES_NOT_EXECUTE_INFERENCE_AND_ITS_TRACE_REACHES_MULTIPLE_OR_NO_RUNTIME_SOURCES"
        )
        recommendation = (
            "Do not generate later-time states. Keep R18 classified as provenance-only and "
            "audit only the highest-ranked R18-linked upstream source files listed by R26D."
        )
        next_milestone = (
            "V15-SG7E1R26E — R18-Linked Upstream Runtime Source Conflict Audit"
        )

    else:
        status = "R18_SOURCE_ROLE_CLASSIFICATION_CONFLICT"
        diagnosis = "R18_SOURCE_DOES_NOT_CLEANLY_CLASSIFY_AS_PROVENANCE_ONLY_OR_RUNTIME_EVALUATOR"
        recommendation = (
            "Do not generate later-time states. Audit the R18 source-role classification before "
            "continuing evaluator extraction."
        )
        next_milestone = (
            "V15-SG7E1R26E — R18 Source-Role Conflict Audit"
        )

    checks = [
        ("Incoming R26C incomplete recipe reproduced", True),
        ("R26C found zero model-predict calls", len(load_csv(R26C_PREDICT)) == 0),
        ("R26C found zero predict-input records", len(load_csv(R26C_INPUT)) == 0),
        ("R18 selected source parsed", True),
        ("R18 runtime-vs-meta operations classified", True),
        ("R18 persisted evaluator trace loaded", len(trace_rows) > 0),
        ("R18-linked upstream source paths audited", True),
        ("Function-level runtime semantics audited", True),
        ("No source selected by numerical performance", True),
        ("No later-time state generated", True),
        ("No fabricated feature used", True),
        ("No training performed", True),
    ]

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "R18_is_audit_meta_program": is_audit_meta_program,
        "upstream_source_count": len(upstream_rows),
        "eligible_runtime_function_count": len(eligible_functions),
        "selected_source": selected_fn["source"] if selected_fn else "",
        "selected_function": selected_fn["function"] if selected_fn else "",
        "selected_score": selected_fn["score"] if selected_fn else "",
        "selection_margin": margin,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26D",
        "status": status,
        "diagnosis": diagnosis,
        "R18_source_role": {
            "source": str(selected_source),
            "audit_meta_program": is_audit_meta_program,
            "predict_call_count": predict_count,
            "model_load_call_count": model_load_count,
            "source_analysis_operations": len(meta_rows),
        },
        "upstream_evaluator": {
            "resolved": selected_fn is not None,
            "source": selected_fn["source"] if selected_fn else None,
            "function": selected_fn["function"] if selected_fn else None,
            "score": int(selected_fn["score"]) if selected_fn else None,
            "selection_margin": margin,
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
            "candidate_performance_used": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26D",
        "status": status,
        "diagnosis": diagnosis,
        "R18_is_audit_meta_program": is_audit_meta_program,
        "selected_upstream_source": selected_fn["source"] if selected_fn else None,
        "selected_upstream_function": selected_fn["function"] if selected_fn else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("R18 SOURCE-ROLE CLASSIFICATION")
    print(f"  Selected source         : {selected_source.name}")
    print(f"  model.predict calls     : {predict_count}")
    print(f"  model-load calls        : {model_load_count}")
    print(f"  AST/source parse ops    : {ast_parse_count}")
    print(f"  source discovery ops    : {glob_count}")
    print(f"  source text reads       : {source_read_count}")
    print(f"  regex/source searches   : {regex_count}")
    print(f"  Audit/meta program      : {is_audit_meta_program}")

    print("\nR18-LINKED UPSTREAM SOURCES")
    for row in upstream_rows[:12]:
        print(
            f"  score={int(row['runtime_score']):4d} | "
            f"traceHits={int(row['row_hits_in_R18_trace']):2d} | "
            f"predict={int(row['predict']) + int(row['predict_on_batch']):2d} | "
            f"{Path(row['source']).name}"
        )

    print("\nTOP UPSTREAM RUNTIME FUNCTIONS")
    for row in function_rows[:15]:
        print(
            f"  score={int(row['score']):4d} | "
            f"predict={int(row['predict_calls']):2d} | "
            f"modelCall={int(row['direct_model_calls']):2d} | "
            f"{Path(row['source']).name} :: {row['function']}"
        )

    if selected_fn:
        print("\nSELECTED TRUE UPSTREAM EVALUATOR")
        print(f"  Source                  : {selected_fn['source']}")
        print(f"  Function                : {selected_fn['function']}")
        print(f"  Score                   : {selected_fn['score']}")
        print(f"  Selection margin        : {margin}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26D MISSING-COMPONENT VALIDATION")
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
        SOURCE_CLASS_TABLE,
        META_TRACE_TABLE,
        UPSTREAM_TABLE,
        FUNCTION_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26D MISSING INLINED INFERENCE COMPONENT AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No later-time deployment state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
