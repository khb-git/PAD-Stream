from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from datetime import datetime, timezone

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R20
# Corrected Persisted Later-Time L2 State Recovery Audit
#
# FORENSIC-ONLY MULTI-TIME STATE RECOVERY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO GAMMA / GUARD RECALIBRATION.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO INTERPOLATION / EXTRAPOLATION.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO PRECISION ENVELOPE WILL BE RELAXED.
# NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
#
# PURPOSE
# -------
# R19E formally closed the runtime-reproduction branch:
#
#   - exact historical runtime replay is NOT certified,
#   - current-runtime later-time generation is PROHIBITED,
#   - persisted later-time state recovery is AUTHORIZED.
#
# R20 therefore performs one corrected, forensic pre-audit inventory for
# genuinely persisted L2 deployment states at:
#
#   250 d
#   500 d
#   1000 d
#
# It:
#
#   1. excludes all R26I diagnostic/runtime-variance products from authority,
#   2. searches historical SG7B / SG7CR3 / SG7D / SG7E artifacts only,
#   3. inventories state-like arrays with 2662x201 shape,
#   4. extracts time labels from keys, sibling arrays, manifests, and filenames,
#   5. recognizes aliases only from persisted provenance,
#   6. deduplicates by numerical hash,
#   7. classifies each required time as:
#        UNIQUE_AUTHORITATIVE_CANDIDATE
#        MULTIPLE_AMBIGUOUS_CANDIDATES
#        NO_PERSISTED_STATE
#
# No state is fabricated or regenerated.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR20"
OUT.mkdir(parents=True, exist_ok=True)

R19E_DIR = ROOT / "output" / "V15_SG7E1R26IR19E"
R19E_SUMMARY = R19E_DIR / "PAD_Stream_V15SG7E1R26IR19E_Summary.json"

R23_DIR = ROOT / "output" / "V15_SG7E1R23"
R23_SUMMARY = R23_DIR / "PAD_Stream_V15SG7E1R23_Summary.json"

REQUIRED_TIMES = [250.0, 500.0, 1000.0]

# Output tables
SCOPE_TABLE = OUT / "V15SG7E1R26IR20_Historical_Search_Scope.csv"
ARRAY_TABLE = OUT / "V15SG7E1R26IR20_Persisted_L2_Array_Inventory.csv"
TIME_TRACE_TABLE = OUT / "V15SG7E1R26IR20_Time_Label_Provenance.csv"
ALIAS_TABLE = OUT / "V15SG7E1R26IR20_State_Alias_Provenance.csv"
HASH_TABLE = OUT / "V15SG7E1R26IR20_State_Hash_Deduplication.csv"
COVERAGE_TABLE = OUT / "V15SG7E1R26IR20_Required_Time_State_Coverage.csv"
CANDIDATE_TABLE = OUT / "V15SG7E1R26IR20_Required_Time_Candidate_Binding.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR20_Final_Recovery_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR20_Later_Time_Recovery_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR20_Persisted_Later_Time_L2_Recovery_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR20_Summary.json"


# Exclude derivative audit/runtime products from the current forensic authority.
EXCLUDE_TOKENS = (
    "V15_SG7E1R26IR16",
    "V15_SG7E1R26IR17",
    "V15_SG7E1R26IR18",
    "V15_SG7E1R26IR18R",
    "V15_SG7E1R26IR19",
    "V15_SG7E1R26IR19R",
    "V15_SG7E1R26IR19A",
    "V15_SG7E1R26IR19B",
    "V15_SG7E1R26IR19C",
    "V15_SG7E1R26IR19D",
    "V15_SG7E1R26IR19E",
    "V15_SG7E1R26IR20",
    "V15SG7E1R26IR16",
    "V15SG7E1R26IR17",
    "V15SG7E1R26IR18",
    "V15SG7E1R26IR18R",
    "V15SG7E1R26IR19",
    "V15SG7E1R26IR19R",
    "V15SG7E1R26IR19A",
    "V15SG7E1R26IR19B",
    "V15SG7E1R26IR19C",
    "V15SG7E1R26IR19D",
    "V15SG7E1R26IR19E",
    "V15SG7E1R26IR20",
)


STATE_KEY_HINTS = (
    "l2",
    "state",
    "prediction",
    "pred",
    "frozen",
    "candidate",
    "deployment",
    "profile",
    "saturation",
    "sat",
)


AUXILIARY_KEY_HINTS = (
    "truth",
    "guard",
    "mask",
    "gamma",
    "coeff",
    "weight",
    "xi",
    "tau",
    "tof",
    "front",
    "error",
    "residual",
    "target",
    "metric",
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
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def is_excluded(path: Path):
    s = str(path).replace("\\", "/")
    return any(tok in s for tok in EXCLUDE_TOKENS)


def historical_npz_files():
    out_root = ROOT / "output"
    files = []
    if not out_root.exists():
        return files

    for p in out_root.rglob("*.npz"):
        if not p.is_file():
            continue
        if is_excluded(p):
            continue

        s = str(p)
        if any(tok in s for tok in ("V15_SG7B", "V15_SG7CR3", "V15_SG7D", "V15_SG7E")):
            files.append(p)

    return sorted(set(files))


def relevant_metadata_files(npz_files):
    parents = {p.parent for p in npz_files}
    files = set()

    for parent in parents:
        for pattern in ("*.json", "*.csv", "*.txt"):
            files.update(parent.glob(pattern))

    # Also allow nearby source Python files with related milestone stems.
    for p in ROOT.glob("PAD_Stream_V15SG7*.py"):
        if not is_excluded(p):
            files.add(p)

    return sorted(p for p in files if p.exists() and p.is_file())


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def state_like_key(key: str):
    low = key.lower()

    if any(tok in low for tok in AUXILIARY_KEY_HINTS):
        # Permit explicit state names such as "L2_independent_250" even if some
        # token overlap exists elsewhere.
        if not any(tok in low for tok in ("l2", "state", "frozen", "candidate", "prediction", "deployment")):
            return False

    return any(tok in low for tok in STATE_KEY_HINTS)


def extract_time_from_text(text: str):
    hits = set()

    patterns = [
        r"(?<!\d)(1000|500|250)\s*(?:d|day|days)\b",
        r"(?:time|t|td|tD)[_\-\s:=]*?(1000|500|250)(?:\.0+)?\b",
        r"(?<!\d)(1000|500|250)(?:\.0+)?(?=[_\-\s\]\),}]|$)",
    ]

    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            try:
                hits.add(float(m.group(1)))
            except Exception:
                pass

    return sorted(hits)


def extract_time_from_key(key: str):
    low = key.lower()
    hits = set()

    for t in REQUIRED_TIMES:
        ti = int(t)
        pats = [
            rf"(^|[_\-]){ti}($|[_\-])",
            rf"{ti}d\b",
            rf"day{ti}\b",
            rf"{ti}day\b",
        ]
        if any(re.search(pat, low) for pat in pats):
            hits.add(t)

    return sorted(hits)


def sibling_time_arrays(npz):
    candidates = {}
    for key in npz.files:
        low = key.lower()
        if any(tok in low for tok in ("time", "times", "days", "t_days", "times_days")):
            try:
                arr = np.asarray(npz[key]).reshape(-1)
            except Exception:
                continue
            if arr.size <= 100 and np.issubdtype(arr.dtype, np.number):
                vals = [float(v) for v in arr if np.isfinite(v)]
                candidates[key] = vals
    return candidates


def stat_info(path: Path):
    st = path.stat()
    return {
        "mtime_iso": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": st.st_size,
    }


def metadata_time_hits(files):
    rows = []

    for path in files:
        text = safe_text(path)
        times = extract_time_from_text(text)
        if not times:
            continue

        for t in times:
            for i, line in enumerate(text.splitlines(), start=1):
                if str(int(t)) in line:
                    rows.append({
                        "source": str(path),
                        "line": i,
                        "time_days": t,
                        "text": line.strip()[:1400],
                    })
    return rows


def alias_hits(files, array_keys):
    rows = []

    normalized_keys = sorted(set(k for k in array_keys if k))
    if not normalized_keys:
        return rows

    for path in files:
        text = safe_text(path)
        if not text:
            continue

        lines = text.splitlines()
        for key in normalized_keys:
            if key not in text:
                continue
            for i, line in enumerate(lines, start=1):
                if key in line:
                    rows.append({
                        "source": str(path),
                        "line": i,
                        "key": key,
                        "text": line.strip()[:1400],
                    })

    return rows


def score_candidate(row, meta_time_rows, alias_rows):
    score = 0
    reasons = []

    key = row["key"]
    artifact = row["artifact"]
    time_days = float(row["time_days"])

    # Explicit time in key is strongest local evidence.
    key_times = extract_time_from_key(key)
    if time_days in key_times:
        score += 500
        reasons.append("explicit_time_in_key")

    # Explicit time in artifact name.
    file_times = extract_time_from_text(Path(artifact).name)
    if time_days in file_times:
        score += 250
        reasons.append("explicit_time_in_filename")

    # State-semantic naming.
    low = key.lower()
    if "l2" in low:
        score += 220
        reasons.append("L2_key_semantics")
    if "independent" in low:
        score += 120
        reasons.append("independent_validation_semantics")
    if "frozen" in low:
        score += 100
        reasons.append("frozen_state_semantics")
    if "candidate" in low:
        score += 80
        reasons.append("candidate_state_semantics")
    if "deployment" in low:
        score += 70
        reasons.append("deployment_state_semantics")

    # Parent milestone lineage.
    if "R1F" in artifact:
        score += 120
        reasons.append("R1F_lineage")
    if "CR3" in artifact:
        score += 100
        reasons.append("CR3_lineage")
    if "SG7B" in artifact:
        score += 50
        reasons.append("SG7B_lineage")

    # Metadata references in same parent directory.
    parent = str(Path(artifact).parent)
    meta_support = sum(
        1 for r in meta_time_rows
        if r["source"].startswith(parent) and float(r["time_days"]) == time_days
    )
    if meta_support:
        score += min(200, 40 * meta_support)
        reasons.append(f"parent_metadata_time_hits={meta_support}")

    alias_support = sum(
        1 for r in alias_rows
        if r["key"] == key and r["source"].startswith(parent)
    )
    if alias_support:
        score += min(160, 40 * alias_support)
        reasons.append(f"parent_alias_hits={alias_support}")

    return score, reasons


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R20")
    print("Corrected Persisted Later-Time L2 State Recovery Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO INTERPOLATION OR EXTRAPOLATION WILL BE USED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO PRECISION ENVELOPE WILL BE CHANGED OR RELAXED.
ONLY GENUINELY PERSISTED PRE-AUDIT L2 STATES MAY RESTORE MULTI-TIME COVERAGE.
""")

    r19e = load_json(R19E_SUMMARY)
    if r19e.get("status") != "HISTORICAL_RUNTIME_REPRODUCIBILITY_LIMITATION_FORMALIZED":
        raise RuntimeError("R20 requires the completed R19E authority-decision milestone.")

    r23 = load_json(R23_SUMMARY)
    if r23.get("status") != "L2_100D_NOMINATED_DEPLOYMENT_STATE_BOUND":
        raise RuntimeError("R20 requires R23 authoritative L2 100-day state binding.")

    npz_files = historical_npz_files()
    meta_files = relevant_metadata_files(npz_files)

    save_csv(SCOPE_TABLE, [
        {
            "artifact": str(p),
            "excluded": False,
            "scope_reason": "PRE_R26I_HISTORICAL_SG7B_CR3_SG7D_SG7E_ARTIFACT",
        }
        for p in npz_files
    ])

    # -------------------------------------------------------------------------
    # Array inventory
    # -------------------------------------------------------------------------
    array_rows = []
    raw_candidates = []

    for path in npz_files:
        try:
            db = np.load(path, allow_pickle=True)
        except Exception:
            continue

        try:
            time_arrays = sibling_time_arrays(db)

            for key in db.files:
                try:
                    arr = np.asarray(db[key])
                except Exception:
                    continue

                if arr.shape != (2662, 201):
                    continue
                if not np.issubdtype(arr.dtype, np.number):
                    continue
                if not np.all(np.isfinite(arr)):
                    continue
                if not state_like_key(key):
                    continue

                arr32 = np.asarray(arr, dtype=np.float32)
                arr_hash = sha256_array(arr32)

                key_times = extract_time_from_key(key)
                file_times = extract_time_from_text(path.name)

                inferred_times = set(key_times) | set(file_times)

                # If there is exactly one sibling time array and the artifact has
                # only one 2662x201 state-like array, its local time cannot be
                # inferred solely from position; retain sibling arrays as evidence
                # but do not assign by assumption.
                stat = stat_info(path)

                array_rows.append({
                    "artifact": str(path),
                    "key": key,
                    "shape": str(arr.shape),
                    "dtype": str(arr.dtype),
                    "sha256_float32": arr_hash,
                    "min": float(np.min(arr32)),
                    "max": float(np.max(arr32)),
                    "mean": float(np.mean(arr32)),
                    "key_time_candidates": ";".join(str(int(t)) for t in key_times),
                    "filename_time_candidates": ";".join(str(int(t)) for t in file_times),
                    "sibling_time_arrays": json.dumps(time_arrays),
                    "mtime_iso": stat["mtime_iso"],
                    "size_bytes": stat["size_bytes"],
                })

                raw_candidates.append({
                    "artifact": str(path),
                    "key": key,
                    "sha256_float32": arr_hash,
                    "key_times": key_times,
                    "file_times": file_times,
                    "sibling_time_arrays": time_arrays,
                })
        finally:
            db.close()

    save_csv(ARRAY_TABLE, array_rows)

    # -------------------------------------------------------------------------
    # Metadata and alias provenance
    # -------------------------------------------------------------------------
    time_rows = metadata_time_hits(meta_files)
    save_csv(TIME_TRACE_TABLE, time_rows)

    alias_rows = alias_hits(meta_files, [r["key"] for r in raw_candidates])
    save_csv(ALIAS_TABLE, alias_rows)

    # -------------------------------------------------------------------------
    # Build time-specific candidates only when explicit time evidence exists.
    # -------------------------------------------------------------------------
    time_candidates = []

    for c in raw_candidates:
        explicit_times = sorted(set(c["key_times"]) | set(c["file_times"]))

        # Metadata support can add a time ONLY if same parent and key is directly
        # referenced in that metadata/source line.
        parent = str(Path(c["artifact"]).parent)

        for t in REQUIRED_TIMES:
            supporting = []

            if t in explicit_times:
                supporting.append("local_explicit_time")

            # Look for alias/source lines mentioning both the key and required time.
            for r in alias_rows:
                if r["key"] != c["key"]:
                    continue
                if not r["source"].startswith(parent):
                    continue
                if str(int(t)) in r["text"]:
                    supporting.append(f"alias_source:{Path(r['source']).name}:{r['line']}")

            if not supporting:
                continue

            row = {
                "artifact": c["artifact"],
                "key": c["key"],
                "time_days": t,
                "sha256_float32": c["sha256_float32"],
                "supporting_evidence": ";".join(supporting),
            }
            score, reasons = score_candidate(row, time_rows, alias_rows)
            row["provenance_score"] = score
            row["provenance_reasons"] = ";".join(reasons)
            time_candidates.append(row)

    # Deduplicate same artifact/key/time
    dedup = {}
    for r in time_candidates:
        k = (r["artifact"], r["key"], float(r["time_days"]))
        old = dedup.get(k)
        if old is None or int(r["provenance_score"]) > int(old["provenance_score"]):
            dedup[k] = r
    time_candidates = list(dedup.values())

    # -------------------------------------------------------------------------
    # Hash deduplication per time
    # -------------------------------------------------------------------------
    hash_rows = []
    candidate_rows = []

    for t in REQUIRED_TIMES:
        rows_t = [r for r in time_candidates if float(r["time_days"]) == t]
        by_hash = {}

        for r in rows_t:
            by_hash.setdefault(r["sha256_float32"], []).append(r)

        for h, members in by_hash.items():
            top = max(members, key=lambda x: int(x["provenance_score"]))
            hash_rows.append({
                "time_days": t,
                "sha256_float32": h,
                "artifact_instance_count": len(members),
                "top_provenance_score": top["provenance_score"],
                "top_artifact": top["artifact"],
                "top_key": top["key"],
            })

            candidate_rows.append({
                "time_days": t,
                "sha256_float32": h,
                "artifact_instance_count": len(members),
                "top_provenance_score": top["provenance_score"],
                "top_artifact": top["artifact"],
                "top_key": top["key"],
                "top_reasons": top["provenance_reasons"],
            })

    save_csv(HASH_TABLE, hash_rows)

    # -------------------------------------------------------------------------
    # Coverage / binding decision
    # -------------------------------------------------------------------------
    coverage_rows = []
    selected_rows = []

    for t in REQUIRED_TIMES:
        hashes_t = [r for r in candidate_rows if float(r["time_days"]) == t]
        hashes_t.sort(key=lambda r: int(r["top_provenance_score"]), reverse=True)

        if len(hashes_t) == 0:
            classification = "NO_PERSISTED_STATE"
            unique = False
            selected = None
            margin = None

        elif len(hashes_t) == 1:
            classification = "UNIQUE_PERSISTED_HASH"
            unique = True
            selected = hashes_t[0]
            margin = None

        else:
            top = hashes_t[0]
            second = hashes_t[1]
            margin = int(top["top_provenance_score"]) - int(second["top_provenance_score"])

            # Strong provenance margin required; no performance criterion used.
            if margin >= 200:
                classification = "UNIQUE_AUTHORITATIVE_CANDIDATE_BY_PROVENANCE"
                unique = True
                selected = top
            else:
                classification = "MULTIPLE_AMBIGUOUS_CANDIDATES"
                unique = False
                selected = None

        coverage_rows.append({
            "time_days": t,
            "candidate_hash_count": len(hashes_t),
            "classification": classification,
            "unique_authoritative_candidate": unique,
            "selected_sha256": selected["sha256_float32"] if selected else "",
            "selected_artifact": selected["top_artifact"] if selected else "",
            "selected_key": selected["top_key"] if selected else "",
            "provenance_margin": margin if margin is not None else "",
        })

        if selected:
            selected_rows.append({
                "time_days": t,
                **selected,
                "selection_basis": classification,
            })

    save_csv(COVERAGE_TABLE, coverage_rows)
    save_csv(CANDIDATE_TABLE, selected_rows)

    all_unique = all(bool(r["unique_authoritative_candidate"]) for r in coverage_rows)
    any_missing = any(r["classification"] == "NO_PERSISTED_STATE" for r in coverage_rows)
    any_ambiguous = any(r["classification"] == "MULTIPLE_AMBIGUOUS_CANDIDATES" for r in coverage_rows)

    if all_unique:
        status = "PERSISTED_LATER_TIME_L2_STATE_COVERAGE_RECOVERED"
        diagnosis = (
            "ALL_REQUIRED_250_500_1000_DAY_L2_STATES_HAVE_UNIQUE_PERSISTED_PRE_AUDIT_PROVENANCE"
        )
        recommendation = (
            "Preserve the recovered hashes and source artifacts as immutable multi-time deployment "
            "authority. Proceed to replay only the historical SG7D map-back from these persisted "
            "L2 states; do not regenerate states with the current runtime."
        )
        next_ms = (
            "V15-SG7E1R26I-R21 — Persisted Multi-Time L2-to-Grid Map-Back Replay Audit"
        )

    elif any_ambiguous:
        status = "PERSISTED_LATER_TIME_L2_STATE_AUTHORITY_AMBIGUOUS"
        diagnosis = (
            "ONE_OR_MORE_REQUIRED_TIMES_HAVE_MULTIPLE_DISTINCT_PERSISTED_L2_HASHES_WITHOUT_SUFFICIENT_PROVENANCE_MARGIN"
        )
        recommendation = (
            "Do not select by numerical similarity or downstream performance. Audit only the "
            "ambiguous required-time candidate lineages using parent manifests, freeze-readiness "
            "records, and explicit consumer paths."
        )
        next_ms = (
            "V15-SG7E1R26I-R21 — Later-Time L2 Candidate Lineage Conflict Audit"
        )

    else:
        status = "PERSISTED_LATER_TIME_L2_STATE_COVERAGE_NOT_RECOVERABLE"
        diagnosis = (
            "ONE_OR_MORE_REQUIRED_250_500_1000_DAY_STATES_HAVE_NO_GENUINELY_PERSISTED_PRE_AUDIT_L2_STATE"
        )
        recommendation = (
            "Do not fabricate or runtime-regenerate missing states. Record the multi-time deployment "
            "coverage limitation formally and determine whether SG7E can proceed only as a historical "
            "reference-validation contract rather than a fully reproducible multi-time deployment contract."
        )
        next_ms = (
            "V15-SG7E1R26I-R21 — Multi-Time Deployment Coverage Limitation / SG7E Scope Decision Audit"
        )

    gates = [
        ("R19E_runtime_limitation_status_reproduced", True),
        ("R23_100d_L2_authority_retained", True),
        ("pre_audit_NPZ_scope_constructed", len(npz_files) > 0),
        ("R26I_derivative_artifacts_excluded", all(not is_excluded(p) for p in npz_files)),
        ("2662x201_state_like_arrays_inventoried", len(array_rows) > 0),
        ("time_label_provenance_audited", True),
        ("alias_provenance_audited", True),
        ("state_hashes_deduplicated", True),
        ("required_250_500_1000_coverage_classified", len(coverage_rows) == 3),
        ("no_candidate_selected_by_numerical_performance", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_interpolation_or_extrapolation", True),
        ("no_precision_relaxation", True),
        ("no_authority_reopened", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "all_required_times_unique": all_unique,
        "any_missing_time": any_missing,
        "any_ambiguous_time": any_ambiguous,
        "selected_time_count": len(selected_rows),
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R20",
        "status": status,
        "diagnosis": diagnosis,
        "required_times_days": REQUIRED_TIMES,
        "coverage": coverage_rows,
        "selected_candidates": selected_rows,
        "exclusion_tokens": list(EXCLUDE_TOKENS),
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "model_parameters_changed": False,
            "later_time_runtime_generation_allowed": False,
            "interpolation_allowed": False,
            "extrapolation_allowed": False,
            "precision_envelope_relaxed": False,
            "candidate_performance_used": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R20",
        "status": status,
        "diagnosis": diagnosis,
        "coverage": coverage_rows,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("HISTORICAL SEARCH SCOPE")
    print(f"  NPZ artifacts           : {len(npz_files)}")
    print(f"  Metadata/source files   : {len(meta_files)}")

    print("\nSTATE-LIKE ARRAY INVENTORY")
    print(f"  2662x201 arrays         : {len(array_rows)}")
    print(f"  Time-bound candidates   : {len(time_candidates)}")
    print(f"  Distinct time/hash rows : {len(hash_rows)}")

    print("\nREQUIRED-TIME COVERAGE")
    for r in coverage_rows:
        print(
            f"  t={float(r['time_days']):7.1f} d | "
            f"hashes={int(r['candidate_hash_count']):2d} | "
            f"{r['classification']}"
        )

    if selected_rows:
        print("\nSELECTED PERSISTED CANDIDATES")
        for r in selected_rows:
            print(
                f"  t={float(r['time_days']):7.1f} d | "
                f"{r['top_key']} | {r['sha256_float32'][:16]} | "
                f"score={r['top_provenance_score']}"
            )

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R20 FINAL RECOVERY GATES")
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
        SCOPE_TABLE,
        ARRAY_TABLE,
        TIME_TRACE_TABLE,
        ALIAS_TABLE,
        HASH_TABLE,
        COVERAGE_TABLE,
        CANDIDATE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R20 CORRECTED PERSISTED LATER-TIME L2 STATE RECOVERY AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No state was interpolated or extrapolated.")
    print("No later-time state was generated.")
    print("The precision envelope was not relaxed.")
    print("=" * 78)


if __name__ == "__main__":
    main()
