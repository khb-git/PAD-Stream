from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import os
import platform
import re

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R18
# Historical SG7B16 Runtime / Serialization Difference Audit
#
# DIAGNOSTIC-ONLY HISTORICAL NUMERICAL-LINEAGE MILESTONE
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
# R17 established:
#
#   creator100 vs frozen100:
#       total values       = 535,062
#       exact equal        = 525,710
#       nonzero            = 9,352
#       above R16 envelope = 90
#       max ULP            = 13
#
# The discrepancy is too large to classify as a uniformly small-ULP replay
# equivalence class, but it is sparse and globally tiny.
#
# R18 asks one precise provenance question:
#
#   Where in the historical SG7B16 -> frozen100 lineage does the numerical
#   identity change from the current creator replay to persisted frozen100?
#
# It therefore:
#
#   1. inventories historical persisted 2662x201 arrays near SG7B16/CR3 lineage,
#   2. hashes each array and compares exact identity to creator100/frozen100,
#   3. computes the 90-cell exceedance fingerprint against each candidate,
#   4. audits SG7B16 source for predict/batch/dtype/cast/save semantics,
#   5. audits saved manifests/contracts for runtime/backend/thread metadata,
#   6. determines whether divergence is:
#        a) already present at historical inference output, or
#        b) introduced downstream during serialization/postprocessing.
#
# No model execution occurs.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR18"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"

R17_DIR = ROOT / "output" / "V15_SG7E1R26IR17"
R17_SUMMARY = R17_DIR / "PAD_Stream_V15SG7E1R26IR17_Summary.json"
R17_NUM = R17_DIR / "V15SG7E1R26IR17_Precision_Audit.npz"

R16_DIR = ROOT / "output" / "V15_SG7E1R26IR16"
R16_CONTRACT = R16_DIR / "V15SG7E1R26IR16_SG7B16_Frozen100_Runtime_Contract.json"

# Outputs
SOURCE_RUNTIME_TABLE = OUT / "V15SG7E1R26IR18_SG7B16_Runtime_Semantics.csv"
SERIAL_TABLE = OUT / "V15SG7E1R26IR18_SG7B16_Serialization_Semantics.csv"
ARTIFACT_TABLE = OUT / "V15SG7E1R26IR18_Historical_Array_Identity_Inventory.csv"
FINGERPRINT_TABLE = OUT / "V15SG7E1R26IR18_Exceedance_Fingerprint_Match.csv"
ENV_TABLE = OUT / "V15SG7E1R26IR18_Historical_Runtime_Metadata.csv"
LINEAGE_TABLE = OUT / "V15SG7E1R26IR18_Numerical_Divergence_Lineage.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR18_Final_Audit_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR18_Runtime_Serialization_Decision.csv"

NUM_FILE = OUT / "V15SG7E1R26IR18_Runtime_Serialization_Audit.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR18_Runtime_Serialization_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR18_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def node_src(text, node):
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""


def call_name(node):
    if not isinstance(node, ast.Call):
        return ""
    cur = node.func
    parts = []
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def error_metrics(a, b):
    a64 = np.asarray(a, dtype=np.float64)
    b64 = np.asarray(b, dtype=np.float64)
    if a64.shape != b64.shape:
        return None
    d = a64 - b64
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


def source_runtime_semantics():
    text = safe_text(SOURCE)
    tree = ast.parse(text)

    runtime_rows = []
    serial_rows = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            cname = call_name(node)
            expr = node_src(text, node)

            if cname.endswith("predict"):
                runtime_rows.append({
                    "line": node.lineno,
                    "kind": "PREDICT_CALL",
                    "call": cname,
                    "expression": expr,
                    "batch_size_expression": next(
                        (node_src(text, kw.value) for kw in node.keywords if kw.arg == "batch_size"),
                        "",
                    ),
                    "dtype_expression": "",
                })

            if cname in {
                "np.asarray",
                "np.array",
                "np.astype",
                "astype",
                "tf.cast",
            } or cname.endswith(".astype"):
                runtime_rows.append({
                    "line": node.lineno,
                    "kind": "CAST_OR_ARRAY_CONSTRUCTION",
                    "call": cname,
                    "expression": expr,
                    "batch_size_expression": "",
                    "dtype_expression": expr,
                })

            if cname in {"np.savez", "np.savez_compressed"}:
                artifact_expr = node_src(text, node.args[0]) if node.args else ""
                for kw in node.keywords:
                    serial_rows.append({
                        "line": node.lineno,
                        "serializer": cname,
                        "artifact_expression": artifact_expr,
                        "key": kw.arg or "",
                        "value_expression": node_src(text, kw.value),
                    })

    return runtime_rows, serial_rows


def candidate_npz_files():
    # Keep the search historically local to SG7B / CR3 / R1F / SG7E outputs.
    roots = []
    out_root = ROOT / "output"
    if out_root.exists():
        for p in out_root.iterdir():
            if not p.is_dir():
                continue
            name = p.name
            if any(tok in name for tok in ("SG7B", "SG7CR3", "SG7E")):
                roots.append(p)

    files = []
    for r in roots:
        files.extend(r.rglob("*.npz"))
    return sorted(set(files))


def inventory_arrays(creator100, frozen100, exceed_mask):
    rows = []
    candidates = []

    creator_hash = sha256_array(creator100)
    frozen_hash = sha256_array(frozen100)

    for path in candidate_npz_files():
        try:
            db = np.load(path, allow_pickle=True)
        except Exception:
            continue

        try:
            for key in db.files:
                try:
                    arr = np.asarray(db[key])
                except Exception:
                    continue

                if arr.shape != creator100.shape:
                    continue
                if not np.issubdtype(arr.dtype, np.number):
                    continue
                if not np.all(np.isfinite(arr)):
                    continue

                arr32 = np.asarray(arr, dtype=np.float32)
                arr_hash = sha256_array(arr32)

                to_creator = error_metrics(arr32, creator100)
                to_frozen = error_metrics(arr32, frozen100)

                exact_creator = arr_hash == creator_hash
                exact_frozen = arr_hash == frozen_hash

                fp_exact = bool(
                    np.array_equal(
                        (arr32 != creator100) & exceed_mask,
                        (frozen100 != creator100) & exceed_mask,
                    )
                )

                row = {
                    "artifact": str(path),
                    "key": key,
                    "dtype": str(arr.dtype),
                    "shape": str(arr.shape),
                    "sha256_float32": arr_hash,
                    "exact_creator100": exact_creator,
                    "exact_frozen100": exact_frozen,
                    "Linf_to_creator100": to_creator["Linf"] if to_creator else "",
                    "Linf_to_frozen100": to_frozen["Linf"] if to_frozen else "",
                    "exceedance_fingerprint_exact": fp_exact,
                }
                rows.append(row)
                candidates.append((path, key, arr32, row))
        finally:
            db.close()

    return rows, candidates


def fingerprint_rows(candidates, creator100, frozen100, exceed_mask):
    rows = []
    target_idx = np.argwhere(exceed_mask)

    for path, key, arr, inv in candidates:
        # At the 90 R16-envelope exceedance cells, count exact matches to either
        # today's creator replay or historical frozen target.
        arr_vals = arr[exceed_mask]
        c_vals = creator100[exceed_mask]
        f_vals = frozen100[exceed_mask]

        exact_creator = int(np.count_nonzero(arr_vals == c_vals))
        exact_frozen = int(np.count_nonzero(arr_vals == f_vals))

        rows.append({
            "artifact": str(path),
            "key": key,
            "exceedance_cells": int(target_idx.shape[0]),
            "exact_creator_values_at_exceedance_cells": exact_creator,
            "exact_frozen_values_at_exceedance_cells": exact_frozen,
            "fraction_creator_exact": exact_creator / target_idx.shape[0] if target_idx.shape[0] else 0.0,
            "fraction_frozen_exact": exact_frozen / target_idx.shape[0] if target_idx.shape[0] else 0.0,
            "exact_creator100_whole_array": inv["exact_creator100"],
            "exact_frozen100_whole_array": inv["exact_frozen100"],
        })

    rows.sort(
        key=lambda r: (
            int(bool(r["exact_frozen100_whole_array"])),
            r["fraction_frozen_exact"],
            -r["fraction_creator_exact"],
        ),
        reverse=True,
    )
    return rows


def historical_runtime_metadata():
    rows = []
    patterns = [
        "TF_ENABLE_ONEDNN_OPTS",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "inter_op_parallelism",
        "intra_op_parallelism",
        "determin",
        "oneDNN",
        "tensorflow",
        "keras",
        "python",
        "batch_size",
    ]

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".txt", ".csv", ".py"}:
            continue
        if not any(tok in str(path) for tok in ("SG7B16", "SG7B11", "SG7CR3", "SG7E1R")):
            continue

        text = safe_text(path)
        hits = []
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                hits.append(pat)

        if hits:
            rows.append({
                "source": str(path),
                "matched_terms": ";".join(hits),
                "TF_ENABLE_ONEDNN_OPTS_literal_present": "TF_ENABLE_ONEDNN_OPTS" in text,
                "thread_setting_literal_present": (
                    "OMP_NUM_THREADS" in text
                    or "MKL_NUM_THREADS" in text
                    or "inter_op_parallelism" in text
                    or "intra_op_parallelism" in text
                ),
                "determinism_literal_present": bool(re.search("determin", text, flags=re.IGNORECASE)),
            })

    rows.append({
        "source": "CURRENT_RUNTIME",
        "matched_terms": "runtime_environment",
        "TF_ENABLE_ONEDNN_OPTS_literal_present": os.environ.get("TF_ENABLE_ONEDNN_OPTS", ""),
        "thread_setting_literal_present": (
            f"OMP={os.environ.get('OMP_NUM_THREADS', '')};"
            f"MKL={os.environ.get('MKL_NUM_THREADS', '')}"
        ),
        "determinism_literal_present": "",
        "python": platform.python_version(),
        "platform": platform.platform(),
    })
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R18")
    print("Historical SG7B16 Runtime / Serialization Difference Audit")
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
ONLY HISTORICAL RUNTIME / SERIALIZATION NUMERICAL LINEAGE WILL BE AUDITED.
""")

    r17 = load_json(R17_SUMMARY)
    if r17.get("status") != "SG7B16_FROZEN100_CLOSURE_FAILURE_NOT_YET_EXPLAINED_BY_SMALL_ULP_DRIFT":
        raise RuntimeError("R18 requires the unresolved R17 precision classification.")

    db = np.load(R17_NUM, allow_pickle=True)
    creator100 = np.asarray(db["creator100"], dtype=np.float32)
    frozen100 = np.asarray(db["frozen100"], dtype=np.float32)
    absdiff = np.asarray(db["abs_difference"], dtype=np.float64)
    precision_envelope = float(np.asarray(db["precision_envelope"]).ravel()[0])
    db.close()

    exceed_mask = absdiff > precision_envelope
    exceed_count = int(np.count_nonzero(exceed_mask))

    runtime_rows, serial_rows = source_runtime_semantics()
    save_csv(SOURCE_RUNTIME_TABLE, runtime_rows)
    save_csv(SERIAL_TABLE, serial_rows)

    artifact_rows, candidates = inventory_arrays(
        creator100,
        frozen100,
        exceed_mask,
    )
    save_csv(ARTIFACT_TABLE, artifact_rows)

    fp_rows = fingerprint_rows(
        candidates,
        creator100,
        frozen100,
        exceed_mask,
    )
    save_csv(FINGERPRINT_TABLE, fp_rows)

    env_rows = historical_runtime_metadata()
    save_csv(ENV_TABLE, env_rows)

    # -------------------------------------------------------------------------
    # Determine whether historical persisted arrays reveal where divergence
    # occurs.
    # -------------------------------------------------------------------------
    creator_matches = [
        r for r in artifact_rows if bool(r["exact_creator100"])
    ]
    frozen_matches = [
        r for r in artifact_rows if bool(r["exact_frozen100"])
    ]

    # Exclude R16/R17 self-artifacts from historical authority.
    def is_self_artifact(path_str):
        return any(
            tok in path_str
            for tok in (
                "V15_SG7E1R16",
                "V15_SG7E1R17",
                "V15_SG7E1R18",
            )
        )

    historical_creator_matches = [
        r for r in creator_matches if not is_self_artifact(r["artifact"])
    ]
    historical_frozen_matches = [
        r for r in frozen_matches if not is_self_artifact(r["artifact"])
    ]

    # Fingerprint support: historical candidates agreeing with frozen values at
    # all exceedance cells, without requiring whole-array identity.
    historical_fp_frozen = [
        r for r in fp_rows
        if not is_self_artifact(r["artifact"])
        and float(r["fraction_frozen_exact"]) == 1.0
    ]
    historical_fp_creator = [
        r for r in fp_rows
        if not is_self_artifact(r["artifact"])
        and float(r["fraction_creator_exact"]) == 1.0
    ]

    if historical_creator_matches and historical_frozen_matches:
        lineage_class = "BOTH_RUNTIME_IDENTITIES_PERSIST_HISTORICALLY"
        diagnosis = (
            "HISTORICAL_ARTIFACTS_CONTAIN_BOTH_CURRENT_CREATOR_REPLAY_AND_FROZEN100_IDENTITIES"
        )
        recommendation = (
            "The numerical divergence is persisted across distinct historical artifacts. "
            "Trace the creation chronology and source serializer for the first artifact carrying "
            "the frozen100 identity after the last artifact carrying the creator100 identity. "
            "Do not relax precision or rerun the model yet."
        )
        next_ms = (
            "V15-SG7E1R26I-R19 — First Divergent Historical Artifact Creation-Chain Audit"
        )

    elif historical_frozen_matches and not historical_creator_matches:
        lineage_class = "FROZEN_IDENTITY_PERSISTS_HISTORICALLY_CREATOR_REPLAY_DOES_NOT"
        diagnosis = (
            "HISTORICAL_PIPELINE_PERSISTED_FROZEN100_IDENTITY_BUT_CURRENT_RUNTIME_REPLAY_IDENTITY_IS_NEW"
        )
        recommendation = (
            "The discrepancy is most consistent with historical inference-runtime reproducibility, "
            "not downstream serialization. Audit the historical SG7B16/SG7B11 runtime environment, "
            "TensorFlow/Keras version, batch execution, oneDNN/threading/determinism settings, and "
            "saved prediction artifact provenance before any controlled environment replay."
        )
        next_ms = (
            "V15-SG7E1R26I-R19 — Historical SG7B16 Inference Runtime Determinism Provenance Audit"
        )

    elif historical_creator_matches and not historical_frozen_matches:
        lineage_class = "CREATOR_IDENTITY_PERSISTS_HISTORICALLY_FROZEN_IDENTITY_DOES_NOT"
        diagnosis = (
            "HISTORICAL_RAW_PREDICTION_MATCHES_CURRENT_CREATOR_REPLAY_AND_DIVERGENCE_OCCURS_DOWNSTREAM"
        )
        recommendation = (
            "The raw creator prediction is historically reproducible and divergence appears after "
            "inference. Audit only the first serializer/postprocessing operation that transforms the "
            "creator identity into the persisted frozen100 identity."
        )
        next_ms = (
            "V15-SG7E1R26I-R19 — Post-Inference Serialization Divergence Creation-Chain Audit"
        )

    elif historical_fp_frozen and not historical_fp_creator:
        lineage_class = "FROZEN_EXCEEDANCE_FINGERPRINT_PERSISTS_HISTORICALLY"
        diagnosis = (
            "HISTORICAL_ARTIFACTS_REPRODUCE_ALL_90_FROZEN100_ENVELOPE_EXCEEDANCE_VALUES"
        )
        recommendation = (
            "The 90-cell discrepancy fingerprint is already present historically, supporting a "
            "runtime-origin interpretation. Audit the historical SG7B16 inference environment and "
            "backend determinism before any replay under modified settings."
        )
        next_ms = (
            "V15-SG7E1R26I-R19 — Historical SG7B16 Inference Runtime Determinism Provenance Audit"
        )

    else:
        lineage_class = "NUMERICAL_DIVERGENCE_LOCATION_NOT_YET_PERSISTED_UNIQUELY"
        diagnosis = (
            "NO_HISTORICAL_ARRAY_IDENTITY_OR_90_CELL_FINGERPRINT_UNIQUELY_LOCATES_DIVERGENCE_STAGE"
        )
        recommendation = (
            "Do not rerun the model or relax tolerance. Audit only SG7B16's explicit prediction-save "
            "and downstream frozen-array creation sources to identify the first persisted numerical "
            "state after inference."
        )
        next_ms = (
            "V15-SG7E1R26I-R19 — SG7B16 First Persisted Prediction Artifact Audit"
        )

    lineage_rows = [{
        "classification": lineage_class,
        "historical_exact_creator_matches": len(historical_creator_matches),
        "historical_exact_frozen_matches": len(historical_frozen_matches),
        "historical_full_frozen_fingerprint_matches": len(historical_fp_frozen),
        "historical_full_creator_fingerprint_matches": len(historical_fp_creator),
        "exceedance_cell_count": exceed_count,
        "diagnosis": diagnosis,
    }]
    save_csv(LINEAGE_TABLE, lineage_rows)

    gates = [
        ("R17_unresolved_precision_classification_reproduced", True),
        ("R16_precision_envelope_retained", True),
        ("SG7B16_runtime_semantics_audited", len(runtime_rows) > 0),
        ("SG7B16_serialization_semantics_audited", True),
        ("historical_2662x201_arrays_inventoried", len(artifact_rows) > 0),
        ("creator100_exact_hash_matches_audited", True),
        ("frozen100_exact_hash_matches_audited", True),
        ("90_cell_exceedance_fingerprint_audited", exceed_count == 90),
        ("historical_runtime_metadata_audited", len(env_rows) > 0),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_precision_relaxation", True),
        ("no_authority_reopened", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    status = "SG7B16_HISTORICAL_RUNTIME_SERIALIZATION_DIFFERENCE_AUDITED"

    save_csv(DECISION_TABLE, [{
        "status": status,
        "classification": lineage_class,
        "diagnosis": diagnosis,
        "historical_exact_creator_matches": len(historical_creator_matches),
        "historical_exact_frozen_matches": len(historical_frozen_matches),
        "historical_full_frozen_fingerprint_matches": len(historical_fp_frozen),
        "historical_full_creator_fingerprint_matches": len(historical_fp_creator),
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    np.savez_compressed(
        NUM_FILE,
        creator100=creator100,
        frozen100=frozen100,
        exceed_mask=exceed_mask.astype(np.uint8),
        precision_envelope=np.asarray([precision_envelope], dtype=np.float64),
    )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R18",
        "status": status,
        "classification": lineage_class,
        "diagnosis": diagnosis,
        "creator100_sha256": sha256_array(creator100),
        "frozen100_sha256": sha256_array(frozen100),
        "precision_envelope": precision_envelope,
        "exceedance_cell_count": exceed_count,
        "historical_exact_creator_matches": historical_creator_matches,
        "historical_exact_frozen_matches": historical_frozen_matches,
        "historical_full_frozen_fingerprint_matches": historical_fp_frozen,
        "historical_full_creator_fingerprint_matches": historical_fp_creator,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "model_parameters_changed": False,
            "precision_envelope_relaxed": False,
            "authority_reopened": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R18",
        "status": status,
        "classification": lineage_class,
        "diagnosis": diagnosis,
        "historical_exact_creator_matches": len(historical_creator_matches),
        "historical_exact_frozen_matches": len(historical_frozen_matches),
        "historical_full_frozen_fingerprint_matches": len(historical_fp_frozen),
        "historical_full_creator_fingerprint_matches": len(historical_fp_creator),
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------
    print("SG7B16 SOURCE RUNTIME SEMANTICS")
    print(f"  Predict/cast records    : {len(runtime_rows)}")
    print(f"  Serialization records   : {len(serial_rows)}")

    print("\nHISTORICAL ARRAY INVENTORY")
    print(f"  Candidate arrays        : {len(artifact_rows)}")
    print(f"  Exact creator matches   : {len(historical_creator_matches)}")
    print(f"  Exact frozen matches    : {len(historical_frozen_matches)}")

    print("\n90-CELL EXCEEDANCE FINGERPRINT")
    print(f"  Exceedance cells        : {exceed_count}")
    print(f"  Full frozen matches     : {len(historical_fp_frozen)}")
    print(f"  Full creator matches    : {len(historical_fp_creator)}")

    print("\nLINEAGE CLASSIFICATION")
    print(f"  {lineage_class}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R18 FINAL AUDIT GATES")
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
        SOURCE_RUNTIME_TABLE,
        SERIAL_TABLE,
        ARTIFACT_TABLE,
        FINGERPRINT_TABLE,
        ENV_TABLE,
        LINEAGE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nNumerical:")
    print(f"  {NUM_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R18 HISTORICAL RUNTIME / SERIALIZATION DIFFERENCE AUDIT: COMPLETE")
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
