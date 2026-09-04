from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R8
# SG7B10 Deployment-Predict Model Object / Architecture Binding Audit
#
# DIAGNOSTIC-ONLY RUNTIME-CONTRACT REPAIR
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R26I-R7 failed with:
#
#   expected shape=(None, 2)
#   found shape=(1024, 201, 2)
#
# R26I-R6 already proved that SG7B10 source-authentically constructs:
#
#   X100.shape = (2662, 201, 2)
#
# Therefore the failure is NOT an X100-construction problem.
#
# The contradiction is now between:
#
#   SG7B10 deployment input contract: (2662, 201, 2)
#   currently bound model input:       (None, 2)
#
# R26I-R8 audits the EXACT model object consumed by the SG7B10 deployment
# prediction call. It traces:
#
#   deployment_prediction = model.predict(...)
#       -> model function parameter
#       -> evaluate_candidate(...) caller
#       -> caller argument
#       -> candidate_model / model assignment
#       -> tf.keras.models.load_model(path)
#       -> exact model artifact path
#
# The audit does not select a model by performance or filename similarity.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR8"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"

PREV_SUMMARY = (
    ROOT / "output" / "V15_SG7E1R26IR6"
    / "PAD_Stream_V15SG7E1R26IR6_Summary.json"
)

# Outputs
PREDICT_TABLE = OUT / "V15SG7E1R26IR8_Deployment_Predict_Call.csv"
FUNCTION_TABLE = OUT / "V15SG7E1R26IR8_Evaluate_Candidate_Function_Contract.csv"
CALLER_TABLE = OUT / "V15SG7E1R26IR8_Evaluate_Candidate_Caller_Binding.csv"
MODEL_ASSIGN_TABLE = OUT / "V15SG7E1R26IR8_Model_Object_Assignment_Trace.csv"
LOAD_TABLE = OUT / "V15SG7E1R26IR8_Model_Load_Path_Trace.csv"
CANDIDATE_TABLE = OUT / "V15SG7E1R26IR8_Model_Artifact_Candidate_Binding.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR8_Model_Object_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR8_Deployment_Model_Object_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR8_Summary.json"


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def assignment_map(scope, text):
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
                    "rhs": node_src(text, node.value),
                    "rhs_node": node.value,
                }
                amap[tgt.id] = rec
                rows.append(rec)
    return rows, amap


def find_deployment_predict(func, text):
    rows = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        cname = call_name(node)
        if not cname.endswith(".predict"):
            continue

        expr = node_src(text, node)
        if "X100" not in expr:
            continue

        model_expr = node_src(text, node.func.value) if isinstance(node.func, ast.Attribute) else ""

        rows.append({
            "line": node.lineno,
            "call": cname,
            "model_expression": model_expr,
            "expression": expr,
        })
    return rows


def function_parameter_rows(func):
    return [{
        "function": func.name,
        "parameter_index": i,
        "parameter": arg.arg,
    } for i, arg in enumerate(func.args.args)]


def caller_bindings(tree, func_name, func_params, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if call_name(node) != func_name:
            continue

        for i, arg in enumerate(node.args):
            rows.append({
                "call_line": node.lineno,
                "parameter_index": i,
                "parameter": func_params[i] if i < len(func_params) else "",
                "argument_expression": node_src(text, arg),
                "argument_type": type(arg).__name__,
            })

        for kw in node.keywords:
            rows.append({
                "call_line": node.lineno,
                "parameter_index": "",
                "parameter": kw.arg or "",
                "argument_expression": node_src(text, kw.value),
                "argument_type": type(kw.value).__name__,
            })
    return rows


def trace_symbol(symbol, amap, text):
    rows = []
    seen = set()
    cur = symbol

    while cur and cur not in seen and cur in amap:
        seen.add(cur)
        rec = amap[cur]
        rhs_node = rec["rhs_node"]

        rows.append({
            "symbol": cur,
            "line": rec["line"],
            "rhs": rec["rhs"],
            "rhs_type": type(rhs_node).__name__,
            "call_name": call_name(rhs_node) if isinstance(rhs_node, ast.Call) else "",
        })

        # Follow simple aliases only.
        if isinstance(rhs_node, ast.Name):
            cur = rhs_node.id
        else:
            break

    return rows


def extract_load_model_records(scope, text):
    rows = []
    for node in ast.walk(scope):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue

        cname = call_name(node.value)
        if not cname.endswith("load_model"):
            continue

        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        path_expr = node_src(text, node.value.args[0]) if node.value.args else ""

        rows.append({
            "line": node.lineno,
            "target": ";".join(targets),
            "call": cname,
            "path_expression": path_expr,
            "full_expression": node_src(text, node.value),
        })
    return rows


def project_model_files():
    exts = {".keras", ".h5", ".hdf5"}
    return sorted(
        p.resolve()
        for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in exts
    )


def score_model_candidate(path: Path, path_expression: str, assignment_symbol: str):
    score = 0
    reasons = []

    pstr = str(path)
    name = path.name

    # Exact literal filename/path evidence.
    if name in path_expression:
        score += 2000
        reasons.append("filename_literal_in_load_expression")
    if pstr in path_expression:
        score += 4000
        reasons.append("full_path_literal_in_load_expression")

    # Candidate/model variable semantics.
    low = path_expression.lower()
    if "candidate" in low:
        if "candidate" in name.lower():
            score += 300
            reasons.append("candidate_semantics")

    if assignment_symbol and assignment_symbol.lower() in {"candidate_model", "model"}:
        score += 100
        reasons.append("model_assignment_target")

    # SG7B10-produced models are strong only if source expression points there.
    if "sg7b10" in str(path).lower() and "candidate" in low:
        score += 250
        reasons.append("SG7B10_candidate_lineage")

    return score, reasons


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R8")
    print("SG7B10 Deployment-Predict Model Object / Architecture Binding Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO X100 WILL BE CHANGED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
MODEL AUTHORITY WILL BE RESOLVED ONLY FROM SG7B10 CALLER/LOAD PROVENANCE.
""")

    prev = load_json(PREV_SUMMARY)
    if prev.get("status") != "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_FULLY_RESOLVED":
        raise RuntimeError("R26I-R8 requires successful R26I-R6 X100 constructor.")

    text = safe_text(SOURCE)
    tree = ast.parse(text)

    eval_func = find_function(tree, "evaluate_candidate")
    if eval_func is None:
        raise RuntimeError("Could not locate evaluate_candidate().")

    predict_rows = find_deployment_predict(eval_func, text)
    save_csv(PREDICT_TABLE, predict_rows)

    params = [a.arg for a in eval_func.args.args]
    save_csv(FUNCTION_TABLE, function_parameter_rows(eval_func))

    caller_rows = caller_bindings(tree, "evaluate_candidate", params, text)
    save_csv(CALLER_TABLE, caller_rows)

    # Determine which parameter is the model object in deployment predict.
    model_exprs = sorted({
        r["model_expression"]
        for r in predict_rows
        if r["model_expression"]
    })

    model_param = model_exprs[0] if len(model_exprs) == 1 else None

    # Caller argument(s) bound to that parameter.
    model_args = sorted({
        r["argument_expression"]
        for r in caller_rows
        if r["parameter"] == model_param
    }) if model_param else []

    # Main/source assignment map.
    source_rows, amap = assignment_map(tree, text)

    trace_rows = []
    for arg in model_args:
        if re.fullmatch(r"[A-Za-z_]\w*", arg):
            trace_rows.extend(trace_symbol(arg, amap, text))

    save_csv(MODEL_ASSIGN_TABLE, trace_rows)

    # Load-model statements in authoritative source.
    load_rows = extract_load_model_records(tree, text)
    save_csv(LOAD_TABLE, load_rows)

    # Match caller-bound symbols to load_model targets.
    relevant_loads = []
    traced_symbols = {r["symbol"] for r in trace_rows}
    traced_symbols.update(model_args)

    for row in load_rows:
        targets = set(filter(None, row["target"].split(";")))
        if targets & traced_symbols:
            relevant_loads.append(row)

    # Also include load rows whose target appears directly as model arg.
    if not relevant_loads:
        for row in load_rows:
            if row["target"] in model_args:
                relevant_loads.append(row)

    models = project_model_files()
    candidate_rows = []

    for load in relevant_loads:
        target = load["target"].split(";")[0] if load["target"] else ""
        for path in models:
            score, reasons = score_model_candidate(
                path,
                load["path_expression"],
                target,
            )
            if score <= 0:
                continue

            candidate_rows.append({
                "load_line": load["line"],
                "load_target": target,
                "path_expression": load["path_expression"],
                "artifact": str(path),
                "filename": path.name,
                "sha256": sha256_file(path),
                "score": score,
                "reasons": ";".join(reasons),
            })

    candidate_rows.sort(key=lambda r: int(r["score"]), reverse=True)
    save_csv(CANDIDATE_TABLE, candidate_rows)

    selected = None
    margin = 0

    if candidate_rows:
        top = candidate_rows[0]
        second = int(candidate_rows[1]["score"]) if len(candidate_rows) > 1 else -999999
        margin = int(top["score"]) - second

        # Require direct load-expression evidence or a substantial margin.
        direct = (
            "filename_literal_in_load_expression" in top["reasons"]
            or "full_path_literal_in_load_expression" in top["reasons"]
        )

        if direct or len(candidate_rows) == 1 or margin >= 1000:
            selected = top

    if selected:
        status = "SG7B10_DEPLOYMENT_PREDICT_MODEL_OBJECT_BOUND"
        diagnosis = (
            "EVALUATE_CANDIDATE_CALLER_AND_LOAD_MODEL_LINEAGE_IDENTIFY_EXACT_RUNTIME_MODEL_ARTIFACT"
        )
        recommendation = (
            "The model object consumed by SG7B10 deployment prediction is now bound from the "
            "evaluate_candidate caller/load chain. Use this exact model artifact—not the prior "
            "CR3F4 model assumption—to audit architecture compatibility with the already-frozen "
            "(2662,201,2) X100 tensor before any inference."
        )
        next_milestone = (
            "V15-SG7E1R26I-R9 — Bound SG7B10 Model Architecture / X100 Compatibility Audit"
        )
    else:
        status = "SG7B10_DEPLOYMENT_PREDICT_MODEL_OBJECT_STILL_AMBIGUOUS"
        diagnosis = (
            "EVALUATE_CANDIDATE_MODEL_PARAMETER_REACHES_MULTIPLE_OR_UNRESOLVED_MODEL_LOAD_PATHS"
        )
        recommendation = (
            "Do not call model.predict. Audit only the evaluate_candidate model caller argument "
            "and the relevant SG7B10 load_model path expression(s). Do not select a model by "
            "runtime performance or filename similarity."
        )
        next_milestone = (
            "V15-SG7E1R26I-R9 — Final SG7B10 Model Load-Path Binding Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "deployment_predict_records": len(predict_rows),
        "model_parameter": model_param or "",
        "model_argument_candidates": ";".join(model_args),
        "relevant_load_records": len(relevant_loads),
        "model_artifact_candidates": len(candidate_rows),
        "selected_artifact": selected["artifact"] if selected else "",
        "selected_sha256": selected["sha256"] if selected else "",
        "selection_margin": margin,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R8",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "deployment_predict": {
            "records": predict_rows,
            "model_parameter": model_param,
            "caller_arguments": model_args,
        },
        "selected_model": {
            "resolved": selected is not None,
            "artifact": selected["artifact"] if selected else None,
            "sha256": selected["sha256"] if selected else None,
            "load_target": selected["load_target"] if selected else None,
            "path_expression": selected["path_expression"] if selected else None,
        },
        "known_X100_contract": {
            "shape": [2662, 201, 2],
            "dtype": "float32",
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "model_predict_executed": False,
            "X100_changed": False,
            "threshold_changed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R8",
        "status": status,
        "diagnosis": diagnosis,
        "selected_model_artifact": selected["artifact"] if selected else None,
        "selected_model_sha256": selected["sha256"] if selected else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("DEPLOYMENT PREDICT CONTRACT")
    print(f"  Predict calls           : {len(predict_rows)}")
    print(f"  Model parameter         : {model_param}")
    print(f"  Caller argument(s)      : {model_args}")

    print("\nRELEVANT MODEL LOADS")
    print(f"  Records                 : {len(relevant_loads)}")
    for row in relevant_loads:
        print(
            f"  line={row['line']} | {row['target']} <- "
            f"{row['call']}({row['path_expression']})"
        )

    print("\nMODEL ARTIFACT CANDIDATES")
    for row in candidate_rows[:12]:
        print(
            f"  score={int(row['score']):5d} | "
            f"{row['filename']} | {row['sha256'][:16]}"
        )

    if selected:
        print("\nSELECTED SG7B10 RUNTIME MODEL")
        print(f"  Artifact                : {selected['artifact']}")
        print(f"  SHA-256                 : {selected['sha256']}")
        print(f"  Score / margin          : {selected['score']} / {margin}")

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
        PREDICT_TABLE,
        FUNCTION_TABLE,
        CALLER_TABLE,
        MODEL_ASSIGN_TABLE,
        LOAD_TABLE,
        CANDIDATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R8 SG7B10 MODEL OBJECT / ARCHITECTURE BINDING AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No X100 tensor was changed.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
