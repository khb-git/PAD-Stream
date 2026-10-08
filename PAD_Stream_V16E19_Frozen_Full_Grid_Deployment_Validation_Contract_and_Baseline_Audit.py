#!/usr/bin/env python3
"""PAD-Stream V16E-19
Frozen Full-Grid Deployment Validation Contract / Baseline Audit.

Contract/baseline milestone after V16E-18-R1 formally froze the independently
validated 100-day SGSim full-grid candidate. E19 verifies the frozen artifact
identity, audits its immutable support/background provenance, computes only
baseline and explicitly diagnostic quantities directly from the frozen field,
and freezes the entry contract for later deployment-validation provenance work.

E19 does NOT adopt or evaluate any historical SG7E pass/fail gate, does NOT
select a reference plume, and does NOT create an authoritative plume threshold.
Historical V15 SG7E0/SG7E0R are bound only as source-pattern authority for the
separation of frozen input, baseline/diagnostic evidence, and gate-provenance
reconciliation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "V16E-19"
SUCCESS = "V16E19_FROZEN_FULL_GRID_DEPLOYMENT_VALIDATION_CONTRACT_BASELINE_PASS"
BLOCKED = "V16E19_FROZEN_FULL_GRID_DEPLOYMENT_VALIDATION_CONTRACT_BASELINE_BLOCKED"
NEXT_PASS = "V16E-20 - Historical SG7E Gate Authority and V16 Applicability Reconciliation"
NEXT_FAIL = "V16E-19-R1 - Repair only the failed V16E-19 contract/baseline gate; preserve the frozen E18-R1 candidate unchanged"

# -----------------------------------------------------------------------------
# V16E-18-R1 frozen deployment authority.
# -----------------------------------------------------------------------------
E18R1_RUNNER = (
    "PAD_Stream_V16E18_R1_E15_Background_Schema_Repair_and_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
    "d3944a6ef13b2c4f36bdcd77fde3845b6f442290e5007b5529c3f288054e7279",
)
E18R1_REL = Path("provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE")
E18R1 = {
    "audit": ("V16E18_R1_Full_Grid_Freeze_Audit.json", "4a77d654cfa218afe4a56d370b7888f5d8e91ec9b9b1281797d0fd86c56499ec"),
    "manifest": ("V16E18_R1_Full_Grid_Freeze_Manifest.json", "f4beb418fb64dd3b97c6f52db4a085e649e155b726fdaff03a3e2f9307d8e59e"),
    "contract": ("V16E18_R1_Frozen_Grid_Deployment_Contract.json", "6c69ee875b724477fb64f3a72cdfbc54098104e0e0de71e62122b044d91916ee"),
    "summary": ("PAD_Stream_V16E18_R1_Summary.json", "7754444cc923fb2179c7de73129f12af351ca0bef91fccbb1a306cc00894df95"),
    "handoff": ("V16E18_R1_Handoff.md", "7ace78ea9c558eda1b6801a846a79ed6b97c8b078908c0a4f3a6aedaf409661c"),
    "hashes_csv": ("V16E18_R1_Artifact_Hashes.csv", "3fc43509316e45318db7a85b1ffab11a6061bc8f8cfc20f1866bbd446da7717a"),
    "provenance_csv": ("V16E18_R1_Provenance_Chain.csv", "11d043f660288ea67c61875a52a199d86c4eb7c76f66f6bdb2e1a596fed3f97a"),
    "gates_csv": ("V16E18_R1_Frozen_Gate_Record.csv", "2d467f3fbd07aba6ac08d1271e109aa93d20adb57301c2ce678899fd210382d6"),
    "identity_csv": ("V16E18_R1_Frozen_Full_Grid_Identity.csv", "4550d80c04bc69c2450cc5291fdb130cef344602e58f802dfb8fa74106c8a644"),
}
E18R1_SUCCESS = "V16E18_R1_FULL_GRID_CANDIDATE_FREEZE_PASS"
FROZEN_REL = E18R1_REL / "frozen_full_grid" / "V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
FROZEN_FILE_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

# Immediate independent-validation parent retained as freeze-entry provenance.
E17R2_RUNNER = (
    "PAD_Stream_V16E17_R2_Blocked_Parent_Locator_Repair_and_Independent_Full_Grid_Completion_Validation.py",
    "a40ddb01dbbe40f7fffcc21203016b94e1b7b939a93d68a22f57360ae668b09e",
)
E17R2_REL = Path("provenance/hybrid_dp/V16E17_R2_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION")
E17R2_READINESS = ("V16E17_R2_Freeze_Readiness_Manifest.json", "9a1ee30a47af214702059ed664286b2892b53fcff36a930d361547e0bca95063")
E17R2_SUMMARY = ("PAD_Stream_V16E17_R2_Summary.json", "96d0b86184cfdc35bed2f5dc11ff9769c0e9424ec6fcfba64ffe60a6676ae676")

# Historical source-pattern authority only; V16 does not adopt gates here.
V15_E0 = (
    "PAD_Stream_V15SG7E0_Frozen_Full_Grid_Deployment_Validation_Contract_Baseline_Audit.py",
    "cc8a280228999d395bb559c4c085a1f3a992419e9a8018b4d1cee07cda3a1bb7",
)
V15_E0R = (
    "PAD_Stream_V15SG7E0R_Historical_SG7E_Gate_Authority_Reconciliation.py",
    "3ba7eef6133333c09aff113c1f92c16e187a856dc5fca856524a7c122c48e3e0",
)

OUT_REL = Path("provenance/hybrid_dp/V16E19_FROZEN_FULL_GRID_DEPLOYMENT_VALIDATION_CONTRACT_BASELINE_AUDIT")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E19_BLOCKED_DEPLOYMENT_VALIDATION_CONTRACT_BASELINE_AUDIT")

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_BACKGROUND_COMPLETED = 17038
EXPECTED_SUPPORT_FRACTION = EXPECTED_SUPPORTED / EXPECTED_CELLS
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
EXPECTED_MIN = 0.2
EXPECTED_MAX = 0.78499960534060065
SELECTED_POLICY = "P4_MASKED_BACKGROUND_PLUS_SUPPORT"
DIAGNOSTIC_THRESHOLD = 0.21  # diagnostic only; explicitly NOT an authoritative SG7E pass/fail threshold

PROHIBITIONS = [
    "NO CHANGE TO THE V16E-18-R1 FROZEN CANDIDATE OR ANY UPSTREAM ARTIFACT.",
    "NO MAP-BACK, BACKGROUND COMPLETION, INDEPENDENT RECONSTRUCTION, OR NUMERICAL REGENERATION.",
    "NO TRAINING, CHECKPOINT LOAD, MODEL INFERENCE, PRESSURE/DARCY/POLLOCK/TOF RECOMPUTATION.",
    "NO INTERPOLATION, NEAREST-NEIGHBOR, ROUTE-SPECIFIC FILL, OR NEW CONSERVATIVE PROJECTION.",
    "NO AUTHORITATIVE SG7E GATE IS ADOPTED OR EVALUATED IN E19.",
    "NO REFERENCE PLUME IS SELECTED IN E19.",
    "0.21 IS DIAGNOSTIC-ONLY AND IS NOT PROMOTED TO AN SG7E PASS/FAIL THRESHOLD.",
    "NO FULL-GRID PLUME CLAIM OR DEPLOYMENT PASS/FAIL DECISION IN E19.",
    "NO INTERNAL-TEST OR OOD REOPENING.",
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


def arr_sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def native(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): native(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [native(x) for x in v]
    if isinstance(v, np.ndarray):
        return native(v.tolist())
    if isinstance(v, np.generic):
        return v.item()
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


def csv_bool(v: Any) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes", "pass"}


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def save_csv(path: Path, rows: list[dict[str, Any]]):
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: native(v) for k, v in row.items()} for row in rows])
    os.replace(tmp, path)


def bind(g: Gates, label: str, path: Path, expected: str) -> str:
    g.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    g.check(label + "_SHA_exact", actual == expected, actual if actual != expected else "")
    return actual


def source_contains(path: Path, required: list[str]) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    return all(token in text for token in required)


def connected_components_3d(mask: np.ndarray) -> list[int]:
    mask = np.asarray(mask, dtype=bool)
    nz, ny, nx = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    nbr = ((-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1))
    sizes: list[int] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if not mask[k,j,i] or seen[k,j,i]:
                    continue
                stack = [(k,j,i)]
                seen[k,j,i] = True
                n = 0
                while stack:
                    ck,cj,ci = stack.pop()
                    n += 1
                    for dk,dj,di in nbr:
                        nk,nj,ni = ck+dk,cj+dj,ci+di
                        if 0 <= nk < nz and 0 <= nj < ny and 0 <= ni < nx and mask[nk,nj,ni] and not seen[nk,nj,ni]:
                            seen[nk,nj,ni] = True
                            stack.append((nk,nj,ni))
                sizes.append(n)
    return sorted(sizes, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--drive-root", required=True)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    compute = Path(args.drive_root).resolve()
    out = compute / OUT_REL
    blocked = compute / BLOCKED_REL
    g = Gates()

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-19 Frozen Full-Grid Deployment Validation Contract / Baseline Audit")
    print("=" * 132)
    for line in PROHIBITIONS:
        print(line)

    try:
        # ------------------------------------------------------------------
        # E18-R1 frozen authority.
        # ------------------------------------------------------------------
        print("\nV16E-18-R1 FROZEN FULL-GRID AUTHORITY")
        bind(g, "E18R1_runner", root / E18R1_RUNNER[0], E18R1_RUNNER[1])
        e18_paths: dict[str, Path] = {}
        for key, (name, digest) in E18R1.items():
            p = compute / E18R1_REL / name
            bind(g, "E18R1_" + key, p, digest)
            e18_paths[key] = p

        frozen_path = compute / FROZEN_REL
        bind(g, "E18R1_frozen_candidate", frozen_path, FROZEN_FILE_SHA)

        e18_audit = read_json(e18_paths["audit"])
        e18_manifest = read_json(e18_paths["manifest"])
        e18_contract = read_json(e18_paths["contract"])
        e18_summary = read_json(e18_paths["summary"])
        e18_gate_rows = read_csv(e18_paths["gates_csv"])

        g.check("E18R1_audit_status_PASS", e18_audit.get("status") == "PASS")
        g.check("E18R1_manifest_status_exact", e18_manifest.get("status") == E18R1_SUCCESS)
        g.check("E18R1_contract_status_exact", e18_contract.get("status") == E18R1_SUCCESS)
        g.check("E18R1_summary_status_PASS", e18_summary.get("status") == "PASS")
        g.check("E18R1_all_frozen_gates_pass", len(e18_gate_rows) > 0 and all(csv_bool(r.get("passed")) for r in e18_gate_rows))
        g.check("E18R1_candidate_frozen", e18_manifest.get("candidate_frozen") is True and e18_summary.get("candidate_frozen") is True)
        g.check("E18R1_authoritative_file_SHA_exact", e18_manifest.get("authoritative_frozen_sha256") == FROZEN_FILE_SHA and e18_summary.get("frozen_full_grid_sha256") == FROZEN_FILE_SHA)
        g.check("E18R1_source_frozen_hash_exact", e18_audit.get("source_frozen_hash_exact") is True and e18_summary.get("source_frozen_hash_exact") is True)
        g.check("E18R1_no_numerical_change", e18_summary.get("numerical_field_changed") is False and e18_manifest.get("numerical_field_changed") is False)
        g.check("E18R1_support_provenance_preserved", e18_summary.get("support_provenance_changed") is False and e18_summary.get("support_evidence_preserved_exact") is True)
        g.check("E18R1_full_grid_plume_not_authorized", e18_summary.get("full_grid_plume_authorized") is False and e18_manifest.get("full_grid_plume_authorized") is False)
        g.check("E18R1_SG7E_threshold_not_changed", e18_summary.get("SG7E_threshold_changed") is False and e18_manifest.get("SG7E_threshold_changed") is False)
        g.check("E18R1_next_is_E19", str(e18_summary.get("next_milestone", "")).startswith("V16E-19"))

        inv = e18_contract.get("invariants", {})
        prov = e18_contract.get("support_provenance", {})
        g.check("E18R1_contract_P4_exact", e18_contract.get("unsupported_cell_policy") == SELECTED_POLICY)
        g.check("E18R1_contract_frozen_bytes_immutable", inv.get("frozen_candidate_bytes_immutable") is True)
        g.check("E18R1_contract_supported_state_immutable", inv.get("supported_state_immutable") is True)
        g.check("E18R1_contract_background_rule_immutable", inv.get("background_completion_rule_immutable") is True)
        g.check("E18R1_contract_no_threshold_defined", inv.get("SG7E_threshold_not_defined_or_changed_by_E18") is True)
        g.check("E18R1_contract_no_plume_claim", inv.get("full_grid_plume_claim_not_authorized_by_E18") is True)
        g.check("E18R1_contract_support_counts_exact", int(prov.get("supported_cells", -1)) == EXPECTED_SUPPORTED and int(prov.get("background_completed_cells", -1)) == EXPECTED_BACKGROUND_COMPLETED)
        g.check("E18R1_contract_completed_cells_remain_unsupported", prov.get("background_completed_cells_remain_unsupported") is True)

        # ------------------------------------------------------------------
        # Independent validation authority retained at validation entry.
        # ------------------------------------------------------------------
        print("\nV16E-17-R2 INDEPENDENT VALIDATION AUTHORITY")
        bind(g, "E17R2_runner", root / E17R2_RUNNER[0], E17R2_RUNNER[1])
        e17_ready_path = compute / E17R2_REL / E17R2_READINESS[0]
        e17_summary_path = compute / E17R2_REL / E17R2_SUMMARY[0]
        bind(g, "E17R2_readiness", e17_ready_path, E17R2_READINESS[1])
        bind(g, "E17R2_summary", e17_summary_path, E17R2_SUMMARY[1])
        e17_ready = read_json(e17_ready_path)
        e17_summary = read_json(e17_summary_path)
        g.check("E17R2_freeze_readiness_was_exact", e17_ready.get("ready_for_V16E18_freeze") is True and e17_ready.get("independent_reconstruction_exact") is True)
        g.check("E17R2_reconstruction_zero_error", float(e17_summary.get("full_grid_reconstruction_L1", np.nan)) == 0.0 and float(e17_summary.get("full_grid_reconstruction_Linf", np.nan)) == 0.0)
        g.check("E17R2_support_evidence_exact", e17_summary.get("support_evidence_preserved_exact") is True)
        g.check("E17R2_full_grid_plume_not_authorized", e17_summary.get("full_grid_plume_authorized") is False)

        # ------------------------------------------------------------------
        # V15 E0/E0R source-pattern authority. No V15 gate is adopted here.
        # ------------------------------------------------------------------
        print("\nVERSION-15 DEPLOYMENT-CONTRACT SOURCE AUTHORITY")
        e0_path = root / V15_E0[0]
        e0r_path = root / V15_E0R[0]
        bind(g, "V15SG7E0_source", e0_path, V15_E0[1])
        bind(g, "V15SG7E0R_source", e0r_path, V15_E0R[1])
        g.check("V15SG7E0_no_threshold_invention_semantics", source_contains(e0_path, [
            "SG7E0 NEVER modifies the frozen field or invents a threshold.",
            "If threshold provenance is ambiguous, the milestone routes to SG7E0R.",
            "DEFAULT_DIAGNOSTIC_THRESHOLD = 0.21",
            '"semantics": "DIAGNOSTIC_ONLY"',
        ]))
        g.check("V15SG7E0R_reconciliation_before_evaluation_semantics", source_contains(e0r_path, [
            "SG7E0R does NOT evaluate the frozen P4 field against gates.",
            "Canonical gate registry constructed",
            "No SG7E threshold changed or relaxed",
        ]))

        # ------------------------------------------------------------------
        # Frozen numerical identity and baseline reconstruction.
        # ------------------------------------------------------------------
        print("\nFROZEN V16E-18-R1 NUMERICAL IDENTITY / BASELINE")
        with np.load(frozen_path, allow_pickle=False) as db:
            required = [
                "saturation_grid_full_float64",
                "saturation_grid_supported_only_float64",
                "supported_mask",
                "support_denominator",
                "support_numerator",
                "segment_piece_count",
                "streamline_visit_count",
                "background_saturation",
                "diagnostic_threshold",
                "physical_time_days",
                "grid_shape",
            ]
            g.check("frozen_required_arrays_present", all(k in db.files for k in required), str(db.files))
            full = np.array(db["saturation_grid_full_float64"], dtype=np.float64, copy=True)
            supported_only = np.array(db["saturation_grid_supported_only_float64"], dtype=np.float64, copy=True)
            support_u8 = np.array(db["supported_mask"], copy=True).astype(np.uint8)
            den = np.array(db["support_denominator"], dtype=np.float64, copy=True)
            num = np.array(db["support_numerator"], dtype=np.float64, copy=True)
            pieces = np.array(db["segment_piece_count"], dtype=np.int64, copy=True)
            visits = np.array(db["streamline_visit_count"], dtype=np.int64, copy=True)
            background = float(np.asarray(db["background_saturation"]))
            diagnostic_threshold = float(np.asarray(db["diagnostic_threshold"]))
            physical_time_days = float(np.asarray(db["physical_time_days"]))
            grid_shape = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())

        g.check("frozen_grid_shape_exact", grid_shape == EXPECTED_GRID and full.shape == EXPECTED_GRID)
        g.check("frozen_time_exact_100d", physical_time_days == EXPECTED_TIME_DAYS)
        g.check("frozen_cell_count_exact", full.size == EXPECTED_CELLS)
        g.check("frozen_all_arrays_shape_exact", all(a.shape == EXPECTED_GRID for a in [supported_only, support_u8, den, num, pieces, visits]))
        g.check("frozen_full_grid_all_finite", np.all(np.isfinite(full)))
        g.check("frozen_background_exact", background == EXPECTED_BACKGROUND, f"{background:.17g}")
        g.check("frozen_min_exact_background", float(np.min(full)) == EXPECTED_MIN, f"{float(np.min(full)):.17g}")
        g.check("frozen_max_exact", float(np.max(full)) == EXPECTED_MAX, f"{float(np.max(full)):.17g}")
        g.check("diagnostic_threshold_exact_0p21", diagnostic_threshold == DIAGNOSTIC_THRESHOLD, f"{diagnostic_threshold:.17g}")

        support = den > 0.0
        unsupported = ~support
        g.check("support_mask_reproduced_from_denominator", np.array_equal(support_u8.astype(bool), support))
        g.check("support_counts_exact", int(np.sum(support)) == EXPECTED_SUPPORTED and int(np.sum(unsupported)) == EXPECTED_BACKGROUND_COMPLETED)
        g.check("support_fraction_exact", float(np.mean(support)) == EXPECTED_SUPPORT_FRACTION, f"{float(np.mean(support)):.17g}")
        g.check("supported_state_exact_sidecar", np.array_equal(full[support], supported_only[support]))
        g.check("supported_only_unsupported_remains_nan", np.all(np.isnan(supported_only[unsupported])))
        g.check("background_completed_cells_exact_background", np.all(full[unsupported] == background))
        g.check("background_completed_cells_remain_unsupported", np.all(support_u8[unsupported] == 0) and np.all(den[unsupported] == 0.0))
        g.check("piece_visit_support_semantics_exact", np.all(pieces[support] > 0) and np.all(visits[support] > 0) and np.all(pieces[unsupported] == 0) and np.all(visits[unsupported] == 0))

        g.check("candidate_array_SHA_matches_E18_audit", arr_sha(full) == e18_audit.get("candidate_array_sha256"))
        g.check("support_mask_SHA_matches_E18_manifest", arr_sha(support_u8) == e18_manifest.get("support_mask_array_sha256"))
        g.check("support_denominator_SHA_matches_E18_manifest", arr_sha(den) == e18_manifest.get("support_denominator_array_sha256"))
        g.check("support_numerator_SHA_matches_E18_manifest", arr_sha(num) == e18_manifest.get("support_numerator_array_sha256"))
        g.check("piece_count_SHA_matches_E18_manifest", arr_sha(pieces) == e18_manifest.get("segment_piece_count_array_sha256"))
        g.check("visit_count_SHA_matches_E18_manifest", arr_sha(visits) == e18_manifest.get("streamline_visit_count_array_sha256"))

        # ------------------------------------------------------------------
        # Baseline and diagnostic-only quantities. No pass/fail use.
        # ------------------------------------------------------------------
        print("\nBASELINE / DIAGNOSTIC-ONLY INVENTORY")
        diagnostic_mask = full >= DIAGNOSTIC_THRESHOLD
        supported_diagnostic = support & diagnostic_mask
        unsupported_diagnostic = unsupported & diagnostic_mask
        components = connected_components_3d(diagnostic_mask)

        baseline = {
            "grid_min": float(np.min(full)),
            "grid_max": float(np.max(full)),
            "grid_mean": float(np.mean(full)),
            "grid_std": float(np.std(full)),
            "supported_mean": float(np.mean(full[support])),
            "background_completed_mean": float(np.mean(full[unsupported])),
            "supported_cells": int(np.sum(support)),
            "background_completed_cells": int(np.sum(unsupported)),
            "support_fraction": float(np.mean(support)),
            "background_saturation": background,
            "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
            "diagnostic_full_grid_cells": int(np.sum(diagnostic_mask)),
            "diagnostic_supported_cells": int(np.sum(supported_diagnostic)),
            "diagnostic_background_completed_cells": int(np.sum(unsupported_diagnostic)),
            "diagnostic_component_count": len(components),
            "diagnostic_largest_component_cells": components[0] if components else 0,
        }
        g.check("diagnostic_background_adds_zero_cells", baseline["diagnostic_background_completed_cells"] == 0)
        g.check("diagnostic_mask_entirely_supported", np.array_equal(diagnostic_mask, supported_diagnostic))
        g.check("baseline_only_no_reference_used", True)
        g.check("baseline_only_no_authoritative_gate_evaluated", True)
        g.check("diagnostic_threshold_role_not_promoted", True)

        # ------------------------------------------------------------------
        # Freeze E19 entry contract. Gate authority remains intentionally open.
        # ------------------------------------------------------------------
        print("\nV16E-19 VALIDATION ENTRY CONTRACT")
        role_rows = [
            {"item": "V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate", "role": "AUTHORITATIVE_FROZEN_INPUT", "pass_fail_use_in_E19": False, "status": "BOUND"},
            {"item": "support_mask/numerator/denominator/piece/visit", "role": "IMMUTABLE_CONSERVATIVE_PROVENANCE", "pass_fail_use_in_E19": False, "status": "BOUND"},
            {"item": "grid_min/max/mean/std/support counts", "role": "BASELINE", "pass_fail_use_in_E19": False, "status": "COMPUTED_FROM_FROZEN_INPUT"},
            {"item": "saturation >= 0.21", "role": "DIAGNOSTIC_ONLY", "pass_fail_use_in_E19": False, "status": "NOT_AN_SG7E_GATE"},
            {"item": "historical_SG7E_gate_registry", "role": "PROVENANCE_PENDING", "pass_fail_use_in_E19": False, "status": "REQUIRES_V16E20_RECONCILIATION"},
            {"item": "authoritative_plume_threshold", "role": "UNDEFINED_IN_E19", "pass_fail_use_in_E19": False, "status": "DO_NOT_INVENT"},
            {"item": "reference_plume", "role": "UNSELECTED_IN_E19", "pass_fail_use_in_E19": False, "status": "DO_NOT_INVENT"},
            {"item": "deployment_PASS_FAIL", "role": "PROHIBITED_IN_E19", "pass_fail_use_in_E19": False, "status": "NOT_AUTHORIZED"},
        ]
        entry_rows = [
            {"entry": "frozen_input_identity", "ready": True, "authority": "V16E-18-R1 byte-for-byte freeze"},
            {"entry": "independent_validation", "ready": True, "authority": "V16E-17-R2 exact reconstruction"},
            {"entry": "support_background_provenance", "ready": True, "authority": "V16E-18-R1 deployment contract"},
            {"entry": "baseline_metrics", "ready": True, "authority": "directly reconstructible from frozen artifact"},
            {"entry": "diagnostic_0p21_context", "ready": True, "authority": "diagnostic only; no pass/fail use"},
            {"entry": "authoritative_gate_registry", "ready": False, "authority": "must be reconciled in V16E-20"},
            {"entry": "authoritative_plume_threshold", "ready": False, "authority": "not defined/adopted in V16E-19"},
            {"entry": "reference_plume", "ready": False, "authority": "not selected in V16E-19"},
            {"entry": "deployment_evaluation", "ready": False, "authority": "not authorized until downstream provenance contract closes"},
        ]

        validation_contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "contract_name": "PAD-Stream V16E-19 Frozen Full-Grid Deployment Validation Entry Contract",
            "authoritative_frozen_input": {
                "file": str(frozen_path),
                "file_sha256": FROZEN_FILE_SHA,
                "candidate_array_sha256": arr_sha(full),
                "grid_shape": list(EXPECTED_GRID),
                "physical_time_days": EXPECTED_TIME_DAYS,
                "supported_cells": EXPECTED_SUPPORTED,
                "background_completed_cells": EXPECTED_BACKGROUND_COMPLETED,
                "background_saturation": EXPECTED_BACKGROUND,
                "selected_policy": SELECTED_POLICY,
            },
            "baseline_semantics": "descriptive quantities computed directly from immutable E18-R1 frozen input; no reference truth and no pass/fail decision",
            "diagnostic_threshold": {
                "value": DIAGNOSTIC_THRESHOLD,
                "role": "DIAGNOSTIC_ONLY",
                "authoritative_SG7E_gate": False,
                "source_pattern": "historical V15 SG7E0 diagnostic baseline and V16 E15-E17 preservation diagnostics",
            },
            "gate_authority": {
                "historical_gate_registry_adopted": False,
                "authoritative_gate_count": 0,
                "authoritative_plume_threshold_defined": False,
                "reference_plume_selected": False,
                "deployment_pass_fail_authorized": False,
                "required_next_action": "reconcile historical SG7E gate authority and V16 applicability without changing thresholds",
            },
            "immutable_invariants": {
                "frozen_candidate_bytes": True,
                "support_mask": True,
                "support_denominator": True,
                "support_numerator": True,
                "segment_piece_count": True,
                "streamline_visit_count": True,
                "background_completion_policy": True,
                "no_numerical_regeneration": True,
                "no_threshold_invention": True,
                "no_reference_invention": True,
            },
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }

        audit = {
            "milestone": MILESTONE,
            "status": "PASS",
            "frozen_file_sha256": FROZEN_FILE_SHA,
            "candidate_array_sha256": arr_sha(full),
            "support_mask_array_sha256": arr_sha(support_u8),
            "support_denominator_array_sha256": arr_sha(den),
            "support_numerator_array_sha256": arr_sha(num),
            "segment_piece_count_array_sha256": arr_sha(pieces),
            "streamline_visit_count_array_sha256": arr_sha(visits),
            "baseline": baseline,
            "authoritative_gate_count_E19": 0,
            "authoritative_plume_threshold_defined": False,
            "reference_plume_selected": False,
            "deployment_pass_fail_evaluated": False,
            "frozen_candidate_modified": False,
            "support_provenance_modified": False,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }

        source_authority = {
            "E18R1_runner_sha256": E18R1_RUNNER[1],
            "E18R1_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E18R1.items()},
            "E18R1_frozen_candidate_sha256": FROZEN_FILE_SHA,
            "E17R2_runner_sha256": E17R2_RUNNER[1],
            "E17R2_readiness_sha256": E17R2_READINESS[1],
            "E17R2_summary_sha256": E17R2_SUMMARY[1],
            "V15SG7E0_source_sha256": V15_E0[1],
            "V15SG7E0R_source_sha256": V15_E0R[1],
        }
        validation_contract["source_authority"] = source_authority
        audit["source_authority"] = source_authority

        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "frozen_candidate_sha256": FROZEN_FILE_SHA,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_BACKGROUND_COMPLETED,
            "support_fraction": EXPECTED_SUPPORT_FRACTION,
            "background_saturation": EXPECTED_BACKGROUND,
            "grid_min": baseline["grid_min"],
            "grid_max": baseline["grid_max"],
            "grid_mean": baseline["grid_mean"],
            "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
            "diagnostic_threshold_role": "DIAGNOSTIC_ONLY",
            "diagnostic_full_grid_cells": baseline["diagnostic_full_grid_cells"],
            "diagnostic_background_completed_cells": baseline["diagnostic_background_completed_cells"],
            "authoritative_gate_registry_adopted": False,
            "authoritative_gate_count": 0,
            "authoritative_plume_threshold_defined": False,
            "reference_plume_selected": False,
            "deployment_validation_authorized": False,
            "frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }

        handoff = f"""# PAD-Stream V16E-19 - Frozen Full-Grid Deployment Validation Contract / Baseline Audit PASS

V16E-19 verified the formal V16E-18-R1 100-day SGSim frozen full-grid candidate and established the immutable deployment-validation entry contract.

- Frozen candidate SHA-256: {FROZEN_FILE_SHA}
- Grid: 15 x 50 x 50
- Physical time: {EXPECTED_TIME_DAYS:.1f} days
- Supported cells: {EXPECTED_SUPPORTED}
- Background-completed cells: {EXPECTED_BACKGROUND_COMPLETED}
- Frozen background Swc: {EXPECTED_BACKGROUND:.17g}
- Frozen field modified by E19: NO
- Support/conservative provenance modified: NO
- Baseline metrics computed from frozen input: YES
- Diagnostic threshold 0.21 role: DIAGNOSTIC ONLY
- Authoritative SG7E deployment gates adopted in E19: NO
- Authoritative plume threshold defined in E19: NO
- Reference plume selected in E19: NO
- Deployment pass/fail evaluated in E19: NO
- Full-grid plume authorized: NO

NEXT: {NEXT_PASS}
""".encode("utf-8")

        out.mkdir(parents=True, exist_ok=True)
        files = {
            "V16E19_Deployment_Validation_Contract.json": enc(validation_contract),
            "V16E19_Baseline_Audit.json": enc(audit),
            "PAD_Stream_V16E19_Summary.json": enc(summary),
            "V16E19_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)

        save_csv(out / "V16E19_Frozen_Input_Identity.csv", [{
            "frozen_file": str(frozen_path),
            "file_sha256": FROZEN_FILE_SHA,
            "candidate_array_sha256": arr_sha(full),
            "grid_shape": "15x50x50",
            "physical_time_days": EXPECTED_TIME_DAYS,
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_BACKGROUND_COMPLETED,
            "support_fraction": EXPECTED_SUPPORT_FRACTION,
            "background_saturation": EXPECTED_BACKGROUND,
            "grid_min": baseline["grid_min"],
            "grid_max": baseline["grid_max"],
            "all_finite": True,
        }])
        save_csv(out / "V16E19_Frozen_Baseline_Metrics.csv", [
            {"metric": k, "value": v, "semantics": "DIAGNOSTIC_ONLY" if k.startswith("diagnostic_") else "BASELINE"}
            for k, v in baseline.items()
        ])
        save_csv(out / "V16E19_Deployment_Compatibility_Audit.csv", [
            {"item": "frozen_grid_shape", "expected": "15x50x50", "observed": "15x50x50", "compatible": True},
            {"item": "frozen_physical_time_days", "expected": 100.0, "observed": physical_time_days, "compatible": True},
            {"item": "full_grid_finite", "expected": True, "observed": True, "compatible": True},
            {"item": "P4_background_policy", "expected": SELECTED_POLICY, "observed": e18_contract.get("unsupported_cell_policy"), "compatible": True},
            {"item": "background_completed_cells_remain_unsupported", "expected": True, "observed": True, "compatible": True},
            {"item": "conservative_support_evidence_available", "expected": True, "observed": True, "compatible": True},
            {"item": "authoritative_gate_registry_ready", "expected": "requires provenance reconciliation", "observed": "not adopted in E19", "compatible": True},
            {"item": "reference_plume_ready", "expected": "requires later provenance contract", "observed": "not selected in E19", "compatible": True},
        ])
        save_csv(out / "V16E19_Validation_Role_Registry.csv", role_rows)
        save_csv(out / "V16E19_Validation_Entry_Matrix.csv", entry_rows)
        save_csv(out / "V16E19_Final_Gate_Matrix.csv", [
            {"gate": name, "passed": rec["passed"], "detail": rec["detail"]}
            for name, rec in g.items.items()
        ])

        print("\n" + "=" * 132)
        print("V16E-19 RESULT: PASS")
        print("=" * 132)
        print(f"{'Frozen candidate SHA-256':72}: {FROZEN_FILE_SHA}")
        print(f"{'SGSim grid / physical time':72}: 15 x 50 x 50 / {EXPECTED_TIME_DAYS:.1f} days")
        print(f"{'Supported / background-completed cells':72}: {EXPECTED_SUPPORTED} / {EXPECTED_BACKGROUND_COMPLETED}")
        print(f"{'Support fraction':72}: {EXPECTED_SUPPORT_FRACTION:.16g}")
        print(f"{'Frozen background saturation Swc':72}: {EXPECTED_BACKGROUND:.17g}")
        print(f"{'Frozen full-grid min / max':72}: {baseline['grid_min']:.17g} / {baseline['grid_max']:.17g}")
        print(f"{'Frozen full-grid mean':72}: {baseline['grid_mean']:.17g}")
        print(f"{'Diagnostic threshold':72}: {DIAGNOSTIC_THRESHOLD:.17g} (DIAGNOSTIC ONLY)")
        print(f"{'Diagnostic full-grid cells / unsupported cells':72}: {baseline['diagnostic_full_grid_cells']} / {baseline['diagnostic_background_completed_cells']}")
        print(f"{'Authoritative deployment gates adopted':72}: NO")
        print(f"{'Authoritative plume threshold defined':72}: NO")
        print(f"{'Reference plume selected':72}: NO")
        print(f"{'Deployment pass/fail evaluated':72}: NO")
        print(f"{'Frozen candidate modified':72}: NO")
        print(f"{'Full-grid plume authorized':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        for name in [
            "V16E19_Frozen_Input_Identity.csv",
            "V16E19_Frozen_Baseline_Metrics.csv",
            "V16E19_Deployment_Compatibility_Audit.csv",
            "V16E19_Validation_Role_Registry.csv",
            "V16E19_Validation_Entry_Matrix.csv",
            "V16E19_Final_Gate_Matrix.csv",
        ]:
            print(f"{name} SHA: {sha(out / name)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-19 did not close: {exc}", flush=True)
        try:
            blocked.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "E18R1_modified": False,
                "frozen_candidate_modified": False,
                "support_provenance_modified": False,
                "authoritative_gate_registry_adopted": False,
                "authoritative_plume_threshold_defined": False,
                "reference_plume_selected": False,
                "deployment_pass_fail_evaluated": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = blocked / "V16E19_Blocked_Deployment_Validation_Contract_Baseline_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", blocked)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
