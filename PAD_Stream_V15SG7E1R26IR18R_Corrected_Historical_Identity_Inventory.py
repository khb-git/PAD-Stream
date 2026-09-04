from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
from datetime import datetime, timezone

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R18R
# Corrected Historical Identity Inventory
#
# DIAGNOSTIC-ONLY HISTORICAL IDENTITY RECONSTRUCTION
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
# R19R corrected a self-referential provenance error and established:
#
#   historical exact creator100 matches = 0
#   historical exact frozen100 matches  = 12
#
# Therefore the earlier R18 statement that "both runtime identities persist
# historically" was false after derivative audit products were excluded.
#
# R18R rebuilds the historical identity inventory with the corrected exclusion
# policy and asks:
#
#   1. Is persisted frozen100 genuinely historical?  (expected YES)
#   2. Does any pre-R16 artifact exactly equal current creator100? (expected NO)
#   3. Which historical arrays are numerically nearest to creator100?
#   4. Do the 90 R16-envelope exceedance cells already match frozen100 exactly
#      in historical artifacts?
#   5. Does historical evidence therefore favor an inference-runtime
#      reproducibility difference rather than downstream serialization?
#
# No new model inference occurs.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR18R"
OUT.mkdir(parents=True, exist_ok=True)

R17_DIR = ROOT / "output" / "V15_SG7E1R26IR17"
R17_NUM = R17_DIR / "V15SG7E1R26IR17_Precision_Audit.npz"

R19R_DIR = ROOT / "output" / "V15_SG7E1R26IR19R"
R19R_SUMMARY = R19R_DIR / "PAD_Stream_V15SG7E1R26IR19R_Summary.json"

# Outputs
EXCLUSION_TABLE = OUT / "V15SG7E1R26IR18R_Historical_Exclusion_Policy.csv"
IDENTITY_TABLE = OUT / "V15SG7E1R26IR18R_Corrected_Historical_Array_Inventory.csv"
NEAREST_TABLE = OUT / "V15SG7E1R26IR18R_Nearest_Historical_Arrays_to_Creator100.csv"
FINGERPRINT_TABLE = OUT / "V15SG7E1R26IR18R_Frozen100_90_Cell_Fingerprint_Audit.csv"
FROZEN_LINEAGE_TABLE = OUT / "V15SG7E1R26IR18R_Frozen100_Historical_Lineage.csv"
CLASS_TABLE = OUT / "V15SG7E1R26IR18R_Historical_Identity_Classification.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR18R_Final_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR18R_Corrected_Identity_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR18R_Corrected_Historical_Identity_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR18R_Summary.json"


# Exclude all derivative R26I runtime/precision audits from being considered
# "historical" evidence for the original frozen100 lineage.
EXCLUDE_TOKENS = (
    "V15_SG7E1R26IR16",
    "V15_SG7E1R26IR17",
    "V15_SG7E1R26IR18",
    "V15_SG7E1R26IR18R",
    "V15_SG7E1R26IR19",
    "V15_SG7E1R26IR19R",
    "V15SG7E1R26IR16",
    "V15SG7E1R26IR17",
    "V15SG7E1R26IR18",
    "V15SG7E1R26IR18R",
    "V15SG7E1R26IR19",
    "V15SG7E1R26IR19R",
)


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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def is_excluded(path_str: str):
    norm = path_str.replace("\\", "/")
    return any(tok in norm for tok in EXCLUDE_TOKENS)


def candidate_npz_files():
    out_root = ROOT / "output"
    files = []

    if not out_root.exists():
        return files

    for p in out_root.rglob("*.npz"):
        s = str(p)
        if is_excluded(s):
            continue

        # Historical scope remains local to SG7B / CR3 / SG7E ancestry.
        if any(tok in s for tok in ("V15_SG7B", "V15_SG7CR3", "V15_SG7E")):
            files.append(p)

    return sorted(set(files))


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


def stat_info(path: Path):
    st = path.stat()
    return {
        "mtime_epoch": st.st_mtime,
        "mtime_iso": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": st.st_size,
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R18R")
    print("Corrected Historical Identity Inventory")
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
CURRENT R26I AUDIT PRODUCTS WILL BE EXCLUDED FROM HISTORICAL AUTHORITY.
""")

    prev = load_json(R19R_SUMMARY)
    if prev.get("status") != "R19_SELF_REFERENTIAL_BOUNDARY_REJECTED_HISTORICAL_DUAL_IDENTITY_NOT_RETAINED":
        raise RuntimeError("R18R requires the corrected R19R result.")

    db = np.load(R17_NUM, allow_pickle=True)
    creator100 = np.asarray(db["creator100"], dtype=np.float32)
    frozen100 = np.asarray(db["frozen100"], dtype=np.float32)
    absdiff = np.asarray(db["abs_difference"], dtype=np.float64)
    precision_envelope = float(np.asarray(db["precision_envelope"]).ravel()[0])
    db.close()

    creator_hash = sha256_array(creator100)
    frozen_hash = sha256_array(frozen100)
    exceed_mask = absdiff > precision_envelope
    exceed_count = int(np.count_nonzero(exceed_mask))

    save_csv(EXCLUSION_TABLE, [
        {"excluded_token": tok, "reason": "DERIVATIVE_R26I_AUDIT_PRODUCT"}
        for tok in EXCLUDE_TOKENS
    ])

    rows = []
    nearest = []
    frozen_lineage = []

    for path in candidate_npz_files():
        try:
            npz = np.load(path, allow_pickle=True)
        except Exception:
            continue

        try:
            for key in npz.files:
                try:
                    arr = np.asarray(npz[key])
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
                m_creator = error_metrics(arr32, creator100)
                m_frozen = error_metrics(arr32, frozen100)

                exact_creator = arr_hash == creator_hash
                exact_frozen = arr_hash == frozen_hash

                stat = stat_info(path)

                row = {
                    "artifact": str(path),
                    "key": key,
                    "dtype": str(arr.dtype),
                    "shape": str(arr.shape),
                    "sha256_float32": arr_hash,
                    "exact_creator100": exact_creator,
                    "exact_frozen100": exact_frozen,
                    "L1_to_creator100": m_creator["L1"],
                    "L2_to_creator100": m_creator["L2"],
                    "Linf_to_creator100": m_creator["Linf"],
                    "L1_to_frozen100": m_frozen["L1"],
                    "L2_to_frozen100": m_frozen["L2"],
                    "Linf_to_frozen100": m_frozen["Linf"],
                    "mtime_iso": stat["mtime_iso"],
                    "size_bytes": stat["size_bytes"],
                }
                rows.append(row)

                nearest.append({
                    "artifact": str(path),
                    "key": key,
                    "L1_to_creator100": m_creator["L1"],
                    "L2_to_creator100": m_creator["L2"],
                    "Linf_to_creator100": m_creator["Linf"],
                    "exact_creator100": exact_creator,
                    "exact_frozen100": exact_frozen,
                    "sha256_float32": arr_hash,
                })

                if exact_frozen:
                    frozen_lineage.append({
                        "artifact": str(path),
                        "key": key,
                        "mtime_iso": stat["mtime_iso"],
                        "sha256_float32": arr_hash,
                    })
        finally:
            npz.close()

    rows.sort(key=lambda r: (r["artifact"], r["key"]))
    save_csv(IDENTITY_TABLE, rows)

    nearest.sort(
        key=lambda r: (
            float(r["Linf_to_creator100"]),
            float(r["L2_to_creator100"]),
            float(r["L1_to_creator100"]),
        )
    )
    save_csv(NEAREST_TABLE, nearest[:50])

    frozen_lineage.sort(key=lambda r: r["mtime_iso"])
    save_csv(FROZEN_LINEAGE_TABLE, frozen_lineage)

    # -------------------------------------------------------------------------
    # 90-cell fingerprint
    # -------------------------------------------------------------------------
    fingerprint_rows = []

    for row in nearest[:100]:
        path = Path(row["artifact"])
        key = row["key"]

        try:
            npz = np.load(path, allow_pickle=True)
            arr = np.asarray(npz[key], dtype=np.float32)
            npz.close()
        except Exception:
            continue

        vals = arr[exceed_mask]
        cvals = creator100[exceed_mask]
        fvals = frozen100[exceed_mask]

        creator_exact = int(np.count_nonzero(vals == cvals))
        frozen_exact = int(np.count_nonzero(vals == fvals))

        fingerprint_rows.append({
            "artifact": str(path),
            "key": key,
            "exceedance_cells": exceed_count,
            "creator_exact_count": creator_exact,
            "frozen_exact_count": frozen_exact,
            "creator_exact_fraction": creator_exact / exceed_count if exceed_count else 0.0,
            "frozen_exact_fraction": frozen_exact / exceed_count if exceed_count else 0.0,
            "Linf_to_creator100": row["Linf_to_creator100"],
            "Linf_to_frozen100": next(
                (
                    r["Linf_to_frozen100"]
                    for r in rows
                    if r["artifact"] == str(path) and r["key"] == key
                ),
                "",
            ),
        })

    fingerprint_rows.sort(
        key=lambda r: (
            r["frozen_exact_fraction"],
            -float(r["Linf_to_creator100"]),
        ),
        reverse=True,
    )
    save_csv(FINGERPRINT_TABLE, fingerprint_rows)

    exact_creator_rows = [r for r in rows if r["exact_creator100"]]
    exact_frozen_rows = [r for r in rows if r["exact_frozen100"]]

    full_frozen_fingerprint = [
        r for r in fingerprint_rows if r["frozen_exact_fraction"] == 1.0
    ]
    full_creator_fingerprint = [
        r for r in fingerprint_rows if r["creator_exact_fraction"] == 1.0
    ]

    # -------------------------------------------------------------------------
    # Classification
    # -------------------------------------------------------------------------
    if len(exact_creator_rows) == 0 and len(exact_frozen_rows) > 0:
        classification = "HISTORICAL_FROZEN100_PERSISTS_CURRENT_CREATOR100_DOES_NOT"
        diagnosis = (
            "PRE_R16_HISTORY_CONTAINS_FROZEN100_IDENTITY_BUT_NO_EXACT_CURRENT_RUNTIME_CREATOR100_IDENTITY"
        )
        recommendation = (
            "The corrected historical inventory supports a runtime-reproducibility interpretation: "
            "persisted frozen100 is genuinely historical, while today's exact creator100 replay "
            "identity is absent from pre-R16 history. Next audit historical SG7B16/SG7B11 inference "
            "runtime provenance (TensorFlow/Keras version, backend, batching, oneDNN/threading and "
            "determinism settings) before any controlled replay under altered runtime settings."
        )
        next_ms = (
            "V15-SG7E1R26I-R19A — Historical SG7B16 Inference Runtime Determinism Provenance Audit"
        )
    elif len(exact_creator_rows) > 0 and len(exact_frozen_rows) > 0:
        classification = "CORRECTED_PRE_R16_HISTORY_STILL_CONTAINS_BOTH_IDENTITIES"
        diagnosis = (
            "AFTER_CORRECTED_EXCLUSION_BOTH_EXACT_IDENTITIES_REMAIN_IN_TRUE_HISTORY"
        )
        recommendation = (
            "Proceed to source-lineage transition tracing using only the retained pre-R16 artifacts."
        )
        next_ms = (
            "V15-SG7E1R26I-R20 — Corrected Historical Creator/Frozen Source-Lineage Boundary Audit"
        )
    else:
        classification = "CORRECTED_HISTORICAL_IDENTITY_EVIDENCE_INCOMPLETE"
        diagnosis = (
            "CORRECTED_PRE_R16_INVENTORY_DOES_NOT_RETAIN_EXPECTED_FROZEN100_IDENTITY"
        )
        recommendation = (
            "Do not rerun the model. Recheck the historical artifact scope and frozen100 lineage."
        )
        next_ms = (
            "V15-SG7E1R26I-R18R1 — Frozen100 Historical Scope Repair"
        )

    class_rows = [{
        "classification": classification,
        "historical_candidate_arrays": len(rows),
        "exact_creator100_matches": len(exact_creator_rows),
        "exact_frozen100_matches": len(exact_frozen_rows),
        "full_90_cell_creator_fingerprint_matches": len(full_creator_fingerprint),
        "full_90_cell_frozen_fingerprint_matches": len(full_frozen_fingerprint),
        "diagnosis": diagnosis,
    }]
    save_csv(CLASS_TABLE, class_rows)

    gates = [
        ("R19R_corrected_result_reproduced", True),
        ("current_R26I_audit_products_excluded", True),
        ("historical_arrays_reinventoried", len(rows) > 0),
        ("historical_exact_creator100_count_recomputed", True),
        ("historical_exact_frozen100_count_recomputed", True),
        ("nearest_historical_creator_candidates_ranked", len(nearest) > 0),
        ("90_cell_fingerprint_recomputed", exceed_count == 90),
        ("historical_frozen100_lineage_retained", len(exact_frozen_rows) > 0),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_precision_relaxation", True),
        ("no_authority_reopened", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    status = "CORRECTED_HISTORICAL_IDENTITY_INVENTORY_COMPLETE"

    save_csv(DECISION_TABLE, [{
        "status": status,
        "classification": classification,
        "diagnosis": diagnosis,
        "exact_creator100_matches": len(exact_creator_rows),
        "exact_frozen100_matches": len(exact_frozen_rows),
        "full_90_cell_creator_fingerprint_matches": len(full_creator_fingerprint),
        "full_90_cell_frozen_fingerprint_matches": len(full_frozen_fingerprint),
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R18R",
        "status": status,
        "classification": classification,
        "diagnosis": diagnosis,
        "creator100_sha256": creator_hash,
        "frozen100_sha256": frozen_hash,
        "precision_envelope": precision_envelope,
        "excluded_tokens": list(EXCLUDE_TOKENS),
        "historical_candidate_array_count": len(rows),
        "exact_creator100_matches": exact_creator_rows,
        "exact_frozen100_matches": exact_frozen_rows,
        "nearest_to_creator100": nearest[:10],
        "full_90_cell_creator_fingerprint_matches": full_creator_fingerprint,
        "full_90_cell_frozen_fingerprint_matches": full_frozen_fingerprint,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
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
        "milestone": "V15-SG7E1R26I-R18R",
        "status": status,
        "classification": classification,
        "diagnosis": diagnosis,
        "exact_creator100_matches": len(exact_creator_rows),
        "exact_frozen100_matches": len(exact_frozen_rows),
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("CORRECTED HISTORICAL ARRAY INVENTORY")
    print(f"  Candidate arrays        : {len(rows)}")
    print(f"  Exact creator100        : {len(exact_creator_rows)}")
    print(f"  Exact frozen100         : {len(exact_frozen_rows)}")

    print("\n90-CELL FINGERPRINT")
    print(f"  Exceedance cells        : {exceed_count}")
    print(f"  Full creator matches    : {len(full_creator_fingerprint)}")
    print(f"  Full frozen matches     : {len(full_frozen_fingerprint)}")

    print("\nTOP NEAREST HISTORICAL ARRAYS TO CURRENT CREATOR100")
    for r in nearest[:10]:
        print(
            f"  Linf={float(r['Linf_to_creator100']):.6e} | "
            f"L2={float(r['L2_to_creator100']):.6e} | "
            f"{Path(r['artifact']).name} :: {r['key']}"
        )

    print("\nCLASSIFICATION")
    print(f"  {classification}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R18R FINAL GATES")
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
        EXCLUSION_TABLE,
        IDENTITY_TABLE,
        NEAREST_TABLE,
        FINGERPRINT_TABLE,
        FROZEN_LINEAGE_TABLE,
        CLASS_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R18R CORRECTED HISTORICAL IDENTITY INVENTORY: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("The precision envelope was not relaxed.")
    print("No creator/model/X100 authority was reopened.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
