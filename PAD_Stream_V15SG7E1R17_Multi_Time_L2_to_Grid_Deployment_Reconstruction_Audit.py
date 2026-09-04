from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R17
# Multi-Time L2-to-Grid Deployment Reconstruction Audit
#
# FORENSIC MULTI-TIME DEPLOYMENT-STATE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
# NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
#
# PURPOSE
# -------
# SG7E1R16 established:
#
#   SG7D4_L2_TRANSPORT_STATE_IS_MULTI_TIME
#
# with:
#
#   FROZEN_L2_LINEAGE_CONTAINS_MULTIPLE_PHYSICAL_TIME_STATES
#
# R17 reconstructs the deployment-state inventory required to reproduce the
# historical SG7E four-time contract:
#
#   t = [100, 250, 500, 1000] days
#
# It audits:
#
#   1. all persisted 2-D L2/transport states with 201 xi nodes,
#   2. provenance-supported time labels for those states,
#   3. whether one unique state exists for each required SG7E time,
#   4. whether the conservative SG7D1 map-back inputs/kernel can be replayed,
#   5. whether the frozen SG7D6 grid is one member of that time-labelled set,
#   6. whether a complete four-time grid reconstruction is currently possible
#      without retraining or inventing missing states.
#
# R17 DOES NOT RUN SG7E PERFORMANCE GATES.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R17"
OUT.mkdir(parents=True, exist_ok=True)

R16_DIR = ROOT / "output" / "V15_SG7E1R16"
R16_SUMMARY = R16_DIR / "PAD_Stream_V15SG7E1R16_Summary.json"
R16_CONTRACT = R16_DIR / "V15SG7E1R16_SG7D4_to_L2_Transport_Time_Contract.json"
R16_L2_INV = R16_DIR / "V15SG7E1R16_Frozen_L2_Array_Inventory.csv"
R16_SOURCE = R16_DIR / "V15SG7E1R16_L2_Creation_Evaluation_Source_Trace.csv"

R14_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R14"
    / "V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json"
)

D1_NUM = (
    ROOT / "output" / "V15_SG7D1"
    / "V15SG7D1_Conservative_MapBack.npz"
)

D1_SOURCE = ROOT / "PAD_Stream_V15SG7D1_Conservative_Frozen_L2_Streamline_to_Grid_MapBack.py"

D0_CONTRACT = (
    ROOT / "output" / "V15_SG7D0"
    / "V15SG7D0_Frozen_L2_MapBack_Interface_Contract.json"
)

D6_FROZEN = (
    ROOT / "output" / "V15_SG7D6" / "frozen_full_grid"
    / "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

R1F2CRR_NUM = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
    / "V15SG7CR3F5R1F2CRR_Independent_Validation.npz"
)

REQUIRED_TIMES = np.array([100.0, 250.0, 500.0, 1000.0], dtype=float)
STREAMLINE_COUNT = 2662
XI_NODES = 201
GRID_SHAPE = (15, 50, 50)

STATE_INV = OUT / "V15SG7E1R17_Persisted_Multi_Time_L2_State_Inventory.csv"
TIME_MAP = OUT / "V15SG7E1R17_L2_State_Time_Provenance.csv"
STATE_DECISION = OUT / "V15SG7E1R17_Required_Time_State_Coverage.csv"
MAPBACK_AUDIT = OUT / "V15SG7E1R17_MapBack_Replay_Audit.csv"
FROZEN_LINK = OUT / "V15SG7E1R17_Frozen_Grid_Time_Membership.csv"
FINAL_TABLE = OUT / "V15SG7E1R17_Multi_Time_Reconstruction_Decision.csv"

CONTRACT = OUT / "V15SG7E1R17_Multi_Time_L2_to_Grid_Reconstruction_Contract.json"
SUMMARY = OUT / "PAD_Stream_V15SG7E1R17_Summary.json"


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


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def parse_time_from_name(name: str):
    vals = []
    low = name.lower()
    patterns = [
        r"(?<!\d)(1000)(?:d|day|days)?(?!\d)",
        r"(?<!\d)(500)(?:d|day|days)?(?!\d)",
        r"(?<!\d)(250)(?:d|day|days)?(?!\d)",
        r"(?<!\d)(100)(?:d|day|days)?(?!\d)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, low):
            vals.append(float(m.group(1)))
    return sorted(set(vals))


def candidate_npz_files():
    files = []
    roots = [
        ROOT / "output" / "V15_SG7CR3F5R1F3",
        ROOT / "output" / "V15_SG7CR3F5R1F2CRR",
        ROOT / "output" / "V15_SG7CR3F5R1F2C",
        ROOT / "output" / "V15_SG7CR3F5R1F2B",
        ROOT / "output" / "V15_SG7CR3F5R1F1",
        ROOT / "output" / "V15_SG7CR3F5R1E",
        ROOT / "output" / "V15_SG7CR3F5R1C",
        ROOT / "output" / "V15_SG7CR3F5R1B",
    ]
    for base in roots:
        if base.exists():
            files.extend(base.rglob("*.npz"))
    return sorted(set(p.resolve() for p in files))


def find_grid_key(db):
    preferred = [
        "saturation_grid_full",
        "full_grid_saturation",
        "completed_full_grid",
        "saturation_grid",
        "grid_saturation",
    ]
    for key in preferred:
        if key in db.files:
            arr = np.asarray(db[key])
            if arr.shape == GRID_SHAPE:
                return key, arr
    for key in db.files:
        arr = np.asarray(db[key])
        if arr.shape == GRID_SHAPE:
            return key, arr
    return None, None


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R17")
    print("Multi-Time L2-to-Grid Deployment Reconstruction Audit")
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
NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
""")

    r16 = load_json(R16_SUMMARY)
    r16c = load_json(R16_CONTRACT)
    r14c = load_json(R14_CONTRACT)

    if r16.get("status") != "SG7D4_L2_TRANSPORT_STATE_IS_MULTI_TIME":
        raise RuntimeError("R17 requires the R16 multi-time transport-state status.")

    if r16.get("diagnosis") != "FROZEN_L2_LINEAGE_CONTAINS_MULTIPLE_PHYSICAL_TIME_STATES":
        raise RuntimeError("R17 requires the R16 multi-time lineage diagnosis.")

    hist_times = np.asarray(
        r14c["historical_reference"]["times_days"], dtype=float
    )
    if not np.allclose(hist_times, REQUIRED_TIMES, rtol=0.0, atol=1e-12):
        raise RuntimeError("R17 historical time contract mismatch.")

    # -------------------------------------------------------------------------
    # Discover persisted 2662x201 deployment-state arrays.
    # -------------------------------------------------------------------------

    state_rows = []

    for npz_path in candidate_npz_files():
        try:
            db = np.load(npz_path, allow_pickle=True)
        except Exception:
            continue

        sibling_times = []
        for key in db.files:
            lk = key.lower()
            if "time" in lk or "days" in lk:
                arr = np.asarray(db[key]).reshape(-1)
                if arr.size <= 100:
                    for v in arr:
                        try:
                            fv = float(v)
                        except Exception:
                            continue
                        if np.any(np.isclose(REQUIRED_TIMES, fv, rtol=0.0, atol=1e-12)):
                            sibling_times.append(fv)

        sibling_times = sorted(set(sibling_times))

        for key in db.files:
            arr = np.asarray(db[key])

            if arr.shape != (STREAMLINE_COUNT, XI_NODES):
                continue
            if not np.issubdtype(arr.dtype, np.number):
                continue

            name_times = parse_time_from_name(key + " " + npz_path.name)
            inferred_times = sorted(set(name_times + sibling_times))

            state_rows.append({
                "artifact_path": str(npz_path),
                "artifact_file": npz_path.name,
                "key": key,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "array_sha256": sha256_array(arr),
                "name_time_candidates": ";".join(map(str, name_times)),
                "sibling_time_candidates": ";".join(map(str, sibling_times)),
                "combined_time_candidates": ";".join(map(str, inferred_times)),
                "min": float(np.nanmin(arr)),
                "max": float(np.nanmax(arr)),
                "mean": float(np.nanmean(arr)),
            })

        db.close()

    save_csv(STATE_INV, state_rows)

    # -------------------------------------------------------------------------
    # Supplement time provenance from R16 source trace.
    # -------------------------------------------------------------------------

    source_rows = load_csv(R16_SOURCE)
    provenance_rows = []

    # Index direct state candidates by artifact/key strings.
    for s in state_rows:
        combined = set()
        for part in (
            s["name_time_candidates"],
            s["sibling_time_candidates"],
        ):
            for x in part.split(";"):
                if x:
                    combined.add(float(x))

        for src in source_rows:
            blob = (
                src.get("matched_line", "")
                + "\n"
                + src.get("context", "")
                + "\n"
                + src.get("semantic_hits", "")
            ).lower()

            # State-specific only if key or artifact filename appears in context.
            if (
                s["key"].lower() not in blob
                and s["artifact_file"].lower() not in blob
            ):
                continue

            for t in REQUIRED_TIMES:
                if re.search(
                    rf"(?<!\d){int(t)}(?:\.0+)?\s*(?:d|day|days)?(?!\d)",
                    blob,
                ):
                    combined.add(float(t))

        provenance_rows.append({
            "artifact_path": s["artifact_path"],
            "artifact_file": s["artifact_file"],
            "key": s["key"],
            "array_sha256": s["array_sha256"],
            "provenance_time_candidates": ";".join(map(str, sorted(combined))),
            "unique_time_resolved": len(combined) == 1,
            "resolved_time_days": next(iter(combined)) if len(combined) == 1 else "",
        })

    save_csv(TIME_MAP, provenance_rows)

    # -------------------------------------------------------------------------
    # Deduplicate by numerical state hash and audit required-time coverage.
    # -------------------------------------------------------------------------

    hash_time_map = defaultdict(set)
    hash_members = defaultdict(list)

    for row in provenance_rows:
        h = row["array_sha256"]
        hash_members[h].append(row)
        for x in row["provenance_time_candidates"].split(";"):
            if x:
                hash_time_map[h].add(float(x))

    time_to_hashes = defaultdict(set)

    for h, times in hash_time_map.items():
        if len(times) == 1:
            t = next(iter(times))
            if np.any(np.isclose(REQUIRED_TIMES, t, rtol=0.0, atol=1e-12)):
                time_to_hashes[t].add(h)

    coverage_rows = []
    unique_state_for_time = {}

    for t in REQUIRED_TIMES:
        hashes = sorted(time_to_hashes.get(float(t), set()))
        if len(hashes) == 1:
            unique_state_for_time[float(t)] = hashes[0]

        coverage_rows.append({
            "time_days": float(t),
            "resolved_state_hash_count": len(hashes),
            "state_hashes": ";".join(hashes),
            "unique_state_available": len(hashes) == 1,
        })

    save_csv(STATE_DECISION, coverage_rows)

    # -------------------------------------------------------------------------
    # Conservative map-back replay feasibility.
    # -------------------------------------------------------------------------

    mapback_rows = []

    d1_exists = D1_NUM.exists()
    d0_exists = D0_CONTRACT.exists()
    d1_source_exists = D1_SOURCE.exists()

    d1_keys = []
    geometry_like = []
    weights_like = []

    if d1_exists:
        d1 = np.load(D1_NUM, allow_pickle=True)
        d1_keys = list(d1.files)

        for key in d1.files:
            lk = key.lower()
            arr = np.asarray(d1[key])

            if any(tok in lk for tok in ("xyz", "segment", "piece", "cell_index", "cell_id")):
                geometry_like.append(f"{key}:{arr.shape}")

            if any(tok in lk for tok in ("weight", "denominator", "support")):
                weights_like.append(f"{key}:{arr.shape}")

        d1.close()

    source_text = safe_text(D1_SOURCE) if d1_source_exists else ""

    exact_split_semantics = any(
        token in source_text.lower()
        for token in (
            "segment",
            "cartesian",
            "split",
            "weighted",
            "deposition",
        )
    )

    replay_inputs_available = d1_exists and d0_exists and d1_source_exists

    mapback_rows.append({
        "SG7D1_numerical_exists": d1_exists,
        "SG7D0_contract_exists": d0_exists,
        "SG7D1_source_exists": d1_source_exists,
        "SG7D1_key_count": len(d1_keys),
        "geometry_like_keys": ";".join(geometry_like),
        "weight_like_keys": ";".join(weights_like),
        "exact_segment_split_semantics_found": exact_split_semantics,
        "mapback_replay_inputs_available": replay_inputs_available,
    })

    save_csv(MAPBACK_AUDIT, mapback_rows)

    # -------------------------------------------------------------------------
    # Determine whether frozen SG7D6 is already one time-member.
    #
    # Only hash relationships are reported; no time assigned by field similarity.
    # -------------------------------------------------------------------------

    frozen_membership_rows = []

    frozen_grid_hash = ""
    if D6_FROZEN.exists():
        d6 = np.load(D6_FROZEN, allow_pickle=True)
        gkey, grid = find_grid_key(d6)
        if grid is not None:
            frozen_grid_hash = sha256_array(grid)
        d6.close()

    # We cannot compare a 2D streamline state hash to a 3D grid hash directly.
    # Instead record whether source provenance identifies D6 as the map-back of
    # one uniquely time-labelled state.
    linked_times = []

    d1_source_blob = source_text.lower()
    for t, h in unique_state_for_time.items():
        members = hash_members[h]
        for m in members:
            key = m["key"].lower()
            fname = m["artifact_file"].lower()
            if key in d1_source_blob or fname in d1_source_blob:
                linked_times.append(float(t))

    linked_times = sorted(set(linked_times))

    frozen_membership_rows.append({
        "frozen_grid_sha256": frozen_grid_hash,
        "uniquely_time_labelled_L2_states": len(unique_state_for_time),
        "source_linked_time_candidates": ";".join(map(str, linked_times)),
        "one_time_membership_resolved": len(linked_times) == 1,
        "resolved_time_days": linked_times[0] if len(linked_times) == 1 else "",
    })

    save_csv(FROZEN_LINK, frozen_membership_rows)

    # -------------------------------------------------------------------------
    # Final decision.
    # -------------------------------------------------------------------------

    all_four_states = all(
        bool(r["unique_state_available"])
        for r in coverage_rows
    )

    if all_four_states and replay_inputs_available:
        status = "MULTI_TIME_L2_TO_GRID_RECONSTRUCTION_READY"
        diagnosis = "UNIQUE_L2_STATE_EXISTS_FOR_EACH_REQUIRED_TIME_AND_MAPBACK_IS_REPLAYABLE"
        recommendation = (
            "All four historical SG7E times have one provenance-resolved L2 deployment "
            "state and the conservative SG7D map-back can be replayed without retraining. "
            "Proceed to controlled four-time streamline-to-grid reconstruction, preserving "
            "the exact time labels, support mask policy, background completion rule, and "
            "unchanged SG7E threshold."
        )
        next_milestone = (
            "V15-SG7E1R18 — Controlled Four-Time L2-to-Grid Deployment Reconstruction"
        )

    elif all_four_states and not replay_inputs_available:
        status = "MULTI_TIME_L2_STATES_COMPLETE_MAPBACK_REPLAY_BLOCKED"
        diagnosis = "FOUR_TIME_L2_STATE_SET_RESOLVED_BUT_MAPBACK_REPLAY_INTERFACE_INCOMPLETE"
        recommendation = (
            "The complete four-time L2 state set exists, but the exact conservative map-back "
            "cannot yet be replayed from persisted interfaces. Recover the SG7D1 segment "
            "splitting inputs/kernel without modifying any state before reconstruction."
        )
        next_milestone = (
            "V15-SG7E1R18 — Conservative Map-Back Replay Interface Recovery Audit"
        )

    else:
        missing = [
            float(r["time_days"])
            for r in coverage_rows
            if not bool(r["unique_state_available"])
        ]

        status = "MULTI_TIME_L2_STATE_COVERAGE_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_HISTORICAL_SG7E_TIMES_LACK_UNIQUE_PERSISTED_L2_STATE"
        recommendation = (
            "Do not fabricate missing deployment states and do not evaluate SG7E gates. "
            "Audit the L2 evaluation source for the missing required times and determine "
            "whether those states can be deterministically regenerated from the frozen model "
            "and existing inputs without retraining."
        )
        next_milestone = (
            "V15-SG7E1R18 — Missing L2 Physical-Time State Deterministic-Regeneration Audit"
        )

    checks = [
        ("Incoming R16 multi-time transport-state diagnosis reproduced", True),
        ("Historical times 100/250/500/1000 retained", True),
        ("Persisted 2662x201 deployment states inventoried", len(state_rows) > 0),
        ("State hashes generated", all(bool(r["array_sha256"]) for r in state_rows)),
        ("State-specific time provenance audited", True),
        ("Numerically duplicate states deduplicated by hash", True),
        ("Required-time state coverage established", True),
        ("SG7D1 conservative replay interface audited", True),
        ("Frozen SG7D6 membership audited without performance comparison", True),
        ("No missing state fabricated", True),
        ("No training performed", True),
        ("No SG7E performance gate evaluated", True),
        ("No threshold changed or relaxed", True),
    ]

    final = [{
        "status": status,
        "diagnosis": diagnosis,
        "persisted_state_arrays": len(state_rows),
        "unique_state_hashes": len(hash_members),
        "resolved_required_times": ";".join(
            str(t) for t in REQUIRED_TIMES
            if float(t) in unique_state_for_time
        ),
        "missing_or_ambiguous_required_times": ";".join(
            str(float(r["time_days"]))
            for r in coverage_rows
            if not bool(r["unique_state_available"])
        ),
        "all_four_unique_states_available": all_four_states,
        "mapback_replay_inputs_available": replay_inputs_available,
        "frozen_source_linked_times": ";".join(map(str, linked_times)),
        "next_milestone": next_milestone,
    }]
    save_csv(FINAL_TABLE, final)

    save_json(CONTRACT, {
        "milestone": "V15-SG7E1R17",
        "status": status,
        "diagnosis": diagnosis,
        "historical_times_days": [float(x) for x in REQUIRED_TIMES],
        "state_coverage": coverage_rows,
        "mapback_replay": mapback_rows[0],
        "frozen_membership": frozen_membership_rows[0],
        "constraints": {
            "training_performed": False,
            "missing_state_fabricated": False,
            "candidate_performance_used": False,
            "SG7E_gate_evaluated": False,
            "threshold_changed": False,
            "posthoc_alignment": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY, {
        "milestone": "V15-SG7E1R17",
        "status": status,
        "diagnosis": diagnosis,
        "all_four_unique_states_available": all_four_states,
        "mapback_replay_inputs_available": replay_inputs_available,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("PERSISTED MULTI-TIME L2 STATE INVENTORY")
    print(f"  2662x201 state arrays   : {len(state_rows)}")
    print(f"  Unique state hashes     : {len(hash_members)}")

    print("\nREQUIRED-TIME STATE COVERAGE")
    for row in coverage_rows:
        print(
            f"  t={float(row['time_days']):7.1f} d | "
            f"hashes={int(row['resolved_state_hash_count']):2d} | "
            f"unique={row['unique_state_available']}"
        )

    print("\nMAP-BACK REPLAY")
    print(f"  SG7D1 numerical         : {d1_exists}")
    print(f"  SG7D0 contract          : {d0_exists}")
    print(f"  SG7D1 source            : {d1_source_exists}")
    print(f"  Replay inputs available : {replay_inputs_available}")

    print("\nFROZEN SG7D6 MEMBERSHIP")
    print(f"  Source-linked times     : {linked_times}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R17 RECONSTRUCTION AUDIT VALIDATION")
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
        STATE_INV,
        TIME_MAP,
        STATE_DECISION,
        MAPBACK_AUDIT,
        FROZEN_LINK,
        FINAL_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R17 MULTI-TIME L2-TO-GRID DEPLOYMENT RECONSTRUCTION AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen L2 array was changed.")
    print("No frozen SG7D6 field was changed.")
    print("No missing deployment state was fabricated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
