from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R15
# Frozen SG7D6 Physical-Time Identity / Multi-Time Compatibility Audit
#
# FORENSIC TIME-COMPATIBILITY MILESTONE
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
# NO PHYSICAL TIME WILL BE ASSIGNED TO SG7D6 BY ASSUMPTION.
#
# PURPOSE
# -------
# SG7E1R14 established:
#
#   SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED
#
# with:
#
#   FOUR_TIME_SG7A_CORRECTED_REFERENCE_SET_PERSISTED_WITH_AGGREGATION_SEMANTICS
#
# Historical SG7E truth is:
#
#   t = [100, 250, 500, 1000] days
#
# and acceptance semantics are:
#
#   PER_TIME_ALL_REQUIRED
#
# The frozen SG7D6 artifact is currently a single:
#
#   (15, 50, 50)
#
# grid with no explicit time key.
#
# R15 therefore audits whether its physical-time identity can be recovered from:
#
#   * SG7D6 freeze manifest / contract / summary,
#   * SG7D4 / SG7D5 provenance,
#   * frozen L2 transport lineage,
#   * upstream SG7C validation time semantics,
#   * array/key names,
#   * source save/load expressions,
#   * manifest fields such as time_days / snapshot / evaluation_time,
#   * exact state hashes where temporal source candidates exist.
#
# R15 does NOT compare the frozen grid to the four historical references.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R15"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R14_DIR = ROOT / "output" / "V15_SG7E1R14"
R14_SUMMARY = R14_DIR / "PAD_Stream_V15SG7E1R14_Summary.json"
R14_CONTRACT = R14_DIR / "V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json"
R14_DIMENSION = R14_DIR / "V15SG7E1R14_SG7D6_Reference_Dimensional_Compatibility.csv"

D6_DIR = ROOT / "output" / "V15_SG7D6"
D6_MANIFEST = D6_DIR / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
D6_CONTRACT = D6_DIR / "V15SG7D6_Frozen_Grid_Deployment_Contract.json"
D6_SUMMARY = D6_DIR / "PAD_Stream_V15SG7D6_Summary.json"

D5_DIR = ROOT / "output" / "V15_SG7D5"
D4_DIR = ROOT / "output" / "V15_SG7D4"

R1F3_DIR = ROOT / "output" / "V15_SG7CR3F5R1F3"

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

FROZEN_ID_TABLE = OUT / "V15SG7E1R15_Frozen_SG7D6_Identity.csv"
TIME_EVIDENCE_TABLE = OUT / "V15SG7E1R15_Time_Provenance_Evidence.csv"
SOURCE_TRACE_TABLE = OUT / "V15SG7E1R15_Source_Time_Assignment_Trace.csv"
UPSTREAM_TABLE = OUT / "V15SG7E1R15_Upstream_Temporal_Lineage.csv"
HASH_MATCH_TABLE = OUT / "V15SG7E1R15_Temporal_Source_Hash_Match.csv"
COMPAT_TABLE = OUT / "V15SG7E1R15_Multi_Time_Compatibility_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R15_Frozen_SG7D6_Physical_Time_Compatibility_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R15_Summary.json"

EXPECTED_REFERENCE_TIMES = np.array([100.0, 250.0, 500.0, 1000.0], dtype=float)
EXPECTED_GRID_SHAPE = (15, 50, 50)


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


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def walk_json(obj, prefix=""):
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                rows.extend(walk_json(v, p))
            else:
                rows.append((p, v))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                rows.extend(walk_json(v, p))
            else:
                rows.append((p, v))
    return rows


def extract_time_values_from_text(text):
    evidence = []

    patterns = [
        ("time_days", r"\btime_days\b\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"),
        ("evaluation_time_days", r"\bevaluation_time_days\b\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"),
        ("snapshot_time_days", r"\bsnapshot_time_days\b\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"),
        ("days", r"\b(?:at|time)\s*=?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:d|day|days)\b"),
    ]

    for label, pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            try:
                val = float(m.group(1))
            except Exception:
                continue
            evidence.append((label, val, m.group(0)))

    return evidence


def project_text_files():
    files = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        low = {x.lower() for x in p.parts}
        if ".venv" in low or "site-packages" in low or "__pycache__" in low:
            continue
        if p.suffix.lower() in {".py", ".json", ".csv", ".txt"}:
            files.append(p.resolve())
    return sorted(set(files))


def candidate_grid_arrays(npz_path):
    rows = []
    try:
        db = np.load(npz_path, allow_pickle=True)
    except Exception:
        return rows

    for key in db.files:
        try:
            arr = np.asarray(db[key])
        except Exception:
            continue

        if arr.shape == EXPECTED_GRID_SHAPE:
            rows.append({
                "path": str(npz_path),
                "file": npz_path.name,
                "key": key,
                "shape": str(arr.shape),
                "array_sha256": sha256_array(arr),
            })

    db.close()
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R15")
    print("Frozen SG7D6 Physical-Time Identity / Multi-Time Compatibility Audit")
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
NO PHYSICAL TIME WILL BE ASSIGNED TO SG7D6 BY ASSUMPTION.
""")

    r14_summary = load_json(R14_SUMMARY)
    r14_contract = load_json(R14_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)
    d6_contract = load_json(D6_CONTRACT)
    d6_summary = load_json(D6_SUMMARY)

    if r14_summary.get("status") != (
        "SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED"
    ):
        raise RuntimeError(
            "R15 requires reconstructed R14 multi-time historical contract."
        )

    if r14_summary.get("aggregation_mode") != "PER_TIME_ALL_REQUIRED":
        raise RuntimeError(
            "R15 requires resolved PER_TIME_ALL_REQUIRED aggregation semantics."
        )

    # -------------------------------------------------------------------------
    # Frozen artifact identity.
    # -------------------------------------------------------------------------

    frozen_path = (
        D6_DIR / "frozen_full_grid"
        / "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz"
    ).resolve()

    if not frozen_path.exists():
        raise FileNotFoundError(
            f"Frozen SG7D6 artifact not found:\n{frozen_path}"
        )

    frozen_db = np.load(frozen_path, allow_pickle=True)

    frozen_grid_key = None
    frozen_grid = None

    # Prefer obvious full-grid saturation names.
    preferred = [
        "full_grid_saturation",
        "completed_full_grid",
        "saturation_grid",
        "grid_saturation",
        "S_grid",
        "S_full",
    ]

    for key in preferred:
        if key in frozen_db.files:
            arr = np.asarray(frozen_db[key])
            if arr.shape == EXPECTED_GRID_SHAPE:
                frozen_grid_key = key
                frozen_grid = arr
                break

    if frozen_grid is None:
        for key in frozen_db.files:
            arr = np.asarray(frozen_db[key])
            if arr.shape == EXPECTED_GRID_SHAPE:
                frozen_grid_key = key
                frozen_grid = arr
                break

    if frozen_grid is None:
        raise RuntimeError(
            "Could not identify a 15x50x50 full-grid field in frozen SG7D6 artifact."
        )

    frozen_hash = sha256_array(frozen_grid)
    frozen_file_hash = sha256_file(frozen_path)

    frozen_time_keys = []
    for key in frozen_db.files:
        lk = key.lower()
        if "time" in lk or "days" in lk:
            arr = np.asarray(frozen_db[key])
            frozen_time_keys.append({
                "key": key,
                "shape": str(arr.shape),
                "values": ";".join(map(str, arr.reshape(-1).tolist()[:50])),
            })

    save_csv(FROZEN_ID_TABLE, [{
        "artifact_path": str(frozen_path),
        "artifact_file": frozen_path.name,
        "file_sha256": frozen_file_hash,
        "grid_key": frozen_grid_key,
        "grid_shape": str(frozen_grid.shape),
        "grid_dtype": str(frozen_grid.dtype),
        "grid_sha256": frozen_hash,
        "time_key_count": len(frozen_time_keys),
        "time_keys": ";".join(r["key"] for r in frozen_time_keys),
    }])

    # -------------------------------------------------------------------------
    # Provenance evidence from SG7D6, SG7D5, SG7D4, and frozen SG7C lineage.
    # -------------------------------------------------------------------------

    time_evidence_rows = []

    provenance_files = [
        D6_MANIFEST,
        D6_CONTRACT,
        D6_SUMMARY,
    ]

    for folder in [D5_DIR, D4_DIR, R1F3_DIR]:
        if folder.exists():
            provenance_files.extend(
                p for p in folder.rglob("*")
                if p.is_file() and p.suffix.lower() in {".json", ".csv", ".txt"}
            )

    # JSON structured evidence
    for p in provenance_files:
        if not p.exists():
            continue

        if p.suffix.lower() == ".json":
            try:
                obj = load_json(p)
            except Exception:
                obj = None

            if obj is not None:
                for field, value in walk_json(obj):
                    lf = field.lower()
                    if "time" in lf or "day" in lf or "snapshot" in lf:
                        time_evidence_rows.append({
                            "source": str(p),
                            "kind": "structured_field",
                            "field": field,
                            "value": value,
                            "numeric_time_candidate": (
                                float(value)
                                if isinstance(value, (int, float))
                                else ""
                            ),
                        })

        # Raw text evidence
        text = safe_text(p)
        for label, value, raw in extract_time_values_from_text(text):
            time_evidence_rows.append({
                "source": str(p),
                "kind": "text_time_expression",
                "field": label,
                "value": raw,
                "numeric_time_candidate": value,
            })

    save_csv(TIME_EVIDENCE_TABLE, time_evidence_rows)

    # -------------------------------------------------------------------------
    # Source-code save/assignment trace for SG7D4/D6 artifact.
    # -------------------------------------------------------------------------

    source_trace_rows = []

    relevant_tokens = [
        "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz",
        "V15SG7D4_Completed_Full_Grid.npz",
        "P4_full_grid",
        frozen_grid_key,
    ]

    for src in project_text_files():
        if src.suffix.lower() != ".py":
            continue

        text = safe_text(src)
        low = text.lower()

        if not any(tok.lower() in low for tok in relevant_tokens if tok):
            continue

        lines = text.splitlines()

        for i, line in enumerate(lines, start=1):
            if any(tok.lower() in line.lower() for tok in relevant_tokens if tok):
                ctx = "\n".join(
                    lines[max(0, i-12):min(len(lines), i+15)]
                )

                time_hits = extract_time_values_from_text(ctx)

                source_trace_rows.append({
                    "source": str(src),
                    "line": i,
                    "matched_line": line.strip()[:1500],
                    "context": ctx[:5000],
                    "time_hits": ";".join(
                        f"{lab}:{val}" for lab, val, _ in time_hits
                    ),
                })

    save_csv(SOURCE_TRACE_TABLE, source_trace_rows)

    # -------------------------------------------------------------------------
    # Upstream temporal lineage:
    # find NPZ grids that are numerically identical to frozen SG7D6 grid.
    # -------------------------------------------------------------------------

    temporal_candidates = []

    for p in (ROOT / "output").rglob("*.npz"):
        if p.resolve() == frozen_path:
            continue

        rows = candidate_grid_arrays(p)
        for row in rows:
            if row["array_sha256"] == frozen_hash:
                temporal_candidates.append(row)

    # For each exact hash match, inspect sibling time arrays / parent metadata.
    upstream_rows = []

    for row in temporal_candidates:
        p = Path(row["path"])
        db = np.load(p, allow_pickle=True)

        sibling_time_keys = []
        for key in db.files:
            if "time" in key.lower() or "days" in key.lower():
                arr = np.asarray(db[key]).reshape(-1)
                sibling_time_keys.append(
                    f"{key}={arr.tolist()[:20]}"
                )

        upstream_rows.append({
            **row,
            "sibling_time_keys": ";".join(sibling_time_keys),
            "parent_directory": p.parent.name,
        })

        db.close()

    save_csv(UPSTREAM_TABLE, upstream_rows)

    save_csv(HASH_MATCH_TABLE, temporal_candidates)

    # -------------------------------------------------------------------------
    # Resolve physical time only from explicit provenance.
    # -------------------------------------------------------------------------

    numeric_time_candidates = []

    # Frozen artifact internal time arrays
    for rec in frozen_time_keys:
        try:
            vals = [
                float(x) for x in rec["values"].split(";") if x != ""
            ]
            numeric_time_candidates.extend(vals)
        except Exception:
            pass

    # Structured/text evidence
    for row in time_evidence_rows:
        v = row.get("numeric_time_candidate", "")
        try:
            numeric_time_candidates.append(float(v))
        except Exception:
            pass

    # Restrict to historical contract times.
    matched_reference_times = sorted(set(
        t for t in numeric_time_candidates
        if np.any(np.isclose(EXPECTED_REFERENCE_TIMES, t, rtol=0.0, atol=1e-12))
    ))

    # Exact hash-match artifacts with explicit sibling time keys can strengthen.
    hash_match_times = []

    for row in upstream_rows:
        txt = row.get("sibling_time_keys", "")
        for t in EXPECTED_REFERENCE_TIMES:
            if re.search(
                rf"(?<![0-9.]){re.escape(str(float(t)))}(?![0-9.])",
                txt,
            ):
                hash_match_times.append(float(t))

    hash_match_times = sorted(set(hash_match_times))

    # Conservative resolution:
    # exactly one reference-contract time must be supported.
    all_supported_times = sorted(set(matched_reference_times + hash_match_times))

    physical_time_resolved = len(all_supported_times) == 1
    selected_time = all_supported_times[0] if physical_time_resolved else None

    # -------------------------------------------------------------------------
    # Compatibility classification.
    # -------------------------------------------------------------------------

    if physical_time_resolved:
        status = "SG7D6_PHYSICAL_TIME_IDENTITY_RESOLVED"
        diagnosis = "FROZEN_SINGLE_GRID_MAPS_TO_ONE_HISTORICAL_REFERENCE_TIME"
        recommendation = (
            "The frozen SG7D6 15x50x50 field has one provenance-supported physical time. "
            "Proceed to a time-matched SG7E deployment comparison only at that historical "
            "time. Because the historical SG7E contract requires all four times, do not "
            "claim full multi-time deployment acceptance from one frozen snapshot; audit "
            "whether equivalent frozen SG7D states exist for the other required times."
        )
        next_milestone = (
            "V15-SG7E1R16 — Time-Matched Frozen-State Coverage / Multi-Time Deployment Readiness Audit"
        )

    elif len(all_supported_times) > 1:
        status = "SG7D6_PHYSICAL_TIME_PROVENANCE_CONFLICT"
        diagnosis = "MULTIPLE_HISTORICAL_TIMES_ARE_ASSOCIATED_WITH_SINGLE_FROZEN_GRID"
        recommendation = (
            "Do not evaluate SG7E gates. More than one historical reference time is associated "
            "with the single frozen SG7D6 grid in provenance. Resolve the exact save-time or "
            "source-state identity before any temporal comparison."
        )
        next_milestone = (
            "V15-SG7E1R16 — Frozen SG7D6 Time-Provenance Conflict Resolution Audit"
        )

    else:
        status = "SG7D6_PHYSICAL_TIME_IDENTITY_NOT_RESOLVED"
        diagnosis = "FROZEN_SINGLE_GRID_HAS_NO_AUTHORITATIVE_TIME_ASSIGNMENT"
        recommendation = (
            "Do not evaluate SG7E gates. The frozen SG7D6 field remains temporally unlabelled "
            "relative to the four-time historical contract. Trace the SG7D4 completion source "
            "back to the frozen L2 streamline state and identify the exact transport time that "
            "produced the mapped full-grid field. Do not assign 100, 250, 500, or 1000 days by "
            "similarity or candidate performance."
        )
        next_milestone = (
            "V15-SG7E1R16 — SG7D4-to-L2 Transport-Time Lineage Audit"
        )

    checks = [
        ("Incoming R14 multi-time reference contract reproduced", True),
        ("Historical aggregation = PER_TIME_ALL_REQUIRED", True),
        ("Frozen SG7D6 artifact loaded", True),
        ("Frozen SG7D6 grid shape = 15x50x50", frozen_grid.shape == EXPECTED_GRID_SHAPE),
        ("Frozen grid hash established", bool(frozen_hash)),
        ("Frozen artifact internal time keys audited", True),
        ("SG7D6 manifest/contract/summary time fields audited", True),
        ("SG7D5/SG7D4 provenance time fields audited", True),
        ("Frozen SG7C lineage time fields audited", True),
        ("Source save/assignment contexts audited", True),
        ("Exact upstream grid-hash matches searched", True),
        ("No physical time assigned by similarity", True),
        ("No SG7E performance gate evaluated", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No post-hoc alignment performed", True),
        ("No deployment correction performed", True),
    ]

    compatibility_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "historical_reference_times_days": ";".join(map(str, EXPECTED_REFERENCE_TIMES)),
        "historical_aggregation": "PER_TIME_ALL_REQUIRED",
        "frozen_artifact": str(frozen_path),
        "frozen_grid_key": frozen_grid_key,
        "frozen_grid_sha256": frozen_hash,
        "frozen_internal_time_keys": ";".join(r["key"] for r in frozen_time_keys),
        "provenance_reference_time_candidates": ";".join(map(str, matched_reference_times)),
        "hash_match_time_candidates": ";".join(map(str, hash_match_times)),
        "all_supported_time_candidates": ";".join(map(str, all_supported_times)),
        "physical_time_resolved": physical_time_resolved,
        "selected_time_days": selected_time if selected_time is not None else "",
        "next_milestone": next_milestone,
    }]

    save_csv(COMPAT_TABLE, compatibility_rows)

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R15",
            "status": status,
            "diagnosis": diagnosis,
            "historical_reference": {
                "times_days": [float(x) for x in EXPECTED_REFERENCE_TIMES],
                "aggregation": "PER_TIME_ALL_REQUIRED",
            },
            "frozen_SG7D6": {
                "artifact_path": str(frozen_path),
                "file_sha256": frozen_file_hash,
                "grid_key": frozen_grid_key,
                "grid_shape": list(frozen_grid.shape),
                "grid_sha256": frozen_hash,
                "internal_time_keys": frozen_time_keys,
            },
            "time_provenance": {
                "resolved": physical_time_resolved,
                "selected_time_days": selected_time,
                "provenance_reference_time_candidates": matched_reference_times,
                "hash_match_time_candidates": hash_match_times,
                "all_supported_time_candidates": all_supported_times,
            },
            "constraints": {
                "physical_time_assigned_by_similarity": False,
                "candidate_performance_used": False,
                "SG7E_gate_evaluated": False,
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
            "milestone": "V15-SG7E1R15",
            "status": status,
            "diagnosis": diagnosis,
            "physical_time_resolved": physical_time_resolved,
            "selected_time_days": selected_time,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("FROZEN SG7D6 IDENTITY")
    print(f"  Artifact                : {frozen_path}")
    print(f"  Grid key                : {frozen_grid_key}")
    print(f"  Grid shape              : {frozen_grid.shape}")
    print(f"  Grid SHA-256            : {frozen_hash}")
    print(f"  Internal time keys      : {[r['key'] for r in frozen_time_keys]}")

    print("\nHISTORICAL MULTI-TIME CONTRACT")
    print(f"  Required times [days]   : {[float(x) for x in EXPECTED_REFERENCE_TIMES]}")
    print("  Aggregation             : PER_TIME_ALL_REQUIRED")

    print("\nTIME-PROVENANCE EVIDENCE")
    print(f"  Structured/text records : {len(time_evidence_rows)}")
    print(f"  Source trace records     : {len(source_trace_rows)}")
    print(f"  Exact hash-match grids   : {len(temporal_candidates)}")
    print(f"  Provenance time matches  : {matched_reference_times}")
    print(f"  Hash-match time matches  : {hash_match_times}")

    print("\nPHYSICAL-TIME DECISION")
    print(f"  Resolved                : {physical_time_resolved}")
    print(f"  Candidate times         : {all_supported_times}")
    if selected_time is not None:
        print(f"  Selected time [days]    : {selected_time:.6f}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R15 TIME-COMPATIBILITY VALIDATION")
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
        FROZEN_ID_TABLE,
        TIME_EVIDENCE_TABLE,
        SOURCE_TRACE_TABLE,
        UPSTREAM_TABLE,
        HASH_MATCH_TABLE,
        COMPAT_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R15 FROZEN SG7D6 PHYSICAL-TIME / MULTI-TIME COMPATIBILITY AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No physical time was assigned by similarity.")
    print("No SG7E performance gate was evaluated.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)

    frozen_db.close()


if __name__ == "__main__":
    main()
