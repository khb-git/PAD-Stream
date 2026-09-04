from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import hashlib
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R2
# Top Reference Lineage Creation-Chain Audit
#
# FORENSIC REFERENCE-SEMANTICS MILESTONE
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
# SG7E1R1 found 7 distinct historical 15x50x50 array identities and could not
# resolve the top reference lineage. The leading keys included:
#
#   coverage_mask
#   streamline_count
#   coverage_weight_m3
#
# Those names may describe map-back/support diagnostics rather than physical
# saturation/reference truth. SG7E1R2 therefore resolves SEMANTIC ROLE and
# CREATION CHAIN before any array may be admitted as an SG7E truth/reference.
#
# SG7E1R2:
#
#   1. loads the 7 distinct reference-array lineages from SG7E1R1,
#   2. traces np.savez / np.savez_compressed creation statements,
#   3. traces array-key assignments and upstream variable dependencies,
#   4. searches sibling source/contracts/summaries for semantic descriptions,
#   5. classifies each array as:
#
#        REFERENCE_SATURATION_TRUTH
#        REFERENCE_PLUME_MASK
#        COVERAGE_SUPPORT_MASK
#        STREAMLINE_COUNT_DIAGNOSTIC
#        COVERAGE_WEIGHT_DIAGNOSTIC
#        CANDIDATE_OR_PREDICTION
#        UNKNOWN
#
#   6. excludes diagnostics from reference eligibility,
#   7. determines whether exactly one reference-eligible historical lineage
#      remains.
#
# SG7E1R2 does NOT select a reference based on candidate performance.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R2"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1_DIR = ROOT / "output" / "V15_SG7E1R1"

R1_SUMMARY = R1_DIR / "PAD_Stream_V15SG7E1R1_Summary.json"
R1_CONTRACT = R1_DIR / "V15SG7E1R1_Reconciled_Reference_Lineage_Contract.json"
R1_PROVENANCE = R1_DIR / "V15SG7E1R1_Reference_Provenance_Scoring.csv"
R1_LINEAGE = R1_DIR / "V15SG7E1R1_Reference_Array_Lineage.csv"
R1_MORPHOLOGY = R1_DIR / "V15SG7E1R1_Reference_Array_Morphology.csv"

R0_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R0"
    / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"
)

E0_SOURCE_DISCOVERY = (
    ROOT / "output" / "V15_SG7E0"
    / "V15SG7E0_Historical_SG7E_Source_Discovery.csv"
)

D6_FREEZE_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R2_Summary.json"

CREATION_TRACE_TABLE = OUT / "V15SG7E1R2_Array_Creation_Trace.csv"
DEPENDENCY_TABLE = OUT / "V15SG7E1R2_Array_Dependency_Trace.csv"
SEMANTIC_EVIDENCE_TABLE = OUT / "V15SG7E1R2_Semantic_Evidence.csv"
ROLE_TABLE = OUT / "V15SG7E1R2_Array_Semantic_Roles.csv"
ELIGIBILITY_TABLE = OUT / "V15SG7E1R2_Reference_Eligibility.csv"
DECISION_TABLE = OUT / "V15SG7E1R2_Reference_Creation_Chain_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R2_Reference_Creation_Chain_Contract.json"

EXPECTED_SHAPE = (15, 50, 50)

ROLE_REFERENCE_SAT = "REFERENCE_SATURATION_TRUTH"
ROLE_REFERENCE_MASK = "REFERENCE_PLUME_MASK"
ROLE_COVERAGE = "COVERAGE_SUPPORT_MASK"
ROLE_COUNT = "STREAMLINE_COUNT_DIAGNOSTIC"
ROLE_WEIGHT = "COVERAGE_WEIGHT_DIAGNOSTIC"
ROLE_CANDIDATE = "CANDIDATE_OR_PREDICTION"
ROLE_UNKNOWN = "UNKNOWN"

REFERENCE_ELIGIBLE_ROLES = {
    ROLE_REFERENCE_SAT,
    ROLE_REFERENCE_MASK,
}


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
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def sha256_array(arr):
    return hashlib.sha256(
        np.ascontiguousarray(arr).tobytes()
    ).hexdigest()


def load_array(path: str, key: str):
    p = Path(path)
    db = np.load(p, allow_pickle=True)
    arr = np.asarray(db[key])
    if arr.shape != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected shape for {p.name}::{key}: {arr.shape}"
        )
    return arr


def source_files_near(npz_path: Path):
    """
    Return source/contract/summary files in the NPZ directory and parent.
    """
    files = []
    seen = set()

    for directory in [npz_path.parent, npz_path.parent.parent]:
        if not directory.exists():
            continue

        for p in directory.iterdir():
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".py", ".json", ".csv", ".txt"}:
                continue
            rp = str(p.resolve())
            if rp in seen:
                continue
            seen.add(rp)
            files.append(p)

    return files


def find_savez_assignments(source_path: Path, target_filename: str, target_key: str):
    """
    Best-effort source trace for np.savez / np.savez_compressed calls that
    mention the target NPZ filename and/or target key.
    """
    text = safe_text(source_path)
    if not text:
        return []

    rows = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        lower = line.lower()

        if "savez" not in lower:
            continue

        context = "\n".join(
            lines[max(0, idx - 8):min(len(lines), idx + 12)]
        )

        filename_hit = target_filename.lower() in context.lower()
        key_hit = re.search(
            rf'(?<![A-Za-z0-9_]){re.escape(target_key)}\s*=',
            context,
        ) is not None

        if filename_hit or key_hit:
            expr = ""

            # Extract key=value expression from context if available.
            m = re.search(
                rf'(?<![A-Za-z0-9_]){re.escape(target_key)}\s*=\s*([^,\n\)]+)',
                context,
            )
            if m:
                expr = m.group(1).strip()

            rows.append({
                "source": str(source_path),
                "line": idx,
                "target_filename": target_filename,
                "target_key": target_key,
                "filename_hit": filename_hit,
                "key_hit": key_hit,
                "saved_expression": expr,
                "context": context[:2000],
            })

    return rows


def extract_identifier(expr: str):
    """
    Simple dependency extraction from a saved expression.
    """
    if not expr:
        return []

    tokens = re.findall(
        r'(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)',
        expr,
    )

    ignore = {
        "np", "float", "int", "bool", "array", "asarray",
        "astype", "where", "clip", "minimum", "maximum",
        "sum", "mean", "nan", "True", "False",
    }

    return [t for t in tokens if t not in ignore]


def trace_symbol_assignments(source_path: Path, symbol: str):
    """
    Search direct assignments of a variable symbol in source.
    """
    text = safe_text(source_path)
    if not text or not symbol:
        return []

    rows = []

    pattern = re.compile(
        rf'^\s*{re.escape(symbol)}\s*=\s*(.+)$'
    )

    for idx, line in enumerate(text.splitlines(), start=1):
        m = pattern.match(line)
        if m:
            rows.append({
                "source": str(source_path),
                "line": idx,
                "symbol": symbol,
                "expression": m.group(1).strip()[:1000],
            })

    return rows


def semantic_evidence(path: Path, key: str):
    """
    Collect semantic evidence from key/file names and sibling text.
    """
    file_name = path.name.lower()
    key_l = key.lower()

    bundle = "\n".join(
        safe_text(p)
        for p in source_files_near(path)
    ).lower()

    evidence = []

    def add(kind, score, text):
        evidence.append({
            "kind": kind,
            "score": score,
            "text": text,
        })

    # Strong diagnostic key semantics.
    if "streamline_count" in key_l or (
        "streamline" in key_l and "count" in key_l
    ):
        add("count_key", 100, "key explicitly denotes streamline count")

    if "coverage_weight" in key_l or (
        "coverage" in key_l and "weight" in key_l
    ):
        add("coverage_weight_key", 100, "key explicitly denotes coverage weight")

    if "coverage_mask" in key_l or (
        "coverage" in key_l and "mask" in key_l
    ):
        add("coverage_mask_key", 90, "key explicitly denotes coverage/support mask")

    # Reference truth semantics.
    if any(tok in key_l for tok in ("truth", "reference", "canonical", "benchmark")):
        add("reference_key", 80, "key contains explicit reference/truth semantics")

    if any(tok in file_name for tok in ("truth", "reference", "canonical", "benchmark")):
        add("reference_filename", 50, "filename contains explicit reference/truth semantics")

    # Candidate/prediction semantics.
    if any(tok in key_l for tok in ("candidate", "pred", "prediction", "mapped", "p4")):
        add("candidate_key", 80, "key denotes candidate/prediction")

    if any(tok in file_name for tok in ("candidate", "prediction", "mapped", "p4")):
        add("candidate_filename", 40, "filename denotes candidate/prediction")

    # Source text semantics.
    for token, score in (
        ("reference plume", 70),
        ("reference_plume", 70),
        ("truth plume", 70),
        ("truth_plume", 70),
        ("ground truth", 70),
        ("ground_truth", 70),
        ("canonical plume", 60),
        ("canonical_plume", 60),
        ("coverage mask", 60),
        ("coverage_mask", 60),
        ("streamline count", 60),
        ("streamline_count", 60),
        ("coverage weight", 60),
        ("coverage_weight", 60),
    ):
        if token in bundle:
            add("source_text", score, f"source bundle contains {token}")

    return evidence


def infer_role(path: Path, key: str, arr: np.ndarray, creation_rows, evidence):
    """
    Conservative semantic role classification.
    """

    key_l = key.lower()

    # Explicit key semantics dominate.
    if "streamline_count" in key_l or (
        "streamline" in key_l and "count" in key_l
    ):
        return ROLE_COUNT, "explicit_key_semantics"

    if "coverage_weight" in key_l or (
        "coverage" in key_l and "weight" in key_l
    ):
        return ROLE_WEIGHT, "explicit_key_semantics"

    if "coverage_mask" in key_l or (
        "coverage" in key_l and "mask" in key_l
    ):
        return ROLE_COVERAGE, "explicit_key_semantics"

    if any(tok in key_l for tok in ("candidate", "pred", "prediction", "mapped", "p4")):
        return ROLE_CANDIDATE, "explicit_key_semantics"

    # Explicit truth/reference naming.
    if any(tok in key_l for tok in ("truth", "reference", "canonical", "benchmark")):
        finite = arr[np.isfinite(arr)]

        if finite.size:
            unique = np.unique(finite)

            if (
                unique.size <= 3
                and np.all(np.isin(unique, [0, 1, 0.0, 1.0]))
            ):
                return ROLE_REFERENCE_MASK, "explicit_reference_key_binary_array"

        return ROLE_REFERENCE_SAT, "explicit_reference_key"

    # Creation expression can disambiguate.
    creation_text = " ".join(
        str(r.get("saved_expression", ""))
        for r in creation_rows
    ).lower()

    if "coverage" in creation_text and "mask" in creation_text:
        return ROLE_COVERAGE, "creation_expression"

    if "streamline" in creation_text and "count" in creation_text:
        return ROLE_COUNT, "creation_expression"

    if "coverage" in creation_text and "weight" in creation_text:
        return ROLE_WEIGHT, "creation_expression"

    if any(tok in creation_text for tok in ("truth", "reference", "canonical", "benchmark")):
        finite = arr[np.isfinite(arr)]
        if finite.size:
            unique = np.unique(finite)
            if unique.size <= 3 and np.all(np.isin(unique, [0, 1, 0.0, 1.0])):
                return ROLE_REFERENCE_MASK, "creation_expression_reference_binary"
        return ROLE_REFERENCE_SAT, "creation_expression_reference"

    # Array morphology alone cannot establish truth. It may only flag a mask.
    finite = arr[np.isfinite(arr)]
    if finite.size:
        unique = np.unique(finite)

        if unique.size <= 3 and np.all(np.isin(unique, [0, 1, 0.0, 1.0])):
            # Do NOT call binary arrays reference masks without provenance.
            return ROLE_UNKNOWN, "binary_array_but_no_reference_semantics"

    return ROLE_UNKNOWN, "insufficient_semantic_provenance"


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R2")
    print("Top Reference Lineage Creation-Chain Audit")
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

    r1_summary = load_json(R1_SUMMARY)
    r1_contract = load_json(R1_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_FREEZE_MANIFEST)

    if (
        r1_summary.get("status")
        != "SG7E_REFERENCE_LINEAGE_CONFLICT_REMAINS"
    ):
        raise RuntimeError(
            "SG7E1R2 requires SG7E1R1 lineage-conflict status."
        )

    if (
        r1_summary.get("diagnosis")
        != "TOP_HISTORICAL_REFERENCE_LINEAGES_REMAIN_PROVENANCE_TIED"
    ):
        raise RuntimeError(
            "SG7E1R2 requires SG7E1R1 tied-reference diagnosis."
        )

    threshold_info = r0_contract.get("plume_threshold", {})

    if not threshold_info.get("resolved", False):
        raise RuntimeError(
            "SG7E1R2 requires the already resolved plume threshold."
        )

    threshold = float(threshold_info["value"])

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError(
            "SG7E1R2 requires frozen SG7D6 input provenance."
        )

    provenance_rows = load_csv(R1_PROVENANCE)
    lineage_rows_in = load_csv(R1_LINEAGE)
    morphology_rows_in = load_csv(R1_MORPHOLOGY)

    # One representative per distinct array identity.
    reps = []

    for row in provenance_rows:
        reps.append({
            "array_sha256": row["array_sha256"],
            "path": row["representative_path"],
            "key": row["representative_key"],
            "lineage_score": int(float(row["lineage_score"])),
        })

    # -------------------------------------------------------------------------
    # Trace creation calls
    # -------------------------------------------------------------------------

    creation_trace_rows = []
    dependency_rows = []
    semantic_rows = []
    role_rows = []
    eligibility_rows = []

    source_inventory = load_csv(E0_SOURCE_DISCOVERY)

    python_sources = [
        Path(row["path"])
        for row in source_inventory
        if Path(row["path"]).suffix.lower() == ".py"
        and Path(row["path"]).exists()
    ]

    for rep in reps:
        npz_path = Path(rep["path"])
        key = rep["key"]
        arr = load_array(rep["path"], key)

        local_sources = source_files_near(npz_path)

        # Include all SG7E python sources, but local sources first.
        candidates_sources = []
        seen = set()

        for p in local_sources + python_sources:
            rp = str(p.resolve())
            if rp in seen:
                continue
            seen.add(rp)
            candidates_sources.append(p)

        creation_rows = []

        for source in candidates_sources:
            hits = find_savez_assignments(
                source,
                npz_path.name,
                key,
            )
            creation_rows.extend(hits)

        for hit in creation_rows:
            row = dict(hit)
            row["array_sha256"] = rep["array_sha256"]
            creation_trace_rows.append(row)

            symbols = extract_identifier(
                hit.get("saved_expression", "")
            )

            for symbol in symbols:
                assignments = trace_symbol_assignments(
                    Path(hit["source"]),
                    symbol,
                )

                if assignments:
                    for a in assignments:
                        dep = dict(a)
                        dep["array_sha256"] = rep["array_sha256"]
                        dep["target_key"] = key
                        dependency_rows.append(dep)
                else:
                    dependency_rows.append({
                        "array_sha256": rep["array_sha256"],
                        "target_key": key,
                        "source": hit["source"],
                        "line": "",
                        "symbol": symbol,
                        "expression": "",
                    })

        # Semantic evidence.
        evidence = semantic_evidence(npz_path, key)

        for ev in evidence:
            semantic_rows.append({
                "array_sha256": rep["array_sha256"],
                "path": rep["path"],
                "key": key,
                "evidence_kind": ev["kind"],
                "evidence_score": ev["score"],
                "evidence_text": ev["text"],
            })

        role, role_basis = infer_role(
            npz_path,
            key,
            arr,
            creation_rows,
            evidence,
        )

        finite = arr[np.isfinite(arr)]
        unique_count = (
            int(np.unique(finite).size)
            if finite.size
            else 0
        )

        role_rows.append({
            "array_sha256": rep["array_sha256"],
            "path": rep["path"],
            "key": key,
            "historical_lineage_score": rep["lineage_score"],
            "creation_trace_count": len(creation_rows),
            "semantic_role": role,
            "role_basis": role_basis,
            "dtype": str(arr.dtype),
            "unique_finite_values": unique_count,
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
        })

        eligible = role in REFERENCE_ELIGIBLE_ROLES

        eligibility_rows.append({
            "array_sha256": rep["array_sha256"],
            "path": rep["path"],
            "key": key,
            "semantic_role": role,
            "reference_eligible": eligible,
            "eligibility_reason":
                "physical/historical reference semantics established"
                if eligible
                else
                "diagnostic/candidate/unknown semantics are not valid SG7E truth",
        })

    save_csv(CREATION_TRACE_TABLE, creation_trace_rows)
    save_csv(DEPENDENCY_TABLE, dependency_rows)
    save_csv(SEMANTIC_EVIDENCE_TABLE, semantic_rows)
    save_csv(ROLE_TABLE, role_rows)
    save_csv(ELIGIBILITY_TABLE, eligibility_rows)

    # -------------------------------------------------------------------------
    # Determine eligible reference lineages
    # -------------------------------------------------------------------------

    eligible_rows = [
        row
        for row in eligibility_rows
        if row["reference_eligible"]
    ]

    # Sort eligible arrays by historical lineage score only.
    score_lookup = {
        row["array_sha256"]: int(row["historical_lineage_score"])
        for row in role_rows
    }

    eligible_rows.sort(
        key=lambda r: score_lookup[r["array_sha256"]],
        reverse=True,
    )

    selected = eligible_rows[0] if len(eligible_rows) == 1 else None

    # If multiple eligible references exist, do NOT use score alone to select.
    # Their creation chains need a further divergence audit.
    if len(eligible_rows) == 1:
        status = "SG7E_REFERENCE_CREATION_CHAIN_RECONCILED"
        diagnosis = "ONE_REFERENCE_ELIGIBLE_HISTORICAL_TRUTH_LINEAGE_REMAINS"
        recommendation = (
            "Creation-chain and semantic-role auditing leaves exactly one historical "
            "reference-eligible SG7E truth/plume lineage. Lock that array identity with "
            "the previously resolved S=0.5 plume threshold and rerun the frozen deployment "
            "validation. Coverage masks, streamline counts, coverage weights, candidate "
            "fields, and unknown arrays remain excluded from truth/reference use."
        )
        next_milestone = (
            "V15-SG7E1-R — Reconciled Frozen Full-Grid Deployment Validation"
        )

    elif len(eligible_rows) > 1:
        status = "SG7E_MULTIPLE_REFERENCE_TRUTH_LINEAGES_REMAIN"
        diagnosis = "MORE_THAN_ONE_REFERENCE_ELIGIBLE_CREATION_CHAIN_SURVIVES"
        recommendation = (
            "Do not evaluate SG7E gates. Multiple arrays still have defensible historical "
            "truth/reference creation chains. Audit only those eligible truth lineages and "
            "their upstream creation semantics; do not use frozen-candidate performance to "
            "choose among them."
        )
        next_milestone = (
            "V15-SG7E1R3 — Eligible Truth-Lineage Divergence Audit"
        )

    else:
        status = "SG7E_HISTORICAL_REFERENCE_TRUTH_NOT_PERSISTED"
        diagnosis = "NO_DISCOVERED_15X50X50_ARRAY_HAS_VALID_REFERENCE_TRUTH_SEMANTICS"
        recommendation = (
            "Do not evaluate SG7E gates and do not repurpose a coverage/support diagnostic "
            "as truth. The historical SG7E acceptance workflow appears not to have persisted "
            "a valid 15x50x50 reference truth/plume array among the discovered artifacts. "
            "Trace the historical SG7E source that generated the acceptance metrics and "
            "reconstruct its reference input from the original upstream physics artifact."
        )
        next_milestone = (
            "V15-SG7E1R3 — Historical SG7E Reference Input Reconstruction Audit"
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    role_counts = defaultdict(int)
    for row in role_rows:
        role_counts[row["semantic_role"]] += 1

    checks = [
        (
            "Incoming SG7E1R1 lineage conflict reproduced",
            True,
        ),
        (
            "Resolved historical plume threshold retained",
            abs(threshold - 0.5) < 1e-15,
        ),
        (
            "All distinct reference identities retained",
            len(reps) == 7,
        ),
        (
            "Array creation statements searched",
            True,
        ),
        (
            "Upstream dependency symbols searched",
            True,
        ),
        (
            "Semantic role assigned to every distinct array",
            len(role_rows) == len(reps),
        ),
        (
            "Coverage/support diagnostics explicitly excluded from truth eligibility",
            all(
                not row["reference_eligible"]
                for row in eligibility_rows
                if row["semantic_role"] in {
                    ROLE_COVERAGE,
                    ROLE_COUNT,
                    ROLE_WEIGHT,
                    ROLE_CANDIDATE,
                }
            ),
        ),
        (
            "No frozen-candidate performance used for reference selection",
            True,
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

    # -------------------------------------------------------------------------
    # Decision output
    # -------------------------------------------------------------------------

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "plume_threshold": threshold,
        "distinct_arrays": len(reps),
        "reference_eligible_arrays": len(eligible_rows),
        "selected_array_sha256":
            selected["array_sha256"] if selected else "",
        "selected_path":
            selected["path"] if selected else "",
        "selected_key":
            selected["key"] if selected else "",
        "reference_saturation_truth_count":
            role_counts[ROLE_REFERENCE_SAT],
        "reference_plume_mask_count":
            role_counts[ROLE_REFERENCE_MASK],
        "coverage_support_mask_count":
            role_counts[ROLE_COVERAGE],
        "streamline_count_diagnostic_count":
            role_counts[ROLE_COUNT],
        "coverage_weight_diagnostic_count":
            role_counts[ROLE_WEIGHT],
        "candidate_or_prediction_count":
            role_counts[ROLE_CANDIDATE],
        "unknown_count":
            role_counts[ROLE_UNKNOWN],
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R2",
            "status": status,
            "diagnosis": diagnosis,

            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },

            "semantic_roles": {
                "REFERENCE_SATURATION_TRUTH": role_counts[ROLE_REFERENCE_SAT],
                "REFERENCE_PLUME_MASK": role_counts[ROLE_REFERENCE_MASK],
                "COVERAGE_SUPPORT_MASK": role_counts[ROLE_COVERAGE],
                "STREAMLINE_COUNT_DIAGNOSTIC": role_counts[ROLE_COUNT],
                "COVERAGE_WEIGHT_DIAGNOSTIC": role_counts[ROLE_WEIGHT],
                "CANDIDATE_OR_PREDICTION": role_counts[ROLE_CANDIDATE],
                "UNKNOWN": role_counts[ROLE_UNKNOWN],
            },

            "reference_eligible": {
                "count": len(eligible_rows),
                "selected":
                    {
                        "array_sha256": selected["array_sha256"],
                        "path": selected["path"],
                        "key": selected["key"],
                    }
                    if selected
                    else None,
            },

            "selection_constraints": {
                "candidate_performance_used": False,
                "diagnostic_arrays_allowed_as_truth": False,
                "threshold_changed": False,
                "posthoc_alignment": False,
                "deployment_correction_performed": False,
            },

            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E1R2",
            "status": status,
            "diagnosis": diagnosis,
            "plume_threshold": threshold,
            "distinct_arrays": len(reps),
            "reference_eligible_arrays": len(eligible_rows),
            "semantic_role_counts": dict(role_counts),
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("CREATION-CHAIN SEMANTIC AUDIT")
    print(f"  Distinct arrays         : {len(reps)}")
    print(f"  Plume threshold         : {threshold:.6f}")
    print(f"  Creation traces found   : {len(creation_trace_rows)}")
    print(f"  Dependency records      : {len(dependency_rows)}")
    print(f"  Reference eligible      : {len(eligible_rows)}")

    print("\nSEMANTIC ROLE COUNTS")
    for role in (
        ROLE_REFERENCE_SAT,
        ROLE_REFERENCE_MASK,
        ROLE_COVERAGE,
        ROLE_COUNT,
        ROLE_WEIGHT,
        ROLE_CANDIDATE,
        ROLE_UNKNOWN,
    ):
        print(f"  {role:36s}: {role_counts[role]}")

    print("\nARRAY ROLE CLASSIFICATION")
    for row in role_rows:
        print(
            f"  {row['semantic_role']:36s} | "
            f"{Path(row['path']).name} :: {row['key']} | "
            f"{row['array_sha256'][:16]}"
        )

    if selected:
        print("\nSELECTED REFERENCE-ELIGIBLE LINEAGE")
        print(f"  File                    : {Path(selected['path']).name}")
        print(f"  Key                     : {selected['key']}")
        print(f"  Array SHA-256           : {selected['array_sha256']}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R2 CREATION-CHAIN VALIDATION")
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
    print(f"  {CREATION_TRACE_TABLE.name}")
    print(f"  {DEPENDENCY_TABLE.name}")
    print(f"  {SEMANTIC_EVIDENCE_TABLE.name}")
    print(f"  {ROLE_TABLE.name}")
    print(f"  {ELIGIBILITY_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R2 TOP REFERENCE LINEAGE CREATION-CHAIN AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No coverage/support diagnostic was promoted to truth by assumption.")
    print("No frozen-candidate performance was used for reference selection.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
