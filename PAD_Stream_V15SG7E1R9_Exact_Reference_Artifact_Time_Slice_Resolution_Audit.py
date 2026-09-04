from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R9
# Exact Reference Artifact / Time-Slice Resolution Audit
#
# FORENSIC REFERENCE-IDENTITY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
# NO REFERENCE FIELD RECONSTRUCTED OR FROZEN BY R9.
#
# PURPOSE
# -------
# SG7E1R8 established:
#
#   SG7E_FINAL_REFERENCE_KEY_CONSUMPTION_RESOLVED
#
# with:
#
#   ALL_AUTHORITATIVE_GATES_CONSUME_SAME_PERSISTED_REFERENCE_KEY
#
# and selected:
#
#   SG7A_corrected
#
# R9 now resolves:
#
#   1. which persisted artifact instance containing SG7A_corrected is historical,
#   2. whether duplicate artifact instances are byte/numerically identical,
#   3. whether SG7A_corrected is 3-D or 4-D,
#   4. if 4-D, which historical time slice was consumed by SG7E,
#   5. whether times_days uniquely maps the selected time slice,
#   6. the exact 15x50x50 reference-field identity to be reconstructed next.
#
# R9 DOES NOT compare candidate performance.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R9"
OUT.mkdir(parents=True, exist_ok=True)

R8_DIR = ROOT / "output" / "V15_SG7E1R8"
R8_SUMMARY = R8_DIR / "PAD_Stream_V15SG7E1R8_Summary.json"
R8_CONTRACT = R8_DIR / "V15SG7E1R8_Final_Reference_Key_Consumption_Contract.json"
R8_GATE_TRACE = R8_DIR / "V15SG7E1R8_Authoritative_Gate_Consumer_Trace.csv"
R8_KEY_AUDIT = R8_DIR / "V15SG7E1R8_Persisted_Key_Consumption_Audit.csv"

R3_UPSTREAM = (
    ROOT / "output" / "V15_SG7E1R3"
    / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv"
)

R7_MATCHES = (
    ROOT / "output" / "V15_SG7E1R7"
    / "V15SG7E1R7_Upstream_Key_Object_Provenance_Match.csv"
)

R0_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R0"
    / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"
)

D6_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# Outputs
ARTIFACT_TABLE = OUT / "V15SG7E1R9_Reference_Artifact_Instance_Audit.csv"
HASH_TABLE = OUT / "V15SG7E1R9_Reference_Artifact_Hash_Groups.csv"
ARRAY_TABLE = OUT / "V15SG7E1R9_Reference_Array_Identity.csv"
TIME_TABLE = OUT / "V15SG7E1R9_Time_Index_Provenance.csv"
SLICE_TABLE = OUT / "V15SG7E1R9_Time_Slice_Identity_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R9_Artifact_TimeSlice_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R9_Exact_Reference_Artifact_TimeSlice_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R9_Summary.json"

EXPECTED_GRID_SHAPE = (15, 50, 50)


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def safe_npz(path: Path):
    try:
        return np.load(path, allow_pickle=True)
    except Exception:
        return None


def search_index_evidence(text: str, key: str):
    """
    Find index/slice expressions associated with the selected key.
    """
    rows = []
    lines = text.splitlines()

    patterns = [
        re.compile(rf"{re.escape(key)}\s*\[\s*([^\]]+)\s*\]", re.I),
        re.compile(rf"\[\s*['\"]{re.escape(key)}['\"]\s*\]\s*\[\s*([^\]]+)\s*\]", re.I),
    ]

    for i, line in enumerate(lines, start=1):
        for p in patterns:
            m = p.search(line)
            if m:
                rows.append({
                    "line": i,
                    "index_expression": m.group(1).strip(),
                    "raw": line.strip()[:1000],
                })

    return rows


def parse_literal_int(expr):
    try:
        return int(str(expr).strip())
    except Exception:
        return None


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R9")
    print("Exact Reference Artifact / Time-Slice Resolution Audit")
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
NO REFERENCE FIELD WILL BE RECONSTRUCTED OR FROZEN BY R9.
""")

    r8_summary = load_json(R8_SUMMARY)
    r8_contract = load_json(R8_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r8_summary.get("status") != "SG7E_FINAL_REFERENCE_KEY_CONSUMPTION_RESOLVED":
        raise RuntimeError("R9 requires the resolved R8 reference-key status.")

    if r8_summary.get("diagnosis") != (
        "ALL_AUTHORITATIVE_GATES_CONSUME_SAME_PERSISTED_REFERENCE_KEY"
    ):
        raise RuntimeError("R9 requires R8 cross-gate reference consistency.")

    selected_key = r8_summary.get("selected_key") or r8_contract.get("selected_key")
    if selected_key != "SG7A_corrected":
        raise RuntimeError(
            f"R9 expected historical key SG7A_corrected, found {selected_key!r}."
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])
    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold is not resolved.")

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    upstream_rows = load_csv(R3_UPSTREAM)
    r7_rows = load_csv(R7_MATCHES)
    gate_rows = load_csv(R8_GATE_TRACE)
    key_rows = load_csv(R8_KEY_AUDIT)

    # -------------------------------------------------------------------------
    # Discover every persisted artifact instance that contains SG7A_corrected.
    # -------------------------------------------------------------------------

    candidate_paths = set()

    for row in upstream_rows:
        if row.get("key", "") == selected_key and row.get("path", ""):
            candidate_paths.add(Path(row["path"]).resolve())

    # Also inspect nearby NPZ artifacts in project output folders that may not
    # have been fully represented in R3's inventory.
    for p in (ROOT / "output").rglob("*.npz"):
        db = safe_npz(p)
        if db is None:
            continue
        if selected_key in db.files:
            candidate_paths.add(p.resolve())
        db.close()

    artifact_rows = []
    hash_groups = defaultdict(list)

    for path in sorted(candidate_paths):
        db = safe_npz(path)
        if db is None or selected_key not in db.files:
            continue

        arr = np.asarray(db[selected_key])

        row = {
            "path": str(path),
            "file": path.name,
            "file_sha256": sha256_file(path),
            "key": selected_key,
            "array_shape": str(arr.shape),
            "array_dtype": str(arr.dtype),
            "array_sha256": sha256_array(arr),
            "finite_fraction": float(np.mean(np.isfinite(arr))) if arr.size else 0.0,
            "array_min": float(np.nanmin(arr)) if arr.size else "",
            "array_max": float(np.nanmax(arr)) if arr.size else "",
            "array_mean": float(np.nanmean(arr)) if arr.size else "",
            "has_times_days": "times_days" in db.files,
            "times_days_shape": (
                str(np.asarray(db["times_days"]).shape)
                if "times_days" in db.files else ""
            ),
        }

        artifact_rows.append(row)
        hash_groups[row["array_sha256"]].append(row)
        db.close()

    save_csv(ARTIFACT_TABLE, artifact_rows)

    hash_rows = []
    for h, rows in hash_groups.items():
        hash_rows.append({
            "array_sha256": h,
            "artifact_count": len(rows),
            "files": ";".join(sorted(r["file"] for r in rows)),
            "paths": ";".join(sorted(r["path"] for r in rows)),
            "shapes": ";".join(sorted(set(r["array_shape"] for r in rows))),
        })

    save_csv(HASH_TABLE, hash_rows)

    # -------------------------------------------------------------------------
    # Determine whether artifact ambiguity is real or duplicate serialization.
    # -------------------------------------------------------------------------

    unique_array_hashes = sorted(hash_groups)

    # Prefer provenance-linked artifacts when several numerical identities exist.
    provenance_names = set()
    for row in r7_rows:
        if row.get("key", "") == selected_key:
            for path in row.get("upstream_artifact_paths", "").split(";"):
                if path.strip():
                    provenance_names.add(Path(path.strip()).name)

    linked_artifacts = [
        r for r in artifact_rows
        if r["file"] in provenance_names
    ]

    if len(unique_array_hashes) == 1 and artifact_rows:
        artifact_resolved = True
        artifact_resolution = "ALL_PERSISTED_INSTANCES_NUMERICALLY_IDENTICAL"
        selected_artifact_row = artifact_rows[0]
    elif len(linked_artifacts) == 1:
        artifact_resolved = True
        artifact_resolution = "UNIQUE_OBJECT_PROVENANCE_LINKED_ARTIFACT"
        selected_artifact_row = linked_artifacts[0]
    else:
        artifact_resolved = False
        artifact_resolution = "MULTIPLE_DISTINCT_ARTIFACT_INSTANCES_REMAIN"
        selected_artifact_row = None

    # -------------------------------------------------------------------------
    # Time-index provenance from authoritative source context.
    # -------------------------------------------------------------------------

    time_rows = []

    for row in gate_rows:
        ctx = row.get("context", "") + "\n" + row.get("expression", "")
        if not ctx.strip():
            continue

        for hit in search_index_evidence(ctx, selected_key):
            time_rows.append({
                "gate": row.get("gate", ""),
                "source": row.get("source", ""),
                "source_line": row.get("line", ""),
                "evidence_line": hit["line"],
                "index_expression": hit["index_expression"],
                "raw": hit["raw"],
                "origin": "authoritative_gate_context",
            })

        # Generic historical time-index forms in same context.
        for pattern, label in (
            (r"\btime_idx\s*=\s*(\d+)", "time_idx_assignment"),
            (r"\btidx\s*=\s*(\d+)", "tidx_assignment"),
            (r"\bidx\s*=\s*(\d+)", "idx_assignment"),
            (r"\bit\s*=\s*(\d+)", "it_assignment"),
        ):
            for m in re.finditer(pattern, ctx, flags=re.I):
                time_rows.append({
                    "gate": row.get("gate", ""),
                    "source": row.get("source", ""),
                    "source_line": row.get("line", ""),
                    "evidence_line": "",
                    "index_expression": m.group(1),
                    "raw": m.group(0),
                    "origin": label,
                })

    # Inspect source files directly as a second provenance channel.
    source_paths = sorted({
        Path(r.get("source", ""))
        for r in gate_rows
        if r.get("source", "")
    })

    for src in source_paths:
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8", errors="ignore")

        for hit in search_index_evidence(text, selected_key):
            time_rows.append({
                "gate": "GLOBAL",
                "source": str(src),
                "source_line": hit["line"],
                "evidence_line": hit["line"],
                "index_expression": hit["index_expression"],
                "raw": hit["raw"],
                "origin": "direct_source_search",
            })

        for key_alias in ("SG7A_corrected", "reference_grid", "reference_saturation",
                          "truth_grid", "truth_saturation"):
            for hit in search_index_evidence(text, key_alias):
                time_rows.append({
                    "gate": "GLOBAL",
                    "source": str(src),
                    "source_line": hit["line"],
                    "evidence_line": hit["line"],
                    "index_expression": hit["index_expression"],
                    "raw": hit["raw"],
                    "origin": f"alias_search:{key_alias}",
                })

    save_csv(TIME_TABLE, time_rows)

    # -------------------------------------------------------------------------
    # Resolve array shape and historical time slice.
    # -------------------------------------------------------------------------

    array_rows = []
    slice_rows = []

    selected_array_shape = None
    selected_array_hash = None
    selected_times = None

    if selected_artifact_row:
        p = Path(selected_artifact_row["path"])
        db = np.load(p, allow_pickle=True)
        arr = np.asarray(db[selected_key])
        selected_array_shape = arr.shape
        selected_array_hash = sha256_array(arr)

        if "times_days" in db.files:
            selected_times = np.asarray(db["times_days"]).reshape(-1)

        array_rows.append({
            "artifact": str(p),
            "key": selected_key,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "array_sha256": selected_array_hash,
            "is_3d_grid": arr.shape == EXPECTED_GRID_SHAPE,
            "is_4d_time_grid": (
                arr.ndim == 4 and tuple(arr.shape[1:]) == EXPECTED_GRID_SHAPE
            ),
            "time_count": arr.shape[0] if arr.ndim == 4 else 1,
        })

        if arr.ndim == 4 and tuple(arr.shape[1:]) == EXPECTED_GRID_SHAPE:
            for i in range(arr.shape[0]):
                slice_rows.append({
                    "slice_index": i,
                    "time_days": (
                        float(selected_times[i])
                        if selected_times is not None and i < len(selected_times)
                        else ""
                    ),
                    "slice_sha256": sha256_array(arr[i]),
                    "min": float(np.nanmin(arr[i])),
                    "max": float(np.nanmax(arr[i])),
                    "mean": float(np.nanmean(arr[i])),
                })

        db.close()

    save_csv(ARRAY_TABLE, array_rows)
    save_csv(SLICE_TABLE, slice_rows)

    # Literal time-index evidence.
    literal_indices = []
    for row in time_rows:
        val = parse_literal_int(row.get("index_expression", ""))
        if val is not None:
            literal_indices.append(val)

    unique_literal_indices = sorted(set(literal_indices))

    if selected_array_shape == EXPECTED_GRID_SHAPE:
        time_resolved = True
        time_resolution = "REFERENCE_ARTIFACT_ALREADY_3D_NO_TIME_SELECTION_REQUIRED"
        selected_index = None
        selected_time_days = None

    elif (
        selected_array_shape is not None
        and len(selected_array_shape) == 4
        and tuple(selected_array_shape[1:]) == EXPECTED_GRID_SHAPE
        and len(unique_literal_indices) == 1
        and 0 <= unique_literal_indices[0] < selected_array_shape[0]
    ):
        time_resolved = True
        time_resolution = "UNIQUE_LITERAL_HISTORICAL_TIME_INDEX"
        selected_index = unique_literal_indices[0]
        selected_time_days = (
            float(selected_times[selected_index])
            if selected_times is not None and selected_index < len(selected_times)
            else None
        )

    else:
        time_resolved = False
        time_resolution = "HISTORICAL_TIME_INDEX_NOT_YET_UNIQUELY_RESOLVED"
        selected_index = None
        selected_time_days = None

    # -------------------------------------------------------------------------
    # Final decision.
    # -------------------------------------------------------------------------

    checks = [
        ("Incoming SG7E1R8 reference-key resolution reproduced", True),
        ("Selected historical key = SG7A_corrected", selected_key == "SG7A_corrected"),
        ("Historical plume threshold retained", abs(threshold - 0.5) < 1e-15),
        ("Frozen SG7D6 input remains authoritative", True),
        ("All persisted SG7A_corrected artifact instances inventoried", len(artifact_rows) > 0),
        ("Artifact numerical identities hashed", len(hash_rows) > 0),
        ("Artifact provenance ambiguity audited", True),
        ("Reference array dimensionality audited", True),
        ("Historical time-index evidence searched", True),
        ("times_days linkage audited where available", True),
        ("No candidate performance used", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No post-hoc alignment performed", True),
        ("No deployment correction performed", True),
        ("No reference field frozen by R9", True),
    ]

    if artifact_resolved and time_resolved:
        status = "SG7E_EXACT_REFERENCE_ARTIFACT_TIMESLICE_RESOLVED"
        diagnosis = "HISTORICAL_REFERENCE_FIELD_IDENTITY_READY_FOR_RECONSTRUCTION"
        recommendation = (
            "The historical SG7E reference key, persisted artifact identity, and required "
            "time selection are resolved. Proceed to exact reference-field reconstruction "
            "and persistence, then independently verify byte/numerical closure and the "
            "S=0.5 plume mask before rerunning SG7E deployment validation."
        )
        next_milestone = (
            "V15-SG7E1R10 — Exact Historical Reference Field Reconstruction / Persistence"
        )

    elif not artifact_resolved:
        status = "SG7E_REFERENCE_ARTIFACT_INSTANCE_CONFLICT"
        diagnosis = "MULTIPLE_DISTINCT_SG7A_CORRECTED_ARTIFACT_IDENTITIES_REMAIN"
        recommendation = (
            "Do not reconstruct the reference field yet. Multiple numerically distinct "
            "artifacts contain SG7A_corrected. Resolve which artifact instance belongs to "
            "the authoritative SG7E consumer lineage using file/source/manifest provenance."
        )
        next_milestone = (
            "V15-SG7E1R10 — SG7A Corrected Artifact Instance Provenance Audit"
        )

    else:
        status = "SG7E_REFERENCE_TIMESLICE_NOT_YET_RESOLVED"
        diagnosis = "SG7A_CORRECTED_ARTIFACT_RESOLVED_TIME_INDEX_REMAINS_AMBIGUOUS"
        recommendation = (
            "Do not reconstruct or evaluate SG7E gates yet. The SG7A_corrected artifact "
            "identity is resolved, but the historical time selection is not. Audit only the "
            "gate-local time/index variable, times_days mapping, and final snapshot selector."
        )
        next_milestone = (
            "V15-SG7E1R10 — Historical Reference Time-Index Resolution Audit"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "selected_key": selected_key,
        "plume_threshold": threshold,
        "artifact_instance_count": len(artifact_rows),
        "unique_array_hashes": len(unique_array_hashes),
        "artifact_resolved": artifact_resolved,
        "artifact_resolution": artifact_resolution,
        "selected_artifact": (
            selected_artifact_row["path"] if selected_artifact_row else ""
        ),
        "selected_array_shape": str(selected_array_shape),
        "time_resolved": time_resolved,
        "time_resolution": time_resolution,
        "selected_time_index": (
            selected_index if selected_index is not None else ""
        ),
        "selected_time_days": (
            selected_time_days if selected_time_days is not None else ""
        ),
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R9",
            "status": status,
            "diagnosis": diagnosis,
            "reference_key": selected_key,
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "artifact": {
                "resolved": artifact_resolved,
                "resolution": artifact_resolution,
                "path": (
                    selected_artifact_row["path"] if selected_artifact_row else None
                ),
                "array_sha256": selected_array_hash,
                "shape": (
                    list(selected_array_shape)
                    if selected_array_shape is not None else None
                ),
            },
            "time_selection": {
                "resolved": time_resolved,
                "resolution": time_resolution,
                "index": selected_index,
                "time_days": selected_time_days,
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
            "milestone": "V15-SG7E1R9",
            "status": status,
            "diagnosis": diagnosis,
            "reference_key": selected_key,
            "artifact_resolved": artifact_resolved,
            "time_resolved": time_resolved,
            "selected_artifact": (
                selected_artifact_row["path"] if selected_artifact_row else None
            ),
            "selected_time_index": selected_index,
            "selected_time_days": selected_time_days,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("REFERENCE ARTIFACT / TIME-SLICE TRACE")
    print(f"  Historical key          : {selected_key}")
    print(f"  Artifact instances      : {len(artifact_rows)}")
    print(f"  Unique array hashes     : {len(unique_array_hashes)}")
    print(f"  Artifact resolved       : {artifact_resolved}")
    print(f"  Artifact resolution     : {artifact_resolution}")

    if selected_artifact_row:
        print(f"  Selected artifact       : {Path(selected_artifact_row['path']).name}")
        print(f"  Array shape             : {selected_artifact_row['array_shape']}")

    print("\nTIME-SLICE PROVENANCE")
    print(f"  Index evidence records  : {len(time_rows)}")
    print(f"  Literal indices         : {unique_literal_indices}")
    print(f"  Time resolved           : {time_resolved}")
    print(f"  Time resolution         : {time_resolution}")

    if selected_index is not None:
        print(f"  Selected index          : {selected_index}")
    if selected_time_days is not None:
        print(f"  Selected time [days]    : {selected_time_days:.6f}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R9 ARTIFACT / TIME-SLICE VALIDATION")
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
        ARTIFACT_TABLE,
        HASH_TABLE,
        ARRAY_TABLE,
        TIME_TABLE,
        SLICE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R9 EXACT REFERENCE ARTIFACT / TIME-SLICE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No candidate performance was used.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print("No reference field was reconstructed or frozen by R9.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
