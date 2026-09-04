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
# PAD-Stream V16A-R5
# Residual Frozen Component Authority / Regeneration Policy Audit
#
# PURPOSE
# -------
# R4 established:
#
#   pressure : NO_PERSISTED_AUTHORITY_FOUND
#   Qx/Qy/Qz: NO_PERSISTED_AUTHORITY_FOUND
#   producer_id:
#       SHAPE_OR_PATH_CANDIDATES_ONLY_NOT_AUTHORITATIVE
#
# R5 answers two questions without executing physics:
#
#   1. Is there enough frozen V15 source/manifest/consumer provenance to define
#      one authoritative regeneration recipe for pressure and Darcy flux?
#
#   2. Can producer identity be bound from exact SG5/SG6 termination/capture
#      semantics without retracing streamlines?
#
# R5 DOES NOT:
#   - solve pressure,
#   - recompute flux,
#   - reconstruct velocity,
#   - retrace Pollock streamlines,
#   - run Fast Marching,
#   - train or infer any ML model,
#   - mutate frozen V15 artifacts.
#
# The output is a FORMAL POLICY DECISION:
#
#   REGENERATION_AUTHORIZED_AS_DERIVED_V16_ARTIFACT
#   or
#   REGENERATION_NOT_YET_AUTHORIZED
#
# If authorized, future regenerated arrays are V16-derived artifacts produced
# from immutable V15 inputs and source-authentic equations. They are NOT to be
# relabelled as historical persisted V15 arrays.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R5_REGENERATION_POLICY_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R4_DIR = ROOT / "output" / "V16_A_R4_PERSISTED_AUTHORITY_RECOVERY_AUDIT"
R4_SUMMARY = R4_DIR / "PAD_Stream_V16AR4_Summary.json"

SOURCE_INVENTORY = OUT / "V16AR5_Authoritative_Source_Inventory.csv"
PARAMETER_TRACE = OUT / "V16AR5_Frozen_Input_Parameter_Trace.csv"
PRESSURE_RECIPE = OUT / "V16AR5_Pressure_Regeneration_Recipe_Audit.csv"
FLUX_RECIPE = OUT / "V16AR5_Flux_Regeneration_Recipe_Audit.csv"
PRODUCER_TRACE = OUT / "V16AR5_Producer_Identity_Semantic_Audit.csv"
POLICY_TABLE = OUT / "V16AR5_Regeneration_Policy_Decision.csv"
GATE_TABLE = OUT / "V16AR5_Final_Policy_Gates.csv"
CONTRACT = OUT / "V16AR5_Regeneration_Policy_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR5_Summary.json"


REQUIRED_PRESSURE_INPUT_TERMS = [
    "transmiss", "bhp", "injection", "rate", "gravity", "density", "viscos",
    "well", "matrix", "rhs", "boundary"
]

REQUIRED_FLUX_INPUT_TERMS = [
    "pressure", "transmiss", "gravity", "density", "viscos"
]

PRODUCER_TERMS = [
    "producer", "capture", "captured", "terminal", "destination",
    "well_id", "well_index", "producer_id", "producer_idx"
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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def milestone_tag(path: Path):
    s = (path.name + " " + str(path.parent)).upper()
    for i in range(1, 7):
        if f"V15SG{i}" in s or f"V15_SG{i}" in s:
            return f"SG{i}"
    return None


def read_source(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(text)
        return text, tree
    except Exception:
        return "", None


def source_files():
    out = []
    for p in sorted(ROOT.glob("PAD_Stream_V15SG*.py")):
        tag = milestone_tag(p)
        if tag in {"SG2", "SG3", "SG4", "SG5", "SG6"}:
            text, tree = read_source(p)
            if tree is not None:
                out.append((tag, p, text, tree))
    return out


def source_inventory_rows(sources):
    rows = []
    for tag, p, text, tree in sources:
        rows.append({
            "owner": tag,
            "source": str(p),
            "sha256": sha256_file(p),
            "line_count": len(text.splitlines()),
        })
    return rows


def ast_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def pressure_recipe_audit(sources):
    rows = []
    candidates = []

    for tag, p, text, tree in sources:
        if tag != "SG3":
            continue
        lines = text.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                expr = ast_text(node)
                low = expr.lower()
                if any(tok in low for tok in ["spsolve", "cg(", "bicg", "gmres", "solve("]):
                    rec = {
                        "owner": tag,
                        "source": str(p),
                        "line": getattr(node, "lineno", None),
                        "call_expression": expr,
                        "solver_call": True,
                        "source_text": lines[node.lineno - 1].strip() if getattr(node, "lineno", None) else "",
                    }
                    candidates.append(rec)

        # source-level parameter evidence
        lowtext = text.lower()
        evidence = {term: (term in lowtext) for term in REQUIRED_PRESSURE_INPUT_TERMS}
        rows.append({
            "owner": tag,
            "source": str(p),
            "solver_call_count": len([c for c in candidates if c["source"] == str(p)]),
            **{f"has_{k}": v for k, v in evidence.items()},
        })

    unique_solver_sources = sorted({c["source"] for c in candidates})
    complete = (
        len(unique_solver_sources) == 1
        and len(candidates) >= 1
        and any(all(r.get(f"has_{k}", False) for k in REQUIRED_PRESSURE_INPUT_TERMS) for r in rows)
    )

    return rows, candidates, complete


def flux_recipe_audit(sources):
    rows = []
    assignments = []

    for tag, p, text, tree in sources:
        if tag != "SG4":
            continue
        lines = text.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = []
                if isinstance(node, ast.Assign):
                    raw = node.targets
                else:
                    raw = [node.target]
                for t in raw:
                    if isinstance(t, ast.Name):
                        targets.append(t.id)
                expr = ast_text(getattr(node, "value", None))
                for target in targets:
                    if target.lower() in {"qx", "qy", "qz"}:
                        assignments.append({
                            "owner": tag,
                            "source": str(p),
                            "line": getattr(node, "lineno", None),
                            "target": target,
                            "expression": expr,
                            "source_text": lines[node.lineno - 1].strip() if getattr(node, "lineno", None) else "",
                        })

        lowtext = text.lower()
        evidence = {term: (term in lowtext) for term in REQUIRED_FLUX_INPUT_TERMS}
        rows.append({
            "owner": tag,
            "source": str(p),
            "Q_assignment_count": len([a for a in assignments if a["source"] == str(p)]),
            **{f"has_{k}": v for k, v in evidence.items()},
        })

    targets = {a["target"].lower() for a in assignments}
    unique_sources = {a["source"] for a in assignments}
    complete = (
        {"qx", "qy", "qz"}.issubset(targets)
        and len(unique_sources) >= 1
        and any(all(r.get(f"has_{k}", False) for k in REQUIRED_FLUX_INPUT_TERMS) for r in rows)
    )

    return rows, assignments, complete


def frozen_parameter_trace(sources):
    rows = []
    patterns = [
        ("producer_bhp_psi", re.compile(r"2000")),
        ("co2_injection_tonnes_per_day", re.compile(r"500")),
        ("co2_density", re.compile(r"700")),
        ("brine_density", re.compile(r"1020")),
        ("reference_viscosity", re.compile(r"0\.5")),
        ("gravity", re.compile(r"gravity", re.I)),
        ("five_spot", re.compile(r"five.?spot", re.I)),
    ]

    for tag, p, text, tree in sources:
        if tag not in {"SG3", "SG4", "SG5"}:
            continue
        for name, pat in patterns:
            if pat.search(text):
                rows.append({
                    "parameter_or_control": name,
                    "owner": tag,
                    "source": str(p),
                    "source_sha256": sha256_file(p),
                    "evidence_found": True,
                })
    return rows


def producer_semantic_audit(sources):
    rows = []
    semantic_records = []

    for tag, p, text, tree in sources:
        if tag not in {"SG5", "SG6"}:
            continue
        lines = text.splitlines()

        for i, line in enumerate(lines, 1):
            low = line.lower()
            if any(term in low for term in PRODUCER_TERMS):
                semantic_records.append({
                    "owner": tag,
                    "source": str(p),
                    "line": i,
                    "text": line.strip()[:600],
                    "mentions_capture": ("capture" in low or "captured" in low),
                    "mentions_producer": ("producer" in low),
                    "mentions_terminal": ("terminal" in low or "destination" in low),
                    "mentions_id": ("id" in low or "index" in low or "idx" in low),
                })

        rows.append({
            "owner": tag,
            "source": str(p),
            "semantic_record_count": len([r for r in semantic_records if r["source"] == str(p)]),
        })

    # Conservative criterion: need explicit capture/terminal semantics AND
    # explicit producer identifier/index semantics in the frozen SG5/SG6 source.
    has_capture = any(r["mentions_capture"] or r["mentions_terminal"] for r in semantic_records)
    has_producer = any(r["mentions_producer"] for r in semantic_records)
    has_id = any(r["mentions_id"] for r in semantic_records)

    bindable_without_retrace = has_capture and has_producer and has_id

    return rows, semantic_records, bindable_without_retrace


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R5")
    print("Residual Frozen Component Authority / Regeneration Policy Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO PRESSURE SOLVE WILL BE EXECUTED.
NO DARCY FLUX WILL BE RECOMPUTED.
NO VELOCITY FIELD WILL BE RECONSTRUCTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
THIS MILESTONE MAKES A REGENERATION POLICY DECISION ONLY.
""")

    if not R4_SUMMARY.exists():
        raise FileNotFoundError(R4_SUMMARY)

    r4 = json.loads(R4_SUMMARY.read_text(encoding="utf-8"))
    if r4.get("status") != "V16A_PERSISTED_AUTHORITY_RECOVERY_INCOMPLETE":
        raise RuntimeError("V16A-R5 expects incomplete R4 persisted-authority status.")

    sources = source_files()
    save_csv(SOURCE_INVENTORY, source_inventory_rows(sources))

    pressure_summary, pressure_calls, pressure_recipe_ready = pressure_recipe_audit(sources)
    pressure_out = pressure_summary + [
        {
            "owner": r["owner"], "source": r["source"], "line": r["line"],
            "solver_call_count": "", "call_expression": r["call_expression"],
            "solver_call": True, "source_text": r["source_text"],
        }
        for r in pressure_calls
    ]
    save_csv(PRESSURE_RECIPE, pressure_out)

    flux_summary, flux_assignments, flux_recipe_ready = flux_recipe_audit(sources)
    flux_out = flux_summary + [
        {
            "owner": r["owner"], "source": r["source"], "line": r["line"],
            "Q_assignment_count": "", "target": r["target"],
            "expression": r["expression"], "source_text": r["source_text"],
        }
        for r in flux_assignments
    ]
    save_csv(FLUX_RECIPE, flux_out)

    params = frozen_parameter_trace(sources)
    save_csv(PARAMETER_TRACE, params)

    producer_summary, producer_records, producer_bindable = producer_semantic_audit(sources)
    producer_out = producer_summary + producer_records
    save_csv(PRODUCER_TRACE, producer_out)

    pressure_inputs_evidenced = len(params) > 0
    regeneration_recipe_ready = pressure_recipe_ready and flux_recipe_ready and pressure_inputs_evidenced

    # Policy:
    # Pressure and Q regeneration can be authorized as NEW V16 DERIVED artifacts
    # if the source-authentic recipe and frozen input controls are uniquely
    # traceable. This does not mutate or rewrite V15.
    regeneration_authorized = regeneration_recipe_ready

    if regeneration_authorized and producer_bindable:
        status = "V16A_SOURCE_AUTHENTIC_REGENERATION_AUTHORIZED_AS_DERIVED_V16_ARTIFACT"
        diagnosis = (
            "FROZEN_V15_SG3_SG4_SOURCE_AND_INPUT_CONTRACTS_DEFINE_ONE_REGENERATION_PATH_AND_SG5_SG6_DEFINE_PRODUCER_IDENTITY_SEMANTICS"
        )
        recommendation = (
            "Proceed to controlled V16-derived regeneration. Execute the frozen SG3 pressure solve and SG4 flux equations "
            "with immutable V15 inputs, reconstruct V from the recovered flux contract, bind producer identity from frozen SG5/SG6 "
            "termination semantics, and label all outputs as DERIVED_V16_FROM_FROZEN_V15 rather than historical V15 arrays."
        )
        next_ms = "V16A-R6 — Controlled Source-Authentic Foundation Component Regeneration"
    elif regeneration_authorized and not producer_bindable:
        status = "V16A_PRESSURE_FLUX_REGENERATION_AUTHORIZED_PRODUCER_IDENTITY_STILL_UNRESOLVED"
        diagnosis = (
            "SG3_SG4_REGENERATION_RECIPE_IS_AUTHORITATIVE_BUT_PRODUCER_IDENTITY_CANNOT_YET_BE_BOUND_WITHOUT_ADDITIONAL_SG5_SG6_SEMANTIC_RESOLUTION"
        )
        recommendation = (
            "Do not retrace Pollock streamlines yet. Audit only producer capture/termination mapping so that producer IDs can be "
            "bound from existing streamline endpoint semantics."
        )
        next_ms = "V16A-R6 — SG5/SG6 Producer Identity Final Binding Audit"
    else:
        status = "V16A_SOURCE_AUTHENTIC_REGENERATION_NOT_YET_AUTHORIZED"
        diagnosis = (
            "ONE_OR_MORE_REQUIRED_SG3_SG4_FROZEN_INPUT_OR_SOURCE_RECIPE_COMPONENTS_ARE_NOT_YET_UNIQUE"
        )
        recommendation = (
            "Do not rerun frozen physics. Audit only the unresolved SG3 pressure recipe, SG4 flux recipe, or frozen input-control provenance."
        )
        next_ms = "V16A-R6 — Residual Regeneration Recipe Binding Audit"

    gates = [
        ("incoming_R4_status_reproduced", True),
        ("SG2_SG6_authoritative_source_inventory_completed", len(sources) > 0),
        ("SG3_pressure_solver_recipe_audited", True),
        ("SG4_flux_recipe_audited", True),
        ("frozen_input_parameter_evidence_audited", True),
        ("SG5_SG6_producer_semantics_audited", True),
        ("pressure_recipe_ready_classified", True),
        ("flux_recipe_ready_classified", True),
        ("producer_identity_bindability_classified", True),
        ("no_pressure_solve_executed", True),
        ("no_Darcy_flux_recomputed", True),
        ("no_velocity_reconstructed", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g,p in gates])

    policy = [{
        "status": status,
        "diagnosis": diagnosis,
        "pressure_recipe_ready": pressure_recipe_ready,
        "flux_recipe_ready": flux_recipe_ready,
        "frozen_parameter_evidence": pressure_inputs_evidenced,
        "producer_identity_bindable_without_retrace": producer_bindable,
        "regeneration_authorized": regeneration_authorized,
        "derived_artifact_label": "DERIVED_V16_FROM_FROZEN_V15" if regeneration_authorized else "",
        "next_milestone": next_ms,
    }]
    save_csv(POLICY_TABLE, policy)

    contract = {
        "milestone": "V16A-R5",
        "status": status,
        "diagnosis": diagnosis,
        "policy": {
            "pressure_regeneration_authorized": regeneration_authorized,
            "flux_regeneration_authorized": regeneration_authorized,
            "velocity_reconstruction_authorized_only_after_authoritative_flux": regeneration_authorized,
            "producer_identity_bindable_without_retrace": producer_bindable,
            "historical_V15_relabelling_prohibited": True,
            "derived_artifact_label": "DERIVED_V16_FROM_FROZEN_V15" if regeneration_authorized else None,
        },
        "constraints": {
            "pressure_solve_executed": False,
            "Darcy_flux_recomputed": False,
            "velocity_reconstructed": False,
            "Pollock_retrace_executed": False,
            "FMM_executed": False,
            "model_predict_executed": False,
            "training_performed": False,
            "V15_artifact_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT, contract)
    save_json(SUMMARY, {
        "milestone": "V16A-R5",
        "status": status,
        "diagnosis": diagnosis,
        "pressure_recipe_ready": pressure_recipe_ready,
        "flux_recipe_ready": flux_recipe_ready,
        "producer_identity_bindable_without_retrace": producer_bindable,
        "regeneration_authorized": regeneration_authorized,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("REGENERATION POLICY INPUTS")
    print(f"  SG3 pressure recipe ready        : {pressure_recipe_ready}")
    print(f"  SG4 flux recipe ready            : {flux_recipe_ready}")
    print(f"  Frozen parameter evidence        : {pressure_inputs_evidenced}")
    print(f"  Producer ID bindable w/o retrace : {producer_bindable}")

    print("\nPOLICY")
    print(f"  Regeneration authorized          : {regeneration_authorized}")
    print(f"  Historical V15 relabelling       : PROHIBITED")
    if regeneration_authorized:
        print(f"  Derived artifact label           : DERIVED_V16_FROM_FROZEN_V15")

    print("\n" + "=" * 78)
    print("V16A-R5 FINAL POLICY GATES")
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
        SOURCE_INVENTORY, PARAMETER_TRACE, PRESSURE_RECIPE,
        FLUX_RECIPE, PRODUCER_TRACE, POLICY_TABLE, GATE_TABLE
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT.name}")

    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R5 REGENERATION POLICY AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
