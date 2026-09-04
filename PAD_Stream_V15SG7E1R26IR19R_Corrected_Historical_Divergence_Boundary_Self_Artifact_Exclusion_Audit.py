from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
from datetime import datetime, timezone


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R19R
# Corrected Historical Divergence Boundary / Self-Artifact Exclusion Audit
#
# PURPOSE
# -------
# R19 produced an invalid "resolved" boundary because its historical-match
# filter excluded tokens such as "V15_SG7E1R17" rather than the actual current
# audit directory token "V15_SG7E1R26IR17".
#
# Consequently, R19 selected:
#
#   output/V15_SG7E1R26IR17/V15SG7E1R26IR17_Precision_Audit.npz
#
# as BOTH the last creator artifact and first frozen artifact. That file is an
# audit product containing both arrays by construction and cannot establish a
# historical creator->frozen transition.
#
# R19R repairs ONLY the self-artifact exclusion policy and reruns the boundary
# determination from the R18 historical array inventory.
#
# NO TRAINING.
# NO MODEL.PREDICT.
# NO MODEL/X100/CREATOR AUTHORITY CHANGE.
# NO PRECISION-ENVELOPE CHANGE.
# NO LATER-TIME STATE GENERATION.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR19R"
OUT.mkdir(parents=True, exist_ok=True)

R18_DIR = ROOT / "output" / "V15_SG7E1R26IR18"
R18_SUMMARY = R18_DIR / "PAD_Stream_V15SG7E1R26IR18_Summary.json"
R18_ARTIFACTS = R18_DIR / "V15SG7E1R26IR18_Historical_Array_Identity_Inventory.csv"

R19_DIR = ROOT / "output" / "V15_SG7E1R26IR19"
R19_SUMMARY = R19_DIR / "PAD_Stream_V15SG7E1R26IR19_Summary.json"

FILTER_TABLE = OUT / "V15SG7E1R26IR19R_Self_Artifact_Exclusion_Audit.csv"
IDENTITY_TABLE = OUT / "V15SG7E1R26IR19R_Corrected_Historical_Identity_Inventory.csv"
CHRON_TABLE = OUT / "V15SG7E1R26IR19R_Corrected_Identity_Chronology.csv"
BOUNDARY_TABLE = OUT / "V15SG7E1R26IR19R_Corrected_Divergence_Boundary.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR19R_Final_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR19R_Corrected_Decision.csv"
CONTRACT_FILE = OUT / "V15SG7E1R26IR19R_Corrected_Boundary_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR19R_Summary.json"


# Exclude ALL audit products created at or after the current replay/precision
# investigation. They are derivative artifacts and cannot serve as historical
# provenance for the original frozen100 transition.
SELF_AUDIT_TOKENS = (
    "V15_SG7E1R26IR16",
    "V15_SG7E1R26IR17",
    "V15_SG7E1R26IR18",
    "V15_SG7E1R26IR19",
    "V15_SG7E1R26IR19R",
    "V15SG7E1R26IR16",
    "V15SG7E1R26IR17",
    "V15SG7E1R26IR18",
    "V15SG7E1R26IR19",
    "V15SG7E1R26IR19R",
)


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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def normalize_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes"}


def is_self_audit_artifact(path_str: str):
    norm = path_str.replace("\\", "/")
    return any(tok in norm for tok in SELF_AUDIT_TOKENS)


def stat_row(path_str):
    p = Path(path_str)
    if not p.exists():
        return {
            "exists": False,
            "mtime_epoch": "",
            "mtime_iso": "",
            "size_bytes": "",
        }
    st = p.stat()
    return {
        "exists": True,
        "mtime_epoch": st.st_mtime,
        "mtime_iso": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": st.st_size,
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R19R")
    print("Corrected Historical Divergence Boundary / Self-Artifact Exclusion Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO PRECISION ENVELOPE WILL BE CHANGED OR RELAXED.
NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
R19'S SELF-REFERENTIAL BOUNDARY WILL NOT BE ACCEPTED AS HISTORICAL PROVENANCE.
ONLY THE SELF-ARTIFACT EXCLUSION POLICY WILL BE REPAIRED.
""")

    r18 = load_json(R18_SUMMARY)
    r19 = load_json(R19_SUMMARY)

    if r18.get("classification") != "BOTH_RUNTIME_IDENTITIES_PERSIST_HISTORICALLY":
        raise RuntimeError("R19R requires the R18 dual-identity classification.")

    if r19.get("status") != "FIRST_CREATOR_TO_FROZEN_DIVERGENCE_CHAIN_RESOLVED":
        raise RuntimeError("R19R expects the R19 self-referential resolved result.")

    rows = load_csv(R18_ARTIFACTS)

    filter_rows = []
    historical_rows = []

    for row in rows:
        artifact = row.get("artifact", "")
        creator = normalize_bool(row.get("exact_creator100", False))
        frozen = normalize_bool(row.get("exact_frozen100", False))

        if not (creator or frozen):
            continue

        excluded = is_self_audit_artifact(artifact)

        filter_rows.append({
            "artifact": artifact,
            "key": row.get("key", ""),
            "exact_creator100": creator,
            "exact_frozen100": frozen,
            "self_audit_excluded": excluded,
            "exclusion_reason": (
                "CURRENT_R26I_REPLAY_PRECISION_AUDIT_PRODUCT"
                if excluded else ""
            ),
        })

        if not excluded:
            historical_rows.append(row)

    save_csv(FILTER_TABLE, filter_rows)

    creator_rows = [
        r for r in historical_rows
        if normalize_bool(r.get("exact_creator100", False))
    ]
    frozen_rows = [
        r for r in historical_rows
        if normalize_bool(r.get("exact_frozen100", False))
    ]

    id_rows = []
    for role, selected in (
        ("CREATOR100", creator_rows),
        ("FROZEN100", frozen_rows),
    ):
        for row in selected:
            stat = stat_row(row["artifact"])
            id_rows.append({
                "identity_role": role,
                "artifact": row["artifact"],
                "key": row.get("key", ""),
                "array_sha256_float32": row.get("sha256_float32", ""),
                **stat,
            })

    save_csv(IDENTITY_TABLE, id_rows)

    chron_rows = sorted(
        id_rows,
        key=lambda r: float(r["mtime_epoch"])
        if r["mtime_epoch"] != "" else float("inf"),
    )
    save_csv(CHRON_TABLE, chron_rows)

    creators_with_time = [
        r for r in chron_rows
        if r["identity_role"] == "CREATOR100" and r["mtime_epoch"] != ""
    ]
    frozens_with_time = [
        r for r in chron_rows
        if r["identity_role"] == "FROZEN100" and r["mtime_epoch"] != ""
    ]

    last_creator = (
        max(creators_with_time, key=lambda r: float(r["mtime_epoch"]))
        if creators_with_time else None
    )

    first_frozen_after = None
    frozen_after = []

    if last_creator:
        lc_t = float(last_creator["mtime_epoch"])
        frozen_after = [
            r for r in frozens_with_time
            if float(r["mtime_epoch"]) >= lc_t
        ]
        if frozen_after:
            first_frozen_after = min(
                frozen_after,
                key=lambda r: float(r["mtime_epoch"]),
            )

    # Also retain earliest frozen overall for context if no "after" boundary
    # exists. Do NOT call this a transition by chronology alone.
    earliest_frozen = (
        min(frozens_with_time, key=lambda r: float(r["mtime_epoch"]))
        if frozens_with_time else None
    )

    same_artifact_boundary = bool(
        last_creator
        and first_frozen_after
        and last_creator["artifact"] == first_frozen_after["artifact"]
    )

    boundary_rows = [{
        "historical_creator_count": len(creator_rows),
        "historical_frozen_count": len(frozen_rows),
        "last_creator_artifact": last_creator["artifact"] if last_creator else "",
        "last_creator_key": last_creator["key"] if last_creator else "",
        "last_creator_mtime_iso": last_creator["mtime_iso"] if last_creator else "",
        "first_frozen_after_creator_artifact": (
            first_frozen_after["artifact"] if first_frozen_after else ""
        ),
        "first_frozen_after_creator_key": (
            first_frozen_after["key"] if first_frozen_after else ""
        ),
        "first_frozen_after_creator_mtime_iso": (
            first_frozen_after["mtime_iso"] if first_frozen_after else ""
        ),
        "earliest_frozen_artifact": earliest_frozen["artifact"] if earliest_frozen else "",
        "earliest_frozen_key": earliest_frozen["key"] if earliest_frozen else "",
        "same_artifact_boundary": same_artifact_boundary,
        "frozen_candidates_after_last_creator": len(frozen_after),
    }]
    save_csv(BOUNDARY_TABLE, boundary_rows)

    # Correct interpretation:
    # The audit is successful if self-artifacts were excluded and we have
    # retained at least one historical identity on both sides. But a direct
    # transition is NOT declared unless a later source-lineage audit establishes
    # the edge independently of derivative audit files.
    r19_bad_boundary_detected = any(
        "V15_SG7E1R26IR17" in r.get("artifact", "").replace("\\", "/")
        and normalize_bool(r.get("self_audit_excluded", False))
        for r in filter_rows
    )

    gates = [
        ("R18_dual_identity_result_retained", True),
        ("R19_self_referential_boundary_detected", r19_bad_boundary_detected),
        ("current_R26I_audit_products_excluded", all(
            not is_self_audit_artifact(r["artifact"]) for r in historical_rows
        )),
        ("historical_creator_identity_remains", len(creator_rows) > 0),
        ("historical_frozen_identity_remains", len(frozen_rows) > 0),
        ("chronology_recomputed_after_exclusion", True),
        ("no_transition_declared_from_same_derivative_audit_artifact", not same_artifact_boundary),
        ("chronology_supporting_only", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_precision_relaxation", True),
        ("no_authority_reopened", True),
        ("no_later_time_state_generated", True),
    ]

    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    if len(creator_rows) > 0 and len(frozen_rows) > 0:
        status = "R19_SELF_REFERENTIAL_BOUNDARY_REJECTED_CORRECTED_HISTORICAL_IDENTITIES_RETAINED"
        diagnosis = (
            "R19_FALSE_BOUNDARY_WAS_DERIVATIVE_R17_AUDIT_ARTIFACT_BUT_BOTH_IDENTITIES_EXIST_IN_PRE_R16_HISTORY"
        )
        recommendation = (
            "Reject the original R19 resolved edge. Use only the corrected pre-R16 historical "
            "creator/frozen artifacts from R19R and audit their actual source creation/consumer "
            "lineage. Do not use filesystem chronology as sole transition authority."
        )
        next_ms = (
            "V15-SG7E1R26I-R20 — Corrected Historical Creator/Frozen Source-Lineage Boundary Audit"
        )
    else:
        status = "R19_SELF_REFERENTIAL_BOUNDARY_REJECTED_HISTORICAL_DUAL_IDENTITY_NOT_RETAINED"
        diagnosis = (
            "AFTER_EXCLUDING_CURRENT_AUDIT_PRODUCTS_ONE_OR_BOTH_HISTORICAL_IDENTITIES_DISAPPEAR"
        )
        recommendation = (
            "Do not proceed to a transition audit. Revisit R18's definition of historical matches "
            "with the corrected exclusion policy."
        )
        next_ms = (
            "V15-SG7E1R26I-R18R — Corrected Historical Identity Inventory"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "historical_creator_count": len(creator_rows),
        "historical_frozen_count": len(frozen_rows),
        "r19_bad_boundary_detected": r19_bad_boundary_detected,
        "same_artifact_boundary_after_repair": same_artifact_boundary,
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R19R",
        "status": status,
        "diagnosis": diagnosis,
        "r19_original_status_rejected": True,
        "r19_rejection_reason": (
            "R19 selected the derivative V15_SG7E1R26IR17 precision-audit NPZ "
            "as both last creator and first frozen artifact."
        ),
        "excluded_tokens": list(SELF_AUDIT_TOKENS),
        "historical_creator_count": len(creator_rows),
        "historical_frozen_count": len(frozen_rows),
        "last_creator": last_creator,
        "first_frozen_after_creator": first_frozen_after,
        "earliest_frozen": earliest_frozen,
        "failed_gates": failed,
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
        "milestone": "V15-SG7E1R26I-R19R",
        "status": status,
        "diagnosis": diagnosis,
        "historical_creator_count": len(creator_rows),
        "historical_frozen_count": len(frozen_rows),
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("R19 SELF-REFERENCE CHECK")
    print(f"  Bad R17 boundary found  : {r19_bad_boundary_detected}")
    print("  Original R19 edge valid : False")

    print("\nCORRECTED HISTORICAL IDENTITY COUNTS")
    print(f"  Creator100 exact        : {len(creator_rows)}")
    print(f"  Frozen100 exact         : {len(frozen_rows)}")

    print("\nCORRECTED CHRONOLOGY")
    if last_creator:
        print(f"  Last creator artifact   : {last_creator['artifact']}")
        print(f"  Last creator key        : {last_creator['key']}")
        print(f"  Creator mtime           : {last_creator['mtime_iso']}")
    else:
        print("  Last creator artifact   : NONE")

    if first_frozen_after:
        print(f"  First frozen after      : {first_frozen_after['artifact']}")
        print(f"  First frozen key        : {first_frozen_after['key']}")
        print(f"  Frozen mtime            : {first_frozen_after['mtime_iso']}")
    else:
        print("  First frozen after      : NONE")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19R FINAL GATES")
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
        FILTER_TABLE,
        IDENTITY_TABLE,
        CHRON_TABLE,
        BOUNDARY_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19R CORRECTED HISTORICAL BOUNDARY AUDIT: COMPLETE")
    print()
    print("The original R19 self-referential boundary is rejected.")
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("The precision envelope was not relaxed.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
