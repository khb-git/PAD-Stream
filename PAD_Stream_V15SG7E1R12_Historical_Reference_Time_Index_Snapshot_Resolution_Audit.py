from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R12
# Historical Reference Time-Index / Snapshot Resolution Audit
#
# FORENSIC SNAPSHOT-IDENTITY MILESTONE
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
# NO SNAPSHOT WILL BE SELECTED BY CANDIDATE PERFORMANCE.
#
# PURPOSE
# -------
# SG7E1R11 established:
#
#   SG7E_TOP_ARTIFACT_LINEAGE_RESOLVED
#
# with:
#
#   ONE_TOP_SG7A_CORRECTED_ARTIFACT_HAS_UNIQUE_AUTHORITATIVE_LINEAGE
#
# and selected:
#
#   output/V15_SG7E/V15SG7E_Plume_Coverage_Validation.npz
#
# containing:
#
#   SG7A_corrected
#
# R12 resolves only the historical snapshot/time index used by the authoritative
# SG7E acceptance workflow.
#
# The audit uses:
#   * selected artifact contents,
#   * times_days or related time arrays,
#   * authoritative SG7E source contexts,
#   * index/slice expressions,
#   * loop/enumeration variables,
#   * diagnostic table time labels,
#   * saved plume/metric arrays indexed by time,
#   * manifest/contract source semantics.
#
# Time chronology alone is not authority.
# Candidate performance is prohibited from snapshot selection.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R12"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R11_DIR = ROOT / "output" / "V15_SG7E1R11"
R11_SUMMARY = R11_DIR / "PAD_Stream_V15SG7E1R11_Summary.json"
R11_CONTRACT = R11_DIR / "V15SG7E1R11_Top_SG7A_Corrected_Lineage_Contract.json"

R8_GATE_TRACE = (
    ROOT / "output" / "V15_SG7E1R8"
    / "V15SG7E1R8_Authoritative_Gate_Consumer_Trace.csv"
)

R10_LOAD_TRACE = (
    ROOT / "output" / "V15_SG7E1R10"
    / "V15SG7E1R10_Artifact_Load_Consumption_Trace.csv"
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

ARTIFACT_ARRAY_TABLE = OUT / "V15SG7E1R12_Selected_Artifact_Array_Inventory.csv"
TIME_AXIS_TABLE = OUT / "V15SG7E1R12_Time_Axis_Inventory.csv"
SOURCE_INDEX_TABLE = OUT / "V15SG7E1R12_Authoritative_Source_Time_Index_Trace.csv"
LOOP_TABLE = OUT / "V15SG7E1R12_Time_Loop_Enumeration_Trace.csv"
SLICE_TABLE = OUT / "V15SG7E1R12_Snapshot_Identity_Audit.csv"
METRIC_TIME_TABLE = OUT / "V15SG7E1R12_Metric_Time_Label_Trace.csv"
DECISION_TABLE = OUT / "V15SG7E1R12_Time_Index_Snapshot_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R12_Historical_Reference_Time_Index_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R12_Summary.json"

REFERENCE_KEY = "SG7A_corrected"
EXPECTED_GRID_SHAPE = (15, 50, 50)

TIME_KEY_CANDIDATES = (
    "times_days",
    "time_days",
    "times",
    "time",
    "snapshot_times_days",
    "evaluation_times_days",
)

INDEX_NAMES = (
    "time_idx",
    "tidx",
    "idx_t",
    "it",
    "itime",
    "snapshot_idx",
    "snapshot_index",
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


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def find_index_patterns(text: str, key: str):
    rows = []
    lines = text.splitlines()

    patterns = [
        re.compile(rf"\b{re.escape(key)}\s*\[\s*([^\]]+)\s*\]", re.I),
        re.compile(
            rf"\[\s*['\"]{re.escape(key)}['\"]\s*\]\s*\[\s*([^\]]+)\s*\]",
            re.I,
        ),
    ]

    for i, line in enumerate(lines, start=1):
        for pat in patterns:
            m = pat.search(line)
            if m:
                rows.append({
                    "line": i,
                    "index_expression": m.group(1).strip(),
                    "raw": line.strip()[:1500],
                })
    return rows


def find_loop_patterns(text: str):
    rows = []
    lines = text.splitlines()

    pats = [
        re.compile(
            r"for\s+([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s+in\s+enumerate\(([^)]+)\)"
        ),
        re.compile(
            r"for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+range\(([^)]+)\)"
        ),
    ]

    for i, line in enumerate(lines, start=1):
        for j, pat in enumerate(pats):
            m = pat.search(line)
            if not m:
                continue

            if j == 0:
                rows.append({
                    "line": i,
                    "kind": "enumerate",
                    "index_symbol": m.group(1),
                    "value_symbol": m.group(2),
                    "iterable": m.group(3).strip(),
                    "raw": line.strip(),
                })
            else:
                rows.append({
                    "line": i,
                    "kind": "range",
                    "index_symbol": m.group(1),
                    "value_symbol": "",
                    "iterable": m.group(2).strip(),
                    "raw": line.strip(),
                })
    return rows


def parse_int(expr):
    try:
        return int(str(expr).strip())
    except Exception:
        return None


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


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R12")
    print("Historical Reference Time-Index / Snapshot Resolution Audit")
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

    r11_summary = load_json(R11_SUMMARY)
    r11_contract = load_json(R11_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r11_summary.get("status") != "SG7E_TOP_ARTIFACT_LINEAGE_RESOLVED":
        raise RuntimeError(
            "R12 requires resolved SG7E1R11 artifact lineage status."
        )

    if r11_summary.get("diagnosis") != (
        "ONE_TOP_SG7A_CORRECTED_ARTIFACT_HAS_UNIQUE_AUTHORITATIVE_LINEAGE"
    ):
        raise RuntimeError(
            "R12 requires R11 unique-authoritative-lineage diagnosis."
        )

    selected_artifact = Path(r11_summary["selected_artifact"]).resolve()

    if not selected_artifact.exists():
        raise FileNotFoundError(
            f"Selected R11 artifact does not exist:\n{selected_artifact}"
        )

    if r11_contract.get("reference_key") != REFERENCE_KEY:
        raise RuntimeError("R12 expected historical key SG7A_corrected.")

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])
    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold must remain resolved.")

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    gate_rows = load_csv(R8_GATE_TRACE)
    load_rows = load_csv(R10_LOAD_TRACE)

    # -------------------------------------------------------------------------
    # Selected artifact inventory.
    # -------------------------------------------------------------------------

    db = np.load(selected_artifact, allow_pickle=True)

    if REFERENCE_KEY not in db.files:
        raise RuntimeError(
            f"Resolved artifact does not contain {REFERENCE_KEY}."
        )

    reference = np.asarray(db[REFERENCE_KEY])

    artifact_array_rows = []
    for key in db.files:
        try:
            arr = np.asarray(db[key])
        except Exception:
            continue
        artifact_array_rows.append({
            "key": key,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "ndim": arr.ndim,
            "size": arr.size,
            "is_reference_key": key == REFERENCE_KEY,
            "is_time_candidate": key.lower() in TIME_KEY_CANDIDATES,
        })

    save_csv(ARTIFACT_ARRAY_TABLE, artifact_array_rows)

    # -------------------------------------------------------------------------
    # Resolve explicit time-axis arrays.
    # -------------------------------------------------------------------------

    time_axis_rows = []
    time_arrays = {}

    for key in db.files:
        lk = key.lower()

        if (
            lk in TIME_KEY_CANDIDATES
            or "time" in lk
            or "days" in lk
        ):
            try:
                arr = np.asarray(db[key]).reshape(-1)
            except Exception:
                continue

            if arr.size <= 1000:
                time_arrays[key] = arr
                time_axis_rows.append({
                    "key": key,
                    "length": arr.size,
                    "dtype": str(arr.dtype),
                    "values": ";".join(str(x) for x in arr.tolist()),
                    "matches_reference_axis0": (
                        reference.ndim == 4 and arr.size == reference.shape[0]
                    ),
                })

    save_csv(TIME_AXIS_TABLE, time_axis_rows)

    # -------------------------------------------------------------------------
    # Build source corpus from authoritative source(s) and load traces.
    # -------------------------------------------------------------------------

    source_paths = sorted({
        Path(r.get("source", ""))
        for r in gate_rows
        if r.get("source", "") and Path(r.get("source", "")).exists()
    })

    load_source_paths = sorted({
        Path(r.get("source", ""))
        for r in load_rows
        if r.get("source", "") and Path(r.get("source", "")).exists()
    })

    source_paths = sorted(set(source_paths + load_source_paths))

    index_rows = []
    loop_rows = []

    for src in source_paths:
        text = safe_text(src)

        for alias in (
            REFERENCE_KEY,
            "SG7A_corrected",
            "reference",
            "reference_grid",
            "reference_saturation",
            "truth",
            "truth_grid",
            "truth_saturation",
        ):
            for hit in find_index_patterns(text, alias):
                index_rows.append({
                    "source": str(src),
                    "alias": alias,
                    "line": hit["line"],
                    "index_expression": hit["index_expression"],
                    "raw": hit["raw"],
                })

        for row in find_loop_patterns(text):
            row2 = dict(row)
            row2["source"] = str(src)
            loop_rows.append(row2)

    save_csv(SOURCE_INDEX_TABLE, index_rows)
    save_csv(LOOP_TABLE, loop_rows)

    # -------------------------------------------------------------------------
    # Search manifests/contracts/tables for explicit snapshot index or time.
    # -------------------------------------------------------------------------

    metric_time_rows = []

    selected_filename = selected_artifact.name
    selected_parent = selected_artifact.parent.name

    for src in project_text_files():
        text = safe_text(src)
        if not text:
            continue

        low = text.lower()

        # Restrict to material mentioning artifact/key/reference lineage.
        relevant = (
            selected_filename.lower() in low
            or selected_parent.lower() in low
            or REFERENCE_KEY.lower() in low
            or "sg7a_corrected" in low
        )

        if not relevant:
            continue

        # Explicit index assignments
        for name in INDEX_NAMES:
            for m in re.finditer(
                rf"\b{re.escape(name)}\b\s*[:=]\s*(\d+)",
                text,
                flags=re.I,
            ):
                metric_time_rows.append({
                    "source": str(src),
                    "kind": "explicit_index",
                    "symbol": name,
                    "value": m.group(1),
                    "raw": m.group(0),
                })

        # Explicit time-day assignments / labels
        for m in re.finditer(
            r"\b(?:time_days|time_day|days|t_days)\b\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
            text,
            flags=re.I,
        ):
            metric_time_rows.append({
                "source": str(src),
                "kind": "explicit_time_days",
                "symbol": "",
                "value": m.group(1),
                "raw": m.group(0),
            })

    save_csv(METRIC_TIME_TABLE, metric_time_rows)

    # -------------------------------------------------------------------------
    # Snapshot identities.
    # -------------------------------------------------------------------------

    snapshot_rows = []

    if reference.ndim == 3:
        snapshot_rows.append({
            "snapshot_index": 0,
            "time_days": "",
            "array_sha256": sha256_array(reference),
            "shape": str(reference.shape),
            "min": float(np.nanmin(reference)),
            "max": float(np.nanmax(reference)),
            "mean": float(np.nanmean(reference)),
        })

    elif reference.ndim == 4 and tuple(reference.shape[1:]) == EXPECTED_GRID_SHAPE:
        # Prefer exact-length time axis.
        chosen_time_key = None
        chosen_times = None

        exact_time_axes = [
            (k, v)
            for k, v in time_arrays.items()
            if len(v) == reference.shape[0]
        ]

        if len(exact_time_axes) == 1:
            chosen_time_key, chosen_times = exact_time_axes[0]

        elif len(exact_time_axes) > 1:
            # If multiple axes are numerically identical, treat as one semantic axis.
            base = np.asarray(exact_time_axes[0][1], dtype=float)
            all_same = all(
                np.allclose(
                    base,
                    np.asarray(v, dtype=float),
                    rtol=0.0,
                    atol=0.0,
                    equal_nan=True,
                )
                for _, v in exact_time_axes[1:]
            )
            if all_same:
                chosen_time_key = ";".join(k for k, _ in exact_time_axes)
                chosen_times = base

        for i in range(reference.shape[0]):
            snapshot_rows.append({
                "snapshot_index": i,
                "time_days": (
                    float(chosen_times[i])
                    if chosen_times is not None
                    else ""
                ),
                "time_axis_key": chosen_time_key or "",
                "array_sha256": sha256_array(reference[i]),
                "shape": str(reference[i].shape),
                "min": float(np.nanmin(reference[i])),
                "max": float(np.nanmax(reference[i])),
                "mean": float(np.nanmean(reference[i])),
            })

    save_csv(SLICE_TABLE, snapshot_rows)

    # -------------------------------------------------------------------------
    # Resolve time index.
    # -------------------------------------------------------------------------

    literal_indices = []

    for r in index_rows:
        v = parse_int(r.get("index_expression", ""))
        if v is not None:
            literal_indices.append(v)

    for r in metric_time_rows:
        if r["kind"] == "explicit_index":
            v = parse_int(r["value"])
            if v is not None:
                literal_indices.append(v)

    unique_indices = sorted(set(literal_indices))

    explicit_times = []
    for r in metric_time_rows:
        if r["kind"] == "explicit_time_days":
            try:
                explicit_times.append(float(r["value"]))
            except Exception:
                pass

    unique_explicit_times = sorted(set(explicit_times))

    selected_index = None
    selected_time_days = None
    resolution_basis = ""

    # 3-D reference needs no time selection.
    if reference.ndim == 3 and tuple(reference.shape) == EXPECTED_GRID_SHAPE:
        selected_index = 0
        resolution_basis = "REFERENCE_ARRAY_ALREADY_3D"

    elif reference.ndim == 4 and tuple(reference.shape[1:]) == EXPECTED_GRID_SHAPE:

        valid_literal_indices = [
            i for i in unique_indices
            if 0 <= i < reference.shape[0]
        ]

        if len(valid_literal_indices) == 1:
            selected_index = valid_literal_indices[0]
            resolution_basis = "UNIQUE_SOURCE_OR_CONTRACT_LITERAL_INDEX"

        else:
            # Try exact unique time-day mapping.
            exact_time_axes = [
                v for v in time_arrays.values()
                if len(v) == reference.shape[0]
            ]

            if exact_time_axes and len(unique_explicit_times) == 1:
                axis = np.asarray(exact_time_axes[0], dtype=float)
                target = unique_explicit_times[0]
                matches = np.where(np.isclose(axis, target, rtol=0.0, atol=1e-12))[0]
                if len(matches) == 1:
                    selected_index = int(matches[0])
                    selected_time_days = float(axis[selected_index])
                    resolution_basis = "UNIQUE_EXPLICIT_TIME_DAYS_MATCH"

        # Fill time from resolved axis if available.
        if selected_index is not None and selected_time_days is None:
            exact_time_axes = [
                v for v in time_arrays.values()
                if len(v) == reference.shape[0]
            ]
            if exact_time_axes:
                axis = np.asarray(exact_time_axes[0], dtype=float)
                if selected_index < len(axis):
                    selected_time_days = float(axis[selected_index])

    time_resolved = selected_index is not None

    checks = [
        ("Incoming R11 artifact lineage resolution reproduced", True),
        ("Historical reference key remains SG7A_corrected", True),
        ("Resolved artifact exists", selected_artifact.exists()),
        ("Historical plume threshold retained", abs(threshold - 0.5) < 1e-15),
        ("Frozen SG7D6 input remains authoritative", True),
        ("Resolved artifact contains SG7A_corrected", REFERENCE_KEY in db.files),
        ("Reference dimensionality audited", reference.ndim in (3, 4)),
        ("Time-axis candidate arrays inventoried", True),
        ("Authoritative source index expressions searched", True),
        ("Loop/enumeration semantics searched", True),
        ("Manifest/contract explicit time labels searched", True),
        ("All reference snapshots independently hashed", len(snapshot_rows) > 0),
        ("No candidate performance used", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No reference field reconstructed or frozen", True),
    ]

    if time_resolved:
        status = "SG7E_HISTORICAL_REFERENCE_SNAPSHOT_RESOLVED"
        diagnosis = "UNIQUE_REFERENCE_TIME_INDEX_ESTABLISHED_FROM_HISTORICAL_PROVENANCE"
        recommendation = (
            "The authoritative SG7A_corrected artifact and historical snapshot are now "
            "resolved. Proceed to exact extraction/persistence of the selected 15x50x50 "
            "reference field, preserve artifact/snapshot hashes, construct the unchanged "
            "S=0.5 reference plume mask, and independently validate reconstruction before "
            "rerunning SG7E deployment gates."
        )
        next_milestone = (
            "V15-SG7E1R13 — Exact Historical Reference Field Reconstruction / Persistence"
        )
    else:
        status = "SG7E_HISTORICAL_REFERENCE_SNAPSHOT_NOT_YET_RESOLVED"
        diagnosis = "ARTIFACT_IDENTITY_RESOLVED_BUT_HISTORICAL_TIME_SELECTOR_REMAINS_AMBIGUOUS"
        recommendation = (
            "Do not reconstruct the reference field yet. The artifact identity is fixed, "
            "but the source does not yet provide one unique snapshot selector. Audit only "
            "the authoritative metric loop, saved per-time metric rows, and times_days "
            "ordering associated with SG7A_corrected."
        )
        next_milestone = (
            "V15-SG7E1R13 — Per-Time Metric / Snapshot Correspondence Audit"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "reference_key": REFERENCE_KEY,
        "selected_artifact": str(selected_artifact),
        "reference_shape": str(reference.shape),
        "snapshot_count": reference.shape[0] if reference.ndim == 4 else 1,
        "time_axis_count": len(time_arrays),
        "index_evidence_records": len(index_rows),
        "loop_records": len(loop_rows),
        "metric_time_records": len(metric_time_rows),
        "literal_indices": ";".join(map(str, unique_indices)),
        "explicit_times_days": ";".join(map(str, unique_explicit_times)),
        "snapshot_resolved": time_resolved,
        "selected_snapshot_index": selected_index if selected_index is not None else "",
        "selected_time_days": selected_time_days if selected_time_days is not None else "",
        "resolution_basis": resolution_basis,
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R12",
            "status": status,
            "diagnosis": diagnosis,
            "reference_key": REFERENCE_KEY,
            "artifact": {
                "path": str(selected_artifact),
                "array_sha256": sha256_array(reference),
                "shape": list(reference.shape),
            },
            "time_selection": {
                "resolved": time_resolved,
                "index": selected_index,
                "time_days": selected_time_days,
                "basis": resolution_basis,
                "literal_index_candidates": unique_indices,
                "explicit_time_day_candidates": unique_explicit_times,
            },
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "constraints": {
                "candidate_performance_used": False,
                "chronology_used_as_authority": False,
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
            "milestone": "V15-SG7E1R12",
            "status": status,
            "diagnosis": diagnosis,
            "artifact_resolved": True,
            "snapshot_resolved": time_resolved,
            "selected_artifact": str(selected_artifact),
            "selected_snapshot_index": selected_index,
            "selected_time_days": selected_time_days,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("RESOLVED REFERENCE ARTIFACT")
    print(f"  Artifact                : {selected_artifact}")
    print(f"  Reference key           : {REFERENCE_KEY}")
    print(f"  Reference shape         : {reference.shape}")

    print("\nTIME / SNAPSHOT EVIDENCE")
    print(f"  Time-axis arrays        : {len(time_arrays)}")
    print(f"  Source index records    : {len(index_rows)}")
    print(f"  Loop records            : {len(loop_rows)}")
    print(f"  Metric time records     : {len(metric_time_rows)}")
    print(f"  Literal index candidates: {unique_indices}")
    print(f"  Explicit times [days]   : {unique_explicit_times}")

    print("\nSNAPSHOT RESOLUTION")
    print(f"  Resolved                : {time_resolved}")
    print(f"  Basis                   : {resolution_basis or 'UNRESOLVED'}")
    if selected_index is not None:
        print(f"  Snapshot index          : {selected_index}")
    if selected_time_days is not None:
        print(f"  Time [days]             : {selected_time_days:.6f}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R12 SNAPSHOT VALIDATION")
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
        ARTIFACT_ARRAY_TABLE,
        TIME_AXIS_TABLE,
        SOURCE_INDEX_TABLE,
        LOOP_TABLE,
        SLICE_TABLE,
        METRIC_TIME_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R12 HISTORICAL REFERENCE TIME-INDEX / SNAPSHOT AUDIT: COMPLETE")
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
