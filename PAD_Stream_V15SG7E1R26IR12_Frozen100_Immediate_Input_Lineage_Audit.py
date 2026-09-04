from __future__ import annotations

from pathlib import Path
import ast
import csv
import json


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR12"
OUT.mkdir(parents=True, exist_ok=True)

R11_DIR = ROOT / "output" / "V15_SG7E1R26IR11"
R11_SUMMARY = R11_DIR / "PAD_Stream_V15SG7E1R26IR11_Summary.json"
R11_FROZEN_TABLE = R11_DIR / "V15SG7E1R26IR11_Frozen100_Source_Lineage.csv"

SOURCE_TABLE = OUT / "V15SG7E1R26IR12_Frozen100_Source_Priority.csv"
IMMEDIATE_TABLE = OUT / "V15SG7E1R26IR12_Frozen100_Immediate_Input_Trace.csv"
SYMBOL_TABLE = OUT / "V15SG7E1R26IR12_Immediate_Input_Symbol_Lineage.csv"
MODEL_TABLE = OUT / "V15SG7E1R26IR12_Frozen_Model_Predict_Lineage.csv"
TIME_TABLE = OUT / "V15SG7E1R26IR12_Frozen_Array_Time_Index_Lineage.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR12_Frozen100_Immediate_Input_Decision.csv"
CONTRACT_FILE = OUT / "V15SG7E1R26IR12_Frozen100_Immediate_Input_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR12_Summary.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def assignment_map(tree, text):
    amap = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    amap[tgt.id] = {
                        "line": node.lineno,
                        "rhs": node_src(text, node.value),
                        "rhs_node": node.value,
                    }
    return amap


def direct_name_dependencies(node):
    return sorted({n.id for n in ast.walk(node) if isinstance(n, ast.Name)})


def trace_symbol(symbol, amap):
    rows = []
    seen = set()
    frontier = [symbol]
    while frontier:
        sym = frontier.pop(0)
        if sym in seen:
            continue
        seen.add(sym)
        if sym not in amap:
            rows.append({
                "symbol": sym,
                "line": "",
                "rhs": "",
                "dependencies": "",
                "resolved_assignment": False,
            })
            continue
        rec = amap[sym]
        deps = direct_name_dependencies(rec["rhs_node"])
        rows.append({
            "symbol": sym,
            "line": rec["line"],
            "rhs": rec["rhs"],
            "dependencies": ";".join(deps),
            "resolved_assignment": True,
        })
        for dep in deps:
            if dep not in seen:
                frontier.append(dep)
    return rows


def classify_source(row):
    source = Path(row["source"]).name
    expr = row["expression"]
    compact = expr.replace(" ", "").replace("\n", "")
    score = 0
    reasons = []
    if "frozen_model.predict" in expr:
        score += 1000
        reasons.append("direct_frozen_model_predict")
    if "frozen[idx100]" in compact:
        score += 700
        reasons.append("direct_time_slice_from_frozen_array")
    if row["kind"] == "SERIALIZATION":
        score += 300
        reasons.append("frozen100_serialization")
    if "V15SG7B16" in source:
        score += 220
        reasons.append("late_SG7B_frozen_source")
    if "V15SG7B13" in source:
        score += 200
        reasons.append("SG7B_frozen_source")
    if "V15SG7CR3F5R1A2_Authoritative_Serialization_Runtime" in source:
        score += 180
        reasons.append("authoritative_serialization_runtime")
    if "V15SG7CR3F5R1C_Independent_Exact_Array_Support_Extension_Validation" in source:
        score += 160
        reasons.append("independent_exact_array_validation")
    return score, reasons


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R12")
    print("Frozen100 Immediate-Input Lineage Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO X100 WILL BE CHANGED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SOURCE WILL BE SELECTED BY NUMERICAL PERFORMANCE.
""")

    prev = load_json(R11_SUMMARY)
    if prev.get("status") != "SG7B10_RAW100_TO_FROZEN100_POSTPROCESSING_PATH_NOT_YET_UNIQUE":
        raise RuntimeError("R26I-R12 requires unresolved R11 postprocessing lineage.")

    frozen_rows = load_csv(R11_FROZEN_TABLE)

    priority_rows = []
    for row in frozen_rows:
        score, reasons = classify_source(row)
        priority_rows.append({
            **row,
            "provenance_score": score,
            "provenance_reasons": ";".join(reasons),
        })
    priority_rows.sort(key=lambda r: int(r["provenance_score"]), reverse=True)
    save_csv(SOURCE_TABLE, priority_rows)

    immediate_rows, symbol_rows, model_rows, time_rows = [], [], [], []
    top_rows = [r for r in priority_rows if int(r["provenance_score"]) >= 500]

    for row in top_rows:
        path = Path(row["source"])
        if not path.exists():
            continue
        text = safe_text(path)
        try:
            tree = ast.parse(text)
        except Exception:
            continue

        amap = assignment_map(tree, text)
        expr = row["expression"]
        deps = []
        try:
            expr_node = ast.parse(expr, mode="eval").body
            deps = direct_name_dependencies(expr_node)
        except Exception:
            pass

        immediate_rows.append({
            "source": str(path),
            "line": row["line"],
            "kind": row["kind"],
            "frozen100_expression": expr,
            "immediate_dependencies": ";".join(deps),
            "provenance_score": row["provenance_score"],
            "provenance_reasons": row["provenance_reasons"],
        })

        for dep in deps:
            for tr in trace_symbol(dep, amap):
                symbol_rows.append({
                    "source": str(path),
                    "root_dependency": dep,
                    **tr,
                })

        if "frozen_model.predict" in expr and "frozen_model" in amap:
            rhs = amap["frozen_model"]["rhs"]
            model_rows.append({
                "source": str(path),
                "line": amap["frozen_model"]["line"],
                "symbol": "frozen_model",
                "expression": rhs,
                "contains_load_model": "load_model" in rhs,
            })

        compact = expr.replace(" ", "").replace("\n", "")
        if "frozen[idx100]" in compact:
            time_rows.append({
                "source": str(path),
                "frozen_line": amap.get("frozen", {}).get("line", ""),
                "frozen_expression": amap.get("frozen", {}).get("rhs", ""),
                "idx100_line": amap.get("idx100", {}).get("line", ""),
                "idx100_expression": amap.get("idx100", {}).get("rhs", ""),
            })

    save_csv(IMMEDIATE_TABLE, immediate_rows)
    save_csv(SYMBOL_TABLE, symbol_rows)
    save_csv(MODEL_TABLE, model_rows)
    save_csv(TIME_TABLE, time_rows)

    direct_predict = [r for r in immediate_rows if "direct_frozen_model_predict" in r["provenance_reasons"]]
    direct_time_slice = [r for r in immediate_rows if "direct_time_slice_from_frozen_array" in r["provenance_reasons"]]

    if len(direct_predict) == 1:
        status = "FROZEN100_IMMEDIATE_INPUT_DIRECT_MODEL_PREDICT_RESOLVED"
        diagnosis = "ONE_HISTORICAL_FROZEN100_CREATOR_DIRECTLY_CONSUMES_A_FROZEN_MODEL_PREDICTION"
        recommendation = (
            "Resolve the exact frozen_model artifact and deployment/X100 identity in this creator "
            "source, then compare its 100-day prediction lineage to the R10 runtime path without "
            "changing any numerical operator."
        )
        next_milestone = "V15-SG7E1R26I-R13 — Frozen100 Creator Model / X100 Identity Reconciliation Audit"
    elif len(direct_predict) > 1:
        status = "FROZEN100_IMMEDIATE_INPUT_DIRECT_MODEL_PREDICT_CONFLICT"
        diagnosis = "MULTIPLE_HISTORICAL_FROZEN100_CREATORS_DIRECTLY_CONSUME_FROZEN_MODEL_PREDICTIONS"
        recommendation = (
            "Audit only the direct frozen-model creator lineages using model artifact hashes, "
            "deployment workspace identities, and parent milestone provenance. Do not choose by "
            "numerical closeness."
        )
        next_milestone = "V15-SG7E1R26I-R13 — Direct Frozen100 Creator Lineage Conflict Audit"
    elif direct_time_slice:
        status = "FROZEN100_IMMEDIATE_INPUT_RESOLVED_TO_TIME_SLICE_OF_FROZEN_ARRAY"
        diagnosis = "HISTORICAL_FROZEN100_IS_CONSUMED_AS_FROZEN_IDX100_AND_REQUIRES_FROZEN_ARRAY_ORIGIN_TRACE"
        recommendation = (
            "Trace the origin of the multi-time frozen array and idx100 in the highest-authority "
            "source. Do not infer the source model from numerical similarity."
        )
        next_milestone = "V15-SG7E1R26I-R13 — Multi-Time Frozen Array Origin Audit"
    else:
        status = "FROZEN100_IMMEDIATE_INPUT_LINEAGE_STILL_UNRESOLVED"
        diagnosis = "NO_HIGH_AUTHORITY_FROZEN100_CREATOR_YIELDS_A_UNIQUE_IMMEDIATE_INPUT_SEMANTIC"
        recommendation = (
            "Audit only the top-ranked R12 source records and their immediate dependencies; do not "
            "reopen model/X100 discovery globally."
        )
        next_milestone = "V15-SG7E1R26I-R13 — Top Frozen100 Creator Source Audit"

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "source_records": len(priority_rows),
        "high_value_records": len(top_rows),
        "direct_predict_records": len(direct_predict),
        "direct_time_slice_records": len(direct_time_slice),
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R12",
        "status": status,
        "diagnosis": diagnosis,
        "source_priority": priority_rows,
        "immediate_input_trace": immediate_rows,
        "model_predict_lineage": model_rows,
        "time_slice_lineage": time_rows,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "model_predict_executed": False,
            "X100_changed": False,
            "threshold_changed": False,
            "source_selected_by_performance": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R12",
        "status": status,
        "diagnosis": diagnosis,
        "direct_predict_records": len(direct_predict),
        "direct_time_slice_records": len(direct_time_slice),
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("TOP FROZEN100 CREATOR SOURCES")
    for r in priority_rows[:12]:
        print(f"  score={int(r['provenance_score']):4d} | {Path(r['source']).name} | {r['kind']} | {r['expression']}")

    print("\nDIRECT FROZEN-MODEL CREATOR RECORDS")
    print(f"  Count                   : {len(direct_predict)}")
    for r in direct_predict:
        print(f"  {Path(r['source']).name} | line={r['line']} | {r['frozen100_expression']}")

    print("\nFROZEN[idx100] RECORDS")
    print(f"  Count                   : {len(direct_time_slice)}")
    for r in direct_time_slice[:10]:
        print(f"  {Path(r['source']).name} | line={r['line']} | {r['frozen100_expression']}")

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
    for p in (SOURCE_TABLE, IMMEDIATE_TABLE, SYMBOL_TABLE, MODEL_TABLE, TIME_TABLE, DECISION_TABLE):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R12 FROZEN100 IMMEDIATE-INPUT LINEAGE AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No X100 tensor was changed.")
    print("No source was selected by numerical performance.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
