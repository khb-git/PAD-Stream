from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R21R
# Serializer Binding Semantic-Role Contradiction Audit
#
# PURPOSE
# -------
# R21 reported:
#
#   L2_100D_EVALUATOR_OUTPUT_BOUND
#
# but selected:
#
#   guard_mask
#
# as the alleged 100-day evaluator output.
#
# A guard mask is structurally an auxiliary protection field, not the deployed
# saturation state. R21 also reported:
#
#   evaluator seed symbols : []
#   fallback seed used     : True
#
# Therefore R21's source score is not sufficient to establish semantic identity.
#
# R21R audits whether the selected bound key is actually a deployable saturation
# field or an auxiliary array. It compares:
#
#   - dtype / value range
#   - boolean / binary structure
#   - source semantic role
#   - serializer lineage
#   - frozen-package neighboring keys
#   - explicit state/candidate aliases
#
# NO TRAINING.
# NO MODEL CHANGES.
# NO NEW STATE GENERATION.
# NO SG7E GATE EVALUATION.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R21R"
OUT.mkdir(parents=True, exist_ok=True)

R21_DIR = ROOT / "output" / "V15_SG7E1R21"
R21_SUMMARY = R21_DIR / "PAD_Stream_V15SG7E1R21_Summary.json"
R21_CONTRACT = R21_DIR / "V15SG7E1R21_Final_Freeze_Serializer_Binding_Contract.json"
R21_SCORE = R21_DIR / "V15SG7E1R21_Final_Persisted_Key_Binding.csv"
R21_SERIAL = R21_DIR / "V15SG7E1R21_Serializer_Expansion_Trace.csv"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

ROLE_TABLE = OUT / "V15SG7E1R21R_Frozen_Key_Semantic_Roles.csv"
CONTRADICTION_TABLE = OUT / "V15SG7E1R21R_Selected_Binding_Contradiction.csv"
STATE_CANDIDATES = OUT / "V15SG7E1R21R_State_Like_Key_Candidates.csv"
DECISION_TABLE = OUT / "V15SG7E1R21R_Semantic_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R21R_Semantic_Role_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R21R_Summary.json"

EXPECTED_SHAPE = (2662, 201)


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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def classify_key(key, arr):
    lk = key.lower()

    unique = np.unique(arr[np.isfinite(arr)]) if np.issubdtype(arr.dtype, np.number) else np.array([])
    unique_count = int(len(unique))

    binary_like = False
    if unique_count <= 3 and unique_count > 0:
        vals = set(np.asarray(unique, dtype=float).round(12).tolist())
        binary_like = vals.issubset({0.0, 1.0})

    mask_name = any(tok in lk for tok in ("mask", "guard"))
    coeff_name = any(tok in lk for tok in ("coeff", "gamma", "weight"))
    truth_name = "truth" in lk
    state_name = any(tok in lk for tok in ("state", "candidate", "independent_100", "frozen100", "k5_100"))

    if mask_name or binary_like:
        role = "AUXILIARY_MASK"
    elif coeff_name:
        role = "AUXILIARY_COEFFICIENT"
    elif truth_name:
        role = "REFERENCE_TRUTH"
    elif state_name:
        role = "STATE_LIKE"
    else:
        role = "UNKNOWN"

    return role, binary_like, unique_count


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R21R")
    print("Serializer Binding Semantic-Role Contradiction Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO NEW STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
""")

    s21 = load_json(R21_SUMMARY)
    c21 = load_json(R21_CONTRACT)

    if s21.get("status") != "L2_100D_EVALUATOR_OUTPUT_BOUND":
        raise RuntimeError("R21R requires R21 bound-output status.")

    selected_key = s21.get("selected_key")
    selected_sha = s21.get("selected_sha256")

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    db = np.load(R1F3_FROZEN, allow_pickle=True)

    role_rows = []
    state_rows = []

    for key in db.files:
        arr = np.asarray(db[key])
        if arr.shape != EXPECTED_SHAPE:
            continue

        role, binary_like, unique_count = classify_key(key, arr)

        rec = {
            "key": key,
            "dtype": str(arr.dtype),
            "shape": str(arr.shape),
            "sha256": sha256_array(arr),
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
            "unique_value_count": unique_count,
            "binary_like": binary_like,
            "semantic_role": role,
            "is_selected_R21_key": key == selected_key,
        }
        role_rows.append(rec)

        if role == "STATE_LIKE":
            state_rows.append(rec)

    db.close()

    save_csv(ROLE_TABLE, role_rows)
    save_csv(STATE_CANDIDATES, state_rows)

    selected_row = next((r for r in role_rows if r["key"] == selected_key), None)

    contradiction = False
    reason = ""

    if selected_row is None:
        contradiction = True
        reason = "R21_SELECTED_KEY_NOT_FOUND_IN_FROZEN_PACKAGE"
    elif selected_row["semantic_role"] in {"AUXILIARY_MASK", "AUXILIARY_COEFFICIENT", "REFERENCE_TRUTH"}:
        contradiction = True
        reason = f"R21_SELECTED_KEY_HAS_NON_DEPLOYMENT_ROLE_{selected_row['semantic_role']}"
    elif bool(selected_row["binary_like"]):
        contradiction = True
        reason = "R21_SELECTED_KEY_IS_BINARY_MASK_LIKE"

    fallback_used = bool(
        c21.get("dataflow", {}).get("fallback_seed_used", False)
    )
    evaluator_seeds = c21.get("dataflow", {}).get("evaluator_seed_symbols", [])

    if fallback_used and not evaluator_seeds:
        contradiction = True
        if reason:
            reason += ";"
        reason += "R21_USED_FALLBACK_WITH_NO_EVALUATOR_SEED_SYMBOLS"

    contradiction_rows = [{
        "selected_key": selected_key,
        "selected_sha256": selected_sha,
        "selected_semantic_role": selected_row["semantic_role"] if selected_row else "",
        "selected_binary_like": selected_row["binary_like"] if selected_row else "",
        "fallback_seed_used": fallback_used,
        "evaluator_seed_symbols": ";".join(evaluator_seeds),
        "binding_semantically_valid": not contradiction,
        "contradiction_reason": reason,
    }]
    save_csv(CONTRADICTION_TABLE, contradiction_rows)

    if contradiction:
        status = "R21_SERIALIZER_BINDING_REJECTED_BY_SEMANTIC_ROLE_AUDIT"
        diagnosis = "GUARD_MASK_OR_AUXILIARY_FIELD_CANNOT_BE_AUTHORITATIVE_100D_DEPLOYMENT_STATE"
        recommendation = (
            "Reject the R21 guard_mask binding. Do not perform replay closure against it. "
            "Trace the actual deployed saturation/state variable across the final R1F2C/R1F3 "
            "caller-return boundary, restricting candidates to state-like arrays and excluding "
            "truth, masks, gamma, coefficient, and guard fields."
        )
        next_milestone = (
            "V15-SG7E1R22 — Cross-Function Deployment-State Return / Caller Binding Audit"
        )
    else:
        status = "R21_SERIALIZER_BINDING_SEMANTICALLY_CONFIRMED"
        diagnosis = "SELECTED_KEY_HAS_VALID_DEPLOYMENT_STATE_ROLE"
        recommendation = (
            "The R21 selected key survives semantic-role validation. Proceed to true deterministic "
            "100-day evaluator replay and precision-aware closure."
        )
        next_milestone = (
            "V15-SG7E1R22 — Bound 100-Day Deterministic Evaluator Replay / Closure Validation"
        )

    decision = [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_key": selected_key,
        "selected_sha256": selected_sha,
        "binding_rejected": contradiction,
        "state_like_candidate_count": len(state_rows),
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION_TABLE, decision)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R21R",
        "status": status,
        "diagnosis": diagnosis,
        "selected_key": selected_key,
        "selected_sha256": selected_sha,
        "binding_semantically_valid": not contradiction,
        "contradiction_reason": reason,
        "state_like_candidates": [
            {"key": r["key"], "sha256": r["sha256"]}
            for r in state_rows
        ],
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "new_state_generated": False,
            "SG7E_gate_evaluated": False,
            "threshold_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R21R",
        "status": status,
        "diagnosis": diagnosis,
        "binding_rejected": contradiction,
        "selected_key": selected_key,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("R21 SELECTED BINDING")
    print(f"  Key                     : {selected_key}")
    print(f"  SHA-256                 : {selected_sha}")
    if selected_row:
        print(f"  Semantic role           : {selected_row['semantic_role']}")
        print(f"  Binary-like             : {selected_row['binary_like']}")
        print(f"  Range                   : {selected_row['min']:.6e} -> {selected_row['max']:.6e}")

    print("\nDATAFLOW AUTHORITY")
    print(f"  Evaluator seed symbols  : {evaluator_seeds}")
    print(f"  Fallback seed used      : {fallback_used}")

    print("\nSTATE-LIKE FROZEN CANDIDATES")
    for r in state_rows:
        print(f"  {r['key']:28s} | {r['sha256'][:16]} | range={r['min']:.6f}->{r['max']:.6f}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R21R SEMANTIC-ROLE VALIDATION")
    print("=" * 78)
    print(f"[{'FAIL' if contradiction else 'PASS'}] R21 selected key has valid deployment-state semantics")
    print("[PASS] Frozen package state-like alternatives inventoried")
    print("[PASS] Auxiliary masks/coefficients/reference-truth fields excluded from deployment-state authority")
    print("[PASS] No candidate selected by numerical performance")
    print("[PASS] No training performed")
    print("[PASS] No SG7E gate evaluated")
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
    for p in (ROLE_TABLE, CONTRADICTION_TABLE, STATE_CANDIDATES, DECISION_TABLE):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R21R SERIALIZER BINDING SEMANTIC-ROLE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No new deployment state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
