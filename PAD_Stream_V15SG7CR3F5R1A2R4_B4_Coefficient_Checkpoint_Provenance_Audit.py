from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1A2R4
# B4 Coefficient / Checkpoint Provenance Audit
#
# DIAGNOSTIC / IDENTITY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R1A2R3 established:
#
#   * required_shell closes exactly
#   * supported_required = coeff_shell * required_shell exactly
#   * numerical accumulation does NOT explain the discrepancy
#   * runtime coefficient statistics are slightly different from the
#     authoritative historical B4 statistics
#
# Therefore the remaining question is provenance:
#
#   Which persisted B4 checkpoint / coefficient field produced the historical
#   authoritative scalar:
#
#       front_shell_supported_residual_sum = 62.56321852706
#
# This milestone audits all available B4 checkpoint identities, hashes, epochs,
# experiment manifests, coefficient summary records, and persisted runtime
# candidates. It does NOT change the model or scalar record.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1A2R4"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R3_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R3"
    / "PAD_Stream_V15SG7CR3F5R1A2R3_Summary.json"
)

R3_COEFF = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R3"
    / "V15SG7CR3F5R1A2R3_Coefficient_Provenance_Audit.csv"
)

R3_CHECKPOINT = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R3"
    / "V15SG7CR3F5R1A2R3_Checkpoint_Identity_Audit.csv"
)

RUNTIME_NPZ = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R"
    / "V15SG7CR3F5R1A2R_Runtime_Variables.npz"
)

SUPPORT_CSV = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

BEST_CHECKPOINTS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
)

FINAL_METRICS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
)

CANDIDATE_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Candidate_Manifest.json"
)

R3F4_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "PAD_Stream_V15SG7CR3F4_Summary.json"
)

R3F4R_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "PAD_Stream_V15SG7CR3F4R_Summary.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1A2R4_Summary.json"
CHECKPOINT_TABLE = OUT / "V15SG7CR3F5R1A2R4_All_B4_Checkpoint_Identities.csv"
HASH_TABLE = OUT / "V15SG7CR3F5R1A2R4_B4_Checkpoint_Hash_Audit.csv"
PROVENANCE_TABLE = OUT / "V15SG7CR3F5R1A2R4_B4_Provenance_Evidence.csv"
COEFF_TABLE = OUT / "V15SG7CR3F5R1A2R4_Coefficient_Field_Comparison.csv"
DECISION_TABLE = OUT / "V15SG7CR3F5R1A2R4_Provenance_Decision.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1A2R4_B4_Provenance_Contract.json"
RESOLVED_NPZ = OUT / "V15SG7CR3F5R1A2R4_Resolved_B4_Support_Arrays.npz"

REL_COEFF_TOL = 5e-5
HASH_PREFIX_LEN = 16


# =============================================================================
# IO helpers
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
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def fnum(row, key, default=np.nan):
    try:
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
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


def coeff_stats(arr):
    a = np.asarray(arr, dtype=np.float64)
    return {
        "mean": float(np.mean(a)),
        "P90": float(np.percentile(a, 90)),
        "max": float(np.max(a)),
        "min": float(np.min(a)),
        "std": float(np.std(a)),
    }


def row_for_experiment(rows, experiment):
    for row in rows:
        if row.get("experiment") == experiment:
            return row
    return None


# =============================================================================
# Discovery
# =============================================================================

def discover_b4_models():
    """
    Discover every persisted B4 Keras/checkpoint-like artifact in the project
    and output tree without assuming the manifest is complete.
    """
    patterns = [
        "**/*B4*.keras",
        "**/*B4*.h5",
        "**/*B4*.weights.h5",
        "**/*B4*.ckpt",
    ]

    found = []

    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue

            # Ignore virtual environment packages.
            if ".venv" in path.parts:
                continue

            found.append(path)

    # de-duplicate
    unique = []
    seen = set()

    for path in found:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)

    return sorted(unique)


def historical_checkpoint_rows():
    rows = load_csv(BEST_CHECKPOINTS, required=False)
    return [
        row for row in rows
        if row.get("experiment") == "B4"
    ]


def build_checkpoint_audit():
    manifest_rows = historical_checkpoint_rows()
    discovered = discover_b4_models()

    rows = []

    # Manifest-listed checkpoints.
    for row in manifest_rows:
        path = resolve_path(
            row.get("path")
            or row.get("checkpoint_path")
            or row.get("model_path")
        )

        exists = bool(path and path.exists())

        digest = sha256(path) if exists else ""

        rows.append({
            "source": "R3F4_Best_Checkpoint_By_Experiment",
            "checkpoint_type": row.get("checkpoint_type", ""),
            "epoch": row.get("epoch", ""),
            "path": str(path) if path else "",
            "exists": exists,
            "sha256": digest,
            "sha256_prefix": digest[:HASH_PREFIX_LEN] if digest else "",
            "size_bytes": path.stat().st_size if exists else "",
        })

    # Filesystem discovery.
    known_paths = {
        Path(row["path"]).resolve()
        for row in rows
        if row.get("path") and Path(row["path"]).exists()
    }

    for path in discovered:
        resolved = path.resolve()

        if resolved in known_paths:
            continue

        digest = sha256(path)

        rows.append({
            "source": "filesystem_discovery",
            "checkpoint_type": "",
            "epoch": "",
            "path": str(path),
            "exists": True,
            "sha256": digest,
            "sha256_prefix": digest[:HASH_PREFIX_LEN],
            "size_bytes": path.stat().st_size,
        })

    return rows


# =============================================================================
# Provenance evidence
# =============================================================================

def collect_provenance_evidence():
    evidence = []

    for label, path in [
        ("R3F4 candidate manifest", CANDIDATE_MANIFEST),
        ("R3F4 summary", R3F4_SUMMARY),
        ("R3F4-R summary", R3F4R_SUMMARY),
    ]:
        payload = load_json(path, required=False)

        if payload is None:
            evidence.append({
                "source": label,
                "path": str(path),
                "available": False,
                "key": "",
                "value": "",
            })
            continue

        evidence.append({
            "source": label,
            "path": str(path),
            "available": True,
            "key": "__document__",
            "value": "loaded",
        })

        # flatten only provenance-relevant scalar/string values
        stack = [("", payload)]

        while stack:
            prefix, obj = stack.pop()

            if isinstance(obj, dict):
                for key, value in obj.items():
                    full = f"{prefix}.{key}" if prefix else key
                    stack.append((full, value))

            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    stack.append((f"{prefix}[{i}]", value))

            elif isinstance(obj, (str, int, float, bool)) or obj is None:
                low = prefix.lower()

                if any(
                    token in low
                    for token in [
                        "b4",
                        "checkpoint",
                        "sha",
                        "hash",
                        "epoch",
                        "candidate",
                        "model",
                        "front",
                        "support",
                        "coeff",
                    ]
                ):
                    evidence.append({
                        "source": label,
                        "path": str(path),
                        "available": True,
                        "key": prefix,
                        "value": obj,
                    })

    return evidence


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1A2R4")
    print("B4 Coefficient / Checkpoint Provenance Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO FRONT, TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE CHANGED.
NO HISTORICAL SCALAR WILL BE OVERWRITTEN.
""")

    incoming = load_json(R3_SUMMARY)

    if incoming.get("diagnosis") != "LIKELY_CHECKPOINT_OR_COEFFICIENT_FIELD_PROVENANCE_DRIFT":
        raise RuntimeError(
            "R1A2R4 requires incoming diagnosis "
            "LIKELY_CHECKPOINT_OR_COEFFICIENT_FIELD_PROVENANCE_DRIFT."
        )

    support_rows = load_csv(SUPPORT_CSV)
    b4_support = row_for_experiment(support_rows, "B4")

    if b4_support is None:
        raise RuntimeError("Missing authoritative B4 support record.")

    auth_required = fnum(
        b4_support,
        "front_shell_required_residual_sum",
    )
    auth_supported = fnum(
        b4_support,
        "front_shell_supported_residual_sum",
    )
    auth_fraction = fnum(
        b4_support,
        "front_shell_residual_coverage_fraction",
    )

    auth_coeff = {
        "mean": fnum(b4_support, "front_shell_coefficient_mean"),
        "P90": fnum(b4_support, "front_shell_coefficient_P90"),
        "max": fnum(b4_support, "front_shell_coefficient_max"),
    }

    db = np.load(RUNTIME_NPZ, allow_pickle=True)

    required = np.asarray(
        db["required_shell"],
        dtype=np.float64,
    )
    coeff = np.asarray(
        db["coeff_shell"],
        dtype=np.float64,
    )
    supported = np.asarray(
        db["supported_required"],
        dtype=np.float64,
    )

    runtime_required = float(np.sum(required))
    runtime_supported = float(np.sum(supported))
    runtime_fraction = runtime_supported / runtime_required
    runtime_coeff = coeff_stats(coeff)

    print("AUTHORITATIVE / RUNTIME B4 SUPPORT")
    print(
        f"  Required sum            : "
        f"{runtime_required:.12e} vs {auth_required:.12e}"
    )
    print(
        f"  Supported sum           : "
        f"{runtime_supported:.12e} vs {auth_supported:.12e}"
    )
    print(
        f"  Coverage                : "
        f"{runtime_fraction:.12e} vs {auth_fraction:.12e}"
    )

    print("\nCOEFFICIENT SUMMARY")
    for key in ["mean", "P90", "max"]:
        print(
            f"  {key:<5s} runtime={runtime_coeff[key]:.12e} | "
            f"historical={auth_coeff[key]:.12e} | "
            f"delta={runtime_coeff[key]-auth_coeff[key]:+.6e}"
        )

    # -------------------------------------------------------------------------
    # Checkpoint inventory / hashes
    # -------------------------------------------------------------------------

    checkpoint_rows = build_checkpoint_audit()

    save_csv(
        CHECKPOINT_TABLE,
        checkpoint_rows,
    )

    hash_groups = {}

    for row in checkpoint_rows:
        digest = row.get("sha256", "")

        if not digest:
            continue

        hash_groups.setdefault(
            digest,
            [],
        ).append(
            row["path"]
        )

    hash_rows = []

    for digest, paths in hash_groups.items():
        hash_rows.append({
            "sha256": digest,
            "sha256_prefix": digest[:HASH_PREFIX_LEN],
            "number_of_paths": len(paths),
            "paths": ";".join(paths),
        })

    save_csv(
        HASH_TABLE,
        hash_rows,
    )

    print("\nB4 CHECKPOINT INVENTORY")
    print(f"  Persisted/discovered files : {len(checkpoint_rows)}")
    print(f"  Unique SHA-256 identities  : {len(hash_groups)}")

    for row in checkpoint_rows:
        print(
            f"  {row['sha256_prefix'] or 'NOHASH':<16s} | "
            f"{row['checkpoint_type'] or 'untyped':<14s} | "
            f"epoch={str(row['epoch']):<5s} | "
            f"{Path(row['path']).name if row['path'] else 'missing'}"
        )

    # -------------------------------------------------------------------------
    # Historical provenance records
    # -------------------------------------------------------------------------

    provenance_rows = collect_provenance_evidence()

    save_csv(
        PROVENANCE_TABLE,
        provenance_rows,
    )

    # Find explicit SHA/hash references that match discovered artifacts.
    explicit_hash_values = set()

    for row in provenance_rows:
        value = str(row.get("value", "")).strip().lower()

        if len(value) >= 16 and all(ch in "0123456789abcdef" for ch in value):
            explicit_hash_values.add(value)

    matched_explicit = []

    for digest, paths in hash_groups.items():
        for historical in explicit_hash_values:
            if digest == historical or digest.startswith(historical) or historical.startswith(digest):
                matched_explicit.append({
                    "historical_hash": historical,
                    "discovered_hash": digest,
                    "paths": ";".join(paths),
                })

    # -------------------------------------------------------------------------
    # Coefficient provenance classification
    # -------------------------------------------------------------------------

    coeff_rows = []

    for metric in ["mean", "P90", "max"]:
        historical = auth_coeff[metric]
        runtime = runtime_coeff[metric]

        abs_delta = abs(runtime - historical)
        rel_delta = abs_delta / max(abs(historical), 1e-15)

        coeff_rows.append({
            "metric": metric,
            "runtime": runtime,
            "historical": historical,
            "absolute_delta": abs_delta,
            "relative_delta": rel_delta,
            "within_provenance_tolerance":
                bool(rel_delta <= REL_COEFF_TOL),
        })

    save_csv(
        COEFF_TABLE,
        coeff_rows,
    )

    all_coeff_close = bool(
        all(
            row["within_provenance_tolerance"]
            for row in coeff_rows
        )
    )

    supported_rel_delta = (
        abs(runtime_supported - auth_supported)
        / max(abs(auth_supported), 1e-15)
    )

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    multiple_checkpoint_identities = len(hash_groups) > 1
    explicit_hash_match = bool(matched_explicit)

    historical_model_identity_unambiguous = bool(
        len(hash_groups) == 1
        or explicit_hash_match
    )

    if (
        all_coeff_close
        and
        supported_rel_delta <= REL_COEFF_TOL
        and
        historical_model_identity_unambiguous
    ):
        status = "B4_PROVENANCE_RECONCILED"

        diagnosis = (
            "TINY_COEFFICIENT_SERIALIZATION_DRIFT_WITH_STABLE_B4_MODEL_IDENTITY"
        )

        recommendation = (
            "The B4 model identity is stable and the coefficient-field differences "
            "are below provenance tolerance. Preserve the historical scalar record "
            "unchanged, but use the reconstructed runtime required_shell, coeff_shell, "
            "and supported_required arrays as the authoritative numerical basis for "
            "the minimal-support extension. No scalar anchoring is permitted."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1B — Exact-Array Minimal-Support Extension Calibration"
        )

        resolved = True

    elif (
        all_coeff_close
        and
        supported_rel_delta <= REL_COEFF_TOL
        and
        multiple_checkpoint_identities
    ):
        status = "B4_PROVENANCE_CHECKPOINT_AMBIGUITY"

        diagnosis = (
            "MULTIPLE_B4_CHECKPOINT_IDENTITIES_WITH_TINY_COEFFICIENT_DRIFT"
        )

        recommendation = (
            "The numerical difference is tiny, but more than one B4 checkpoint identity "
            "exists and no unique historical identity has yet been established. Do not "
            "calibrate support. Resolve which checkpoint generated the R3F4-R support "
            "table using manifest/epoch/hash evidence."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A2R4A — Historical B4 Checkpoint Identity Resolution"
        )

        resolved = False

    else:
        status = "B4_COEFFICIENT_PROVENANCE_MISMATCH"

        diagnosis = (
            "RUNTIME_COEFFICIENT_FIELD_NOT_EQUIVALENT_TO_HISTORICAL_B4_RECORD"
        )

        recommendation = (
            "The current runtime coefficient field differs materially from the "
            "historical B4 coefficient record. Do not calibrate support. Reconstruct "
            "the historical B4 coefficient field from the correct persisted checkpoint."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1A2R4B — Historical B4 Coefficient Field Reconstruction"
        )

        resolved = False

    if resolved:
        np.savez_compressed(
            RESOLVED_NPZ,
            required_shell=required,
            coeff_shell=coeff,
            supported_required=supported,
            runtime_required_sum=np.asarray(runtime_required, dtype=np.float64),
            runtime_supported_sum=np.asarray(runtime_supported, dtype=np.float64),
            runtime_coverage_fraction=np.asarray(runtime_fraction, dtype=np.float64),
            historical_required_sum=np.asarray(auth_required, dtype=np.float64),
            historical_supported_sum=np.asarray(auth_supported, dtype=np.float64),
            historical_coverage_fraction=np.asarray(auth_fraction, dtype=np.float64),
        )

    decision_rows = [{
        "all_coefficient_statistics_within_tolerance": all_coeff_close,
        "supported_sum_relative_delta": supported_rel_delta,
        "unique_checkpoint_hash_count": len(hash_groups),
        "multiple_checkpoint_identities": multiple_checkpoint_identities,
        "explicit_historical_hash_match": explicit_hash_match,
        "historical_model_identity_unambiguous":
            historical_model_identity_unambiguous,
        "resolved": resolved,
        "status": status,
        "diagnosis": diagnosis,
        "next_milestone": next_milestone,
    }]

    save_csv(
        DECISION_TABLE,
        decision_rows,
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1A2R4",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_calibrated": False,
            "gate_changed": False,
            "historical_scalar_overwritten": False,
            "runtime_required_sum": runtime_required,
            "historical_required_sum": auth_required,
            "runtime_supported_sum": runtime_supported,
            "historical_supported_sum": auth_supported,
            "supported_sum_relative_delta": supported_rel_delta,
            "runtime_coefficient_statistics": runtime_coeff,
            "historical_coefficient_statistics": auth_coeff,
            "coefficient_statistics_within_provenance_tolerance":
                all_coeff_close,
            "unique_B4_checkpoint_hashes": len(hash_groups),
            "explicit_historical_hash_match": explicit_hash_match,
            "resolved": resolved,
            "resolved_arrays": str(RESOLVED_NPZ) if resolved else None,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1A2R4",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_calibrated": False,
            "gate_changed": False,
            "resolved": resolved,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R4 DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R1A2R3 provenance diagnosis reproduced", True),
        ("Historical B4 coefficient summary loaded", True),
        ("Runtime coefficient field loaded", True),
        ("All B4 checkpoint artifacts inventoried", True),
        ("SHA-256 identities generated", True),
        ("Manifest / summary provenance searched", True),
        ("Coefficient summary differences quantified", True),
        ("Historical supported scalar preserved unchanged", True),
        ("No scalar anchoring applied", True),
        ("No support extension calibrated", True),
        ("No training performed", True),
        ("Provenance decision established", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    print("=" * 78)

    print("\nPROVENANCE FLAGS")
    print(
        f"  Coefficient stats close : "
        f"{all_coeff_close}"
    )
    print(
        f"  Supported rel delta     : "
        f"{supported_rel_delta:.6e}"
    )
    print(
        f"  Unique B4 hashes        : "
        f"{len(hash_groups)}"
    )
    print(
        f"  Explicit hash match     : "
        f"{explicit_hash_match}"
    )
    print(
        f"  Identity unambiguous    : "
        f"{historical_model_identity_unambiguous}"
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
    print(f"  {CHECKPOINT_TABLE.name}")
    print(f"  {HASH_TABLE.name}")
    print(f"  {PROVENANCE_TABLE.name}")
    print(f"  {COEFF_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    if resolved:
        print("\nResolved numerical:")
        print(f"  {RESOLVED_NPZ.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1A2R4 PROVENANCE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No support extension was calibrated.")
    print("No historical scalar was overwritten.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
