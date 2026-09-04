from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R11
# SG7B10 Raw100 Serialization / Postprocessing Closure Audit
#
# DIAGNOSTIC-ONLY POSTPROCESSING LINEAGE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POSTPROCESSING OPERATOR WILL BE SELECTED BY NUMERICAL PERFORMANCE.
#
# PURPOSE
# -------
# R26I-R10 proved:
#
#   correct SG7B10 model + source-authentic X100 -> valid raw100 runtime output
#
# but:
#
#   Linf(raw100, frozen100) = 9.418756e-03
#
# which is far outside the unchanged precision envelope.
#
# Therefore the unresolved chain is now:
#
#   model.predict(... )[:,:,0]
#       -> historical postprocessing / serialization
#       -> frozen100
#
# R26I-R11 audits ONLY source/serialization provenance between those states.
# It does NOT choose a transform because it reduces error.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR11"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"

R10_DIR = ROOT / "output" / "V15_SG7E1R26IR10"
R10_SUMMARY = R10_DIR / "PAD_Stream_V15SG7E1R26IR10_Summary.json"
R10_NUM = R10_DIR / "V15SG7E1R26IR10_100d_Runtime_Control.npz"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# Outputs
RAW_ASSIGN_TABLE = OUT / "V15SG7E1R26IR11_Raw_Prediction_Assignment_Trace.csv"
POST_TABLE = OUT / "V15SG7E1R26IR11_Postprocessing_Operation_Trace.csv"
SERIAL_TABLE = OUT / "V15SG7E1R26IR11_Serialization_Trace.csv"
FROZEN_TRACE_TABLE = OUT / "V15SG7E1R26IR11_Frozen100_Source_Lineage.csv"
CANDIDATE_TABLE = OUT / "V15SG7E1R26IR11_Postprocessing_Candidate_Contract.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR11_Raw100_Postprocessing_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR11_Raw100_Postprocessing_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR11_Summary.json"


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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def find_function(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def assignment_map(scope, text):
    rows = []
    amap = {}

    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    rec = {
                        "line": node.lineno,
                        "target": tgt.id,
                        "rhs": node_src(text, node.value),
                        "rhs_node": node.value,
                    }
                    rows.append(rec)
                    amap[tgt.id] = rec

    return rows, amap


def find_raw_prediction_assignments(func, text):
    rows = []

    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue

        rhs = node.value
        rhs_text = node_src(text, rhs)

        if "predict" not in rhs_text:
            continue

        targets = [
            tgt.id
            for tgt in node.targets
            if isinstance(tgt, ast.Name)
        ]

        rows.append({
            "line": node.lineno,
            "targets": ";".join(targets),
            "rhs": rhs_text,
        })

    return rows


def recursive_symbol_trace(seed, amap):
    rows = []
    seen = set()
    frontier = [seed]

    while frontier:
        sym = frontier.pop()
        if sym in seen:
            continue
        seen.add(sym)

        if sym not in amap:
            continue

        rec = amap[sym]
        rhs_node = rec["rhs_node"]

        deps = sorted({
            n.id for n in ast.walk(rhs_node)
            if isinstance(n, ast.Name)
        })

        rows.append({
            "symbol": sym,
            "line": rec["line"],
            "rhs": rec["rhs"],
            "dependencies": ";".join(deps),
        })

        frontier.extend([d for d in deps if d not in seen])

    return rows


def postprocess_ops_from_trace(trace_rows):
    rows = []

    for rec in trace_rows:
        rhs = rec["rhs"]
        low = rhs.lower()

        ops = []
        if "clip" in low:
            ops.append("CLIP")
        if "where" in low:
            ops.append("WHERE")
        if "maximum" in low or "minimum" in low:
            ops.append("MINMAX")
        if "astype" in low:
            ops.append("CAST")
        if "copy" in low:
            ops.append("COPY")
        if "reshape" in low:
            ops.append("RESHAPE")
        if "squeeze" in low:
            ops.append("SQUEEZE")
        if "[:, :, 0]" in rhs or "[:,:,0]" in rhs:
            ops.append("CHANNEL_SELECT")
        if "guard" in low:
            ops.append("GUARD")
        if "gamma" in low:
            ops.append("GAMMA")
        if "residual" in low:
            ops.append("RESIDUAL")
        if "front" in low:
            ops.append("FRONT")
        if "frozen" in low:
            ops.append("FROZEN")
        if "candidate" in low:
            ops.append("CANDIDATE")

        rows.append({
            "symbol": rec["symbol"],
            "line": rec["line"],
            "rhs": rhs,
            "operation_tags": ";".join(ops),
        })

    return rows


def serializer_trace(tree, text):
    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node)
        if cname not in {"np.savez", "np.savez_compressed"}:
            continue

        positional = [
            node_src(text, a)
            for a in node.args
        ]

        for kw in node.keywords:
            rows.append({
                "line": node.lineno,
                "serializer": cname,
                "artifact_expression": positional[0] if positional else "",
                "key": kw.arg or "",
                "value_expression": node_src(text, kw.value),
            })

    return rows


def project_python_files():
    return sorted(ROOT.glob("PAD_Stream_*.py"))


def frozen100_source_lineage():
    """
    Search project source only for source-level persistence or assignments
    mentioning frozen100. No performance-based inference.
    """
    rows = []

    for path in project_python_files():
        text = safe_text(path)
        if "frozen100" not in text:
            continue

        try:
            tree = ast.parse(text)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == "frozen100":
                        rows.append({
                            "source": str(path),
                            "line": node.lineno,
                            "kind": "ASSIGNMENT",
                            "expression": node_src(text, node.value),
                        })

            if isinstance(node, ast.Call):
                cname = call_name(node)
                if cname in {"np.savez", "np.savez_compressed"}:
                    for kw in node.keywords:
                        if kw.arg == "frozen100":
                            rows.append({
                                "source": str(path),
                                "line": node.lineno,
                                "kind": "SERIALIZATION",
                                "expression": node_src(text, kw.value),
                            })

    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R11")
    print("SG7B10 Raw100 Serialization / Postprocessing Closure Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO X100 WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POSTPROCESSING OPERATOR WILL BE SELECTED BY NUMERICAL PERFORMANCE.
""")

    prev = load_json(R10_SUMMARY)
    if prev.get("status") != "SG7B10_BOUND_100D_RAW_RUNTIME_CONTROL_EXECUTED_CLOSURE_FAILED":
        raise RuntimeError("R26I-R11 requires R10 raw-runtime closure failure.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    if not R10_NUM.exists():
        raise FileNotFoundError(R10_NUM)

    text = safe_text(SOURCE)
    tree = ast.parse(text)

    eval_func = find_function(tree, "evaluate_candidate")
    if eval_func is None:
        raise RuntimeError("Missing evaluate_candidate().")

    assign_rows, amap = assignment_map(eval_func, text)
    raw_rows = find_raw_prediction_assignments(eval_func, text)
    save_csv(RAW_ASSIGN_TABLE, raw_rows)

    raw_symbols = []
    for row in raw_rows:
        raw_symbols.extend([s for s in row["targets"].split(";") if s])

    trace_rows = []
    for sym in raw_symbols:
        trace_rows.extend(recursive_symbol_trace(sym, amap))

    # Deduplicate by symbol/line.
    dedup = {}
    for r in trace_rows:
        dedup[(r["symbol"], r["line"])] = r
    trace_rows = list(dedup.values())

    post_rows = postprocess_ops_from_trace(trace_rows)
    save_csv(POST_TABLE, post_rows)

    serial_rows = serializer_trace(tree, text)
    save_csv(SERIAL_TABLE, serial_rows)

    frozen_rows = frozen100_source_lineage()
    save_csv(FROZEN_TRACE_TABLE, frozen_rows)

    # Candidate source operators are provenance records only.
    candidate_rows = []
    for r in post_rows:
        tags = r["operation_tags"]
        if tags:
            candidate_rows.append({
                "source": str(SOURCE),
                "line": r["line"],
                "symbol": r["symbol"],
                "operation_tags": tags,
                "expression": r["rhs"],
                "authority": "SOURCE_PROVENANCE_ONLY",
            })

    # Include frozen100 creator expressions from historical lineage.
    for r in frozen_rows:
        candidate_rows.append({
            "source": r["source"],
            "line": r["line"],
            "symbol": "frozen100",
            "operation_tags": r["kind"],
            "expression": r["expression"],
            "authority": "FROZEN100_CREATION_PROVENANCE",
        })

    save_csv(CANDIDATE_TABLE, candidate_rows)

    # Load numerical context for identity only.
    db = np.load(R10_NUM, allow_pickle=True)
    raw100 = np.asarray(db["raw100"])
    frozen100 = np.asarray(db["frozen100"])
    db.close()

    raw_hash = sha256_array(raw100)
    frozen_hash = sha256_array(frozen100)

    # Decision logic is provenance-based:
    # resolved only if there is an explicit frozen100 creator expression that
    # directly references a raw-model symbol / direct SG7B10 output lineage.
    explicit_creator = False
    creator_rows = []

    raw_token_set = set(raw_symbols) | {"deployment_prediction", "raw100"}

    for r in frozen_rows:
        expr = r["expression"]
        if any(tok in expr for tok in raw_token_set):
            explicit_creator = True
            creator_rows.append(r)

    if explicit_creator:
        status = "SG7B10_RAW100_TO_FROZEN100_POSTPROCESSING_PATH_RESOLVED"
        diagnosis = (
            "EXPLICIT_SOURCE_CREATION_LINEAGE_CONNECTS_SG7B10_RAW_PREDICTION_TO_FROZEN100"
        )
        recommendation = (
            "The historical source explicitly links the SG7B10 raw prediction to frozen100 through "
            "a deterministic postprocessing/serialization chain. Reconstruct only that exact chain "
            "at 100 days and require closure under the unchanged precision envelope before any "
            "later-time generation."
        )
        next_milestone = (
            "V15-SG7E1R26I-R12 — Exact Raw100-to-Frozen100 Postprocessing Replay"
        )
    else:
        status = "SG7B10_RAW100_TO_FROZEN100_POSTPROCESSING_PATH_NOT_YET_UNIQUE"
        diagnosis = (
            "SOURCE_POSTPROCESSING_AND_FROZEN100_CREATION_RECORDS_EXIST_BUT_NO_SINGLE_DIRECT_CHAIN_IS_YET_EXPLICIT"
        )
        recommendation = (
            "Do not generate later-time states. Audit only the frozen100 creation/serialization "
            "sources listed by R11 and trace their immediate input symbols backward until one direct "
            "SG7B10 raw-prediction lineage is reached. Do not choose an operator by numerical error."
        )
        next_milestone = (
            "V15-SG7E1R26I-R12 — Frozen100 Immediate-Input Lineage Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "raw_prediction_assignment_count": len(raw_rows),
        "postprocessing_records": len(post_rows),
        "serialization_records": len(serial_rows),
        "frozen100_lineage_records": len(frozen_rows),
        "explicit_raw_to_frozen_creator": explicit_creator,
        "raw100_sha256": raw_hash,
        "frozen100_sha256": frozen_hash,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R11",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "raw100_identity": {
            "sha256": raw_hash,
            "shape": list(raw100.shape),
            "dtype": str(raw100.dtype),
        },
        "frozen100_identity": {
            "sha256": frozen_hash,
            "shape": list(frozen100.shape),
            "dtype": str(frozen100.dtype),
        },
        "raw_prediction_assignments": raw_rows,
        "postprocessing_trace": post_rows,
        "frozen100_creation_lineage": frozen_rows,
        "explicit_creator_rows": creator_rows,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "model_predict_executed": False,
            "X100_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "operator_selected_by_performance": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R11",
        "status": status,
        "diagnosis": diagnosis,
        "explicit_postprocessing_path_resolved": explicit_creator,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("RAW PREDICTION ASSIGNMENTS")
    print(f"  Records                 : {len(raw_rows)}")
    for r in raw_rows:
        print(f"  line={r['line']} | {r['targets']} <- {r['rhs']}")

    print("\nPOSTPROCESSING TRACE")
    print(f"  Records                 : {len(post_rows)}")
    for r in post_rows[:20]:
        print(
            f"  line={r['line']} | {r['symbol']} | "
            f"{r['operation_tags']} | {r['rhs']}"
        )

    print("\nFROZEN100 CREATION LINEAGE")
    print(f"  Records                 : {len(frozen_rows)}")
    for r in frozen_rows[:20]:
        print(
            f"  {Path(r['source']).name} | line={r['line']} | "
            f"{r['kind']} | {r['expression']}"
        )

    print("\nIDENTITY")
    print(f"  raw100 SHA-256          : {raw_hash}")
    print(f"  frozen100 SHA-256       : {frozen_hash}")

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
        RAW_ASSIGN_TABLE,
        POST_TABLE,
        SERIAL_TABLE,
        FROZEN_TRACE_TABLE,
        CANDIDATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R11 RAW100 SERIALIZATION / POSTPROCESSING AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No X100 tensor was changed.")
    print("No postprocessing operator was selected by numerical performance.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
