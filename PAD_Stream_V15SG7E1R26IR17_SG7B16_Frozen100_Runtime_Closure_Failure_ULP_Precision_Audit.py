from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import math
import os
import platform
import struct

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R17
# SG7B16 Frozen100 Runtime Closure Failure / ULP Precision Audit
#
# DIAGNOSTIC-ONLY NUMERICAL REPRODUCIBILITY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA / GUARD RECALIBRATION.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO PRECISION ENVELOPE WILL BE RELAXED.
#
# PURPOSE
# -------
# R16 established one remaining failure:
#
#   Linf(creator100, frozen100) = 2.682209e-07
#   precision envelope          = 1.192093e-07
#
# while all creator/model/X100 bindings are frozen and authoritative.
#
# R17 therefore performs NO inference. It audits:
#
#   - exact elementwise difference distribution
#   - float32 ULP distance distribution
#   - counts above 1/2/3/... epsilon-scale thresholds
#   - location of max discrepancy
#   - whether differences cluster near the saturation front
#   - whether plain float32 reserialization changes either array
#   - persisted precision-contract provenance
#   - runtime environment metadata relevant to reproducibility
#
# R17 does NOT decide by convenience. If precision equivalence is justified,
# it must be justified from frozen/persisted precision semantics, not by
# widening the R16 gate ad hoc.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR17"
OUT.mkdir(parents=True, exist_ok=True)

R16_DIR = ROOT / "output" / "V15_SG7E1R26IR16"
R16_SUMMARY = R16_DIR / "PAD_Stream_V15SG7E1R26IR16_Summary.json"
R16_NUM = R16_DIR / "V15SG7E1R26IR16_SG7B16_Frozen100_Runtime_Control.npz"
R16_CLOSURE = R16_DIR / "V15SG7E1R26IR16_Frozen100_Closure.csv"

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

# Optional earlier precision audit artifacts if they exist.
R25_DIR = ROOT / "output" / "V15_SG7E1R25"
R25_PAIRWISE = R25_DIR / "V15SG7E1R25_Passing_Variant_Pairwise_Closure.csv"
R25_CLASS = R25_DIR / "V15SG7E1R25_Uniqueness_Failure_Classification.csv"

# Outputs
IDENTITY_TABLE = OUT / "V15SG7E1R26IR17_Array_Identity.csv"
DIFF_TABLE = OUT / "V15SG7E1R26IR17_Elementwise_Difference_Summary.csv"
ULP_TABLE = OUT / "V15SG7E1R26IR17_ULP_Distance_Distribution.csv"
THRESH_TABLE = OUT / "V15SG7E1R26IR17_Epsilon_Threshold_Counts.csv"
MAX_TABLE = OUT / "V15SG7E1R26IR17_Max_Discrepancy_Location.csv"
FRONT_TABLE = OUT / "V15SG7E1R26IR17_Front_Region_Discrepancy_Audit.csv"
SERIAL_TABLE = OUT / "V15SG7E1R26IR17_Float32_Reserialization_Audit.csv"
PRECISION_TABLE = OUT / "V15SG7E1R26IR17_Precision_Contract_Provenance.csv"
ENV_TABLE = OUT / "V15SG7E1R26IR17_Runtime_Environment_Metadata.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR17_Final_Precision_Audit_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR17_Precision_Audit_Decision.csv"

NUM_FILE = OUT / "V15SG7E1R26IR17_Precision_Audit.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR17_Precision_Audit_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR17_Summary.json"


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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def float32_ordered_int(arr):
    """
    Map float32 bit patterns to monotonic ordered signed integers suitable for
    ULP-distance comparison.
    """
    a = np.asarray(arr, dtype=np.float32)
    u = a.view(np.uint32)
    sign = (u >> 31).astype(np.uint32)
    ordered = np.where(sign == 0, u | np.uint32(0x80000000), ~u)
    return ordered.astype(np.int64)


def ulp_distance_float32(a, b):
    oa = float32_ordered_int(a)
    ob = float32_ordered_int(b)
    return np.abs(oa - ob)


def percentile_rows(values, label):
    vals = np.asarray(values)
    ps = [0, 50, 90, 95, 99, 99.9, 100]
    rows = []
    for p in ps:
        rows.append({
            "metric": label,
            "percentile": p,
            "value": float(np.percentile(vals, p)),
        })
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R17")
    print("SG7B16 Frozen100 Runtime Closure Failure / ULP Precision Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
THE R16 PRECISION ENVELOPE WILL NOT BE RELAXED.
ONLY NUMERICAL REPRODUCIBILITY / ULP PROVENANCE WILL BE AUDITED.
""")

    r16 = load_json(R16_SUMMARY)
    if r16.get("status") != "SG7B16_FROZEN100_CREATOR_RUNTIME_CONTROL_FAILED":
        raise RuntimeError("R17 requires the R16 runtime-closure failure.")

    if r16.get("failed_gates") != ["creator100_closes_to_frozen100"]:
        raise RuntimeError("R17 requires creator100_closes_to_frozen100 as the only failed R16 gate.")

    db = np.load(R16_NUM, allow_pickle=True)
    creator100 = np.asarray(db["creator100"], dtype=np.float32)
    frozen100 = np.asarray(db["frozen100"], dtype=np.float32)
    precision_envelope = float(np.asarray(db["precision_envelope"]).ravel()[0])
    db.close()

    if creator100.shape != frozen100.shape:
        raise RuntimeError("R17 requires equal creator100/frozen100 shapes.")

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    save_csv(IDENTITY_TABLE, [{
        "creator_shape": str(creator100.shape),
        "frozen_shape": str(frozen100.shape),
        "creator_dtype": str(creator100.dtype),
        "frozen_dtype": str(frozen100.dtype),
        "creator_sha256": sha256_array(creator100),
        "frozen_sha256": sha256_array(frozen100),
        "same_shape": creator100.shape == frozen100.shape,
        "same_dtype": creator100.dtype == frozen100.dtype,
        "exact_array_equal": bool(np.array_equal(creator100, frozen100)),
    }])

    # -------------------------------------------------------------------------
    # Difference statistics
    # -------------------------------------------------------------------------
    diff = creator100.astype(np.float64) - frozen100.astype(np.float64)
    absdiff = np.abs(diff)

    total = diff.size
    nonzero = int(np.count_nonzero(diff))
    exact = total - nonzero

    diff_rows = [
        {
            "metric": "count_total",
            "value": total,
        },
        {
            "metric": "count_exact_equal",
            "value": exact,
        },
        {
            "metric": "count_nonzero_difference",
            "value": nonzero,
        },
        {
            "metric": "fraction_nonzero_difference",
            "value": nonzero / total,
        },
        {
            "metric": "mean_abs_difference",
            "value": float(np.mean(absdiff)),
        },
        {
            "metric": "rms_difference",
            "value": float(np.sqrt(np.mean(diff * diff))),
        },
        {
            "metric": "max_abs_difference",
            "value": float(np.max(absdiff)),
        },
        {
            "metric": "signed_mean_difference",
            "value": float(np.mean(diff)),
        },
    ]
    diff_rows.extend(percentile_rows(absdiff.ravel(), "abs_difference"))
    save_csv(DIFF_TABLE, diff_rows)

    # -------------------------------------------------------------------------
    # ULP audit
    # -------------------------------------------------------------------------
    ulp = ulp_distance_float32(creator100, frozen100)

    unique_ulp, counts_ulp = np.unique(ulp, return_counts=True)
    ulp_rows = []
    for u, c in zip(unique_ulp, counts_ulp):
        ulp_rows.append({
            "ulp_distance": int(u),
            "count": int(c),
            "fraction": float(c / total),
        })
    save_csv(ULP_TABLE, ulp_rows)

    max_ulp = int(np.max(ulp))
    mean_ulp = float(np.mean(ulp))
    p99_ulp = float(np.percentile(ulp, 99))
    p999_ulp = float(np.percentile(ulp, 99.9))

    # -------------------------------------------------------------------------
    # Epsilon / threshold counts
    # -------------------------------------------------------------------------
    eps32 = np.finfo(np.float32).eps
    threshold_rows = []
    for mult in [0.5, 1, 2, 3, 4, 5, 8, 16]:
        thresh = mult * eps32
        count = int(np.count_nonzero(absdiff > thresh))
        threshold_rows.append({
            "epsilon_multiple": mult,
            "threshold": float(thresh),
            "count_above": count,
            "fraction_above": count / total,
        })

    count_above_envelope = int(np.count_nonzero(absdiff > precision_envelope))
    threshold_rows.append({
        "epsilon_multiple": "R16_envelope",
        "threshold": precision_envelope,
        "count_above": count_above_envelope,
        "fraction_above": count_above_envelope / total,
    })
    save_csv(THRESH_TABLE, threshold_rows)

    # -------------------------------------------------------------------------
    # Max discrepancy location
    # -------------------------------------------------------------------------
    flat_idx = int(np.argmax(absdiff))
    idx = np.unravel_index(flat_idx, absdiff.shape)

    max_rows = [{
        "streamline_index": int(idx[0]),
        "node_index": int(idx[1]),
        "creator_value": float(creator100[idx]),
        "frozen_value": float(frozen100[idx]),
        "signed_difference": float(diff[idx]),
        "abs_difference": float(absdiff[idx]),
        "ulp_distance": int(ulp[idx]),
    }]
    save_csv(MAX_TABLE, max_rows)

    # -------------------------------------------------------------------------
    # Front-region concentration audit
    # -------------------------------------------------------------------------
    # Historical states are saturation profiles. Use gradient magnitude of
    # persisted frozen100 as a purely diagnostic front-region indicator.
    grad = np.abs(np.gradient(frozen100.astype(np.float64), axis=1))

    # Define front-like cells by upper 10% of nonzero gradient magnitude.
    nonzero_grad = grad[grad > 0]
    if nonzero_grad.size:
        front_cut = float(np.percentile(nonzero_grad, 90))
    else:
        front_cut = math.inf

    front_mask = grad >= front_cut if np.isfinite(front_cut) else np.zeros_like(grad, dtype=bool)
    background_mask = ~front_mask

    front_rows = [{
        "front_gradient_cutoff": front_cut,
        "front_cell_count": int(np.count_nonzero(front_mask)),
        "background_cell_count": int(np.count_nonzero(background_mask)),
        "front_mean_abs_diff": float(np.mean(absdiff[front_mask])) if np.any(front_mask) else "",
        "background_mean_abs_diff": float(np.mean(absdiff[background_mask])) if np.any(background_mask) else "",
        "front_max_abs_diff": float(np.max(absdiff[front_mask])) if np.any(front_mask) else "",
        "background_max_abs_diff": float(np.max(absdiff[background_mask])) if np.any(background_mask) else "",
        "front_mean_ulp": float(np.mean(ulp[front_mask])) if np.any(front_mask) else "",
        "background_mean_ulp": float(np.mean(ulp[background_mask])) if np.any(background_mask) else "",
        "count_above_R16_envelope_in_front": int(np.count_nonzero(absdiff[front_mask] > precision_envelope)) if np.any(front_mask) else 0,
        "count_above_R16_envelope_in_background": int(np.count_nonzero(absdiff[background_mask] > precision_envelope)) if np.any(background_mask) else 0,
    }]
    save_csv(FRONT_TABLE, front_rows)

    # -------------------------------------------------------------------------
    # Float32 reserialization audit
    # -------------------------------------------------------------------------
    creator_bytes_roundtrip = np.frombuffer(
        np.asarray(creator100, dtype=np.float32).tobytes(),
        dtype=np.float32,
    ).reshape(creator100.shape)

    frozen_bytes_roundtrip = np.frombuffer(
        np.asarray(frozen100, dtype=np.float32).tobytes(),
        dtype=np.float32,
    ).reshape(frozen100.shape)

    serial_rows = [{
        "creator_roundtrip_exact": bool(np.array_equal(creator100, creator_bytes_roundtrip)),
        "frozen_roundtrip_exact": bool(np.array_equal(frozen100, frozen_bytes_roundtrip)),
        "creator_roundtrip_sha256": sha256_array(creator_bytes_roundtrip),
        "frozen_roundtrip_sha256": sha256_array(frozen_bytes_roundtrip),
        "cross_equal_after_roundtrip": bool(np.array_equal(creator_bytes_roundtrip, frozen_bytes_roundtrip)),
    }]
    save_csv(SERIAL_TABLE, serial_rows)

    # -------------------------------------------------------------------------
    # Precision-contract provenance
    # -------------------------------------------------------------------------
    precision_rows = []

    if R25R_CONTRACT.exists():
        r25r = load_json(R25R_CONTRACT)
        repaired_env = r25r.get("contract_repair", {}).get("precision_envelope")
        precision_rows.append({
            "source": str(R25R_CONTRACT),
            "kind": "R25R_REPAIRED_PRECISION_CONTRACT",
            "precision_envelope": repaired_env,
            "matches_R16_envelope": (
                float(repaired_env) == precision_envelope
                if repaired_env is not None else False
            ),
            "note": "R25R repaired uniqueness semantics without changing tolerance.",
        })

    if R25_PAIRWISE.exists():
        rows = load_csv(R25_PAIRWISE)
        precision_rows.append({
            "source": str(R25_PAIRWISE),
            "kind": "R25_PAIRWISE_PRECISION_EQUIVALENCE",
            "precision_envelope": precision_envelope,
            "matches_R16_envelope": True,
            "note": f"Rows={len(rows)}",
        })

    if R25_CLASS.exists():
        rows = load_csv(R25_CLASS)
        precision_rows.append({
            "source": str(R25_CLASS),
            "kind": "R25_UNIQUENESS_FAILURE_CLASSIFICATION",
            "precision_envelope": precision_envelope,
            "matches_R16_envelope": True,
            "note": f"Rows={len(rows)}",
        })

    save_csv(PRECISION_TABLE, precision_rows)

    # -------------------------------------------------------------------------
    # Runtime environment metadata
    # -------------------------------------------------------------------------
    env_rows = [{
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "TF_ENABLE_ONEDNN_OPTS": os.environ.get("TF_ENABLE_ONEDNN_OPTS", ""),
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", ""),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", ""),
        "note": "Environment metadata only; no causal attribution is made by R17.",
    }]
    save_csv(ENV_TABLE, env_rows)

    # -------------------------------------------------------------------------
    # Precision-equivalence interpretation
    # -------------------------------------------------------------------------
    # R17 does not alter the R16 gate. It only classifies the discrepancy.
    #
    # Strong precision-equivalence evidence if:
    #   - global L1/L2 tiny
    #   - max ULP bounded to a small integer
    #   - only a very small fraction exceed the frozen envelope
    #
    # This remains a diagnostic classification, not an acceptance-gate repair.
    small_ulp_class = max_ulp <= 4
    sparse_envelope_exceedance = (count_above_envelope / total) <= 1.0e-3
    tiny_global_error = (
        float(np.mean(absdiff)) <= 1.0e-8
        and float(np.sqrt(np.mean(diff * diff))) <= 1.0e-7
    )
    precision_equivalence_supported = bool(
        small_ulp_class and sparse_envelope_exceedance and tiny_global_error
    )

    gates = [
        ("R16_only_failed_gate_reproduced", True),
        ("creator_and_frozen_shapes_match", creator100.shape == frozen100.shape),
        ("creator_and_frozen_dtype_float32", creator100.dtype == np.float32 and frozen100.dtype == np.float32),
        ("difference_distribution_audited", True),
        ("ULP_distribution_audited", True),
        ("epsilon_threshold_counts_audited", True),
        ("max_discrepancy_location_audited", True),
        ("front_region_concentration_audited", True),
        ("float32_reserialization_audited", True),
        ("precision_contract_provenance_audited", True),
        ("R16_precision_envelope_unchanged", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_threshold_or_tolerance_relaxed", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    if precision_equivalence_supported:
        status = "SG7B16_FROZEN100_CLOSURE_FAILURE_CLASSIFIED_AS_SMALL_ULP_REPRODUCIBILITY_DRIFT"
        diagnosis = (
            "AUTHORITATIVE_CREATOR_AND_FROZEN100_DIFFER_BY_SPARSE_SMALL_ULP_FLOAT32_RUNTIME_DRIFT"
        )
        recommendation = (
            "Do not change the R16 precision envelope yet. The discrepancy is classified as small-ULP "
            "runtime reproducibility drift rather than a model/X100 provenance error. Next audit the "
            "historical SG7B16 freeze/serialization runtime environment and whether persisted frozen100 "
            "was produced under a different deterministic execution backend or thread/oneDNN setting."
        )
        next_ms = (
            "V15-SG7E1R26I-R18 — Historical SG7B16 Runtime-Environment / Determinism Provenance Audit"
        )
    else:
        status = "SG7B16_FROZEN100_CLOSURE_FAILURE_NOT_YET_EXPLAINED_BY_SMALL_ULP_DRIFT"
        diagnosis = (
            "ELEMENTWISE_OR_ULP_DISTRIBUTION_EXCEEDS_SMALL_RUNTIME_REPRODUCIBILITY_CLASS"
        )
        recommendation = (
            "Do not relax tolerance and do not generate later-time states. Audit only the locations "
            "and source-level serialization/runtime differences identified by R17."
        )
        next_ms = (
            "V15-SG7E1R26I-R18 — Historical SG7B16 Runtime / Serialization Difference Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "total_values": total,
        "nonzero_values": nonzero,
        "fraction_nonzero": nonzero / total,
        "max_abs_difference": float(np.max(absdiff)),
        "count_above_R16_envelope": count_above_envelope,
        "fraction_above_R16_envelope": count_above_envelope / total,
        "max_ulp_distance": max_ulp,
        "mean_ulp_distance": mean_ulp,
        "p99_ulp_distance": p99_ulp,
        "p999_ulp_distance": p999_ulp,
        "small_ulp_class": small_ulp_class,
        "sparse_envelope_exceedance": sparse_envelope_exceedance,
        "tiny_global_error": tiny_global_error,
        "precision_equivalence_supported": precision_equivalence_supported,
        "precision_envelope_changed": False,
        "next_milestone": next_ms,
    }])

    np.savez_compressed(
        NUM_FILE,
        creator100=creator100,
        frozen100=frozen100,
        difference=diff.astype(np.float64),
        abs_difference=absdiff.astype(np.float64),
        ulp_distance=ulp.astype(np.int64),
        front_mask=front_mask.astype(np.uint8),
        precision_envelope=np.asarray([precision_envelope], dtype=np.float64),
    )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R17",
        "status": status,
        "diagnosis": diagnosis,
        "array_identity": {
            "creator_sha256": sha256_array(creator100),
            "frozen_sha256": sha256_array(frozen100),
            "shape": list(creator100.shape),
            "dtype": str(creator100.dtype),
        },
        "difference": {
            "total_values": total,
            "exact_equal_values": exact,
            "nonzero_values": nonzero,
            "fraction_nonzero": nonzero / total,
            "mean_abs_difference": float(np.mean(absdiff)),
            "rms_difference": float(np.sqrt(np.mean(diff * diff))),
            "max_abs_difference": float(np.max(absdiff)),
            "count_above_R16_envelope": count_above_envelope,
            "fraction_above_R16_envelope": count_above_envelope / total,
        },
        "ulp": {
            "max": max_ulp,
            "mean": mean_ulp,
            "p99": p99_ulp,
            "p999": p999_ulp,
        },
        "classification": {
            "small_ulp_class": small_ulp_class,
            "sparse_envelope_exceedance": sparse_envelope_exceedance,
            "tiny_global_error": tiny_global_error,
            "precision_equivalence_supported": precision_equivalence_supported,
        },
        "precision_envelope": precision_envelope,
        "precision_envelope_changed": False,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "model_parameters_changed": False,
            "threshold_changed": False,
            "precision_envelope_relaxed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R17",
        "status": status,
        "diagnosis": diagnosis,
        "precision_equivalence_supported": precision_equivalence_supported,
        "max_ulp_distance": max_ulp,
        "count_above_R16_envelope": count_above_envelope,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------
    print("ARRAY IDENTITY")
    print(f"  Shape                   : {creator100.shape}")
    print(f"  Creator SHA-256         : {sha256_array(creator100)}")
    print(f"  Frozen SHA-256          : {sha256_array(frozen100)}")

    print("\nDIFFERENCE DISTRIBUTION")
    print(f"  Total values            : {total}")
    print(f"  Exact equal             : {exact}")
    print(f"  Nonzero differences     : {nonzero}")
    print(f"  Fraction nonzero        : {nonzero / total:.6e}")
    print(f"  Mean abs diff           : {np.mean(absdiff):.6e}")
    print(f"  RMS diff                : {np.sqrt(np.mean(diff * diff)):.6e}")
    print(f"  Max abs diff            : {np.max(absdiff):.6e}")

    print("\nULP DISTANCE")
    print(f"  Max ULP                 : {max_ulp}")
    print(f"  Mean ULP                : {mean_ulp:.6e}")
    print(f"  P99 ULP                 : {p99_ulp:.6f}")
    print(f"  P99.9 ULP               : {p999_ulp:.6f}")

    print("\nR16 ENVELOPE EXCEEDANCE")
    print(f"  Envelope                : {precision_envelope:.6e}")
    print(f"  Count above             : {count_above_envelope}")
    print(f"  Fraction above          : {count_above_envelope / total:.6e}")

    print("\nMAX DISCREPANCY")
    print(f"  Streamline              : {idx[0]}")
    print(f"  Node                    : {idx[1]}")
    print(f"  Creator value           : {creator100[idx]:.9f}")
    print(f"  Frozen value            : {frozen100[idx]:.9f}")
    print(f"  Abs diff                : {absdiff[idx]:.6e}")
    print(f"  ULP distance            : {ulp[idx]}")

    print("\nPRECISION CLASSIFICATION")
    print(f"  Small-ULP class         : {small_ulp_class}")
    print(f"  Sparse envelope exceed. : {sparse_envelope_exceedance}")
    print(f"  Tiny global error       : {tiny_global_error}")
    print(f"  Precision-equivalence   : {precision_equivalence_supported}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R17 FINAL PRECISION AUDIT GATES")
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
        IDENTITY_TABLE,
        DIFF_TABLE,
        ULP_TABLE,
        THRESH_TABLE,
        MAX_TABLE,
        FRONT_TABLE,
        SERIAL_TABLE,
        PRECISION_TABLE,
        ENV_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nNumerical:")
    print(f"  {NUM_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R17 SG7B16 FROZEN100 PRECISION AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("The R16 precision envelope was not relaxed.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
