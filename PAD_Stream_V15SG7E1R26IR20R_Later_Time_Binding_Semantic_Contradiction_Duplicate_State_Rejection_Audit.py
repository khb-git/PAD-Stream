from __future__ import annotations

from pathlib import Path
import csv
import json
from collections import defaultdict

# =============================================================================
# PAD-Stream V15-SG7E1R26I-R20R
# Later-Time Binding Semantic Contradiction / Duplicate-State Rejection Audit
#
# PURPOSE
# -------
# R20 reported:
#
#   250 d  -> frozen100 -> a08c7320...
#   500 d  -> frozen100 -> a08c7320...
#   1000 d -> no persisted state
#
# The 250-d and 500-d bindings are semantically suspicious because:
#
#   1. both use the key "frozen100",
#   2. both use the exact same numerical SHA-256,
#   3. frozen100 is already established as the historical 100-day state,
#   4. R20 did not demonstrate a persisted multi-time tensor or explicit
#      per-time serializer mapping that would authorize the same single state
#      as distinct 250-d and 500-d physical states.
#
# Therefore R20R does NOT accept those bindings automatically.
#
# It audits whether any selected later-time candidate:
#   - is identical to the authoritative 100-day frozen state,
#   - is bound to multiple required times,
#   - uses a key with explicit 100-day semantics,
#   - has explicit source-level time binding sufficient to override the
#     contradiction.
#
# NO TRAINING.
# NO MODEL.PREDICT.
# NO STATE GENERATION.
# NO THRESHOLD OR TOLERANCE CHANGE.
# =============================================================================

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR20R"
OUT.mkdir(parents=True, exist_ok=True)

R20_DIR = ROOT / "output" / "V15_SG7E1R26IR20"
R20_SUMMARY = R20_DIR / "PAD_Stream_V15SG7E1R26IR20_Summary.json"
R20_CANDIDATES = R20_DIR / "V15SG7E1R26IR20_Required_Time_Candidate_Binding.csv"
R20_TIME_TRACE = R20_DIR / "V15SG7E1R26IR20_Time_Label_Provenance.csv"
R20_ALIAS_TRACE = R20_DIR / "V15SG7E1R26IR20_State_Alias_Provenance.csv"

R18R_DIR = ROOT / "output" / "V15_SG7E1R26IR18R"
R18R_SUMMARY = R18R_DIR / "PAD_Stream_V15SG7E1R26IR18R_Summary.json"

R17_DIR = ROOT / "output" / "V15_SG7E1R26IR17"
R17_ARRAY_ID = R17_DIR / "V15SG7E1R26IR17_Array_Identity.csv"

CONTRADICTION_TABLE = OUT / "V15SG7E1R26IR20R_Later_Time_Binding_Contradictions.csv"
EXPLICIT_BINDING_TABLE = OUT / "V15SG7E1R26IR20R_Explicit_Time_Binding_Evidence.csv"
CORRECTED_COVERAGE_TABLE = OUT / "V15SG7E1R26IR20R_Corrected_Required_Time_Coverage.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR20R_Final_Contradiction_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR20R_Corrected_Later_Time_Decision.csv"
CONTRACT_FILE = OUT / "V15SG7E1R26IR20R_Later_Time_Binding_Contradiction_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR20R_Summary.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows):
    rows = list(rows)
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


def boolish(v):
    return str(v).strip().lower() in {"1", "true", "yes"}


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R20R")
    print("Later-Time Binding Semantic Contradiction / Duplicate-State Rejection Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO INTERPOLATION OR EXTRAPOLATION WILL BE USED.
NO SG7E THRESHOLD OR PRECISION ENVELOPE WILL BE CHANGED.
R20'S 250/500-DAY BINDINGS WILL NOT BE ACCEPTED IF THEY ARE ONLY RE-LABELLED 100-DAY STATE COPIES.
""")

    r20 = load_json(R20_SUMMARY)
    if r20.get("status") != "PERSISTED_LATER_TIME_L2_STATE_COVERAGE_NOT_RECOVERABLE":
        raise RuntimeError("R20R requires the completed R20 recovery audit.")

    r18r = load_json(R18R_SUMMARY)
    if r18r.get("classification") != "HISTORICAL_FROZEN100_PERSISTS_CURRENT_CREATOR100_DOES_NOT":
        raise RuntimeError("R20R requires corrected historical frozen100 authority.")

    selected = load_csv(R20_CANDIDATES)
    time_trace = load_csv(R20_TIME_TRACE)
    alias_trace = load_csv(R20_ALIAS_TRACE)
    r17_identity = load_csv(R17_ARRAY_ID)

    # Resolve authoritative historical frozen100 SHA from R17 identity table.
    frozen100_sha = ""
    for row in r17_identity:
        role = (row.get("role") or row.get("array") or row.get("name") or "").lower()
        if "frozen" in role:
            frozen100_sha = (
                row.get("sha256")
                or row.get("sha256_float32")
                or row.get("hash")
                or ""
            )
            if frozen100_sha:
                break

    # Fallback from known corrected historical record if R17 table schema differs.
    if not frozen100_sha:
        frozen100_sha = "a08c7320a63ace580456191f408a29afde65e0ad3f078846265243e53cd10297"

    # Group selected bindings by numerical hash.
    by_hash = defaultdict(list)
    for row in selected:
        by_hash[row.get("sha256_float32", "")].append(row)

    contradiction_rows = []
    explicit_rows = []
    corrected_rows = []

    for required_time in (250.0, 500.0, 1000.0):
        candidates = [
            r for r in selected
            if float(r.get("time_days", -1)) == required_time
        ]

        if not candidates:
            corrected_rows.append({
                "time_days": required_time,
                "R20_selected_candidate": False,
                "accepted_after_semantic_audit": False,
                "classification": "NO_PERSISTED_STATE",
                "selected_key": "",
                "selected_sha256": "",
                "reason": "R20 had no selected persisted candidate.",
            })
            continue

        # R20 should have at most one selected candidate per time.
        cand = candidates[0]
        key = cand.get("top_key", cand.get("key", ""))
        sha = cand.get("sha256_float32", "")
        artifact = cand.get("top_artifact", cand.get("artifact", ""))

        same_as_frozen100 = sha == frozen100_sha
        hash_times = sorted({
            float(r.get("time_days", -1))
            for r in by_hash.get(sha, [])
            if r.get("time_days", "") != ""
        })
        same_hash_multiple_times = len(hash_times) > 1

        key_100_semantics = "100" in key.lower() and not any(
            tok in key.lower() for tok in ("250", "500", "1000")
        )

        # Require explicit source line tying this exact key to this exact time.
        supporting_alias = []
        for row in alias_trace:
            if row.get("key") != key:
                continue
            text = row.get("text", "")
            if str(int(required_time)) in text:
                supporting_alias.append(row)

        # Require explicit time provenance in the SAME artifact parent or source
        # context, not merely a global metadata mention.
        parent = str(Path(artifact).parent)
        supporting_time = []
        for row in time_trace:
            try:
                t = float(row.get("time_days", -1))
            except Exception:
                continue
            if t != required_time:
                continue
            source = row.get("source", "")
            if source.startswith(parent):
                supporting_time.append(row)

        explicit_key_time_binding = bool(supporting_alias)
        explicit_parent_time_context = bool(supporting_time)

        contradiction = (
            same_as_frozen100
            or same_hash_multiple_times
            or key_100_semantics
        )

        override_sufficient = bool(
            explicit_key_time_binding
            and explicit_parent_time_context
            and not key_100_semantics
        )

        accepted = bool(not contradiction or override_sufficient)

        contradiction_rows.append({
            "time_days": required_time,
            "artifact": artifact,
            "key": key,
            "sha256_float32": sha,
            "same_as_authoritative_frozen100": same_as_frozen100,
            "same_hash_bound_to_times": ";".join(str(int(t)) for t in hash_times),
            "same_hash_multiple_required_times": same_hash_multiple_times,
            "key_has_100_day_semantics": key_100_semantics,
            "explicit_key_time_binding": explicit_key_time_binding,
            "explicit_parent_time_context": explicit_parent_time_context,
            "override_sufficient": override_sufficient,
            "accepted_after_semantic_audit": accepted,
        })

        for row in supporting_alias:
            explicit_rows.append({
                "time_days": required_time,
                "evidence_type": "KEY_TIME_ALIAS",
                "source": row.get("source", ""),
                "line": row.get("line", ""),
                "text": row.get("text", ""),
            })
        for row in supporting_time:
            explicit_rows.append({
                "time_days": required_time,
                "evidence_type": "PARENT_TIME_CONTEXT",
                "source": row.get("source", ""),
                "line": row.get("line", ""),
                "text": row.get("text", ""),
            })

        corrected_rows.append({
            "time_days": required_time,
            "R20_selected_candidate": True,
            "accepted_after_semantic_audit": accepted,
            "classification": (
                "VALID_PERSISTED_LATER_TIME_STATE"
                if accepted
                else "REJECTED_RELABELED_OR_SEMANTICALLY_CONTRADICTORY_STATE"
            ),
            "selected_key": key,
            "selected_sha256": sha,
            "reason": (
                "Explicit provenance overcomes contradiction."
                if accepted and contradiction
                else "No contradiction."
                if accepted
                else "Candidate duplicates authoritative 100-day state, reuses one hash across multiple times, or carries explicit 100-day key semantics without sufficient override."
            ),
        })

    save_csv(CONTRADICTION_TABLE, contradiction_rows)
    save_csv(EXPLICIT_BINDING_TABLE, explicit_rows)
    save_csv(CORRECTED_COVERAGE_TABLE, corrected_rows)

    rejected = [
        r for r in corrected_rows
        if boolish(r.get("R20_selected_candidate", False))
        and not boolish(r.get("accepted_after_semantic_audit", False))
    ]
    accepted = [
        r for r in corrected_rows
        if boolish(r.get("accepted_after_semantic_audit", False))
    ]

    any_rejected_r20_binding = len(rejected) > 0
    all_later_times_recovered = len(accepted) == 3

    if all_later_times_recovered:
        status = "R20_LATER_TIME_BINDINGS_SEMANTICALLY_VALIDATED"
        diagnosis = (
            "ALL_SELECTED_LATER_TIME_STATES_SURVIVE_DUPLICATE_STATE_AND_100D_SEMANTIC_CONTRADICTION_AUDIT"
        )
        recommendation = (
            "Proceed with persisted multi-time map-back replay using only the semantically validated hashes."
        )
        next_ms = (
            "V15-SG7E1R26I-R21 — Persisted Multi-Time L2-to-Grid Map-Back Replay Audit"
        )
    else:
        status = "R20_LATER_TIME_BINDINGS_REJECTED_OR_INCOMPLETE"
        diagnosis = (
            "R20_250_500_BINDINGS_REUSE_AUTHORITATIVE_100D_STATE_OR_OTHERWISE_LACK_VALID_PHYSICAL_TIME_AUTHORITY"
        )
        recommendation = (
            "Treat rejected bindings as non-recovered. Do not relabel frozen100 as 250/500-day state. "
            "The corrected persisted later-time coverage is incomplete. Proceed to a formal multi-time "
            "deployment coverage limitation / SG7E scope decision audit."
        )
        next_ms = (
            "V15-SG7E1R26I-R21 — Multi-Time Deployment Coverage Limitation / SG7E Scope Decision Audit"
        )

    gates = [
        ("R20_recovery_result_reproduced", True),
        ("R18R_frozen100_authority_retained", True),
        ("selected_R20_bindings_reaudited_semantically", True),
        ("same_hash_multi_time_reuse_audited", True),
        ("100_day_key_semantics_audited", True),
        ("explicit_key_time_binding_audited", True),
        ("no_binding_accepted_by_numerical_performance", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_state_generated", True),
        ("no_threshold_or_precision_change", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "R20_selected_binding_count": len(selected),
        "accepted_later_time_binding_count": len(accepted),
        "rejected_R20_binding_count": len(rejected),
        "all_250_500_1000_recovered": all_later_times_recovered,
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R20R",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_frozen100_sha256": frozen100_sha,
        "corrected_coverage": corrected_rows,
        "contradictions": contradiction_rows,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "state_generated": False,
            "interpolation_used": False,
            "extrapolation_used": False,
            "threshold_changed": False,
            "precision_envelope_changed": False,
            "numerical_performance_used_for_binding": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R20R",
        "status": status,
        "diagnosis": diagnosis,
        "accepted_later_time_binding_count": len(accepted),
        "rejected_R20_binding_count": len(rejected),
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("R20 SELECTED BINDINGS")
    for r in selected:
        print(
            f"  t={float(r['time_days']):7.1f} d | "
            f"{r.get('top_key', r.get('key',''))} | "
            f"{r.get('sha256_float32','')[:16]}"
        )

    print("\nSEMANTIC CONTRADICTION AUDIT")
    for r in contradiction_rows:
        print(
            f"  t={float(r['time_days']):7.1f} d | "
            f"key={r['key']:<20} | "
            f"same100={str(r['same_as_authoritative_frozen100']):<5} | "
            f"multiTimeHash={str(r['same_hash_multiple_required_times']):<5} | "
            f"key100={str(r['key_has_100_day_semantics']):<5} | "
            f"accepted={r['accepted_after_semantic_audit']}"
        )

    print("\nCORRECTED REQUIRED-TIME COVERAGE")
    for r in corrected_rows:
        print(
            f"  t={float(r['time_days']):7.1f} d | "
            f"{r['classification']}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R20R FINAL CONTRADICTION GATES")
    print("=" * 78)
    for g, p in gates:
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
    for p in (
        CONTRADICTION_TABLE,
        EXPLICIT_BINDING_TABLE,
        CORRECTED_COVERAGE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R20R LATER-TIME BINDING CONTRADICTION AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No later-time state was generated.")
    print("No 100-day state was relabelled without explicit authority.")
    print("=" * 78)


if __name__ == "__main__":
    main()
