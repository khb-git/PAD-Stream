from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import re
from collections import defaultdict, Counter


# =============================================================================
# PAD-Stream V15-SG7E0R
# Historical SG7E Gate Authority Reconciliation
#
# FORENSIC / CONTRACT-PROVENANCE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO DEPLOYMENT CORRECTION PERFORMED.
#
# PURPOSE
# -------
# SG7E0 found:
#
#   historical SG7E sources      = 81
#   threshold/gate records       = 45
#   explicit authoritative      = 0
#   unknown role                = 43
#
# Therefore SG7E1 cannot safely proceed until historical gate authority is
# reconciled from provenance.
#
# SG7E0R:
#
#   1. loads SG7E0 discovery / threshold evidence,
#   2. searches historical SG7E source lineage,
#   3. identifies repeated gate symbols and duplicate definitions,
#   4. searches for pass/fail use, acceptance language, and final-screen usage,
#   5. scores evidence for AUTHORITATIVE / DIAGNOSTIC / SUPERSEDED / UNKNOWN,
#   6. detects conflicting numerical thresholds,
#   7. constructs a canonical historical gate registry,
#   8. refuses to resolve ambiguity by changing a threshold.
#
# SG7E0R does NOT evaluate the frozen P4 field against gates.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E0R"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7E0_DIR = ROOT / "output" / "V15_SG7E0"

SG7E0_SUMMARY = SG7E0_DIR / "PAD_Stream_V15SG7E0_Summary.json"
SG7E0_CONTRACT = SG7E0_DIR / "V15SG7E0_Deployment_Validation_Contract.json"
SG7E0_SOURCES = SG7E0_DIR / "V15SG7E0_Historical_SG7E_Source_Discovery.csv"
SG7E0_THRESHOLDS = SG7E0_DIR / "V15SG7E0_SG7E_Threshold_Provenance.csv"

SG7D6_FREEZE_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E0R_Summary.json"

SOURCE_LINEAGE_TABLE = OUT / "V15SG7E0R_SG7E_Source_Lineage.csv"
SYMBOL_TABLE = OUT / "V15SG7E0R_Gate_Symbol_Registry.csv"
USAGE_TABLE = OUT / "V15SG7E0R_Gate_Usage_Evidence.csv"
CONFLICT_TABLE = OUT / "V15SG7E0R_Threshold_Conflict_Audit.csv"
AUTHORITY_TABLE = OUT / "V15SG7E0R_Gate_Authority_Scoring.csv"
CANONICAL_TABLE = OUT / "V15SG7E0R_Canonical_SG7E_Gate_Registry.csv"
DECISION_TABLE = OUT / "V15SG7E0R_Authority_Reconciliation_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E0R_Reconciled_SG7E_Gate_Authority_Contract.json"

# -----------------------------------------------------------------------------
# Evidence vocabulary
# -----------------------------------------------------------------------------

AUTHORITATIVE_TOKENS = (
    "final gate",
    "final_gate",
    "acceptance gate",
    "acceptance_gate",
    "deployment gate",
    "deployment_gate",
    "must pass",
    "must_pass",
    "freeze ready",
    "freeze_ready",
    "final screen",
    "final_screen",
    "authoritative",
    "accepted",
    "candidate passes",
    "candidate_passes",
)

DIAGNOSTIC_TOKENS = (
    "diagnostic only",
    "diagnostic_only",
    "report only",
    "report_only",
    "informational",
    "diagnostic",
)

SUPERSEDED_TOKENS = (
    "deprecated",
    "superseded",
    "historical only",
    "historical_only",
    "legacy",
    "obsolete",
)

FAIL_USAGE_TOKENS = (
    "[fail]",
    "failed gates",
    "failed_gates",
    "fails=",
    "gate matrix",
    "gate_matrix",
)

PASS_USAGE_TOKENS = (
    "[pass]",
    "passes complete contract",
    "passes_complete_contract",
    "all gates pass",
    "all_gates_pass",
)

# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
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


def sha256(path: Path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def normalize_symbol(symbol: str):
    return re.sub(r"[^A-Za-z0-9_]+", "", str(symbol)).strip()


def parse_numeric(value):
    try:
        return float(value)
    except Exception:
        return None


def source_generation_rank(path: str):
    """
    Approximate milestone recency from SG7E naming.

    Later numeric suffixes rank higher. This is only lineage evidence; it does
    not itself establish authority.
    """
    name = Path(path).name.upper()

    # Examples: SG7E, SG7E1, SG7E2R, SG7E10...
    m = re.search(r"SG7E(\d+)", name)
    if m:
        return int(m.group(1))

    # Plain SG7E baseline
    if "SG7E" in name:
        return 0

    return -1


def score_usage(text: str):
    t = text.lower()

    score = 0
    reasons = []

    if any(tok in t for tok in AUTHORITATIVE_TOKENS):
        score += 6
        reasons.append("authoritative_language")

    if any(tok in t for tok in FAIL_USAGE_TOKENS):
        score += 4
        reasons.append("used_in_failure_screen")

    if any(tok in t for tok in PASS_USAGE_TOKENS):
        score += 4
        reasons.append("used_in_pass_screen")

    if any(tok in t for tok in DIAGNOSTIC_TOKENS):
        score -= 6
        reasons.append("diagnostic_language")

    if any(tok in t for tok in SUPERSEDED_TOKENS):
        score -= 8
        reasons.append("superseded_or_legacy_language")

    return score, reasons


def classify_from_score(score, reasons):
    if any("superseded" in r for r in reasons):
        return "SUPERSEDED"
    if score >= 6:
        return "AUTHORITATIVE"
    if score <= -5:
        return "DIAGNOSTIC"
    return "UNKNOWN"


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E0R")
    print("Historical SG7E Gate Authority Reconciliation")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO SUPPORT MASK OR BACKGROUND POLICY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO DEPLOYMENT CORRECTION WILL BE PERFORMED.
""")

    e0_summary = load_json(SG7E0_SUMMARY)
    e0_contract = load_json(SG7E0_CONTRACT)
    freeze_manifest = load_json(SG7D6_FREEZE_MANIFEST)

    if (
        e0_summary.get("status")
        != "SG7E_CONTRACT_PROVENANCE_REQUIRES_CLARIFICATION"
    ):
        raise RuntimeError(
            "SG7E0R requires the SG7E0 provenance-clarification status."
        )

    if (
        e0_summary.get("diagnosis")
        != "SG7E_GATE_EVIDENCE_FOUND_BUT_AUTHORITY_NOT_EXPLICITLY_RESOLVED"
    ):
        raise RuntimeError(
            "SG7E0R requires the SG7E0 gate-authority diagnosis."
        )

    if (
        freeze_manifest.get("status")
        != "SG7D_FULL_GRID_CANDIDATE_FROZEN"
    ):
        raise RuntimeError(
            "SG7E0R requires the frozen SG7D6 deployment field."
        )

    source_rows = load_csv(SG7E0_SOURCES)
    threshold_rows = load_csv(SG7E0_THRESHOLDS)

    # -------------------------------------------------------------------------
    # Build source lineage
    # -------------------------------------------------------------------------

    lineage_rows = []

    for row in source_rows:
        path = Path(row["path"])
        text = safe_text(path)
        score, reasons = score_usage(text)

        lineage_rows.append({
            "path": str(path),
            "name": path.name,
            "role": row.get("role"),
            "generation_rank": source_generation_rank(str(path)),
            "authority_language_score": score,
            "authority_reasons": ";".join(reasons),
            "contains_final_gate_language":
                any(tok in text.lower() for tok in ("final gate", "final_gate")),
            "contains_acceptance_language":
                any(tok in text.lower() for tok in ("acceptance", "accepted")),
            "contains_diagnostic_language":
                any(tok in text.lower() for tok in DIAGNOSTIC_TOKENS),
            "sha256": row.get("sha256") or sha256(path),
        })

    save_csv(SOURCE_LINEAGE_TABLE, lineage_rows)

    lineage_lookup = {
        row["path"]: row
        for row in lineage_rows
    }

    # -------------------------------------------------------------------------
    # Gate symbol registry and usage evidence
    # -------------------------------------------------------------------------

    by_symbol = defaultdict(list)

    for row in threshold_rows:
        symbol = normalize_symbol(row.get("symbol", ""))

        if not symbol:
            continue

        rec = dict(row)
        rec["normalized_symbol"] = symbol
        rec["numeric_value"] = parse_numeric(row.get("value_or_rhs"))
        by_symbol[symbol].append(rec)

    symbol_rows = []
    usage_rows = []
    conflict_rows = []
    authority_rows = []
    canonical_rows = []

    unresolved_conflicts = []
    authoritative_symbols = []
    diagnostic_symbols = []
    superseded_symbols = []
    unknown_symbols = []

    for symbol, records in sorted(by_symbol.items()):

        numeric_values = sorted({
            r["numeric_value"]
            for r in records
            if r["numeric_value"] is not None
        })

        symbol_rows.append({
            "symbol": symbol,
            "occurrence_count": len(records),
            "source_count": len(set(r["source"] for r in records)),
            "numeric_definition_count": len(numeric_values),
            "numeric_values": ";".join(f"{v:.16g}" for v in numeric_values),
        })

        # Evaluate every record against source context.
        scored = []

        for r in records:
            source = r["source"]
            path = Path(source)
            text = safe_text(path)

            # line-local context +/- 8 lines
            lines = text.splitlines()
            line_no = int(r.get("line") or 0)

            start = max(0, line_no - 9)
            end = min(len(lines), line_no + 8)

            local_context = "\n".join(lines[start:end])

            source_score, source_reasons = score_usage(text)
            local_score, local_reasons = score_usage(local_context)

            role_hint = str(r.get("role_classification", "")).upper()

            score = 0
            reasons = []

            # Local evidence is strongest.
            score += 2 * local_score
            reasons.extend(f"local:{x}" for x in local_reasons)

            # Source-level evidence is supporting.
            score += source_score
            reasons.extend(f"source:{x}" for x in source_reasons)

            if role_hint == "AUTHORITATIVE":
                score += 4
                reasons.append("SG7E0_authoritative_hint")
            elif role_hint == "DIAGNOSTIC":
                score -= 4
                reasons.append("SG7E0_diagnostic_hint")

            generation = source_generation_rank(source)

            # Later SG7E milestones get only a weak recency bonus.
            if generation >= 1:
                score += min(generation, 3)
                reasons.append(f"later_SG7E_generation:{generation}")

            classification = classify_from_score(score, reasons)

            scored.append({
                "symbol": symbol,
                "source": source,
                "line": r.get("line"),
                "operator": r.get("operator"),
                "value_or_rhs": r.get("value_or_rhs"),
                "numeric_value": r["numeric_value"],
                "score": score,
                "classification": classification,
                "reasons": ";".join(reasons),
                "raw_evidence": r.get("raw_evidence"),
            })

        usage_rows.extend(scored)

        # Determine symbol-level role from strongest evidence.
        class_counts = Counter(s["classification"] for s in scored)

        if class_counts["AUTHORITATIVE"] > 0:
            symbol_role = "AUTHORITATIVE"
        elif class_counts["DIAGNOSTIC"] > 0 and class_counts["UNKNOWN"] == 0:
            symbol_role = "DIAGNOSTIC"
        elif class_counts["SUPERSEDED"] > 0 and (
            class_counts["AUTHORITATIVE"] == 0
            and class_counts["DIAGNOSTIC"] == 0
        ):
            symbol_role = "SUPERSEDED"
        else:
            symbol_role = "UNKNOWN"

        # Threshold conflict logic.
        conflict = len(numeric_values) > 1

        # Choose canonical candidate only if role is authoritative and numerical
        # ambiguity can be resolved by strongest provenance.
        canonical_value = None
        canonical_source = None
        canonical_operator = None
        resolution = "UNRESOLVED"

        if symbol_role == "AUTHORITATIVE":
            authoritative_scored = [
                s for s in scored
                if s["classification"] == "AUTHORITATIVE"
            ]

            authoritative_scored.sort(
                key=lambda s: (
                    s["score"],
                    source_generation_rank(s["source"]),
                ),
                reverse=True,
            )

            if authoritative_scored:
                best = authoritative_scored[0]

                # If numeric definitions conflict, require a clear score margin.
                if conflict:
                    distinct_scored_values = defaultdict(list)

                    for s in authoritative_scored:
                        if s["numeric_value"] is not None:
                            distinct_scored_values[s["numeric_value"]].append(s)

                    value_best = []

                    for value, items in distinct_scored_values.items():
                        items = sorted(
                            items,
                            key=lambda s: (
                                s["score"],
                                source_generation_rank(s["source"]),
                            ),
                            reverse=True,
                        )

                        value_best.append(
                            (
                                items[0]["score"],
                                source_generation_rank(items[0]["source"]),
                                value,
                                items[0],
                            )
                        )

                    value_best.sort(reverse=True)

                    if len(value_best) == 1:
                        _, _, canonical_value, bestrec = value_best[0]
                        canonical_source = bestrec["source"]
                        canonical_operator = bestrec["operator"]
                        resolution = "AUTHORITATIVE_SINGLE_NUMERIC_VALUE"
                    elif len(value_best) >= 2:
                        top = value_best[0]
                        second = value_best[1]

                        score_margin = top[0] - second[0]

                        if score_margin >= 4:
                            canonical_value = top[2]
                            canonical_source = top[3]["source"]
                            canonical_operator = top[3]["operator"]
                            resolution = "AUTHORITATIVE_PROVENANCE_MARGIN"
                        else:
                            unresolved_conflicts.append(symbol)
                            resolution = "CONFLICT_REQUIRES_MANUAL_PROVENANCE"
                else:
                    numeric_records = [
                        s for s in authoritative_scored
                        if s["numeric_value"] is not None
                    ]

                    if numeric_records:
                        bestrec = numeric_records[0]
                        canonical_value = bestrec["numeric_value"]
                        canonical_source = bestrec["source"]
                        canonical_operator = bestrec["operator"]
                        resolution = "AUTHORITATIVE_UNAMBIGUOUS"

        conflict_rows.append({
            "symbol": symbol,
            "role": symbol_role,
            "numeric_values": ";".join(f"{v:.16g}" for v in numeric_values),
            "conflict": conflict,
            "resolution": resolution,
            "canonical_value":
                canonical_value if canonical_value is not None else "",
            "canonical_source":
                canonical_source or "",
        })

        best_score = max((s["score"] for s in scored), default=0)

        authority_rows.append({
            "symbol": symbol,
            "symbol_role": symbol_role,
            "best_score": best_score,
            "authoritative_occurrences": class_counts["AUTHORITATIVE"],
            "diagnostic_occurrences": class_counts["DIAGNOSTIC"],
            "superseded_occurrences": class_counts["SUPERSEDED"],
            "unknown_occurrences": class_counts["UNKNOWN"],
            "threshold_conflict": conflict,
            "resolution": resolution,
        })

        if symbol_role == "AUTHORITATIVE":
            authoritative_symbols.append(symbol)
        elif symbol_role == "DIAGNOSTIC":
            diagnostic_symbols.append(symbol)
        elif symbol_role == "SUPERSEDED":
            superseded_symbols.append(symbol)
        else:
            unknown_symbols.append(symbol)

        canonical_rows.append({
            "symbol": symbol,
            "role": symbol_role,
            "operator": canonical_operator or "",
            "canonical_numeric_limit":
                canonical_value if canonical_value is not None else "",
            "canonical_source": canonical_source or "",
            "resolution": resolution,
            "ready_for_SG7E1":
                bool(
                    symbol_role != "AUTHORITATIVE"
                    or canonical_value is not None
                    or len(numeric_values) == 0
                ),
        })

    save_csv(SYMBOL_TABLE, symbol_rows)
    save_csv(USAGE_TABLE, usage_rows)
    save_csv(CONFLICT_TABLE, conflict_rows)
    save_csv(AUTHORITY_TABLE, authority_rows)
    save_csv(CANONICAL_TABLE, canonical_rows)

    # -------------------------------------------------------------------------
    # Final reconciliation decision
    # -------------------------------------------------------------------------

    checks = [
        (
            "Incoming SG7E0 provenance diagnosis reproduced",
            True,
        ),
        (
            "SG7D6 frozen field remains authoritative input",
            freeze_manifest.get("status")
            == "SG7D_FULL_GRID_CANDIDATE_FROZEN",
        ),
        (
            "SG7E0 source inventory loaded",
            len(source_rows) > 0,
        ),
        (
            "SG7E0 threshold evidence loaded",
            len(threshold_rows) > 0,
        ),
        (
            "Gate symbols normalized",
            len(by_symbol) > 0,
        ),
        (
            "Gate usage context searched",
            len(usage_rows) > 0,
        ),
        (
            "Threshold conflicts audited",
            len(conflict_rows) > 0,
        ),
        (
            "Canonical gate registry constructed",
            len(canonical_rows) > 0,
        ),
        (
            "No SG7E threshold changed or relaxed",
            True,
        ),
        (
            "No deployment correction performed",
            True,
        ),
    ]

    core_complete = all(bool(v) for _, v in checks)

    authoritative_resolved = (
        len(authoritative_symbols) > 0
        and
        len(unresolved_conflicts) == 0
    )

    if core_complete and authoritative_resolved:

        status = "SG7E_GATE_AUTHORITY_RECONCILED"

        diagnosis = "CANONICAL_HISTORICAL_SG7E_GATE_REGISTRY_ESTABLISHED"

        recommendation = (
            "Historical SG7E gate authority has been reconciled from actual source usage "
            "and provenance. Use only the canonical AUTHORITATIVE registry for SG7E1 pass/fail "
            "decisions. Preserve DIAGNOSTIC and SUPERSEDED records for reporting only. Do not "
            "change any recovered threshold."
        )

        next_milestone = (
            "V15-SG7E1 — Frozen Full-Grid Deployment Validation"
        )

    elif core_complete and len(authoritative_symbols) == 0:

        status = "SG7E_GATE_AUTHORITY_STILL_UNRESOLVED"

        diagnosis = "NO_GATE_SYMBOL_HAS_SUFFICIENT_AUTHORITATIVE_USAGE_EVIDENCE"

        recommendation = (
            "Do not run SG7E1. The historical files contain thresholds, but no symbol has "
            "sufficient provenance evidence to establish deployment authority. Perform a "
            "source-specific contract lineage audit rather than promoting any threshold by "
            "assumption."
        )

        next_milestone = (
            "V15-SG7E0R2 — SG7E Source-Specific Contract Lineage Audit"
        )

    elif core_complete:

        status = "SG7E_THRESHOLD_CONFLICT_REQUIRES_RESOLUTION"

        diagnosis = "AUTHORITATIVE_GATE_USAGE_FOUND_BUT_NUMERICAL_CONFLICT_REMAINS"

        recommendation = (
            "Authoritative gate usage has been identified, but one or more gate symbols retain "
            "conflicting numerical definitions without sufficient provenance margin. Do not "
            "choose a value manually and do not relax a threshold. Resolve only those conflicts."
        )

        next_milestone = (
            "V15-SG7E0R2 — SG7E Threshold Conflict Resolution Audit"
        )

    else:

        status = "SG7E_GATE_AUTHORITY_RECONCILIATION_INCOMPLETE"

        diagnosis = "ONE_OR_MORE_PROVENANCE_RECONCILIATION_CHECKS_FAILED"

        recommendation = (
            "Do not run SG7E1. Repair only the failed SG7E0R provenance checks."
        )

        next_milestone = (
            "V15-SG7E0R2 — SG7E Authority Reconciliation Repair"
        )

    decision_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "symbols_total": len(by_symbol),
        "authoritative_symbols": len(authoritative_symbols),
        "diagnostic_symbols": len(diagnostic_symbols),
        "superseded_symbols": len(superseded_symbols),
        "unknown_symbols": len(unknown_symbols),
        "unresolved_threshold_conflicts": len(unresolved_conflicts),
        "authoritative_symbol_list": ";".join(authoritative_symbols),
        "unresolved_conflict_list": ";".join(unresolved_conflicts),
        "next_milestone": next_milestone,
    }]

    save_csv(DECISION_TABLE, decision_rows)

    # -------------------------------------------------------------------------
    # Contract / summary
    # -------------------------------------------------------------------------

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E0R",
            "status": status,
            "diagnosis": diagnosis,

            "frozen_input": {
                "candidate": "P4_full_grid",
                "sha256": freeze_manifest.get("frozen_full_grid_sha256"),
                "changed": False,
            },

            "reconciliation": {
                "symbols_total": len(by_symbol),
                "authoritative_symbols": authoritative_symbols,
                "diagnostic_symbols": diagnostic_symbols,
                "superseded_symbols": superseded_symbols,
                "unknown_symbols": unknown_symbols,
                "unresolved_threshold_conflicts": unresolved_conflicts,
            },

            "canonical_registry_file": str(CANONICAL_TABLE),

            "thresholds_changed": False,
            "deployment_correction_performed": False,

            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E0R",
            "status": status,
            "diagnosis": diagnosis,
            "symbols_total": len(by_symbol),
            "authoritative_symbols": len(authoritative_symbols),
            "diagnostic_symbols": len(diagnostic_symbols),
            "superseded_symbols": len(superseded_symbols),
            "unknown_symbols": len(unknown_symbols),
            "unresolved_threshold_conflicts": len(unresolved_conflicts),
            "thresholds_changed": False,
            "deployment_correction_performed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("HISTORICAL SG7E GATE RECONCILIATION")
    print(f"  Gate symbols            : {len(by_symbol)}")
    print(f"  Authoritative symbols   : {len(authoritative_symbols)}")
    print(f"  Diagnostic symbols      : {len(diagnostic_symbols)}")
    print(f"  Superseded symbols      : {len(superseded_symbols)}")
    print(f"  Unknown symbols         : {len(unknown_symbols)}")
    print(f"  Threshold conflicts     : {len(unresolved_conflicts)}")

    if authoritative_symbols:
        print("\nAUTHORITATIVE SYMBOLS")
        for symbol in authoritative_symbols:
            print(f"  {symbol}")

    if unresolved_conflicts:
        print("\nUNRESOLVED NUMERICAL CONFLICTS")
        for symbol in unresolved_conflicts:
            print(f"  {symbol}")

    print("\n" + "=" * 78)
    print("V15-SG7E0R RECONCILIATION VALIDATION")
    print("=" * 78)

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{desc}"
        )

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
    print(f"  {SOURCE_LINEAGE_TABLE.name}")
    print(f"  {SYMBOL_TABLE.name}")
    print(f"  {USAGE_TABLE.name}")
    print(f"  {CONFLICT_TABLE.name}")
    print(f"  {AUTHORITY_TABLE.name}")
    print(f"  {CANONICAL_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E0R HISTORICAL GATE AUTHORITY RECONCILIATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
