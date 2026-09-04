from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R24
# Bound L2 100-Day Deterministic Evaluator Replay / Closure Validation
#
# CONTROLLED REPLAY-CLOSURE MILESTONE
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
# SG7E1R23 established:
#
#   L2_100D_NOMINATED_DEPLOYMENT_STATE_BOUND
#
# with:
#
#   FINAL_CANDIDATE_SELECTION_PROVENANCE_IDENTIFIES_L2_INDEPENDENT_100
#
# Authoritative 100-day target:
#
#   key    = L2_independent_100
#   SHA256 = 01bb967c07b262836f6c140dd519538db13d9ce5b3bc0f83d52a6164ddcfa950
#
# R24 now validates the deterministic 100-day deployment operator itself.
#
# The final L2 crossing-local candidate was built from persisted, immutable
# arrays:
#
#   K5_100
#   truth100
#   L2_gamma_independent
#   guard_mask
#
# The principal replay algebra is:
#
#   L2_replay = K5_100 + gamma * (truth100 - K5_100)
#
# with the accepted crossing guard already represented by the persisted gamma
# field. R24 also audits equivalent source-compatible guarded/clipped/float32
# operation-order variants without calibrating or fitting anything.
#
# Acceptance requires:
#
#   1. R23 bound target reproduced exactly,
#   2. immutable model/checkpoint hash reproduced,
#   3. all replay inputs loaded from persisted provenance,
#   4. one deterministic replay expression uniquely closes to the bound target,
#   5. closure is within precision-aware float32 ULP envelope,
#   6. no truth overshoot / direction violation introduced,
#   7. no training, scaling, anchoring, or gate changes.
#
# Only after R24 passes may 250/500/1000-day states be generated.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R24"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R23_DIR = ROOT / "output" / "V15_SG7E1R23"
R23_SUMMARY = R23_DIR / "PAD_Stream_V15SG7E1R23_Summary.json"
R23_CONTRACT = R23_DIR / "V15SG7E1R23_Final_Candidate_Selection_Binding_Contract.json"
R23_BOUND = R23_DIR / "V15SG7E1R23_Bound_Nominated_State_Hash.csv"

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# Source files used only to corroborate the replay algebra.
SOURCE_CANDIDATES = [
    ROOT / "PAD_Stream_V15SG7CR3F5R1F2B_Controlled_Crossing_Local_Residual_Correction.py",
    ROOT / "PAD_Stream_V15SG7CR3F5R1F2C_Independent_Crossing_Local_Candidate_Validation.py",
    ROOT / "PAD_Stream_V15SG7CR3F5R1F2CRR_Precision_Aware_Independent_Validation_Contract_Repair.py",
    ROOT / "PAD_Stream_V15SG7CR3F5R1F3_Crossing_Local_Candidate_Freeze_Provenance_Manifest.py",
]

EXPECTED_SHAPE = (2662, 201)
TARGET_TIME_DAYS = 100.0

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

IDENTITY_TABLE = OUT / "V15SG7E1R24_Bound_Target_Identity.csv"
INPUT_TABLE = OUT / "V15SG7E1R24_Replay_Input_Identity.csv"
SOURCE_TABLE = OUT / "V15SG7E1R24_Replay_Algebra_Source_Trace.csv"
VARIANT_TABLE = OUT / "V15SG7E1R24_Replay_Expression_Variants.csv"
PRECISION_TABLE = OUT / "V15SG7E1R24_Precision_Aware_Closure.csv"
PHYSICS_TABLE = OUT / "V15SG7E1R24_Replay_Direction_Bounds_Audit.csv"
GATE_TABLE = OUT / "V15SG7E1R24_Final_Replay_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R24_Replay_Validation_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R24_100d_Deterministic_Replay.npz"
CONTRACT_FILE = OUT / "V15SG7E1R24_Bound_100d_Replay_Validation_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R24_Summary.json"


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def float32_envelope(arr):
    a = np.asarray(arr, dtype=np.float32)
    spacing = np.abs(np.spacing(a))
    half_ulp_max = float(np.nanmax(spacing) / 2.0)
    # Same conservative philosophy used in prior precision-aware repair:
    # allow several float32 operations / serialization steps.
    envelope = max(4.0 * half_ulp_max, 1e-12)
    return half_ulp_max, envelope


def metrics(a, b):
    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R24")
    print("Bound L2 100-Day Deterministic Evaluator Replay / Closure Validation")
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

    s23 = load_json(R23_SUMMARY)
    c23 = load_json(R23_CONTRACT)

    if s23.get("status") != "L2_100D_NOMINATED_DEPLOYMENT_STATE_BOUND":
        raise RuntimeError("R24 requires R23 nominated-state bound status.")

    if s23.get("diagnosis") != (
        "FINAL_CANDIDATE_SELECTION_PROVENANCE_IDENTIFIES_L2_INDEPENDENT_100"
    ):
        raise RuntimeError("R24 requires R23 L2_independent_100 diagnosis.")

    bound_key = s23.get("selected_key")
    bound_sha = s23.get("selected_sha256")

    if bound_key != "L2_independent_100":
        raise RuntimeError(f"Unexpected R23 bound key: {bound_key}")

    # -------------------------------------------------------------------------
    # Bound target + replay inputs
    # -------------------------------------------------------------------------

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    db = np.load(R1F3_FROZEN, allow_pickle=True)

    required_keys = [
        "L2_independent_100",
        "K5_100",
        "truth100",
        "L2_gamma_independent",
        "guard_mask",
    ]

    missing = [k for k in required_keys if k not in db.files]
    if missing:
        db.close()
        raise RuntimeError(f"Missing required replay arrays: {missing}")

    target = np.array(db["L2_independent_100"], copy=True)
    k5 = np.array(db["K5_100"], copy=True)
    truth = np.array(db["truth100"], copy=True)
    gamma = np.array(db["L2_gamma_independent"], copy=True)
    guard = np.array(db["guard_mask"], copy=True)

    db.close()

    for name, arr in (
        ("target", target),
        ("K5_100", k5),
        ("truth100", truth),
        ("L2_gamma_independent", gamma),
        ("guard_mask", guard),
    ):
        if arr.shape != EXPECTED_SHAPE:
            raise RuntimeError(f"{name} shape mismatch: {arr.shape}")

    target_sha = sha256_array(target)
    target_hash_match = target_sha == bound_sha

    save_csv(IDENTITY_TABLE, [{
        "time_days": TARGET_TIME_DAYS,
        "bound_key": bound_key,
        "expected_sha256": bound_sha,
        "actual_sha256": target_sha,
        "hash_match": target_hash_match,
        "shape": str(target.shape),
        "dtype": str(target.dtype),
    }])

    input_rows = []
    for key, arr in (
        ("K5_100", k5),
        ("truth100", truth),
        ("L2_gamma_independent", gamma),
        ("guard_mask", guard),
    ):
        input_rows.append({
            "key": key,
            "sha256": sha256_array(arr),
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
        })
    save_csv(INPUT_TABLE, input_rows)

    # -------------------------------------------------------------------------
    # Authoritative model identity remains immutable
    # -------------------------------------------------------------------------

    model_rows = load_csv(R18_MODEL)
    if len(model_rows) != 1:
        raise RuntimeError(f"Expected one authoritative model, found {len(model_rows)}")

    model_path = Path(model_rows[0]["path"])
    expected_model_sha = model_rows[0]["sha256"]
    if not model_path.exists():
        raise FileNotFoundError(model_path)

    actual_model_sha = sha256_file(model_path)
    model_hash_match = actual_model_sha == expected_model_sha

    # -------------------------------------------------------------------------
    # Source algebra corroboration
    # -------------------------------------------------------------------------

    source_rows = []
    algebra_patterns = [
        ("residual_form", r"truth\w*\s*-\s*(?:k5|base|state|candidate)\w*"),
        ("gamma_times_residual", r"gamma\w*\s*\*"),
        ("base_plus_correction", r"(?:k5|base|state|candidate)\w*\s*\+"),
        ("guard_where", r"np\.where\s*\("),
        ("clip", r"np\.clip\s*\("),
        ("float32_cast", r"(?:astype\s*\(\s*np\.float32|dtype\s*=\s*np\.float32)"),
    ]

    for src in SOURCE_CANDIDATES:
        if not src.exists():
            continue
        text = safe_text(src)
        lines = text.splitlines()

        for i, line in enumerate(lines, start=1):
            ll = line.lower()
            if not any(tok in ll for tok in (
                "l2",
                "gamma",
                "truth",
                "k5",
                "guard",
                "candidate",
            )):
                continue

            matched = []
            for name, pat in algebra_patterns:
                if re.search(pat, line, flags=re.I):
                    matched.append(name)

            if matched:
                source_rows.append({
                    "source": str(src),
                    "line": i,
                    "matched_line": line.strip()[:1800],
                    "algebra_features": ";".join(matched),
                    "context": "\n".join(
                        lines[max(0, i-5):min(len(lines), i+7)]
                    )[:5000],
                })

    save_csv(SOURCE_TABLE, source_rows)

    # -------------------------------------------------------------------------
    # Deterministic replay variants
    #
    # No free parameters. Every variant is an exact algebra / dtype / clipping
    # ordering derived from the persisted arrays.
    # -------------------------------------------------------------------------

    variants = {}

    # Float64 arithmetic from persisted values
    k5_64 = np.asarray(k5, dtype=np.float64)
    truth_64 = np.asarray(truth, dtype=np.float64)
    gamma_64 = np.asarray(gamma, dtype=np.float64)
    guard_bool = np.asarray(guard) > 0.5

    correction64 = gamma_64 * (truth_64 - k5_64)
    raw64 = k5_64 + correction64

    variants["V0_float64_base_plus_gamma_residual"] = raw64
    variants["V1_float64_clip01"] = np.clip(raw64, 0.0, 1.0)
    variants["V2_float64_guard_preserve_K5"] = np.where(guard_bool, k5_64, raw64)
    variants["V3_float64_guard_then_clip"] = np.clip(
        np.where(guard_bool, k5_64, raw64), 0.0, 1.0
    )

    # Explicit float32 operation order
    k5_32 = np.asarray(k5, dtype=np.float32)
    truth_32 = np.asarray(truth, dtype=np.float32)
    gamma_32 = np.asarray(gamma, dtype=np.float32)

    residual32 = np.subtract(truth_32, k5_32, dtype=np.float32)
    corr32 = np.multiply(gamma_32, residual32, dtype=np.float32)
    raw32 = np.add(k5_32, corr32, dtype=np.float32)

    variants["V4_float32_base_plus_gamma_residual"] = raw32
    variants["V5_float32_clip01"] = np.clip(raw32, np.float32(0.0), np.float32(1.0)).astype(np.float32)
    variants["V6_float32_guard_preserve_K5"] = np.where(guard_bool, k5_32, raw32).astype(np.float32)
    variants["V7_float32_guard_then_clip"] = np.clip(
        np.where(guard_bool, k5_32, raw32),
        np.float32(0.0),
        np.float32(1.0),
    ).astype(np.float32)

    # Serialization-equivalent: calculate float64 then persist float32
    variants["V8_float64_then_float32"] = raw64.astype(np.float32)
    variants["V9_float64_clip_then_float32"] = np.clip(raw64, 0.0, 1.0).astype(np.float32)

    variant_rows = []
    for name, arr in variants.items():
        m = metrics(arr, target)
        variant_rows.append({
            "variant": name,
            "dtype": str(np.asarray(arr).dtype),
            "sha256": sha256_array(np.asarray(arr)),
            **m,
            "exact_hash_match": sha256_array(np.asarray(arr)) == target_sha,
        })

    variant_rows.sort(
        key=lambda r: (
            float(r["Linf"]),
            float(r["L1"]),
            float(r["L2"]),
        )
    )
    save_csv(VARIANT_TABLE, variant_rows)

    # -------------------------------------------------------------------------
    # Precision-aware closure
    # -------------------------------------------------------------------------

    half_ulp, envelope = float32_envelope(target)

    best = variant_rows[0]
    second = variant_rows[1] if len(variant_rows) > 1 else None

    best_linf = float(best["Linf"])
    second_linf = float(second["Linf"]) if second else float("inf")
    unique_margin = second_linf - best_linf

    precision_pass = best_linf <= envelope

    # Multiple mathematically equivalent variants may tie exactly. Uniqueness is
    # therefore defined at the NUMERICAL OUTPUT HASH level, not variant label.
    passing_hashes = sorted(set(
        r["sha256"] for r in variant_rows
        if float(r["Linf"]) <= envelope
    ))
    unique_output = len(passing_hashes) == 1

    precision_rows = [{
        "target_dtype": str(target.dtype),
        "half_ulp_max": half_ulp,
        "derived_envelope": envelope,
        "best_variant": best["variant"],
        "best_L1": best["L1"],
        "best_L2": best["L2"],
        "best_Linf": best["Linf"],
        "best_exact_hash_match": best["exact_hash_match"],
        "second_best_Linf": second_linf,
        "variant_margin": unique_margin,
        "passing_output_hash_count": len(passing_hashes),
        "unique_numerical_output": unique_output,
        "precision_aware_pass": precision_pass,
    }]
    save_csv(PRECISION_TABLE, precision_rows)

    # -------------------------------------------------------------------------
    # Direction / bounds audit
    # -------------------------------------------------------------------------

    best_arr = np.asarray(variants[best["variant"]], dtype=np.float64)
    k5_cmp = np.asarray(k5, dtype=np.float64)
    truth_cmp = np.asarray(truth, dtype=np.float64)

    initial_residual = truth_cmp - k5_cmp
    final_residual = truth_cmp - best_arr

    # A truth-directed correction should not reverse sign unless already zero.
    direction_ok = np.all(
        (np.abs(initial_residual) <= 1e-12)
        | (np.sign(final_residual) == np.sign(initial_residual))
        | (np.abs(final_residual) <= 1e-12)
    )

    no_overshoot = np.all(
        np.abs(final_residual) <= np.abs(initial_residual) + 1e-7
    )

    lower_bound = float(np.nanmin(target))
    upper_bound = float(np.nanmax(target))

    replay_lower = float(np.nanmin(best_arr))
    replay_upper = float(np.nanmax(best_arr))

    bounds_ok = (
        replay_lower >= min(lower_bound, 0.0) - 1e-7
        and replay_upper <= max(upper_bound, 1.0) + 1e-7
    )

    guard_delta = np.abs(best_arr[guard_bool] - k5_cmp[guard_bool])
    guard_linf = float(np.max(guard_delta)) if guard_delta.size else 0.0

    physics_rows = [{
        "truth_direction_preserved": bool(direction_ok),
        "no_truth_overshoot": bool(no_overshoot),
        "replay_min": replay_lower,
        "replay_max": replay_upper,
        "target_min": lower_bound,
        "target_max": upper_bound,
        "bounds_preserved": bool(bounds_ok),
        "guard_point_count": int(np.sum(guard_bool)),
        "guard_vs_K5_Linf": guard_linf,
    }]
    save_csv(PHYSICS_TABLE, physics_rows)

    # -------------------------------------------------------------------------
    # Final gates
    # -------------------------------------------------------------------------

    gates = [
        ("R23_bound_target_status_reproduced", True),
        ("bound_key_is_L2_independent_100", bound_key == "L2_independent_100"),
        ("bound_target_sha256_reproduced", target_hash_match),
        ("authoritative_model_sha256_reproduced", model_hash_match),
        ("K5_100_input_loaded", True),
        ("truth100_input_loaded", True),
        ("L2_gamma_independent_input_loaded", True),
        ("guard_mask_input_loaded", True),
        ("deterministic_replay_variants_evaluated", len(variant_rows) > 0),
        ("precision_aware_closure", precision_pass),
        ("unique_numerical_replay_output", unique_output),
        ("truth_direction_preserved", bool(direction_ok)),
        ("no_truth_overshoot", bool(no_overshoot)),
        ("saturation_bounds_preserved", bool(bounds_ok)),
        ("no_250_500_1000d_state_generated", True),
        ("no_training_performed", True),
        ("no_scalar_anchoring_or_fitting", True),
        ("no_SG7E_threshold_change", True),
        ("no_SG7E_performance_gate_evaluated", True),
    ]

    gate_rows = [
        {"gate": name, "passed": bool(passed)}
        for name, passed in gates
    ]
    save_csv(GATE_TABLE, gate_rows)

    failed = [name for name, passed in gates if not passed]

    if not failed:
        status = "L2_100D_DETERMINISTIC_REPLAY_VALIDATED"
        diagnosis = "BOUND_L2_INDEPENDENT_100_REPRODUCED_WITH_PRECISION_AWARE_DETERMINISTIC_CLOSURE"
        recommendation = (
            "The nominated L2_independent_100 state is deterministically reproduced from the "
            "persisted K5/truth/gamma/guard deployment inputs within the precision-aware float32 "
            "closure contract, with truth direction and bounds preserved. The 100-day replay "
            "operator is validated. Proceed to controlled no-training regeneration of the full "
            "100/250/500/1000-day L2 state set using the same frozen model, transforms, and "
            "correction operator."
        )
        next_milestone = (
            "V15-SG7E1R25 — Controlled Four-Time L2 State Regeneration"
        )
    else:
        status = "L2_100D_DETERMINISTIC_REPLAY_VALIDATION_FAILED"
        diagnosis = "BOUND_100D_STATE_DOES_NOT_CLOSE_UNDER_CURRENT_DETERMINISTIC_REPLAY_CONTRACT"
        recommendation = (
            "Do not generate 250/500/1000-day states. Audit only the failed R24 replay gates, "
            "with emphasis on exact operation order, guard semantics, and float32 serialization. "
            "Do not recalibrate gamma, change the guard, alter model weights, or relax tolerance."
        )
        next_milestone = (
            "V15-SG7E1R25 — Bound 100-Day Replay Failure / Operation-Order Audit"
        )

    decision_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "target_key": bound_key,
        "target_sha256": target_sha,
        "model_sha256": actual_model_sha,
        "best_variant": best["variant"],
        "best_replay_sha256": best["sha256"],
        "best_L1": best["L1"],
        "best_L2": best["L2"],
        "best_Linf": best["Linf"],
        "precision_envelope": envelope,
        "precision_pass": precision_pass,
        "unique_numerical_output": unique_output,
        "failed_gates": ";".join(failed),
        "next_milestone": next_milestone,
    }]
    save_csv(DECISION_TABLE, decision_rows)

    np.savez_compressed(
        NUMERICAL_FILE,
        target_L2_independent_100=np.asarray(target),
        replay_100d=np.asarray(variants[best["variant"]]),
        K5_100=np.asarray(k5),
        truth100=np.asarray(truth),
        L2_gamma_independent=np.asarray(gamma),
        guard_mask=np.asarray(guard),
        target_time_days=np.array([TARGET_TIME_DAYS], dtype=np.float64),
        best_variant=np.array([best["variant"]]),
        precision_envelope=np.array([envelope], dtype=np.float64),
    )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R24",
        "status": status,
        "diagnosis": diagnosis,
        "target": {
            "key": bound_key,
            "sha256": target_sha,
            "dtype": str(target.dtype),
            "shape": list(target.shape),
            "time_days": TARGET_TIME_DAYS,
        },
        "model": {
            "path": str(model_path),
            "sha256": actual_model_sha,
            "hash_match": model_hash_match,
            "immutable": True,
        },
        "replay": {
            "best_variant": best["variant"],
            "sha256": best["sha256"],
            "L1": float(best["L1"]),
            "L2": float(best["L2"]),
            "Linf": float(best["Linf"]),
            "precision_envelope": envelope,
            "precision_pass": precision_pass,
            "unique_numerical_output": unique_output,
        },
        "failed_gates": failed,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_recalibrated": False,
            "guard_changed": False,
            "scalar_anchoring_used": False,
            "posthoc_alignment_used": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
            "SG7E_threshold_changed": False,
            "SG7E_gate_evaluated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R24",
        "status": status,
        "diagnosis": diagnosis,
        "replay_validated": not failed,
        "target_key": bound_key,
        "target_sha256": target_sha,
        "best_variant": best["variant"],
        "best_Linf": float(best["Linf"]),
        "precision_envelope": envelope,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("BOUND 100-DAY TARGET")
    print(f"  Key                     : {bound_key}")
    print(f"  SHA-256                 : {target_sha}")
    print(f"  Hash reproduced         : {target_hash_match}")
    print(f"  Shape                   : {target.shape}")
    print(f"  Dtype                   : {target.dtype}")

    print("\nAUTHORITATIVE MODEL")
    print(f"  File                    : {model_path.name}")
    print(f"  SHA-256                 : {actual_model_sha}")
    print(f"  Hash reproduced         : {model_hash_match}")

    print("\nDETERMINISTIC REPLAY INPUTS")
    for row in input_rows:
        print(
            f"  {row['key']:24s} | {row['dtype']:8s} | "
            f"{row['sha256'][:16]} | "
            f"range={row['min']:.6f}->{row['max']:.6f}"
        )

    print("\nTOP REPLAY EXPRESSIONS")
    for row in variant_rows[:10]:
        print(
            f"  {row['variant']:42s} | "
            f"L1={float(row['L1']):.6e} | "
            f"L2={float(row['L2']):.6e} | "
            f"Linf={float(row['Linf']):.6e} | "
            f"exact={row['exact_hash_match']}"
        )

    print("\nPRECISION-AWARE CLOSURE")
    print(f"  Best variant            : {best['variant']}")
    print(f"  Best Linf               : {best_linf:.6e}")
    print(f"  Float32 half-ULP max    : {half_ulp:.6e}")
    print(f"  Closure envelope        : {envelope:.6e}")
    print(f"  Precision pass          : {precision_pass}")
    print(f"  Unique output hash      : {unique_output}")

    print("\nREPLAY PHYSICS / DIRECTION")
    print(f"  Truth direction         : {direction_ok}")
    print(f"  No truth overshoot      : {no_overshoot}")
    print(f"  Bounds preserved        : {bounds_ok}")
    print(f"  Guard vs K5 Linf        : {guard_linf:.6e}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R24 FINAL REPLAY GATES")
    print("=" * 78)
    for name, passed in gates:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    if failed:
        print("\nFAILED AUTHORITATIVE GATES")
        for g in failed:
            print(f"  {g}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    for p in (
        IDENTITY_TABLE,
        INPUT_TABLE,
        SOURCE_TABLE,
        VARIANT_TABLE,
        PRECISION_TABLE,
        PHYSICS_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R24 BOUND L2 100-DAY DETERMINISTIC REPLAY / CLOSURE VALIDATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
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
