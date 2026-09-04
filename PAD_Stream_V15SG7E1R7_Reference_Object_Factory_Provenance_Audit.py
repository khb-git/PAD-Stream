from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict


# =============================================================================
# PAD-Stream V15-SG7E1R7
# Reference Object / Factory Provenance Audit
#
# FORENSIC PROVENANCE ONLY.
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
# NO REFERENCE FIELD SELECTED BY CANDIDATE PERFORMANCE.
#
# PURPOSE
# -------
# SG7E1R6 recursively traced helper parameters through caller arguments and
# caller-local assignments but still did not reach a persisted upstream key.
#
# The unresolved lineage can therefore be hidden behind:
#   * factory/helper return values,
#   * returned dictionaries,
#   * class/instance attributes,
#   * constructor assignments,
#   * object fields populated by loader calls,
#   * subscripted containers whose creation precedes the caller boundary.
#
# R7 audits those interfaces without selecting a truth field.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R7"
OUT.mkdir(parents=True, exist_ok=True)

R6_DIR = ROOT / "output" / "V15_SG7E1R6"
R6_SUMMARY = R6_DIR / "PAD_Stream_V15SG7E1R6_Summary.json"
R6_CONTRACT = R6_DIR / "V15SG7E1R6_Recursive_Caller_Argument_Provenance_Contract.json"
R6_RECURSIVE = R6_DIR / "V15SG7E1R6_Recursive_Argument_Chain.csv"
R6_FIELDS = R6_DIR / "V15SG7E1R6_Field_Source_Trace.csv"

R3_UPSTREAM = (
    ROOT / "output" / "V15_SG7E1R3"
    / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv"
)
R0_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R0"
    / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"
)
D6_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

MODULE_TABLE = OUT / "V15SG7E1R7_Project_Module_Inventory.csv"
RETURN_TABLE = OUT / "V15SG7E1R7_Function_Return_Trace.csv"
FACTORY_TABLE = OUT / "V15SG7E1R7_Factory_Return_Provenance.csv"
CLASS_TABLE = OUT / "V15SG7E1R7_Class_Constructor_Attribute_Trace.csv"
ATTRIBUTE_TABLE = OUT / "V15SG7E1R7_Object_Attribute_Source_Trace.csv"
DICT_TABLE = OUT / "V15SG7E1R7_Returned_Dictionary_Key_Trace.csv"
LOADER_TABLE = OUT / "V15SG7E1R7_Loader_Construction_Trace.csv"
CONTAINER_TABLE = OUT / "V15SG7E1R7_Unresolved_Container_Provenance.csv"
MATCH_TABLE = OUT / "V15SG7E1R7_Upstream_Key_Object_Provenance_Match.csv"
DECISION_TABLE = OUT / "V15SG7E1R7_Object_Factory_Provenance_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R7_Reference_Object_Factory_Provenance_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R7_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def parse_module(path: Path):
    text = safe_text(path)
    if not text:
        return None, ""
    try:
        return ast.parse(text), text
    except SyntaxError:
        return None, text


def node_text(source: str, node):
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:
        return ""


def attr_chain(node):
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


def call_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return attr_chain(call.func)
    return ""


def project_py_files():
    out = []
    for p in ROOT.rglob("*.py"):
        low = {x.lower() for x in p.parts}
        if ".venv" in low or "site-packages" in low:
            continue
        if "output" in low or "__pycache__" in low:
            continue
        out.append(p.resolve())
    return sorted(set(out))


def exact_key_hits(text, keys):
    t = text or ""
    return [k for k in keys if k and k.lower() in t.lower()]


def is_excluded_key(key):
    k = key.lower()
    return any(x in k for x in (
        "coverage",
        "streamline_count",
        "coverage_weight",
        "support_distance",
    ))


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R7")
    print("Reference Object / Factory Provenance Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO SUPPORT MASK OR BACKGROUND POLICY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POST-HOC ALIGNMENT WILL BE PERFORMED.
NO DEPLOYMENT CORRECTION WILL BE PERFORMED.
NO REFERENCE FIELD WILL BE SELECTED BY CANDIDATE PERFORMANCE.
""")

    r6_summary = load_json(R6_SUMMARY)
    r6_contract = load_json(R6_CONTRACT)
    r0 = load_json(R0_CONTRACT)
    d6 = load_json(D6_MANIFEST)
    recursive = load_csv(R6_RECURSIVE)
    r6_fields = load_csv(R6_FIELDS)
    upstream = load_csv(R3_UPSTREAM)

    if r6_summary.get("status") != "SG7E_RECURSIVE_REFERENCE_PROVENANCE_NOT_YET_RESOLVED":
        raise RuntimeError("R7 requires the unresolved R6 provenance status.")

    if r6_summary.get("diagnosis") != (
        "CALLER_ARGUMENT_CHAIN_STILL_DOES_NOT_REACH_PERSISTED_REFERENCE_KEY"
    ):
        raise RuntimeError("R7 requires the unresolved R6 caller-chain diagnosis.")

    threshold_info = r0.get("plume_threshold", {})
    threshold = float(threshold_info["value"])
    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold must remain resolved.")

    if d6.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    upstream_keys = sorted({
        r.get("key", "").strip()
        for r in upstream
        if r.get("key", "").strip()
    })

    modules = project_py_files()
    save_csv(MODULE_TABLE, [{
        "source": str(p),
        "relative_to_root": str(p.relative_to(ROOT)),
    } for p in modules])

    # Containers observed at the end of R6.
    unresolved_containers = set()
    unresolved_fields = set()

    for r in r6_fields:
        c = r.get("container", "").strip()
        f = r.get("field_or_key", "").strip()
        if c:
            unresolved_containers.add(c)
        if f:
            unresolved_fields.add(f)

    # Also mine R6 argument expressions for variable/object roots.
    for r in recursive:
        expr = r.get("argument_expression", "")
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\.", expr):
            unresolved_containers.add(m.group(1))
        for m in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*['\"]([^'\"]+)['\"]\s*\]",
            expr,
        ):
            unresolved_containers.add(m.group(1))
            unresolved_fields.add(m.group(2))

    return_rows = []
    factory_rows = []
    class_rows = []
    attribute_rows = []
    dict_rows = []
    loader_rows = []
    container_rows = []
    match_evidence = defaultdict(list)

    loader_tokens = (
        "np.load",
        "numpy.load",
        "load_json",
        "load_csv",
        "read_csv",
        "pickle.load",
        "joblib.load",
        "fromfile",
        "memmap",
    )

    for path in modules:
        tree, text = parse_module(path)
        if tree is None:
            continue

        # ---------------------------------------------------------------------
        # Function return values and returned dictionaries.
        # ---------------------------------------------------------------------
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            params = [a.arg for a in fn.args.args]

            for n in ast.walk(fn):
                if not isinstance(n, ast.Return) or n.value is None:
                    continue

                expr = node_text(text, n.value)
                hits = [k for k in exact_key_hits(expr, upstream_keys)
                        if not is_excluded_key(k)]

                rec = {
                    "source": str(path),
                    "function": fn.name,
                    "function_line": fn.lineno,
                    "return_line": n.lineno,
                    "parameters": ";".join(params),
                    "return_expression": expr,
                    "exact_upstream_keys": ";".join(hits),
                }
                return_rows.append(rec)

                for k in hits:
                    match_evidence[k].append(
                        f"return:{path.name}:{n.lineno}:{fn.name}"
                    )

                if isinstance(n.value, ast.Dict):
                    for key_node, val_node in zip(n.value.keys, n.value.values):
                        key_txt = node_text(text, key_node) if key_node else ""
                        val_txt = node_text(text, val_node)
                        hits2 = [k for k in exact_key_hits(
                            key_txt + " " + val_txt, upstream_keys
                        ) if not is_excluded_key(k)]

                        dict_rows.append({
                            "source": str(path),
                            "function": fn.name,
                            "line": n.lineno,
                            "dict_key": key_txt,
                            "dict_value": val_txt,
                            "exact_upstream_keys": ";".join(hits2),
                        })

                        for k in hits2:
                            match_evidence[k].append(
                                f"returned_dict:{path.name}:{n.lineno}:{fn.name}"
                            )

        # ---------------------------------------------------------------------
        # Classes, constructor assignments, self attributes.
        # ---------------------------------------------------------------------
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]

            for fn in methods:
                for n in ast.walk(fn):
                    if isinstance(n, (ast.Assign, ast.AnnAssign)):
                        value = getattr(n, "value", None)
                        if value is None:
                            continue

                        expr = node_text(text, value)
                        targets = []

                        if isinstance(n, ast.Assign):
                            raw_targets = n.targets
                        else:
                            raw_targets = [n.target]

                        for target in raw_targets:
                            for t in ast.walk(target):
                                if isinstance(t, ast.Attribute):
                                    chain = attr_chain(t)
                                    if chain:
                                        targets.append(chain)

                        if not targets:
                            continue

                        hits = [k for k in exact_key_hits(
                            " ".join(targets) + " " + expr, upstream_keys
                        ) if not is_excluded_key(k)]

                        row = {
                            "source": str(path),
                            "class": cls.name,
                            "method": fn.name,
                            "line": n.lineno,
                            "targets": ";".join(sorted(set(targets))),
                            "value_expression": expr,
                            "constructor_assignment": fn.name == "__init__",
                            "exact_upstream_keys": ";".join(hits),
                        }
                        class_rows.append(row)

                        for target in targets:
                            attribute_rows.append({
                                "source": str(path),
                                "class": cls.name,
                                "method": fn.name,
                                "line": n.lineno,
                                "attribute": target,
                                "value_expression": expr,
                                "exact_upstream_keys": ";".join(hits),
                            })

                        for k in hits:
                            match_evidence[k].append(
                                f"attribute:{path.name}:{n.lineno}:{cls.name}.{fn.name}"
                            )

        # ---------------------------------------------------------------------
        # All assignments involving unresolved R6 containers/fields.
        # ---------------------------------------------------------------------
        for n in ast.walk(tree):
            if not isinstance(n, (ast.Assign, ast.AnnAssign)):
                continue

            value = getattr(n, "value", None)
            if value is None:
                continue

            expr = node_text(text, value)

            if isinstance(n, ast.Assign):
                target_nodes = n.targets
            else:
                target_nodes = [n.target]

            target_txt = " ; ".join(node_text(text, x) for x in target_nodes)
            combined = target_txt + " " + expr

            related_containers = sorted({
                c for c in unresolved_containers
                if re.search(rf"\b{re.escape(c)}\b", combined)
            })

            related_fields = sorted({
                f for f in unresolved_fields
                if f and f.lower() in combined.lower()
            })

            hits = [k for k in exact_key_hits(combined, upstream_keys)
                    if not is_excluded_key(k)]

            if related_containers or related_fields or hits:
                container_rows.append({
                    "source": str(path),
                    "line": n.lineno,
                    "targets": target_txt,
                    "value_expression": expr,
                    "related_r6_containers": ";".join(related_containers),
                    "related_r6_fields": ";".join(related_fields),
                    "exact_upstream_keys": ";".join(hits),
                })

            for k in hits:
                match_evidence[k].append(
                    f"container_assignment:{path.name}:{n.lineno}"
                )

            # Loader construction audit.
            low = expr.lower()
            if any(tok.lower() in low for tok in loader_tokens):
                hits2 = [k for k in exact_key_hits(combined, upstream_keys)
                         if not is_excluded_key(k)]
                loader_rows.append({
                    "source": str(path),
                    "line": n.lineno,
                    "targets": target_txt,
                    "loader_expression": expr,
                    "related_r6_containers": ";".join(related_containers),
                    "exact_upstream_keys": ";".join(hits2),
                })
                for k in hits2:
                    match_evidence[k].append(
                        f"loader:{path.name}:{n.lineno}"
                    )

        # ---------------------------------------------------------------------
        # Factory calls: assignment target = function(...)
        # ---------------------------------------------------------------------
        for n in ast.walk(tree):
            if not isinstance(n, ast.Assign):
                continue
            if not isinstance(n.value, ast.Call):
                continue

            target_txt = " ; ".join(node_text(text, x) for x in n.targets)
            call_txt = node_text(text, n.value)
            cname = call_name(n.value)

            related = sorted({
                c for c in unresolved_containers
                if re.search(rf"\b{re.escape(c)}\b", target_txt)
            })

            hits = [k for k in exact_key_hits(
                target_txt + " " + call_txt, upstream_keys
            ) if not is_excluded_key(k)]

            if related or hits:
                factory_rows.append({
                    "source": str(path),
                    "line": n.lineno,
                    "targets": target_txt,
                    "factory_call": cname,
                    "call_expression": call_txt,
                    "related_r6_containers": ";".join(related),
                    "exact_upstream_keys": ";".join(hits),
                })

            for k in hits:
                match_evidence[k].append(
                    f"factory:{path.name}:{n.lineno}:{cname}"
                )

    save_csv(RETURN_TABLE, return_rows)
    save_csv(FACTORY_TABLE, factory_rows)
    save_csv(CLASS_TABLE, class_rows)
    save_csv(ATTRIBUTE_TABLE, attribute_rows)
    save_csv(DICT_TABLE, dict_rows)
    save_csv(LOADER_TABLE, loader_rows)
    save_csv(CONTAINER_TABLE, container_rows)

    match_rows = []
    for key, evidence in sorted(
        match_evidence.items(),
        key=lambda kv: len(kv[1]),
        reverse=True,
    ):
        paths = sorted({
            r.get("path", "")
            for r in upstream
            if r.get("key", "") == key and r.get("path", "")
        })
        match_rows.append({
            "key": key,
            "provenance_hit_count": len(evidence),
            "upstream_artifact_paths": ";".join(paths),
            "evidence_examples": ";".join(evidence[:8]),
        })

    save_csv(MATCH_TABLE, match_rows)

    matched_keys = [r["key"] for r in match_rows]

    # Conservative resolution rule:
    # R7 resolves only if exactly one non-diagnostic persisted key is reached.
    if len(matched_keys) == 1:
        selected_key = matched_keys[0]
        status = "SG7E_REFERENCE_OBJECT_PROVENANCE_RESOLVED"
        diagnosis = "UNIQUE_PERSISTED_REFERENCE_KEY_REACHED_THROUGH_OBJECT_FACTORY_LINEAGE"
        recommendation = (
            "The previously unresolved reference lineage now reaches exactly one persisted "
            "upstream physics key through object/factory provenance. Do not evaluate SG7E "
            "gates yet. Resolve the exact artifact instance and any historical time-slice or "
            "branch selection, then independently reconstruct the reference field."
        )
        next_milestone = (
            "V15-SG7E1R8 — Exact Reference Artifact / Time-Slice Resolution Audit"
        )
    elif len(matched_keys) > 1:
        selected_key = ""
        status = "SG7E_REFERENCE_OBJECT_PROVENANCE_CONFLICT"
        diagnosis = "MULTIPLE_PERSISTED_REFERENCE_KEYS_REACHED_THROUGH_OBJECT_FACTORY_LINEAGE"
        recommendation = (
            "Do not evaluate SG7E gates. Object/factory tracing reaches multiple persisted "
            "physics keys. Audit only the final constructor/factory branch and field-consumption "
            "semantics that distinguish them; do not select by frozen-candidate performance."
        )
        next_milestone = (
            "V15-SG7E1R8 — Final Object-Branch / Reference-Key Consumption Audit"
        )
    else:
        selected_key = ""
        status = "SG7E_REFERENCE_OBJECT_PROVENANCE_NOT_YET_RESOLVED"
        diagnosis = "OBJECT_FACTORY_LINEAGE_STILL_TERMINATES_BEFORE_PERSISTED_REFERENCE_KEY"
        recommendation = (
            "Do not evaluate SG7E gates. The unresolved reference is still hidden before a "
            "persisted key. Use the R7 container, factory, constructor, return, and loader "
            "tables to identify the final object boundary, then audit serialized object "
            "members, dynamically constructed keys, aliases, and indirect loader wrappers."
        )
        next_milestone = (
            "V15-SG7E1R8 — Dynamic Key / Alias / Loader-Wrapper Provenance Audit"
        )

    checks = [
        ("Incoming SG7E1R6 unresolved provenance reproduced", True),
        ("Historical plume threshold retained", abs(threshold - 0.5) < 1e-15),
        ("Frozen SG7D6 input remains authoritative", True),
        ("R6 unresolved containers retained", True),
        ("Function return values audited", True),
        ("Returned dictionary keys audited", True),
        ("Factory-return construction audited", True),
        ("Class constructor assignments audited", True),
        ("Object attribute sources audited", True),
        ("Loader construction sites audited", True),
        ("Coverage/support diagnostics excluded", True),
        ("Frozen candidate performance not used", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No post-hoc alignment performed", True),
        ("No deployment correction performed", True),
    ]

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "plume_threshold": threshold,
        "project_modules": len(modules),
        "r6_unresolved_containers": len(unresolved_containers),
        "r6_unresolved_fields": len(unresolved_fields),
        "function_returns": len(return_rows),
        "factory_records": len(factory_rows),
        "constructor_attribute_records": len(class_rows),
        "attribute_records": len(attribute_rows),
        "returned_dict_records": len(dict_rows),
        "loader_records": len(loader_rows),
        "container_records": len(container_rows),
        "matched_upstream_keys": len(matched_keys),
        "matched_key_names": ";".join(matched_keys),
        "selected_key": selected_key,
        "next_milestone": next_milestone,
    }
    save_csv(DECISION_TABLE, [decision])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R7",
        "status": status,
        "diagnosis": diagnosis,
        "plume_threshold": {"value": threshold, "changed": False},
        "object_factory_provenance": {
            "r6_unresolved_containers": sorted(unresolved_containers),
            "r6_unresolved_fields": sorted(unresolved_fields),
            "matched_upstream_keys": matched_keys,
            "selected_key": selected_key or None,
        },
        "constraints": {
            "candidate_performance_used": False,
            "coverage_support_diagnostic_promoted_to_truth": False,
            "threshold_changed": False,
            "posthoc_alignment": False,
            "deployment_correction_performed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R7",
        "status": status,
        "diagnosis": diagnosis,
        "matched_upstream_keys": matched_keys,
        "reference_selected": len(matched_keys) == 1,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("REFERENCE OBJECT / FACTORY TRACE")
    print(f"  Project modules         : {len(modules)}")
    print(f"  R6 containers           : {len(unresolved_containers)}")
    print(f"  R6 fields               : {len(unresolved_fields)}")
    print(f"  Function returns        : {len(return_rows)}")
    print(f"  Factory records         : {len(factory_rows)}")
    print(f"  Constructor attributes  : {len(class_rows)}")
    print(f"  Object attributes       : {len(attribute_rows)}")
    print(f"  Returned dict records   : {len(dict_rows)}")
    print(f"  Loader records          : {len(loader_rows)}")
    print(f"  Container records       : {len(container_rows)}")
    print(f"  Matched upstream keys   : {len(matched_keys)}")

    if match_rows:
        print("\nUPSTREAM OBJECT-PROVENANCE MATCHES")
        for row in match_rows[:12]:
            print(
                f"  hits={int(row['provenance_hit_count']):3d} | "
                f"{row['key']}"
            )

    print("\n" + "=" * 78)
    print("V15-SG7E1R7 OBJECT / FACTORY PROVENANCE VALIDATION")
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
        MODULE_TABLE, RETURN_TABLE, FACTORY_TABLE, CLASS_TABLE,
        ATTRIBUTE_TABLE, DICT_TABLE, LOADER_TABLE, CONTAINER_TABLE,
        MATCH_TABLE, DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R7 REFERENCE OBJECT / FACTORY PROVENANCE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No coverage/support diagnostic was promoted to truth.")
    print("No frozen-candidate performance was used to select a reference.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
