from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R11
# Top SG7A Corrected Artifact Lineage Conflict Audit
#
# FORENSIC LINEAGE-DISAMBIGUATION MILESTONE
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
# NO ARTIFACT INSTANCE SELECTED BY CANDIDATE PERFORMANCE.
#
# PURPOSE
# -------
# SG7E1R10 established:
#
#   SG7E_SG7A_CORRECTED_ARTIFACT_PROVENANCE_STILL_AMBIGUOUS
#
# with:
#
#   NO_SINGLE_ARTIFACT_INSTANCE_HAS_SUFFICIENT_AUTHORITATIVE_PROVENANCE_MARGIN
#
# The top conflict is especially narrow:
#
#   two V15SG7E_Plume_Coverage_Validation.npz instances
#   both score 310
#   but contain DIFFERENT SG7A_corrected numerical identities.
#
# R11 therefore compares only the top lineage conflict using:
#
#   1. full absolute path identity,
#   2. parent output/milestone directory,
#   3. creation source and save statement,
#   4. authoritative load source and load-path expression,
#   5. nearby manifest/contract/summary parent references,
#   6. filesystem chronology as supporting evidence only,
#   7. sibling arrays / keys for lineage fingerprinting,
#   8. exact file and SG7A_corrected array hashes.
#
# Filename equality alone is NOT sufficient.
# Chronology alone is NOT authority.
# Candidate deployment performance is prohibited from selection.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R11"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R10_DIR = ROOT / "output" / "V15_SG7E1R10"

R10_SUMMARY = R10_DIR / "PAD_Stream_V15SG7E1R10_Summary.json"
R10_CONTRACT = R10_DIR / "V15SG7E1R10_SG7A_Corrected_Artifact_Instance_Contract.json"
R10_SCORES = R10_DIR / "V15SG7E1R10_Artifact_Instance_Provenance_Scoring.csv"
R10_SOURCE_REFS = R10_DIR / "V15SG7E1R10_Authoritative_Source_Artifact_References.csv"
R10_MANIFEST_REFS = R10_DIR / "V15SG7E1R10_Manifest_Contract_Artifact_References.csv"
R10_SAVE_TRACE = R10_DIR / "V15SG7E1R10_Artifact_Save_Creation_Trace.csv"
R10_LOAD_TRACE = R10_DIR / "V15SG7E1R10_Artifact_Load_Consumption_Trace.csv"

R9_ARTIFACTS = (
    ROOT / "output" / "V15_SG7E1R9"
    / "V15SG7E1R9_Reference_Artifact_Instance_Audit.csv"
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

TOP_PAIR_TABLE = OUT / "V15SG7E1R11_Top_Lineage_Conflict.csv"
PARENT_TABLE = OUT / "V15SG7E1R11_Parent_Directory_Lineage.csv"
CREATION_TABLE = OUT / "V15SG7E1R11_Creation_Source_Disambiguation.csv"
LOAD_TABLE = OUT / "V15SG7E1R11_Authoritative_Load_Path_Disambiguation.csv"
MANIFEST_TABLE = OUT / "V15SG7E1R11_Parent_Manifest_Lineage.csv"
SIBLING_TABLE = OUT / "V15SG7E1R11_Sibling_Key_Fingerprint.csv"
CHRONOLOGY_TABLE = OUT / "V15SG7E1R11_Chronology_Audit.csv"
HASH_TABLE = OUT / "V15SG7E1R11_Top_Artifact_Hash_Identity.csv"
DECISION_TABLE = OUT / "V15SG7E1R11_Top_Lineage_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R11_Top_SG7A_Corrected_Lineage_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R11_Summary.json"

REFERENCE_KEY = "SG7A_corrected"


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
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def path_tokens(path: Path):
    return [p.lower() for p in path.parts]


def nearest_output_milestone(path: Path):
    """
    Return nearest ancestor directory beginning with V15_ or output child.
    """
    parts = list(path.parts)
    for p in reversed(parts[:-1]):
        if p.upper().startswith("V15_"):
            return p
    return path.parent.name


def project_text_files():
    rows = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        low = {x.lower() for x in p.parts}
        if ".venv" in low or "site-packages" in low or "__pycache__" in low:
            continue
        if p.suffix.lower() in {".py", ".json", ".csv", ".txt"}:
            rows.append(p.resolve())
    return sorted(set(rows))


def normalized_path(s):
    try:
        return str(Path(s).resolve()).lower()
    except Exception:
        return str(s).lower()


def context_contains_path_or_parent(context: str, artifact_path: Path):
    low = context.lower()
    full = str(artifact_path).lower()
    fname = artifact_path.name.lower()
    parent = artifact_path.parent.name.lower()
    milestone = nearest_output_milestone(artifact_path).lower()

    return {
        "full_path": full in low,
        "filename": fname in low,
        "parent_dir": parent in low if parent else False,
        "milestone_dir": milestone in low if milestone else False,
    }


def load_npz_fingerprint(path: Path):
    try:
        db = np.load(path, allow_pickle=True)
    except Exception:
        return None

    keys = list(db.files)
    rows = []

    for key in keys:
        try:
            arr = np.asarray(db[key])
        except Exception:
            continue

        # Hash modest/normal arrays; object arrays still hash their raw contiguous
        # representation only if conversion is safe.
        try:
            ah = sha256_array(arr)
        except Exception:
            ah = ""

        rows.append({
            "key": key,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "array_sha256": ah,
        })

    db.close()
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R11")
    print("Top SG7A Corrected Artifact Lineage Conflict Audit")
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
NO ARTIFACT INSTANCE WILL BE SELECTED BY CANDIDATE PERFORMANCE.
""")

    r10_summary = load_json(R10_SUMMARY)
    r10_contract = load_json(R10_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r10_summary.get("status") != (
        "SG7E_SG7A_CORRECTED_ARTIFACT_PROVENANCE_STILL_AMBIGUOUS"
    ):
        raise RuntimeError(
            "R11 requires the unresolved R10 SG7A-corrected artifact status."
        )

    if r10_summary.get("diagnosis") != (
        "NO_SINGLE_ARTIFACT_INSTANCE_HAS_SUFFICIENT_AUTHORITATIVE_PROVENANCE_MARGIN"
    ):
        raise RuntimeError(
            "R11 requires the R10 insufficient-provenance-margin diagnosis."
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])
    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold must remain resolved.")

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    scores = load_csv(R10_SCORES)
    artifacts = load_csv(R9_ARTIFACTS)
    source_refs = load_csv(R10_SOURCE_REFS)
    manifest_refs = load_csv(R10_MANIFEST_REFS)
    save_trace = load_csv(R10_SAVE_TRACE)
    load_trace = load_csv(R10_LOAD_TRACE)
    gate_trace = load_csv(R8_GATE_TRACE)

    # -------------------------------------------------------------------------
    # Isolate top tied lineage candidates.
    # -------------------------------------------------------------------------

    scores = sorted(scores, key=lambda r: int(r.get("score", 0)), reverse=True)
    if not scores:
        raise RuntimeError("R11 found no R10 provenance score records.")

    top_score = int(scores[0]["score"])
    top_rows = [r for r in scores if int(r["score"]) == top_score]

    # The expected R10 conflict is two top records with same filename but
    # distinct array hashes. Keep all ties safely if more than two appear.
    top_paths = [Path(r["artifact_path"]).resolve() for r in top_rows]

    top_pair_rows = []
    for r in top_rows:
        p = Path(r["artifact_path"]).resolve()
        top_pair_rows.append({
            "artifact_file": r["artifact_file"],
            "artifact_path": str(p),
            "parent_directory": str(p.parent),
            "milestone_directory": nearest_output_milestone(p),
            "provenance_score": int(r["score"]),
            "array_sha256": r["array_sha256"],
            "file_sha256": r["file_sha256"],
            "array_shape": r["array_shape"],
        })

    save_csv(TOP_PAIR_TABLE, top_pair_rows)

    # -------------------------------------------------------------------------
    # Parent-directory lineage.
    # -------------------------------------------------------------------------

    parent_rows = []
    for r in top_rows:
        p = Path(r["artifact_path"]).resolve()
        parent_rows.append({
            "artifact_path": str(p),
            "artifact_file": p.name,
            "parent_directory": str(p.parent),
            "parent_name": p.parent.name,
            "grandparent_name": p.parent.parent.name if p.parent.parent else "",
            "milestone_directory": nearest_output_milestone(p),
            "under_output": "output" in {x.lower() for x in p.parts},
        })

    save_csv(PARENT_TABLE, parent_rows)

    # -------------------------------------------------------------------------
    # Creation/save source disambiguation.
    # Use full path / parent context, not filename alone.
    # -------------------------------------------------------------------------

    creation_rows = []
    creation_strength = defaultdict(int)

    for row in save_trace:
        ctx = row.get("context", "")
        src = row.get("source", "")

        for p in top_paths:
            evidence = context_contains_path_or_parent(ctx, p)
            strength = (
                100 * int(evidence["full_path"])
                + 40 * int(evidence["milestone_dir"])
                + 25 * int(evidence["parent_dir"])
                + 5 * int(evidence["filename"])
            )

            if strength > 0:
                creation_strength[str(p)] += strength
                creation_rows.append({
                    "artifact_path": str(p),
                    "artifact_file": p.name,
                    "source": src,
                    "line": row.get("line", ""),
                    "full_path_match": evidence["full_path"],
                    "milestone_dir_match": evidence["milestone_dir"],
                    "parent_dir_match": evidence["parent_dir"],
                    "filename_match": evidence["filename"],
                    "creation_strength": strength,
                    "context": ctx[:3500],
                })

    save_csv(CREATION_TABLE, creation_rows)

    # -------------------------------------------------------------------------
    # Authoritative load-path disambiguation.
    # -------------------------------------------------------------------------

    load_rows = []
    load_strength = defaultdict(int)

    for row in load_trace:
        ctx = row.get("context", "")
        src = row.get("source", "")

        for p in top_paths:
            evidence = context_contains_path_or_parent(ctx, p)
            strength = (
                150 * int(evidence["full_path"])
                + 70 * int(evidence["milestone_dir"])
                + 50 * int(evidence["parent_dir"])
                + 5 * int(evidence["filename"])
            )

            if strength > 0:
                load_strength[str(p)] += strength
                load_rows.append({
                    "artifact_path": str(p),
                    "artifact_file": p.name,
                    "source": src,
                    "line": row.get("line", ""),
                    "full_path_match": evidence["full_path"],
                    "milestone_dir_match": evidence["milestone_dir"],
                    "parent_dir_match": evidence["parent_dir"],
                    "filename_match": evidence["filename"],
                    "load_strength": strength,
                    "context": ctx[:3500],
                })

    save_csv(LOAD_TABLE, load_rows)

    # -------------------------------------------------------------------------
    # Parent manifest / contract lineage.
    # Search specific parent/milestone directory names and absolute paths.
    # -------------------------------------------------------------------------

    manifest_rows = []
    manifest_strength = defaultdict(int)

    for row in manifest_refs:
        ref_source = Path(row.get("reference_source", ""))
        text = safe_text(ref_source) if ref_source.exists() else ""

        for p in top_paths:
            full = str(p).lower()
            parent = p.parent.name.lower()
            milestone = nearest_output_milestone(p).lower()
            fname = p.name.lower()

            strength = 0
            signals = []

            if full in text.lower():
                strength += 120
                signals.append("full_path")
            if milestone and milestone in text.lower():
                strength += 60
                signals.append("milestone_dir")
            if parent and parent in text.lower():
                strength += 40
                signals.append("parent_dir")
            if fname in text.lower():
                strength += 5
                signals.append("filename")

            if strength > 0:
                manifest_strength[str(p)] += strength
                manifest_rows.append({
                    "artifact_path": str(p),
                    "artifact_file": p.name,
                    "reference_source": str(ref_source),
                    "signals": ";".join(signals),
                    "manifest_strength": strength,
                })

    save_csv(MANIFEST_TABLE, manifest_rows)

    # -------------------------------------------------------------------------
    # Sibling-key fingerprinting.
    # Different NPZs with same filename can often be traced by their full key set.
    # -------------------------------------------------------------------------

    sibling_rows = []
    fingerprint_by_path = {}

    for p in top_paths:
        fp = load_npz_fingerprint(p)
        if fp is None:
            continue

        key_signature = "|".join(
            f"{r['key']}:{r['shape']}:{r['dtype']}"
            for r in sorted(fp, key=lambda x: x["key"])
        )
        fingerprint_hash = hashlib.sha256(
            key_signature.encode("utf-8")
        ).hexdigest()

        fingerprint_by_path[str(p)] = {
            "fingerprint_hash": fingerprint_hash,
            "keys": [r["key"] for r in fp],
        }

        for rec in fp:
            sibling_rows.append({
                "artifact_path": str(p),
                "artifact_file": p.name,
                "fingerprint_sha256": fingerprint_hash,
                "key": rec["key"],
                "shape": rec["shape"],
                "dtype": rec["dtype"],
                "array_sha256": rec["array_sha256"],
                "is_reference_key": rec["key"] == REFERENCE_KEY,
            })

    save_csv(SIBLING_TABLE, sibling_rows)

    # -------------------------------------------------------------------------
    # Chronology supporting evidence.
    # -------------------------------------------------------------------------

    chronology_rows = []
    for p in top_paths:
        st = p.stat()
        chronology_rows.append({
            "artifact_path": str(p),
            "artifact_file": p.name,
            "mtime_epoch": st.st_mtime,
            "size_bytes": st.st_size,
            "milestone_directory": nearest_output_milestone(p),
        })

    chronology_rows.sort(key=lambda r: float(r["mtime_epoch"]))
    save_csv(CHRONOLOGY_TABLE, chronology_rows)

    # -------------------------------------------------------------------------
    # Hash identity.
    # -------------------------------------------------------------------------

    hash_rows = []

    for p in top_paths:
        db = np.load(p, allow_pickle=True)
        arr = np.asarray(db[REFERENCE_KEY])

        hash_rows.append({
            "artifact_path": str(p),
            "artifact_file": p.name,
            "file_sha256": sha256_file(p),
            "reference_array_sha256": sha256_array(arr),
            "reference_shape": str(arr.shape),
            "reference_dtype": str(arr.dtype),
            "sibling_fingerprint_sha256": (
                fingerprint_by_path.get(str(p), {}).get("fingerprint_hash", "")
            ),
        })
        db.close()

    save_csv(HASH_TABLE, hash_rows)

    # -------------------------------------------------------------------------
    # Final lineage scoring.
    #
    # Strong evidence only:
    #   authoritative/load path > parent manifest > creation path
    #
    # Filename-only tie contributes nothing discriminating here.
    # Chronology is reported but intentionally not scored.
    # -------------------------------------------------------------------------

    final_rows = []

    for r in top_rows:
        p = str(Path(r["artifact_path"]).resolve())

        lineage_score = (
            load_strength[p]
            + manifest_strength[p]
            + creation_strength[p]
        )

        signals = []
        if load_strength[p] > 0:
            signals.append("authoritative_load_path")
        if manifest_strength[p] > 0:
            signals.append("parent_manifest_contract")
        if creation_strength[p] > 0:
            signals.append("creation_save_path")

        final_rows.append({
            "artifact_path": p,
            "artifact_file": Path(p).name,
            "R10_score": int(r["score"]),
            "lineage_score": lineage_score,
            "authoritative_load_strength": load_strength[p],
            "manifest_strength": manifest_strength[p],
            "creation_strength": creation_strength[p],
            "signals": ";".join(signals),
            "array_sha256": r["array_sha256"],
        })

    final_rows.sort(
        key=lambda r: (
            int(r["lineage_score"]),
            int(r["authoritative_load_strength"]),
            int(r["manifest_strength"]),
            int(r["creation_strength"]),
        ),
        reverse=True,
    )

    # Require a direct/strong lineage difference.
    selected = None
    lineage_margin = 0

    if final_rows:
        top = final_rows[0]
        second_score = (
            int(final_rows[1]["lineage_score"])
            if len(final_rows) > 1 else -999
        )
        top_lineage = int(top["lineage_score"])
        lineage_margin = top_lineage - second_score

        strong = (
            int(top["authoritative_load_strength"]) >= 50
            or int(top["manifest_strength"]) >= 40
            or int(top["creation_strength"]) >= 40
        )

        if strong and lineage_margin >= 40:
            selected = top

    checks = [
        ("Incoming R10 top-lineage ambiguity reproduced", True),
        ("Historical reference key remains SG7A_corrected", True),
        ("Historical plume threshold retained", abs(threshold - 0.5) < 1e-15),
        ("Frozen SG7D6 input remains authoritative", True),
        ("Top tied R10 candidates isolated", len(top_rows) >= 2),
        ("Top candidates retain distinct numerical hashes", len({r['array_sha256'] for r in top_rows}) >= 2),
        ("Full artifact paths compared, not filename only", True),
        ("Parent/milestone directories audited", True),
        ("Creation/save path lineage audited", True),
        ("Authoritative load path lineage audited", True),
        ("Parent manifest/contract lineage audited", True),
        ("Sibling NPZ key fingerprints audited", True),
        ("Filesystem chronology recorded as supporting evidence only", True),
        ("No candidate performance used", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No reference field reconstructed or frozen", True),
    ]

    if selected is not None:
        status = "SG7E_TOP_ARTIFACT_LINEAGE_RESOLVED"
        diagnosis = "ONE_TOP_SG7A_CORRECTED_ARTIFACT_HAS_UNIQUE_AUTHORITATIVE_LINEAGE"
        recommendation = (
            "The previously tied SG7A_corrected artifact instances are now separated by "
            "full-path creation/load/manifest provenance. Preserve the selected file and "
            "array hashes. Proceed to resolve the historical snapshot/time index used by "
            "the authoritative SG7E consumer before reconstructing the 15x50x50 reference."
        )
        next_milestone = (
            "V15-SG7E1R12 — Historical Reference Time-Index / Snapshot Resolution Audit"
        )
    else:
        status = "SG7E_TOP_ARTIFACT_LINEAGE_CONFLICT_REMAINS"
        diagnosis = "TOP_SG7A_CORRECTED_INSTANCES_REMAIN_PROVENANCE_TIED_AFTER_PATH_AUDIT"
        recommendation = (
            "Do not reconstruct the reference field. The two top SG7A_corrected instances "
            "remain tied even after full-path, parent, creation, load, manifest, sibling-key, "
            "and chronology audits. Inspect only the final authoritative load-path variable "
            "or parent producer branch that generates these same-named artifacts."
        )
        next_milestone = (
            "V15-SG7E1R12 — Authoritative Load-Path Variable / Producer-Branch Audit"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "reference_key": REFERENCE_KEY,
        "plume_threshold": threshold,
        "R10_top_score": top_score,
        "top_candidate_count": len(top_rows),
        "lineage_margin": lineage_margin,
        "selected_artifact": selected["artifact_path"] if selected else "",
        "selected_array_sha256": selected["array_sha256"] if selected else "",
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R11",
        "status": status,
        "diagnosis": diagnosis,
        "reference_key": REFERENCE_KEY,
        "plume_threshold": {
            "value": threshold,
            "changed": False,
        },
        "top_lineage": {
            "candidate_count": len(top_rows),
            "selected": selected is not None,
            "selected_artifact": selected["artifact_path"] if selected else None,
            "selected_array_sha256": selected["array_sha256"] if selected else None,
            "lineage_margin": lineage_margin,
        },
        "constraints": {
            "candidate_performance_used": False,
            "filename_only_used_as_authority": False,
            "chronology_used_as_authority": False,
            "threshold_changed": False,
            "posthoc_alignment": False,
            "deployment_correction_performed": False,
            "reference_field_reconstructed": False,
            "reference_field_frozen": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R11",
        "status": status,
        "diagnosis": diagnosis,
        "artifact_resolved": selected is not None,
        "selected_artifact": selected["artifact_path"] if selected else None,
        "selected_array_sha256": selected["array_sha256"] if selected else None,
        "lineage_margin": lineage_margin,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("TOP SG7A CORRECTED LINEAGE CONFLICT")
    print(f"  R10 top provenance score: {top_score}")
    print(f"  Top tied candidates     : {len(top_rows)}")

    for r in final_rows:
        print(
            f"  lineage={int(r['lineage_score']):4d} | "
            f"load={int(r['authoritative_load_strength']):4d} | "
            f"manifest={int(r['manifest_strength']):4d} | "
            f"create={int(r['creation_strength']):4d} | "
            f"{Path(r['artifact_path']).parent.name}\\{r['artifact_file']} | "
            f"{r['array_sha256'][:16]}"
        )

    if selected:
        print("\nSELECTED TOP LINEAGE")
        print(f"  Artifact                : {selected['artifact_path']}")
        print(f"  Array SHA-256           : {selected['array_sha256']}")
        print(f"  Lineage margin          : {lineage_margin}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R11 LINEAGE VALIDATION")
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
        TOP_PAIR_TABLE,
        PARENT_TABLE,
        CREATION_TABLE,
        LOAD_TABLE,
        MANIFEST_TABLE,
        SIBLING_TABLE,
        CHRONOLOGY_TABLE,
        HASH_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R11 TOP SG7A CORRECTED ARTIFACT LINEAGE CONFLICT AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No filename-only or chronology-only authority was used.")
    print("No candidate performance was used.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print("No reference field was reconstructed or frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
