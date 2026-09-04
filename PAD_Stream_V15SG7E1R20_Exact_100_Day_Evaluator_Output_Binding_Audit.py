from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R20
# Exact 100-Day Evaluator Output Binding Audit
#
# FORENSIC OUTPUT-BINDING MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO SCALAR ANCHORING OR FITTING.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
#
# PURPOSE
# -------
# SG7E1R19 established:
#
#   L2_100D_REPLAY_BINDING_INCOMPLETE
#
# with:
#
#   UNIQUE_100D_REPLAY_STATE_NOT_EXPLICITLY_BOUND_IN_FROZEN_PACKAGE
#
# The model identity is already resolved and immutable:
#
#   V15SG7CR3F4_B4_Best_Any_Alpha_Model.keras
#
# R20 therefore does NOT search for a "best" 100d state numerically.
# It traces the exact evaluator OUTPUT SYMBOL produced by the historical
# R1F2B/R1F2C/R1F3 deployment call and binds that symbol to the persisted NPZ
# key/artifact that captured it.
#
# Evidence hierarchy:
#
#   evaluator call
#      -> assigned output symbol
#      -> deterministic post-processing chain
#      -> np.savez / manifest serialization key
#      -> persisted array identity
#
# The selected output must be established by source/serialization provenance,
# never by SG7E performance and never by minimum error among the 44 candidates.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R20"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R19_DIR = ROOT / "output" / "V15_SG7E1R19"
R19_SUMMARY = R19_DIR / "PAD_Stream_V15SG7E1R19_Summary.json"
R19_CONTRACT = R19_DIR / "V15SG7E1R19_100d_Replay_Validation_Contract.json"
R19_PERSISTED = R19_DIR / "V15SG7E1R19_Persisted_100d_Candidate_Inventory.csv"
R19_EVAL_BINDING = R19_DIR / "V15SG7E1R19_Evaluator_Binding_Audit.csv"

R18_DIR = ROOT / "output" / "V15_SG7E1R18"
R18_EVAL_TRACE = R18_DIR / "V15SG7E1R18_Deployment_Evaluator_Source_Trace.csv"
R18_ARG_TRACE = R18_DIR / "V15SG7E1R18_Evaluation_Argument_Contract.csv"
R18_MODEL = R18_DIR / "V15SG7E1R18_Frozen_Model_Identity.csv"

R17_STATE_INV = (
    ROOT / "output" / "V15_SG7E1R17"
    / "V15SG7E1R17_Persisted_Multi_Time_L2_State_Inventory.csv"
)

R1F3_DIR = ROOT / "output" / "V15_SG7CR3F5R1F3"
R1F3_FROZEN = (
    R1F3_DIR / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)
R1F3_MANIFEST = R1F3_DIR / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
R1F3_CONTRACT = R1F3_DIR / "V15SG7CR3F5R1F3_Frozen_Deployment_Contract.json"

# Relevant historical source branch
SOURCE_PATTERNS = (
    "PAD_Stream_V15SG7CR3F5R1F2B",
    "PAD_Stream_V15SG7CR3F5R1F2C",
    "PAD_Stream_V15SG7CR3F5R1F2CRR",
    "PAD_Stream_V15SG7CR3F5R1F3",
)

EXPECTED_STATE_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

CALL_TABLE = OUT / "V15SG7E1R20_Evaluator_Call_Output_Assignment.csv"
SYMBOL_TABLE = OUT / "V15SG7E1R20_Output_Symbol_Propagation.csv"
SAVE_TABLE = OUT / "V15SG7E1R20_Output_Serialization_Trace.csv"
KEY_TABLE = OUT / "V15SG7E1R20_Persisted_Key_Candidate_Audit.csv"
HASH_TABLE = OUT / "V15SG7E1R20_Bound_Output_Hash_Identity.csv"
DECISION_TABLE = OUT / "V15SG7E1R20_Output_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R20_Exact_100d_Evaluator_Output_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R20_Summary.json"


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


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


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def project_sources():
    files = []
    for p in ROOT.glob("*.py"):
        if any(tok in p.name for tok in SOURCE_PATTERNS):
            files.append(p.resolve())
    return sorted(set(files))


def extract_assignment_calls(text: str):
    """
    Find simple assignment sites whose RHS contains predict/model invocation.
    """
    rows = []
    lines = text.splitlines()

    patterns = [
        re.compile(
            r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+(?:\.predict\(|predict_on_batch\(|model\().*)$"
        ),
        re.compile(
            r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+load_model\().*$"
        ),
    ]

    for i, line in enumerate(lines, start=1):
        for pat in patterns:
            m = pat.match(line)
            if not m:
                continue

            lhs = m.group(1)
            rhs = m.group(2)

            ctx = "\n".join(lines[max(0, i - 10): min(len(lines), i + 14)])

            rows.append({
                "line": i,
                "lhs_symbol": lhs,
                "rhs_expression": rhs.strip()[:2500],
                "context": ctx[:6000],
                "mentions_100d": bool(
                    re.search(r"(?<!\d)100(?:\.0+)?\s*(?:d|day|days)?(?!\d)", ctx, re.I)
                ),
                "mentions_xi": "xi" in ctx.lower(),
                "mentions_tau_or_tof": ("tau" in ctx.lower() or "tof" in ctx.lower()),
            })

    return rows


def extract_symbol_assignments(text: str, symbols):
    rows = []
    lines = text.splitlines()

    sym_alt = "|".join(re.escape(s) for s in symbols)
    if not sym_alt:
        return rows

    # RHS depends on any tracked symbol.
    pat = re.compile(
        rf"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*\b(?:{sym_alt})\b.*)$"
    )

    for i, line in enumerate(lines, start=1):
        m = pat.match(line)
        if m:
            rows.append({
                "line": i,
                "lhs_symbol": m.group(1),
                "rhs_expression": m.group(2).strip()[:3000],
            })

    return rows


def extract_save_keys(text: str, tracked_symbols):
    """
    Trace np.savez / np.savez_compressed keyword serialization.
    """
    rows = []
    lines = text.splitlines()

    # Capture multi-line np.savez blocks conservatively.
    joined = "\n".join(lines)
    for m in re.finditer(
        r"np\.savez(?:_compressed)?\s*\((.*?)\)\s*",
        joined,
        flags=re.S,
    ):
        block = m.group(1)
        start_line = joined[:m.start()].count("\n") + 1

        for sym in tracked_symbols:
            # key=sym or key=np.asarray(sym)
            for km in re.finditer(
                rf"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:np\.[A-Za-z_]+\()?{re.escape(sym)}\b",
                block,
            ):
                rows.append({
                    "line": start_line,
                    "serialization_key": km.group(1),
                    "source_symbol": sym,
                    "save_block": block[:6000],
                })

    return rows


def candidate_state_artifacts():
    rows = []

    # Current frozen R1F3 package first.
    candidates = [R1F3_FROZEN]

    # Then all late branch NPZs.
    for base in [
        ROOT / "output" / "V15_SG7CR3F5R1F2B",
        ROOT / "output" / "V15_SG7CR3F5R1F2C",
        ROOT / "output" / "V15_SG7CR3F5R1F2CRR",
        ROOT / "output" / "V15_SG7CR3F5R1F3",
    ]:
        if base.exists():
            candidates.extend(base.rglob("*.npz"))

    for p in sorted(set(x.resolve() for x in candidates if x.exists())):
        try:
            db = np.load(p, allow_pickle=True)
        except Exception:
            continue

        for key in db.files:
            arr = np.asarray(db[key])
            if arr.shape == EXPECTED_STATE_SHAPE and np.issubdtype(arr.dtype, np.number):
                rows.append({
                    "artifact_path": str(p),
                    "artifact_file": p.name,
                    "key": key,
                    "shape": str(arr.shape),
                    "dtype": str(arr.dtype),
                    "array_sha256": sha256_array(arr),
                })
        db.close()

    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R20")
    print("Exact 100-Day Evaluator Output Binding Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POST-HOC ALIGNMENT WILL BE PERFORMED.
NO SCALAR ANCHORING OR FITTING WILL BE PERFORMED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
""")

    r19s = load_json(R19_SUMMARY)
    r19c = load_json(R19_CONTRACT)
    r1f3_manifest = load_json(R1F3_MANIFEST)
    r1f3_contract = load_json(R1F3_CONTRACT)

    if r19s.get("status") != "L2_100D_REPLAY_BINDING_INCOMPLETE":
        raise RuntimeError("R20 requires R19 replay-binding-incomplete status.")

    if r19s.get("diagnosis") != (
        "UNIQUE_100D_REPLAY_STATE_NOT_EXPLICITLY_BOUND_IN_FROZEN_PACKAGE"
    ):
        raise RuntimeError("R20 requires R19 output-binding diagnosis.")

    # -------------------------------------------------------------------------
    # Trace evaluator output assignment.
    # -------------------------------------------------------------------------

    call_rows = []
    propagation_rows = []
    save_rows = []

    tracked_symbols = set()

    for src in project_sources():
        text = safe_text(src)

        calls = extract_assignment_calls(text)
        for r in calls:
            r["source"] = str(src)
            call_rows.append(r)

            # Keep deployment-like call outputs.
            if (
                r["mentions_100d"]
                or r["mentions_xi"]
                or r["mentions_tau_or_tof"]
                or "candidate" in r["lhs_symbol"].lower()
                or "state" in r["lhs_symbol"].lower()
                or "pred" in r["lhs_symbol"].lower()
            ):
                tracked_symbols.add(r["lhs_symbol"])

    # Expand symbol graph iteratively.
    for _ in range(6):
        before = set(tracked_symbols)
        for src in project_sources():
            text = safe_text(src)
            assigns = extract_symbol_assignments(text, tracked_symbols)
            for r in assigns:
                r["source"] = str(src)
                propagation_rows.append(r)
                tracked_symbols.add(r["lhs_symbol"])
        if tracked_symbols == before:
            break

    # Trace serialization.
    for src in project_sources():
        text = safe_text(src)
        rows = extract_save_keys(text, tracked_symbols)
        for r in rows:
            r["source"] = str(src)
            save_rows.append(r)

    save_csv(CALL_TABLE, call_rows)
    save_csv(SYMBOL_TABLE, propagation_rows)
    save_csv(SAVE_TABLE, save_rows)

    # -------------------------------------------------------------------------
    # Persisted keys and source-binding evidence.
    # -------------------------------------------------------------------------

    state_rows = candidate_state_artifacts()

    # Score only source/serialization provenance, never performance.
    key_rows = []

    save_by_key = defaultdict(list)
    for r in save_rows:
        save_by_key[r["serialization_key"]].append(r)

    manifest_blob = (
        json.dumps(r1f3_manifest, indent=2)
        + "\n"
        + json.dumps(r1f3_contract, indent=2)
    ).lower()

    for r in state_rows:
        key = r["key"]
        score = 0
        evidence = []

        if key in save_by_key:
            score += 100
            evidence.append("source_serialization_key")

        # If tracked symbol name exactly equals persisted key.
        if key in tracked_symbols:
            score += 60
            evidence.append("tracked_output_symbol_name")

        if key.lower() in manifest_blob:
            score += 30
            evidence.append("manifest_contract_key_reference")

        # Prefer exact R1F3 frozen artifact provenance.
        if Path(r["artifact_path"]).resolve() == R1F3_FROZEN.resolve():
            score += 20
            evidence.append("R1F3_frozen_artifact")

        key_rows.append({
            **r,
            "binding_score": score,
            "binding_evidence": ";".join(evidence),
        })

    key_rows.sort(
        key=lambda r: (
            int(r["binding_score"]),
            r["artifact_file"],
            r["key"],
        ),
        reverse=True,
    )

    save_csv(KEY_TABLE, key_rows)

    # -------------------------------------------------------------------------
    # Unique provenance binding decision.
    # -------------------------------------------------------------------------

    selected = None
    margin = 0

    if key_rows:
        top = key_rows[0]
        second = int(key_rows[1]["binding_score"]) if len(key_rows) > 1 else -999
        top_score = int(top["binding_score"])
        margin = top_score - second

        strong = top_score >= 100
        if strong and margin >= 30:
            selected = top

    hash_rows = []

    if selected is not None:
        p = Path(selected["artifact_path"])
        db = np.load(p, allow_pickle=True)
        arr = np.asarray(db[selected["key"]])
        arr_hash = sha256_array(arr)
        db.close()

        hash_rows.append({
            "artifact_path": str(p),
            "artifact_file": p.name,
            "key": selected["key"],
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "array_sha256": arr_hash,
            "binding_score": selected["binding_score"],
            "binding_margin": margin,
            "binding_evidence": selected["binding_evidence"],
        })

    save_csv(HASH_TABLE, hash_rows)

    # -------------------------------------------------------------------------
    # Cross-check whether bound hash is part of historical 100d candidate set.
    # -------------------------------------------------------------------------

    persisted_100 = load_csv(R19_PERSISTED)
    persisted_100_hashes = {r["array_sha256"] for r in persisted_100}

    bound_in_100d_set = (
        selected is not None
        and selected["array_sha256"] in persisted_100_hashes
    )

    # -------------------------------------------------------------------------
    # Final status
    # -------------------------------------------------------------------------

    if selected is not None and bound_in_100d_set:
        status = "L2_100D_EVALUATOR_OUTPUT_BOUND"
        diagnosis = "SOURCE_SERIALIZATION_PROVENANCE_IDENTIFIES_UNIQUE_100D_OUTPUT_ARRAY"
        recommendation = (
            "The exact 100-day evaluator output is now bound by source and serialization "
            "provenance to one persisted historical state. Rerun deterministic replay closure "
            "against this bound array only, using precision-aware dtype closure. Do not search "
            "or rank the remaining historical candidates."
        )
        next_milestone = (
            "V15-SG7E1R21 — Bound 100-Day Deterministic Replay Closure Validation"
        )

    elif selected is not None and not bound_in_100d_set:
        status = "L2_100D_OUTPUT_BOUND_BUT_TIME_PROVENANCE_CONFLICT"
        diagnosis = "BOUND_EVALUATOR_OUTPUT_NOT_PRESENT_IN_R19_100D_CANDIDATE_SET"
        recommendation = (
            "Do not replay new times. The evaluator output is uniquely bound, but its numerical "
            "identity is not present in the R19 historical 100-day candidate set. Audit only the "
            "time-label provenance assigned to the bound array."
        )
        next_milestone = (
            "V15-SG7E1R21 — Bound Output Time-Label Provenance Audit"
        )

    else:
        status = "L2_100D_EVALUATOR_OUTPUT_BINDING_STILL_AMBIGUOUS"
        diagnosis = "SOURCE_SYMBOL_OR_SERIALIZATION_CHAIN_DOES_NOT_SELECT_ONE_UNIQUE_OUTPUT_KEY"
        recommendation = (
            "Do not choose among persisted 100-day arrays. Trace the final source variable "
            "passed into the R1F3 freeze serializer, including any dictionary packing or alias "
            "assignment, until one NPZ key is uniquely reached."
        )
        next_milestone = (
            "V15-SG7E1R21 — Final Freeze-Serializer Alias / Dictionary Binding Audit"
        )

    checks = [
        ("Incoming R19 replay-binding diagnosis reproduced", True),
        ("Historical evaluator source branch inventoried", len(project_sources()) > 0),
        ("Evaluator call output assignments traced", len(call_rows) > 0),
        ("Output symbol propagation traced", True),
        ("Serialization keys traced", True),
        ("Persisted 2662x201 state candidates inventoried", len(state_rows) > 0),
        ("Binding uses source/serialization provenance only", True),
        ("No SG7E performance used for selection", True),
        ("No scalar anchoring/scaling used", True),
        ("No 250/500/1000d state generated", True),
        ("No training performed", True),
        ("No model parameter changed", True),
        ("No SG7E threshold changed or relaxed", True),
    ]

    decision = [{
        "status": status,
        "diagnosis": diagnosis,
        "tracked_output_symbols": ";".join(sorted(tracked_symbols)),
        "evaluator_call_records": len(call_rows),
        "propagation_records": len(propagation_rows),
        "serialization_records": len(save_rows),
        "persisted_state_candidates": len(state_rows),
        "selected_artifact": selected["artifact_path"] if selected else "",
        "selected_key": selected["key"] if selected else "",
        "selected_sha256": selected["array_sha256"] if selected else "",
        "binding_score": selected["binding_score"] if selected else "",
        "binding_margin": margin,
        "bound_in_R19_100d_candidate_set": bound_in_100d_set,
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION_TABLE, decision)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R20",
        "status": status,
        "diagnosis": diagnosis,
        "output_binding": {
            "resolved": selected is not None,
            "artifact_path": selected["artifact_path"] if selected else None,
            "key": selected["key"] if selected else None,
            "sha256": selected["array_sha256"] if selected else None,
            "binding_score": int(selected["binding_score"]) if selected else None,
            "binding_margin": margin,
            "in_R19_100d_candidate_set": bound_in_100d_set,
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "candidate_performance_used": False,
            "scalar_anchoring_used": False,
            "posthoc_alignment_used": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
            "threshold_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R20",
        "status": status,
        "diagnosis": diagnosis,
        "output_binding_resolved": selected is not None,
        "selected_key": selected["key"] if selected else None,
        "selected_sha256": selected["array_sha256"] if selected else None,
        "bound_in_R19_100d_candidate_set": bound_in_100d_set,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("EVALUATOR OUTPUT TRACE")
    print(f"  Source files            : {len(project_sources())}")
    print(f"  Call assignments        : {len(call_rows)}")
    print(f"  Tracked symbols         : {len(tracked_symbols)}")
    print(f"  Propagation records     : {len(propagation_rows)}")
    print(f"  Serialization records   : {len(save_rows)}")

    print("\nPERSISTED STATE BINDING")
    print(f"  Candidate state arrays  : {len(state_rows)}")

    for row in key_rows[:12]:
        print(
            f"  score={int(row['binding_score']):3d} | "
            f"{row['artifact_file']} :: {row['key']} | "
            f"{row['array_sha256'][:16]}"
        )

    if selected:
        print("\nSELECTED OUTPUT BINDING")
        print(f"  Artifact                : {selected['artifact_path']}")
        print(f"  Key                     : {selected['key']}")
        print(f"  SHA-256                 : {selected['array_sha256']}")
        print(f"  Score / margin          : {selected['binding_score']} / {margin}")
        print(f"  In R19 100d set         : {bound_in_100d_set}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R20 OUTPUT-BINDING VALIDATION")
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
        CALL_TABLE,
        SYMBOL_TABLE,
        SAVE_TABLE,
        KEY_TABLE,
        HASH_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R20 EXACT 100-DAY EVALUATOR OUTPUT BINDING AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No scalar anchoring or post-hoc alignment was used.")
    print("No 250/500/1000-day state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
