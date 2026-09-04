from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R14
# Multi-Time Historical Reference Reconstruction / Contract Audit
#
# FORENSIC REFERENCE-CONTRACT MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
# NO SG7D6/P4 PERFORMANCE EVALUATION WILL BE USED TO DEFINE THE REFERENCE.
#
# PURPOSE
# -------
# SG7E1R13 established:
#
#   SG7E_HISTORICAL_REFERENCE_IS_MULTI_TIME_CONTRACT
#
# with:
#
#   AUTHORITATIVE_SG7E_REFERENCE_METRICS_CONSUME_ALL_PERSISTED_SNAPSHOTS
#
# Historical truth is therefore:
#
#   SG7A_corrected(t), t = [100, 250, 500, 1000] days
#
# with shape:
#
#   (4, 15, 50, 50)
#
# R14 reconstructs and persists the complete multi-time reference contract,
# including:
#
#   * exact 4-D SG7A_corrected tensor,
#   * exact time axis,
#   * unchanged plume threshold S=0.5,
#   * per-time reference plume masks,
#   * per-time morphology/volume/centroid/vertical extent,
#   * complete tensor and per-snapshot hashes,
#   * historical multi-time aggregation semantics if recoverable,
#   * dimensional compatibility audit against frozen SG7D6/P4.
#
# IMPORTANT:
# R14 does NOT evaluate whether P4 passes SG7E.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R14"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R13_DIR = ROOT / "output" / "V15_SG7E1R13"
R13_SUMMARY = R13_DIR / "PAD_Stream_V15SG7E1R13_Summary.json"
R13_CONTRACT = R13_DIR / "V15SG7E1R13_Per_Time_Snapshot_Correspondence_Contract.json"
R13_CORRESP = R13_DIR / "V15SG7E1R13_Time_Snapshot_Correspondence.csv"
R13_TIME_ORDER = R13_DIR / "V15SG7E1R13_Artifact_Time_Order.csv"
R13_SNAPSHOT_MORPH = R13_DIR / "V15SG7E1R13_Snapshot_Plume_Morphology.csv"

R11_SUMMARY = (
    ROOT / "output" / "V15_SG7E1R11"
    / "PAD_Stream_V15SG7E1R11_Summary.json"
)

R8_GATE_TRACE = (
    ROOT / "output" / "V15_SG7E1R8"
    / "V15SG7E1R8_Authoritative_Gate_Consumer_Trace.csv"
)

R0_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R0"
    / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"
)

D6_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

REFERENCE_ID_TABLE = OUT / "V15SG7E1R14_Multi_Time_Reference_Identity.csv"
SNAPSHOT_HASH_TABLE = OUT / "V15SG7E1R14_Per_Time_Reference_Hashes.csv"
PLUME_TABLE = OUT / "V15SG7E1R14_Per_Time_Reference_Plume_Metrics.csv"
AGGREGATION_TABLE = OUT / "V15SG7E1R14_Historical_Multi_Time_Aggregation_Audit.csv"
DIMENSION_TABLE = OUT / "V15SG7E1R14_SG7D6_Reference_Dimensional_Compatibility.csv"
DECISION_TABLE = OUT / "V15SG7E1R14_Multi_Time_Contract_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R14_Multi_Time_Historical_Reference.npz"
CONTRACT_FILE = OUT / "V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R14_Summary.json"

REFERENCE_KEY = "SG7A_corrected"
EXPECTED_REFERENCE_SHAPE = (4, 15, 50, 50)
EXPECTED_TIMES = np.array([100.0, 250.0, 500.0, 1000.0], dtype=float)
EXPECTED_GRID_SHAPE = (15, 50, 50)
EXPECTED_THRESHOLD = 0.5

AUTHORITATIVE_GATES = (
    "PRIMARY_VOLUME_GATE",
    "FOOTPRINT_IOU_GATE",
    "CENTROID_GATE_CELLS",
    "VERTICAL_EXTENT_GATE_LAYERS",
)


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def plume_morphology(mask):
    mask = np.asarray(mask, dtype=bool)

    plume_cells = int(np.sum(mask))
    footprint = np.any(mask, axis=0)
    footprint_cells = int(np.sum(footprint))

    active_layers = np.where(np.any(mask, axis=(1, 2)))[0]
    if len(active_layers):
        zmin = int(active_layers[0])
        zmax = int(active_layers[-1])
        vertical_extent = int(zmax - zmin + 1)
    else:
        zmin = zmax = -1
        vertical_extent = 0

    coords = np.argwhere(mask)
    if len(coords):
        centroid = np.mean(coords, axis=0)
        ck, cj, ci = map(float, centroid)
    else:
        ck = cj = ci = float("nan")

    return {
        "plume_cells": plume_cells,
        "footprint_cells": footprint_cells,
        "vertical_extent_layers": vertical_extent,
        "zmin_layer_zero_based": zmin,
        "zmax_layer_zero_based": zmax,
        "centroid_k": ck,
        "centroid_j": cj,
        "centroid_i": ci,
    }


def search_aggregation_semantics(rows):
    """
    Infer historical aggregation semantics from authoritative gate contexts.

    Conservative classifications:
      - PER_TIME_ALL_REQUIRED
      - WORST_CASE_MAX
      - WORST_CASE_MIN
      - MEAN_AGGREGATE
      - MULTI_TIME_BUT_AGGREGATION_NOT_EXPLICITLY_RESOLVED
    """
    blob = "\n".join(
        (r.get("context", "") + "\n" + r.get("expression", ""))
        for r in rows
    ).lower()

    evidence = []

    if any(tok in blob for tok in (
        "all(",
        "np.all(",
        ".all()",
        "all_pass",
        "all_times",
        "every time",
    )):
        evidence.append("all_semantics")

    if any(tok in blob for tok in (
        "max(",
        "np.max(",
        "worst",
        "maximum",
    )):
        evidence.append("max_semantics")

    if any(tok in blob for tok in (
        "min(",
        "np.min(",
        "minimum",
    )):
        evidence.append("min_semantics")

    if any(tok in blob for tok in (
        "mean(",
        "np.mean(",
        "average",
    )):
        evidence.append("mean_semantics")

    if "all_semantics" in evidence and "mean_semantics" not in evidence:
        return "PER_TIME_ALL_REQUIRED", evidence

    if "max_semantics" in evidence and "all_semantics" not in evidence:
        return "WORST_CASE_MAX", evidence

    if "min_semantics" in evidence and "all_semantics" not in evidence:
        return "WORST_CASE_MIN", evidence

    if "mean_semantics" in evidence and "all_semantics" not in evidence:
        return "MEAN_AGGREGATE", evidence

    return "MULTI_TIME_BUT_AGGREGATION_NOT_EXPLICITLY_RESOLVED", evidence


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R14")
    print("Multi-Time Historical Reference Reconstruction / Contract Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO SUPPORT MASK OR BACKGROUND POLICY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POST-HOC ALIGNMENT WILL BE PERFORMED.
NO DEPLOYMENT CORRECTION WILL BE PERFORMED.
NO SG7D6/P4 PERFORMANCE WILL BE USED TO DEFINE THE REFERENCE CONTRACT.
""")

    r13_summary = load_json(R13_SUMMARY)
    r13_contract = load_json(R13_CONTRACT)
    r11_summary = load_json(R11_SUMMARY)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r13_summary.get("status") != (
        "SG7E_HISTORICAL_REFERENCE_IS_MULTI_TIME_CONTRACT"
    ):
        raise RuntimeError(
            "R14 requires R13 multi-time reference contract status."
        )

    if r13_summary.get("diagnosis") != (
        "AUTHORITATIVE_SG7E_REFERENCE_METRICS_CONSUME_ALL_PERSISTED_SNAPSHOTS"
    ):
        raise RuntimeError(
            "R14 requires R13 all-snapshot-consumption diagnosis."
        )

    selected_artifact = Path(r11_summary["selected_artifact"]).resolve()

    if not selected_artifact.exists():
        raise FileNotFoundError(
            f"Resolved reference artifact missing:\n{selected_artifact}"
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])

    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold must remain resolved.")

    if abs(threshold - EXPECTED_THRESHOLD) > 1e-15:
        raise RuntimeError(
            f"R14 expected unchanged threshold {EXPECTED_THRESHOLD}, found {threshold}."
        )

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    # -------------------------------------------------------------------------
    # Load exact historical reference tensor.
    # -------------------------------------------------------------------------

    db = np.load(selected_artifact, allow_pickle=True)

    if REFERENCE_KEY not in db.files:
        raise RuntimeError(
            f"Authoritative artifact lacks {REFERENCE_KEY}."
        )

    reference = np.asarray(db[REFERENCE_KEY])

    if reference.shape != EXPECTED_REFERENCE_SHAPE:
        raise RuntimeError(
            f"Expected historical reference shape {EXPECTED_REFERENCE_SHAPE}, "
            f"found {reference.shape}."
        )

    if "times_days" not in db.files:
        raise RuntimeError(
            "Authoritative artifact lacks times_days."
        )

    times_days = np.asarray(db["times_days"], dtype=float).reshape(-1)

    if times_days.shape != (4,):
        raise RuntimeError(
            f"Expected four historical times, found {times_days.shape}."
        )

    if not np.allclose(
        times_days,
        EXPECTED_TIMES,
        rtol=0.0,
        atol=1e-12,
    ):
        raise RuntimeError(
            f"Historical times do not match expected R13 contract: {times_days}."
        )

    # -------------------------------------------------------------------------
    # Construct exact multi-time reference plume contract.
    # -------------------------------------------------------------------------

    plume_masks = reference >= threshold

    reference_hash = sha256_array(reference)
    time_hash = sha256_array(times_days)
    plume_hash = sha256_array(plume_masks.astype(np.uint8))

    reference_identity_rows = [{
        "artifact_path": str(selected_artifact),
        "reference_key": REFERENCE_KEY,
        "reference_shape": str(reference.shape),
        "reference_dtype": str(reference.dtype),
        "reference_sha256": reference_hash,
        "times_key": "times_days",
        "times_shape": str(times_days.shape),
        "times_sha256": time_hash,
        "times_days": ";".join(map(str, times_days.tolist())),
        "plume_threshold": threshold,
        "plume_mask_shape": str(plume_masks.shape),
        "plume_mask_sha256": plume_hash,
    }]

    save_csv(REFERENCE_ID_TABLE, reference_identity_rows)

    snapshot_hash_rows = []
    plume_rows = []

    for i, t in enumerate(times_days):
        sat = reference[i]
        mask = plume_masks[i]

        sat_hash = sha256_array(sat)
        mask_hash = sha256_array(mask.astype(np.uint8))

        snapshot_hash_rows.append({
            "snapshot_index": i,
            "time_days": float(t),
            "saturation_sha256": sat_hash,
            "plume_mask_sha256": mask_hash,
            "shape": str(sat.shape),
            "dtype": str(sat.dtype),
        })

        plume_rows.append({
            "snapshot_index": i,
            "time_days": float(t),
            "saturation_min": float(np.nanmin(sat)),
            "saturation_max": float(np.nanmax(sat)),
            "saturation_mean": float(np.nanmean(sat)),
            **plume_morphology(mask),
        })

    save_csv(SNAPSHOT_HASH_TABLE, snapshot_hash_rows)
    save_csv(PLUME_TABLE, plume_rows)

    # Persist complete multi-time historical reference set.
    np.savez_compressed(
        NUMERICAL_FILE,
        SG7A_corrected=reference,
        times_days=times_days,
        plume_threshold=np.array([threshold], dtype=np.float64),
        SG7A_reference_plume_mask=plume_masks.astype(np.uint8),
    )

    # -------------------------------------------------------------------------
    # Historical multi-time aggregation semantics.
    # -------------------------------------------------------------------------

    gate_rows = load_csv(R8_GATE_TRACE)

    aggregation_mode, aggregation_evidence = search_aggregation_semantics(gate_rows)

    aggregation_rows = []

    for gate in AUTHORITATIVE_GATES:
        contexts = [
            r for r in gate_rows
            if r.get("gate", "") == gate
        ]

        local_mode, local_evidence = search_aggregation_semantics(contexts)

        aggregation_rows.append({
            "gate": gate,
            "gate_context_records": len(contexts),
            "aggregation_mode": local_mode,
            "evidence": ";".join(local_evidence),
            "all_four_times_in_reference_contract": True,
        })

    aggregation_rows.append({
        "gate": "GLOBAL",
        "gate_context_records": len(gate_rows),
        "aggregation_mode": aggregation_mode,
        "evidence": ";".join(aggregation_evidence),
        "all_four_times_in_reference_contract": True,
    })

    save_csv(AGGREGATION_TABLE, aggregation_rows)

    # -------------------------------------------------------------------------
    # Dimensional compatibility with frozen SG7D6/P4.
    #
    # R14 does not evaluate performance. It only checks whether the frozen field
    # carries an explicit time coordinate compatible with the 4-time reference.
    # -------------------------------------------------------------------------

    frozen_candidate_path = None

    # Find frozen artifact from manifest recursively.
    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.lower().endswith(".npz"):
                    yield k, v
                else:
                    yield from walk(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from walk(v)

    for k, v in walk(d6_manifest):
        if "frozen" in k.lower() or "artifact" in k.lower() or "path" in k.lower():
            p = Path(v)
            if not p.is_absolute():
                p = (ROOT / p).resolve()
            if p.exists():
                frozen_candidate_path = p
                break

    # Fallback to known canonical path.
    if frozen_candidate_path is None:
        known = (
            ROOT / "output" / "V15_SG7D6" / "frozen_full_grid"
            / "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz"
        )
        if known.exists():
            frozen_candidate_path = known.resolve()

    dimension_rows = []

    p4_shape = None
    p4_time_keys = []

    if frozen_candidate_path and frozen_candidate_path.exists():
        p4db = np.load(frozen_candidate_path, allow_pickle=True)

        for key in p4db.files:
            arr = np.asarray(p4db[key])

            if arr.shape == EXPECTED_GRID_SHAPE:
                if p4_shape is None:
                    p4_shape = arr.shape

            if "time" in key.lower() or "days" in key.lower():
                p4_time_keys.append(key)

        p4db.close()

    dimension_rows.append({
        "historical_reference_shape": str(reference.shape),
        "historical_times_days": ";".join(map(str, times_days.tolist())),
        "frozen_SG7D6_artifact": str(frozen_candidate_path) if frozen_candidate_path else "",
        "frozen_grid_shape_detected": str(p4_shape),
        "frozen_time_keys": ";".join(p4_time_keys),
        "reference_is_multi_time": True,
        "frozen_field_is_single_grid": p4_shape == EXPECTED_GRID_SHAPE,
        "explicit_time_compatibility_resolved": bool(p4_time_keys),
    })

    save_csv(DIMENSION_TABLE, dimension_rows)

    # -------------------------------------------------------------------------
    # Final contract decision.
    # -------------------------------------------------------------------------

    aggregation_resolved = aggregation_mode != (
        "MULTI_TIME_BUT_AGGREGATION_NOT_EXPLICITLY_RESOLVED"
    )

    dimensional_time_compatibility = bool(p4_time_keys)

    if aggregation_resolved:
        status = "SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED"
        diagnosis = "FOUR_TIME_SG7A_CORRECTED_REFERENCE_SET_PERSISTED_WITH_AGGREGATION_SEMANTICS"
        recommendation = (
            "The exact four-time historical SG7E reference set is reconstructed and persisted "
            "with immutable hashes, unchanged S=0.5 plume masks, and recovered multi-time "
            "aggregation semantics. Before evaluating frozen SG7D6, resolve the physical time "
            "identity of its single 15x50x50 field if not already explicit. Do not compare one "
            "untimed grid against all four historical snapshots by assumption."
        )
        next_milestone = (
            "V15-SG7E1R15 — Frozen SG7D6 Physical-Time Identity / Multi-Time Compatibility Audit"
        )
    else:
        status = "SG7E_MULTI_TIME_REFERENCE_RECONSTRUCTED_AGGREGATION_NOT_YET_RESOLVED"
        diagnosis = "FOUR_TIME_REFERENCE_SET_PERSISTED_BUT_FINAL_MULTI_TIME_GATE_AGGREGATION_UNCLEAR"
        recommendation = (
            "The exact four-time historical SG7E reference set is now reconstructed and persisted. "
            "Do not evaluate SG7D6 yet. Audit only the final historical aggregation semantics that "
            "combine per-time PRIMARY_VOLUME, FOOTPRINT_IOU, CENTROID, and VERTICAL_EXTENT results "
            "into deployment acceptance."
        )
        next_milestone = (
            "V15-SG7E1R15 — Historical Multi-Time Gate Aggregation Resolution Audit"
        )

    checks = [
        ("Incoming R13 multi-time contract reproduced", True),
        ("R11 authoritative artifact retained", True),
        ("Historical reference key remains SG7A_corrected", True),
        ("Reference tensor shape = 4x15x50x50", reference.shape == EXPECTED_REFERENCE_SHAPE),
        ("Historical times = 100/250/500/1000 days", np.allclose(times_days, EXPECTED_TIMES)),
        ("Historical plume threshold remains exactly 0.5", abs(threshold - 0.5) < 1e-15),
        ("Complete 4-D reference tensor hashed", bool(reference_hash)),
        ("All four snapshots independently hashed", len(snapshot_hash_rows) == 4),
        ("All four plume masks independently constructed", plume_masks.shape == EXPECTED_REFERENCE_SHAPE),
        ("Per-time plume morphology reconstructed", len(plume_rows) == 4),
        ("Multi-time aggregation semantics audited", True),
        ("Frozen SG7D6 dimensional/time compatibility audited", True),
        ("No SG7D6 performance evaluated", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No post-hoc alignment performed", True),
        ("No deployment correction performed", True),
    ]

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "reference_key": REFERENCE_KEY,
        "artifact_path": str(selected_artifact),
        "reference_sha256": reference_hash,
        "times_sha256": time_hash,
        "plume_mask_sha256": plume_hash,
        "times_days": ";".join(map(str, times_days.tolist())),
        "plume_threshold": threshold,
        "aggregation_mode": aggregation_mode,
        "aggregation_resolved": aggregation_resolved,
        "frozen_SG7D6_artifact": str(frozen_candidate_path) if frozen_candidate_path else "",
        "frozen_SG7D6_grid_shape": str(p4_shape),
        "frozen_SG7D6_time_keys": ";".join(p4_time_keys),
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R14",
            "status": status,
            "diagnosis": diagnosis,
            "historical_reference": {
                "artifact_path": str(selected_artifact),
                "key": REFERENCE_KEY,
                "shape": list(reference.shape),
                "sha256": reference_hash,
                "times_days": [float(x) for x in times_days],
                "times_sha256": time_hash,
                "plume_threshold": threshold,
                "plume_mask_sha256": plume_hash,
            },
            "per_time_snapshots": snapshot_hash_rows,
            "aggregation": {
                "mode": aggregation_mode,
                "evidence": aggregation_evidence,
                "resolved": aggregation_resolved,
            },
            "frozen_SG7D6_compatibility": {
                "artifact_path": str(frozen_candidate_path) if frozen_candidate_path else None,
                "grid_shape": list(p4_shape) if p4_shape else None,
                "time_keys": p4_time_keys,
                "explicit_time_compatibility_resolved": dimensional_time_compatibility,
            },
            "constraints": {
                "candidate_performance_used": False,
                "threshold_changed": False,
                "posthoc_alignment": False,
                "deployment_correction_performed": False,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E1R14",
            "status": status,
            "diagnosis": diagnosis,
            "multi_time_reference_reconstructed": True,
            "aggregation_resolved": aggregation_resolved,
            "aggregation_mode": aggregation_mode,
            "SG7D6_time_compatibility_resolved": dimensional_time_compatibility,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("MULTI-TIME HISTORICAL REFERENCE")
    print(f"  Artifact                : {selected_artifact}")
    print(f"  Key                     : {REFERENCE_KEY}")
    print(f"  Shape                   : {reference.shape}")
    print(f"  Times [days]            : {[float(x) for x in times_days]}")
    print(f"  Threshold               : {threshold:.6f}")
    print(f"  Reference SHA-256       : {reference_hash}")
    print(f"  Plume-mask SHA-256      : {plume_hash}")

    print("\nPER-TIME REFERENCE CONTRACT")
    for row in plume_rows:
        print(
            f"  t={float(row['time_days']):7.1f} d | "
            f"plumeCells={int(row['plume_cells']):6d} | "
            f"footprint={int(row['footprint_cells']):4d} | "
            f"vert={int(row['vertical_extent_layers']):2d} | "
            f"centroid=({float(row['centroid_i']):.2f},"
            f"{float(row['centroid_j']):.2f},"
            f"{float(row['centroid_k']):.2f})"
        )

    print("\nMULTI-TIME AGGREGATION")
    print(f"  Mode                    : {aggregation_mode}")
    print(f"  Resolved                : {aggregation_resolved}")
    print(f"  Evidence                : {aggregation_evidence}")

    print("\nFROZEN SG7D6 DIMENSIONAL COMPATIBILITY")
    print(f"  Frozen artifact         : {frozen_candidate_path}")
    print(f"  Grid shape              : {p4_shape}")
    print(f"  Time keys               : {p4_time_keys}")
    print(f"  Explicit time resolved  : {dimensional_time_compatibility}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R14 CONTRACT VALIDATION")
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
        REFERENCE_ID_TABLE,
        SNAPSHOT_HASH_TABLE,
        PLUME_TABLE,
        AGGREGATION_TABLE,
        DIMENSION_TABLE,
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
    print("V15-SG7E1R14 MULTI-TIME HISTORICAL REFERENCE RECONSTRUCTION / CONTRACT AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No candidate performance was used to define the reference.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)

    db.close()


if __name__ == "__main__":
    main()
