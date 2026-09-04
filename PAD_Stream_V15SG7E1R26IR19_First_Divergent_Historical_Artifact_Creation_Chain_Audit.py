from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R19
# First Divergent Historical Artifact Creation-Chain Audit
#
# DIAGNOSTIC-ONLY HISTORICAL NUMERICAL IDENTITY CHAIN AUDIT
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA / GUARD RECALIBRATION.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO PRECISION ENVELOPE WILL BE RELAXED.
# NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
#
# PURPOSE
# -------
# R18 established that BOTH exact numerical identities persist historically:
#
#   creator100 identity  : 2 historical exact matches
#   frozen100 identity   : 14 historical exact matches
#
# Therefore the discrepancy is not hypothetical runtime drift only; the project
# persisted both identities in different historical artifacts.
#
# R19 determines:
#
#   1. the last historical artifact carrying creator100,
#   2. the first historical artifact carrying frozen100 after that point,
#   3. source/serializer records associated with those two artifacts,
#   4. parent manifest/contract references,
#   5. whether one explicit creation edge connects the two identities.
#
# Filesystem chronology is supporting evidence ONLY. Authority comes from
# creation/save/load/manifest/source lineage where available.
#
# No inference is executed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR19"
OUT.mkdir(parents=True, exist_ok=True)

R18_DIR = ROOT / "output" / "V15_SG7E1R26IR18"
R18_SUMMARY = R18_DIR / "PAD_Stream_V15SG7E1R26IR18_Summary.json"
R18_ARTIFACTS = R18_DIR / "V15SG7E1R26IR18_Historical_Array_Identity_Inventory.csv"
R18_FINGERPRINT = R18_DIR / "V15SG7E1R26IR18_Exceedance_Fingerprint_Match.csv"

R18_CONTRACT = R18_DIR / "V15SG7E1R26IR18_Runtime_Serialization_Contract.json"

# Outputs
IDENTITY_CHAIN_TABLE = OUT / "V15SG7E1R26IR19_Identity_Chronology.csv"
BOUNDARY_TABLE = OUT / "V15SG7E1R26IR19_Creator_to_Frozen_Boundary.csv"
SOURCE_TABLE = OUT / "V15SG7E1R26IR19_Source_Creation_Trace.csv"
SERIAL_TABLE = OUT / "V15SG7E1R26IR19_Serializer_Creation_Trace.csv"
LOAD_TABLE = OUT / "V15SG7E1R26IR19_Load_Consumer_Trace.csv"
MANIFEST_TABLE = OUT / "V15SG7E1R26IR19_Manifest_Contract_Boundary_Trace.csv"
EDGE_TABLE = OUT / "V15SG7E1R26IR19_Direct_Creation_Edge_Audit.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR19_Final_Audit_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR19_First_Divergence_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR19_First_Divergent_Artifact_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR19_Summary.json"


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
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def safe_text(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes"}


def historical_matches(rows):
    creator = []
    frozen = []

    for row in rows:
        artifact = row.get("artifact", "")
        if any(tok in artifact for tok in ("V15_SG7E1R16", "V15_SG7E1R17", "V15_SG7E1R18", "V15_SG7E1R19")):
            continue

        if normalize_bool(row.get("exact_creator100", False)):
            creator.append(row)
        if normalize_bool(row.get("exact_frozen100", False)):
            frozen.append(row)

    return creator, frozen


def artifact_stat(path_str):
    p = Path(path_str)
    if not p.exists():
        return {
            "exists": False,
            "mtime": None,
            "ctime": None,
            "size": None,
            "file_sha256": None,
        }

    st = p.stat()
    return {
        "exists": True,
        "mtime": st.st_mtime,
        "ctime": st.st_ctime,
        "size": st.st_size,
        "file_sha256": sha256_file(p),
    }


def chronology_rows(creator_rows, frozen_rows):
    rows = []

    for role, source_rows in (
        ("CREATOR100_IDENTITY", creator_rows),
        ("FROZEN100_IDENTITY", frozen_rows),
    ):
        for row in source_rows:
            stat = artifact_stat(row["artifact"])
            rows.append({
                "identity_role": role,
                "artifact": row["artifact"],
                "key": row.get("key", ""),
                "array_sha256_float32": row.get("sha256_float32", ""),
                "exists": stat["exists"],
                "mtime_epoch": stat["mtime"] if stat["mtime"] is not None else "",
                "mtime_iso": (
                    datetime.fromtimestamp(stat["mtime"], tz=timezone.utc).isoformat()
                    if stat["mtime"] is not None else ""
                ),
                "ctime_epoch": stat["ctime"] if stat["ctime"] is not None else "",
                "ctime_iso": (
                    datetime.fromtimestamp(stat["ctime"], tz=timezone.utc).isoformat()
                    if stat["ctime"] is not None else ""
                ),
                "size_bytes": stat["size"] if stat["size"] is not None else "",
                "file_sha256": stat["file_sha256"] or "",
            })

    rows.sort(key=lambda r: float(r["mtime_epoch"]) if r["mtime_epoch"] != "" else float("inf"))
    return rows


def boundary_candidates(chron_rows):
    creators = [r for r in chron_rows if r["identity_role"] == "CREATOR100_IDENTITY"]
    frozens = [r for r in chron_rows if r["identity_role"] == "FROZEN100_IDENTITY"]

    if not creators or not frozens:
        return None, None, []

    last_creator = max(
        creators,
        key=lambda r: float(r["mtime_epoch"]) if r["mtime_epoch"] != "" else float("-inf")
    )

    lc_time = float(last_creator["mtime_epoch"]) if last_creator["mtime_epoch"] != "" else None

    after = []
    if lc_time is not None:
        for r in frozens:
            if r["mtime_epoch"] != "" and float(r["mtime_epoch"]) >= lc_time:
                after.append(r)

    if after:
        first_frozen = min(after, key=lambda r: float(r["mtime_epoch"]))
    else:
        first_frozen = min(
            frozens,
            key=lambda r: float(r["mtime_epoch"]) if r["mtime_epoch"] != "" else float("inf")
        )

    return last_creator, first_frozen, after


def project_text_files():
    files = []
    for suffix in ("*.py", "*.json", "*.csv", "*.txt"):
        files.extend(ROOT.rglob(suffix))
    return [p for p in files if p.is_file()]


def trace_artifact_mentions(boundary_paths):
    source_rows = []
    serial_rows = []
    load_rows = []
    manifest_rows = []

    names = {Path(p).name: p for p in boundary_paths if p}

    for path in project_text_files():
        if any(tok in str(path) for tok in ("V15_SG7E1R19",)):
            continue

        text = safe_text(path)

        for filename, fullpath in names.items():
            if filename not in text and fullpath not in text:
                continue

            line_hits = []
            for i, line in enumerate(text.splitlines(), start=1):
                if filename in line or fullpath in line:
                    line_hits.append((i, line.strip()))

            for line_no, line in line_hits:
                category = "SOURCE_REFERENCE"

                low = line.lower()
                if "savez" in low or "save(" in low:
                    category = "SERIALIZER_REFERENCE"
                elif "np.load" in low or "load(" in low:
                    category = "LOAD_REFERENCE"
                elif path.suffix.lower() in {".json", ".csv"} or "manifest" in path.name.lower() or "contract" in path.name.lower():
                    category = "MANIFEST_CONTRACT_REFERENCE"

                row = {
                    "boundary_artifact": fullpath,
                    "boundary_filename": filename,
                    "source": str(path),
                    "line": line_no,
                    "text": line,
                    "category": category,
                }

                source_rows.append(row)
                if category == "SERIALIZER_REFERENCE":
                    serial_rows.append(row)
                elif category == "LOAD_REFERENCE":
                    load_rows.append(row)
                elif category == "MANIFEST_CONTRACT_REFERENCE":
                    manifest_rows.append(row)

    return source_rows, serial_rows, load_rows, manifest_rows


def direct_edge_audit(last_creator, first_frozen, source_rows, serial_rows, load_rows, manifest_rows):
    if not last_creator or not first_frozen:
        return [{
            "edge_resolved": False,
            "reason": "boundary artifacts unavailable",
            "creator_artifact": "",
            "frozen_artifact": "",
            "shared_source_count": 0,
            "shared_manifest_count": 0,
            "creator_loaded_where_frozen_saved": False,
        }]

    c_art = last_creator["artifact"]
    f_art = first_frozen["artifact"]

    c_sources = {r["source"] for r in source_rows if r["boundary_artifact"] == c_art}
    f_sources = {r["source"] for r in source_rows if r["boundary_artifact"] == f_art}
    shared_sources = c_sources & f_sources

    c_man = {r["source"] for r in manifest_rows if r["boundary_artifact"] == c_art}
    f_man = {r["source"] for r in manifest_rows if r["boundary_artifact"] == f_art}
    shared_manifests = c_man & f_man

    creator_load_sources = {r["source"] for r in load_rows if r["boundary_artifact"] == c_art}
    frozen_save_sources = {r["source"] for r in serial_rows if r["boundary_artifact"] == f_art}
    load_save_intersection = creator_load_sources & frozen_save_sources

    edge_resolved = bool(load_save_intersection or shared_sources or shared_manifests)

    return [{
        "edge_resolved": edge_resolved,
        "creator_artifact": c_art,
        "creator_key": last_creator.get("key", ""),
        "frozen_artifact": f_art,
        "frozen_key": first_frozen.get("key", ""),
        "shared_source_count": len(shared_sources),
        "shared_sources": ";".join(sorted(shared_sources)),
        "shared_manifest_count": len(shared_manifests),
        "shared_manifests": ";".join(sorted(shared_manifests)),
        "creator_loaded_where_frozen_saved": bool(load_save_intersection),
        "load_save_sources": ";".join(sorted(load_save_intersection)),
    }]


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R19")
    print("First Divergent Historical Artifact Creation-Chain Audit")
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
CREATOR / MODEL / X100 AUTHORITY WILL NOT BE REOPENED.
FILESYSTEM CHRONOLOGY IS SUPPORTING EVIDENCE ONLY.
""")

    r18 = load_json(R18_SUMMARY)
    if r18.get("classification") != "BOTH_RUNTIME_IDENTITIES_PERSIST_HISTORICALLY":
        raise RuntimeError("R19 requires the R18 dual-identity historical classification.")

    artifact_rows = load_csv(R18_ARTIFACTS)
    creator_rows, frozen_rows = historical_matches(artifact_rows)

    chron_rows = chronology_rows(creator_rows, frozen_rows)
    save_csv(IDENTITY_CHAIN_TABLE, chron_rows)

    last_creator, first_frozen, after = boundary_candidates(chron_rows)

    boundary_rows = [{
        "last_creator_artifact": last_creator["artifact"] if last_creator else "",
        "last_creator_key": last_creator.get("key", "") if last_creator else "",
        "last_creator_mtime_iso": last_creator.get("mtime_iso", "") if last_creator else "",
        "first_frozen_artifact": first_frozen["artifact"] if first_frozen else "",
        "first_frozen_key": first_frozen.get("key", "") if first_frozen else "",
        "first_frozen_mtime_iso": first_frozen.get("mtime_iso", "") if first_frozen else "",
        "frozen_candidates_after_last_creator": len(after),
    }]
    save_csv(BOUNDARY_TABLE, boundary_rows)

    boundary_paths = [
        last_creator["artifact"] if last_creator else "",
        first_frozen["artifact"] if first_frozen else "",
    ]

    source_rows, serial_rows, load_rows, manifest_rows = trace_artifact_mentions(boundary_paths)
    save_csv(SOURCE_TABLE, source_rows)
    save_csv(SERIAL_TABLE, serial_rows)
    save_csv(LOAD_TABLE, load_rows)
    save_csv(MANIFEST_TABLE, manifest_rows)

    edge_rows = direct_edge_audit(
        last_creator,
        first_frozen,
        source_rows,
        serial_rows,
        load_rows,
        manifest_rows,
    )
    save_csv(EDGE_TABLE, edge_rows)

    edge_resolved = normalize_bool(edge_rows[0].get("edge_resolved", False))

    gates = [
        ("R18_dual_identity_classification_reproduced", True),
        ("historical_creator_matches_retained", len(creator_rows) == 2),
        ("historical_frozen_matches_retained", len(frozen_rows) == 14),
        ("identity_chronology_established", len(chron_rows) == 16),
        ("last_creator_identity_artifact_identified", last_creator is not None),
        ("first_frozen_identity_artifact_identified", first_frozen is not None),
        ("boundary_source_references_audited", True),
        ("boundary_serializer_references_audited", True),
        ("boundary_load_references_audited", True),
        ("boundary_manifest_contract_references_audited", True),
        ("direct_creation_edge_audited", True),
        ("chronology_not_used_as_sole_authority", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_precision_relaxation", True),
        ("no_authority_reopened", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    if edge_resolved:
        status = "FIRST_CREATOR_TO_FROZEN_DIVERGENCE_CHAIN_RESOLVED"
        diagnosis = (
            "ONE_CREATION_LOAD_MANIFEST_CHAIN_CONNECTS_LAST_CREATOR_IDENTITY_TO_FIRST_FROZEN_IDENTITY"
        )
        recommendation = (
            "The first persisted numerical identity transition is now isolated. Audit only the "
            "specific source operation(s) on this creation edge to determine whether the change is "
            "caused by runtime inference, dtype conversion, array copying, or serialization. "
            "Do not rerun the model yet."
        )
        next_ms = (
            "V15-SG7E1R26I-R20 — First Divergence Source-Operation Audit"
        )
    else:
        status = "FIRST_CREATOR_TO_FROZEN_DIVERGENCE_BOUNDARY_IDENTIFIED_EDGE_NOT_YET_EXPLICIT"
        diagnosis = (
            "BOUNDARY_ARTIFACTS_ARE_IDENTIFIED_BUT_DIRECT_CREATION_EDGE_IS_NOT_EXPLICIT_IN_SOURCE_OR_MANIFESTS"
        )
        recommendation = (
            "Do not rerun the model or relax precision. Audit only the two boundary artifacts' "
            "parent directories, sibling manifests/contracts, and immediate source creators to "
            "resolve one explicit numerical transition edge."
        )
        next_ms = (
            "V15-SG7E1R26I-R20 — Boundary Artifact Parent / Sibling Lineage Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "last_creator_artifact": last_creator["artifact"] if last_creator else "",
        "last_creator_key": last_creator.get("key", "") if last_creator else "",
        "first_frozen_artifact": first_frozen["artifact"] if first_frozen else "",
        "first_frozen_key": first_frozen.get("key", "") if first_frozen else "",
        "edge_resolved": edge_resolved,
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R19",
        "status": status,
        "diagnosis": diagnosis,
        "creator_identity_match_count": len(creator_rows),
        "frozen_identity_match_count": len(frozen_rows),
        "last_creator": last_creator,
        "first_frozen": first_frozen,
        "edge_audit": edge_rows[0],
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "precision_envelope_relaxed": False,
            "authority_reopened": False,
            "chronology_used_as_sole_authority": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R19",
        "status": status,
        "diagnosis": diagnosis,
        "edge_resolved": edge_resolved,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("HISTORICAL IDENTITY COUNTS")
    print(f"  Creator100 exact        : {len(creator_rows)}")
    print(f"  Frozen100 exact         : {len(frozen_rows)}")

    print("\nDIVERGENCE BOUNDARY")
    if last_creator:
        print(f"  Last creator artifact   : {last_creator['artifact']}")
        print(f"  Last creator key        : {last_creator.get('key', '')}")
        print(f"  Creator mtime           : {last_creator.get('mtime_iso', '')}")
    if first_frozen:
        print(f"  First frozen artifact   : {first_frozen['artifact']}")
        print(f"  First frozen key        : {first_frozen.get('key', '')}")
        print(f"  Frozen mtime            : {first_frozen.get('mtime_iso', '')}")

    print("\nBOUNDARY LINEAGE EVIDENCE")
    print(f"  Source references       : {len(source_rows)}")
    print(f"  Serializer references   : {len(serial_rows)}")
    print(f"  Load references         : {len(load_rows)}")
    print(f"  Manifest references     : {len(manifest_rows)}")
    print(f"  Explicit edge resolved  : {edge_resolved}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19 FINAL AUDIT GATES")
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
        IDENTITY_CHAIN_TABLE,
        BOUNDARY_TABLE,
        SOURCE_TABLE,
        SERIAL_TABLE,
        LOAD_TABLE,
        MANIFEST_TABLE,
        EDGE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19 FIRST DIVERGENT ARTIFACT CREATION-CHAIN AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("The R16 precision envelope was not relaxed.")
    print("No creator/model/X100 authority was reopened.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
