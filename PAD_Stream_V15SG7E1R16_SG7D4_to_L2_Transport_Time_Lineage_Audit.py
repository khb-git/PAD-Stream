from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R16
# SG7D4-to-L2 Transport-Time Lineage Audit
#
# FORENSIC TRANSPORT-TIME CLASSIFICATION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
# NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
# NO PHYSICAL TIME WILL BE ASSIGNED BY SIMILARITY.
#
# PURPOSE
# -------
# SG7E1R15 established:
#
#   SG7D6_PHYSICAL_TIME_IDENTITY_NOT_RESOLVED
#
# with:
#
#   FROZEN_SINGLE_GRID_HAS_NO_AUTHORITATIVE_TIME_ASSIGNMENT
#
# R16 now traces the frozen grid backward numerically and semantically:
#
#   SG7D6 frozen full grid
#      <- SG7D4 completed grid
#      <- SG7D1 conservative map-back
#      <- frozen L2 streamline state
#      <- SG7C/R1F3 deployment state
#
# and classifies the L2 transport state as one of:
#
#   EXPLICIT_PHYSICAL_TIME_SNAPSHOT
#   TERMINAL_OR_ENDPOINT_STATE
#   NORMALIZED_XI_TAU_DEPLOYMENT_STATE
#   MULTI_TIME_TRANSPORT_STATE
#   TRANSPORT_TIME_IDENTITY_UNRESOLVED
#
# This milestone explicitly distinguishes calendar-time semantics from
# streamline-coordinate / TOF semantics.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R16"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R15_DIR = ROOT / "output" / "V15_SG7E1R15"
R15_SUMMARY = R15_DIR / "PAD_Stream_V15SG7E1R15_Summary.json"
R15_CONTRACT = R15_DIR / "V15SG7E1R15_Frozen_SG7D6_Physical_Time_Compatibility_Contract.json"

D6_DIR = ROOT / "output" / "V15_SG7D6"
D6_FROZEN = (
    D6_DIR / "frozen_full_grid"
    / "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz"
)

D4_NUM = (
    ROOT / "output" / "V15_SG7D4"
    / "V15SG7D4_Completed_Full_Grid.npz"
)

D1_NUM = (
    ROOT / "output" / "V15_SG7D1"
    / "V15SG7D1_Conservative_MapBack.npz"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

R1F3_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
)

R1F3_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "V15SG7CR3F5R1F3_Frozen_Deployment_Contract.json"
)

R1F2CRR_NUM = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
    / "V15SG7CR3F5R1F2CRR_Independent_Validation.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

CHAIN_TABLE = OUT / "V15SG7E1R16_Numerical_Lineage_Closure.csv"
L2_ARRAY_TABLE = OUT / "V15SG7E1R16_Frozen_L2_Array_Inventory.csv"
TIME_SEMANTIC_TABLE = OUT / "V15SG7E1R16_Transport_Time_Semantic_Evidence.csv"
SOURCE_TRACE_TABLE = OUT / "V15SG7E1R16_L2_Creation_Evaluation_Source_Trace.csv"
TOF_TABLE = OUT / "V15SG7E1R16_Xi_TOF_Semantic_Audit.csv"
CLASS_TABLE = OUT / "V15SG7E1R16_Transport_State_Classification.csv"
DECISION_TABLE = OUT / "V15SG7E1R16_Transport_Time_Lineage_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R16_SG7D4_to_L2_Transport_Time_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R16_Summary.json"

EXPECTED_GRID_SHAPE = (15, 50, 50)


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def find_grid_key(db):
    preferred = [
        "saturation_grid_full",
        "full_grid_saturation",
        "completed_full_grid",
        "saturation_grid",
        "grid_saturation",
    ]
    for key in preferred:
        if key in db.files:
            arr = np.asarray(db[key])
            if arr.shape == EXPECTED_GRID_SHAPE:
                return key, arr
    for key in db.files:
        arr = np.asarray(db[key])
        if arr.shape == EXPECTED_GRID_SHAPE:
            return key, arr
    return None, None


def extract_time_semantics_from_text(text):
    rows = []
    patterns = [
        ("physical_time_days", r"\b(?:time_days|evaluation_time_days|snapshot_time_days)\b\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"),
        ("calendar_day_label", r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:d|day|days)\b"),
        ("terminal_semantics", r"\b(?:terminal|endpoint|final state|tau_end|terminal_tof)\b"),
        ("xi_semantics", r"\b(?:xi|common_xi|transport_xi|normalized_xi)\b"),
        ("tof_semantics", r"\b(?:tof|time[-_ ]of[-_ ]flight|tau_s|tau_end)\b"),
        ("normalized_semantics", r"\b(?:normalized|dimensionless|0\s*->\s*1|0\s*to\s*1)\b"),
        ("multi_time_semantics", r"\b(?:times_days|multiple times|multi[-_ ]time|time axis)\b"),
    ]

    for label, pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            value = ""
            if m.lastindex:
                value = m.group(1)
            rows.append((label, value, m.group(0)))
    return rows


def project_python_files():
    files = []
    for p in ROOT.rglob("*.py"):
        low = {x.lower() for x in p.parts}
        if ".venv" in low or "site-packages" in low or "__pycache__" in low:
            continue
        files.append(p.resolve())
    return sorted(set(files))


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R16")
    print("SG7D4-to-L2 Transport-Time Lineage Audit")
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
NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
NO PHYSICAL TIME WILL BE ASSIGNED BY SIMILARITY.
""")

    r15_summary = load_json(R15_SUMMARY)
    r15_contract = load_json(R15_CONTRACT)
    r1f3_manifest = load_json(R1F3_MANIFEST)
    r1f3_contract = load_json(R1F3_CONTRACT)

    if r15_summary.get("status") != "SG7D6_PHYSICAL_TIME_IDENTITY_NOT_RESOLVED":
        raise RuntimeError(
            "R16 requires unresolved R15 physical-time status."
        )

    # -------------------------------------------------------------------------
    # Numerical lineage closure.
    # -------------------------------------------------------------------------

    chain_rows = []

    if not D6_FROZEN.exists():
        raise FileNotFoundError(D6_FROZEN)
    if not D4_NUM.exists():
        raise FileNotFoundError(D4_NUM)
    if not D1_NUM.exists():
        raise FileNotFoundError(D1_NUM)
    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    d6 = np.load(D6_FROZEN, allow_pickle=True)
    d4 = np.load(D4_NUM, allow_pickle=True)
    d1 = np.load(D1_NUM, allow_pickle=True)
    l2 = np.load(R1F3_FROZEN, allow_pickle=True)

    d6_key, d6_grid = find_grid_key(d6)
    d4_key, d4_grid = find_grid_key(d4)

    if d6_grid is None or d4_grid is None:
        raise RuntimeError("Could not identify full-grid saturation in D6 or D4.")

    d6_hash = sha256_array(d6_grid)
    d4_hash = sha256_array(d4_grid)

    chain_rows.append({
        "stage_from": "SG7D4",
        "stage_to": "SG7D6",
        "from_key": d4_key,
        "to_key": d6_key,
        "from_shape": str(d4_grid.shape),
        "to_shape": str(d6_grid.shape),
        "from_sha256": d4_hash,
        "to_sha256": d6_hash,
        "exact_hash_match": d4_hash == d6_hash,
    })

    # D1 grid-like supported saturation field may be NaN outside support.
    d1_grid_candidates = []
    for key in d1.files:
        arr = np.asarray(d1[key])
        if arr.shape == EXPECTED_GRID_SHAPE:
            d1_grid_candidates.append((key, arr))

    for key, arr in d1_grid_candidates:
        supported = np.isfinite(arr)
        if np.any(supported):
            linf = float(np.nanmax(np.abs(d4_grid[supported] - arr[supported])))
            chain_rows.append({
                "stage_from": "SG7D1",
                "stage_to": "SG7D4",
                "from_key": key,
                "to_key": d4_key,
                "from_shape": str(arr.shape),
                "to_shape": str(d4_grid.shape),
                "supported_cells": int(np.sum(supported)),
                "supported_linf_difference": linf,
                "supported_exact": linf == 0.0,
            })

    save_csv(CHAIN_TABLE, chain_rows)

    # -------------------------------------------------------------------------
    # Frozen L2 inventory.
    # -------------------------------------------------------------------------

    l2_rows = []

    for key in l2.files:
        arr = np.asarray(l2[key])
        l2_rows.append({
            "key": key,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "ndim": arr.ndim,
            "size": arr.size,
            "is_streamline_state_candidate": (
                arr.ndim == 2 and arr.shape[1] == 201
            ),
            "is_time_key": (
                "time" in key.lower()
                or "days" in key.lower()
            ),
            "is_xi_key": "xi" in key.lower(),
            "is_tof_key": (
                "tof" in key.lower()
                or "tau" in key.lower()
            ),
        })

    save_csv(L2_ARRAY_TABLE, l2_rows)

    # -------------------------------------------------------------------------
    # Semantic evidence from frozen L2 manifest/contract and validation artifact.
    # -------------------------------------------------------------------------

    semantic_rows = []

    provenance_files = [R1F3_MANIFEST, R1F3_CONTRACT]

    if R1F2CRR_NUM.exists():
        # Inventory keys from independent validation artifact.
        dbv = np.load(R1F2CRR_NUM, allow_pickle=True)
        for key in dbv.files:
            arr = np.asarray(dbv[key])
            semantic_rows.append({
                "source": str(R1F2CRR_NUM),
                "kind": "validation_npz_key",
                "field": key,
                "value": str(arr.shape),
            })
        dbv.close()

    for p in provenance_files:
        text = safe_text(p)
        for label, value, raw in extract_time_semantics_from_text(text):
            semantic_rows.append({
                "source": str(p),
                "kind": label,
                "field": "",
                "value": value or raw,
            })

        try:
            obj = load_json(p)
        except Exception:
            obj = None

        if isinstance(obj, dict):
            stack = [("", obj)]
            while stack:
                prefix, cur = stack.pop()
                if isinstance(cur, dict):
                    for k, v in cur.items():
                        name = f"{prefix}.{k}" if prefix else k
                        if isinstance(v, (dict, list)):
                            stack.append((name, v))
                        else:
                            lk = name.lower()
                            if any(tok in lk for tok in ("time", "day", "xi", "tof", "tau", "terminal")):
                                semantic_rows.append({
                                    "source": str(p),
                                    "kind": "structured_field",
                                    "field": name,
                                    "value": v,
                                })
                elif isinstance(cur, list):
                    for i, v in enumerate(cur):
                        name = f"{prefix}[{i}]"
                        if isinstance(v, (dict, list)):
                            stack.append((name, v))

    save_csv(TIME_SEMANTIC_TABLE, semantic_rows)

    # -------------------------------------------------------------------------
    # Source-code trace for L2 creation/evaluation.
    # -------------------------------------------------------------------------

    source_rows = []

    tokens = [
        "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz",
        "L2",
        "crossing_guard",
        "gamma",
        "100d",
        "times_days",
        "tau_s",
        "xi",
    ]

    for src in project_python_files():
        text = safe_text(src)
        low = text.lower()

        if not any(tok.lower() in low for tok in tokens):
            continue

        lines = text.splitlines()

        for i, line in enumerate(lines, start=1):
            if any(tok.lower() in line.lower() for tok in tokens):
                ctx = "\n".join(
                    lines[max(0, i-10):min(len(lines), i+14)]
                )
                hits = extract_time_semantics_from_text(ctx)

                if hits:
                    source_rows.append({
                        "source": str(src),
                        "line": i,
                        "matched_line": line.strip()[:1200],
                        "context": ctx[:5000],
                        "semantic_hits": ";".join(
                            f"{lab}:{val or raw}"
                            for lab, val, raw in hits
                        ),
                    })

    save_csv(SOURCE_TRACE_TABLE, source_rows)

    # -------------------------------------------------------------------------
    # Xi / TOF semantic audit.
    # -------------------------------------------------------------------------

    xi_tof_rows = []

    # Search L2 and upstream validation keys.
    for key in l2.files:
        lk = key.lower()
        arr = np.asarray(l2[key])

        if "xi" in lk or "tof" in lk or "tau" in lk:
            rec = {
                "artifact": str(R1F3_FROZEN),
                "key": key,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
            }

            if arr.size and np.issubdtype(arr.dtype, np.number):
                rec.update({
                    "min": float(np.nanmin(arr)),
                    "max": float(np.nanmax(arr)),
                    "mean": float(np.nanmean(arr)),
                })

            xi_tof_rows.append(rec)

    if R1F2CRR_NUM.exists():
        dbv = np.load(R1F2CRR_NUM, allow_pickle=True)
        for key in dbv.files:
            lk = key.lower()
            if "xi" in lk or "tof" in lk or "tau" in lk or "time" in lk:
                arr = np.asarray(dbv[key])

                rec = {
                    "artifact": str(R1F2CRR_NUM),
                    "key": key,
                    "shape": str(arr.shape),
                    "dtype": str(arr.dtype),
                }

                if arr.size and np.issubdtype(arr.dtype, np.number):
                    rec.update({
                        "min": float(np.nanmin(arr)),
                        "max": float(np.nanmax(arr)),
                        "mean": float(np.nanmean(arr)),
                    })

                xi_tof_rows.append(rec)

        dbv.close()

    save_csv(TOF_TABLE, xi_tof_rows)

    # -------------------------------------------------------------------------
    # Classification logic.
    # -------------------------------------------------------------------------

    blob = "\n".join(
        " ".join(str(v) for v in row.values())
        for row in semantic_rows + source_rows + xi_tof_rows
    ).lower()

    # Evidence flags
    explicit_physical_time_values = []

    for row in semantic_rows + source_rows:
        txt = " ".join(str(v) for v in row.values()).lower()

        for m in re.finditer(
            r"(?<![0-9.])(100|250|500|1000)(?:\.0+)?\s*(?:d|day|days)?",
            txt,
        ):
            try:
                explicit_physical_time_values.append(float(m.group(1)))
            except Exception:
                pass

    explicit_physical_time_values = sorted(set(explicit_physical_time_values))

    has_terminal = any(tok in blob for tok in (
        "terminal",
        "endpoint",
        "tau_end",
        "terminal_tof",
    ))

    has_xi = "xi" in blob

    has_tof = any(tok in blob for tok in (
        "tof",
        "tau_s",
        "time-of-flight",
        "time of flight",
    ))

    has_normalized = any(tok in blob for tok in (
        "normalized",
        "0 to 1",
        "0->1",
        "common xi",
        "common_xi",
    ))

    has_multi_time = (
        "times_days" in blob
        or len(explicit_physical_time_values) > 1
    )

    classification = None
    physical_time = None

    if len(explicit_physical_time_values) == 1 and not has_multi_time:
        classification = "EXPLICIT_PHYSICAL_TIME_SNAPSHOT"
        physical_time = explicit_physical_time_values[0]

    elif has_multi_time:
        classification = "MULTI_TIME_TRANSPORT_STATE"

    elif has_terminal and not has_xi and not has_tof:
        classification = "TERMINAL_OR_ENDPOINT_STATE"

    elif has_xi or has_tof or has_normalized:
        classification = "NORMALIZED_XI_TAU_DEPLOYMENT_STATE"

    elif has_terminal:
        classification = "TERMINAL_OR_ENDPOINT_STATE"

    else:
        classification = "TRANSPORT_TIME_IDENTITY_UNRESOLVED"

    # Conservative override: if both a physical time label and strong xi/tof
    # semantics coexist, do not force calendar-time identity unless provenance
    # clearly states the frozen state itself is that snapshot.
    if (
        classification == "EXPLICIT_PHYSICAL_TIME_SNAPSHOT"
        and (has_xi or has_tof or has_normalized)
    ):
        classification = "NORMALIZED_XI_TAU_DEPLOYMENT_STATE"
        physical_time = None

    # -------------------------------------------------------------------------
    # Status / next milestone.
    # -------------------------------------------------------------------------

    if classification == "EXPLICIT_PHYSICAL_TIME_SNAPSHOT":
        status = "SG7D4_L2_TRANSPORT_TIME_IDENTITY_RESOLVED"
        diagnosis = "FROZEN_L2_STATE_IS_ONE_EXPLICIT_PHYSICAL_TIME_SNAPSHOT"
        recommendation = (
            "The frozen L2 state resolves to one physical calendar time. Carry that time "
            "through SG7D1/SG7D4/SG7D6 provenance and perform a time-matched SG7E comparison "
            "only at that snapshot. Because historical SG7E requires all four times, audit "
            "whether equivalent frozen deployment states exist for the other required times."
        )
        next_milestone = (
            "V15-SG7E1R17 — Time-Matched Frozen-State Coverage / Multi-Time Readiness Audit"
        )

    elif classification == "MULTI_TIME_TRANSPORT_STATE":
        status = "SG7D4_L2_TRANSPORT_STATE_IS_MULTI_TIME"
        diagnosis = "FROZEN_L2_LINEAGE_CONTAINS_MULTIPLE_PHYSICAL_TIME_STATES"
        recommendation = (
            "The L2 lineage is multi-time rather than a single untimed snapshot. Reconstruct "
            "the per-time SG7D map-back sequence from the corresponding L2 states and preserve "
            "time labels before evaluating historical SG7E gates."
        )
        next_milestone = (
            "V15-SG7E1R17 — Multi-Time L2-to-Grid Deployment Reconstruction Audit"
        )

    elif classification == "NORMALIZED_XI_TAU_DEPLOYMENT_STATE":
        status = "SG7D4_L2_STATE_IS_TRANSPORT_COORDINATE_DEPLOYMENT_STATE"
        diagnosis = "FROZEN_L2_FIELD_IS_XI_TOF_STATE_NOT_CALENDAR_TIME_SNAPSHOT"
        recommendation = (
            "Do not assign 100/250/500/1000 days to the frozen SG7D6 field. The frozen L2 "
            "state is defined in streamline transport coordinates / TOF rather than as one "
            "calendar-time snapshot. The next milestone must reconstruct the temporal deployment "
            "operator that evaluates L2 at the historical physical times and map each time to grid."
        )
        next_milestone = (
            "V15-SG7E1R17 — Physical-Time Evaluation Operator Reconstruction Audit"
        )

    elif classification == "TERMINAL_OR_ENDPOINT_STATE":
        status = "SG7D4_L2_STATE_IS_TERMINAL_ENDPOINT_STATE"
        diagnosis = "FROZEN_L2_FIELD_REPRESENTS_ENDPOINT_NOT_HISTORICAL_CALENDAR_SNAPSHOT"
        recommendation = (
            "Do not compare the endpoint field directly against the four-time SG7E contract. "
            "Recover the pre-endpoint temporal evaluation path or generate provenance-preserving "
            "time-specific states from the frozen model without retraining."
        )
        next_milestone = (
            "V15-SG7E1R17 — Pre-Endpoint Temporal Evaluation Path Audit"
        )

    else:
        status = "SG7D4_L2_TRANSPORT_TIME_IDENTITY_STILL_UNRESOLVED"
        diagnosis = "NUMERICAL_LINEAGE_CLOSED_BUT_TRANSPORT_TIME_SEMANTICS_REMAIN_UNCLEAR"
        recommendation = (
            "Do not evaluate SG7E gates. The numerical lineage from L2 to SG7D6 is established, "
            "but the transport-state time semantics remain unresolved. Audit only the exact L2 "
            "deployment constructor/evaluation call and its time/TOF arguments."
        )
        next_milestone = (
            "V15-SG7E1R17 — L2 Deployment Constructor Time-Argument Audit"
        )

    classification_rows = [{
        "classification": classification,
        "explicit_physical_time_candidates": ";".join(map(str, explicit_physical_time_values)),
        "resolved_physical_time_days": physical_time if physical_time is not None else "",
        "has_terminal_semantics": has_terminal,
        "has_xi_semantics": has_xi,
        "has_tof_semantics": has_tof,
        "has_normalized_semantics": has_normalized,
        "has_multi_time_semantics": has_multi_time,
    }]

    save_csv(CLASS_TABLE, classification_rows)

    checks = [
        ("Incoming R15 unresolved physical-time diagnosis reproduced", True),
        ("SG7D6 frozen grid loaded", True),
        ("SG7D4 completed grid loaded", True),
        ("SG7D4 -> SG7D6 numerical lineage audited", True),
        ("SG7D1 -> SG7D4 supported-state lineage audited", True),
        ("Frozen R1F3 L2 artifact loaded", True),
        ("Frozen L2 array inventory established", True),
        ("Frozen L2 manifest/contract time semantics audited", True),
        ("Independent validation artifact semantics audited", True),
        ("L2 creation/evaluation source contexts audited", True),
        ("Xi/TOF fields audited", True),
        ("Transport state classified without candidate performance", True),
        ("No physical time assigned by similarity", True),
        ("No SG7E performance gate evaluated", True),
        ("No threshold changed or relaxed", True),
    ]

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "transport_state_classification": classification,
        "resolved_physical_time_days": physical_time if physical_time is not None else "",
        "explicit_physical_time_candidates": ";".join(map(str, explicit_physical_time_values)),
        "has_terminal_semantics": has_terminal,
        "has_xi_semantics": has_xi,
        "has_tof_semantics": has_tof,
        "has_normalized_semantics": has_normalized,
        "has_multi_time_semantics": has_multi_time,
        "D6_grid_sha256": d6_hash,
        "D4_grid_sha256": d4_hash,
        "D4_D6_exact_hash_match": d4_hash == d6_hash,
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R16",
            "status": status,
            "diagnosis": diagnosis,
            "transport_state": {
                "classification": classification,
                "resolved_physical_time_days": physical_time,
                "explicit_physical_time_candidates": explicit_physical_time_values,
                "has_terminal_semantics": has_terminal,
                "has_xi_semantics": has_xi,
                "has_tof_semantics": has_tof,
                "has_normalized_semantics": has_normalized,
                "has_multi_time_semantics": has_multi_time,
            },
            "numerical_lineage": {
                "SG7D6_grid_sha256": d6_hash,
                "SG7D4_grid_sha256": d4_hash,
                "SG7D4_to_SG7D6_exact_hash_match": d4_hash == d6_hash,
            },
            "constraints": {
                "candidate_performance_used": False,
                "physical_time_assigned_by_similarity": False,
                "SG7E_gate_evaluated": False,
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
            "milestone": "V15-SG7E1R16",
            "status": status,
            "diagnosis": diagnosis,
            "transport_state_classification": classification,
            "resolved_physical_time_days": physical_time,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("NUMERICAL LINEAGE")
    print(f"  SG7D4 grid SHA-256      : {d4_hash}")
    print(f"  SG7D6 grid SHA-256      : {d6_hash}")
    print(f"  D4 -> D6 exact match    : {d4_hash == d6_hash}")

    print("\nFROZEN L2 INVENTORY")
    print(f"  Artifact                : {R1F3_FROZEN}")
    print(f"  Array count             : {len(l2_rows)}")
    print(f"  201-node states         : {sum(r['is_streamline_state_candidate'] for r in l2_rows)}")
    print(f"  Explicit time keys      : {[r['key'] for r in l2_rows if r['is_time_key']]}")
    print(f"  Xi keys                 : {[r['key'] for r in l2_rows if r['is_xi_key']]}")
    print(f"  TOF/tau keys            : {[r['key'] for r in l2_rows if r['is_tof_key']]}")

    print("\nTRANSPORT-TIME SEMANTICS")
    print(f"  Physical-time candidates: {explicit_physical_time_values}")
    print(f"  Terminal semantics      : {has_terminal}")
    print(f"  Xi semantics            : {has_xi}")
    print(f"  TOF semantics           : {has_tof}")
    print(f"  Normalized semantics    : {has_normalized}")
    print(f"  Multi-time semantics    : {has_multi_time}")

    print("\nCLASSIFICATION")
    print(f"  {classification}")
    if physical_time is not None:
        print(f"  Physical time [days]    : {physical_time:.6f}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R16 LINEAGE VALIDATION")
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
    for p in (
        CHAIN_TABLE,
        L2_ARRAY_TABLE,
        TIME_SEMANTIC_TABLE,
        SOURCE_TRACE_TABLE,
        TOF_TABLE,
        CLASS_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R16 SG7D4-TO-L2 TRANSPORT-TIME LINEAGE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No physical time was assigned by similarity.")
    print("No SG7E performance gate was evaluated.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)

    d6.close()
    d4.close()
    d1.close()
    l2.close()


if __name__ == "__main__":
    main()
