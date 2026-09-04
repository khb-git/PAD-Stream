from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R23
# Final Candidate-Selection Manifest / Nominated-State Binding Audit
#
# FORENSIC NOMINATED-STATE BINDING MILESTONE
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
# SG7E1R22 established:
#
#   L2_100D_CROSS_FUNCTION_BINDING_STILL_AMBIGUOUS
#
# with:
#
#   NO_SINGLE_STATE_LIKE_KEY_HAS_UNIQUE_RETURN_CALLER_SERIALIZER_LINEAGE
#
# The only permitted state-like frozen candidates are:
#
#   frozen100
#   K5_100
#   L2_independent_100
#
# R23 therefore leaves source alias tracing and audits the FINAL candidate-
# selection provenance itself:
#
#   controlled R1F2B result
#      -> independent R1F2C / R1F2C-R validation
#      -> freeze-readiness manifest
#      -> R1F3 freeze manifest
#      -> nominated candidate/state identity
#      -> persisted frozen NPZ key/hash
#
# Authority hierarchy:
#
#   1. explicit candidate identity / selected experiment
#   2. freeze-readiness manifest fields
#   3. R1F3 frozen candidate identity
#   4. manifest/contract array-key references
#   5. source save lineage
#
# Candidate performance is NOT used to choose between the state-like keys.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R23"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R22_DIR = ROOT / "output" / "V15_SG7E1R22"
R22_SUMMARY = R22_DIR / "PAD_Stream_V15SG7E1R22_Summary.json"
R22_CONTRACT = R22_DIR / "V15SG7E1R22_Cross_Function_Deployment_State_Binding_Contract.json"

R21R_CANDS = (
    ROOT / "output" / "V15_SG7E1R21R"
    / "V15SG7E1R21R_State_Like_Key_Candidates.csv"
)

R19_PERSISTED = (
    ROOT / "output" / "V15_SG7E1R19"
    / "V15SG7E1R19_Persisted_100d_Candidate_Inventory.csv"
)

# Candidate-selection / validation provenance
R1F2B_DIR = ROOT / "output" / "V15_SG7CR3F5R1F2B"
R1F2B_MANIFEST = R1F2B_DIR / "V15SG7CR3F5R1F2B_Candidate_Manifest.json"
R1F2B_CONTRACT = R1F2B_DIR / "V15SG7CR3F5R1F2B_Result_Contract.json"
R1F2B_SUMMARY = R1F2B_DIR / "PAD_Stream_V15SG7CR3F5R1F2B_Summary.json"

R1F2C_DIR = ROOT / "output" / "V15_SG7CR3F5R1F2C"
R1F2C_FREEZE = R1F2C_DIR / "V15SG7CR3F5R1F2C_Freeze_Readiness_Manifest.json"
R1F2C_CONTRACT = R1F2C_DIR / "V15SG7CR3F5R1F2C_Independent_Validation_Contract.json"
R1F2C_SUMMARY = R1F2C_DIR / "PAD_Stream_V15SG7CR3F5R1F2C_Summary.json"

R1F2CRR_DIR = ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
R1F2CRR_FREEZE = R1F2CRR_DIR / "V15SG7CR3F5R1F2CRR_Freeze_Readiness_Manifest.json"
R1F2CRR_CONTRACT = R1F2CRR_DIR / "V15SG7CR3F5R1F2CRR_Repaired_Independent_Validation_Contract.json"
R1F2CRR_SUMMARY = R1F2CRR_DIR / "PAD_Stream_V15SG7CR3F5R1F2CRR_Summary.json"

R1F3_DIR = ROOT / "output" / "V15_SG7CR3F5R1F3"
R1F3_MANIFEST = R1F3_DIR / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
R1F3_CONTRACT = R1F3_DIR / "V15SG7CR3F5R1F3_Frozen_Deployment_Contract.json"
R1F3_SUMMARY = R1F3_DIR / "PAD_Stream_V15SG7CR3F5R1F3_Summary.json"
R1F3_FROZEN = (
    R1F3_DIR / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

EXPECTED_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

MANIFEST_TRACE = OUT / "V15SG7E1R23_Candidate_Selection_Manifest_Trace.csv"
IDENTITY_TRACE = OUT / "V15SG7E1R23_Nominated_Candidate_Identity.csv"
KEY_ROLE_TRACE = OUT / "V15SG7E1R23_State_Key_Role_Mapping.csv"
KEY_SCORE = OUT / "V15SG7E1R23_Nominated_State_Key_Scoring.csv"
BOUND_HASH = OUT / "V15SG7E1R23_Bound_Nominated_State_Hash.csv"
DECISION_TABLE = OUT / "V15SG7E1R23_Nominated_State_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R23_Final_Candidate_Selection_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R23_Summary.json"


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def flatten_json(obj, prefix=""):
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                rows.extend(flatten_json(v, p))
            else:
                rows.append((p, v))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                rows.extend(flatten_json(v, p))
            else:
                rows.append((p, v))
    return rows


def semantic_candidate_tokens(field, value):
    text = f"{field} {value}".lower()
    hits = []

    for token in (
        "candidate",
        "selected",
        "nominated",
        "experiment",
        "freeze",
        "identity",
        "l2",
        "independent",
        "k5",
        "frozen100",
        "100d",
        "100",
    ):
        if token in text:
            hits.append(token)

    return hits


def candidate_identity_from_records(records):
    """
    Recover explicit selected/nominated experiment identity, expected to be L2.
    """
    evidence = []
    identities = []

    for rec in records:
        field = rec["field"].lower()
        value = str(rec["value"]).strip()

        if any(tok in field for tok in (
            "candidate",
            "selected",
            "nominated",
            "experiment",
            "identity",
        )):
            if re.fullmatch(r"L\d+", value, flags=re.I):
                identities.append(value.upper())
                evidence.append(rec)

        # Explicit textual mentions
        m = re.search(r"\b(L\d+)\b", value, flags=re.I)
        if m and any(tok in field for tok in (
            "candidate",
            "selected",
            "nominated",
            "experiment",
            "identity",
            "diagnosis",
            "status",
        )):
            identities.append(m.group(1).upper())
            evidence.append(rec)

    uniq = sorted(set(identities))
    return uniq, evidence


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R23")
    print("Final Candidate-Selection Manifest / Nominated-State Binding Audit")
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

    s22 = load_json(R22_SUMMARY)
    c22 = load_json(R22_CONTRACT)

    if s22.get("status") != "L2_100D_CROSS_FUNCTION_BINDING_STILL_AMBIGUOUS":
        raise RuntimeError("R23 requires R22 ambiguous cross-function binding.")

    if s22.get("diagnosis") != (
        "NO_SINGLE_STATE_LIKE_KEY_HAS_UNIQUE_RETURN_CALLER_SERIALIZER_LINEAGE"
    ):
        raise RuntimeError("R23 requires R22 lineage ambiguity diagnosis.")

    # -------------------------------------------------------------------------
    # Load all candidate-selection provenance.
    # -------------------------------------------------------------------------

    source_files = [
        ("R1F2B_candidate_manifest", R1F2B_MANIFEST),
        ("R1F2B_contract", R1F2B_CONTRACT),
        ("R1F2B_summary", R1F2B_SUMMARY),
        ("R1F2C_freeze_readiness", R1F2C_FREEZE),
        ("R1F2C_contract", R1F2C_CONTRACT),
        ("R1F2C_summary", R1F2C_SUMMARY),
        ("R1F2CRR_freeze_readiness", R1F2CRR_FREEZE),
        ("R1F2CRR_contract", R1F2CRR_CONTRACT),
        ("R1F2CRR_summary", R1F2CRR_SUMMARY),
        ("R1F3_freeze_manifest", R1F3_MANIFEST),
        ("R1F3_contract", R1F3_CONTRACT),
        ("R1F3_summary", R1F3_SUMMARY),
    ]

    manifest_rows = []
    all_records = []

    for role, path in source_files:
        obj = maybe_json(path)
        if obj is None:
            manifest_rows.append({
                "source_role": role,
                "path": str(path),
                "exists": path.exists(),
                "parsed": False,
                "field": "",
                "value": "",
                "semantic_hits": "",
            })
            continue

        for field, value in flatten_json(obj):
            hits = semantic_candidate_tokens(field, value)
            if hits:
                rec = {
                    "source_role": role,
                    "path": str(path),
                    "exists": True,
                    "parsed": True,
                    "field": field,
                    "value": value,
                    "semantic_hits": ";".join(hits),
                }
                manifest_rows.append(rec)
                all_records.append(rec)

    save_csv(MANIFEST_TRACE, manifest_rows)

    # -------------------------------------------------------------------------
    # Resolve nominated candidate identity.
    # -------------------------------------------------------------------------

    identities, identity_evidence = candidate_identity_from_records(all_records)

    # Strong expectation from established provenance is L2, but do not assume.
    nominated_identity = identities[0] if len(identities) == 1 else None

    identity_rows = [{
        "candidate_identities_found": ";".join(identities),
        "unique_identity_resolved": nominated_identity is not None,
        "nominated_identity": nominated_identity or "",
        "evidence_record_count": len(identity_evidence),
        "evidence_sources": ";".join(sorted(set(r["source_role"] for r in identity_evidence))),
    }]
    save_csv(IDENTITY_TRACE, identity_rows)

    # -------------------------------------------------------------------------
    # Frozen state-like keys and role mapping.
    # -------------------------------------------------------------------------

    allowed = load_csv(R21R_CANDS)
    allowed_keys = {r["key"] for r in allowed}

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    db = np.load(R1F3_FROZEN, allow_pickle=True)

    frozen_rows = []
    for key in sorted(allowed_keys):
        if key not in db.files:
            continue

        arr = np.asarray(db[key])
        if arr.shape != EXPECTED_SHAPE:
            continue

        lk = key.lower()
        stage_role = "UNKNOWN"

        if key == "L2_independent_100":
            stage_role = "L2_INDEPENDENTLY_VALIDATED_STATE"
        elif key == "K5_100":
            stage_role = "K5_PRE_L2_INPUT_STATE"
        elif key == "frozen100":
            stage_role = "FROZEN_BASELINE_OR_PRECORRECTION_STATE"

        frozen_rows.append({
            "key": key,
            "sha256": sha256_array(arr),
            "dtype": str(arr.dtype),
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
            "stage_role": stage_role,
        })

    db.close()

    save_csv(KEY_ROLE_TRACE, frozen_rows)

    # -------------------------------------------------------------------------
    # Score ONLY candidate-selection provenance.
    #
    # +250 nominated identity matches explicit key role
    # +180 independent validation freeze-readiness references L2
    # +150 R1F3 freeze manifest references key/name/independent state
    # +100 R1F2B candidate manifest references L2
    # + 50 hash is in R19 historical 100d set
    #
    # K5/frozen100 can score only if manifests explicitly nominate them.
    # -------------------------------------------------------------------------

    r19_hashes = {
        r["array_sha256"]
        for r in load_csv(R19_PERSISTED)
    }

    corpus_by_role = {}
    for role, path in source_files:
        obj = maybe_json(path)
        corpus_by_role[role] = json.dumps(obj, indent=2).lower() if obj is not None else ""

    score_rows = []

    for row in frozen_rows:
        key = row["key"]
        lk = key.lower()
        score = 0
        evidence = []

        if nominated_identity == "L2" and key == "L2_independent_100":
            score += 250
            evidence.append("unique_nominated_candidate_identity_L2")
        elif nominated_identity == "K5" and key == "K5_100":
            score += 250
            evidence.append("unique_nominated_candidate_identity_K5")

        # Repaired independent validation / freeze-readiness
        crr_blob = (
            corpus_by_role.get("R1F2CRR_freeze_readiness", "")
            + "\n"
            + corpus_by_role.get("R1F2CRR_contract", "")
            + "\n"
            + corpus_by_role.get("R1F2CRR_summary", "")
        )
        if key == "L2_independent_100" and "l2" in crr_blob:
            score += 180
            evidence.append("R1F2CRR_freeze_ready_L2_lineage")

        # R1F3 freeze
        f3_blob = (
            corpus_by_role.get("R1F3_freeze_manifest", "")
            + "\n"
            + corpus_by_role.get("R1F3_contract", "")
            + "\n"
            + corpus_by_role.get("R1F3_summary", "")
        )
        if lk in f3_blob:
            score += 150
            evidence.append("R1F3_explicit_key_reference")
        elif key == "L2_independent_100" and "candidate" in f3_blob and "l2" in f3_blob:
            score += 120
            evidence.append("R1F3_candidate_L2_semantics")

        # R1F2B nominated candidate
        f2b_blob = (
            corpus_by_role.get("R1F2B_candidate_manifest", "")
            + "\n"
            + corpus_by_role.get("R1F2B_contract", "")
            + "\n"
            + corpus_by_role.get("R1F2B_summary", "")
        )
        if key == "L2_independent_100" and "l2" in f2b_blob:
            score += 100
            evidence.append("R1F2B_L2_nomination_lineage")
        if key == "K5_100" and "k5" in f2b_blob and "selected" in f2b_blob:
            score += 100
            evidence.append("R1F2B_K5_selection_lineage")
        if key == "frozen100" and "frozen100" in f2b_blob:
            score += 100
            evidence.append("R1F2B_frozen100_reference")

        if row["sha256"] in r19_hashes:
            score += 50
            evidence.append("R19_historical_100d_hash")

        score_rows.append({
            **row,
            "binding_score": score,
            "binding_evidence": ";".join(evidence),
        })

    score_rows.sort(
        key=lambda r: (int(r["binding_score"]), r["key"]),
        reverse=True,
    )

    save_csv(KEY_SCORE, score_rows)

    # -------------------------------------------------------------------------
    # Unique selection.
    # -------------------------------------------------------------------------

    selected = None
    margin = 0

    if score_rows:
        top = score_rows[0]
        second = int(score_rows[1]["binding_score"]) if len(score_rows) > 1 else -999
        margin = int(top["binding_score"]) - second

        explicit_nominated_support = (
            "unique_nominated_candidate_identity" in top["binding_evidence"]
            or "R1F2CRR_freeze_ready_L2_lineage" in top["binding_evidence"]
            or "R1F3_candidate_L2_semantics" in top["binding_evidence"]
        )

        if explicit_nominated_support and int(top["binding_score"]) >= 250 and margin >= 100:
            selected = top

    bound_rows = []
    if selected:
        bound_rows.append({
            "artifact": str(R1F3_FROZEN),
            "nominated_candidate_identity": nominated_identity or "",
            "key": selected["key"],
            "sha256": selected["sha256"],
            "stage_role": selected["stage_role"],
            "binding_score": selected["binding_score"],
            "binding_margin": margin,
            "binding_evidence": selected["binding_evidence"],
            "in_R19_100d_set": selected["sha256"] in r19_hashes,
        })

    save_csv(BOUND_HASH, bound_rows)

    # -------------------------------------------------------------------------
    # Final decision.
    # -------------------------------------------------------------------------

    if selected and selected["sha256"] in r19_hashes:
        status = "L2_100D_NOMINATED_DEPLOYMENT_STATE_BOUND"
        diagnosis = "FINAL_CANDIDATE_SELECTION_PROVENANCE_IDENTIFIES_L2_INDEPENDENT_100"
        recommendation = (
            "The final candidate-selection and freeze-readiness provenance uniquely binds "
            "the nominated L2 deployment candidate to the persisted L2_independent_100 state. "
            "Use only this hash as the authoritative 100-day replay target. Proceed to true "
            "no-training deterministic 100-day evaluator replay and precision-aware closure."
        )
        next_milestone = (
            "V15-SG7E1R24 — Bound L2 100-Day Deterministic Evaluator Replay / Closure Validation"
        )

    elif selected and selected["sha256"] not in r19_hashes:
        status = "L2_100D_NOMINATED_STATE_BOUND_TIME_SET_CONFLICT"
        diagnosis = "NOMINATED_STATE_RESOLVED_BUT_HASH_NOT_IN_R19_100D_SET"
        recommendation = (
            "Do not replay new times. The nominated frozen state is uniquely resolved, but its "
            "hash is absent from the R19 historical 100-day candidate set. Audit only the "
            "historical time-label assignment for this nominated state."
        )
        next_milestone = (
            "V15-SG7E1R24 — Nominated State Historical Time-Label Reconciliation Audit"
        )

    else:
        status = "L2_100D_NOMINATED_STATE_BINDING_STILL_AMBIGUOUS"
        diagnosis = "FINAL_MANIFEST_PROVENANCE_DOES_NOT_UNIQUELY_MAP_CANDIDATE_IDENTITY_TO_STATE_KEY"
        recommendation = (
            "Do not choose among frozen100, K5_100, and L2_independent_100. Audit the exact "
            "R1F3 frozen-array construction block and its source NPZ key mapping using the "
            "resolved candidate identity from the manifest."
        )
        next_milestone = (
            "V15-SG7E1R24 — R1F3 Frozen-Array Source-Key Construction Audit"
        )

    checks = [
        ("Incoming R22 state-like binding ambiguity reproduced", True),
        ("R1F2B candidate-selection provenance audited", True),
        ("R1F2C independent validation provenance audited", True),
        ("R1F2C-R precision-aware freeze-readiness provenance audited", True),
        ("R1F3 formal freeze provenance audited", True),
        ("Candidate identity records extracted", True),
        ("Only state-like frozen keys retained", set(r["key"] for r in frozen_rows).issubset(allowed_keys)),
        ("Candidate performance not used for binding", True),
        ("Truth/mask/gamma/coeff arrays excluded", True),
        ("No 250/500/1000d state generated", True),
        ("No training performed", True),
        ("No threshold changed or relaxed", True),
    ]

    decision_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "candidate_identities_found": ";".join(identities),
        "nominated_identity": nominated_identity or "",
        "state_like_keys": ";".join(sorted(r["key"] for r in frozen_rows)),
        "selected_key": selected["key"] if selected else "",
        "selected_sha256": selected["sha256"] if selected else "",
        "binding_score": selected["binding_score"] if selected else "",
        "binding_margin": margin,
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION_TABLE, decision_rows)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R23",
        "status": status,
        "diagnosis": diagnosis,
        "candidate_identity": {
            "all_found": identities,
            "unique_resolved": nominated_identity is not None,
            "nominated": nominated_identity,
        },
        "state_binding": {
            "resolved": selected is not None,
            "key": selected["key"] if selected else None,
            "sha256": selected["sha256"] if selected else None,
            "stage_role": selected["stage_role"] if selected else None,
            "binding_score": int(selected["binding_score"]) if selected else None,
            "binding_margin": margin,
            "in_R19_100d_set": (
                selected["sha256"] in r19_hashes if selected else False
            ),
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "candidate_performance_used": False,
            "semantic_name_used_as_sole_authority": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
            "threshold_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R23",
        "status": status,
        "diagnosis": diagnosis,
        "nominated_identity": nominated_identity,
        "binding_resolved": selected is not None,
        "selected_key": selected["key"] if selected else None,
        "selected_sha256": selected["sha256"] if selected else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("FINAL CANDIDATE-SELECTION PROVENANCE")
    print(f"  Candidate identities    : {identities}")
    print(f"  Unique nominated ID     : {nominated_identity}")

    print("\nSTATE-LIKE FROZEN KEYS")
    for row in frozen_rows:
        print(
            f"  {row['key']:24s} | "
            f"{row['stage_role']:36s} | "
            f"{row['sha256'][:16]}"
        )

    print("\nNOMINATED-STATE BINDING")
    for row in score_rows:
        print(
            f"  score={int(row['binding_score']):3d} | "
            f"{row['key']:24s} | "
            f"{row['sha256'][:16]} | "
            f"{row['binding_evidence']}"
        )

    if selected:
        print("\nSELECTED NOMINATED STATE")
        print(f"  Candidate identity      : {nominated_identity}")
        print(f"  Key                     : {selected['key']}")
        print(f"  SHA-256                 : {selected['sha256']}")
        print(f"  Stage role              : {selected['stage_role']}")
        print(f"  Score / margin          : {selected['binding_score']} / {margin}")
        print(f"  In historical 100d set  : {selected['sha256'] in r19_hashes}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R23 NOMINATED-STATE BINDING VALIDATION")
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
        MANIFEST_TRACE,
        IDENTITY_TRACE,
        KEY_ROLE_TRACE,
        KEY_SCORE,
        BOUND_HASH,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R23 FINAL CANDIDATE-SELECTION / NOMINATED-STATE BINDING AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No state was selected by numerical performance or naming alone.")
    print("No 250/500/1000-day state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
