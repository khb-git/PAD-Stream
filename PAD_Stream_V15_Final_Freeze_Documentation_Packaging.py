from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone


# =============================================================================
# PAD-Stream Version 15
# Final Freeze / Documentation Packaging
#
# FINAL PACKAGING MILESTONE
#
# NO TRAINING.
# NO MODEL.PREDICT.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN NUMERICAL ARTIFACT CHANGED.
# NO SG7E THRESHOLD CHANGED.
# NO PRECISION ENVELOPE CHANGED.
# NO 250/500/1000-DAY STATE GENERATED.
#
# PURPOSE
# -------
# R22 established:
#
#   STATUS:
#   SG7E1_BRANCH_CLOSED_VERSION15_FREEZE_READY_WITH_DOCUMENTED_SCOPE_LIMITATION
#
# This milestone creates the immutable Version 15 freeze package containing:
#
#   - final branch disposition
#   - SG7E historical reference contract
#   - runtime reproducibility limitation
#   - corrected later-time binding rejection
#   - SG7E scope decision
#   - final freeze-readiness contract
#   - final authority registry
#   - frozen scope limitations
#   - post-V15 development handoff
#   - SHA-256 package manifest
#   - human-readable freeze README
#   - ZIP archive of the documentation package
#
# Numerical artifacts are NOT copied or modified unless they are explicitly
# referenced by the final authority records. Their identities are recorded by
# path and SHA-256 where resolvable.
# =============================================================================


ROOT = Path(__file__).resolve().parent

OUT = ROOT / "output" / "V15_FINAL_FREEZE"
PACKAGE_DIR = OUT / "PAD_Stream_Version15_Frozen_Validation_Record"
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# Authoritative milestone directories
# -------------------------------------------------------------------------
R14_DIR = ROOT / "output" / "V15_SG7E1R14"
R19E_DIR = ROOT / "output" / "V15_SG7E1R26IR19E"
R20R_DIR = ROOT / "output" / "V15_SG7E1R26IR20R"
R21_DIR = ROOT / "output" / "V15_SG7E1R26IR21"
R22_DIR = ROOT / "output" / "V15_SG7E1R26IR22"

REQUIRED_INPUTS = [
    R14_DIR / "V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json",
    R14_DIR / "PAD_Stream_V15SG7E1R14_Summary.json",

    R19E_DIR / "V15SG7E1R26IR19E_Runtime_Reproducibility_Authority_Contract.json",
    R19E_DIR / "PAD_Stream_V15SG7E1R26IR19E_Summary.json",

    R20R_DIR / "V15SG7E1R26IR20R_Later_Time_Binding_Contradiction_Contract.json",
    R20R_DIR / "PAD_Stream_V15SG7E1R26IR20R_Summary.json",

    R21_DIR / "V15SG7E1R26IR21_Multi_Time_Coverage_Scope_Contract.json",
    R21_DIR / "PAD_Stream_V15SG7E1R26IR21_Summary.json",

    R22_DIR / "V15SG7E1R26IR22_Version15_Freeze_Readiness_Contract.json",
    R22_DIR / "PAD_Stream_V15SG7E1R26IR22_Summary.json",

    R22_DIR / "V15SG7E1R26IR22_SG7E1_Branch_Disposition.csv",
    R22_DIR / "V15SG7E1R26IR22_Version15_Freeze_Readiness.csv",
    R22_DIR / "V15SG7E1R26IR22_Frozen_Scope_Limitations.csv",
    R22_DIR / "V15SG7E1R26IR22_Final_Authority_Registry.csv",
    R22_DIR / "V15SG7E1R26IR22_Post_V15_Development_Handoff.csv",
    R22_DIR / "V15SG7E1R26IR22_Final_Freeze_Gates.csv",
    R22_DIR / "V15SG7E1R26IR22_Final_Freeze_Decision.csv",
]

MANIFEST_CSV = OUT / "PAD_Stream_Version15_Freeze_File_Manifest.csv"
MASTER_CONTRACT = OUT / "PAD_Stream_Version15_Master_Freeze_Contract.json"
README_FILE = PACKAGE_DIR / "README_PAD_Stream_Version15_Freeze.txt"
ZIP_FILE = OUT / "PAD_Stream_Version15_Frozen_Validation_Record.zip"
SUMMARY_FILE = OUT / "PAD_Stream_Version15_Final_Freeze_Summary.json"


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_required_inputs():
    copied = []
    for src in REQUIRED_INPUTS:
        if not src.exists():
            raise FileNotFoundError(f"Required freeze input missing: {src}")

        dst = PACKAGE_DIR / src.name
        shutil.copy2(src, dst)
        copied.append((src, dst))
    return copied


def discover_authoritative_artifacts(r22_contract):
    """
    Record any explicit existing paths referenced by final contract objects.
    We do not guess missing paths.
    """
    paths = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    if "\\" in v or "/" in v:
                        p = Path(v)
                        if p.exists() and p.is_file():
                            paths.add(p.resolve())
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(r22_contract)

    # Also inspect upstream final contracts for exact artifact paths.
    for p in [
        R14_DIR / "V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json",
        R19E_DIR / "V15SG7E1R26IR19E_Runtime_Reproducibility_Authority_Contract.json",
        R20R_DIR / "V15SG7E1R26IR20R_Later_Time_Binding_Contradiction_Contract.json",
        R21_DIR / "V15SG7E1R26IR21_Multi_Time_Coverage_Scope_Contract.json",
    ]:
        obj = load_json(p)
        walk(obj)

    return sorted(paths)


def build_readme(r14, r19e, r20r, r21, r22):
    text = f"""
PAD-Stream Version 15 — Frozen Validation Record
================================================

Freeze timestamp (UTC):
  {datetime.now(timezone.utc).isoformat()}

FINAL STATUS
------------
{r22["status"]}

FINAL DIAGNOSIS
---------------
{r22["diagnosis"]}

FROZEN VERSION 15 SCOPE
-----------------------
1. SG7E historical reference:
   - Four-time reference contract preserved.
   - Historical times: 100, 250, 500, 1000 days.
   - Historical plume threshold remains S = 0.5.

2. Certified deployment state:
   - L2_independent_100 is the authoritative 100-day L2 deployment state.

3. Frozen SG7D6 deployment:
   - Preserved as an authoritative single-state deployment artifact.
   - No unsupported 250/500/1000-day physical-time assignment is permitted.

4. Multi-time deployment:
   - A reproducible four-time frozen deployment sequence is NOT certified.
   - 250/500/1000-day frozen deployment states are not present with valid
     preserved provenance.
   - Four-time SG7E deployment gate evaluation is therefore not applicable to
     the frozen Version 15 deployment lineage.

5. Runtime reproducibility:
   - Exact historical inference runtime reproduction is not certified.
   - Runtime-variance testing was terminated without relaxing the precision
     envelope or changing model/X100 authority.

6. Rejected interpretation:
   - Historical frozen100 may not be relabelled as 250-day or 500-day state.
   - Current-runtime generated later-time states may not be inserted into
     frozen Version 15.

FINAL DEVELOPMENT RULE
----------------------
Version 15 is frozen with the above documented scope limitation.

Any future implementation of an explicitly time-indexed 250/500/1000-day
deployment sequence belongs to a post-Version-15 development branch/version.

AUTHORITATIVE CONTRACT STATUS
-----------------------------
R14:
  {r14["status"]}

R19E:
  {r19e["status"]}

R20R:
  {r20r["status"]}

R21:
  {r21["status"]}

R22:
  {r22["status"]}

No training was performed during final packaging.
No model inference was performed during final packaging.
No frozen numerical artifact was changed during final packaging.
"""
    README_FILE.write_text(text.strip() + "\n", encoding="utf-8")


def make_zip():
    if ZIP_FILE.exists():
        ZIP_FILE.unlink()

    with zipfile.ZipFile(ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PACKAGE_DIR.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=p.relative_to(PACKAGE_DIR.parent))


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15")
    print("Final Freeze / Documentation Packaging")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO MODEL PARAMETER WILL BE CHANGED.
NO FROZEN NUMERICAL ARTIFACT WILL BE CHANGED.
NO SG7E THRESHOLD OR PRECISION ENVELOPE WILL BE CHANGED.
THIS MILESTONE PACKAGES THE FINAL VERSION 15 VALIDATION RECORD.
""")

    r14 = load_json(R14_DIR / "PAD_Stream_V15SG7E1R14_Summary.json")
    r19e = load_json(R19E_DIR / "PAD_Stream_V15SG7E1R19E_Summary.json") if False else load_json(
        R19E_DIR / "PAD_Stream_V15SG7E1R26IR19E_Summary.json"
    )
    r20r = load_json(R20R_DIR / "PAD_Stream_V15SG7E1R26IR20R_Summary.json")
    r21 = load_json(R21_DIR / "PAD_Stream_V15SG7E1R26IR21_Summary.json")
    r22 = load_json(R22_DIR / "PAD_Stream_V15SG7E1R26IR22_Summary.json")

    if r22.get("status") != "SG7E1_BRANCH_CLOSED_VERSION15_FREEZE_READY_WITH_DOCUMENTED_SCOPE_LIMITATION":
        raise RuntimeError("Final packaging requires successful R22 freeze-readiness status.")

    # Recreate package directory cleanly.
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

    copied = copy_required_inputs()

    r22_contract = load_json(
        R22_DIR / "V15SG7E1R26IR22_Version15_Freeze_Readiness_Contract.json"
    )
    authoritative_artifacts = discover_authoritative_artifacts(r22_contract)

    # Record artifact identities only; do not mutate originals.
    artifact_rows = []
    for p in authoritative_artifacts:
        artifact_rows.append({
            "path": str(p),
            "sha256": sha256_file(p),
            "size_bytes": p.stat().st_size,
            "copied_into_package": False,
            "role": "EXPLICITLY_REFERENCED_AUTHORITATIVE_OR_SUPPORTING_ARTIFACT",
        })

    build_readme(r14, r19e, r20r, r21, r22)

    manifest_rows = []
    for _, dst in copied:
        manifest_rows.append({
            "package_file": str(dst.relative_to(PACKAGE_DIR)),
            "sha256": sha256_file(dst),
            "size_bytes": dst.stat().st_size,
            "category": "FINAL_VALIDATION_RECORD",
        })

    manifest_rows.append({
        "package_file": str(README_FILE.relative_to(PACKAGE_DIR)),
        "sha256": sha256_file(README_FILE),
        "size_bytes": README_FILE.stat().st_size,
        "category": "README",
    })

    package_manifest_copy = PACKAGE_DIR / "PAD_Stream_Version15_Freeze_File_Manifest.csv"
    save_csv(package_manifest_copy, manifest_rows)

    # Now add the manifest itself to the external manifest.
    external_manifest_rows = list(manifest_rows)
    external_manifest_rows.append({
        "package_file": str(package_manifest_copy.relative_to(PACKAGE_DIR)),
        "sha256": sha256_file(package_manifest_copy),
        "size_bytes": package_manifest_copy.stat().st_size,
        "category": "PACKAGE_MANIFEST",
    })

    save_csv(MANIFEST_CSV, external_manifest_rows)

    authority_registry = load_csv(
        R22_DIR / "V15SG7E1R26IR22_Final_Authority_Registry.csv"
    )
    limitations = load_csv(
        R22_DIR / "V15SG7E1R26IR22_Frozen_Scope_Limitations.csv"
    )
    handoff = load_csv(
        R22_DIR / "V15SG7E1R26IR22_Post_V15_Development_Handoff.csv"
    )

    master_contract = {
        "project": "PAD-Stream",
        "version": "15",
        "freeze_status": r22["status"],
        "freeze_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "final_diagnosis": r22["diagnosis"],
        "SG7E_reference_scope": {
            "historical_times_days": [100.0, 250.0, 500.0, 1000.0],
            "threshold": 0.5,
            "role": "HISTORICAL_MULTI_TIME_REFERENCE_ACCEPTANCE_CONTRACT",
        },
        "deployment_scope": {
            "certified_L2_times_days": [100.0],
            "uncertified_L2_times_days": [250.0, 500.0, 1000.0],
            "four_time_deployment_sequence_certified": False,
            "SG7D6_role": "AUTHORITATIVE_FROZEN_SINGLE_STATE_DEPLOYMENT_ARTIFACT",
        },
        "runtime_scope": {
            "exact_historical_runtime_replay_certified": False,
            "additional_runtime_search_authorized_in_V15": False,
        },
        "authority_registry": authority_registry,
        "frozen_scope_limitations": limitations,
        "post_V15_handoff": handoff,
        "authoritative_artifact_identities": artifact_rows,
        "packaged_validation_files": external_manifest_rows,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "frozen_numerical_artifact_changed": False,
            "threshold_changed": False,
            "precision_envelope_changed": False,
            "later_time_state_generated": False,
        },
        "next_development_stage": "POST_VERSION_15_BRANCH",
    }

    save_json(MASTER_CONTRACT, master_contract)

    # Copy the master contract into package after it is created.
    shutil.copy2(
        MASTER_CONTRACT,
        PACKAGE_DIR / MASTER_CONTRACT.name,
    )

    # Refresh package manifest after master contract addition.
    package_files = []
    for p in sorted(PACKAGE_DIR.rglob("*")):
        if p.is_file() and p.name != "PAD_Stream_Version15_Freeze_File_Manifest.csv":
            package_files.append({
                "package_file": str(p.relative_to(PACKAGE_DIR)),
                "sha256": sha256_file(p),
                "size_bytes": p.stat().st_size,
                "category": (
                    "MASTER_FREEZE_CONTRACT"
                    if p.name == MASTER_CONTRACT.name
                    else "FINAL_VALIDATION_RECORD"
                ),
            })

    save_csv(package_manifest_copy, package_files)
    save_csv(MANIFEST_CSV, package_files)

    make_zip()

    summary = {
        "milestone": "VERSION 15 FREEZE / DOCUMENTATION PACKAGING",
        "status": "PAD_STREAM_VERSION15_FROZEN_VALIDATION_PACKAGE_COMPLETE",
        "freeze_ready_source_status": r22["status"],
        "package_directory": str(PACKAGE_DIR),
        "zip_archive": str(ZIP_FILE),
        "zip_sha256": sha256_file(ZIP_FILE),
        "packaged_file_count": len(package_files),
        "authoritative_artifact_identity_count": len(artifact_rows),
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "frozen_numerical_artifact_changed": False,
            "later_time_state_generated": False,
        },
        "next_stage": "POST_VERSION_15_DEVELOPMENT",
    }
    save_json(SUMMARY_FILE, summary)

    print("FREEZE STATUS")
    print("  R22 freeze-ready        : True")
    print("  Version 15 package      : COMPLETE")
    print("  Numerical mutation      : NONE")
    print("  Training                : NONE")
    print("  Model inference         : NONE")

    print("\nFROZEN SCOPE")
    print("  SG7E reference          : 100/250/500/1000 d")
    print("  Certified L2 deployment : 100 d")
    print("  SG7D6 deployment        : single-state")
    print("  Four-time deployment    : NOT CERTIFIED")

    print("\nPACKAGE")
    print(f"  Directory               : {PACKAGE_DIR}")
    print(f"  Files                   : {len(package_files)}")
    print(f"  ZIP                     : {ZIP_FILE}")
    print(f"  ZIP SHA-256             : {sha256_file(ZIP_FILE)}")

    print("\nSTATUS")
    print("  PAD_STREAM_VERSION15_FROZEN_VALIDATION_PACKAGE_COMPLETE")

    print("\nNEXT STAGE")
    print("  POST_VERSION_15_DEVELOPMENT")

    print("\n" + "=" * 78)
    print("PAD-STREAM VERSION 15 FINAL FREEZE / DOCUMENTATION PACKAGING: COMPLETE")
    print()
    print("No training was performed.")
    print("No model.predict call was executed.")
    print("No frozen numerical artifact was changed.")
    print("No later-time deployment state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
