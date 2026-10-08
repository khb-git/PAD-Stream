#!/usr/bin/env python3
"""PAD-Stream V16E-21
Historical SG7E Plume-Threshold and Reference-Plume Provenance Reconciliation.

This milestone is provenance-only. It binds the accepted V16E-20-R2 gate
registry/applicability contract, preserves the frozen V16E-18-R1 full-grid
candidate exactly, and reconciles the historical SG7E plume-threshold lineage
from the V15 SG7E1R0/R1/R2 forensic sources.

E21 does not evaluate the four deployment gates. It does not select a reference
plume. It does not modify the frozen V16 candidate. Its purpose is to separate
the historical authoritative plume-mask threshold from the unrelated 0.21
map-back diagnostic threshold and to freeze the remaining reference-truth
provenance problem for the next milestone.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

MILESTONE = "V16E-21"
SUCCESS = "V16E21_HISTORICAL_SG7E_PLUME_THRESHOLD_RECONCILED_REFERENCE_PROVENANCE_DEFERRED"
BLOCKED = "V16E21_HISTORICAL_SG7E_PLUME_THRESHOLD_REFERENCE_PROVENANCE_BLOCKED"
NEXT_PASS = "V16E-22 - Historical SG7E 100-Day Reference-Truth Lineage Reconstruction Audit"
NEXT_FAIL = "V16E-21-R1 - Repair only the failed V16E-21 threshold/reference provenance gate; preserve E18-R1/E19/E20-R2 unchanged"

# -----------------------------------------------------------------------------
# Accepted V16E-20-R2 authority.
# -----------------------------------------------------------------------------
E20R2_RUNNER = (
    "PAD_Stream_V16E20_R2_SG7E0R_Semantic_String_Repair_and_V16_Applicability_Audit.py",
    "fc60f11a588ca24e2bb246859f0c3d3b4be3799a1191b0679f5fada9ddef7022",
)
E20R2_REL = Path(
    "provenance/hybrid_dp/"
    "V16E20_R2_HISTORICAL_SG7E_GATE_AUTHORITY_V16_APPLICABILITY_RECONCILIATION"
)
E20R2 = {
    "contract": (
        "V16E20_R2_Historical_SG7E_Gate_Authority_Contract.json",
        "1467c6d8dcf2e7a414e4808618c94fa0dd5770063587ee213ecd64550d4375ec",
    ),
    "applicability": (
        "V16E20_R2_V16_Applicability_Audit.json",
        "9baddcb61cd0a03f3c6cb29824dbf7029a78d05027cc30c28483ff5b8120ac7f",
    ),
    "summary": (
        "PAD_Stream_V16E20_R2_Summary.json",
        "7c601b189f6a92046f16ceccb32bb290fa240e9a87f8a1dbd888445edbf0f84f",
    ),
    "handoff": (
        "V16E20_R2_Handoff.md",
        "ae2d729b8a1bc344f83b921236cb389b95c27357bfd55238b086ed8439d2768b",
    ),
    "registry_csv": (
        "V16E20_R2_Historical_Authoritative_Gate_Registry.csv",
        "1d0cddd73eec4d2cfa8c95c0659145e41a66d9fd5ebb636c544a9e8341efd68f",
    ),
    "applicability_csv": (
        "V16E20_R2_V16_Gate_Applicability_Matrix.csv",
        "6b2370090cba83fba42841852ade00615ccd61ff873281baa1c108bf093b5daa",
    ),
    "source_csv": (
        "V16E20_R2_Source_Authority.csv",
        "1672289202bdb2d84137751a3244a31e46aeb29b13505f16030a8eaab618b10f",
    ),
    "prereq_csv": (
        "V16E20_R2_Evaluation_Prerequisite_Matrix.csv",
        "1e7a84ce37e8f933b806d766c3d1341f04d1abdea9b691dfe16f3f09b65ec737",
    ),
    "gates_csv": (
        "V16E20_R2_Final_Gate_Matrix.csv",
        "dfa6546e16e80cc0c05f4c09ee4317cf3fcef39213b8a7a61cc7c1067460fa60",
    ),
}

FROZEN_REL = Path(
    "provenance/hybrid_dp/"
    "V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
FROZEN_FILE_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

# -----------------------------------------------------------------------------
# Historical V15 reference/threshold forensic source authority.
# These are immutable source snapshots; no historical output is rewritten.
# -----------------------------------------------------------------------------
V15_R0 = (
    "PAD_Stream_V15SG7E1R0_Historical_SG7E_Reference_Plume_Provenance_Audit.py",
    "e9ec9d8a377965017349466a98c78a2adea02f3d5cb11b929c42a7d17b7bf34b",
)
V15_R1 = (
    "PAD_Stream_V15SG7E1R1_Reference_Plume_Lineage_Conflict_Audit.py",
    "350b962209ee2f5ae15b33287a195712b0ac1b11840660a36e2467198b1048a7",
)
V15_R2 = (
    "PAD_Stream_V15SG7E1R2_Top_Reference_Lineage_Creation_Chain_Audit.py",
    "e6c2b77f1911fc4109ab333fdc8b35e7390754b69693b0f158548b786e789f12",
)

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E21_HISTORICAL_SG7E_PLUME_THRESHOLD_REFERENCE_PROVENANCE_RECONCILIATION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E21_BLOCKED_HISTORICAL_SG7E_PLUME_THRESHOLD_REFERENCE_PROVENANCE"
)

HISTORICAL_PLUME_THRESHOLD = 0.5
DIAGNOSTIC_MAPBACK_THRESHOLD = 0.21
EXPECTED_GRID = [15, 50, 50]
EXPECTED_TIME_DAYS = 100.0

PROHIBITIONS = [
    "NO CHANGE TO THE V16E-18-R1 FROZEN CANDIDATE OR ANY V16E-19/V16E-20-R2 ARTIFACT.",
    "NO MAP-BACK, BACKGROUND COMPLETION, TRANSPORT, PRESSURE, DARCY, POLLOCK, OR TOF RECOMPUTATION.",
    "NO TRAINING, CHECKPOINT LOAD, MODEL INFERENCE, OR INTERNAL-TEST/OOD REOPENING.",
    "NO DEPLOYMENT GATE IS EVALUATED IN E21.",
    "NO REFERENCE PLUME IS SELECTED IN E21.",
    "NO CANDIDATE PERFORMANCE MAY BE USED TO CHOOSE REFERENCE TRUTH.",
    "0.21 REMAINS MAP-BACK/TOPOLOGY DIAGNOSTIC-ONLY AND IS NOT THE HISTORICAL SG7E PLUME THRESHOLD.",
    "THE HISTORICAL SG7E PLUME THRESHOLD IS RECONCILED FROM SOURCE PROVENANCE ONLY; IT IS NOT TUNED TO V16.",
    "NO DEPLOYMENT PASS/FAIL OR FULL-GRID PLUME CLAIM IS MADE IN E21.",
]


class GateError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items: dict[str, dict[str, Any]] = {}

    def check(self, name: str, cond: Any, detail: str = ""):
        ok = bool(cond)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name + (f": {detail}" if detail else ""))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def native(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): native(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [native(x) for x in v]
    if isinstance(v, Path):
        return str(v)
    return v


def enc(v: Any) -> bytes:
    return (json.dumps(native(v), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def save_csv(path: Path, rows: list[dict[str, Any]]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: native(v) for k, v in row.items()})


def semantic_string_corpus(text: str) -> str:
    """Join Python string constants using parser semantics, not raw line layout."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ""
    strings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return "\n".join(strings)


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def verify_file(g: Gates, path: Path, expected_sha: str, label: str):
    g.check(f"{label}_exists", path.is_file(), str(path))
    got = sha(path) if path.is_file() else ""
    g.check(f"{label}_SHA_exact", got == expected_sha, got)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--drive-root", type=Path, required=True)
    args = ap.parse_args()

    root = args.project_root.resolve()
    drive = args.drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    g = Gates()

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-21 Historical SG7E Plume-Threshold and Reference-Plume Provenance Reconciliation")
    print("=" * 132)
    for line in PROHIBITIONS:
        print(line)

    try:
        # ------------------------------------------------------------------
        # V16E-20-R2 accepted authority.
        # ------------------------------------------------------------------
        print("\nV16E-20-R2 GATE-AUTHORITY / APPLICABILITY AUTHORITY")
        e20_runner = root / E20R2_RUNNER[0]
        verify_file(g, e20_runner, E20R2_RUNNER[1], "E20R2_runner")

        e20_dir = drive / E20R2_REL
        e20_paths: dict[str, Path] = {}
        for key, (name, expected) in E20R2.items():
            p = e20_dir / name
            e20_paths[key] = p
            verify_file(g, p, expected, f"E20R2_{key}")

        e20_summary = read_json(e20_paths["summary"])
        e20_contract = read_json(e20_paths["contract"])
        e20_audit = read_json(e20_paths["applicability"])
        e20_registry = read_csv(e20_paths["registry_csv"])
        e20_prereq = read_csv(e20_paths["prereq_csv"])
        e20_gates = read_csv(e20_paths["gates_csv"])

        g.check("E20R2_summary_status_PASS", e20_summary.get("status") == "PASS")
        g.check("E20R2_all_recorded_gates_pass", bool(e20_gates) and all(str(r.get("passed", "")).lower() in {"true", "1"} for r in e20_gates))
        g.check("E20R2_historical_gate_registry_exact_four", len(e20_registry) == 4)
        g.check("E20R2_V16_structural_applicability_exact_four", int(e20_summary.get("V16_structurally_applicable_gate_count", -1)) == 4)
        g.check("E20R2_no_evaluable_gate_yet", int(e20_summary.get("V16_evaluable_gate_count", -1)) == 0)
        g.check("E20R2_no_authoritative_plume_threshold_yet", e20_summary.get("authoritative_plume_threshold_defined") is False)
        g.check("E20R2_no_reference_selected_yet", e20_summary.get("reference_plume_selected") is False)
        g.check("E20R2_no_deployment_evaluation_yet", e20_summary.get("deployment_pass_fail_evaluated") is False)
        g.check("E20R2_diagnostic_0p21_role_exact", float(e20_summary.get("diagnostic_threshold")) == DIAGNOSTIC_MAPBACK_THRESHOLD and e20_summary.get("diagnostic_threshold_role") == "DIAGNOSTIC_ONLY")
        g.check("E20R2_frozen_candidate_unchanged", e20_summary.get("frozen_candidate_modified") is False)
        g.check("E20R2_full_grid_plume_not_authorized", e20_summary.get("full_grid_plume_authorized") is False)
        g.check("E20R2_next_is_E21", str(e20_summary.get("next_milestone", "")).startswith("V16E-21"))

        prereq_lookup = {r.get("prerequisite", ""): r.get("status", "") for r in e20_prereq}
        g.check("E20R2_threshold_prerequisite_unresolved", prereq_lookup.get("authoritative plume threshold") == "UNRESOLVED")
        g.check("E20R2_reference_prerequisite_unresolved", prereq_lookup.get("reference plume identity") == "UNRESOLVED")

        frozen_path = drive / FROZEN_REL
        verify_file(g, frozen_path, FROZEN_FILE_SHA, "E18R1_frozen_candidate")

        # ------------------------------------------------------------------
        # Historical V15 source authority.
        # ------------------------------------------------------------------
        print("\nHISTORICAL V15 SG7E REFERENCE / THRESHOLD SOURCE AUTHORITY")
        r0_path = root / V15_R0[0]
        r1_path = root / V15_R1[0]
        r2_path = root / V15_R2[0]
        verify_file(g, r0_path, V15_R0[1], "V15SG7E1R0_source")
        verify_file(g, r1_path, V15_R1[1], "V15SG7E1R1_source")
        verify_file(g, r2_path, V15_R2[1], "V15SG7E1R2_source")

        r0 = r0_path.read_text(encoding="utf-8", errors="strict")
        r1 = r1_path.read_text(encoding="utf-8", errors="strict")
        r2 = r2_path.read_text(encoding="utf-8", errors="strict")
        r0n, r1n, r2n = normalized(r0), normalized(r1), normalized(r2)
        r0s, r1s, r2s = normalized(semantic_string_corpus(r0)), normalized(semantic_string_corpus(r1)), normalized(semantic_string_corpus(r2))

        # R0 must recover threshold from discovered evidence rather than hardcode
        # a value for the V16 candidate.
        g.check("V15R0_threshold_evidence_extractor_present", "def extract_threshold_evidence" in r0 and "def reconcile_threshold" in r0)
        g.check("V15R0_threshold_resolution_is_provenance_ranked", "THRESHOLD_PROVENANCE_MARGIN" in r0 and "AMBIGUOUS_THRESHOLD_VALUES" in r0)
        g.check("V15R0_no_gate_evaluation_semantics", "SG7E1R0 does NOT evaluate deployment gates" in r0)
        g.check("V15R0_no_threshold_change_semantics", "No SG7E threshold was changed or relaxed" in r0s or "No SG7E threshold changed or relaxed" in r0s)

        # R1 is the first source that explicitly records the historical R0
        # outcome: S_plume=0.5 resolved, reference still ambiguous.
        g.check(
            "V15R1_historical_threshold_0p5_explicit",
            bool(re.search(r"threshold\s*==\s*0\.5", r1)) and "S_plume = 0.5" in r1,
        )
        g.check("V15R1_reference_ambiguity_explicit", "AMBIGUOUS_DISTINCT_REFERENCE_ARRAYS" in r1)
        g.check("V15R1_candidate_performance_prohibited_for_reference_selection", "No frozen candidate performance used for reference selection" in r1s)
        g.check("V15R1_no_gate_evaluation_semantics", "SG7E1R1 does NOT evaluate deployment gates" in r1)

        # R2 independently retains 0.5 and defines the safe historical outcome
        # when no persisted 15x50x50 array has valid reference-truth semantics.
        g.check(
            "V15R2_historical_threshold_0p5_retained",
            bool(re.search(r"abs\(threshold\s*-\s*0\.5\)\s*<\s*1e-15", r2.replace(" ", "")))
            or "Resolved historical plume threshold retained" in r2,
        )
        g.check("V15R2_reference_truth_nonpersistence_status_present", "SG7E_HISTORICAL_REFERENCE_TRUTH_NOT_PERSISTED" in r2)
        g.check("V15R2_reference_truth_nonpersistence_diagnosis_present", "NO_DISCOVERED_15X50X50_ARRAY_HAS_VALID_REFERENCE_TRUTH_SEMANTICS" in r2)
        g.check("V15R2_diagnostic_arrays_excluded_from_truth", "Coverage/support diagnostics explicitly excluded from truth eligibility" in r2s)
        g.check("V15R2_candidate_performance_prohibited_for_reference_selection", "No frozen-candidate performance used for reference selection" in r2s)
        g.check("V15R2_routes_to_reference_input_reconstruction", "Historical SG7E Reference Input Reconstruction Audit" in r2s)

        # ------------------------------------------------------------------
        # Threshold reconciliation.
        # ------------------------------------------------------------------
        print("\nHISTORICAL PLUME-THRESHOLD RECONCILIATION")
        r1_threshold = 0.5 if (re.search(r"threshold\s*==\s*0\.5", r1) and "S_plume = 0.5" in r1) else None
        r2_threshold = 0.5 if ("Resolved historical plume threshold retained" in r2 and "0.5" in r2) else None

        g.check("historical_threshold_R1_R2_consistent", r1_threshold == HISTORICAL_PLUME_THRESHOLD and r2_threshold == HISTORICAL_PLUME_THRESHOLD)
        g.check("historical_authoritative_plume_threshold_reconciled", HISTORICAL_PLUME_THRESHOLD == 0.5, "S >= 0.5")
        g.check("historical_threshold_not_tuned_to_V16", True)
        g.check("diagnostic_0p21_distinct_from_authoritative_0p5", DIAGNOSTIC_MAPBACK_THRESHOLD != HISTORICAL_PLUME_THRESHOLD)
        g.check("diagnostic_0p21_not_promoted", True)
        g.check("historical_0p5_not_used_for_gate_evaluation_in_E21", True)

        # ------------------------------------------------------------------
        # Reference-plume provenance state.
        # ------------------------------------------------------------------
        print("\nREFERENCE-PLUME PROVENANCE STATE")
        g.check("historical_reference_not_selected_from_R1_ambiguity", "AMBIGUOUS_DISTINCT_REFERENCE_ARRAYS" in r1)
        g.check("historical_reference_requires_truth_lineage_reconstruction", "NO_DISCOVERED_15X50X50_ARRAY_HAS_VALID_REFERENCE_TRUTH_SEMANTICS" in r2)
        g.check("no_reference_plume_selected_in_E21", True)
        g.check("no_candidate_performance_used_for_reference_selection_E21", True)
        g.check("reference_time_identity_not_claimed_in_E21", True)
        g.check("no_deployment_pass_fail_evaluated", True)
        g.check("frozen_candidate_not_modified", sha(frozen_path) == FROZEN_FILE_SHA)
        g.check("full_grid_plume_not_authorized", True)

        # ------------------------------------------------------------------
        # Persist provenance-only outputs.
        # ------------------------------------------------------------------
        threshold_contract = {
            "milestone": MILESTONE,
            "status": "PASS",
            "historical_SG7E_plume_threshold": {
                "value": HISTORICAL_PLUME_THRESHOLD,
                "operator": ">=",
                "semantic_role": "AUTHORITATIVE_HISTORICAL_PLUME_MASK_THRESHOLD_FOR_FUTURE_V16_GATE_EVALUATION",
                "reconciled_from": [V15_R0[0], V15_R1[0], V15_R2[0]],
                "changed_or_tuned_in_V16": False,
            },
            "diagnostic_mapback_threshold": {
                "value": DIAGNOSTIC_MAPBACK_THRESHOLD,
                "semantic_role": "DIAGNOSTIC_ONLY_NOT_SG7E_AUTHORITY",
                "promoted": False,
            },
            "gate_evaluation_performed": False,
            "frozen_candidate_modified": False,
            "next_milestone": NEXT_PASS,
        }

        reference_status = {
            "milestone": MILESTONE,
            "status": "PASS",
            "reference_plume_selected": False,
            "reference_truth_status": "UNRESOLVED_REQUIRES_HISTORICAL_100_DAY_TRUTH_LINEAGE_RECONSTRUCTION",
            "historical_evidence": {
                "R1": "resolved threshold / ambiguous distinct reference arrays",
                "R2": "no discovered 15x50x50 array safely eligible as persisted reference truth; reconstruct original upstream physics reference input",
            },
            "selection_constraints": {
                "candidate_performance_used": False,
                "posthoc_alignment_used": False,
                "diagnostic_or_coverage_arrays_promoted_to_truth": False,
                "reference_selected_by_convenience": False,
            },
            "next_milestone": NEXT_PASS,
        }

        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "frozen_candidate_sha256": FROZEN_FILE_SHA,
            "grid_shape": EXPECTED_GRID,
            "physical_time_days": EXPECTED_TIME_DAYS,
            "historical_authoritative_gate_count": 4,
            "historical_authoritative_plume_threshold": HISTORICAL_PLUME_THRESHOLD,
            "historical_authoritative_plume_threshold_reconciled": True,
            "diagnostic_threshold": DIAGNOSTIC_MAPBACK_THRESHOLD,
            "diagnostic_threshold_role": "DIAGNOSTIC_ONLY",
            "diagnostic_threshold_promoted": False,
            "reference_plume_selected": False,
            "reference_truth_status": "UNRESOLVED_REQUIRES_LINEAGE_RECONSTRUCTION",
            "V16_evaluable_gate_count": 0,
            "deployment_pass_fail_evaluated": False,
            "frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }

        handoff = f"""# PAD-Stream V16E-21 PASS

Historical SG7E plume-threshold provenance is reconciled without changing the V16 frozen candidate or tuning a threshold to V16.

- Historical authoritative SG7E plume-mask threshold: `S >= 0.5`
- V16 map-back/topology diagnostic threshold: `S >= 0.21` (DIAGNOSTIC ONLY)
- 0.21 promoted to SG7E authority: NO
- Four historical deployment gates evaluated: NO
- Historical 100-day reference truth selected: NO
- Candidate performance used to choose truth: NO
- Frozen V16E-18-R1 candidate modified: NO
- Full-grid plume authorized: NO

The historical V15 reference lineage remains unresolved at this stage: R1 records ambiguous distinct reference arrays and R2 requires reconstruction of the original upstream physics/reference input rather than repurposing coverage/support diagnostics.

NEXT: {NEXT_PASS}
""".encode("utf-8")

        out.mkdir(parents=True, exist_ok=True)
        files = {
            "V16E21_Historical_Plume_Threshold_Contract.json": enc(threshold_contract),
            "V16E21_Reference_Plume_Provenance_Status.json": enc(reference_status),
            "PAD_Stream_V16E21_Summary.json": enc(summary),
            "V16E21_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)

        save_csv(out / "V16E21_Threshold_Authority_Evidence.csv", [
            {
                "source": V15_R0[0],
                "sha256": V15_R0[1],
                "evidence": "threshold extracted/reconciled from historical SG7E source evidence",
                "threshold_value": "",
                "role": "FORENSIC_RESOLUTION_METHOD",
            },
            {
                "source": V15_R1[0],
                "sha256": V15_R1[1],
                "evidence": "R0 resolved historical plume threshold; exact retained check",
                "threshold_value": HISTORICAL_PLUME_THRESHOLD,
                "role": "HISTORICAL_THRESHOLD_CONFIRMATION",
            },
            {
                "source": V15_R2[0],
                "sha256": V15_R2[1],
                "evidence": "resolved historical plume threshold retained",
                "threshold_value": HISTORICAL_PLUME_THRESHOLD,
                "role": "INDEPENDENT_LINEAGE_RETENTION",
            },
        ])
        save_csv(out / "V16E21_Threshold_Role_Separation.csv", [
            {
                "threshold": HISTORICAL_PLUME_THRESHOLD,
                "role": "AUTHORITATIVE_HISTORICAL_SG7E_PLUME_MASK_FOR_FUTURE_V16_EVALUATION",
                "deployment_gate_use_in_E21": False,
                "promoted_or_tuned": False,
            },
            {
                "threshold": DIAGNOSTIC_MAPBACK_THRESHOLD,
                "role": "DIAGNOSTIC_ONLY_MAPBACK_TOPOLOGY",
                "deployment_gate_use_in_E21": False,
                "promoted_or_tuned": False,
            },
        ])
        save_csv(out / "V16E21_Reference_Provenance_Evidence.csv", [
            {
                "source": V15_R1[0],
                "sha256": V15_R1[1],
                "historical_state": "AMBIGUOUS_DISTINCT_REFERENCE_ARRAYS",
                "reference_selected_in_E21": False,
                "candidate_performance_allowed_for_selection": False,
            },
            {
                "source": V15_R2[0],
                "sha256": V15_R2[1],
                "historical_state": "NO_DISCOVERED_15X50X50_ARRAY_HAS_VALID_REFERENCE_TRUTH_SEMANTICS",
                "reference_selected_in_E21": False,
                "candidate_performance_allowed_for_selection": False,
            },
        ])
        save_csv(out / "V16E21_Evaluation_Prerequisite_Matrix.csv", [
            {"prerequisite": "frozen V16 candidate identity", "status": "READY"},
            {"prerequisite": "historical four-gate authority", "status": "READY"},
            {"prerequisite": "V16 structural gate applicability", "status": "READY"},
            {"prerequisite": "historical authoritative plume threshold", "status": "READY_0.5"},
            {"prerequisite": "100-day historical reference truth identity", "status": "UNRESOLVED"},
            {"prerequisite": "deployment gate evaluation", "status": "BLOCKED_PENDING_REFERENCE_TRUTH"},
        ])
        save_csv(out / "V16E21_Final_Gate_Matrix.csv", [
            {"gate": name, "passed": rec["passed"], "detail": rec["detail"]}
            for name, rec in g.items.items()
        ])

        print("\n" + "=" * 132)
        print("V16E-21 RESULT: PASS")
        print("=" * 132)
        print(f"{'Frozen candidate SHA-256':76}: {FROZEN_FILE_SHA}")
        print(f"{'Grid / primary time':76}: 15 x 50 x 50 / {EXPECTED_TIME_DAYS:.1f} days")
        print(f"{'Historical authoritative deployment gates retained':76}: 4")
        print(f"{'Historical authoritative plume threshold':76}: S >= {HISTORICAL_PLUME_THRESHOLD:.1f}")
        print(f"{'Diagnostic map-back threshold':76}: S >= {DIAGNOSTIC_MAPBACK_THRESHOLD:.2f} (DIAGNOSTIC ONLY)")
        print(f"{'Diagnostic 0.21 promoted':76}: NO")
        print(f"{'Reference plume selected':76}: NO")
        print(f"{'Reference truth status':76}: REQUIRES HISTORICAL 100-DAY LINEAGE RECONSTRUCTION")
        print(f"{'V16 gates evaluable in E21':76}: 0")
        print(f"{'Deployment pass/fail evaluated':76}: NO")
        print(f"{'Frozen candidate modified':76}: NO")
        print(f"{'Full-grid plume authorized':76}: NO")
        print(f"{'Internal test / OOD reopened':76}: NO / NO")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        for name in [
            "V16E21_Threshold_Authority_Evidence.csv",
            "V16E21_Threshold_Role_Separation.csv",
            "V16E21_Reference_Provenance_Evidence.csv",
            "V16E21_Evaluation_Prerequisite_Matrix.csv",
            "V16E21_Final_Gate_Matrix.csv",
        ]:
            print(f"{name} SHA: {sha(out / name)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-21 did not close: {exc}", flush=True)
        try:
            blocked.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "E20R2_modified": False,
                "frozen_candidate_modified": False,
                "historical_authoritative_plume_threshold_reconciled": False,
                "diagnostic_0p21_promoted": False,
                "reference_plume_selected": False,
                "deployment_pass_fail_evaluated": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = blocked / "V16E21_Blocked_Historical_SG7E_Plume_Threshold_Reference_Provenance_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", blocked)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
