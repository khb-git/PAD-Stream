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
# PAD-Stream V16A-R7C1
# Producer Classification Rule Edge Audit
#
# PURPOSE
# -------
# R7C established:
#   - producer_id is the ONLY remaining V16A residual component
#   - SG5/SG6 contain substantial producer/capture semantics
#   - one terminal metadata record exists
#   - five grouping metadata records exist
#   - but no single executable non-retrace classification rule is yet bound
#
# R7C1 isolates the missing RULE EDGE:
#
#   persisted terminal/grouping metadata
#        -> exact SG5/SG6 producer classification semantics
#        -> one deterministic producer_id rule
#
# This milestone DOES NOT reconstruct producer_id.
#
# It audits:
#   1. exact source expressions around capture/terminal producer assignment,
#   2. producer name <-> index mappings,
#   3. how terminal metadata is created and consumed,
#   4. how grouping metadata is created and consumed,
#   5. whether grouping arrays collectively partition all 1,078 streamlines,
#   6. whether one rule can be bound without inventing nearest-producer logic.
#
# NO SG3 rerun.
# NO SG4 rerun.
# NO velocity recomputation.
# NO Pollock retrace.
# NO FMM.
# NO ML.
# NO V15 mutation.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R7C1_PRODUCER_CLASSIFICATION_RULE_EDGE_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R7C_DIR = ROOT / "output" / "V16_A_R7C_PRODUCER_IDENTITY_FAILURE_AUDIT"
R7C_SUMMARY = R7C_DIR / "PAD_Stream_V16AR7C_Summary.json"
R7C_TERMINAL = R7C_DIR / "V16AR7C_Terminal_Endpoint_Metadata_Inventory.csv"
R7C_GROUPING = R7C_DIR / "V16AR7C_Downstream_Producer_Grouping_Inventory.csv"

SOURCE_EDGE = OUT / "V16AR7C1_Source_Producer_Assignment_Edge_Trace.csv"
MAPPING_EDGE = OUT / "V16AR7C1_Producer_Index_Name_Map_Audit.csv"
TERMINAL_EDGE = OUT / "V16AR7C1_Terminal_Metadata_Creation_Consumer_Trace.csv"
GROUP_EDGE = OUT / "V16AR7C1_Grouping_Metadata_Creation_Consumer_Trace.csv"
PARTITION_AUDIT = OUT / "V16AR7C1_Streamline_Group_Partition_Audit.csv"
RULE_BINDING = OUT / "V16AR7C1_Executable_Producer_Rule_Binding.csv"
GATES = OUT / "V16AR7C1_Final_Rule_Edge_Gates.csv"
DECISION = OUT / "V16AR7C1_Rule_Edge_Decision.csv"
CONTRACT = OUT / "V16AR7C1_Producer_Classification_Rule_Edge_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR7C1_Summary.json"

EXPECTED_STREAMLINES = 1078

PRODUCER_LABEL_HINTS = [
    "PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE",
    "SW", "SE", "NW", "NE"
]

ASSIGNMENT_TERMS = [
    "producer_id", "producer_idx", "producer_index",
    "target_producer", "captured_by", "capture_id",
    "terminal_producer", "destination_id", "well_id",
]

GROUP_TERMS = [
    "producer", "prod_", "capture", "group", "bucket",
    "streamline_ids", "streamline_indices"
]


def save_csv(path: Path, rows):
    rows = list(rows)
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


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def ast_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def assigned_targets(node):
    out = []
    raw = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    for t in raw:
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Tuple):
            for e in t.elts:
                if isinstance(e, ast.Name):
                    out.append(e.id)
    return out


def sg56_sources():
    rows = []
    for p in sorted(list(ROOT.glob("PAD_Stream_V15SG5*.py")) + list(ROOT.glob("PAD_Stream_V15SG6*.py"))):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except Exception:
            continue
        rows.append((p, text, tree))
    return rows


def source_assignment_edge_trace(sources):
    rows = []
    maps = []

    for p, text, tree in sources:
        lines = text.splitlines()

        # AST assignment / conditional / append / dictionary traces
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = assigned_targets(node)
                expr = ast_text(getattr(node, "value", None))
                joined = (" ".join(targets) + " " + expr).lower()

                if any(term in joined for term in ASSIGNMENT_TERMS):
                    rows.append({
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": getattr(node, "lineno", None),
                        "record_type": "ASSIGNMENT",
                        "targets": ";".join(targets),
                        "expression": expr,
                    })

                if "producer" in joined or "prod_" in joined:
                    if any(label.lower() in joined for label in PRODUCER_LABEL_HINTS):
                        maps.append({
                            "source": str(p),
                            "source_sha256": sha256_file(p),
                            "line": getattr(node, "lineno", None),
                            "record_type": "PRODUCER_LABEL_ASSIGNMENT",
                            "expression": ast_text(node),
                        })

            if isinstance(node, ast.Dict):
                expr = ast_text(node)
                low = expr.lower()
                if ("producer" in low or "prod_" in low) and any(
                    label.lower() in low for label in PRODUCER_LABEL_HINTS
                ):
                    maps.append({
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": getattr(node, "lineno", None),
                        "record_type": "PRODUCER_LABEL_DICT",
                        "expression": expr,
                    })

            if isinstance(node, ast.If):
                expr = ast_text(node.test)
                low = expr.lower()
                if "producer" in low or "capture" in low or "terminal" in low:
                    rows.append({
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": getattr(node, "lineno", None),
                        "record_type": "CONDITIONAL",
                        "targets": "",
                        "expression": expr,
                    })

            if isinstance(node, ast.Call):
                fn = ast_text(node.func)
                expr = ast_text(node)
                low = expr.lower()
                if any(term in low for term in ASSIGNMENT_TERMS) and any(
                    tok in fn.lower() for tok in ["append", "extend", "add", "setdefault"]
                ):
                    rows.append({
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": getattr(node, "lineno", None),
                        "record_type": "COLLECTION_WRITE",
                        "targets": "",
                        "expression": expr,
                    })

        # Text context to catch tuple/list producer structures.
        for i, line in enumerate(lines, 1):
            low = line.lower()
            if ("producer" in low or "prod_" in low) and any(
                label.lower() in low for label in PRODUCER_LABEL_HINTS
            ):
                maps.append({
                    "source": str(p),
                    "source_sha256": sha256_file(p),
                    "line": i,
                    "record_type": "TEXT_LABEL_MAP",
                    "expression": line.strip()[:1000],
                })

    return rows, maps


def trace_key_references(key: str, sources):
    rows = []
    if not key:
        return rows

    patt = re.compile(rf"\b{re.escape(key)}\b", re.I)

    for p, text, tree in sources:
        for i, line in enumerate(text.splitlines(), 1):
            if patt.search(line):
                low = line.lower()
                role = "REFERENCE"
                if "np.save" in low or "savez" in low:
                    role = "SERIALIZATION"
                elif "np.load" in low or "load(" in low:
                    role = "LOAD"
                elif "=" in line:
                    role = "ASSIGNMENT_OR_USE"
                elif "append" in low:
                    role = "COLLECTION_WRITE"

                rows.append({
                    "source": str(p),
                    "source_sha256": sha256_file(p),
                    "line": i,
                    "key": key,
                    "role": role,
                    "text": line.strip()[:1000],
                })
    return rows


def metadata_edge_trace(inv_rows, sources):
    rows = []
    for rec in inv_rows:
        key = rec.get("key", "")
        refs = trace_key_references(key, sources)
        if refs:
            for r in refs:
                x = dict(rec)
                x.update({
                    "ref_source": r["source"],
                    "ref_line": r["line"],
                    "ref_role": r["role"],
                    "ref_text": r["text"],
                })
                rows.append(x)
        else:
            x = dict(rec)
            x.update({
                "ref_source": "",
                "ref_line": "",
                "ref_role": "NO_EXACT_SOURCE_KEY_REFERENCE",
                "ref_text": "",
            })
            rows.append(x)
    return rows


def audit_group_partition(group_rows):
    """
    Determine whether persisted producer grouping arrays collectively partition
    the 1,078 streamlines.

    Only integer index arrays are used. We do not infer producer labels from
    geometry or numerical closeness.
    """
    rows = []
    groups = []

    for rec in group_rows:
        path = Path(rec["artifact"])
        key = rec["key"]
        try:
            with np.load(path, allow_pickle=False) as db:
                a = np.asarray(db[key])
        except Exception:
            continue

        if not np.issubdtype(a.dtype, np.number):
            continue

        flat = np.asarray(a).reshape(-1)
        integer_like = np.allclose(flat, np.rint(flat), atol=0, rtol=0)

        if not integer_like:
            continue

        vals = np.rint(flat).astype(np.int64)

        # Candidate grouping index arrays should contain values in [0,1077].
        if len(vals) == 0:
            continue

        valid_index_range = np.all((vals >= 0) & (vals < EXPECTED_STREAMLINES))
        if not valid_index_range:
            continue

        rows.append({
            "artifact": str(path),
            "key": key,
            "count": len(vals),
            "min_index": int(vals.min()),
            "max_index": int(vals.max()),
            "unique_index_count": len(np.unique(vals)),
            "valid_index_range": True,
            "array_sha256": rec.get("array_sha256", ""),
        })
        groups.append((str(path), key, vals))

    if not groups:
        return rows, None

    # Test all candidate grouping arrays as a union.
    union = np.concatenate([g[2] for g in groups])
    unique = np.unique(union)
    duplicates = len(union) - len(unique)
    covers_all = (
        len(unique) == EXPECTED_STREAMLINES
        and unique[0] == 0
        and unique[-1] == EXPECTED_STREAMLINES - 1
    )

    summary = {
        "group_array_count": len(groups),
        "total_memberships": len(union),
        "unique_streamline_indices": len(unique),
        "duplicate_memberships": duplicates,
        "covers_all_1078": covers_all,
        "exact_partition": covers_all and duplicates == 0,
    }

    rows.append({
        "artifact": "COMBINED_GROUP_PARTITION",
        "key": "",
        "count": summary["total_memberships"],
        "min_index": int(unique.min()) if len(unique) else "",
        "max_index": int(unique.max()) if len(unique) else "",
        "unique_index_count": summary["unique_streamline_indices"],
        "valid_index_range": True,
        "duplicate_memberships": summary["duplicate_memberships"],
        "covers_all_1078": summary["covers_all_1078"],
        "exact_partition": summary["exact_partition"],
    })

    return rows, summary


def producer_labels_from_keys(group_rows):
    """
    Extract explicit producer labels from grouping keys/path names only.
    This is semantic provenance, not geometric inference.
    """
    labels = []
    for rec in group_rows:
        text = (rec.get("key","") + " " + rec.get("artifact","")).upper()
        found = None
        for label in ["PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE"]:
            if label in text:
                found = label
                break

        if found is None:
            # stricter corner shorthand patterns
            for short in ["SW", "SE", "NW", "NE"]:
                if re.search(rf"(^|[_\-]){short}([_\-.]|$)", text):
                    found = f"PROD_{short}"
                    break

        if found:
            labels.append((rec, found))

    return labels


def classify_rule_edge(source_rows, map_rows, terminal_edge_rows, group_rows, partition_summary):
    group_labels = producer_labels_from_keys(group_rows)
    distinct_labels = sorted({label for _, label in group_labels})

    source_explicit_assignment = any(
        r["record_type"] in {"ASSIGNMENT", "COLLECTION_WRITE"}
        for r in source_rows
    )

    map_explicit = len(map_rows) > 0
    grouping_exact_partition = bool(partition_summary and partition_summary.get("exact_partition"))
    four_group_labels = set(distinct_labels) == {"PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE"}

    # Strongest non-retrace path: 4 explicitly labeled producer grouping arrays
    # partition all streamlines exactly once.
    if grouping_exact_partition and four_group_labels:
        return {
            "status": "EXECUTABLE_GROUP_PARTITION_RULE_BOUND",
            "authorized": True,
            "rule_type": "PERSISTED_LABELED_PRODUCER_GROUP_PARTITION",
            "producer_labels": ";".join(distinct_labels),
            "reason": "Persisted explicitly labeled producer groups partition all 1,078 streamline indices exactly once.",
        }

    # Second-best: explicit source assignment + producer map + terminal metadata
    # that is source-referenced. Do not execute yet unless the edge is complete.
    terminal_source_linked = any(
        r.get("ref_role") != "NO_EXACT_SOURCE_KEY_REFERENCE"
        for r in terminal_edge_rows
    )

    if source_explicit_assignment and map_explicit and terminal_source_linked:
        return {
            "status": "SOURCE_TERMINAL_RULE_EDGE_PARTIALLY_BOUND",
            "authorized": False,
            "rule_type": "SOURCE_TERMINAL_CAPTURE_MAPPING_REQUIRES_FINAL_OPERAND_BINDING",
            "producer_labels": ";".join(distinct_labels),
            "reason": "Source assignment semantics and terminal metadata are linked, but one final executable operand mapping remains unresolved.",
        }

    return {
        "status": "PRODUCER_RULE_EDGE_REMAINS_UNRESOLVED",
        "authorized": False,
        "rule_type": "",
        "producer_labels": ";".join(distinct_labels),
        "reason": "Neither an exact labeled grouping partition nor a fully executable source-terminal mapping is established.",
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R7C1")
    print("Producer Classification Rule Edge Audit")
    print("=" * 78)

    print("""
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECOMPUTED.
NO PRODUCER ID WILL BE RECONSTRUCTED IN R7C1.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO NEAREST-PRODUCER RULE WILL BE INVENTED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
ONLY THE MISSING PRODUCER CLASSIFICATION RULE EDGE WILL BE AUDITED.
""")

    if not R7C_SUMMARY.exists():
        raise FileNotFoundError(R7C_SUMMARY)

    r7c = json.loads(R7C_SUMMARY.read_text(encoding="utf-8"))
    if r7c.get("status") != "V16A_PRODUCER_IDENTITY_RULE_STILL_INCOMPLETE":
        raise RuntimeError("R7C1 expects the incomplete R7C producer-rule status.")

    terminal_inv = load_csv(R7C_TERMINAL)
    group_inv = load_csv(R7C_GROUPING)
    sources = sg56_sources()

    source_rows, map_rows = source_assignment_edge_trace(sources)
    save_csv(SOURCE_EDGE, source_rows)
    save_csv(MAPPING_EDGE, map_rows)

    terminal_edge_rows = metadata_edge_trace(terminal_inv, sources)
    group_edge_rows = metadata_edge_trace(group_inv, sources)
    save_csv(TERMINAL_EDGE, terminal_edge_rows)
    save_csv(GROUP_EDGE, group_edge_rows)

    partition_rows, partition_summary = audit_group_partition(group_inv)
    save_csv(PARTITION_AUDIT, partition_rows)

    rule = classify_rule_edge(
        source_rows, map_rows, terminal_edge_rows, group_inv, partition_summary
    )
    save_csv(RULE_BINDING, [rule])

    print("RULE EDGE AUDIT")
    print(f"  Source assignment records  : {len(source_rows)}")
    print(f"  Producer mapping records   : {len(map_rows)}")
    print(f"  Terminal edge records      : {len(terminal_edge_rows)}")
    print(f"  Group edge records         : {len(group_edge_rows)}")
    if partition_summary:
        print(f"  Group arrays               : {partition_summary['group_array_count']}")
        print(f"  Unique streamline indices  : {partition_summary['unique_streamline_indices']}")
        print(f"  Duplicate memberships      : {partition_summary['duplicate_memberships']}")
        print(f"  Exact 1,078 partition      : {partition_summary['exact_partition']}")
    else:
        print("  Group partition            : NOT RESOLVED")
    print(f"  Rule status                : {rule['status']}")
    print(f"  Reconstruction authorized  : {rule['authorized']}")
    print(f"  Rule type                  : {rule['rule_type'] or 'NONE'}")

    gates = [
        ("incoming_R7C_incomplete_rule_status_reproduced", True),
        ("producer_assignment_source_edges_audited", True),
        ("producer_name_index_maps_audited", True),
        ("terminal_metadata_creation_consumer_edges_audited", True),
        ("grouping_metadata_creation_consumer_edges_audited", True),
        ("streamline_group_partition_audited", True),
        ("producer_rule_edge_classified", True),
        ("no_producer_id_reconstructed", True),
        ("no_nearest_producer_rule_invented", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_recompute", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATES, [{"gate": g, "passed": p} for g,p in gates])

    if rule["authorized"]:
        status = "V16A_PRODUCER_CLASSIFICATION_RULE_EDGE_FINAL_BOUND"
        diagnosis = "ONE_EXECUTABLE_NONRETRACE_PRODUCER_CLASSIFICATION_RULE_IS_SUPPORTED_BY_PERSISTED_SOURCE_AUTHENTIC_METADATA"
        recommendation = (
            "Proceed to controlled producer-ID reconstruction using only the exact R7C1 rule. "
            "Do not rerun SG3/SG4, recompute velocity, or retrace Pollock."
        )
        next_ms = "V16A-R7D — Controlled Producer Identity Reconstruction"
    elif rule["status"] == "SOURCE_TERMINAL_RULE_EDGE_PARTIALLY_BOUND":
        status = "V16A_PRODUCER_CLASSIFICATION_RULE_EDGE_ONE_BINDING_SHORT"
        diagnosis = "SOURCE_AND_TERMINAL_METADATA_ARE_LINKED_BUT_ONE_FINAL_OPERAND_MAPPING_REMAINS_UNRESOLVED"
        recommendation = (
            "Audit only the unresolved terminal-to-producer operand mapping. Do not reconstruct producer_id yet."
        )
        next_ms = "V16A-R7C2 — Final Terminal-to-Producer Operand Binding Audit"
    else:
        status = "V16A_PRODUCER_CLASSIFICATION_RULE_EDGE_STILL_UNRESOLVED"
        diagnosis = "NO_EXACT_LABELED_GROUP_PARTITION_OR_COMPLETE_SOURCE_TERMINAL_RULE_WAS_ESTABLISHED"
        recommendation = (
            "Do not reconstruct producer_id. Inspect the partition and source-edge tables to identify the exact missing metadata link."
        )
        next_ms = "V16A-R7C2 — Producer Group / Terminal Metadata Resolution Audit"

    save_csv(DECISION, [{
        "status": status,
        "diagnosis": diagnosis,
        "rule_status": rule["status"],
        "rule_type": rule["rule_type"],
        "authorized": rule["authorized"],
        "partition_exact": bool(partition_summary and partition_summary.get("exact_partition")),
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R7C1",
        "status": status,
        "diagnosis": diagnosis,
        "rule": rule,
        "partition_summary": partition_summary,
        "constraints": {
            "producer_id_reconstructed": False,
            "nearest_rule_invented": False,
            "SG3_rerun": False,
            "SG4_rerun": False,
            "velocity_recompute": False,
            "Pollock_retrace": False,
            "FMM": False,
            "model_predict": False,
            "training": False,
            "V15_mutation": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT, contract)

    save_json(SUMMARY, {
        "milestone": "V16A-R7C1",
        "status": status,
        "diagnosis": diagnosis,
        "rule": rule,
        "partition_summary": partition_summary,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\n" + "=" * 78)
    print("V16A-R7C1 FINAL RULE EDGE GATES")
    print("=" * 78)
    for g,p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

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
    for p in [
        SOURCE_EDGE, MAPPING_EDGE, TERMINAL_EDGE, GROUP_EDGE,
        PARTITION_AUDIT, RULE_BINDING, GATES, DECISION
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R7C1 PRODUCER RULE EDGE AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
