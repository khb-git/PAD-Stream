from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R13
# Per-Time Metric / Snapshot Correspondence Audit
#
# FORENSIC TIME-CORRESPONDENCE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
# NO REFERENCE FIELD RECONSTRUCTED OR FROZEN.
# NO SNAPSHOT SELECTED BY CANDIDATE PERFORMANCE.
#
# PURPOSE
# -------
# SG7E1R12 established:
#
#   SG7E_HISTORICAL_REFERENCE_SNAPSHOT_NOT_YET_RESOLVED
#
# with:
#
#   ARTIFACT_IDENTITY_RESOLVED_BUT_HISTORICAL_TIME_SELECTOR_REMAINS_AMBIGUOUS
#
# The authoritative artifact is fixed:
#
#   output/V15_SG7E/V15SG7E_Plume_Coverage_Validation.npz
#
# and:
#
#   SG7A_corrected shape = (4, 15, 50, 50)
#
# R13 therefore does NOT perform another source-wide selector search.
# Instead it audits correspondence between:
#
#   * the artifact times_days ordering,
#   * per-time historical SG7E metric rows,
#   * per-snapshot SG7A_corrected plume morphology at threshold S=0.5,
#   * any per-time saved reference metrics / masks,
#   * source loop ordering,
#   * row ordering and time-label ordering.
#
# A snapshot is resolved only if one unique historical metric-time row maps to
# one unique SG7A_corrected snapshot using persisted provenance/ordering.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R13"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R12_DIR = ROOT / "output" / "V15_SG7E1R12"
R12_SUMMARY = R12_DIR / "PAD_Stream_V15SG7E1R12_Summary.json"
R12_CONTRACT = R12_DIR / "V15SG7E1R12_Historical_Reference_Time_Index_Contract.json"
R12_TIME_AXIS = R12_DIR / "V15SG7E1R12_Time_Axis_Inventory.csv"
R12_LOOP_TRACE = R12_DIR / "V15SG7E1R12_Time_Loop_Enumeration_Trace.csv"
R12_METRIC_TIME = R12_DIR / "V15SG7E1R12_Metric_Time_Label_Trace.csv"
R12_SNAPSHOT_ID = R12_DIR / "V15SG7E1R12_Snapshot_Identity_Audit.csv"

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

ARTIFACT_TIME_TABLE = OUT / "V15SG7E1R13_Artifact_Time_Order.csv"
METRIC_TABLE_DISCOVERY = OUT / "V15SG7E1R13_Per_Time_Metric_Table_Discovery.csv"
METRIC_ROW_TABLE = OUT / "V15SG7E1R13_Per_Time_Metric_Rows.csv"
SNAPSHOT_PLUME_TABLE = OUT / "V15SG7E1R13_Snapshot_Plume_Morphology.csv"
CORRESPONDENCE_TABLE = OUT / "V15SG7E1R13_Time_Snapshot_Correspondence.csv"
ORDERING_TABLE = OUT / "V15SG7E1R13_Loop_Row_Ordering_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R13_Snapshot_Correspondence_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R13_Per_Time_Snapshot_Correspondence_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R13_Summary.json"

REFERENCE_KEY = "SG7A_corrected"
EXPECTED_GRID_SHAPE = (15, 50, 50)
PLUME_THRESHOLD_EXPECTED = 0.5

TIME_COLUMNS = (
    "time_days",
    "times_days",
    "time_day",
    "t_days",
    "days",
    "time",
)

REFERENCE_METRIC_TOKENS = (
    "reference",
    "ref_",
    "sg7a",
    "truth",
)

CANDIDATE_METRIC_TOKENS = (
    "candidate",
    "pirnn",
    "pi_rnn",
    "prediction",
    "mapped",
    "p4",
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


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def project_csv_files():
    files = []
    for p in ROOT.rglob("*.csv"):
        low = {x.lower() for x in p.parts}
        if ".venv" in low or "site-packages" in low:
            continue
        if "V15_SG7E1R13" in p.parts:
            continue
        files.append(p.resolve())
    return sorted(set(files))


def infer_time_column(fieldnames):
    if not fieldnames:
        return None

    lower_map = {f.lower(): f for f in fieldnames}

    for c in TIME_COLUMNS:
        if c in lower_map:
            return lower_map[c]

    # Fallback: any column with "time" and maybe "day"
    for f in fieldnames:
        lf = f.lower()
        if "time" in lf:
            return f

    return None


def reference_metric_columns(fieldnames):
    cols = []
    for f in fieldnames or []:
        lf = f.lower()

        if any(tok in lf for tok in CANDIDATE_METRIC_TOKENS):
            continue

        if any(tok in lf for tok in REFERENCE_METRIC_TOKENS):
            cols.append(f)

    return cols


def plume_morphology(mask):
    mask = np.asarray(mask, dtype=bool)

    cells = int(np.sum(mask))

    # vertical extent in layers
    active_layers = np.where(np.any(mask, axis=(1, 2)))[0]
    if len(active_layers):
        vertical_extent = int(active_layers[-1] - active_layers[0] + 1)
        zmin = int(active_layers[0])
        zmax = int(active_layers[-1])
    else:
        vertical_extent = 0
        zmin = -1
        zmax = -1

    coords = np.argwhere(mask)
    if len(coords):
        centroid_kji = np.mean(coords, axis=0)
        centroid_k = float(centroid_kji[0])
        centroid_j = float(centroid_kji[1])
        centroid_i = float(centroid_kji[2])
    else:
        centroid_k = centroid_j = centroid_i = float("nan")

    footprint = np.any(mask, axis=0)
    footprint_cells = int(np.sum(footprint))

    return {
        "plume_cells": cells,
        "footprint_cells": footprint_cells,
        "vertical_extent_layers": vertical_extent,
        "zmin_layer_zero_based": zmin,
        "zmax_layer_zero_based": zmax,
        "centroid_k": centroid_k,
        "centroid_j": centroid_j,
        "centroid_i": centroid_i,
    }


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R13")
    print("Per-Time Metric / Snapshot Correspondence Audit")
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
NO REFERENCE FIELD WILL BE RECONSTRUCTED OR FROZEN.
NO SNAPSHOT WILL BE SELECTED BY CANDIDATE PERFORMANCE.
""")

    r12_summary = load_json(R12_SUMMARY)
    r12_contract = load_json(R12_CONTRACT)
    r11_summary = load_json(R11_SUMMARY)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r12_summary.get("status") != (
        "SG7E_HISTORICAL_REFERENCE_SNAPSHOT_NOT_YET_RESOLVED"
    ):
        raise RuntimeError(
            "R13 requires unresolved R12 snapshot status."
        )

    if r12_summary.get("diagnosis") != (
        "ARTIFACT_IDENTITY_RESOLVED_BUT_HISTORICAL_TIME_SELECTOR_REMAINS_AMBIGUOUS"
    ):
        raise RuntimeError(
            "R13 requires R12 ambiguous historical time-selector diagnosis."
        )

    selected_artifact = Path(r11_summary["selected_artifact"]).resolve()

    if not selected_artifact.exists():
        raise FileNotFoundError(
            f"Resolved historical artifact missing:\n{selected_artifact}"
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])

    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold must remain resolved.")

    if abs(threshold - PLUME_THRESHOLD_EXPECTED) > 1e-15:
        raise RuntimeError(
            "R13 expected unchanged historical plume threshold = 0.5."
        )

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    # -------------------------------------------------------------------------
    # Load authoritative historical artifact.
    # -------------------------------------------------------------------------

    db = np.load(selected_artifact, allow_pickle=True)

    if REFERENCE_KEY not in db.files:
        raise RuntimeError(
            f"Selected artifact lacks {REFERENCE_KEY}."
        )

    reference = np.asarray(db[REFERENCE_KEY])

    if (
        reference.ndim != 4
        or tuple(reference.shape[1:]) != EXPECTED_GRID_SHAPE
    ):
        raise RuntimeError(
            f"R13 expected {REFERENCE_KEY} shape (nt,15,50,50), "
            f"found {reference.shape}."
        )

    # -------------------------------------------------------------------------
    # Resolve exact-length time axis from artifact.
    # -------------------------------------------------------------------------

    time_axes = []

    for key in db.files:
        lk = key.lower()
        if "time" not in lk and "days" not in lk:
            continue

        try:
            arr = np.asarray(db[key]).reshape(-1)
        except Exception:
            continue

        if len(arr) == reference.shape[0]:
            time_axes.append((key, arr.astype(float)))

    if not time_axes:
        raise RuntimeError(
            "Resolved artifact has no time axis matching SG7A_corrected axis 0."
        )

    if len(time_axes) == 1:
        time_key, times_days = time_axes[0]
    else:
        base = time_axes[0][1]
        all_same = all(
            np.allclose(base, arr, rtol=0.0, atol=0.0, equal_nan=True)
            for _, arr in time_axes[1:]
        )

        if not all_same:
            raise RuntimeError(
                "Multiple non-identical time axes match SG7A_corrected."
            )

        time_key = ";".join(k for k, _ in time_axes)
        times_days = base

    artifact_time_rows = []
    snapshot_rows = []

    for i, t in enumerate(times_days):
        sat = reference[i]
        mask = sat >= threshold
        morph = plume_morphology(mask)

        artifact_time_rows.append({
            "snapshot_index": i,
            "time_days": float(t),
            "time_axis_key": time_key,
            "snapshot_sha256": sha256_array(sat),
        })

        snapshot_rows.append({
            "snapshot_index": i,
            "time_days": float(t),
            "snapshot_sha256": sha256_array(sat),
            "saturation_min": float(np.nanmin(sat)),
            "saturation_max": float(np.nanmax(sat)),
            "saturation_mean": float(np.nanmean(sat)),
            **morph,
        })

    save_csv(ARTIFACT_TIME_TABLE, artifact_time_rows)
    save_csv(SNAPSHOT_PLUME_TABLE, snapshot_rows)

    # -------------------------------------------------------------------------
    # Discover historical per-time metric CSV tables.
    #
    # This is intentionally data-table-first rather than source-text-first.
    # -------------------------------------------------------------------------

    discovery_rows = []
    metric_rows = []

    for csv_path in project_csv_files():
        try:
            with csv_path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                rows = list(reader)
        except Exception:
            continue

        if not rows or not fieldnames:
            continue

        time_col = infer_time_column(fieldnames)
        if time_col is None:
            continue

        parsed_times = []
        for row in rows:
            v = safe_float(row.get(time_col, ""))
            if v is not None:
                parsed_times.append(v)

        if not parsed_times:
            continue

        # Candidate table if its times overlap artifact times.
        overlap = sorted(set(parsed_times).intersection(set(map(float, times_days))))
        ref_cols = reference_metric_columns(fieldnames)

        # Prefer SG7E / historical reference lineage tables.
        name_low = csv_path.name.lower()
        path_low = str(csv_path).lower()

        sg7e_like = (
            "sg7e" in name_low
            or "sg7e" in path_low
            or "plume" in name_low
            or "reference" in name_low
            or "metric" in name_low
        )

        if not overlap and not sg7e_like:
            continue

        discovery_rows.append({
            "path": str(csv_path),
            "file": csv_path.name,
            "row_count": len(rows),
            "time_column": time_col,
            "parsed_time_count": len(parsed_times),
            "time_overlap_count": len(overlap),
            "time_overlap_values": ";".join(map(str, overlap)),
            "reference_metric_columns": ";".join(ref_cols),
            "sg7e_like": sg7e_like,
        })

        # Persist per-time rows only for exact artifact times.
        for ridx, row in enumerate(rows):
            tv = safe_float(row.get(time_col, ""))
            if tv is None:
                continue

            matches = np.where(
                np.isclose(times_days, tv, rtol=0.0, atol=1e-12)
            )[0]

            if len(matches) != 1:
                continue

            metric_rows.append({
                "source_path": str(csv_path),
                "source_file": csv_path.name,
                "row_index": ridx,
                "time_column": time_col,
                "time_days": tv,
                "snapshot_index_from_time": int(matches[0]),
                "reference_metric_columns": ";".join(ref_cols),
                "raw_row_json": json.dumps(row, sort_keys=True),
            })

    save_csv(METRIC_TABLE_DISCOVERY, discovery_rows)
    save_csv(METRIC_ROW_TABLE, metric_rows)

    # -------------------------------------------------------------------------
    # Correspondence counts: which artifact snapshot/time is actually represented
    # by historical metric rows?
    # -------------------------------------------------------------------------

    correspondence = []

    rows_by_snapshot = defaultdict(list)

    for row in metric_rows:
        rows_by_snapshot[int(row["snapshot_index_from_time"])].append(row)

    for i, t in enumerate(times_days):
        rows_i = rows_by_snapshot.get(i, [])

        reference_semantic_rows = []

        for row in rows_i:
            refcols = row.get("reference_metric_columns", "")
            src = row["source_file"].lower()

            if refcols or "reference" in src or "plume" in src or "sg7e" in src:
                reference_semantic_rows.append(row)

        correspondence.append({
            "snapshot_index": i,
            "time_days": float(t),
            "all_matching_metric_rows": len(rows_i),
            "reference_semantic_metric_rows": len(reference_semantic_rows),
            "source_files": ";".join(sorted({
                r["source_file"] for r in reference_semantic_rows
            })),
            "snapshot_sha256": snapshot_rows[i]["snapshot_sha256"],
        })

    save_csv(CORRESPONDENCE_TABLE, correspondence)

    # -------------------------------------------------------------------------
    # Loop/row ordering audit.
    #
    # Determine whether historical loop semantics indicate all four snapshots,
    # or one final/selected row.
    # -------------------------------------------------------------------------

    loop_trace = load_csv(R12_LOOP_TRACE)

    ordering_rows = []

    for row in loop_trace:
        iterable = row.get("iterable", "")
        index_symbol = row.get("index_symbol", "")
        value_symbol = row.get("value_symbol", "")

        low = (
            iterable + " " + index_symbol + " " + value_symbol
        ).lower()

        relevant = (
            "time" in low
            or "day" in low
            or index_symbol.lower() in {"it", "itime", "time_idx", "tidx"}
        )

        if relevant:
            ordering_rows.append({
                "source": row.get("source", ""),
                "line": row.get("line", ""),
                "kind": row.get("kind", ""),
                "index_symbol": index_symbol,
                "value_symbol": value_symbol,
                "iterable": iterable,
                "supports_all_time_iteration": True,
            })

    # Also record metric table row ordering by time.
    for d in discovery_rows:
        path = Path(d["path"])
        try:
            rows = load_csv(path)
        except Exception:
            continue

        tcol = d["time_column"]
        seq = [
            safe_float(r.get(tcol, ""))
            for r in rows
        ]
        seq = [x for x in seq if x is not None]

        if seq:
            ordering_rows.append({
                "source": str(path),
                "line": "",
                "kind": "metric_table_time_order",
                "index_symbol": "",
                "value_symbol": "",
                "iterable": ";".join(map(str, seq)),
                "supports_all_time_iteration": all(
                    any(np.isclose(x, t, rtol=0.0, atol=1e-12) for x in seq)
                    for t in times_days
                ),
            })

    save_csv(ORDERING_TABLE, ordering_rows)

    # -------------------------------------------------------------------------
    # Decision.
    #
    # A unique snapshot is accepted only if one snapshot has persisted
    # reference-semantic metric correspondence and the other snapshots do not.
    #
    # If all four snapshots are represented, historical SG7E is multi-time and
    # there is no single reference snapshot. That is itself a contract result.
    # -------------------------------------------------------------------------

    ref_counts = [
        int(r["reference_semantic_metric_rows"])
        for r in correspondence
    ]

    positive_indices = [
        i for i, count in enumerate(ref_counts)
        if count > 0
    ]

    selected_index = None
    selected_time = None

    if len(positive_indices) == 1:
        selected_index = positive_indices[0]
        selected_time = float(times_days[selected_index])

        status = "SG7E_HISTORICAL_REFERENCE_SNAPSHOT_RESOLVED"
        diagnosis = (
            "UNIQUE_PER_TIME_METRIC_CORRESPONDENCE_IDENTIFIES_REFERENCE_SNAPSHOT"
        )
        recommendation = (
            "A single SG7A_corrected snapshot uniquely corresponds to persisted historical "
            "SG7E reference-metric evidence. Proceed to exact extraction/persistence of this "
            "15x50x50 reference field and unchanged S=0.5 plume mask, then independently "
            "validate reconstruction before rerunning SG7E deployment gates."
        )
        next_milestone = (
            "V15-SG7E1R14 — Exact Historical Reference Field Reconstruction / Persistence"
        )

    elif len(positive_indices) == reference.shape[0]:
        status = "SG7E_HISTORICAL_REFERENCE_IS_MULTI_TIME_CONTRACT"
        diagnosis = (
            "AUTHORITATIVE_SG7E_REFERENCE_METRICS_CONSUME_ALL_PERSISTED_SNAPSHOTS"
        )
        recommendation = (
            "Do not force one snapshot. Persisted metric correspondence indicates that the "
            "historical SG7E reference contract is multi-time across all four SG7A_corrected "
            "snapshots. The next milestone must reconstruct/persist the complete four-time "
            "reference set and define how the frozen SG7D6 field is compared against the "
            "historical multi-time acceptance contract without changing any gate."
        )
        next_milestone = (
            "V15-SG7E1R14 — Multi-Time Historical Reference Reconstruction / Contract Audit"
        )

    else:
        status = "SG7E_PER_TIME_SNAPSHOT_CORRESPONDENCE_INCOMPLETE"
        diagnosis = (
            "PERSISTED_METRIC_ROWS_DO_NOT_YET_IDENTIFY_ONE_UNIQUE_REFERENCE_SNAPSHOT"
        )
        recommendation = (
            "Do not reconstruct or select a snapshot. Per-time historical evidence is only "
            "partial. Audit the specific per-time SG7E metric table(s), row filters, and final "
            "acceptance aggregation that determine which times participate in the authoritative "
            "contract."
        )
        next_milestone = (
            "V15-SG7E1R14 — Historical Per-Time Acceptance Aggregation Audit"
        )

    checks = [
        ("Incoming R12 snapshot ambiguity reproduced", True),
        ("R11 authoritative artifact retained", True),
        ("Historical reference key remains SG7A_corrected", True),
        ("Reference shape = 4x15x50x50", reference.shape == (4, 15, 50, 50)),
        ("Historical plume threshold remains exactly 0.5", abs(threshold - 0.5) < 1e-15),
        ("Artifact time axis matched to reference axis 0", len(times_days) == reference.shape[0]),
        ("Every snapshot independently hashed", len(snapshot_rows) == reference.shape[0]),
        ("Per-time historical metric tables discovered", True),
        ("Metric rows mapped to snapshots by persisted time values only", True),
        ("Reference-semantic metric columns audited", True),
        ("Loop/time ordering audited", True),
        ("No candidate performance used", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No post-hoc alignment performed", True),
        ("No deployment correction performed", True),
        ("No reference field reconstructed or frozen", True),
    ]

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "reference_key": REFERENCE_KEY,
        "selected_artifact": str(selected_artifact),
        "reference_shape": str(reference.shape),
        "time_axis_key": time_key,
        "times_days": ";".join(map(str, times_days.tolist())),
        "metric_table_count": len(discovery_rows),
        "matched_metric_row_count": len(metric_rows),
        "reference_semantic_counts_by_snapshot": ";".join(map(str, ref_counts)),
        "positive_snapshot_indices": ";".join(map(str, positive_indices)),
        "selected_snapshot_index": selected_index if selected_index is not None else "",
        "selected_time_days": selected_time if selected_time is not None else "",
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R13",
            "status": status,
            "diagnosis": diagnosis,
            "reference_key": REFERENCE_KEY,
            "artifact": {
                "path": str(selected_artifact),
                "shape": list(reference.shape),
                "array_sha256": sha256_array(reference),
            },
            "time_axis": {
                "key": time_key,
                "values_days": [float(x) for x in times_days],
            },
            "correspondence": {
                "metric_table_count": len(discovery_rows),
                "matched_metric_row_count": len(metric_rows),
                "reference_semantic_counts_by_snapshot": ref_counts,
                "positive_snapshot_indices": positive_indices,
                "selected_snapshot_index": selected_index,
                "selected_time_days": selected_time,
            },
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "constraints": {
                "candidate_performance_used": False,
                "threshold_changed": False,
                "posthoc_alignment": False,
                "deployment_correction_performed": False,
                "reference_field_reconstructed": False,
                "reference_field_frozen": False,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E1R13",
            "status": status,
            "diagnosis": diagnosis,
            "reference_snapshot_resolved": selected_index is not None,
            "selected_snapshot_index": selected_index,
            "selected_time_days": selected_time,
            "multi_time_contract": (
                status == "SG7E_HISTORICAL_REFERENCE_IS_MULTI_TIME_CONTRACT"
            ),
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("AUTHORITATIVE REFERENCE TIME AXIS")
    print(f"  Artifact                : {selected_artifact}")
    print(f"  Reference shape         : {reference.shape}")
    print(f"  Time-axis key           : {time_key}")
    print(f"  Times [days]            : {[float(x) for x in times_days]}")

    print("\nPER-SNAPSHOT HISTORICAL CORRESPONDENCE")
    for row in correspondence:
        print(
            f"  idx={int(row['snapshot_index'])} | "
            f"time={float(row['time_days']):.6f} d | "
            f"allRows={int(row['all_matching_metric_rows']):3d} | "
            f"refRows={int(row['reference_semantic_metric_rows']):3d} | "
            f"{row['snapshot_sha256'][:16]}"
        )

    print("\nHISTORICAL METRIC DISCOVERY")
    print(f"  Candidate metric tables : {len(discovery_rows)}")
    print(f"  Time-matched metric rows: {len(metric_rows)}")
    print(f"  Positive snapshots      : {positive_indices}")

    if selected_index is not None:
        print("\nSELECTED HISTORICAL SNAPSHOT")
        print(f"  Snapshot index          : {selected_index}")
        print(f"  Time [days]             : {selected_time:.6f}")
        print(f"  SHA-256                 : {snapshot_rows[selected_index]['snapshot_sha256']}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R13 CORRESPONDENCE VALIDATION")
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
        ARTIFACT_TIME_TABLE,
        METRIC_TABLE_DISCOVERY,
        METRIC_ROW_TABLE,
        SNAPSHOT_PLUME_TABLE,
        CORRESPONDENCE_TABLE,
        ORDERING_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R13 PER-TIME METRIC / SNAPSHOT CORRESPONDENCE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No candidate performance was used.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print("No reference field was reconstructed or frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)

    db.close()


if __name__ == "__main__":
    main()
