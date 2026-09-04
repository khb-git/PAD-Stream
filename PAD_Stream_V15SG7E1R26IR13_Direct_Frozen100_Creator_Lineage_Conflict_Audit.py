from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R13
# Direct Frozen100 Creator Lineage Conflict Audit
#
# DIAGNOSTIC-ONLY CREATOR-LINEAGE DISAMBIGUATION
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO X100 WILL BE CHANGED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO CREATOR WILL BE SELECTED BY NUMERICAL CLOSENESS.
#
# PURPOSE
# -------
# R26I-R12 resolved the frozen100 immediate input to two direct historical
# creators:
#
#   SG7B13: frozen100 <- frozen_model.predict(deployment["X100"])[:,:,0]
#   SG7B16: frozen100 <- frozen_model.predict(deployment["X100"])[:,:,0]
#
# R26I-R13 separates these two lineages using ONLY provenance:
#
#   - exact frozen_model load path / artifact hash
#   - deployment workspace construction
#   - deployment/X100 helper lineage
#   - frozen100 serialization path
#   - downstream CR3 / R1F consumer references
#   - parent manifest / contract references
#
# No model execution is performed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR13"
OUT.mkdir(parents=True, exist_ok=True)

R12_DIR = ROOT / "output" / "V15_SG7E1R26IR12"
R12_SUMMARY = R12_DIR / "PAD_Stream_V15SG7E1R26IR12_Summary.json"
R12_PRIORITY = R12_DIR / "V15SG7E1R26IR12_Frozen100_Source_Priority.csv"

CREATOR_B13 = ROOT / "PAD_Stream_V15SG7B13_Controlled_TOF_Conditioned_Residual_Bias_Refinement.py"
CREATOR_B16 = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"

# Outputs
IDENTITY_TABLE = OUT / "V15SG7E1R26IR13_Direct_Creator_Identity.csv"
MODEL_TABLE = OUT / "V15SG7E1R26IR13_Frozen_Model_Load_Lineage.csv"
WORKSPACE_TABLE = OUT / "V15SG7E1R26IR13_Deployment_Workspace_Lineage.csv"
X100_TABLE = OUT / "V15SG7E1R26IR13_X100_Constructor_Lineage.csv"
SERIAL_TABLE = OUT / "V15SG7E1R26IR13_Frozen100_Serialization_Lineage.csv"
CONSUMER_TABLE = OUT / "V15SG7E1R26IR13_Downstream_CR3_R1F_Consumer_Lineage.csv"
MANIFEST_TABLE = OUT / "V15SG7E1R26IR13_Manifest_Contract_Lineage.csv"
SCORING_TABLE = OUT / "V15SG7E1R26IR13_Creator_Provenance_Scoring.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR13_Creator_Lineage_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR13_Direct_Frozen100_Creator_Lineage_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR13_Summary.json"


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
    for row in rows:
        for k in row:
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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def assignment_map(tree, text):
    amap = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                amap[tgt.id] = {
                    "line": node.lineno,
                    "rhs": node_src(text, node.value),
                    "rhs_node": node.value,
                }
    return amap


def find_frozen100_assignment(tree, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == "frozen100":
                rows.append({
                    "line": node.lineno,
                    "expression": node_src(text, node.value),
                })
    return rows


def find_load_model_assignments(tree, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        cname = call_name(node.value)
        if not cname.endswith("load_model"):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        rows.append({
            "line": node.lineno,
            "target": ";".join(targets),
            "path_expression": node_src(text, node.value.args[0]) if node.value.args else "",
            "full_expression": node_src(text, node.value),
        })
    return rows


def find_workspace_assignments(tree, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and "workspace" in tgt.id.lower():
                rows.append({
                    "line": node.lineno,
                    "symbol": tgt.id,
                    "expression": node_src(text, node.value),
                })
    return rows


def find_x100_lineage(tree, text):
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                lhs = node_src(text, tgt)
                rhs = node_src(text, node.value)
                if "X100" in lhs or "X100" in rhs:
                    rows.append({
                        "line": node.lineno,
                        "kind": "ASSIGNMENT",
                        "lhs": lhs,
                        "rhs": rhs,
                    })

        if isinstance(node, ast.Call):
            expr = node_src(text, node)
            if "load_deployment_database" in expr or "X100" in expr:
                rows.append({
                    "line": getattr(node, "lineno", ""),
                    "kind": "CALL",
                    "lhs": "",
                    "rhs": expr,
                })
    return rows


def find_serializers(tree, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        cname = call_name(node)
        if cname not in {"np.savez", "np.savez_compressed"}:
            continue

        artifact = node_src(text, node.args[0]) if node.args else ""
        for kw in node.keywords:
            if kw.arg and ("frozen" in kw.arg.lower() or "prediction" in kw.arg.lower()):
                rows.append({
                    "line": node.lineno,
                    "serializer": cname,
                    "artifact_expression": artifact,
                    "key": kw.arg,
                    "value_expression": node_src(text, kw.value),
                })
    return rows


def project_text_files():
    files = []
    for pat in ("*.py", "*.json", "*.csv"):
        files.extend(ROOT.rglob(pat))
    return [p for p in files if p.is_file()]


def source_mentions(filename: str):
    """
    Search downstream project files for explicit textual mentions of creator
    source filename or its milestone token.
    """
    stem = Path(filename).stem
    milestone_tokens = []
    if "V15SG7B13" in filename:
        milestone_tokens = ["V15SG7B13", "SG7B13"]
    elif "V15SG7B16" in filename:
        milestone_tokens = ["V15SG7B16", "SG7B16"]

    rows = []
    for path in project_text_files():
        if path.name == filename:
            continue

        text = safe_text(path)

        hits = 0
        hit_tokens = []
        for tok in [filename, stem, *milestone_tokens]:
            c = text.count(tok)
            if c > 0:
                hits += c
                hit_tokens.append(f"{tok}:{c}")

        if hits:
            low_name = path.name.lower()
            category = "OTHER"
            if "cr3" in low_name:
                category = "CR3"
            elif "r1f" in low_name:
                category = "R1F"
            elif "manifest" in low_name or "contract" in low_name or path.suffix.lower() == ".json":
                category = "MANIFEST_OR_CONTRACT"

            rows.append({
                "creator_source": filename,
                "consumer_path": str(path),
                "consumer_name": path.name,
                "category": category,
                "hit_count": hits,
                "hit_tokens": ";".join(hit_tokens),
            })
    return rows


def resolve_literal_model_path(path_expr: str, amap):
    """
    Conservative source resolution of common creator model path expressions.
    We only resolve if the expression is a direct string/Path or simple alias
    whose assignment is a literal/root-relative expression.
    """
    expr = path_expr.strip()

    if re.fullmatch(r"[A-Za-z_]\w*", expr) and expr in amap:
        return amap[expr]["rhs"]

    return expr


def candidate_model_artifacts(path_expr: str):
    """
    Match project model artifacts using exact basename tokens present in source
    expression. This is provenance matching, not performance selection.
    """
    models = [
        p.resolve()
        for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".keras", ".h5", ".hdf5"}
    ]

    rows = []
    for p in models:
        if p.name in path_expr:
            rows.append({
                "artifact": str(p),
                "filename": p.name,
                "sha256": sha256_file(p),
                "match_basis": "EXACT_FILENAME_IN_SOURCE_EXPRESSION",
            })
    return rows


def audit_creator(path: Path):
    text = safe_text(path)
    tree = ast.parse(text)
    amap = assignment_map(tree, text)

    frozen_rows = find_frozen100_assignment(tree, text)
    load_rows = find_load_model_assignments(tree, text)
    workspace_rows = find_workspace_assignments(tree, text)
    x100_rows = find_x100_lineage(tree, text)
    serial_rows = find_serializers(tree, text)

    frozen_model_loads = [
        r for r in load_rows
        if "frozen_model" in r["target"].split(";")
    ]

    model_artifact_rows = []
    for r in frozen_model_loads:
        resolved_expr = resolve_literal_model_path(r["path_expression"], amap)
        matches = candidate_model_artifacts(resolved_expr)
        for m in matches:
            model_artifact_rows.append({
                "creator_source": path.name,
                "load_line": r["line"],
                "load_target": r["target"],
                "path_expression": r["path_expression"],
                "resolved_expression": resolved_expr,
                **m,
            })

    return {
        "source": path,
        "sha256": sha256_file(path),
        "frozen100": frozen_rows,
        "loads": frozen_model_loads,
        "workspace": workspace_rows,
        "x100": x100_rows,
        "serial": serial_rows,
        "model_artifacts": model_artifact_rows,
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R13")
    print("Direct Frozen100 Creator Lineage Conflict Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO X100 WILL BE CHANGED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO CREATOR WILL BE SELECTED BY NUMERICAL CLOSENESS.
ONLY SG7B13 AND SG7B16 DIRECT FROZEN100 CREATOR LINEAGES WILL BE AUDITED.
""")

    prev = load_json(R12_SUMMARY)
    if prev.get("status") != "FROZEN100_IMMEDIATE_INPUT_DIRECT_MODEL_PREDICT_CONFLICT":
        raise RuntimeError("R26I-R13 requires the R12 direct-creator conflict.")

    creators = [CREATOR_B13, CREATOR_B16]
    for p in creators:
        if not p.exists():
            raise FileNotFoundError(p)

    audits = [audit_creator(p) for p in creators]

    identity_rows = []
    model_rows = []
    workspace_rows = []
    x100_rows = []
    serial_rows = []
    consumer_rows = []
    manifest_rows = []

    for a in audits:
        source = a["source"]
        identity_rows.append({
            "creator_source": source.name,
            "source_path": str(source),
            "source_sha256": a["sha256"],
            "frozen100_assignment_count": len(a["frozen100"]),
            "frozen_model_load_count": len(a["loads"]),
            "workspace_record_count": len(a["workspace"]),
            "X100_lineage_record_count": len(a["x100"]),
            "serialization_record_count": len(a["serial"]),
        })

        for r in a["loads"]:
            model_rows.append({
                "creator_source": source.name,
                **r,
            })
        model_rows.extend(a["model_artifacts"])

        for r in a["workspace"]:
            workspace_rows.append({
                "creator_source": source.name,
                **r,
            })

        for r in a["x100"]:
            x100_rows.append({
                "creator_source": source.name,
                **r,
            })

        for r in a["serial"]:
            serial_rows.append({
                "creator_source": source.name,
                **r,
            })

        mentions = source_mentions(source.name)
        for r in mentions:
            if r["category"] in {"CR3", "R1F"}:
                consumer_rows.append(r)
            if r["category"] == "MANIFEST_OR_CONTRACT":
                manifest_rows.append(r)

    save_csv(IDENTITY_TABLE, identity_rows)
    save_csv(MODEL_TABLE, model_rows)
    save_csv(WORKSPACE_TABLE, workspace_rows)
    save_csv(X100_TABLE, x100_rows)
    save_csv(SERIAL_TABLE, serial_rows)
    save_csv(CONSUMER_TABLE, consumer_rows)
    save_csv(MANIFEST_TABLE, manifest_rows)

    # -------------------------------------------------------------------------
    # Provenance scoring
    # -------------------------------------------------------------------------
    scores = []

    for a in audits:
        name = a["source"].name
        score = 0
        reasons = []

        exact_model_artifacts = len(a["model_artifacts"])
        if exact_model_artifacts == 1:
            score += 2000
            reasons.append("unique_exact_model_artifact")
        elif exact_model_artifacts > 1:
            score += 500
            reasons.append("multiple_exact_model_artifacts")

        if a["frozen100"]:
            score += 500
            reasons.append("direct_frozen100_creator")

        if a["serial"]:
            score += 500
            reasons.append("frozen_prediction_serialized")

        cr3_hits = sum(
            int(r["hit_count"])
            for r in consumer_rows
            if r["creator_source"] == name and r["category"] == "CR3"
        )
        r1f_hits = sum(
            int(r["hit_count"])
            for r in consumer_rows
            if r["creator_source"] == name and r["category"] == "R1F"
        )
        manifest_hits = sum(
            int(r["hit_count"])
            for r in manifest_rows
            if r["creator_source"] == name
        )

        if cr3_hits:
            score += 1000 * cr3_hits
            reasons.append(f"CR3_consumer_hits={cr3_hits}")
        if r1f_hits:
            score += 1500 * r1f_hits
            reasons.append(f"R1F_consumer_hits={r1f_hits}")
        if manifest_hits:
            score += 750 * manifest_hits
            reasons.append(f"manifest_contract_hits={manifest_hits}")

        # Later milestone gets no automatic authority merely for chronology.
        # This avoids chronology-only selection.
        scores.append({
            "creator_source": name,
            "score": score,
            "unique_exact_model_artifacts": exact_model_artifacts,
            "CR3_hits": cr3_hits,
            "R1F_hits": r1f_hits,
            "manifest_contract_hits": manifest_hits,
            "reasons": ";".join(reasons),
        })

    scores.sort(key=lambda r: int(r["score"]), reverse=True)
    save_csv(SCORING_TABLE, scores)

    resolved = False
    selected = None
    margin = 0

    if len(scores) == 2:
        top, second = scores[0], scores[1]
        margin = int(top["score"]) - int(second["score"])

        # Require downstream/manifest authority, not chronology.
        top_has_direct_downstream = (
            int(top["CR3_hits"]) > 0
            or int(top["R1F_hits"]) > 0
            or int(top["manifest_contract_hits"]) > 0
        )

        if top_has_direct_downstream and margin > 0:
            resolved = True
            selected = top

    if resolved:
        status = "FROZEN100_DIRECT_CREATOR_LINEAGE_RESOLVED"
        diagnosis = (
            "ONE_DIRECT_FROZEN100_CREATOR_HAS_STRONGER_DOWNSTREAM_CR3_R1F_OR_MANIFEST_PROVENANCE"
        )
        recommendation = (
            "The SG7B13/SG7B16 creator conflict is resolved from downstream provenance rather than "
            "numerical closeness or chronology. Preserve the selected creator source, frozen-model "
            "load path, and deployment/X100 lineage. Next resolve the exact model artifact and "
            "replay only that creator's 100-day frozen_model.predict path against persisted frozen100."
        )
        next_milestone = (
            "V15-SG7E1R26I-R14 — Selected Frozen100 Creator Model / X100 Runtime Reconciliation"
        )
    else:
        status = "FROZEN100_DIRECT_CREATOR_LINEAGE_CONFLICT_REMAINS"
        diagnosis = (
            "SG7B13_AND_SG7B16_REMAIN_INSUFFICIENTLY_SEPARATED_BY_NON_PERFORMANCE_PROVENANCE"
        )
        recommendation = (
            "Do not choose either creator by numerical closeness or chronology. Audit only their "
            "parent manifest/contract creation chains and exact frozen-model artifact hashes until "
            "one lineage is explicitly connected to the CR3 frozen array."
        )
        next_milestone = (
            "V15-SG7E1R26I-R14 — Frozen100 Creator Parent-Manifest / Model-Artifact Conflict Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": selected["creator_source"] if selected else "",
        "top_score": scores[0]["score"] if scores else "",
        "second_score": scores[1]["score"] if len(scores) > 1 else "",
        "margin": margin,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R13",
        "status": status,
        "diagnosis": diagnosis,
        "candidate_creators": [p.name for p in creators],
        "creator_identity": identity_rows,
        "model_lineage": model_rows,
        "workspace_lineage": workspace_rows,
        "X100_lineage": x100_rows,
        "serialization_lineage": serial_rows,
        "downstream_consumers": consumer_rows,
        "manifest_contract_lineage": manifest_rows,
        "provenance_scoring": scores,
        "selected_creator": selected["creator_source"] if selected else None,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "model_predict_executed": False,
            "X100_changed": False,
            "threshold_changed": False,
            "creator_selected_by_numerical_closeness": False,
            "creator_selected_by_chronology_only": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R13",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": selected["creator_source"] if selected else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("DIRECT CREATOR CANDIDATES")
    for r in identity_rows:
        print(
            f"  {r['creator_source']} | "
            f"frozen100={r['frozen100_assignment_count']} | "
            f"modelLoads={r['frozen_model_load_count']} | "
            f"serial={r['serialization_record_count']}"
        )

    print("\nPROVENANCE SCORING")
    for r in scores:
        print(
            f"  score={int(r['score']):6d} | "
            f"CR3={int(r['CR3_hits']):3d} | "
            f"R1F={int(r['R1F_hits']):3d} | "
            f"manifest={int(r['manifest_contract_hits']):3d} | "
            f"{r['creator_source']}"
        )

    if selected:
        print("\nSELECTED CREATOR")
        print(f"  Source                  : {selected['creator_source']}")
        print(f"  Margin                  : {margin}")

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
        IDENTITY_TABLE,
        MODEL_TABLE,
        WORKSPACE_TABLE,
        X100_TABLE,
        SERIAL_TABLE,
        CONSUMER_TABLE,
        MANIFEST_TABLE,
        SCORING_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R13 DIRECT FROZEN100 CREATOR LINEAGE CONFLICT AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No X100 tensor was changed.")
    print("No creator was selected by numerical closeness.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
