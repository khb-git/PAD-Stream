from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R10
# SG7A Corrected Artifact Instance Provenance Audit
#
# FORENSIC ARTIFACT-LINEAGE MILESTONE
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
# NO ARTIFACT INSTANCE WILL BE SELECTED BY CANDIDATE PERFORMANCE.
#
# PURPOSE
# -------
# SG7E1R9 established:
#
#   SG7E_REFERENCE_ARTIFACT_INSTANCE_CONFLICT
#
# with:
#
#   MULTIPLE_DISTINCT_SG7A_CORRECTED_ARTIFACT_IDENTITIES_REMAIN
#
# R9 found:
#
#   Historical reference key : SG7A_corrected
#   Artifact instances       : 4
#   Unique array hashes      : 3
#
# R10 resolves which artifact instance belongs to the authoritative historical
# SG7E consumer lineage using provenance only:
#
#   authoritative SG7E source
#       -> source / save / load lineage
#       -> artifact filename/path
#       -> manifest / summary / contract references
#       -> SG7A_corrected array identity
#
# R10 does NOT resolve time slice unless artifact identity becomes unique.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R10"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R9_DIR = ROOT / "output" / "V15_SG7E1R9"
R9_SUMMARY = R9_DIR / "PAD_Stream_V15SG7E1R9_Summary.json"
R9_CONTRACT = R9_DIR / "V15SG7E1R9_Exact_Reference_Artifact_TimeSlice_Contract.json"
R9_ARTIFACTS = R9_DIR / "V15SG7E1R9_Reference_Artifact_Instance_Audit.csv"
R9_HASHES = R9_DIR / "V15SG7E1R9_Reference_Artifact_Hash_Groups.csv"

R8_GATE_TRACE = (
    ROOT / "output" / "V15_SG7E1R8"
    / "V15SG7E1R8_Authoritative_Gate_Consumer_Trace.csv"
)

R7_MATCHES = (
    ROOT / "output" / "V15_SG7E1R7"
    / "V15SG7E1R7_Upstream_Key_Object_Provenance_Match.csv"
)

R3_UPSTREAM = (
    ROOT / "output" / "V15_SG7E1R3"
    / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv"
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

SOURCE_REF_TABLE = OUT / "V15SG7E1R10_Authoritative_Source_Artifact_References.csv"
MANIFEST_REF_TABLE = OUT / "V15SG7E1R10_Manifest_Contract_Artifact_References.csv"
SAVE_TRACE_TABLE = OUT / "V15SG7E1R10_Artifact_Save_Creation_Trace.csv"
LOAD_TRACE_TABLE = OUT / "V15SG7E1R10_Artifact_Load_Consumption_Trace.csv"
CANDIDATE_SCORE_TABLE = OUT / "V15SG7E1R10_Artifact_Instance_Provenance_Scoring.csv"
HASH_DECISION_TABLE = OUT / "V15SG7E1R10_Array_Hash_Provenance_Decision.csv"
DECISION_TABLE = OUT / "V15SG7E1R10_Artifact_Instance_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R10_SG7A_Corrected_Artifact_Instance_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R10_Summary.json"

SELECTED_KEY = "SG7A_corrected"


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_files():
    """
    Search local PAD-Stream project source/provenance text, excluding venv/output
    numerical bulk where possible.
    """
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        low_parts = {x.lower() for x in p.parts}
        if ".venv" in low_parts or "site-packages" in low_parts or "__pycache__" in low_parts:
            continue
        if p.suffix.lower() not in {".py", ".json", ".csv", ".txt"}:
            continue
        out.append(p.resolve())
    return sorted(set(out))


def filename_occurrences(text: str, filename: str):
    if not text or not filename:
        return 0
    return len(re.findall(re.escape(filename), text, flags=re.I))


def key_occurrences(text: str, key: str):
    if not text or not key:
        return 0
    return len(re.findall(re.escape(key), text, flags=re.I))


def search_save_trace(text: str, filename: str, key: str):
    rows = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        low = line.lower()
        if "savez" not in low and "save(" not in low:
            continue
        ctx = "\n".join(lines[max(0, i-8):min(len(lines), i+12)])
        if filename.lower() in ctx.lower() or key.lower() in ctx.lower():
            rows.append((i, ctx[:3000]))
    return rows


def search_load_trace(text: str, filename: str, key: str):
    rows = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        low = line.lower()
        if "np.load" not in low and ".load(" not in low:
            continue
        ctx = "\n".join(lines[max(0, i-8):min(len(lines), i+12)])
        if filename.lower() in ctx.lower() or key.lower() in ctx.lower():
            rows.append((i, ctx[:3000]))
    return rows


def chronology_score(path: Path):
    """
    Weak supporting evidence only. Newer/older is not authority by itself.
    Returns file mtime as sortable evidence.
    """
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R10")
    print("SG7A Corrected Artifact Instance Provenance Audit")
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

    r9_summary = load_json(R9_SUMMARY)
    r9_contract = load_json(R9_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r9_summary.get("status") != "SG7E_REFERENCE_ARTIFACT_INSTANCE_CONFLICT":
        raise RuntimeError(
            "R10 requires SG7E1R9 artifact-instance conflict status."
        )

    if r9_summary.get("diagnosis") != (
        "MULTIPLE_DISTINCT_SG7A_CORRECTED_ARTIFACT_IDENTITIES_REMAIN"
    ):
        raise RuntimeError(
            "R10 requires SG7E1R9 multiple-artifact diagnosis."
        )

    if r9_contract.get("reference_key") != SELECTED_KEY:
        raise RuntimeError(
            f"R10 expected reference key {SELECTED_KEY!r}."
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])
    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold must remain resolved.")

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    artifact_rows = load_csv(R9_ARTIFACTS)
    hash_rows = load_csv(R9_HASHES)
    r8_gate_rows = load_csv(R8_GATE_TRACE)
    r7_match_rows = load_csv(R7_MATCHES)
    r3_upstream_rows = load_csv(R3_UPSTREAM)

    # Keep only true SG7A_corrected artifact instances.
    candidates = [
        r for r in artifact_rows
        if r.get("key", "") == SELECTED_KEY
    ]

    if len(candidates) < 2:
        raise RuntimeError(
            "R10 expected multiple SG7A_corrected artifact instances."
        )

    project_sources = source_files()

    source_reference_rows = []
    manifest_reference_rows = []
    save_rows = []
    load_rows = []

    # Authoritative source file names from R8 contexts.
    authoritative_sources = sorted({
        r.get("source", "")
        for r in r8_gate_rows
        if r.get("source", "")
    })

    authoritative_text = "\n".join(
        safe_text(Path(s))
        for s in authoritative_sources
        if Path(s).exists()
    )

    # Search all text/provenance files for each artifact filename.
    evidence = defaultdict(lambda: {
        "authoritative_filename_hits": 0,
        "authoritative_key_hits": 0,
        "project_filename_hits": 0,
        "manifest_contract_hits": 0,
        "save_trace_hits": 0,
        "load_trace_hits": 0,
        "r7_explicit_path_hits": 0,
        "r3_upstream_path_hits": 0,
    })

    candidate_by_file = {r["file"]: r for r in candidates}

    # R7 explicit provenance paths
    r7_paths = defaultdict(list)
    for row in r7_match_rows:
        if row.get("key", "") != SELECTED_KEY:
            continue
        for p in row.get("upstream_artifact_paths", "").split(";"):
            p = p.strip()
            if p:
                r7_paths[Path(p).name].append(p)

    # R3 upstream paths
    r3_paths = defaultdict(list)
    for row in r3_upstream_rows:
        if row.get("key", "") != SELECTED_KEY:
            continue
        p = row.get("path", "").strip()
        if p:
            r3_paths[Path(p).name].append(p)

    for cand in candidates:
        filename = cand["file"]
        path = Path(cand["path"])

        # Direct authoritative source references
        auth_filename_hits = filename_occurrences(authoritative_text, filename)
        auth_key_hits = key_occurrences(authoritative_text, SELECTED_KEY)

        evidence[filename]["authoritative_filename_hits"] += auth_filename_hits
        evidence[filename]["authoritative_key_hits"] += auth_key_hits

        if auth_filename_hits or auth_key_hits:
            source_reference_rows.append({
                "artifact_file": filename,
                "artifact_path": str(path),
                "authoritative_filename_hits": auth_filename_hits,
                "authoritative_key_hits": auth_key_hits,
                "authoritative_sources": ";".join(authoritative_sources),
            })

        # Project-wide manifest/contract/source references
        for src in project_sources:
            text = safe_text(src)
            if not text:
                continue

            fh = filename_occurrences(text, filename)
            if fh:
                evidence[filename]["project_filename_hits"] += fh

                kind = (
                    "manifest_contract"
                    if src.suffix.lower() == ".json"
                    or "manifest" in src.name.lower()
                    or "contract" in src.name.lower()
                    or "summary" in src.name.lower()
                    else "source"
                )

                if kind == "manifest_contract":
                    evidence[filename]["manifest_contract_hits"] += fh

                manifest_reference_rows.append({
                    "artifact_file": filename,
                    "artifact_path": str(path),
                    "reference_source": str(src),
                    "reference_kind": kind,
                    "filename_hits": fh,
                })

            # Save trace
            for line, ctx in search_save_trace(text, filename, SELECTED_KEY):
                evidence[filename]["save_trace_hits"] += 1
                save_rows.append({
                    "artifact_file": filename,
                    "artifact_path": str(path),
                    "source": str(src),
                    "line": line,
                    "context": ctx,
                })

            # Load trace
            for line, ctx in search_load_trace(text, filename, SELECTED_KEY):
                evidence[filename]["load_trace_hits"] += 1
                load_rows.append({
                    "artifact_file": filename,
                    "artifact_path": str(path),
                    "source": str(src),
                    "line": line,
                    "context": ctx,
                })

        if filename in r7_paths:
            evidence[filename]["r7_explicit_path_hits"] += len(r7_paths[filename])

        if filename in r3_paths:
            evidence[filename]["r3_upstream_path_hits"] += len(r3_paths[filename])

    save_csv(SOURCE_REF_TABLE, source_reference_rows)
    save_csv(MANIFEST_REF_TABLE, manifest_reference_rows)
    save_csv(SAVE_TRACE_TABLE, save_rows)
    save_csv(LOAD_TRACE_TABLE, load_rows)

    # -------------------------------------------------------------------------
    # Score provenance, not performance.
    # -------------------------------------------------------------------------

    score_rows = []

    for cand in candidates:
        filename = cand["file"]
        path = Path(cand["path"])
        e = evidence[filename]

        score = 0
        reasons = []

        # Strong direct lineage
        if e["authoritative_filename_hits"] > 0:
            score += 100
            reasons.append("authoritative_source_filename")

        if e["load_trace_hits"] > 0:
            score += min(60, 20 * e["load_trace_hits"])
            reasons.append("historical_load_trace")

        if e["r7_explicit_path_hits"] > 0:
            score += 50
            reasons.append("R7_object_provenance_path")

        if e["manifest_contract_hits"] > 0:
            score += min(40, 10 * e["manifest_contract_hits"])
            reasons.append("manifest_contract_reference")

        if e["save_trace_hits"] > 0:
            score += min(30, 10 * e["save_trace_hits"])
            reasons.append("save_creation_trace")

        if e["r3_upstream_path_hits"] > 0:
            score += 20
            reasons.append("R3_upstream_inventory")

        # Generic project occurrences are weaker.
        if e["project_filename_hits"] > 0:
            score += min(10, e["project_filename_hits"])
            reasons.append("project_filename_occurrence")

        # Key-only authoritative hits are common across artifacts and therefore
        # not artifact-specific. Retain as evidence but give no discriminating score.
        reasons.append(
            f"authoritative_key_hits={e['authoritative_key_hits']}"
        )

        score_rows.append({
            "artifact_file": filename,
            "artifact_path": str(path),
            "array_sha256": cand["array_sha256"],
            "file_sha256": cand["file_sha256"],
            "array_shape": cand["array_shape"],
            "score": score,
            "reasons": ";".join(reasons),
            "authoritative_filename_hits": e["authoritative_filename_hits"],
            "authoritative_key_hits": e["authoritative_key_hits"],
            "project_filename_hits": e["project_filename_hits"],
            "manifest_contract_hits": e["manifest_contract_hits"],
            "save_trace_hits": e["save_trace_hits"],
            "load_trace_hits": e["load_trace_hits"],
            "r7_explicit_path_hits": e["r7_explicit_path_hits"],
            "r3_upstream_path_hits": e["r3_upstream_path_hits"],
            "mtime": chronology_score(path),
        })

    score_rows.sort(
        key=lambda r: (
            int(r["score"]),
            int(r["authoritative_filename_hits"]),
            int(r["load_trace_hits"]),
            int(r["r7_explicit_path_hits"]),
        ),
        reverse=True,
    )

    save_csv(CANDIDATE_SCORE_TABLE, score_rows)

    # -------------------------------------------------------------------------
    # Hash-group provenance aggregation.
    # -------------------------------------------------------------------------

    hash_evidence = defaultdict(lambda: {
        "score": 0,
        "artifact_files": [],
        "authoritative_filename_hits": 0,
        "load_trace_hits": 0,
        "r7_explicit_path_hits": 0,
        "manifest_contract_hits": 0,
    })

    for row in score_rows:
        h = row["array_sha256"]
        he = hash_evidence[h]
        he["score"] += int(row["score"])
        he["artifact_files"].append(row["artifact_file"])
        he["authoritative_filename_hits"] += int(row["authoritative_filename_hits"])
        he["load_trace_hits"] += int(row["load_trace_hits"])
        he["r7_explicit_path_hits"] += int(row["r7_explicit_path_hits"])
        he["manifest_contract_hits"] += int(row["manifest_contract_hits"])

    hash_decision_rows = []
    for h, he in hash_evidence.items():
        hash_decision_rows.append({
            "array_sha256": h,
            "aggregate_provenance_score": he["score"],
            "artifact_files": ";".join(sorted(he["artifact_files"])),
            "authoritative_filename_hits": he["authoritative_filename_hits"],
            "load_trace_hits": he["load_trace_hits"],
            "r7_explicit_path_hits": he["r7_explicit_path_hits"],
            "manifest_contract_hits": he["manifest_contract_hits"],
        })

    hash_decision_rows.sort(
        key=lambda r: int(r["aggregate_provenance_score"]),
        reverse=True,
    )

    save_csv(HASH_DECISION_TABLE, hash_decision_rows)

    # -------------------------------------------------------------------------
    # Decision rule.
    # -------------------------------------------------------------------------

    selected = None
    score_margin = 0

    if score_rows:
        top = score_rows[0]
        second_score = int(score_rows[1]["score"]) if len(score_rows) > 1 else -999
        top_score = int(top["score"])
        score_margin = top_score - second_score

        # Require at least one strong lineage signal and a meaningful margin.
        strong_signal = (
            int(top["authoritative_filename_hits"]) > 0
            or int(top["load_trace_hits"]) > 0
            or int(top["r7_explicit_path_hits"]) > 0
            or int(top["manifest_contract_hits"]) > 0
        )

        if strong_signal and score_margin >= 20:
            selected = top

    checks = [
        ("Incoming SG7E1R9 artifact conflict reproduced", True),
        ("Historical reference key = SG7A_corrected", True),
        ("Historical plume threshold retained", abs(threshold - 0.5) < 1e-15),
        ("Frozen SG7D6 input remains authoritative", True),
        ("All R9 artifact instances retained", len(candidates) == len(artifact_rows)),
        ("All distinct R9 numerical identities retained", len(hash_decision_rows) >= 2),
        ("Authoritative source artifact references searched", True),
        ("Manifest / contract artifact references searched", True),
        ("Artifact save creation traces searched", True),
        ("Artifact load consumption traces searched", True),
        ("R7 explicit object-provenance paths retained", True),
        ("No candidate performance used in artifact selection", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No post-hoc alignment performed", True),
        ("No deployment correction performed", True),
        ("No reference field reconstructed or frozen", True),
    ]

    if selected is not None:
        status = "SG7E_SG7A_CORRECTED_ARTIFACT_INSTANCE_RESOLVED"
        diagnosis = "UNIQUE_AUTHORITATIVE_ARTIFACT_INSTANCE_ESTABLISHED_BY_PROVENANCE"
        recommendation = (
            "The historical SG7E consumer lineage now resolves to one SG7A_corrected "
            "artifact instance with a clear provenance margin. Preserve its file and array "
            "hashes. Proceed to resolve only the historical time index/snapshot used by the "
            "authoritative SG7E metrics before reconstructing the final 15x50x50 reference field."
        )
        next_milestone = (
            "V15-SG7E1R11 — Historical Reference Time-Index / Snapshot Resolution Audit"
        )
    else:
        status = "SG7E_SG7A_CORRECTED_ARTIFACT_PROVENANCE_STILL_AMBIGUOUS"
        diagnosis = "NO_SINGLE_ARTIFACT_INSTANCE_HAS_SUFFICIENT_AUTHORITATIVE_PROVENANCE_MARGIN"
        recommendation = (
            "Do not reconstruct the reference field. The SG7A_corrected key is authoritative, "
            "but artifact-instance provenance remains insufficiently unique. Audit only the "
            "top artifact lineages using creation/load chronology, parent manifests, and the "
            "historical SG7E source path; do not use candidate performance."
        )
        next_milestone = (
            "V15-SG7E1R11 — Top SG7A Corrected Artifact Lineage Conflict Audit"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "reference_key": SELECTED_KEY,
        "plume_threshold": threshold,
        "artifact_instance_count": len(candidates),
        "distinct_array_hashes": len(hash_decision_rows),
        "selected_artifact": selected["artifact_path"] if selected else "",
        "selected_artifact_file": selected["artifact_file"] if selected else "",
        "selected_array_sha256": selected["array_sha256"] if selected else "",
        "selected_file_sha256": selected["file_sha256"] if selected else "",
        "top_score": int(score_rows[0]["score"]) if score_rows else 0,
        "score_margin": score_margin,
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R10",
            "status": status,
            "diagnosis": diagnosis,
            "reference_key": SELECTED_KEY,
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "artifact_resolution": {
                "resolved": selected is not None,
                "artifact_path": selected["artifact_path"] if selected else None,
                "artifact_file": selected["artifact_file"] if selected else None,
                "array_sha256": selected["array_sha256"] if selected else None,
                "file_sha256": selected["file_sha256"] if selected else None,
                "score_margin": score_margin,
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
            "milestone": "V15-SG7E1R10",
            "status": status,
            "diagnosis": diagnosis,
            "artifact_resolved": selected is not None,
            "selected_artifact": selected["artifact_path"] if selected else None,
            "selected_array_sha256": selected["array_sha256"] if selected else None,
            "score_margin": score_margin,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("SG7A CORRECTED ARTIFACT PROVENANCE")
    print(f"  Historical key          : {SELECTED_KEY}")
    print(f"  Artifact instances      : {len(candidates)}")
    print(f"  Distinct array hashes   : {len(hash_decision_rows)}")

    print("\nARTIFACT PROVENANCE SCORES")
    for row in score_rows:
        print(
            f"  score={int(row['score']):4d} | "
            f"authFile={int(row['authoritative_filename_hits']):2d} | "
            f"loads={int(row['load_trace_hits']):2d} | "
            f"R7path={int(row['r7_explicit_path_hits']):2d} | "
            f"{row['artifact_file']} | {row['array_sha256'][:16]}"
        )

    if selected:
        print("\nSELECTED ARTIFACT")
        print(f"  File                    : {selected['artifact_file']}")
        print(f"  Path                    : {selected['artifact_path']}")
        print(f"  Array SHA-256           : {selected['array_sha256']}")
        print(f"  File SHA-256            : {selected['file_sha256']}")
        print(f"  Provenance score margin : {score_margin}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R10 ARTIFACT PROVENANCE VALIDATION")
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
        SOURCE_REF_TABLE,
        MANIFEST_REF_TABLE,
        SAVE_TRACE_TABLE,
        LOAD_TRACE_TABLE,
        CANDIDATE_SCORE_TABLE,
        HASH_DECISION_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R10 SG7A CORRECTED ARTIFACT INSTANCE PROVENANCE AUDIT: COMPLETE")
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


if __name__ == "__main__":
    main()
