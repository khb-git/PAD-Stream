from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import re
from collections import defaultdict, Counter

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R0
# Historical SG7E Reference Plume Provenance Audit
#
# FORENSIC REFERENCE-CONTRACT MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
#
# PURPOSE
# -------
# SG7E1 blocked safely because:
#
#   Reference status        : AMBIGUOUS_REFERENCE_CANDIDATES
#   Plume threshold resolved: False
#
# while the authoritative SG7E gate registry itself was already resolved.
#
# SG7E1R0 therefore audits ONLY:
#
#   1. historical plume/reference array provenance,
#   2. historical plume-threshold provenance,
#   3. source/manifest/summary linkage,
#   4. duplicate vs distinct reference arrays,
#   5. shape/range/hash identity,
#   6. whether a unique reference + threshold pair can be recovered.
#
# SG7E1R0 does NOT evaluate deployment gates.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R0"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7E1_DIR = ROOT / "output" / "V15_SG7E1"
SG7E0_DIR = ROOT / "output" / "V15_SG7E0"
SG7E0R_DIR = ROOT / "output" / "V15_SG7E0R"

SG7E1_SUMMARY = SG7E1_DIR / "PAD_Stream_V15SG7E1_Summary.json"
SG7E1_REFERENCE_DISCOVERY = SG7E1_DIR / "V15SG7E1_Reference_Plume_Discovery.csv"
SG7E1_REFERENCE_IDENTITY = SG7E1_DIR / "V15SG7E1_Reference_Plume_Identity.csv"

SG7E0_SOURCE_DISCOVERY = (
    SG7E0_DIR / "V15SG7E0_Historical_SG7E_Source_Discovery.csv"
)

SG7E0R_CONTRACT = (
    SG7E0R_DIR / "V15SG7E0R_Reconciled_SG7E_Gate_Authority_Contract.json"
)

SG7D6_FREEZE_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R0_Summary.json"

REFERENCE_CANDIDATE_TABLE = OUT / "V15SG7E1R0_Reference_Candidate_Audit.csv"
REFERENCE_HASH_TABLE = OUT / "V15SG7E1R0_Reference_Array_Hash_Groups.csv"
REFERENCE_USAGE_TABLE = OUT / "V15SG7E1R0_Reference_Usage_Provenance.csv"
THRESHOLD_EVIDENCE_TABLE = OUT / "V15SG7E1R0_Plume_Threshold_Evidence.csv"
THRESHOLD_CONFLICT_TABLE = OUT / "V15SG7E1R0_Plume_Threshold_Conflict_Audit.csv"
PAIR_TABLE = OUT / "V15SG7E1R0_Reference_Threshold_Pair_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R0_Reference_Contract_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"

EXPECTED_SHAPE = (15, 50, 50)

# =============================================================================
# Evidence vocabulary
# =============================================================================

REFERENCE_POSITIVE_TOKENS = (
    "truth",
    "reference",
    "canonical",
    "physics",
    "benchmark",
    "target",
    "ground_truth",
    "groundtruth",
)

REFERENCE_NEGATIVE_TOKENS = (
    "pred",
    "prediction",
    "candidate",
    "mapped",
    "full_grid",
    "p4",
    "deployment",
)

THRESHOLD_NAME_TOKENS = (
    "plume",
    "sat",
    "saturation",
    "threshold",
    "cutoff",
)

AUTHORITY_TOKENS = (
    "authoritative",
    "acceptance",
    "deployment",
    "final gate",
    "final_gate",
    "must pass",
    "must_pass",
    "reference plume",
    "reference_plume",
    "truth plume",
    "truth_plume",
)

DIAGNOSTIC_TOKENS = (
    "diagnostic only",
    "diagnostic_only",
    "report only",
    "report_only",
    "diagnostic",
)

LEGACY_TOKENS = (
    "legacy",
    "deprecated",
    "superseded",
    "historical only",
    "historical_only",
)


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
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


def sha256_file(path: Path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def milestone_rank(path: str):
    """
    Later SG7E milestones get a weak recency score.
    """
    name = Path(path).name.upper()
    m = re.search(r"SG7E(\d+)", name)
    if m:
        return int(m.group(1))
    if "SG7E" in name:
        return 0
    return -1


def score_reference_name(path: str, key: str):
    p = Path(path).name.lower()
    k = key.lower()

    score = 0
    reasons = []

    for tok in REFERENCE_POSITIVE_TOKENS:
        if tok in k:
            score += 6
            reasons.append(f"key:{tok}")
        if tok in p:
            score += 2
            reasons.append(f"file:{tok}")

    for tok in REFERENCE_NEGATIVE_TOKENS:
        if tok in k:
            score -= 5
            reasons.append(f"neg_key:{tok}")
        if tok in p:
            score -= 1
            reasons.append(f"neg_file:{tok}")

    return score, reasons


def score_text_authority(text):
    t = text.lower()
    score = 0
    reasons = []

    if any(tok in t for tok in AUTHORITY_TOKENS):
        score += 6
        reasons.append("authority_language")

    if any(tok in t for tok in DIAGNOSTIC_TOKENS):
        score -= 6
        reasons.append("diagnostic_language")

    if any(tok in t for tok in LEGACY_TOKENS):
        score -= 8
        reasons.append("legacy_language")

    return score, reasons


def parse_reference_candidates(source_rows):
    """
    Inventory all 15x50x50 arrays from historical SG7E NPZs.
    """

    candidates = []

    for row in source_rows:
        path = Path(row["path"])

        if path.suffix.lower() != ".npz" or not path.exists():
            continue

        try:
            db = np.load(path, allow_pickle=True)
        except Exception:
            continue

        text = ""

        # Search sibling source/summary/contract text near this numerical file.
        parent = path.parent
        for sibling in parent.iterdir():
            if (
                sibling.is_file()
                and sibling.suffix.lower() in {".py", ".json", ".txt", ".csv"}
            ):
                text += "\n" + safe_text(sibling)

        source_score, source_reasons = score_text_authority(text)

        for key in db.files:
            try:
                arr = np.asarray(db[key])
            except Exception:
                continue

            if arr.shape != EXPECTED_SHAPE:
                continue

            name_score, name_reasons = score_reference_name(
                str(path),
                key,
            )

            total_score = name_score + source_score

            if milestone_rank(str(path)) >= 1:
                total_score += min(milestone_rank(str(path)), 3)
                name_reasons.append(
                    f"later_generation:{milestone_rank(str(path))}"
                )

            finite = np.isfinite(arr)

            candidates.append({
                "path": str(path),
                "key": key,
                "file_sha256": sha256_file(path),
                "array_sha256": sha256_array(arr),
                "dtype": str(arr.dtype),
                "shape": str(arr.shape),
                "finite_fraction": float(np.mean(finite)),
                "min": float(np.nanmin(arr)) if np.any(finite) else np.nan,
                "max": float(np.nanmax(arr)) if np.any(finite) else np.nan,
                "mean": float(np.nanmean(arr)) if np.any(finite) else np.nan,
                "name_score": name_score,
                "source_score": source_score,
                "total_score": total_score,
                "reasons": ";".join(name_reasons + source_reasons),
            })

    candidates.sort(
        key=lambda r: (
            r["total_score"],
            r["finite_fraction"],
            milestone_rank(r["path"]),
        ),
        reverse=True,
    )

    return candidates


def search_reference_usage(candidates, source_rows):
    """
    Search historical textual sources for exact NPZ filename/key usage.
    """

    text_sources = []

    for row in source_rows:
        path = Path(row["path"])

        if path.suffix.lower() not in {".py", ".json", ".txt", ".csv"}:
            continue

        text = safe_text(path)

        if text:
            text_sources.append((path, text))

    rows = []

    for cand in candidates:
        file_name = Path(cand["path"]).name
        key = cand["key"]

        filename_hits = []
        key_hits = []

        for path, text in text_sources:
            lower = text.lower()

            if file_name.lower() in lower:
                filename_hits.append(str(path))

            if re.search(
                rf'(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])',
                text,
            ):
                key_hits.append(str(path))

        usage_score = (
            4 * len(set(filename_hits))
            +
            3 * len(set(key_hits))
        )

        rows.append({
            "reference_path": cand["path"],
            "reference_key": key,
            "filename_usage_hits": len(set(filename_hits)),
            "key_usage_hits": len(set(key_hits)),
            "usage_score": usage_score,
            "filename_usage_sources": ";".join(sorted(set(filename_hits))),
            "key_usage_sources": ";".join(sorted(set(key_hits))),
        })

    return rows


def extract_threshold_evidence(source_rows):
    """
    Extract candidate plume/saturation threshold definitions and usage.
    """

    rows = []

    assignment = re.compile(
        r'(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:threshold|cutoff)[A-Za-z0-9_]*)'
        r'\s*=\s*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)',
        re.IGNORECASE,
    )

    comparison = re.compile(
        r'(?P<lhs>[A-Za-z_][A-Za-z0-9_\[\]\.\(\)]*)'
        r'\s*(?P<op>>=|>|<=|<)\s*'
        r'(?P<rhs>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)'
    )

    for row in source_rows:
        path = Path(row["path"])

        if path.suffix.lower() not in {".py", ".json", ".txt", ".csv"}:
            continue

        text = safe_text(path)

        if not text:
            continue

        lines = text.splitlines()

        for line_no, line in enumerate(lines, start=1):
            lower = line.lower()

            for m in assignment.finditer(line):
                name = m.group("name")
                value = float(m.group("value"))

                token_hit = any(tok in name.lower() for tok in THRESHOLD_NAME_TOKENS)

                if not token_hit:
                    continue

                context = "\n".join(
                    lines[max(0, line_no - 6):min(len(lines), line_no + 5)]
                )

                score, reasons = score_text_authority(context)

                if "plume" in name.lower():
                    score += 5
                    reasons.append("plume_named_threshold")

                if "sat" in name.lower():
                    score += 3
                    reasons.append("saturation_named_threshold")

                rows.append({
                    "source": str(path),
                    "line": line_no,
                    "evidence_type": "assignment",
                    "symbol": name,
                    "operator": "=",
                    "value": value,
                    "score": score,
                    "reasons": ";".join(reasons),
                    "raw": line.strip()[:500],
                })

            # Also catch direct plume comparisons with literals.
            if (
                "plume" in lower
                or "sat" in lower
                or "saturation" in lower
            ):
                for m in comparison.finditer(line):
                    lhs = m.group("lhs")
                    value = float(m.group("rhs"))

                    # plausible saturation threshold range only
                    if not (0.0 <= value <= 1.0):
                        continue

                    context = "\n".join(
                        lines[max(0, line_no - 6):min(len(lines), line_no + 5)]
                    )

                    score, reasons = score_text_authority(context)

                    if "plume" in lower:
                        score += 4
                        reasons.append("plume_comparison")

                    rows.append({
                        "source": str(path),
                        "line": line_no,
                        "evidence_type": "comparison",
                        "symbol": lhs,
                        "operator": m.group("op"),
                        "value": value,
                        "score": score,
                        "reasons": ";".join(reasons),
                        "raw": line.strip()[:500],
                    })

    return rows


def reconcile_threshold(rows):
    if not rows:
        return None, "NO_THRESHOLD_EVIDENCE", []

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["value"]].append(row)

    ranked = []

    for value, items in grouped.items():
        best = max(
            items,
            key=lambda r: (
                r["score"],
                milestone_rank(r["source"]),
            ),
        )

        ranked.append({
            "value": value,
            "best_score": best["score"],
            "best_source": best["source"],
            "best_line": best["line"],
            "evidence_count": len(items),
            "best_reasons": best["reasons"],
        })

    ranked.sort(
        key=lambda r: (
            r["best_score"],
            r["evidence_count"],
            milestone_rank(r["best_source"]),
        ),
        reverse=True,
    )

    top = ranked[0]

    if top["best_score"] <= 0:
        return None, "NO_POSITIVE_THRESHOLD_AUTHORITY", ranked

    if len(ranked) == 1:
        return top["value"], "UNIQUE_THRESHOLD_VALUE", ranked

    second = ranked[1]

    score_margin = top["best_score"] - second["best_score"]

    if score_margin >= 4:
        return top["value"], "THRESHOLD_PROVENANCE_MARGIN", ranked

    return None, "AMBIGUOUS_THRESHOLD_VALUES", ranked


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R0")
    print("Historical SG7E Reference Plume Provenance Audit")
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
""")

    e1_summary = load_json(SG7E1_SUMMARY)
    e0r_contract = load_json(SG7E0R_CONTRACT)
    freeze_manifest = load_json(SG7D6_FREEZE_MANIFEST)

    if (
        e1_summary.get("status")
        != "SG7E1_REFERENCE_CONTRACT_BLOCKED"
    ):
        raise RuntimeError(
            "SG7E1R0 requires SG7E1 reference-contract blocked status."
        )

    if (
        e1_summary.get("diagnosis")
        != "HISTORICAL_REFERENCE_PLUME_OR_THRESHOLD_NOT_UNIQUELY_RECOVERED"
    ):
        raise RuntimeError(
            "SG7E1R0 requires SG7E1 reference-provenance diagnosis."
        )

    if (
        e0r_contract.get("status")
        != "SG7E_GATE_AUTHORITY_RECONCILED"
    ):
        raise RuntimeError(
            "SG7E1R0 requires reconciled SG7E gate authority."
        )

    if (
        freeze_manifest.get("status")
        != "SG7D_FULL_GRID_CANDIDATE_FROZEN"
    ):
        raise RuntimeError(
            "SG7E1R0 requires frozen SG7D6 input."
        )

    source_rows = load_csv(SG7E0_SOURCE_DISCOVERY)
    e1_candidates = load_csv(SG7E1_REFERENCE_DISCOVERY)

    # -------------------------------------------------------------------------
    # Rebuild reference candidate inventory with stronger provenance
    # -------------------------------------------------------------------------

    candidates = parse_reference_candidates(source_rows)
    usage_rows = search_reference_usage(candidates, source_rows)

    usage_lookup = {
        (r["reference_path"], r["reference_key"]): r
        for r in usage_rows
    }

    audited_candidates = []

    for cand in candidates:
        u = usage_lookup.get(
            (cand["path"], cand["key"]),
            {},
        )

        usage_score = int(u.get("usage_score", 0) or 0)

        total = cand["total_score"] + usage_score

        audited = dict(cand)
        audited["usage_score"] = usage_score
        audited["combined_score"] = total
        audited["filename_usage_hits"] = u.get("filename_usage_hits", 0)
        audited["key_usage_hits"] = u.get("key_usage_hits", 0)

        audited_candidates.append(audited)

    audited_candidates.sort(
        key=lambda r: (
            r["combined_score"],
            r["total_score"],
            r["finite_fraction"],
            milestone_rank(r["path"]),
        ),
        reverse=True,
    )

    save_csv(
        REFERENCE_CANDIDATE_TABLE,
        audited_candidates,
    )

    save_csv(
        REFERENCE_USAGE_TABLE,
        usage_rows,
    )

    # -------------------------------------------------------------------------
    # Group candidate arrays by actual array identity
    # -------------------------------------------------------------------------

    hash_groups = defaultdict(list)

    for cand in audited_candidates:
        hash_groups[cand["array_sha256"]].append(cand)

    hash_rows = []

    for array_hash, items in hash_groups.items():
        hash_rows.append({
            "array_sha256": array_hash,
            "candidate_count": len(items),
            "paths": ";".join(sorted(set(i["path"] for i in items))),
            "keys": ";".join(sorted(set(i["key"] for i in items))),
            "best_combined_score": max(i["combined_score"] for i in items),
        })

    hash_rows.sort(
        key=lambda r: r["best_combined_score"],
        reverse=True,
    )

    save_csv(
        REFERENCE_HASH_TABLE,
        hash_rows,
    )

    # -------------------------------------------------------------------------
    # Choose reference by distinct array identity, not filename duplication
    # -------------------------------------------------------------------------

    distinct_reference_groups = []

    for array_hash, items in hash_groups.items():
        best = max(
            items,
            key=lambda r: (
                r["combined_score"],
                r["total_score"],
                milestone_rank(r["path"]),
            ),
        )

        distinct_reference_groups.append({
            "array_sha256": array_hash,
            "best_candidate": best,
            "best_score": best["combined_score"],
            "candidate_count": len(items),
        })

    distinct_reference_groups.sort(
        key=lambda r: r["best_score"],
        reverse=True,
    )

    reference_choice = None
    reference_resolution = "NO_REFERENCE_GROUP"

    if distinct_reference_groups:
        top = distinct_reference_groups[0]

        if top["best_score"] > 0:
            if len(distinct_reference_groups) == 1:
                reference_choice = top["best_candidate"]
                reference_resolution = "UNIQUE_ARRAY_IDENTITY"
            else:
                second = distinct_reference_groups[1]

                if top["best_score"] - second["best_score"] >= 4:
                    reference_choice = top["best_candidate"]
                    reference_resolution = "REFERENCE_PROVENANCE_MARGIN"
                else:
                    reference_resolution = "AMBIGUOUS_DISTINCT_REFERENCE_ARRAYS"

    # -------------------------------------------------------------------------
    # Threshold provenance
    # -------------------------------------------------------------------------

    threshold_rows = extract_threshold_evidence(source_rows)

    save_csv(
        THRESHOLD_EVIDENCE_TABLE,
        threshold_rows,
    )

    threshold_value, threshold_resolution, threshold_ranked = (
        reconcile_threshold(threshold_rows)
    )

    threshold_conflict_rows = []

    for row in threshold_ranked:
        threshold_conflict_rows.append({
            "value": row["value"],
            "best_score": row["best_score"],
            "best_source": row["best_source"],
            "best_line": row["best_line"],
            "evidence_count": row["evidence_count"],
            "best_reasons": row["best_reasons"],
            "selected":
                threshold_value is not None
                and abs(row["value"] - threshold_value) < 1e-15,
        })

    save_csv(
        THRESHOLD_CONFLICT_TABLE,
        threshold_conflict_rows,
    )

    # -------------------------------------------------------------------------
    # Reference/threshold pair contract
    # -------------------------------------------------------------------------

    pair_rows = []

    if reference_choice is not None and threshold_value is not None:
        pair_rows.append({
            "reference_path": reference_choice["path"],
            "reference_key": reference_choice["key"],
            "reference_array_sha256": reference_choice["array_sha256"],
            "reference_resolution": reference_resolution,
            "reference_combined_score": reference_choice["combined_score"],
            "plume_threshold": threshold_value,
            "threshold_resolution": threshold_resolution,
            "pair_ready": True,
        })
    else:
        pair_rows.append({
            "reference_path":
                reference_choice["path"] if reference_choice else "",
            "reference_key":
                reference_choice["key"] if reference_choice else "",
            "reference_array_sha256":
                reference_choice["array_sha256"] if reference_choice else "",
            "reference_resolution": reference_resolution,
            "reference_combined_score":
                reference_choice["combined_score"] if reference_choice else "",
            "plume_threshold":
                threshold_value if threshold_value is not None else "",
            "threshold_resolution": threshold_resolution,
            "pair_ready": False,
        })

    save_csv(PAIR_TABLE, pair_rows)

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    checks = [
        (
            "Incoming SG7E1 reference-contract block reproduced",
            True,
        ),
        (
            "SG7E0R authoritative gate registry remains valid",
            e0r_contract.get("status")
            == "SG7E_GATE_AUTHORITY_RECONCILED",
        ),
        (
            "Frozen SG7D6 input remains authoritative",
            freeze_manifest.get("status")
            == "SG7D_FULL_GRID_CANDIDATE_FROZEN",
        ),
        (
            "Historical SG7E source inventory loaded",
            len(source_rows) > 0,
        ),
        (
            "Reference candidate arrays inventoried",
            len(audited_candidates) > 0,
        ),
        (
            "Reference array identities hashed/grouped",
            len(hash_rows) > 0,
        ),
        (
            "Reference usage provenance searched",
            len(usage_rows) > 0,
        ),
        (
            "Plume-threshold evidence searched",
            len(threshold_rows) > 0,
        ),
        (
            "No SG7E threshold changed or relaxed",
            True,
        ),
        (
            "No post-hoc alignment performed",
            True,
        ),
        (
            "No deployment correction performed",
            True,
        ),
    ]

    core_complete = all(bool(passed) for _, passed in checks)

    reference_resolved = reference_choice is not None
    threshold_resolved = threshold_value is not None

    if core_complete and reference_resolved and threshold_resolved:

        status = "SG7E_REFERENCE_CONTRACT_RECONCILED"

        diagnosis = "UNIQUE_HISTORICAL_REFERENCE_PLUME_AND_THRESHOLD_PAIR_ESTABLISHED"

        recommendation = (
            "Historical reference-plume provenance and plume-threshold provenance are now "
            "reconciled without inventing a new reference or changing any threshold. Rerun "
            "the frozen SG7E deployment validation using this locked reference/threshold pair "
            "and the already reconciled four-gate registry."
        )

        next_milestone = (
            "V15-SG7E1-R — Reconciled Frozen Full-Grid Deployment Validation"
        )

    elif core_complete and not reference_resolved and not threshold_resolved:

        status = "SG7E_REFERENCE_AND_THRESHOLD_PROVENANCE_STILL_AMBIGUOUS"

        diagnosis = "DISTINCT_REFERENCE_ARRAYS_AND_THRESHOLD_VALUES_REQUIRE_LINEAGE_RESOLUTION"

        recommendation = (
            "Do not evaluate SG7E gates. Both the physical reference array and plume threshold "
            "remain ambiguous across historical artifacts. Resolve only the top conflicting "
            "reference and threshold lineages; do not select values manually."
        )

        next_milestone = (
            "V15-SG7E1R1 — Reference / Threshold Lineage Conflict Audit"
        )

    elif core_complete and not reference_resolved:

        status = "SG7E_REFERENCE_PLUME_PROVENANCE_STILL_AMBIGUOUS"

        diagnosis = "PLUME_THRESHOLD_RESOLVED_REFERENCE_ARRAY_IDENTITY_NOT_RESOLVED"

        recommendation = (
            "Do not evaluate SG7E gates. The plume threshold is resolved, but distinct "
            "historical reference arrays remain tied in provenance. Audit only those reference "
            "array lineages."
        )

        next_milestone = (
            "V15-SG7E1R1 — Reference Plume Lineage Conflict Audit"
        )

    elif core_complete:

        status = "SG7E_PLUME_THRESHOLD_PROVENANCE_STILL_AMBIGUOUS"

        diagnosis = "REFERENCE_ARRAY_RESOLVED_PLUME_THRESHOLD_NOT_RESOLVED"

        recommendation = (
            "Do not evaluate SG7E gates. The historical reference array is resolved, but the "
            "plume threshold remains ambiguous. Audit only threshold provenance."
        )

        next_milestone = (
            "V15-SG7E1R1 — Plume Threshold Lineage Conflict Audit"
        )

    else:

        status = "SG7E_REFERENCE_PROVENANCE_AUDIT_INCOMPLETE"

        diagnosis = "ONE_OR_MORE_REFERENCE_PROVENANCE_CHECKS_FAILED"

        recommendation = (
            "Do not evaluate SG7E gates. Repair only the failed SG7E1R0 provenance checks."
        )

        next_milestone = (
            "V15-SG7E1R1 — Reference Provenance Audit Repair"
        )

    decision_rows = [{
        "status": status,
        "diagnosis": diagnosis,
        "reference_resolved": reference_resolved,
        "reference_resolution": reference_resolution,
        "reference_path":
            reference_choice["path"] if reference_choice else "",
        "reference_key":
            reference_choice["key"] if reference_choice else "",
        "reference_array_sha256":
            reference_choice["array_sha256"] if reference_choice else "",
        "threshold_resolved": threshold_resolved,
        "threshold_value":
            threshold_value if threshold_value is not None else "",
        "threshold_resolution": threshold_resolution,
        "distinct_reference_arrays": len(distinct_reference_groups),
        "threshold_value_count": len(threshold_ranked),
        "next_milestone": next_milestone,
    }]

    save_csv(DECISION_TABLE, decision_rows)

    # -------------------------------------------------------------------------
    # Contract / summary
    # -------------------------------------------------------------------------

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R0",
            "status": status,
            "diagnosis": diagnosis,

            "reference": {
                "resolved": reference_resolved,
                "path":
                    reference_choice["path"] if reference_choice else None,
                "key":
                    reference_choice["key"] if reference_choice else None,
                "array_sha256":
                    reference_choice["array_sha256"] if reference_choice else None,
                "resolution": reference_resolution,
            },

            "plume_threshold": {
                "resolved": threshold_resolved,
                "value": threshold_value,
                "resolution": threshold_resolution,
            },

            "frozen_candidate_changed": False,
            "threshold_changed": False,
            "posthoc_alignment": False,
            "deployment_correction_performed": False,

            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E1R0",
            "status": status,
            "diagnosis": diagnosis,
            "reference_resolved": reference_resolved,
            "threshold_resolved": threshold_resolved,
            "distinct_reference_arrays": len(distinct_reference_groups),
            "threshold_value_count": len(threshold_ranked),
            "threshold_changed": False,
            "deployment_correction_performed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("REFERENCE PLUME PROVENANCE")
    print(f"  Candidate arrays        : {len(audited_candidates)}")
    print(f"  Distinct array hashes   : {len(distinct_reference_groups)}")
    print(f"  Reference resolved      : {reference_resolved}")
    print(f"  Resolution              : {reference_resolution}")

    if reference_choice is not None:
        print(f"  Selected file           : {Path(reference_choice['path']).name}")
        print(f"  Selected key            : {reference_choice['key']}")
        print(f"  Array SHA-256           : {reference_choice['array_sha256']}")
        print(f"  Combined score          : {reference_choice['combined_score']}")

    print("\nPLUME THRESHOLD PROVENANCE")
    print(f"  Evidence records        : {len(threshold_rows)}")
    print(f"  Distinct values         : {len(threshold_ranked)}")
    print(f"  Threshold resolved      : {threshold_resolved}")
    print(f"  Resolution              : {threshold_resolution}")

    if threshold_value is not None:
        print(f"  Selected threshold      : {threshold_value:.12g}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R0 PROVENANCE VALIDATION")
    print("=" * 78)

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{desc}"
        )

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
    print(f"  {REFERENCE_CANDIDATE_TABLE.name}")
    print(f"  {REFERENCE_HASH_TABLE.name}")
    print(f"  {REFERENCE_USAGE_TABLE.name}")
    print(f"  {THRESHOLD_EVIDENCE_TABLE.name}")
    print(f"  {THRESHOLD_CONFLICT_TABLE.name}")
    print(f"  {PAIR_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R0 HISTORICAL REFERENCE PLUME PROVENANCE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
