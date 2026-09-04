from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict

# =============================================================================
# PAD-Stream V15-SG7E1R26E
# R18-Linked Upstream Runtime Source Conflict Audit
#
# DIAGNOSTIC-ONLY SOURCE-RESOLUTION MILESTONE
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
# R26D established:
#
#   R18_CONFIRMED_META_PROGRAM_UPSTREAM_RUNTIME_SOURCE_NOT_YET_UNIQUE
#
# and proved that R18 is a provenance/meta-program rather than a runtime
# evaluator.
#
# R26D's first path-recovery pass still collapsed back onto the R18 audit file
# itself. R26E therefore resolves the actual upstream runtime source using
# several independent provenance channels:
#
#   1. every field/value in the persisted R18 evaluator trace,
#   2. function names / signatures mentioned by R18,
#   3. project-wide Python source inventory,
#   4. exact frozen model filename/path references,
#   5. actual model.predict / predict_on_batch / direct-model-call semantics,
#   6. physical-time + xi + tau/TOF semantics,
#   7. source chronology only as supporting evidence,
#   8. exclusion of the R18 meta-program itself from runtime authority.
#
# No source is selected by candidate performance.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26E"
OUT.mkdir(parents=True, exist_ok=True)

R26D_DIR = ROOT / "output" / "V15_SG7E1R26D"
R26D_SUMMARY = R26D_DIR / "PAD_Stream_V15SG7E1R26D_Summary.json"
R26D_CONTRACT = R26D_DIR / "V15SG7E1R26D_Missing_Inference_Component_Contract.json"

R18_DIR = ROOT / "output" / "V15_SG7E1R18"
R18_EVAL_TRACE = R18_DIR / "V15SG7E1R18_Deployment_Evaluator_Source_Trace.csv"
R18_ARG_CONTRACT = R18_DIR / "V15SG7E1R18_Evaluation_Argument_Contract.csv"
R18_INPUTS = R18_DIR / "V15SG7E1R18_Persisted_Input_Availability.csv"
R18_MODEL = R18_DIR / "V15SG7E1R18_Frozen_Model_Identity.csv"

R18_SOURCE = ROOT / "PAD_Stream_V15SG7E1R18_Missing_L2_Physical_Time_State_Deterministic_Regeneration_Audit.py"

TRACE_SCHEMA_TABLE = OUT / "V15SG7E1R26E_R18_Trace_Schema_Inventory.csv"
TRACE_TOKEN_TABLE = OUT / "V15SG7E1R26E_R18_Trace_Runtime_Tokens.csv"
PROJECT_TABLE = OUT / "V15SG7E1R26E_Project_Runtime_Source_Inventory.csv"
FUNCTION_TABLE = OUT / "V15SG7E1R26E_Runtime_Function_Candidate_Audit.csv"
MODEL_REF_TABLE = OUT / "V15SG7E1R26E_Frozen_Model_Source_Reference_Audit.csv"
CROSSWALK_TABLE = OUT / "V15SG7E1R26E_R18_Trace_to_Project_Source_Crosswalk.csv"
DECISION_TABLE = OUT / "V15SG7E1R26E_Upstream_Runtime_Source_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26E_Upstream_Runtime_Source_Conflict_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26E_Summary.json"


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


def normalize_token(s: str):
    return re.sub(r"[^a-z0-9_]+", " ", str(s).lower()).strip()


def project_python_files():
    return sorted(
        p.resolve()
        for p in ROOT.glob("*.py")
        if p.is_file()
    )


def extract_trace_tokens(rows):
    """
    Extract probable function/source/model/runtime tokens from every R18 trace
    field without assuming a fixed CSV schema.
    """
    schema_rows = []
    token_rows = []
    function_tokens = set()
    file_tokens = set()
    model_tokens = set()
    symbol_tokens = set()

    columns = sorted(set(k for r in rows for k in r))
    for col in columns:
        vals = [str(r.get(col, "")) for r in rows if str(r.get(col, "")).strip()]
        schema_rows.append({
            "column": col,
            "nonempty_records": len(vals),
            "sample": vals[0][:800] if vals else "",
        })

    for idx, row in enumerate(rows):
        for col, value in row.items():
            if value is None:
                continue
            raw = str(value).strip()
            if not raw:
                continue

            kind = []
            extracted = []

            # Python filenames / stems
            for m in re.findall(r"([A-Za-z0-9_.\-]+\.py)", raw, flags=re.I):
                file_tokens.add(m)
                extracted.append(m)
                kind.append("python_file")

            # Keras model names
            for m in re.findall(r"([A-Za-z0-9_.\-]+\.keras)", raw, flags=re.I):
                model_tokens.add(m)
                extracted.append(m)
                kind.append("keras_model")

            # Function-call-like tokens
            for m in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", raw):
                if m not in {
                    "if", "for", "while", "print", "str", "float", "int",
                    "list", "dict", "tuple", "len", "range", "enumerate",
                }:
                    function_tokens.add(m)
                    extracted.append(m)
                    kind.append("function")

            # Explicit function/name/symbol columns
            lcol = col.lower()
            if any(tok in lcol for tok in ("function", "call", "symbol", "name", "evaluator")):
                for m in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", raw):
                    if len(m) >= 3:
                        symbol_tokens.add(m)

            if extracted or any(tok in raw.lower() for tok in (
                "predict", "model", "time", "xi", "tau", "tof", "keras"
            )):
                token_rows.append({
                    "trace_row": idx,
                    "column": col,
                    "raw_value": raw[:1600],
                    "token_kinds": ";".join(sorted(set(kind))),
                    "extracted_tokens": ";".join(sorted(set(extracted))),
                })

    return (
        schema_rows,
        token_rows,
        function_tokens,
        file_tokens,
        model_tokens,
        symbol_tokens,
    )


def audit_source(path: Path, trace_function_tokens, trace_symbols, model_names):
    text = safe_text(path)
    low_text = text.lower()

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None, []

    predict_calls = 0
    predict_on_batch = 0
    load_model_calls = 0
    direct_model_calls = 0
    time_mentions = 0
    xi_mentions = 0
    tau_mentions = 0

    for node in ast.walk(tree):
        src = node_src(text, node).lower()

        if isinstance(node, ast.Call):
            cname = call_name(node).lower()
            if ".predict" in cname:
                predict_calls += 1
            if "predict_on_batch" in cname:
                predict_on_batch += 1
            if "load_model" in cname:
                load_model_calls += 1
            if isinstance(node.func, ast.Name) and node.func.id.lower() in {
                "model", "network", "net", "pirnn", "rnn"
            }:
                direct_model_calls += 1

        if any(tok in src for tok in ("time_days", "t_days", "physical_time", "days")):
            time_mentions += 1
        if "xi" in src:
            xi_mentions += 1
        if "tau" in src or "tof" in src:
            tau_mentions += 1

    matched_functions = sorted(
        t for t in trace_function_tokens
        if re.search(rf"\bdef\s+{re.escape(t)}\s*\(", text)
    )
    matched_symbols = sorted(
        t for t in trace_symbols
        if len(t) >= 4 and re.search(rf"\b{re.escape(t)}\b", text)
    )

    matched_models = sorted(
        m for m in model_names
        if m.lower() in low_text
    )

    self_r18 = path.resolve() == R18_SOURCE.resolve() if R18_SOURCE.exists() else False

    source_score = (
        130 * predict_calls
        + 130 * predict_on_batch
        + 70 * direct_model_calls
        + 40 * load_model_calls
        + 50 * len(matched_models)
        + 35 * len(matched_functions)
        + 3 * min(time_mentions, 15)
        + 2 * min(xi_mentions, 15)
        + 2 * min(tau_mentions, 15)
        + min(len(matched_symbols), 20)
        - (1000 if self_r18 else 0)
    )

    source_row = {
        "source": str(path),
        "is_R18_meta_program": self_r18,
        "predict_calls": predict_calls,
        "predict_on_batch_calls": predict_on_batch,
        "direct_model_calls": direct_model_calls,
        "load_model_calls": load_model_calls,
        "time_mentions": time_mentions,
        "xi_mentions": xi_mentions,
        "tau_tof_mentions": tau_mentions,
        "matched_trace_functions": ";".join(matched_functions),
        "matched_trace_function_count": len(matched_functions),
        "matched_trace_symbol_count": len(matched_symbols),
        "matched_model_names": ";".join(matched_models),
        "runtime_source_score": source_score,
    }

    function_rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        pred = 0
        direct = 0
        load = 0
        time = 0
        xi = 0
        tau = 0
        returns = 0

        for sub in ast.walk(node):
            src = node_src(text, sub).lower()

            if isinstance(sub, ast.Call):
                cname = call_name(sub).lower()
                if ".predict" in cname or "predict_on_batch" in cname:
                    pred += 1
                if "load_model" in cname:
                    load += 1
                if isinstance(sub.func, ast.Name) and sub.func.id.lower() in {
                    "model", "network", "net", "pirnn", "rnn"
                }:
                    direct += 1

            if isinstance(sub, ast.Return):
                returns += 1
            if any(tok in src for tok in ("time_days", "t_days", "physical_time", "days")):
                time += 1
            if "xi" in src:
                xi += 1
            if "tau" in src or "tof" in src:
                tau += 1

        trace_name_match = node.name in trace_function_tokens or node.name in trace_symbols

        fscore = (
            170 * pred
            + 90 * direct
            + 40 * load
            + 70 * int(trace_name_match)
            + 5 * min(time, 10)
            + 3 * min(xi, 10)
            + 3 * min(tau, 10)
            + 10 * int(returns > 0)
        )

        if node.name == "main":
            fscore -= 25
        if "audit" in node.name.lower():
            fscore -= 40
        if "train" in node.name.lower() or "fit" in node.name.lower():
            fscore -= 250

        function_rows.append({
            "source": str(path),
            "function": node.name,
            "line": node.lineno,
            "parameters": ";".join(a.arg for a in node.args.args),
            "predict_calls": pred,
            "direct_model_calls": direct,
            "load_model_calls": load,
            "time_mentions": time,
            "xi_mentions": xi,
            "tau_tof_mentions": tau,
            "return_count": returns,
            "trace_name_match": trace_name_match,
            "function_score": fscore,
        })

    return source_row, function_rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26E")
    print("R18-Linked Upstream Runtime Source Conflict Audit")
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

    s26d = load_json(R26D_SUMMARY)
    c26d = load_json(R26D_CONTRACT)

    if s26d.get("status") != "R18_CONFIRMED_META_PROGRAM_UPSTREAM_RUNTIME_SOURCE_NOT_YET_UNIQUE":
        raise RuntimeError("R26E requires R26D upstream-runtime-source conflict.")

    if not bool(s26d.get("R18_is_audit_meta_program")):
        raise RuntimeError("R26E requires R18 to be classified as audit/meta-program.")

    trace_rows = load_csv(R18_EVAL_TRACE)
    if not trace_rows:
        raise RuntimeError("R18 evaluator trace is missing or empty.")

    (
        schema_rows,
        token_rows,
        trace_function_tokens,
        trace_file_tokens,
        trace_model_tokens,
        trace_symbols,
    ) = extract_trace_tokens(trace_rows)

    save_csv(TRACE_SCHEMA_TABLE, schema_rows)
    save_csv(TRACE_TOKEN_TABLE, token_rows)

    # -------------------------------------------------------------------------
    # Frozen model identity gives another strong, independent source anchor.
    # -------------------------------------------------------------------------

    model_rows = load_csv(R18_MODEL)
    model_names = set(trace_model_tokens)

    for r in model_rows:
        for k, v in r.items():
            if v and ".keras" in str(v).lower():
                model_names.add(Path(str(v)).name)

    # -------------------------------------------------------------------------
    # Project-wide source inventory, but runtime authority is scored only from
    # R18 trace semantics + actual inference semantics + exact model reference.
    # -------------------------------------------------------------------------

    project_rows = []
    function_rows = []

    for path in project_python_files():
        source_row, frows = audit_source(
            path,
            trace_function_tokens,
            trace_symbols,
            model_names,
        )
        if source_row is not None:
            project_rows.append(source_row)
            function_rows.extend(frows)

    project_rows.sort(
        key=lambda r: (
            int(r["runtime_source_score"]),
            int(r["predict_calls"]) + int(r["predict_on_batch_calls"]),
        ),
        reverse=True,
    )
    function_rows.sort(
        key=lambda r: (
            int(r["function_score"]),
            int(r["predict_calls"]),
        ),
        reverse=True,
    )

    save_csv(PROJECT_TABLE, project_rows)
    save_csv(FUNCTION_TABLE, function_rows)

    # Exact model-source reference table
    model_ref_rows = []
    for row in project_rows:
        if row["matched_model_names"]:
            model_ref_rows.append({
                "source": row["source"],
                "matched_model_names": row["matched_model_names"],
                "predict_calls": row["predict_calls"],
                "predict_on_batch_calls": row["predict_on_batch_calls"],
                "runtime_source_score": row["runtime_source_score"],
            })
    save_csv(MODEL_REF_TABLE, model_ref_rows)

    # -------------------------------------------------------------------------
    # Crosswalk explicit trace filenames/function tokens to project sources.
    # -------------------------------------------------------------------------

    crosswalk_rows = []

    for row in project_rows:
        path = Path(row["source"])
        filename_match = (
            path.name in trace_file_tokens
            or any(path.name.lower() == t.lower() for t in trace_file_tokens)
        )
        function_count = int(row["matched_trace_function_count"])
        model_match = bool(row["matched_model_names"])
        runtime_calls = int(row["predict_calls"]) + int(row["predict_on_batch_calls"]) + int(row["direct_model_calls"])

        cross_score = (
            200 * int(filename_match)
            + 100 * int(model_match)
            + 60 * function_count
            + 80 * runtime_calls
            + int(row["runtime_source_score"])
        )

        crosswalk_rows.append({
            "source": row["source"],
            "filename_match_R18_trace": filename_match,
            "trace_function_matches": function_count,
            "model_reference_match": model_match,
            "runtime_call_count": runtime_calls,
            "source_runtime_score": row["runtime_source_score"],
            "crosswalk_score": cross_score,
            "is_R18_meta_program": row["is_R18_meta_program"],
        })

    crosswalk_rows.sort(
        key=lambda r: int(r["crosswalk_score"]),
        reverse=True,
    )
    save_csv(CROSSWALK_TABLE, crosswalk_rows)

    # -------------------------------------------------------------------------
    # Select a true upstream runtime source/function.
    # R18 itself is categorically excluded.
    # -------------------------------------------------------------------------

    eligible_sources = [
        r for r in crosswalk_rows
        if not bool(r["is_R18_meta_program"])
        and int(r["runtime_call_count"]) > 0
        and (
            bool(r["filename_match_R18_trace"])
            or bool(r["model_reference_match"])
            or int(r["trace_function_matches"]) > 0
        )
    ]

    selected_source = None
    source_margin = 0

    if eligible_sources:
        top = eligible_sources[0]
        second = int(eligible_sources[1]["crosswalk_score"]) if len(eligible_sources) > 1 else -999
        source_margin = int(top["crosswalk_score"]) - second

        # Require either a unique candidate or a meaningful provenance margin.
        if len(eligible_sources) == 1 or source_margin >= 50:
            selected_source = top

    selected_function = None
    function_margin = 0

    if selected_source:
        feligible = [
            r for r in function_rows
            if r["source"] == selected_source["source"]
            and (
                int(r["predict_calls"]) > 0
                or int(r["direct_model_calls"]) > 0
            )
            and int(r["function_score"]) > 0
        ]

        if feligible:
            topf = feligible[0]
            secondf = int(feligible[1]["function_score"]) if len(feligible) > 1 else -999
            function_margin = int(topf["function_score"]) - secondf
            if len(feligible) == 1 or function_margin >= 30:
                selected_function = topf

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    if selected_source and selected_function:
        status = "TRUE_UPSTREAM_RUNTIME_SOURCE_AND_FUNCTION_RESOLVED"
        diagnosis = (
            "R18_TRACE_MODEL_REFERENCE_AND_RUNTIME_SEMANTICS_CONVERGE_ON_ONE_UPSTREAM_EVALUATOR"
        )
        recommendation = (
            "The R18 meta-program is now cleanly separated from the actual runtime evaluator. "
            "R18 trace semantics, project source structure, frozen-model references, and real "
            "inference calls converge on one upstream source/function. Preserve this identity "
            "and proceed to bind its exact input tensors, physical-time transform, model output, "
            "and postprocessing/return semantics. Do not use R18 main() as the evaluator again."
        )
        next_milestone = (
            "V15-SG7E1R26F — True Upstream Evaluator Input / Return Binding Audit"
        )

    else:
        status = "TRUE_UPSTREAM_RUNTIME_SOURCE_CONFLICT_REMAINS"
        diagnosis = (
            "R18_TRACE_AND_PROJECT_RUNTIME_SEMANTICS_DO_NOT_YET_YIELD_ONE_UNIQUE_EVALUATOR"
        )
        recommendation = (
            "Do not generate later-time states. Audit only the top R26E crosswalk candidates. "
            "Use exact frozen-model load provenance and R18 trace function/symbol evidence to "
            "separate them; do not use candidate performance."
        )
        next_milestone = (
            "V15-SG7E1R26F — Top Upstream Evaluator Source Lineage Conflict Audit"
        )

    checks = [
        ("Incoming R26D conflict reproduced", True),
        ("R18 remains classified as meta-program", True),
        ("R18 evaluator trace schema inventoried", len(schema_rows) > 0),
        ("R18 runtime tokens extracted", len(token_rows) > 0),
        ("Project Python sources inventoried", len(project_rows) > 0),
        ("Actual inference calls audited project-wide", True),
        ("Frozen model source references audited", True),
        ("R18 meta-program excluded from runtime authority", True),
        ("Trace-to-project crosswalk constructed", True),
        ("No source selected by numerical performance", True),
        ("No later-time state generated", True),
        ("No fabricated feature used", True),
        ("No training performed", True),
    ]

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "trace_row_count": len(trace_rows),
        "trace_function_token_count": len(trace_function_tokens),
        "trace_file_token_count": len(trace_file_tokens),
        "trace_model_token_count": len(model_names),
        "project_source_count": len(project_rows),
        "eligible_source_count": len(eligible_sources),
        "selected_source": selected_source["source"] if selected_source else "",
        "source_margin": source_margin,
        "selected_function": selected_function["function"] if selected_function else "",
        "function_margin": function_margin,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26E",
        "status": status,
        "diagnosis": diagnosis,
        "R18_meta_program_excluded": True,
        "trace_inventory": {
            "rows": len(trace_rows),
            "function_tokens": sorted(trace_function_tokens),
            "file_tokens": sorted(trace_file_tokens),
            "model_tokens": sorted(model_names),
        },
        "upstream_runtime_evaluator": {
            "resolved": selected_source is not None and selected_function is not None,
            "source": selected_source["source"] if selected_source else None,
            "source_score": int(selected_source["crosswalk_score"]) if selected_source else None,
            "source_margin": source_margin,
            "function": selected_function["function"] if selected_function else None,
            "function_score": int(selected_function["function_score"]) if selected_function else None,
            "function_margin": function_margin,
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
        "milestone": "V15-SG7E1R26E",
        "status": status,
        "diagnosis": diagnosis,
        "selected_upstream_source": selected_source["source"] if selected_source else None,
        "selected_upstream_function": selected_function["function"] if selected_function else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("R18 TRACE TOKEN INVENTORY")
    print(f"  Trace rows              : {len(trace_rows)}")
    print(f"  Function tokens         : {len(trace_function_tokens)}")
    print(f"  Python file tokens      : {len(trace_file_tokens)}")
    print(f"  Model tokens            : {len(model_names)}")
    print(f"  Symbol tokens           : {len(trace_symbols)}")

    print("\nTOP TRACE-TO-PROJECT SOURCE CANDIDATES")
    for row in crosswalk_rows[:15]:
        print(
            f"  score={int(row['crosswalk_score']):5d} | "
            f"runtime={int(row['runtime_call_count']):2d} | "
            f"fnMatch={int(row['trace_function_matches']):2d} | "
            f"modelRef={row['model_reference_match']} | "
            f"{Path(row['source']).name}"
        )

    print("\nTOP RUNTIME FUNCTION CANDIDATES")
    for row in function_rows[:15]:
        print(
            f"  score={int(row['function_score']):4d} | "
            f"predict={int(row['predict_calls']):2d} | "
            f"direct={int(row['direct_model_calls']):2d} | "
            f"traceName={row['trace_name_match']} | "
            f"{Path(row['source']).name} :: {row['function']}"
        )

    if selected_source and selected_function:
        print("\nSELECTED TRUE UPSTREAM RUNTIME EVALUATOR")
        print(f"  Source                  : {selected_source['source']}")
        print(f"  Source score / margin   : {selected_source['crosswalk_score']} / {source_margin}")
        print(f"  Function                : {selected_function['function']}")
        print(f"  Function score / margin : {selected_function['function_score']} / {function_margin}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26E UPSTREAM SOURCE CONFLICT VALIDATION")
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
        TRACE_SCHEMA_TABLE,
        TRACE_TOKEN_TABLE,
        PROJECT_TABLE,
        FUNCTION_TABLE,
        MODEL_REF_TABLE,
        CROSSWALK_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26E R18-LINKED UPSTREAM RUNTIME SOURCE CONFLICT AUDIT: COMPLETE")
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
