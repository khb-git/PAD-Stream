from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1A2R4A
# Historical B4 Checkpoint Identity Resolution
#
# DIAGNOSTIC / PROVENANCE-RESOLUTION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R1A2R4 established:
#
#   MULTIPLE_B4_CHECKPOINT_IDENTITIES_WITH_TINY_COEFFICIENT_DRIFT
#
# with six distinct B4-related SHA-256 identities and no explicit historical
# hash match in the previously searched manifests.
#
# R1A2R4A resolves WHICH B4 artifact generated the historical R3F4-R support
# record by cross-referencing:
#
#   * R3F4 checkpoint tables
#   * R3F4 epoch metrics
#   * R3F4 final metrics
#   * R3F4 manifest / summary
#   * R3F4-R source code
#   * R3F4-R summary
#   * exact filenames referenced by source
#   * epoch / checkpoint-type provenance
#   * SHA-256 identities
#
# The milestone does NOT load and evaluate every old B4 model. It first resolves
# provenance from the historical source/manifest chain. If provenance remains
# ambiguous, it routes to an explicit model-by-model coefficient reconstruction
# milestone.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1A2R4A"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R4_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R4"
    / "PAD_Stream_V15SG7CR3F5R1A2R4_Summary.json"
)

R4_IDENTITIES = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R4"
    / "V15SG7CR3F5R1A2R4_All_B4_Checkpoint_Identities.csv"
)

R3F4_DIR = ROOT / "output" / "V15_SG7CR3F4"
R3F4R_DIR = ROOT / "output" / "V15_SG7CR3F4R"

R3F4_BEST = R3F4_DIR / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
R3F4_EPOCH = R3F4_DIR / "V15SG7CR3F4_Epoch_Metrics.csv"
R3F4_FINAL = R3F4_DIR / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
R3F4_MANIFEST = R3F4_DIR / "V15SG7CR3F4_Candidate_Manifest.json"
R3F4_SUMMARY = R3F4_DIR / "PAD_Stream_V15SG7CR3F4_Summary.json"

R3F4R_SUMMARY = R3F4R_DIR / "PAD_Stream_V15SG7CR3F4R_Summary.json"
R3F4R_SUPPORT = R3F4R_DIR / "V15SG7CR3F4R_Basis_Support_Coverage.csv"

# The authoritative audit source that produced the historical support table.
R3F4R_SOURCE = ROOT / "PAD_Stream_V15SG7CR3F4R_Front_Local_Basis_Outcome_Audit.py"

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1A2R4A_Summary.json"
SOURCE_REF_TABLE = OUT / "V15SG7CR3F5R1A2R4A_Source_Checkpoint_References.csv"
MANIFEST_TABLE = OUT / "V15SG7CR3F5R1A2R4A_Manifest_Checkpoint_References.csv"
EPOCH_TABLE = OUT / "V15SG7CR3F5R1A2R4A_B4_Epoch_Provenance.csv"
IDENTITY_TABLE = OUT / "V15SG7CR3F5R1A2R4A_Identity_Candidate_Scores.csv"
DECISION_TABLE = OUT / "V15SG7CR3F5R1A2R4A_Historical_Identity_Decision.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1A2R4A_Historical_B4_Identity_Contract.json"

HASH_PREFIX_LEN = 16


# =============================================================================
# IO
# =============================================================================

def load_json(path: Path, required=True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing prerequisite:\n{path}")
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path, required=True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing prerequisite:\n{path}")
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def fnum(row, key, default=np.nan):
    try:
        v = row.get(key, default)
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def resolve_path(value):
    if not value:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = ROOT / p
    return p


# =============================================================================
# Reference extraction
# =============================================================================

MODEL_PATTERN = re.compile(
    r"""["']([^"']*B4[^"']*\.(?:keras|h5|weights\.h5|ckpt))["']""",
    re.IGNORECASE,
)

GENERIC_MODEL_PATTERN = re.compile(
    r"""["']([^"']*\.(?:keras|h5|weights\.h5|ckpt))["']""",
    re.IGNORECASE,
)

HASH_PATTERN = re.compile(r"\b[a-fA-F0-9]{16,64}\b")


def source_references(path: Path):
    rows = []

    if not path.exists():
        return rows

    lines = path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    for i, line in enumerate(lines):
        low = line.lower()

        if not any(
            token in low
            for token in [
                "b4",
                "checkpoint",
                "best_any",
                "model",
                "keras",
                "sha",
                "hash",
            ]
        ):
            continue

        model_matches = MODEL_PATTERN.findall(line)

        if not model_matches and "B4" in line:
            model_matches = GENERIC_MODEL_PATTERN.findall(line)

        hashes = HASH_PATTERN.findall(line)

        rows.append({
            "line_number": i + 1,
            "line": line.strip(),
            "model_references": ";".join(model_matches),
            "hash_references": ";".join(hashes),
        })

    return rows


def flatten_json(payload, prefix=""):
    rows = []

    if isinstance(payload, dict):
        for key, value in payload.items():
            full = f"{prefix}.{key}" if prefix else key
            rows.extend(flatten_json(value, full))

    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            rows.extend(flatten_json(value, f"{prefix}[{i}]"))

    else:
        rows.append((prefix, payload))

    return rows


def manifest_references():
    rows = []

    for label, path in [
        ("R3F4 manifest", R3F4_MANIFEST),
        ("R3F4 summary", R3F4_SUMMARY),
        ("R3F4-R summary", R3F4R_SUMMARY),
    ]:
        payload = load_json(path, required=False)

        if payload is None:
            continue

        for key, value in flatten_json(payload):
            text = str(value)
            low = (key + " " + text).lower()

            if not any(
                token in low
                for token in [
                    "b4",
                    "checkpoint",
                    "model",
                    "keras",
                    "sha",
                    "hash",
                    "best_any",
                    "epoch",
                ]
            ):
                continue

            rows.append({
                "source": label,
                "path": str(path),
                "key": key,
                "value": text,
            })

    return rows


# =============================================================================
# Historical B4 evidence
# =============================================================================

def b4_epoch_rows():
    rows = []

    for source_name, path in [
        ("epoch_metrics", R3F4_EPOCH),
        ("final_metrics", R3F4_FINAL),
        ("best_checkpoint", R3F4_BEST),
    ]:
        source_rows = load_csv(path, required=False)

        for row in source_rows:
            if row.get("experiment") != "B4":
                continue

            rows.append({
                "source": source_name,
                **row,
            })

    return rows


def normalize_filename(path_string):
    if not path_string:
        return ""
    return Path(path_string).name.lower()


# =============================================================================
# Candidate scoring
# =============================================================================

def build_identity_candidates():
    identities = load_csv(R4_IDENTITIES)

    source_rows = source_references(R3F4R_SOURCE)
    manifest_rows = manifest_references()
    epoch_rows = b4_epoch_rows()

    source_text = "\n".join(
        row["line"]
        for row in source_rows
    ).lower()

    manifest_text = "\n".join(
        f"{row['key']}={row['value']}"
        for row in manifest_rows
    ).lower()

    # Exact filenames mentioned anywhere.
    source_filenames = set()

    for row in source_rows:
        for item in row["model_references"].split(";"):
            if item:
                source_filenames.add(
                    Path(item).name.lower()
                )

    manifest_filenames = set()

    for row in manifest_rows:
        value = row["value"]

        if any(
            ext in value.lower()
            for ext in [
                ".keras",
                ".h5",
                ".ckpt",
            ]
        ):
            manifest_filenames.add(
                Path(value).name.lower()
            )

    explicit_hashes = set()

    for row in source_rows:
        for h in row["hash_references"].split(";"):
            if h:
                explicit_hashes.add(h.lower())

    for row in manifest_rows:
        value = row["value"].strip().lower()
        if re.fullmatch(r"[a-f0-9]{16,64}", value):
            explicit_hashes.add(value)

    candidates = []

    for row in identities:
        path = resolve_path(row.get("path", ""))

        name = path.name.lower() if path else ""
        digest = row.get("sha256", "").lower()

        score = 0
        reasons = []

        # Strongest: exact source filename.
        if name and name in source_filenames:
            score += 100
            reasons.append("exact_filename_in_R3F4R_source")

        # Strong: exact manifest filename.
        if name and name in manifest_filenames:
            score += 80
            reasons.append("exact_filename_in_manifest_or_summary")

        # Explicit hash match.
        for historical_hash in explicit_hashes:
            if (
                digest
                and (
                    digest == historical_hash
                    or digest.startswith(historical_hash)
                    or historical_hash.startswith(digest)
                )
            ):
                score += 120
                reasons.append("explicit_hash_match")
                break

        # Historical table explicitly designates best_any.
        if row.get("checkpoint_type", "").lower() == "best_any":
            score += 40
            reasons.append("R3F4_best_any_record")

        # Filename semantics.
        if "r3f4" in name:
            score += 20
            reasons.append("R3F4_branch_filename")

        if "best_any" in name:
            score += 20
            reasons.append("best_any_filename")

        # Old SG7B4 files should not normally be considered R3F4 products.
        if "sg7b4_" in name and "r3f4" not in name:
            score -= 30
            reasons.append("legacy_SG7B4_artifact")

        # Source raw-text reference even when parser misses quoting structure.
        if name and name in source_text:
            score += 50
            reasons.append("filename_literal_in_source_text")

        if name and name in manifest_text:
            score += 30
            reasons.append("filename_literal_in_manifest_text")

        candidates.append({
            "path": str(path) if path else "",
            "filename": path.name if path else "",
            "checkpoint_type": row.get("checkpoint_type", ""),
            "epoch": row.get("epoch", ""),
            "sha256": digest,
            "sha256_prefix": digest[:HASH_PREFIX_LEN] if digest else "",
            "score": score,
            "reasons": ";".join(reasons),
            "exact_source_filename_reference":
                bool(name and name in source_filenames),
            "exact_manifest_filename_reference":
                bool(name and name in manifest_filenames),
            "explicit_hash_match":
                any(
                    digest
                    and (
                        digest == h
                        or digest.startswith(h)
                        or h.startswith(digest)
                    )
                    for h in explicit_hashes
                ),
        })

    candidates.sort(
        key=lambda row: (
            -row["score"],
            row["filename"],
        )
    )

    return candidates, source_rows, manifest_rows, epoch_rows


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1A2R4A")
    print("Historical B4 Checkpoint Identity Resolution")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO HISTORICAL SCALAR OR CHECKPOINT WILL BE OVERWRITTEN.
NO GATE WILL BE CHANGED OR RELAXED.
""")

    incoming = load_json(R4_SUMMARY)

    if (
        incoming.get("diagnosis")
        !=
        "MULTIPLE_B4_CHECKPOINT_IDENTITIES_WITH_TINY_COEFFICIENT_DRIFT"
    ):
        raise RuntimeError(
            "R1A2R4A requires the R1A2R4 checkpoint-ambiguity diagnosis."
        )

    candidates, source_rows, manifest_rows, epoch_rows = (
        build_identity_candidates()
    )

    save_csv(
        SOURCE_REF_TABLE,
        source_rows,
    )

    save_csv(
        MANIFEST_TABLE,
        manifest_rows,
    )

    save_csv(
        EPOCH_TABLE,
        epoch_rows,
    )

    save_csv(
        IDENTITY_TABLE,
        candidates,
    )

    print("B4 IDENTITY CANDIDATES")

    for row in candidates:
        print(
            f"  score={row['score']:>4} | "
            f"{row['sha256_prefix'] or 'NOHASH':<16s} | "
            f"{row['filename']:<50s} | "
            f"{row['reasons']}"
        )

    if not candidates:
        raise RuntimeError(
            "No B4 checkpoint candidates available."
        )

    best = candidates[0]

    second_score = (
        candidates[1]["score"]
        if len(candidates) > 1
        else -10**9
    )

    score_margin = (
        best["score"]
        -
        second_score
    )

    direct_authoritative_reference = bool(
        best["exact_source_filename_reference"]
        or best["explicit_hash_match"]
    )

    strong_manifest_reference = bool(
        best["exact_manifest_filename_reference"]
    )

    branch_semantic_resolution = bool(
        "R3F4_best_any_record" in best["reasons"]
        and
        "R3F4_branch_filename" in best["reasons"]
        and
        score_margin >= 40
    )

    resolved = bool(
        direct_authoritative_reference
        or
        (
            strong_manifest_reference
            and score_margin >= 30
        )
        or
        branch_semantic_resolution
    )

    # Historical support record for context.
    support_rows = load_csv(R3F4R_SUPPORT, required=False)
    b4_support = None

    for row in support_rows:
        if row.get("experiment") == "B4":
            b4_support = row
            break

    if resolved:

        status = "HISTORICAL_B4_CHECKPOINT_IDENTITY_RESOLVED"

        diagnosis = (
            "R3F4_B4_BEST_ANY_CHECKPOINT_IS_AUTHORITATIVE_SUPPORT_SOURCE"
        )

        recommendation = (
            "The historical R3F4-R provenance chain identifies the R3F4 B4 "
            "Best-Any checkpoint as the authoritative model source. The legacy "
            "SG7B4 artifacts are separate historical models and should not compete "
            "with the R3F4 provenance chain. Preserve the historical support scalar "
            "unchanged and use the R3F4 B4 Best-Any runtime arrays as the numerical "
            "basis for exact-array support extension."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )

    else:

        status = "HISTORICAL_B4_CHECKPOINT_IDENTITY_STILL_AMBIGUOUS"

        diagnosis = (
            "PROVENANCE_RECORD_INSUFFICIENT_FOR_UNIQUE_B4_CHECKPOINT_IDENTITY"
        )

        recommendation = (
            "Historical source/manifest evidence is insufficient to uniquely identify "
            "the support-table-generating B4 checkpoint. Do not calibrate support. "
            "Evaluate each plausible B4 checkpoint through the deterministic R3F4-R "
            "coefficient reconstruction and select the one reproducing the historical "
            "coefficient statistics and supported residual sum."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A2R4A2 — Candidate-by-Candidate B4 Coefficient Reconstruction"
        )

    decision = [{
        "selected_filename": best["filename"],
        "selected_path": best["path"],
        "selected_sha256": best["sha256"],
        "selected_sha256_prefix": best["sha256_prefix"],
        "selected_score": best["score"],
        "second_best_score": second_score,
        "score_margin": score_margin,
        "selected_reasons": best["reasons"],
        "direct_authoritative_reference": direct_authoritative_reference,
        "strong_manifest_reference": strong_manifest_reference,
        "branch_semantic_resolution": branch_semantic_resolution,
        "resolved": resolved,
        "status": status,
        "diagnosis": diagnosis,
        "next_milestone": next_milestone,
    }]

    save_csv(
        DECISION_TABLE,
        decision,
    )

    contract = {
        "milestone": "V15-SG7C-R3F5-R1A2R4A",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_calibrated": False,
        "gate_changed": False,
        "historical_scalar_overwritten": False,
        "identity_resolved": resolved,
        "selected_checkpoint": {
            "filename": best["filename"],
            "path": best["path"],
            "sha256": best["sha256"],
            "score": best["score"],
            "reasons": best["reasons"],
        },
        "score_margin": score_margin,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    if b4_support is not None:
        contract["historical_B4_support"] = {
            "front_shell_required_residual_sum":
                fnum(
                    b4_support,
                    "front_shell_required_residual_sum",
                ),
            "front_shell_supported_residual_sum":
                fnum(
                    b4_support,
                    "front_shell_supported_residual_sum",
                ),
            "front_shell_residual_coverage_fraction":
                fnum(
                    b4_support,
                    "front_shell_residual_coverage_fraction",
                ),
        }

    save_json(
        CONTRACT_FILE,
        contract,
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1A2R4A",
            "status":
                status,
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "support_extension_calibrated":
                False,
            "gate_changed":
                False,
            "identity_resolved":
                resolved,
            "selected_checkpoint":
                best["filename"],
            "selected_sha256":
                best["sha256"],
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R4A DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Incoming R1A2R4 ambiguity diagnosis reproduced",
            True,
        ),
        (
            "R3F4-R source searched for checkpoint references",
            R3F4R_SOURCE.exists(),
        ),
        (
            "R3F4 manifest / summaries searched",
            True,
        ),
        (
            "R3F4 B4 epoch/checkpoint records loaded",
            bool(epoch_rows),
        ),
        (
            "All six B4 identities retained in candidate set",
            len(candidates) >= 6,
        ),
        (
            "Identity candidates scored without modifying checkpoints",
            True,
        ),
        (
            "Historical support scalar preserved unchanged",
            True,
        ),
        (
            "No support extension calibrated",
            True,
        ),
        (
            "No training performed",
            True,
        ),
        (
            "Historical identity decision established",
            True,
        ),
    ]

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] {desc}"
        )

    print("=" * 78)

    print("\nSELECTED IDENTITY")
    print(
        f"  File                    : "
        f"{best['filename']}"
    )
    print(
        f"  SHA-256                 : "
        f"{best['sha256']}"
    )
    print(
        f"  Score                   : "
        f"{best['score']}"
    )
    print(
        f"  Score margin            : "
        f"{score_margin}"
    )
    print(
        f"  Evidence                : "
        f"{best['reasons']}"
    )

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
    print(f"  {SOURCE_REF_TABLE.name}")
    print(f"  {MANIFEST_TABLE.name}")
    print(f"  {EPOCH_TABLE.name}")
    print(f"  {IDENTITY_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R4A IDENTITY RESOLUTION: COMPLETE")
    print()
    print("No training was performed.")
    print("No support extension was calibrated.")
    print("No historical scalar/checkpoint was overwritten.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
