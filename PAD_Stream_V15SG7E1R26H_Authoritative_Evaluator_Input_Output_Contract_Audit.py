from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict

# =============================================================================
# PAD-Stream V15-SG7E1R26H
# Authoritative Evaluator Input / Output Contract Audit
#
# DIAGNOSTIC-ONLY EXECUTABLE-CONTRACT MILESTONE
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
# R26G established:
#
#   AUTHORITATIVE_UPSTREAM_EVALUATOR_SOURCE_RESOLVED
#
# and selected:
#
#   PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py
#
# as the authoritative upstream evaluator parent.
#
# R26H does NOT search for any alternative evaluator source.
#
# R26H binds the exact executable contract of the authoritative B10 source:
#
#   persisted inputs
#       -> physical-time / xi / tau feature construction
#       -> frozen-model load
#       -> model.predict(...) call
#       -> raw model output
#       -> reshape / clipping / correction / guard semantics
#       -> final deployable state
#       -> persisted artifact key(s)
#
# R26H does not execute new physical-time states. It only proves that the
# authoritative source has one sufficiently explicit input/output contract for
# the next 100-day runtime-control milestone.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26H"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R26G_DIR = ROOT / "output" / "V15_SG7E1R26G"
R26G_SUMMARY = R26G_DIR / "PAD_Stream_V15SG7E1R26G_Summary.json"
R26G_CONTRACT = R26G_DIR / "V15SG7E1R26G_Final_Evaluator_Parent_Consumer_Contract.json"

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SOURCE_TABLE = OUT / "V15SG7E1R26H_Authoritative_Source_Identity.csv"
MODEL_TABLE = OUT / "V15SG7E1R26H_Model_Load_Contract.csv"
PREDICT_TABLE = OUT / "V15SG7E1R26H_Model_Predict_Call_Contract.csv"
INPUT_TABLE = OUT / "V15SG7E1R26H_Predict_Input_Dependency_Trace.csv"
TIME_TABLE = OUT / "V15SG7E1R26H_Time_Xi_Tau_Transform_Contract.csv"
OUTPUT_TABLE = OUT / "V15SG7E1R26H_Raw_Output_Postprocessing_Trace.csv"
SERIAL_TABLE = OUT / "V15SG7E1R26H_Deployment_State_Serialization_Trace.csv"
BINDING_TABLE = OUT / "V15SG7E1R26H_Persisted_Input_Output_Binding.csv"
DECISION_TABLE = OUT / "V15SG7E1R26H_Executable_Contract_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26H_Authoritative_Evaluator_IO_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26H_Summary.json"


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


def frozen_key_inventory():
    if not R1F3_FROZEN.exists():
        return set()
    import numpy as np
    db = np.load(R1F3_FROZEN, allow_pickle=True)
    keys = set(db.files)
    db.close()
    return keys


def source_assignment_inventory(tree, text):
    rows = []
    by_target = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        targets = []
        for t in node.targets:
            targets.extend(flatten_targets(t))

        rhs = node.value
        row = {
            "line": node.lineno,
            "targets": ";".join(targets),
            "rhs": node_src(text, rhs),
            "rhs_symbols": ";".join(names_in(rhs)),
            "rhs_call": call_name(rhs) if isinstance(rhs, ast.Call) else "",
        }
        rows.append(row)

        for t in targets:
            by_target[t] = row

    return rows, by_target


def recursive_dependency_trace(seed_symbols, by_target):
    rows = []
    frontier = list(seed_symbols)
    seen = set()

    while frontier:
        sym = frontier.pop()
        if sym in seen:
            continue
        seen.add(sym)

        if sym not in by_target:
            continue

        row = by_target[sym]
        rows.append({
            "symbol": sym,
            "assignment_line": row["line"],
            "rhs": row["rhs"],
            "rhs_symbols": row["rhs_symbols"],
        })

        for dep in filter(None, row["rhs_symbols"].split(";")):
            if dep not in seen:
                frontier.append(dep)

    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26H")
    print("Authoritative Evaluator Input / Output Contract Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
NO ALTERNATIVE EVALUATOR SOURCE WILL BE SEARCHED.
""")

    s26g = load_json(R26G_SUMMARY)
    c26g = load_json(R26G_CONTRACT)

    if s26g.get("status") != "AUTHORITATIVE_UPSTREAM_EVALUATOR_SOURCE_RESOLVED":
        raise RuntimeError("R26H requires resolved R26G evaluator authority.")

    selected_source = Path(s26g["selected_source"])
    if not selected_source.exists():
        raise FileNotFoundError(selected_source)

    if selected_source.name != "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py":
        raise RuntimeError(
            "R26H expected authoritative source SG7B10, got "
            f"{selected_source.name}"
        )

    model_rows = load_csv(R18_MODEL)
    if len(model_rows) != 1:
        raise RuntimeError("Expected one authoritative frozen model record.")

    model_path = Path(model_rows[0]["path"])
    model_name = model_path.name
    model_sha = model_rows[0]["sha256"]

    text = safe_text(selected_source)
    tree = ast.parse(text)

    save_csv(SOURCE_TABLE, [{
        "source": str(selected_source),
        "source_name": selected_source.name,
        "R26G_status_reproduced": True,
        "authoritative_model_name": model_name,
        "authoritative_model_sha256": model_sha,
    }])

    assignments, by_target = source_assignment_inventory(tree, text)

    # -------------------------------------------------------------------------
    # Model-load contract
    # -------------------------------------------------------------------------

    model_load_rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node)
        low = cname.lower()
        expr = node_src(text, node)

        if "load_model" in low or ".keras" in expr.lower():
            model_load_rows.append({
                "line": getattr(node, "lineno", ""),
                "call": cname,
                "expression": expr[:4000],
                "references_authoritative_model_name": model_name.lower() in expr.lower(),
                "references_authoritative_model_sha": model_sha.lower() in expr.lower(),
            })

    save_csv(MODEL_TABLE, model_load_rows)

    # -------------------------------------------------------------------------
    # Predict-call contract
    # -------------------------------------------------------------------------

    predict_rows = []
    predict_nodes = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node)
        low = cname.lower()

        if ".predict" in low or "predict_on_batch" in low:
            predict_nodes.append(node)

            predict_rows.append({
                "line": getattr(node, "lineno", ""),
                "call": cname,
                "expression": node_src(text, node)[:4000],
                "argument_symbols": ";".join(names_in(node)),
            })

    save_csv(PREDICT_TABLE, predict_rows)

    # -------------------------------------------------------------------------
    # Predict-input dependencies
    # -------------------------------------------------------------------------

    input_rows = []

    for pnode in predict_nodes:
        seeds = names_in(pnode)
        deps = recursive_dependency_trace(seeds, by_target)

        for row in deps:
            input_rows.append({
                "predict_line": getattr(pnode, "lineno", ""),
                **row,
            })

    save_csv(INPUT_TABLE, input_rows)

    # -------------------------------------------------------------------------
    # Time / xi / tau transform contract
    # -------------------------------------------------------------------------

    time_rows = []

    for row in assignments:
        blob = (row["targets"] + " " + row["rhs"]).lower()

        if any(tok in blob for tok in (
            "time_days",
            "t_days",
            "physical_time",
            "days",
            "xi",
            "tau",
            "tof",
            "normalize",
            "scale",
            "log1p",
        )):
            time_rows.append(row)

    save_csv(TIME_TABLE, time_rows)

    # -------------------------------------------------------------------------
    # Raw output -> deployment state postprocessing
    # -------------------------------------------------------------------------

    predict_outputs = set()

    for row in assignments:
        low_rhs = row["rhs"].lower()
        if ".predict" in low_rhs or "predict_on_batch" in low_rhs:
            predict_outputs.update(filter(None, row["targets"].split(";")))

    downstream = set(predict_outputs)
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

    output_rows = []

    for row in assignments:
        targets = set(filter(None, row["targets"].split(";")))

        if not targets.intersection(downstream):
            continue

        blob = (row["targets"] + " " + row["rhs"]).lower()

        semantic_score = 0
        evidence = []

        for tok, val in (
            ("corrected", 50),
            ("candidate", 40),
            ("state", 35),
            ("saturation", 30),
            ("deploy", 30),
            ("prediction", 15),
        ):
            if tok in blob:
                semantic_score += val
                evidence.append(tok)

        for tok, val in (
            ("mask", -20),
            ("weight", -15),
            ("metric", -20),
            ("loss", -40),
            ("residual", -5),
        ):
            if tok in blob:
                semantic_score += val
                evidence.append(f"neg:{tok}")

        output_rows.append({
            "line": row["line"],
            "targets": row["targets"],
            "rhs": row["rhs"],
            "semantic_score": semantic_score,
            "evidence": ";".join(evidence),
        })

    output_rows.sort(
        key=lambda r: int(r["semantic_score"]),
        reverse=True,
    )

    save_csv(OUTPUT_TABLE, output_rows)

    # -------------------------------------------------------------------------
    # Serialization of downstream state
    # -------------------------------------------------------------------------

    serial_rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node).lower()

        if "savez" not in cname and "np.save" not in cname:
            continue

        expr = node_src(text, node)
        syms = names_in(node)
        state_syms = sorted(set(syms).intersection(downstream))

        serial_rows.append({
            "line": getattr(node, "lineno", ""),
            "call": call_name(node),
            "expression": expr[:5000],
            "downstream_state_symbols": ";".join(state_syms),
            "state_symbol_count": len(state_syms),
        })

    save_csv(SERIAL_TABLE, serial_rows)

    # -------------------------------------------------------------------------
    # Persisted input/output binding
    # -------------------------------------------------------------------------

    frozen_keys = frozen_key_inventory()
    combined_input_text = "\n".join(
        row["rhs"] for row in input_rows
    ).lower()

    binding_rows = []

    for key in sorted(frozen_keys):
        direct = key.lower() in combined_input_text

        if direct:
            binding_rows.append({
                "key": key,
                "role": "PERSISTED_INPUT_DIRECT_SOURCE_MATCH",
                "evidence": "predict-input dependency chain",
            })

    # Track serialized downstream state aliases as output candidates.
    for row in serial_rows:
        for sym in filter(None, row["downstream_state_symbols"].split(";")):
            binding_rows.append({
                "key": sym,
                "role": "SERIALIZED_DOWNSTREAM_STATE_SYMBOL",
                "evidence": f"serializer_line_{row['line']}",
            })

    save_csv(BINDING_TABLE, binding_rows)

    # -------------------------------------------------------------------------
    # Readiness decision
    # -------------------------------------------------------------------------

    model_load_present = len(model_load_rows) > 0
    predict_present = len(predict_rows) > 0
    input_trace_present = len(input_rows) > 0
    time_contract_present = len(time_rows) > 0
    postprocess_present = len(output_rows) > 0
    serialization_present = len(serial_rows) > 0

    # Strong executable-contract readiness requires the actual source to show:
    # model inference + feature dependency chain + time semantics + downstream
    # state semantics. Serialization is useful but not strictly required if the
    # state remains in-memory before a later consumer persists it.
    ready = (
        predict_present
        and input_trace_present
        and time_contract_present
        and postprocess_present
    )

    if ready:
        status = "AUTHORITATIVE_EVALUATOR_IO_CONTRACT_READY"
        diagnosis = (
            "SG7B10_MODEL_INPUT_TIME_TRANSFORM_PREDICTION_AND_POSTPROCESSING_CHAIN_RESOLVED"
        )
        recommendation = (
            "The authoritative SG7B10 evaluator parent now has a source-level executable "
            "input/output contract: model inference, predictor-input dependencies, physical-time/"
            "xi/tau transforms, and downstream state postprocessing are explicitly traced. "
            "Proceed to an execution-controlled 100-day replay using only this SG7B10 contract. "
            "Require closure to L2_independent_100 under the unchanged R25R float32 envelope "
            "before any 250/500/1000-day evaluation."
        )
        next_milestone = (
            "V15-SG7E1R26I — Authoritative SG7B10 100-Day Runtime Control"
        )
    else:
        status = "AUTHORITATIVE_EVALUATOR_IO_CONTRACT_INCOMPLETE"
        diagnosis = (
            "SG7B10_SOURCE_AUTHORITY_RESOLVED_BUT_ONE_OR_MORE_EXECUTABLE_IO_COMPONENTS_REMAIN_UNBOUND"
        )
        recommendation = (
            "Do not execute later-time states. Audit only the missing SG7B10 component(s) "
            "identified by R26H: model load, predict call, input dependency, time transform, "
            "or downstream postprocessing. Do not reopen evaluator-source selection."
        )
        next_milestone = (
            "V15-SG7E1R26I — Missing SG7B10 Executable Contract Component Audit"
        )

    checks = [
        ("Incoming R26G evaluator authority reproduced", True),
        ("Authoritative source fixed to SG7B10", True),
        ("No alternative source search performed", True),
        ("Authoritative model identity retained", len(model_rows) == 1),
        ("Model-load contract audited", True),
        ("Prediction calls audited", True),
        ("Prediction-input dependency chain audited", True),
        ("Physical-time/xi/tau transforms audited", True),
        ("Raw-output postprocessing audited", True),
        ("Deployment-state serialization audited", True),
        ("Frozen input/output bindings audited", True),
        ("No new later-time state generated", True),
        ("No training performed", True),
        ("No threshold changed or relaxed", True),
    ]

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(selected_source),
        "model_load_records": len(model_load_rows),
        "predict_records": len(predict_rows),
        "input_dependency_records": len(input_rows),
        "time_transform_records": len(time_rows),
        "postprocess_records": len(output_rows),
        "serialization_records": len(serial_rows),
        "binding_records": len(binding_rows),
        "io_contract_ready": ready,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26H",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(selected_source),
        "authoritative_model": {
            "path": str(model_path),
            "filename": model_name,
            "sha256": model_sha,
        },
        "io_contract": {
            "model_load_records": len(model_load_rows),
            "predict_records": len(predict_rows),
            "input_dependency_records": len(input_rows),
            "time_transform_records": len(time_rows),
            "postprocess_records": len(output_rows),
            "serialization_records": len(serial_rows),
            "binding_records": len(binding_rows),
            "ready": ready,
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
            "alternative_source_search_performed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26H",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(selected_source),
        "io_contract_ready": ready,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("AUTHORITATIVE EVALUATOR")
    print(f"  Source                  : {selected_source.name}")
    print(f"  Model                   : {model_name}")
    print(f"  Model SHA-256           : {model_sha}")

    print("\nEXECUTABLE I/O CONTRACT")
    print(f"  Model-load records      : {len(model_load_rows)}")
    print(f"  Predict calls           : {len(predict_rows)}")
    print(f"  Input dependency records: {len(input_rows)}")
    print(f"  Time/xi/tau records     : {len(time_rows)}")
    print(f"  Postprocess records     : {len(output_rows)}")
    print(f"  Serialization records   : {len(serial_rows)}")
    print(f"  Persisted bindings      : {len(binding_rows)}")
    print(f"  Contract ready          : {ready}")

    print("\nTOP POSTPROCESSING CANDIDATES")
    for row in output_rows[:12]:
        print(
            f"  score={int(row['semantic_score']):3d} | "
            f"line={row['line']} | "
            f"{row['targets']} <- {row['rhs'][:150]}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7E1R26H EXECUTABLE-CONTRACT VALIDATION")
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
        MODEL_TABLE,
        PREDICT_TABLE,
        INPUT_TABLE,
        TIME_TABLE,
        OUTPUT_TABLE,
        SERIAL_TABLE,
        BINDING_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26H AUTHORITATIVE EVALUATOR INPUT / OUTPUT CONTRACT AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No alternative evaluator source was searched.")
    print("No later-time deployment state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
