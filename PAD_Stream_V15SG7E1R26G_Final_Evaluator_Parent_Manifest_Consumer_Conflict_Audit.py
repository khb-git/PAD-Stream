from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict

# =============================================================================
# PAD-Stream V15-SG7E1R26G
# Final Evaluator Parent-Manifest / Consumer Conflict Audit
#
# DIAGNOSTIC-ONLY FINAL SOURCE-AUTHORITY MILESTONE
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
# R26F established:
#
#   UPSTREAM_EVALUATOR_LINEAGE_CONFLICT_REMAINS
#
# with the top two runtime-source candidates:
#
#   1. PAD_Stream_V15SG7B6G_Residual_Metric_Reconciliation.py
#   2. PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py
#
# R26G resolves ONLY these two candidates.
#
# It audits:
#
#   model/checkpoint
#       -> source
#       -> prediction
#       -> saved numerical artifact
#       -> parent manifest / contract
#       -> downstream consumer
#       -> SG7CR3 / L2 frozen lineage
#
# Candidate performance is NEVER used.
# No broader source search is permitted.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26G"
OUT.mkdir(parents=True, exist_ok=True)

R26F_DIR = ROOT / "output" / "V15_SG7E1R26F"
R26F_SUMMARY = R26F_DIR / "PAD_Stream_V15SG7E1R26F_Summary.json"
R26F_SCORING = R26F_DIR / "V15SG7E1R26F_Lineage_Resolution_Scoring.csv"

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

# Only these two candidates may compete in R26G.
CANDIDATE_NAMES = [
    "PAD_Stream_V15SG7B6G_Residual_Metric_Reconciliation.py",
    "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py",
]

# Outputs
CANDIDATE_TABLE = OUT / "V15SG7E1R26G_Final_Two_Candidate_Identity.csv"
ARTIFACT_TABLE = OUT / "V15SG7E1R26G_Prediction_Artifact_Save_Lineage.csv"
MANIFEST_TABLE = OUT / "V15SG7E1R26G_Parent_Manifest_Contract_Lineage.csv"
CONSUMER_TABLE = OUT / "V15SG7E1R26G_Downstream_Consumer_Lineage.csv"
CR3_TABLE = OUT / "V15SG7E1R26G_CR3_L2_Lineage_Match.csv"
SCORING_TABLE = OUT / "V15SG7E1R26G_Final_Lineage_Authority_Scoring.csv"
DECISION_TABLE = OUT / "V15SG7E1R26G_Final_Evaluator_Authority_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26G_Final_Evaluator_Parent_Consumer_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26G_Summary.json"


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


def node_src(text, node):
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""


def parse_saved_artifacts(path: Path):
    """
    Trace np.savez / np.savez_compressed / np.save calls and likely output paths.
    """
    text = safe_text(path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node).lower()
        if not (
            "savez" in cname
            or "np.save" in cname
            or cname.endswith(".save")
        ):
            continue

        expr = node_src(text, node)
        rows.append({
            "source": str(path),
            "line": getattr(node, "lineno", ""),
            "call": call_name(node),
            "expression": expr[:4000],
        })

    return rows


def referenced_outputs_from_source(path: Path):
    """
    Extract literal strings that look like output files or milestone directories.
    """
    text = safe_text(path)
    refs = set()

    patterns = [
        r'["\']([^"\']+\.npz)["\']',
        r'["\']([^"\']+\.json)["\']',
        r'["\']([^"\']+\.csv)["\']',
        r'["\'](V15_SG7[^"\']+)["\']',
    ]

    for pat in patterns:
        for m in re.findall(pat, text, flags=re.I):
            refs.add(m)

    return sorted(refs)


def project_json_files():
    return sorted((ROOT / "output").rglob("*.json")) if (ROOT / "output").exists() else []


def project_python_files():
    return sorted(ROOT.glob("*.py"))


def search_manifest_contract_mentions(candidate_path: Path, candidate_refs: list[str]):
    """
    Search output JSONs for candidate filename, candidate stem, and its explicit
    saved artifact references.
    """
    tokens = {
        candidate_path.name,
        candidate_path.stem,
    }
    tokens.update(candidate_refs)

    rows = []

    for jp in project_json_files():
        text = safe_text(jp)
        low = text.lower()

        matched = [t for t in tokens if t and t.lower() in low]
        if matched:
            rows.append({
                "candidate": candidate_path.name,
                "json_path": str(jp),
                "matched_tokens": ";".join(sorted(matched)),
                "match_count": len(matched),
            })

    return rows


def search_downstream_consumers(candidate_path: Path, candidate_refs: list[str]):
    """
    Search Python sources for consumers of artifacts created/referenced by the
    candidate. Excludes the candidate source itself.
    """
    tokens = set(candidate_refs)
    tokens.add(candidate_path.name)
    tokens.add(candidate_path.stem)

    rows = []

    for py in project_python_files():
        if py.resolve() == candidate_path.resolve():
            continue

        text = safe_text(py)
        low = text.lower()

        matched = [t for t in tokens if t and t.lower() in low]
        if not matched:
            continue

        cr3 = "sg7cr3" in py.name.lower()
        r1f = "r1f" in py.name.lower()
        freeze = "freeze" in py.name.lower() or "frozen" in py.name.lower()

        rows.append({
            "candidate": candidate_path.name,
            "consumer_source": str(py),
            "matched_tokens": ";".join(sorted(matched)),
            "match_count": len(matched),
            "is_CR3_consumer": cr3,
            "is_R1F_consumer": r1f,
            "is_freeze_consumer": freeze,
        })

    return rows


def source_runtime_semantics(path: Path):
    """
    Small, explicit semantic audit for the final two candidates.
    """
    text = safe_text(path)
    low = text.lower()

    pred = low.count(".predict(") + low.count("predict_on_batch")
    fit = low.count(".fit(") + low.count("train_on_batch")
    load = low.count("load_model")
    save = low.count("savez") + low.count("np.save(")
    time = low.count("time_days") + low.count("t_days") + low.count("physical_time")
    xi = low.count("xi")
    tau = low.count("tau") + low.count("tof")

    return {
        "predict_count": pred,
        "fit_count": fit,
        "load_model_count": load,
        "save_array_count": save,
        "time_mentions": time,
        "xi_mentions": xi,
        "tau_tof_mentions": tau,
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26G")
    print("Final Evaluator Parent-Manifest / Consumer Conflict Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
ONLY THE TOP TWO R26F EVALUATOR LINEAGES WILL BE AUDITED.
""")

    s26f = load_json(R26F_SUMMARY)
    if s26f.get("status") != "UPSTREAM_EVALUATOR_LINEAGE_CONFLICT_REMAINS":
        raise RuntimeError("R26G requires unresolved R26F evaluator-lineage conflict.")

    model_rows = load_csv(R18_MODEL)
    if len(model_rows) != 1:
        raise RuntimeError("Expected exactly one authoritative model record.")

    model_path = Path(model_rows[0]["path"])
    model_name = model_path.name
    model_sha = model_rows[0]["sha256"]

    # -------------------------------------------------------------------------
    # Exact final-two candidate identity
    # -------------------------------------------------------------------------

    candidates = []
    for name in CANDIDATE_NAMES:
        p = ROOT / name
        if not p.exists():
            raise FileNotFoundError(f"Missing R26G candidate: {p}")

        sem = source_runtime_semantics(p)
        refs = referenced_outputs_from_source(p)

        candidates.append({
            "path": p,
            "name": name,
            "semantics": sem,
            "refs": refs,
        })

    save_csv(CANDIDATE_TABLE, [
        {
            "candidate": c["name"],
            "source": str(c["path"]),
            **c["semantics"],
            "explicit_artifact_reference_count": len(c["refs"]),
        }
        for c in candidates
    ])

    # -------------------------------------------------------------------------
    # Save/artifact lineage
    # -------------------------------------------------------------------------

    artifact_rows = []

    for c in candidates:
        saves = parse_saved_artifacts(c["path"])
        if not saves:
            artifact_rows.append({
                "candidate": c["name"],
                "source": str(c["path"]),
                "line": "",
                "call": "",
                "expression": "",
                "artifact_reference_count": len(c["refs"]),
                "artifact_references": ";".join(c["refs"]),
            })
        else:
            for row in saves:
                artifact_rows.append({
                    "candidate": c["name"],
                    **row,
                    "artifact_reference_count": len(c["refs"]),
                    "artifact_references": ";".join(c["refs"]),
                })

    save_csv(ARTIFACT_TABLE, artifact_rows)

    # -------------------------------------------------------------------------
    # Parent manifest / contract lineage
    # -------------------------------------------------------------------------

    manifest_rows = []

    for c in candidates:
        rows = search_manifest_contract_mentions(c["path"], c["refs"])
        manifest_rows.extend(rows)

    save_csv(MANIFEST_TABLE, manifest_rows)

    # -------------------------------------------------------------------------
    # Downstream consumer lineage
    # -------------------------------------------------------------------------

    consumer_rows = []

    for c in candidates:
        rows = search_downstream_consumers(c["path"], c["refs"])
        consumer_rows.extend(rows)

    save_csv(CONSUMER_TABLE, consumer_rows)

    # -------------------------------------------------------------------------
    # CR3/L2 lineage authority
    # -------------------------------------------------------------------------

    cr3_rows = []
    score_rows = []

    r26f_scores = {
        r["source"]: int(float(r["lineage_score"]))
        for r in load_csv(R26F_SCORING)
    }

    for c in candidates:
        cname = c["name"]

        mans = [r for r in manifest_rows if r["candidate"] == cname]
        cons = [r for r in consumer_rows if r["candidate"] == cname]

        cr3_cons = [r for r in cons if str(r["is_CR3_consumer"]).lower() in {"true", "1"}]
        r1f_cons = [r for r in cons if str(r["is_R1F_consumer"]).lower() in {"true", "1"}]
        freeze_cons = [r for r in cons if str(r["is_freeze_consumer"]).lower() in {"true", "1"}]

        manifest_cr3 = [
            r for r in mans
            if "sg7cr3" in r["json_path"].lower()
            or "r1f" in r["json_path"].lower()
        ]

        cr3_rows.append({
            "candidate": cname,
            "manifest_records": len(mans),
            "manifest_CR3_R1F_records": len(manifest_cr3),
            "consumer_records": len(cons),
            "CR3_consumers": len(cr3_cons),
            "R1F_consumers": len(r1f_cons),
            "freeze_consumers": len(freeze_cons),
        })

        # ---------------------------------------------------------------------
        # Final authority scoring
        #
        # Strongest evidence:
        #   - direct CR3/R1F/freeze consumer
        #   - parent manifest/contract linkage into CR3/R1F
        #   - explicit artifact save chain
        #
        # Supporting:
        #   - no-training runtime semantics
        #   - previous R26F lineage score
        #
        # Performance is not used.
        # ---------------------------------------------------------------------

        score = 0
        reasons = []

        if len(cr3_cons) > 0:
            score += 1000 * len(cr3_cons)
            reasons.append("direct_CR3_consumer")

        if len(r1f_cons) > 0:
            score += 1500 * len(r1f_cons)
            reasons.append("direct_R1F_consumer")

        if len(freeze_cons) > 0:
            score += 2000 * len(freeze_cons)
            reasons.append("freeze_consumer")

        if len(manifest_cr3) > 0:
            score += 700 * len(manifest_cr3)
            reasons.append("CR3_R1F_manifest_lineage")

        if len(mans) > 0:
            score += 100 * len(mans)
            reasons.append("manifest_contract_lineage")

        save_count = len(parse_saved_artifacts(c["path"]))
        if save_count > 0:
            score += 100 * save_count
            reasons.append("persists_numerical_artifact")

        sem = c["semantics"]
        if sem["predict_count"] > 0 and sem["fit_count"] == 0:
            score += 300
            reasons.append("no_training_runtime_inference")

        old_score = r26f_scores.get(str(c["path"]), 0)
        score += min(old_score, 1000) // 5
        reasons.append("R26F_lineage_support")

        score_rows.append({
            "candidate": cname,
            "source": str(c["path"]),
            "R26F_lineage_score": old_score,
            "manifest_records": len(mans),
            "manifest_CR3_R1F_records": len(manifest_cr3),
            "consumer_records": len(cons),
            "CR3_consumers": len(cr3_cons),
            "R1F_consumers": len(r1f_cons),
            "freeze_consumers": len(freeze_cons),
            "save_call_count": save_count,
            "final_authority_score": score,
            "reasons": ";".join(reasons),
        })

    save_csv(CR3_TABLE, cr3_rows)

    score_rows.sort(key=lambda r: int(r["final_authority_score"]), reverse=True)
    save_csv(SCORING_TABLE, score_rows)

    # -------------------------------------------------------------------------
    # Final resolution
    # -------------------------------------------------------------------------

    top = score_rows[0]
    second = score_rows[1]
    margin = int(top["final_authority_score"]) - int(second["final_authority_score"])

    direct_lineage = (
        int(top["R1F_consumers"]) > 0
        or int(top["freeze_consumers"]) > 0
        or int(top["manifest_CR3_R1F_records"]) > 0
        or int(top["CR3_consumers"]) > 0
    )

    resolved = direct_lineage and margin >= 500

    if resolved:
        status = "AUTHORITATIVE_UPSTREAM_EVALUATOR_SOURCE_RESOLVED"
        diagnosis = (
            "ONE_FINAL_RUNTIME_SOURCE_HAS_UNIQUE_PARENT_MANIFEST_AND_DOWNSTREAM_CR3_L2_CONSUMER_LINEAGE"
        )
        recommendation = (
            "The final two-source conflict is resolved by artifact/manifest/consumer provenance. "
            "One runtime source uniquely reaches the SG7CR3/R1F/L2 deployment lineage. Preserve "
            "this source as the authoritative evaluator parent. Proceed to bind only its exact "
            "model-input tensor construction, physical-time transform, prediction output, and "
            "postprocessing state contract before executing the 100-day runtime control."
        )
        next_milestone = (
            "V15-SG7E1R26H — Authoritative Evaluator Input / Output Contract Audit"
        )
    else:
        status = "FINAL_EVALUATOR_PARENT_CONSUMER_CONFLICT_REMAINS"
        diagnosis = (
            "TOP_TWO_RUNTIME_SOURCES_DO_NOT_YET_HAVE_SUFFICIENT_CR3_L2_PARENT_CONSUMER_SEPARATION"
        )
        recommendation = (
            "Do not generate later-time states. Audit only the persisted NPZ/JSON artifacts "
            "created by the two R26G candidates and follow their exact consumer chains into "
            "SG7CR3/R1F. Do not broaden the candidate set and do not use numerical performance."
        )
        next_milestone = (
            "V15-SG7E1R26H — Final Two Artifact-Consumer Chain Audit"
        )

    checks = [
        ("Incoming R26F conflict reproduced", True),
        ("Exactly two R26G candidates retained", len(candidates) == 2),
        ("Authoritative frozen model identity retained", len(model_rows) == 1),
        ("Candidate save/artifact lineage audited", True),
        ("Parent manifest/contract lineage audited", True),
        ("Downstream consumer lineage audited", True),
        ("CR3/R1F/freeze lineage audited", True),
        ("No candidate performance used", True),
        ("No broader source search used", True),
        ("No later-time state generated", True),
        ("No training performed", True),
        ("No threshold changed or relaxed", True),
    ]

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_candidate": top["candidate"] if resolved else "",
        "selected_source": top["source"] if resolved else "",
        "top_score": top["final_authority_score"],
        "second_score": second["final_authority_score"],
        "margin": margin,
        "direct_lineage_evidence": direct_lineage,
        "resolved": resolved,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26G",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_model": {
            "path": str(model_path),
            "filename": model_name,
            "sha256": model_sha,
        },
        "candidate_scope": CANDIDATE_NAMES,
        "selection": {
            "resolved": resolved,
            "selected_candidate": top["candidate"] if resolved else None,
            "selected_source": top["source"] if resolved else None,
            "top_score": int(top["final_authority_score"]),
            "second_score": int(second["final_authority_score"]),
            "margin": margin,
            "direct_lineage_evidence": direct_lineage,
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
            "candidate_set_broadened": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26G",
        "status": status,
        "diagnosis": diagnosis,
        "selected_candidate": top["candidate"] if resolved else None,
        "selected_source": top["source"] if resolved else None,
        "authority_margin": margin,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("FINAL TWO EVALUATOR CANDIDATES")
    for c in candidates:
        print(f"  {c['name']}")

    print("\nFINAL PARENT / CONSUMER AUTHORITY")
    for row in score_rows:
        print(
            f"  score={int(row['final_authority_score']):5d} | "
            f"CR3={int(row['CR3_consumers']):2d} | "
            f"R1F={int(row['R1F_consumers']):2d} | "
            f"freeze={int(row['freeze_consumers']):2d} | "
            f"manifestCR3={int(row['manifest_CR3_R1F_records']):2d} | "
            f"{row['candidate']}"
        )

    print("\nFINAL AUTHORITY MARGIN")
    print(f"  Top score               : {top['final_authority_score']}")
    print(f"  Second score            : {second['final_authority_score']}")
    print(f"  Margin                  : {margin}")
    print(f"  Direct lineage evidence : {direct_lineage}")

    if resolved:
        print("\nSELECTED AUTHORITATIVE EVALUATOR PARENT")
        print(f"  Candidate               : {top['candidate']}")
        print(f"  Source                  : {top['source']}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26G FINAL PARENT / CONSUMER VALIDATION")
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
        CANDIDATE_TABLE,
        ARTIFACT_TABLE,
        MANIFEST_TABLE,
        CONSUMER_TABLE,
        CR3_TABLE,
        SCORING_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26G FINAL EVALUATOR PARENT-MANIFEST / CONSUMER CONFLICT AUDIT: COMPLETE")
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
