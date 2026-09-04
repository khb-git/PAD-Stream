from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re

import numpy as np

# =============================================================================
# PAD-Stream V16A-R7C3
# Final Producer Metadata Provenance Audit
#
# PURPOSE
# -------
# R7C2 established that persisted producer-group and terminal arrays do not,
# by themselves, define one executable producer_id rule.
#
# R7C3 audits only the remaining metadata provenance:
#   - exact SG5/SG6 producer-capture source semantics,
#   - source constants / producer coordinate definitions,
#   - terminal endpoint creation and use,
#   - whether producer identity was ever a transient runtime-only attribute,
#   - whether any summary/JSON/CSV artifact contains producer capture labels,
#   - whether a source-authentic endpoint-to-producer mapping rule exists.
#
# IMPORTANT
# ---------
# R7C3 DOES NOT reconstruct producer_id.
# It only decides whether reconstruction is source-authentically possible
# without Pollock retracing.
# =============================================================================

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R7C3_FINAL_PRODUCER_METADATA_PROVENANCE_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R7C2_DIR = ROOT / "output" / "V16_A_R7C2_PRODUCER_GROUP_TERMINAL_METADATA_RESOLUTION"
R7C2_SUMMARY = R7C2_DIR / "PAD_Stream_V16AR7C2_Summary.json"

SOURCE_RULES = OUT / "V16AR7C3_Source_Producer_Capture_Rule_Trace.csv"
PRODUCER_GEOM = OUT / "V16AR7C3_Producer_Definition_Geometry_Trace.csv"
TRANSIENT = OUT / "V16AR7C3_Transient_Runtime_Producer_Attribute_Audit.csv"
TEXT_META = OUT / "V16AR7C3_JSON_CSV_Summary_Producer_Metadata_Audit.csv"
ENDPOINT_RULE = OUT / "V16AR7C3_Endpoint_to_Producer_Rule_Decision.csv"
GATES = OUT / "V16AR7C3_Final_Provenance_Gates.csv"
DECISION = OUT / "V16AR7C3_Final_Producer_Metadata_Decision.csv"
CONTRACT = OUT / "V16AR7C3_Final_Producer_Metadata_Provenance_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR7C3_Summary.json"

PRODUCER_NAMES = ["PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE"]

def save_csv(path, rows):
    rows = list(rows)
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

def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def sha_file(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""):
            h.update(c)
    return h.hexdigest()

def ast_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""

def sources():
    out = []
    for p in sorted(list(ROOT.glob("PAD_Stream_V15SG5*.py")) + list(ROOT.glob("PAD_Stream_V15SG6*.py"))):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except Exception:
            continue
        out.append((p,text,tree))
    return out

def audit_source_rules(srcs):
    rows = []
    geom = []
    transient = []

    for p,text,tree in srcs:
        lines = text.splitlines()

        # text-level source semantics
        for i,line in enumerate(lines,1):
            low = line.lower()

            if any(tok in low for tok in ["producer", "capture", "terminal", "endpoint", "destination"]):
                if any(tok in low for tok in ["argmin", "nearest", "distance", "norm(", "sqrt(", "cell", "well"]):
                    rows.append({
                        "source": str(p),
                        "source_sha256": sha_file(p),
                        "line": i,
                        "text": line.strip()[:900],
                        "uses_distance": any(tok in low for tok in ["argmin", "nearest", "distance", "norm(", "sqrt("]),
                        "uses_cell": "cell" in low,
                        "uses_well": "well" in low,
                        "uses_terminal": ("terminal" in low or "endpoint" in low),
                    })

            if any(name.lower() in low for name in [x.lower() for x in PRODUCER_NAMES]):
                geom.append({
                    "source": str(p),
                    "source_sha256": sha_file(p),
                    "line": i,
                    "text": line.strip()[:900],
                })

            if any(tok in low for tok in ["producer_id", "producer_idx", "producer_index", "captured_by", "target_producer", "terminal_producer"]):
                transient.append({
                    "source": str(p),
                    "source_sha256": sha_file(p),
                    "line": i,
                    "text": line.strip()[:900],
                })

        # AST-level assignments / returns / dict packing
        for node in ast.walk(tree):
            expr = ast_text(node)
            low = expr.lower()
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Return, ast.Dict, ast.Call)):
                if any(tok in low for tok in ["producer_id", "producer_idx", "captured_by", "terminal_producer", "target_producer"]):
                    transient.append({
                        "source": str(p),
                        "source_sha256": sha_file(p),
                        "line": getattr(node, "lineno", None),
                        "text": expr[:1200],
                    })

    return rows, geom, transient

def audit_text_metadata():
    rows = []
    for ext in ("*.json","*.csv"):
        for p in sorted((ROOT/"output").rglob(ext)) if (ROOT/"output").exists() else []:
            lowp = str(p).lower()
            if "v16_" in lowp or "v16a" in lowp:
                continue
            if not any(tok in lowp for tok in ["sg5","sg6","pollock","streamline"]):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            low = text.lower()
            if any(tok in low for tok in ["producer", "capture", "terminal", "destination"]):
                # record only files that materially mention capture identity
                rows.append({
                    "artifact": str(p),
                    "artifact_sha256": sha_file(p),
                    "mentions_producer": "producer" in low,
                    "mentions_capture": "capture" in low,
                    "mentions_terminal": "terminal" in low,
                    "mentions_destination": "destination" in low,
                    "mentions_PROD_SW": "prod_sw" in low,
                    "mentions_PROD_SE": "prod_se" in low,
                    "mentions_PROD_NW": "prod_nw" in low,
                    "mentions_PROD_NE": "prod_ne" in low,
                })
    return rows

def classify(rule_rows, geom_rows, transient_rows, meta_rows):
    explicit_distance = any(r["uses_distance"] and r["uses_terminal"] and r["uses_well"] for r in rule_rows)
    explicit_cell = any(r["uses_cell"] and r["uses_terminal"] and r["uses_well"] for r in rule_rows)
    all_producers_defined = all(any(name.lower() in r["text"].lower() for r in geom_rows) for name in PRODUCER_NAMES)
    transient_identity = len(transient_rows) > 0
    metadata_mentions_all = any(
        r["mentions_PROD_SW"] and r["mentions_PROD_SE"] and r["mentions_PROD_NW"] and r["mentions_PROD_NE"]
        for r in meta_rows
    )

    if explicit_distance and all_producers_defined:
        return {
            "status": "SOURCE_AUTHENTIC_ENDPOINT_DISTANCE_RULE_BOUND",
            "authorized": True,
            "rule_type": "EXPLICIT_ENDPOINT_TO_PRODUCER_DISTANCE_RULE",
            "reason": "SG5/SG6 explicitly define terminal endpoint classification using producer/well distance and all four producer definitions are source-bound."
        }

    if explicit_cell and all_producers_defined:
        return {
            "status": "SOURCE_AUTHENTIC_TERMINAL_CELL_RULE_BOUND",
            "authorized": True,
            "rule_type": "EXPLICIT_TERMINAL_CELL_TO_PRODUCER_RULE",
            "reason": "SG5/SG6 explicitly define terminal-cell producer classification and all four producer definitions are source-bound."
        }

    if transient_identity and metadata_mentions_all:
        return {
            "status": "TRANSIENT_PRODUCER_ATTRIBUTE_WITH_COMPLETE_METADATA_SUPPORT",
            "authorized": False,
            "rule_type": "TRANSIENT_RUNTIME_IDENTITY_REQUIRES_FINAL_ASSIGNMENT_TRACE",
            "reason": "Producer identity existed transiently and all four producers appear in metadata, but the exact assignment operator is still not bound."
        }

    return {
        "status": "PRODUCER_IDENTITY_NOT_RECOVERABLE_WITHOUT_RETRACE_OR_NEW_RULE",
        "authorized": False,
        "rule_type": "",
        "reason": "No persisted producer_id and no exact executable endpoint/cell mapping rule is bound from frozen SG5/SG6 provenance."
    }

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16A-R7C3")
    print("Final Producer Metadata Provenance Audit")
    print("="*78)
    print("""
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECOMPUTED.
NO PRODUCER ID WILL BE RECONSTRUCTED IN R7C3.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO NEW NEAREST-PRODUCER RULE WILL BE INVENTED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
THIS IS THE FINAL PRODUCER-METADATA PROVENANCE AUDIT.
""")

    if not R7C2_SUMMARY.exists():
        raise FileNotFoundError(R7C2_SUMMARY)

    r7c2 = json.loads(R7C2_SUMMARY.read_text(encoding="utf-8"))
    if r7c2.get("status") != "V16A_PRODUCER_IDENTITY_METADATA_RESOLUTION_STILL_INCOMPLETE":
        raise RuntimeError("R7C3 expects the incomplete R7C2 metadata-resolution status.")

    srcs = sources()
    rule_rows, geom_rows, transient_rows = audit_source_rules(srcs)
    meta_rows = audit_text_metadata()

    save_csv(SOURCE_RULES, rule_rows)
    save_csv(PRODUCER_GEOM, geom_rows)
    save_csv(TRANSIENT, transient_rows)
    save_csv(TEXT_META, meta_rows)

    rule = classify(rule_rows, geom_rows, transient_rows, meta_rows)
    save_csv(ENDPOINT_RULE, [rule])

    print("FINAL PRODUCER PROVENANCE")
    print(f"  Source rule records         : {len(rule_rows)}")
    print(f"  Producer geometry records   : {len(geom_rows)}")
    print(f"  Transient identity records  : {len(transient_rows)}")
    print(f"  Text metadata records       : {len(meta_rows)}")
    print(f"  Rule status                 : {rule['status']}")
    print(f"  Reconstruction authorized   : {rule['authorized']}")
    print(f"  Rule type                   : {rule['rule_type'] or 'NONE'}")

    gates = [
        ("incoming_R7C2_incomplete_status_reproduced", True),
        ("SG5_SG6_source_rule_semantics_audited", True),
        ("producer_geometry_definitions_audited", True),
        ("transient_runtime_identity_audited", True),
        ("JSON_CSV_summary_metadata_audited", True),
        ("final_endpoint_rule_classified", True),
        ("no_producer_id_reconstructed", True),
        ("no_nearest_rule_invented", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_recompute", True),
        ("no_Pollock_retrace", True),
        ("no_FMM", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_V15_mutation", True),
    ]
    save_csv(GATES, [{"gate":g,"passed":p} for g,p in gates])

    if rule["authorized"]:
        status = "V16A_PRODUCER_IDENTITY_SOURCE_RULE_FINAL_BOUND"
        diagnosis = "ONE_EXPLICIT_SOURCE_AUTHENTIC_ENDPOINT_OR_TERMINAL_CELL_CLASSIFICATION_RULE_IS_BOUND"
        recommendation = (
            "Proceed to V16A-R7D controlled producer identity reconstruction using only the bound rule and existing frozen endpoint metadata."
        )
        next_ms = "V16A-R7D — Controlled Producer Identity Reconstruction"
    elif rule["status"] == "TRANSIENT_PRODUCER_ATTRIBUTE_WITH_COMPLETE_METADATA_SUPPORT":
        status = "V16A_PRODUCER_IDENTITY_ONE_ASSIGNMENT_EDGE_SHORT"
        diagnosis = "PRODUCER_IDENTITY_EXISTED_TRANSIENTLY_BUT_THE_EXACT_ASSIGNMENT_OPERATOR_REMAINS_UNBOUND"
        recommendation = (
            "Audit only the final transient producer assignment operator. Do not retrace Pollock."
        )
        next_ms = "V16A-R7C4 — Final Transient Producer Assignment Audit"
    else:
        status = "V16A_PRODUCER_IDENTITY_NOT_RECOVERABLE_WITHOUT_RETRACE"
        diagnosis = "NO_PERSISTED_OR_EXECUTABLY_BOUND_NONRETRACE_PRODUCER_IDENTITY_RULE_REMAINS"
        recommendation = (
            "Record producer_id as unavailable from frozen non-retrace provenance. Decide whether Foundation Case 0001 can freeze without producer_id or whether a post-freeze derived connectivity label may be created from existing endpoints under a new V16 rule."
        )
        next_ms = "V16A-R7E — Producer Identity Scope Limitation / Foundation Case Freeze Decision"

    save_csv(DECISION, [{
        "status": status,
        "diagnosis": diagnosis,
        "rule_status": rule["status"],
        "rule_type": rule["rule_type"],
        "authorized": rule["authorized"],
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT, {
        "milestone":"V16A-R7C3",
        "status":status,
        "diagnosis":diagnosis,
        "rule":rule,
        "constraints":{
            "producer_id_reconstructed":False,
            "nearest_rule_invented":False,
            "SG3_rerun":False,
            "SG4_rerun":False,
            "velocity_recompute":False,
            "Pollock_retrace":False,
            "FMM":False,
            "model_predict":False,
            "training":False,
            "V15_mutation":False,
        },
        "recommendation":recommendation,
        "next_milestone":next_ms,
    })

    save_json(SUMMARY, {
        "milestone":"V16A-R7C3",
        "status":status,
        "diagnosis":diagnosis,
        "rule":rule,
        "recommendation":recommendation,
        "next_milestone":next_ms,
    })

    print("\n"+"="*78)
    print("V16A-R7C3 FINAL PROVENANCE GATES")
    print("="*78)
    for g,p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("="*78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in [SOURCE_RULES, PRODUCER_GEOM, TRANSIENT, TEXT_META, ENDPOINT_RULE, GATES, DECISION]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n"+"="*78)
    print("PAD-STREAM V16A-R7C3 FINAL PRODUCER METADATA PROVENANCE AUDIT: COMPLETE")
    print("="*78)

if __name__ == "__main__":
    main()
