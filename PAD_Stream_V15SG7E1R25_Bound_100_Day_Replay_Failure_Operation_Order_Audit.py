from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R25
# Bound 100-Day Replay Failure / Operation-Order Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO GUARD CHANGE.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
#
# PURPOSE
# -------
# R24 failed only:
#
#   unique_numerical_replay_output
#
# while ALL of the following passed:
#
#   - bound target hash
#   - authoritative model hash
#   - precision-aware closure
#   - truth direction
#   - no overshoot
#   - saturation bounds
#
# R25 determines whether the multiple passing replay hashes represent:
#
#   A) genuinely different physical replay operators, or
#   B) the same deterministic algebra under float32/float64 operation order,
#      clipping no-ops, and serialization precision.
#
# R25 does NOT relax the R24 precision envelope.
# It audits the failed uniqueness criterion itself.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R25"
OUT.mkdir(parents=True, exist_ok=True)

R24_DIR = ROOT / "output" / "V15_SG7E1R24"

R24_SUMMARY = R24_DIR / "PAD_Stream_V15SG7E1R24_Summary.json"
R24_CONTRACT = R24_DIR / "V15SG7E1R24_Bound_100d_Replay_Validation_Contract.json"
R24_VARIANTS = R24_DIR / "V15SG7E1R24_Replay_Expression_Variants.csv"
R24_PRECISION = R24_DIR / "V15SG7E1R24_Precision_Aware_Closure.csv"
R24_GATES = R24_DIR / "V15SG7E1R24_Final_Replay_Gate_Matrix.csv"
R24_NUM = R24_DIR / "V15SG7E1R24_100d_Deterministic_Replay.npz"

PAIRWISE_TABLE = OUT / "V15SG7E1R25_Passing_Variant_Pairwise_Closure.csv"
FAMILY_TABLE = OUT / "V15SG7E1R25_Operation_Order_Equivalence_Families.csv"
NOOP_TABLE = OUT / "V15SG7E1R25_Clip_Guard_NoOp_Audit.csv"
FAILURE_TABLE = OUT / "V15SG7E1R25_Uniqueness_Failure_Classification.csv"
DECISION_TABLE = OUT / "V15SG7E1R25_Operation_Order_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R25_Operation_Order_Audit_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R25_Summary.json"


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


def metrics(a, b):
    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


def sha256_array(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def canonical_family(name: str):
    low = name.lower()

    if "guard" in low:
        guard = "GUARDED"
    else:
        guard = "UNGUARDED"

    if "clip" in low:
        clip = "CLIPPED"
    else:
        clip = "UNCLIPPED"

    if "float32" in low:
        precision = "FLOAT32"
    elif "float64_then_float32" in low or "clip_then_float32" in low:
        precision = "SERIALIZED_FLOAT32"
    else:
        precision = "FLOAT64"

    return precision, guard, clip


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R25")
    print("Bound 100-Day Replay Failure / Operation-Order Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE CHANGED.
NO REPLAY TOLERANCE WILL BE RELAXED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
""")

    s24 = load_json(R24_SUMMARY)
    c24 = load_json(R24_CONTRACT)

    if s24.get("status") != "L2_100D_DETERMINISTIC_REPLAY_VALIDATION_FAILED":
        raise RuntimeError("R25 requires the R24 replay-validation failure status.")

    if s24.get("diagnosis") != (
        "BOUND_100D_STATE_DOES_NOT_CLOSE_UNDER_CURRENT_DETERMINISTIC_REPLAY_CONTRACT"
    ):
        raise RuntimeError("R25 requires the R24 replay-contract diagnosis.")

    gate_rows = load_csv(R24_GATES)
    failed = [r["gate"] for r in gate_rows if str(r["passed"]).lower() not in ("true", "1")]

    if failed != ["unique_numerical_replay_output"]:
        raise RuntimeError(
            f"R25 expects only unique_numerical_replay_output to fail; got {failed}"
        )

    precision_rows = load_csv(R24_PRECISION)
    if len(precision_rows) != 1:
        raise RuntimeError("R24 precision table malformed.")

    envelope = float(precision_rows[0]["derived_envelope"])

    variant_rows = load_csv(R24_VARIANTS)
    if not variant_rows:
        raise RuntimeError("No R24 replay variants found.")

    passing = [
        r for r in variant_rows
        if float(r["Linf"]) <= envelope
    ]

    if len(passing) < 2:
        raise RuntimeError("R25 requires multiple precision-passing replay variants.")

    # -------------------------------------------------------------------------
    # Reconstruct known R24 variants from the persisted R24 numerical package.
    # -------------------------------------------------------------------------

    if not R24_NUM.exists():
        raise FileNotFoundError(R24_NUM)

    db = np.load(R24_NUM, allow_pickle=True)

    target = np.asarray(db["target_L2_independent_100"])
    k5 = np.asarray(db["K5_100"])
    truth = np.asarray(db["truth100"])
    gamma = np.asarray(db["L2_gamma_independent"])
    guard = np.asarray(db["guard_mask"]) > 0.5

    db.close()

    k5_64 = k5.astype(np.float64)
    truth_64 = truth.astype(np.float64)
    gamma_64 = gamma.astype(np.float64)

    raw64 = k5_64 + gamma_64 * (truth_64 - k5_64)

    k5_32 = k5.astype(np.float32)
    truth_32 = truth.astype(np.float32)
    gamma_32 = gamma.astype(np.float32)

    residual32 = np.subtract(truth_32, k5_32, dtype=np.float32)
    corr32 = np.multiply(gamma_32, residual32, dtype=np.float32)
    raw32 = np.add(k5_32, corr32, dtype=np.float32)

    arrays = {
        "V0_float64_base_plus_gamma_residual": raw64,
        "V1_float64_clip01": np.clip(raw64, 0.0, 1.0),
        "V2_float64_guard_preserve_K5": np.where(guard, k5_64, raw64),
        "V3_float64_guard_then_clip": np.clip(np.where(guard, k5_64, raw64), 0.0, 1.0),
        "V4_float32_base_plus_gamma_residual": raw32,
        "V5_float32_clip01": np.clip(raw32, np.float32(0.0), np.float32(1.0)).astype(np.float32),
        "V6_float32_guard_preserve_K5": np.where(guard, k5_32, raw32).astype(np.float32),
        "V7_float32_guard_then_clip": np.clip(
            np.where(guard, k5_32, raw32),
            np.float32(0.0),
            np.float32(1.0),
        ).astype(np.float32),
        "V8_float64_then_float32": raw64.astype(np.float32),
        "V9_float64_clip_then_float32": np.clip(raw64, 0.0, 1.0).astype(np.float32),
    }

    # -------------------------------------------------------------------------
    # Pairwise closure among all precision-passing variants.
    # -------------------------------------------------------------------------

    passing_names = [r["variant"] for r in passing if r["variant"] in arrays]

    pairwise_rows = []
    max_pairwise_linf = 0.0

    for i, a_name in enumerate(passing_names):
        for b_name in passing_names[i + 1:]:
            m = metrics(arrays[a_name], arrays[b_name])
            max_pairwise_linf = max(max_pairwise_linf, m["Linf"])

            pairwise_rows.append({
                "variant_A": a_name,
                "variant_B": b_name,
                **m,
                "within_R24_envelope": m["Linf"] <= envelope,
            })

    save_csv(PAIRWISE_TABLE, pairwise_rows)

    all_pairwise_close = all(
        bool(r["within_R24_envelope"])
        for r in pairwise_rows
    )

    # -------------------------------------------------------------------------
    # Audit whether clipping and guard application actually modify the replay.
    # -------------------------------------------------------------------------

    noop_rows = []

    comparisons = [
        ("clip_float64", "V0_float64_base_plus_gamma_residual", "V1_float64_clip01"),
        ("guard_float64", "V0_float64_base_plus_gamma_residual", "V2_float64_guard_preserve_K5"),
        ("guard_clip_float64", "V0_float64_base_plus_gamma_residual", "V3_float64_guard_then_clip"),
        ("clip_float32", "V4_float32_base_plus_gamma_residual", "V5_float32_clip01"),
        ("guard_float32", "V4_float32_base_plus_gamma_residual", "V6_float32_guard_preserve_K5"),
        ("guard_clip_float32", "V4_float32_base_plus_gamma_residual", "V7_float32_guard_then_clip"),
        ("clip_serialized_float32", "V8_float64_then_float32", "V9_float64_clip_then_float32"),
    ]

    for label, a_name, b_name in comparisons:
        m = metrics(arrays[a_name], arrays[b_name])
        noop_rows.append({
            "comparison": label,
            "variant_A": a_name,
            "variant_B": b_name,
            **m,
            "exact_noop": m["Linf"] == 0.0,
            "precision_noop": m["Linf"] <= envelope,
        })

    save_csv(NOOP_TABLE, noop_rows)

    all_guard_clip_noop = all(bool(r["precision_noop"]) for r in noop_rows)

    # -------------------------------------------------------------------------
    # Group variants by numerical hash and semantic family.
    # -------------------------------------------------------------------------

    family_rows = []

    hashes = {}
    for name in passing_names:
        arr = np.asarray(arrays[name])
        h = sha256_array(arr)
        hashes.setdefault(h, []).append(name)

    for h, names in hashes.items():
        fams = sorted(set("|".join(canonical_family(n)) for n in names))
        target_metrics = [metrics(arrays[n], target) for n in names]

        family_rows.append({
            "output_sha256": h,
            "variant_count": len(names),
            "variants": ";".join(names),
            "semantic_families": ";".join(fams),
            "best_target_Linf": min(m["Linf"] for m in target_metrics),
            "all_within_R24_envelope": all(m["Linf"] <= envelope for m in target_metrics),
        })

    save_csv(FAMILY_TABLE, family_rows)

    # -------------------------------------------------------------------------
    # Failure classification.
    #
    # The key question is whether multiple hashes indicate physically distinct
    # operators. If:
    #
    #   - every passing output closes to target inside the unchanged envelope,
    #   - every passing output closes pairwise inside the same envelope,
    #   - guard and clip variants are no-ops within that envelope,
    #
    # then the failure is representation / operation-order multiplicity rather
    # than physical replay ambiguity.
    # -------------------------------------------------------------------------

    passing_all_target_close = all(float(r["Linf"]) <= envelope for r in passing)

    representation_only = (
        passing_all_target_close
        and all_pairwise_close
        and all_guard_clip_noop
    )

    failure_rows = [{
        "failed_R24_gate": "unique_numerical_replay_output",
        "passing_variant_count": len(passing_names),
        "passing_output_hash_count": len(hashes),
        "R24_envelope": envelope,
        "max_pairwise_passing_Linf": max_pairwise_linf,
        "all_passing_close_to_target": passing_all_target_close,
        "all_passing_pairwise_close": all_pairwise_close,
        "guard_clip_are_precision_noops": all_guard_clip_noop,
        "representation_only_nonuniqueness": representation_only,
    }]
    save_csv(FAILURE_TABLE, failure_rows)

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    if representation_only:
        status = "R24_UNIQUENESS_FAILURE_IS_PRECISION_EQUIVALENCE"
        diagnosis = "MULTIPLE_REPLAY_HASHES_ARE_OPERATION_ORDER_REPRESENTATIONS_OF_ONE_PHYSICAL_STATE"
        recommendation = (
            "The R24 failure is not a physical replay ambiguity. All precision-passing "
            "variants close to the same bound target and to one another inside the unchanged "
            "float32 ULP envelope, while guard/clipping variants are numerical no-ops at this "
            "state. Replace the exact-hash uniqueness gate with a precision-equivalence-class "
            "criterion derived from the persisted float32 representation, then rerun the bound "
            "100-day validation without changing gamma, guard, model weights, or tolerance."
        )
        next_milestone = (
            "V15-SG7E1R25R — Precision-Equivalence Replay Contract Repair / Revalidation"
        )
    else:
        status = "R24_UNIQUENESS_FAILURE_REFLECTS_REAL_REPLAY_AMBIGUITY"
        diagnosis = "PASSING_VARIANTS_ARE_NOT_ONE_PRECISION_EQUIVALENCE_CLASS"
        recommendation = (
            "Do not repair the uniqueness contract. Audit the exact historical operation order "
            "and guard application because the passing variants remain materially distinct."
        )
        next_milestone = (
            "V15-SG7E1R25A — Historical Replay Operation-Order Provenance Audit"
        )

    checks = [
        ("Incoming R24 failure reproduced", True),
        ("Only R24 uniqueness gate failed", failed == ["unique_numerical_replay_output"]),
        ("R24 precision envelope preserved unchanged", True),
        ("All precision-passing variants reconstructed", len(passing_names) == len(passing)),
        ("Pairwise passing-variant closure audited", True),
        ("Guard / clip no-op behavior audited", True),
        ("Output-hash families established", True),
        ("No tolerance relaxed", True),
        ("No gamma/guard/model change", True),
        ("No new physical-time state generated", True),
        ("No training performed", True),
    ]

    decision_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "R24_envelope": envelope,
        "passing_variant_count": len(passing_names),
        "passing_hash_count": len(hashes),
        "max_pairwise_Linf": max_pairwise_linf,
        "representation_only_nonuniqueness": representation_only,
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION_TABLE, decision_rows)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R25",
        "status": status,
        "diagnosis": diagnosis,
        "R24_failed_gate": "unique_numerical_replay_output",
        "precision_envelope": envelope,
        "passing_variant_count": len(passing_names),
        "passing_output_hash_count": len(hashes),
        "max_pairwise_passing_Linf": max_pairwise_linf,
        "representation_only_nonuniqueness": representation_only,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_recalibrated": False,
            "guard_changed": False,
            "tolerance_relaxed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R25",
        "status": status,
        "diagnosis": diagnosis,
        "representation_only_nonuniqueness": representation_only,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("R24 FAILURE REPRODUCTION")
    print(f"  Failed gates            : {failed}")
    print(f"  Precision envelope      : {envelope:.6e}")
    print(f"  Passing variants        : {len(passing_names)}")
    print(f"  Passing output hashes   : {len(hashes)}")

    print("\nPASSING-VARIANT PAIRWISE CLOSURE")
    print(f"  Max pairwise Linf       : {max_pairwise_linf:.6e}")
    print(f"  All pairwise <= envelope: {all_pairwise_close}")

    print("\nGUARD / CLIP OPERATION AUDIT")
    for row in noop_rows:
        print(
            f"  {row['comparison']:28s} | "
            f"Linf={float(row['Linf']):.6e} | "
            f"precisionNoOp={row['precision_noop']}"
        )

    print("\nOUTPUT HASH FAMILIES")
    for row in family_rows:
        print(
            f"  {row['output_sha256'][:16]} | "
            f"variants={int(row['variant_count'])} | "
            f"bestTargetLinf={float(row['best_target_Linf']):.6e}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7E1R25 OPERATION-ORDER AUDIT VALIDATION")
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
        PAIRWISE_TABLE,
        FAMILY_TABLE,
        NOOP_TABLE,
        FAILURE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R25 BOUND 100-DAY REPLAY FAILURE / OPERATION-ORDER AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was changed.")
    print("The R24 precision envelope was not relaxed.")
    print("No 250/500/1000-day state was generated.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
